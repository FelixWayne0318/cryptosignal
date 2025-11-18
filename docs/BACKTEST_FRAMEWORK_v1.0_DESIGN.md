# Backtest Framework v1.0 - Requirements & Design

**Created**: 2025-11-18
**Author**: Claude (Following SYSTEM_ENHANCEMENT_STANDARD.md v3.3.0)
**Priority**: P1 (High)
**Version**: v1.0
**Standard**: SYSTEM_ENHANCEMENT_STANDARD.md v3.3.0
**Related Docs**:
- FOUR_STEP_IMPLEMENTATION_GUIDE.md
- FOUR_STEP_SYSTEM_VERIFICATION_REPORT.md
- BACKTEST_READINESS_ASSESSMENT.md

---

## 1. Problem Statement

### 1.1 Current Situation
CryptoSignal v7.4.0 has successfully implemented the revolutionary four-step decision system:
- **Step1**: Direction confirmation (A-layer + I-factor + BTC alignment)
- **Step2**: Timing judgment (Enhanced F v2: flow_momentum - price_momentum)
- **Step3**: Risk management (Entry/SL/TP price calculation)
- **Step4**: Quality control (4 gates: volume, noise, strength, contradiction)

**Verification Status** (from FOUR_STEP_SYSTEM_VERIFICATION_REPORT.md):
- ✅ Implementation completeness: 98%
- ✅ Configuration enabled: `four_step_system.enabled: true`
- ✅ Pipeline integration: Complete
- ✅ Data persistence: 80 historical signals in SQLite

### 1.2 Gap Analysis
**Missing capability**: Production-grade backtest framework to:
1. Validate four-step system performance on historical data
2. Measure quantitative metrics (win rate, RR ratio, Sharpe, drawdown)
3. Identify parameter optimization opportunities
4. Compare four-step system vs legacy system
5. Build confidence before live trading deployment

**Current backtest readiness** (from BACKTEST_READINESS_ASSESSMENT.md):
- Four-step system: 100% ✅
- Historical data API: 100% ✅ (Binance klines available)
- Factor calculation: 100% ✅ (analyze_symbol independent)
- **Backtest framework: 0%** ❌ (needs development)
- **Performance metrics: 30%** ⚠️ (needs systematization)

### 1.3 Why This Matters (P1 Priority)
**Risk without backtest**:
- Blind deployment without historical validation
- Unknown win rate and risk-reward characteristics
- Unoptimized parameters (potentially suboptimal performance)
- No benchmark for future improvements

**Value with backtest**:
- Data-driven validation of system effectiveness
- Quantified performance metrics for decision making
- Parameter sensitivity analysis
- Continuous improvement feedback loop

---

## 2. Goals & Success Criteria

### 2.1 Primary Goals

**Goal 1: Historical Data Replay**
- Execute four-step decision system on 3-12 months historical data
- Support configurable time range and symbol list
- Simulate real-time execution constraints (no future data leakage)

**Goal 2: Comprehensive Metrics**
- Signal-level metrics: Win rate, average RR, max drawdown
- Step-level metrics: Step1-4 pass rates, bottleneck identification
- Portfolio-level metrics: Sharpe ratio, max concurrent positions
- Distribution analysis: PnL histogram, holding time distribution

**Goal 3: Zero Hardcoding**
- All parameters from `config/params.json`
- Following §6.1 Base + Range pattern for algorithm curves
- Following §6.2 Function signature evolution for backward compatibility
- Following §6.4 Segmented logic configuration for if-elif-else branches

**Goal 4: Production-Grade Quality**
- Complete documentation (code + user guide)
- Unit tests for core logic
- Integration tests for end-to-end workflow
- Performance optimization (target: <5 min for 3 months data)

### 2.2 Success Criteria

**Functional Requirements**:
- ✅ Backtest execution completes without errors
- ✅ Generates ≥50 signals on 3-month EUR data (validation threshold)
- ✅ Metrics match manual calculation (±2% tolerance)
- ✅ Configuration changes don't require code modification

**Performance Requirements**:
- ✅ Execution time <5 minutes for 3 months, single symbol
- ✅ Execution time <30 minutes for 3 months, 20 symbols
- ✅ Memory usage <2GB for 12 months data

**Quality Requirements**:
- ✅ Zero hardcoded thresholds or magic numbers
- ✅ All functions have type hints and docstrings
- ✅ Test coverage >80% for core logic
- ✅ Documentation includes examples and troubleshooting

### 2.3 Non-Goals (Out of Scope for v1.0)

**Deferred to future versions**:
- ❌ Multi-threaded parallel backtesting (v1.1)
- ❌ Real-time backtest visualization dashboard (v1.2)
- ❌ Automated parameter optimization (grid search) (v1.3)
- ❌ Walk-forward analysis (v2.0)
- ❌ Machine learning integration (v2.0)

**Rationale**: Focus on core functionality first, iterate based on user feedback.

---

## 3. Technical Approach

### 3.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  Backtest Framework v1.0                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │   Data       │───▶│   Backtest   │───▶│  Performance │ │
│  │   Loader     │    │   Engine     │    │   Metrics    │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│        │                     │                    │        │
│        ▼                     ▼                    ▼        │
│  Historical Data       Signal Records       JSON Report   │
│  (Binance API)         (Simulation)         (+ CSV)       │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│          Configuration: config/params.json                  │
│          (Zero Hardcoding - All Parameters Configurable)    │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Module Design

#### 3.2.1 HistoricalDataLoader (`ats_core/backtest/data_loader.py`)

**Responsibility**: Fetch and cache historical market data from Binance API.

**Key Functions**:
```python
class HistoricalDataLoader:
    def __init__(self, config: Dict):
        """
        Args:
            config: Backtest data_loader configuration from params.json
                - default_interval: str (e.g., "1h")
                - api_retry_count: int (e.g., 3)
                - api_retry_delay_base: float (e.g., 2.0)
                - cache_enabled: bool
                - cache_dir: str
        """

    def load_klines(self, symbol: str, start_time: int, end_time: int,
                    interval: str = None) -> List[Dict]:
        """
        Load historical klines for a symbol.

        Args:
            symbol: Trading pair (e.g., "ETHUSDT")
            start_time: Unix timestamp (milliseconds)
            end_time: Unix timestamp (milliseconds)
            interval: Candle interval (default from config)

        Returns:
            List of kline dicts with keys: timestamp, open, high, low,
            close, volume, quote_volume, trades, taker_buy_base,
            taker_buy_quote
        """

    def load_btc_klines(self, start_time: int, end_time: int) -> List[Dict]:
        """Load BTC klines for Step1 BTC alignment check."""

    def load_funding_rate_history(self, symbol: str, start_time: int,
                                   end_time: int) -> List[Dict]:
        """Load historical funding rates (optional for future enhancement)."""

    def load_oi_history(self, symbol: str, start_time: int,
                        end_time: int) -> List[Dict]:
        """Load historical open interest (optional for future enhancement)."""
```

**Configuration Pattern** (§5 Zero Hardcoding):
```python
# ✅ Correct: Read from config with defaults
interval = config.get("default_interval", "1h")
retry_count = config.get("api_retry_count", 3)
retry_delay_base = config.get("api_retry_delay_base", 2.0)

# ❌ Wrong: Magic number hardcoding
interval = "1h"  # Hardcoded!
retry_count = 3  # Hardcoded!
```

**Caching Strategy** (Performance Optimization):
- Cache raw klines to `data/backtest_cache/{symbol}_{start}_{end}_{interval}.json`
- LRU eviction policy (configurable max cache size)
- Cache invalidation: Manual clear command or TTL-based

#### 3.2.2 BacktestEngine (`ats_core/backtest/engine.py`)

**Responsibility**: Orchestrate backtest execution with time-loop simulation.

**Key Functions**:
```python
class BacktestEngine:
    def __init__(self, config: Dict, data_loader: HistoricalDataLoader):
        """
        Args:
            config: Backtest engine configuration from params.json
                - batch_size: int (process N symbols concurrently)
                - progress_log_interval: int (log every N iterations)
                - signal_cooldown_hours: int (Anti-Jitter compliance)
        """

    def run(self, symbols: List[str], start_time: int, end_time: int) -> BacktestResult:
        """
        Execute backtest on historical data.

        Algorithm:
        1. For each timestamp in [start_time, end_time] (hourly step):
            2. For each symbol:
                3. Fetch historical klines up to current timestamp
                4. Calculate factor scores via analyze_symbol()
                5. Run four_step_system.run_four_step_decision()
                6. If signal generated:
                    7. Simulate order execution (entry price ± slippage)
                    8. Track position lifecycle (SL/TP monitoring)
                    9. Record signal outcome
        10. Return BacktestResult with all signals and metadata

        Returns:
            BacktestResult: Dataclass containing:
                - signals: List[SimulatedSignal]
                - metadata: Dict (execution time, total iterations, etc.)
        """

    def _simulate_order_execution(self, signal: Dict, klines: List[Dict]) -> SimulatedSignal:
        """
        Simulate order fill with slippage.

        Args:
            signal: Raw signal from four_step_system
            klines: Future klines for SL/TP monitoring

        Returns:
            SimulatedSignal with actual entry/exit prices and PnL
        """

    def _check_stop_loss_hit(self, position: SimulatedSignal, kline: Dict) -> bool:
        """Check if SL triggered in this candle."""

    def _check_take_profit_hit(self, position: SimulatedSignal, kline: Dict) -> Tuple[bool, int]:
        """Check if TP1 or TP2 triggered. Returns (hit, tp_level)."""
```

**Anti-Future Data Leakage** (Critical):
```python
# ✅ Correct: Only use data up to current_timestamp
historical_data = data_loader.load_klines(
    symbol, start_time, current_timestamp, interval
)
factor_scores = analyze_symbol(symbol, historical_data)

# ❌ Wrong: Using future data (lookahead bias)
all_data = data_loader.load_klines(symbol, start_time, end_time, interval)
factor_scores = analyze_symbol(symbol, all_data)  # Knows future!
```

**Position Lifecycle Simulation**:
```
Entry → Monitor every candle → Exit (SL hit / TP hit / Manual close)
         ├─ Low ≤ SL → Exit at SL price
         ├─ High ≥ TP1 → Exit at TP1 (50% position)
         └─ High ≥ TP2 → Exit at TP2 (remaining 50%)
```

#### 3.2.3 BacktestMetrics (`ats_core/backtest/metrics.py`)

**Responsibility**: Calculate comprehensive performance metrics.

**Key Functions**:
```python
class BacktestMetrics:
    def __init__(self, config: Dict):
        """
        Args:
            config: Backtest metrics configuration from params.json
                - min_signals_for_stats: int (e.g., 10)
                - confidence_level: float (e.g., 0.95 for 95% CI)
                - risk_free_rate: float (e.g., 0.03 for 3% annual)
        """

    def calculate_all_metrics(self, backtest_result: BacktestResult) -> MetricsReport:
        """
        Calculate comprehensive metrics.

        Returns:
            MetricsReport dataclass with:
                - signal_metrics: SignalMetrics
                - step_metrics: StepMetrics
                - portfolio_metrics: PortfolioMetrics
                - distribution_metrics: DistributionMetrics
        """

    def calculate_signal_metrics(self, signals: List[SimulatedSignal]) -> SignalMetrics:
        """
        Signal-level performance metrics.

        Returns:
            SignalMetrics:
                - total_signals: int
                - win_rate: float (%)
                - avg_rr_ratio: float (average reward/risk)
                - avg_pnl_percent: float (%)
                - max_pnl_percent: float (%)
                - min_pnl_percent: float (%)
                - median_pnl_percent: float (%)
                - max_consecutive_wins: int
                - max_consecutive_losses: int
                - avg_holding_hours: float
        """

    def calculate_step_metrics(self, signals: List[SimulatedSignal]) -> StepMetrics:
        """
        Four-step bottleneck analysis.

        Returns:
            StepMetrics:
                - step1_pass_rate: float (%)
                - step2_pass_rate: float (%)
                - step3_pass_rate: float (%)
                - step4_pass_rate: float (%)
                - final_pass_rate: float (%)
                - bottleneck_step: int (1-4, lowest pass rate)
        """

    def calculate_portfolio_metrics(self, signals: List[SimulatedSignal]) -> PortfolioMetrics:
        """
        Portfolio-level risk metrics.

        Returns:
            PortfolioMetrics:
                - sharpe_ratio: float
                - sortino_ratio: float
                - max_drawdown_percent: float (%)
                - max_concurrent_positions: int
                - avg_trades_per_day: float
                - profit_factor: float (gross_profit / gross_loss)
        """

    def calculate_distribution_metrics(self, signals: List[SimulatedSignal]) -> DistributionMetrics:
        """
        Statistical distribution analysis.

        Returns:
            DistributionMetrics:
                - pnl_histogram: Dict[str, int] (bins → count)
                - holding_time_histogram: Dict[str, int]
                - win_rate_by_direction: Dict[str, float] (long/short)
                - avg_pnl_by_step1_confidence: Dict[str, float]
        """

    def generate_report(self, metrics_report: MetricsReport,
                       output_format: str = "json") -> str:
        """
        Generate human-readable report.

        Args:
            output_format: "json" | "markdown" | "csv"

        Returns:
            Formatted report string
        """
```

**Metrics Calculation Example** (§6.1 Base + Range Pattern):
```python
# ✅ Correct: Configurable confidence level for statistical tests
confidence_level = config.get("confidence_level", 0.95)
risk_free_rate = config.get("risk_free_rate", 0.03)

sharpe_ratio = (mean_return - risk_free_rate) / std_return * sqrt(252)

# ❌ Wrong: Hardcoded risk-free rate
sharpe_ratio = (mean_return - 0.03) / std_return * sqrt(252)  # 0.03 is magic number!
```

### 3.3 Data Structures

#### 3.3.1 SimulatedSignal (Dataclass)
```python
@dataclass
class SimulatedSignal:
    """Backtest signal with execution simulation."""
    # Original signal data
    symbol: str
    timestamp: int  # Entry timestamp (ms)
    side: str  # "long" | "short"
    entry_price_recommended: float  # From Step3
    stop_loss_recommended: float
    take_profit_1_recommended: float
    take_profit_2_recommended: float

    # Simulation results
    entry_price_actual: float  # After slippage
    stop_loss_actual: float
    take_profit_1_actual: float
    take_profit_2_actual: float

    exit_time: int  # Exit timestamp (ms)
    exit_price: float
    exit_reason: str  # "SL_HIT" | "TP1_HIT" | "TP2_HIT" | "MANUAL_CLOSE"

    pnl_percent: float  # (exit_price - entry_price) / entry_price * 100
    pnl_usdt: float  # Assuming 100 USDT position size

    # Four-step metadata
    step1_result: Dict  # Step1 output
    step2_result: Dict
    step3_result: Dict
    step4_result: Dict

    holding_hours: float  # (exit_time - timestamp) / 3600000
```

#### 3.3.2 BacktestResult (Dataclass)
```python
@dataclass
class BacktestResult:
    """Complete backtest execution result."""
    signals: List[SimulatedSignal]
    metadata: Dict[str, Any]  # {
        # "start_time": int,
        # "end_time": int,
        # "symbols": List[str],
        # "total_iterations": int,
        # "execution_time_seconds": float,
        # "config_snapshot": Dict
        # }
```

#### 3.3.3 MetricsReport (Dataclass)
```python
@dataclass
class MetricsReport:
    """Comprehensive performance metrics."""
    signal_metrics: SignalMetrics
    step_metrics: StepMetrics
    portfolio_metrics: PortfolioMetrics
    distribution_metrics: DistributionMetrics
    timestamp_generated: int
```

### 3.4 CLI Interface

**Script**: `scripts/backtest_four_step.py`

**Usage**:
```bash
# Basic usage: 3 months backtest on ETH
python scripts/backtest_four_step.py \
    --symbols ETHUSDT \
    --start 2024-08-01 \
    --end 2024-11-01 \
    --output reports/backtest_eth_3m.json

# Multi-symbol backtest
python scripts/backtest_four_step.py \
    --symbols ETHUSDT,BTCUSDT,SOLUSDT \
    --start 2024-01-01 \
    --end 2024-06-01 \
    --output reports/backtest_multi_6m.json

# Custom config override
python scripts/backtest_four_step.py \
    --symbols ETHUSDT \
    --start 2024-08-01 \
    --end 2024-11-01 \
    --config-override '{"data_loader": {"cache_enabled": false}}' \
    --output reports/backtest_nocache.json

# Generate markdown report
python scripts/backtest_four_step.py \
    --symbols ETHUSDT \
    --start 2024-08-01 \
    --end 2024-11-01 \
    --output reports/backtest_eth.json \
    --report-format markdown \
    --report-output reports/backtest_eth.md
```

**Script Structure**:
```python
import argparse
from datetime import datetime
from ats_core.backtest import HistoricalDataLoader, BacktestEngine, BacktestMetrics
from ats_core.utils.config_loader import load_config

def main():
    parser = argparse.ArgumentParser(description="CryptoSignal Backtest v1.0")
    parser.add_argument("--symbols", required=True, help="Comma-separated symbols")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--config-override", help="JSON config override")
    parser.add_argument("--report-format", choices=["json", "markdown", "csv"], default="json")
    parser.add_argument("--report-output", help="Report output path (optional)")

    args = parser.parse_args()

    # Load configuration
    config = load_config()
    backtest_config = config.get("backtest", {})

    # Initialize components
    data_loader = HistoricalDataLoader(backtest_config.get("data_loader", {}))
    engine = BacktestEngine(backtest_config.get("engine", {}), data_loader)
    metrics = BacktestMetrics(backtest_config.get("metrics", {}))

    # Run backtest
    symbols = args.symbols.split(",")
    start_ts = int(datetime.strptime(args.start, "%Y-%m-%d").timestamp() * 1000)
    end_ts = int(datetime.strptime(args.end, "%Y-%m-%d").timestamp() * 1000)

    print(f"Starting backtest: {symbols} from {args.start} to {args.end}")
    result = engine.run(symbols, start_ts, end_ts)

    # Calculate metrics
    print(f"Calculating metrics for {len(result.signals)} signals...")
    metrics_report = metrics.calculate_all_metrics(result)

    # Save results
    with open(args.output, "w") as f:
        json.dump(result.to_dict(), f, indent=2)
    print(f"✅ Results saved to {args.output}")

    # Generate report
    if args.report_output:
        report = metrics.generate_report(metrics_report, args.report_format)
        with open(args.report_output, "w") as f:
            f.write(report)
        print(f"✅ Report saved to {args.report_output}")

    # Print summary
    print("\n" + "=" * 60)
    print("BACKTEST SUMMARY")
    print("=" * 60)
    print(f"Total Signals: {metrics_report.signal_metrics.total_signals}")
    print(f"Win Rate: {metrics_report.signal_metrics.win_rate:.2f}%")
    print(f"Avg RR Ratio: {metrics_report.signal_metrics.avg_rr_ratio:.2f}")
    print(f"Sharpe Ratio: {metrics_report.portfolio_metrics.sharpe_ratio:.2f}")
    print(f"Max Drawdown: {metrics_report.portfolio_metrics.max_drawdown_percent:.2f}%")
    print("=" * 60)

if __name__ == "__main__":
    main()
```

---

## 4. Configuration Design

### 4.1 Configuration Structure (`config/params.json`)

**New top-level block** (following zero-hardcode principle):

```json
{
  "backtest": {
    "_comment": "Backtest Framework v1.0 - 零硬编码历史数据回测系统",
    "_version": "v1.0",
    "_description": "配置驱动的回测框架，所有参数可调，支持多符号、多时间段回测",

    "data_loader": {
      "_comment": "历史数据加载器配置",
      "default_interval": "1h",
      "api_retry_count": 3,
      "api_retry_delay_base": 2.0,
      "api_retry_delay_range": 2.0,
      "api_timeout_seconds": 30,
      "cache_enabled": true,
      "cache_dir": "data/backtest_cache",
      "cache_max_size_mb": 500,
      "cache_ttl_hours": 168
    },

    "engine": {
      "_comment": "回测引擎配置",
      "batch_size": 1,
      "progress_log_interval": 100,
      "signal_cooldown_hours": 2,
      "slippage_percent": 0.1,
      "position_size_usdt": 100,
      "max_holding_hours": 168,
      "enable_anti_jitter": true
    },

    "metrics": {
      "_comment": "性能评估配置",
      "min_signals_for_stats": 10,
      "confidence_level": 0.95,
      "risk_free_rate": 0.03,
      "pnl_histogram_bins": [-10, -5, -2, 0, 2, 5, 10, 20],
      "holding_time_bins_hours": [1, 6, 12, 24, 48, 72, 168]
    },

    "output": {
      "_comment": "输出格式配置",
      "default_format": "json",
      "json_indent": 2,
      "markdown_include_charts": false,
      "csv_delimiter": ","
    }
  }
}
```

### 4.2 Configuration Pattern Examples

#### 4.2.1 §6.1 Base + Range Pattern (Algorithm Curves)

**Slippage Simulation**:
```python
# config/params.json
{
  "engine": {
    "slippage_percent": 0.1,  # Base: 0.1%
    "slippage_range": 0.05    # Range: ±0.05%
  }
}

# ats_core/backtest/engine.py
slippage_base = config.get("slippage_percent", 0.1)
slippage_range = config.get("slippage_range", 0.05)
# Randomize slippage within range for realism
import random
actual_slippage = slippage_base + random.uniform(-slippage_range, slippage_range)
entry_price_actual = entry_price_recommended * (1 + actual_slippage / 100)
```

#### 4.2.2 §6.2 Function Signature Evolution (Backward Compatibility)

**New optional parameters with defaults**:
```python
# v1.0 signature
def run(self, symbols: List[str], start_time: int, end_time: int) -> BacktestResult:
    ...

# v1.1 enhanced signature (backward compatible)
def run(
    self,
    symbols: List[str],
    start_time: int,
    end_time: int,
    interval: str = None,  # ✅ New param with default (v1.1)
    parallel: bool = False  # ✅ New param with default (v1.1)
) -> BacktestResult:
    """
    Args:
        interval: Candle interval (v1.1新增，默认从config读取)
        parallel: Enable parallel execution (v1.1新增，默认False)
    """
    if interval is None:
        interval = self.config.get("default_interval", "1h")
    ...
```

#### 4.2.3 §6.4 Segmented Logic Configuration (If-Elif-Else Branches)

**Exit reason classification**:
```python
# config/params.json
{
  "engine": {
    "exit_classification": {
      "sl_hit": {"priority": 1, "label": "SL_HIT"},
      "tp1_hit": {"priority": 2, "label": "TP1_HIT"},
      "tp2_hit": {"priority": 3, "label": "TP2_HIT"},
      "max_holding_exceeded": {"priority": 4, "label": "TIMEOUT"},
      "manual_close": {"priority": 5, "label": "MANUAL"}
    }
  }
}

# ats_core/backtest/engine.py
exit_config = config.get("exit_classification", {})

if self._check_stop_loss_hit(position, kline):
    exit_reason = exit_config["sl_hit"]["label"]
elif tp_hit, tp_level = self._check_take_profit_hit(position, kline):
    exit_reason = exit_config[f"tp{tp_level}_hit"]["label"]
elif holding_hours > max_holding:
    exit_reason = exit_config["max_holding_exceeded"]["label"]
else:
    exit_reason = exit_config["manual_close"]["label"]
```

---

## 5. File Modification Plan

**Following strict order** (SYSTEM_ENHANCEMENT_STANDARD.md §3):

### Phase 2: Core Implementation

**Step 1: Configuration** (Priority 1 - Highest)
```
File: config/params.json
Action: Add "backtest" configuration block
Lines: ~100 new lines
Dependencies: None
```

**Step 2: Core Algorithms** (Priority 2)
```
Files:
1. ats_core/backtest/__init__.py
   - Module initialization
   - Export public classes

2. ats_core/backtest/data_loader.py
   - HistoricalDataLoader class
   - Binance API integration
   - Caching logic
   Lines: ~300
   Dependencies: config/params.json

3. ats_core/backtest/engine.py
   - BacktestEngine class
   - Time-loop simulation
   - Position lifecycle tracking
   Lines: ~400
   Dependencies: data_loader.py, config/params.json

4. ats_core/backtest/metrics.py
   - BacktestMetrics class
   - All metrics calculation functions
   - Report generation
   Lines: ~350
   Dependencies: config/params.json
```

**Step 3: Pipeline Integration** (Priority 3)
```
File: ats_core/backtest/__init__.py (update)
Action: Export all public interfaces
Lines: ~20
Dependencies: data_loader.py, engine.py, metrics.py
```

**Step 4: Output/CLI** (Priority 4 - Lowest)
```
File: scripts/backtest_four_step.py
Action: Create CLI script
Lines: ~150
Dependencies: ats_core/backtest/*
```

### Phase 3: Testing

```
Files:
1. tests/test_backtest_data_loader.py (~150 lines)
2. tests/test_backtest_engine.py (~200 lines)
3. tests/test_backtest_metrics.py (~150 lines)
4. tests/test_backtest_integration.py (~100 lines)
```

### Phase 4: Documentation

```
Files:
1. docs/BACKTEST_FRAMEWORK_USER_GUIDE.md (~400 lines)
   - Installation
   - Usage examples
   - Configuration reference
   - Troubleshooting

2. docs/SESSION_STATE.md (update)
   - Record backtest development session
   - Technical decisions made
   - Lessons learned
```

**Total Lines of Code**: ~2,320 lines

---

## 6. Testing Strategy

### 6.1 Unit Tests

**Test Coverage Target**: >80% for core logic

**Test Categories**:

**1. Data Loader Tests** (`tests/test_backtest_data_loader.py`)
```python
def test_load_klines_basic():
    """Test basic klines loading."""

def test_load_klines_with_cache():
    """Test caching mechanism."""

def test_load_klines_api_retry():
    """Test API retry logic with exponential backoff."""

def test_load_btc_klines():
    """Test BTC klines for Step1 BTC alignment."""
```

**2. Engine Tests** (`tests/test_backtest_engine.py`)
```python
def test_backtest_single_symbol():
    """Test backtest on single symbol."""

def test_position_lifecycle_sl_hit():
    """Test SL hit simulation."""

def test_position_lifecycle_tp_hit():
    """Test TP1/TP2 hit simulation."""

def test_anti_jitter_cooldown():
    """Test 2-hour cooldown enforcement."""

def test_no_future_data_leakage():
    """Critical: Verify no lookahead bias."""
```

**3. Metrics Tests** (`tests/test_backtest_metrics.py`)
```python
def test_win_rate_calculation():
    """Test win rate accuracy."""

def test_sharpe_ratio_calculation():
    """Test Sharpe ratio calculation."""

def test_max_drawdown_calculation():
    """Test max drawdown calculation."""

def test_step_pass_rates():
    """Test four-step pass rate calculation."""
```

**4. Integration Tests** (`tests/test_backtest_integration.py`)
```python
def test_end_to_end_backtest():
    """Test complete backtest workflow."""

def test_cli_script_execution():
    """Test CLI script with mock data."""

def test_config_override():
    """Test configuration override mechanism."""
```

### 6.2 Configuration Tests

**Test zero-hardcode compliance**:
```python
def test_all_thresholds_from_config():
    """Scan code for hardcoded magic numbers."""
    # Use AST parsing to detect literal numbers
    # Whitelist: 0, 1, 100, 1000 (common multipliers)
    # Fail if any suspicious literals found
```

### 6.3 Logic Tests

**Test edge cases**:
- Empty signal list (no trades during period)
- Single signal (insufficient for statistics)
- All wins / all losses (extreme scenarios)
- Concurrent positions (max limit enforcement)
- Exact SL/TP hit (boundary conditions)

### 6.4 Import Tests

**Test module imports**:
```python
def test_import_data_loader():
    from ats_core.backtest import HistoricalDataLoader

def test_import_engine():
    from ats_core.backtest import BacktestEngine

def test_import_metrics():
    from ats_core.backtest import BacktestMetrics
```

---

## 7. Performance Optimization Strategy

### 7.1 Bottleneck Analysis

**Expected bottlenecks**:
1. **Binance API calls**: 1 request per symbol per hour → 2160 requests for 3 months
2. **Factor calculation**: `analyze_symbol()` called 2160 times
3. **Four-step execution**: `run_four_step_decision()` called 2160 times

### 7.2 Optimization Techniques

**1. Caching** (Highest Impact)
- Cache raw klines to disk (LRU eviction)
- Cache factor calculation results (optional, v1.1)
- Estimated speedup: 10-50x for repeated backtests

**2. Batch API Requests** (Medium Impact)
- Binance allows 500 klines per request
- Batch multiple hours into single request
- Estimated speedup: 2-3x

**3. Vectorized Calculations** (Medium Impact)
- Use NumPy for metrics calculation
- Pandas for DataFrame operations
- Estimated speedup: 2-5x vs pure Python loops

**4. Parallel Execution** (Deferred to v1.1)
- Multi-threading for independent symbols
- Process pool for CPU-intensive calculations
- Estimated speedup: 2-4x on multi-core systems

### 7.3 Performance Targets

**Baseline (no optimization)**:
- 3 months, 1 symbol: ~10 minutes
- 3 months, 10 symbols: ~100 minutes

**With caching + batching**:
- 3 months, 1 symbol: <5 minutes ✅
- 3 months, 10 symbols: <30 minutes ✅

---

## 8. Risk Assessment & Mitigation

### 8.1 Technical Risks

**Risk 1: Future Data Leakage** (Severity: Critical)
- **Description**: Using future data in factor calculation (lookahead bias)
- **Impact**: Inflated backtest performance, false confidence
- **Mitigation**:
  - Strict time-loop simulation (only data up to current timestamp)
  - Unit test: `test_no_future_data_leakage()`
  - Code review: Manual verification of data slicing logic

**Risk 2: Binance API Rate Limits** (Severity: High)
- **Description**: 1200 requests/minute weight limit, IP ban if exceeded
- **Impact**: Backtest failure, temporary API access loss
- **Mitigation**:
  - Exponential backoff retry (2s → 4s → 8s → 16s)
  - Request rate throttling (configurable delay between requests)
  - Caching to minimize redundant requests

**Risk 3: Configuration Complexity** (Severity: Medium)
- **Description**: 30+ configuration parameters, easy to misconfigure
- **Impact**: Incorrect backtest results, user confusion
- **Mitigation**:
  - Comprehensive default values for all parameters
  - Configuration validation at startup (type checks, range checks)
  - User guide with recommended configurations

**Risk 4: Slippage Simulation Inaccuracy** (Severity: Medium)
- **Description**: Fixed percentage slippage may not reflect real market conditions
- **Impact**: Backtest performance differs from live trading
- **Mitigation**:
  - Conservative slippage assumptions (0.1% default)
  - Sensitivity analysis: Test with 0.05%, 0.1%, 0.2% slippage
  - Document limitations in user guide

### 8.2 Project Risks

**Risk 5: Scope Creep** (Severity: Medium)
- **Description**: Adding features beyond v1.0 scope (visualization, optimization)
- **Impact**: Delayed delivery, reduced quality
- **Mitigation**:
  - Strict adherence to "Non-Goals" section
  - Feature requests logged for v1.1+
  - Regular scope review with stakeholder

**Risk 6: Backward Incompatibility** (Severity: Low)
- **Description**: Changes break existing four-step system
- **Impact**: Production system disruption
- **Mitigation**:
  - Backtest as separate module (no modifications to existing code)
  - Integration tests verify four-step system still works
  - Version pinning in configuration

---

## 9. Timeline & Milestones

### 9.1 Development Phases

**Phase 1: Requirements & Design** (Current)
- Duration: 0.5 day
- Deliverable: This document (BACKTEST_FRAMEWORK_v1.0_DESIGN.md)
- Status: ✅ Complete

**Phase 2: Core Implementation**
- Duration: 1.5 days
- Deliverables:
  - config/params.json (backtest block)
  - ats_core/backtest/*.py (data_loader, engine, metrics)
  - scripts/backtest_four_step.py

**Phase 3: Testing & Validation**
- Duration: 0.5 day
- Deliverables:
  - tests/test_backtest_*.py
  - Test execution report
  - Bug fixes

**Phase 4: Documentation**
- Duration: 0.3 day
- Deliverables:
  - BACKTEST_FRAMEWORK_USER_GUIDE.md
  - SESSION_STATE.md update
  - Code comments and docstrings

**Phase 5: Git Commit & Push**
- Duration: 0.2 day
- Deliverables:
  - Git commit with standardized message
  - Push to remote branch

**Total Duration**: 3 days

### 9.2 Milestones

- [x] M1: Requirements analysis complete (2025-11-18)
- [ ] M2: Configuration complete (2025-11-18)
- [ ] M3: Data loader complete (2025-11-18)
- [ ] M4: Engine complete (2025-11-19)
- [ ] M5: Metrics complete (2025-11-19)
- [ ] M6: CLI script complete (2025-11-19)
- [ ] M7: All tests passing (2025-11-19)
- [ ] M8: Documentation complete (2025-11-19)
- [ ] M9: Code committed & pushed (2025-11-20)

---

## 10. Success Validation Plan

### 10.1 Validation Criteria

**Functional Validation**:
1. Run backtest on ETHUSDT, 2024-08-01 to 2024-11-01 (3 months)
2. Verify ≥50 signals generated (validates system activity)
3. Manually verify 5 random signals:
   - Entry/SL/TP prices realistic
   - Exit reason correct (SL/TP hit matches price action)
   - PnL calculation accurate (±0.1%)
4. Compare win rate with manual calculation (±2% tolerance)

**Performance Validation**:
1. Measure execution time (must be <5 minutes for 3 months)
2. Monitor memory usage (must be <2GB)
3. Verify cache hit rate >80% on repeated runs

**Quality Validation**:
1. Zero hardcoded magic numbers (AST scan test passes)
2. All functions have type hints and docstrings (100% coverage)
3. Test coverage >80% (pytest-cov report)
4. Documentation includes ≥3 usage examples

### 10.2 Acceptance Test

**Test Scenario**: Three-month ETHUSDT backtest
```bash
python scripts/backtest_four_step.py \
    --symbols ETHUSDT \
    --start 2024-08-01 \
    --end 2024-11-01 \
    --output reports/backtest_acceptance_test.json \
    --report-format markdown \
    --report-output reports/backtest_acceptance_test.md
```

**Expected Results**:
- ✅ Execution completes without errors
- ✅ Execution time <5 minutes
- ✅ Total signals ≥50
- ✅ Win rate between 30-70% (reasonable range)
- ✅ Avg RR ratio >1.0 (validates risk management)
- ✅ Max drawdown <30% (validates risk control)
- ✅ Markdown report generated with all sections

### 10.3 User Acceptance

**Stakeholder Review**:
1. Review backtest report for reasonableness
2. Verify metrics align with expectations
3. Confirm configuration flexibility meets needs
4. Approve for production use

---

## 11. Future Enhancements (v1.1+)

### v1.1 (Performance Optimization)
- Parallel execution (multi-threading for symbols)
- Factor calculation caching
- Database backend for large-scale backtests

### v1.2 (Visualization)
- Interactive backtest dashboard (Plotly/Streamlit)
- Equity curve chart
- Drawdown chart
- PnL distribution histogram

### v1.3 (Parameter Optimization)
- Grid search for optimal parameters
- Genetic algorithm optimization
- Bayesian optimization

### v2.0 (Advanced Analysis)
- Walk-forward analysis
- Monte Carlo simulation
- Regime-based analysis (bull/bear/sideways)
- Machine learning integration (predict win rate)

---

## 12. References

**Internal Documents**:
- FOUR_STEP_IMPLEMENTATION_GUIDE.md (Four-step system specification)
- FOUR_STEP_SYSTEM_VERIFICATION_REPORT.md (Implementation verification)
- BACKTEST_READINESS_ASSESSMENT.md (Current capabilities assessment)
- SYSTEM_ENHANCEMENT_STANDARD.md v3.3.0 (Development standard)

**External References**:
- Binance API Documentation: https://binance-docs.github.io/apidocs/
- Sharpe Ratio: https://en.wikipedia.org/wiki/Sharpe_ratio
- Sortino Ratio: https://en.wikipedia.org/wiki/Sortino_ratio
- Max Drawdown: https://en.wikipedia.org/wiki/Drawdown_(economics)

---

## Appendix A: Configuration Parameter Reference

**(Full parameter table with descriptions, defaults, and valid ranges)**

| Parameter | Type | Default | Valid Range | Description |
|-----------|------|---------|-------------|-------------|
| `data_loader.default_interval` | str | "1h" | "1m", "5m", "15m", "1h", "4h", "1d" | Default candle interval |
| `data_loader.api_retry_count` | int | 3 | 1-10 | Max API retry attempts |
| `data_loader.api_retry_delay_base` | float | 2.0 | 0.5-10.0 | Retry delay base (seconds) |
| `data_loader.cache_enabled` | bool | true | true/false | Enable klines caching |
| `data_loader.cache_ttl_hours` | int | 168 | 1-720 | Cache TTL (hours) |
| `engine.slippage_percent` | float | 0.1 | 0.0-1.0 | Slippage simulation (%) |
| `engine.position_size_usdt` | float | 100 | 10-10000 | Position size for PnL calc |
| `engine.signal_cooldown_hours` | int | 2 | 0-24 | Anti-Jitter cooldown (hours) |
| `metrics.min_signals_for_stats` | int | 10 | 1-100 | Min signals for statistics |
| `metrics.confidence_level` | float | 0.95 | 0.90-0.99 | Statistical confidence level |
| `metrics.risk_free_rate` | float | 0.03 | 0.0-0.1 | Risk-free rate for Sharpe |

---

## Appendix B: Code Quality Checklist

**Pre-commit checklist** (before Phase 5):

- [ ] All configuration parameters read from `config/params.json` (zero hardcoding)
- [ ] All functions have type hints (`def func(x: int) -> str:`)
- [ ] All public functions have docstrings (Google style)
- [ ] No print() statements (use logging module)
- [ ] No commented-out code blocks
- [ ] Variable names descriptive (no single-letter except loop counters)
- [ ] Import order: stdlib → third-party → local (PEP 8)
- [ ] Line length ≤100 characters (PEP 8 relaxed)
- [ ] Tests pass: `pytest tests/test_backtest_*.py`
- [ ] Coverage >80%: `pytest --cov=ats_core/backtest tests/`
- [ ] Type check pass: `mypy ats_core/backtest/`
- [ ] Linting pass: `pylint ats_core/backtest/` (score >8.0)

---

**END OF DOCUMENT**

**Next Step**: Proceed to Phase 2 - Core Implementation (Step 1: Configuration)
