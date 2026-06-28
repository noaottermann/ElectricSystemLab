import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from model.circuit import Circuit
from model.components import (
    Capacitor,
    CurrentControlledVoltageSource,
    CurrentControlledCurrentSource,
    CurrentSourceAC,
    CurrentSourceDC,
    Diode,
    Inductor,
    LED,
    Resistor,
    VoltageControlledVoltageSource,
    VoltageControlledCurrentSource,
    VoltageSourceAC,
    VoltageSourceDC,
)
from solver.dc_solver import DCSolver
from solver.transient_solver import TransientSolver

class TestDCSolver(unittest.TestCase):
    
    def setUp(self):
        self.circuit = Circuit()
        self.solver = DCSolver()

    def test_simple_ohm_law(self):
        """
        Source 10V + résistance 5 Ohms
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
        Verifie que le solveur fusionne les noeuds reliés par un fil
        Source 5V -- fil -- résistance 10 Ohms -- GND
        """
        n_gnd = self.circuit.create_node(0, 0, is_ground=True)
        n_src = self.circuit.create_node(0, 10)
        n_res = self.circuit.create_node(10, 10)
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
        Attribue automatiquement la masse si l'utilisateur oublie de la définir
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

    def test_current_source_dc_sets_node_voltage(self):
        n_gnd = self.circuit.create_node(0, 0, is_ground=True)
        n_pos = self.circuit.create_node(0, 100)
        source = CurrentSourceDC(self.circuit.get_next_dipole_id(), n_gnd, n_pos, dc_current=0.001)
        self.circuit.add_dipole(source)
        resistor = Resistor(self.circuit.get_next_dipole_id(), n_pos, n_gnd, resistance=1000.0)
        self.circuit.add_dipole(resistor)

        self.solver.solve(self.circuit)

        self.assertAlmostEqual(n_pos.potential, 1.0, places=4)
        self.assertAlmostEqual(source.current, 0.001, places=6)

    def test_vccs_current_matches_control_voltage(self):
        n_gnd = self.circuit.create_node(0, 0, is_ground=True)
        n_ctrl = self.circuit.create_node(0, 100)
        n_out = self.circuit.create_node(80, 100)

        ctrl_source = VoltageSourceDC(self.circuit.get_next_dipole_id(), n_ctrl, n_gnd, dc_voltage=2.0)
        self.circuit.add_dipole(ctrl_source)
        vccs = VoltageControlledCurrentSource(
            self.circuit.get_next_dipole_id(),
            n_out,
            n_gnd,
            transconductance=1e-3,
            control_dipole_id=ctrl_source.id,
        )
        self.circuit.add_dipole(vccs)
        self.circuit.add_dipole(Resistor(self.circuit.get_next_dipole_id(), n_out, n_gnd, resistance=1000.0))

        self.solver.solve(self.circuit)

        self.assertAlmostEqual(vccs.current, 0.002, places=5)

    def test_cccs_current_matches_control_current(self):
        n_gnd = self.circuit.create_node(0, 0, is_ground=True)
        n_ctrl = self.circuit.create_node(0, 100)
        n_out = self.circuit.create_node(80, 100)

        ctrl_source = VoltageSourceDC(self.circuit.get_next_dipole_id(), n_ctrl, n_gnd, dc_voltage=1.0)
        self.circuit.add_dipole(ctrl_source)
        self.circuit.add_dipole(Resistor(self.circuit.get_next_dipole_id(), n_ctrl, n_gnd, resistance=1000.0))

        cccs = CurrentControlledCurrentSource(
            self.circuit.get_next_dipole_id(),
            n_out,
            n_gnd,
            gain=2.0,
            control_dipole_id=ctrl_source.id,
        )
        self.circuit.add_dipole(cccs)
        self.circuit.add_dipole(Resistor(self.circuit.get_next_dipole_id(), n_out, n_gnd, resistance=1000.0))

        self.solver.solve(self.circuit)

        self.assertAlmostEqual(cccs.current, 2.0 * ctrl_source.current, places=5)

    def test_cccs_can_use_resistor_control_current(self):
        n_gnd = self.circuit.create_node(0, 0, is_ground=True)
        n_ctrl = self.circuit.create_node(0, 100)
        n_out = self.circuit.create_node(80, 100)

        self.circuit.add_dipole(VoltageSourceDC(self.circuit.get_next_dipole_id(), n_ctrl, n_gnd, dc_voltage=10.0))
        control_resistor = Resistor(self.circuit.get_next_dipole_id(), n_ctrl, n_gnd, resistance=1000.0)
        self.circuit.add_dipole(control_resistor)

        cccs = CurrentControlledCurrentSource(
            self.circuit.get_next_dipole_id(),
            n_out,
            n_gnd,
            gain=2.0,
            control_dipole_id=control_resistor.id,
        )
        self.circuit.add_dipole(cccs)
        self.circuit.add_dipole(Resistor(self.circuit.get_next_dipole_id(), n_out, n_gnd, resistance=1000.0))

        self.solver.solve(self.circuit)

        self.assertAlmostEqual(n_out.potential, 20.0, places=4)

    def test_vcvs_sets_output_voltage(self):
        n_gnd = self.circuit.create_node(0, 0, is_ground=True)
        n_ctrl = self.circuit.create_node(0, 100)
        n_out = self.circuit.create_node(80, 100)

        ctrl_source = VoltageSourceDC(self.circuit.get_next_dipole_id(), n_ctrl, n_gnd, dc_voltage=2.0)
        self.circuit.add_dipole(ctrl_source)
        self.circuit.add_dipole(Resistor(self.circuit.get_next_dipole_id(), n_ctrl, n_gnd, resistance=1000.0))

        vcvs = VoltageControlledVoltageSource(
            self.circuit.get_next_dipole_id(),
            n_out,
            n_gnd,
            gain=3.0,
            control_dipole_id=ctrl_source.id,
        )
        self.circuit.add_dipole(vcvs)
        self.circuit.add_dipole(Resistor(self.circuit.get_next_dipole_id(), n_out, n_gnd, resistance=1000.0))

        self.solver.solve(self.circuit)

        self.assertAlmostEqual(n_out.potential, 6.0, places=4)

    def test_ccvs_sets_output_voltage_from_control_current(self):
        n_gnd = self.circuit.create_node(0, 0, is_ground=True)
        n_ctrl = self.circuit.create_node(0, 100)
        n_out = self.circuit.create_node(80, 100)

        self.circuit.add_dipole(VoltageSourceDC(self.circuit.get_next_dipole_id(), n_ctrl, n_gnd, dc_voltage=10.0))
        control_resistor = Resistor(self.circuit.get_next_dipole_id(), n_ctrl, n_gnd, resistance=1000.0)
        self.circuit.add_dipole(control_resistor)

        ccvs = CurrentControlledVoltageSource(
            self.circuit.get_next_dipole_id(),
            n_out,
            n_gnd,
            transresistance=50.0,
            control_dipole_id=control_resistor.id,
        )
        self.circuit.add_dipole(ccvs)
        self.circuit.add_dipole(Resistor(self.circuit.get_next_dipole_id(), n_out, n_gnd, resistance=1000.0))

        self.solver.solve(self.circuit)

        self.assertAlmostEqual(n_out.potential, 0.5, places=4)

    def test_diode_forward_conduction(self):
        n_gnd = self.circuit.create_node(0, 0, is_ground=True)
        n_pos = self.circuit.create_node(0, 100)
        n_out = self.circuit.create_node(80, 100)

        source = VoltageSourceDC(self.circuit.get_next_dipole_id(), n_pos, n_gnd, dc_voltage=1.0)
        self.circuit.add_dipole(source)
        self.circuit.add_dipole(Resistor(self.circuit.get_next_dipole_id(), n_pos, n_out, resistance=1000.0))
        diode = Diode(self.circuit.get_next_dipole_id(), n_out, n_gnd)
        self.circuit.add_dipole(diode)

        self.solver.solve(self.circuit)

        self.assertGreater(diode.current, 0.0)
        self.assertGreater(diode.voltage, 0.3)
        self.assertLess(diode.voltage, 0.9)

    def test_led_forward_conduction(self):
        n_gnd = self.circuit.create_node(0, 0, is_ground=True)
        n_pos = self.circuit.create_node(0, 100)
        n_out = self.circuit.create_node(80, 100)

        source = VoltageSourceDC(self.circuit.get_next_dipole_id(), n_pos, n_gnd, dc_voltage=3.0)
        self.circuit.add_dipole(source)
        self.circuit.add_dipole(Resistor(self.circuit.get_next_dipole_id(), n_pos, n_out, resistance=220.0))
        led = LED(self.circuit.get_next_dipole_id(), n_out, n_gnd)
        self.circuit.add_dipole(led)

        self.solver.solve(self.circuit)

        self.assertGreater(led.current, 0.0)
        self.assertGreater(led.voltage, 1.2)
        self.assertLess(led.voltage, 3.0)


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

    def test_transient_rc_response_is_dynamic(self):
        n_gnd = self.circuit.create_node(0, 0, is_ground=True)
        n_src = self.circuit.create_node(0, 100)
        n_out = self.circuit.create_node(80, 100)

        source = VoltageSourceDC(self.circuit.get_next_dipole_id(), n_src, n_gnd, dc_voltage=10.0)
        self.circuit.add_dipole(source)
        resistor = Resistor(self.circuit.get_next_dipole_id(), n_src, n_out, resistance=1000.0)
        self.circuit.add_dipole(resistor)
        capacitor = Capacitor(self.circuit.get_next_dipole_id(), n_out, n_gnd, capacitance=1e-6)
        self.circuit.add_dipole(capacitor)

        result = self.solver.solve(self.circuit, duration=0.003, time_step=0.0001)
        v_cap = result["dipole_voltages"][capacitor.id]

        self.assertGreater(v_cap[-1], v_cap[0])
        self.assertGreater(v_cap[-1], 0.0)
        self.assertLess(v_cap[-1], 10.1)

    def test_transient_rl_response_is_dynamic(self):
        n_gnd = self.circuit.create_node(0, 0, is_ground=True)
        n_src = self.circuit.create_node(0, 100)
        n_mid = self.circuit.create_node(80, 100)

        source = VoltageSourceDC(self.circuit.get_next_dipole_id(), n_src, n_gnd, dc_voltage=10.0)
        self.circuit.add_dipole(source)
        inductor = Inductor(self.circuit.get_next_dipole_id(), n_src, n_mid, inductance=1e-3)
        self.circuit.add_dipole(inductor)
        resistor = Resistor(self.circuit.get_next_dipole_id(), n_mid, n_gnd, resistance=10.0)
        self.circuit.add_dipole(resistor)

        result = self.solver.solve(self.circuit, duration=0.005, time_step=0.0001)
        i_l = result["dipole_currents"][inductor.id]

        self.assertGreater(i_l[-1], i_l[0])
        self.assertGreater(i_l[-1], 0.0)

    def test_transient_time_grid_with_start_time_offset(self):
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

        result = self.solver.solve(self.circuit, duration=0.25, time_step=0.25, start_time=0.25)

        self.assertEqual(result["time"], [0.25, 0.5])
        self.assertAlmostEqual(result["dipole_voltages"][resistor.id][0], 10.0, places=5)
        self.assertAlmostEqual(result["dipole_voltages"][resistor.id][1], 0.0, places=5)

    def test_transient_current_source_ac_trace(self):
        n_gnd = self.circuit.create_node(0, 0, is_ground=True)
        n_pos = self.circuit.create_node(0, 100)
        source = CurrentSourceAC(
            self.circuit.get_next_dipole_id(),
            n_gnd,
            n_pos,
            amplitude=0.001,
            frequency=1.0,
            phase=0.0,
            offset=0.0,
        )
        self.circuit.add_dipole(source)
        resistor = Resistor(self.circuit.get_next_dipole_id(), n_pos, n_gnd, resistance=1000.0)
        self.circuit.add_dipole(resistor)

        result = self.solver.solve(self.circuit, duration=0.5, time_step=0.25)

        self.assertEqual(result["time"], [0.0, 0.25, 0.5])
        self.assertAlmostEqual(result["dipole_currents"][source.id][0], 0.0, places=6)
        self.assertAlmostEqual(result["dipole_currents"][source.id][1], 0.001, places=6)
        self.assertAlmostEqual(result["dipole_currents"][source.id][2], 0.0, places=6)
        self.assertAlmostEqual(result["dipole_voltages"][resistor.id][1], 1.0, places=4)

if __name__ == '__main__':
    unittest.main()