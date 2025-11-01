"""
C-layer: Execution and liquidity metrics.

Simplified implementation using K-line data proxies.
"""

from .metrics_estimator import ExecutionMetricsEstimator, ExecutionGates

__all__ = ['ExecutionMetricsEstimator', 'ExecutionGates']
