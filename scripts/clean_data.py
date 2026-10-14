"""
clean_data.py
-------------
Charge les données brutes (raw/), les nettoie selon params.yaml,
et écrit data/interim/cleaned.csv.

Colonnes de sortie : wolof | francais

Usage :
    python scripts/clean_data.py
"""

import json
from pathlib import Path

import pandas as pd
import yaml

# ── Chemins ────────────────────────────────────────────────────────────────────

RAW_DIR = Path("data/raw")
OUTPUT_FILE = Path("data/interim/cleaned.csv")
PARAMS_FILE = Path("params.yaml")

# ── Schéma de normalisation des colonnes ───────────────────────────────────────

COLUMN_ALIASES: dict[str, set[str]] = {
    "wolof":   {"wolof", "wo", "input", "source"},
    "francais": {"francais", "français", "french", "fr", "target", "output"},
}


# ── Utilitaires ────────────────────────────────────────────────────────────────

def load_params() -> dict:
    """Charge la section clean_data depuis params.yaml."""
    with PARAMS_FILE.open("r", encoding="utf-8") as fh:
        all_params = yaml.safe_load(fh)
    return all_params.get("clean_data", {})


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Renomme les colonnes reconnues vers le schéma cible (wolof, francais)."""
    rename: dict[str, str] = {}
    already_mapped: set[str] = set()

    for col in df.columns:
        key = str(col).strip().lower()
        for target, aliases in COLUMN_ALIASES.items():
            if key in aliases and target not in already_mapped:
                rename[col] = target
                already_mapped.add(target)
                break

    return df.rename(columns=rename)


# ── Chargeurs ──────────────────────────────────────────────────────────────────

def load_jsonl(path: Path) -> pd.DataFrame:
    """
    Charge un fichier JSONL.
    Schéma attendu : {"input": "<wolof>", "output": "<français>"}
    Les lignes dont output n'est pas une str (ex. dict) sont ignorées.
    """
    rows: list[dict] = []

    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"  [WARN] JSON invalide {path.name}:{line_no} — {exc}")
                continue

            wolof = record.get("input", record.get("wolof"))
            francais = record.get("output", record.get("francais", record.get("french")))

            # Ignorer les sorties structurées (définitions, synonymes, …)
            if not isinstance(wolof, str) or not isinstance(francais, str):
                continue

            rows.append({"wolof": wolof, "francais": francais})

    return pd.DataFrame(rows, columns=["wolof", "francais"])


def load_csv(path: Path) -> pd.DataFrame:
    """Charge un CSV et normalise les noms de colonnes."""
    df = pd.read_csv(path, dtype=str)
    df = normalize_columns(df)

    missing = {"wolof", "francais"} - set(df.columns)
    if missing:
        raise ValueError(
            f"{path.name} : colonnes introuvables {missing}. "
            f"Disponibles : {list(df.columns)}"
        )

    return df[["wolof", "francais"]]


def load_all_raw(raw_dir: Path) -> pd.DataFrame:
    """Charge tous les .csv et .jsonl présents dans raw_dir."""
    files = sorted(
        p for p in raw_dir.iterdir()
        if p.is_file() and p.suffix.lower() in {".csv", ".jsonl"}
    )

    if not files:
        raise FileNotFoundError(f"Aucun CSV ou JSONL trouvé dans {raw_dir}")

    frames: list[pd.DataFrame] = []
    for path in files:
        print(f"  Lecture : {path.name}")
        frame = load_csv(path) if path.suffix.lower() == ".csv" else load_jsonl(path)
        frames.append(frame)

    df = pd.concat(frames, ignore_index=True)
    print(f"  Lignes chargées (brut) : {len(df):,}")
    return df


# ── Nettoyage ──────────────────────────────────────────────────────────────────

def clean(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """
    Applique les étapes de nettoyage paramétrées :
      1. Strip + normalisation des valeurs
      2. Filtrage par longueur minimale
      3. Suppression des doublons (optionnelle)
    """
    min_wo = int(params.get("min_wolof_chars", 2))
    min_fr = int(params.get("min_french_chars", 2))
    remove_dup = bool(params.get("remove_duplicates", True))

    # 1. Strip et forçage en str
    for col in ("wolof", "francais"):
        df[col] = df[col].fillna("").astype(str).str.strip()

    # 2. Filtrage longueur minimale
    before = len(df)
    df = df[
        (df["wolof"].str.len() >= min_wo)
        & (df["francais"].str.len() >= min_fr)
    ]
    print(f"  Après filtre longueur min ({min_wo}/{min_fr} chars) : {len(df):,} lignes (retiré {before - len(df):,})")

    # 3. Déduplication
    if remove_dup:
        before = len(df)
        df = df.drop_duplicates(subset=["wolof", "francais"])
        print(f"  Doublons exacts supprimés : {before - len(df):,}")

    df = df.reset_index(drop=True)
    return df


# ── Point d'entrée ─────────────────────────────────────────────────────────────

def main() -> None:
    print("=== clean_data ===")
    params = load_params()

    print(f"\n[1/3] Chargement des fichiers bruts depuis '{RAW_DIR}/'")
    df = load_all_raw(RAW_DIR)

    print("\n[2/3] Nettoyage")
    df = clean(df, params)

    print(f"\n[3/3] Sauvegarde -> {OUTPUT_FILE}")
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")

    print(f"\nOK Dataset nettoye : {len(df):,} paires -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()