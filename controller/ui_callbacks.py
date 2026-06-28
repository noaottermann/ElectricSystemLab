"""
Interface de rappels UI pour découpler les contrôleurs de la vue.

Les contrôleurs utilisent ces callbacks pour communiquer avec la Vue
sans avoir de dépendance directe sur ses détails d'implémentation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional


class MessageType(Enum):
    """Types de messages à afficher à l'utilisateur."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class UICallbacks(ABC):
    """Interface abstraite pour les interactions UI."""

    @abstractmethod
    def set_status_message(self, message: str, timeout_ms: int = 3000) -> None:
        """Affiche un message dans la barre de statut."""
        pass

    @abstractmethod
    def show_message(
        self,
        title: str,
        message: str,
        message_type: MessageType = MessageType.INFO,
    ) -> None:
        """Affiche une boîte de dialogue de message."""
        pass

    @abstractmethod
    def apply_tool(self, tool_name: str) -> None:
        """Active un outil dans la vue."""
        pass

    @abstractmethod
    def set_current_filename(self, filename: Optional[str]) -> None:
        """Met à jour le nom de fichier affiché dans la fenêtre."""
        pass

    @abstractmethod
    def refresh_scene_from_model(self) -> None:
        """Rafraîchit la scène graphique à partir du modèle."""
        pass

    @abstractmethod
    def update_transform_actions_visibility(self) -> None:
        """Met à jour la visibilité des actions de transformation."""
        pass

    @abstractmethod
    def push_undo_snapshot(self) -> None:
        """Enregistre un point de sauvegarde pour undo/redo."""
        pass

    @abstractmethod
    def update_toolbar_geometry(self) -> None:
        """Met à jour la géométrie de la barre d'outils."""
        pass

    @abstractmethod
    def toggle_grid(self) -> None:
        """Active/désactive l'affichage de la grille."""
        pass

    @abstractmethod
    def toggle_snap(self) -> None:
        """Active/désactive l'aimantation à la grille."""
        pass

    @abstractmethod
    def toggle_nodes(self) -> None:
        """Active/désactive l'affichage des noeuds."""
        pass

    @abstractmethod
    def toggle_wire_direction(self) -> None:
        """Active/désactive l'affichage de la direction des fils."""
        pass

    @abstractmethod
    def set_meter_label_mode(self, mode: str) -> None:
        """Définit le mode d'étiquette pour les instruments."""
        pass

    @abstractmethod
    def pick_color(self) -> object | None:
        """Ouvre un sélecteur de couleur et retourne la valeur choisie."""
        pass

    @abstractmethod
    def apply_view_background_color(self, color: object) -> None:
        """Applique une couleur de fond à la vue principale."""
        pass
