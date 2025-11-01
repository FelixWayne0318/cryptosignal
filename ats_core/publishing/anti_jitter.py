"""
Anti-jitter mechanism for signal publishing.
Implements PUBLISHING.md § 4.3 triple defense.

Author: CryptoSignal v2.0 Compliance Team
Date: 2025-11-01
"""

import time
from typing import Optional, Literal
from dataclasses import dataclass

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
    """

    def __init__(
        self,
        prime_entry_threshold: float = 0.80,
        prime_maintain_threshold: float = 0.70,
        watch_entry_threshold: float = 0.50,
        watch_maintain_threshold: float = 0.40,
        confirmation_bars: int = 2,
        total_bars: int = 3,
        cooldown_seconds: int = 90
    ):
        """
        Initialize anti-jitter controller with PUBLISHING.md parameters.

        Args:
            prime_entry_threshold: Probability to enter PRIME (0.80)
            prime_maintain_threshold: Probability to stay in PRIME (0.70)
            watch_entry_threshold: Probability to enter WATCH (0.50)
            watch_maintain_threshold: Probability to stay in WATCH (0.40)
            confirmation_bars: K bars required (2)
            total_bars: N total bars window (3)
            cooldown_seconds: Minimum seconds between changes (90)
        """
        self.prime_entry = prime_entry_threshold
        self.prime_maintain = prime_maintain_threshold
        self.watch_entry = watch_entry_threshold
        self.watch_maintain = watch_maintain_threshold
        self.K = confirmation_bars
        self.N = total_bars
        self.cooldown = cooldown_seconds

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
            self.states[symbol] = SignalState(
                current_level='IGNORE',
                bars_in_state=0,
                last_change_ts=now
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
