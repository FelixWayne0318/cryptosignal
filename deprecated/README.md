# Deprecated Files Archive

> **⚠️ WARNING: These files are kept for historical reference only. DO NOT USE in production.**

---

## Pipeline Evolution History

This directory contains old versions of the analysis pipeline that have been superseded by the current v6.0 implementation.

### Archived Files

| File | Version | Description | Deprecated Date |
|------|---------|-------------|----------------|
| **analyze_symbol_v2.py** | v2.0 | 160-point weight system | 2025-10-30 |
| **analyze_symbol_v3.py** | v3.0 | Transition version with hybrid scoring | 2025-10-30 |
| **analyze_symbol_v22.py** | v2.2 | Microstructure factors enhancement | 2025-10-30 |
| **batch_scan.py** | v2.x | Old batch scanning (replaced by batch_scan_optimized) | 2025-10-30 |

---

## Why These Files Were Deprecated

### 1. analyze_symbol_v2.py (v2.0 - 160-point system)
- **Weight System**: Used 160-point total weight system
- **Factors**: 7-dimension system (T/M/C/S/V/O/F)
- **Replaced By**: v6.0 with 100% percentage-based weights and 10+1 dimensions

### 2. analyze_symbol_v3.py (v3.0 - Transition)
- **Purpose**: Experimental version testing new factor combinations
- **Status**: Never reached production
- **Replaced By**: Direct upgrade to v6.0

### 3. analyze_symbol_v22.py (v2.2 - Microstructure)
- **Features**: Added L/B/Q microstructure factors
- **Issue**: Circular self-import bug (line 11)
- **Replaced By**: v6.0 with proper factor integration

### 4. batch_scan.py (Old Batch Scanner)
- **Method**: Sequential processing with basic caching
- **Performance**: ~30-40 seconds for 200 symbols
- **Replaced By**: `batch_scan_optimized.py` (12-15 seconds, WebSocket caching)

---

## Current Production Files

**Use these instead:**

| Purpose | File | Version |
|---------|------|---------|
| Single Symbol Analysis | `ats_core/pipeline/analyze_symbol.py` | v6.0 |
| Batch Scanning | `ats_core/pipeline/batch_scan_optimized.py` | v6.0 |
| Main Entry Point | `scripts/realtime_signal_scanner.py` | v6.0 |

---

## Version History Overview

```
v2.0 (160-point) → v3.0 (hybrid) → v6.0 (100% system)
     ↓                                    ↑
   v2.2 (microstructure) ─────────────────┘
```

### Key Changes in v6.0

1. **Weight System**: 180/160-point → 100% percentage-based
2. **Factor Count**: 7 → 10+1 dimensions (T/M/C/S/V/O/L/B/Q/I + F)
3. **F Factor**: Now participates in scoring (10.0% weight) + extreme veto
4. **Prime Threshold**: 65 points → 35 points (adjusted for 100-base)
5. **Performance**: WebSocket caching, 0 API calls per scan

---

## If You Need Old Code

**For reference purposes only:**

```bash
# View old v2.0 implementation
cat deprecated/pipeline/analyze_symbol_v2.py

# View old batch scanner
cat deprecated/pipeline/batch_scan.py
```

**DO NOT import or use these files in new code!**

---

## Migration Guide

If you have code depending on old functions:

| Old Code (v2.x) | New Code (v6.0) |
|----------------|----------------|
| `from ats_core.pipeline.analyze_symbol_v2 import analyze_symbol_v2` | `from ats_core.pipeline.analyze_symbol import analyze_symbol` |
| `from ats_core.pipeline.batch_scan import batch_run_parallel` | `from ats_core.pipeline.batch_scan_optimized import batch_run` |
| `weights = {"T": 25, "M": 20, ...}  # 160 total` | `weights = {"T": 13.9, "M": 8.3, ...}  # 100% total` |

---

## Questions?

See the current documentation:
- [standards/SYSTEM_OVERVIEW.md](../standards/SYSTEM_OVERVIEW.md) - v6.0 system explanation
- [standards/ARCHITECTURE.md](../standards/ARCHITECTURE.md) - Technical architecture
- [standards/MODIFICATION_RULES.md](../standards/MODIFICATION_RULES.md) - What files to modify

---

**Archived**: 2025-10-30
**Version**: v6.0 cleanup
