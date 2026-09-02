"""
Constantes de configuration pour l'application Nodal.

Centralise l'ensemble des constantes magiques du projet (dimensions,
tolérances géométriques, paramètres par défaut de simulation et UI).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CanvasConstants:
    """Constantes pour le canvas, la grille et la détection géométrique."""
    GRID_SIZE: int = 20
    GRID_COLOR_LIGHT: str = "#E0E0E0"
    GRID_COLOR_DARK: str = "#2A2A2A"

    WIRE_SNAP_THRESHOLD: float = 15.0
    NODE_SNAP_THRESHOLD: float = 10.0
    COMPONENT_TERMINAL_OFFSET: int = 30

    NODE_HIT_RADIUS: int = 8
    NODE_VISUAL_RADIUS: int = 2
    NODE_GROUND_RADIUS: int = 3

    WIRE_WIDTH: float = 2.0
    WIRE_SELECTED_WIDTH: float = 3.0


@dataclass(frozen=True)
class ComponentDimensions:
    """Dimensions standards des composants et représentations graphiques."""
    DEFAULT_WIDTH: int = 60
    DEFAULT_HEIGHT: int = 40

    RESISTOR_LENGTH: int = 60
    RESISTOR_ZIG_WIDTH: int = 8
    RESISTOR_ZIG_COUNT: int = 5

    CAPACITOR_PLATE_WIDTH: int = 30
    CAPACITOR_PLATE_GAP: int = 10

    SOURCE_CIRCLE_RADIUS: int = 20


@dataclass(frozen=True)
class SimulationDefaults:
    """Valeurs par défaut pour les moteurs de simulation."""
    AC_START_FREQ: float = 1.0  # Hz
    AC_STOP_FREQ: float = 1e6   # Hz
    AC_POINTS: int = 100

    TRANSIENT_DURATION: float = 1.0     # secondes
    TRANSIENT_TIME_STEP: float = 0.01  # secondes

    CONVERGENCE_TOLERANCE: float = 1e-6
    MAX_ITERATIONS: int = 100


@dataclass(frozen=True)
class UIConstants:
    """Constantes pour l'interface utilisateur et la disposition."""
    PANEL_MIN_WIDTH: int = 250
    PANEL_MAX_WIDTH: int = 400

    ICON_SIZE: int = 48
    BUTTON_SIZE: int = 32

    STATUS_MESSAGE_TIMEOUT: int = 3000  # millisecondes


# Instances globales accessibles par import direct
CANVAS = CanvasConstants()
COMPONENT_DIM = ComponentDimensions()
SIMULATION = SimulationDefaults()
UI = UIConstants()
