"""Controleur des operations d'edition."""

from __future__ import annotations

from typing import Callable, Optional

from PyQt5.QtCore import QPointF
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QGraphicsItem

from view.component_item import ComponentItem
from view.node_item import NodeItem
from view.wire_item import WireItem


class EditController:
	"""Gere les actions d'edition et de selection."""

	def __init__(self, window, scene, view=None, app_controller=None) -> None:
		self.window = window
		self.scene = scene
		self.view = view
		self.app_controller = app_controller

	def cut(self) -> None:
		if self.scene is not None:
			self.scene.cut_selection()
		self._refresh_actions()

	def copy(self) -> None:
		if self.scene is not None:
			self.scene.copy_selection()
		self._refresh_actions()

	def paste(self) -> None:
		if self.scene is None:
			return
		if self.view is not None:
			view_rect = self.view.mapToScene(self.view.viewport().rect()).boundingRect()
			self.scene.paste_selection(view_rect=view_rect)
		else:
			self.scene.paste_selection()
		self._refresh_actions()

	def paste_near_cursor(self) -> None:
		if self.scene is None or self.view is None:
			return
		if hasattr(self.scene, "has_clipboard_content") and not self.scene.has_clipboard_content():
			self._refresh_actions()
			return
		cursor_pos = self.view.mapFromGlobal(QCursor.pos())
		cursor_scene_pos = self.view.mapToScene(cursor_pos)
		self.scene.paste_selection(target_scene_pos=cursor_scene_pos)
		self._refresh_actions()

	def duplicate(self) -> None:
		if self.scene is None:
			return
		if not self.scene.copy_selection():
			self._refresh_actions()
			return
		if self.view is not None:
			view_rect = self.view.mapToScene(self.view.viewport().rect()).boundingRect()
			self.scene.paste_selection(view_rect=view_rect)
		else:
			self.scene.paste_selection()
		self._refresh_actions()

	def lock_selection(self) -> None:
		if self.scene is not None:
			self.scene.lock_selection()
		self._refresh_actions()

	def unlock_selection(self) -> None:
		if self.scene is not None:
			self.scene.unlock_selection()
		self._refresh_actions()

	def delete_selection(self) -> None:
		if self.scene is not None:
			self.scene.delete_selection()
		self._refresh_actions()

	def undo(self) -> None:
		if self.scene is not None:
			self.scene.undo_last_action()
		self._refresh_actions()

	def redo(self) -> None:
		if self.scene is not None:
			self.scene.redo_last_action()
		self._refresh_actions()

	def rotate_selection(self, angle_degrees: float) -> None:
		if self.scene is not None:
			self.scene.rotate_selected_components(angle_degrees)
		self._refresh_actions()

	def flip_selection(self) -> None:
		if self.scene is not None:
			self.scene.rotate_selected_components(180)
		self._refresh_actions()

	def select_all(self) -> None:
		if self.scene is None:
			return
		for item in self.scene.items():
			if item.flags() & QGraphicsItem.ItemIsSelectable:
				item.setSelected(True)
		self._refresh_actions()

	def select_none(self) -> None:
		if self.scene is None:
			return
		self.scene.clearSelection()
		self._refresh_actions()

	def select_invert(self) -> None:
		if self.scene is None:
			return
		for item in self.scene.items():
			if item.flags() & QGraphicsItem.ItemIsSelectable:
				item.setSelected(not item.isSelected())
		self._refresh_actions()

	def filter_nodes(self) -> None:
		self._filter_selection(lambda item: isinstance(item, NodeItem))

	def filter_wires(self) -> None:
		self._filter_selection(lambda item: isinstance(item, WireItem))

	def filter_sources(self) -> None:
		def _predicate(item) -> bool:
			return isinstance(item, ComponentItem) and item.component.__class__.__name__ in {
				"VoltageSourceDC",
				"VoltageSourceAC",
				"CurrentSourceDC",
				"CurrentSourceAC",
				"VoltageControlledCurrentSource",
				"CurrentControlledCurrentSource",
				"VoltageControlledVoltageSource",
				"CurrentControlledVoltageSource",
			}

		self._filter_selection(_predicate)

	def filter_resistors(self) -> None:
		self._filter_selection(
			lambda item: isinstance(item, ComponentItem) and item.component.__class__.__name__ == "Resistor"
		)

	def filter_capacitors(self) -> None:
		self._filter_selection(
			lambda item: isinstance(item, ComponentItem) and item.component.__class__.__name__ == "Capacitor"
		)

	def filter_inductors(self) -> None:
		self._filter_selection(
			lambda item: isinstance(item, ComponentItem) and item.component.__class__.__name__ == "Inductor"
		)

	def filter_add(self) -> None:
		if self.app_controller is not None:
			self.app_controller.not_implemented("Filtre supplementaire")

	def invert_x(self) -> None:
		self._mirror_selection(axis="x")

	def invert_y(self) -> None:
		self._mirror_selection(axis="y")

	def invert_xy(self) -> None:
		self._mirror_selection(axis="xy")

	def align_left(self) -> None:
		self._align_selection("left")

	def align_right(self) -> None:
		self._align_selection("right")

	def align_top(self) -> None:
		self._align_selection("top")

	def align_bottom(self) -> None:
		self._align_selection("bottom")

	def distribute_horizontal(self) -> None:
		self._distribute_selection(axis="x")

	def distribute_vertical(self) -> None:
		self._distribute_selection(axis="y")

	def group_items(self) -> None:
		if self.app_controller is not None:
			self.app_controller.not_implemented("Groupement")

	def ungroup_items(self) -> None:
		if self.app_controller is not None:
			self.app_controller.not_implemented("Degroupement")

	def clean_canvas(self) -> None:
		if self.scene is None:
			return
		if hasattr(self.scene, "clean_canvas"):
			self.scene.clean_canvas()
		else:
			if self.app_controller is not None:
				self.app_controller.not_implemented("Nettoyage")
		self._refresh_actions()

	def _filter_selection(self, predicate: Callable[[object], bool]) -> None:
		if self.scene is None:
			return
		selected_items = self.scene.selectedItems()
		if selected_items:
			for item in selected_items:
				if not predicate(item):
					item.setSelected(False)
		else:
			for item in self.scene.items():
				if predicate(item):
					if item.flags() & QGraphicsItem.ItemIsSelectable:
						item.setSelected(True)
		self._refresh_actions()

	def _mirror_selection(self, axis: str) -> None:
		if self.scene is None:
			return
		items = [item for item in self.scene.selectedItems() if isinstance(item, (ComponentItem, NodeItem))]
		if not items:
			return
		self.scene._push_undo_snapshot()
		centers = [item.sceneBoundingRect().center() for item in items]
		center_x = sum(p.x() for p in centers) / len(centers)
		center_y = sum(p.y() for p in centers) / len(centers)

		for item in items:
			pos = item.pos()
			new_x = pos.x()
			new_y = pos.y()
			if axis in ("x", "xy"):
				new_x = center_x - (pos.x() - center_x)
			if axis in ("y", "xy"):
				new_y = center_y - (pos.y() - center_y)
			item.setPos(QPointF(new_x, new_y))
			self._sync_item_model(item)

		self._finalize_transform(items)

	def _align_selection(self, direction: str) -> None:
		if self.scene is None:
			return
		items = [item for item in self.scene.selectedItems() if isinstance(item, (ComponentItem, NodeItem))]
		if len(items) < 2:
			return
		self.scene._push_undo_snapshot()
		rects = [item.sceneBoundingRect() for item in items]
		if direction == "left":
			target = min(rect.left() for rect in rects)
			for item, rect in zip(items, rects):
				delta = target - rect.left()
				item.setPos(item.pos() + QPointF(delta, 0))
				self._sync_item_model(item)
		elif direction == "right":
			target = max(rect.right() for rect in rects)
			for item, rect in zip(items, rects):
				delta = target - rect.right()
				item.setPos(item.pos() + QPointF(delta, 0))
				self._sync_item_model(item)
		elif direction == "top":
			target = min(rect.top() for rect in rects)
			for item, rect in zip(items, rects):
				delta = target - rect.top()
				item.setPos(item.pos() + QPointF(0, delta))
				self._sync_item_model(item)
		elif direction == "bottom":
			target = max(rect.bottom() for rect in rects)
			for item, rect in zip(items, rects):
				delta = target - rect.bottom()
				item.setPos(item.pos() + QPointF(0, delta))
				self._sync_item_model(item)

		self._finalize_transform(items)

	def _distribute_selection(self, axis: str) -> None:
		if self.scene is None:
			return
		items = [item for item in self.scene.selectedItems() if isinstance(item, (ComponentItem, NodeItem))]
		if len(items) < 3:
			return
		self.scene._push_undo_snapshot()
		items.sort(key=lambda item: item.sceneBoundingRect().center().x() if axis == "x" else item.sceneBoundingRect().center().y())
		centers = [item.sceneBoundingRect().center() for item in items]
		if axis == "x":
			start = centers[0].x()
			end = centers[-1].x()
			step = (end - start) / (len(items) - 1)
			for idx, item in enumerate(items):
				target_x = start + step * idx
				delta = target_x - item.sceneBoundingRect().center().x()
				item.setPos(item.pos() + QPointF(delta, 0))
				self._sync_item_model(item)
		else:
			start = centers[0].y()
			end = centers[-1].y()
			step = (end - start) / (len(items) - 1)
			for idx, item in enumerate(items):
				target_y = start + step * idx
				delta = target_y - item.sceneBoundingRect().center().y()
				item.setPos(item.pos() + QPointF(0, delta))
				self._sync_item_model(item)

		self._finalize_transform(items)

	def _sync_item_model(self, item) -> None:
		if isinstance(item, ComponentItem):
			item.update_model_nodes()
		elif isinstance(item, NodeItem):
			item.node.position = (item.pos().x(), item.pos().y())
			if self.scene is not None:
				self.scene.preview_node_move(item.node, item.pos())

	def _finalize_transform(self, items: list[object]) -> None:
		if self.scene is None:
			return
		for item in items:
			if isinstance(item, ComponentItem):
				self.scene.handle_component_move(item)
			elif isinstance(item, NodeItem):
				self.scene.finalize_node_move(item)
		self.scene._merge_overlaps_and_refresh()
		self.scene._sync_free_node_items_from_model()
		self._refresh_actions()

	def _refresh_actions(self) -> None:
		if hasattr(self.window, "_update_transform_actions_visibility"):
			self.window._update_transform_actions_visibility()
