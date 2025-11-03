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
    bad_wick_ratio: float = 0.0  # 异常蜡烛线比例

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

    def check_cache_freshness(
        self,
        symbol: str,
        kline_cache=None,
        max_age_seconds: int = 300
    ) -> Tuple[float, str]:
        """
        检查缓存数据新鲜度（REST模式下使用）

        Args:
            symbol: 交易币种
            kline_cache: K线缓存管理器
            max_age_seconds: 最大过期时间（默认5分钟）

        Returns:
            Tuple of (dataqual_score, reason)
        """
        if kline_cache is None:
            return 1.0, "No cache to check"

        # 检查缓存是否存在
        if not kline_cache.is_initialized(symbol):
            return 0.5, f"Cache not initialized for {symbol}"

        # 检查数据新鲜度
        if symbol not in kline_cache.last_update:
            return 0.7, "No update timestamp"

        age = time.time() - kline_cache.last_update[symbol]

        # 根据数据年龄计算质量分数
        if age <= 30:  # 30秒内
            return 1.0, f"Data fresh ({age:.0f}s)"
        elif age <= 60:  # 1分钟内
            return 0.95, f"Data slightly old ({age:.0f}s)"
        elif age <= 180:  # 3分钟内
            return 0.90, f"Data moderately old ({age:.0f}s)"
        elif age <= max_age_seconds:  # 5分钟内
            return 0.85, f"Data old ({age:.0f}s)"
        else:  # 超过5分钟
            return 0.70, f"Data stale ({age:.0f}s > {max_age_seconds}s)"

    def can_publish_prime(
        self,
        symbol: str,
        kline_cache=None  # 新增：K线缓存，用于REST模式
    ) -> Tuple[bool, float, str]:
        """
        Check if symbol's data quality allows Prime signal publishing.

        Args:
            symbol: Trading symbol
            kline_cache: K线缓存管理器（REST模式下必须提供）

        Returns:
            Tuple of (allowed, dataqual_score, reason)
        """
        # 优先使用WebSocket模式的质量指标
        quality = self.get_quality(symbol)

        # 如果有WebSocket事件记录，使用WebSocket质量
        if symbol in self.metrics and self.metrics[symbol].total_received > 0:
            dataqual = quality.dataqual
            reason_suffix = " (WebSocket mode)"
        else:
            # REST模式：检查缓存新鲜度
            dataqual, cache_reason = self.check_cache_freshness(symbol, kline_cache)
            reason_suffix = f" (REST mode: {cache_reason})"

        if dataqual >= self.ALLOW_PRIME_THRESHOLD:
            return True, dataqual, "Quality sufficient for Prime" + reason_suffix

        if dataqual < self.DEGRADE_THRESHOLD:
            return False, dataqual, f"Quality degraded: {dataqual:.3f} < {self.DEGRADE_THRESHOLD}" + reason_suffix

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


# ==================== Bad Wick Detection ====================

def calculate_bad_wick_ratio(
    candles: list,
    atr: Optional[float] = None,
    wick_threshold_multiplier: float = 2.0
) -> float:
    """
    Calculate the ratio of candles with abnormal wicks.

    A "bad wick" indicates potential data quality issues:
    - Flash crashes
    - Fat finger trades
    - Exchange glitches
    - Low liquidity spikes

    Criteria for bad wick:
    1. Upper wick > wick_threshold_multiplier × body_size, OR
    2. Lower wick > wick_threshold_multiplier × body_size, OR
    3. If ATR provided: upper/lower wick > 3 × ATR

    Args:
        candles: List of candle dicts with keys: 'open', 'high', 'low', 'close'
        atr: Average True Range (optional, for ATR-based detection)
        wick_threshold_multiplier: Multiplier for body-based detection (default 2.0)

    Returns:
        bad_wick_ratio: Ratio of bad wicks in [0, 1]
            - 0.0: No bad wicks (good)
            - 0.1: 10% bad wicks (acceptable)
            - >0.2: High bad wick ratio (poor data quality)

    Example:
        >>> candles = [
        ...     {'open': 100, 'high': 105, 'low': 99, 'close': 102},  # Normal
        ...     {'open': 102, 'high': 120, 'low': 101, 'close': 103}, # Bad upper wick
        ... ]
        >>> calculate_bad_wick_ratio(candles)
        0.5  # 50% bad wicks
    """
    if not candles:
        return 0.0

    bad_count = 0

    for candle in candles:
        o = float(candle.get('open', 0))
        h = float(candle.get('high', 0))
        l = float(candle.get('low', 0))
        c = float(candle.get('close', 0))

        # Skip invalid candles
        if h < l or h == 0 or l == 0:
            continue

        # Body size (absolute)
        body_size = abs(c - o)
        if body_size < 1e-9:
            body_size = 0.01 * c  # Doji: use 1% of price as proxy

        # Wick sizes
        upper_wick = h - max(o, c)
        lower_wick = min(o, c) - l

        is_bad = False

        # Check 1: Body-based detection
        if upper_wick > wick_threshold_multiplier * body_size:
            is_bad = True
        if lower_wick > wick_threshold_multiplier * body_size:
            is_bad = True

        # Check 2: ATR-based detection (if ATR provided)
        if atr is not None and atr > 0:
            atr_threshold = 3.0 * atr
            if upper_wick > atr_threshold or lower_wick > atr_threshold:
                is_bad = True

        if is_bad:
            bad_count += 1

    bad_ratio = bad_count / len(candles) if candles else 0.0

    return bad_ratio


def is_bad_wick_acceptable(bad_wick_ratio: float, threshold: float = 0.15) -> Tuple[bool, str]:
    """
    Check if bad wick ratio is acceptable for trading.

    Args:
        bad_wick_ratio: Bad wick ratio from calculate_bad_wick_ratio()
        threshold: Maximum acceptable ratio (default 0.15 = 15%)

    Returns:
        Tuple of (acceptable, reason)
    """
    if bad_wick_ratio <= threshold:
        return True, f"Bad wick ratio acceptable: {bad_wick_ratio:.1%} ≤ {threshold:.1%}"
    else:
        return False, f"Bad wick ratio too high: {bad_wick_ratio:.1%} > {threshold:.1%} (data quality concern)"
