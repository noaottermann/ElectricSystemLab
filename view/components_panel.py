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
    QVBoxLayout,
    QWidget,
)


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

		layout = QHBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(0)

		self.category_list = QListWidget()
		self.category_list.setObjectName("categoryList")
		self.category_list.setViewMode(QListWidget.ListMode)
		self.category_list.setFixedWidth(82)
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
		self.components_list.setIconSize(QSize(28, 28))
		self.components_list.setSpacing(4)
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
		layout.setContentsMargins(0, 8, 0, 8)
		layout.addWidget(self.category_list)
		return frame

	def _wrap_components_list(self) -> QFrame:
		"""Construit la colonne des composants."""
		frame = QFrame()
		frame.setObjectName("componentsPane")
		layout = QVBoxLayout(frame)
		layout.setContentsMargins(10, 8, 10, 8)

		title = QLabel("Composants")
		title.setObjectName("componentsTitle")
		layout.addWidget(title)

		self.search_input = QLineEdit()
		self.search_input.setPlaceholderText("Rechercher des composants")
		self.search_input.textChanged.connect(self._apply_search_filter)
		layout.addWidget(self.search_input)

		layout.addWidget(self.components_list, 1)
		return frame

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
				padding: 6px;
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
			QLabel#componentsTitle {
				color: #2a2a2a;
				font-size: 14px;
				font-weight: 600;
				padding: 4px 2px;
			}
			"""
		)

		base_font = QFont("Segoe UI", 10)
		self.setFont(base_font)

	def _build_default_categories(self) -> list[dict]:
		"""Construit la liste des categories par defaut."""
		return [
			{
				"key": "connections",
				"label": "Connexions",
				"icon": "categories/connections.png",
				"color": "#7a6a3a",
			},
			{
				"key": "sources",
				"label": "Sources",
				"icon": "categories/sources.png",
				"color": "#f25f5c",
			},
			{
				"key": "passive",
				"label": "Passifs",
				"icon": "categories/passive.png",
				"color": "#247ba0",
			},
		]

	def _build_default_components(self) -> dict[str, list[dict]]:
		"""Construit les composants par defaut affiches dans la liste."""
		return {
			"connections": [
				{
					"id": "wire",
					"label": "Fil",
					"icon": "components/placeholder.png",
				},
			],
			"sources": [
				{
					"id": "source_dc",
					"label": "Source DC",
					"icon": "components/source_dc.png",
				},
				{
					"id": "source_ac",
					"label": "Source AC",
					"icon": "components/source_ac.png",
				},
			],
			"passive": [
				{
					"id": "resistor",
					"label": "Resistance",
					"icon": "components/resistor.png",
				},
				{
					"id": "capacitor",
					"label": "Condensateur",
					"icon": "components/capacitor.png",
				},
				{
					"id": "inductor",
					"label": "Inductance",
					"icon": "components/inductor.png",
				},
			],
		}

	def _populate_categories(self) -> None:
		"""Remplit la liste des categories disponibles."""
		self.category_list.clear()
		for category in self._category_data:
			icon = self._load_icon(category["icon"], category["color"], QSize(24, 24))
			item = QListWidgetItem()
			item.setToolTip(category["label"])
			item.setData(Qt.UserRole, category["key"])
			item.setSizeHint(QSize(82, 72))
			self.category_list.addItem(item)
			self.category_list.setItemWidget(
				item, self._build_category_widget(icon, category["label"])
			)

		self._sync_category_item_widths()

	def _on_category_changed(self, current: Optional[QListWidgetItem], _previous: Optional[QListWidgetItem]) -> None:
		"""Fait defiler la liste des composants selon la categorie active."""
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
		self.tool_selected.emit(component_id)

	def _populate_components_all(self) -> None:
		"""Remplit la liste des composants pour toutes les categories."""
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
		header_item = QListWidgetItem(category["label"])
		header_item.setData(Qt.UserRole, f"header:{category['key']}")
		header_item.setFlags(Qt.NoItemFlags)
		header_item.setSizeHint(QSize(160, 26))
		self.components_list.addItem(header_item)

	def _add_empty_category(self) -> None:
		"""Ajoute une ligne vide lorsqu'une categorie n'a pas de composants."""
		empty_item = QListWidgetItem("Aucun composant")
		empty_item.setFlags(Qt.NoItemFlags)
		empty_item.setSizeHint(QSize(160, 22))
		self.components_list.addItem(empty_item)

	def _add_component_row(self, component: dict, category_key: str) -> None:
		"""Ajoute une ligne pour un composant."""
		icon = self._load_icon(component["icon"], "#d7d7d7", QSize(28, 28))
		item = QListWidgetItem(icon, component["label"])
		item.setData(Qt.UserRole, component["id"])
		item.setData(Qt.UserRole + 1, category_key)
		item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
		item.setSizeHint(QSize(160, 38))
		self.components_list.addItem(item)

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
		"""Filtre la liste de composants selon le texte de recherche."""
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
		"""Retourne le premier item visible dans la liste des composants."""
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
		icon_label.setPixmap(icon.pixmap(24, 24))

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
			item.setSizeHint(QSize(viewport_width, 72))
			widget = self.category_list.itemWidget(item)
			if widget is not None:
				widget.setFixedWidth(viewport_width)
				text_label = widget.findChild(QLabel, "categoryText")
				if text_label is not None:
					text_label.setFixedWidth(max(1, viewport_width))

	def _load_icon(self, relative_path: str, fallback_color: str, size: QSize) -> QIcon:
		"""Charge un icone ou genere un substitut si manquant."""
		icon_path = self.assets_root / relative_path
		if icon_path.exists():
			pixmap = QPixmap(str(icon_path))
			if not pixmap.isNull():
				return QIcon(pixmap)

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

		return QIcon(pixmap)


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
		if component_id in self.NON_DRAGGABLE_COMPONENT_IDS:
			self.tool_requested.emit(str(component_id))
			return

		mime = QMimeData()
		mime.setData(self.MIME_TYPE, str(component_id).encode("utf-8"))

		drag = QDrag(self)
		drag.setMimeData(mime)
		if not item.icon().isNull():
			drag.setPixmap(item.icon().pixmap(32, 32))
		drag.exec_(supported_actions)
