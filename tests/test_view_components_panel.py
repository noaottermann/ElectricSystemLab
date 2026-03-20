from PyQt5.QtWidgets import QApplication

from view.components_panel import ComponentsPanel


def _get_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
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

    assert "Passif" in labels
    assert "Mesure" in labels
