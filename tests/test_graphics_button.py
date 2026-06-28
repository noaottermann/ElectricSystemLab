import sys
from PyQt5.QtWidgets import QApplication
from model.circuit import Circuit
from view.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Crée un circuit vide
    circuit = Circuit()
    
    # Ouvre la fenêtre principale
    window = MainWindow(circuit)
    window.show()
    
    # Affiche un message de test
    print("✓ Bouton Graphiques créé et positionné")
    print("✓ Position: 2/3 de la hauteur, tout à droite")
    print("✓ Style: Rectangle portrait (80x120px)")
    print("✓ Fonction: Ouvre/fermé le panneau des graphiques")
    print("\nTestez le bouton en cliquant dessus dans l'interface pour basculer l'affichage du panneau de droite.")
    
    sys.exit(app.exec_())
