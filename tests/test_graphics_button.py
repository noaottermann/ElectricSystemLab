import pytest
from PyQt5.QtWidgets import QApplication
from model.circuit import Circuit
from view.main_window import MainWindow


def test_graphics_toggle_button():
    """Vérifie le fonctionnement du bouton basculant le panneau de graphiques."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    circuit = Circuit()
    window = MainWindow(circuit)

    assert hasattr(window, "graphics_button")
    window.show()
    assert not window.graph_panel.isVisible()
    window.graphics_button.click()
    assert window.graph_panel.isVisible()
    window.close()
