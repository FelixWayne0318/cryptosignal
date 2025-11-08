"""
Expected Value (EV) calculation for signal publishing.

Implements EV formula from PUBLISHING.md:
EV = P·μ_win - (1-P)·μ_loss - cost_eff

Where:
- P: Probability of winning (from probability_v2.py)
- μ_win, μ_loss: Historical conditional mean returns (from backtested stats)
- cost_eff: Effective cost from F/I modulators

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 IMPORTANT: Data Source and Units
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. UNITS (统一量纲)
   ─────────────────
   All μ values are in PERCENTAGE TERMS (百分比形式):
   - μ_win = 0.052  → 5.2% average return when winning
   - μ_loss = -0.010 → -1.0% average return when losing
   - cost_eff = 0.002 → 0.2% effective cost (2 bps = 0.02%)

   EV output is also in percentage:
   - EV = 0.03 → Expected 3% return per trade

2. DATA SOURCE (数据来源)
   ──────────────────────
   Current Status: BOOTSTRAP / PLACEHOLDER VALUES

   ⚠️  The DEFAULT_STATS below are ESTIMATED values based on:
   - Industry average for crypto futures (50-85% win rate range)
   - Conservative risk/reward assumptions
   - NOT from actual backtest of this system

   TODO: Replace with ACTUAL backtest results:
   - Run historical backtest over 6-12 months
   - Stratify by probability bins [0.50-0.55, 0.55-0.60, ...]
   - Calculate true μ_win, μ_loss, sample_count for each bin
   - Save to data/ev_stats.json
   - Update this module to load from that file

3. CALIBRATION (校准要求)
   ─────────────────────
   For production use, you MUST:

   a) Run backtest and collect:
      - Entry price, exit price, side (long/short)
      - Predicted probability P at entry
      - Actual outcome (win/loss)
      - Return% = (exit - entry) / entry

   b) Bin by probability:
      - [0.50-0.55]: μ_win = mean(returns | win), μ_loss = mean(returns | loss)
      - [0.55-0.60]: ...
      - ... (10 bins total)

   c) Save to JSON:
      {
        "default": [...],
        "BTCUSDT": [...],  // Optional: symbol-specific
        "ETHUSDT": [...]
      }

   d) Load via:
      ev_calc = EVCalculator(stats_file="data/ev_stats.json")

4. VALIDATION (验证方法)
   ─────────────────────
   To verify EV accuracy:
   - Compare predicted EV vs actual returns over 100+ trades
   - Calculate Brier score for probability calibration
   - Check if EV > 0 signals actually profitable
   - Adjust μ values if systematic bias detected

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class EVStats:
    """Expected value statistics for a probability bin."""

    p_min: float
    p_max: float
    mu_win: float  # Mean winning return (positive)
    mu_loss: float  # Mean losing return (negative)
    samples: int

    def get_mu(self, probability: float) -> Tuple[float, float]:
        """Get μ_win and μ_loss for this bin."""
        return self.mu_win, abs(self.mu_loss)


class EVCalculator:
    """
    Calculate Expected Value for trade signals.

    Uses historical backtested data to estimate conditional mean returns.
    """

    # ⚠️  BOOTSTRAP / PLACEHOLDER VALUES - Replace with actual backtest data!
    # These are ESTIMATED values, NOT from real backtest of this system.
    # samples=0 indicates no historical data backing these numbers.
    #
    # Assumptions used for bootstrap:
    # - Higher P → Higher μ_win (as signal quality improves, wins get bigger)
    # - Higher P → Lower |μ_loss| (better signals = smaller losses via better stops)
    # - Risk/Reward improves with probability (roughly 2:1 to 50:1 at extremes)
    #
    # Units: All values in PERCENTAGE (e.g., 0.052 = 5.2%)
    DEFAULT_STATS = {
        "default": [
            # P ∈ [0.50, 0.55]: Near 50/50, conservative R:R ~0.9:1
            {"p_min": 0.50, "p_max": 0.55, "mu_win": 0.018, "mu_loss": -0.020, "samples": 0},

            # P ∈ [0.55, 0.60]: Slight edge, R:R ~1.2:1
            {"p_min": 0.55, "p_max": 0.60, "mu_win": 0.022, "mu_loss": -0.018, "samples": 0},

            # P ∈ [0.60, 0.65]: Moderate edge, R:R ~1.75:1
            {"p_min": 0.60, "p_max": 0.65, "mu_win": 0.028, "mu_loss": -0.016, "samples": 0},

            # P ∈ [0.65, 0.70]: Good edge, R:R ~2.4:1
            {"p_min": 0.65, "p_max": 0.70, "mu_win": 0.034, "mu_loss": -0.014, "samples": 0},

            # P ∈ [0.70, 0.75]: Strong edge, R:R ~3.5:1
            {"p_min": 0.70, "p_max": 0.75, "mu_win": 0.042, "mu_loss": -0.012, "samples": 0},

            # P ∈ [0.75, 0.80]: Very strong, R:R ~5.2:1
            {"p_min": 0.75, "p_max": 0.80, "mu_win": 0.052, "mu_loss": -0.010, "samples": 0},

            # P ∈ [0.80, 0.85]: Excellent, R:R ~8:1
            {"p_min": 0.80, "p_max": 0.85, "mu_win": 0.065, "mu_loss": -0.008, "samples": 0},

            # P ∈ [0.85, 0.90]: Rare quality, R:R ~13:1
            {"p_min": 0.85, "p_max": 0.90, "mu_win": 0.082, "mu_loss": -0.006, "samples": 0},

            # P ∈ [0.90, 0.95]: Exceptional, R:R ~26:1
            {"p_min": 0.90, "p_max": 0.95, "mu_win": 0.105, "mu_loss": -0.004, "samples": 0},

            # P ∈ [0.95, 1.00]: Near-certain, R:R ~67:1
            {"p_min": 0.95, "p_max": 1.00, "mu_win": 0.135, "mu_loss": -0.002, "samples": 0},
        ]
    }

    def __init__(self, stats_file: Optional[str] = None):
        """
        Initialize EV calculator.

        Args:
            stats_file: Path to ev_stats.json with historical data.
                       If None or file doesn't exist, uses DEFAULT_STATS
        """
        self.stats_by_symbol: Dict[str, list[EVStats]] = {}

        if stats_file:
            stats_path = Path(stats_file)
            if stats_path.exists():
                self._load_stats(stats_path)
                logger.info(f"Loaded EV stats from {stats_file}")
            else:
                logger.warning(
                    f"EV stats file not found: {stats_file}, using bootstrap defaults. "
                    f"⚠️  For production, calibrate with actual backtest data!"
                )
                self._load_default_stats()
        else:
            logger.warning(
                "Using default EV statistics (bootstrap/placeholder values). "
                "⚠️  These are NOT from actual backtest! "
                "For production use, run backtest and save to data/ev_stats.json"
            )
            self._load_default_stats()

    def _load_stats(self, stats_path: Path) -> None:
        """Load statistics from JSON file."""
        with open(stats_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for symbol, bins in data.items():
            self.stats_by_symbol[symbol] = [
                EVStats(**bin_data) for bin_data in bins
            ]

    def _load_default_stats(self) -> None:
        """Load default statistics."""
        default_bins = [
            EVStats(**bin_data) for bin_data in self.DEFAULT_STATS["default"]
        ]
        self.stats_by_symbol["default"] = default_bins

    def _find_bin(self, symbol: str, probability: float) -> Optional[EVStats]:
        """
        Find the statistics bin for a given probability.

        Args:
            symbol: Trading symbol
            probability: Probability value [0, 1]

        Returns:
            EVStats for the bin, or None if not found
        """
        # Try symbol-specific stats first
        bins = self.stats_by_symbol.get(symbol)

        # Fall back to default
        if not bins:
            bins = self.stats_by_symbol.get("default")

        if not bins:
            return None

        # Find matching bin
        for bin_stats in bins:
            if bin_stats.p_min <= probability < bin_stats.p_max:
                return bin_stats

        # Handle edge case: p = 1.0
        if probability >= bins[-1].p_max:
            return bins[-1]

        return None

    def calculate_ev(
        self,
        symbol: str,
        probability: float,
        cost_eff: float = 0.0,
        direction: str = "long"
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate Expected Value for a trade signal.

        Args:
            symbol: Trading symbol
            probability: Win probability [0, 1]
            cost_eff: Effective cost from modulators (default 0.0)
            direction: "long" or "short"

        Returns:
            Tuple of (ev, details_dict)

            details_dict contains:
            - ev: Expected value
            - p: Probability used
            - mu_win: Mean winning return
            - mu_loss: Mean losing return (positive value)
            - cost_eff: Effective cost
            - bin_samples: Number of historical samples in bin
        """
        # Find statistics bin
        bin_stats = self._find_bin(symbol, probability)

        if not bin_stats:
            logger.warning(f"No EV stats found for {symbol} p={probability:.3f}")
            # Conservative fallback: assume zero EV
            return 0.0, {
                "ev": 0.0,
                "p": probability,
                "mu_win": 0.0,
                "mu_loss": 0.0,
                "cost_eff": cost_eff,
                "bin_samples": 0,
                "warning": "no_stats"
            }

        # Get conditional means
        mu_win, mu_loss = bin_stats.get_mu(probability)

        # Calculate EV
        # EV = P·μ_win - (1-P)·μ_loss - cost_eff
        ev = probability * mu_win - (1.0 - probability) * mu_loss - cost_eff

        details = {
            "ev": ev,
            "p": probability,
            "mu_win": mu_win,
            "mu_loss": mu_loss,
            "cost_eff": cost_eff,
            "bin_samples": bin_stats.samples,
            "bin_range": [bin_stats.p_min, bin_stats.p_max]
        }

        return ev, details

    def passes_ev_gate(
        self,
        symbol: str,
        probability: float,
        cost_eff: float = 0.0,
        direction: str = "long"
    ) -> Tuple[bool, float, str]:
        """
        Check if signal passes EV > 0 hard gate.

        Args:
            symbol: Trading symbol
            probability: Win probability
            cost_eff: Effective cost
            direction: "long" or "short"

        Returns:
            Tuple of (passes, ev, reason)
        """
        ev, details = self.calculate_ev(symbol, probability, cost_eff, direction)

        if ev > 0:
            return True, ev, f"EV positive: {ev:.4f}"
        else:
            return False, ev, f"EV non-positive: {ev:.4f} ≤ 0"

    def get_min_probability_for_positive_ev(
        self,
        symbol: str,
        cost_eff: float = 0.0
    ) -> Optional[float]:
        """
        Find minimum probability needed for EV > 0.

        Args:
            symbol: Trading symbol
            cost_eff: Effective cost

        Returns:
            Minimum probability, or None if can't be determined
        """
        # Binary search for p where EV = 0
        p_low, p_high = 0.5, 1.0
        tolerance = 0.001

        for _ in range(20):  # Max iterations
            p_mid = (p_low + p_high) / 2.0
            ev, _ = self.calculate_ev(symbol, p_mid, cost_eff)

            if abs(ev) < tolerance:
                return p_mid

            if ev > 0:
                p_high = p_mid
            else:
                p_low = p_mid

        return p_low if p_low > 0.5 else None


# Global instance (lazy initialization)
_ev_calculator: Optional[EVCalculator] = None


def get_ev_calculator(stats_file: Optional[str] = None) -> EVCalculator:
    """
    Get global EV calculator instance.

    Args:
        stats_file: Path to ev_stats.json (only used on first call)

    Returns:
        EVCalculator instance
    """
    global _ev_calculator

    if _ev_calculator is None:
        # Try default location
        if stats_file is None:
            default_path = Path(__file__).parent.parent.parent / "data" / "ev_stats.json"
            if default_path.exists():
                stats_file = str(default_path)

        _ev_calculator = EVCalculator(stats_file)

    return _ev_calculator
