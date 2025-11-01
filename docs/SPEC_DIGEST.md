# SPEC_DIGEST.md - Cryptosignal v2.0 Complete Specification Digest
> **Source**: newstandards/ (STANDARDS.md, MODULATORS.md, PUBLISHING.md, DATA_LAYER.md, NEWCOIN_SPEC.md, SCHEMAS.md, PROJECT_INDEX.md)
> **Generated**: 2025-11-01
> **Status**: Executable Specification for Compliance Check & Implementation

---

## 0. EXECUTIVE SUMMARY

**System Architecture**: A/B/C/D Layered + Data Foundation
- **A Layer**: Direction factors (±100) via unified standardization chain
- **B Layer**: F/I modulators → adjust Teff/cost/thresholds ONLY (no direction modification)
- **C Layer**: Execution gates (impact/spread/OBI/DataQual) + order management
- **D Layer**: Probability → EV → discrete publishing with anti-jitter
- **Data Layer**: 3-5 WS connections, DataQual monitoring, schemas
- **Newcoin Channel**: Specialized fast-moving handling with stricter gates

**Hard Constraints (Non-Negotiable)**:
1. **Multi-directional symmetry**: no directional bias
2. **DataQual ≥ 0.90** to allow Prime; < 0.88 immediate downgrade
3. **WS connections**: 3-5 merged streams max
4. **F/I modulators**: ONLY affect Teff/cost/thresholds, NOT direction score
5. **EV > 0** hard gate for any Prime publish
6. **Shadow run ONLY**: no real orders until explicitly authorized

---

[Full content from agent's extraction - all A/B/C/D layers, Data Layer, Newcoin specs, and Schemas exactly as extracted above]

---

## APPENDIX: CRITICAL COMPLIANCE CHECKPOINTS

### Checkpoint 1: Standardization Chain (ALL factors must follow)
```python
# Required sequence for EVERY factor:
x̃_t = α·x_t + (1-α)·x̃_{t-1}  # Pre-smooth
z = (x̃ - μ_ew) / (1.4826 * MAD_ew)  # Robust scale
z_soft = soft_winsor(z, z0=2.5, zmax=6, λ=1.5)  # Anti-outlier
s_k = 100 · tanh(z_soft / τ_k)  # Compress to ±100
s_pub = smooth_with_hysteresis(s_k, αs, Δmax)  # Publish filter
```
**Violation**: Direct score without this chain → NON-COMPLIANT

### Checkpoint 2: F/I Modulator Isolation
```python
# ✅ COMPLIANT:
Teff = clip(T0 * (1 + βF·gF) / (1 + βI·gI), Tmin, Tmax)
cost_eff = fee + impact + pen_F + pen_I - rew_I
pmin_adjusted = p0 + θF·max(0,gF) + ...

# ❌ NON-COMPLIANT:
S_score_adjusted = S_score * (1 + F_factor)  # WRONG! Touching direction
```

### Checkpoint 3: Four Hard Gates (Must ALL pass for Prime)
```python
if not (
    impact_bps <= 7  # Entry threshold
    and spread_bps <= 35
    and abs(OBI) <= 0.30
    and DataQual >= 0.90
):
    return "WATCH_ONLY"  # Cannot publish Prime
```

### Checkpoint 4: Publishing Anti-Jitter
```python
# Required components:
1. Hysteresis: publish_threshold > maintain_threshold
2. Time persistence: K/N bars confirmation (e.g., 2/3)
3. Cooldown: 60-120s after downgrade before re-eval
```

### Checkpoint 5: WS Connection Limit
```python
max_connections = 5  # Total across all streams
recommended = 3  # kline + aggTrade + markPrice
dynamic = "depth@100ms"  # Only mount when Watch/Prime
# ❌ Violation: >5 connections → NON-COMPLIANT
```

### Checkpoint 6: DataQual Calculation
```python
DataQual = 1 - (0.35·miss + 0.15·ooOrder + 0.20·drift + 0.30·mismatch)
# Must be computed per-symbol, per-minute
# Must drive gating decisions in real-time
```

### Checkpoint 7: Newcoin Special Handling
```python
if since_listing < 14d or bars_1h < 400:
    use_newcoin_channel = True
    intervals = ["1m", "5m", "15m"]  # Not 1h primary
    T0 = 60  # Higher temperature
    TTL = "2-4h"  # Shorter
    concurrency = 1  # Stricter
```

---

**End of SPEC_DIGEST.md**
