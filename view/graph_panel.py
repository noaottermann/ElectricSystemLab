from __future__ import annotations

from PyQt5.QtGui import QPainter, QPen, QColor
from PyQt5.QtWidgets import (
	QLabel, QTextEdit, QTabWidget, QVBoxLayout, QWidget,
	QCheckBox, QHBoxLayout, QScrollArea, QGroupBox, QPushButton
)
from PyQt5.QtCore import Qt

import numpy as np
from typing import Optional

try:
	import matplotlib
	matplotlib.use('Qt5Agg')
	from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
	from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
	from matplotlib.figure import Figure
	MATPLOTLIB_AVAILABLE = True
except ImportError:
	MATPLOTLIB_AVAILABLE = False


def _rms(values: np.ndarray) -> float:
	"""Retourne la valeur efficace d'un signal."""
	if values.size == 0:
		return 0.0
	return float(np.sqrt(np.mean(np.square(values))))


def _nearest_index(time_values: np.ndarray, target_time: float) -> int:
	"""Retourne l'indice du temps le plus proche de la cible."""
	if time_values.size == 0:
		return 0
	return int(np.abs(time_values - target_time).argmin())


def _trace_value_at_time(time_values: np.ndarray, values: np.ndarray, target_time: float) -> tuple[int, float, float]:
	"""Retourne l'échantillon le plus proche d'un instant cible."""
	if time_values.size == 0 or values.size == 0:
		return 0, 0.0, 0.0
	index = _nearest_index(time_values, target_time)
	return index, float(time_values[index]), float(values[index])


def _pad_range(min_value: float, max_value: float) -> tuple[float, float]:
	"""Élargit une plage pour éviter les axes dégénérés."""
	if min_value == max_value:
		margin = 1.0 if min_value == 0 else abs(min_value) * 0.1
		return min_value - margin, max_value + margin
	span = max_value - min_value
	margin = span * 0.08
	return min_value - margin, max_value + margin


class TimeSeriesPlotWidget(QWidget):
	"""Rendu de courbes temporelles sans dépendre de matplotlib."""

	def __init__(self, parent=None) -> None:
		super().__init__(parent)
		self.series = []
		self.cursor_time = None
		self.setMinimumHeight(220)

	def set_series(self, series: list[dict], cursor_time: float | None = None) -> None:
		self.series = series
		self.cursor_time = cursor_time
		self.update()

	def paintEvent(self, event) -> None:
		super().paintEvent(event)
		painter = QPainter(self)
		painter.setRenderHint(QPainter.Antialiasing)
		painter.fillRect(self.rect(), QColor("white"))

		if not self.series:
			painter.setPen(QPen(QColor("#555555")))
			painter.drawText(self.rect(), Qt.AlignCenter, "Aucune courbe disponible.")
			return

		margin_left = 56
		margin_top = 18
		margin_right = 18
		margin_bottom = 34
		plot_rect = self.rect().adjusted(margin_left, margin_top, -margin_right, -margin_bottom)
		if plot_rect.width() <= 0 or plot_rect.height() <= 0:
			return

		all_x = np.concatenate([np.asarray(entry["x"], dtype=float) for entry in self.series if len(entry.get("x", []))])
		all_y = np.concatenate([np.asarray(entry["y"], dtype=float) for entry in self.series if len(entry.get("y", []))])
		if all_x.size == 0 or all_y.size == 0:
			return

		x_min, x_max = _pad_range(float(all_x.min()), float(all_x.max()))
		y_min, y_max = _pad_range(float(all_y.min()), float(all_y.max()))

		def map_x(value: float) -> float:
			if x_max == x_min:
				return float(plot_rect.left())
			return plot_rect.left() + (value - x_min) * plot_rect.width() / (x_max - x_min)

		def map_y(value: float) -> float:
			if y_max == y_min:
				return float(plot_rect.center().y())
			return plot_rect.bottom() - (value - y_min) * plot_rect.height() / (y_max - y_min)

		painter.setPen(QPen(QColor("#777777"), 1))
		painter.drawRect(plot_rect)

		# Axes simples
		painter.drawLine(plot_rect.left(), plot_rect.bottom(), plot_rect.right(), plot_rect.bottom())
		painter.drawLine(plot_rect.left(), plot_rect.top(), plot_rect.left(), plot_rect.bottom())

		# Grille légère
		painter.setPen(QPen(QColor("#e0e0e0"), 1, Qt.DashLine))
		for step in range(1, 5):
			x = plot_rect.left() + plot_rect.width() * step / 5.0
			painter.drawLine(int(x), plot_rect.top(), int(x), plot_rect.bottom())
			y = plot_rect.top() + plot_rect.height() * step / 5.0
			painter.drawLine(plot_rect.left(), int(y), plot_rect.right(), int(y))

		# Courbes
		colors = [QColor("#2563eb"), QColor("#16a34a"), QColor("#dc2626"), QColor("#7c3aed"), QColor("#ea580c")]
		for index, entry in enumerate(self.series):
			x_values = np.asarray(entry.get("x", []), dtype=float)
			y_values = np.asarray(entry.get("y", []), dtype=float)
			if x_values.size == 0 or y_values.size == 0:
				continue
			painter.setPen(QPen(colors[index % len(colors)], 2))
			points = []
			for x_value, y_value in zip(x_values, y_values):
				points.append((map_x(float(x_value)), map_y(float(y_value))))
			for i in range(1, len(points)):
				p1 = points[i - 1]
				p2 = points[i]
				painter.drawLine(int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1]))

		# Repère temporel
		if self.cursor_time is not None:
			cursor_x = map_x(float(self.cursor_time))
			painter.setPen(QPen(QColor("#6b7280"), 1, Qt.DashLine))
			painter.drawLine(int(cursor_x), plot_rect.top(), int(cursor_x), plot_rect.bottom())

		# Légende
		legend_x = plot_rect.right() - 150
		legend_y = plot_rect.top() + 8
		painter.setPen(QPen(QColor("#111827")))
		for index, entry in enumerate(self.series):
			label = str(entry.get("label", f"Trace {index + 1}"))
			color = colors[index % len(colors)]
			painter.setPen(QPen(color, 3))
			painter.drawLine(legend_x, legend_y + 8, legend_x + 18, legend_y + 8)
			painter.setPen(QPen(QColor("#111827")))
			painter.drawText(legend_x + 24, legend_y + 12, label)
			legend_y += 18

		# Étiquettes d'axes
		painter.setPen(QPen(QColor("#374151")))
		painter.drawText(plot_rect.center().x() - 18, self.height() - 8, "Temps (s)")
		painter.save()
		painter.translate(12, plot_rect.center().y() + 32)
		painter.rotate(-90)
		painter.drawText(0, 0, self.series[0].get("unit_label", "Valeur"))
		painter.restore()

		painter.end()


class GraphPanel(QWidget):
	"""Panneau persistant avec graphiques et controles interactifs."""

	def __init__(self, parent=None) -> None:
		super().__init__(parent)
		self.setObjectName("graphPanel")
		
		# État pour le filtrage transient
		self.selected_nodes = set()
		self.selected_dipoles = set()
		self.last_transient_result = None
		self.last_circuit = None
		self.hover_time = None
		self.cursor_time = None

		layout = QVBoxLayout(self)
		layout.setContentsMargins(10, 8, 10, 8)
		layout.setSpacing(8)

		title = QLabel("Résultats & Graphiques")
		title.setObjectName("graphPanelTitle")
		layout.addWidget(title)

		self.tabs = QTabWidget()
		
		# ===== Onglet DC =====
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
		
		# ===== Onglet Transitoire =====
		self.transient_widget = QWidget()
		self.transient_layout = QVBoxLayout(self.transient_widget)
		self.transient_layout.setContentsMargins(0, 0, 0, 0)
		
		# Contrôles de sélection
		self.transient_controls = QWidget()
		self.transient_controls_layout = QVBoxLayout(self.transient_controls)
		self.transient_controls_layout.setContentsMargins(5, 5, 5, 5)
		self.transient_controls_layout.setSpacing(5)
		
		# Sélection des nœuds
		self.nodes_group = QGroupBox("Nœuds")
		self.nodes_layout = QHBoxLayout(self.nodes_group)
		self.nodes_layout.setSpacing(3)
		self.nodes_layout.setContentsMargins(5, 5, 5, 5)
		self.nodes_scroll = QScrollArea()
		self.nodes_scroll.setWidgetResizable(True)
		self.nodes_scroll.setMaximumHeight(35)
		nodes_container = QWidget()
		self.nodes_scroll.setWidget(nodes_container)
		self.nodes_container = nodes_container
		self.nodes_scroll_layout = QHBoxLayout(nodes_container)
		self.nodes_scroll_layout.setSpacing(3)
		self.nodes_scroll_layout.setContentsMargins(0, 0, 0, 0)
		self.nodes_layout.addWidget(self.nodes_scroll)
		self.nodes_select_all_button = QPushButton("Tout")
		self.nodes_select_all_button.clicked.connect(lambda: self._set_group_selection(self.nodes_scroll_layout, True))
		self.nodes_layout.addWidget(self.nodes_select_all_button)
		self.nodes_select_none_button = QPushButton("Aucun")
		self.nodes_select_none_button.clicked.connect(lambda: self._set_group_selection(self.nodes_scroll_layout, False))
		self.nodes_layout.addWidget(self.nodes_select_none_button)
		self.transient_controls_layout.addWidget(self.nodes_group)
		
		# Sélection des dipôles
		self.dipoles_group = QGroupBox("Dipôles")
		self.dipoles_layout = QHBoxLayout(self.dipoles_group)
		self.dipoles_layout.setSpacing(3)
		self.dipoles_layout.setContentsMargins(5, 5, 5, 5)
		self.dipoles_scroll = QScrollArea()
		self.dipoles_scroll.setWidgetResizable(True)
		self.dipoles_scroll.setMaximumHeight(35)
		dipoles_container = QWidget()
		self.dipoles_scroll.setWidget(dipoles_container)
		self.dipoles_container = dipoles_container
		self.dipoles_scroll_layout = QHBoxLayout(dipoles_container)
		self.dipoles_scroll_layout.setSpacing(3)
		self.dipoles_scroll_layout.setContentsMargins(0, 0, 0, 0)
		self.dipoles_layout.addWidget(self.dipoles_scroll)
		self.dipoles_select_all_button = QPushButton("Tout")
		self.dipoles_select_all_button.clicked.connect(lambda: self._set_group_selection(self.dipoles_scroll_layout, True))
		self.dipoles_layout.addWidget(self.dipoles_select_all_button)
		self.dipoles_select_none_button = QPushButton("Aucun")
		self.dipoles_select_none_button.clicked.connect(lambda: self._set_group_selection(self.dipoles_scroll_layout, False))
		self.dipoles_layout.addWidget(self.dipoles_select_none_button)
		self.transient_controls_layout.addWidget(self.dipoles_group)
		
		self.transient_layout.addWidget(self.transient_controls)
		
		# Graphique transitoire
		if MATPLOTLIB_AVAILABLE:
			self.transient_figure = Figure(figsize=(4, 3), dpi=100)
			self.transient_canvas = FigureCanvas(self.transient_figure)
			self.transient_layout.addWidget(self.transient_canvas, 1)
			self.transient_canvas.mpl_connect("motion_notify_event", self._on_plot_motion)
			self.transient_canvas.mpl_connect("button_press_event", self._on_plot_click)
			
			# Toolbar zoom/pan
			self.transient_toolbar = NavigationToolbar2QT(self.transient_canvas, self.transient_widget)
			self.transient_layout.addWidget(self.transient_toolbar)
		else:
			self.transient_plot = TimeSeriesPlotWidget()
			self.transient_layout.addWidget(self.transient_plot, 1)

		self.transient_stats_text = QTextEdit()
		self.transient_stats_text.setReadOnly(True)
		self.transient_stats_text.setMaximumHeight(130)
		self.transient_layout.addWidget(self.transient_stats_text)
		
		self.tabs.addTab(self.dc_widget, "DC")
		self.tabs.addTab(self.transient_widget, "Transitoire")
		layout.addWidget(self.tabs, 1)

		self.clear_results()

	def _create_node_checkbox(self, node_id: str) -> None:
		"""Crée une checkbox pour un nœud."""
		checkbox = QCheckBox(f"N{node_id}")
		checkbox.setChecked(True)
		checkbox.stateChanged.connect(lambda: self._on_selection_changed())
		self.nodes_scroll_layout.addWidget(checkbox)

	def _create_dipole_checkbox(self, dipole_id: str) -> None:
		"""Crée une checkbox pour un dipôle."""
		checkbox = QCheckBox(f"D{dipole_id}")
		checkbox.setChecked(True)
		checkbox.stateChanged.connect(lambda: self._on_selection_changed())
		self.dipoles_scroll_layout.addWidget(checkbox)

	def _clear_checkboxes(self) -> None:
		"""Efface toutes les checkboxes existantes."""
		while self.nodes_scroll_layout.count():
			item = self.nodes_scroll_layout.takeAt(0)
			if item and item.widget():
				item.widget().deleteLater()
		while self.dipoles_scroll_layout.count():
			item = self.dipoles_scroll_layout.takeAt(0)
			if item and item.widget():
				item.widget().deleteLater()

	def _set_group_selection(self, layout: QHBoxLayout, checked: bool) -> None:
		"""Coche/decoches toutes les checkbox d'un groupe."""
		for i in range(layout.count()):
			item = layout.itemAt(i)
			if not item or not item.widget():
				continue
			widget = item.widget()
			if isinstance(widget, QCheckBox):
				widget.blockSignals(True)
				widget.setChecked(checked)
				widget.blockSignals(False)
		self._on_selection_changed()

	def _on_plot_click(self, event) -> None:
		"""Place un curseur temporel sur clic dans un graphe transitoire."""
		if event is None or event.xdata is None:
			return
		self.cursor_time = float(event.xdata)
		if self.last_transient_result:
			self._plot_transient_results(self.last_transient_result, self.last_circuit)

	def _on_plot_motion(self, event) -> None:
		"""Met à jour le repère temporaire au survol du graphe."""
		if event is None or event.xdata is None or event.inaxes is None:
			return
		if self.cursor_time is not None:
			return
		self.hover_time = float(event.xdata)
		if self.last_transient_result:
			self._plot_transient_results(self.last_transient_result, self.last_circuit)

	def _on_selection_changed(self) -> None:
		"""Callback quand la sélection change."""
		if not self.last_transient_result:
			return
		
		# Récupère la sélection actuelle
		self.selected_nodes = set()
		self.selected_dipoles = set()
		
		for i in range(self.nodes_scroll_layout.count()):
			item = self.nodes_scroll_layout.itemAt(i)
			if item and item.widget():
				checkbox = item.widget()
				if isinstance(checkbox, QCheckBox) and checkbox.isChecked():
					node_id = checkbox.text().replace("N", "")
					self.selected_nodes.add(node_id)
		
		for i in range(self.dipoles_scroll_layout.count()):
			item = self.dipoles_scroll_layout.itemAt(i)
			if item and item.widget():
				checkbox = item.widget()
				if isinstance(checkbox, QCheckBox) and checkbox.isChecked():
					dipole_id = checkbox.text().replace("D", "")
					self.selected_dipoles.add(dipole_id)
		
		# Redessine les graphiques
		if MATPLOTLIB_AVAILABLE:
			self._plot_transient_results(self.last_transient_result, self.last_circuit)
		else:
			self._plot_transient_results_native(self.last_transient_result)
			self.transient_stats_text.setPlainText("\n".join(self._build_native_transient_summary(self.last_transient_result)))

	def clear_results(self) -> None:
		"""Reinitialise le contenu affiche."""
		self._clear_checkboxes()
		self.selected_nodes = set()
		self.selected_dipoles = set()
		self.hover_time = None
		self.cursor_time = None
		self.transient_stats_text.setPlainText("Aucune mesure disponible.")
		
		if MATPLOTLIB_AVAILABLE:
			self.dc_figure.clear()
			self.dc_canvas.draw()
			self.transient_figure.clear()
			self.transient_canvas.draw()
		else:
			if hasattr(self, 'dc_text'):
				self.dc_text.setPlainText("Aucun résultat DC disponible.")
			if hasattr(self, 'transient_plot'):
				self.transient_plot.set_series([])

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
			self._clear_checkboxes()
			if not MATPLOTLIB_AVAILABLE and hasattr(self, 'transient_plot'):
				self.transient_plot.set_series([])
			return

		# Stocke les résultats pour les mises à jour interactives
		self.last_transient_result = result
		self.last_circuit = circuit
		self.selected_nodes = set()
		self.selected_dipoles = set()

		# Crée les checkboxes de sélection
		self._clear_checkboxes()
		node_potentials = result.get("node_potentials", {})
		dipole_currents = result.get("dipole_currents", {})
		
		for node_id in sorted(node_potentials.keys()):
			self._create_node_checkbox(str(node_id))
			self.selected_nodes.add(str(node_id))
		
		for dipole_id in sorted(dipole_currents.keys()):
			self._create_dipole_checkbox(str(dipole_id))
			self.selected_dipoles.add(str(dipole_id))

		if MATPLOTLIB_AVAILABLE:
			self._plot_transient_results(result, circuit)
		else:
			self._plot_transient_results_native(result)
			self.transient_stats_text.setPlainText("\n".join(self._build_native_transient_summary(result)))

	def _build_native_transient_summary(self, result: dict) -> list[str]:
		"""Construit un résumé texte court pour le mode natif sans matplotlib."""
		time_values = np.asarray(result.get("time", []), dtype=float)
		lines = ["Simulation transitoire"]
		if time_values.size:
			lines.append(f"Points: {len(time_values)} | t0={float(time_values[0]):.6g}s | tfin={float(time_values[-1]):.6g}s")
		else:
			lines.append("Aucun point temporel.")
		lines.append("")
		lines.append("Nœuds sélectionnés: " + (", ".join(sorted(self.selected_nodes)) if self.selected_nodes else "aucun"))
		lines.append("Dipôles sélectionnés: " + (", ".join(sorted(self.selected_dipoles)) if self.selected_dipoles else "aucun"))
		cursor_time = self.cursor_time if self.cursor_time is not None else self.hover_time
		if cursor_time is not None:
			lines.append("")
			lines.append(f"Repère temporel: {cursor_time:.6g}s")
		return lines

	def _plot_transient_results_native(self, result: dict) -> None:
		"""Prépare un rendu natif Qt quand matplotlib n'est pas disponible."""
		time_values = np.asarray(result.get("time", []), dtype=float)
		node_potentials = result.get("node_potentials", {})
		dipole_currents = result.get("dipole_currents", {})
		cursor_time = self.cursor_time if self.cursor_time is not None else self.hover_time

		series = []
		for node_id in sorted(node_potentials.keys()):
			if str(node_id) not in self.selected_nodes:
				continue
			values = np.asarray(node_potentials.get(node_id, []), dtype=float)
			if values.size == 0:
				continue
			series.append({"x": time_values, "y": values, "label": f"N{node_id}", "unit_label": "Potentiel (V)"})
		for dipole_id in sorted(dipole_currents.keys()):
			if str(dipole_id) not in self.selected_dipoles:
				continue
			values = np.asarray(dipole_currents.get(dipole_id, []), dtype=float)
			if values.size == 0:
				continue
			series.append({"x": time_values, "y": values, "label": f"D{dipole_id}", "unit_label": "Courant (A)"})

		if hasattr(self, 'transient_plot'):
			self.transient_plot.set_series(series, cursor_time=cursor_time)

	def _plot_transient_results(self, result: dict, circuit=None) -> None:
		"""Affiche les resultats transitoires avec matplotlib."""
		self.transient_figure.clear()
		
		time_values = np.array(result.get("time", []))
		node_potentials = result.get("node_potentials", {})
		dipole_currents = result.get("dipole_currents", {})
		
		if len(time_values) == 0:
			return
		
		# Filtre selon la sélection
		selected_nodes = []
		for node_id in sorted(node_potentials.keys()):
			if str(node_id) in self.selected_nodes:
				values = np.array(node_potentials.get(node_id, []))
				if len(values) > 0:
					selected_nodes.append((node_id, values))
		
		selected_dipoles = []
		for dipole_id in sorted(dipole_currents.keys()):
			if str(dipole_id) in self.selected_dipoles:
				values = np.array(dipole_currents.get(dipole_id, []))
				if len(values) > 0:
					selected_dipoles.append((dipole_id, values))
		
		total_plots = len(selected_nodes) + len(selected_dipoles)
		if total_plots == 0:
			self.transient_stats_text.setPlainText("Aucune trace sélectionnée.")
			return

		cursor_time = self.cursor_time if self.cursor_time is not None else self.hover_time
		
		# Crée les subplots dynamiquement
		if total_plots == 1:
			axes = [self.transient_figure.add_subplot(111)]
		elif total_plots == 2:
			axes = [self.transient_figure.add_subplot(211), self.transient_figure.add_subplot(212)]
		elif total_plots == 3:
			axes = [self.transient_figure.add_subplot(311), self.transient_figure.add_subplot(312),
					self.transient_figure.add_subplot(313)]
		else:
			axes = [self.transient_figure.add_subplot(221), self.transient_figure.add_subplot(222),
					self.transient_figure.add_subplot(223), self.transient_figure.add_subplot(224)]
		
		ax_idx = 0
		
		# Affiche les potentiels des nœuds sélectionnés
		for node_id, values in selected_nodes:
			if ax_idx >= len(axes):
				break
			axes[ax_idx].plot(time_values, values, 'b-', linewidth=2, label=f'N{node_id}')
			if cursor_time is not None:
				axes[ax_idx].axvline(cursor_time, color="#7f8c8d", linestyle="--", linewidth=1.0)
			axes[ax_idx].set_ylabel('Potentiel (V)', fontsize=9)
			axes[ax_idx].set_xlabel('Temps (s)', fontsize=9)
			axes[ax_idx].set_title(f'Potentiel du Nœud {node_id}', fontsize=10, fontweight='bold')
			axes[ax_idx].grid(True, alpha=0.3)
			axes[ax_idx].legend(loc='best', fontsize=8)
			ax_idx += 1
		
		# Affiche les courants des dipôles sélectionnés
		for dipole_id, values in selected_dipoles:
			if ax_idx >= len(axes):
				break
			axes[ax_idx].plot(time_values, values, 'g-', linewidth=2, label=f'D{dipole_id}')
			if cursor_time is not None:
				axes[ax_idx].axvline(cursor_time, color="#7f8c8d", linestyle="--", linewidth=1.0)
			axes[ax_idx].set_ylabel('Courant (A)', fontsize=9)
			axes[ax_idx].set_xlabel('Temps (s)', fontsize=9)
			axes[ax_idx].set_title(f'Courant du Dipôle {dipole_id}', fontsize=10, fontweight='bold')
			axes[ax_idx].grid(True, alpha=0.3)
			axes[ax_idx].legend(loc='best', fontsize=8)
			ax_idx += 1
		
		self.transient_figure.tight_layout()
		self.transient_canvas.draw()
		self._update_transient_stats(time_values, selected_nodes, selected_dipoles)

	def _build_trace_stats(self, label: str, unit: str, time_values: np.ndarray, values: np.ndarray) -> str:
		"""Construit la ligne de stats pour une trace."""
		if values.size == 0:
			return f"{label}: trace vide"
		parts = [
			f"{label}",
			f"min={float(values.min()):.4g}{unit}",
			f"max={float(values.max()):.4g}{unit}",
			f"rms={_rms(values):.4g}{unit}",
			f"fin={float(values[-1]):.4g}{unit}",
		]
		cursor_time = self.cursor_time if self.cursor_time is not None else self.hover_time
		if cursor_time is not None and time_values.size:
			idx, sample_time, sample_value = _trace_value_at_time(time_values, values, cursor_time)
			parts.append(f"@t={sample_time:.4g}s -> {sample_value:.4g}{unit}")
		return " | ".join(parts)

	def _update_transient_stats(self, time_values: np.ndarray, selected_nodes: list, selected_dipoles: list) -> None:
		"""Met a jour le panneau de mesures transitoires."""
		lines = ["Mesures:"]
		for node_id, values in selected_nodes:
			lines.append(self._build_trace_stats(f"N{node_id}", "V", time_values, values))
		for dipole_id, values in selected_dipoles:
			lines.append(self._build_trace_stats(f"D{dipole_id}", "A", time_values, values))
		if len(lines) == 1:
			lines.append("Aucune mesure disponible.")
		self.transient_stats_text.setPlainText("\n".join(lines))

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
