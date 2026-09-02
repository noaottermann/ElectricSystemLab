from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from unittest.mock import patch

from view.components_panel import ComponentsPanel


import sys

def _get_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_components_panel_filter_sources() -> None:
    _get_app()
    panel = ComponentsPanel()
    visible_by_category = panel._apply_component_filter("source")

    assert visible_by_category.get("sources") is True
    assert visible_by_category.get("passive") is False


def test_components_panel_default_labels_are_french() -> None:
    _get_app()
    panel = ComponentsPanel()
    categories = panel._build_default_categories()
    labels = {category["label"] for category in categories}

    assert "Connexions" in labels
    assert "Sources" in labels
    assert "Passifs" in labels


def test_components_panel_drag_requests_dragged_tool() -> None:
    _get_app()
    panel = ComponentsPanel()
    emitted_tools: list[str] = []
    panel.tool_selected.connect(emitted_tools.append)

    target_item = None
    for row in range(panel.components_list.count()):
        item = panel.components_list.item(row)
        if item.data(Qt.UserRole) == "source":
            target_item = item
            break

    assert target_item is not None
    panel.components_list.setCurrentItem(target_item)

    class _FakeDrag:
        def __init__(self, *_args, **_kwargs) -> None:
            self.exec_called = False

        def setMimeData(self, *_args, **_kwargs) -> None:
            return None

        def setPixmap(self, *_args, **_kwargs) -> None:
            return None

        def exec_(self, *_args, **_kwargs) -> None:
            self.exec_called = True

    with patch("view.components_panel.QDrag", _FakeDrag):
        panel.components_list.startDrag(Qt.CopyAction)

    assert emitted_tools == ["source"]
