"""
Tests unitaires pour les modules d'utilitaires et de persistance :
- utils.translator (chargement de langues, traductions, gestion d'erreurs)
- utils.assets (chemins d'accès aux ressources, détection de logo, icônes)
- persistence.serializer, exporter, importer (export JSON avec/sans simulation, CSV transitoire, import)
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from model.circuit import Circuit
from model.components import Capacitor, Resistor, VoltageSourceDC
from persistence import exporter, importer, serializer
from utils import assets, translator


# ==============================================================================
# 1. Tests Translator
# ==============================================================================

def test_translator_load_and_translate() -> None:
    # Charger la langue française
    assert translator.Translator.load_language("fr") is True
    assert translator.Translator.get_current_lang() == "fr"

    # Traduire une clé existante
    translated = translator.Translator.tr("app_title")
    assert isinstance(translated, str)

    # Clé inconnue retourne la clé elle-même
    unknown_key = "non_existent_key_12345"
    assert translator.Translator.tr(unknown_key) == unknown_key

    # Charger l'anglais
    assert translator.Translator.load_language("en") is True
    assert translator.Translator.get_current_lang() == "en"


def test_translator_errors(tmp_path: Path) -> None:
    # Fichier introuvable
    with pytest.raises(FileNotFoundError):
        translator.Translator.load_language("non_existent_lang_xyz")

    # Fichier JSON malformé
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{ unclosed json: ", encoding="utf-8")

    orig_locales = translator.Translator.LOCALES_DIR
    try:
        translator.Translator.LOCALES_DIR = str(tmp_path)
        with pytest.raises(json.JSONDecodeError):
            translator.Translator.load_language("bad")
    finally:
        translator.Translator.LOCALES_DIR = orig_locales


# ==============================================================================
# 2. Tests Assets
# ==============================================================================

def test_assets_paths() -> None:
    assets_dir = assets.get_assets_dir()
    assert isinstance(assets_dir, Path)
    assert assets_dir.name == "assets"

    logo_path = assets.get_asset_path("logo.png")
    assert logo_path.parent == assets_dir

    exists = assets.logo_exists()
    assert isinstance(exists, bool)

    icon = assets.get_logo_icon()
    assert icon is not None


# ==============================================================================
# 3. Tests Persistence (Serializer, Exporter, Importer)
# ==============================================================================

def test_serializer_errors() -> None:
    with pytest.raises(ValueError, match="Circuit manquant"):
        serializer.serialize_circuit(None)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="Circuit manquant"):
        serializer.deserialize_circuit(None, "{}")  # type: ignore[arg-type]


def test_exporter_and_importer_full(tmp_path: Path) -> None:
    c = Circuit()
    n1 = c.create_node(0, 0, is_ground=True)
    n2 = c.create_node(100, 0)
    c.add_dipole(VoltageSourceDC(1, n1, n2, dc_voltage=5.0))
    c.add_dipole(Resistor(2, n1, n2, resistance=100.0))

    # Export standard JSON
    json_path = tmp_path / "circuit.json"
    exporter.export_circuit(c, json_path)
    assert json_path.exists()

    # Import
    c_loaded = Circuit()
    importer.import_circuit(c_loaded, json_path)
    assert len(c_loaded.nodes) == 2
    assert len(c_loaded.dipoles) == 2

    # Export avec données de simulation
    sim_json_path = tmp_path / "circuit_sim.json"
    sim_data = {"operating_point": {"n1": 0.0, "n2": 5.0}}
    exporter.export_circuit(c, sim_json_path, simulation_data=sim_data)
    loaded_text = sim_json_path.read_text(encoding="utf-8")
    assert "simulation" in loaded_text

    # Export des résultats seuls
    results_path = tmp_path / "results.json"
    exporter.export_simulation_results_to_file({"status": "ok"}, results_path)
    assert results_path.exists()

    # Export CSV
    csv_path = tmp_path / "transient.csv"
    transient_data = {
        "time": [0.0, 0.001, 0.002],
        "dipole_voltages": {1: [5.0, 5.0, 5.0]},
        "dipole_currents": {1: [0.05, 0.05, 0.05]},
    }
    exporter.export_transient_results_to_csv(transient_data, csv_path)
    assert csv_path.exists()
    csv_text = csv_path.read_text(encoding="utf-8")
    assert "time" in csv_text
    assert "dipole_voltage_1" in csv_text
    assert "dipole_1" in csv_text


def test_exporter_unsupported_formats(tmp_path: Path) -> None:
    c = Circuit()
    with pytest.raises(ValueError, match="Format non pris en charge"):
        exporter.export_circuit(c, tmp_path / "circuit.xml")

    with pytest.raises(ValueError, match="Format non pris en charge"):
        exporter.export_simulation_results_to_file({}, tmp_path / "results.txt")

    with pytest.raises(ValueError, match="Format non pris en charge"):
        exporter.export_transient_results_to_csv({}, tmp_path / "transient.dat")

    with pytest.raises(ValueError, match="Format non pris en charge"):
        importer.import_circuit(c, tmp_path / "circuit.txt")