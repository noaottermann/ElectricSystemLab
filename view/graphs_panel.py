from __future__ import annotations

from PyQt5.QtGui import QPainter, QPen, QColor
from PyQt5.QtWidgets import (
	QLabel, QTextEdit, QVBoxLayout, QWidget,
	QCheckBox, QHBoxLayout, QGridLayout, QScrollArea, QGroupBox, QPushButton
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
		cursor_points = []
		for index, entry in enumerate(self.series):
			x_values = np.asarray(entry.get("x", []), dtype=float)
			y_values = np.asarray(entry.get("y", []), dtype=float)
			if x_values.size == 0 or y_values.size == 0:
				continue
			painter.setPen(QPen(colors[index % len(colors)], 2))
			if self.cursor_time is not None:
				cursor_index, cursor_sample_time, cursor_sample_value = _trace_value_at_time(x_values, y_values, float(self.cursor_time))
				cursor_points.append((index, cursor_sample_time, cursor_sample_value))
			points = []
			for x_value, y_value in zip(x_values, y_values):
				points.append((map_x(float(x_value)), map_y(float(y_value))))
			for i in range(1, len(points)):
				p1 = points[i - 1]
				p2 = points[i]
				painter.drawLine(int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1]))
			if self.cursor_time is not None and x_values.size:
				cursor_index = _nearest_index(x_values, float(self.cursor_time))
				cursor_x = map_x(float(x_values[cursor_index]))
				cursor_y = map_y(float(y_values[cursor_index]))
				painter.setBrush(colors[index % len(colors)])
				painter.setPen(QPen(colors[index % len(colors)], 1))
				painter.drawEllipse(int(cursor_x) - 3, int(cursor_y) - 3, 6, 6)

		# Repère temporel
		if self.cursor_time is not None:
			cursor_x = map_x(float(self.cursor_time))
			painter.setPen(QPen(QColor("#6b7280"), 1, Qt.DashLine))
			painter.drawLine(int(cursor_x), plot_rect.top(), int(cursor_x), plot_rect.bottom())

			info_lines = [f"t = {float(self.cursor_time):.4g} s"]
			for index, sample_time, sample_value in cursor_points[:4]:
				label = str(self.series[index].get("label", f"Trace {index + 1}"))
				unit_label = str(self.series[index].get("unit_label", "Valeur"))
				info_lines.append(f"{label}: {sample_value:.4g} {unit_label.split('(')[-1].rstrip(')') if '(' in unit_label else ''}".rstrip())

			box_width = min(220, plot_rect.width() - 20)
			box_height = 18 + 14 * len(info_lines)
			box_left = max(plot_rect.left() + 8, min(int(cursor_x) + 10, plot_rect.right() - box_width - 6))
			box_top = plot_rect.top() + 8
			painter.setPen(QPen(QColor("#cbd5e1"), 1))
			painter.setBrush(QColor(255, 255, 255, 235))
			painter.drawRoundedRect(box_left, box_top, box_width, box_height, 6, 6)
			painter.setPen(QPen(QColor("#111827")))
			text_y = box_top + 16
			for line in info_lines:
				painter.drawText(box_left + 10, text_y, line)
				text_y += 14

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
		self.node_checkboxes: dict[str, QCheckBox] = {}
		self.dipole_checkboxes: dict[str, QCheckBox] = {}
		self.last_transient_result = None
		self.last_circuit = None
		self.hover_time = None
		self.cursor_time = None
		self.transient_window_seconds = None

		layout = QVBoxLayout(self)
		layout.setContentsMargins(10, 8, 10, 8)
		layout.setSpacing(8)

		header = QWidget()
		header_layout = QHBoxLayout(header)
		header_layout.setContentsMargins(0, 0, 0, 0)
		header_layout.setSpacing(8)

		title = QLabel("Graphiques")
		title.setObjectName("graphPanelTitle")
		header_layout.addWidget(title, 1)

		layout.addWidget(header)

		# ===== Panneau Transitoire =====
		self.transient_widget = QWidget()
		self.transient_layout = QVBoxLayout(self.transient_widget)
		self.transient_layout.setContentsMargins(0, 0, 0, 0)
		
		# Contrôles de sélection
		self.transient_controls = QWidget()
		self.transient_controls_layout = QVBoxLayout(self.transient_controls)
		self.transient_controls_layout.setContentsMargins(5, 5, 5, 5)
		self.transient_controls_layout.setSpacing(8)
		
		# Sélection des dipôles pour les tensions
		self.nodes_group = QGroupBox("Dipôles (tension)")
		self.nodes_layout = QVBoxLayout(self.nodes_group)
		self.nodes_layout.setSpacing(4)
		self.nodes_layout.setContentsMargins(5, 5, 5, 5)
		self.nodes_scroll = QScrollArea()
		self.nodes_scroll.setWidgetResizable(True)
		self.nodes_scroll.setMaximumHeight(150)
		nodes_container = QWidget()
		self.nodes_scroll.setWidget(nodes_container)
		self.nodes_container = nodes_container
		self.nodes_scroll_layout = QGridLayout(nodes_container)
		self.nodes_scroll_layout.setSpacing(4)
		self.nodes_scroll_layout.setContentsMargins(0, 0, 0, 0)
		self.nodes_scroll_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
		self.nodes_layout.addWidget(self.nodes_scroll)
		nodes_controls = QWidget()
		nodes_controls_layout = QHBoxLayout(nodes_controls)
		nodes_controls_layout.setContentsMargins(0, 0, 0, 0)
		nodes_controls_layout.setSpacing(4)
		nodes_controls_layout.addWidget(QLabel("Sélection"))
		nodes_controls_layout.addStretch(1)
		self.nodes_select_all_button = QPushButton("Tout")
		self.nodes_select_all_button.setFixedSize(42, 20)
		self.nodes_select_all_button.setStyleSheet("QPushButton { padding: 0 4px; font-size: 10px; }")
		self.nodes_select_all_button.clicked.connect(lambda: self._set_checkboxes_selection(self.node_checkboxes, True))
		nodes_controls_layout.addWidget(self.nodes_select_all_button)
		self.nodes_select_none_button = QPushButton("Aucun")
		self.nodes_select_none_button.setFixedSize(48, 20)
		self.nodes_select_none_button.setStyleSheet("QPushButton { padding: 0 4px; font-size: 10px; }")
		self.nodes_select_none_button.clicked.connect(lambda: self._set_checkboxes_selection(self.node_checkboxes, False))
		nodes_controls_layout.addWidget(self.nodes_select_none_button)
		self.nodes_layout.addWidget(nodes_controls)
		self.transient_controls_layout.addWidget(self.nodes_group)
		
		# Sélection des dipôles
		self.dipoles_group = QGroupBox("Dipôles")
		self.dipoles_layout = QVBoxLayout(self.dipoles_group)
		self.dipoles_layout.setSpacing(4)
		self.dipoles_layout.setContentsMargins(5, 5, 5, 5)
		self.dipoles_scroll = QScrollArea()
		self.dipoles_scroll.setWidgetResizable(True)
		self.dipoles_scroll.setMaximumHeight(150)
		dipoles_container = QWidget()
		self.dipoles_scroll.setWidget(dipoles_container)
		self.dipoles_container = dipoles_container
		self.dipoles_scroll_layout = QGridLayout(dipoles_container)
		self.dipoles_scroll_layout.setSpacing(4)
		self.dipoles_scroll_layout.setContentsMargins(0, 0, 0, 0)
		self.dipoles_scroll_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
		self.dipoles_layout.addWidget(self.dipoles_scroll)
		dipoles_controls = QWidget()
		dipoles_controls_layout = QHBoxLayout(dipoles_controls)
		dipoles_controls_layout.setContentsMargins(0, 0, 0, 0)
		dipoles_controls_layout.setSpacing(4)
		dipoles_controls_layout.addWidget(QLabel("Sélection"))
		dipoles_controls_layout.addStretch(1)
		self.dipoles_select_all_button = QPushButton("Tout")
		self.dipoles_select_all_button.setFixedSize(42, 20)
		self.dipoles_select_all_button.setStyleSheet("QPushButton { padding: 0 4px; font-size: 10px; }")
		self.dipoles_select_all_button.clicked.connect(lambda: self._set_checkboxes_selection(self.dipole_checkboxes, True))
		dipoles_controls_layout.addWidget(self.dipoles_select_all_button)
		self.dipoles_select_none_button = QPushButton("Aucun")
		self.dipoles_select_none_button.setFixedSize(48, 20)
		self.dipoles_select_none_button.setStyleSheet("QPushButton { padding: 0 4px; font-size: 10px; }")
		self.dipoles_select_none_button.clicked.connect(lambda: self._set_checkboxes_selection(self.dipole_checkboxes, False))
		dipoles_controls_layout.addWidget(self.dipoles_select_none_button)
		self.dipoles_layout.addWidget(dipoles_controls)
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
			self.transient_voltage_plot = TimeSeriesPlotWidget()
			self.transient_current_plot = TimeSeriesPlotWidget()
			self.transient_layout.addWidget(self.transient_voltage_plot, 1)
			self.transient_layout.addWidget(self.transient_current_plot, 1)

		self.transient_stats_text = QTextEdit()
		self.transient_stats_text.setReadOnly(True)
		self.transient_stats_text.setMaximumHeight(130)
		self.transient_stats_text.setStyleSheet(
			"""
			QTextEdit {
				background-color: #f8fafc;
				border: 1px solid #dbe2ea;
				border-radius: 6px;
				padding: 6px;
				line-height: 1.25;
			}
			"""
		)
		self.transient_layout.addWidget(self.transient_stats_text)

		layout.addWidget(self.transient_widget, 1)

		self.clear_results()

	def set_transient_window(self, window_seconds: Optional[float]) -> None:
		"""Definit la fenetre temporelle affichee pour le mode transitoire."""
		if window_seconds is None or window_seconds <= 0:
			self.transient_window_seconds = None
		else:
			self.transient_window_seconds = float(window_seconds)

	def _compute_time_window(self, time_values: np.ndarray) -> tuple[np.ndarray, float, float]:
		"""Retourne le masque de fenetre [t-delta, t] et ses bornes."""
		if time_values.size == 0:
			return np.array([], dtype=bool), 0.0, 0.0

		end_time = float(time_values[-1])
		if self.transient_window_seconds is None:
			start_time = float(time_values[0])
		else:
			start_time = max(float(time_values[0]), end_time - float(self.transient_window_seconds))

		mask = time_values >= start_time
		if not np.any(mask):
			mask = np.zeros(time_values.size, dtype=bool)
			mask[-1] = True
			start_time = float(time_values[-1])
		return mask, start_time, end_time

	def _create_node_checkbox(self, node_id: str, checked: bool = True) -> QCheckBox:
		"""Crée une checkbox pour un dipôle (tension)."""
		checkbox = QCheckBox(f"D{node_id}")
		checkbox.setChecked(checked)
		checkbox.stateChanged.connect(lambda: self._on_selection_changed())
		return checkbox

	def _create_dipole_checkbox(self, dipole_id: str, checked: bool = True) -> QCheckBox:
		"""Crée une checkbox pour un dipôle."""
		checkbox = QCheckBox(f"D{dipole_id}")
		checkbox.setChecked(checked)
		checkbox.stateChanged.connect(lambda: self._on_selection_changed())
		return checkbox

	def _clear_checkboxes(self) -> None:
		"""Efface toutes les checkboxes existantes."""
		self.node_checkboxes.clear()
		self.dipole_checkboxes.clear()
		while self.nodes_scroll_layout.count():
			item = self.nodes_scroll_layout.takeAt(0)
			if item and item.widget():
				item.widget().deleteLater()
		while self.dipoles_scroll_layout.count():
			item = self.dipoles_scroll_layout.takeAt(0)
			if item and item.widget():
				item.widget().deleteLater()

	def _reflow_checkboxes_grid(self, layout: QGridLayout, checkboxes: dict[str, QCheckBox], columns: int = 2) -> None:
		"""Réorganise les checkboxes dans une grille compacte et lisible."""
		while layout.count():
			layout.takeAt(0)

		sorted_ids = sorted(checkboxes.keys(), key=lambda value: (len(value), value))
		for index, item_id in enumerate(sorted_ids):
			row = index // columns
			column = index % columns
			layout.addWidget(checkboxes[item_id], row, column)

	def _adaptive_columns(self, scroll_area: QScrollArea, min_cell_width: int = 76) -> int:
		"""Calcule le nombre de colonnes en fonction de la largeur disponible."""
		if scroll_area is None or scroll_area.viewport() is None:
			return 2
		available_width = max(1, scroll_area.viewport().width())
		return max(1, available_width // min_cell_width)

	def _sync_checkbox_group(
		self,
		layout: QGridLayout,
		existing_checkboxes: dict[str, QCheckBox],
		available_ids: set[str],
		create_checkbox,
	) -> None:
		"""Met à jour un groupe de checkboxes sans les recréer inutilement."""
		# Retire uniquement les cases obsolètes
		for item_id in list(existing_checkboxes.keys()):
			if item_id in available_ids:
				continue
			checkbox = existing_checkboxes.pop(item_id)
			layout.removeWidget(checkbox)
			checkbox.deleteLater()

		# Ajoute uniquement les nouvelles cases
		for item_id in sorted(available_ids, key=lambda value: (len(value), value)):
			if item_id in existing_checkboxes:
				continue
			existing_checkboxes[item_id] = create_checkbox(item_id, checked=True)

		columns = self._adaptive_columns(self.nodes_scroll if layout is self.nodes_scroll_layout else self.dipoles_scroll)
		self._reflow_checkboxes_grid(layout, existing_checkboxes, columns=columns)

	def resizeEvent(self, event) -> None:
		"""Réadapte la grille des checkboxes lors du redimensionnement du panneau."""
		super().resizeEvent(event)
		if hasattr(self, "nodes_scroll_layout"):
			self._reflow_checkboxes_grid(
				self.nodes_scroll_layout,
				self.node_checkboxes,
				columns=self._adaptive_columns(self.nodes_scroll),
			)
		if hasattr(self, "dipoles_scroll_layout"):
			self._reflow_checkboxes_grid(
				self.dipoles_scroll_layout,
				self.dipole_checkboxes,
				columns=self._adaptive_columns(self.dipoles_scroll),
			)

	def _set_checkboxes_selection(self, checkboxes: dict[str, QCheckBox], checked: bool) -> None:
		"""Coche/decoches toutes les checkboxes d'un groupe."""
		for checkbox in checkboxes.values():
			checkbox.blockSignals(True)
			checkbox.setChecked(checked)
			checkbox.blockSignals(False)
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
		self.selected_nodes = {node_id for node_id, checkbox in self.node_checkboxes.items() if checkbox.isChecked()}
		self.selected_dipoles = {dipole_id for dipole_id, checkbox in self.dipole_checkboxes.items() if checkbox.isChecked()}
		
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
			self.transient_figure.clear()
			self.transient_canvas.draw()
		else:
			if hasattr(self, 'transient_voltage_plot'):
				self.transient_voltage_plot.set_series([])
			if hasattr(self, 'transient_current_plot'):
				self.transient_current_plot.set_series([])

	def set_dc_results(self, circuit) -> None:
		"""Compatibilite: les resultats DC ne sont plus affiches dans ce panneau."""
		return

	def _plot_dc_results(self, circuit) -> None:
		"""Affiche les resultats DC avec matplotlib."""
		self.dc_figure.clear()
		
		# Récupère les données par dipôle
		dipoles = sorted(circuit.dipoles.values(), key=lambda d: d.id)
		dipole_names = [f"D{d.id}" for d in dipoles]
		dipole_voltages = [d.voltage for d in dipoles]
		dipole_currents = [d.current for d in dipoles]
		
		# Crée la figure avec 2 subplots
		ax1 = self.dc_figure.add_subplot(211)
		ax2 = self.dc_figure.add_subplot(212)
		
		# Tensions des dipôles
		if dipole_voltages:
			colors = ['#3498db' if v >= 0 else '#e74c3c' for v in dipole_voltages]
			ax1.bar(range(len(dipole_voltages)), dipole_voltages, color=colors, alpha=0.7)
			ax1.set_xticks(range(len(dipole_names)))
			ax1.set_xticklabels(dipole_names, fontsize=9)
			ax1.set_ylabel('Tension (V)', fontsize=9)
			ax1.set_title('Tensions des Dipôles', fontsize=10, fontweight='bold')
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
		lines = ["Simulation DC", "", "Dipoles (tensions):"]
		for dipole in sorted(circuit.dipoles.values(), key=lambda d: d.id):
			lines.append(f"- D{dipole.id} {dipole.__class__.__name__}: {dipole.voltage:.6g} V")

		lines.append("")
		lines.append("Dipoles (courants):")
		for dipole in sorted(circuit.dipoles.values(), key=lambda d: d.id):
			lines.append(f"- D{dipole.id} {dipole.__class__.__name__}: {dipole.current:.6g} A")

		self.dc_text.setPlainText("\n".join(lines))

	def set_transient_results(self, result: dict | None, circuit=None) -> None:
		"""Affiche les traces transitoires avec graphiques."""
		if not result:
			self._clear_checkboxes()
			if not MATPLOTLIB_AVAILABLE and hasattr(self, 'transient_voltage_plot'):
				self.transient_voltage_plot.set_series([])
			if not MATPLOTLIB_AVAILABLE and hasattr(self, 'transient_current_plot'):
				self.transient_current_plot.set_series([])
			return

		# Stocke les résultats pour les mises à jour interactives
		self.last_transient_result = result
		self.last_circuit = circuit
		previous_node_states = {node_id: checkbox.isChecked() for node_id, checkbox in self.node_checkboxes.items()}
		previous_dipole_states = {dipole_id: checkbox.isChecked() for dipole_id, checkbox in self.dipole_checkboxes.items()}

		# Met à jour les checkboxes de sélection sans recréer tout le groupe (évite le flicker)
		dipole_voltages = result.get("dipole_voltages", {})
		dipole_currents = result.get("dipole_currents", {})
		available_node_ids = {str(node_id) for node_id in dipole_voltages.keys()}
		available_dipole_ids = {str(dipole_id) for dipole_id in dipole_currents.keys()}
		node_ids_changed = available_node_ids != set(self.node_checkboxes.keys())
		dipole_ids_changed = available_dipole_ids != set(self.dipole_checkboxes.keys())

		if node_ids_changed:
			self._sync_checkbox_group(
				self.nodes_scroll_layout,
				self.node_checkboxes,
				available_node_ids,
				self._create_node_checkbox,
			)
		if dipole_ids_changed:
			self._sync_checkbox_group(
				self.dipoles_scroll_layout,
				self.dipole_checkboxes,
				available_dipole_ids,
				self._create_dipole_checkbox,
			)
		
		# N'applique des etats que lorsque la liste des courbes change.
		# Sinon, on conserve strictement la selection utilisateur en cours.
		if node_ids_changed:
			for node_id, checkbox in self.node_checkboxes.items():
				target_checked = previous_node_states.get(node_id, True)
				if checkbox.isChecked() == target_checked:
					continue
				checkbox.blockSignals(True)
				checkbox.setChecked(target_checked)
				checkbox.blockSignals(False)

		if dipole_ids_changed:
			for dipole_id, checkbox in self.dipole_checkboxes.items():
				target_checked = previous_dipole_states.get(dipole_id, True)
				if checkbox.isChecked() == target_checked:
					continue
				checkbox.blockSignals(True)
				checkbox.setChecked(target_checked)
				checkbox.blockSignals(False)

		self.selected_nodes = {node_id for node_id, checkbox in self.node_checkboxes.items() if checkbox.isChecked()}
		self.selected_dipoles = {dipole_id for dipole_id, checkbox in self.dipole_checkboxes.items() if checkbox.isChecked()}

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
		if self.transient_window_seconds is not None and time_values.size:
			mask, start_time, end_time = self._compute_time_window(time_values)
			window_points = int(np.count_nonzero(mask))
			lines.append(
				f"Fenêtre affichée: [{start_time:.6g}s, {end_time:.6g}s] ({window_points} points)"
			)
			lines.append("")
		lines.append("Dipôles tension sélectionnés: " + (", ".join(sorted(self.selected_nodes)) if self.selected_nodes else "aucun"))
		lines.append("Dipôles courant sélectionnés: " + (", ".join(sorted(self.selected_dipoles)) if self.selected_dipoles else "aucun"))
		cursor_time = self.cursor_time if self.cursor_time is not None else self.hover_time
		if cursor_time is not None:
			lines.append("")
			lines.append(f"Repère temporel: {cursor_time:.6g}s")
		return lines

	def _plot_transient_results_native(self, result: dict) -> None:
		"""Prépare un rendu natif Qt quand matplotlib n'est pas disponible."""
		time_values = np.asarray(result.get("time", []), dtype=float)
		dipole_voltages = result.get("dipole_voltages", {})
		dipole_currents = result.get("dipole_currents", {})
		cursor_time = self.cursor_time if self.cursor_time is not None else self.hover_time
		window_mask, _, _ = self._compute_time_window(time_values)
		visible_time_values = time_values[window_mask]

		voltage_series = []
		for node_id in sorted(dipole_voltages.keys()):
			if str(node_id) not in self.selected_nodes:
				continue
			values = np.asarray(dipole_voltages.get(node_id, []), dtype=float)
			if values.size == 0:
				continue
			if values.size != time_values.size:
				trim_size = min(values.size, time_values.size)
				x_values = time_values[:trim_size]
				y_values = values[:trim_size]
				local_mask, _, _ = self._compute_time_window(x_values)
				voltage_series.append({"x": x_values[local_mask], "y": y_values[local_mask], "label": f"D{node_id}", "unit_label": "Tension (V)"})
				continue
			voltage_series.append({"x": visible_time_values, "y": values[window_mask], "label": f"D{node_id}", "unit_label": "Tension (V)"})

		current_series = []
		for dipole_id in sorted(dipole_currents.keys()):
			if str(dipole_id) not in self.selected_dipoles:
				continue
			values = np.asarray(dipole_currents.get(dipole_id, []), dtype=float)
			if values.size == 0:
				continue
			if values.size != time_values.size:
				trim_size = min(values.size, time_values.size)
				x_values = time_values[:trim_size]
				y_values = values[:trim_size]
				local_mask, _, _ = self._compute_time_window(x_values)
				current_series.append({"x": x_values[local_mask], "y": y_values[local_mask], "label": f"D{dipole_id}", "unit_label": "Courant (A)"})
				continue
			current_series.append({"x": visible_time_values, "y": values[window_mask], "label": f"D{dipole_id}", "unit_label": "Courant (A)"})

		if hasattr(self, 'transient_voltage_plot'):
			self.transient_voltage_plot.set_series(voltage_series, cursor_time=cursor_time)
		if hasattr(self, 'transient_current_plot'):
			self.transient_current_plot.set_series(current_series, cursor_time=cursor_time)

	def _plot_transient_results(self, result: dict, circuit=None) -> None:
		"""Affiche les resultats transitoires avec matplotlib."""
		self.transient_figure.clear()
		
		time_values = np.array(result.get("time", []))
		dipole_voltages = result.get("dipole_voltages", {})
		dipole_currents = result.get("dipole_currents", {})
		
		if len(time_values) == 0:
			return

		window_mask, window_start, window_end = self._compute_time_window(time_values)
		visible_time_values = time_values[window_mask]
		
		# Filtre selon la sélection des tensions
		selected_nodes = []
		for node_id in sorted(dipole_voltages.keys()):
			if str(node_id) in self.selected_nodes:
				values = np.array(dipole_voltages.get(node_id, []))
				if len(values) > 0:
					if len(values) == len(time_values):
						selected_nodes.append((node_id, values[window_mask]))
					else:
						trim_size = min(len(values), len(time_values))
						x_values = time_values[:trim_size]
						y_values = values[:trim_size]
						local_mask, _, _ = self._compute_time_window(x_values)
						visible_time_values = x_values[local_mask]
						selected_nodes.append((node_id, y_values[local_mask]))
		
		selected_dipoles = []
		for dipole_id in sorted(dipole_currents.keys()):
			if str(dipole_id) in self.selected_dipoles:
				values = np.array(dipole_currents.get(dipole_id, []))
				if len(values) > 0:
					if len(values) == len(time_values):
						selected_dipoles.append((dipole_id, values[window_mask]))
					else:
						trim_size = min(len(values), len(time_values))
						x_values = time_values[:trim_size]
						y_values = values[:trim_size]
						local_mask, _, _ = self._compute_time_window(x_values)
						visible_time_values = x_values[local_mask]
						selected_dipoles.append((dipole_id, y_values[local_mask]))
		
		if len(selected_nodes) == 0 and len(selected_dipoles) == 0:
			self.transient_stats_text.setPlainText("Aucune trace sélectionnée.")
			self.transient_canvas.draw()
			return

		cursor_time = self.cursor_time if self.cursor_time is not None else self.hover_time

		ax_voltage = self.transient_figure.add_subplot(211)
		ax_current = self.transient_figure.add_subplot(212)

		if selected_nodes:
			for node_id, values in selected_nodes:
				ax_voltage.plot(visible_time_values, values, linewidth=2, label=f'D{node_id}')
			if cursor_time is not None:
				ax_voltage.axvline(cursor_time, color="#7f8c8d", linestyle="--", linewidth=1.0)
			if self.transient_window_seconds is not None:
				ax_voltage.set_xlim(window_start, window_end)
			ax_voltage.set_ylabel('Tension (V)', fontsize=9)
			ax_voltage.set_xlabel('Temps (s)', fontsize=9)
			ax_voltage.set_title('Tensions des dipôles sélectionnés', fontsize=10, fontweight='bold')
			ax_voltage.grid(True, alpha=0.3)
			ax_voltage.legend(loc='best', fontsize=8)
		else:
			ax_voltage.set_title('Tensions des dipôles sélectionnés', fontsize=10, fontweight='bold')
			ax_voltage.set_ylabel('Tension (V)', fontsize=9)
			ax_voltage.set_xlabel('Temps (s)', fontsize=9)
			ax_voltage.grid(True, alpha=0.3)
			ax_voltage.text(0.5, 0.5, 'Aucune tension sélectionnée', transform=ax_voltage.transAxes, ha='center', va='center')

		if selected_dipoles:
			for dipole_id, values in selected_dipoles:
				ax_current.plot(visible_time_values, values, linewidth=2, label=f'D{dipole_id}')
			if cursor_time is not None:
				ax_current.axvline(cursor_time, color="#7f8c8d", linestyle="--", linewidth=1.0)
			if self.transient_window_seconds is not None:
				ax_current.set_xlim(window_start, window_end)
			ax_current.set_ylabel('Courant (A)', fontsize=9)
			ax_current.set_xlabel('Temps (s)', fontsize=9)
			ax_current.set_title('Courants des dipôles sélectionnés', fontsize=10, fontweight='bold')
			ax_current.grid(True, alpha=0.3)
			ax_current.legend(loc='best', fontsize=8)
		else:
			ax_current.set_title('Courants des dipôles sélectionnés', fontsize=10, fontweight='bold')
			ax_current.set_ylabel('Courant (A)', fontsize=9)
			ax_current.set_xlabel('Temps (s)', fontsize=9)
			ax_current.grid(True, alpha=0.3)
			ax_current.text(0.5, 0.5, 'Aucun courant sélectionné', transform=ax_current.transAxes, ha='center', va='center')
		
		self.transient_figure.tight_layout()
		self.transient_canvas.draw()
		self._update_transient_stats(visible_time_values, selected_nodes, selected_dipoles)

	def _build_trace_stats(self, label: str, unit: str, time_values: np.ndarray, values: np.ndarray) -> str:
		"""Construit un bloc de stats lisible pour une trace."""
		if values.size == 0:
			return f"{label}\n  Etat      : trace vide"

		parts = [
			f"{label}",
			f"  Min       : {float(values.min()):.4g} {unit}",
			f"  Max       : {float(values.max()):.4g} {unit}",
			f"  RMS       : {_rms(values):.4g} {unit}",
			f"  Final     : {float(values[-1]):.4g} {unit}",
		]
		cursor_time = self.cursor_time if self.cursor_time is not None else self.hover_time
		if cursor_time is not None and time_values.size:
			_, sample_time, sample_value = _trace_value_at_time(time_values, values, cursor_time)
			parts.append(f"  Curseur   : t={sample_time:.4g} s -> {sample_value:.4g} {unit}")
		return "\n".join(parts)

	def _update_transient_stats(self, time_values: np.ndarray, selected_nodes: list, selected_dipoles: list) -> None:
		"""Met a jour le panneau de mesures transitoires."""
		lines = ["MESURES TRANSITOIRES"]
		if time_values.size:
			lines.append(f"Fenetre: {float(time_values[0]):.4g} s -> {float(time_values[-1]):.4g} s ({len(time_values)} points)")
		lines.append("")

		if selected_nodes:
			lines.append("TENSIONS")
		for node_id, values in selected_nodes:
			lines.append(self._build_trace_stats(f"D{node_id}", "V", time_values, values))
			lines.append("")

		if selected_dipoles:
			lines.append("COURANTS")
		for dipole_id, values in selected_dipoles:
			lines.append(self._build_trace_stats(f"D{dipole_id}", "A", time_values, values))
			lines.append("")

		if not selected_nodes and not selected_dipoles:
			lines.append("Aucune mesure disponible.")

		while lines and lines[-1] == "":
			lines.pop()
		self.transient_stats_text.setPlainText("\n".join(lines))

	def _text_transient_results(self, result: dict) -> None:
		"""Affiche les resultats transitoires en texte (fallback sans matplotlib)."""
		time_values = result.get("time", [])
		dipole_voltages = result.get("dipole_voltages", {})
		dipole_currents = result.get("dipole_currents", {})

		lines = ["Simulation transitoire", ""]
		if time_values:
			lines.append(
				f"Points: {len(time_values)} | t0={time_values[0]:.6g}s | tfin={time_values[-1]:.6g}s"
			)
		else:
			lines.append("Aucun point temporel.")

		lines.append("")
		lines.append("Dipoles (tensions, dernier point):")
		for node_id in sorted(dipole_voltages, key=lambda x: str(x)):
			values = dipole_voltages.get(node_id, [])
			if not values:
				continue
			lines.append(f"- D{node_id}: {values[-1]:.6g} V")

		lines.append("")
		lines.append("Dipoles (dernier point):")
		for dipole_id in sorted(dipole_currents, key=lambda x: str(x)):
			values = dipole_currents.get(dipole_id, [])
			if not values:
				continue
			lines.append(f"- D{dipole_id}: {values[-1]:.6g} A")

		self.transient_text.setPlainText("\n".join(lines))
