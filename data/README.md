# 📁 Architecture et Documentation des Données — Dataset Wolof-Français

Ce répertoire regroupe les données du projet de traduction automatique bidirectionnelle **Wolof ↔ Français**, structurées en 3 niveaux de maturité et versionnées avec **DVC**.

---

## 📂 Organisation du Répertoire

```
data/
├── raw/                      # Données brutes sources (gérées par DVC, lecture seule)
│   ├── batch_2026_01.jsonl   # Dataset collecté (schéma input/output)
│   └── ...                   # Nouveaux batches (.csv ou .jsonl)
├── interim/                  # Données nettoyées et standardisées (non versionnées git)
│   └── cleaned.csv           # Paires uniques dédupliquées (wolof, francais)
├── processed/                # Données finales prêtes pour l'entraînement (gérées par DVC)
│   ├── train.csv             # Split d'entraînement (~80%)
│   ├── validation.csv        # Split d'évaluation périodique (~10%)
│   └── test.csv              # Split de test final non vu (~10%)
└── README.md                 # Documentation technique et schémas
```

---

## 📋 Schémas Détaillés par Étape

### 1. `data/raw/` — Données brutes (Source)
> ⚠️ **Immuables :** Ces fichiers ne doivent jamais être modifiés ou écrasés manuellement. Ils sont indexés et suivis via `data/raw.dvc`.

Le pipeline supporte deux formats d'entrée avec détection automatique des alias de colonnes :

* **Format JSONL (`.jsonl`) :**
  ```json
  {"input": "Omar a lekk ceeb bi", "output": "C'est Omar qui a mangé le riz."}
  ```
  *(Note : les enregistrements dont l'output est structuré sous forme de dictionnaire — définitions, synonymes — sont automatiquement ignorés par le chargeur).*

* **Format CSV (`.csv`) :**
  ```csv
  wolof,francais
  "Omar a lekk ceeb bi","C'est Omar qui a mangé le riz."
  ```

* **Alias de colonnes pris en charge :**
  - **Wolof** : `wolof`, `wo`, `input`, `source`
  - **Français** : `francais`, `français`, `french`, `fr`, `target`, `output`

---

### 2. `data/interim/` — Données nettoyées

* **Fichier produit :** `data/interim/cleaned.csv`
* **Schéma :**
  ```csv
  wolof,francais
  ```
* **Opérations appliquées (`scripts/clean_data.py`) :**
  1. **Normalisation** : renommage automatique des alias vers `wolof` et `francais`.
  2. **Nettoyage textuel** : suppression des espaces superflus (`strip`) et conversion systématique en chaînes de caractères.
  3. **Filtrage de longueur** : conservation des phrases respectant les seuils minimums (`min_wolof_chars`, `min_french_chars`).
  4. **Déduplication stricte** : suppression des doublons exacts sur le couple `(wolof, francais)`.

---

### 3. `data/processed/` — Données finales prêtes pour le modèle

* **Fichiers produits :**
  - `train.csv` (80%)
  - `validation.csv` (10%)
  - `test.csv` (10%)
* **Schéma standardisé (compatible modèles Seq2Seq / NLLB / mBART) :**
  ```csv
  source,target,tgt_lang_code
  ```
* **Doublement bidirectionnel (`WO ↔ FR`) :**
  Pour chaque paire nettoyée `(wolof, francais)`, deux exemples sont systématiquement créés :
  | Direction | `source` | `target` | `tgt_lang_code` |
  |---|---|---|---|
  | **Wolof → Français** | Texte Wolof | Traduction Française | `fra_Latn` |
  | **Français → Wolof** | Texte Français | Traduction Wolof | `wol_Latn` |

* **Mélange & Split :**
  Mélange aléatoire reproductible (`shuffle_seed`), puis découpage en 3 ensembles étanches avec conservation d'au moins un exemple par split.

---

## 📊 Statistiques Actuelles du Dataset

| Niveau | Volume | Remarques |
|---|---|---|
| **Raw** | 5 784 lignes | Données brutes issues de `batch_2026_01.jsonl` |
| **Interim (`cleaned.csv`)** | 5 677 paires | 107 doublons supprimés |
| **Processed (Total)** | **11 354 exemples** | Obtenu après doublement bidirectionnel (×2) |
| ├── `train.csv` | 9 083 exemples | 80% des exemples |
| ├── `validation.csv` | 1 135 exemples | 10% des exemples |
| └── `test.csv` | 1 136 exemples | 10% des exemples |

---

## ⚙️ Paramètres (`params.yaml`)

Tous les hyperparamètres du pipeline sont centralisés dans [`params.yaml`](file:///d:/Projets_IA/dataset_wolof_francais/params.yaml) :

```yaml
# Nettoyage
clean_data:
  remove_duplicates: true
  min_wolof_chars: 2
  min_french_chars: 2

# Doublement bidirectionnel
double_examples:
  wolof_lang_code: "wol_Latn"
  french_lang_code: "fra_Latn"
  shuffle_seed: 42

# Répartition des splits
prepare_dataset:
  seed: 42
  train_ratio: 0.80
  validation_ratio: 0.10
  test_ratio: 0.10
```

---

## 🔄 Pipeline & Reproductibilité (DVC)

Le pipeline de données est entièrement orchestré via **DVC** ([`dvc.yaml`](file:///d:/Projets_IA/dataset_wolof_francais/dvc.yaml)) :

```
             ┌─────────────────────────┐
             │       data/raw/         │
             └────────────┬────────────┘
                          │ (dvc add data/raw)
                          ▼
             ┌─────────────────────────┐
             │  scripts/clean_data.py  │  ◄── params: clean_data
             └────────────┬────────────┘
                          │
                          ▼
             ┌─────────────────────────┐
             │ data/interim/cleaned.csv│
             └────────────┬────────────┘
                          │
                          ▼
             ┌─────────────────────────┐
             │scripts/prepare_dataset.py│ ◄── params: double_examples, prepare_dataset
             └────────────┬────────────┘
                          │
                          ▼
       ┌──────────────────┼──────────────────┐
       ▼                  ▼                  ▼
   train.csv        validation.csv        test.csv
```

### Commandes Utiles

* **Exécuter ou mettre à jour tout le pipeline :**
  ```bash
  dvc repro
  ```
* **Vérifier l'état de synchronisation :**
  ```bash
  dvc status
  ```
* **Exécution manuelle (script par script) :**
  ```bash
  python scripts/clean_data.py
  python scripts/prepare_dataset.py
  ```

---

## 📌 Conventions Techniques

- **Encodage :** `UTF-8` sans BOM obligatoire pour tous les fichiers.
- **Séparateur CSV :** Virgule (`,`).
- **Codes de langues cibles :** Codes FLORES-200 / NLLB-200 (`wol_Latn` pour le Wolof en alphabet latin, `fra_Latn` pour le Français).
- **Règle d'or :** Aucun fichier dans `data/interim/` ou `data/processed/` ne doit être édité à la main ; toute modification passe par l'ajustement de `params.yaml` ou des scripts, suivi de `dvc repro`.
