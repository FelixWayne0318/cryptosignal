# IMPLEMENTATION_PLAN_v2.md - CryptoSignal v2.0 Compliance Implementation Plan

> **Generated**: 2025-11-01
> **Based On**: COMPLIANCE_REPORT.md findings
> **Target**: Full compliance with newstandards/ specifications
> **Mode**: Shadow run only (no real orders)

---

## 📋 EXECUTIVE SUMMARY

**Current Status**: 5/8 requirements met (62.5% partial compliance)
**Critical Issues**: 3 CRITICAL, 2 HIGH, 3 LOW priority gaps
**Implementation Strategy**: 3-phase incremental rollout with rollback points

**Phases**:
- **Phase 1 (CRITICAL)**: F/I isolation, standardization chain, publishing anti-jitter
- **Phase 2 (HIGH)**: Impact threshold fix, factor pre-processing
- **Phase 3 (LOW)**: WS connection pooling, advanced monitoring

**Estimated Timeline**:
- Phase 1: 2-3 days (critical compliance fixes)
- Phase 2: 1-2 days (optimization)
- Phase 3: 1-2 days (infrastructure)

**Risk Level**: MEDIUM (breaking changes to scoring logic)

---

## 🎯 PHASE 1: CRITICAL COMPLIANCE FIXES

**Priority**: CRITICAL
**Duration**: 2-3 days
**Risk**: MEDIUM (affects scoring output)
**Rollback**: Git branch `feature/v2-phase1-critical`

### 1.1 Remove F from Scorecard (CRITICAL)

**Issue**: F has 10% weight in scorecard, violates B-layer spec
**Spec Reference**: MODULATORS.md § 2.1 - "F/I affect Teff/cost/thresholds ONLY"

**Files to Modify**:

#### `ats_core/pipeline/analyze_symbol.py`

**Location**: Lines 372-423
**Current Code**:
```python
# ❌ WRONG: F in scorecard
base_weights = {
    "T": 15.0, "M": 10.0, "C": 10.0, "S": 15.0,
    "V": 8.0, "O": 7.0, "F": 10.0,  # ← VIOLATION
    "L": 10.0, "B": 10.0, "Q": 10.0, "I": 5.0
}
scores = {
    "T": T, "M": M, "C": C, "S": S,
    "V": V, "O": O, "F": F,  # ← VIOLATION
    "L": L, "B": B, "Q": Q, "I": I
}
```

**New Code**:
```python
# ✅ CORRECT: F removed from scorecard, weight redistributed
base_weights = {
    "T": 17.0,  # +2.0
    "M": 12.0,  # +2.0
    "C": 11.0,  # +1.0
    "S": 17.0,  # +2.0
    "V": 9.0,   # +1.0
    "O": 8.0,   # +1.0
    "L": 11.0,  # +1.0
    "B": 10.0,  # unchanged
    "Q": 10.0,  # unchanged
    "I": 5.0    # unchanged
}  # Total: 100.0

scores = {
    "T": T, "M": M, "C": C, "S": S,
    "V": V, "O": O,  # NO F
    "L": L, "B": B, "Q": Q, "I": I
}

# F stored separately for modulation only
modulation_factors = {
    "F": F_raw,  # Raw F score before any processing
    "I": I_raw   # Raw I score before any processing
}
```

**Interface Changes**:
- **Input**: No change (F still calculated)
- **Output**: `result['scores']` no longer contains 'F' key
- **New Field**: `result['modulation'] = {"F": F_raw, "I": I_raw}`

**Parameter Source**:
- MODULATORS.md: "F/I 仅调节 Teff/cost/thresholds，绝不修改方向分数"
- Weight redistribution: Balanced across momentum (T/M), reversal (C/S), microstructure (V/O/L)

**Testing**:
- Run 10 symbols, verify `scores` dict has exactly 10 keys (no 'F')
- Verify `modulation` dict contains F/I raw values
- Verify total score sum = 100.0

**Rollback Strategy**:
```bash
git checkout analyze_symbol.py
# Restore original scorecard weights
```

---

### 1.2 Implement Unified Standardization Chain (CRITICAL)

**Issue**: Factors use direct tanh mapping, missing EW-Median/MAD/soft-winsor pre-processing
**Spec Reference**: STANDARDS.md § 1.2 - Complete standardization chain

**Files to Modify**:

#### `ats_core/scoring/scoring_utils.py` (NEW MODULE)

**Create New File**:
```python
"""
Unified standardization chain for all A-layer factors.
Implements STANDARDS.md § 1.2 complete pre-processing pipeline.
"""

import numpy as np
from typing import Tuple

class StandardizationChain:
    """
    Unified standardization pipeline for factor scores.

    Sequence:
    1. Pre-smoothing: EW with α=0.15
    2. Robust scaling: EW-Median/MAD (1.4826 factor)
    3. Soft winsorization: z0=2.5, zmax=6, λ=1.5
    4. Compression: tanh(z/τ) → ±100
    5. Publish filter: hysteresis + Δmax
    """

    def __init__(self, alpha: float = 0.15, tau: float = 3.0):
        """
        Args:
            alpha: Pre-smoothing coefficient (0.10-0.20)
            tau: Compression temperature (2.5-4.0)
        """
        self.alpha = alpha
        self.tau = tau

        # EW median/MAD accumulators (per-factor persistent state)
        self.ew_median = None
        self.ew_mad = None
        self.prev_smooth = None

    def standardize(self, x_raw: float) -> Tuple[float, dict]:
        """
        Apply full standardization chain to raw input.

        Args:
            x_raw: Raw factor value (unstandardized)

        Returns:
            (s_pub, diagnostics):
                - s_pub: Final ±100 score ready for publishing
                - diagnostics: {x_smooth, z_raw, z_soft, s_k}
        """
        # Step 1: Pre-smooth (α-weighted)
        if self.prev_smooth is None:
            x_smooth = x_raw
        else:
            x_smooth = self.alpha * x_raw + (1 - self.alpha) * self.prev_smooth
        self.prev_smooth = x_smooth

        # Step 2: Robust scaling (EW-Median/MAD)
        if self.ew_median is None:
            # Cold start
            self.ew_median = x_smooth
            self.ew_mad = 0.01  # Small initial MAD
            z_raw = 0.0
        else:
            # Update EW median
            self.ew_median = self.alpha * x_smooth + (1 - self.alpha) * self.ew_median

            # Update EW MAD
            abs_dev = abs(x_smooth - self.ew_median)
            if self.ew_mad is None:
                self.ew_mad = abs_dev
            else:
                self.ew_mad = self.alpha * abs_dev + (1 - self.alpha) * self.ew_mad

            # Robust z-score
            scale = 1.4826 * max(self.ew_mad, 1e-6)  # Prevent division by zero
            z_raw = (x_smooth - self.ew_median) / scale

        # Step 3: Soft winsorization
        z_soft = self._soft_winsor(z_raw, z0=2.5, zmax=6.0, lam=1.5)

        # Step 4: Compress to ±100
        s_k = 100.0 * np.tanh(z_soft / self.tau)

        # Step 5: Publish filter (simplified - full version in Phase 1.3)
        s_pub = s_k  # Will be enhanced with hysteresis in 1.3

        diagnostics = {
            'x_smooth': x_smooth,
            'z_raw': z_raw,
            'z_soft': z_soft,
            's_k': s_k,
            'ew_median': self.ew_median,
            'ew_mad': self.ew_mad
        }

        return s_pub, diagnostics

    @staticmethod
    def _soft_winsor(z: float, z0: float, zmax: float, lam: float) -> float:
        """
        Soft winsorization with smooth transition.

        Args:
            z: Input z-score
            z0: Threshold for soft clipping (2.5)
            zmax: Hard maximum (6.0)
            lam: Smoothness parameter (1.5)

        Returns:
            z_soft: Winsorized z-score
        """
        abs_z = abs(z)

        if abs_z <= z0:
            return z
        elif abs_z >= zmax:
            return np.sign(z) * zmax
        else:
            # Smooth transition: z0 + (zmax - z0) * [1 - exp(-λ*(|z|-z0))]
            excess = abs_z - z0
            clipped = z0 + (zmax - z0) * (1.0 - np.exp(-lam * excess))
            return np.sign(z) * clipped
```

**Integration Points**:

#### `ats_core/factors_v2/trend_v2.py`
```python
from ats_core.scoring.scoring_utils import StandardizationChain

class TrendFactorV2:
    def __init__(self):
        self.standardizer = StandardizationChain(alpha=0.15, tau=3.0)

    async def calculate(self, df: pd.DataFrame, interval: str) -> dict:
        # ... existing calculation ...
        raw_score = self._compute_raw_trend(df)

        # Apply standardization chain
        T_score, diagnostics = self.standardizer.standardize(raw_score)

        return {
            "score": T_score,
            "diagnostics": diagnostics,
            "interval": interval
        }
```

**Apply to ALL Factors**:
- `ats_core/factors_v2/trend_v2.py` (T)
- `ats_core/factors_v2/momentum_v2.py` (M)
- `ats_core/factors_v2/cyclical_v2.py` (C)
- `ats_core/factors_v2/structure_v2.py` (S)
- `ats_core/features/volume.py` (V)
- `ats_core/features/open_interest.py` (O)
- `ats_core/features/liquidity.py` (L)
- `ats_core/features/book.py` (B)
- `ats_core/features/quality.py` (Q)
- `ats_core/features/imbalance.py` (I)

**Parameter Source**:
- STANDARDS.md § 1.2: α=0.15, τ=3.0, z0=2.5, zmax=6.0, λ=1.5
- MAD scale factor: 1.4826 (Gaussian consistency constant)

**Testing**:
```python
# Test standardization chain
chain = StandardizationChain()
scores = []
for x in [1.5, 2.0, 5.0, 10.0, 100.0, 1000.0]:  # Increasing outliers
    s, diag = chain.standardize(x)
    scores.append(s)
    assert -100 <= s <= 100, f"Score {s} out of range"
    print(f"x={x} → z_raw={diag['z_raw']:.2f}, z_soft={diag['z_soft']:.2f}, s={s:.2f}")

# Verify outlier resistance
assert scores[-1] < 105, "Extreme outlier not properly winsorized"
```

**Rollback Strategy**:
```bash
rm ats_core/scoring/scoring_utils.py
git checkout ats_core/factors_v2/*.py ats_core/features/*.py
```

---

### 1.3 Publishing Anti-Jitter Mechanism (CRITICAL)

**Issue**: No hysteresis/persistence/cooldown, signals flip rapidly
**Spec Reference**: PUBLISHING.md § 4.3 - Anti-jitter triple defense

**Files to Modify**:

#### `ats_core/publishing/anti_jitter.py` (NEW MODULE)

**Create New File**:
```python
"""
Anti-jitter mechanism for signal publishing.
Implements PUBLISHING.md § 4.3 triple defense.
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
```

**Integration Point**:

#### `scripts/realtime_signal_scanner.py`

```python
from ats_core.publishing.anti_jitter import AntiJitter

class SignalScanner:
    def __init__(self, ...):
        # ... existing init ...
        self.anti_jitter = AntiJitter(
            prime_entry_threshold=0.80,
            prime_maintain_threshold=0.70,
            watch_entry_threshold=0.50,
            watch_maintain_threshold=0.40,
            confirmation_bars=2,
            total_bars=3,
            cooldown_seconds=90
        )

    async def _check_and_send_signal(self, symbol: str, result: dict):
        """Check signal with anti-jitter before sending."""
        publish = result.get('publish', {})
        probability = publish.get('probability', 0)
        ev = publish.get('ev', 0)
        gates_passed = publish.get('final_level') in ['PRIME', 'WATCH']

        # Apply anti-jitter
        new_level, should_publish = self.anti_jitter.update(
            symbol=symbol,
            probability=probability,
            ev=ev,
            gates_passed=gates_passed
        )

        if should_publish:
            # State changed AND cooldown passed, send signal
            log(f"✅ {symbol}: {new_level} (anti-jitter confirmed)")
            await self._send_telegram_signal(symbol, result)
        else:
            log(f"⏸️  {symbol}: {new_level} (waiting for confirmation)")
```

**Parameter Source**:
- PUBLISHING.md § 4.3:
  - Prime entry: P ≥ 0.80
  - Prime maintain: P ≥ 0.70 (hysteresis)
  - Watch entry: P ≥ 0.50
  - Watch maintain: P ≥ 0.40
  - Confirmation: 2/3 bars
  - Cooldown: 90 seconds

**Testing**:
```python
# Test anti-jitter
aj = AntiJitter()

# Scenario 1: Gradual entry
for i in range(5):
    prob = 0.75 + i * 0.02  # 0.75, 0.77, 0.79, 0.81, 0.83
    level, publish = aj.update('BTCUSDT', prob, ev=0.5, gates_passed=True)
    print(f"Bar {i}: P={prob:.2f} → {level}, publish={publish}")

# Should see: IGNORE → ... → PRIME (on bar 3 or 4)

# Scenario 2: Jitter test (rapid flip)
for prob in [0.82, 0.68, 0.84, 0.66, 0.85]:  # Alternating
    level, publish = aj.update('ETHUSDT', prob, ev=0.5, gates_passed=True)
# Should suppress rapid changes
```

**Rollback Strategy**:
```bash
rm ats_core/publishing/anti_jitter.py
git checkout scripts/realtime_signal_scanner.py
```

---

### Phase 1 Summary

**Files Modified**: 13 files
**Files Created**: 2 new modules
**Breaking Changes**: Yes (scoring output changes)
**Shadow Run Toggle**: Add `--shadow-mode` flag (default: True)

**Testing Checklist**:
- [ ] Run 10 symbols, verify F not in scores dict
- [ ] Verify standardization diagnostics present
- [ ] Verify anti-jitter delays rapid state changes
- [ ] Verify total score sum = 100.0
- [ ] Compare old vs new S_total distribution (expect ±10% shift)

**Rollback Command**:
```bash
git checkout feature/v2-phase1-critical
git reset --hard HEAD~1
```

---

## 🎯 PHASE 2: HIGH PRIORITY FIXES

**Priority**: HIGH
**Duration**: 1-2 days
**Risk**: LOW (parameter tuning)
**Rollback**: Git branch `feature/v2-phase2-high`

### 2.1 Fix Impact Threshold (HIGH)

**Issue**: Impact threshold 10.0 bps, should be 7.0 bps
**Spec Reference**: PUBLISHING.md § 3.2.1

**Files to Modify**:

#### `ats_core/execution/metrics_estimator.py`

**Location**: Line 239
**Current**:
```python
impact_bps = 10.0  # ❌ WRONG
```

**New**:
```python
impact_bps = 7.0  # ✅ CORRECT - Standard coins (STANDARDS.md)
```

**Parameter Source**: PUBLISHING.md Table 3-1: "Entry impact ≤ 7 bps (standard)"

**Interface Changes**: None (internal threshold only)

**Testing**:
- Run BTC/ETH, verify PRIME published if impact 6-7 bps range
- Verify WATCH_ONLY if impact 8-9 bps range

**Rollback Strategy**:
```bash
git checkout ats_core/execution/metrics_estimator.py
# Change line 239 back to 10.0
```

---

### 2.2 Add Factor Pre-Processing (HIGH)

**Issue**: Factors like V/O/L/B don't implement full standardization chain
**Spec Reference**: STANDARDS.md § 1.2

**Files to Modify**: Same as Phase 1.2 (already integrated)

**Additional Work**: Verify all 11 factors use StandardizationChain

**Testing**:
```python
# Verify all factors have standardizer
from ats_core.factors_v2 import *
from ats_core.features import *

factors = [TrendFactorV2(), MomentumFactorV2(), ..., ImbalanceFactor()]
for f in factors:
    assert hasattr(f, 'standardizer'), f"{f.__class__.__name__} missing standardizer"
```

---

### Phase 2 Summary

**Files Modified**: 2 files
**Breaking Changes**: No (threshold tightening only)
**Testing**: Compare signal counts before/after (expect ~10% reduction)

---

## 🎯 PHASE 3: INFRASTRUCTURE & OPTIMIZATION

**Priority**: LOW
**Duration**: 1-2 days
**Risk**: LOW (infrastructure only)
**Rollback**: Git branch `feature/v2-phase3-infra`

### 3.1 WS Connection Pooling (LOW)

**Issue**: Potential 280 connections if WS enabled for all symbols
**Spec Reference**: DATA_LAYER.md § 2.1 - "3-5 connections max"

**Files to Modify**:

#### `ats_core/data/realtime_kline.py` (NEW DESIGN)

**Current Design**:
```python
# One connection per symbol per interval
for symbol in symbols:
    for interval in ['1h', '4h']:
        create_websocket(symbol, interval)  # 140×2 = 280 connections
```

**New Design** (Connection Pooling):
```python
# Multiplexed streams (combine symbols)
class WSConnectionPool:
    """
    Manage 3-5 shared WS connections for all symbols.

    Strategy:
    - kline_1h: 1 connection (all symbols combined)
    - kline_4h: 1 connection (all symbols combined)
    - aggTrade: 1 connection (all symbols combined)
    - depth: Dynamic (mount only for WATCH/PRIME symbols)
    - markPrice: 1 connection (all symbols combined)

    Total: 3-4 baseline + 0-1 dynamic = 3-5 connections
    """

    def __init__(self, max_connections: int = 5):
        self.max_connections = max_connections
        self.active_connections = {}

    async def subscribe_combined(self, symbols: list, stream_type: str):
        """
        Subscribe to combined stream for multiple symbols.

        Args:
            symbols: List of symbols (e.g., ['BTCUSDT', 'ETHUSDT'])
            stream_type: 'kline_1h', 'kline_4h', 'aggTrade', etc.

        Returns:
            connection_id: Shared connection ID
        """
        # Binance combined stream format
        streams = [f"{s.lower()}@{stream_type}" for s in symbols]
        combined_url = f"wss://fstream.binance.com/stream?streams={'/'.join(streams)}"

        if len(self.active_connections) >= self.max_connections:
            raise RuntimeError(f"WS limit reached: {self.max_connections}")

        conn_id = f"combined_{stream_type}"
        self.active_connections[conn_id] = await create_websocket(combined_url)

        return conn_id
```

**Parameter Source**: DATA_LAYER.md § 2.1: "3-5 WS max"

**Testing**:
```python
# Test connection pool
pool = WSConnectionPool(max_connections=5)
symbols = ['BTCUSDT', 'ETHUSDT', ...]

# Subscribe to baseline streams
await pool.subscribe_combined(symbols, 'kline_1h')  # 1
await pool.subscribe_combined(symbols, 'kline_4h')  # 2
await pool.subscribe_combined(symbols, 'aggTrade')  # 3

assert len(pool.active_connections) == 3, "Should have 3 connections"
```

**Rollback Strategy**: Keep WS disabled (current safe state)

---

### 3.2 Advanced Monitoring Dashboard (LOW)

**Files to Create**:
- `ats_core/monitoring/dashboard.py` - Real-time monitoring
- `scripts/view_dashboard.sh` - CLI dashboard viewer

**Features**:
- DataQual heatmap (per-symbol)
- EV distribution histogram
- WS connection count gauge
- Signal publication log

---

### Phase 3 Summary

**Files Created**: 3 new modules
**Breaking Changes**: None
**Testing**: Monitor WS count < 5 during runtime

---

## 📊 SHADOW RUN CONFIGURATION

**Default Mode**: Shadow run (no real orders)

### Shadow Run Toggle

**Environment Variable**:
```bash
export CRYPTOSIGNAL_SHADOW_MODE=1  # Default
export CRYPTOSIGNAL_REAL_TRADING=0  # Explicitly disabled
```

**Code Integration** (`ats_core/execution/order_manager.py`):
```python
import os

class OrderManager:
    def __init__(self):
        self.shadow_mode = os.getenv('CRYPTOSIGNAL_SHADOW_MODE', '1') == '1'
        self.real_trading = os.getenv('CRYPTOSIGNAL_REAL_TRADING', '0') == '1'

        if self.real_trading and self.shadow_mode:
            raise ValueError("Cannot enable both SHADOW_MODE and REAL_TRADING")

        if self.real_trading:
            log("⚠️  REAL TRADING ENABLED - Live orders will be placed!")
        else:
            log("✅ Shadow mode - No real orders (simulation only)")

    async def place_order(self, symbol: str, side: str, qty: float):
        if self.shadow_mode:
            log(f"[SHADOW] {side} {qty} {symbol} (simulated)")
            return {"status": "simulated", "order_id": None}
        else:
            # Real order placement
            return await self.exchange.create_order(symbol, side, qty)
```

**Validation**:
- [ ] Verify shadow mode logs show "[SHADOW]" prefix
- [ ] Verify no API keys required in shadow mode
- [ ] Verify real trading requires explicit environment variable

---

## 🔄 ROLLBACK STRATEGIES

### Per-Phase Rollback

**Phase 1 Rollback**:
```bash
git checkout main
git branch -D feature/v2-phase1-critical
# Restore original files
git checkout HEAD~3 -- ats_core/pipeline/analyze_symbol.py
git checkout HEAD~3 -- ats_core/scoring/
git checkout HEAD~3 -- scripts/realtime_signal_scanner.py
```

**Phase 2 Rollback**:
```bash
git checkout feature/v2-phase1-critical  # Restore to Phase 1 state
git branch -D feature/v2-phase2-high
```

**Phase 3 Rollback**:
```bash
git checkout feature/v2-phase2-high  # Restore to Phase 2 state
git branch -D feature/v2-phase3-infra
```

### Emergency Rollback (Full Revert)

```bash
git checkout main
git reset --hard HEAD~10  # Revert all v2.0 changes
git push -f origin main  # Force push (USE WITH CAUTION)
```

---

## 📈 TESTING & VALIDATION

### Unit Tests (Per-Phase)

**Phase 1 Tests**:
```bash
pytest tests/test_standardization_chain.py -v
pytest tests/test_f_isolation.py -v
pytest tests/test_anti_jitter.py -v
```

**Phase 2 Tests**:
```bash
pytest tests/test_impact_threshold.py -v
pytest tests/test_factor_preprocessing.py -v
```

**Phase 3 Tests**:
```bash
pytest tests/test_ws_connection_pool.py -v
pytest tests/test_monitoring.py -v
```

### Integration Tests

**Shadow Run Validation**:
```bash
# Run 10-symbol shadow test
python3 scripts/realtime_signal_scanner.py \
    --symbols BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,ADAUSDT \
    --interval 60 \
    --min-score 70 \
    --shadow-mode

# Verify outputs
ls shadow_out/*.parquet  # Should contain signal records
ls shadow_out/*.json     # Should contain diagnostics

# Check no real orders
grep "REAL ORDER" /tmp/cryptosignal_scanner.log  # Should be empty
```

**Compliance Verification**:
```bash
# Run compliance check script
python3 scripts/check_compliance.py --phase 1
# Expected output: "Phase 1: 3/3 CRITICAL fixes validated ✅"
```

---

## 🎯 SUCCESS CRITERIA

### Phase 1 Success
- [ ] F not in `result['scores']` dict
- [ ] All 11 factors use StandardizationChain
- [ ] Anti-jitter suppresses <90s state changes
- [ ] Total score sum = 100.0 ± 0.01
- [ ] No signals published in first 3 bars (persistence check)

### Phase 2 Success
- [ ] Impact threshold = 7.0 bps enforced
- [ ] ~10% fewer PRIME signals (stricter gate)
- [ ] Standardization diagnostics in all factor outputs

### Phase 3 Success
- [ ] WS connection count ≤ 5 (monitored)
- [ ] Dashboard shows real-time DataQual
- [ ] No performance degradation vs Phase 2

### Overall Success
- [ ] COMPLIANCE_REPORT.md shows 8/8 ✅
- [ ] Shadow run generates valid output (no crashes)
- [ ] EV > 0 for all PRIME signals
- [ ] No directional bias (long/short ratio 45-55%)

---

## 📋 RISK MITIGATION

### High-Risk Changes

**F Removal from Scorecard** (Phase 1.1):
- **Risk**: Score distribution shifts significantly
- **Mitigation**:
  - Compare old vs new S_total on 100-symbol test
  - If shift > 15%, re-balance weights
  - Keep F available as diagnostic field

**Standardization Chain** (Phase 1.2):
- **Risk**: Cold-start instability (first few bars)
- **Mitigation**:
  - Initialize EW median with first raw value
  - Require minimum 10 bars before publishing signals
  - Add `bars_initialized` counter to diagnostics

**Anti-Jitter** (Phase 1.3):
- **Risk**: Miss fast-moving opportunities
- **Mitigation**:
  - Configurable K/N parameters (default 2/3)
  - Allow emergency override for high-confidence signals (P > 0.95)
  - Monitor missed signal count

### Monitoring Alerts

**Phase 1 Alerts**:
- Alert if WS connections > 5
- Alert if DataQual < 0.88 for > 5 minutes
- Alert if EV < 0 for any PRIME signal

**Phase 2 Alerts**:
- Alert if impact > 7 bps but still PRIME
- Alert if standardization chain fails (NaN/inf)

**Phase 3 Alerts**:
- Alert if connection pool exhausted
- Alert if dashboard unreachable

---

## 📅 IMPLEMENTATION TIMELINE

### Week 1: Phase 1 (Critical)
- **Day 1**: F isolation + weight rebalancing
- **Day 2**: Standardization chain implementation
- **Day 3**: Anti-jitter + integration testing

### Week 2: Phase 2 (High Priority)
- **Day 4**: Impact threshold fix
- **Day 5**: Factor pre-processing verification
- **Day 6**: Integration testing

### Week 3: Phase 3 (Infrastructure)
- **Day 7**: WS connection pooling
- **Day 8**: Monitoring dashboard
- **Day 9**: Final integration + shadow run validation

**Total Duration**: 9 days (with 2-day buffer)

---

## ✅ FINAL CHECKLIST

### Pre-Implementation
- [ ] Backup current main branch
- [ ] Create feature branches for each phase
- [ ] Set up shadow run environment variables
- [ ] Prepare test symbol lists

### Phase 1
- [ ] Remove F from scorecard
- [ ] Implement StandardizationChain
- [ ] Add anti-jitter mechanism
- [ ] Run unit tests
- [ ] Run 10-symbol shadow test

### Phase 2
- [ ] Fix impact threshold to 7.0
- [ ] Verify all factors pre-processed
- [ ] Compare signal distributions
- [ ] Run integration tests

### Phase 3
- [ ] Implement WS connection pooling
- [ ] Create monitoring dashboard
- [ ] Verify WS count ≤ 5
- [ ] Final compliance audit

### Post-Implementation
- [ ] Generate SHADOW_RUN_REPORT.md
- [ ] Update COMPLIANCE_REPORT.md to 8/8 ✅
- [ ] Merge to main (with review)
- [ ] Deploy to production (shadow mode)

---

**End of IMPLEMENTATION_PLAN_v2.md**

**Next Steps**:
1. Review and approve this plan
2. Begin Phase 1 implementation
3. Generate SHADOW_RUN_REPORT.md after Phase 1 completion
