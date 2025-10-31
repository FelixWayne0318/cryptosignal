"""
Execution metrics estimator (simplified version).

Since we don't have depth@100ms stream yet, this provides proxy estimates
using K-line OHLC data for spread/impact calculations.

For production: Replace with real depth-based calculations once depth stream is available.
"""

from typing import Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ExecutionMetrics:
    """Execution metrics for a symbol."""

    spread_bps: float  # Estimated spread in basis points
    impact_bps: float  # Estimated impact in basis points
    OBI: float  # Order book imbalance (estimated, [-1, 1])
    liquidity_score: float  # Liquidity estimate [0, 1]


class ExecutionMetricsEstimator:
    """
    Estimate execution metrics from K-line data.

    This is a SIMPLIFIED VERSION using OHLC proxies.
    Replace with real depth calculations when depth stream is available.
    """

    def __init__(self):
        """Initialize estimator."""
        pass

    def estimate_spread_bps(
        self,
        high: float,
        low: float,
        close: float,
        volume: float
    ) -> float:
        """
        Estimate spread from H-L range.

        Proxy formula: spread_bps ≈ (high - low) / close * 10000 * 0.5

        Args:
            high: High price
            low: Low price
            close: Close price
            volume: Volume

        Returns:
            Estimated spread in bps
        """
        if close <= 0:
            return 999.9  # Invalid

        # High-low range as spread proxy
        # Factor 0.5 because H-L includes market movement, not just spread
        spread_bps = (high - low) / close * 10000 * 0.5

        # Adjust for volume (low volume → wider spread)
        if volume > 0:
            # Lower volume means less liquidity, wider spread
            volume_factor = min(2.0, 1.0 / (volume ** 0.1))  # Dampened adjustment
            spread_bps *= volume_factor

        # Clamp to reasonable range
        spread_bps = max(1.0, min(500.0, spread_bps))

        return spread_bps

    def estimate_impact_bps(
        self,
        spread_bps: float,
        volume: float,
        avg_volume: float = None
    ) -> float:
        """
        Estimate market impact.

        Proxy formula: impact ≈ spread * 1.5 + volume_adj

        Args:
            spread_bps: Estimated spread
            volume: Current volume
            avg_volume: Average volume (if available)

        Returns:
            Estimated impact in bps
        """
        # Base impact from spread
        impact_bps = spread_bps * 1.5

        # Volume adjustment
        if avg_volume and avg_volume > 0:
            volume_ratio = volume / avg_volume
            # Low volume → higher impact
            if volume_ratio < 0.5:
                impact_bps *= 1.5
            elif volume_ratio < 0.8:
                impact_bps *= 1.2
            elif volume_ratio > 2.0:
                impact_bps *= 0.8
            elif volume_ratio > 1.5:
                impact_bps *= 0.9

        # Clamp
        impact_bps = max(spread_bps, min(1000.0, impact_bps))

        return impact_bps

    def estimate_obi(
        self,
        taker_buy_volume: float,
        total_volume: float
    ) -> float:
        """
        Estimate Order Book Imbalance from taker buy/sell ratio.

        OBI ∈ [-1, 1]
        - OBI > 0: More buying pressure (bid side thicker)
        - OBI < 0: More selling pressure (ask side thicker)

        Proxy: Use taker buy ratio as proxy
        OBI ≈ 2 * (taker_buy_ratio - 0.5)

        Args:
            taker_buy_volume: Taker buy volume
            total_volume: Total volume

        Returns:
            OBI estimate in [-1, 1]
        """
        if total_volume <= 0:
            return 0.0

        taker_buy_ratio = taker_buy_volume / total_volume

        # Convert to [-1, 1]
        obi = 2.0 * (taker_buy_ratio - 0.5)

        # Clamp
        obi = max(-1.0, min(1.0, obi))

        return obi

    def estimate_liquidity_score(
        self,
        volume: float,
        avg_volume: float,
        spread_bps: float
    ) -> float:
        """
        Estimate overall liquidity score [0, 1].

        Higher is better:
        - High volume relative to average
        - Low spread

        Args:
            volume: Current volume
            avg_volume: Average volume
            spread_bps: Spread in bps

        Returns:
            Liquidity score [0, 1]
        """
        # Volume component
        if avg_volume > 0:
            volume_score = min(1.0, volume / avg_volume)
        else:
            volume_score = 0.5

        # Spread component (inverse: lower spread = higher score)
        # Typical spread range: 5-50 bps
        spread_score = max(0.0, 1.0 - spread_bps / 50.0)

        # Combine (weighted average)
        liquidity_score = 0.6 * volume_score + 0.4 * spread_score

        # Clamp
        liquidity_score = max(0.0, min(1.0, liquidity_score))

        return liquidity_score

    def calculate(
        self,
        high: float,
        low: float,
        close: float,
        volume: float,
        taker_buy_volume: float,
        avg_volume: Optional[float] = None
    ) -> ExecutionMetrics:
        """
        Calculate all execution metrics.

        Args:
            high: High price
            low: Low price
            close: Close price
            volume: Total volume
            taker_buy_volume: Taker buy volume
            avg_volume: Average volume (optional)

        Returns:
            ExecutionMetrics object
        """
        spread_bps = self.estimate_spread_bps(high, low, close, volume)
        impact_bps = self.estimate_impact_bps(spread_bps, volume, avg_volume)
        obi = self.estimate_obi(taker_buy_volume, volume)
        liquidity_score = self.estimate_liquidity_score(
            volume,
            avg_volume if avg_volume else volume,
            spread_bps
        )

        return ExecutionMetrics(
            spread_bps=spread_bps,
            impact_bps=impact_bps,
            OBI=obi,
            liquidity_score=liquidity_score
        )


class ExecutionGates:
    """
    Execution layer hard gates per PUBLISHING.md.

    Gates check if execution conditions are favorable for opening position.
    """

    # Default thresholds
    DEFAULT_THRESHOLDS = {
        "standard": {
            "impact_bps": 10.0,
            "spread_bps": 35.0,
            "obi_abs": 0.30,
        },
        "newcoin": {
            "impact_bps": 7.0,
            "spread_bps": 30.0,
            "obi_abs": 0.25,
        }
    }

    def __init__(self, thresholds: Optional[Dict] = None):
        """
        Initialize execution gates.

        Args:
            thresholds: Custom thresholds (uses defaults if None)
        """
        self.thresholds = thresholds or self.DEFAULT_THRESHOLDS

    def check_gates(
        self,
        metrics: ExecutionMetrics,
        is_newcoin: bool = False
    ) -> Tuple[bool, Dict[str, any]]:
        """
        Check if execution metrics pass all gates.

        Args:
            metrics: Execution metrics
            is_newcoin: Use newcoin thresholds

        Returns:
            Tuple of (passes, details_dict)
        """
        thresh_key = "newcoin" if is_newcoin else "standard"
        thresh = self.thresholds[thresh_key]

        # Check each gate
        checks = {
            "impact": metrics.impact_bps <= thresh["impact_bps"],
            "spread": metrics.spread_bps <= thresh["spread_bps"],
            "obi": abs(metrics.OBI) <= thresh["obi_abs"],
        }

        all_pass = all(checks.values())

        details = {
            "passes": all_pass,
            "checks": checks,
            "metrics": {
                "impact_bps": metrics.impact_bps,
                "spread_bps": metrics.spread_bps,
                "OBI": metrics.OBI,
            },
            "thresholds": thresh,
            "failed_gates": [k for k, v in checks.items() if not v]
        }

        if not all_pass:
            details["reason"] = f"Failed gates: {details['failed_gates']}"
        else:
            details["reason"] = "All execution gates passed"

        return all_pass, details


# Global instance
_estimator: Optional[ExecutionMetricsEstimator] = None
_gates: Optional[ExecutionGates] = None


def get_execution_estimator() -> ExecutionMetricsEstimator:
    """Get global execution metrics estimator."""
    global _estimator
    if _estimator is None:
        _estimator = ExecutionMetricsEstimator()
    return _estimator


def get_execution_gates(thresholds: Optional[Dict] = None) -> ExecutionGates:
    """
    Get global execution gates.

    Args:
        thresholds: Custom thresholds (only used on first call)
    """
    global _gates
    if _gates is None:
        _gates = ExecutionGates(thresholds)
    return _gates
