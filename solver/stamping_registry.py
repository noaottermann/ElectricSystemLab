"""
Module pour configurer et attacher les méthodes de stamping polymorphes sur les classes de composants.

Attache automatiquement les méthodes stamp_dc(), stamp_ac() et stamp_transient()
à chaque classe de composant selon le pattern Strategy / Polymorphisme.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _register_stamping_methods() -> None:
    """Enregistre et attache les méthodes de stamping sur toutes les classes de composants."""
    from model import components as comp
    from solver import stamping

    # Mapping: classe -> (methode_dc, methode_ac, methode_transient)
    registry: list[tuple[type, object, object, object]] = [
        # Passifs linéaires
        (comp.Resistor, stamping.stamp_resistor_dc, stamping.stamp_resistor_ac, stamping.stamp_resistor_transient),
        (comp.Switch, stamping.stamp_resistor_dc, stamping.stamp_resistor_ac, stamping.stamp_resistor_transient),
        (comp.Ammeter, stamping.stamp_resistor_dc, stamping.stamp_resistor_ac, stamping.stamp_resistor_transient),
        (comp.Voltmeter, stamping.stamp_resistor_dc, stamping.stamp_resistor_ac, stamping.stamp_resistor_transient),

        # Éléments réactifs / dynamiques
        (comp.Capacitor, stamping.stamp_capacitor_dc, stamping.stamp_capacitor_ac, stamping.stamp_capacitor_transient),
        (comp.Inductor, stamping.stamp_inductor_dc, stamping.stamp_inductor_ac, stamping.stamp_inductor_transient),

        # Sources de tension
        (comp.VoltageSource, stamping.stamp_voltage_source_dc, stamping.stamp_voltage_source_ac, stamping.stamp_voltage_source_transient),
        (comp.VoltageSourceDC, stamping.stamp_voltage_source_dc, stamping.stamp_voltage_source_ac, stamping.stamp_voltage_source_transient),
        (comp.VoltageSourceAC, stamping.stamp_voltage_source_dc, stamping.stamp_voltage_source_ac, stamping.stamp_voltage_source_transient),
        (comp.PulseVoltageSource, stamping.stamp_pulse_voltage_source_dc, stamping.stamp_pulse_voltage_source_ac, stamping.stamp_pulse_voltage_source_transient),

        # Sources de courant
        (comp.CurrentSource, stamping.stamp_current_source_dc, stamping.stamp_current_source_ac, stamping.stamp_current_source_transient),
        (comp.CurrentSourceDC, stamping.stamp_current_source_dc, stamping.stamp_current_source_ac, stamping.stamp_current_source_transient),
        (comp.CurrentSourceAC, stamping.stamp_current_source_dc, stamping.stamp_current_source_ac, stamping.stamp_current_source_transient),

        # Sources commandées
        (comp.VoltageControlledCurrentSource, stamping.stamp_vccs_dc, stamping.stamp_vccs_ac, stamping.stamp_vccs_transient),
        (comp.CurrentControlledCurrentSource, stamping.stamp_cccs_dc, stamping.stamp_cccs_ac, stamping.stamp_cccs_transient),
        (comp.VoltageControlledVoltageSource, stamping.stamp_vcvs_dc, stamping.stamp_vcvs_ac, stamping.stamp_vcvs_transient),
        (comp.CurrentControlledVoltageSource, stamping.stamp_ccvs_dc, stamping.stamp_ccvs_ac, stamping.stamp_ccvs_transient),

        # Non linéaires / Semi-conducteurs
        (comp.Diode, stamping.stamp_diode_dc, stamping.stamp_diode_ac, stamping.stamp_diode_transient),
        (comp.ZenerDiode, stamping.stamp_zener_diode_dc, stamping.stamp_zener_diode_ac, stamping.stamp_zener_diode_transient),
        (comp.LED, stamping.stamp_diode_dc, stamping.stamp_diode_ac, stamping.stamp_diode_transient),
        (comp.Transistor, stamping.stamp_transistor_dc, stamping.stamp_transistor_ac, stamping.stamp_transistor_transient),
        (comp.MOSFET, stamping.stamp_mosfet_dc, stamping.stamp_mosfet_ac, stamping.stamp_mosfet_transient),
        (comp.MOSFET_NMOS, stamping.stamp_mosfet_dc, stamping.stamp_mosfet_ac, stamping.stamp_mosfet_transient),
        (comp.MOSFET_PMOS, stamping.stamp_mosfet_dc, stamping.stamp_mosfet_ac, stamping.stamp_mosfet_transient),

        # Composants actifs et intégrés
        (comp.OpAmp, stamping.stamp_opamp_dc, stamping.stamp_opamp_ac, stamping.stamp_opamp_transient),
        (comp.Comparator, stamping.stamp_comparator_dc, stamping.stamp_comparator_ac, stamping.stamp_comparator_transient),
        (comp.Transformer, stamping.stamp_transformer_dc, stamping.stamp_transformer_ac, stamping.stamp_transformer_transient),
        (comp.Potentiometer, stamping.stamp_potentiometer_dc, stamping.stamp_potentiometer_ac, stamping.stamp_potentiometer_transient),

        # Logique & Protection
        (comp.LogicGate, stamping.stamp_logic_gate_dc, stamping.stamp_logic_gate_ac, stamping.stamp_logic_gate_transient),
        (comp.LogicGateAND, stamping.stamp_logic_gate_dc, stamping.stamp_logic_gate_ac, stamping.stamp_logic_gate_transient),
        (comp.LogicGateOR, stamping.stamp_logic_gate_dc, stamping.stamp_logic_gate_ac, stamping.stamp_logic_gate_transient),
        (comp.LogicGateNOT, stamping.stamp_logic_gate_dc, stamping.stamp_logic_gate_ac, stamping.stamp_logic_gate_transient),
        (comp.LogicGateNAND, stamping.stamp_logic_gate_dc, stamping.stamp_logic_gate_ac, stamping.stamp_logic_gate_transient),
        (comp.LogicGateNOR, stamping.stamp_logic_gate_dc, stamping.stamp_logic_gate_ac, stamping.stamp_logic_gate_transient),
        (comp.LogicGateXOR, stamping.stamp_logic_gate_dc, stamping.stamp_logic_gate_ac, stamping.stamp_logic_gate_transient),
        (comp.Fuse, stamping.stamp_fuse_dc, stamping.stamp_fuse_ac, stamping.stamp_fuse_transient),

        # Symboles
        (comp.Ground, stamping.stamp_noop, stamping.stamp_noop, stamping.stamp_noop),
    ]

    for comp_class, dc_fn, ac_fn, transient_fn in registry:
        if dc_fn is not None:
            setattr(comp_class, "stamp_dc", dc_fn)
            logger.debug("Enregistre stamp_dc pour %s", comp_class.__name__)
        if ac_fn is not None:
            setattr(comp_class, "stamp_ac", ac_fn)
            logger.debug("Enregistre stamp_ac pour %s", comp_class.__name__)
        if transient_fn is not None:
            setattr(comp_class, "stamp_transient", transient_fn)
            logger.debug("Enregistre stamp_transient pour %s", comp_class.__name__)


def validate_registry() -> bool:
    """
    Vérifie que tous les composants enregistrés dans le catalogue possèdent
    les méthodes polymorphes stamp_dc, stamp_ac et stamp_transient.
    """
    from model.components import get_component_registry

    all_valid = True
    for comp_name, comp_class in get_component_registry().items():
        if not hasattr(comp_class, "stamp_dc"):
            logger.warning("%s n'a pas de methode stamp_dc", comp_name)
            all_valid = False
        if not hasattr(comp_class, "stamp_ac"):
            logger.warning("%s n'a pas de methode stamp_ac", comp_name)
            all_valid = False
        if not hasattr(comp_class, "stamp_transient"):
            logger.warning("%s n'a pas de methode stamp_transient", comp_name)
            all_valid = False
    return all_valid


# Enregistrement automatique à l'importation
_register_stamping_methods()
