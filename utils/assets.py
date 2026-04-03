"""Gestionnaire des ressources et assets du logiciel"""

import os
import sys
from pathlib import Path
from PyQt5.QtGui import QIcon


def get_assets_dir() -> Path:
    """Retourne le chemin du dossier assets."""
    project_root = Path(__file__).parent.parent
    return project_root / "assets"


def get_logo_icon() -> QIcon:
    """
    Charge et retourne l'icône du logo.
    
    Cherche le logo dans l'ordre:
    1. logo.png
    2. logo.jpg
    3. logo.ico
    
    Returns:
        QIcon: L'icône du logo si elle existe, sinon un icône vide.
    """
    assets_dir = get_assets_dir()
    
    # Liste des formats acceptés par ordre de préférence
    logo_formats = ["logo.png", "logo.jpg", "logo.jpeg", "logo.ico", "logo.bmp"]
    
    for filename in logo_formats:
        logo_path = assets_dir / filename
        if logo_path.exists():
            icon = QIcon(str(logo_path))
            if not icon.isNull():
                return icon
    
    return QIcon()


def logo_exists() -> bool:
    """
    Vérifie si un fichier de logo existe dans le dossier assets.
    
    Returns:
        bool: True si un logo existe, False sinon
    """
    assets_dir = get_assets_dir()
    logo_formats = ["logo.png", "logo.jpg", "logo.jpeg", "logo.ico", "logo.bmp"]
    
    for filename in logo_formats:
        if (assets_dir / filename).exists():
            return True
    return False


def get_asset_path(filename: str) -> Path:
    """
    Retourne le chemin complet d'un asset.
    
    Args:
        filename: Le nom du fichier dans le dossier assets
        
    Returns:
        Path: Le chemin complet vers l'asset
    """
    return get_assets_dir() / filename
