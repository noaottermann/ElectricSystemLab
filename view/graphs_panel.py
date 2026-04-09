from __future__ import annotations

from PyQt5.QtGui import QPainter, QPen, QColor
from PyQt5.QtWidgets import (
	QLabel, QTextEdit, QVBoxLayout, QWidget,
	QCheckBox, QHBoxLayout, QGridLayout, QScrollArea, QGroupBox, QPushButton
)
from PyQt5.QtCore import Qt

import numpy as np
from typing import Optional

from utils.translator import Translator

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
	"""Rendu de courbes temporelles natif Qt."""

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
			painter.drawText(self.rect(), Qt.AlignCenter, Translator.tr("graph_no_curve"))
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
				unit_label = str(self.series[index].get("unit_label", Translator.tr("graph_value_axis")))
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
		painter.drawText(plot_rect.center().x() - 18, self.height() - 8, Translator.tr("graph_time_axis"))
		painter.save()
		painter.translate(12, plot_rect.center().y() + 32)
		painter.rotate(-90)
		painter.drawText(0, 0, self.series[0].get("unit_label", Translator.tr("graph_value_axis")))
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

		self.title_label = QLabel(Translator.tr("graph_panel_title"))
		self.title_label.setObjectName("graphPanelTitle")
		header_layout.addWidget(self.title_label, 1)

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
		self.nodes_group = QGroupBox(Translator.tr("graph_voltage_group"))
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
		self.nodes_controls_label = QLabel(Translator.tr("graph_selection_label"))
		nodes_controls_layout.addWidget(self.nodes_controls_label)
		nodes_controls_layout.addStretch(1)
		self.nodes_select_all_button = QPushButton(Translator.tr("graph_select_all"))
		self.nodes_select_all_button.setFixedSize(42, 20)
		self.nodes_select_all_button.setStyleSheet("QPushButton { padding: 0 4px; font-size: 10px; }")
		self.nodes_select_all_button.clicked.connect(lambda: self._set_checkboxes_selection(self.node_checkboxes, True))
		nodes_controls_layout.addWidget(self.nodes_select_all_button)
		self.nodes_select_none_button = QPushButton(Translator.tr("graph_select_none"))
		self.nodes_select_none_button.setFixedSize(48, 20)
		self.nodes_select_none_button.setStyleSheet("QPushButton { padding: 0 4px; font-size: 10px; }")
		self.nodes_select_none_button.clicked.connect(lambda: self._set_checkboxes_selection(self.node_checkboxes, False))
		nodes_controls_layout.addWidget(self.nodes_select_none_button)
		self.nodes_layout.addWidget(nodes_controls)
		self.transient_controls_layout.addWidget(self.nodes_group)
		
		# Sélection des dipôles
		self.dipoles_group = QGroupBox(Translator.tr("graph_current_group"))
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
		self.dipoles_controls_label = QLabel(Translator.tr("graph_selection_label"))
		dipoles_controls_layout.addWidget(self.dipoles_controls_label)
		dipoles_controls_layout.addStretch(1)
		self.dipoles_select_all_button = QPushButton(Translator.tr("graph_select_all"))
		self.dipoles_select_all_button.setFixedSize(42, 20)
		self.dipoles_select_all_button.setStyleSheet("QPushButton { padding: 0 4px; font-size: 10px; }")
		self.dipoles_select_all_button.clicked.connect(lambda: self._set_checkboxes_selection(self.dipole_checkboxes, True))
		dipoles_controls_layout.addWidget(self.dipoles_select_all_button)
		self.dipoles_select_none_button = QPushButton(Translator.tr("graph_select_none"))
		self.dipoles_select_none_button.setFixedSize(48, 20)
		self.dipoles_select_none_button.setStyleSheet("QPushButton { padding: 0 4px; font-size: 10px; }")
		self.dipoles_select_none_button.clicked.connect(lambda: self._set_checkboxes_selection(self.dipole_checkboxes, False))
		dipoles_controls_layout.addWidget(self.dipoles_select_none_button)
		self.dipoles_layout.addWidget(dipoles_controls)
		self.transient_controls_layout.addWidget(self.dipoles_group)
		
		self.transient_layout.addWidget(self.transient_controls)
		
		# Graphique transitoire
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

	def retranslate_ui(self) -> None:
		"""Met à jour les textes visibles selon la langue active."""
		self.title_label.setText(Translator.tr("graph_panel_title"))
		self.nodes_group.setTitle(Translator.tr("graph_voltage_group"))
		self.dipoles_group.setTitle(Translator.tr("graph_current_group"))
		self.nodes_controls_label.setText(Translator.tr("graph_selection_label"))
		self.dipoles_controls_label.setText(Translator.tr("graph_selection_label"))
		self.nodes_select_all_button.setText(Translator.tr("graph_select_all"))
		self.nodes_select_none_button.setText(Translator.tr("graph_select_none"))
		self.dipoles_select_all_button.setText(Translator.tr("graph_select_all"))
		self.dipoles_select_none_button.setText(Translator.tr("graph_select_none"))
		if hasattr(self, "transient_voltage_plot"):
			self.transient_voltage_plot.update()
		if hasattr(self, "transient_current_plot"):
			self.transient_current_plot.update()
		if self.last_transient_result:
			self.set_transient_results(self.last_transient_result, self.last_circuit)
		else:
			self.transient_stats_text.setPlainText(Translator.tr("graph_no_measure"))

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

	def _on_selection_changed(self) -> None:
		"""Callback quand la sélection change."""
		if not self.last_transient_result:
			return
		
		# Récupère la sélection actuelle
		self.selected_nodes = {node_id for node_id, checkbox in self.node_checkboxes.items() if checkbox.isChecked()}
		self.selected_dipoles = {dipole_id for dipole_id, checkbox in self.dipole_checkboxes.items() if checkbox.isChecked()}
		
		# Redessine les graphiques
		self._plot_transient_results_native(self.last_transient_result)
		window_time, selected_nodes, selected_dipoles = self._collect_selected_traces(self.last_transient_result)
		self._update_transient_stats(window_time, selected_nodes, selected_dipoles)

	def clear_results(self) -> None:
		"""Reinitialise le contenu affiche."""
		self._clear_checkboxes()
		self.selected_nodes = set()
		self.selected_dipoles = set()
		self.hover_time = None
		self.cursor_time = None
		self.transient_stats_text.setPlainText(Translator.tr("graph_no_measure"))
		
		if hasattr(self, "transient_voltage_plot"):
			self.transient_voltage_plot.set_series([])
		if hasattr(self, "transient_current_plot"):
			self.transient_current_plot.set_series([])

	def set_dc_results(self, circuit) -> None:
		"""Compatibilite: les resultats DC ne sont plus affiches dans ce panneau."""
		return

	def set_transient_results(self, result: dict | None, circuit=None) -> None:
		"""Affiche les traces transitoires avec graphiques."""
		if not result:
			self._clear_checkboxes()
			if hasattr(self, "transient_voltage_plot"):
				self.transient_voltage_plot.set_series([])
			if hasattr(self, "transient_current_plot"):
				self.transient_current_plot.set_series([])
			self.transient_stats_text.setPlainText(Translator.tr("graph_no_measure"))
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

		self._plot_transient_results_native(result)
		window_time, selected_nodes, selected_dipoles = self._collect_selected_traces(result)
		self._update_transient_stats(window_time, selected_nodes, selected_dipoles)

	def _collect_selected_traces(
		self,
		result: dict,
	) -> tuple[np.ndarray, list[tuple[str, np.ndarray, np.ndarray]], list[tuple[str, np.ndarray, np.ndarray]]]:
		"""Retourne les traces selectionnees avec leur grille temporelle visible."""
		time_values = np.asarray(result.get("time", []), dtype=float)
		dipole_voltages = result.get("dipole_voltages", {})
		dipole_currents = result.get("dipole_currents", {})
		if time_values.size == 0:
			return time_values, [], []

		window_mask, _, _ = self._compute_time_window(time_values)
		visible_time_values = time_values[window_mask]

		selected_nodes: list[tuple[str, np.ndarray, np.ndarray]] = []
		for node_id in sorted(dipole_voltages.keys(), key=lambda value: str(value)):
			if str(node_id) not in self.selected_nodes:
				continue
			values = np.asarray(dipole_voltages.get(node_id, []), dtype=float)
			if values.size == 0:
				continue
			if values.size == time_values.size:
				selected_nodes.append((str(node_id), visible_time_values, values[window_mask]))
				continue
			trim_size = min(values.size, time_values.size)
			x_values = time_values[:trim_size]
			y_values = values[:trim_size]
			local_mask, _, _ = self._compute_time_window(x_values)
			selected_nodes.append((str(node_id), x_values[local_mask], y_values[local_mask]))

		selected_dipoles: list[tuple[str, np.ndarray, np.ndarray]] = []
		for dipole_id in sorted(dipole_currents.keys(), key=lambda value: str(value)):
			if str(dipole_id) not in self.selected_dipoles:
				continue
			values = np.asarray(dipole_currents.get(dipole_id, []), dtype=float)
			if values.size == 0:
				continue
			if values.size == time_values.size:
				selected_dipoles.append((str(dipole_id), visible_time_values, values[window_mask]))
				continue
			trim_size = min(values.size, time_values.size)
			x_values = time_values[:trim_size]
			y_values = values[:trim_size]
			local_mask, _, _ = self._compute_time_window(x_values)
			selected_dipoles.append((str(dipole_id), x_values[local_mask], y_values[local_mask]))

		return visible_time_values, selected_nodes, selected_dipoles

	def _plot_transient_results_native(self, result: dict) -> None:
		"""Prépare un rendu natif Qt des courbes transitoires."""
		cursor_time = self.cursor_time if self.cursor_time is not None else self.hover_time
		_, selected_nodes, selected_dipoles = self._collect_selected_traces(result)

		voltage_series = [
			{
				"x": time_values,
				"y": values,
				"label": f"D{node_id}",
				"unit_label": Translator.tr("graph_voltage_axis"),
			}
			for node_id, time_values, values in selected_nodes
		]

		current_series = [
			{
				"x": time_values,
				"y": values,
				"label": f"D{dipole_id}",
				"unit_label": Translator.tr("graph_current_axis"),
			}
			for dipole_id, time_values, values in selected_dipoles
		]

		if hasattr(self, 'transient_voltage_plot'):
			self.transient_voltage_plot.set_series(voltage_series, cursor_time=cursor_time)
		if hasattr(self, 'transient_current_plot'):
			self.transient_current_plot.set_series(current_series, cursor_time=cursor_time)

	def _build_trace_stats(self, label: str, unit: str, time_values: np.ndarray, values: np.ndarray) -> str:
		"""Construit un bloc de stats lisible pour une trace."""
		if values.size == 0:
			return f"{label}\n  {Translator.tr('graph_state')}      : {Translator.tr('graph_empty_trace')}"

		parts = [
			f"{label}",
			f"  {Translator.tr('graph_min')}       : {float(values.min()):.4g} {unit}",
			f"  {Translator.tr('graph_max')}       : {float(values.max()):.4g} {unit}",
			f"  {Translator.tr('graph_rms')}       : {_rms(values):.4g} {unit}",
			f"  {Translator.tr('graph_final')}     : {float(values[-1]):.4g} {unit}",
		]
		cursor_time = self.cursor_time if self.cursor_time is not None else self.hover_time
		if cursor_time is not None and time_values.size:
			_, sample_time, sample_value = _trace_value_at_time(time_values, values, cursor_time)
			parts.append(f"  {Translator.tr('graph_cursor')}   : t={sample_time:.4g} s -> {sample_value:.4g} {unit}")
		return "\n".join(parts)

	def _update_transient_stats(
		self,
		time_values: np.ndarray,
		selected_nodes: list[tuple[str, np.ndarray, np.ndarray]],
		selected_dipoles: list[tuple[str, np.ndarray, np.ndarray]],
	) -> None:
		"""Met a jour le panneau de mesures transitoires."""
		scroll_bar = self.transient_stats_text.verticalScrollBar()
		previous_value = scroll_bar.value()
		previous_max = scroll_bar.maximum()
		was_at_bottom = previous_value >= previous_max

		lines = [Translator.tr("graph_measurements_title")]
		if time_values.size:
			lines.append(Translator.tr("graph_window").format(start=float(time_values[0]), end=float(time_values[-1]), count=len(time_values)))
		lines.append("")

		if selected_nodes:
			lines.append(Translator.tr("graph_voltage_section"))
		for node_id, node_time, values in selected_nodes:
			lines.append(self._build_trace_stats(f"D{node_id}", Translator.tr("graph_voltage_unit"), node_time, values))
			lines.append("")

		if selected_dipoles:
			lines.append(Translator.tr("graph_current_section"))
		for dipole_id, dipole_time, values in selected_dipoles:
			lines.append(self._build_trace_stats(f"D{dipole_id}", Translator.tr("graph_current_unit"), dipole_time, values))
			lines.append("")

		if not selected_nodes and not selected_dipoles:
			lines.append(Translator.tr("graph_no_measure"))

		while lines and lines[-1] == "":
			lines.pop()
		self.transient_stats_text.setPlainText("\n".join(lines))

		new_max = scroll_bar.maximum()
		if was_at_bottom:
			scroll_bar.setValue(new_max)
		else:
			scroll_bar.setValue(min(previous_value, new_max))

