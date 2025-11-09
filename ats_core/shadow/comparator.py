"""
Shadow comparator for metrics comparison between old and new implementations.

Compares outputs from production code vs. new standard implementations.
"""

from typing import Dict, List, Any, Optional, Tuple
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

# UTC+8时区（北京时间）
TZ_UTC8 = timezone(timedelta(hours=8))


@dataclass
class ComparisonResult:
    """Result of comparing old vs new implementation."""

    symbol: str
    timestamp: datetime
    metric_name: str

    # Values
    old_value: Optional[float]
    new_value: Optional[float]

    # Comparison metrics
    absolute_diff: Optional[float]
    relative_diff: Optional[float]  # (new - old) / old

    # Categorization
    within_threshold: bool
    threshold_used: float

    # Context
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'metric': self.metric_name,
            'old': self.old_value,
            'new': self.new_value,
            'abs_diff': self.absolute_diff,
            'rel_diff': self.relative_diff,
            'ok': self.within_threshold,
            'threshold': self.threshold_used,
            **self.metadata
        }


class ShadowComparator:
    """Compares outputs between old and new implementations."""

    # Default thresholds for different metric types
    DEFAULT_THRESHOLDS = {
        'score': 5.0,           # ±5 points for scores on [-100, 100]
        'probability': 0.05,    # ±0.05 for probabilities [0, 1]
        'dataqual': 0.02,       # ±0.02 for DataQual [0, 1]
        'weight': 0.01,         # ±0.01 for weights
        'temperature': 0.1,     # ±0.1 for temperature
        'cost': 0.005,          # ±0.005 for cost adjustments
    }

    def __init__(self, thresholds: Optional[Dict[str, float]] = None):
        """
        Initialize comparator.

        Args:
            thresholds: Custom thresholds by metric type. Overrides defaults.
        """
        self.thresholds = {**self.DEFAULT_THRESHOLDS}
        if thresholds:
            self.thresholds.update(thresholds)

        self.results: List[ComparisonResult] = []

    def compare(
        self,
        symbol: str,
        metric_name: str,
        old_value: Optional[float],
        new_value: Optional[float],
        metric_type: str = 'score',
        metadata: Optional[Dict[str, Any]] = None
    ) -> ComparisonResult:
        """
        Compare old vs new value for a metric.

        Args:
            symbol: Trading symbol
            metric_name: Name of metric being compared
            old_value: Value from old implementation
            new_value: Value from new implementation
            metric_type: Type of metric (determines threshold)
            metadata: Additional context

        Returns:
            ComparisonResult with comparison details
        """
        threshold = self.thresholds.get(metric_type, 1.0)

        # Calculate differences
        if old_value is None or new_value is None:
            abs_diff = None
            rel_diff = None
            within_threshold = False
        else:
            abs_diff = abs(new_value - old_value)

            # Relative difference (handle division by zero)
            if abs(old_value) < 1e-9:
                rel_diff = None if abs_diff < 1e-9 else float('inf')
            else:
                rel_diff = (new_value - old_value) / old_value

            within_threshold = abs_diff <= threshold

        result = ComparisonResult(
            symbol=symbol,
            timestamp=datetime.now(TZ_UTC8),
            metric_name=metric_name,
            old_value=old_value,
            new_value=new_value,
            absolute_diff=abs_diff,
            relative_diff=rel_diff,
            within_threshold=within_threshold,
            threshold_used=threshold,
            metadata=metadata or {}
        )

        self.results.append(result)
        return result

    def compare_dict(
        self,
        symbol: str,
        old_dict: Dict[str, float],
        new_dict: Dict[str, float],
        metric_type: str = 'score',
        prefix: str = ''
    ) -> List[ComparisonResult]:
        """
        Compare all matching keys in two dictionaries.

        Args:
            symbol: Trading symbol
            old_dict: Dictionary of old values
            new_dict: Dictionary of new values
            metric_type: Type of metrics
            prefix: Prefix for metric names

        Returns:
            List of comparison results
        """
        results = []
        all_keys = set(old_dict.keys()) | set(new_dict.keys())

        for key in all_keys:
            metric_name = f"{prefix}{key}" if prefix else key
            old_val = old_dict.get(key)
            new_val = new_dict.get(key)

            result = self.compare(
                symbol=symbol,
                metric_name=metric_name,
                old_value=old_val,
                new_value=new_val,
                metric_type=metric_type
            )
            results.append(result)

        return results

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics of all comparisons.

        Returns:
            Dictionary with summary metrics
        """
        if not self.results:
            return {'total': 0}

        total = len(self.results)
        passed = sum(1 for r in self.results if r.within_threshold)
        failed = total - passed

        # Calculate statistics on differences
        abs_diffs = [r.absolute_diff for r in self.results if r.absolute_diff is not None]

        # Calculate p95 manually
        p95 = None
        if abs_diffs:
            sorted_diffs = sorted(abs_diffs)
            p95_idx = int(len(sorted_diffs) * 0.95)
            p95 = sorted_diffs[min(p95_idx, len(sorted_diffs) - 1)]

        return {
            'total': total,
            'passed': passed,
            'failed': failed,
            'pass_rate': passed / total if total > 0 else 0.0,
            'abs_diff_mean': statistics.mean(abs_diffs) if abs_diffs else None,
            'abs_diff_median': statistics.median(abs_diffs) if abs_diffs else None,
            'abs_diff_p95': p95,
        }

    def clear(self):
        """Clear all stored results."""
        self.results.clear()
