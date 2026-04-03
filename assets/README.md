# Dossier Assets

Ce dossier contient les ressources visuelles du logiciel Nodal.

## Logo

Placez votre fichier `logo.png` (format PNG) dans ce dossier pour personnaliser le logo du logiciel.

- **Nom du fichier**: `logo.png` (obligatoire)
- **Format**: PNG (recommandé)
- **Dimensions recommandées**: 256x256 pixels ou plus pour une meilleure qualité
- **Autres formats acceptés**: JPG, BMP, etc. (tant que PyQt5 les supporte)

Le logo sera automatiquement chargé au démarrage de l'application et apparaîtra dans:
- La barre de titre de la fenêtre principale
- La barre des tâches (Windows, Linux)
- Les fenêtres de dialogue système

## Structure

```
assets/
├── logo.png          # Logo principal de l'application
└── README.md         # Ce fichier
```

## Utilisation

Le module `utils/assets.py` fournit des fonctions pour accéder aux ressources :

```python
from utils.assets import get_logo_icon, get_asset_path

# Charger le logo comme QIcon
icon = get_logo_icon()

# Obtenir le chemin d'un asset
path = get_asset_path("logo.png")
```
