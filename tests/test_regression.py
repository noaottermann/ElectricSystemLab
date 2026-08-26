import pytest
from model.circuit import Circuit
from model.components import (
    Resistor, VoltageSourceDC, VoltageSourceAC,
    CurrentSourceDC, CurrentSourceAC, Ground
)

def test_remove_node_cleans_connections():
    """Vérifie que la suppression d'un nœud détruit également les fils et composants connectés."""
    circuit = Circuit()
    n1 = circuit.create_node(0, 0)
    n2 = circuit.create_node(100, 0)

    # Créer un fil entre les deux
    wire = circuit.create_wire(n1, n2)
    assert wire.id in circuit.wires

    # Créer un composant rattaché aux nœuds
    resistor = Resistor(1, n1, n2)
    circuit.add_dipole(resistor)
    assert resistor.id in circuit.dipoles

    # Supprimer le nœud n1
    circuit.remove_node(n1.id)

    # Le nœud n1 ne doit plus exister
    assert n1.id not in circuit.nodes

    # Le fil connecté à n1 doit avoir été supprimé
    assert wire.id not in circuit.wires

    # La résistance connectée à n1 doit avoir été supprimée
    assert resistor.id not in circuit.dipoles


def test_unified_sources_polymorphism():
    """Vérifie que les classes VoltageSourceDC/AC héritent bien de VoltageSource et gèrent les états."""
    from model.components import VoltageSource, CurrentSource

    # Tension
    v_dc = VoltageSourceDC(1, None, None, dc_voltage=7.5)
    v_ac = VoltageSourceAC(2, None, None, amplitude=12.0)

    assert isinstance(v_dc, VoltageSource)
    assert isinstance(v_ac, VoltageSource)

    # Vérifier les états via get_state()
    assert v_dc.get_state() == "dc"
    assert v_ac.get_state() == "ac"

    assert v_dc.get_dc_value() == 7.5
    assert v_ac.get_dc_value() == 0.0  # L'analyse AC ne doit pas renvoyer de DC value en mode AC
    assert v_ac.amplitude == 12.0

    # Courant
    i_dc = CurrentSourceDC(3, None, None, dc_current=1.5)
    i_ac = CurrentSourceAC(4, None, None, amplitude=5.0)

    assert isinstance(i_dc, CurrentSource)
    assert isinstance(i_ac, CurrentSource)

    # Vérifier les états via get_state()
    assert i_dc.get_state() == "dc"
    assert i_ac.get_state() == "ac"

    assert i_dc.get_dc_value() == 1.5
    assert i_ac.get_dc_value() == 0.0


def test_ground_disconnect():
    """Vérifie que déconnecter un Ground remet is_ground du nœud à False."""
    circuit = Circuit()
    node = circuit.create_node(0, 0)

    ground = Ground(1, node)
    circuit.add_dipole(ground)

    assert node.is_ground is True

    # Supprimer ou déconnecter le ground
    circuit.remove_dipole(ground.id)

    assert node.is_ground is False


def test_control_current_from_state_fixed():
    """Vérifie que _control_current_from_state retourne 0.0 par défaut pour les types inconnus."""
    from solver.base_solver import BaseSolver

    solver = BaseSolver()
    resistor = Resistor(1, None, None)

    val = solver._control_current_from_state(
        None, resistor, {}, {}, 0, [], {}
    )
    assert val == 0.0


def test_update_dependent_source_current_fixed():
    """Vérifie la valeur de retour de update_dependent_source_current pour les sources contrôlées."""
    from solver.utils import MatrixStamper
    from model.components import (
        CurrentControlledCurrentSource, VoltageSourceDC
    )

    circuit = Circuit()

    # Créer une source de contrôle de tension
    v_source = VoltageSourceDC(1, None, None, dc_voltage=5.0)
    circuit.add_dipole(v_source)

    # Créer une CCCS contrôlée par notre source
    cccs = CurrentControlledCurrentSource(2, None, None)
    cccs.control_dipole_id = v_source.id
    cccs.gain = 3.0

    # Mettre à jour avec un vecteur d'état simulant 2A passant par la source de tension
    voltage_source_indices = {v_source.id: 0}
    state_vector = [2.0]

    val = MatrixStamper.update_dependent_source_current(
        cccs,
        circuit,
        None,
        None,
        None,
        state_vector,
        voltage_source_indices
    )

    # I_control = -2A, Gain = 3.0 -> I_cccs = -6.0 A
    assert val == -6.0
