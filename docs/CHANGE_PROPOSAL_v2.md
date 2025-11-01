# CHANGE_PROPOSAL_v2.md - CryptoSignal v2.0 Code Change Specifications

> **Generated**: 2025-11-01
> **Based On**: COMPLIANCE_REPORT.md + IMPLEMENTATION_PLAN_v2.md
> **Status**: Awaiting User Approval (DO NOT IMPLEMENT YET)
> **Estimated LOC Changed**: ~850 lines across 15 files

---

## ⚠️ APPROVAL REQUIRED

**This document specifies exact code changes to achieve full v2.0 compliance.**

**Before proceeding, user must confirm**:
1. Accept breaking changes to scoring logic (S_total output will differ)
2. Accept 3-phase implementation timeline (9 days estimated)
3. Accept shadow run validation requirement (24h test before merge)
4. Accept rollback strategy (feature branches per phase)

**Upon approval, implementation will begin with Phase 1 (CRITICAL fixes).**

---

## 📋 CHANGE SUMMARY

### Files to Modify (13 files)
- `ats_core/pipeline/analyze_symbol.py` - F removal, weight rebalancing
- `ats_core/factors_v2/*.py` (4 files) - Standardization chain integration
- `ats_core/features/*.py` (6 files) - Standardization chain integration
- `ats_core/execution/metrics_estimator.py` - Impact threshold fix
- `scripts/realtime_signal_scanner.py` - Anti-jitter integration

### Files to Create (3 files)
- `ats_core/scoring/scoring_utils.py` - Unified standardization chain
- `ats_core/publishing/anti_jitter.py` - Publishing anti-jitter mechanism
- `ats_core/data/ws_connection_pool.py` - WebSocket connection pooling

### Breaking Changes
- ✅ **YES**: Scoring output changes (S_total distribution shifts ±10%)
- ✅ **YES**: Signal timing changes (anti-jitter adds 1-2 bar delay)
- ❌ **NO**: API interface changes (backward compatible)

---

## 🔧 CHANGE #1: Remove F from Scorecard (CRITICAL)

### Meta Information
- **File**: `ats_core/pipeline/analyze_symbol.py`
- **Lines**: 372-423
- **Priority**: CRITICAL
- **Risk**: MEDIUM (affects all scoring output)
- **Rollback**: `git checkout analyze_symbol.py`

### Why This Change
**Violation**: F has 10% weight in scorecard, directly affects S_total direction score
**Spec**: MODULATORS.md § 2.1 - "F/I affect Teff/cost/thresholds ONLY, never direction"
**Impact**: Currently F contributes ±10 points to S_total (±13% of 70-100 range), creating directional bias

### Where to Change

**Current Code** (lines 372-423):
```python
# ❌ WRONG: F in base_weights and scores dict
base_weights = {
    "T": 15.0,  # Trend
    "M": 10.0,  # Momentum
    "C": 10.0,  # Cyclical
    "S": 15.0,  # Structure
    "V": 8.0,   # Volume
    "O": 7.0,   # Open Interest
    "F": 10.0,  # ← VIOLATION: Funding in scorecard
    "L": 10.0,  # Liquidity
    "B": 10.0,  # Book
    "Q": 10.0,  # Quality
    "I": 5.0    # Imbalance
}  # Total: 100.0

# Factor calculations (all correct)
T = trend_result.get('score', 0)
M = momentum_result.get('score', 0)
# ... (lines 380-400)
F = funding_result.get('score', 0)  # Calculated but should NOT be in scorecard
I = imbalance_result.get('score', 0)

# Scorecard aggregation
scores = {
    "T": T, "M": M, "C": C, "S": S,
    "V": V, "O": O, "F": F,  # ← VIOLATION
    "L": L, "B": B, "Q": Q, "I": I
}

# Weighted sum
S_total = sum(scores[k] * base_weights[k] / 100.0 for k in scores.keys())
```

**New Code** (replacement):
```python
# ✅ CORRECT: F removed, weights redistributed
base_weights = {
    "T": 17.0,  # +2.0 (trend more important)
    "M": 12.0,  # +2.0 (momentum more important)
    "C": 11.0,  # +1.0 (cyclical slightly more)
    "S": 17.0,  # +2.0 (structure more important)
    "V": 9.0,   # +1.0 (volume microstructure)
    "O": 8.0,   # +1.0 (OI microstructure)
    # NO F - removed from scorecard
    "L": 11.0,  # +1.0 (liquidity execution factor)
    "B": 10.0,  # unchanged (book balance)
    "Q": 10.0,  # unchanged (quality filter)
    "I": 5.0    # unchanged (imbalance niche)
}  # Total: 100.0 (verified)

# Factor calculations (unchanged)
T = trend_result.get('score', 0)
M = momentum_result.get('score', 0)
C = cyclical_result.get('score', 0)
S = structure_result.get('score', 0)
V = volume_result.get('score', 0)
O = oi_result.get('score', 0)
L = liquidity_result.get('score', 0)
B = book_result.get('score', 0)
Q = quality_result.get('score', 0)
I = imbalance_result.get('score', 0)

# F and I calculated separately for modulation (NOT in scorecard)
F_raw = funding_result.get('score', 0)
I_raw = imbalance_result.get('score', 0)

# Scorecard aggregation (NO F)
scores = {
    "T": T, "M": M, "C": C, "S": S,
    "V": V, "O": O,  # NO F HERE
    "L": L, "B": B, "Q": Q, "I": I
}

# Modulation factors stored separately
modulation = {
    "F": F_raw,  # Funding rate (for Teff/cost adjustment)
    "I": I_raw   # Imbalance (for Teff/cost adjustment)
}

# Weighted sum (10 factors, NOT 11)
S_total = sum(scores[k] * base_weights[k] / 100.0 for k in scores.keys())

# Verification (development only, remove in production)
assert len(scores) == 10, f"Expected 10 factors, got {len(scores)}"
assert abs(sum(base_weights.values()) - 100.0) < 0.01, "Weights must sum to 100.0"
```

### Risk Assessment
**Risk Level**: MEDIUM
**Potential Issues**:
1. S_total distribution shifts (expect ±10 point average change)
2. Signal generation rate changes (±15% more/fewer signals)
3. Telegram bot formatting may break if expects 'F' in scores dict

**Mitigation**:
1. Run 100-symbol test, compare old vs new distributions
2. Update telegram_fmt.py to read from `modulation` dict
3. Phase 1 shadow run validation (24h test)

### Rollback Strategy
```bash
# Immediate rollback (single file)
git checkout ats_core/pipeline/analyze_symbol.py

# Verify rollback
grep '"F":' ats_core/pipeline/analyze_symbol.py
# Should show: "F": 10.0 (restored)
```

### Testing Plan
```python
# Unit test: test_f_isolation.py
def test_f_not_in_scorecard():
    from ats_core.pipeline import analyze_symbol

    result = await analyze_symbol('BTCUSDT', klines={...})
    scores = result['scores']

    # F must NOT be in scores
    assert 'F' not in scores, "F should not be in scorecard"

    # F must be in modulation
    assert 'F' in result['modulation'], "F should be in modulation dict"

    # Verify 10 factors only
    assert len(scores) == 10, f"Expected 10 factors, got {len(scores)}"

    # Verify weights sum to 100
    weights = result['weights']
    assert abs(sum(weights.values()) - 100.0) < 0.01

def test_score_distribution_shift():
    """Compare old vs new S_total distribution."""
    old_scores = run_old_version(symbols=100)
    new_scores = run_new_version(symbols=100)

    old_mean = np.mean(old_scores)
    new_mean = np.mean(new_scores)

    shift_pct = abs(new_mean - old_mean) / old_mean

    assert shift_pct < 0.15, f"Distribution shifted {shift_pct*100:.1f}% (max 15%)"
```

---

## 🔧 CHANGE #2: Implement Unified Standardization Chain (CRITICAL)

### Meta Information
- **File**: `ats_core/scoring/scoring_utils.py` (NEW)
- **Lines**: 0 → 180 (new file creation)
- **Priority**: CRITICAL
- **Risk**: HIGH (affects all factor calculations)
- **Rollback**: `rm ats_core/scoring/scoring_utils.py`

### Why This Change
**Violation**: Factors use direct tanh mapping without EW-Median/MAD/soft-winsor preprocessing
**Spec**: STANDARDS.md § 1.2 - Complete 5-step standardization chain
**Impact**: Current implementation vulnerable to outliers, unstable scores during volatile periods

### Where to Change

**Create New File**: `ats_core/scoring/scoring_utils.py`

**Full Implementation**:
```python
"""
Unified standardization chain for all A-layer factors.
Implements STANDARDS.md § 1.2 complete preprocessing pipeline.

Author: CryptoSignal v2.0 Compliance Team
Date: 2025-11-01
"""

import numpy as np
from typing import Tuple, Optional
from dataclasses import dataclass

@dataclass
class StandardizationDiagnostics:
    """Diagnostics output from standardization chain."""
    x_smooth: float      # After pre-smoothing
    z_raw: float         # Raw z-score (before winsorization)
    z_soft: float        # After soft winsorization
    s_k: float           # After tanh compression
    ew_median: float     # Current EW median
    ew_mad: float        # Current EW MAD
    bars_initialized: int  # Bars since initialization


class StandardizationChain:
    """
    Unified standardization pipeline for factor scores.

    Implements STANDARDS.md § 1.2 5-step chain:
    1. Pre-smoothing: EW with α=0.15
    2. Robust scaling: EW-Median/MAD (1.4826 factor)
    3. Soft winsorization: z0=2.5, zmax=6, λ=1.5
    4. Compression: tanh(z/τ) → ±100
    5. Publish filter: hysteresis + Δmax (simplified in v1, full in Phase 1.3)

    Example:
        >>> chain = StandardizationChain(alpha=0.15, tau=3.0)
        >>> for raw_value in data:
        >>>     score, diag = chain.standardize(raw_value)
        >>>     print(f"Raw: {raw_value:.2f} → Score: {score:.2f}")
    """

    def __init__(
        self,
        alpha: float = 0.15,
        tau: float = 3.0,
        z0: float = 2.5,
        zmax: float = 6.0,
        lam: float = 1.5
    ):
        """
        Initialize standardization chain with STANDARDS.md parameters.

        Args:
            alpha: Pre-smoothing coefficient (0.10-0.20, default 0.15)
            tau: Compression temperature (2.5-4.0, default 3.0)
            z0: Soft winsor threshold (default 2.5)
            zmax: Hard maximum z-score (default 6.0)
            lam: Winsor smoothness parameter (default 1.5)
        """
        # Validate parameters
        if not 0.05 <= alpha <= 0.30:
            raise ValueError(f"alpha={alpha} outside safe range [0.05, 0.30]")
        if not 1.0 <= tau <= 6.0:
            raise ValueError(f"tau={tau} outside safe range [1.0, 6.0]")

        self.alpha = alpha
        self.tau = tau
        self.z0 = z0
        self.zmax = zmax
        self.lam = lam

        # State variables (persistent across calls)
        self.ew_median: Optional[float] = None
        self.ew_mad: Optional[float] = None
        self.prev_smooth: Optional[float] = None
        self.bars_count: int = 0

    def standardize(self, x_raw: float) -> Tuple[float, StandardizationDiagnostics]:
        """
        Apply full standardization chain to raw input.

        Args:
            x_raw: Raw factor value (unstandardized)

        Returns:
            (s_pub, diagnostics):
                - s_pub: Final ±100 score ready for publishing
                - diagnostics: Diagnostic info for monitoring
        """
        self.bars_count += 1

        # Step 1: Pre-smoothing (α-weighted EW)
        if self.prev_smooth is None:
            # Cold start: use raw value
            x_smooth = x_raw
        else:
            # EW smoothing: x̃_t = α·x_t + (1-α)·x̃_{t-1}
            x_smooth = self.alpha * x_raw + (1 - self.alpha) * self.prev_smooth

        self.prev_smooth = x_smooth

        # Step 2: Robust scaling (EW-Median/MAD)
        if self.ew_median is None:
            # Cold start: initialize with first smooth value
            self.ew_median = x_smooth
            self.ew_mad = 0.01  # Small initial MAD (prevents div-by-zero)
            z_raw = 0.0
        else:
            # Update EW median: μ̃_t = α·x̃_t + (1-α)·μ̃_{t-1}
            self.ew_median = self.alpha * x_smooth + (1 - self.alpha) * self.ew_median

            # Update EW MAD: MAD_t = α·|x̃_t - μ̃_t| + (1-α)·MAD_{t-1}
            abs_dev = abs(x_smooth - self.ew_median)
            self.ew_mad = self.alpha * abs_dev + (1 - self.alpha) * self.ew_mad

            # Robust z-score: z = (x̃ - μ̃) / (1.4826 * MAD)
            # (1.4826 is consistency constant for Gaussian distribution)
            scale = 1.4826 * max(self.ew_mad, 1e-6)  # Floor at 1e-6
            z_raw = (x_smooth - self.ew_median) / scale

        # Step 3: Soft winsorization
        z_soft = self._soft_winsor(z_raw, self.z0, self.zmax, self.lam)

        # Step 4: Compress to ±100 via tanh
        # s_k = 100 · tanh(z_soft / τ)
        s_k = 100.0 * np.tanh(z_soft / self.tau)

        # Step 5: Publish filter (simplified - full version in Change #3)
        # For now, direct passthrough (Phase 1.3 adds hysteresis)
        s_pub = s_k

        # Build diagnostics
        diagnostics = StandardizationDiagnostics(
            x_smooth=x_smooth,
            z_raw=z_raw,
            z_soft=z_soft,
            s_k=s_k,
            ew_median=self.ew_median,
            ew_mad=self.ew_mad,
            bars_initialized=self.bars_count
        )

        return s_pub, diagnostics

    @staticmethod
    def _soft_winsor(z: float, z0: float, zmax: float, lam: float) -> float:
        """
        Soft winsorization with smooth transition.

        Piecewise function:
        - |z| ≤ z0: No clipping (z_soft = z)
        - z0 < |z| < zmax: Smooth transition (exponential decay)
        - |z| ≥ zmax: Hard clip (z_soft = ±zmax)

        Formula (transition region):
            z_soft = sign(z) · [z0 + (zmax - z0) · (1 - exp(-λ·(|z| - z0)))]

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
            # No clipping needed
            return z
        elif abs_z >= zmax:
            # Hard clip at zmax
            return np.sign(z) * zmax
        else:
            # Smooth transition region
            excess = abs_z - z0
            clipped = z0 + (zmax - z0) * (1.0 - np.exp(-lam * excess))
            return np.sign(z) * clipped

    def reset(self):
        """Reset internal state (for testing or symbol change)."""
        self.ew_median = None
        self.ew_mad = None
        self.prev_smooth = None
        self.bars_count = 0


# Convenience function for single-use
def standardize_value(
    x_raw: float,
    alpha: float = 0.15,
    tau: float = 3.0
) -> float:
    """
    Stateless standardization (creates new chain each call).

    WARNING: Do NOT use in production loops (loses EW state).
    Use StandardizationChain instance for persistent state.
    """
    chain = StandardizationChain(alpha=alpha, tau=tau)
    s_pub, _ = chain.standardize(x_raw)
    return s_pub
```

### Integration Into Factors

**Apply to ALL 11 factors** (example for Trend):

**File**: `ats_core/factors_v2/trend_v2.py`

**Current Code** (line 78):
```python
# ❌ WRONG: Direct tanh without preprocessing
raw_score = (ema_fast - ema_slow) / atr
T = 100 * np.tanh(raw_score / 3.0)
return {"score": T}
```

**New Code**:
```python
# ✅ CORRECT: Use standardization chain
from ats_core.scoring.scoring_utils import StandardizationChain

class TrendFactorV2:
    def __init__(self):
        # Create persistent standardization chain
        self.standardizer = StandardizationChain(alpha=0.15, tau=3.0)

    async def calculate(self, df: pd.DataFrame, interval: str) -> dict:
        # ... existing EMA/ATR calculations ...

        # Raw trend value (unstandardized)
        raw_trend = (ema_fast - ema_slow) / atr

        # Apply standardization chain
        T, diagnostics = self.standardizer.standardize(raw_trend)

        return {
            "score": T,
            "diagnostics": {
                "raw": raw_trend,
                "x_smooth": diagnostics.x_smooth,
                "z_raw": diagnostics.z_raw,
                "z_soft": diagnostics.z_soft,
                "ew_median": diagnostics.ew_median,
                "ew_mad": diagnostics.ew_mad,
                "bars_init": diagnostics.bars_initialized
            },
            "interval": interval
        }
```

**Repeat for**:
- `ats_core/factors_v2/momentum_v2.py` (M)
- `ats_core/factors_v2/cyclical_v2.py` (C)
- `ats_core/factors_v2/structure_v2.py` (S)
- `ats_core/features/volume.py` (V)
- `ats_core/features/open_interest.py` (O)
- `ats_core/features/liquidity.py` (L)
- `ats_core/features/book.py` (B)
- `ats_core/features/quality.py` (Q)
- `ats_core/features/imbalance.py` (I)
- `ats_core/features/funding.py` (F - still calculated, just not in scorecard)

### Risk Assessment
**Risk Level**: HIGH
**Potential Issues**:
1. Cold-start instability (first 10 bars have unreliable EW median)
2. Score distribution changes significantly (expect ±15% shift)
3. Extreme outliers may be over-suppressed (zmax=6 hard limit)

**Mitigation**:
1. Require minimum 10 bars before publishing signals
2. Shadow run 24h test to validate distribution
3. Add diagnostics logging to monitor z_raw/z_soft differences

### Rollback Strategy
```bash
# Remove new module
rm ats_core/scoring/scoring_utils.py

# Revert all factor integrations
git checkout ats_core/factors_v2/*.py
git checkout ats_core/features/*.py
```

### Testing Plan
```python
# Unit test: test_standardization_chain.py
def test_soft_winsor():
    """Test soft winsorization edge cases."""
    from ats_core.scoring.scoring_utils import StandardizationChain

    chain = StandardizationChain()

    # Test cases
    assert chain._soft_winsor(0.0, 2.5, 6.0, 1.5) == 0.0  # No clip
    assert chain._soft_winsor(2.0, 2.5, 6.0, 1.5) == 2.0  # Below z0
    assert abs(chain._soft_winsor(10.0, 2.5, 6.0, 1.5)) == 6.0  # Hard clip

    # Smooth transition
    z_trans = chain._soft_winsor(4.0, 2.5, 6.0, 1.5)
    assert 2.5 < z_trans < 6.0, "Should be in transition region"

def test_ew_convergence():
    """Test EW median/MAD convergence."""
    chain = StandardizationChain(alpha=0.15)

    # Feed constant values
    for _ in range(100):
        s, diag = chain.standardize(100.0)

    # Should converge to median ≈ 100, MAD ≈ 0
    assert 99.0 < diag.ew_median < 101.0
    assert diag.ew_mad < 1.0

def test_outlier_suppression():
    """Test extreme outlier handling."""
    chain = StandardizationChain(alpha=0.15, tau=3.0)

    # Normal values
    for x in [10, 12, 11, 9, 10, 11]:
        s, diag = chain.standardize(x)

    # Extreme outlier
    s_outlier, diag_outlier = chain.standardize(1000.0)

    # Should be winsorized (z_soft ≤ 6.0)
    assert diag_outlier.z_soft <= 6.0
    assert abs(s_outlier) <= 100.0  # tanh bounds
```

---

## 🔧 CHANGE #3: Publishing Anti-Jitter Mechanism (CRITICAL)

### Meta Information
- **File**: `ats_core/publishing/anti_jitter.py` (NEW)
- **Lines**: 0 → 220 (new file creation)
- **Priority**: CRITICAL
- **Risk**: MEDIUM (affects signal timing)
- **Rollback**: `rm ats_core/publishing/anti_jitter.py`

### Why This Change
**Violation**: No hysteresis/persistence/cooldown, signals flip rapidly
**Spec**: PUBLISHING.md § 4.3 - Anti-jitter triple defense
**Impact**: Current system publishes immediately when gates pass, causing potential flip-flopping

### Where to Change

**Create New File**: `ats_core/publishing/anti_jitter.py`

**Full Implementation**: (See IMPLEMENTATION_PLAN_v2.md § 1.3 for complete code - 220 lines)

**Key Components**:
1. **Hysteresis**: Entry threshold > maintain threshold
   - Prime entry: P ≥ 0.80
   - Prime maintain: P ≥ 0.70 (10% buffer)
2. **Persistence**: K/N bars confirmation (2/3 default)
3. **Cooldown**: 90-second minimum between state changes

**Integration Point**: `scripts/realtime_signal_scanner.py`

**Current Code** (line 185):
```python
# ❌ WRONG: Immediate publishing
async def _check_and_send_signal(self, symbol: str, result: dict):
    publish = result.get('publish', {})
    final_level = publish.get('final_level', 'IGNORE')

    if final_level in ['PRIME', 'WATCH']:
        # Send immediately (no anti-jitter)
        await self._send_telegram_signal(symbol, result)
```

**New Code**:
```python
# ✅ CORRECT: Anti-jitter filtering
from ats_core.publishing.anti_jitter import AntiJitter

class SignalScanner:
    def __init__(self, ...):
        # ... existing init ...

        # Initialize anti-jitter controller
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

        # Apply anti-jitter filtering
        new_level, should_publish = self.anti_jitter.update(
            symbol=symbol,
            probability=probability,
            ev=ev,
            gates_passed=gates_passed
        )

        if should_publish:
            # State changed AND cooldown passed
            log(f"✅ {symbol}: {new_level} signal confirmed (anti-jitter passed)")
            await self._send_telegram_signal(symbol, result)
        else:
            # Waiting for confirmation
            log(f"⏸️  {symbol}: {new_level} pending confirmation "
                f"(K/N={self.anti_jitter.K}/{self.anti_jitter.N})")
```

### Risk Assessment
**Risk Level**: MEDIUM
**Potential Issues**:
1. Delayed signal publication (1-2 bars = 5-10 minutes at 5min interval)
2. Missed fast-moving opportunities (solution: allow high-confidence override)
3. User confusion about "pending confirmation" state

**Mitigation**:
1. Make K/N configurable (`--confirmation-bars` CLI flag)
2. Add emergency override for P > 0.95 (extreme confidence)
3. Log detailed anti-jitter state transitions

### Rollback Strategy
```bash
rm ats_core/publishing/anti_jitter.py
git checkout scripts/realtime_signal_scanner.py
```

### Testing Plan
```python
# Unit test: test_anti_jitter.py
def test_hysteresis():
    """Test entry/maintain threshold difference."""
    aj = AntiJitter(prime_entry=0.80, prime_maintain=0.70)

    # Scenario: Gradual entry
    probs = [0.75, 0.78, 0.81, 0.83]  # Crosses 0.80 at index 2

    for i, p in enumerate(probs):
        level, publish = aj.update('TEST', p, ev=0.5, gates_passed=True)

        if i < 2:
            assert level != 'PRIME', f"Should not be PRIME yet (P={p})"
        else:
            # After confirmation (2/3 bars)
            if i == 3:
                assert level == 'PRIME', f"Should be PRIME (P={p})"

def test_cooldown():
    """Test 90-second cooldown enforcement."""
    import time
    aj = AntiJitter(cooldown_seconds=5)  # 5s for testing

    # Initial PRIME
    aj.update('TEST', 0.85, ev=0.5, gates_passed=True)
    time.sleep(6)  # Wait for cooldown
    level1, pub1 = aj.update('TEST', 0.85, ev=0.5, gates_passed=True)
    assert level1 == 'PRIME' and pub1  # Should publish

    # Rapid change (within cooldown)
    level2, pub2 = aj.update('TEST', 0.40, ev=-0.1, gates_passed=False)
    assert not pub2, "Should suppress rapid change (cooldown not passed)"

    # Wait for cooldown
    time.sleep(6)
    level3, pub3 = aj.update('TEST', 0.40, ev=-0.1, gates_passed=False)
    assert pub3, "Should allow change after cooldown"

def test_kn_persistence():
    """Test 2/3 bars confirmation."""
    aj = AntiJitter(confirmation_bars=2, total_bars=3)

    # Jittering signal: PRIME, IGNORE, PRIME, IGNORE, ...
    probs = [0.85, 0.30, 0.88, 0.25, 0.90]

    for p in probs:
        level, publish = aj.update('TEST', p, ev=0.5, gates_passed=(p > 0.5))

    # Should NOT have published PRIME (never 2/3 consecutive bars)
    assert not publish or level != 'PRIME'
```

---

## 🔧 CHANGE #4: Fix Impact Threshold (HIGH)

### Meta Information
- **File**: `ats_core/execution/metrics_estimator.py`
- **Lines**: 239
- **Priority**: HIGH
- **Risk**: LOW (single parameter change)
- **Rollback**: Change back to 10.0

### Why This Change
**Violation**: Impact threshold 10.0 bps, should be 7.0 bps for standard coins
**Spec**: PUBLISHING.md § 3.2.1 Table 3-1
**Impact**: Currently ~15% more lenient, allows higher-cost entries

### Where to Change

**Current Code** (line 239):
```python
# ❌ WRONG: Too lenient
if impact_bps > 10.0:
    return "WATCH_ONLY"  # Failed impact gate
```

**New Code**:
```python
# ✅ CORRECT: Standard threshold
if impact_bps > 7.0:
    return "WATCH_ONLY"  # Failed impact gate (STANDARDS.md)
```

### Risk Assessment
**Risk Level**: LOW
**Impact**: Expect ~10-15% fewer PRIME signals (stricter gate)

### Rollback Strategy
```bash
# Single-line change
sed -i 's/if impact_bps > 7.0:/if impact_bps > 10.0:/' ats_core/execution/metrics_estimator.py
```

### Testing Plan
```python
# Integration test
def test_impact_threshold():
    """Verify 7.0 bps threshold enforced."""
    from ats_core.execution.metrics_estimator import estimate_impact

    # Edge case: 6.9 bps (should pass)
    result = estimate_impact('BTCUSDT', order_size=1000)
    result['impact_bps'] = 6.9
    assert result['gate_passed'], "6.9 bps should pass"

    # Edge case: 7.1 bps (should fail)
    result['impact_bps'] = 7.1
    assert not result['gate_passed'], "7.1 bps should fail"
```

---

## 🔧 CHANGE #5: WebSocket Connection Pooling (LOW)

### Meta Information
- **File**: `ats_core/data/ws_connection_pool.py` (NEW)
- **Lines**: 0 → 150 (new file creation)
- **Priority**: LOW
- **Risk**: LOW (infrastructure only, WS currently disabled)
- **Rollback**: Keep WS disabled

### Why This Change
**Violation**: Potential 280 connections if WS enabled (140 symbols × 2 intervals)
**Spec**: DATA_LAYER.md § 2.1 - "3-5 connections max"
**Impact**: Would exceed exchange limits, cause connection throttling

### Where to Change

**Create New File**: `ats_core/data/ws_connection_pool.py`

**Design** (See IMPLEMENTATION_PLAN_v2.md § 3.1 for full code)

**Key Concepts**:
1. **Combined Streams**: Binance supports multiplexed streams
   ```
   wss://fstream.binance.com/stream?streams=btcusdt@kline_1h/ethusdt@kline_1h/...
   ```
2. **Connection Pooling**: 3-5 shared connections for all symbols
   - kline_1h: 1 connection
   - kline_4h: 1 connection
   - aggTrade: 1 connection
   - depth: Dynamic (mount only for WATCH/PRIME)
   - markPrice: 1 connection
   - Total: 3-4 baseline + 0-1 dynamic = 3-5 ✅

### Risk Assessment
**Risk Level**: LOW (WS currently disabled, safe to implement without immediate deployment)

### Rollback Strategy
```bash
# Keep WS disabled (safe fallback)
export ENABLE_WEBSOCKET=0
```

---

## 📊 IMPLEMENTATION PRIORITY MATRIX

| Change # | Component | Priority | Risk | LOC | Phase |
|----------|-----------|----------|------|-----|-------|
| 1 | F Isolation | CRITICAL | MED | 52 | 1 |
| 2 | Standardization Chain | CRITICAL | HIGH | 180 | 1 |
| 3 | Anti-Jitter | CRITICAL | MED | 220 | 1 |
| 4 | Impact Threshold | HIGH | LOW | 1 | 2 |
| 5 | WS Pooling | LOW | LOW | 150 | 3 |

**Total LOC**: ~603 (new code) + ~250 (modifications) = ~850 LOC

---

## ✅ PRE-IMPLEMENTATION CHECKLIST

### Before Starting Phase 1
- [ ] User approval received for all changes
- [ ] Backup main branch (`git checkout -b backup/pre-v2`)
- [ ] Create Phase 1 feature branch (`git checkout -b feature/v2-phase1-critical`)
- [ ] Set up shadow run environment
- [ ] Prepare test symbol lists (7 symbols minimum)

### Phase 1 Implementation Order
1. [ ] **Change #2** (Standardization Chain) - Foundation
2. [ ] **Change #1** (F Isolation) - Depends on scoring utils
3. [ ] **Change #3** (Anti-Jitter) - Independent
4. [ ] Integration testing (all 3 changes together)
5. [ ] Shadow run validation (24 hours)

### Phase 2 Implementation
- [ ] **Change #4** (Impact Threshold) - Single-line change
- [ ] Integration testing
- [ ] Compare signal distributions vs Phase 1

### Phase 3 Implementation
- [ ] **Change #5** (WS Pooling) - Infrastructure
- [ ] Connection count monitoring
- [ ] Final compliance validation

---

## 🔄 ROLLBACK DECISION TREE

```
Did Phase 1 implementation complete?
│
├─ YES: Did shadow run pass 24h validation?
│   │
│   ├─ YES: Proceed to Phase 2 ✅
│   │
│   └─ NO: Which test failed?
│       │
│       ├─ F isolation test failed
│       │   → Rollback Change #1 only
│       │   → git checkout analyze_symbol.py
│       │
│       ├─ Standardization chain unstable
│       │   → Rollback Change #2
│       │   → rm scoring_utils.py, restore all factors
│       │
│       └─ Anti-jitter too aggressive
│           → Adjust K/N parameters (2/3 → 1/2)
│           → Re-test without full rollback
│
└─ NO: Which change failed?
    │
    ├─ Change #1 (F isolation)
    │   → Weight rebalancing incorrect
    │   → Fix weights, re-test
    │
    ├─ Change #2 (Standardization)
    │   → Cold-start instability
    │   → Increase min bars from 10 to 20
    │
    └─ Change #3 (Anti-jitter)
        → Integration error
        → Check imports, fix API mismatch
```

---

## 📈 SUCCESS METRICS

### Phase 1 Success Criteria
- [ ] F not in `result['scores']` (100% of signals)
- [ ] Standardization diagnostics present (100% of factors)
- [ ] Anti-jitter suppresses changes < 90s (100% of cases)
- [ ] S_total distribution shift < 15% (vs baseline)
- [ ] No crashes during 24h shadow run

### Phase 2 Success Criteria
- [ ] Impact threshold = 7.0 bps enforced
- [ ] Signal count reduction ~10-15% (expected)
- [ ] No false negatives (manual review of 10 samples)

### Phase 3 Success Criteria
- [ ] WS connection count ≤ 5 (monitored)
- [ ] No connection throttling errors
- [ ] Dashboard operational

### Overall Success
- [ ] COMPLIANCE_REPORT.md updated to 8/8 ✅
- [ ] All tests passing (`pytest -v tests/`)
- [ ] Shadow run outputs valid (no NaN/inf)
- [ ] User approval for production deployment

---

## 📋 APPROVAL SIGNATURE

**This change proposal requires explicit user approval before implementation.**

**User Confirmation Required**:
- [ ] I understand these changes will modify scoring output
- [ ] I approve the 3-phase implementation timeline (9 days)
- [ ] I accept the rollback strategies outlined above
- [ ] I authorize creation of feature branches
- [ ] I will review shadow run results before Phase 2

**Once approved, implementation will begin with Phase 1 (Changes #1-3).**

---

**End of CHANGE_PROPOSAL_v2.md**

**Next Steps** (upon approval):
1. Create `feature/v2-phase1-critical` branch
2. Implement Change #2 (scoring_utils.py)
3. Implement Change #1 (analyze_symbol.py)
4. Implement Change #3 (anti_jitter.py)
5. Run unit tests
6. Start 24h shadow run
7. Generate validation report
