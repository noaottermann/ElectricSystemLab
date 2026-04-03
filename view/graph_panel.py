from __future__ import annotations

from PyQt5.QtWidgets import QLabel, QTextEdit, QTabWidget, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt

import numpy as np
from typing import Optional

try:
	import matplotlib
	matplotlib.use('Qt5Agg')
	from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
	from matplotlib.figure import Figure
	MATPLOTLIB_AVAILABLE = True
except ImportError:
	MATPLOTLIB_AVAILABLE = False


class GraphPanel(QWidget):
	"""Panneau persistant affichant les resultats de simulation avec graphiques."""

	def __init__(self, parent=None) -> None:
		super().__init__(parent)
		self.setObjectName("graphPanel")

		layout = QVBoxLayout(self)
		layout.setContentsMargins(10, 8, 10, 8)
		layout.setSpacing(8)

		title = QLabel("Résultats")
		title.setObjectName("graphPanelTitle")
		layout.addWidget(title)

		self.tabs = QTabWidget()
		
		# Onglet DC
		self.dc_widget = QWidget()
		self.dc_layout = QVBoxLayout(self.dc_widget)
		self.dc_layout.setContentsMargins(0, 0, 0, 0)
		
		if MATPLOTLIB_AVAILABLE:
			self.dc_figure = Figure(figsize=(4, 3), dpi=100)
			self.dc_canvas = FigureCanvas(self.dc_figure)
			self.dc_layout.addWidget(self.dc_canvas)
		else:
			self.dc_text = QTextEdit()
			self.dc_text.setReadOnly(True)
			self.dc_layout.addWidget(self.dc_text)
		
		# Onglet Transitoire
		self.transient_widget = QWidget()
		self.transient_layout = QVBoxLayout(self.transient_widget)
		self.transient_layout.setContentsMargins(0, 0, 0, 0)
		
		if MATPLOTLIB_AVAILABLE:
			self.transient_figure = Figure(figsize=(4, 3), dpi=100)
			self.transient_canvas = FigureCanvas(self.transient_figure)
			self.transient_layout.addWidget(self.transient_canvas)
		else:
			self.transient_text = QTextEdit()
			self.transient_text.setReadOnly(True)
			self.transient_layout.addWidget(self.transient_text)
		
		self.tabs.addTab(self.dc_widget, "DC")
		self.tabs.addTab(self.transient_widget, "Transitoire")
		layout.addWidget(self.tabs, 1)

		self.clear_results()

	def clear_results(self) -> None:
		"""Reinitialise le contenu affiche."""
		if MATPLOTLIB_AVAILABLE:
			self.dc_figure.clear()
			self.dc_canvas.draw()
			self.transient_figure.clear()
			self.transient_canvas.draw()
		else:
			if hasattr(self, 'dc_text'):
				self.dc_text.setPlainText("Aucun résultat DC disponible.")
			if hasattr(self, 'transient_text'):
				self.transient_text.setPlainText("Aucun résultat transitoire disponible.")

	def set_dc_results(self, circuit) -> None:
		"""Affiche un resume des potentiels/courants apres simulation DC."""
		if circuit is None:
			if not MATPLOTLIB_AVAILABLE and hasattr(self, 'dc_text'):
				self.dc_text.setPlainText("Aucun circuit disponible.")
			return

		if MATPLOTLIB_AVAILABLE:
			self._plot_dc_results(circuit)
		else:
			self._text_dc_results(circuit)

	def _plot_dc_results(self, circuit) -> None:
		"""Affiche les resultats DC avec matplotlib."""
		self.dc_figure.clear()
		
		# Récupère les données
		nodes = sorted(circuit.nodes.values(), key=lambda n: n.id)
		node_names = [f"N{n.id}" for n in nodes]
		node_potentials = [n.potential for n in nodes]
		
		dipoles = sorted(circuit.dipoles.values(), key=lambda d: d.id)
		dipole_names = [f"D{d.id}" for d in dipoles]
		dipole_currents = [d.current for d in dipoles]
		
		# Crée la figure avec 2 subplots
		ax1 = self.dc_figure.add_subplot(211)
		ax2 = self.dc_figure.add_subplot(212)
		
		# Potentiels des nœuds
		if node_potentials:
			colors = ['#3498db' if v >= 0 else '#e74c3c' for v in node_potentials]
			ax1.bar(range(len(node_potentials)), node_potentials, color=colors, alpha=0.7)
			ax1.set_xticks(range(len(node_names)))
			ax1.set_xticklabels(node_names, fontsize=9)
			ax1.set_ylabel('Potentiel (V)', fontsize=9)
			ax1.set_title('Potentiels des Nœuds', fontsize=10, fontweight='bold')
			ax1.grid(True, alpha=0.3)
		
		# Courants des dipôles
		if dipole_currents:
			colors = ['#2ecc71' if i >= 0 else '#e67e22' for i in dipole_currents]
			ax2.bar(range(len(dipole_currents)), dipole_currents, color=colors, alpha=0.7)
			ax2.set_xticks(range(len(dipole_names)))
			ax2.set_xticklabels(dipole_names, fontsize=9)
			ax2.set_ylabel('Courant (A)', fontsize=9)
			ax2.set_title('Courants des Dipôles', fontsize=10, fontweight='bold')
			ax2.grid(True, alpha=0.3)
		
		self.dc_figure.tight_layout()
		self.dc_canvas.draw()

	def _text_dc_results(self, circuit) -> None:
		"""Affiche les resultats DC en texte (fallback sans matplotlib)."""
		lines = ["Simulation DC", "", "Noeuds (potentiels):"]
		for node in sorted(circuit.nodes.values(), key=lambda n: n.id):
			lines.append(f"- N{node.id}: {node.potential:.6g} V")

		lines.append("")
		lines.append("Dipoles (courants):")
		for dipole in sorted(circuit.dipoles.values(), key=lambda d: d.id):
			lines.append(f"- D{dipole.id} {dipole.__class__.__name__}: {dipole.current:.6g} A")

		self.dc_text.setPlainText("\n".join(lines))

	def set_transient_results(self, result: dict | None, circuit=None) -> None:
		"""Affiche les traces transitoires avec graphiques."""
		if not result:
			if not MATPLOTLIB_AVAILABLE and hasattr(self, 'transient_text'):
				self.transient_text.setPlainText("Aucun résultat transitoire disponible.")
			return

		if MATPLOTLIB_AVAILABLE:
			self._plot_transient_results(result, circuit)
		else:
			self._text_transient_results(result)

	def _plot_transient_results(self, result: dict, circuit=None) -> None:
		"""Affiche les resultats transitoires avec matplotlib."""
		self.transient_figure.clear()
		
		time_values = np.array(result.get("time", []))
		node_potentials = result.get("node_potentials", {})
		dipole_currents = result.get("dipole_currents", {})
		
		if len(time_values) == 0:
			return
		
		# Nombre de subplots: nœuds + dipôles
		num_nodes = len(node_potentials)
		num_dipoles = len(dipole_currents)
		total_plots = max(1, min(4, num_nodes + num_dipoles))  # Limité à 4 plots
		
		# Crée les subplots
		if total_plots == 1:
			axes = [self.transient_figure.add_subplot(111)]
		elif total_plots == 2:
			axes = [self.transient_figure.add_subplot(211), self.transient_figure.add_subplot(212)]
		else:
			axes = [self.transient_figure.add_subplot(221), self.transient_figure.add_subplot(222),
					self.transient_figure.add_subplot(223), self.transient_figure.add_subplot(224)]
		
		# Affiche les potentiels des nœuds
		ax_idx = 0
		for node_id in sorted(node_potentials.keys())[:2]:  # Affiche les 2 premiers nœuds
			values = np.array(node_potentials.get(node_id, []))
			if len(values) > 0:
				axes[ax_idx].plot(time_values, values, 'b-', linewidth=2, label=f'N{node_id}')
				axes[ax_idx].set_ylabel('Potentiel (V)', fontsize=9)
				axes[ax_idx].set_xlabel('Temps (s)', fontsize=9)
				axes[ax_idx].set_title(f'Potentiel du Nœud {node_id}', fontsize=10, fontweight='bold')
				axes[ax_idx].grid(True, alpha=0.3)
				axes[ax_idx].legend(loc='best', fontsize=8)
				ax_idx += 1
				if ax_idx >= len(axes):
					break
		
		# Affiche les courants des dipôles
		for dipole_id in sorted(dipole_currents.keys())[:2]:  # Affiche les 2 premiers dipôles
			values = np.array(dipole_currents.get(dipole_id, []))
			if len(values) > 0:
				axes[ax_idx].plot(time_values, values, 'g-', linewidth=2, label=f'D{dipole_id}')
				axes[ax_idx].set_ylabel('Courant (A)', fontsize=9)
				axes[ax_idx].set_xlabel('Temps (s)', fontsize=9)
				axes[ax_idx].set_title(f'Courant du Dipôle {dipole_id}', fontsize=10, fontweight='bold')
				axes[ax_idx].grid(True, alpha=0.3)
				axes[ax_idx].legend(loc='best', fontsize=8)
				ax_idx += 1
				if ax_idx >= len(axes):
					break
		
		self.transient_figure.tight_layout()
		self.transient_canvas.draw()

	def _text_transient_results(self, result: dict) -> None:
		"""Affiche les resultats transitoires en texte (fallback sans matplotlib)."""
		time_values = result.get("time", [])
		node_potentials = result.get("node_potentials", {})
		dipole_currents = result.get("dipole_currents", {})

		lines = ["Simulation transitoire", ""]
		if time_values:
			lines.append(
				f"Points: {len(time_values)} | t0={time_values[0]:.6g}s | tfin={time_values[-1]:.6g}s"
			)
		else:
			lines.append("Aucun point temporel.")

		lines.append("")
		lines.append("Noeuds (dernier point):")
		for node_id in sorted(node_potentials, key=lambda x: str(x)):
			values = node_potentials.get(node_id, [])
			if not values:
				continue
			lines.append(f"- N{node_id}: {values[-1]:.6g} V")

		lines.append("")
		lines.append("Dipoles (dernier point):")
		for dipole_id in sorted(dipole_currents, key=lambda x: str(x)):
			values = dipole_currents.get(dipole_id, [])
			if not values:
				continue
			lines.append(f"- D{dipole_id}: {values[-1]:.6g} A")

		self.transient_text.setPlainText("\n".join(lines))
		lines.append("Dipoles (dernier point):")
		for dipole_id in sorted(dipole_currents, key=lambda x: str(x)):
			values = dipole_currents.get(dipole_id, [])
			if not values:
				continue
			label = f"D{dipole_id}"
			if circuit is not None and isinstance(dipole_id, int) and dipole_id in circuit.dipoles:
				label = f"D{dipole_id} {circuit.dipoles[dipole_id].__class__.__name__}"
			lines.append(f"- {label}: {values[-1]:.6g} A")

		self.transient_text.setPlainText("\n".join(lines))
