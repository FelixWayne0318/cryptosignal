"""
Integrated four-gates checker for Prime signal publishing.

Per PUBLISHING.md, all Prime signals must pass four gates:
1. DataQual ≥ 0.90
2. EV > 0
3. Execution (impact/spread/OBI within limits)
4. Probability threshold (p ≥ p_min, ΔP ≥ Δp_min)
"""

from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime

# Import gate components
from ats_core.data.quality import DataQualMonitor
from ats_core.scoring.expected_value import get_ev_calculator
from ats_core.execution.metrics_estimator import ExecutionMetrics, get_execution_gates
from ats_core.modulators.fi_modulators import get_fi_modulator


@dataclass
class GateResult:
    """Result of gate checking."""

    passed: bool
    gate_name: str
    value: Any
    threshold: Any
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class FourGatesChecker:
    """
    Checks all four gates for Prime signal publishing.

    Usage:
        checker = FourGatesChecker()
        passes, results = checker.check_all_gates(...)
        if passes:
            # OK to publish Prime
    """

    def __init__(
        self,
        dataqual_monitor: Optional[DataQualMonitor] = None,
        custom_thresholds: Optional[Dict] = None
    ):
        """
        Initialize four-gates checker.

        Args:
            dataqual_monitor: DataQual monitor instance (creates new if None)
            custom_thresholds: Custom gate thresholds
        """
        self.dataqual_monitor = dataqual_monitor or DataQualMonitor()
        self.ev_calculator = get_ev_calculator()
        self.execution_gates = get_execution_gates()
        self.fi_modulator = get_fi_modulator()

        self.thresholds = custom_thresholds or {}

    def check_gate1_dataqual(
        self,
        symbol: str
    ) -> GateResult:
        """
        Gate 1: DataQual ≥ 0.90

        Args:
            symbol: Trading symbol

        Returns:
            GateResult
        """
        quality = self.dataqual_monitor.get_quality(symbol)
        can_publish, dataqual, reason = self.dataqual_monitor.can_publish_prime(symbol)

        return GateResult(
            passed=can_publish,
            gate_name="DataQual",
            value=dataqual,
            threshold=0.90,
            details={
                "dataqual": dataqual,
                "miss_rate": quality.miss_rate,
                "oo_order_rate": quality.oo_order_rate,
                "drift_rate": quality.drift_rate,
                "mismatch_rate": quality.mismatch_rate,
                "reason": reason
            }
        )

    def check_gate2_ev(
        self,
        symbol: str,
        probability: float,
        cost_eff: float = 0.0
    ) -> GateResult:
        """
        Gate 2: EV > 0

        Args:
            symbol: Trading symbol
            probability: Win probability
            cost_eff: Effective cost from modulators

        Returns:
            GateResult
        """
        passes, ev, reason = self.ev_calculator.passes_ev_gate(
            symbol=symbol,
            probability=probability,
            cost_eff=cost_eff
        )

        ev_value, ev_details = self.ev_calculator.calculate_ev(
            symbol=symbol,
            probability=probability,
            cost_eff=cost_eff
        )

        return GateResult(
            passed=passes,
            gate_name="EV",
            value=ev,
            threshold=0.0,
            details={
                **ev_details,
                "reason": reason
            }
        )

    def check_gate3_execution(
        self,
        metrics: ExecutionMetrics,
        is_newcoin: bool = False
    ) -> GateResult:
        """
        Gate 3: Execution metrics within limits.

        Checks:
        - impact_bps ≤ threshold
        - spread_bps ≤ threshold
        - |OBI| ≤ threshold

        Args:
            metrics: Execution metrics
            is_newcoin: Use newcoin thresholds

        Returns:
            GateResult
        """
        passes, details = self.execution_gates.check_gates(metrics, is_newcoin)

        return GateResult(
            passed=passes,
            gate_name="Execution",
            value={
                "impact_bps": metrics.impact_bps,
                "spread_bps": metrics.spread_bps,
                "OBI": metrics.OBI
            },
            threshold=details["thresholds"],
            details=details
        )

    def check_gate4_probability(
        self,
        probability: float,
        p_min: float,
        delta_p: float,
        delta_p_min: float
    ) -> GateResult:
        """
        Gate 4: Probability threshold.

        Checks:
        - p ≥ p_min
        - ΔP ≥ Δp_min (probability change from previous)

        Args:
            probability: Current probability
            p_min: Minimum probability threshold
            delta_p: Probability change from previous
            delta_p_min: Minimum probability change

        Returns:
            GateResult
        """
        check_p = probability >= p_min
        check_delta = abs(delta_p) >= delta_p_min

        passes = check_p and check_delta

        return GateResult(
            passed=passes,
            gate_name="Probability",
            value={"p": probability, "delta_p": delta_p},
            threshold={"p_min": p_min, "delta_p_min": delta_p_min},
            details={
                "probability": probability,
                "p_min": p_min,
                "delta_p": delta_p,
                "delta_p_min": delta_p_min,
                "check_p": check_p,
                "check_delta": check_delta,
                "reason": "Probability threshold passed" if passes else
                         f"Failed: p={probability:.3f}<{p_min:.3f} or ΔP={delta_p:.3f}<{delta_p_min:.3f}"
            }
        )

    def check_all_gates(
        self,
        symbol: str,
        probability: float,
        execution_metrics: ExecutionMetrics,
        F_raw: float = 0.5,
        I_raw: float = 0.5,
        delta_p: float = 0.0,
        is_newcoin: bool = False
    ) -> Tuple[bool, Dict[str, GateResult]]:
        """
        Check all four gates.

        Args:
            symbol: Trading symbol
            probability: Win probability
            execution_metrics: Execution metrics
            F_raw: F factor value [0, 1]
            I_raw: I factor value [0, 1]
            delta_p: Probability change from previous
            is_newcoin: Use newcoin thresholds

        Returns:
            Tuple of (all_passed, gate_results_dict)
        """
        # Calculate modulated values
        modulation = self.fi_modulator.modulate(F_raw, I_raw, symbol)
        cost_eff = modulation["cost_eff"]
        p_min = modulation["p_min"]
        delta_p_min = modulation["delta_p_min"]

        # Check each gate
        results = {
            "gate1_dataqual": self.check_gate1_dataqual(symbol),
            "gate2_ev": self.check_gate2_ev(symbol, probability, cost_eff),
            "gate3_execution": self.check_gate3_execution(execution_metrics, is_newcoin),
            "gate4_probability": self.check_gate4_probability(probability, p_min, delta_p, delta_p_min)
        }

        # All must pass
        all_passed = all(result.passed for result in results.values())

        return all_passed, results

    def get_summary(self, results: Dict[str, GateResult]) -> Dict[str, Any]:
        """
        Get summary of gate results.

        Args:
            results: Gate results from check_all_gates

        Returns:
            Summary dict
        """
        passed_gates = [name for name, result in results.items() if result.passed]
        failed_gates = [name for name, result in results.items() if not result.passed]

        return {
            "all_passed": len(failed_gates) == 0,
            "passed_count": len(passed_gates),
            "failed_count": len(failed_gates),
            "passed_gates": passed_gates,
            "failed_gates": failed_gates,
            "gate_details": {
                name: {
                    "passed": result.passed,
                    "value": result.value,
                    "threshold": result.threshold
                }
                for name, result in results.items()
            }
        }
