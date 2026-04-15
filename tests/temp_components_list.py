from pathlib import Path
import sys

from PyQt5.QtWidgets import QApplication

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from view.components_panel import ComponentsPanel

def main() -> None:
    app = QApplication.instance() or QApplication([])
    panel = ComponentsPanel()

    categories = panel._build_default_categories()
    components = panel._build_default_components()

    for category in categories:
        key = category.get("key")
        label_key = category.get("label_key")
        print(f"[{key}] {label_key}")
        for component in components.get(key, []):
            comp_id = component.get("id")
            comp_label = component.get("label_key")
            print(f"  - {comp_id} ({comp_label})")
        print("")

    app.quit()


if __name__ == "__main__":
    main()
