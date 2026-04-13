"""Point d'entree de l'application"""

import sys
import platform

from PyQt5.QtWidgets import QApplication

from model.circuit import Circuit
from view.main_window import MainWindow
from utils.translator import Translator
from utils.assets import get_logo_icon, logo_exists

#TODO certaines clés de traduction sont dupliquées

def _setup_windows_icon():
    """Configure l'icône pour Windows (taskbar et autres)."""
    if platform.system() == "Windows":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Nodal.Application")
        except Exception:
            pass

def main():
    """Cree l'application Qt et affiche la fenetre principale"""
    _setup_windows_icon()
    
    app = QApplication(sys.argv)
    
    app.setApplicationName("Nodal")
    app.setApplicationVersion("1.0.0")
    
    if logo_exists():
        logo_icon = get_logo_icon()
        app.setWindowIcon(logo_icon)

    Translator.load_language("fr")

    circuit = Circuit()
    
    window = MainWindow(model=circuit)
    
    window.showMaximized()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()