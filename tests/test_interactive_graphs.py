#!/usr/bin/env python3
"""
Démonstration des contrôles interactifs du GraphPanel.
"""

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QTextEdit
from PyQt5.QtCore import Qt

from model.circuit import Circuit
from model.components import Resistor, VoltageSourceDC, Capacitor
from view.graphs_panel import GraphPanel, MATPLOTLIB_AVAILABLE

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Crée un circuit de test
    circuit = Circuit()
    n0 = circuit.add_node("N0", is_ground=True)
    n1 = circuit.add_node("N1")
    n2 = circuit.add_node("N2")
    
    # Ajoute des composants
    vsrc = circuit.add_dipole(VoltageSourceDC(10), n0, n1, "V1")
    r1 = circuit.add_dipole(Resistor(1000), n1, n2, "R1")
    r2 = circuit.add_dipole(Resistor(1000), n2, n0, "R2")
    c1 = circuit.add_dipole(Capacitor(1e-6), n1, n2, "C1")
    
    # Simule un résultat DC
    n0.potential = 0.0
    n1.potential = 10.0
    n2.potential = 5.0
    vsrc.current = 0.005
    r1.current = 0.005
    r2.current = 0.005
    c1.current = 0.0
    
    # Simule un résultat transitoire
    import numpy as np
    time_points = np.linspace(0, 1, 100)
    transient_result = {
        "time": time_points,
        "node_potentials": {
            "N1": 10.0 * (1 - np.exp(-time_points * 2)),
            "N2": 5.0 * (1 - np.exp(-time_points * 2)),
        },
        "dipole_currents": {
            "V1": 0.005 * np.exp(-time_points * 2),
            "R1": 0.005 * np.exp(-time_points * 2),
            "R2": 0.005 * np.exp(-time_points * 2),
            "C1": 0.01 * np.exp(-time_points * 2),
        }
    }
    
    # Crée la fenêtre de test
    window = QMainWindow()
    window.setWindowTitle("GraphPanel - Interactive Controls Demo")
    window.setGeometry(100, 100, 600, 700)
    
    central_widget = QWidget()
    layout = QVBoxLayout(central_widget)
    
    # Titre
    title = QLabel("=== Démonstration des Contrôles Interactifs ===")
    title.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
    layout.addWidget(title)
    
    # Instructions
    instructions_text = """
Nouvelles Fonctionnalités:

1. 📊 Sélection Interactive (Onglet Transitoire)
   • Checkboxes pour chaque nœud (N0, N1, N2...)
   • Checkboxes pour chaque dipôle (D0, D1...)
   • Tous cochés par défaut
   • Les graphiques se mettent à jour instantanément

2. 🔍 Toolbar Zoom/Pan
   • Bouton Home : Réinitialiser la vue
   • Bouton Back/Forward : Navigation historique
   • Zoom : Sélectionner une région
   • Pan : Déplacer avec la souris
   • Save : Exporter en PNG/PDF

3. 📈 Graphiques Adaptatifs
   • Nombre de courbes = nœuds sélectionnés + dipôles sélectionnés
   • Layout automatique (1, 2 ou 4 graphiques)
   • Chaque courbe a titre, légende et grille

Instructions:
1. Regarder le panel de droite
2. Cocher/décocher les nœuds et dipôles
3. Observer comment le graphique se met à jour
4. Utiliser la toolbar pour zoomer (clic sur 🔍 puis région)
5. Pan avec 🖱️ pour déplacer
6. Save (💾) pour exporter en PNG
    """
    
    instructions = QTextEdit()
    instructions.setPlainText(instructions_text)
    instructions.setReadOnly(True)
    instructions.setMaximumHeight(300)
    layout.addWidget(instructions)
    
    # Panel graphique
    graph_panel = GraphPanel()
    layout.addWidget(graph_panel, 1)
    
    window.setCentralWidget(central_widget)
    window.show()
    
    # Affiche les résultats
    print("\n✅ GraphPanel Interactif Créé")
    print("=" * 50)
    print(f"Matplotlib disponible: {MATPLOTLIB_AVAILABLE}")
    print(f"Nœuds du circuit: N0 (ground), N1, N2")
    print(f"Dipôles: V1, R1, R2, C1")
    print("=" * 50)
    print("\nTest DC:")
    graph_panel.set_dc_results(circuit)
    print("✓ Résultats DC affichés")
    
    print("\nTest Transitoire:")
    graph_panel.set_transient_results(transient_result, circuit)
    print("✓ Résultats Transitoires affichés")
    print("  - Checkboxes créées pour chaque nœud/dipôle")
    print("  - Tous les éléments cochés par défaut")
    print("  - Graphiques affichés dynamiquement")
    
    print("\n💡 Testez les fonctionnalités:")
    print("  1. Décochez des checkboxes pour voir les graphiques se mettre à jour")
    print("  2. Utilisez la toolbar pour zoomer/pan")
    print("  3. Cliquez 'Save' pour exporter en image")
    
    sys.exit(app.exec_())
