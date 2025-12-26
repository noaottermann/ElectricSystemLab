import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from model.circuit import Circuit
from model.components import Resistor, VoltageSourceDC
from model.node import Node, Wire
from solver.dc_solver import DCSolver

class TestDCSolver(unittest.TestCase):
    
    def setUp(self):
        self.circuit = Circuit()
        self.solver = DCSolver()

    def test_simple_ohm_law(self):
        """
        Source 10V + Résistance 5 Ohms
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
         12V + 2 Résistances de 1kOhm en série
        Attendu : 6V au point milieu
        """
        # GND --(Src)-- N_Top --(R1)-- N_Mid --(R2)-- GND
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
        Vérifie que le solveur fusionne bien les noeuds reliés par un fil
        Source 5V -- Fil -- Résistance 10 Ohm -- GND
        """
        n_gnd = self.circuit.create_node(0, 0, is_ground=True)
        n_src = self.circuit.create_node(0, 10)
        n_res = self.circuit.create_node(10, 10) # Noeud physiquement distant mais relié par fil
        src = VoltageSourceDC(self.circuit.get_next_dipole_id(), n_src, n_gnd, dc_voltage=5.0)
        self.circuit.add_dipole(src)
        wire = self.circuit.create_wire(n_src, n_res)
        res = Resistor(self.circuit.get_next_dipole_id(), n_res, n_gnd, resistance=10.0)
        self.circuit.add_dipole(res)
        
        self.solver.solve(self.circuit)
        
        self.assertAlmostEqual(n_res.potential, 5.0, places=5)
        self.assertAlmostEqual(abs(res.current), 0.5, places=5)

    def test_auto_ground_fallback(self):
        """
        Si l'utilisateur oublie de mettre une masse
        """
        n1 = self.circuit.create_node(0, 0, is_ground=False) # Pas de masse explicite
        n2 = self.circuit.create_node(10, 0, is_ground=False)
        src = VoltageSourceDC(self.circuit.get_next_dipole_id(), n1, n2, dc_voltage=10.0)
        res = Resistor(self.circuit.get_next_dipole_id(), n1, n2, resistance=100.0)
        self.circuit.add_dipole(src)
        self.circuit.add_dipole(res)
        
        try:
            self.solver.solve(self.circuit)
        except Exception as e:
            self.fail(f"Le solveur a planté sur un circuit flottant : {e}")
            
        diff = abs(n1.potential - n2.potential)
        self.assertAlmostEqual(diff, 10.0, places=5)

if __name__ == '__main__':
    unittest.main()