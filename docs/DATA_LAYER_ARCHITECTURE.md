# 数据层架构说明（v6.0）

## 📋 目录
- [架构概览](#架构概览)
- [三层架构设计](#三层架构设计)
- [数据分类与获取策略](#数据分类与获取策略)
- [核心组件详解](#核心组件详解)
- [数据流程](#数据流程)
- [性能优化](#性能优化)
- [数据质量监控](#数据质量监控)

---

## 📐 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                      业务逻辑层                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │  OptimizedBatchScanner                            │     │
│  │  - scan(): 批量扫描140个币种                       │     │
│  │  - 0次API调用（纯缓存读取）                        │     │
│  │  - 5-10秒完成扫描                                  │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
                           ↓ 读取
┌─────────────────────────────────────────────────────────────┐
│                      缓存层（ats_core/data）                 │
│  ┌──────────────────────┐  ┌──────────────────────┐        │
│  │ RealtimeKlineCache   │  │ 市场数据缓存          │        │
│  │ ─────────────────    │  │ ─────────────────    │        │
│  │ • K线缓存（WebSocket）│  │ • 订单簿缓存          │        │
│  │ • 1h/4h/15m/1d      │  │ • 标记价格缓存        │        │
│  │ • 固定大小deque     │  │ • 资金费率缓存        │        │
│  │ • 实时增量更新      │  │ • OI历史缓存          │        │
│  │                     │  │ • 聚合成交缓存        │        │
│  └──────────────────────┘  └──────────────────────┘        │
│                                                              │
│  ┌──────────────────────────────────────────────────┐      │
│  │ DataQualMonitor（数据质量监控）                   │      │
│  │ - miss_rate: 数据丢失率                           │      │
│  │ - oo_order_rate: 乱序率                          │      │
│  │ - drift_rate: 时间漂移率                         │      │
│  │ - mismatch_rate: 订单簿不一致率                  │      │
│  │ → DataQual评分: 0.90以上允许Prime信号             │      │
│  └──────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
                           ↓ 数据源
┌─────────────────────────────────────────────────────────────┐
│                  数据获取层（ats_core/sources）              │
│  ┌──────────────────────┐  ┌──────────────────────┐        │
│  │ WebSocket实时推送    │  │ REST API批量获取      │        │
│  │ ─────────────────    │  │ ─────────────────    │        │
│  │ • K线流（1h/4h/15m） │  │ • OI历史数据          │        │
│  │ • 订单簿流（depth20） │  │ • 现货价格            │        │
│  │ • 标记价格流         │  │ • 资金费率            │        │
│  │ • 实时成交流         │  │ • 聚合成交            │        │
│  │                     │  │ • 历史K线（初始化）   │        │
│  └──────────────────────┘  └──────────────────────┘        │
│                                                              │
│  📡 Binance Futures API                                     │
│  - WebSocket: wss://fstream.binance.com/stream             │
│  - REST: https://fapi.binance.com                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🏗️ 三层架构设计

### 第一层：数据获取层（`ats_core/sources/`）

**职责**：直接与Binance API交互，获取原始市场数据

| 模块 | 文件 | 功能 |
|------|------|------|
| **Binance API** | `binance.py` | REST API封装（K线、订单簿、资金费率等） |
| **安全调用** | `binance_safe.py` | 带重试和限流的安全API调用 |
| **K线获取** | `klines.py` | 专门的K线数据获取模块 |
| **持仓量** | `oi.py` | OI历史数据获取（1h粒度） |
| **行情数据** | `tickers.py` | 24h行情和实时价格 |

**关键特性**：
- ✅ 自动重试机制（最多3次）
- ✅ 速率限制保护（每秒20次请求）
- ✅ 并发控制（批量请求用asyncio.gather）
- ✅ 错误处理和日志记录

---

### 第二层：缓存层（`ats_core/data/`）

**职责**：缓存市场数据，提供统一访问接口，监控数据质量

#### 核心组件

##### 1. RealtimeKlineCache（`realtime_kline_cache.py`）

**K线实时缓存管理器**

```python
class RealtimeKlineCache:
    """
    缓存结构: {symbol: {interval: deque([kline1, kline2, ...])}}

    特性:
    - REST初始化历史K线（一次性，~2分钟）
    - WebSocket实时增量更新（每个K线周期推送一次）
    - 固定大小deque（内存友好）
    - 多币种 × 多周期支持
    """
```

**性能指标**：
- 初始化：140币种 × 4周期 = 560次REST调用，~2分钟
- 更新频率：1h K线每小时更新一次，15m K线每15分钟更新一次
- 内存占用：~150MB（140币种 × 4周期 × 300根K线）
- 缓存命中率：99.9%（扫描时100%命中）

##### 2. 市场数据缓存（`batch_scan_optimized.py`）

**多维度市场数据缓存**

```python
class OptimizedBatchScanner:
    # 高频数据缓存（WebSocket可选，当前使用REST定时更新）
    self.kline_cache          # K线缓存管理器

    # 低频数据缓存（REST批量获取，初始化时加载）
    self.orderbook_cache = {}      # 订单簿快照（20档）
    self.mark_price_cache = {}     # 标记价格
    self.funding_rate_cache = {}   # 资金费率
    self.spot_price_cache = {}     # 现货价格
    self.liquidation_cache = {}    # 聚合成交数据（Q因子）
    self.oi_cache = {}             # OI历史数据（O因子）
    self.btc_klines = []           # BTC K线（I因子）
    self.eth_klines = []           # ETH K线（I因子）
```

##### 3. DataQualMonitor（`quality.py`）

**数据质量监控**

```python
class DataQualMonitor:
    """
    评分公式:
    DataQual = 1 - (w_h·miss + w_o·ooOrder + w_d·drift + w_m·mismatch)

    权重配置:
    - miss (缺失率): 35%
    - oo_order (乱序率): 15%
    - drift (时间漂移): 20%
    - mismatch (订单簿不一致): 30%

    质量门槛:
    - DataQual ≥ 0.90: 允许Prime信号
    - DataQual < 0.88: 降级为Watch-only
    """
```

---

### 第三层：业务逻辑层（`ats_core/pipeline/`）

**职责**：使用缓存数据进行信号分析和扫描

```python
class OptimizedBatchScanner:
    async def scan(self, min_score=70, verbose=False):
        """
        批量扫描（超快速）

        性能:
        - 140个币种：12-15秒
        - API调用：0次（纯缓存读取）
        - 速度提升：17倍（相比原始REST方案）
        """
        for symbol in symbols:
            # 1. 从缓存获取K线（0次API调用）
            k1h = self.kline_cache.get_klines(symbol, '1h', 300)
            k4h = self.kline_cache.get_klines(symbol, '4h', 200)
            k15m = self.kline_cache.get_klines(symbol, '15m', 200)
            k1d = self.kline_cache.get_klines(symbol, '1d', 100)

            # 2. 获取其他市场数据（0次API调用，从缓存读取）
            orderbook = self.orderbook_cache.get(symbol)
            mark_price = self.mark_price_cache.get(symbol)
            funding_rate = self.funding_rate_cache.get(symbol)
            oi_data = self.oi_cache.get(symbol, [])

            # 3. 因子分析（11维因子系统）
            result = analyze_symbol_with_preloaded_klines(
                symbol, k1h, k4h, k15m, k1d,
                orderbook, mark_price, funding_rate, ...
            )

            # 4. 筛选Prime信号
            if result['publish']['prime']:
                prime_signals.append(result)
```

---

## 📊 数据分类与获取策略

### 混合策略设计

| 数据类型 | 更新频率 | 获取方式 | 原因 |
|---------|---------|---------|------|
| **K线数据** | 实时（按周期） | REST初始化 + 定时更新 | 1h/4h K线更新慢，不需要WebSocket |
| **订单簿** | 100ms | REST批量获取 | 初始化时一次性获取20档深度 |
| **标记价格** | 3秒 | REST批量获取 | 1次API调用获取所有币种 |
| **资金费率** | 8小时 | REST批量获取 | 更新很慢，批量获取即可 |
| **现货价格** | 1秒 | REST批量获取 | 1次API调用获取所有币种 |
| **OI历史** | 1小时 | REST批量获取 | 最大性能瓶颈，并发优化 |
| **聚合成交** | 实时 | REST批量获取 | 替代已废弃的清算API |

### WebSocket vs REST 选择逻辑

**当前策略：推荐禁用WebSocket，使用REST定时更新**

理由：
1. **1h/4h K线更新很慢**：每小时/4小时才更新一次，不需要实时推送
2. **连接数限制**：140币种 × 2周期 = 280个连接，接近300上限
3. **稳定性问题**：网络波动时频繁重连，增加复杂度
4. **实际收益小**：REST定时更新（每5分钟）已足够

**WebSocket模式**（可选，默认禁用）：
```python
await scanner.initialize(enable_websocket=True)  # 不推荐
```

**REST模式**（推荐，默认）：
```python
await scanner.initialize(enable_websocket=False)  # 推荐
```

---

## 🔧 核心组件详解

### 1. 初始化流程（`OptimizedBatchScanner.initialize()`）

```
┌─────────────────────────────────────────────────────────┐
│ 步骤1: 初始化Binance客户端                               │
│ - 创建aiohttp session                                   │
│ - 验证API连接                                            │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ 步骤2: 获取高流动性USDT合约币种                          │
│ - 获取交易所信息（1次API调用）                           │
│ - 获取24h行情（1次API调用）                              │
│ - 按成交额排序，取TOP 140                                │
│ - 过滤：24h成交额 >= 3M USDT                             │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ 步骤3: 批量初始化K线缓存（REST）                         │
│ - 140币种 × 4周期 = 560次API调用                        │
│ - 每个币种获取300/200根历史K线                           │
│ - 耗时：~2分钟（一次性成本）                             │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ 步骤4: 启动WebSocket实时更新（可选，默认禁用）            │
│ - 订阅K线流（1h/4h）                                     │
│ - 自动重连和心跳                                         │
│ - 实时增量更新缓存                                       │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ 步骤5: 预加载10维因子数据                                │
│ 5.1 现货价格（1次API调用）                               │
│ 5.2 标记价格+资金费率（1次API调用）                      │
│ 5.3 订单簿快照（140次API调用，并发20个/批）              │
│ 5.4 聚合成交数据（140次API调用，并发20个/批）            │
│ 5.5 OI历史数据（140次API调用，并发20个/批）              │
│ 5.6 BTC/ETH K线（2次API调用，I因子用）                  │
│ 耗时：~60-80秒                                           │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ 初始化完成！                                             │
│ - 总耗时：~2-3分钟                                       │
│ - 后续扫描：5-10秒（0次API调用）                         │
└─────────────────────────────────────────────────────────┘
```

### 2. 扫描流程（`OptimizedBatchScanner.scan()`）

```
开始扫描（140个币种）
    ↓
对每个币种:
    ├─ 从K线缓存获取数据（0次API）
    │  ├─ 1h K线（300根）
    │  ├─ 4h K线（200根）
    │  ├─ 15m K线（200根）
    │  └─ 1d K线（100根）
    │
    ├─ 从市场数据缓存获取（0次API）
    │  ├─ 订单簿快照
    │  ├─ 标记价格
    │  ├─ 资金费率
    │  ├─ 现货价格
    │  ├─ OI历史数据
    │  └─ 聚合成交数据
    │
    ├─ 因子分析（11维因子）
    │  ├─ T（趋势）: 基于EMA和MACD
    │  ├─ M（动量）: RSI和Stoch
    │  ├─ C（确认）: MTF确认
    │  ├─ S（结构）: 支撑阻力
    │  ├─ V（量能）: 放量确认（v2.0多空对称）
    │  ├─ O（持仓）: OI变化（v2.0多空对称）
    │  ├─ L（流动性）: 订单簿深度
    │  ├─ B（基差）: 期现价差
    │  ├─ Q（清算）: 聚合成交密度
    │  ├─ I（独立性）: 与BTC/ETH相关性
    │  └─ F（微确认）: 15m级别确认
    │
    ├─ 四门系统验证
    │  ├─ DataQual门（数据质量≥0.90）
    │  ├─ EV门（期望值>0）
    │  ├─ Execution门（执行成本<2%）
    │  └─ Probability门（概率≥55%）
    │
    └─ Prime信号筛选
       └─ 通过四门 + confidence≥70 → 发送信号
    ↓
扫描完成（12-15秒）
    ├─ API调用：0次 ✅
    ├─ 缓存命中率：99.9% ✅
    └─ Prime信号：0-10个
```

---

## ⚡ 性能优化

### 1. 并发优化

**问题**：串行获取140个币种的订单簿需要140秒

**解决**：使用asyncio.gather并发获取

```python
async def fetch_one_orderbook(symbol: str):
    loop = asyncio.get_event_loop()
    orderbook = await loop.run_in_executor(
        None,  # 使用默认线程池
        lambda: get_orderbook_snapshot(symbol, limit=20)
    )
    return symbol, orderbook, None

# 分批并发（每批20个）
batch_size = 20
for i in range(0, len(symbols), batch_size):
    batch = symbols[i:i+batch_size]
    tasks = [fetch_one_orderbook(symbol) for symbol in batch]
    results = await asyncio.gather(*tasks)
    # 批间延迟0.5秒（避免速率限制）
```

**效果**：
- 订单簿获取：140秒 → 20秒（7倍提升）
- OI历史获取：700秒 → 60秒（11.7倍提升）
- 聚合成交获取：140秒 → 15秒（9.3倍提升）

### 2. 缓存复用

**K线缓存命中率优化**：

```python
# 缓存结构：固定大小deque
self.cache[symbol][interval] = deque(maxlen=300)

# 首次获取：REST API
klines = await client.get_klines(symbol, '1h', limit=300)

# 后续扫描：纯内存读取
klines = self.kline_cache.get_klines(symbol, '1h', 300)  # 0次API
```

**效果**：
- 首次扫描：560次API调用（初始化K线）
- 后续扫描：0次API调用（100%缓存命中）
- 速度提升：85秒 → 5秒（17倍）

### 3. 内存优化

**固定大小deque防止内存泄漏**：

```python
from collections import deque

# 最多保留300根K线
self.cache[symbol][interval] = deque(maxlen=300)

# 新K线自动淘汰旧K线
self.cache[symbol][interval].append(new_kline)
```

**内存占用估算**：
- K线缓存：140币种 × 4周期 × 300根 × 1KB ≈ 150MB
- 市场数据缓存：订单簿+OI+其他 ≈ 50MB
- 总计：~200MB（可接受）

---

## 🔍 数据质量监控

### DataQual评分系统

**评分公式**：

```
DataQual = 1 - (w_h·miss + w_o·ooOrder + w_d·drift + w_m·mismatch)

其中：
- miss: 数据缺失率（weight=0.35）
- ooOrder: 乱序率（weight=0.15）
- drift: 时间漂移率（weight=0.20）
- mismatch: 订单簿不一致率（weight=0.30）
```

**质量门槛**：

```python
if DataQual >= 0.90:
    允许Prime信号
elif DataQual >= 0.88:
    降级为Watch-only
else:
    跳过该币种
```

**监控指标**：

| 指标 | 定义 | 阈值 | 影响 |
|------|------|------|------|
| **miss_rate** | 预期数据中缺失的比例 | <5% | 影响因子计算准确性 |
| **oo_order_rate** | 乱序数据的比例 | <2% | 影响趋势判断 |
| **drift_rate** | 时间戳漂移超过300ms的比例 | <3% | 影响时序分析 |
| **mismatch_rate** | 订单簿bid/ask交叉的比例 | <1% | 影响流动性评估 |

**实现示例**：

```python
monitor = DataQualMonitor()

# 记录数据事件
monitor.record_data_point('BTCUSDT', timestamp, received=True)
monitor.record_out_of_order('BTCUSDT')
monitor.record_drift_violation('BTCUSDT', drift_ms=350)
monitor.record_mismatch('BTCUSDT')

# 获取质量评分
metrics = monitor.get_metrics('BTCUSDT')
print(f"DataQual: {metrics.dataqual:.3f}")

# 门槛判断
if metrics.dataqual >= 0.90:
    print("✅ 允许Prime信号")
elif metrics.dataqual >= 0.88:
    print("⚠️  降级为Watch-only")
else:
    print("❌ 跳过该币种")
```

---

## 📈 性能指标总结

| 指标 | 原方案 | 优化后 | 提升 |
|------|--------|--------|------|
| **首次扫描时间** | N/A | ~2-3分钟 | 一次性成本 |
| **后续扫描时间** | 85秒 | 5-10秒 | 17倍 ⚡ |
| **API调用/扫描** | 400次 | 0次 | -100% ✅ |
| **缓存命中率** | 0% | 99.9% | +99.9% ✅ |
| **内存占用** | ~50MB | ~200MB | 可接受 |
| **数据新鲜度** | 实时 | <5分钟 | 足够 |
| **WebSocket连接数** | 0 | 0（推荐禁用） | 稳定优先 |

---

## 🎯 最佳实践

### 1. 初始化一次，多次扫描

```python
# ✅ 正确：初始化一次
scanner = OptimizedBatchScanner()
await scanner.initialize()  # 2-3分钟

# 后续每5分钟扫描一次
while True:
    await scanner.scan()  # 5-10秒，0次API
    await asyncio.sleep(300)
```

```python
# ❌ 错误：每次都初始化
while True:
    scanner = OptimizedBatchScanner()
    await scanner.initialize()  # 每次都要2-3分钟！
    await scanner.scan()
```

### 2. 禁用WebSocket（推荐）

```python
# ✅ 推荐：REST定时更新模式
await scanner.initialize(enable_websocket=False)

# 理由：
# 1. 1h/4h K线更新很慢，不需要实时
# 2. 避免280个WebSocket连接
# 3. 稳定性更好
```

### 3. 合理使用verbose模式

```python
# 生产环境：关闭verbose（减少日志）
await scanner.scan(min_score=70, verbose=False)

# 调试分析：开启verbose（监控所有币种评分）
await scanner.scan(min_score=70, verbose=True)
```

### 4. 监控数据质量

```python
# 定期检查缓存状态
stats = scanner.kline_cache.get_stats()
print(f"缓存命中率: {stats['hit_rate']}")
print(f"内存占用: {stats['memory_estimate_mb']:.1f}MB")

# 检查数据质量
metrics = data_qual_monitor.get_metrics('BTCUSDT')
if metrics.dataqual < 0.90:
    warn(f"数据质量低: {metrics.dataqual:.3f}")
```

---

## 📚 相关文档

- [系统总览](../standards/SYSTEM_OVERVIEW.md) - 完整系统架构
- [因子系统](../standards/FACTOR_WEIGHTS.md) - 11维因子详解
- [四门系统](../docs/FOUR_GATES_SYSTEM.md) - 质量控制门槛
- [数据质量](./DATA_LAYER.md) - DataQual评分细节
- [性能优化](./PERFORMANCE_OPTIMIZATION.md) - 性能优化技术

---

**最后更新**: 2025-11-01
**版本**: v6.0 (多空对称性修复版)
