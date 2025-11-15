# CryptoSignal v7.2 - Claude Project 导入指南

生成时间：2025-11-14

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 📋 导入策略
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 🎯 核心理念
- **核心文件**：必须完整导入Claude Project，需要深入理解和修改
- **接口文件**：只需要知道函数签名和返回值，无需导入完整代码
- **配置文件**：导入JSON配置文件，理解参数含义

### 📊 统计
- **仓库总计**：67 个Python文件，25,356 行代码，887.4KB
- **核心文件**：12 个文件，9,778 行代码，368.9KB
- **压缩率**：38.6% 的代码量，覆盖 100% 的功能理解

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## ⭐ 第一部分：核心文件（必须导入）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

这些文件是系统的骨架，必须完整理解：

### 核心配置

- `ats_core/cfg.py` (155 行, 5.6KB)
- `ats_core/config/anti_jitter_config.py` (288 行, 9.0KB)
- `ats_core/config/factor_config.py` (565 行, 16.9KB)
- `ats_core/config/threshold_config.py` (207 行, 7.0KB)

### 核心流程

- `ats_core/pipeline/analyze_symbol.py` (2045 行, 87.1KB)
- `ats_core/pipeline/analyze_symbol_v72.py` (893 行, 39.1KB)
- `ats_core/pipeline/batch_scan_optimized.py` (1253 行, 55.6KB)

### 核心输出

- `ats_core/outputs/telegram_fmt.py` (2648 行, 89.0KB)
- `ats_core/publishing/anti_jitter.py` (237 行, 9.1KB)

### 核心数据

- `ats_core/data/analysis_db.py` (1062 行, 36.7KB)
- `ats_core/data/trade_recorder.py` (409 行, 13.4KB)

### 核心工具

- `ats_core/logging.py` (16 行, 0.5KB)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 📚 第二部分：接口模块（只需要知道API）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

这些模块的实现细节可以不导入，只需要在Claude Project中记录接口规范：

### ANALYSIS 模块

**统计**：3 个文件，933 行代码，37.4KB

#### `ats_core/analysis/__init__.py`

（内部实现细节）

#### `ats_core/analysis/report_writer.py`

**主要API**：
- `class ReportWriter`
- `def get_report_writer()`
- `def write_scan_report(self, summary, detail, text_report)`
- `def write_setup_log(self, log_content)`
- `def write_scan_progress(self, progress_data)`
- ... 还有 1 个API

#### `ats_core/analysis/scan_statistics.py`

**主要API**：
- `class ScanStatistics`
- `def get_global_stats()`
- `def reset_global_stats()`
- `def reset(self)`
- `def add_symbol_result(self, symbol, result)`
- ... 还有 4 个API

### CALIBRATION 模块

**统计**：1 个文件，378 行代码，13.4KB

#### `ats_core/calibration/empirical_calibration.py`

**主要API**：
- `class EmpiricalCalibrator`
- `def record_signal_result(self, confidence, result, metadata)`
- `def get_calibrated_probability(self, confidence)`
- `def get_statistics(self)`
- `def reset_history(self)`

### EXECUTION 模块

**统计**：3 个文件，1,316 行代码，43.5KB

#### `ats_core/execution/__init__.py`

（内部实现细节）

#### `ats_core/execution/binance_futures_client.py`

**主要API**：
- `class BinanceFuturesClient`
- `def get_binance_client(config_path)`

#### `ats_core/execution/stop_loss_calculator.py`

**主要API**：
- `class StopLossResult`
- `class ThreeTierStopLoss`
- `def to_dict(self)`
- `def calculate_stop_loss(self, direction, current_price, highs, lows, orderbook, atr)`

### FACTORS_V2 模块

**统计**：3 个文件，772 行代码，26.0KB

#### `ats_core/factors_v2/__init__.py`

（内部实现细节）

#### `ats_core/factors_v2/basis_funding.py`

**主要API**：
- `def get_adaptive_basis_thresholds(basis_history, mode, min_data_points)`
- `def get_adaptive_funding_thresholds(funding_history, mode, min_data_points)`
- `def calculate_basis_funding(perp_price, spot_price, funding_rate, funding_history, basis_history, params)`

#### `ats_core/factors_v2/independence.py`

**主要API**：
- `def calculate_independence(alt_prices, btc_prices, eth_prices, params)`
- `def remove_outliers(returns_array)`

### FEATURES 模块

**统计**：18 个文件，5,292 行代码，180.5KB

#### `ats_core/features/accel.py`

**主要API**：
- `def score_accel(c, cvd_series, params)`

#### `ats_core/features/accumulation_detection.py`

**主要API**：
- `def detect_accumulation_v1(factors, meta, params)`
- `def detect_accumulation_v2(factors, meta, params)`
- `def detect_accumulation(factors, meta, version, params)`

#### `ats_core/features/cvd.py`

**主要API**：
- `def cvd_from_klines(klines, use_taker_buy, use_quote, filter_outliers, outlier_weight, expose_meta)`
- `def zscore_last(xs, window)`
- `def cvd_from_spot_klines(klines, use_quote)`
- `def cvd_combined(futures_klines, spot_klines, use_dynamic_weight, use_quote, min_quote_factor, min_quote_window, min_quote_fallback, max_discard_ratio, return_meta)`
- `def cvd_mix_with_oi_price(klines, oi_hist, spot_klines, use_quote, rolling_window, use_robust, use_strict_oi_align, oi_align_tolerance_ms, return_meta)`

... 还有 15 个文件

### MODULATORS 模块

**统计**：3 个文件，1,019 行代码，33.4KB

#### `ats_core/modulators/__init__.py`

（内部实现细节）

#### `ats_core/modulators/fi_modulators.py`

**主要API**：
- `class ModulatorParams`
- `class FIModulator`
- `def get_fi_modulator(params)`
- `def from_config(cls, config_dict)`
- `def normalize_g(self, x)`
- ... 还有 6 个API

#### `ats_core/modulators/modulator_chain.py`

**主要API**：
- `class ModulatorOutput`
- `class ModulatorChain`
- `def logistic(x, T)`
- `def calculate_EV(P, edge, cost)`
- `def to_dict(self)`
- ... 还有 1 个API

### SCORING 模块

**统计**：6 个文件，1,211 行代码，38.7KB

#### `ats_core/scoring/adaptive_weights.py`

**主要API**：
- `def get_regime_weights(market_regime, volatility)`
- `def blend_weights(regime_weights, base_weights, blend_ratio)`

#### `ats_core/scoring/factor_groups.py`

**主要API**：
- `def calculate_grouped_score(T, M, C, V, O, B, params)`
- `def compare_with_original(T, M, C, V, O, B, original_weights)`

#### `ats_core/scoring/probability.py`

**主要API**：
- `def map_probability(edge, prior_up, Q)`

... 还有 3 个文件

### SOURCES 模块

**统计**：4 个文件，881 行代码，26.5KB

#### `ats_core/sources/binance.py`

**主要API**：
- `def get_klines(symbol, interval, limit, start_time, end_time)`
- `def get_spot_klines(symbol, interval, limit, start_time, end_time)`
- `def get_open_interest_hist(symbol, period, limit)`
- `def get_funding_hist(symbol, limit, start_time, end_time)`
- `def get_orderbook_snapshot(symbol, limit)`
- ... 还有 8 个API

#### `ats_core/sources/binance_safe.py`

**主要API**：
- `class RateLimiter`
- `def get_klines(symbol, interval, limit, start_time, end_time)`
- `def get_open_interest_hist(symbol, period, limit)`
- `def get_funding_hist(symbol, limit, start_time, end_time)`
- `def get_ticker_24h(symbol)`
- ... 还有 3 个API

#### `ats_core/sources/klines.py`

**主要API**：
- `def klines_1h(symbol, limit)`
- `def klines_4h(symbol, limit)`
- `def klines_15m(symbol, limit)`
- `def split_ohlcv(rows)`

... 还有 1 个文件

### UTILS 模块

**统计**：6 个文件，1,757 行代码，52.4KB

#### `ats_core/utils/__init__.py`

（内部实现细节）

#### `ats_core/utils/cvd_utils.py`

**主要API**：
- `def align_oi_to_klines(oi_hist, klines)`
- `def compute_dynamic_min_quote(klines, window, factor, min_fallback)`
- `def align_klines_by_open_time(futures_klines, spot_klines, max_discard_ratio)`
- `def rolling_z(values, window, robust)`
- `def compute_cvd_delta(klines, use_quote, symbol, interval)`
- ... 还有 4 个API

#### `ats_core/utils/degradation.py`

**主要API**：
- `class DegradationLevel`
- `class DegradationResult`
- `class DegradationManager`
- `def create_degradation_metadata(reason, min_required, actual, confidence, additional)`
- `def calculate_confidence_from_data_ratio(actual, required, warning_threshold, degraded_threshold)`
- ... 还有 4 个API

... 还有 3 个文件

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 🔗 第三部分：模块接口规范
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

在Claude Project中，只需要记录这些模块的接口约定：

### 1. Features模块（因子计算）
```python
# 接口规范：所有因子计算函数返回 float 或 Dict[str, float]
from ats_core.features.trend import analyze_trend
from ats_core.features.momentum import calc_momentum
from ats_core.features.liquidity import calc_liquidity_score

# 示例：
trend_score = analyze_trend(klines)  # 返回 Dict[str, float]
momentum = calc_momentum(klines)      # 返回 float
```

### 2. Sources模块（数据源）
```python
# 接口规范：获取市场数据
from ats_core.sources.klines import get_klines
from ats_core.sources.oi import fetch_oi_history

# 示例：
klines = get_klines(symbol, interval, limit)  # 返回 List[Dict]
oi_data = fetch_oi_history(symbol)             # 返回 List[float]
```

### 3. Scoring模块（评分系统）
```python
# 接口规范：标准化和评分
from ats_core.scoring.scoring_utils import StandardizationChain

# 示例：
chain = StandardizationChain()
normalized = chain.standardize(value, method='robust')  # 返回 float
```

### 4. Factors_v2模块（v7.2因子）
```python
# 接口规范：v7.2版本的因子计算
from ats_core.factors_v2.funding_v2 import calc_F_v2

# 示例：
F_score = calc_F_v2(funding_rate, oi_change)  # 返回 float
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 🎯 第四部分：Claude Project 导入清单
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 必须导入的文件（按优先级）

#### 第一优先级：理解系统入口和主流程
```
scripts/realtime_signal_scanner.py   # 主入口
ats_core/pipeline/analyze_symbol.py  # 核心分析流程
ats_core/pipeline/analyze_symbol_v72.py  # v7.2增强
```

#### 第二优先级：理解配置和阈值
```
config/signal_thresholds.json        # 信号阈值配置
config/factor_weights.json           # 因子权重配置
ats_core/config/threshold_config.py  # 阈值读取
ats_core/config/factor_config.py     # 因子配置
```

#### 第三优先级：理解输出和发布
```
ats_core/outputs/telegram_fmt.py     # Telegram格式化
ats_core/publishing/anti_jitter.py   # 防抖动
```

#### 第四优先级：理解数据存储
```
ats_core/data/analysis_db.py         # 分析结果数据库
ats_core/data/trade_recorder.py      # 交易记录
```

### 只需要记录接口的模块

创建一个 `INTERFACES.md` 文件，记录以下模块的接口规范：

```markdown
# CryptoSignal 模块接口规范

## Features模块
- `analyze_trend(klines) -> Dict[str, float]`
- `calc_momentum(klines) -> float`
- `calc_liquidity_score(volume, trades) -> float`

## Sources模块
- `get_klines(symbol, interval, limit) -> List[Dict]`
- `fetch_oi_history(symbol) -> List[float]`

## Scoring模块
- `StandardizationChain.standardize(value, method) -> float`
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 🚀 第五部分：使用建议
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 在Claude Project中的工作流程

1. **导入核心文件**（约15个文件，3000-4000行代码）
   - 完整理解系统架构和主流程
   - 可以修改配置、阈值、流程逻辑

2. **创建接口文档** `INTERFACES.md`
   - 记录所有辅助模块的API
   - 无需导入实现细节（节省tokens）

3. **修改代码时**
   - 修改核心文件：直接在Claude Project中修改
   - 修改接口文件：回到仓库修改，然后更新 `INTERFACES.md`

4. **理解系统运行**
   - 主入口 → 批量扫描 → 单币分析 → v7.2增强 → 输出格式化
   - 配置层控制所有阈值和权重
   - 辅助模块提供计算能力（只需要知道输入输出）

### 优势

- ✅ **Token使用减少 61%**
- ✅ **聚焦核心逻辑**，避免陷入实现细节
- ✅ **快速定位问题**，所有关键代码都在Claude Project中
- ✅ **接口清晰**，模块之间的调用关系一目了然

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 📝 附录：完整文件清单
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 核心文件详细列表

- `ats_core/logging.py` - 核心工具 (16 行, 0.5KB)
- `ats_core/data/analysis_db.py` - 核心数据 (1062 行, 36.7KB)
- `ats_core/data/trade_recorder.py` - 核心数据 (409 行, 13.4KB)
- `ats_core/pipeline/analyze_symbol.py` - 核心流程 (2045 行, 87.1KB)
- `ats_core/pipeline/analyze_symbol_v72.py` - 核心流程 (893 行, 39.1KB)
- `ats_core/pipeline/batch_scan_optimized.py` - 核心流程 (1253 行, 55.6KB)
- `ats_core/outputs/telegram_fmt.py` - 核心输出 (2648 行, 89.0KB)
- `ats_core/publishing/anti_jitter.py` - 核心输出 (237 行, 9.1KB)
- `ats_core/cfg.py` - 核心配置 (155 行, 5.6KB)
- `ats_core/config/anti_jitter_config.py` - 核心配置 (288 行, 9.0KB)
- `ats_core/config/factor_config.py` - 核心配置 (565 行, 16.9KB)
- `ats_core/config/threshold_config.py` - 核心配置 (207 行, 7.0KB)

**核心文件总计**：12 个文件，9,778 行代码
