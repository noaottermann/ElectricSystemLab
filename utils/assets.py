"""Gestionnaire des ressources graphiques, logos et icônes du projet."""

from __future__ import annotations

import os
from pathlib import Path
from PyQt5.QtGui import QIcon


def get_assets_dir() -> Path:
    """Retourne le chemin absolu du dossier des ressources (assets).

    Returns:
        Path vers le dossier assets.
    """
    project_root = Path(__file__).parent.parent
    return project_root / "assets"


def get_logo_icon() -> QIcon:
    """Charge et retourne l'icône du logo de l'application.

    Returns:
        QIcon chargée ou icône vide si introuvable.
    """
    assets_dir = get_assets_dir()
    logo_formats = ["logo.png", "logo.jpg", "logo.jpeg", "logo.ico", "logo.bmp"]

    for filename in logo_formats:
        logo_path = assets_dir / filename
        if logo_path.exists():
            icon = QIcon(str(logo_path))
            if not icon.isNull():
                return icon

    return QIcon()


def logo_exists() -> bool:
    """Vérifie si un fichier de logo valide existe dans le dossier des ressources.

    Returns:
        True si un fichier de logo est présent, False sinon.
    """
    assets_dir = get_assets_dir()
    logo_formats = ["logo.png", "logo.jpg", "logo.jpeg", "logo.ico", "logo.bmp"]

    for filename in logo_formats:
        if (assets_dir / filename).exists():
            return True
    return False


def get_asset_path(filename: str) -> Path:
    """Construit et retourne le chemin d'accès vers un fichier de ressource spécifique.

    Args:
        filename: Nom du fichier recherché.

    Returns:
        Path vers la ressource dans le dossier assets.
    """
    return get_assets_dir() / filename
