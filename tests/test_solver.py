import unittest
import json
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from model.circuit import Circuit
from model.components import Resistor, VoltageSourceDC, Capacitor
from model.node import Node
from model.wire import Wire

class TestCircuitModel(unittest.TestCase):
    
    def setUp(self):
        """S'exécute avant chaque test : on part d'un circuit vide"""
        self.circuit = Circuit()

    def test_node_creation(self):
        """Test la création et le stockage des noeuds"""
        n1 = self.circuit.create_node(10, 20, is_ground=True)
        n2 = self.circuit.create_node(30, 40)

        # Vérifie que les noeuds sont bien dans le dictionnaire
        self.assertEqual(len(self.circuit.nodes), 2)
        self.assertTrue(n1.is_ground)
        self.assertFalse(n2.is_ground)
        
        # Vérifie les positions
        self.assertEqual(n1.position, (10, 20))
        
        # Vérifie l'incrémentation des ID
        self.assertNotEqual(n1.id, n2.id)

    def test_dipole_connection(self):
        """Test l'ajout d'un dipôle entre deux noeuds"""
        n1 = self.circuit.create_node(0, 0)
        n2 = self.circuit.create_node(100, 0)
        uid = self.circuit.get_next_dipole_id()
        resistor = Resistor(uid, n1, n2, resistance=220.0)
        
        self.circuit.add_dipole(resistor)

        self.assertEqual(len(self.circuit.dipoles), 1)
        self.assertEqual(resistor.resistance, 220.0)
        self.assertIn(resistor, n1.connected_dipoles)
        self.assertIn(resistor, n2.connected_dipoles)

    def test_wire_creation(self):
        """Test la création de fils"""
        n1 = self.circuit.create_node(0, 0)
        n2 = self.circuit.create_node(50, 50)
        
        wire = self.circuit.create_wire(n1, n2)
        
        self.assertEqual(len(self.circuit.wires), 1)
        self.assertEqual(wire.node_a, n1)
        self.assertEqual(wire.node_b, n2)

    def test_json_serialization(self):
        """Test la sauvegarde et chargement"""
        n1 = self.circuit.create_node(0, 0, is_ground=True)
        n2 = self.circuit.create_node(0, 100)

        src = VoltageSourceDC(self.circuit.get_next_dipole_id(), n1, n2, dc_voltage=12.0)
        self.circuit.add_dipole(src)
        
        r1 = Resistor(self.circuit.get_next_dipole_id(), n2, n1, resistance=1000.0)
        self.circuit.add_dipole(r1)
        
        json_output = self.circuit.to_json()
        print(json_output)
        
        new_circuit = Circuit()
        comp_classes = {
            "Resistor": Resistor,
            "VoltageSourceDC": VoltageSourceDC
        }
        new_circuit.load_from_json(json_output, comp_classes)

        self.assertEqual(len(new_circuit.nodes), 2)
        self.assertEqual(len(new_circuit.dipoles), 2)
        
        loaded_resistor = None
        loaded_source = None
        
        for d in new_circuit.dipoles.values():
            if isinstance(d, Resistor):
                loaded_resistor = d
            elif isinstance(d, VoltageSourceDC):
                loaded_source = d
                
        self.assertIsNotNone(loaded_resistor)
        if loaded_resistor:
            self.assertEqual(loaded_resistor.resistance, 1000.0)
        
        self.assertIsNotNone(loaded_source)
        if loaded_source:
            self.assertEqual(loaded_source.dc_voltage, 12.0)
        
        has_ground = any(n.is_ground for n in new_circuit.nodes.values())
        self.assertTrue(has_ground)

if __name__ == '__main__':
    unittest.main()