"""
Gestionnaire d'édition des composants et fils pour le canvas.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from model.components import (
    Ammeter,
    Capacitor,
    CurrentControlledCurrentSource,
    CurrentControlledVoltageSource,
    CurrentSource,
    CurrentSourceAC,
    CurrentSourceDC,
    Diode,
    Ground,
    Inductor,
    LED,
    OpAmp,
    Resistor,
    Switch,
    Transformer,
    Transistor,
    Voltmeter,
    VoltageControlledCurrentSource,
    VoltageControlledVoltageSource,
    VoltageSource,
    VoltageSourceAC,
    VoltageSourceDC,
)

if TYPE_CHECKING:
    from model.circuit import Circuit


class EditingManager:
    """Gère la création, modification et suppression des dipôles et fils."""

    COMPONENT_CLASSES = {
        "Resistor": Resistor,
        "VoltageSource": VoltageSource,
        "VoltageSourceDC": VoltageSourceDC,
        "VoltageSourceAC": VoltageSourceAC,
        "CurrentSource": CurrentSource,
        "CurrentSourceDC": CurrentSourceDC,
        "CurrentSourceAC": CurrentSourceAC,
        "VoltageControlledCurrentSource": VoltageControlledCurrentSource,
        "CurrentControlledCurrentSource": CurrentControlledCurrentSource,
        "VoltageControlledVoltageSource": VoltageControlledVoltageSource,
        "CurrentControlledVoltageSource": CurrentControlledVoltageSource,
        "Capacitor": Capacitor,
        "Inductor": Inductor,
        "Diode": Diode,
        "LED": LED,
        "Switch": Switch,
        "Ammeter": Ammeter,
        "Voltmeter": Voltmeter,
        "Ground": Ground,
        "Transformer": Transformer,
        "Transistor": Transistor,
        "OpAmp": OpAmp,
    }

    TOOL_TO_CLASS = {
        "resistor": Resistor,
        "source": VoltageSourceDC,
        "source_dc": VoltageSourceDC,
        "source_ac": VoltageSourceAC,
        "current_source": CurrentSourceDC,
        "current_source_dc": CurrentSourceDC,
        "current_source_ac": CurrentSourceAC,
        "vccs": VoltageControlledCurrentSource,
        "cccs": CurrentControlledCurrentSource,
        "vcvs": VoltageControlledVoltageSource,
        "ccvs": CurrentControlledVoltageSource,
        "capacitor": Capacitor,
        "inductor": Inductor,
        "diode": Diode,
        "led": LED,
        "switch": Switch,
        "ammeter": Ammeter,
        "voltmeter": Voltmeter,
        "ground": Ground,
        "transformer": Transformer,
        "transistor": Transistor,
        "opamp": OpAmp,
    }

    def __init__(self, circuit: Optional[Circuit] = None) -> None:
        self.circuit = circuit

    def create_component_by_tool(
        self,
        tool_name: str,
        x: float,
        y: float,
        rotation: float = 0.0,
    ) -> Optional[Any]:
        """Instancie un composant à partir de son nom d'outil."""
        if self.circuit is None:
            return None

        cls = self.TOOL_TO_CLASS.get(tool_name.lower())
        if cls is None:
            return None

        dipole_id = self.circuit.get_next_dipole_id()
        n_a = self.circuit.create_node(x - 30.0, y)
        n_b = self.circuit.create_node(x + 30.0, y)

        if cls is Ground:
            n_a.is_ground = True
            comp = Ground(dipole_id, n_a, x=x, y=y, rotation=rotation)
        elif cls is OpAmp:
            n_c = self.circuit.create_node(x + 30.0, y)
            comp = OpAmp(dipole_id, n_a, n_b, n_c, x=x, y=y, rotation=rotation)
        elif cls is Transformer:
            n_c = self.circuit.create_node(x - 30.0, y + 20.0)
            n_d = self.circuit.create_node(x + 30.0, y + 20.0)
            comp = Transformer(dipole_id, n_a, n_b, n_c, n_d, x=x, y=y, rotation=rotation)
        elif cls is Transistor:
            n_c = self.circuit.create_node(x, y + 30.0)
            comp = Transistor(dipole_id, n_a, n_b, n_c, x=x, y=y, rotation=rotation)
        else:
            comp = cls(dipole_id, n_a, n_b, x=x, y=y, rotation=rotation)

        self.circuit.add_dipole(comp)
        return comp
