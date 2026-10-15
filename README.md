# Dataset de Traduction Automatique Wolof ↔ Français

Pipeline de données MLOps pour la préparation d'un corpus de traduction automatique bidirectionnelle **Wolof ↔ Français**, orchestré et versionné avec **DVC** et **Git**.

---

## 🌐 Dépôts Distants & Synchronisation Multi-Remotes

Le projet est hébergé en miroir sur deux plateformes complémentaires :

| Remote Git | Plateforme | URL du Dépôt |
|---|---|---|
| **`origin`** | **GitHub** | `https://github.com/DrEPL/dataset_wolof_francais.git` |
| **`dagshub`** | **DagsHub** | `https://dagshub.com/DrEPL/ml-translation-wo-fr.git` |

### 🚀 Push simultané vers GitHub & DagsHub (`all-remotes`)

Le groupe `all-remotes` est configuré pour pousser vers les deux dépôts en une seule commande :

```bash
# Configuration du groupe multi-remotes (déjà configuré) :
# git config remotes.all-remotes "origin dagshub"

# Pousser simultanément sur GitHub et DagsHub
git push all-remotes main
```

### 📦 Synchronisation du Stockage des Données (DVC)

Les fichiers de données volumineux (`data/raw/`, `data/processed/`) sont versionnés et hébergés sur le stockage distant **DagsHub Storage** :

```bash
# Envoyer les données vers le stockage distant DagsHub
dvc push

# Récupérer les données sur une nouvelle machine
dvc pull
```

---

## ⚡ Quickstart : Lancer le Système en 2 Minutes

### 1. Cloner et préparer l'environnement
```bash
# Cloner depuis GitHub ou DagsHub
git clone https://github.com/DrEPL/dataset_wolof_francais.git
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

### 2. Récupérer les données ou ré-exécuter le pipeline
```bash
# Option A : Récupérer les données déjà calculées depuis DagsHub
dvc pull

# Option B : Ré-exécuter le pipeline DVC complet en local
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
| **Sauvegarde distante** | `dvc push` | Envoie les données vers le remote (DagsHub). |
| **Récupérer les données** | `dvc pull` | Télécharge les données versionnées sur une nouvelle machine. |
| **Pousser les données sur tous les dépot distants** | `git push all-remotes main` | Pousse les données versionnées sur les repo distants. |

Pour plus de détails techniques sur les données, consultez [`data/README.md`](file:///d:/Projets_IA/dataset_wolof_francais/data/README.md).
