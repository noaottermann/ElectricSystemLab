import math
from typing import Any

from .dipole import Dipole


def _get_float_param(params: dict[str, Any], key: str, default: float) -> float:
    """Extrait un parametre numerique en appliquant un defaut."""
    return float(params.get(key, default))

class Resistor(Dipole):
    """Resistance ideale"""

    def __init__(
        self,
        dipole_id: int,
        node_a,
        node_b,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "Resistor",
        resistance: float = 1000.0,
    ) -> None:
        """Initialise une resistance ideale."""
        super().__init__(dipole_id, "Resistor", node_a, node_b, x, y, rotation)
        self.resistance = float(resistance)

    def get_params(self) -> dict[str, float]:
        """Retourne les parametres de la resistance."""
        return {"resistance": self.resistance}

    def set_params(self, params: dict[str, Any]) -> None:
        """Met a jour les parametres de la resistance."""
        self.resistance = _get_float_param(params, "resistance", 1000.0)


class Capacitor(Dipole):
    """Condensateur ideal"""

    def __init__(
        self,
        dipole_id: int,
        node_a,
        node_b,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "Capacitor",
        capacitance: float = 1e-6,
    ) -> None:
        """Initialise un condensateur ideal."""
        super().__init__(dipole_id, "Capacitor", node_a, node_b, x, y, rotation)
        self.capacitance = float(capacitance)

    def get_params(self) -> dict[str, float]:
        """Retourne les parametres du condensateur."""
        return {"capacitance": self.capacitance}

    def set_params(self, params: dict[str, Any]) -> None:
        """Met a jour les parametres du condensateur."""
        self.capacitance = _get_float_param(params, "capacitance", 1e-6)


class Inductor(Dipole):
    """Inductance ideale"""

    def __init__(
        self,
        dipole_id: int,
        node_a,
        node_b,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "Inductor",
        inductance: float = 1e-3,
    ) -> None:
        """Initialise une inductance ideale."""
        super().__init__(dipole_id, "Inductor", node_a, node_b, x, y, rotation)
        self.inductance = float(inductance)

    def get_params(self) -> dict[str, float]:
        """Retourne les parametres de l'inductance."""
        return {"inductance": self.inductance}

    def set_params(self, params: dict[str, Any]) -> None:
        """Met a jour les parametres de l'inductance."""
        self.inductance = _get_float_param(params, "inductance", 1e-3)

class VoltageSourceDC(Dipole):
    """Source de tension continue ideale"""

    def __init__(
        self,
        dipole_id: int,
        node_a,
        node_b,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "VoltageSourceDC",
        dc_voltage: float = 5.0,
    ) -> None:
        """Initialise une source de tension continue."""
        super().__init__(dipole_id, "DC Source", node_a, node_b, x, y, rotation)
        self.dc_voltage = float(dc_voltage)

    def get_params(self) -> dict[str, float]:
        """Retourne les parametres de la source DC."""
        return {"dc_voltage": self.dc_voltage}

    def set_params(self, params: dict[str, Any]) -> None:
        """Met a jour les parametres de la source DC."""
        self.dc_voltage = _get_float_param(params, "dc_voltage", 5.0)


class VoltageSourceAC(Dipole):
    """Source de tension alternative sinusoidale"""

    def __init__(
        self,
        dipole_id: int,
        node_a,
        node_b,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "VoltageSourceAC",
        amplitude: float = 10.0,
        frequency: float = 50.0,
        phase: float = 0.0,
        offset: float = 0.0,
    ) -> None:
        """Initialise une source de tension alternative."""
        super().__init__(dipole_id, "AC Source", node_a, node_b, x, y, rotation)
        self.amplitude = float(amplitude)
        self.frequency = float(frequency)
        self.phase = float(phase)
        self.offset = float(offset)

    def get_value_at_time(self, t: float) -> float:
        """Retourne la tension instantanee a l'instant t."""
        # Utilise une sinusoide amplitude * sin(omega * t + phi) + offset.
        omega = 2 * math.pi * self.frequency
        phi = math.radians(self.phase)
        return self.offset + self.amplitude * math.sin(omega * t + phi)

    def get_params(self) -> dict[str, float]:
        """Retourne les parametres de la source AC."""
        return {
            "amplitude": self.amplitude,
            "frequency": self.frequency,
            "phase": self.phase,
            "offset": self.offset
        }

    def set_params(self, params: dict[str, Any]) -> None:
        """Met a jour les parametres de la source AC."""
        self.amplitude = _get_float_param(params, "amplitude", 10.0)
        self.frequency = _get_float_param(params, "frequency", 50.0)
        self.phase = _get_float_param(params, "phase", 0.0)
        self.offset = _get_float_param(params, "offset", 0.0)