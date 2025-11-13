# Claude Project 接口规范文档

**文档版本**: v1.0
**创建时间**: 2025-11-13
**系统版本**: CryptoSignal v7.2.36
**目的**: 明确Project中代码与仓库代码的接口边界和调用关系

---

## 📋 目录

1. [接口概述](#1-接口概述)
2. [导入范围](#2-导入范围)
3. [主要接口](#3-主要接口)
4. [数据结构](#4-数据结构)
5. [依赖关系](#5-依赖关系)
6. [使用示例](#6-使用示例)
7. [注意事项](#7-注意事项)

---

## 1. 接口概述

### 1.1 Project的定位

本Project导入了**从数据获取到信号输出的完整数据流核心文件**，包括：
- ✅ 数据获取和预处理
- ✅ 因子计算（7个核心因子）
- ✅ 评分和分组
- ✅ 四道闸门
- ✅ 统计校准
- ✅ v7.2集成引擎
- ✅ 配置和工具函数

### 1.2 接口边界

```
┌──────────────────────────────────────────────────────────┐
│ 仓库代码（不在Project中）                                  │
├──────────────────────────────────────────────────────────┤
│ • setup.sh - 启动脚本                                     │
│ • scripts/realtime_signal_scanner.py - 实时扫描器        │
│ • scripts/batch_scan_optimized.py - 批量扫描             │
└──────────────────────────────────────────────────────────┘
                         ↓ 调用
┌──────────────────────────────────────────────────────────┐
│ Project代码（在Project中）- 核心接口                       │
├──────────────────────────────────────────────────────────┤
│ ★ analyze_with_v72_enhancements()  - v7.2分析引擎主入口  │
│   ├─ UnifiedDataManager - 数据管理接口                   │
│   ├─ 7个因子计算函数                                      │
│   ├─ factor_groups.py - 评分分组                         │
│   ├─ integrated_gates.py - 四道闸门                      │
│   └─ empirical_calibration.py - 统计校准                 │
└──────────────────────────────────────────────────────────┘
                         ↓ 返回
┌──────────────────────────────────────────────────────────┐
│ 仓库代码（不在Project中）                                  │
├──────────────────────────────────────────────────────────┤
│ • outputs/telegram_fmt.py - Telegram格式化（可选在Project）│
│ • publishing/ - 信号发布                                  │
└──────────────────────────────────────────────────────────┘
```

---

## 2. 导入范围

### 2.1 完整导入清单

#### ✅ 在Project中（可以直接修改）

**数据流核心**（~19个文件）:
```
ats_core/sources/
├─ binance_futures_client.py    - Binance期货API
├─ binance.py                    - 通用Binance接口
└─ binance_safe.py               - 安全封装

ats_core/data/
├─ unified_data_manager.py       - 统一数据管理器
├─ realtime_kline_cache.py       - K线缓存
└─ quality.py                    - 数据质量检测

ats_core/preprocessing/
└─ standardization.py            - 数据标准化

ats_core/features/
├─ fund_leading.py               - F因子v2
├─ trend.py                      - T因子
├─ momentum.py                   - M因子
├─ cvd.py                        - C因子
├─ volume.py                     - V因子
├─ open_interest.py              - O因子
└─ basis.py                      - B因子

ats_core/scoring/
├─ factor_groups.py              - 因子分组
└─ integrated_score.py           - 综合评分

ats_core/gates/
└─ integrated_gates.py           - 四道闸门

ats_core/calibration/
└─ empirical_calibration.py      - 统计校准

ats_core/pipeline/
└─ analyze_symbol_v72.py         - v7.2集成引擎
```

**核心依赖**（~15个文件）:
```
ats_core/config/
├─ threshold_config.py           - 阈值配置管理
├─ factor_config.py              - 因子配置管理 ★
└─ anti_jitter_config.py         - 防抖动配置

ats_core/utils/
├─ math_utils.py                 - 数学工具
├─ cvd_utils.py                  - CVD工具
├─ factor_normalizer.py          - 因子标准化
└─ outlier_detection.py          - 异常值检测

ats_core/features/
└─ scoring_utils.py              - 因子评分工具 ★

ats_core/scoring/
└─ expected_value.py             - 期望值计算 ★

ats_core/execution/
└─ metrics_estimator.py          - 执行指标估算 ★

ats_core/modulators/
└─ fi_modulators.py              - 资金流调节器 ★

ats_core/
└─ logging.py                    - 日志模块

config/
└─ signal_thresholds.json        - 阈值配置文件
```

**标注说明**：★ 为依赖关系检查后新增的必需文件

#### ❌ 在仓库中（不在Project，需要时粘贴或说明）

**调用方**:
```
setup.sh
scripts/realtime_signal_scanner.py
scripts/init_databases.py
ats_core/pipeline/batch_scan_optimized.py
```

**输出层**（可选导入）:
```
ats_core/outputs/telegram_fmt.py   - 如果太大(89K)可排除
```

**其他模块**:
```
ats_core/execution/              - 执行层
ats_core/publishing/             - 发布层
ats_core/analysis/               - 分析工具
ats_core/monitoring/             - 监控
tests/, diagnose/                - 测试和诊断
```

---

## 3. 主要接口

### 3.1 主入口接口：v7.2分析引擎

**文件**: `ats_core/pipeline/analyze_symbol_v72.py`

**主函数**: `analyze_with_v72_enhancements()`

**完整签名**:
```python
def analyze_with_v72_enhancements(
    result: Dict[str, Any],           # 基础分析结果
    symbol: str,                       # 交易对，如"BTCUSDT"
    klines: pd.DataFrame,              # K线数据
    oi_data: Dict[str, Any],           # 持仓量数据
    cvd_series: pd.Series,             # CVD数据序列
    atr_now: float,                    # 当前ATR值
    config: ThresholdConfig = None     # 配置对象（可选）
) -> Dict[str, Any]:
    """
    v7.2增强分析主入口函数

    功能：
    1. 计算F因子v2（资金流领先）
    2. 应用因子分组（TC/VOM/B）
    3. 四道闸门过滤
    4. 统计校准

    返回：
    {
        # 原result中的所有字段，plus:
        'F_factor': float,              # F因子v2得分
        'F_raw': float,                 # F因子原始值
        'TC_group': float,              # TC组得分（T+C）
        'VOM_group': float,             # VOM组得分（V+O+M）
        'B_group': float,               # B组得分
        'weighted_score': float,        # 加权总分
        'gate1_passed': bool,           # Gate1数据质量
        'gate2_passed': bool,           # Gate2资金支持
        'gate3_passed': bool,           # Gate3 EV计算
        'gate4_passed': bool,           # Gate4概率评估
        'gate_passed': bool,            # 是否通过所有闸门
        'calibrated_prob': float,       # 校准后的概率
        'calibrated_confidence': float, # 校准后的置信度
        ...
    }
    """
```

**调用示例**（在仓库代码中）:
```python
# 在 scripts/realtime_signal_scanner.py 中
from ats_core.pipeline.analyze_symbol_v72 import analyze_with_v72_enhancements

# 获取基础数据
klines = data_manager.get_klines(symbol, "1h", 200)
oi_data = data_manager.get_open_interest(symbol)
cvd_series = data_manager.get_cvd(symbol, 200)

# 调用v7.2分析引擎（Project中的代码）
result_v72 = analyze_with_v72_enhancements(
    result=base_result,
    symbol=symbol,
    klines=klines,
    oi_data=oi_data,
    cvd_series=cvd_series,
    atr_now=atr
)

# 使用返回的信号
if result_v72['gate_passed']:
    send_telegram_notification(result_v72)
```

---

### 3.2 数据管理接口

**文件**: `ats_core/data/unified_data_manager.py`

**主类**: `UnifiedDataManager`

**关键方法**:
```python
class UnifiedDataManager:
    """统一数据管理器"""

    def get_klines(self, symbol: str, interval: str = "1h",
                   limit: int = 200) -> pd.DataFrame:
        """
        获取K线数据

        返回DataFrame包含列：
        ['timestamp', 'open', 'high', 'low', 'close', 'volume', ...]
        """

    def get_open_interest(self, symbol: str) -> Dict[str, Any]:
        """
        获取持仓量数据

        返回：
        {
            'openInterest': float,
            'sumOpenInterest': float,
            'timestamp': int
        }
        """

    def get_cvd(self, symbol: str, lookback: int = 200) -> pd.Series:
        """
        获取CVD数据序列

        返回：pd.Series with index=timestamp, values=cvd
        """

    def get_funding_rate(self, symbol: str) -> float:
        """获取资金费率"""

    def get_basis(self, symbol: str) -> float:
        """获取基差"""
```

**使用说明**:
- 这个类在Project中，可以修改数据获取逻辑
- 调用方在 `scripts/realtime_signal_scanner.py`（仓库中）
- 修改后需要重启系统才能生效

---

### 3.3 配置管理接口

**文件**: `ats_core/config/threshold_config.py`

**主类**: `ThresholdConfig`

**关键方法**:
```python
class ThresholdConfig:
    """阈值配置管理器"""

    def __init__(self, config_file: str = "config/signal_thresholds.json"):
        """从配置文件加载阈值"""

    def get_mature_threshold(self, key: str, default=None):
        """
        获取成熟币阈值

        示例：
        config.get_mature_threshold('confidence_min', 0.50)
        -> 从signal_thresholds.json中读取
        """

    def get_newcoin_threshold(self, phase: str, key: str, default=None):
        """
        获取新币阈值

        phase: 'ultra', 'phaseA', 'phaseB'
        key: 'confidence_min', 'edge_min', ...
        """

    def get_gate_threshold(self, gate_name: str, key: str, default=None):
        """
        获取闸门阈值

        gate_name: 'gate2_fund_support', 'gate3_ev', ...
        key: 'F_min', 'EV_min', ...
        """
```

**配置文件**: `config/signal_thresholds.json`

**使用说明**:
- 修改阈值：只需编辑 `signal_thresholds.json`
- 代码会自动读取最新配置
- 严禁在代码中硬编码阈值

---

### 3.4 因子计算接口

**文件**: `ats_core/features/fund_leading.py`

**主函数**: `calculate_fund_leading_v2()`

**完整签名**:
```python
def calculate_fund_leading_v2(
    klines: pd.DataFrame,
    oi_data: Dict,
    cvd_series: pd.Series,
    config: Dict = None
) -> Tuple[float, Dict]:
    """
    计算F因子v2（资金流领先）

    返回：
    (
        F_factor,  # 最终F因子得分
        details    # 详细信息字典
    )
    """
```

**类似的其他因子**:
- `calculate_trend()` - T因子
- `calculate_momentum()` - M因子
- `calculate_cvd_factor()` - C因子
- `calculate_volume()` - V因子
- `calculate_open_interest()` - O因子
- `calculate_basis()` - B因子

**使用说明**:
- 这些函数都在Project中，可以直接修改
- 修改后在Project中测试，然后同步到GitHub
- 在Termius上拉取并重启系统

---

## 4. 数据结构

### 4.1 分析结果结构

**类型**: `Dict[str, Any]`

**基础字段**（来自基础分析）:
```python
{
    'symbol': str,              # 交易对
    'price': float,             # 当前价格
    'confidence': float,        # 置信度
    'direction': str,           # 方向 'long'/'short'
    'edge': float,              # 优势
    'T': float,                 # T因子得分
    'M': float,                 # M因子得分
    'C': float,                 # C因子得分
    'V': float,                 # V因子得分
    'O': float,                 # O因子得分
    'B': float,                 # B因子得分
    ...
}
```

**v7.2增强字段**（analyze_with_v72_enhancements添加）:
```python
{
    # F因子v2
    'F_factor': float,          # F因子得分 [-100, 100]
    'F_raw': float,             # F因子原始值
    'fund_momentum': float,     # 资金动量
    'price_momentum': float,    # 价格动量

    # 因子分组
    'TC_group': float,          # TC组得分 (T+C)
    'VOM_group': float,         # VOM组得分 (V+O+M)
    'B_group': float,           # B组得分
    'weighted_score': float,    # 加权总分

    # 四道闸门
    'gate1_passed': bool,       # Gate1: 数据质量
    'gate2_passed': bool,       # Gate2: 资金支持 (F >= -10)
    'gate3_passed': bool,       # Gate3: EV计算 (EV >= 0.015)
    'gate4_passed': bool,       # Gate4: 概率评估 (P >= 0.50)
    'gate_passed': bool,        # 是否通过所有闸门
    'gate_reject_reason': str,  # 拒绝原因（如果未通过）

    # 统计校准
    'calibrated_prob': float,   # 校准后的概率
    'calibrated_confidence': float,  # 校准后的置信度
    'calibration_method': str,  # 校准方法

    # 元数据
    'v72_version': str,         # v7.2版本号
    'analysis_time': str,       # 分析时间
    ...
}
```

---

### 4.2 K线数据结构

**类型**: `pd.DataFrame`

**必需列**:
```python
DataFrame columns:
[
    'timestamp',    # int64, Unix timestamp (ms)
    'open',         # float, 开盘价
    'high',         # float, 最高价
    'low',          # float, 最低价
    'close',        # float, 收盘价
    'volume',       # float, 成交量
    'quote_volume', # float, 成交额（可选）
]

Index: RangeIndex or timestamp作为index
Shape: (200, 6) 典型情况
```

---

### 4.3 持仓量数据结构

**类型**: `Dict[str, Any]`

**必需字段**:
```python
{
    'openInterest': float,      # 当前持仓量
    'sumOpenInterest': float,   # 累计持仓量
    'timestamp': int,           # Unix timestamp (ms)
    'symbol': str               # 交易对（可选）
}
```

---

### 4.4 CVD数据结构

**类型**: `pd.Series`

**结构**:
```python
pd.Series(
    index=timestamp,   # Unix timestamp (ms)
    values=cvd_value,  # CVD累计值
    dtype=float
)

Length: 200 (典型情况)
```

---

## 5. 依赖关系

### 5.1 Project内部依赖（完整版）

```
analyze_symbol_v72.py (主入口)
  ├─> features/fund_leading.py
  │     ├─> features/scoring_utils.py ★（新增依赖）
  │     ├─> config/factor_config.py ★（新增依赖）
  │     ├─> utils/math_utils.py
  │     └─> utils/cvd_utils.py
  │
  ├─> features/trend.py
  ├─> features/momentum.py
  ├─> features/cvd.py
  │     └─> utils/cvd_utils.py
  ├─> features/volume.py
  ├─> features/open_interest.py
  ├─> features/basis.py
  │
  ├─> scoring/factor_groups.py
  │     ├─> config/threshold_config.py
  │     └─> utils/factor_normalizer.py
  │
  ├─> gates/integrated_gates.py
  │     ├─> data/quality.py
  │     ├─> scoring/expected_value.py ★（新增依赖）
  │     ├─> execution/metrics_estimator.py ★（新增依赖）
  │     ├─> modulators/fi_modulators.py ★（新增依赖）
  │     └─> config/threshold_config.py
  │
  ├─> calibration/empirical_calibration.py
  │
  └─> preprocessing/standardization.py
        └─> utils/outlier_detection.py
```

**新增依赖说明**（★标记）:
1. **features/scoring_utils.py** (4.5K) - 因子评分工具，被fund_leading.py导入
2. **config/factor_config.py** (17K) - 因子配置管理，被fund_leading.py导入
3. **scoring/expected_value.py** (13K) - 期望值计算，被integrated_gates.py导入
4. **execution/metrics_estimator.py** (12K) - 执行指标估算，被integrated_gates.py导入
5. **modulators/fi_modulators.py** (12K) - 资金流调节器，被integrated_gates.py导入

**依赖规则**:
- ✅ Project中的模块可以互相导入
- ✅ 所有依赖都在Project中
- ✅ 没有循环依赖
- ✅ 所有新增依赖都已验证（见CLAUDE_PROJECT_DEPENDENCY_CHECK.md）

---

### 5.2 与仓库代码的依赖

```
仓库代码 → Project代码（调用关系）
─────────────────────────────────

scripts/realtime_signal_scanner.py
  ├─> data/unified_data_manager.py (Project)
  └─> pipeline/analyze_symbol_v72.py (Project)

pipeline/batch_scan_optimized.py (仓库)
  └─> pipeline/analyze_symbol_v72.py (Project)

outputs/telegram_fmt.py (可选在Project)
  └─> 被 realtime_signal_scanner.py 调用
```

**接口规则**:
- ✅ 仓库代码可以导入Project中的模块
- ✅ Project代码**不应该**导入仓库中的模块（除非明确文档化）
- ✅ 接口清晰：主入口是 `analyze_with_v72_enhancements()`

---

### 5.3 配置文件依赖

```
代码 → 配置文件
─────────────

所有需要阈值的模块 → config/signal_thresholds.json
  ├─> threshold_config.py (加载配置)
  ├─> factor_groups.py (权重配置)
  ├─> integrated_gates.py (闸门阈值)
  └─> empirical_calibration.py (校准参数)
```

**配置规则**:
- ✅ 修改配置文件后，Project代码自动使用新配置
- ✅ 不需要修改代码，只需修改JSON
- ❌ 严禁在代码中硬编码阈值

---

## 6. 使用示例

### 6.1 场景1：修改F因子计算逻辑

**需求**: 优化F因子v2的fund_momentum计算，调整OI/VOL/CVD权重

**步骤**:

1. **在Project中查看现有实现**:
```
"请查看 ats_core/features/fund_leading.py 的实现，
特别是fund_momentum的计算逻辑。

当前的权重配置是什么？"
```

2. **分析并提出优化方案**:
```
"根据现有逻辑，我想让CVD的权重从30%提高到40%，
OI的权重从40%降低到30%。

请帮我修改代码并确保权重总和=100%。"
```

3. **修改代码**（Claude在Project中修改）:
```python
# fund_leading.py
fund_momentum = (
    0.30 * oi_score +      # OI权重: 40% -> 30%
    0.30 * vol_score +     # VOL权重不变
    0.40 * cvd_score       # CVD权重: 30% -> 40%
)
```

4. **验证修改**:
```
"请确认修改后的权重：
- OI: 30%
- VOL: 30%
- CVD: 40%
总和: 100%"
```

5. **同步到GitHub**:
```bash
git pull
git add ats_core/features/fund_leading.py
git commit -m "feat: 优化F因子v2 CVD权重从30%到40%"
git push
```

6. **在Termius上测试**:
```bash
ssh user@server
cd ~/cryptosignal
./setup.sh  # 拉取最新代码并重启
tail -f ~/cryptosignal_*.log
```

---

### 6.2 场景2：调整闸门阈值

**需求**: Gate2的F_min从-10调整到-5

**步骤**:

1. **在Project中查看闸门逻辑**:
```
"请查看 ats_core/gates/integrated_gates.py 中Gate2的实现，
以及 config/signal_thresholds.json 中的F_min配置。"
```

2. **修改配置文件**:
```json
// config/signal_thresholds.json
{
  "v72闸门阈值": {
    "gate2_fund_support": {
      "F_min": -5  // 从-10改为-5
    }
  }
}
```

3. **验证修改**:
```
"请确认Gate2现在的F_min阈值是-5。"
```

4. **同步并测试**（同上）

---

### 6.3 场景3：添加新因子

**需求**: 新增L因子（流动性因子）

**步骤**:

1. **参考现有因子结构**:
```
"请查看 ats_core/features/fund_leading.py 的实现，
作为参考，创建新的 ats_core/features/liquidity.py。"
```

2. **创建新因子文件**（Claude在Project中创建）:
```python
# ats_core/features/liquidity.py
def calculate_liquidity(klines, orderbook_data, config=None):
    """
    计算L因子（流动性因子）
    """
    # 实现逻辑
    ...
    return L_factor, details
```

3. **集成到因子分组**:
```
"请修改 ats_core/scoring/factor_groups.py，
将新的L因子集成进去，权重设为5%。"
```

4. **更新配置文件**:
```json
// config/signal_thresholds.json
{
  "因子权重": {
    "L_weight": 0.05
  }
}
```

5. **更新v7.2引擎**:
```
"请修改 ats_core/pipeline/analyze_symbol_v72.py，
添加对L因子的调用。"
```

---

### 6.4 场景4：追踪完整数据流

**需求**: 理解从数据获取到信号输出的完整流程

**步骤**:

1. **追踪数据流**:
```
"请从数据获取开始，追踪一次完整的信号生成流程：

1. data/unified_data_manager.py - 数据获取
2. preprocessing/standardization.py - 数据预处理
3. features/*.py - 7个因子计算
4. scoring/factor_groups.py - 因子分组评分
5. gates/integrated_gates.py - 四道闸门过滤
6. calibration/empirical_calibration.py - 统计校准
7. pipeline/analyze_symbol_v72.py - v7.2集成

每一步的输入输出是什么？"
```

2. **验证理解**:
```
"请用一个具体例子（如BTCUSDT），
展示数据在每个环节如何变化。"
```

---

## 7. 注意事项

### 7.1 接口边界

✅ **Project中的代码**:
- 可以直接修改
- 可以添加新函数/类
- 可以调整逻辑
- 修改后需要同步到GitHub

❌ **仓库中的代码**（不在Project）:
- 不能直接修改
- 需要时可以粘贴到对话中
- 或者在仓库中手动修改

---

### 7.2 依赖管理

✅ **Project内部依赖**:
- 所有依赖都在Project中
- 可以自由导入和使用

⚠️ **仓库依赖**:
- 如果Project代码需要导入仓库中的模块
- 必须在本文档中明确说明
- 或者将该模块也导入Project

---

### 7.3 配置管理

✅ **推荐做法**:
- 阈值配置在 `signal_thresholds.json`
- 代码中使用 `ThresholdConfig` 读取
- 修改配置后自动生效

❌ **禁止做法**:
- 在代码中硬编码阈值
- 在多个地方重复定义同一阈值
- 不使用配置管理器直接读JSON

---

### 7.4 测试验证

**修改Project代码后的验证流程**:

1. **Project中验证**:
   - 确认修改符合逻辑
   - 检查语法错误
   - 验证依赖关系

2. **同步到GitHub**:
   ```bash
   git pull
   git add [修改的文件]
   git commit -m "..."
   git push
   ```

3. **Termius上测试**:
   ```bash
   ./setup.sh    # 拉取并重启
   tail -f *.log # 查看日志
   ```

4. **验证结果**:
   - 查看信号生成是否正常
   - 检查日志是否有错误
   - 验证修改是否生效

---

### 7.5 可能遗漏的依赖

**检查清单**:

- [ ] 类型定义文件（如 `types.py`, `models.py`）
- [ ] 常量定义（如 `constants.py`）
- [ ] 枚举类型（如 `enums.py`）
- [ ] 异常类（如 `exceptions.py`）
- [ ] 数据类（如 `dataclasses`）
- [ ] 所有 `__init__.py` 文件
- [ ] 测试fixtures（如果需要测试）
- [ ] 辅助配置文件（如 `factor_weights.json`）

**如果发现遗漏**:
1. 在本文档中添加说明
2. 考虑是否需要导入Project
3. 或在使用时明确文档化

---

## 8. 版本历史

| 版本 | 日期 | 修改内容 |
|------|------|---------|
| v1.0 | 2025-11-13 | 初始版本 |

---

## 9. 联系与反馈

**遇到问题**:
1. 检查本文档的接口说明
2. 查看 `CLAUDE_PROJECT_CONTEXT.md` 了解系统状态
3. 参考 `standards/SYSTEM_ENHANCEMENT_STANDARD.md` 开发规范

**需要更新本文档**:
- 添加新接口时更新第3节
- 添加新数据结构时更新第4节
- 发现新依赖时更新第5节

---

**文档维护**: 随代码更新同步维护
**最后更新**: 2025-11-13
**下次审查**: 每次重大功能更新后
