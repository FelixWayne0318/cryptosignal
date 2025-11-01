"""
Unified standardization chain for all A-layer factors.
Implements STANDARDS.md § 1.2 complete preprocessing pipeline.

Author: CryptoSignal v2.0 Compliance Team
Date: 2025-11-01
"""

import numpy as np
from typing import Tuple, Optional
from dataclasses import dataclass

@dataclass
class StandardizationDiagnostics:
    """Diagnostics output from standardization chain."""
    x_smooth: float      # After pre-smoothing
    z_raw: float         # Raw z-score (before winsorization)
    z_soft: float        # After soft winsorization
    s_k: float           # After tanh compression
    ew_median: float     # Current EW median
    ew_mad: float        # Current EW MAD
    bars_initialized: int  # Bars since initialization


class StandardizationChain:
    """
    Unified standardization pipeline for factor scores.

    Implements STANDARDS.md § 1.2 5-step chain:
    1. Pre-smoothing: EW with α=0.15
    2. Robust scaling: EW-Median/MAD (1.4826 factor)
    3. Soft winsorization: z0=2.5, zmax=6, λ=1.5
    4. Compression: tanh(z/τ) → ±100
    5. Publish filter: hysteresis + Δmax (simplified in v1, full in Phase 1.3)

    Example:
        >>> chain = StandardizationChain(alpha=0.15, tau=3.0)
        >>> for raw_value in data:
        >>>     score, diag = chain.standardize(raw_value)
        >>>     print(f"Raw: {raw_value:.2f} → Score: {score:.2f}")
    """

    def __init__(
        self,
        alpha: float = 0.15,
        tau: float = 3.0,
        z0: float = 2.5,
        zmax: float = 6.0,
        lam: float = 1.5
    ):
        """
        Initialize standardization chain with STANDARDS.md parameters.

        Args:
            alpha: Pre-smoothing coefficient (0.10-0.20, default 0.15)
            tau: Compression temperature (2.5-4.0, default 3.0)
            z0: Soft winsor threshold (default 2.5)
            zmax: Hard maximum z-score (default 6.0)
            lam: Winsor smoothness parameter (default 1.5)
        """
        # Validate parameters
        if not 0.05 <= alpha <= 0.30:
            raise ValueError(f"alpha={alpha} outside safe range [0.05, 0.30]")
        if not 1.0 <= tau <= 6.0:
            raise ValueError(f"tau={tau} outside safe range [1.0, 6.0]")

        self.alpha = alpha
        self.tau = tau
        self.z0 = z0
        self.zmax = zmax
        self.lam = lam

        # State variables (persistent across calls)
        self.ew_median: Optional[float] = None
        self.ew_mad: Optional[float] = None
        self.prev_smooth: Optional[float] = None
        self.bars_count: int = 0

    def standardize(self, x_raw: float) -> Tuple[float, StandardizationDiagnostics]:
        """
        Apply full standardization chain to raw input.

        Args:
            x_raw: Raw factor value (unstandardized)

        Returns:
            (s_pub, diagnostics):
                - s_pub: Final ±100 score ready for publishing
                - diagnostics: Diagnostic info for monitoring
        """
        self.bars_count += 1

        # Step 1: Pre-smoothing (α-weighted EW)
        if self.prev_smooth is None:
            # Cold start: use raw value
            x_smooth = x_raw
        else:
            # EW smoothing: x̃_t = α·x_t + (1-α)·x̃_{t-1}
            x_smooth = self.alpha * x_raw + (1 - self.alpha) * self.prev_smooth

        self.prev_smooth = x_smooth

        # Step 2: Robust scaling (EW-Median/MAD)
        if self.ew_median is None:
            # Cold start: initialize with first smooth value
            self.ew_median = x_smooth
            self.ew_mad = 0.01  # Small initial MAD (prevents div-by-zero)
            z_raw = 0.0
        else:
            # Update EW median: μ̃_t = α·x̃_t + (1-α)·μ̃_{t-1}
            self.ew_median = self.alpha * x_smooth + (1 - self.alpha) * self.ew_median

            # Update EW MAD: MAD_t = α·|x̃_t - μ̃_t| + (1-α)·MAD_{t-1}
            abs_dev = abs(x_smooth - self.ew_median)
            self.ew_mad = self.alpha * abs_dev + (1 - self.alpha) * self.ew_mad

            # Robust z-score: z = (x̃ - μ̃) / (1.4826 * MAD)
            # (1.4826 is consistency constant for Gaussian distribution)
            scale = 1.4826 * max(self.ew_mad, 1e-6)  # Floor at 1e-6
            z_raw = (x_smooth - self.ew_median) / scale

        # Step 3: Soft winsorization
        z_soft = self._soft_winsor(z_raw, self.z0, self.zmax, self.lam)

        # Step 4: Compress to ±100 via tanh
        # s_k = 100 · tanh(z_soft / τ)
        s_k = 100.0 * np.tanh(z_soft / self.tau)

        # Step 5: Publish filter (simplified - full version in Change #3)
        # For now, direct passthrough (Phase 1.3 adds hysteresis)
        s_pub = s_k

        # Build diagnostics
        diagnostics = StandardizationDiagnostics(
            x_smooth=x_smooth,
            z_raw=z_raw,
            z_soft=z_soft,
            s_k=s_k,
            ew_median=self.ew_median,
            ew_mad=self.ew_mad,
            bars_initialized=self.bars_count
        )

        return s_pub, diagnostics

    @staticmethod
    def _soft_winsor(z: float, z0: float, zmax: float, lam: float) -> float:
        """
        Soft winsorization with smooth transition.

        Piecewise function:
        - |z| ≤ z0: No clipping (z_soft = z)
        - z0 < |z| < zmax: Smooth transition (exponential decay)
        - |z| ≥ zmax: Hard clip (z_soft = ±zmax)

        Formula (transition region):
            z_soft = sign(z) · [z0 + (zmax - z0) · (1 - exp(-λ·(|z| - z0)))]

        Args:
            z: Input z-score
            z0: Threshold for soft clipping (2.5)
            zmax: Hard maximum (6.0)
            lam: Smoothness parameter (1.5)

        Returns:
            z_soft: Winsorized z-score
        """
        abs_z = abs(z)

        if abs_z <= z0:
            # No clipping needed
            return z
        elif abs_z >= zmax:
            # Hard clip at zmax
            return np.sign(z) * zmax
        else:
            # Smooth transition region
            excess = abs_z - z0
            clipped = z0 + (zmax - z0) * (1.0 - np.exp(-lam * excess))
            return np.sign(z) * clipped

    def reset(self):
        """Reset internal state (for testing or symbol change)."""
        self.ew_median = None
        self.ew_mad = None
        self.prev_smooth = None
        self.bars_count = 0


# Convenience function for single-use
def standardize_value(
    x_raw: float,
    alpha: float = 0.15,
    tau: float = 3.0
) -> float:
    """
    Stateless standardization (creates new chain each call).

    WARNING: Do NOT use in production loops (loses EW state).
    Use StandardizationChain instance for persistent state.
    """
    chain = StandardizationChain(alpha=alpha, tau=tau)
    s_pub, _ = chain.standardize(x_raw)
    return s_pub
