"""
build_from_text.py
------------------
Construit un dataset de traduction Wolof-Français a partir de deux
fichiers texte paralleles (une phrase par ligne, meme ordre).

Entrees (data/unstructured/) :
    wo.txt   -- phrases en wolof
    fr.txt   -- traductions francaises correspondantes

Sortie (data/raw/) :
    batch_text_<timestamp>.jsonl   -- paires pretes pour le pipeline

Usage :
    python scripts/build_from_text.py [--wo WO] [--fr FR] [--out OUT]

Options :
    --wo            Chemin vers le fichier wolof    (defaut : data/unstructured/wo.txt)
    --fr            Chemin vers le fichier francais (defaut : data/unstructured/fr.txt)
    --out           Repertoire de sortie            (defaut : data/raw/)
    --min-wo-chars  Longueur minimale cote wolof    (defaut : 3)
    --min-fr-chars  Longueur minimale cote francais (defaut : 3)
    --no-dedup      Desactiver la deduplication
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# -- Chemins par defaut -------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WO = ROOT / "data" / "unstructured" / "wo.txt"
DEFAULT_FR = ROOT / "data" / "unstructured" / "fr.txt"
DEFAULT_OUT = ROOT / "data" / "raw"


# -- Utilitaires --------------------------------------------------------------

def read_lines(path: Path) -> list[str]:
    """Lit un fichier texte UTF-8 et retourne les lignes (avec vides conservees pour aligner)."""
    with path.open(encoding="utf-8") as f:
        return [line.strip() for line in f]


def clean_line(text: str) -> str:
    """Nettoyage minimal : collapse des espaces multiples / tabs."""
    return " ".join(text.split())


def build_pairs(
    wo_lines: list[str],
    fr_lines: list[str],
    min_wo: int,
    min_fr: int,
    dedup: bool,
) -> list[dict]:
    """
    Aligne ligne-par-ligne les deux fichiers et construit les paires.

    Retourne une liste de dicts {"wolof": ..., "francais": ...}.
    """
    n = min(len(wo_lines), len(fr_lines))
    if len(wo_lines) != len(fr_lines):
        log.warning(
            "Fichiers desynchronises : %d lignes wolof vs %d lignes francais. "
            "Seules les %d premieres paires seront traitees.",
            len(wo_lines),
            len(fr_lines),
            n,
        )

    pairs: list[dict] = []
    seen: set[tuple[str, str]] = set()

    skipped_empty = 0
    skipped_short = 0
    skipped_dup = 0

    for i, (wo_raw, fr_raw) in enumerate(zip(wo_lines, fr_lines), start=1):
        wo = clean_line(wo_raw)
        fr = clean_line(fr_raw)

        # Ignorer les lignes vides
        if not wo or not fr:
            skipped_empty += 1
            continue

        # Filtrer les phrases trop courtes
        if len(wo) < min_wo or len(fr) < min_fr:
            skipped_short += 1
            log.debug("Ligne %d trop courte (wo=%d, fr=%d) -- ignoree.", i, len(wo), len(fr))
            continue

        # Deduplication exacte
        key = (wo, fr)
        if dedup and key in seen:
            skipped_dup += 1
            log.debug("Ligne %d dupliquee -- ignoree.", i)
            continue

        seen.add(key)
        pairs.append({"wolof": wo, "francais": fr})

    log.info("Lignes lues         : %d", n)
    log.info("Lignes vides        : %d", skipped_empty)
    log.info("Lignes trop courtes : %d", skipped_short)
    log.info("Doublons exacts     : %d", skipped_dup)
    log.info("Paires retenues     : %d", len(pairs))

    return pairs


def write_jsonl(pairs: list[dict], out_dir: Path, wo_path: Path, fr_path: Path) -> Path:
    """Ecrit les paires dans un fichier JSONL horodate dans out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"batch_text_{timestamp}.jsonl"

    with out_path.open("w", encoding="utf-8") as f:
        for pair in pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    # Fichier de provenance (tracabilite DVC)
    meta = {
        "source_wo": str(wo_path),
        "source_fr": str(fr_path),
        "created_at": datetime.now().isoformat(),
        "n_pairs": len(pairs),
    }
    meta_path = out_dir / f"batch_text_{timestamp}.meta.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    return out_path


# -- CLI ----------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Construit un dataset JSONL a partir de deux fichiers texte paralleles.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--wo", type=Path, default=DEFAULT_WO, help="Fichier texte wolof")
    parser.add_argument("--fr", type=Path, default=DEFAULT_FR, help="Fichier texte francais")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Repertoire de sortie")
    parser.add_argument(
        "--min-wo-chars", type=int, default=3, metavar="N",
        help="Longueur minimale (caracteres) cote wolof",
    )
    parser.add_argument(
        "--min-fr-chars", type=int, default=3, metavar="N",
        help="Longueur minimale (caracteres) cote francais",
    )
    parser.add_argument(
        "--no-dedup", action="store_true",
        help="Desactiver la deduplication exacte",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Verification des fichiers d'entree
    for path, label in [(args.wo, "wolof"), (args.fr, "francais")]:
        if not path.exists():
            log.error("Fichier %s introuvable : %s", label, path)
            sys.exit(1)

    log.info("Lecture des fichiers...")
    log.info("  Wolof    : %s", args.wo)
    log.info("  Francais : %s", args.fr)

    wo_lines = read_lines(args.wo)
    fr_lines = read_lines(args.fr)

    pairs = build_pairs(
        wo_lines=wo_lines,
        fr_lines=fr_lines,
        min_wo=args.min_wo_chars,
        min_fr=args.min_fr_chars,
        dedup=not args.no_dedup,
    )

    if not pairs:
        log.error("Aucune paire valide trouvee. Verifiez vos fichiers d'entree.")
        sys.exit(1)

    out_path = write_jsonl(pairs, args.out, args.wo, args.fr)
    log.info("Fichier ecrit : %s", out_path)
    log.info("Lancez ensuite :")
    log.info("  python scripts/clean_data.py")
    log.info("  python scripts/prepare_dataset.py")


if __name__ == "__main__":
    main()
