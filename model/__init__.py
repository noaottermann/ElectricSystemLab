"""Public API for model."""

from .component import Component
from .dipole import Dipole, StatefulDipole
from .circuit import Circuit
from .node import Node
from .wire import Wire
from .components import get_component_registry
import solver.stamping_registry  # noqa: F401 - Attache les méthodes polymorphes

__all__ = [
    "Component",
    "Dipole",
    "StatefulDipole",
    "Circuit",
    "Node",
    "Wire",
    "get_component_registry",
]
