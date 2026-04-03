from __future__ import annotations

from PyQt5.QtWidgets import QLabel, QTextEdit, QTabWidget, QVBoxLayout, QWidget


class GraphPanel(QWidget):
	"""Panneau persistant affichant les resultats de simulation."""

	def __init__(self, parent=None) -> None:
		super().__init__(parent)
		self.setObjectName("graphPanel")

		layout = QVBoxLayout(self)
		layout.setContentsMargins(10, 8, 10, 8)
		layout.setSpacing(8)

		title = QLabel("Resultats")
		title.setObjectName("graphPanelTitle")
		layout.addWidget(title)

		self.tabs = QTabWidget()
		self.dc_text = QTextEdit()
		self.dc_text.setReadOnly(True)
		self.transient_text = QTextEdit()
		self.transient_text.setReadOnly(True)
		self.tabs.addTab(self.dc_text, "DC")
		self.tabs.addTab(self.transient_text, "Transitoire")
		layout.addWidget(self.tabs, 1)

		self.clear_results()

	def clear_results(self) -> None:
		"""Reinitialise le contenu affiche."""
		self.dc_text.setPlainText("Aucun resultat DC disponible.")
		self.transient_text.setPlainText("Aucun resultat transitoire disponible.")

	def set_dc_results(self, circuit) -> None:
		"""Affiche un resume des potentiels/courants apres simulation DC."""
		if circuit is None:
			self.dc_text.setPlainText("Aucun circuit disponible.")
			return

		lines = ["Simulation DC", "", "Noeuds (potentiels):"]
		for node in sorted(circuit.nodes.values(), key=lambda n: n.id):
			lines.append(f"- N{node.id}: {node.potential:.6g} V")

		lines.append("")
		lines.append("Dipoles (courants):")
		for dipole in sorted(circuit.dipoles.values(), key=lambda d: d.id):
			lines.append(f"- D{dipole.id} {dipole.__class__.__name__}: {dipole.current:.6g} A")

		self.dc_text.setPlainText("\n".join(lines))

	def set_transient_results(self, result: dict | None, circuit=None) -> None:
		"""Affiche un resume des traces transitoires."""
		if not result:
			self.transient_text.setPlainText("Aucun resultat transitoire disponible.")
			return

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
			label = f"D{dipole_id}"
			if circuit is not None and isinstance(dipole_id, int) and dipole_id in circuit.dipoles:
				label = f"D{dipole_id} {circuit.dipoles[dipole_id].__class__.__name__}"
			lines.append(f"- {label}: {values[-1]:.6g} A")

		self.transient_text.setPlainText("\n".join(lines))
