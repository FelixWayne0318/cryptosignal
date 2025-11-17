"""
Unified Anti-Jitter Configuration.

Centralizes anti-jitter parameters to ensure consistency across:
- K-line periods (15m, 1h, etc.)
- Scanning intervals
- Cooldown periods
- K/N confirmation windows

Author: CryptoSignal v6.7 Compliance Team
Date: 2025-11-06
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class AntiJitterConfig:
    """
    Unified anti-jitter configuration.

    Ensures consistency between K-line period, scan interval, and cooldown.
    """

    # === Core Parameters ===
    kline_period: str = "15m"  # Primary K-line period: 1m, 5m, 15m, 1h, etc.
    scan_interval_seconds: int = 60  # How often to scan (seconds)

    # === K/N Confirmation ===
    confirmation_bars: int = 2  # K: number of bars that must confirm
    total_bars: int = 3  # N: total bars in confirmation window

    # === Cooldown (in K-line bars, not seconds) ===
    cooldown_bars: int = 1  # Cooldown in number of K-line bars

    # === Hysteresis Thresholds ===
    prime_entry_threshold: float = 0.45
    prime_maintain_threshold: float = 0.42
    watch_entry_threshold: float = 0.40
    watch_maintain_threshold: float = 0.37

    def __post_init__(self):
        """Validate configuration and compute derived values."""
        # Validate K/N relationship
        if self.confirmation_bars > self.total_bars:
            raise ValueError(
                f"confirmation_bars ({self.confirmation_bars}) cannot exceed "
                f"total_bars ({self.total_bars})"
            )

        if self.confirmation_bars < 1:
            raise ValueError("confirmation_bars must be >= 1")

        if self.total_bars < 1:
            raise ValueError("total_bars must be >= 1")

        # Validate cooldown
        if self.cooldown_bars < 0:
            raise ValueError("cooldown_bars must be >= 0")

        # Compute derived values
        self._kline_seconds = self._parse_kline_period(self.kline_period)
        self.cooldown_seconds = self.cooldown_bars * self._kline_seconds

        # Compute confirmation window duration
        self.confirmation_window_seconds = self.total_bars * self._kline_seconds

    @staticmethod
    def _parse_kline_period(period: str) -> int:
        """
        Parse K-line period string to seconds.

        Args:
            period: K-line period like "1m", "5m", "15m", "1h", "4h", "1d"

        Returns:
            Duration in seconds

        Raises:
            ValueError: If period format is invalid
        """
        period = period.lower().strip()

        if period.endswith('m'):
            minutes = int(period[:-1])
            return minutes * 60
        elif period.endswith('h'):
            hours = int(period[:-1])
            return hours * 3600
        elif period.endswith('d'):
            days = int(period[:-1])
            return days * 86400
        elif period.endswith('w'):
            weeks = int(period[:-1])
            return weeks * 604800
        else:
            raise ValueError(
                f"Invalid K-line period: {period}. "
                f"Expected format: <number><unit> (e.g., 1m, 5m, 15m, 1h, 4h, 1d)"
            )

    @property
    def kline_seconds(self) -> int:
        """K-line period in seconds."""
        return self._kline_seconds

    def get_recommended_scan_interval(self) -> int:
        """
        Get recommended scan interval based on K-line period.

        Returns:
            Recommended scan interval in seconds

        Logic:
        - For periods < 5m: scan every 60s
        - For 5m: scan every 60s (sub-period monitoring)
        - For 15m: scan every 60s (4x per bar for early detection)
        - For 1h+: scan every 5 minutes (multiple checks per bar)
        """
        if self._kline_seconds < 300:  # < 5 minutes
            return 60
        elif self._kline_seconds <= 900:  # <= 15 minutes
            return 60  # Scan 4x per bar for 5m, 15x per bar for 15m
        elif self._kline_seconds <= 3600:  # <= 1 hour
            return 300  # Scan every 5 minutes (12x per hour bar)
        else:  # > 1 hour
            return 300  # Scan every 5 minutes

    def validate_consistency(self) -> tuple[bool, list[str]]:
        """
        Validate configuration consistency.

        Returns:
            Tuple of (is_valid, warnings)
        """
        warnings = []

        # Check if scan interval is appropriate for K-line period
        recommended = self.get_recommended_scan_interval()
        if self.scan_interval_seconds > self._kline_seconds:
            warnings.append(
                f"⚠️ Scan interval ({self.scan_interval_seconds}s) exceeds K-line period "
                f"({self._kline_seconds}s). Signals will be delayed."
            )
        elif self.scan_interval_seconds < recommended / 2:
            warnings.append(
                f"⚠️ Scan interval ({self.scan_interval_seconds}s) is very short. "
                f"Recommended: {recommended}s for {self.kline_period} K-lines."
            )

        # Check if cooldown is appropriate
        if self.cooldown_seconds < self._kline_seconds:
            warnings.append(
                f"ℹ️ Cooldown ({self.cooldown_seconds}s) < K-line period ({self._kline_seconds}s). "
                f"This allows rapid state changes within a single bar."
            )

        # Check if confirmation window is reasonable
        if self.confirmation_window_seconds < 300:
            warnings.append(
                f"ℹ️ Confirmation window ({self.confirmation_window_seconds}s = {self.total_bars} bars) "
                f"is very short. Signals may be unstable."
            )

        return len(warnings) == 0, warnings

    def __str__(self) -> str:
        """Human-readable summary."""
        return (
            f"AntiJitterConfig(\n"
            f"  K-line: {self.kline_period} ({self._kline_seconds}s)\n"
            f"  Scan: every {self.scan_interval_seconds}s\n"
            f"  K/N: {self.confirmation_bars}/{self.total_bars} "
            f"(window: {self.confirmation_window_seconds}s = {self.confirmation_window_seconds//60:.0f}min)\n"
            f"  Cooldown: {self.cooldown_bars} bars = {self.cooldown_seconds}s\n"
            f"  Thresholds: PRIME {self.prime_entry_threshold}/{self.prime_maintain_threshold}, "
            f"WATCH {self.watch_entry_threshold}/{self.watch_maintain_threshold}\n"
            f")"
        )


# === Preset Configurations ===

def get_config_15m_standard() -> AntiJitterConfig:
    """
    Standard configuration for 15-minute K-lines.

    - K-line: 15m
    - Scan: every 60s (4x per bar)
    - K/N: 2/3 (need 2 out of 3 bars = 30-45min window)
    - Cooldown: 1 bar = 15 minutes
    """
    return AntiJitterConfig(
        kline_period="15m",
        scan_interval_seconds=60,
        confirmation_bars=2,
        total_bars=3,
        cooldown_bars=1,
        prime_entry_threshold=0.45,
        prime_maintain_threshold=0.42,
        watch_entry_threshold=0.40,
        watch_maintain_threshold=0.37
    )


def get_config_1h_standard() -> AntiJitterConfig:
    """
    Standard configuration for 1-hour K-lines.

    - K-line: 1h
    - Scan: every 5 minutes (12x per bar)
    - K/N: 2/3 (need 2 out of 3 bars = 2-3 hour window)
    - Cooldown: 1 bar = 1 hour
    """
    return AntiJitterConfig(
        kline_period="1h",
        scan_interval_seconds=300,
        confirmation_bars=2,
        total_bars=3,
        cooldown_bars=1,
        prime_entry_threshold=0.50,
        prime_maintain_threshold=0.47,
        watch_entry_threshold=0.43,
        watch_maintain_threshold=0.40
    )


def get_config_5m_aggressive() -> AntiJitterConfig:
    """
    Aggressive configuration for 5-minute K-lines (faster signals).

    - K-line: 5m
    - Scan: every 60s (1.2x per bar)
    - K/N: 1/2 (need 1 out of 2 bars = 5-10min window)
    - Cooldown: 1 bar = 5 minutes
    """
    return AntiJitterConfig(
        kline_period="5m",
        scan_interval_seconds=60,
        confirmation_bars=1,
        total_bars=2,
        cooldown_bars=1,
        prime_entry_threshold=0.45,
        prime_maintain_threshold=0.42,
        watch_entry_threshold=0.40,
        watch_maintain_threshold=0.37
    )


def get_config_2h_diversified() -> AntiJitterConfig:
    """
    2小时多样化配置 - 强制币种轮换，降低集中风险（v7.4.0推荐）

    设计理念：
    - 每个币种发出信号后2小时内不再发送
    - 配合Top 1竞争机制，强制多币种轮换
    - 降低单一币种集中风险，提高投资组合多样化
    - 减少同一币种频繁出现导致的信息疲劳

    配置参数：
    - K-line: 15m（标准周期）
    - Scan: every 60s（频繁扫描，快速响应）
    - K/N: 2/3（需要2/3个bar确认，确保信号稳定）
    - Cooldown: 8 bars = 120分钟 = 2小时（关键差异）

    适用场景：
    - 多币种轮换策略
    - Top 1信号发送机制
    - 强调投资组合分散
    - 控制单币种暴露风险

    Returns:
        AntiJitterConfig实例，冷却期=2小时
    """
    return AntiJitterConfig(
        kline_period="15m",
        scan_interval_seconds=60,
        confirmation_bars=2,
        total_bars=3,
        cooldown_bars=8,  # 8 bars × 15min = 120min = 2小时
        prime_entry_threshold=0.45,
        prime_maintain_threshold=0.42,
        watch_entry_threshold=0.40,
        watch_maintain_threshold=0.37
    )


def get_config_default() -> AntiJitterConfig:
    """
    Default configuration (15m standard).

    This is the recommended configuration for production.
    """
    return get_config_15m_standard()


# === Configuration Selection ===

def get_config(preset: Literal["15m", "1h", "5m", "2h", "default"] = "default") -> AntiJitterConfig:
    """
    Get anti-jitter configuration by preset name.

    Args:
        preset: Configuration preset ("15m", "1h", "5m", "2h", "default")
            - "15m": 标准15分钟配置（cooldown=15min）
            - "1h": 保守1小时配置（cooldown=1h）
            - "5m": 激进5分钟配置（cooldown=5min）
            - "2h": 多样化2小时配置（cooldown=2h，v7.4.0推荐）
            - "default": 默认配置（15m）

    Returns:
        AntiJitterConfig instance

    Raises:
        ValueError: If preset name is invalid
    """
    presets = {
        "default": get_config_default,
        "15m": get_config_15m_standard,
        "1h": get_config_1h_standard,
        "5m": get_config_5m_aggressive,
        "2h": get_config_2h_diversified
    }

    if preset not in presets:
        raise ValueError(
            f"Invalid preset: {preset}. "
            f"Available: {', '.join(presets.keys())}"
        )

    return presets[preset]()
