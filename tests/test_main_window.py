import pytest
from types import SimpleNamespace

from PySide6.QtWidgets import QApplication, QMainWindow, QToolBar, QMessageBox
from PySide6.QtCore import Qt, QPointF

from maltoolbox.language import LanguageGraph
from maltoolbox.model import Model
from malsim import policies
from malsim.config.agent_settings import AttackerSettings, AgentType

from mal_gui.main_window import MainWindow
from mal_gui.model_scene import ModelScene


@pytest.fixture
def main_window(app, lang_file_path):
    """Create a MainWindow instance."""
    window = MainWindow(app, lang_file_path)
    yield window
    window.close()


# -------------------------------------------------------------------
# Initialization
# -------------------------------------------------------------------


def test_main_window_initialization(main_window):
    assert isinstance(main_window, QMainWindow)
    assert main_window.windowTitle() == "MAL GUI"

    # Core attributes
    assert main_window.scene is not None
    assert main_window.view is not None
    assert main_window.asset_factory is not None

    # Toolbar exists
    assert isinstance(main_window.toolbar, QToolBar)

    # Dock widgets created
    assert len(main_window.dock_widgets) > 0


def test_scene_is_model_scene(main_window):
    assert isinstance(main_window.scene, ModelScene)
    assert isinstance(main_window.scene.model, Model)


# -------------------------------------------------------------------
# Menu & Actions
# -------------------------------------------------------------------


def test_menu_bar_created(main_window):
    menu_bar = main_window.menuBar()
    actions = [
        menu.title() for menu in menu_bar.findChildren(type(menu_bar.addMenu("tmp")))
    ]

    assert "&File" in actions
    assert "Edit" in actions


def test_actions_exist(main_window):
    assert main_window.zoom_in_action is not None
    assert main_window.zoom_out_action is not None
    assert main_window.undo_action is not None
    assert main_window.redo_action is not None
    assert main_window.cut_action is not None
    assert main_window.copy_action is not None
    assert main_window.paste_action is not None
    assert main_window.delete_action is not None


# -------------------------------------------------------------------
# Toolbar behavior
# -------------------------------------------------------------------


def test_zoom_actions(main_window):
    initial_zoom = main_window.view.zoom_factor

    main_window.zoom_in()
    assert main_window.view.zoom_factor > initial_zoom

    main_window.zoom_out()
    assert main_window.view.zoom_factor <= initial_zoom


def test_zoom_line_edit(main_window):
    main_window.zoom_line_edit.setText("150")
    main_window.set_zoom_level_from_line_edit()

    assert int(main_window.view.zoom_factor * 100) == 150
    assert main_window.zoom_label.text() == "150%"


# -------------------------------------------------------------------
# Scene reload / clearing
# -------------------------------------------------------------------


def test_clear_window(main_window):
    # Sanity: items exist initially
    assert main_window.scene is not None
    assert main_window.toolbar is not None

    main_window.clear_window()

    # Menu bar cleared
    assert main_window.menuBar().actions() == []


def test_load_scene_recreates_components(app, lang_file_path):
    window = MainWindow(app, lang_file_path)

    old_scene = window.scene
    lang_graph = LanguageGraph.load_from_file(lang_file_path)
    model = Model("ReloadedModel", lang_graph)

    window.load_scene(lang_file_path, model)

    assert window.scene is not old_scene
    assert window.scene.model.name == "ReloadedModel"


def test_load_model_recreates_scene(tmp_path, app, lang_file_path):
    window = MainWindow(app, lang_file_path)

    lang_graph = LanguageGraph.load_from_file(lang_file_path)
    model = Model("SavedModel", lang_graph)
    model_path = tmp_path / "saved-model.yml"
    model.save_to_file(model_path)

    old_scene = window.scene
    window.load_model(str(model_path))

    assert window.scene is not old_scene
    assert window.scene.model.name == "SavedModel"
    assert window.model_file_name == str(model_path)
    assert window.scenario_file_name is None


def test_load_scene_restores_attacker_policy_from_scenario(app, lang_file_path):
    window = MainWindow(app, lang_file_path)

    lang_graph = LanguageGraph.load_from_file(lang_file_path)
    model = Model("ScenarioPolicyModel", lang_graph)
    asset = model.add_asset("Application", name="App1")
    asset.extras = {"position": {"x": 0, "y": 0}}

    scenario = SimpleNamespace(
        agent_settings={
            "Attacker1": AttackerSettings(
                name="Attacker1",
                entry_points={"App1:attemptRead"},
                goals={"App1:successfulRead"},
                type=AgentType.ATTACKER,
                policy=policies.DepthFirstAttacker,
            )
        }
    )

    window.load_scene(lang_file_path, model, scenario)

    assert len(window.scene.attacker_items) == 1
    attacker = window.scene.attacker_items[0]
    assert attacker.policy is policies.DepthFirstAttacker
    assert attacker.entry_points == ["App1:attemptRead"]
    assert attacker.goals == ["App1:successfulRead"]


def test_quick_load_current_file_reloads_model(tmp_path, monkeypatch, app, lang_file_path):
    window = MainWindow(app, lang_file_path)

    lang_graph = LanguageGraph.load_from_file(lang_file_path)
    model = Model("ReloadTarget", lang_graph)
    model_path = tmp_path / "reload-model.yml"
    model.save_to_file(model_path)
    window.load_model(str(model_path))

    reloaded_scene = window.scene
    window.scene.model.name = "MutatedInMemory"
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Ok)

    window.quick_load_current_file()

    assert window.scene is not reloaded_scene
    assert window.scene.model.name == "ReloadTarget"
    assert window.model_file_name == str(model_path)


def test_save_model_persists_attacker_metadata(monkeypatch, main_window):
    asset_item = main_window.scene.create_asset("Application", QPointF(100, 100), name="App1")
    attacker_item = main_window.scene.create_attacker(
        QPointF(25, 50),
        "Attacker1",
        entry_points=["App1:attemptRead"],
        goals=["App1:successfulRead"],
        policy=policies.RandomAgent,
    )

    main_window.model_file_name = "saved-model.yml"
    saved = {}
    monkeypatch.setattr(
        main_window.scene.model,
        "save_to_file",
        lambda path: saved.setdefault("path", path),
    )

    main_window.save_model()

    asset_extras = main_window.scene.model.assets[asset_item.asset.id].extras
    attacker_metadata = asset_extras[main_window.ATTACKER_METADATA_KEY]

    assert saved["path"] == "saved-model.yml"
    assert attacker_metadata == [
        {
            "name": "Attacker1",
            "entry_points": ["App1:attemptRead"],
            "goals": ["App1:successfulRead"],
            "policy": "RandomAgent",
            "position": {"x": attacker_item.pos().x(), "y": attacker_item.pos().y()},
        }
    ]


def test_load_scene_restores_attacker_policy_from_model_metadata(app, lang_file_path):
    window = MainWindow(app, lang_file_path)

    lang_graph = LanguageGraph.load_from_file(lang_file_path)
    model = Model("ModelPolicyRoundTrip", lang_graph)
    asset = model.add_asset("Application", name="App1")
    asset.extras = {
        "position": {"x": 0, "y": 0},
        window.ATTACKER_METADATA_KEY: [
            {
                "name": "Attacker1",
                "entry_points": ["App1:attemptRead"],
                "goals": ["App1:successfulRead"],
                "policy": "BreadthFirstAttacker",
                "position": {"x": 10, "y": 20},
            }
        ],
    }

    window.load_scene(lang_file_path, model)

    assert len(window.scene.attacker_items) == 1
    attacker = window.scene.attacker_items[0]
    assert attacker.policy is policies.BreadthFirstAttacker
    assert attacker.entry_points == ["App1:attemptRead"]
    assert attacker.goals == ["App1:successfulRead"]
    assert attacker.pos() == QPointF(10, 20)


def test_reload_project_from_mal_falls_back_to_empty_project(monkeypatch, main_window):
    messages = []

    main_window.scenario_file_name = "missing-scenario.yml"
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Ok)
    monkeypatch.setattr(main_window, "show_error_popup", messages.append)

    main_window.reload_project_from_mal()

    assert main_window.scene.model.name == "New Model"
    assert main_window.scenario_file_name is None
    assert main_window.model_file_name is None
    assert messages
    assert "Could not reload scenario file" in messages[0]


# -------------------------------------------------------------------
# Object explorer update signal
# -------------------------------------------------------------------


def test_update_explorer_signal(main_window):
    # Should not raise
    main_window.update_childs_in_object_explorer_signal.emit()


# -------------------------------------------------------------------
# Theme handling
# -------------------------------------------------------------------


def test_theme_selection(main_window):
    # First item is "None"
    main_window.theme_combo_box.setCurrentIndex(0)
    assert main_window.theme_combo_box.currentText() == "None"


# -------------------------------------------------------------------
# Model interaction (lightweight)
# -------------------------------------------------------------------


def test_add_asset_updates_scene(main_window):
    scene = main_window.scene

    pos = QPointF(100, 100)
    asset = scene.create_asset("Application", pos, name="App1")

    assert asset in scene.items()


# -------------------------------------------------------------------
# Quit behavior
# -------------------------------------------------------------------


def test_quit_app_calls_app_quit(monkeypatch, main_window):
    called = {"quit": False}

    def fake_quit():
        called["quit"] = True

    monkeypatch.setattr(main_window.app, "quit", fake_quit)
    main_window.quitApp()

    assert called["quit"] is True
