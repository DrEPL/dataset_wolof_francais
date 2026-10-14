"""
prepare_dataset.py
------------------
1. Charge data/interim/cleaned.csv
2. Applique le doublement bidirectionnel (WO-FR + FR-WO)
3. Mélange de façon reproductible
4. Divise en train / validation / test selon params.yaml
5. Écrit dans data/processed/

Colonnes de sortie : source | target | tgt_lang_code

Usage :
    python scripts/prepare_dataset.py
"""

import random
from pathlib import Path

import pandas as pd
import yaml

# ── Chemins ────────────────────────────────────────────────────────────────────

INPUT_FILE = Path("data/interim/cleaned.csv")
OUTPUT_DIR = Path("data/processed")
PARAMS_FILE = Path("params.yaml")


# ── Chargement des paramètres ──────────────────────────────────────────────────

def load_params() -> tuple[dict, dict]:
    """Retourne (double_params, split_params) depuis params.yaml."""
    with PARAMS_FILE.open("r", encoding="utf-8") as fh:
        all_params = yaml.safe_load(fh)
    return (
        all_params.get("double_examples", {}),
        all_params.get("prepare_dataset", {}),
    )


# ── Doublement bidirectionnel ──────────────────────────────────────────────────

def double_examples(
    df: pd.DataFrame,
    wolof_lang_code: str,
    french_lang_code: str,
) -> pd.DataFrame:
    """
    Pour chaque paire (wolof, francais), crée deux exemples :
      • WO → FR  (source=wolof,   target=francais, tgt_lang_code=fra_Latn)
      • FR → WO  (source=francais, target=wolof,   tgt_lang_code=wol_Latn)

    Retourne un DataFrame avec les colonnes : source | target | tgt_lang_code
    """
    sources:   list[str] = []
    targets:   list[str] = []
    tgt_langs: list[str] = []

    for wolof, francais in zip(df["wolof"], df["francais"]):
        # WO → FR
        sources.append(wolof)
        targets.append(francais)
        tgt_langs.append(french_lang_code)

        # FR → WO
        sources.append(francais)
        targets.append(wolof)
        tgt_langs.append(wolof_lang_code)

    return pd.DataFrame({
        "source":       sources,
        "target":       targets,
        "tgt_lang_code": tgt_langs,
    })


# ── Split ──────────────────────────────────────────────────────────────────────

def make_splits(
    df: pd.DataFrame,
    train_ratio: float,
    validation_ratio: float,
    test_ratio: float,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Mélange et divise df en trois ensembles disjoints.
    Garantit qu'aucun split n'est vide.
    """
    total = round(train_ratio + validation_ratio + test_ratio, 9)
    if abs(total - 1.0) > 1e-6:
        raise ValueError(
            f"Les ratios doivent totaliser 1.0 — actuel : {total}"
        )
    if any(r < 0 for r in (train_ratio, validation_ratio, test_ratio)):
        raise ValueError("Tous les ratios doivent être positifs.")

    # Mélange reproductible sans dépendance à scikit-learn
    indices = list(range(len(df)))
    random.Random(seed).shuffle(indices)
    df = df.iloc[indices].reset_index(drop=True)

    n = len(df)
    n_train = max(1, int(n * train_ratio))
    n_val   = max(1, int(n * validation_ratio))

    # S'assurer que le test n'est pas vide
    if n_train + n_val >= n:
        n_train = n - 2
        n_val = 1

    train      = df.iloc[:n_train]
    validation = df.iloc[n_train : n_train + n_val]
    test       = df.iloc[n_train + n_val :]

    return train, validation, test


# ── Point d'entrée ─────────────────────────────────────────────────────────────

def main() -> None:
    print("=== prepare_dataset ===")

    double_params, split_params = load_params()

    wolof_lang_code = double_params.get("wolof_lang_code", "wol_Latn")
    french_lang_code = double_params.get("french_lang_code", "fra_Latn")
    shuffle_seed = int(double_params.get("shuffle_seed", 42))

    seed             = int(split_params["seed"])
    train_ratio      = float(split_params["train_ratio"])
    validation_ratio = float(split_params["validation_ratio"])
    test_ratio       = float(split_params["test_ratio"])

    # ── 1. Chargement ──────────────────────────────────────────────────────────
    print(f"\n[1/4] Chargement : {INPUT_FILE}")
    df = pd.read_csv(INPUT_FILE, dtype=str).fillna("")

    required = {"wolof", "francais"}
    if not required.issubset(df.columns):
        raise ValueError(f"Colonnes attendues : {required} — trouvées : {set(df.columns)}")

    df = df[["wolof", "francais"]].drop_duplicates(subset=["wolof", "francais"])
    print(f"  Paires uniques : {len(df):,}")

    if len(df) < 3:
        raise ValueError(f"Il faut au moins 3 paires pour créer les splits (trouvé : {len(df)}).")

    # ── 2. Doublement bidirectionnel ───────────────────────────────────────────
    print("\n[2/4] Doublement bidirectionnel (WO→FR + FR→WO)")
    df_bidir = double_examples(df, wolof_lang_code, french_lang_code)
    print(f"  Exemples après doublement : {len(df_bidir):,}")

    # Mélange global avant le split
    df_bidir = df_bidir.sample(frac=1, random_state=shuffle_seed).reset_index(drop=True)

    # ── 3. Split ───────────────────────────────────────────────────────────────
    print(f"\n[3/4] Split {train_ratio:.0%} / {validation_ratio:.0%} / {test_ratio:.0%}  (seed={seed})")
    train, validation, test = make_splits(
        df_bidir, train_ratio, validation_ratio, test_ratio, seed
    )
    print(f"  Train      : {len(train):,}")
    print(f"  Validation : {len(validation):,}")
    print(f"  Test       : {len(test):,}")

    # ── 4. Sauvegarde ──────────────────────────────────────────────────────────
    print(f"\n[4/4] Sauvegarde dans '{OUTPUT_DIR}/'")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    train.to_csv(OUTPUT_DIR / "train.csv",           index=False, encoding="utf-8")
    validation.to_csv(OUTPUT_DIR / "validation.csv", index=False, encoding="utf-8")
    test.to_csv(OUTPUT_DIR / "test.csv",             index=False, encoding="utf-8")

    print(f"\n✓ Fichiers générés :")
    print(f"   {OUTPUT_DIR}/train.csv       ({len(train):,} lignes)")
    print(f"   {OUTPUT_DIR}/validation.csv  ({len(validation):,} lignes)")
    print(f"   {OUTPUT_DIR}/test.csv        ({len(test):,} lignes)")


if __name__ == "__main__":
    main()