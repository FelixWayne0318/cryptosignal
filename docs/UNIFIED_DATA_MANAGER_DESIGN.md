# 统一数据管理器 - 架构设计文档

## 目录
1. [设计背景](#设计背景)
2. [核心架构](#核心架构)
3. [数据分类策略](#数据分类策略)
4. [性能优化](#性能优化)
5. [使用指南](#使用指南)
6. [API文档](#api文档)
7. [迁移指南](#迁移指南)

---

## 设计背景

### 当前问题

**现有架构的痛点**：

```
❌ 问题1: 数据获取方式混乱
   - K线: WebSocket缓存（实现分散）
   - OI/资金费率/订单簿: REST API（每次扫描都调用）
   - 没有统一的数据管理层

❌ 问题2: REST和WebSocket没有有机结合
   - WebSocket框架只是空壳（未实现）
   - K线缓存独立存在，其他数据无缓存
   - 无法自动降级（WebSocket断线时无法回退REST）

❌ 问题3: 性能瓶颈
   - 每次扫描200个币种，需要调用数百次REST API
   - 扫描耗时: 80-120秒（API请求占90%时间）
   - API限流风险

❌ 问题4: 代码重复
   - analyze_symbol每次都独立获取数据
   - 批量扫描器无法共享数据
   - 无法利用缓存
```

### 解决方案

**统一数据管理器 (Unified Data Manager)**

```
✅ 核心理念: 智能路由 + 自动降级 + 统一接口

┌─────────────────────────────────────────┐
│    统一数据管理器 (UnifiedDataManager) │
│                                         │
│  • 智能决策: WebSocket vs REST         │
│  • 自动缓存: 内存优化                   │
│  • 自动降级: 容错机制                   │
│  • 统一接口: 简化调用                   │
└─────────────────────────────────────────┘
           │
           ├───► 高频数据 → WebSocket实时推送
           │      • K线 (1m/5m/15m/1h/4h/1d)
           │      • 订单簿 (depth20@100ms)
           │      • 标记价格 (markPrice@3s)
           │      • 成交流 (aggTrade)
           │
           └───► 低频数据 → REST定期轮询
                  • OI历史 (每5分钟)
                  • 资金费率 (每小时)
                  • 现货价格 (每分钟)
                  • 清算数据 (每5分钟)
```

---

## 核心架构

### 1. 三层架构设计

```
┌─────────────────────────────────────────────────────┐
│           应用层 (Application Layer)                │
│  • analyze_symbol_v2()                             │
│  • batch_scan()                                     │
│  • auto_trader                                      │
└─────────────────┬───────────────────────────────────┘
                  │
                  │ 统一接口
                  │
┌─────────────────▼───────────────────────────────────┐
│        数据管理层 (Unified Data Manager)           │
│                                                     │
│  核心职责:                                          │
│  ✓ 智能路由（WebSocket/REST）                      │
│  ✓ 数据缓存（内存优化）                             │
│  ✓ 自动降级（容错机制）                             │
│  ✓ 生命周期管理                                     │
└─────────────────┬───────────────────────────────────┘
                  │
          ┌───────┴───────┐
          │               │
┌─────────▼────┐   ┌──────▼─────────┐
│  WebSocket   │   │   REST API     │
│  实时推送    │   │   定期轮询     │
│              │   │                │
│ • K线        │   │ • OI历史       │
│ • 订单簿     │   │ • 资金费率     │
│ • 标记价格   │   │ • 现货价格     │
│ • 成交流     │   │ • 清算数据     │
└──────────────┘   └────────────────┘
```

### 2. 数据流向图

```
初始化阶段（一次性，2-3分钟）：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REST批量获取
     │
     ├─► K线历史数据（所有周期）
     ├─► OI历史数据（最近300条）
     ├─► 资金费率（当前值）
     └─► 现货价格（当前值）
     │
     ▼
   缓存初始化完成

运行阶段（持续）：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WebSocket实时推送
     │
     ├─► K线更新（每周期实时）
     ├─► 订单簿更新（100ms）
     └─► 标记价格更新（3s）
     │
     ▼
   实时缓存更新

+

REST定期轮询
     │
     ├─► OI数据（每5分钟）
     ├─► 资金费率（每小时）
     ├─► 现货价格（每分钟）
     └─► 清算数据（每5分钟）
     │
     ▼
   定期缓存更新

=

应用层调用
     │
     ├─► get_klines() → 读取WebSocket缓存（实时）
     ├─► get_oi_history() → 读取REST缓存（5分钟新鲜）
     ├─► get_orderbook() → 读取WebSocket缓存（100ms新鲜）
     ├─► get_funding_rate() → 读取REST缓存（1小时新鲜）
     ├─► get_spot_price() → 读取REST缓存（1分钟新鲜）
     └─► get_liquidation_trades() → 读取REST缓存（5分钟新鲜）
     │
     ▼
   零延迟数据访问（纯内存读取）
```

---

## 数据分类策略

### 分类原则

```
高频数据（实时性要求高）→ WebSocket
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 更新频率: 秒级、毫秒级
• 延迟要求: <5秒
• 数据量: 大（持续流式）
• 成本: 高（需维持长连接）

低频数据（实时性要求低）→ REST轮询
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 更新频率: 分钟级、小时级
• 延迟要求: <5分钟
• 数据量: 小（按需请求）
• 成本: 低（按需调用）
```

### 数据分类表

| 数据类型 | 更新频率 | 延迟要求 | 方式 | 缓存时长 | 备注 |
|---------|---------|---------|------|---------|------|
| **K线 (1m/5m/15m)** | 实时 | <5秒 | WebSocket | 实时 | 高频交易核心数据 |
| **K线 (1h/4h/1d)** | 实时 | <5秒 | WebSocket | 实时 | 趋势分析核心数据 |
| **订单簿 (depth20)** | 100ms | <1秒 | WebSocket | 实时 | L因子（流动性）使用 |
| **标记价格 (markPrice)** | 3秒 | <5秒 | WebSocket | 实时 | 实时价格参考 |
| **实时成交 (aggTrade)** | 实时 | <1秒 | WebSocket | 实时 | CVD因子、Q因子使用 |
| **OI历史 (1h粒度)** | 1小时 | <5分钟 | REST轮询 | 5分钟 | O+因子（OI体制）使用 |
| **资金费率** | 8小时 | <1小时 | REST轮询 | 1小时 | B因子（基差+资金费）使用 |
| **现货价格** | 分钟级 | <1分钟 | REST轮询 | 1分钟 | B因子（现货-期货基差）使用 |
| **清算数据 (aggTrades)** | 实时 | <5分钟 | REST轮询 | 5分钟 | Q因子（清算密度）使用 |

---

## 性能优化

### 1. 性能对比

#### 当前方案（REST only）

```
扫描200个币种，每个币种需要:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• K线数据（1h/4h/15m/1d）: 4次REST调用
• OI历史: 1次REST调用
• 资金费率: 1次REST调用
• 订单簿: 1次REST调用（如果需要）
• 现货价格: 1次REST调用（如果需要）

总计: 200币种 × 6-8次 = 1200-1600次REST调用
耗时: 每次200ms，总计 240-320秒（4-5分钟）
限流风险: ⚠️  极易触发（限制1200次/分钟）
```

#### 新方案（WebSocket + REST混合）

```
初始化阶段（一次性）:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• REST批量加载历史数据: ~2-3分钟
• WebSocket订阅启动: ~30秒
• 总耗时: ~3分钟

扫描阶段（每次）:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 200币种 × 纯内存读取
• API调用: 0次 ✅
• 耗时: 5-10秒 ✅（仅计算时间）
• 限流风险: 无 ✅
```

### 2. 性能指标

| 指标 | 当前方案 | 新方案 | 提升 |
|------|---------|--------|------|
| 首次启动 | ~30秒 | ~3分钟 | -6倍（一次性成本） |
| 每次扫描 | 4-5分钟 | 5-10秒 | **30-50倍** ✅ |
| API调用 | 1200-1600次 | 0次 | **-100%** ✅ |
| 限流风险 | 极高 | 无 | **消除** ✅ |
| 数据新鲜度 | 每次实时 | <5秒 | 相当 |
| 内存占用 | ~50MB | ~200MB | -4倍（可接受） |

### 3. 降级策略

```
WebSocket断线处理:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 检测断线（心跳超时）
2. 标记数据源状态为"降级"
3. 自动回退REST API
4. 尝试重连WebSocket（指数退避）
5. 重连成功后恢复WebSocket模式

降级期间:
• K线数据: REST API获取（每次扫描时）
• 订单簿: REST API获取
• 性能: 降至当前方案水平（4-5分钟/扫描）
• 用户体验: 无缝切换，无感知
```

---

## 使用指南

### 1. 快速开始

```python
# 示例: 使用统一数据管理器

import asyncio
from ats_core.data.unified_data_manager import get_data_manager


async def main():
    # 1. 获取数据管理器（单例）
    dm = get_data_manager()

    # 2. 初始化（仅一次，2-3分钟）
    await dm.initialize(
        symbols=['BTCUSDT', 'ETHUSDT', 'BNBUSDT'],
        intervals=['1h', '4h', '15m', '1d'],
        enable_websocket=True  # 生产环境：True，测试环境：False
    )

    # 3. 获取数据（零延迟，纯内存读取）

    # K线数据（WebSocket实时）
    klines_1h = await dm.get_klines('BTCUSDT', '1h', limit=300)
    print(f"K线数据: {len(klines_1h)}根")

    # OI历史（REST缓存，5分钟新鲜）
    oi_data = await dm.get_oi_history('BTCUSDT', '1h', limit=100)
    print(f"OI数据: {len(oi_data)}条")

    # 订单簿（WebSocket实时）
    orderbook = await dm.get_orderbook('BTCUSDT', limit=20)
    print(f"订单簿: {len(orderbook['bids'])}档买单, {len(orderbook['asks'])}档卖单")

    # 资金费率（REST缓存，1小时新鲜）
    funding = await dm.get_funding_rate('BTCUSDT')
    print(f"资金费率: {funding['rate']}")

    # 现货价格（REST缓存，1分钟新鲜）
    spot_price = await dm.get_spot_price('BTCUSDT')
    print(f"现货价格: {spot_price}")

    # 清算数据（REST缓存，5分钟新鲜）
    liquidations = await dm.get_liquidation_trades('BTCUSDT', limit=500)
    print(f"清算数据: {len(liquidations)}笔")

    # 4. 查看统计信息
    stats = dm.get_stats()
    print(f"\n统计信息:")
    print(f"  缓存命中率: {stats['cache_hit_rate']}")
    print(f"  REST调用次数: {stats['rest_calls']}")
    print(f"  WebSocket更新次数: {stats['ws_updates']}")

    # 5. 关闭管理器
    await dm.close()


if __name__ == "__main__":
    asyncio.run(main())
```

### 2. 集成到现有系统

#### 方案A: 修改 analyze_symbol_v2.py

```python
# 原代码（每次都REST调用）:
from ats_core.sources.binance import get_klines, get_open_interest_hist

k1 = get_klines(symbol, "1h", 300)        # REST调用
k4 = get_klines(symbol, "4h", 200)        # REST调用
oi_data = get_open_interest_hist(symbol, "1h", 300)  # REST调用

# 新代码（使用数据管理器）:
from ats_core.data.unified_data_manager import get_data_manager

dm = get_data_manager()
k1 = await dm.get_klines(symbol, "1h", 300)      # 缓存读取，0次API调用
k4 = await dm.get_klines(symbol, "4h", 200)      # 缓存读取，0次API调用
oi_data = await dm.get_oi_history(symbol, "1h", 300)  # 缓存读取，0次API调用
```

#### 方案B: 修改 batch_scan_optimized.py

```python
# 原代码:
from ats_core.data.realtime_kline_cache import get_kline_cache

kline_cache = get_kline_cache()
await kline_cache.initialize_batch(symbols, intervals, client)

# 新代码:
from ats_core.data.unified_data_manager import get_data_manager

dm = get_data_manager()
await dm.initialize(symbols, intervals, enable_websocket=True)

# 后续所有数据获取都使用 dm.get_xxx() 方法
```

---

## API文档

### 初始化和生命周期

#### `initialize(symbols, intervals, enable_websocket)`

初始化数据管理器（仅一次，2-3分钟）

**参数**:
- `symbols: List[str]` - 币种列表（如 `['BTCUSDT', 'ETHUSDT']`）
- `intervals: List[str]` - K线周期列表（默认 `['1h', '4h', '15m', '1d']`）
- `enable_websocket: bool` - 是否启用WebSocket（生产：True，测试：False）

**示例**:
```python
await dm.initialize(
    symbols=['BTCUSDT', 'ETHUSDT'],
    intervals=['1h', '4h'],
    enable_websocket=True
)
```

#### `close()`

关闭数据管理器，释放资源

**示例**:
```python
await dm.close()
```

---

### 高频数据API（WebSocket实时）

#### `get_klines(symbol, interval, limit)`

获取K线数据（优先WebSocket缓存，降级REST）

**参数**:
- `symbol: str` - 交易对（如 `'BTCUSDT'`）
- `interval: str` - K线周期（`'1m'`, `'5m'`, `'15m'`, `'1h'`, `'4h'`, `'1d'`）
- `limit: int` - 数量限制（默认300）

**返回**:
- `List[List]` - K线数据列表 `[[timestamp, open, high, low, close, volume, ...], ...]`

**数据新鲜度**: <5秒（WebSocket实时更新）

**示例**:
```python
klines = await dm.get_klines('BTCUSDT', '1h', limit=300)
# klines[0] = [1699999999000, 50000.0, 50100.0, 49900.0, 50050.0, 100.5, ...]
```

#### `get_orderbook(symbol, limit)`

获取订单簿快照（优先WebSocket，降级REST）

**参数**:
- `symbol: str` - 交易对
- `limit: int` - 深度档位（5, 10, 20）

**返回**:
- `Dict` - `{'bids': [[price, qty], ...], 'asks': [[price, qty], ...], 'timestamp': ...}`

**数据新鲜度**: <1秒（WebSocket 100ms推送）

**示例**:
```python
orderbook = await dm.get_orderbook('BTCUSDT', limit=20)
# orderbook = {
#     'bids': [[50000.0, 1.5], [49999.0, 2.3], ...],
#     'asks': [[50001.0, 1.8], [50002.0, 2.1], ...],
#     'timestamp': 1699999999000
# }
```

---

### 低频数据API（REST定期轮询）

#### `get_oi_history(symbol, interval, limit)`

获取持仓量OI历史（REST轮询缓存，每5分钟更新）

**参数**:
- `symbol: str` - 交易对
- `interval: str` - 周期（仅支持 `'1h'`）
- `limit: int` - 数量限制（默认100）

**返回**:
- `List[Dict]` - `[{'timestamp': ..., 'sumOpenInterest': ..., 'sumOpenInterestValue': ...}, ...]`

**数据新鲜度**: <5分钟

**示例**:
```python
oi_data = await dm.get_oi_history('BTCUSDT', '1h', limit=100)
# oi_data[0] = {'timestamp': 1699999999000, 'sumOpenInterest': 123456.78, ...}
```

#### `get_funding_rate(symbol)`

获取资金费率（REST缓存，每小时更新）

**参数**:
- `symbol: str` - 交易对

**返回**:
- `Dict` - `{'rate': ..., 'nextTime': ..., 'markPrice': ..., 'timestamp': ...}`

**数据新鲜度**: <1小时

**示例**:
```python
funding = await dm.get_funding_rate('BTCUSDT')
# funding = {'rate': 0.0001, 'nextTime': 1700000000000, 'markPrice': 50000.0, ...}
```

#### `get_spot_price(symbol)`

获取现货价格（REST缓存，每分钟更新）

**参数**:
- `symbol: str` - 交易对

**返回**:
- `float` - 现货价格

**数据新鲜度**: <1分钟

**示例**:
```python
spot_price = await dm.get_spot_price('BTCUSDT')
# spot_price = 49995.50
```

#### `get_liquidation_trades(symbol, limit)`

获取清算数据（aggTrades，REST缓存，每5分钟更新）

**参数**:
- `symbol: str` - 交易对
- `limit: int` - 数量限制（默认500）

**返回**:
- `List[Dict]` - `[{'price': ..., 'qty': ..., 'time': ..., 'isBuyerMaker': ...}, ...]`

**数据新鲜度**: <5分钟

**用途**: Q因子（清算密度）计算

**示例**:
```python
liquidations = await dm.get_liquidation_trades('BTCUSDT', limit=500)
# liquidations[0] = {'price': 50000.0, 'qty': 1.5, 'time': 1699999999000, 'isBuyerMaker': True}
```

---

### 统计和监控

#### `get_stats()`

获取统计信息

**返回**:
- `Dict` - 统计数据

**示例**:
```python
stats = dm.get_stats()
# stats = {
#     'initialized': True,
#     'symbols_count': 200,
#     'klines_cached': 800,  # 200币种 × 4周期
#     'oi_cached': 200,
#     'funding_cached': 200,
#     'ws_updates': 15000,
#     'rest_calls': 800,
#     'cache_hits': 50000,
#     'cache_misses': 100,
#     'cache_hit_rate': '99.8%'
# }
```

---

## 迁移指南

### 第一阶段: 测试验证（1-2天）

1. **运行测试脚本**

```bash
cd ~/cryptosignal
python3 -m ats_core.data.unified_data_manager
```

预期输出:
```
======================================================================
统一数据管理器测试
======================================================================

🚀 初始化统一数据管理器
======================================================================
   币种数: 2
   K线周期: 1h, 4h
   WebSocket: 禁用
======================================================================

1️⃣  创建HTTP会话...
2️⃣  REST批量初始化历史数据...
   初始化K线缓存: 2币种 × 2周期
      进度: 4/4 (100%)
   ✅ K线缓存初始化完成: 4个
   ...

✅ 数据管理器初始化完成！耗时: 8.5秒
======================================================================

测试数据获取
======================================================================

1️⃣  K线数据: 300根
   最新K线: [1699999999000, 50000.0, 50100.0, 49900.0, 50050.0, 100.5]

2️⃣  OI数据: 100条
   最新OI: {'timestamp': 1699999999000, 'sumOpenInterest': 123456.78}

...

✅ 测试完成
======================================================================
```

2. **对比性能**

```bash
# 测试当前方案（REST only）
time python3 tools/test_batch_scan.py --max-symbols 20

# 测试新方案（Unified Data Manager）
time python3 tools/test_unified_dm.py --max-symbols 20

# 对比耗时和API调用次数
```

### 第二阶段: 逐步迁移（1周）

1. **迁移analyze_symbol_v2.py**

创建新版本 `analyze_symbol_v3.py`，使用统一数据管理器

2. **迁移batch_scan.py**

修改为使用 `UnifiedDataManager` 替代 `RealtimeKlineCache`

3. **迁移auto_trader.py**

集成数据管理器，减少API调用

### 第三阶段: WebSocket实现（1-2周）

1. **实现WebSocket连接**

安装依赖:
```bash
pip install websockets
```

2. **实现K线流订阅**

```python
async def _start_websocket_streams(self, symbols, intervals):
    import websockets

    # 订阅K线流
    streams = [
        f"{symbol.lower()}@kline_{interval}"
        for symbol in symbols
        for interval in intervals
    ]

    # 连接WebSocket
    url = f"wss://fstream.binance.com/stream?streams={'/'.join(streams)}"
    async with websockets.connect(url) as ws:
        async for message in ws:
            await self._handle_kline_update(message)
```

3. **实现订单簿流订阅**

4. **压力测试**

```bash
# 测试200币种 × 4周期 = 800个流
python3 tools/stress_test_websocket.py
```

---

## FAQ

### Q1: 为什么初始化需要2-3分钟？

**A**: 初始化需要REST批量加载历史数据:
- 200币种 × 4周期 × 300根K线 = 240,000根K线
- 200币种 × 100条OI历史 = 20,000条OI
- 每次REST调用200ms，总计800次调用 = 160秒

这是**一次性成本**，后续扫描只需5-10秒。

### Q2: WebSocket断线后会怎样？

**A**: 自动降级到REST API，无缝切换:
1. 检测到断线
2. 标记数据源状态
3. 自动回退REST
4. 尝试重连（指数退避）
5. 重连成功后恢复WebSocket

用户无感知，数据获取不中断。

### Q3: 内存占用多大？

**A**: 约200MB（200币种）:
- K线缓存: 200币种 × 4周期 × 500根 × 12字段 × 8字节 ≈ 38MB
- OI缓存: 200币种 × 300条 × 3字段 × 8字节 ≈ 1.4MB
- 订单簿缓存: 200币种 × 40档 × 2字段 × 8字节 ≈ 0.1MB
- 其他缓存: ~5MB
- 总计: ~50MB（实际约200MB，包括Python对象开销）

内存占用可接受（现代服务器8-16GB）。

### Q4: 如何禁用WebSocket（测试模式）？

**A**:
```python
await dm.initialize(
    symbols=['BTCUSDT'],
    intervals=['1h'],
    enable_websocket=False  # 禁用WebSocket
)
```

此时所有数据都通过REST获取，性能降至当前方案水平。

### Q5: 如何监控数据新鲜度？

**A**:
```python
stats = dm.get_stats()
print(f"缓存命中率: {stats['cache_hit_rate']}")
print(f"WebSocket更新次数: {stats['ws_updates']}")

# 检查最后更新时间
last_update = dm.last_update.get('BTCUSDT_klines_1h', 0)
age_seconds = time.time() - last_update
print(f"K线数据年龄: {age_seconds:.1f}秒")
```

---

## 总结

### 核心优势

```
✅ 性能提升: 30-50倍（4-5分钟 → 5-10秒）
✅ API优化: -100%（1200-1600次 → 0次）
✅ 限流风险: 消除
✅ 数据新鲜度: <5秒
✅ 自动降级: WebSocket断线无感知
✅ 统一接口: 简化开发
✅ 可扩展: 易于添加新数据源
```

### 实施建议

1. **立即实施**: 测试验证（1-2天）
2. **短期实施**: 逐步迁移（1周）
3. **中期实施**: WebSocket实现（1-2周）
4. **长期维护**: 监控优化（持续）

### 预期收益

- **开发效率**: 减少API调用代码，统一数据访问
- **系统性能**: 扫描速度提升30-50倍
- **系统稳定**: 消除限流风险
- **用户体验**: 更快的信号生成

---

**文档版本**: v1.0
**最后更新**: 2025-10-29
**作者**: Claude
**状态**: ✅ 设计完成，待实施
