"""
Anti-jitter mechanism for signal publishing.
Implements PUBLISHING.md § 4.3 triple defense.

Author: CryptoSignal v2.0 Compliance Team
Date: 2025-11-01
Updated: 2025-11-06 v6.7 - Unified configuration system
"""

import time
from typing import Optional, Literal, Union
from dataclasses import dataclass

from ats_core.config.anti_jitter_config import AntiJitterConfig

@dataclass
class SignalState:
    """Track signal state for a single symbol."""
    current_level: Literal['PRIME', 'WATCH', 'IGNORE']
    bars_in_state: int  # Consecutive bars at current level
    last_change_ts: float  # Timestamp of last state change
    last_publish_ts: Optional[float] = None

class AntiJitter:
    """
    Anti-jitter controller with triple defense:
    1. Hysteresis: Different thresholds for entry/exit
    2. Persistence: K/N bars confirmation
    3. Cooldown: Minimum time between state changes

    v6.7 Update: Now supports unified configuration via AntiJitterConfig.
    """

    def __init__(
        self,
        config: Optional[AntiJitterConfig] = None,
        # Legacy parameters (for backward compatibility)
        prime_entry_threshold: Optional[float] = None,
        prime_maintain_threshold: Optional[float] = None,
        watch_entry_threshold: Optional[float] = None,
        watch_maintain_threshold: Optional[float] = None,
        confirmation_bars: Optional[int] = None,
        total_bars: Optional[int] = None,
        cooldown_seconds: Optional[int] = None
    ):
        """
        Initialize anti-jitter controller.

        Args:
            config: AntiJitterConfig instance (recommended, v6.7+)

            Legacy parameters (for backward compatibility):
            prime_entry_threshold: Probability to enter PRIME
            prime_maintain_threshold: Probability to stay in PRIME
            watch_entry_threshold: Probability to enter WATCH
            watch_maintain_threshold: Probability to stay in WATCH
            confirmation_bars: K bars required
            total_bars: N total bars window
            cooldown_seconds: Minimum seconds between changes

        Examples:
            # New way (recommended):
            >>> from ats_core.config.anti_jitter_config import get_config
            >>> aj = AntiJitter(config=get_config("15m"))

            # Old way (still works):
            >>> aj = AntiJitter(confirmation_bars=2, total_bars=3, cooldown_seconds=90)
        """
        # Use config if provided, otherwise create from legacy parameters
        if config is not None:
            self.config = config
        else:
            # Create config from legacy parameters (backward compatibility)
            from ats_core.config.anti_jitter_config import get_config_default
            default = get_config_default()

            self.config = AntiJitterConfig(
                kline_period=default.kline_period,
                scan_interval_seconds=default.scan_interval_seconds,
                confirmation_bars=confirmation_bars if confirmation_bars is not None else default.confirmation_bars,
                total_bars=total_bars if total_bars is not None else default.total_bars,
                cooldown_bars=default.cooldown_bars,
                prime_entry_threshold=prime_entry_threshold if prime_entry_threshold is not None else default.prime_entry_threshold,
                prime_maintain_threshold=prime_maintain_threshold if prime_maintain_threshold is not None else default.prime_maintain_threshold,
                watch_entry_threshold=watch_entry_threshold if watch_entry_threshold is not None else default.watch_entry_threshold,
                watch_maintain_threshold=watch_maintain_threshold if watch_maintain_threshold is not None else default.watch_maintain_threshold
            )

            # Override cooldown_seconds if provided (legacy)
            if cooldown_seconds is not None:
                self.config.cooldown_seconds = cooldown_seconds

        # Extract parameters from config
        self.prime_entry = self.config.prime_entry_threshold
        self.prime_maintain = self.config.prime_maintain_threshold
        self.watch_entry = self.config.watch_entry_threshold
        self.watch_maintain = self.config.watch_maintain_threshold
        self.K = self.config.confirmation_bars
        self.N = self.config.total_bars
        self.cooldown = self.config.cooldown_seconds

        # Per-symbol state tracking
        self.states = {}  # symbol -> SignalState
        self.history = {}  # symbol -> list of last N probabilities

    def update(
        self,
        symbol: str,
        probability: float,
        ev: float,
        gates_passed: bool
    ) -> tuple[Literal['PRIME', 'WATCH', 'IGNORE'], bool]:
        """
        Update signal state with anti-jitter logic.

        Args:
            symbol: Trading symbol
            probability: Current win probability (0-1)
            ev: Expected value (must be > 0 for PRIME)
            gates_passed: Whether execution gates passed

        Returns:
            (new_level, should_publish):
                - new_level: Recommended signal level
                - should_publish: True if state changed AND cooldown passed
        """
        now = time.time()

        # Initialize state if new symbol
        if symbol not in self.states:
            # v6.6修复：新symbol的last_change_ts设置为远古时间，避免cooldown阻止首次发布
            # 原因：如果设置为now，则首次检查时time_since_change=0 < cooldown，导致信号被拒绝
            self.states[symbol] = SignalState(
                current_level='IGNORE',
                bars_in_state=0,
                last_change_ts=now - self.cooldown - 1  # 确保cooldown已过期
            )
            self.history[symbol] = []

        state = self.states[symbol]
        history = self.history[symbol]

        # Add to history (keep last N bars)
        history.append(probability)
        if len(history) > self.N:
            history.pop(0)

        # Check persistence: K/N bars confirmation
        if len(history) < self.K:
            # Not enough history, maintain current state
            return state.current_level, False

        # Determine target level based on hysteresis
        if state.current_level == 'PRIME':
            # Already PRIME: use maintain threshold (lower)
            if probability >= self.prime_maintain and ev > 0 and gates_passed:
                target = 'PRIME'
            elif probability >= self.watch_maintain:
                target = 'WATCH'
            else:
                target = 'IGNORE'
        elif state.current_level == 'WATCH':
            # Already WATCH: check for upgrade or downgrade
            if probability >= self.prime_entry and ev > 0 and gates_passed:
                target = 'PRIME'
            elif probability >= self.watch_maintain:
                target = 'WATCH'
            else:
                target = 'IGNORE'
        else:  # IGNORE
            # Need to cross entry threshold
            if probability >= self.prime_entry and ev > 0 and gates_passed:
                target = 'PRIME'
            elif probability >= self.watch_entry:
                target = 'WATCH'
            else:
                target = 'IGNORE'

        # Check K/N persistence
        bars_at_target = sum(
            1 for p in history[-self.N:]
            if self._meets_threshold(p, target, ev, gates_passed)
        )

        confirmed = bars_at_target >= self.K

        if not confirmed:
            # Not enough bars confirmation, maintain current state
            state.bars_in_state += 1
            return state.current_level, False

        # Check cooldown
        time_since_change = now - state.last_change_ts
        if time_since_change < self.cooldown and target != state.current_level:
            # Still in cooldown, maintain current state
            state.bars_in_state += 1
            return state.current_level, False

        # State change logic
        if target != state.current_level:
            # State changed AND cooldown passed
            state.current_level = target
            state.bars_in_state = 1
            state.last_change_ts = now
            state.last_publish_ts = now
            return target, True
        else:
            # No change
            state.bars_in_state += 1
            return target, False

    def _meets_threshold(self, prob: float, level: str, ev: float, gates: bool) -> bool:
        """Check if probability meets threshold for given level."""
        if level == 'PRIME':
            return prob >= self.prime_maintain and ev > 0 and gates
        elif level == 'WATCH':
            return prob >= self.watch_maintain
        else:
            return prob < self.watch_maintain

    def get_state(self, symbol: str) -> Optional[SignalState]:
        """Get current state for a symbol."""
        return self.states.get(symbol)

    def reset(self, symbol: str = None):
        """
        Reset state for a symbol (or all symbols if symbol=None).

        Args:
            symbol: Symbol to reset, or None to reset all
        """
        if symbol is None:
            self.states.clear()
            self.history.clear()
        else:
            self.states.pop(symbol, None)
            self.history.pop(symbol, None)
