"""
F/I Modulators implementation per MODULATORS.md.

F (Funding/Crowding): Measures market crowding
I (Independence): Measures correlation with BTC/ETH

These factors do NOT participate in scoring. They only adjust:
1. Teff = T0·(1+βF·gF)/(1+βI·gI)  - Probability temperature
2. cost_eff = pen_F + pen_I - rew_I  - EV cost
3. p_min, Δp_min - Publishing thresholds
"""

import math
from typing import Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class ModulatorParams:
    """Parameters for F/I modulators."""

    # Temperature modulation
    T0: float = 50.0  # Base temperature
    beta_F: float = 0.15  # F sensitivity (crowding increases temp)
    beta_I: float = 0.10  # I sensitivity (independence decreases temp)
    T_min: float = 25.0  # Min temperature
    T_max: float = 100.0  # Max temperature

    # Cost modulation
    pen_F_low: float = 0.002  # Penalty when F < 0.3
    pen_F_high: float = 0.005  # Penalty when F > 0.7
    pen_I_low: float = 0.003  # Penalty when I < 0.3
    rew_I_high: float = -0.002  # Reward when I > 0.7

    # Threshold modulation
    p0: float = 0.58  # Base probability threshold
    theta_F: float = 0.03  # F threshold adjustment
    theta_I: float = -0.02  # I threshold adjustment (negative = easier when independent)
    delta_p0: float = 0.03  # Base probability change threshold

    # g(x) normalization
    gamma: float = 4.0  # tanh steepness
    alpha_ema: float = 0.2  # EMA smoothing


class FIModulator:
    """
    F/I modulator that adjusts temperature, cost, and thresholds.

    Does NOT participate in directional scoring!
    """

    def __init__(self, params: ModulatorParams = None):
        """
        Initialize modulator.

        Args:
            params: Modulator parameters (uses defaults if None)
        """
        self.params = params or ModulatorParams()

        # State for EMA smoothing
        self.g_F_ema: Dict[str, float] = {}
        self.g_I_ema: Dict[str, float] = {}

    def normalize_g(self, x: float) -> float:
        """
        Normalize raw F/I value to [-1, 1] using tanh.

        Formula: g(x) = tanh(γ·(x - 0.5))

        Args:
            x: Raw F or I value [0, 1]

        Returns:
            Normalized value [-1, 1]
        """
        return math.tanh(self.params.gamma * (x - 0.5))

    def smooth_g(self, symbol: str, g_raw: float, is_F: bool) -> float:
        """
        Apply EMA smoothing to g(x).

        Args:
            symbol: Trading symbol
            g_raw: Raw g(x) value
            is_F: True for F factor, False for I factor

        Returns:
            Smoothed g(x)
        """
        alpha = self.params.alpha_ema
        state_dict = self.g_F_ema if is_F else self.g_I_ema

        if symbol not in state_dict:
            state_dict[symbol] = g_raw
            return g_raw

        # EMA update
        g_smooth = alpha * g_raw + (1 - alpha) * state_dict[symbol]
        state_dict[symbol] = g_smooth

        return g_smooth

    def calculate_teff(
        self,
        F_raw: float,
        I_raw: float,
        symbol: str = "default"
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate effective temperature.

        Formula: Teff = clip(T0·(1+βF·gF)/(1+βI·gI), Tmin, Tmax)

        Args:
            F_raw: Raw F factor value [0, 1]
            I_raw: Raw I factor value [0, 1]
            symbol: Trading symbol (for EMA state)

        Returns:
            Tuple of (Teff, details_dict)
        """
        # Normalize and smooth
        g_F_raw = self.normalize_g(F_raw)
        g_I_raw = self.normalize_g(I_raw)

        g_F = self.smooth_g(symbol, g_F_raw, is_F=True)
        g_I = self.smooth_g(symbol, g_I_raw, is_F=False)

        # Calculate Teff
        numerator = self.params.T0 * (1.0 + self.params.beta_F * g_F)
        denominator = 1.0 + self.params.beta_I * g_I

        if abs(denominator) < 1e-6:
            Teff = self.params.T0
        else:
            Teff = numerator / denominator

        # Clamp to limits
        Teff = max(self.params.T_min, min(self.params.T_max, Teff))

        details = {
            "Teff": Teff,
            "T0": self.params.T0,
            "g_F": g_F,
            "g_I": g_I,
            "numerator": numerator,
            "denominator": denominator
        }

        return Teff, details

    def calculate_cost_eff(
        self,
        F_raw: float,
        I_raw: float
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate effective cost adjustment.

        Formula: cost_eff = pen_F + pen_I - rew_I

        Where:
        - pen_F: Penalty when crowded (F high)
        - pen_I: Penalty when correlated (I low)
        - rew_I: Reward when independent (I high)

        Args:
            F_raw: Raw F factor value [0, 1]
            I_raw: Raw I factor value [0, 1]

        Returns:
            Tuple of (cost_eff, details_dict)
        """
        # F penalty (crowding)
        if F_raw < 0.3:
            pen_F = 0.0  # No penalty when not crowded
        elif F_raw < 0.7:
            # Linear interpolation
            pen_F = self.params.pen_F_low + (F_raw - 0.3) / 0.4 * (
                self.params.pen_F_high - self.params.pen_F_low
            )
        else:
            pen_F = self.params.pen_F_high

        # I penalty (correlation) and reward (independence)
        if I_raw < 0.3:
            pen_I = self.params.pen_I_low
            rew_I = 0.0
        elif I_raw < 0.7:
            pen_I = self.params.pen_I_low * (0.7 - I_raw) / 0.4
            rew_I = 0.0
        else:
            pen_I = 0.0
            rew_I = self.params.rew_I_high * (I_raw - 0.7) / 0.3

        cost_eff = pen_F + pen_I - rew_I

        details = {
            "cost_eff": cost_eff,
            "pen_F": pen_F,
            "pen_I": pen_I,
            "rew_I": rew_I,
            "F_raw": F_raw,
            "I_raw": I_raw
        }

        return cost_eff, details

    def calculate_thresholds(
        self,
        F_raw: float,
        I_raw: float,
        symbol: str = "default"
    ) -> Tuple[float, float, Dict[str, Any]]:
        """
        Calculate adjusted publishing thresholds.

        Formula:
        p_min = p0 + θF·max(0, gF) + θI·min(0, gI)
        Δp_min = Δp0  (currently fixed)

        Args:
            F_raw: Raw F factor value [0, 1]
            I_raw: Raw I factor value [0, 1]
            symbol: Trading symbol

        Returns:
            Tuple of (p_min, delta_p_min, details_dict)
        """
        # Normalize and smooth
        g_F_raw = self.normalize_g(F_raw)
        g_I_raw = self.normalize_g(I_raw)

        g_F = self.smooth_g(symbol, g_F_raw, is_F=True)
        g_I = self.smooth_g(symbol, g_I_raw, is_F=False)

        # Calculate adjusted p_min
        # High F (crowding) increases threshold (harder to publish)
        # Low I (correlated) increases threshold (harder to publish)
        p_min = self.params.p0 + \
                self.params.theta_F * max(0.0, g_F) + \
                self.params.theta_I * min(0.0, g_I)

        # Clamp to reasonable range
        p_min = max(0.50, min(0.75, p_min))

        delta_p_min = self.params.delta_p0

        details = {
            "p_min": p_min,
            "delta_p_min": delta_p_min,
            "p0": self.params.p0,
            "g_F": g_F,
            "g_I": g_I,
            "adj_F": self.params.theta_F * max(0.0, g_F),
            "adj_I": self.params.theta_I * min(0.0, g_I)
        }

        return p_min, delta_p_min, details

    def modulate(
        self,
        F_raw: float,
        I_raw: float,
        symbol: str = "default"
    ) -> Dict[str, Any]:
        """
        Complete modulation calculation.

        Returns all adjusted values: Teff, cost_eff, p_min, delta_p_min.

        Args:
            F_raw: Raw F factor value [0, 1]
            I_raw: Raw I factor value [0, 1]
            symbol: Trading symbol

        Returns:
            Dict with all modulated values and details
        """
        Teff, teff_details = self.calculate_teff(F_raw, I_raw, symbol)
        cost_eff, cost_details = self.calculate_cost_eff(F_raw, I_raw)
        p_min, delta_p_min, thresh_details = self.calculate_thresholds(F_raw, I_raw, symbol)

        return {
            "Teff": Teff,
            "cost_eff": cost_eff,
            "p_min": p_min,
            "delta_p_min": delta_p_min,
            "details": {
                "teff": teff_details,
                "cost": cost_details,
                "thresholds": thresh_details
            }
        }

    def verify_assertions(self, F_raw: float, I_raw: float) -> Dict[str, bool]:
        """
        Verify online assertions from spec.

        Assertions:
        1. F↑ → Teff↑ (crowding makes probability more uncertain)
        2. F↑ → cost↑ (crowding increases costs)
        3. F↑ → p_min↑ (crowding makes publishing harder)
        4. I↓ → Teff↑ (correlation makes probability more uncertain)
        5. I↓ → cost↑ (correlation increases costs)

        Args:
            F_raw: F factor value
            I_raw: I factor value

        Returns:
            Dict of assertion results (True = passed)
        """
        # Test with small delta
        delta = 0.01

        # Baseline
        result_base = self.modulate(F_raw, I_raw, "test")

        # F increase
        result_F_up = self.modulate(F_raw + delta, I_raw, "test")

        # I decrease
        result_I_down = self.modulate(F_raw, I_raw - delta, "test")

        assertions = {
            "F_up_Teff_up": result_F_up["Teff"] >= result_base["Teff"],
            "F_up_cost_up": result_F_up["cost_eff"] >= result_base["cost_eff"],
            "F_up_pmin_up": result_F_up["p_min"] >= result_base["p_min"],
            "I_down_Teff_up": result_I_down["Teff"] >= result_base["Teff"],
            "I_down_cost_up": result_I_down["cost_eff"] >= result_base["cost_eff"]
        }

        return assertions


# Global instance
_fi_modulator: FIModulator = None


def get_fi_modulator(params: ModulatorParams = None) -> FIModulator:
    """
    Get global FI modulator instance.

    Args:
        params: Modulator parameters (only used on first call)

    Returns:
        FIModulator instance
    """
    global _fi_modulator

    if _fi_modulator is None:
        _fi_modulator = FIModulator(params)

    return _fi_modulator
