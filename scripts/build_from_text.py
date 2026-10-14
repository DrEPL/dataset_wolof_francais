"""
build_from_text.py
------------------
Construit un dataset de traduction Wolof-Francais a partir de fichiers
texte paralleles (une phrase par ligne, meme ordre).

Deux modes de fonctionnement :

  Mode 1 - Scan automatique (defaut) :
    Parcourt tous les sous-dossiers de data/unstructured/ et traite
    chaque paire (wo.txt, fr.txt) trouvee. Un fichier JSONL par source.

  Mode 2 - Fichiers explicites :
    python scripts/build_from_text.py --wo chemin/wo.txt --fr chemin/fr.txt

Options :
    --src-dir       Repertoire a scanner     (defaut : data/unstructured/)
    --out           Repertoire de sortie     (defaut : data/raw/)
    --wo            Fichier wolof explicite  (desactive le scan)
    --fr            Fichier francais explicite (desactive le scan)
    --min-wo-chars  Longueur minimale cote wolof    (defaut : 3)
    --min-fr-chars  Longueur minimale cote francais (defaut : 3)
    --no-dedup      Desactiver la deduplication exacte
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
DEFAULT_SRC_DIR = ROOT / "data" / "unstructured"
DEFAULT_OUT = ROOT / "data" / "raw"


# -- Utilitaires --------------------------------------------------------------

def read_lines(path: Path) -> list[str]:
    """Lit un fichier texte UTF-8 et retourne les lignes (vides conservees pour aligner)."""
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
    seen_global: set[tuple[str, str]] | None = None,
) -> list[dict]:
    """
    Aligne ligne-par-ligne wo_lines et fr_lines et retourne les paires.

    Args:
        seen_global: si fourni, les paires deja rencontrees DANS D'AUTRES
                     sources sont aussi exclues (deduplication croisee).

    Retourne une liste de dicts {"wolof": ..., "francais": ..., "source": ...}.
    """
    n = min(len(wo_lines), len(fr_lines))
    if len(wo_lines) != len(fr_lines):
        log.warning(
            "Fichiers desynchronises : %d lignes wolof vs %d lignes francais. "
            "Seules les %d premieres paires seront traitees.",
            len(wo_lines), len(fr_lines), n,
        )

    pairs: list[dict] = []
    seen_local: set[tuple[str, str]] = set()

    skipped_empty = 0
    skipped_short = 0
    skipped_dup = 0

    for i, (wo_raw, fr_raw) in enumerate(zip(wo_lines, fr_lines), start=1):
        wo = clean_line(wo_raw)
        fr = clean_line(fr_raw)

        if not wo or not fr:
            skipped_empty += 1
            continue

        if len(wo) < min_wo or len(fr) < min_fr:
            skipped_short += 1
            continue

        key = (wo, fr)
        if dedup:
            if key in seen_local:
                skipped_dup += 1
                continue
            if seen_global is not None and key in seen_global:
                skipped_dup += 1
                continue

        seen_local.add(key)
        if seen_global is not None:
            seen_global.add(key)
        pairs.append({"wolof": wo, "francais": fr})

    log.info("  Lignes lues         : %d", n)
    log.info("  Lignes vides        : %d", skipped_empty)
    log.info("  Lignes trop courtes : %d", skipped_short)
    log.info("  Doublons            : %d", skipped_dup)
    log.info("  Paires retenues     : %d", len(pairs))

    return pairs


def write_jsonl(
    pairs: list[dict],
    out_dir: Path,
    source_name: str,
    wo_path: Path,
    fr_path: Path,
) -> Path:
    """Ecrit les paires dans data/raw/batch_<source>_<timestamp>.jsonl."""
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = source_name.replace(" ", "_").replace("/", "-")
    out_path = out_dir / f"batch_{safe_name}_{timestamp}.jsonl"

    with out_path.open("w", encoding="utf-8") as f:
        for pair in pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    meta = {
        "source": source_name,
        "source_wo": str(wo_path),
        "source_fr": str(fr_path),
        "created_at": datetime.now().isoformat(),
        "n_pairs": len(pairs),
    }
    meta_path = out_dir / f"batch_{safe_name}_{timestamp}.meta.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    return out_path


def find_pairs(src_dir: Path) -> list[tuple[str, Path, Path]]:
    """
    Parcourt src_dir recursivement et retourne toutes les paires (wo.txt, fr.txt).
    Retourne une liste de (nom_source, wo_path, fr_path).
    """
    pairs = []

    # Chercher dans les sous-dossiers directs
    for subdir in sorted(src_dir.iterdir()):
        if not subdir.is_dir():
            continue
        wo = subdir / "wo.txt"
        fr = subdir / "fr.txt"
        if wo.exists() and fr.exists():
            pairs.append((subdir.name, wo, fr))
        else:
            missing = []
            if not wo.exists():
                missing.append("wo.txt")
            if not fr.exists():
                missing.append("fr.txt")
            if missing:
                log.warning("Dossier %s : fichier(s) manquant(s) : %s", subdir.name, ", ".join(missing))

    # Verifier aussi a la racine de src_dir
    wo_root = src_dir / "wo.txt"
    fr_root = src_dir / "fr.txt"
    if wo_root.exists() and fr_root.exists():
        pairs.append(("root", wo_root, fr_root))

    return pairs


# -- CLI ----------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Construit des fichiers JSONL a partir de paires texte paralleles Wolof/Francais.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--src-dir", type=Path, default=DEFAULT_SRC_DIR,
        help="Repertoire a scanner (mode automatique)",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Repertoire de sortie")
    parser.add_argument("--wo", type=Path, default=None, help="Fichier wolof explicite (desactive le scan)")
    parser.add_argument("--fr", type=Path, default=None, help="Fichier francais explicite (desactive le scan)")
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
        help="Desactiver la deduplication exacte (y compris croisee entre sources)",
    )
    return parser.parse_args()


def process_pair(
    source_name: str,
    wo_path: Path,
    fr_path: Path,
    out_dir: Path,
    min_wo: int,
    min_fr: int,
    dedup: bool,
    seen_global: set[tuple[str, str]] | None,
) -> int:
    """Traite une paire (wo, fr) et ecrit le JSONL. Retourne le nombre de paires."""
    log.info("")
    log.info("=== Source : %s ===", source_name)
    log.info("  Wolof    : %s", wo_path)
    log.info("  Francais : %s", fr_path)

    wo_lines = read_lines(wo_path)
    fr_lines = read_lines(fr_path)

    pairs = build_pairs(
        wo_lines=wo_lines,
        fr_lines=fr_lines,
        min_wo=min_wo,
        min_fr=min_fr,
        dedup=dedup,
        seen_global=seen_global,
    )

    if not pairs:
        log.warning("  Aucune paire valide pour '%s' -- fichier non genere.", source_name)
        return 0

    out_path = write_jsonl(pairs, out_dir, source_name, wo_path, fr_path)
    log.info("  Fichier ecrit : %s", out_path)
    return len(pairs)


def main() -> None:
    args = parse_args()

    min_wo = args.min_wo_chars
    min_fr = args.min_fr_chars
    dedup = not args.no_dedup
    seen_global: set[tuple[str, str]] | None = set() if dedup else None

    # -- Mode explicite (--wo et --fr fournis) --------------------------------
    if args.wo is not None or args.fr is not None:
        if args.wo is None or args.fr is None:
            log.error("--wo et --fr doivent etre fournis ensemble.")
            sys.exit(1)
        for path, label in [(args.wo, "wolof"), (args.fr, "francais")]:
            if not path.exists():
                log.error("Fichier %s introuvable : %s", label, path)
                sys.exit(1)

        total = process_pair(
            source_name=args.wo.parent.name or "explicit",
            wo_path=args.wo,
            fr_path=args.fr,
            out_dir=args.out,
            min_wo=min_wo,
            min_fr=min_fr,
            dedup=dedup,
            seen_global=seen_global,
        )
        log.info("")
        log.info("Total : %d paires", total)

    # -- Mode scan automatique ------------------------------------------------
    else:
        if not args.src_dir.exists():
            log.error("Repertoire source introuvable : %s", args.src_dir)
            sys.exit(1)

        found = find_pairs(args.src_dir)
        if not found:
            log.error("Aucune paire (wo.txt + fr.txt) trouvee dans %s", args.src_dir)
            sys.exit(1)

        log.info("Sources trouvees : %d", len(found))

        total_all = 0
        results = []
        for source_name, wo_path, fr_path in found:
            n = process_pair(
                source_name=source_name,
                wo_path=wo_path,
                fr_path=fr_path,
                out_dir=args.out,
                min_wo=min_wo,
                min_fr=min_fr,
                dedup=dedup,
                seen_global=seen_global,
            )
            total_all += n
            results.append((source_name, n))

        log.info("")
        log.info("=" * 50)
        log.info("RECAPITULATIF")
        log.info("=" * 50)
        for name, n in results:
            log.info("  %-20s : %d paires", name, n)
        log.info("  %-20s : %d paires", "TOTAL", total_all)
        log.info("")
        log.info("Lancez ensuite :")
        log.info("  python scripts/clean_data.py")
        log.info("  python scripts/prepare_dataset.py")


if __name__ == "__main__":
    main()
