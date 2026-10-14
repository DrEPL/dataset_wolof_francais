# 🇸🇳 Dataset de Traduction Automatique Wolof ↔ Français

Pipeline de données MLOps pour la préparation d'un corpus de traduction automatique bidirectionnelle **Wolof ↔ Français**, orchestré et versionné avec **DVC** et **Git**.

---

## ⚡ Quickstart : Lancer le Système en 2 Minutes

### 1. Cloner et préparer l'environnement
```bash
# Cloner le dépôt
git clone <url-du-depot>
cd dataset_wolof_francais

# Créer l'environnement virtuel
python -m venv venv

# Activer l'environnement
# Sous Windows (PowerShell) :
.\venv\Scripts\Activate.ps1
# Sous Linux / macOS :
# source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt
```

### 2. Exécuter le pipeline DVC complet
```bash
dvc repro
```
> DVC vérifie automatiquement les dépendances et génère les fichiers finaux dans `data/processed/` (`train.csv`, `validation.csv`, `test.csv`).

---

## 🏗️ Architecture du Projet

```
dataset_wolof_francais/
├── .dvc/                     # Configuration interne de DVC
├── data/
│   ├── raw/                  # Données brutes (indexées via raw.dvc)
│   ├── interim/              # Données nettoyées (cleaned.csv)
│   ├── processed/            # Données prêtes pour l'entraînement (train/val/test)
│   └── README.md             # Documentation approfondie des schémas et conventions
├── scripts/
│   ├── clean_data.py         # Ingestion, normalisation et nettoyage
│   └── prepare_dataset.py    # Doublement bidirectionnel (WO↔FR) et split
├── params.yaml               # Hyperparamètres centralisés
├── dvc.yaml                  # Définition des étapes et dépendances du pipeline
├── dvc.lock                  # Empreintes cryptographiques de l'état reproductible
└── README.md                 # Vue d'ensemble du projet
```

---

## 🔄 Pipeline de Données

```
data/raw/ ──► [clean_data.py] ──► data/interim/cleaned.csv ──► [prepare_dataset.py] ──► data/processed/
                                                                                         ├── train.csv
                                                                                         ├── validation.csv
                                                                                         └── test.csv
```

1. **Nettoyage (`clean`)** : chargement des JSONL / CSV, normalisation des colonnes (`wolof`, `francais`), filtrage par longueur de caractères et suppression des doublons.
2. **Doublement bidirectionnel & Split (`prepare`)** :
   - Génération automatique des paires **Wolof → Français** (`tgt_lang_code: fra_Latn`) et **Français → Wolof** (`tgt_lang_code: wol_Latn`).
   - Découpage en 3 ensembles étanches (`train`, `validation`, `test`) selon les ratios définis.

---

## 🛠️ Commandes DVC Essentielles

| Action | Commande | Description |
|---|---|---|
| **Exécuter le pipeline** | `dvc repro` | Ne recalcule que les étapes dont le code, les données ou les paramètres ont changé. |
| **Forcer l'exécution** | `dvc repro -f` | Force la ré-exécution complète de toutes les étapes. |
| **Vérifier l'état** | `dvc status` | Indique si le pipeline ou les données ont divergé. |
| **Visualiser le graphe** | `dvc dag` | Affiche les étapes et dépendances dans le terminal. |
| **Ajouter des données brutes** | `dvc add data/raw` | Met à jour le suivi DVC après l'ajout de nouveaux fichiers bruts. |
| **Sauvegarde distante** | `dvc push` | Envoie les données vers le remote (DagsHub, S3, etc.). |
| **Récupérer les données** | `dvc pull` | Télécharge les données versionnées sur une nouvelle machine. |

Pour plus de détails techniques, consultez [`data/README.md`](file:///d:/Projets_IA/dataset_wolof_francais/data/README.md).
