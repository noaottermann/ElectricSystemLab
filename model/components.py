import math
from .dipole import Dipole

class Resistor(Dipole):
    """
    Résistance idéale
    """
    def __init__(self, dipole_id, node_a, node_b, x=0.0, y=0.0, rotation=0.0, name="Resistor", resistance=1000.0):
        super().__init__(dipole_id, "Resistor", node_a, node_b, x, y, rotation)
        self.resistance = float(resistance)

    def get_params(self):
        return {"resistance": self.resistance}

    def set_params(self, params):
        self.resistance = float(params.get("resistance", 1000.0))


class Capacitor(Dipole):
    """
    Condensateur idéal
    """
    def __init__(self, dipole_id, node_a, node_b, x=0.0, y=0.0, rotation=0.0, name="Capacitor", capacitance=1e-6):
        super().__init__(dipole_id, "Capacitor", node_a, node_b, x, y, rotation)
        self.capacitance = float(capacitance)

    def get_params(self):
        return {"capacitance": self.capacitance}

    def set_params(self, params):
        self.capacitance = float(params.get("capacitance", 1e-6))


class Inductor(Dipole):
    """
    Bobine (Inductance) idéale
    """
    def __init__(self, dipole_id, node_a, node_b, x=0.0, y=0.0, rotation=0.0, name="Inductor", inductance=1e-3):
        super().__init__(dipole_id, "Inductor", node_a, node_b, x, y, rotation)
        self.inductance = float(inductance)

    def get_params(self):
        return {"inductance": self.inductance}

    def set_params(self, params):
        self.inductance = float(params.get("inductance", 1e-3))

class VoltageSourceDC(Dipole):
    """
    Source de tension continue idéale (Générateur DC)
    """
    def __init__(self, dipole_id, node_a, node_b, x=0.0, y=0.0, rotation=0.0, name="VoltageSourceDC", dc_voltage=5.0):
        super().__init__(dipole_id, "DC Source", node_a, node_b, x, y, rotation)
        self.dc_voltage = float(dc_voltage)

    def get_params(self):
        return {"dc_voltage": self.dc_voltage}

    def set_params(self, params):
        self.dc_voltage = float(params.get("dc_voltage", 5.0))


class VoltageSourceAC(Dipole):
    """
    Source de tension alternative sinusoïdale
    """
    def __init__(self, dipole_id, node_a, node_b, x=0.0, y=0.0, rotation=0.0, name="VoltageSourceAC", 
                 amplitude=10.0, frequency=50.0, phase=0.0, offset=0.0):
        super().__init__(dipole_id, "AC Source", node_a, node_b, x, y, rotation)
        self.amplitude = float(amplitude)
        self.frequency = float(frequency)
        self.phase = float(phase)
        self.offset = float(offset)

    def get_value_at_time(self, t):
        omega = 2 * math.pi * self.frequency
        phi = math.radians(self.phase)
        return self.offset + self.amplitude * math.sin(omega * t + phi)

    def get_params(self):
        return {
            "amplitude": self.amplitude,
            "frequency": self.frequency,
            "phase": self.phase,
            "offset": self.offset
        }

    def set_params(self, params):
        self.amplitude = float(params.get("amplitude", 10.0))
        self.frequency = float(params.get("frequency", 50.0))
        self.phase = float(params.get("phase", 0.0))
        self.offset = float(params.get("offset", 0.0))