import math
from typing import Any

from .dipole import Dipole, StatefulDipole


_COMPONENT_REGISTRY: dict[str, type] = {}


def register_component(component_name: str, component_class: type) -> type:
    """Enregistre une classe de composant dans le registre global."""
    _COMPONENT_REGISTRY[component_name] = component_class
    return component_class


def get_component_registry() -> dict[str, type]:
    """Retourne la correspondance entre nom de type et classe de composant."""
    return _COMPONENT_REGISTRY.copy()


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


class Switch(StatefulDipole):
    """Interrupteur ideal avec etat ouvert/ferme."""

    def __init__(
        self,
        dipole_id: int,
        node_a,
        node_b,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "Switch",
        state: str = "open",
        resistance_closed: float = 0.0,
        resistance_open: float = 1e12,
    ) -> None:
        """Initialise un interrupteur ideal."""
        super().__init__(
            dipole_id,
            name,
            node_a,
            node_b,
            x,
            y,
            rotation,
            state=str(state),
            state_options=[("open", "switch_state_open"), ("closed", "switch_state_closed")],
        )
        self.resistance_closed = float(resistance_closed)
        self.resistance_open = float(resistance_open)

    @property
    def resistance(self) -> float:
        """Retourne la resistance equivalente selon l'etat."""
        if (self.get_state() or "").lower() == "closed":
            return self.resistance_closed if self.resistance_closed > 0.0 else 1e-9
        return self.resistance_open if self.resistance_open > 0.0 else 1e12

    def get_params(self) -> dict[str, float]:
        """Retourne les parametres du switch."""
        params = super().get_params()
        params.update(
            {
                "resistance_closed": self.resistance_closed,
                "resistance_open": self.resistance_open,
            }
        )
        return params

    def set_params(self, params: dict[str, Any]) -> None:
        """Met a jour les parametres du switch."""
        super().set_params(params)
        self.resistance_closed = _get_float_param(params, "resistance_closed", 0.0)
        self.resistance_open = _get_float_param(params, "resistance_open", 1e12)


class VoltageSource(StatefulDipole):
    """Source de tension avec etat DC/AC selectionnable."""

    def __init__(
        self,
        dipole_id: int,
        node_a,
        node_b,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "VoltageSource",
        state: str = "dc",
        dc_voltage: float = 5.0,
        amplitude: float = 10.0,
        frequency: float = 50.0,
        phase: float = 0.0,
        offset: float = 0.0,
    ) -> None:
        """Initialise une source de tension selectionnable."""
        super().__init__(
            dipole_id,
            name,
            node_a,
            node_b,
            x,
            y,
            rotation,
            state=str(state),
            state_options=[("dc", "source_state_dc"), ("ac", "source_state_ac")],
        )
        self.dc_voltage = float(dc_voltage)
        self.amplitude = float(amplitude)
        self.frequency = float(frequency)
        self.phase = float(phase)
        self.offset = float(offset)

    def get_dc_value(self) -> float:
        """Retourne la valeur DC utilisee par le solveur."""
        if (self.get_state() or "dc").lower() != "dc":
            return 0.0
        return float(self.dc_voltage)

    def get_ac_phasor(self) -> complex:
        """Retourne le phaseur utilise par le solveur AC."""
        if (self.get_state() or "dc").lower() != "ac":
            return 0.0
        omega_phase = math.radians(self.phase)
        return float(self.amplitude) * (math.cos(omega_phase) + 1j * math.sin(omega_phase))

    def get_value_at_time(self, t: float) -> float:
        """Retourne la valeur instantanee associee a l'etat actif."""
        if (self.get_state() or "dc").lower() == "ac":
            omega = 2 * math.pi * self.frequency
            phi = math.radians(self.phase)
            return self.offset + self.amplitude * math.sin(omega * t + phi)
        return self.dc_voltage

    def get_params(self) -> dict[str, float]:
        return {
            "state": self.get_state() or "dc",
            "dc_voltage": self.dc_voltage,
            "amplitude": self.amplitude,
            "frequency": self.frequency,
            "phase": self.phase,
            "offset": self.offset,
        }

    def set_params(self, params: dict[str, Any]) -> None:
        self.set_state(str(params.get("state", self.get_state() or "dc")))
        self.dc_voltage = _get_float_param(params, "dc_voltage", 5.0)
        self.amplitude = _get_float_param(params, "amplitude", 10.0)
        self.frequency = _get_float_param(params, "frequency", 50.0)
        self.phase = _get_float_param(params, "phase", 0.0)
        self.offset = _get_float_param(params, "offset", 0.0)


class VoltageSourceDC(VoltageSource):
    """Source de tension continue ideale."""

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
        super().__init__(
            dipole_id,
            node_a,
            node_b,
            x,
            y,
            rotation,
            name="DC Source",
            state="dc",
            dc_voltage=dc_voltage,
        )


class VoltageSourceAC(VoltageSource):
    """Source de tension alternative sinusoidale."""

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
        super().__init__(
            dipole_id,
            node_a,
            node_b,
            x,
            y,
            rotation,
            name="AC Source",
            state="ac",
            amplitude=amplitude,
            frequency=frequency,
            phase=phase,
            offset=offset,
        )


class CurrentSource(StatefulDipole):
    """Source de courant avec etat DC/AC selectionnable."""

    def __init__(
        self,
        dipole_id: int,
        node_a,
        node_b,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "CurrentSource",
        state: str = "dc",
        dc_current: float = 1.0,
        amplitude: float = 1.0,
        frequency: float = 50.0,
        phase: float = 0.0,
        offset: float = 0.0,
    ) -> None:
        """Initialise une source de courant selectionnable."""
        super().__init__(
            dipole_id,
            name,
            node_a,
            node_b,
            x,
            y,
            rotation,
            state=str(state),
            state_options=[("dc", "source_state_dc"), ("ac", "source_state_ac")],
        )
        self.dc_current = float(dc_current)
        self.amplitude = float(amplitude)
        self.frequency = float(frequency)
        self.phase = float(phase)
        self.offset = float(offset)

    def get_dc_value(self) -> float:
        """Retourne la valeur DC utilisee par le solveur."""
        if (self.get_state() or "dc").lower() != "dc":
            return 0.0
        return float(self.dc_current)

    def get_ac_phasor(self) -> complex:
        """Retourne le phaseur utilise par le solveur AC."""
        if (self.get_state() or "dc").lower() != "ac":
            return 0.0
        omega_phase = math.radians(self.phase)
        return float(self.amplitude) * (math.cos(omega_phase) + 1j * math.sin(omega_phase))

    def get_value_at_time(self, t: float) -> float:
        """Retourne la valeur instantanee associee a l'etat actif."""
        if (self.get_state() or "dc").lower() == "ac":
            omega = 2 * math.pi * self.frequency
            phi = math.radians(self.phase)
            return self.offset + self.amplitude * math.sin(omega * t + phi)
        return self.dc_current

    def get_params(self) -> dict[str, float]:
        return {
            "state": self.get_state() or "dc",
            "dc_current": self.dc_current,
            "amplitude": self.amplitude,
            "frequency": self.frequency,
            "phase": self.phase,
            "offset": self.offset,
        }

    def set_params(self, params: dict[str, Any]) -> None:
        self.set_state(str(params.get("state", self.get_state() or "dc")))
        self.dc_current = _get_float_param(params, "dc_current", 1.0)
        self.amplitude = _get_float_param(params, "amplitude", 1.0)
        self.frequency = _get_float_param(params, "frequency", 50.0)
        self.phase = _get_float_param(params, "phase", 0.0)
        self.offset = _get_float_param(params, "offset", 0.0)


class CurrentSourceDC(CurrentSource):
    """Source de courant continue ideale."""

    def __init__(
        self,
        dipole_id: int,
        node_a,
        node_b,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "CurrentSourceDC",
        dc_current: float = 1.0,
    ) -> None:
        super().__init__(
            dipole_id,
            node_a,
            node_b,
            x,
            y,
            rotation,
            name="DC Current",
            state="dc",
            dc_current=dc_current,
        )


class CurrentSourceAC(CurrentSource):
    """Source de courant alternative sinusoidale."""

    def __init__(
        self,
        dipole_id: int,
        node_a,
        node_b,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "CurrentSourceAC",
        amplitude: float = 1.0,
        frequency: float = 50.0,
        phase: float = 0.0,
        offset: float = 0.0,
    ) -> None:
        super().__init__(
            dipole_id,
            node_a,
            node_b,
            x,
            y,
            rotation,
            name="AC Current",
            state="ac",
            amplitude=amplitude,
            frequency=frequency,
            phase=phase,
            offset=offset,
        )

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


class CurrentSourceDC(Dipole):
    """Source de courant continue ideale."""

    def __init__(
        self,
        dipole_id: int,
        node_a,
        node_b,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "CurrentSourceDC",
        dc_current: float = 1.0,
    ) -> None:
        """Initialise une source de courant continue."""
        super().__init__(dipole_id, "DC Current", node_a, node_b, x, y, rotation)
        self.dc_current = float(dc_current)

    def get_params(self) -> dict[str, float]:
        """Retourne les parametres de la source de courant DC."""
        return {"dc_current": self.dc_current}

    def set_params(self, params: dict[str, Any]) -> None:
        """Met a jour les parametres de la source de courant DC."""
        self.dc_current = _get_float_param(params, "dc_current", 1.0)


class CurrentSourceAC(Dipole):
    """Source de courant alternative sinusoidale."""

    def __init__(
        self,
        dipole_id: int,
        node_a,
        node_b,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "CurrentSourceAC",
        amplitude: float = 1.0,
        frequency: float = 50.0,
        phase: float = 0.0,
        offset: float = 0.0,
    ) -> None:
        """Initialise une source de courant alternative."""
        super().__init__(dipole_id, "AC Current", node_a, node_b, x, y, rotation)
        self.amplitude = float(amplitude)
        self.frequency = float(frequency)
        self.phase = float(phase)
        self.offset = float(offset)

    def get_value_at_time(self, t: float) -> float:
        """Retourne le courant instantane a l'instant t."""
        omega = 2 * math.pi * self.frequency
        phi = math.radians(self.phase)
        return self.offset + self.amplitude * math.sin(omega * t + phi)

    def get_params(self) -> dict[str, float]:
        """Retourne les parametres de la source AC."""
        return {
            "amplitude": self.amplitude,
            "frequency": self.frequency,
            "phase": self.phase,
            "offset": self.offset,
        }

    def set_params(self, params: dict[str, Any]) -> None:
        """Met a jour les parametres de la source AC."""
        self.amplitude = _get_float_param(params, "amplitude", 1.0)
        self.frequency = _get_float_param(params, "frequency", 50.0)
        self.phase = _get_float_param(params, "phase", 0.0)
        self.offset = _get_float_param(params, "offset", 0.0)


class VoltageControlledCurrentSource(Dipole):
    """Source de courant dependante (VCCS)."""

    def __init__(
        self,
        dipole_id: int,
        node_a,
        node_b,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "VCCS",
        transconductance: float = 1e-3,
        control_dipole_id: int = 0,
    ) -> None:
        """Initialise une source de courant commandee en tension."""
        super().__init__(dipole_id, "VCCS", node_a, node_b, x, y, rotation)
        self.transconductance = float(transconductance)
        self.control_dipole_id = int(control_dipole_id)

    def get_params(self) -> dict[str, float]:
        """Retourne les parametres de la source dependante."""
        return {
            "transconductance": self.transconductance,
            "control_dipole_id": self.control_dipole_id,
        }

    def set_params(self, params: dict[str, Any]) -> None:
        """Met a jour les parametres de la source dependante."""
        self.transconductance = _get_float_param(params, "transconductance", 1e-3)
        self.control_dipole_id = int(params.get("control_dipole_id", self.control_dipole_id) or 0)


class CurrentControlledCurrentSource(Dipole):
    """Source de courant dependante (CCCS)."""

    def __init__(
        self,
        dipole_id: int,
        node_a,
        node_b,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "CCCS",
        gain: float = 1.0,
        control_dipole_id: int = 0,
    ) -> None:
        """Initialise une source de courant commandee en courant."""
        super().__init__(dipole_id, "CCCS", node_a, node_b, x, y, rotation)
        self.gain = float(gain)
        self.control_dipole_id = int(control_dipole_id)

    def get_params(self) -> dict[str, float]:
        """Retourne les parametres de la source dependante."""
        return {
            "gain": self.gain,
            "control_dipole_id": self.control_dipole_id,
        }

    def set_params(self, params: dict[str, Any]) -> None:
        """Met a jour les parametres de la source dependante."""
        self.gain = _get_float_param(params, "gain", 1.0)
        self.control_dipole_id = int(params.get("control_dipole_id", self.control_dipole_id) or 0)


class VoltageControlledVoltageSource(Dipole):
    """Source de tension dependante (VCVS)."""

    def __init__(
        self,
        dipole_id: int,
        node_a,
        node_b,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "VCVS",
        gain: float = 1.0,
        control_dipole_id: int = 0,
    ) -> None:
        """Initialise une source de tension commandee en tension."""
        super().__init__(dipole_id, "VCVS", node_a, node_b, x, y, rotation)
        self.gain = float(gain)
        self.control_dipole_id = int(control_dipole_id)

    def get_params(self) -> dict[str, float]:
        """Retourne les parametres de la source dependante."""
        return {
            "gain": self.gain,
            "control_dipole_id": self.control_dipole_id,
        }

    def set_params(self, params: dict[str, Any]) -> None:
        """Met a jour les parametres de la source dependante."""
        self.gain = _get_float_param(params, "gain", 1.0)
        self.control_dipole_id = int(params.get("control_dipole_id", self.control_dipole_id) or 0)


class CurrentControlledVoltageSource(Dipole):
    """Source de tension dependante (CCVS)."""

    def __init__(
        self,
        dipole_id: int,
        node_a,
        node_b,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "CCVS",
        transresistance: float = 1.0,
        control_dipole_id: int = 0,
    ) -> None:
        """Initialise une source de tension commandee en courant."""
        super().__init__(dipole_id, "CCVS", node_a, node_b, x, y, rotation)
        self.transresistance = float(transresistance)
        self.control_dipole_id = int(control_dipole_id)

    def get_params(self) -> dict[str, float]:
        """Retourne les parametres de la source dependante."""
        return {
            "transresistance": self.transresistance,
            "control_dipole_id": self.control_dipole_id,
        }

    def set_params(self, params: dict[str, Any]) -> None:
        """Met a jour les parametres de la source dependante."""
        self.transresistance = _get_float_param(params, "transresistance", 1.0)
        self.control_dipole_id = int(params.get("control_dipole_id", self.control_dipole_id) or 0)


class Diode(Dipole):
    """Diode ideale avec loi exponentielle."""

    def __init__(
        self,
        dipole_id: int,
        node_a,
        node_b,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "Diode",
        saturation_current: float = 1e-12,
        ideality_factor: float = 1.0,
        thermal_voltage: float = 0.02585,
    ) -> None:
        """Initialise une diode non lineaire."""
        super().__init__(dipole_id, "Diode", node_a, node_b, x, y, rotation)
        self.saturation_current = float(saturation_current)
        self.ideality_factor = float(ideality_factor)
        self.thermal_voltage = float(thermal_voltage)

    def get_params(self) -> dict[str, float]:
        """Retourne les parametres de la diode."""
        return {
            "saturation_current": self.saturation_current,
            "ideality_factor": self.ideality_factor,
            "thermal_voltage": self.thermal_voltage,
        }

    def set_params(self, params: dict[str, Any]) -> None:
        """Met a jour les parametres de la diode."""
        self.saturation_current = _get_float_param(params, "saturation_current", 1e-12)
        self.ideality_factor = _get_float_param(params, "ideality_factor", 1.0)
        self.thermal_voltage = _get_float_param(params, "thermal_voltage", 0.02585)


class LED(Diode):
    """LED avec parametres par defaut adaptes."""

    def __init__(
        self,
        dipole_id: int,
        node_a,
        node_b,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "LED",
        saturation_current: float = 1e-9,
        ideality_factor: float = 2.0,
        thermal_voltage: float = 0.02585,
    ) -> None:
        """Initialise une LED non lineaire."""
        super().__init__(
            dipole_id,
            node_a,
            node_b,
            x=x,
            y=y,
            rotation=rotation,
            name=name,
            saturation_current=saturation_current,
            ideality_factor=ideality_factor,
            thermal_voltage=thermal_voltage,
        )


class Ammeter(Dipole):
    """Ampèremètre ideal, approximé comme une resistance quasi-nulle."""

    def __init__(
        self,
        dipole_id: int,
        node_a,
        node_b,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "Ammeter",
        resistance: float = 1e-9,
    ) -> None:
        super().__init__(dipole_id, "Ammeter", node_a, node_b, x, y, rotation)
        self.resistance = float(resistance)

    def get_params(self) -> dict[str, float]:
        return {"resistance": self.resistance}

    def set_params(self, params: dict[str, Any]) -> None:
        self.resistance = _get_float_param(params, "resistance", 1e-9)


class Voltmeter(Dipole):
    """Voltmètre ideal, approximé comme une resistance quasi-infinie."""

    def __init__(
        self,
        dipole_id: int,
        node_a,
        node_b,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "Voltmeter",
        resistance: float = 1e12,
    ) -> None:
        super().__init__(dipole_id, "Voltmeter", node_a, node_b, x, y, rotation)
        self.resistance = float(resistance)

    def get_params(self) -> dict[str, float]:
        return {"resistance": self.resistance}

    def set_params(self, params: dict[str, Any]) -> None:
        self.resistance = _get_float_param(params, "resistance", 1e12)


class Ground(Dipole):
    """Symbole de masse, attache a un noeud mis a la masse."""

    def __init__(
        self,
        dipole_id: int,
        node_a,
        node_b=None,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "Ground",
    ) -> None:
        if node_a is not None and hasattr(node_a, "is_ground"):
            node_a.is_ground = True
        super().__init__(dipole_id, "Ground", node_a, node_b, x, y, rotation)


class OpAmp(Dipole):
    """AOP ideal simplifie pour l'interface."""

    def __init__(
        self,
        dipole_id: int,
        node_a,
        node_b,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "OpAmp",
        gain: float = 1e5,
    ) -> None:
        super().__init__(dipole_id, "OpAmp", node_a, node_b, x, y, rotation)
        self.gain = float(gain)

    def get_params(self) -> dict[str, float]:
        return {"gain": self.gain}

    def set_params(self, params: dict[str, Any]) -> None:
        self.gain = _get_float_param(params, "gain", 1e5)


class Transformer(Dipole):
    """Transformateur ideal simplifie."""

    def __init__(
        self,
        dipole_id: int,
        node_a,
        node_b,
        node_c=None,
        node_d=None,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "Transformer",
        ratio: float = 1.0,
    ) -> None:
        super().__init__(dipole_id, "Transformer", node_a, node_b, x, y, rotation)
        self.node_c = node_c
        self.node_d = node_d
        self.ratio = float(ratio)

    def get_params(self) -> dict[str, float]:
        return {"ratio": self.ratio}

    def set_params(self, params: dict[str, Any]) -> None:
        self.ratio = _get_float_param(params, "ratio", 1.0)


class Transistor(Dipole):
    """Transistor ideal simplifie."""

    def __init__(
        self,
        dipole_id: int,
        node_a,
        node_b,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "Transistor",
        beta: float = 100.0,
    ) -> None:
        super().__init__(dipole_id, "Transistor", node_a, node_b, x, y, rotation)
        self.beta = float(beta)

    def get_params(self) -> dict[str, float]:
        return {"beta": self.beta}

    def set_params(self, params: dict[str, Any]) -> None:
        self.beta = _get_float_param(params, "beta", 100.0)


def _populate_component_registry() -> None:
    """Enregistre les composants concrets disponibles dans ce module."""
    for component_name in [
        "Resistor",
        "Capacitor",
        "Inductor",
        "Switch",
        "VoltageSource",
        "VoltageSourceDC",
        "VoltageSourceAC",
        "CurrentSource",
        "CurrentSourceDC",
        "CurrentSourceAC",
        "VoltageControlledCurrentSource",
        "CurrentControlledCurrentSource",
        "VoltageControlledVoltageSource",
        "CurrentControlledVoltageSource",
        "Diode",
        "LED",
        "Ammeter",
        "Voltmeter",
        "Ground",
        "OpAmp",
        "Transformer",
        "Transistor",
    ]:
        component_class = globals().get(component_name)
        if isinstance(component_class, type) and issubclass(component_class, Dipole):
            if component_class not in (Dipole, StatefulDipole):
                register_component(component_name, component_class)


_populate_component_registry()