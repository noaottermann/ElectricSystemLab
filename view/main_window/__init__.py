"""
Package pour les composants de la fenêtre principale.
"""

from .actions import ActionManager
from .menus import MenuBuilder
from .toolbar import ToolbarBuilder

__all__ = [
    "ActionManager",
    "MenuBuilder",
    "ToolbarBuilder",
]
