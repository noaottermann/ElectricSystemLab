import sys
import pytest
from PyQt5.QtWidgets import QApplication, QGraphicsScene, QGraphicsView
from PyQt5.QtGui import QPainter, QImage, QPixmap
from PyQt5.QtCore import Qt, QPointF

from model.circuit import Circuit
from model.components import (
    Ammeter,
    Capacitor,
    Comparator,
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
    LogicGateNOT,
    LogicGateOR,
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
    VoltageSource,
    VoltageSourceAC,
    VoltageSourceDC,
    Voltmeter,
    ZenerDiode,
)
from view.component_item import (
    AmmeterItem,
    CapacitorItem,
    ComparatorItem,
    ComponentItem,
    CurrentSourceItem,
    DiodeItem,
    FuseItem,
    GroundItem,
    InductorItem,
    LedItem,
    LogicGateItem,
    MosfetItem,
    OpAmpItem,
    PotentiometerItem,
    PulseVoltageSourceItem,
    ResistorItem,
    SwitchItem,
    TransformerItem,
    TransistorItem,
    VoltageSourceItem,
    VoltmeterItem,
    ZenerDiodeItem,
    create_component_item,
)
from view.wire_item import WireItem
from view.node_item import NodeItem
from view.canvas.canvas_scene import CircuitScene


def _get_qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_all_component_items_instantiation_and_rendering():
    """Teste le rendu graphique paint() de tous les types d'items de composants."""
    _get_qapp()
    img = QImage(200, 200, QImage.Format_ARGB32)
    painter = QPainter(img)

    circuit = Circuit()
    n1 = circuit.create_node(-30, 0)
    n2 = circuit.create_node(30, 0)
    n3 = circuit.create_node(0, 30)
    n4 = circuit.create_node(0, -30)
    n5 = circuit.create_node(0, 0)

    components_to_test = [
        Resistor(1, n1, n2, resistance=100.0),
        Capacitor(2, n1, n2, capacitance=1e-6),
        Inductor(3, n1, n2, inductance=1e-3),
        Switch(4, n1, n2, state="closed"),
        Switch(5, n1, n2, state="open"),
        VoltageSourceDC(6, n1, n2, dc_voltage=5.0),
        VoltageSourceAC(7, n1, n2, amplitude=10.0, frequency=50.0),
        CurrentSourceDC(8, n1, n2, dc_current=1.0),
        CurrentSourceAC(9, n1, n2, amplitude=2.0, frequency=60.0),
        PulseVoltageSource(10, n1, n2, v_initial=0, v_pulsed=5),
        Diode(11, n1, n2),
        LED(12, n1, n2),
        ZenerDiode(13, n1, n2, zener_voltage=5.1),
        Voltmeter(14, n1, n2),
        Ammeter(15, n1, n2),
        Ground(16, n1),
        Fuse(17, n1, n2),
        Potentiometer(18, n1, n3, n2),
        Transformer(19, n1, n2, n3, n4),
        OpAmp(20, n1, n2, n3, mode="3_terminal"),
        OpAmp(21, n1, n2, n3, n4, n5, mode="5_terminal"),
        Comparator(22, n1, n2, n3),
        Transistor(23, n1, n2, n3, transistor_type="NPN"),
        Transistor(24, n1, n2, n3, transistor_type="PNP"),
        MOSFET_NMOS(25, n1, n2, n3),
        MOSFET_PMOS(26, n1, n2, n3),
        LogicGate(27, n1, n2, n3, gate_type="AND"),
        LogicGate(28, n1, n2, n3, gate_type="OR"),
        LogicGate(29, n1, n2, gate_type="NOT"),
        LogicGate(30, n1, n2, n3, gate_type="NAND"),
        LogicGate(31, n1, n2, n3, gate_type="NOR"),
        LogicGate(32, n1, n2, n3, gate_type="XOR"),
    ]

    from PyQt5.QtWidgets import QStyleOptionGraphicsItem
    opt = QStyleOptionGraphicsItem()

    for comp in components_to_test:
        circuit.add_dipole(comp)
        item = create_component_item(comp)
        assert item is not None
        assert item.boundingRect().isValid()

        # Test rotation et update_model_nodes
        for rot in (0, 90, 180, 270):
            item.setRotation(rot)
            item.update_model_nodes()

        # Dessin du symbole
        item.paint(painter, opt)
        item.draw_symbol(painter)
        item.draw_labels(painter)
        item.get_value_text()

    painter.end()


def test_diode_item_state_variations():
    """Teste le composant Diode polymorphe dans ses états diode standard, zener et led."""
    _get_qapp()
    img = QImage(100, 100, QImage.Format_ARGB32)
    painter = QPainter(img)

    circuit = Circuit()
    n1 = circuit.create_node(-30, 0)
    n2 = circuit.create_node(30, 0)
    diode = Diode(1, n1, n2)
    item = DiodeItem(diode)

    for state in ("diode", "zener", "led"):
        diode.set_state(state)
        item.draw_symbol(painter)
        text = item.get_value_text()
        assert isinstance(text, str)

    painter.end()


def test_meter_items_readout_badges():
    """Teste l'affichage digital LCD live pour Voltmètre et Ampèremètre."""
    _get_qapp()
    img = QImage(100, 100, QImage.Format_ARGB32)
    painter = QPainter(img)

    circuit = Circuit()
    n1 = circuit.create_node(-30, 0)
    n2 = circuit.create_node(30, 0)
    n1.potential = 3.305
    n2.potential = 0.0

    vm = Voltmeter(1, n1, n2)
    vm_item = VoltmeterItem(vm)
    vm_item.draw_symbol(painter)

    am = Ammeter(2, n1, n2)
    am.current = 0.045
    am_item = AmmeterItem(am)
    am_item.draw_symbol(painter)

    painter.end()


def test_wire_item_thickness_and_geometry():
    """Teste WireItem et son adaptation dynamique d'épaisseur de trait."""
    from model.circuit import Wire
    _get_qapp()
    scene = CircuitScene(Circuit())
    n1 = scene.model.create_node(0, 0)
    n2 = scene.model.create_node(100, 100)

    node_item1 = NodeItem(n1)
    node_item2 = NodeItem(n2)
    scene.addItem(node_item1)
    scene.addItem(node_item2)

    wire = Wire(1, n1, n2)
    wire_item = WireItem(wire)
    scene.addItem(wire_item)

    # Vérification épaisseur par défaut
    wire_item.refresh_geometry()
    assert wire_item.pen().width() == 2

    # Modification épaisseur fils dans la scène
    scene.wire_width = 4
    wire_item.refresh_geometry()
    assert wire_item.pen().width() == 4


def test_canvas_scene_multi_terminal_snapping_and_nodes():
    """Teste la détection et magnétisation de composants à 3 bornes et plus."""
    _get_qapp()
    circuit = Circuit()
    n1 = circuit.create_node(0, 0)
    n2 = circuit.create_node(0, 0)
    n3 = circuit.create_node(0, 0)
    scene = CircuitScene(circuit)

    # Ajout d'un transistor BJT (3 bornes)
    t = Transistor(1, n1, n2, n3, transistor_type="NPN")
    item = create_component_item(t)
    scene.addItem(item)
    item.setPos(100.0, 100.0)
    item.update_model_nodes()

    assert len(t.nodes) == 3
    for node in t.nodes:
        assert node is not None

    # Déplacement et mise à jour
    item.setPos(200.0, 200.0)
    item.update_model_nodes()
    for node in t.nodes:
        assert node.position[0] > 150.0


def test_main_window_state_buttons_and_render_state_icon():
    """Teste le rendu des icônes d'état et le widget de sélection avec boutons illustrés."""
    _get_qapp()
    from view.main_window import MainWindow
    window = MainWindow(Circuit())

    # Test _render_state_icon pour Transistor (NPN et PNP)
    t = Transistor(1, None, None, None, transistor_type="NPN")
    icon_npn = window._render_state_icon(t, "NPN")
    assert not icon_npn.isNull()
    icon_pnp = window._render_state_icon(t, "PNP")
    assert not icon_pnp.isNull()

    # Test _render_state_icon pour Diode (diode, zener, led)
    d = Diode(2, None, None)
    icon_diode = window._render_state_icon(d, "diode")
    assert not icon_diode.isNull()
    icon_zener = window._render_state_icon(d, "zener")
    assert not icon_zener.isNull()
    icon_led = window._render_state_icon(d, "led")
    assert not icon_led.isNull()

    # Test _create_state_selector_widget
    changed_state = []
    widget, get_state = window._create_state_selector_widget(
        d, [("diode", "Diode standard"), ("zener", "Diode Zener"), ("led", "DEL / LED")],
        "diode", on_change=lambda s: changed_state.append(s)
    )
    assert widget is not None
    assert get_state() == "diode"

    window.close()


def test_main_window_options_handlers():
    """Teste les actions du menu Options ajoutées pour personnalisation."""
    _get_qapp()
    from view.main_window import MainWindow
    from PyQt5.QtWidgets import QInputDialog
    window = MainWindow(Circuit())

    # Toggle terminal dots
    action_dots = window.custom_actions["action_show_terminal_dots"]
    action_dots.setChecked(False)
    window.on_toggle_show_terminal_dots()
    assert window.scene.show_terminal_dots is False

    action_dots.setChecked(True)
    window.on_toggle_show_terminal_dots()
    assert window.scene.show_terminal_dots is True

    # Snap tolerance, wire width, export resolution with mocked input
    orig_getInt = QInputDialog.getInt
    QInputDialog.getInt = staticmethod(lambda *args, **kwargs: (5, True))
    try:
        window.on_set_snap_tolerance()
        assert window.scene.snap_tolerance == 5

        window.on_set_wire_width()
        assert window.scene.wire_width == 5

        window.on_set_export_resolution()
        assert window.export_resolution_scale == 5
    finally:
        QInputDialog.getInt = orig_getInt

    window.close()
