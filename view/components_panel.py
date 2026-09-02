from pathlib import Path
from typing import Optional

from PyQt5.QtCore import QEvent, QPointF, QSize, Qt, QMimeData, pyqtSignal
from PyQt5.QtGui import QColor, QDrag, QFont, QIcon, QPainter, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QStyleOptionGraphicsItem,
    QVBoxLayout,
    QWidget,
)
from utils.translator import Translator

from model.components import (
	Ammeter,
	Capacitor,
	Comparator,
	CurrentControlledCurrentSource,
	CurrentControlledVoltageSource,
	CurrentSource,
	Diode,
	Fuse,
	Ground,
	Inductor,
	LED,
	LogicGate,
	LogicGateAND,
	LogicGateNAND,
	LogicGateNOR,
	LogicGateNOT,
	LogicGateOR,
	LogicGateXOR,
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
	Voltmeter,
	VoltageControlledCurrentSource,
	VoltageControlledVoltageSource,
	VoltageSource,
	ZenerDiode,
)
from model.node import Node
from model.wire import Wire
from .component_item import create_component_item
from .wire_item import WireItem


class ComponentsPanel(QWidget):
	"""Panneau lateral listant les composants disponibles."""

	# Signal emis lorsqu'un composant est double-clique (pour la selection d'outil)
	tool_selected = pyqtSignal(str)

	def __init__(self, parent=None) -> None:
		"""Initialise l'interface et les listes de composants."""
		super().__init__(parent)
		self.assets_root = Path(__file__).resolve().parents[1] / "assets"

		self._category_data = self._build_default_categories()
		self._component_data = self._build_default_components()
		self._suppress_category_highlight = False
		self._updating_category_highlight = False
		self._icon_cache: dict[str, QIcon] = {}

		layout = QHBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(0)

		self.category_list = QListWidget()
		self.category_list.setObjectName("categoryList")
		self.category_list.setViewMode(QListWidget.ListMode)
		self.category_list.setFixedWidth(124)
		self.category_list.setSpacing(0)
		self.category_list.setUniformItemSizes(True)
		self.category_list.setSelectionMode(QListWidget.SingleSelection)
		self.category_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
		self.category_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
		self.category_list.setFocusPolicy(Qt.NoFocus)
		self.category_list.setViewportMargins(0, 0, 0, 0)
		self.category_list.setContentsMargins(0, 0, 0, 0)
		self.category_list.setFrameShape(QFrame.NoFrame)
		self.category_list.setLineWidth(0)

		self.components_list = ComponentsListWidget()
		self.components_list.setObjectName("componentsList")
		self.components_list.setViewMode(QListWidget.ListMode)
		self.components_list.setIconSize(QSize(60, 60))
		self.components_list.setSpacing(0)
		self.components_list.setUniformItemSizes(True)
		self.components_list.setSelectionMode(QListWidget.SingleSelection)
		self.components_list.setDragEnabled(True)
		self.components_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
		self.components_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
		self.components_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
		self.components_list.setFocusPolicy(Qt.NoFocus)
		self.components_list.verticalScrollBar().setSingleStep(8)
		self.components_list.verticalScrollBar().valueChanged.connect(
			self._update_highlight_from_scroll
		)

		layout.addWidget(self._wrap_category_list())
		layout.addWidget(self._wrap_components_list(), 1)

		self._apply_styles()
		self._populate_categories()
		self._populate_components_all()
		self._sync_category_item_widths()
		self.category_list.currentItemChanged.connect(self._on_category_changed)
		self.category_list.itemClicked.connect(self._on_category_clicked)
		self.components_list.itemClicked.connect(self._on_component_clicked)
		self.components_list.tool_requested.connect(self.tool_selected.emit)

		self._app = QApplication.instance()
		if self._app is not None:
			self._app.installEventFilter(self)

		if self.category_list.count() > 0:
			self.category_list.setCurrentRow(0)

	def retranslate_ui(self) -> None:
		"""Met a jour les textes visibles du panneau selon la langue active."""
		current_category_key = None
		current_item = self.category_list.currentItem()
		if current_item is not None:
			current_category_key = current_item.data(Qt.UserRole)
		search_text = self.search_input.text() if hasattr(self, "search_input") else ""

		self.category_list.blockSignals(True)
		self.components_list.blockSignals(True)
		self._category_data = self._build_default_categories()
		self._component_data = self._build_default_components()
		self._populate_categories()
		self._populate_components_all()
		self._sync_category_item_widths()

		if current_category_key is not None:
			for row in range(self.category_list.count()):
				item = self.category_list.item(row)
				if item.data(Qt.UserRole) == current_category_key:
					self.category_list.setCurrentRow(row)
					break

		self.category_list.blockSignals(False)
		self.components_list.blockSignals(False)

		if hasattr(self, "search_input"):
			self.search_input.setPlaceholderText(Translator.tr("components_search_placeholder"))
			if search_text:
				self.search_input.setText(search_text)
			else:
				self._apply_search_filter("")


	def resizeEvent(self, event: object) -> None:
		"""Reagit aux redimensionnements pour ajuster la liste des categories."""
		super().resizeEvent(event)
		self._sync_category_item_widths()

	def closeEvent(self, event: object) -> None:
		"""Nettoie les filtres d'evenements Qt."""
		if self._app is not None:
			self._app.removeEventFilter(self)
		super().closeEvent(event)

	def eventFilter(self, watched: object, event: object) -> bool:
		"""Laisse la selection active meme si l'utilisateur clique hors du panneau."""
		return super().eventFilter(watched, event)

	def _clear_component_selection(self) -> None:
		"""Reinitialise la selection des composants."""
		self.components_list.clearSelection()
		self.components_list.setCurrentRow(-1)

	def clear_component_selection(self) -> None:
		"""Expose la reinitialisation de la selection des composants."""
		self._clear_component_selection()

	def _wrap_category_list(self) -> QFrame:
		"""Construit la colonne des categories."""
		frame = QFrame()
		frame.setObjectName("categoryPane")
		layout = QVBoxLayout(frame)
		layout.setContentsMargins(0, 0, 0, 8)
		layout.addWidget(self.category_list)
		return frame

	def _wrap_components_list(self) -> QFrame:
		"""Construit la colonne des composants."""
		frame = QFrame()
		frame.setObjectName("componentsPane")
		layout = QVBoxLayout(frame)
		layout.setContentsMargins(0, 0, 1, 2)
		layout.setSpacing(0)
		self._components_layout = layout
		self._components_left_margin = 0
		self._components_top_margin = 0
		self._components_right_margin = 2
		self._components_bottom_margin = 8

		self.header_widget = QWidget()
		header_layout = QVBoxLayout(self.header_widget)
		header_layout.setContentsMargins(0, 0, 0, 0)
		header_layout.setSpacing(0)

		self.search_input = QLineEdit()
		self.search_input.setPlaceholderText(Translator.tr("components_search_placeholder"))
		self.search_input.textChanged.connect(self._apply_search_filter)
		header_layout.addWidget(self.search_input)

		layout.addWidget(self.header_widget)

		layout.addWidget(self.components_list, 1)
		return frame

	def set_header_height(self, height: int) -> None:
		"""Force la hauteur du bloc titre + recherche."""
		if not hasattr(self, "header_widget") or self.header_widget is None:
			return
		self.header_widget.setFixedHeight(max(0, int(height)))

	def clear_header_height(self) -> None:
		"""Restaure la hauteur automatique du bloc titre + recherche."""
		if not hasattr(self, "header_widget") or self.header_widget is None:
			return
		self.header_widget.setMinimumHeight(0)
		self.header_widget.setMaximumHeight(16777215)

	def set_header_visible(self, visible: bool) -> None:
		"""Affiche ou masque le bloc titre + recherche."""
		if not hasattr(self, "header_widget") or self.header_widget is None:
			return
		self.header_widget.setVisible(bool(visible))

	def set_header_overlap(self, overlap_height: int) -> None:
		"""Decale le header vers le haut pour chevaucher la barre de simulation."""
		if not hasattr(self, "_components_layout"):
			return
		overlap = int(overlap_height)
		self._components_layout.setContentsMargins(
			self._components_left_margin,
			self._components_top_margin - overlap,
			self._components_right_margin,
			self._components_bottom_margin,
		)

	def set_header_top_margin(self, margin: int) -> None:
		"""Definit la marge haute du panneau composants."""
		if not hasattr(self, "_components_layout"):
			return
		self._components_layout.setContentsMargins(
			self._components_left_margin,
			int(margin),
			self._components_right_margin,
			self._components_bottom_margin,
		)

	def _apply_styles(self) -> None:
		"""Applique le style visuel du panneau."""
		self.setStyleSheet(
			"""
			QFrame#categoryPane {
				background: #f6f4ef;
				border-right: 1px solid #d7d2c8;
			}
			QFrame#componentsPane {
				background: #f6f4ef;
			}
			QListWidget {
				border: none;
				background: transparent;
			}
			QListWidget::item {
				padding: 0px 1px 0px 0px;
				border-radius: 8px;
				color: #2a2a2a;
			}
			QListWidget#categoryList::item {
				padding: 0px;
				margin: 0px;
			}
			QListWidget#categoryList {
				padding-left: 0px;
				margin: 0px;
			}
			QListWidget::item:selected {
				background: #ffe2b6;
			}
			"""
		)

		base_font = QFont("Segoe UI", 10)
		self.setFont(base_font)

	def _build_default_categories(self) -> list[dict]:
		"""Construit la liste des categories par defaut."""
		return [
			{
				"key": "topology",
				"label_key": "components_category_topology",
				"icon": "categories/topology.png",
				"color": "#4c5c68",
			},
			{
				"key": "sources",
				"label_key": "components_category_sources",
				"icon": "categories/sources.png",
				"color": "#f18f01",
			},
			{
				"key": "passives",
				"label_key": "components_category_passives",
				"icon": "categories/passives.png",
				"color": "#247ba0",
			},
			{
				"key": "semiconductors",
				"label_key": "components_category_semiconductors",
				"icon": "categories/semiconductors.png",
				"color": "#6d597a",
			},
			{
				"key": "analog_ics",
				"label_key": "components_category_analog_ics",
				"icon": "categories/analog_ics.png",
				"color": "#c1666b",
			},
			{
				"key": "logic",
				"label_key": "components_category_logic",
				"icon": "categories/analog_ics.png",
				"color": "#3d5a80",
			},
			{
				"key": "electromechanical",
				"label_key": "components_category_electromechanical",
				"icon": "categories/electromechanical.png",
				"color": "#7f5539",
			},
			{
				"key": "instruments",
				"label_key": "components_category_instruments",
				"icon": "categories/instruments.png",
				"color": "#386641",
			},
		]

	def _build_default_components(self) -> dict[str, list[dict]]:
		"""Construit les composants par defaut affiches dans la liste."""
		return {
			"topology": [
				{
					"id": "wire",
					"label_key": "components_item_wire",
					"icon": "components/wire.png",
				},
				{
					"id": "ground",
					"label_key": "components_item_ground",
					"icon": "components/ground.png",
				},
			],
			"sources": [
				{
					"id": "source",
					"label_key": "components_item_source",
					"icon": "components/source_dc.png",
				},
				{
					"id": "pulse_source",
					"label_key": "components_item_pulse_source",
					"icon": "components/source_ac.png",
				},
				{
					"id": "current_source",
					"label_key": "components_item_current_source",
					"icon": "components/current_source_dc.png",
				},
				{
					"id": "source_vccs",
					"label_key": "components_item_source_vccs",
					"icon": "components/source_vccs.png",
				},
				{
					"id": "source_vcvs",
					"label_key": "components_item_source_vcvs",
					"icon": "components/source_vcvs.png",
				},
				{
					"id": "source_cccs",
					"label_key": "components_item_source_cccs",
					"icon": "components/source_cccs.png",
				},
				{
					"id": "source_ccvs",
					"label_key": "components_item_source_ccvs",
					"icon": "components/source_ccvs.png",
				},
			],
			"passives": [
				{
					"id": "resistor",
					"label_key": "components_item_resistor",
					"icon": "components/resistor.png",
				},
				{
					"id": "potentiometer",
					"label_key": "components_item_potentiometer",
					"icon": "components/resistor.png",
				},
				{
					"id": "capacitor",
					"label_key": "components_item_capacitor",
					"icon": "components/capacitor.png",
				},
				{
					"id": "inductor",
					"label_key": "components_item_inductor",
					"icon": "components/inductor.png",
				},
				{
					"id": "transformer",
					"label_key": "components_item_transformer",
					"icon": "components/transformer.png",
				},
				{
					"id": "fuse",
					"label_key": "components_item_fuse",
					"icon": "components/resistor.png",
				},
			],
			"semiconductors": [
				{
					"id": "diode",
					"label_key": "components_item_diode",
					"icon": "components/diode.png",
				},
				{
					"id": "zener_diode",
					"label_key": "components_item_zener_diode",
					"icon": "components/diode.png",
				},
				{
					"id": "transistor",
					"label_key": "components_item_transistor",
					"icon": "components/diode.png",
				},
				{
					"id": "mosfet",
					"label_key": "components_item_mosfet",
					"icon": "components/diode.png",
				},
			],
			"analog_ics": [
				{
					"id": "opamp",
					"label_key": "components_item_opamp",
					"icon": "components/source_vcvs.png",
				},
				{
					"id": "comparator",
					"label_key": "components_item_comparator",
					"icon": "components/source_vcvs.png",
				},
			],
			"logic": [
				{
					"id": "logic_and",
					"label_key": "components_item_logic_and",
					"icon": "components/source_vcvs.png",
				},
				{
					"id": "logic_or",
					"label_key": "components_item_logic_or",
					"icon": "components/source_vcvs.png",
				},
				{
					"id": "logic_not",
					"label_key": "components_item_logic_not",
					"icon": "components/source_vcvs.png",
				},
				{
					"id": "logic_nand",
					"label_key": "components_item_logic_nand",
					"icon": "components/source_vcvs.png",
				},
				{
					"id": "logic_nor",
					"label_key": "components_item_logic_nor",
					"icon": "components/source_vcvs.png",
				},
				{
					"id": "logic_xor",
					"label_key": "components_item_logic_xor",
					"icon": "components/source_vcvs.png",
				},
			],
			"electromechanical": [
				{
					"id": "switch",
					"label_key": "components_item_switch",
					"icon": "components/switch.png",
				},
			],
			"instruments": [
				{
					"id": "voltmeter",
					"label_key": "components_item_voltmeter",
					"icon": "components/voltmeter.png",
				},
				{
					"id": "ammeter",
					"label_key": "components_item_ammeter",
					"icon": "components/ammeter.png",
				},
			],
		}

	def _populate_categories(self) -> None:
		"""Remplit la liste des categories disponibles."""
		self.category_list.clear()
		for category in self._category_data:
			icon = self._load_icon(category["icon"], category["color"], QSize(48, 48))
			label = Translator.tr(category["label_key"])
			item = QListWidgetItem()
			item.setToolTip(label)
			item.setData(Qt.UserRole, category["key"])
			item.setSizeHint(QSize(132, 104))
			self.category_list.addItem(item)
			self.category_list.setItemWidget(
				item, self._build_category_widget(icon, label)
			)

		self._sync_category_item_widths()

	def _on_category_changed(self, current: Optional[QListWidgetItem], _previous: Optional[QListWidgetItem]) -> None:
		"""Fait defiler la liste d'elements de circuit selon la categorie active."""
		if current is None:
			return
		category_key = current.data(Qt.UserRole)
		self._scroll_to_category(category_key)

	def _on_category_clicked(self, item: Optional[QListWidgetItem]) -> None:
		"""Reagit au clic sur une categorie."""
		if item is None:
			return
		category_key = item.data(Qt.UserRole)
		self._scroll_to_category(category_key)

	def _on_component_clicked(self, item: Optional[QListWidgetItem]) -> None:
		"""Emet le signal tool_selected lorsqu'un composant est clique."""
		if item is None:
			return
		component_id = item.data(Qt.UserRole)
		if not component_id or (isinstance(component_id, str) and component_id.startswith("header:")):
			return
		self._emit_tool_request(component_id)

	def _emit_tool_request(self, component_id: object) -> None:
		"""Demande la selection de l'outil associe a un composant."""
		if not component_id:
			return
		self.tool_selected.emit(str(component_id))

	def _populate_components_all(self) -> None:
		"""Remplit la liste d'elements de circuit pour toutes les categories."""
		self.components_list.clear()
		for category in self._category_data:
			self._add_category_section(category)

	def _add_category_section(self, category: dict) -> None:
		"""Ajoute une section complete (en-tete + composants)."""
		self._add_category_header(category)
		components = self._component_data.get(category["key"], [])
		if not components:
			self._add_empty_category()
			return
		for component in components:
			self._add_component_row(component, category["key"])

	def _add_category_header(self, category: dict) -> None:
		"""Ajoute un en-tete de categorie dans la liste."""
		header_item = QListWidgetItem(" " + Translator.tr(category["label_key"]))
		header_item.setData(Qt.UserRole, f"header:{category['key']}")
		header_item.setFlags(Qt.NoItemFlags)
		header_item.setSizeHint(QSize(160, 12))
		self.components_list.addItem(header_item)

	def _add_empty_category(self) -> None:
		"""Ajoute une ligne vide lorsqu'une categorie n'a pas de composants."""
		empty_item = QListWidgetItem(Translator.tr("components_empty_category"))
		empty_item.setFlags(Qt.NoItemFlags)
		empty_item.setSizeHint(QSize(160, 14))
		self.components_list.addItem(empty_item)

	def _add_component_row(self, component: dict, category_key: str) -> None:
		"""Ajoute une ligne pour un composant."""
		icon = self._build_component_icon(component)
		item = QListWidgetItem(icon, Translator.tr(component["label_key"]))
		item.setData(Qt.UserRole, component["id"])
		item.setData(Qt.UserRole + 1, category_key)
		item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
		item.setSizeHint(QSize(160, 52))
		self.components_list.addItem(item)

	def set_component_icon(self, component_id: str, icon_path: str) -> None:
		"""Met a jour l'icone d'un composant dans la liste."""
		if not component_id or not icon_path:
			return
		for category_key, components in self._component_data.items():
			for component in components:
				if component.get("id") == component_id:
					component["icon"] = icon_path

		icon = self._load_icon(icon_path, "#d7d7d7", QSize(44, 44))
		for row in range(self.components_list.count()):
			item = self.components_list.item(row)
			if item is None:
				continue
			if item.data(Qt.UserRole) == component_id:
				item.setIcon(icon)

	def set_component_state_icon(self, component_id: str, state_value: str | None) -> None:
		"""Met a jour l'icone d'un composant selon un etat."""
		if not component_id:
			return
		icon = self._build_component_icon({"id": component_id}, state_value=state_value)
		for row in range(self.components_list.count()):
			item = self.components_list.item(row)
			if item is None:
				continue
			if item.data(Qt.UserRole) == component_id:
				item.setIcon(icon)

	def _build_component_icon(self, component: dict, state_value: str | None = None) -> QIcon:
		"""Construit une icône à partir du rendu canvas du composant (avec mise en cache)."""
		component_id = component.get("id") if isinstance(component, dict) else None
		icon_size = self.components_list.iconSize() if hasattr(self, "components_list") else QSize(44, 44)
		cache_key = f"comp_{component_id}_{state_value}_{icon_size.width()}x{icon_size.height()}"

		if hasattr(self, "_icon_cache") and cache_key in self._icon_cache:
			return self._icon_cache[cache_key]

		if not component_id:
			icon = self._load_icon(component.get("icon", ""), "#d7d7d7", icon_size)
			if hasattr(self, "_icon_cache"):
				self._icon_cache[cache_key] = icon
			return icon

		item = self._create_component_item_for_icon(str(component_id), state_value)
		if item is None:
			icon = self._load_icon(component.get("icon", ""), "#d7d7d7", icon_size)
		else:
			icon = self._render_component_item_icon(item, icon_size)

		if hasattr(self, "_icon_cache"):
			self._icon_cache[cache_key] = icon
		return icon

	def _create_component_item_for_icon(self, component_id: str, state_value: str | None):
		"""Cree un item graphique pour la liste de composants."""
		if component_id == "wire":
			node_a = Node(1, -20.0, 0.0)
			node_b = Node(2, 20.0, 0.0)
			wire = Wire(1, node_a, node_b)
			return WireItem(wire)

		component_cls = {
			"resistor": Resistor,
			"potentiometer": Potentiometer,
			"capacitor": Capacitor,
			"inductor": Inductor,
			"transformer": Transformer,
			"source": VoltageSource,
			"pulse_source": PulseVoltageSource,
			"current_source": CurrentSource,
			"source_vccs": VoltageControlledCurrentSource,
			"source_vcvs": VoltageControlledVoltageSource,
			"source_cccs": CurrentControlledCurrentSource,
			"source_ccvs": CurrentControlledVoltageSource,
			"diode": Diode,
			"zener_diode": ZenerDiode,
			"transistor": Transistor,
			"mosfet": MOSFET,
			"opamp": OpAmp,
			"comparator": Comparator,
			"fuse": Fuse,
			"logic_and": LogicGateAND,
			"logic_or": LogicGateOR,
			"logic_not": LogicGateNOT,
			"logic_nand": LogicGateNAND,
			"logic_nor": LogicGateNOR,
			"logic_xor": LogicGateXOR,
			"switch": Switch,
			"voltmeter": Voltmeter,
			"ammeter": Ammeter,
			"ground": Ground,
		}.get(component_id)

		if component_cls is None:
			return None

		node_a = Node(1, -30.0, -12.0)
		node_b = Node(2, -30.0, 12.0)
		node_c = Node(3, 30.0, -12.0)
		node_d = Node(4, 30.0, 12.0)
		if component_cls is Ground:
			node_a = Node(1, 0.0, 0.0, is_ground=True)
			node_b = node_a
			node_c = None
			node_d = None

		if component_cls is Transformer:
			component = component_cls(1, node_a, node_b, node_c, node_d, 0.0, 0.0)
		elif component_cls in (OpAmp, Comparator, Transistor, MOSFET, Potentiometer) or (issubclass(component_cls, LogicGate) and component_cls is not LogicGateNOT):
			component = component_cls(1, node_a, node_b, node_c, 0.0, 0.0)
		else:
			component = component_cls(1, node_a, node_b, 0.0, 0.0)
		if state_value and hasattr(component, "set_state"):
			component.set_state(str(state_value))
		return create_component_item(component)

	def _render_component_item_icon(self, item, icon_size: QSize) -> QIcon:
		"""Rendu de l'item graphique dans un pixmap d'icone."""
		pixmap = QPixmap(icon_size)
		pixmap.fill(Qt.transparent)
		painter = QPainter(pixmap)
		painter.setRenderHint(QPainter.Antialiasing)
		rect = item.boundingRect()
		width = max(1.0, rect.width())
		height = max(1.0, rect.height())
		available_w = max(1, icon_size.width() - 6)
		available_h = max(1, icon_size.height() - 6)
		scale = min(available_w / width, available_h / height)
		painter.translate(icon_size.width() / 2, icon_size.height() / 2)
		painter.scale(scale, scale)
		option = QStyleOptionGraphicsItem()
		item.paint(painter, option)
		if isinstance(item, WireItem):
			line = item.line()
			painter.setPen(Qt.NoPen)
			painter.setBrush(QColor("#1f2937"))
			node_radius = 2
			painter.drawEllipse(line.p1(), node_radius, node_radius)
			painter.drawEllipse(line.p2(), node_radius, node_radius)
		painter.end()
		return QIcon(pixmap)

	def _scroll_to_category(self, category_key: str) -> None:
		"""Fait defiler jusqu'a l'en-tete de la categorie cible."""
		if self._suppress_category_highlight or self._updating_category_highlight:
			return
		target_data = f"header:{category_key}"
		for row in range(self.components_list.count()):
			item = self.components_list.item(row)
			if item.data(Qt.UserRole) == target_data:
				self.components_list.scrollToItem(item, QListWidget.PositionAtTop)
				return

	def _apply_search_filter(self, text: str) -> None:
		"""Filtre la liste d'elements de circuit selon le texte de recherche."""
		filter_text = text.strip().lower()
		self._set_filter_state(filter_text)
		visible_by_category = self._apply_component_filter(filter_text)
		self._apply_header_visibility(visible_by_category)
		if not self._suppress_category_highlight:
			self._update_highlight_from_scroll()

	def _set_filter_state(self, filter_text: str) -> None:
		"""Ajuste l'etat d'affichage lie au filtrage."""
		self._suppress_category_highlight = bool(filter_text)
		if self._suppress_category_highlight:
			self.category_list.setCurrentRow(-1)

	def _apply_component_filter(self, filter_text: str) -> dict[str, bool]:
		"""Applique le filtre et retourne les categories visibles."""
		visible_by_category = {}
		for row in range(self.components_list.count()):
			item = self.components_list.item(row)
			data = item.data(Qt.UserRole)
			if isinstance(data, str) and data.startswith("header:"):
				category_key = data.split(":", 1)[1]
				item.setHidden(True)
				visible_by_category[category_key] = False
				continue

			label = item.text().lower()
			is_match = filter_text in label if filter_text else True
			item.setHidden(not is_match)
			if is_match:
				category_key = item.data(Qt.UserRole + 1)
				visible_by_category[category_key] = True
		return visible_by_category

	def _apply_header_visibility(self, visible_by_category: dict[str, bool]) -> None:
		"""Met a jour la visibilite des en-tetes de categorie."""
		for row in range(self.components_list.count()):
			item = self.components_list.item(row)
			data = item.data(Qt.UserRole)
			if isinstance(data, str) and data.startswith("header:"):
				category_key = data.split(":", 1)[1]
				item.setHidden(not visible_by_category.get(category_key, False))

	def _update_highlight_from_scroll(self) -> None:
		"""Selectionne la categorie correspondant a la zone visible."""
		if self._suppress_category_highlight:
			return

		top_item = self._find_top_visible_item()
		if top_item is None:
			return

		category_key = None
		data = top_item.data(Qt.UserRole)
		if isinstance(data, str) and data.startswith("header:"):
			category_key = data.split(":", 1)[1]
		else:
			category_key = top_item.data(Qt.UserRole + 1)

		if category_key is None:
			return

		for row in range(self.category_list.count()):
			item = self.category_list.item(row)
			if item.data(Qt.UserRole) == category_key:
				if self.category_list.currentRow() != row:
					self._updating_category_highlight = True
					self.category_list.setCurrentRow(row)
					self._updating_category_highlight = False
				return

	def _find_top_visible_item(self) -> Optional[QListWidgetItem]:
		"""Retourne le premier item visible dans la liste d'elements de circuit."""
		viewport_rect = self.components_list.viewport().rect()
		for row in range(self.components_list.count()):
			item = self.components_list.item(row)
			if item.isHidden():
				continue
			item_rect = self.components_list.visualItemRect(item)
			if item_rect.bottom() >= viewport_rect.top():
				return item
		return None

	def _build_category_widget(self, icon: QIcon, label: str) -> QWidget:
		"""Construit le widget visuel d'une categorie."""
		widget = QWidget()
		widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
		layout = QVBoxLayout(widget)
		layout.setContentsMargins(0, 4, 0, 4)
		layout.setSpacing(2)
		layout.setAlignment(Qt.AlignHCenter)

		icon_label = QLabel()
		icon_label.setObjectName("categoryIcon")
		icon_label.setAlignment(Qt.AlignCenter)
		icon_label.setPixmap(icon.pixmap(32, 32))

		text_label = QLabel(label)
		text_label.setObjectName("categoryText")
		text_label.setAlignment(Qt.AlignCenter)
		text_label.setWordWrap(True)
		text_label.setStyleSheet("font-size: 11px; color: #2a2a2a; margin: 0px;")

		layout.addWidget(icon_label)
		layout.addWidget(text_label)
		return widget

	def _sync_category_item_widths(self) -> None:
		"""Ajuste la largeur des items de categorie a la colonne."""
		viewport_width = self.category_list.viewport().width()
		if viewport_width <= 0:
			return
		for row in range(self.category_list.count()):
			item = self.category_list.item(row)
			item.setSizeHint(QSize(viewport_width, 84))
			widget = self.category_list.itemWidget(item)
			if widget is not None:
				widget.setFixedWidth(viewport_width)
				text_label = widget.findChild(QLabel, "categoryText")
				if text_label is not None:
					text_label.setFixedWidth(max(1, viewport_width))

	def _load_icon(self, relative_path: str, fallback_color: str, size: QSize) -> QIcon:
		"""Charge une icône ou génère un substitut si manquant (avec mise en cache)."""
		cache_key = f"load_{relative_path}_{fallback_color}_{size.width()}x{size.height()}"
		if hasattr(self, "_icon_cache") and cache_key in self._icon_cache:
			return self._icon_cache[cache_key]

		icon_path = self.assets_root / relative_path
		if icon_path.exists():
			pixmap = QPixmap(str(icon_path))
			if not pixmap.isNull():
				icon = QIcon(pixmap)
				if hasattr(self, "_icon_cache"):
					self._icon_cache[cache_key] = icon
				return icon

		pixmap = QPixmap(size)
		pixmap.fill(Qt.transparent)
		painter = QPainter(pixmap)
		painter.setRenderHint(QPainter.Antialiasing)
		painter.setPen(Qt.NoPen)
		painter.setBrush(QColor(fallback_color))
		painter.drawRoundedRect(2, 2, size.width() - 4, size.height() - 4, 6, 6)

		painter.setBrush(QColor(255, 255, 255, 40))
		center = QPointF(size.width() / 2, size.height() / 2)
		painter.drawEllipse(center, size.width() / 4, size.height() / 4)
		painter.end()

		icon = QIcon(pixmap)
		if hasattr(self, "_icon_cache"):
			self._icon_cache[cache_key] = icon
		return icon


class ComponentsListWidget(QListWidget):
	MIME_TYPE = "application/x-component-id"
	NON_DRAGGABLE_COMPONENT_IDS = {"wire"}
	tool_requested = pyqtSignal(str)

	def startDrag(self, supported_actions: Qt.DropActions) -> None:
		"""Demarre le glisser-deposer d'un composant."""
		item = self.currentItem()
		if item is None:
			return

		component_id = item.data(Qt.UserRole)
		if not component_id or (isinstance(component_id, str) and component_id.startswith("header:")):
			return
		self.tool_requested.emit(str(component_id))
		if component_id in self.NON_DRAGGABLE_COMPONENT_IDS:
			return

		mime = QMimeData()
		mime.setData(self.MIME_TYPE, str(component_id).encode("utf-8"))

		drag = QDrag(self)
		drag.setMimeData(mime)
		if not item.icon().isNull():
			drag.setPixmap(item.icon().pixmap(32, 32))
		drag.exec_(supported_actions)
