import math
from typing import Any

from .component import Component
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

    def get_params(self) -> dict[str, Any]:
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

    def get_params(self) -> dict[str, Any]:
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

    def get_params(self) -> dict[str, Any]:
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

    def get_params(self) -> dict[str, Any]:
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

    def get_params(self) -> dict[str, Any]:
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

    def get_params(self) -> dict[str, Any]:
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

    def get_params(self) -> dict[str, Any]:
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

    def get_params(self) -> dict[str, Any]:
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

    def get_params(self) -> dict[str, Any]:
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

    def get_params(self) -> dict[str, Any]:
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

    def get_params(self) -> dict[str, Any]:
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

    def get_params(self) -> dict[str, Any]:
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

    def get_params(self) -> dict[str, Any]:
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

    def disconnect(self) -> None:
        """Déconnecte le ground et remet is_ground à False."""
        if self.node_a is not None and hasattr(self.node_a, "is_ground"):
            self.node_a.is_ground = False
        super().disconnect()

    def get_terminal_offsets(self) -> list[tuple[float, float]]:
        return [(0.0, -15.0)]


class OpAmp(Component):
    """Amplificateur Opérationnel (AOP à 3 bornes : Entrée+, Entrée-, Sortie)."""

    def __init__(
        self,
        dipole_id: int,
        node_a=None,
        node_b=None,
        node_c=None,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "OpAmp",
        gain: float = 1e5,
        v_sat_pos: float = 15.0,
        v_sat_neg: float = -15.0,
        r_in: float = 1e6,
        r_out: float = 10.0,
    ) -> None:
        super().__init__(dipole_id, name, node_a, node_b, node_c, x=x, y=y, rotation=rotation)
        self.gain = float(gain)
        self.v_sat_pos = float(v_sat_pos)
        self.v_sat_neg = float(v_sat_neg)
        self.r_in = float(r_in)
        self.r_out = float(r_out)

    def get_terminal_offsets(self) -> list[tuple[float, float]]:
        return [(-30.0, -12.0), (-30.0, 12.0), (30.0, 0.0)]

    @property
    def node_a(self):
        return self.nodes[0] if len(self.nodes) > 0 else None

    @node_a.setter
    def node_a(self, value):
        if len(self.nodes) > 0:
            self.nodes[0] = value
        else:
            self.nodes.append(value)

    @property
    def node_b(self):
        return self.nodes[1] if len(self.nodes) > 1 else None

    @node_b.setter
    def node_b(self, value):
        if len(self.nodes) > 1:
            self.nodes[1] = value
        elif len(self.nodes) == 1:
            self.nodes.append(value)
        else:
            self.nodes.extend([None, value])

    @property
    def node_c(self):
        return self.nodes[2] if len(self.nodes) > 2 else None

    @node_c.setter
    def node_c(self, value):
        while len(self.nodes) < 3:
            self.nodes.append(None)
        self.nodes[2] = value

    @property
    def node_in_plus(self):
        return self.node_a

    @property
    def node_in_minus(self):
        return self.node_b

    @property
    def node_out(self):
        return self.node_c

    def get_params(self) -> dict[str, Any]:
        return {
            "gain": self.gain,
            "v_sat_pos": self.v_sat_pos,
            "v_sat_neg": self.v_sat_neg,
            "r_in": self.r_in,
            "r_out": self.r_out,
        }

    def set_params(self, params: dict[str, Any]) -> None:
        self.gain = _get_float_param(params, "gain", 1e5)
        self.v_sat_pos = _get_float_param(params, "v_sat_pos", 15.0)
        self.v_sat_neg = _get_float_param(params, "v_sat_neg", -15.0)
        self.r_in = _get_float_param(params, "r_in", 1e6)
        self.r_out = _get_float_param(params, "r_out", 10.0)


class Transformer(Component):
    """Transformateur idéal à 4 bornes (Primaire+, Primaire-, Secondaire+, Secondaire-)."""

    def __init__(
        self,
        dipole_id: int,
        node_a=None,
        node_b=None,
        node_c=None,
        node_d=None,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "Transformer",
        ratio: float = 1.0,
        l1: float = 1e-3,
        l2: float = 1e-3,
        coupling: float = 0.99,
    ) -> None:
        super().__init__(dipole_id, name, node_a, node_b, node_c, node_d, x=x, y=y, rotation=rotation)
        self.ratio = float(ratio)
        self.l1 = float(l1)
        self.l2 = float(l2)
        self.coupling = float(coupling)

    @property
    def node_a(self):
        return self.nodes[0] if len(self.nodes) > 0 else None

    @node_a.setter
    def node_a(self, value):
        if len(self.nodes) > 0:
            self.nodes[0] = value
        else:
            self.nodes.append(value)

    @property
    def node_b(self):
        return self.nodes[1] if len(self.nodes) > 1 else None

    @node_b.setter
    def node_b(self, value):
        if len(self.nodes) > 1:
            self.nodes[1] = value
        elif len(self.nodes) == 1:
            self.nodes.append(value)
        else:
            self.nodes.extend([None, value])

    @property
    def node_c(self):
        return self.nodes[2] if len(self.nodes) > 2 else None

    @node_c.setter
    def node_c(self, value):
        while len(self.nodes) < 3:
            self.nodes.append(None)
        self.nodes[2] = value

    @property
    def node_d(self):
        return self.nodes[3] if len(self.nodes) > 3 else None

    @node_d.setter
    def node_d(self, value):
        while len(self.nodes) < 4:
            self.nodes.append(None)
        self.nodes[3] = value

    @property
    def node_p_pos(self):
        return self.node_a

    @property
    def node_p_neg(self):
        return self.node_b

    @property
    def node_s_pos(self):
        return self.node_c

    @property
    def node_s_neg(self):
        return self.node_d

    def get_terminal_offsets(self) -> list[tuple[float, float]]:
        return [(-30.0, -15.0), (-30.0, 15.0), (30.0, -15.0), (30.0, 15.0)]

    def get_params(self) -> dict[str, Any]:
        return {
            "ratio": self.ratio,
            "l1": self.l1,
            "l2": self.l2,
            "coupling": self.coupling,
        }

    def set_params(self, params: dict[str, Any]) -> None:
        self.ratio = _get_float_param(params, "ratio", 1.0)
        self.l1 = _get_float_param(params, "l1", 1e-3)
        self.l2 = _get_float_param(params, "l2", 1e-3)
        self.coupling = _get_float_param(params, "coupling", 0.99)


class Transistor(Component):
    """Transistor Bipolaire (BJT NPN ou PNP à 3 bornes : Collecteur, Base, Émetteur)."""

    def __init__(
        self,
        dipole_id: int,
        node_a=None,
        node_b=None,
        node_c=None,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "Transistor",
        transistor_type: str = "NPN",
        beta: float = 100.0,
        v_be0: float = 0.7,
        r_in: float = 1000.0,
    ) -> None:
        super().__init__(dipole_id, name, node_a, node_b, node_c, x=x, y=y, rotation=rotation)
        self.transistor_type = "PNP" if str(transistor_type).upper() == "PNP" else "NPN"
        self.beta = float(beta)
        self.v_be0 = float(v_be0)
        self.r_in = float(r_in)

    def get_terminal_offsets(self) -> list[tuple[float, float]]:
        return [(15.0, -25.0), (-30.0, 0.0), (15.0, 25.0)]

    @property
    def node_a(self):
        return self.nodes[0] if len(self.nodes) > 0 else None

    @node_a.setter
    def node_a(self, value):
        if len(self.nodes) > 0:
            self.nodes[0] = value
        else:
            self.nodes.append(value)

    @property
    def node_b(self):
        return self.nodes[1] if len(self.nodes) > 1 else None

    @node_b.setter
    def node_b(self, value):
        if len(self.nodes) > 1:
            self.nodes[1] = value
        elif len(self.nodes) == 1:
            self.nodes.append(value)
        else:
            self.nodes.extend([None, value])

    @property
    def node_c(self):
        return self.nodes[2] if len(self.nodes) > 2 else None

    @node_c.setter
    def node_c(self, value):
        while len(self.nodes) < 3:
            self.nodes.append(None)
        self.nodes[2] = value

    @property
    def node_collector(self):
        return self.node_a

    @property
    def node_base(self):
        return self.node_b

    @property
    def node_emitter(self):
        return self.node_c

    def get_state(self) -> str:
        return self.transistor_type

    def get_state_options(self) -> list[tuple[str, str]]:
        return [("NPN", "NPN"), ("PNP", "PNP")]

    def set_state(self, value: str) -> None:
        self.transistor_type = "PNP" if str(value).upper() == "PNP" else "NPN"

    def get_params(self) -> dict[str, Any]:
        return {
            "transistor_type": self.transistor_type,
            "beta": self.beta,
            "v_be0": self.v_be0,
            "r_in": self.r_in,
        }

    def set_params(self, params: dict[str, Any]) -> None:
        self.transistor_type = str(params.get("transistor_type", self.transistor_type)).upper()
        self.beta = _get_float_param(params, "beta", 100.0)
        self.v_be0 = _get_float_param(params, "v_be0", 0.7)
        self.r_in = _get_float_param(params, "r_in", 1000.0)


class ZenerDiode(Diode):
    """Diode Zener pour régulation et écrêtage de tension."""

    def __init__(
        self,
        dipole_id: int,
        node_a,
        node_b,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "ZenerDiode",
        zener_voltage: float = 5.1,
        zener_resistance: float = 10.0,
        zener_current: float = 1e-3,
        saturation_current: float = 1e-12,
        ideality_factor: float = 1.0,
        thermal_voltage: float = 0.02585,
    ) -> None:
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
        self.zener_voltage = float(zener_voltage)
        self.zener_resistance = float(zener_resistance)
        self.zener_current = float(zener_current)

    def get_params(self) -> dict[str, Any]:
        params = super().get_params()
        params.update({
            "zener_voltage": self.zener_voltage,
            "zener_resistance": self.zener_resistance,
            "zener_current": self.zener_current,
        })
        return params

    def set_params(self, params: dict[str, Any]) -> None:
        super().set_params(params)
        self.zener_voltage = _get_float_param(params, "zener_voltage", 5.1)
        self.zener_resistance = _get_float_param(params, "zener_resistance", 10.0)
        self.zener_current = _get_float_param(params, "zener_current", 1e-3)


class Potentiometer(Component):
    """Potentiomètre (résistance variable à 3 bornes avec curseur réglable)."""

    def __init__(
        self,
        dipole_id: int,
        node_a=None,
        node_w=None,
        node_b=None,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "Potentiometer",
        resistance: float = 10000.0,
        slider_ratio: float = 0.5,
    ) -> None:
        super().__init__(dipole_id, name, node_a, node_w, node_b, x=x, y=y, rotation=rotation)
        self.resistance = float(resistance)
        self.slider_ratio = max(0.001, min(0.999, float(slider_ratio)))

    def get_terminal_offsets(self) -> list[tuple[float, float]]:
        return [(-30.0, 0.0), (0.0, -20.0), (30.0, 0.0)]

    @property
    def node_a(self):
        return self.nodes[0] if len(self.nodes) > 0 else None

    @node_a.setter
    def node_a(self, value):
        if len(self.nodes) > 0:
            self.nodes[0] = value
        else:
            self.nodes.append(value)

    @property
    def node_w(self):
        return self.nodes[1] if len(self.nodes) > 1 else None

    @node_w.setter
    def node_w(self, value):
        if len(self.nodes) > 1:
            self.nodes[1] = value
        elif len(self.nodes) == 1:
            self.nodes.append(value)
        else:
            self.nodes.extend([None, value])

    @property
    def node_b(self):
        return self.nodes[2] if len(self.nodes) > 2 else None

    @node_b.setter
    def node_b(self, value):
        while len(self.nodes) < 3:
            self.nodes.append(None)
        self.nodes[2] = value

    @property
    def r1(self) -> float:
        """Résistance entre borne A et curseur W."""
        return max(1e-3, self.resistance * self.slider_ratio)

    @property
    def r2(self) -> float:
        """Résistance entre curseur W et borne B."""
        return max(1e-3, self.resistance * (1.0 - self.slider_ratio))

    def get_params(self) -> dict[str, Any]:
        return {
            "resistance": self.resistance,
            "slider_ratio": self.slider_ratio,
        }

    def set_params(self, params: dict[str, Any]) -> None:
        self.resistance = _get_float_param(params, "resistance", 10000.0)
        self.slider_ratio = max(0.001, min(0.999, _get_float_param(params, "slider_ratio", 0.5)))


class MOSFET(Component):
    """Transistor à effet de champ MOSFET (NMOS ou PMOS à 3 bornes : Drain, Grille, Source)."""

    def __init__(
        self,
        dipole_id: int,
        node_a=None,
        node_b=None,
        node_c=None,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "MOSFET",
        mosfet_type: str = "NMOS",
        v_threshold: float = 2.0,
        transconductance: float = 0.02,
        lambda_mod: float = 0.01,
        r_ds_on: float = 0.1,
    ) -> None:
        super().__init__(dipole_id, name, node_a, node_b, node_c, x=x, y=y, rotation=rotation)
        self.mosfet_type = "PMOS" if str(mosfet_type).upper() == "PMOS" else "NMOS"
        self.v_threshold = float(v_threshold)
        self.transconductance = float(transconductance)
        self.lambda_mod = float(lambda_mod)
        self.r_ds_on = float(r_ds_on)

    def get_terminal_offsets(self) -> list[tuple[float, float]]:
        return [(15.0, -25.0), (-30.0, 0.0), (15.0, 25.0)]

    @property
    def node_a(self):
        return self.nodes[0] if len(self.nodes) > 0 else None

    @node_a.setter
    def node_a(self, value):
        if len(self.nodes) > 0:
            self.nodes[0] = value
        else:
            self.nodes.append(value)

    @property
    def node_b(self):
        return self.nodes[1] if len(self.nodes) > 1 else None

    @node_b.setter
    def node_b(self, value):
        if len(self.nodes) > 1:
            self.nodes[1] = value
        elif len(self.nodes) == 1:
            self.nodes.append(value)
        else:
            self.nodes.extend([None, value])

    @property
    def node_c(self):
        return self.nodes[2] if len(self.nodes) > 2 else None

    @node_c.setter
    def node_c(self, value):
        while len(self.nodes) < 3:
            self.nodes.append(None)
        self.nodes[2] = value

    @property
    def node_drain(self):
        return self.node_a

    @property
    def node_gate(self):
        return self.node_b

    @property
    def node_source(self):
        return self.node_c

    def get_state(self) -> str:
        return self.mosfet_type

    def get_state_options(self) -> list[tuple[str, str]]:
        return [("NMOS", "NMOS (Canal N)"), ("PMOS", "PMOS (Canal P)")]

    def set_state(self, value: str) -> None:
        self.mosfet_type = "PMOS" if str(value).upper() == "PMOS" else "NMOS"

    def get_params(self) -> dict[str, Any]:
        return {
            "mosfet_type": self.mosfet_type,
            "v_threshold": self.v_threshold,
            "transconductance": self.transconductance,
            "lambda_mod": self.lambda_mod,
            "r_ds_on": self.r_ds_on,
        }

    def set_params(self, params: dict[str, Any]) -> None:
        self.mosfet_type = str(params.get("mosfet_type", self.mosfet_type)).upper()
        self.v_threshold = _get_float_param(params, "v_threshold", 2.0)
        self.transconductance = _get_float_param(params, "transconductance", 0.02)
        self.lambda_mod = _get_float_param(params, "lambda_mod", 0.01)
        self.r_ds_on = _get_float_param(params, "r_ds_on", 0.1)


class MOSFET_NMOS(MOSFET):
    def __init__(self, dipole_id: int, *nodes, **kwargs) -> None:
        super().__init__(dipole_id, *nodes, mosfet_type="NMOS", name="MOSFET_NMOS", **kwargs)


class MOSFET_PMOS(MOSFET):
    def __init__(self, dipole_id: int, *nodes, **kwargs) -> None:
        super().__init__(dipole_id, *nodes, mosfet_type="PMOS", v_threshold=-2.0, name="MOSFET_PMOS", **kwargs)


class Comparator(Component):
    """Comparateur de tension analogique (In+, In-, Out) avec hystérésis."""

    def __init__(
        self,
        dipole_id: int,
        node_a=None,
        node_b=None,
        node_c=None,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "Comparator",
        v_sat_pos: float = 5.0,
        v_sat_neg: float = 0.0,
        hysteresis: float = 0.05,
    ) -> None:
        super().__init__(dipole_id, name, node_a, node_b, node_c, x=x, y=y, rotation=rotation)
        self.v_sat_pos = float(v_sat_pos)
        self.v_sat_neg = float(v_sat_neg)
        self.hysteresis = float(hysteresis)
        self._last_state: float = 0.0

    def get_terminal_offsets(self) -> list[tuple[float, float]]:
        return [(-30.0, -12.0), (-30.0, 12.0), (30.0, 0.0)]

    @property
    def node_a(self):
        return self.nodes[0] if len(self.nodes) > 0 else None

    @node_a.setter
    def node_a(self, value):
        if len(self.nodes) > 0:
            self.nodes[0] = value
        else:
            self.nodes.append(value)

    @property
    def node_b(self):
        return self.nodes[1] if len(self.nodes) > 1 else None

    @node_b.setter
    def node_b(self, value):
        if len(self.nodes) > 1:
            self.nodes[1] = value
        elif len(self.nodes) == 1:
            self.nodes.append(value)
        else:
            self.nodes.extend([None, value])

    @property
    def node_c(self):
        return self.nodes[2] if len(self.nodes) > 2 else None

    @node_c.setter
    def node_c(self, value):
        while len(self.nodes) < 3:
            self.nodes.append(None)
        self.nodes[2] = value

    @property
    def node_in_plus(self):
        return self.node_a

    @property
    def node_in_minus(self):
        return self.node_b

    @property
    def node_out(self):
        return self.node_c

    def get_params(self) -> dict[str, Any]:
        return {
            "v_sat_pos": self.v_sat_pos,
            "v_sat_neg": self.v_sat_neg,
            "hysteresis": self.hysteresis,
        }

    def set_params(self, params: dict[str, Any]) -> None:
        self.v_sat_pos = _get_float_param(params, "v_sat_pos", 5.0)
        self.v_sat_neg = _get_float_param(params, "v_sat_neg", 0.0)
        self.hysteresis = _get_float_param(params, "hysteresis", 0.05)


class PulseVoltageSource(Dipole):
    """Source de tension impulsionnelle / horloge périodique."""

    def __init__(
        self,
        dipole_id: int,
        node_a,
        node_b,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "PulseVoltageSource",
        v_initial: float = 0.0,
        v_pulsed: float = 5.0,
        delay: float = 0.0,
        rise_time: float = 1e-6,
        fall_time: float = 1e-6,
        pulse_width: float = 0.5e-3,
        period: float = 1e-3,
    ) -> None:
        super().__init__(dipole_id, name, node_a, node_b, x, y, rotation)
        self.v_initial = float(v_initial)
        self.v_pulsed = float(v_pulsed)
        self.delay = float(delay)
        self.rise_time = max(1e-12, float(rise_time))
        self.fall_time = max(1e-12, float(fall_time))
        self.pulse_width = float(pulse_width)
        self.period = max(1e-12, float(period))

    def get_value_at_time(self, t: float) -> float:
        """Calcule la tension instantanée au temps t."""
        if t < self.delay:
            return self.v_initial
        t_rel = (t - self.delay) % self.period
        if t_rel < self.rise_time:
            return self.v_initial + (self.v_pulsed - self.v_initial) * (t_rel / self.rise_time)
        elif t_rel < self.rise_time + self.pulse_width:
            return self.v_pulsed
        elif t_rel < self.rise_time + self.pulse_width + self.fall_time:
            frac = (t_rel - self.rise_time - self.pulse_width) / self.fall_time
            return self.v_pulsed + (self.v_initial - self.v_pulsed) * frac
        else:
            return self.v_initial

    def get_params(self) -> dict[str, Any]:
        return {
            "v_initial": self.v_initial,
            "v_pulsed": self.v_pulsed,
            "delay": self.delay,
            "rise_time": self.rise_time,
            "fall_time": self.fall_time,
            "pulse_width": self.pulse_width,
            "period": self.period,
        }

    def set_params(self, params: dict[str, Any]) -> None:
        self.v_initial = _get_float_param(params, "v_initial", 0.0)
        self.v_pulsed = _get_float_param(params, "v_pulsed", 5.0)
        self.delay = _get_float_param(params, "delay", 0.0)
        self.rise_time = max(1e-12, _get_float_param(params, "rise_time", 1e-6))
        self.fall_time = max(1e-12, _get_float_param(params, "fall_time", 1e-6))
        self.pulse_width = _get_float_param(params, "pulse_width", 0.5e-3)
        self.period = max(1e-12, _get_float_param(params, "period", 1e-3))


class LogicGate(Component):
    """Porte logique combinatoire idéale (AND, OR, NOT, NAND, NOR, XOR)."""

    def __init__(
        self,
        dipole_id: int,
        *nodes,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "LogicGate",
        gate_type: str = "AND",
        v_high: float = 5.0,
        v_threshold: float = 2.5,
        r_out: float = 50.0,
    ) -> None:
        super().__init__(dipole_id, name, *nodes, x=x, y=y, rotation=rotation)
        self.gate_type = str(gate_type).upper()
        self.v_high = float(v_high)
        self.v_threshold = float(v_threshold)
        self.r_out = float(r_out)

    def get_terminal_offsets(self) -> list[tuple[float, float]]:
        if self.gate_type == "NOT":
            return [(-30.0, 0.0), (30.0, 0.0)]
        return [(-30.0, -10.0), (-30.0, 10.0), (30.0, 0.0)]

    @property
    def node_in_a(self):
        return self.nodes[0] if len(self.nodes) > 0 else None

    @property
    def node_in_b(self):
        return self.nodes[1] if len(self.nodes) > 1 else None

    @property
    def node_out(self):
        return self.nodes[-1] if len(self.nodes) > 0 else None

    @property
    def node_a(self):
        return self.node_in_a

    @property
    def node_b(self):
        return self.node_in_b

    @property
    def node_c(self):
        return self.node_out

    def evaluate_output_voltage(self, va: float | None = None, vb: float | None = None) -> float:
        """Évalue l'état logique de sortie et retourne la tension cible."""
        if va is None:
            va = self.node_in_a.potential if self.node_in_a else 0.0
        in_a = bool(va >= self.v_threshold)

        if self.gate_type == "NOT":
            out_bool = not in_a
        else:
            if vb is None:
                vb = self.node_in_b.potential if self.node_in_b else 0.0
            in_b = bool(vb >= self.v_threshold)
            if self.gate_type == "AND":
                out_bool = in_a and in_b
            elif self.gate_type == "OR":
                out_bool = in_a or in_b
            elif self.gate_type == "NAND":
                out_bool = not (in_a and in_b)
            elif self.gate_type == "NOR":
                out_bool = not (in_a or in_b)
            elif self.gate_type == "XOR":
                out_bool = in_a != in_b
            else:
                out_bool = False

        return self.v_high if out_bool else 0.0

    def get_state(self) -> str:
        return self.gate_type

    def get_state_options(self) -> list[tuple[str, str]]:
        return [
            ("AND", "ET (AND)"),
            ("OR", "OU (OR)"),
            ("NOT", "NON (NOT)"),
            ("NAND", "NON-ET (NAND)"),
            ("NOR", "NON-OU (NOR)"),
            ("XOR", "OU-Exclusif (XOR)"),
        ]

    def set_state(self, value: str) -> None:
        self.gate_type = str(value).upper()

    def get_params(self) -> dict[str, Any]:
        return {
            "gate_type": self.gate_type,
            "v_high": self.v_high,
            "v_threshold": self.v_threshold,
            "r_out": self.r_out,
        }

    def set_params(self, params: dict[str, Any]) -> None:
        self.gate_type = str(params.get("gate_type", self.gate_type)).upper()
        self.v_high = _get_float_param(params, "v_high", 5.0)
        self.v_threshold = _get_float_param(params, "v_threshold", 2.5)
        self.r_out = _get_float_param(params, "r_out", 50.0)


class LogicGateAND(LogicGate):
    def __init__(self, dipole_id: int, *nodes, **kwargs) -> None:
        super().__init__(dipole_id, *nodes, gate_type="AND", name="LogicGateAND", **kwargs)


class LogicGateOR(LogicGate):
    def __init__(self, dipole_id: int, *nodes, **kwargs) -> None:
        super().__init__(dipole_id, *nodes, gate_type="OR", name="LogicGateOR", **kwargs)


class LogicGateNOT(LogicGate):
    def __init__(self, dipole_id: int, *nodes, **kwargs) -> None:
        super().__init__(dipole_id, *nodes, gate_type="NOT", name="LogicGateNOT", **kwargs)


class LogicGateNAND(LogicGate):
    def __init__(self, dipole_id: int, *nodes, **kwargs) -> None:
        super().__init__(dipole_id, *nodes, gate_type="NAND", name="LogicGateNAND", **kwargs)


class LogicGateNOR(LogicGate):
    def __init__(self, dipole_id: int, *nodes, **kwargs) -> None:
        super().__init__(dipole_id, *nodes, gate_type="NOR", name="LogicGateNOR", **kwargs)


class LogicGateXOR(LogicGate):
    def __init__(self, dipole_id: int, *nodes, **kwargs) -> None:
        super().__init__(dipole_id, *nodes, gate_type="XOR", name="LogicGateXOR", **kwargs)


class Fuse(Dipole):
    """Fusible de protection électrique thermique."""

    def __init__(
        self,
        dipole_id: int,
        node_a,
        node_b,
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        name: str = "Fuse",
        i_nominal: float = 1.0,
        i2t_rating: float = 0.5,
        resistance_intact: float = 0.01,
        resistance_blown: float = 1e12,
        blown: bool = False,
    ) -> None:
        super().__init__(dipole_id, name, node_a, node_b, x, y, rotation)
        self.i_nominal = float(i_nominal)
        self.i2t_rating = float(i2t_rating)
        self.resistance_intact = float(resistance_intact)
        self.resistance_blown = float(resistance_blown)
        self.blown = bool(blown)
        self._energy_accumulated: float = 0.0

    @property
    def resistance(self) -> float:
        return self.resistance_blown if self.blown else self.resistance_intact

    def update_thermal_energy(self, current: float, dt: float) -> bool:
        """Met à jour l'intégrale d'énergie thermique I²t."""
        if self.blown:
            return True
        self._energy_accumulated += (current ** 2) * dt
        if self._energy_accumulated >= self.i2t_rating or abs(current) >= self.i_nominal * 5.0:
            self.blown = True
        return self.blown

    def get_state(self) -> str:
        return "blown" if self.blown else "intact"

    def get_state_options(self) -> list[tuple[str, str]]:
        return [("intact", "Intact"), ("blown", "Fondu")]

    def set_state(self, value: str) -> None:
        self.blown = str(value).lower() == "blown"

    def get_params(self) -> dict[str, Any]:
        return {
            "i_nominal": self.i_nominal,
            "i2t_rating": self.i2t_rating,
            "resistance_intact": self.resistance_intact,
            "resistance_blown": self.resistance_blown,
            "blown": self.blown,
        }

    def set_params(self, params: dict[str, Any]) -> None:
        self.i_nominal = _get_float_param(params, "i_nominal", 1.0)
        self.i2t_rating = _get_float_param(params, "i2t_rating", 0.5)
        self.resistance_intact = _get_float_param(params, "resistance_intact", 0.01)
        self.resistance_blown = _get_float_param(params, "resistance_blown", 1e12)
        if "blown" in params:
            self.blown = bool(params["blown"])


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
        "ZenerDiode",
        "LED",
        "Ammeter",
        "Voltmeter",
        "Ground",
        "OpAmp",
        "Transformer",
        "Transistor",
        "Potentiometer",
        "MOSFET",
        "MOSFET_NMOS",
        "MOSFET_PMOS",
        "Comparator",
        "PulseVoltageSource",
        "LogicGate",
        "LogicGateAND",
        "LogicGateOR",
        "LogicGateNOT",
        "LogicGateNAND",
        "LogicGateNOR",
        "LogicGateXOR",
        "Fuse",
    ]:
        component_class = globals().get(component_name)
        if isinstance(component_class, type) and issubclass(component_class, Component):
            if component_class not in (Component, Dipole, StatefulDipole):
                register_component(component_name, component_class)


_populate_component_registry()