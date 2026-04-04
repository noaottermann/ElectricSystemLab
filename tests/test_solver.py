import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from model.circuit import Circuit
from model.components import Resistor, VoltageSourceAC, VoltageSourceDC
from solver.dc_solver import DCSolver
from solver.transient_solver import TransientSolver

class TestDCSolver(unittest.TestCase):
    
    def setUp(self):
        self.circuit = Circuit()
        self.solver = DCSolver()

    def test_simple_ohm_law(self):
        """
        Source 10V + resistance 5 Ohms
        Attendu : I = U/R = 2A
        """
        n_gnd = self.circuit.create_node(0, 0, is_ground=True)
        n_pos = self.circuit.create_node(0, 100)
        source = VoltageSourceDC(self.circuit.get_next_dipole_id(), n_pos, n_gnd, dc_voltage=10.0)
        self.circuit.add_dipole(source)
        resistor = Resistor(self.circuit.get_next_dipole_id(), n_pos, n_gnd, resistance=5.0)
        self.circuit.add_dipole(resistor)

        self.solver.solve(self.circuit)
        
        self.assertAlmostEqual(n_pos.potential, 10.0, places=5)
        self.assertAlmostEqual(abs(resistor.current), 2.0, places=5)

    def test_voltage_divider(self):
        """
        Source 12V + deux resistances de 1k Ohm en serie
        Attendu : 6V au point milieu
        """
        # GND --(Src)-- N_Haut --(R1)-- N_Milieu --(R2)-- GND
        n_gnd = self.circuit.create_node(0, 0, is_ground=True)
        n_top = self.circuit.create_node(0, 10)
        n_mid = self.circuit.create_node(0, 20)
        src = VoltageSourceDC(self.circuit.get_next_dipole_id(), n_top, n_gnd, dc_voltage=12.0)
        self.circuit.add_dipole(src)
        r1 = Resistor(self.circuit.get_next_dipole_id(), n_top, n_mid, resistance=1000.0)
        self.circuit.add_dipole(r1)
        r2 = Resistor(self.circuit.get_next_dipole_id(), n_mid, n_gnd, resistance=1000.0)
        self.circuit.add_dipole(r2)
        
        self.solver.solve(self.circuit)
        
        self.assertAlmostEqual(n_mid.potential, 6.0, places=5)
        self.assertAlmostEqual(abs(r1.current), 0.006, places=5)
        self.assertAlmostEqual(abs(r2.current), 0.006, places=5)

    def test_wire_handling(self):
        """
        Verifie que le solveur fusionne les noeuds relies par un fil
        Source 5V -- fil -- resistance 10 Ohms -- GND
        """
        n_gnd = self.circuit.create_node(0, 0, is_ground=True)
        n_src = self.circuit.create_node(0, 10)
        n_res = self.circuit.create_node(10, 10)  # Noeud eloigne relie par un fil
        src = VoltageSourceDC(self.circuit.get_next_dipole_id(), n_src, n_gnd, dc_voltage=5.0)
        self.circuit.add_dipole(src)
        self.circuit.create_wire(n_src, n_res)
        res = Resistor(self.circuit.get_next_dipole_id(), n_res, n_gnd, resistance=10.0)
        self.circuit.add_dipole(res)
        
        self.solver.solve(self.circuit)
        
        self.assertAlmostEqual(n_res.potential, 5.0, places=5)
        self.assertAlmostEqual(abs(res.current), 0.5, places=5)

    def test_auto_ground_fallback(self):
        """
        Attribue automatiquement la masse si l'utilisateur oublie de la definir
        """
        n1 = self.circuit.create_node(0, 0, is_ground=False)  # Pas de masse explicite
        n2 = self.circuit.create_node(10, 0, is_ground=False)
        src = VoltageSourceDC(self.circuit.get_next_dipole_id(), n1, n2, dc_voltage=10.0)
        self.circuit.add_dipole(src)
        res = Resistor(self.circuit.get_next_dipole_id(), n1, n2, resistance=100.0)
        self.circuit.add_dipole(res)
        
        try:
            self.solver.solve(self.circuit)
        except Exception as e:
            self.fail(f"Solver failed on a floating circuit: {e}")
            
        diff = abs(n1.potential - n2.potential)
        self.assertAlmostEqual(diff, 10.0, places=5)


class TestTransientSolver(unittest.TestCase):
    def setUp(self):
        self.circuit = Circuit()
        self.solver = TransientSolver()

    def test_transient_dc_resistive_trace(self):
        n_gnd = self.circuit.create_node(0, 0, is_ground=True)
        n_pos = self.circuit.create_node(0, 100)
        source = VoltageSourceDC(self.circuit.get_next_dipole_id(), n_pos, n_gnd, dc_voltage=10.0)
        self.circuit.add_dipole(source)
        resistor = Resistor(self.circuit.get_next_dipole_id(), n_pos, n_gnd, resistance=5.0)
        self.circuit.add_dipole(resistor)

        result = self.solver.solve(self.circuit, duration=0.01, time_step=0.005)

        self.assertEqual(result["time"], [0.0, 0.005, 0.01])
        self.assertIn(resistor.id, result["dipole_voltages"])
        self.assertEqual(len(result["dipole_voltages"][resistor.id]), 3)
        self.assertAlmostEqual(result["dipole_voltages"][resistor.id][-1], 10.0, places=5)
        self.assertAlmostEqual(abs(result["dipole_currents"][resistor.id][-1]), 2.0, places=5)

    def test_transient_ac_source_changes_over_time(self):
        n_gnd = self.circuit.create_node(0, 0, is_ground=True)
        n_pos = self.circuit.create_node(0, 100)
        source = VoltageSourceAC(
            self.circuit.get_next_dipole_id(),
            n_pos,
            n_gnd,
            amplitude=10.0,
            frequency=1.0,
            phase=0.0,
            offset=0.0,
        )
        self.circuit.add_dipole(source)
        resistor = Resistor(self.circuit.get_next_dipole_id(), n_pos, n_gnd, resistance=10.0)
        self.circuit.add_dipole(resistor)

        result = self.solver.solve(self.circuit, duration=0.5, time_step=0.25)
        voltages = result["dipole_voltages"][resistor.id]

        self.assertEqual(result["time"], [0.0, 0.25, 0.5])
        self.assertAlmostEqual(voltages[0], 0.0, places=5)
        self.assertAlmostEqual(voltages[1], 10.0, places=5)
        self.assertAlmostEqual(voltages[2], 0.0, places=5)
        self.assertAlmostEqual(result["dipole_currents"][resistor.id][1], 1.0, places=5)

    def test_transient_invalid_step(self):
        n1 = self.circuit.create_node(0, 0, is_ground=True)
        n2 = self.circuit.create_node(20, 0)
        self.circuit.add_dipole(VoltageSourceDC(self.circuit.get_next_dipole_id(), n2, n1, dc_voltage=5.0))
        self.circuit.add_dipole(Resistor(self.circuit.get_next_dipole_id(), n2, n1, resistance=10.0))

        with self.assertRaises(ValueError):
            self.solver.solve(self.circuit, duration=0.1, time_step=0.0)

if __name__ == '__main__':
    unittest.main()