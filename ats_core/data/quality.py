"""
Data quality monitoring (DataQual) implementation.

Implements DataQual scoring as specified in DATA_LAYER.md:
DataQual = 1 - (w_h·miss + w_o·ooOrder + w_d·drift + w_m·mismatch)

Quality gates:
- DataQual ≥ 0.90: Allow Prime signals
- DataQual < 0.88: Degrade to Watch-only
"""

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta


@dataclass
class QualityMetrics:
    """Quality metrics for a symbol/stream."""

    # Rolling window counters
    total_expected: int = 0
    total_received: int = 0
    out_of_order: int = 0
    drift_violations: int = 0
    mismatch_events: int = 0

    # Derived rates
    miss_rate: float = 0.0
    oo_order_rate: float = 0.0
    drift_rate: float = 0.0
    mismatch_rate: float = 0.0

    # Final score
    dataqual: float = 1.0

    # Timestamps
    last_update: Optional[datetime] = None
    window_start: Optional[datetime] = None


class DataQualMonitor:
    """
    Monitor data quality for WebSocket streams.

    Tracks miss rate, out-of-order events, timestamp drift, and order book mismatches.
    """

    # Default weights from DATA_LAYER.md
    DEFAULT_WEIGHTS = {
        'miss': 0.35,
        'oo_order': 0.15,
        'drift': 0.20,
        'mismatch': 0.30
    }

    # Default thresholds
    ALLOW_PRIME_THRESHOLD = 0.90
    DEGRADE_THRESHOLD = 0.88
    DRIFT_THRESHOLD_MS = 300  # 300ms drift threshold

    def __init__(
        self,
        window_seconds: int = 300,  # 5-minute rolling window
        weights: Optional[Dict[str, float]] = None,
        drift_threshold_ms: int = 300
    ):
        """
        Initialize DataQual monitor.

        Args:
            window_seconds: Rolling window size in seconds
            weights: Custom weights for quality components
            drift_threshold_ms: Timestamp drift threshold in milliseconds
        """
        self.window_seconds = window_seconds
        self.weights = weights or self.DEFAULT_WEIGHTS
        self.drift_threshold_ms = drift_threshold_ms

        # Per-symbol quality metrics
        self.metrics: Dict[str, QualityMetrics] = {}

        # Rolling event windows for rate calculation
        self.event_windows: Dict[str, deque] = {}

    def _get_or_create_metrics(self, symbol: str) -> QualityMetrics:
        """Get or create metrics for a symbol."""
        if symbol not in self.metrics:
            self.metrics[symbol] = QualityMetrics(
                window_start=datetime.now()
            )
            self.event_windows[symbol] = deque(maxlen=10000)  # Keep last 10k events

        return self.metrics[symbol]

    def record_event(
        self,
        symbol: str,
        ts_exch: int,  # Exchange timestamp (ms)
        ts_srv: int,  # Server receipt timestamp (ms)
        is_ordered: bool = True
    ) -> None:
        """
        Record a received event for quality tracking.

        Args:
            symbol: Trading symbol
            ts_exch: Exchange event timestamp (milliseconds)
            ts_srv: Server receipt timestamp (milliseconds)
            is_ordered: Whether event is in correct order
        """
        metrics = self._get_or_create_metrics(symbol)
        now = datetime.now()

        # Record event
        self.event_windows[symbol].append({
            'ts': now,
            'ts_exch': ts_exch,
            'ts_srv': ts_srv,
            'ordered': is_ordered
        })

        metrics.total_received += 1

        # Check for out-of-order
        if not is_ordered:
            metrics.out_of_order += 1

        # Check for drift
        drift_ms = abs(ts_exch - ts_srv)
        if drift_ms > self.drift_threshold_ms:
            metrics.drift_violations += 1

        metrics.last_update = now

        # Update rates periodically
        self._update_rates(symbol)

    def record_miss(self, symbol: str, expected_count: int = 1) -> None:
        """
        Record missed/expected events (heartbeat failures, etc.).

        Args:
            symbol: Trading symbol
            expected_count: Number of expected events that were missed
        """
        metrics = self._get_or_create_metrics(symbol)
        metrics.total_expected += expected_count
        metrics.last_update = datetime.now()

        self._update_rates(symbol)

    def record_mismatch(self, symbol: str) -> None:
        """
        Record order book mismatch event.

        Args:
            symbol: Trading symbol
        """
        metrics = self._get_or_create_metrics(symbol)
        metrics.mismatch_events += 1
        metrics.last_update = datetime.now()

        self._update_rates(symbol)

    def _update_rates(self, symbol: str) -> None:
        """Update quality rates and DataQual score for a symbol."""
        metrics = self.metrics[symbol]
        events = self.event_windows[symbol]

        if not events:
            return

        # Clean old events outside window
        cutoff = datetime.now() - timedelta(seconds=self.window_seconds)
        while events and events[0]['ts'] < cutoff:
            events.popleft()

        if not events:
            return

        # Calculate rates based on window
        window_received = len(events)
        window_expected = max(window_received, metrics.total_expected)

        # Miss rate
        missed = window_expected - window_received
        metrics.miss_rate = missed / window_expected if window_expected > 0 else 0.0

        # Out-of-order rate
        oo_count = sum(1 for e in events if not e['ordered'])
        metrics.oo_order_rate = oo_count / window_received if window_received > 0 else 0.0

        # Drift rate
        drift_count = sum(
            1 for e in events
            if abs(e['ts_exch'] - e['ts_srv']) > self.drift_threshold_ms
        )
        metrics.drift_rate = drift_count / window_received if window_received > 0 else 0.0

        # Mismatch rate (mismatches per event)
        metrics.mismatch_rate = metrics.mismatch_events / window_received if window_received > 0 else 0.0

        # Calculate DataQual
        metrics.dataqual = 1.0 - (
            self.weights['miss'] * metrics.miss_rate +
            self.weights['oo_order'] * metrics.oo_order_rate +
            self.weights['drift'] * metrics.drift_rate +
            self.weights['mismatch'] * metrics.mismatch_rate
        )

        # Clamp to [0, 1]
        metrics.dataqual = max(0.0, min(1.0, metrics.dataqual))

    def get_quality(self, symbol: str) -> QualityMetrics:
        """
        Get current quality metrics for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Current quality metrics
        """
        if symbol not in self.metrics:
            return QualityMetrics(dataqual=1.0)  # Default perfect quality

        return self.metrics[symbol]

    def can_publish_prime(self, symbol: str) -> Tuple[bool, float, str]:
        """
        Check if symbol's data quality allows Prime signal publishing.

        Args:
            symbol: Trading symbol

        Returns:
            Tuple of (allowed, dataqual_score, reason)
        """
        quality = self.get_quality(symbol)

        if quality.dataqual >= self.ALLOW_PRIME_THRESHOLD:
            return True, quality.dataqual, "Quality sufficient for Prime"

        if quality.dataqual < self.DEGRADE_THRESHOLD:
            return False, quality.dataqual, f"Quality degraded: {quality.dataqual:.3f} < {self.DEGRADE_THRESHOLD}"

        return False, quality.dataqual, f"Quality below Prime threshold: {quality.dataqual:.3f} < {self.ALLOW_PRIME_THRESHOLD}"

    def get_all_qualities(self) -> Dict[str, float]:
        """
        Get DataQual scores for all tracked symbols.

        Returns:
            Dict mapping symbol to DataQual score
        """
        return {
            symbol: metrics.dataqual
            for symbol, metrics in self.metrics.items()
        }

    def reset_symbol(self, symbol: str) -> None:
        """Reset quality tracking for a symbol."""
        if symbol in self.metrics:
            del self.metrics[symbol]
        if symbol in self.event_windows:
            del self.event_windows[symbol]
