from PyQt5.QtCore import QSize, Qt, QTimer
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QHBoxLayout,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QShortcut,
    QStatusBar,
    QStyle,
    QToolBar,
    QWidget,
)
from controller.app_controller import AppController
from controller.circuit_controller import CircuitController
from controller.edit_controller import EditController
from controller.file_controller import FileController
from controller.simulation_controller import SimulationController
from model.components import (
    Capacitor,
    CurrentControlledCurrentSource,
    CurrentSourceAC,
    CurrentSourceDC,
    Diode,
    Inductor,
    LED,
    Resistor,
    VoltageControlledCurrentSource,
    VoltageSourceAC,
    VoltageSourceDC,
)
from model.dipole import Dipole
from utils.translator import Translator
from utils.assets import get_asset_path, get_logo_icon, logo_exists
from view.canvas import CircuitView, CircuitScene
from view.components_panel import ComponentsPanel
from view.graphs_panel import GraphPanel

class MainWindow(QMainWindow):
    """
    Fenêtre principale de Nodal
    """

    def __init__(self, model=None) -> None:
        """Initialise la fenêtre principale et ses actions."""
        super().__init__()
        self.model = model
        self.custom_actions: dict[str, QAction] = {}
        self.init_ui_structure()
        self._init_controllers()
        self.retranslate_ui()

    def init_ui_structure(self) -> None:
        """Crée la structure principale de l'interface."""
        self._configure_window_geometry()
        self._set_window_logo()
        self.include_simulation_in_export = False
        
        # Initialisation
        self.create_actions()
        self.create_shortcuts()
        self.setup_menus()
        self.setup_toolbar()

        # Barre de statut
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Widget central
        self._setup_central_widget()

        self._realtime_auto_open_graph_once = False
        self._realtime_timer_interval_ms = 30
        self.realtime_timer = QTimer(self)
        self.realtime_timer.setSingleShot(False)
        self.realtime_timer.timeout.connect(self._on_realtime_tick)

    def _configure_window_geometry(self) -> None:
        """Calcule et applique la taille initiale de la fenêtre."""
        primary_screen = QApplication.primaryScreen()
        if primary_screen is not None:
            screen_geometry = primary_screen.availableGeometry()
            screen_width = screen_geometry.width()
            screen_height = screen_geometry.height()
        else:
            screen_width = 1024
            screen_height = 768
        width = int(screen_width * 0.8)
        height = int(screen_height * 0.8)
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.setGeometry(x, y, width, height)

    def _set_window_logo(self) -> None:
        """Définit le logo de la fenêtre principale."""
        if logo_exists():
            logo_icon = get_logo_icon()
            if not logo_icon.isNull():
                self.setWindowIcon(logo_icon)

    def _setup_central_widget(self) -> None:
        """Construit le widget central et ses panneaux."""
        self.scene = CircuitScene(self.model)
        self.view = CircuitView(self.scene)
        self.scene.selectionChanged.connect(self._update_transform_actions_visibility)

        self.components_panel = ComponentsPanel()
        self.components_panel.setMinimumWidth(200)
        self.components_panel.setMaximumWidth(300)
        self.components_panel.tool_selected.connect(self.set_tool)
        self.graph_panel = GraphPanel()
        self.graph_panel.setMinimumWidth(200)
        self.graph_panel.setMaximumWidth(300)
        self.graph_panel.setVisible(False)

        # Crée le bouton Graphiques flottant
        self.graphics_button = QPushButton()
        self.graphics_button.setFixedSize(116, 132)  # Compact mais lisible
        self.graphics_button.clicked.connect(self.on_toggle_view_graphs)
        self.graphics_button.setParent(self)
        self.graphics_button.setStyleSheet(
            """
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 12px;
                padding: 10px 12px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1f618d;
            }
            """
        )
        graphs_icon_path = get_asset_path("panels/graphs.png")
        if graphs_icon_path.exists():
            self.graphics_button.setIcon(QIcon(str(graphs_icon_path)))
            self.graphics_button.setIconSize(QSize(72, 72))
            self.graphics_button.setText("")

        central_widget = QWidget()
        central_layout = QHBoxLayout(central_widget)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(self.components_panel)
        central_layout.addWidget(self.view, 1)
        central_layout.addWidget(self.graph_panel)
        self.setCentralWidget(central_widget)

        # Bouton de repli externe, collé à gauche de l'onglet Graphiques
        self.graph_collapse_button = QPushButton(">>>", central_widget)
        self.graph_collapse_button.setFixedSize(36, 24)
        self.graph_collapse_button.setVisible(False)
        self.graph_collapse_button.clicked.connect(lambda: self._set_graph_panel_visible(False))
        self.graph_collapse_button.setStyleSheet(
            """
            QPushButton {
                background-color: #2c3e50;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1f2d3a;
            }
            QPushButton:pressed {
                background-color: #17212b;
            }
            """
        )

        # Ancre la barre d'outils dans la zone centrale pour suivre la géométrie du panneau et de la vue
        if hasattr(self, "toolbar"):
            self.toolbar.setParent(central_widget)
            self.toolbar.show()
            self._update_toolbar_geometry()
            self._update_transform_actions_visibility()
        
        # Place le focus initial sur la vue du circuit plutôt que sur la barre de recherche
        self.view.setFocus()

    def _init_controllers(self) -> None:
        """Initialise les controleurs MVC et leurs dependances."""
        self.app_controller = AppController(self, view=getattr(self, "view", None))
        self.file_controller = FileController(self, self.model, getattr(self, "scene", None))
        self.edit_controller = EditController(
            self,
            getattr(self, "scene", None),
            view=getattr(self, "view", None),
            app_controller=self.app_controller,
        )
        self.circuit_controller = CircuitController(
            self,
            getattr(self, "scene", None),
            getattr(self, "view", None),
            app_controller=self.app_controller,
        )
        self.simulation_controller = SimulationController(
            self.model,
            app_controller=self.app_controller,
        )

    def resizeEvent(self, event) -> None:
        """Ajuste la barre d'outils lors des redimensionnements."""
        super().resizeEvent(event)
        self._update_toolbar_geometry()

    def closeEvent(self, event) -> None:
        """Nettoie les connexions Qt lors de la fermeture."""
        if hasattr(self, "realtime_timer") and self.realtime_timer.isActive():
            self.realtime_timer.stop()
        if hasattr(self, "simulation_controller") and self.simulation_controller is not None:
            self.simulation_controller.stop_realtime_transient(status_message=None)

        # Pendant la fermeture, des signaux Qt en attente peuvent encore arriver pendant la destruction de la scène
        try:
            if hasattr(self, "scene") and self.scene is not None:
                self.scene.selectionChanged.disconnect(self._update_transform_actions_visibility)
        except (RuntimeError, TypeError):
            pass
        super().closeEvent(event)

    def _update_toolbar_geometry(self) -> None:
        """Positionne la barre d'outils en bas du widget central et le bouton flottant."""
        if not hasattr(self, "toolbar") or self.toolbar is None:
            return
        if self.centralWidget() is None:
            return

        central_widget = self.centralWidget()
        content_width = central_widget.width()
        content_height = central_widget.height()
        if content_width <= 0 or content_height <= 0:
            return

        # Positionne le bouton Graphiques aux 2/3 de la hauteur de l'écran, tout à droite
        if hasattr(self, "graphics_button") and self.graphics_button is not None:
            button_width = self.graphics_button.width()
            button_height = self.graphics_button.height()

            screen_geometry = None
            screen = self.screen()
            if screen is not None:
                screen_geometry = screen.availableGeometry()
            elif QApplication.primaryScreen() is not None:
                screen_geometry = QApplication.primaryScreen().availableGeometry()

            if screen_geometry is not None:
                btn_x = screen_geometry.right() - button_width - 10
                btn_y = screen_geometry.top() + int(screen_geometry.height() * 1 / 3) - button_height // 2
            else:
                btn_x = self.width() - button_width - 10
                btn_y = int(self.height() * 1 / 3 - button_height / 2)

            btn_x = max(0, btn_x)
            btn_y = max(0, btn_y)

            self.graphics_button.move(btn_x, btn_y)
            self.graphics_button.raise_()

        # Positionne le bouton de repli juste a gauche de l'onglet Graphiques quand il est visible
        if (
            hasattr(self, "graph_collapse_button")
            and self.graph_collapse_button is not None
            and hasattr(self, "graph_panel")
            and self.graph_panel is not None
            and self.graph_panel.isVisible()
        ):
            panel_geo = self.graph_panel.geometry()
            button_width = self.graph_collapse_button.width()
            button_height = self.graph_collapse_button.height()
            btn_x = max(0, panel_geo.x() - button_width)
            btn_y = max(0, panel_geo.y())
            if button_height > panel_geo.height():
                btn_y = max(0, panel_geo.y() + panel_geo.height() - button_height)
            self.graph_collapse_button.move(btn_x, btn_y)
            self.graph_collapse_button.raise_()

        panel_width = 0
        if hasattr(self, "components_panel") and self.components_panel.isVisible():
            panel_width = self.components_panel.width()

        right_panel_width = 0
        if hasattr(self, "graph_panel") and self.graph_panel.isVisible():
            right_panel_width = self.graph_panel.width()

        x = min(panel_width, max(0, content_width - 1))
        remaining_width = content_width - x - right_panel_width
        if remaining_width <= 0:
            return

        desired_width = content_width - panel_width - right_panel_width
        min_width = min(280, remaining_width)
        toolbar_width = max(min_width, desired_width)
        toolbar_width = min(toolbar_width, remaining_width)

        toolbar_height = max(self.toolbar.sizeHint().height(), 44)
        y = max(0, content_height - toolbar_height)

        self.toolbar.setGeometry(x, y, toolbar_width, toolbar_height)
        self.toolbar.raise_()

    def _set_graph_panel_visible(self, visible: bool) -> None:
        """Affiche/masque le panneau Graphiques et synchronise le bouton flottant."""
        if not hasattr(self, "graph_panel") or self.graph_panel is None:
            return
        self.graph_panel.setVisible(visible)

        # En mode temps reel, la simulation ne tourne que lorsque le panneau Graphiques est ouvert.
        if hasattr(self, "simulation_controller") and self.simulation_controller is not None:
            if self.simulation_controller.is_realtime_running:
                if visible:
                    if hasattr(self, "realtime_timer") and not self.realtime_timer.isActive():
                        self.realtime_timer.start(self._realtime_timer_interval_ms)
                else:
                    if hasattr(self, "realtime_timer") and self.realtime_timer.isActive():
                        self.realtime_timer.stop()

        if hasattr(self, "graphics_button") and self.graphics_button is not None:
            self.graphics_button.setVisible(not visible)

        if hasattr(self, "graph_collapse_button") and self.graph_collapse_button is not None:
            self.graph_collapse_button.setVisible(visible)

        action = self.custom_actions.get("action_show_graphs")
        if action is not None:
            action.setChecked(visible)

        self._update_toolbar_geometry()

    def _update_transform_actions_visibility(self) -> None:
        """Ajuste la visibilite des actions selon la selection."""
        if not hasattr(self, "scene"):
            return

        try:
            selected_items = self.scene.selectedItems()
        except RuntimeError:
            # L'enveloppe de la scène peut déjà être détruite pendant la fermeture
            return

        dipole_items = [
            item for item in selected_items
            if hasattr(item, "component") and isinstance(item.component, Dipole)
        ]
        dipole_count = len(dipole_items)
        has_dipole = dipole_count > 0
        has_single_dipole = dipole_count == 1
        has_unlocked_dipole = any(
            hasattr(item, "component") and not getattr(item, "is_locked", lambda: False)()
            for item in selected_items
        )
        has_selection = bool(selected_items)
        has_deletable = any(
            not getattr(item, "is_locked", lambda: False)() for item in selected_items
        )
        has_locked = any(
            getattr(item, "is_locked", lambda: False)() for item in selected_items
        )
        has_unlocked = any(
            not getattr(item, "is_locked", lambda: False)() for item in selected_items
        )

        paste_enabled = False
        if hasattr(self.scene, "has_clipboard_content"):
            paste_enabled = self.scene.has_clipboard_content()

        if "action_paste" in self.custom_actions:
            self.custom_actions["action_paste"].setEnabled(paste_enabled)
        if hasattr(self, "toolbar_paste_action") and self.toolbar_paste_action is not None:
            self.toolbar_paste_action.setEnabled(paste_enabled)

        if "action_duplicate" in self.custom_actions:
            self.custom_actions["action_duplicate"].setVisible(has_selection)
        if hasattr(self, "toolbar_duplicate_action") and self.toolbar_duplicate_action is not None:
            self.toolbar_duplicate_action.setVisible(has_selection)

        if "action_edit_value" in self.custom_actions:
            self.custom_actions["action_edit_value"].setVisible(has_dipole)
            self.custom_actions["action_edit_value"].setEnabled(has_single_dipole)
        if hasattr(self, "toolbar_edit_value_action") and self.toolbar_edit_value_action is not None:
            self.toolbar_edit_value_action.setVisible(has_dipole)
            self.toolbar_edit_value_action.setEnabled(has_single_dipole)
        if hasattr(self, "toolbar_edit_value_separator_left") and self.toolbar_edit_value_separator_left is not None:
            self.toolbar_edit_value_separator_left.setVisible(has_dipole)

        if "action_lock" in self.custom_actions:
            self.custom_actions["action_lock"].setVisible(has_selection)
            self.custom_actions["action_lock"].setEnabled(has_unlocked)
        if hasattr(self, "toolbar_lock_action") and self.toolbar_lock_action is not None:
            self.toolbar_lock_action.setVisible(has_selection)
            self.toolbar_lock_action.setEnabled(has_unlocked)
        if "action_unlock" in self.custom_actions:
            self.custom_actions["action_unlock"].setVisible(has_selection)
            self.custom_actions["action_unlock"].setEnabled(has_locked)
        if hasattr(self, "toolbar_unlock_action") and self.toolbar_unlock_action is not None:
            self.toolbar_unlock_action.setVisible(has_selection)
            self.toolbar_unlock_action.setEnabled(has_locked)
        if hasattr(self, "toolbar_lock_separator") and self.toolbar_lock_separator is not None:
            self.toolbar_lock_separator.setVisible(has_selection)

        if "action_rotate" in self.custom_actions:
            self.custom_actions["action_rotate"].setVisible(has_unlocked_dipole)
        if "action_flip" in self.custom_actions:
            self.custom_actions["action_flip"].setVisible(has_unlocked_dipole)
        if hasattr(self, "toolbar_transform_separator") and self.toolbar_transform_separator is not None:
            self.toolbar_transform_separator.setVisible(has_unlocked_dipole)
        if hasattr(self, "toolbar_delete_separator") and self.toolbar_delete_separator is not None:
            self.toolbar_delete_separator.setVisible(has_deletable)
        if hasattr(self, "toolbar_delete_action") and self.toolbar_delete_action is not None:
            self.toolbar_delete_action.setVisible(has_deletable)

    def _get_selected_dipole_items(self) -> list:
        """Retourne les items selectionnes qui correspondent a des dipoles."""
        if not hasattr(self, "scene"):
            return []
        try:
            selected_items = self.scene.selectedItems()
        except RuntimeError:
            return []
        return [
            item for item in selected_items
            if hasattr(item, "component") and isinstance(item.component, Dipole)
        ]

    def _get_edit_value_config(self, component: Dipole) -> tuple[str, str] | None:
        """Retourne la cle parametre et l'unite principale pour un dipole."""
        if isinstance(component, Resistor):
            return "resistance", "Ohm"
        if isinstance(component, Capacitor):
            return "capacitance", "F"
        if isinstance(component, Inductor):
            return "inductance", "H"
        if isinstance(component, VoltageSourceDC):
            return "dc_voltage", "V"
        if isinstance(component, VoltageSourceAC):
            return "amplitude", "V"
        if isinstance(component, CurrentSourceDC):
            return "dc_current", "A"
        if isinstance(component, CurrentSourceAC):
            return "amplitude", "A"
        if isinstance(component, VoltageControlledCurrentSource):
            return "transconductance", "S"
        if isinstance(component, CurrentControlledCurrentSource):
            return "gain", "A/A"
        if isinstance(component, (Diode, LED)):
            return "saturation_current", "A"
        return None

    def create_actions(self) -> None:
        """Crée toutes les actions de la fenêtre principale."""
        self._create_file_actions()
        self._create_edit_actions()
        self._create_view_actions()
        self._create_options_actions()
        self._create_simulation_actions()

    def _create_simulation_actions(self) -> None:
        """Cree les actions du menu Simulation."""
        self._make_action("action_sim_run_dc", None, self.on_run_simulation_dc)
        self._make_action("action_sim_run_transient", None, self.on_run_simulation_transient)
        self._make_action("action_sim_run_realtime", None, self.on_run_simulation_realtime)
        self._make_action("action_sim_stop_realtime", None, self.on_stop_simulation_realtime)
        self._make_action("action_sim_export_results", None, self.on_export_simulation_results)
        self._make_action("action_sim_export_csv", None, self.on_export_transient_csv)
        self.custom_actions["action_sim_stop_realtime"].setEnabled(False)

    def _make_action(self, key, shortcut=None, slot=None) -> QAction:
        """Cree une action Qt et l'enregistre dans le dictionnaire."""
        action = QAction('', self)
        if shortcut:
            action.setShortcut(shortcut)
        if slot:
            action.triggered.connect(slot)
        # L'action est stockée dans le dictionnaire avec sa clé de traduction comme identifiant
        self.custom_actions[key] = action
        return action

    def _create_file_actions(self) -> None:
        """Cree les actions du menu Fichier."""
        self._make_action("action_new_file", "Ctrl+N", self.on_new_file)
        self._make_action("action_new_window", "Ctrl+Shift+N", self.on_new_window)
        self._make_action("action_open", "Ctrl+O", self.on_open_file)
        self._make_action("action_save", "Ctrl+S", self.on_save_file)
        self._make_action("action_save_as", "Ctrl+Shift+S", self.on_save_as)
        self._make_action("action_import", None, self.on_import)
        self._make_action("action_export", None, self.on_export)
        self._make_action("action_history", None, self.on_version_history)
        self._make_action("action_quit", "Ctrl+Q", self.close)

    def _create_edit_actions(self) -> None:
        """Cree les actions du menu Edition."""
        self._make_action("action_undo", QKeySequence.Undo, self.undo_last_action)
        self._make_action("action_redo", QKeySequence.Redo, self.redo_last_action)
        self._make_action("action_cut", QKeySequence.Cut, self.on_cut)
        self._make_action("action_copy", QKeySequence.Copy, self.on_copy)
        self._make_action("action_paste", None, self.on_paste)
        self._make_action("action_duplicate", None, self.on_duplicate)
        self._make_action("action_edit_value", None, self.on_edit_value)
        self._make_action("action_lock", None, self.on_lock)
        self._make_action("action_unlock", None, self.on_unlock)
        self._make_action("action_delete", QKeySequence.Delete, self.delete_selected_items)
        self._make_action("action_rotate", None, self.rotate_selected_components)
        self._make_action("action_flip", None, self.flip_selected_components)

        self._make_action("action_select_all", "Ctrl+A", self.on_select_all)
        self._make_action("action_select_none", "Ctrl+D", self.on_select_none)
        self._make_action("action_select_invert", "Ctrl+I", self.on_select_invert)
        self._make_action("action_filter_nodes", None, self.on_filter_nodes)
        self._make_action("action_filter_wires", None, self.on_filter_wires)
        self._make_action("action_filter_sources", None, self.on_filter_sources)
        self._make_action("action_filter_resistors", None, self.on_filter_resistors)
        self._make_action("action_filter_capacitors", None, self.on_filter_capacitors)
        self._make_action("action_filter_inductors", None, self.on_filter_inductors)
        self._make_action("action_filter_add", None, self.on_filter_add)

        self._make_action("action_invert_x", None, self.on_invert_x)
        self._make_action("action_invert_y", None, self.on_invert_y)
        self._make_action("action_invert_xy", None, self.on_invert_xy)

        self._make_action("action_align_left", None, self.on_align_left)
        self._make_action("action_align_right", None, self.on_align_right)
        self._make_action("action_align_top", None, self.on_align_top)
        self._make_action("action_align_bottom", None, self.on_align_bottom)
        self._make_action("action_distribute_horiz", None, self.on_distribute_horiz)
        self._make_action("action_distribute_vertic", None, self.on_distribute_vertic)

        self._make_action("action_group", None, self.on_group_items)
        self._make_action("action_ungroup", None, self.on_ungroup_items)
        self._make_action("action_clean", None, self.on_clean_canvas)

    def _create_view_actions(self) -> None:
        """Cree les actions du menu Affichage."""
        self._make_action("action_zoom_in", "Ctrl++", self.on_zoom_in)
        self._make_action("action_zoom_out", "Ctrl+-", self.on_zoom_out)
        self._make_action("action_toggle_grid", None, self.on_toggle_grid)
        self._make_action("action_snap_grid", None, self.on_snap_grid)
        self._make_action("action_grid_size", None, self.on_grid_size)

        self._make_action("action_show_labels", None, self.on_toggle_labels)
        self._make_action("action_show_nodes", None, self.on_toggle_nodes)
        self._make_action("action_show_wire_dir", None, self.on_toggle_wire_dir)

        self._make_action("action_center_select", None, self.on_center_selection)
        self._make_action("action_reset_zoom", None, self.on_reset_zoom)
        self._make_action("action_fullscreen", None, self.on_toggle_fullscreen)
        self._make_action("action_highlight_short", None, self.on_highlight_short_circuit)
        self._make_action("action_show_components", None, self.on_toggle_view_components)
        self._make_action("action_show_sim", None, self.on_toggle_view_simulation)
        self._make_action("action_show_graphs", None, self.on_toggle_view_graphs)
        self.custom_actions["action_show_graphs"].setCheckable(True)
        self.custom_actions["action_show_graphs"].setChecked(False)
        self._make_action("action_show_examples", None, self.on_toggle_view_examples)
        self._make_action("action_show_toolbar", None, self.on_toggle_view_toolbar)
        self._make_action("action_theme_dark", None, self.set_dark_mode)
        self._make_action("action_theme_light", None, self.set_light_mode)

    def _create_options_actions(self) -> None:
        """Cree les actions du menu Options."""
        self._make_action("action_auto_save_int", None, self.on_set_autosave_interval)
        self._make_action("action_toggle_auto_save", None, self.on_toggle_autosave)
        self._make_action("action_lang_fr", None, self.set_lang_fr)
        self._make_action("action_lang_en", None, self.set_lang_en)
        self._make_action("action_restore_session", None, self.on_restore_session)

        self._make_action("action_unit_si", None, self.on_set_unit_si)
        self._make_action("action_unit_eng", None, self.on_set_unit_eng)
        self._make_action("action_unit_compact", None, self.on_set_unit_compact)

        self._make_action("action_precision", None, self.on_set_precision)
        self._make_action("action_sci_notation", None, self.on_toggle_sci_notation)
        self._make_action("action_cross_cursor", None, self.on_toggle_cross_cursor)
        self._make_action("action_enable_anim", None, self.on_toggle_animations)
        self._make_action("action_allow_overlap", None, self.on_toggle_overlap)
        self._make_action("action_disable_editing", None, self.on_toggle_editing)
        self._make_action("action_conv_current", None, self.on_toggle_conv_current)

        self._make_action("action_grid_export", None, self.on_toggle_grid_export)
        self._make_action("action_sim_export", None, self.on_toggle_sim_export)
        self.custom_actions["action_sim_export"].setCheckable(True)
        self.custom_actions["action_sim_export"].setChecked(self.include_simulation_in_export)
        self._make_action("action_bg_color", None, self.on_change_bg_color)
        self._make_action("action_keybinds", None, self.on_show_keybinds)

        self._make_action("action_color_pos", None, self.on_set_color_positive)
        self._make_action("action_color_neg", None, self.on_set_color_negative)
        self._make_action("action_color_neu", None, self.on_set_color_neutral)
        self._make_action("action_color_sel", None, self.on_set_color_selected)
        self._make_action("action_color_cur", None, self.on_set_color_current)

    def set_dark_mode(self) -> None:
        """Active le theme sombre."""
        self.change_theme("dark")

    def set_light_mode(self) -> None:
        """Active le theme clair."""
        self.change_theme("light")

    def change_theme(self, theme_name: str) -> None:
        """Change le theme visuel de la fenetre."""
        if theme_name == "dark":
            self.setStyleSheet("QMainWindow { background-color: #2b2b2b; color: white; }")
            self.view.setBackgroundBrush(Qt.black)
        else:
            self.setStyleSheet("")
            self.view.setBackgroundBrush(Qt.white)

    def create_shortcuts(self) -> None:
        """Definit les raccourcis clavier globaux."""

        # Touche de suppression
        self.shortcut_delete = QShortcut(QKeySequence("Del"), self)
        self.shortcut_delete.activated.connect(self.delete_selected_items)

        # Collage près du curseur uniquement via Ctrl+V
        self.shortcut_paste_near_cursor = QShortcut(QKeySequence.Paste, self)
        self.shortcut_paste_near_cursor.activated.connect(self.on_paste_near_cursor)

        # Retour rapide a l'outil de selection
        self.shortcut_tool_pointer = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self.shortcut_tool_pointer.activated.connect(self._reset_tool_selection)
        
        # Les raccourcis d'outils sont supprimes pour privilegier la liste des composants.

    def set_tool(self, tool_name: str) -> None:
        """Change l'outil actif via le controleur."""
        if hasattr(self, "circuit_controller") and self.circuit_controller is not None:
            self.circuit_controller.set_tool(tool_name)
            return
        self._apply_tool(tool_name)

    def _apply_tool(self, tool_name: str) -> None:
        """Applique directement l'outil actif pour la scene et la vue."""

        # Scène
        if hasattr(self, "scene"):
            self.scene.set_tool(tool_name)

        # Vue
        if hasattr(self, "view"):
            self.view.set_tool_mode(tool_name)
            if hasattr(self.view, "clear_tool_preview"):
                self.view.clear_tool_preview()
            if hasattr(self, "scene") and hasattr(self.scene, "_clear_item_cursors"):
                self.scene._clear_item_cursors()

        # Change le curseur
        if tool_name == "pointer":
            self.setCursor(Qt.ArrowCursor)
            if hasattr(self, "view"):
                self.view.setCursor(Qt.ArrowCursor)
                self.view.viewport().setCursor(Qt.ArrowCursor)
        else:
            self.setCursor(Qt.CrossCursor)
            if hasattr(self, "view"):
                self.view.setCursor(Qt.CrossCursor)
                self.view.viewport().setCursor(Qt.CrossCursor)

    def _reset_tool_selection(self) -> None:
        """Revient a l'outil pointeur et efface la selection des composants."""
        self.set_tool("pointer")
        if hasattr(self, "components_panel") and self.components_panel is not None:
            if hasattr(self.components_panel, "clear_component_selection"):
                self.components_panel.clear_component_selection()


    def setup_menus(self) -> None:
        """Cree les menus de la fenetre principale."""
        menubar = self.menuBar()

        # Menus
        self.menu_file = menubar.addMenu('')
        self.menu_edit = menubar.addMenu('')
        self.menu_view = menubar.addMenu('')
        self.menu_options = menubar.addMenu('')
        self.menu_simulation = menubar.addMenu('')
        
        self._setup_file_menu()
        self._setup_edit_menu()
        self._setup_view_menu()
        self._setup_options_menu()
        self._setup_simulation_menu()

    def _setup_simulation_menu(self) -> None:
        """Construit le menu Simulation."""
        self.menu_simulation.addAction(self.custom_actions["action_sim_run_dc"])
        self.menu_simulation.addAction(self.custom_actions["action_sim_run_transient"])
        self.menu_simulation.addAction(self.custom_actions["action_sim_run_realtime"])
        self.menu_simulation.addAction(self.custom_actions["action_sim_stop_realtime"])
        self.menu_simulation.addSeparator()
        self.menu_simulation.addAction(self.custom_actions["action_sim_export_results"])
        self.menu_simulation.addAction(self.custom_actions["action_sim_export_csv"])

    def _setup_file_menu(self) -> None:
        """Construit le menu Fichier."""
        self.menu_file.addAction(self.custom_actions["action_new_file"])
        self.menu_file.addAction(self.custom_actions["action_new_window"])
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.custom_actions["action_open"])
        self.menu_recent_files = self.menu_file.addMenu('') 
        self.placeholder_recent_files = QAction("example.json", self)
        self.menu_recent_files.addAction(self.placeholder_recent_files)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.custom_actions["action_save"])
        self.menu_file.addAction(self.custom_actions["action_save_as"])
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.custom_actions["action_import"])
        self.menu_file.addAction(self.custom_actions["action_export"])
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.custom_actions["action_history"])
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.custom_actions["action_quit"])

    def _setup_edit_menu(self) -> None:
        """Construit le menu Edition."""
        self.menu_edit.addAction(self.custom_actions["action_undo"])
        self.menu_edit.addAction(self.custom_actions["action_redo"])
        self.menu_edit.addAction(self.custom_actions["action_cut"])
        self.menu_edit.addAction(self.custom_actions["action_copy"])
        self.menu_edit.addAction(self.custom_actions["action_paste"])
        self.menu_edit.addSeparator()

        self.menu_edit.addAction(self.custom_actions["action_select_all"])
        self.menu_edit.addAction(self.custom_actions["action_select_none"])
        self.menu_edit.addAction(self.custom_actions["action_select_invert"])
        self.menu_selection_filter = self.menu_edit.addMenu('')
        self.menu_selection_filter.addAction(self.custom_actions["action_filter_nodes"])
        self.menu_selection_filter.addAction(self.custom_actions["action_filter_wires"])
        self.menu_selection_filter.addAction(self.custom_actions["action_filter_sources"])
        self.menu_selection_filter.addAction(self.custom_actions["action_filter_resistors"])
        self.menu_selection_filter.addAction(self.custom_actions["action_filter_capacitors"])
        self.menu_selection_filter.addAction(self.custom_actions["action_filter_inductors"])
        self.menu_selection_filter.addAction(self.custom_actions["action_filter_capacitors"])
        self.menu_selection_filter.addAction(self.custom_actions["action_filter_add"])
        self.menu_edit.addSeparator()
        
        self.menu_edit.addSeparator()
        self.menu_edit.addAction(self.custom_actions["action_invert_x"])
        self.menu_edit.addAction(self.custom_actions["action_invert_y"])
        self.menu_edit.addAction(self.custom_actions["action_invert_xy"])
        
        self.menu_edit.addSeparator() 

        self.menu_align = self.menu_edit.addMenu('') 
        self.menu_align.addAction(self.custom_actions["action_align_left"])
        self.menu_align.addAction(self.custom_actions["action_align_right"])
        self.menu_align.addAction(self.custom_actions["action_align_top"])
        self.menu_align.addAction(self.custom_actions["action_align_bottom"])
        self.menu_align.addSeparator()
        self.menu_align.addAction(self.custom_actions["action_distribute_horiz"])
        self.menu_align.addAction(self.custom_actions["action_distribute_vertic"])
        
        self.menu_edit.addSeparator() 
        self.menu_edit.addAction(self.custom_actions["action_group"])
        self.menu_edit.addAction(self.custom_actions["action_ungroup"])
        
        self.menu_edit.addSeparator() 
        self.menu_edit.addAction(self.custom_actions["action_clean"])

    def _setup_view_menu(self) -> None:
        """Construit le menu Affichage."""
        self.menu_view.addAction(self.custom_actions["action_toggle_grid"])
        self.menu_view.addAction(self.custom_actions["action_snap_grid"])
        self.menu_view.addAction(self.custom_actions["action_grid_size"])
        self.menu_view.addSeparator()
        
        self.menu_view.addAction(self.custom_actions["action_show_labels"])
        self.menu_view.addAction(self.custom_actions["action_show_nodes"])
        self.menu_view.addAction(self.custom_actions["action_show_wire_dir"])
        self.menu_view.addSeparator()

        self.menu_theme = self.menu_view.addMenu('')
        self.menu_theme.addAction(self.custom_actions["action_theme_dark"])
        self.menu_theme.addAction(self.custom_actions["action_theme_light"])

        self.menu_view.addAction(self.custom_actions["action_center_select"])
        self.menu_view.addAction(self.custom_actions["action_reset_zoom"])
        self.menu_view.addAction(self.custom_actions["action_fullscreen"])
        self.menu_view.addSeparator()

        self.menu_show_hide = self.menu_view.addMenu('')
        self.menu_show_hide.addAction(self.custom_actions["action_show_components"])
        self.menu_show_hide.addAction(self.custom_actions["action_show_sim"])
        self.menu_show_hide.addAction(self.custom_actions["action_show_graphs"])
        self.menu_show_hide.addAction(self.custom_actions["action_show_examples"])
        self.menu_show_hide.addAction(self.custom_actions["action_show_toolbar"])
        
        self.menu_view.addSeparator()
        self.menu_view.addAction(self.custom_actions["action_highlight_short"])

    def _setup_options_menu(self) -> None:
        """Construit le menu Options."""
        self.menu_options.addAction(self.custom_actions["action_auto_save_int"])
        self.menu_options.addAction(self.custom_actions["action_toggle_auto_save"])
        self.menu_lang = self.menu_options.addMenu('') 
        self.menu_lang.addAction(self.custom_actions["action_lang_fr"])
        self.menu_lang.addAction(self.custom_actions["action_lang_en"])
        self.menu_options.addAction(self.custom_actions["action_restore_session"])
        self.menu_options.addSeparator()
        
        self.menu_units = self.menu_options.addMenu('')
        self.menu_units.addAction(self.custom_actions["action_unit_si"])
        self.menu_units.addAction(self.custom_actions["action_unit_eng"])
        self.menu_units.addAction(self.custom_actions["action_unit_compact"])
        
        self.menu_options.addSeparator()
        self.menu_options.addAction(self.custom_actions["action_precision"])
        self.menu_options.addAction(self.custom_actions["action_sci_notation"])
        self.menu_options.addAction(self.custom_actions["action_cross_cursor"])
        self.menu_options.addAction(self.custom_actions["action_enable_anim"])
        self.menu_options.addAction(self.custom_actions["action_allow_overlap"])
        self.menu_options.addAction(self.custom_actions["action_disable_editing"])
        self.menu_options.addAction(self.custom_actions["action_conv_current"])
        self.menu_options.addSeparator()
        
        self.menu_options.addAction(self.custom_actions["action_grid_export"])
        self.menu_options.addAction(self.custom_actions["action_sim_export"])
        self.menu_options.addSeparator()
        
        self.menu_options.addAction(self.custom_actions["action_bg_color"])
        self.menu_options.addAction(self.custom_actions["action_keybinds"])

        self.menu_colors = self.menu_options.addMenu('')
        self.menu_colors.addAction(self.custom_actions["action_color_pos"])
        self.menu_colors.addAction(self.custom_actions["action_color_neg"])
        self.menu_colors.addAction(self.custom_actions["action_color_neu"])
        self.menu_colors.addAction(self.custom_actions["action_color_sel"])
        self.menu_colors.addAction(self.custom_actions["action_color_cur"])


    def setup_toolbar(self) -> None:
        """Construit la barre d'outils principale."""
        self.toolbar = QToolBar("Barre d'outils principale", self)
        self.toolbar.setObjectName("mainToolbar")
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        self.toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.toolbar.setIconSize(self.toolbar.iconSize())
        self.toolbar.setStyleSheet(
            """
            QToolBar#mainToolbar {
                spacing: 6px;
                padding: 6px 8px;
            }
            QToolBar#mainToolbar QToolButton {
                min-height: 32px;
                min-width: 32px;
                padding: 4px;
            }
            """
        )
        self.toolbar.setVisible(False)

        self.toolbar.addAction(self.custom_actions["action_undo"])
        self.toolbar.addAction(self.custom_actions["action_redo"])

        self.toolbar.addSeparator()
        self.toolbar.addAction(self.custom_actions["action_zoom_in"])
        self.toolbar.addAction(self.custom_actions["action_zoom_out"])
        self.toolbar.addAction(self.custom_actions["action_reset_zoom"])
        self.toolbar_clipboard_separator = self.toolbar.addSeparator()

        self.toolbar_cut_action = QAction('', self)
        self.toolbar_cut_action.triggered.connect(self.on_cut)
        self.toolbar.addAction(self.toolbar_cut_action)

        self.toolbar_copy_action = QAction('', self)
        self.toolbar_copy_action.triggered.connect(self.on_copy)
        self.toolbar.addAction(self.toolbar_copy_action)

        self.toolbar_paste_action = QAction('', self)
        self.toolbar_paste_action.triggered.connect(self.on_paste)
        self.toolbar.addAction(self.toolbar_paste_action)

        self.toolbar_duplicate_action = QAction('', self)
        self.toolbar_duplicate_action.triggered.connect(self.on_duplicate)
        self.toolbar.addAction(self.toolbar_duplicate_action)

        self.toolbar_edit_value_separator_left = self.toolbar.addSeparator()
        self.toolbar_edit_value_action = QAction('', self)
        self.toolbar_edit_value_action.triggered.connect(self.on_edit_value)
        self.toolbar.addAction(self.toolbar_edit_value_action)

        self.toolbar_lock_separator = self.toolbar.addSeparator()
        self.toolbar_lock_action = QAction('', self)
        self.toolbar_lock_action.triggered.connect(self.on_lock)
        self.toolbar.addAction(self.toolbar_lock_action)

        self.toolbar_unlock_action = QAction('', self)
        self.toolbar_unlock_action.triggered.connect(self.on_unlock)
        self.toolbar.addAction(self.toolbar_unlock_action)

        self.toolbar_transform_separator = self.toolbar.addSeparator()
        self.toolbar.addAction(self.custom_actions["action_rotate"])
        self.toolbar.addAction(self.custom_actions["action_flip"])

        self.toolbar_delete_separator = self.toolbar.addSeparator()
        self.toolbar_delete_action = QAction('', self)
        self.toolbar_delete_action.triggered.connect(self.delete_selected_items)
        self.toolbar.addAction(self.toolbar_delete_action)

        self.custom_actions["action_paste"].setEnabled(False)
        self.toolbar_paste_action.setEnabled(False)
        self.custom_actions["action_duplicate"].setVisible(False)
        self.toolbar_duplicate_action.setVisible(False)
        self.custom_actions["action_edit_value"].setVisible(False)
        self.toolbar_edit_value_action.setVisible(False)
        self.toolbar_edit_value_separator_left.setVisible(False)
        self.custom_actions["action_lock"].setVisible(False)
        self.custom_actions["action_unlock"].setVisible(False)
        self.toolbar_lock_separator.setVisible(False)
        self.toolbar_lock_action.setVisible(False)
        self.toolbar_unlock_action.setVisible(False)
        self.custom_actions["action_rotate"].setVisible(False)
        self.custom_actions["action_flip"].setVisible(False)
        self.toolbar_transform_separator.setVisible(False)
        self.toolbar_delete_separator.setVisible(False)
        self.toolbar_delete_action.setVisible(False)

        self._apply_toolbar_icons()

    def _set_action_icon_from_asset(self, action: QAction, relative_asset_path: str, fallback_icon=None) -> None:
        """Assigne une icone depuis assets, avec fallback optionnel."""
        icon_path = get_asset_path(relative_asset_path)
        if icon_path.exists():
            action.setIcon(QIcon(str(icon_path)))
            return
        if fallback_icon is not None:
            action.setIcon(fallback_icon)

    def _apply_toolbar_icons(self) -> None:
        """Mappe les actions de la toolbar sur les icones du dossier assets/toolbar."""
        self._set_action_icon_from_asset(self.custom_actions["action_undo"], "toolbar/undo.png")
        self._set_action_icon_from_asset(
            self.custom_actions["action_redo"],
            "toolbar/redo.png",
            fallback_icon=self.style().standardIcon(QStyle.SP_ArrowForward),
        )
        self._set_action_icon_from_asset(self.custom_actions["action_zoom_in"], "toolbar/zoom_in.png")
        self._set_action_icon_from_asset(self.custom_actions["action_zoom_out"], "toolbar/zoom_out.png")
        self._set_action_icon_from_asset(self.custom_actions["action_reset_zoom"], "toolbar/zoom_reset.png")

        self._set_action_icon_from_asset(self.toolbar_cut_action, "toolbar/cut.png")
        self._set_action_icon_from_asset(self.toolbar_copy_action, "toolbar/copy.png")
        self._set_action_icon_from_asset(self.toolbar_paste_action, "toolbar/paste.png")
        self._set_action_icon_from_asset(self.toolbar_duplicate_action, "toolbar/duplicate.png")
        self._set_action_icon_from_asset(
            self.toolbar_edit_value_action,
            "toolbar/modify_value.png",
            fallback_icon=self.style().standardIcon(QStyle.SP_FileDialogDetailedView),
        )
        self._set_action_icon_from_asset(self.toolbar_lock_action, "toolbar/lock.png")
        self._set_action_icon_from_asset(self.toolbar_unlock_action, "toolbar/unlock.png")
        self._set_action_icon_from_asset(self.custom_actions["action_rotate"], "toolbar/rotate.png")
        self._set_action_icon_from_asset(self.custom_actions["action_flip"], "toolbar/flip.png")
        self._set_action_icon_from_asset(self.toolbar_delete_action, "toolbar/delete.png")

    def retranslate_ui(self) -> None:
        """Met a jour tous les textes de l'interface."""
        self.setWindowTitle(Translator.tr("app_title"))
        self._retranslate_menus()
        self._retranslate_actions()
        if hasattr(self, "components_panel") and self.components_panel is not None:
            self.components_panel.retranslate_ui()
        if hasattr(self, "graph_panel") and self.graph_panel is not None:
            self.graph_panel.retranslate_ui()
        if hasattr(self, "graph_collapse_button") and self.graph_collapse_button is not None:
            self.graph_collapse_button.setText(Translator.tr("graph_collapse_button"))
        self.status_bar.showMessage(Translator.tr("status_ready"))

    def _retranslate_menus(self) -> None:
        """Met a jour les titres des menus."""
        self.menu_file.setTitle(Translator.tr("menu_file"))
        self.menu_edit.setTitle(Translator.tr("menu_edit"))
        self.menu_view.setTitle(Translator.tr("menu_view"))
        self.menu_options.setTitle(Translator.tr("menu_options"))
        self.menu_simulation.setTitle(Translator.tr("menu_simulation"))

        self.menu_recent_files.setTitle(Translator.tr("menu_recent_files"))
        self.menu_selection_filter.setTitle(Translator.tr("menu_selection_filter"))
        self.menu_align.setTitle(Translator.tr("menu_align"))
        self.menu_show_hide.setTitle(Translator.tr("menu_show_hide"))
        self.menu_units.setTitle(Translator.tr("menu_units"))
        self.menu_colors.setTitle(Translator.tr("menu_colors"))
        self.menu_lang.setTitle(Translator.tr("action_language"))
        self.menu_theme.setTitle(Translator.tr("menu_theme"))

    def _retranslate_actions(self) -> None:
        """Met a jour les libelles des actions Qt."""
        # Le dictionnaire self.custom_actions contient {"cle_traduction": QAction}
        for key, action in self.custom_actions.items():
            action.setText(Translator.tr(key))

        if hasattr(self, "toolbar_cut_action") and self.toolbar_cut_action is not None:
            self.toolbar_cut_action.setText(Translator.tr("action_cut"))
        if hasattr(self, "toolbar_copy_action") and self.toolbar_copy_action is not None:
            self.toolbar_copy_action.setText(Translator.tr("action_copy"))
        if hasattr(self, "toolbar_paste_action") and self.toolbar_paste_action is not None:
            self.toolbar_paste_action.setText(Translator.tr("action_paste"))
        if hasattr(self, "toolbar_duplicate_action") and self.toolbar_duplicate_action is not None:
            self.toolbar_duplicate_action.setText(Translator.tr("action_duplicate"))
        if hasattr(self, "toolbar_edit_value_action") and self.toolbar_edit_value_action is not None:
            self.toolbar_edit_value_action.setText(Translator.tr("action_edit_value"))
        if hasattr(self, "toolbar_lock_action") and self.toolbar_lock_action is not None:
            self.toolbar_lock_action.setText(Translator.tr("action_lock"))
        if hasattr(self, "toolbar_unlock_action") and self.toolbar_unlock_action is not None:
            self.toolbar_unlock_action.setText(Translator.tr("action_unlock"))
        if hasattr(self, "toolbar_delete_action") and self.toolbar_delete_action is not None:
            self.toolbar_delete_action.setText(Translator.tr("action_delete"))
        if hasattr(self, "graphics_button") and self.graphics_button is not None:
            if self.graphics_button.icon().isNull():
                self.graphics_button.setText(Translator.tr("action_show_graphs"))
            else:
                self.graphics_button.setText("")

    def change_language(self, lang: str) -> None:
        """Change la langue et rafraichit l'interface."""
        if Translator.load_language(lang):
            self.retranslate_ui()
        else:
            QMessageBox.warning(self, "Erreur", f"Impossible de charger la langue '{lang}'.")

    # Gestionnaires d'actions
    def on_new_file(self) -> None:
        """Declenche la creation d'un nouveau fichier."""
        if hasattr(self, "file_controller") and self.file_controller is not None:
            self.file_controller.new_circuit()

    def on_new_window(self) -> None:
        """Ouvre une nouvelle fenetre."""
        if hasattr(self, "app_controller") and self.app_controller is not None:
            self.app_controller.not_implemented("Nouvelle fenetre")

    def on_open_file(self) -> None:
        """Declenche l'ouverture d'un fichier."""
        if hasattr(self, "file_controller") and self.file_controller is not None:
            self.file_controller.open_circuit()

    def on_save_file(self) -> None:
        """Declenche la sauvegarde du fichier courant."""
        if hasattr(self, "file_controller") and self.file_controller is not None:
            self.file_controller.save_circuit()

    def on_save_as(self) -> None:
        """Declenche la sauvegarde sous un nouveau nom."""
        if hasattr(self, "file_controller") and self.file_controller is not None:
            self.file_controller.save_circuit_as()

    def on_import(self) -> None:
        """Declenche l'import de donnees."""
        if hasattr(self, "file_controller") and self.file_controller is not None:
            self.file_controller.import_circuit()

    def on_edit_value(self) -> None:
        """Affiche un dialogue pour modifier la valeur principale d'un dipole."""
        dipole_items = self._get_selected_dipole_items()
        if len(dipole_items) != 1:
            return
        item = dipole_items[0]
        component = item.component
        config = self._get_edit_value_config(component)
        if config is None:
            QMessageBox.information(self, Translator.tr("action_edit_value"), Translator.tr("dialog_edit_value_unsupported"))
            return
        param_key, unit = config
        current_value = float(getattr(component, param_key, 0.0))
        title = f"{Translator.tr('dialog_edit_value_title')} - {component.name}"
        label = f"{Translator.tr('dialog_edit_value_label')} ({unit})"
        new_value, ok = QInputDialog.getDouble(
            self,
            title,
            label,
            current_value,
            -1e12,
            1e12,
            6,
        )
        if not ok:
            return
        if hasattr(self.scene, "_push_undo_snapshot"):
            self.scene._push_undo_snapshot()
        setattr(component, param_key, float(new_value))
        item.update()
        if hasattr(self.scene, "update"):
            self.scene.update()

    def on_export(self) -> None:
        """Declenche l'export de donnees."""
        if hasattr(self, "file_controller") and self.file_controller is not None:
            self.file_controller.export_circuit()

    def on_version_history(self) -> None:
        """Affiche l'historique des versions."""
        if hasattr(self, "app_controller") and self.app_controller is not None:
            self.app_controller.not_implemented("Historique des versions")

    def on_select_all(self) -> None:
        """Selectionne tous les elements."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.select_all()

    def on_cut(self) -> None:
        """Coupe la selection courante."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.cut()

    def on_copy(self) -> None:
        """Copie la selection courante."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.copy()

    def on_paste(self) -> None:
        """Colle le contenu du presse-papiers."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.paste()

    def on_duplicate(self) -> None:
        """Duplique la selection courante."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.duplicate()

    def on_lock(self) -> None:
        """Verrouille la selection courante."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.lock_selection()

    def on_unlock(self) -> None:
        """Deverrouille la selection courante."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.unlock_selection()

    def on_paste_near_cursor(self) -> None:
        """Colle le contenu au niveau du curseur."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.paste_near_cursor()

    def on_select_none(self) -> None:
        """Annule toute selection."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.select_none()

    def on_select_invert(self) -> None:
        """Inverse la selection courante."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.select_invert()

    # TODO regrouper ces fonctions de filtre dans une seule avec un paramètre
    def on_filter_nodes(self) -> None:
        """Filtre les noeuds dans la selection."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.filter_nodes()

    def on_filter_wires(self) -> None:
        """Filtre les fils dans la selection."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.filter_wires()

    def on_filter_sources(self) -> None:
        """Filtre les sources dans la selection."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.filter_sources()
    
    def on_filter_resistors(self) -> None:
        """Filtre les resistances dans la selection."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.filter_resistors()

    def on_filter_capacitors(self) -> None:
        """Filtre les condensateurs dans la selection."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.filter_capacitors()

    def on_filter_inductors(self) -> None:
        """Filtre les inductances dans la selection."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.filter_inductors()

    def on_filter_add(self) -> None:
        """Ajoute un filtre supplementaire."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.filter_add()

    def on_invert_x(self) -> None:
        """Inverser la selection sur l'axe X."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.invert_x()

    def on_invert_y(self) -> None:
        """Inverser la selection sur l'axe Y."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.invert_y()

    def on_invert_xy(self) -> None:
        """Inverser la selection sur les axes X/Y."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.invert_xy()

    def on_align_left(self) -> None:
        """Aligne les elements sur la gauche."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.align_left()

    def on_align_right(self) -> None:
        """Aligne les elements sur la droite."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.align_right()

    def on_align_top(self) -> None:
        """Aligne les elements en haut."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.align_top()

    def on_align_bottom(self) -> None:
        """Aligne les elements en bas."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.align_bottom()

    def on_distribute_horiz(self) -> None:
        """Distribue les elements horizontalement."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.distribute_horizontal()

    def on_distribute_vertic(self) -> None:
        """Distribue les elements verticalement."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.distribute_vertical()

    def on_group_items(self) -> None:
        """Groupe les elements selectionnes."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.group_items()

    def on_ungroup_items(self) -> None:
        """Degroupe les elements selectionnes."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.ungroup_items()

    def on_clean_canvas(self) -> None:
        """Nettoie la scene de travail."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.clean_canvas()

    # Actions d'affichage
    def on_toggle_grid(self) -> None:
        """Bascule l'affichage de la grille."""
        if hasattr(self, "circuit_controller") and self.circuit_controller is not None:
            self.circuit_controller.toggle_grid()

    def on_snap_grid(self) -> None:
        """Bascule l'aimantation a la grille."""
        if hasattr(self, "circuit_controller") and self.circuit_controller is not None:
            self.circuit_controller.toggle_snap_grid()

    def on_grid_size(self) -> None:
        """Ouvre le reglage de taille de grille."""
        if hasattr(self, "app_controller") and self.app_controller is not None:
            self.app_controller.not_implemented("Taille de grille")

    def on_toggle_labels(self) -> None:
        """Bascule l'affichage des etiquettes."""
        if hasattr(self, "circuit_controller") and self.circuit_controller is not None:
            self.circuit_controller.toggle_labels()

    def on_toggle_nodes(self) -> None:
        """Bascule l'affichage des identifiants de noeuds."""
        if hasattr(self, "circuit_controller") and self.circuit_controller is not None:
            self.circuit_controller.toggle_nodes()

    def on_toggle_wire_dir(self) -> None:
        """Bascule l'affichage du sens du courant."""
        if hasattr(self, "circuit_controller") and self.circuit_controller is not None:
            self.circuit_controller.toggle_wire_direction()

    def on_center_selection(self) -> None:
        """Centre la vue sur la selection."""
        if hasattr(self, "circuit_controller") and self.circuit_controller is not None:
            self.circuit_controller.center_on_selection()

    def on_zoom_in(self) -> None:
        """Effectue un zoom avant."""
        if hasattr(self, "circuit_controller") and self.circuit_controller is not None:
            self.circuit_controller.zoom_in()

    def on_zoom_out(self) -> None:
        """Effectue un zoom arriere."""
        if hasattr(self, "circuit_controller") and self.circuit_controller is not None:
            self.circuit_controller.zoom_out()

    def on_reset_zoom(self) -> None:
        """Reinitialise le zoom de la vue."""
        if hasattr(self, "circuit_controller") and self.circuit_controller is not None:
            self.circuit_controller.reset_zoom()

    def on_toggle_fullscreen(self) -> None:
        """Bascule le mode plein ecran."""
        if hasattr(self, "circuit_controller") and self.circuit_controller is not None:
            self.circuit_controller.toggle_fullscreen()

    def on_highlight_short_circuit(self) -> None:
        """Declenche la mise en evidence des courts-circuits."""
        if hasattr(self, "circuit_controller") and self.circuit_controller is not None:
            self.circuit_controller.highlight_short_circuit()

    def on_toggle_view_components(self) -> None:
        """Affiche ou masque le panneau des composants."""
        if hasattr(self, "app_controller") and self.app_controller is not None:
            self.app_controller.toggle_components_panel()

    def on_toggle_view_simulation(self) -> None:
        """Affiche la fenetre de simulation."""
        if hasattr(self, "app_controller") and self.app_controller is not None:
            self.app_controller.not_implemented("Fenetre de simulation")

    def on_run_simulation_dc(self) -> None:
        """Lance la simulation DC via le controleur de simulation."""
        if hasattr(self, "simulation_controller") and self.simulation_controller is not None:
            if self.simulation_controller.is_realtime_running:
                self.on_stop_simulation_realtime()
            self.simulation_controller.run_dc()
            if hasattr(self, "scene") and self.scene is not None:
                if hasattr(self.scene, "update_overlay_indicators"):
                    self.scene.update_overlay_indicators()
            if hasattr(self, "graph_panel") and self.graph_panel is not None and self.model is not None:
                self.graph_panel.set_dc_results(self.model)
                if not self.graph_panel.isVisible():
                    self._set_graph_panel_visible(True)

    def on_run_simulation_transient(self) -> None:
        """Lance la simulation transitoire avec des parametres par defaut."""
        if not hasattr(self, "simulation_controller") or self.simulation_controller is None:
            return

        if self.simulation_controller.is_realtime_running:
            self.on_stop_simulation_realtime()

        duration, ok_duration = QInputDialog.getDouble(
            self,
            Translator.tr("dialog_transient_title"),
            Translator.tr("dialog_transient_duration"),
            1.0,
            1e-6,
            1e6,
            6,
        )
        if not ok_duration:
            return

        time_step, ok_step = QInputDialog.getDouble(
            self,
            Translator.tr("dialog_transient_title"),
            Translator.tr("dialog_transient_step"),
            0.01,
            1e-9,
            1e6,
            9,
        )
        if not ok_step:
            return

        result = self.simulation_controller.run_transient(duration=duration, time_step=time_step)
        if hasattr(self, "scene") and self.scene is not None:
            if hasattr(self.scene, "update_overlay_indicators"):
                self.scene.update_overlay_indicators()
        if hasattr(self, "graph_panel") and self.graph_panel is not None:
            self.graph_panel.set_transient_results(result, circuit=self.model)
            if result and not self.graph_panel.isVisible():
                self._set_graph_panel_visible(True)

    def _set_realtime_actions_state(self, is_running: bool) -> None:
        """Synchronise l'etat des actions de simulation temps reel."""
        if "action_sim_run_realtime" in self.custom_actions:
            self.custom_actions["action_sim_run_realtime"].setEnabled(not is_running)
        if "action_sim_stop_realtime" in self.custom_actions:
            self.custom_actions["action_sim_stop_realtime"].setEnabled(is_running)

    def _on_realtime_update(self, result: dict) -> None:
        """Met a jour le panneau graphiques a chaque tick temps reel."""
        if hasattr(self, "graph_panel") and self.graph_panel is not None:
            self.graph_panel.set_transient_results(result, circuit=self.model)
            if self._realtime_auto_open_graph_once and not self.graph_panel.isVisible():
                self._set_graph_panel_visible(True)
            self._realtime_auto_open_graph_once = False

    def _on_realtime_finished(self) -> None:
        """Callback appele a la fin d'une simulation temps reel."""
        if hasattr(self, "realtime_timer") and self.realtime_timer.isActive():
            self.realtime_timer.stop()
        self._set_realtime_actions_state(False)

    def _on_realtime_tick(self) -> None:
        """Declenche un pas de simulation temps reel."""
        if not hasattr(self, "simulation_controller") or self.simulation_controller is None:
            return

        result = self.simulation_controller.tick_realtime_transient()
        if result is None and not self.simulation_controller.is_realtime_running:
            if hasattr(self, "realtime_timer") and self.realtime_timer.isActive():
                self.realtime_timer.stop()
            self._set_realtime_actions_state(False)
        if hasattr(self, "scene") and self.scene is not None:
            if hasattr(self.scene, "update_overlay_indicators"):
                self.scene.update_overlay_indicators()

    def on_run_simulation_realtime(self) -> None:
        """Lance une simulation transitoire avec rafraichissement temps reel du graphe."""
        if not hasattr(self, "simulation_controller") or self.simulation_controller is None:
            return
        if self.simulation_controller.is_realtime_running:
            return

        time_step, ok_step = QInputDialog.getDouble(
            self,
            Translator.tr("dialog_realtime_title"),
            Translator.tr("dialog_transient_step"),
            0.01,
            1e-9,
            1e6,
            9,
        )
        if not ok_step:
            return

        if hasattr(self, "graph_panel") and self.graph_panel is not None:
            target_points = 150
            window_seconds = max(time_step, target_points * time_step)
            self.graph_panel.set_transient_window(window_seconds)
            if hasattr(self, "simulation_controller") and self.simulation_controller is not None:
                self.simulation_controller.set_realtime_history_limit(target_points)

        started = self.simulation_controller.start_realtime_transient(
            time_step=time_step,
            on_update=self._on_realtime_update,
            on_finished=self._on_realtime_finished,
        )
        if not started:
            return

        self._realtime_auto_open_graph_once = True
        self._set_realtime_actions_state(True)
        self._realtime_timer_interval_ms = max(30, int(time_step * 1000))
        self.realtime_timer.start(self._realtime_timer_interval_ms)
        self._on_realtime_tick()

    def on_stop_simulation_realtime(self) -> None:
        """Arrete la simulation temps reel en cours."""
        if hasattr(self, "realtime_timer") and self.realtime_timer.isActive():
            self.realtime_timer.stop()
        if hasattr(self, "simulation_controller") and self.simulation_controller is not None:
            self.simulation_controller.stop_realtime_transient()
        self._realtime_auto_open_graph_once = False
        if hasattr(self, "graph_panel") and self.graph_panel is not None:
            self.graph_panel.set_transient_window(None)
        self._set_realtime_actions_state(False)

    def on_export_simulation_results(self) -> None:
        """Exporte uniquement les resultats de simulation."""
        if hasattr(self, "file_controller") and self.file_controller is not None:
            self.file_controller.export_simulation_results()

    def on_export_transient_csv(self) -> None:
        """Exporte les traces transitoires au format CSV."""
        if hasattr(self, "file_controller") and self.file_controller is not None:
            self.file_controller.export_transient_results_csv()

    def on_toggle_view_graphs(self) -> None:
        """Affiche la fenetre des graphiques."""
        if not hasattr(self, "graph_panel") or self.graph_panel is None:
            return

        self._set_graph_panel_visible(not self.graph_panel.isVisible())

    def on_toggle_view_examples(self) -> None:
        """Affiche la fenetre d'exemples."""
        if hasattr(self, "app_controller") and self.app_controller is not None:
            self.app_controller.not_implemented("Fenetre des exemples")

    def on_toggle_view_toolbar(self) -> None:
        """Affiche ou masque la barre d'outils."""
        if hasattr(self, "app_controller") and self.app_controller is not None:
            self.app_controller.toggle_toolbar()

    # Actions d'options

    def on_set_autosave_interval(self) -> None:
        """Ouvre le reglage de l'intervalle de sauvegarde."""
        if hasattr(self, "app_controller") and self.app_controller is not None:
            self.app_controller.not_implemented("Intervalle de sauvegarde")

    def on_toggle_autosave(self) -> None:
        """Active ou desactive la sauvegarde automatique."""
        if hasattr(self, "app_controller") and self.app_controller is not None:
            self.app_controller.not_implemented("Sauvegarde automatique")

    def on_set_language(self, lang: str) -> None:
        """Change la langue via un code explicite."""
        if hasattr(self, "app_controller") and self.app_controller is not None:
            self.app_controller.change_language(lang)
        else:
            self.change_language(lang)

    def set_lang_fr(self) -> None:
        """Passe l'application en francais."""
        self.on_set_language("fr")

    def set_lang_en(self) -> None:
        """Passe l'application en anglais."""
        self.on_set_language("en")

    def on_restore_session(self) -> None:
        """Restaure la session precedente."""
        if hasattr(self, "app_controller") and self.app_controller is not None:
            self.app_controller.not_implemented("Restaurer la session")

    def on_set_unit_si(self) -> None:
        """Passe les unites en systeme SI."""
        if hasattr(self, "app_controller") and self.app_controller is not None:
            self.app_controller.not_implemented("Unites SI")

    def on_set_unit_eng(self) -> None:
        """Passe les unites au systeme d'ingenierie."""
        if hasattr(self, "app_controller") and self.app_controller is not None:
            self.app_controller.not_implemented("Unites ingenierie")

    def on_set_unit_compact(self) -> None:
        """Passe les unites en mode compact."""
        if hasattr(self, "app_controller") and self.app_controller is not None:
            self.app_controller.not_implemented("Unites compactes")

    def on_set_precision(self) -> None:
        """Ouvre le reglage de precision."""
        if hasattr(self, "app_controller") and self.app_controller is not None:
            self.app_controller.not_implemented("Precision")

    def on_toggle_sci_notation(self) -> None:
        """Bascule la notation scientifique."""
        if hasattr(self, "app_controller") and self.app_controller is not None:
            self.app_controller.not_implemented("Notation scientifique")

    def on_toggle_cross_cursor(self) -> None:
        """Bascule le curseur en croix."""
        if hasattr(self, "app_controller") and self.app_controller is not None:
            self.app_controller.not_implemented("Curseur en croix")

    def on_toggle_animations(self) -> None:
        """Bascule les animations."""
        if hasattr(self, "app_controller") and self.app_controller is not None:
            self.app_controller.not_implemented("Animations")

    def on_toggle_overlap(self) -> None:
        """Bascule l'autorisation de chevauchement."""
        if hasattr(self, "app_controller") and self.app_controller is not None:
            self.app_controller.not_implemented("Chevauchement")

    def on_toggle_editing(self) -> None:
        """Bascule le verrouillage de l'edition."""
        if hasattr(self, "app_controller") and self.app_controller is not None:
            self.app_controller.not_implemented("Verrouillage edition")

    def on_toggle_conv_current(self) -> None:
        """Change la convention du sens du courant."""
        if hasattr(self, "app_controller") and self.app_controller is not None:
            self.app_controller.not_implemented("Sens du courant")

    def on_toggle_grid_export(self) -> None:
        """Bascule l'inclusion de la grille a l'export."""
        if hasattr(self, "app_controller") and self.app_controller is not None:
            self.app_controller.not_implemented("Export grille")

    def on_toggle_sim_export(self) -> None:
        """Bascule l'inclusion des donnees de simulation a l'export."""
        self.include_simulation_in_export = not self.include_simulation_in_export
        action = self.custom_actions.get("action_sim_export")
        if action is not None:
            action.setChecked(self.include_simulation_in_export)

        if hasattr(self, "app_controller") and self.app_controller is not None:
            if self.include_simulation_in_export:
                self.app_controller.set_status("Export simulation active")
            else:
                self.app_controller.set_status("Export simulation inactif")

    def on_change_bg_color(self) -> None:
        """Ouvre la selection de couleur de fond."""
        if hasattr(self, "app_controller") and self.app_controller is not None:
            self.app_controller.change_background_color()

    def on_show_keybinds(self) -> None:
        """Affiche la liste des raccourcis."""
        if hasattr(self, "app_controller") and self.app_controller is not None:
            self.app_controller.not_implemented("Raccourcis")

    def on_set_color_positive(self) -> None:
        """Change la couleur des valeurs positives."""
        if hasattr(self, "app_controller") and self.app_controller is not None:
            self.app_controller.not_implemented("Couleur positif")

    def on_set_color_negative(self) -> None:
        """Change la couleur des valeurs negatives."""
        if hasattr(self, "app_controller") and self.app_controller is not None:
            self.app_controller.not_implemented("Couleur negatif")

    def on_set_color_neutral(self) -> None:
        """Change la couleur des valeurs neutres."""
        if hasattr(self, "app_controller") and self.app_controller is not None:
            self.app_controller.not_implemented("Couleur neutre")

    def on_set_color_selected(self) -> None:
        """Change la couleur de selection."""
        if hasattr(self, "app_controller") and self.app_controller is not None:
            self.app_controller.not_implemented("Couleur selection")

    def on_set_color_current(self) -> None:
        """Change la couleur du courant."""
        if hasattr(self, "app_controller") and self.app_controller is not None:
            self.app_controller.not_implemented("Couleur courant")

    def delete_selected_items(self) -> None:
        """Demande a la scene de supprimer ce qui est selectionne."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.delete_selection()

    def undo_last_action(self) -> None:
        """Annule la derniere action modifiant le circuit."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.undo()

    def redo_last_action(self) -> None:
        """Retablit la derniere action annulee."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.redo()

    def rotate_selected_components(self) -> None:
        """Tourne les composants selectionnes."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.rotate_selection(90)

    def flip_selected_components(self) -> None:
        """Retourne les composants selectionnes."""
        if hasattr(self, "edit_controller") and self.edit_controller is not None:
            self.edit_controller.flip_selection()