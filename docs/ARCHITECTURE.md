# 系统架构说明

> **CryptoSignal v6.0 技术架构详解**

---

## 📐 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│  scripts/realtime_signal_scanner.py (主文件入口)            │
│  - 命令行参数解析                                           │
│  - Telegram配置加载                                         │
│  - 定期/单次扫描控制                                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│  ats_core/pipeline/batch_scan_optimized.py                  │
│  OptimizedBatchScanner (批量扫描器)                         │
│  - WebSocket K线缓存管理                                    │
│  - 200个币种并发分析                                        │
│  - Prime信号过滤                                            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│  ats_core/pipeline/analyze_symbol.py                        │
│  单币种完整分析管道                                         │
│  - 数据获取（K线、OI、订单簿、资金费率）                   │
│  - 10+1维因子计算                                           │
│  - 自适应权重混合                                           │
│  - 加权评分 + 概率映射                                      │
│  - Prime判定                                                │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         ↓                       ↓
┌────────────────────┐  ┌────────────────────┐
│  因子计算层         │  │  评分系统层         │
│                    │  │                    │
│  Layer 1: 价格行为  │  │  scorecard.py      │
│  - T (trend)       │  │  - 加权平均        │
│  - M (momentum)    │  │  - 归一化          │
│  - S (structure)   │  │                    │
│  - V (volume)      │  │  adaptive_weights  │
│                    │  │  - 市场状态检测    │
│  Layer 2: 资金流    │  │  - 动态权重调整    │
│  - C (cvd)         │  │                    │
│  - O (oi)          │  │  probability_v2    │
│  - F (fund_lead)   │  │  - Sigmoid映射     │
│                    │  │  - 温度自适应      │
│  Layer 3: 微观结构  │  └────────────────────┘
│  - L (liquidity)   │
│  - B (basis)       │
│  - Q (liquidation) │
│                    │
│  Layer 4: 市场环境  │
│  - I (independence)│
└────────────────────┘
         │
         ↓
┌─────────────────────────────────────────────────────────────┐
│  ats_core/outputs/telegram_fmt.py                           │
│  - 格式化Telegram消息                                       │
│  - 10维因子可视化                                           │
│  - 价格信息展示                                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│  Telegram API                                               │
│  - 发送Prime信号到电报群                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 数据流详解

### 1. 数据获取层

```
Binance API (REST + WebSocket)
       │
       ├─→ sources/binance.py (API封装)
       │       │
       │       ├─→ get_klines() - K线数据
       │       ├─→ get_open_interest_hist() - OI数据
       │       ├─→ get_spot_klines() - 现货K线
       │       └─→ get_funding_rate() - 资金费率
       │
       └─→ data/realtime_kline_cache.py (WebSocket缓存)
               │
               └─→ RealtimeKlineCache
                   - 维护140个币种的实时K线缓存
                   - 自动订阅WebSocket流
                   - 0次REST API调用
```

### 2. 因子计算层

```
analyze_symbol.py
       │
       ├─→ Layer 1: 价格行为层
       │   ├─→ features/trend.py → T因子
       │   ├─→ features/momentum.py → M因子
       │   ├─→ features/structure_sq.py → S因子
       │   └─→ features/volume.py → V因子
       │
       ├─→ Layer 2: 资金流层
       │   ├─→ features/cvd.py → C因子
       │   ├─→ features/open_interest.py → O因子
       │   └─→ features/fund_leading.py → F因子
       │
       ├─→ Layer 3: 微观结构层
       │   ├─→ factors_v2/liquidity.py → L因子
       │   ├─→ factors_v2/basis_funding.py → B因子
       │   └─→ factors_v2/liquidation.py → Q因子
       │
       └─→ Layer 4: 市场环境层
           └─→ factors_v2/independence.py → I因子
```

### 3. 评分系统层

```
scores = {
    "T": -100~+100,
    "M": -100~+100,
    ...
}
weights = {
    "T": 13.9%,
    "M": 8.3%,
    ...
}
       │
       ├─→ adaptive_weights.py
       │   ├─ 检测市场状态（regime, volatility）
       │   ├─ 获取regime权重
       │   └─ 混合（70%自适应 + 30%基础）
       │
       ├─→ scorecard.py
       │   ├─ 加权平均: Σ(score × weight) / Σ(weight)
       │   └─ 归一化到[-100, +100]
       │
       └─→ probability_v2.py
           ├─ Sigmoid映射: score → probability
           ├─ 温度自适应
           └─ 输出P_long, P_short
```

### 4. Prime判定层

```
weighted_score, confidence, edge = scorecard(scores, weights)
       │
       ├─→ prime_strength计算
       │   ├─ base_strength = confidence × 0.6 (0-60分)
       │   ├─ prob_bonus = (P - 0.60) / 0.15 × 40 (0-40分)
       │   └─ prime_strength = base + bonus (0-100分)
       │
       ├─→ Prime判定
       │   └─ is_prime = (prime_strength >= 35)
       │
       └─→ F因子否决机制
           └─ if F_aligned < -70: P_chosen × 0.7
```

---

## 🧩 核心模块详解

### 1. OptimizedBatchScanner

**文件**: `ats_core/pipeline/batch_scan_optimized.py`

**功能**:
- WebSocket K线缓存管理
- 批量扫描200个币种
- Prime信号过滤

**关键方法**:
```python
class OptimizedBatchScanner:
    async def initialize():
        """初始化WebSocket缓存（3-4分钟）"""
        # 预热K线缓存
        # 订阅140个高流动性币种的WebSocket流

    async def batch_scan(symbols, min_score):
        """批量扫描（12-15秒/200币种）"""
        # 使用缓存的K线数据
        # 并发分析所有币种
        # 返回Prime信号列表
```

**性能指标**:
- 初始化: 3-4分钟
- 扫描速度: 12-15秒/200币种
- API调用: 0次/扫描（使用缓存）
- 内存占用: ~100-200MB

---

### 2. analyze_symbol

**文件**: `ats_core/pipeline/analyze_symbol.py`

**功能**:
- 单币种完整分析
- 10+1维因子计算
- 自适应权重
- Prime判定

**数据流**:
```python
def analyze_symbol(symbol, klines_preloaded=None):
    # 1. 数据获取
    klines_1h = get_klines(symbol, "1h", 400)
    klines_15m = get_klines(symbol, "15m", 100)
    oi_hist = get_open_interest_hist(symbol)

    # 2. 计算10+1维因子
    T = calculate_trend(klines_1h)
    M = calculate_momentum(klines_1h)
    C = calculate_cvd(klines_1h)
    # ... 省略其他因子

    scores = {"T": T, "M": M, "C": C, ...}

    # 3. 自适应权重
    regime_weights = get_regime_weights(market_regime, volatility)
    final_weights = blend_weights(regime_weights, base_weights, 0.7)

    # 4. 加权评分
    weighted_score, confidence, edge = scorecard(scores, final_weights)

    # 5. 概率映射
    P_long, P_short = map_probability_sigmoid(...)

    # 6. Prime判定
    prime_strength = confidence * 0.6 + prob_bonus
    is_prime = (prime_strength >= 35)

    # 7. F因子否决
    if F_aligned < -70:
        P_chosen *= 0.7

    return {
        "symbol": symbol,
        "side": "long" or "short",
        "weighted_score": weighted_score,
        "confidence": confidence,
        "P_long": P_long,
        "P_short": P_short,
        "publish": {
            "prime": is_prime,
            "prime_strength": prime_strength
        },
        "scores": scores,
        ...
    }
```

---

### 3. scorecard

**文件**: `ats_core/scoring/scorecard.py`

**功能**:
- 加权平均评分
- 归一化到[-100, +100]

**公式**:
```python
def scorecard(scores, weights):
    """
    v6.0评分系统：加权平均

    公式：
        weighted_score = Σ(score_i × weight_i) / Σ(weight_i)

    示例：
        scores = {"T": -100, "M": -80, "F": +72}
        weights = {"T": 13.9, "M": 8.3, "F": 10.0}

        total = (-100 × 13.9) + (-80 × 8.3) + (72 × 10.0)
              = -1390 + (-664) + 720
              = -1334

        weight_sum = 13.9 + 8.3 + 10.0 = 32.2

        weighted_score = -1334 / 32.2 = -41.4
    """
    total = sum(scores[dim] * weights[dim] for dim in scores if dim in weights)
    weight_sum = sum(weights[dim] for dim in scores if dim in weights)

    weighted_score = total / weight_sum if weight_sum > 0 else 0.0
    weighted_score = max(-100.0, min(100.0, weighted_score))

    confidence = abs(weighted_score)
    edge = weighted_score / 100.0

    return int(round(weighted_score)), int(round(confidence)), edge
```

---

### 4. adaptive_weights

**文件**: `ats_core/scoring/adaptive_weights.py`

**功能**:
- 根据市场状态动态调整权重
- 平滑混合regime权重和基础权重

**算法**:
```python
def get_regime_weights(market_regime, volatility):
    """
    市场状态分类：
    1. 强势趋势 (|regime| > 60): 趋势权重↑
    2. 震荡市场 (|regime| < 30): 资金流权重↑
    3. 高波动 (vol > 0.03): OI权重↑
    4. 低波动 (vol < 0.01): 趋势稳定性权重↑
    """
    if abs(market_regime) > 60:
        # 强势趋势
        return {
            "T": 19.4,  # ↑
            "M": 11.1,  # ↑
            "S": 2.8,   # ↓
            ...
        }
    elif abs(market_regime) < 30:
        # 震荡市场
        return {
            "T": 8.3,   # ↓
            "C": 13.9,  # ↑
            "O": 13.9,  # ↑
            ...
        }
    # ... 其他状态

def blend_weights(regime_weights, base_weights, blend_ratio=0.7):
    """
    平滑混合：70%自适应 + 30%基础

    blended[dim] = blend_ratio × regime_w + (1 - blend_ratio) × base_w
    """
    blended = {}
    for dim in base_weights.keys():
        base_w = base_weights[dim]
        regime_w = regime_weights.get(dim, base_w)
        blended[dim] = blend_ratio * regime_w + (1 - blend_ratio) * base_w

    # 归一化到100%
    total = sum(blended.values())
    scale_factor = 100.0 / total if total > 0 else 1.0
    for dim in blended:
        blended[dim] = round(blended[dim] * scale_factor, 1)

    return blended
```

---

### 5. probability_v2 (Sigmoid映射)

**文件**: `ats_core/scoring/probability_v2.py`

**功能**:
- 将评分(-100~+100)映射到概率(0~1)
- 温度自适应

**公式**:
```python
def map_probability_sigmoid(weighted_score, confidence, temperature=50.0):
    """
    Sigmoid概率映射

    公式：
        P = 1 / (1 + e^(-x/T))

    其中：
        x = weighted_score (-100~+100)
        T = temperature (温度参数，控制陡峭度)

    示例：
        weighted_score = 60, T = 50
        P = 1 / (1 + e^(-60/50))
          = 1 / (1 + e^(-1.2))
          = 1 / (1 + 0.301)
          = 0.768 (76.8%)
    """
    import math

    # 归一化温度（根据confidence调整）
    adaptive_T = get_adaptive_temperature(confidence)

    # Sigmoid映射
    P = 1.0 / (1.0 + math.exp(-weighted_score / adaptive_T))

    return P
```

---

## 🔗 依赖关系图

```
realtime_signal_scanner.py
  │
  ├─ batch_scan_optimized.py
  │    │
  │    ├─ analyze_symbol.py
  │    │    │
  │    │    ├─ features/*
  │    │    │    ├─ trend.py
  │    │    │    ├─ momentum.py
  │    │    │    ├─ cvd.py
  │    │    │    ├─ structure_sq.py
  │    │    │    ├─ volume.py
  │    │    │    ├─ open_interest.py
  │    │    │    └─ fund_leading.py
  │    │    │
  │    │    ├─ factors_v2/*
  │    │    │    ├─ liquidity.py
  │    │    │    ├─ basis_funding.py
  │    │    │    ├─ liquidation.py
  │    │    │    └─ independence.py
  │    │    │
  │    │    ├─ scoring/scorecard.py
  │    │    ├─ scoring/adaptive_weights.py
  │    │    └─ scoring/probability_v2.py
  │    │
  │    ├─ data/realtime_kline_cache.py
  │    └─ sources/binance.py
  │
  └─ outputs/telegram_fmt.py
```

---

## 💾 数据结构

### 1. K线数据结构

```python
kline = {
    "open_time": 1698739200000,     # 开盘时间（毫秒时间戳）
    "open": "34500.0",              # 开盘价
    "high": "34650.0",              # 最高价
    "low": "34480.0",               # 最低价
    "close": "34580.0",             # 收盘价
    "volume": "1234.5",             # 成交量（币）
    "close_time": 1698742799999,    # 收盘时间
    "quote_volume": "42650000.0",   # 成交额（USDT）
    "trades": 15234,                # 成交笔数
    "taker_buy_base": "678.2",      # 主动买入量（币）
    "taker_buy_quote": "23450000.0" # 主动买入额（USDT）
}
```

### 2. 分析结果结构

```python
result = {
    "symbol": "BTCUSDT",
    "side": "long",                  # "long" or "short"
    "weighted_score": 65,            # 加权分数（-100~+100）
    "confidence": 65,                # 置信度（0-100）
    "edge": 0.65,                    # 优势度（-1.0~+1.0）

    "P_long": 0.82,                  # 做多概率
    "P_short": 0.18,                 # 做空概率

    "scores": {                      # 10维因子分数
        "T": 75,  "M": 60,  "C": 70,
        "S": 50,  "V": 65,  "O": 80,
        "L": 55,  "B": 45,  "Q": 60,
        "I": 70,  "F": 85
    },

    "publish": {
        "prime": True,               # 是否为Prime信号
        "watch": False,
        "dims_ok": 6,                # 达标维度数
        "prime_strength": 67,        # Prime强度（0-100）
        "ttl_h": 8                   # 有效期（小时）
    },

    "pricing": {
        "entry_lo": 34500.0,         # 入场下限
        "entry_hi": 34600.0,         # 入场上限
        "sl": 34200.0,               # 止损
        "tp1": 34900.0,              # 止盈1
        "tp2": 35300.0               # 止盈2
    },

    "meta": {
        "trend_meta": {...},
        "momentum_meta": {...},
        ...
    }
}
```

---

## ⚡ 性能优化

### 1. WebSocket缓存

**问题**: 批量扫描200个币种，每个币种需要400根K线，REST API调用太慢

**解决方案**: WebSocket实时缓存
```python
# ats_core/data/realtime_kline_cache.py
class RealtimeKlineCache:
    def __init__(self):
        self.cache = {}  # {symbol: {interval: deque}}
        self.sockets = []

    async def subscribe(self, symbol, interval):
        """订阅WebSocket流"""
        stream = f"{symbol.lower()}@kline_{interval}"
        # 实时更新cache

    def get_klines(self, symbol, interval, limit):
        """从缓存获取K线（0次API调用）"""
        return list(self.cache[symbol][interval])[-limit:]
```

**效果**:
- 扫描时间: 3-5分钟 → 12-15秒
- API调用: 200个币种 × 400K线 = 80000次 → 0次

### 2. 并发分析

```python
# ats_core/pipeline/batch_scan_optimized.py
async def batch_scan(symbols, min_score):
    tasks = [analyze_symbol(s) for s in symbols]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

### 3. 内存优化

- K线缓存使用 `deque(maxlen=400)` 自动丢弃旧数据
- 只缓存必要的币种（140个高流动性币种）
- 定期清理过期缓存

---

## 🔧 扩展性

### 1. 添加新因子

**步骤**:
1. 创建新因子文件（如 `ats_core/factors_v2/new_factor.py`）
2. 在 `analyze_symbol.py` 中导入并计算
3. 在 `config/params.json` 中添加权重和参数
4. 在 `adaptive_weights.py` 的所有regime中添加
5. （可选）在 `telegram_fmt.py` 中添加显示

### 2. 添加新数据源

**步骤**:
1. 在 `ats_core/sources/` 下创建新数据源文件
2. 实现API封装（带重试、限流）
3. 在 `analyze_symbol.py` 中集成
4. 更新缓存策略

---

## 📊 监控与调试

### 1. 日志系统

```python
# ats_core/logging.py
def log(msg):    # INFO级别
def warn(msg):   # WARNING级别
def error(msg):  # ERROR级别
```

### 2. 性能监控

```python
# analyze_symbol返回的meta中包含性能数据
{
    "elapsed_seconds": 0.5,      # 分析耗时
    "cache_hit": True,           # 是否命中缓存
    "api_calls": 0               # API调用次数
}
```

### 3. 调试技巧

```bash
# 单币种测试
python3 -c "
from ats_core.pipeline.analyze_symbol import analyze_symbol
import asyncio
result = asyncio.run(analyze_symbol('BTCUSDT'))
print(result)
"

# 小规模扫描测试
python3 scripts/realtime_signal_scanner.py --max-symbols 10 --once --verbose

# 查看详细日志
tail -f scanner.log
```

---

## 🔗 相关文档

- [SYSTEM_OVERVIEW.md](./SYSTEM_OVERVIEW.md) - 系统总览
- [CONFIGURATION_GUIDE.md](./CONFIGURATION_GUIDE.md) - 配置参数详解
- [MODIFICATION_RULES.md](./MODIFICATION_RULES.md) - 代码修改规范

---

**最后更新**: 2025-10-30
