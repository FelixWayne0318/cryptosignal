"""
B-layer: Modulators (F/I factors).

These factors do NOT participate in directional scoring.
They ONLY modulate:
1. Teff (probability temperature)
2. cost_eff (EV cost adjustment)
3. Publishing thresholds (p_min, Δp_min)
"""

from .fi_modulators import FIModulator, get_fi_modulator

__all__ = ['FIModulator', 'get_fi_modulator']
