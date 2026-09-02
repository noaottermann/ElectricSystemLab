"""
Gestionnaire du presse-papier et de l'historique undo/redo pour le canvas.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from model.circuit import Circuit


class ClipboardManager:
    """Gère la pile d'annulation et le presse-papier de composants."""

    def __init__(self, max_undo_steps: int = 100) -> None:
        self._undo_stack: list[str] = []
        self._redo_stack: list[str] = []
        self._max_undo_steps = max_undo_steps
        self._clipboard_payload: Optional[dict[str, Any]] = None

    def capture_snapshot(self, circuit: Optional[Circuit]) -> Optional[str]:
        """Capture un instantané JSON complet du circuit."""
        if circuit is None:
            return None
        return circuit.to_json()

    def push_undo_state(self, snapshot: Optional[str]) -> None:
        """Enregistre un état dans la pile d'annulation."""
        if snapshot is None:
            return
        self._undo_stack.append(snapshot)
        if len(self._undo_stack) > self._max_undo_steps:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def undo(self, current_snapshot: Optional[str]) -> Optional[str]:
        """Annule la dernière action et retourne l'état précédent."""
        if not self._undo_stack:
            return None
        if current_snapshot is not None:
            self._redo_stack.append(current_snapshot)
        return self._undo_stack.pop()

    def redo(self, current_snapshot: Optional[str]) -> Optional[str]:
        """Rétablit l'action annulée et retourne l'état suivant."""
        if not self._redo_stack:
            return None
        if current_snapshot is not None:
            self._undo_stack.append(current_snapshot)
        return self._redo_stack.pop()

    def copy(self, payload: dict[str, Any]) -> None:
        """Enregistre un ensemble d'éléments dans le presse-papier."""
        self._clipboard_payload = json.loads(json.dumps(payload))

    def get_clipboard_payload(self) -> Optional[dict[str, Any]]:
        """Retourne une copie du contenu du presse-papier."""
        if self._clipboard_payload is None:
            return None
        return json.loads(json.dumps(self._clipboard_payload))

    def has_clipboard_data(self) -> bool:
        """Indique si le presse-papier contient des éléments."""
        return self._clipboard_payload is not None
