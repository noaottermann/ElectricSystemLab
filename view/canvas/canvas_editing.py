"""
Gestionnaire d'édition des composants et fils pour le canvas.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from model.components import (
    Ammeter,
    Capacitor,
    Comparator,
    CurrentControlledCurrentSource,
    CurrentControlledVoltageSource,
    CurrentSource,
    CurrentSourceAC,
    CurrentSourceDC,
    Diode,
    Fuse,
    Ground,
    Inductor,
    LED,
    LogicGate,
    LogicGateAND,
    LogicGateNAND,
    LogicGateNOR,
    LogicGateNOT,
    LogicGateOR,
    LogicGateXOR,
    MOSFET,
    MOSFET_NMOS,
    MOSFET_PMOS,
    OpAmp,
    Potentiometer,
    PulseVoltageSource,
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
    ZenerDiode,
)

if TYPE_CHECKING:
    from model.circuit import Circuit


class EditingManager:
    """Gère la création, modification et suppression des dipôles et fils."""

    COMPONENT_CLASSES = {
        "Resistor": Resistor,
        "Potentiometer": Potentiometer,
        "VoltageSource": VoltageSource,
        "VoltageSourceDC": VoltageSourceDC,
        "VoltageSourceAC": VoltageSourceAC,
        "PulseVoltageSource": PulseVoltageSource,
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
        "ZenerDiode": ZenerDiode,
        "LED": LED,
        "Switch": Switch,
        "Ammeter": Ammeter,
        "Voltmeter": Voltmeter,
        "Ground": Ground,
        "Transformer": Transformer,
        "Transistor": Transistor,
        "MOSFET": MOSFET,
        "MOSFET_NMOS": MOSFET_NMOS,
        "MOSFET_PMOS": MOSFET_PMOS,
        "OpAmp": OpAmp,
        "Comparator": Comparator,
        "Fuse": Fuse,
        "LogicGate": LogicGate,
        "LogicGateAND": LogicGateAND,
        "LogicGateOR": LogicGateOR,
        "LogicGateNOT": LogicGateNOT,
        "LogicGateNAND": LogicGateNAND,
        "LogicGateNOR": LogicGateNOR,
        "LogicGateXOR": LogicGateXOR,
    }

    TOOL_TO_CLASS = {
        "resistor": Resistor,
        "potentiometer": Potentiometer,
        "source": VoltageSourceDC,
        "source_dc": VoltageSourceDC,
        "source_ac": VoltageSourceAC,
        "pulse_source": PulseVoltageSource,
        "pulse_voltage_source": PulseVoltageSource,
        "current_source": CurrentSourceDC,
        "current_source_dc": CurrentSourceDC,
        "current_source_ac": CurrentSourceAC,
        "vccs": VoltageControlledCurrentSource,
        "source_vccs": VoltageControlledCurrentSource,
        "cccs": CurrentControlledCurrentSource,
        "source_cccs": CurrentControlledCurrentSource,
        "vcvs": VoltageControlledVoltageSource,
        "source_vcvs": VoltageControlledVoltageSource,
        "ccvs": CurrentControlledVoltageSource,
        "source_ccvs": CurrentControlledVoltageSource,
        "capacitor": Capacitor,
        "inductor": Inductor,
        "diode": Diode,
        "zener_diode": ZenerDiode,
        "led": LED,
        "switch": Switch,
        "ammeter": Ammeter,
        "voltmeter": Voltmeter,
        "ground": Ground,
        "transformer": Transformer,
        "transistor": Transistor,
        "mosfet": MOSFET,
        "mosfet_nmos": MOSFET_NMOS,
        "mosfet_pmos": MOSFET_PMOS,
        "opamp": OpAmp,
        "comparator": Comparator,
        "fuse": Fuse,
        "logic_gate": LogicGate,
        "logic_and": LogicGateAND,
        "logic_or": LogicGateOR,
        "logic_not": LogicGateNOT,
        "logic_nand": LogicGateNAND,
        "logic_nor": LogicGateNOR,
        "logic_xor": LogicGateXOR,
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

        if cls is Ground:
            n_a = self.circuit.create_node(x, y - 15.0)
            n_a.is_ground = True
            comp = Ground(dipole_id, n_a, x=x, y=y, rotation=rotation)
        elif cls in (OpAmp, Comparator):
            n_a = self.circuit.create_node(x - 30.0, y - 12.0)
            n_b = self.circuit.create_node(x - 30.0, y + 12.0)
            n_c = self.circuit.create_node(x + 30.0, y)
            comp = cls(dipole_id, n_a, n_b, n_c, x=x, y=y, rotation=rotation)
        elif cls is Transformer:
            n_a = self.circuit.create_node(x - 30.0, y - 15.0)
            n_b = self.circuit.create_node(x - 30.0, y + 15.0)
            n_c = self.circuit.create_node(x + 30.0, y - 15.0)
            n_d = self.circuit.create_node(x + 30.0, y + 15.0)
            comp = Transformer(dipole_id, n_a, n_b, n_c, n_d, x=x, y=y, rotation=rotation)
        elif cls in (Transistor, MOSFET, MOSFET_NMOS, MOSFET_PMOS):
            n_a = self.circuit.create_node(x + 15.0, y - 25.0)
            n_b = self.circuit.create_node(x - 30.0, y)
            n_c = self.circuit.create_node(x + 15.0, y + 25.0)
            comp = cls(dipole_id, n_a, n_b, n_c, x=x, y=y, rotation=rotation)
        elif cls is Potentiometer:
            n_a = self.circuit.create_node(x - 30.0, y)
            n_w = self.circuit.create_node(x, y - 20.0)
            n_b = self.circuit.create_node(x + 30.0, y)
            comp = Potentiometer(dipole_id, n_a, n_w, n_b, x=x, y=y, rotation=rotation)
        elif issubclass(cls, LogicGate):
            if cls is LogicGateNOT:
                n_a = self.circuit.create_node(x - 30.0, y)
                n_out = self.circuit.create_node(x + 30.0, y)
                comp = cls(dipole_id, n_a, n_out, x=x, y=y, rotation=rotation)
            else:
                n_a = self.circuit.create_node(x - 30.0, y - 10.0)
                n_b = self.circuit.create_node(x - 30.0, y + 10.0)
                n_out = self.circuit.create_node(x + 30.0, y)
                comp = cls(dipole_id, n_a, n_b, n_out, x=x, y=y, rotation=rotation)
        else:
            n_a = self.circuit.create_node(x - 30.0, y)
            n_b = self.circuit.create_node(x + 30.0, y)
            comp = cls(dipole_id, n_a, n_b, x=x, y=y, rotation=rotation)

        self.circuit.add_dipole(comp)
        return comp
