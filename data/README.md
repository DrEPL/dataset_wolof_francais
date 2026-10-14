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


---

## 🚀 Guide d'Exécution et Commandes DVC

### 1. Prérequis & Installation de l'environnement

```bash
# 1. Cloner le dépôt et se placer dans le projet
cd dataset_wolof_francais

# 2. Créer et activer l'environnement virtuel Python
python -m venv venv

# Windows (PowerShell) :
.\venv\Scripts\Activate.ps1
# Linux / macOS :
# source venv/bin/activate

# 3. Installer les dépendances nécessaires
pip install -r requirements.txt
```

---

### 2. Comment Lancer le Système (Scénarios Types)

#### Scénario A : Exécution rapide du pipeline (Recommandé)
DVC compare les empreintes numériques (`md5`) de votre code, de vos données brutes et de vos paramètres. Il n'exécute que ce qui a changé :

```bash
# Lancer ou mettre à jour tout le pipeline
dvc repro
```

*Résultat attendu :*
1. Exécution de l'étape `clean` (`scripts/clean_data.py`) → produit `data/interim/cleaned.csv`
2. Exécution de l'étape `prepare` (`scripts/prepare_dataset.py`) → produit `data/processed/train.csv`, `validation.csv`, `test.csv`
3. Mise à jour automatique de `dvc.lock`

#### Scénario B : Modification des hyperparamètres
Si vous modifiez un ratio de split, une longueur minimale ou une seed dans `params.yaml` :

```bash
# 1. Modifier params.yaml (ex. train_ratio: 0.85, test_ratio: 0.05)
# 2. Relancer le pipeline : DVC sait que seule l'étape 'prepare' est impactée !
dvc repro

# 3. Sauvegarder l'état dans git
git add params.yaml dvc.lock
git commit -m "tune: adjust split ratios to 85/10/5"
```

#### Scénario C : Ajout de nouvelles données brutes
Lorsque vous déposez un nouveau fichier dans `data/raw/` (ex. `batch_2026_02.jsonl` ou un nouveau CSV) :

```bash
# 1. Déposer le fichier dans data/raw/
# 2. Enregistrer le nouveau hash du dossier data/raw dans DVC
dvc add data/raw

# 3. Relancer le pipeline (toutes les étapes se recalculeront automatiquement)
dvc repro

# 4. Versionner les pointeurs DVC et le lockfile dans git
git add data/raw.dvc data/.gitignore dvc.lock
git commit -m "data: add batch_2026_02 and re-run pipeline"
```

---

### 3. Boîte à Outils des Commandes DVC

| Commande | Rôle |
|---|---|
| `dvc repro` | Exécute intelligemment les étapes dont le code, les données ou les paramètres ont changé. |
| `dvc repro -f` | Force l'exécution de toutes les étapes du pipeline, même sans changement détecté. |
| `dvc repro clean` | Exécute uniquement l'étape de nettoyage `clean`. |
| `dvc repro prepare` | Exécute uniquement l'étape de préparation et split `prepare`. |
| `dvc status` | Affiche l'état des dépendances et indique si le pipeline est à jour ou a divergé. |
| `dvc dag` | Affiche l'arbre de dépendances (DAG) du pipeline directement dans le terminal. |
| `dvc add data/raw` | Indexe le dossier des données brutes pour le suivi par DVC sans charger git. |
| `dvc push` | Envoie les fichiers de données volumineux vers le stockage distant (S3, DagsHub, etc.). |
| `dvc pull` | Récupère les données trackées par DVC sur une nouvelle machine ou un nouveau clone. |

---

### 4. Exécution Alternative (Sans passer par DVC)

Pour débugger ou exécuter manuellement chaque script en Python pur :

```bash
# Étape 1 : Nettoyage -> data/interim/cleaned.csv
python scripts/clean_data.py

# Étape 2 : Doublement bidirectionnel & Split -> data/processed/*.csv
python scripts/prepare_dataset.py
```

---

## 📌 Conventions Techniques

- **Encodage :** `UTF-8` sans BOM obligatoire pour tous les fichiers.
- **Séparateur CSV :** Virgule (`,`).
- **Codes de langues cibles :** Codes FLORES-200 / NLLB-200 (`wol_Latn` pour le Wolof en alphabet latin, `fra_Latn` pour le Français).
- **Règle d'or :** Aucun fichier dans `data/interim/` ou `data/processed/` ne doit être édité à la main ; toute modification passe par l'ajustement de `params.yaml` ou des scripts, suivi de `dvc repro`.

