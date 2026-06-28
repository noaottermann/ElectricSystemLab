"""
Module pour configurer les méthodes de stamping polymorphe sur les composants.

Attache les méthodes stamp_dc() et stamp_ac() à chaque classe de composant,
utilisant le pattern Strategy pour diriger vers les bonnes implémentations.
"""

from __future__ import annotations


def _register_stamping_methods():
    """Enregistre les méthodes de stamping sur toutes les classes de composant."""
    from model import components as comp_module
    from solver import stamping
    
    # Mapping classe -> (method_dc, method_ac)
    stamping_map = {
        comp_module.Resistor: (stamping.stamp_resistor_dc, stamping.stamp_resistor_dc),
        comp_module.Switch: (stamping.stamp_resistor_dc, stamping.stamp_resistor_dc),  # Même traitement que résistance
        comp_module.Ammeter: (stamping.stamp_resistor_dc, stamping.stamp_resistor_dc),
        comp_module.Voltmeter: (stamping.stamp_resistor_dc, stamping.stamp_resistor_dc),
        
        comp_module.Capacitor: (lambda c, ctx: None, stamping.stamp_capacitor_ac),
        comp_module.Inductor: (lambda c, ctx: None, stamping.stamp_inductor_ac),
        
        comp_module.VoltageSource: (stamping.stamp_voltage_source_dc, stamping.stamp_voltage_source_ac),
        comp_module.VoltageSourceDC: (stamping.stamp_voltage_source_dc, lambda c, ctx: None),
        comp_module.VoltageSourceAC: (lambda c, ctx: None, stamping.stamp_voltage_source_ac),
        
        comp_module.CurrentSource: (stamping.stamp_current_source_dc, stamping.stamp_current_source_ac),
        comp_module.CurrentSourceDC: (stamping.stamp_current_source_dc, lambda c, ctx: None),
        comp_module.CurrentSourceAC: (lambda c, ctx: None, stamping.stamp_current_source_ac),
        
        comp_module.VoltageControlledCurrentSource: (stamping.stamp_vccs_dc, stamping.stamp_vccs_dc),
        comp_module.CurrentControlledCurrentSource: (stamping.stamp_cccs_dc, stamping.stamp_cccs_dc),
        comp_module.VoltageControlledVoltageSource: (stamping.stamp_vcvs_dc, stamping.stamp_vcvs_dc),
        comp_module.CurrentControlledVoltageSource: (stamping.stamp_ccvs_dc, stamping.stamp_ccvs_dc),
        
        comp_module.Diode: (stamping.stamp_diode_dc, lambda c, ctx: None),  # LED non supportée en AC
    }
    
    for cls, (method_dc, method_ac) in stamping_map.items():
        cls.stamp_dc = method_dc
        cls.stamp_ac = method_ac


# Appel automatique lors de l'import
_register_stamping_methods()
