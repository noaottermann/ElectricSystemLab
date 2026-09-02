"""Public API for model helpers."""

from .components import get_component_registry
import solver.stamping_registry  # noqa: F401 - Attache les méthodes polymorphes

__all__ = ["get_component_registry"]
