# 📁 Structure des données — Dataset Wolof-Français

Ce répertoire contient toutes les données du projet, organisées en 3 niveaux de traitement.

---

## 📂 Organisation

```
data/
├── raw/          # Données brutes originales (lecture seule)
├── interim/      # Données nettoyées, en cours de traitement
└── processed/    # Données finales prêtes pour l'entraînement
```

---

## 📋 Schémas des fichiers

### `raw/` — Données brutes
> ⚠️ **Ne jamais modifier ces fichiers.** Toujours travailler sur des copies.

| Fichier | Format | Description |
|---|---|---|
| `batch_2026_01.csv` | CSV | Premier batch de paires Wolof-Français |
| `batch_2026_02.jsonl` | JSONL | Deuxième batch au format JSON Lines |

**Schéma CSV attendu :**
```
id, wolof, francais, source, date_collecte
```

**Schéma JSONL attendu :**
```json
{"id": "...", "wolof": "...", "francais": "...", "source": "...", "date_collecte": "..."}
```

---

### `interim/` — Données intermédiaires

| Fichier | Description |
|---|---|
| `cleaned_v1.csv` | Données nettoyées : doublons supprimés, encodage normalisé, lignes vides retirées |

---

### `processed/` — Données finales

| Fichier | Taille indicative | Rôle |
|---|---|---|
| `train.csv` | ~80% | Entraînement du modèle |
| `validation.csv` | ~10% | Validation pendant l'entraînement |
| `test.csv` | ~10% | Évaluation finale (ne pas utiliser pendant l'entraînement) |

**Split appliqué :** 80 / 10 / 10 (reproductible via `random_state=42`)

---

## 🔄 Pipeline de traitement

```
raw/ ──► [clean_data.py] ──► interim/ ──► [prepare_dataset.py] ──► processed/
```

---

## 📌 Conventions

- Encodage : **UTF-8** pour tous les fichiers
- Séparateur CSV : **virgule** (`,`)
- Colonnes obligatoires : `input`, `target`, `tgt_lang_code`
- Un fichier `processed/` ne doit jamais être modifié manuellement
