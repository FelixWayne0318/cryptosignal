# WebSocket管理规范

**规范版本**: v6.4 Phase 2
**生效日期**: 2025-11-02
**状态**: 生效中

> ⚠️ **核心原则**: 稳定性 > 实时性
> - 指数回退重连
> - 心跳监控 → DataQual降级
> - REST对账保证数据正确性

---

## 📋 目录

1. [总体原则](#1-总体原则)
2. [连接管理](#2-连接管理)
3. [重连策略](#3-重连策略)
4. [心跳监控](#4-心跳监控)
5. [数据对账](#5-数据对账)
6. [组合流订阅](#6-组合流订阅)
7. [缓存管理](#7-缓存管理)

---

## 1. 总体原则

### 1.1 设计理念

**稳定性优先**:
```
WebSocket断连 → 不影响系统运行
使用REST fallback → 数据质量降级 → 信号降级
```

**三层保护**:
1. **连接层**: 指数回退重连
2. **数据层**: 心跳监控 + REST对账
3. **质量层**: DataQual评分 → 降级策略

### 1.2 数据流架构

```
Binance WebSocket
        ↓
   连接池管理 (3-5个连接)
        ↓
   消息分发器
        ↓
   ├─ kline_1m → 本地缓存 (deque 500)
   ├─ kline_5m → 本地缓存 (deque 500)
   ├─ kline_15m → 本地缓存 (deque 500)
   ├─ kline_1h → 本地缓存 (deque 500)
   ├─ kline_4h → 本地缓存 (deque 500)
   └─ aggTrade → 本地缓存 (deque 1000)
        ↓
   心跳监控 (30s检查)
        ↓
   DataQual计算
        ↓
   REST对账 (5分钟)
```

---

## 2. 连接管理

### 2.1 连接池设计

**目标**: 控制连接数，提高稳定性

```python
class WebSocketConnectionPool:
    """
    WebSocket连接池

    管理3-5个连接，每个连接订阅多个流（组合流）
    """

    def __init__(self, max_connections=5):
        self.max_connections = max_connections
        self.connections = {}  # {conn_id: WebSocketConnection}
        self.stream_mapping = {}  # {stream_name: conn_id}

    def allocate_stream(self, stream_name):
        """
        为流分配连接

        策略: 负载均衡（选择流最少的连接）
        """
        if stream_name in self.stream_mapping:
            return self.stream_mapping[stream_name]

        # 找到流最少的连接
        conn_id = min(self.connections.keys(),
                      key=lambda cid: len(self.connections[cid].streams))

        # 分配
        self.stream_mapping[stream_name] = conn_id
        self.connections[conn_id].add_stream(stream_name)

        return conn_id

    def create_connection(self):
        """创建新连接"""
        conn_id = f"ws_{len(self.connections)}"
        conn = WebSocketConnection(conn_id)
        self.connections[conn_id] = conn
        return conn_id
```

### 2.2 连接状态

```
DISCONNECTED → CONNECTING → CONNECTED → SUBSCRIBED
      ↓              ↓            ↓            ↓
   FAILED       FAILED        LOST      RECONNECTING
      ↓              ↓            ↓            ↓
   RETRY        RETRY        RETRY           ...
```

**状态转换**:
```python
class ConnectionState(Enum):
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2
    SUBSCRIBED = 3
    LOST = 4
    RECONNECTING = 5
    FAILED = 6

class WebSocketConnection:
    def __init__(self, conn_id):
        self.conn_id = conn_id
        self.state = ConnectionState.DISCONNECTED
        self.ws = None
        self.streams = []
        self.last_message_time = {}
        self.retry_count = 0

    async def connect(self):
        """建立连接"""
        self.state = ConnectionState.CONNECTING

        try:
            self.ws = await websockets.connect(
                BINANCE_WS_URL,
                ping_interval=20,
                ping_timeout=10,
            )
            self.state = ConnectionState.CONNECTED
            log(f"{self.conn_id}: 连接成功")

        except Exception as e:
            self.state = ConnectionState.FAILED
            error(f"{self.conn_id}: 连接失败 - {e}")
            raise

    async def subscribe(self, streams):
        """订阅流"""
        subscribe_message = {
            "method": "SUBSCRIBE",
            "params": streams,
            "id": int(time.time() * 1000)
        }

        await self.ws.send(json.dumps(subscribe_message))
        self.state = ConnectionState.SUBSCRIBED
        self.streams = streams

        log(f"{self.conn_id}: 订阅成功 - {len(streams)}个流")
```

---

## 3. 重连策略

### 3.1 指数回退

**目的**: 避免频繁重连导致封IP

```python
class ExponentialBackoff:
    """
    指数回退策略

    delay = base * 2^retry_count + jitter
    """

    def __init__(self, base_delay=1.0, max_delay=60.0, jitter_ratio=0.1):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter_ratio = jitter_ratio
        self.retry_count = 0

    def get_delay(self) -> float:
        """计算延迟时间"""
        # 指数增长
        delay = self.base_delay * (2 ** self.retry_count)

        # 限制最大延迟
        delay = min(delay, self.max_delay)

        # 添加抖动（±10%）
        jitter = delay * self.jitter_ratio * (random.random() * 2 - 1)
        final_delay = max(0.1, delay + jitter)

        return final_delay

    def increment(self):
        """增加重试次数"""
        self.retry_count += 1

    def reset(self):
        """重置（连接成功后）"""
        self.retry_count = 0
```

**参数配置**:
```python
backoff_config = {
    'base_delay': 1.0,     # 基础延迟1秒
    'max_delay': 60.0,     # 最大延迟60秒
    'jitter_ratio': 0.1,   # ±10% 抖动
    'max_retries': 10,     # 最多重试10次
}
```

**重连时间序列示例**:
```
第1次: 1s + jitter
第2次: 2s + jitter
第3次: 4s + jitter
第4次: 8s + jitter
第5次: 16s + jitter
第6次: 32s + jitter
第7次: 60s + jitter (达到max)
第8次: 60s + jitter
...
```

### 3.2 重连逻辑

```python
async def auto_reconnect(connection):
    """
    自动重连

    失败后使用指数回退策略重试
    """
    backoff = ExponentialBackoff(**backoff_config)

    while backoff.retry_count < backoff_config['max_retries']:
        try:
            # 尝试连接
            await connection.connect()

            # 重新订阅
            await connection.subscribe(connection.streams)

            # 成功，重置回退
            backoff.reset()
            connection.retry_count = 0

            log(f"{connection.conn_id}: 重连成功")
            return True

        except Exception as e:
            # 失败，等待重试
            backoff.increment()
            delay = backoff.get_delay()

            error(f"{connection.conn_id}: 重连失败 (第{backoff.retry_count}次) - {e}")
            log(f"{connection.conn_id}: {delay:.1f}秒后重试")

            await asyncio.sleep(delay)

    # 超过最大重试次数
    error(f"{connection.conn_id}: 重连失败，超过最大重试次数")
    return False
```

### 3.3 连接断开检测

```python
async def detect_disconnect(connection):
    """
    检测连接断开

    方法:
    1. WebSocket异常
    2. Ping超时
    3. 心跳超时（60秒无消息）
    """
    try:
        # 1. 持续接收消息
        async for message in connection.ws:
            # 更新最后消息时间
            connection.last_message_time['any'] = time.time()

            # 处理消息
            await process_message(connection, message)

    except websockets.exceptions.ConnectionClosed:
        # 连接关闭
        warn(f"{connection.conn_id}: 连接断开（正常关闭）")
        connection.state = ConnectionState.LOST

    except websockets.exceptions.ConnectionClosedError as e:
        # 连接异常关闭
        error(f"{connection.conn_id}: 连接断开（异常）- {e}")
        connection.state = ConnectionState.LOST

    except asyncio.TimeoutError:
        # Ping超时
        error(f"{connection.conn_id}: Ping超时")
        connection.state = ConnectionState.LOST

    # 触发重连
    await auto_reconnect(connection)
```

---

## 4. 心跳监控

### 4.1 心跳检查

**目的**: 及时发现数据流中断

```python
async def heartbeat_monitor(connection, interval=30):
    """
    心跳监控

    每30秒检查一次最后消息时间
    超过60秒无消息 → DataQual降级
    """
    while connection.state in [ConnectionState.CONNECTED, ConnectionState.SUBSCRIBED]:
        await asyncio.sleep(interval)

        current_time = time.time()

        # 检查每个流的心跳
        missing_streams = []
        for stream in connection.streams:
            last_time = connection.last_message_time.get(stream, 0)
            elapsed = current_time - last_time

            if elapsed > 60:  # 60秒无消息
                missing_streams.append(stream)
                warn(f"{connection.conn_id}/{stream}: 心跳超时 ({elapsed:.0f}s)")

        # 更新DataQual
        if missing_streams:
            update_dataqual_for_missing_streams(missing_streams)
```

### 4.2 DataQual降级

**映射**: 缺失流数量 → DataQual下降

```python
def update_dataqual_for_missing_streams(missing_streams):
    """
    根据缺失流更新DataQual

    缺失1个流: DataQual - 0.10
    缺失2个流: DataQual - 0.20
    缺失3个流: DataQual - 0.30
    缺失全部: DataQual = 0.20
    """
    total_streams = 5  # 1m/5m/15m/1h/4h
    missing_count = len(missing_streams)

    if missing_count == 0:
        dataqual_penalty = 0.0
    elif missing_count == 1:
        dataqual_penalty = 0.10
    elif missing_count == 2:
        dataqual_penalty = 0.20
    elif missing_count == 3:
        dataqual_penalty = 0.30
    else:
        dataqual_penalty = 0.80  # 全部缺失 → 0.20

    # 应用惩罚
    for symbol in get_active_symbols():
        current_dataqual = get_dataqual(symbol)
        new_dataqual = max(0.0, current_dataqual - dataqual_penalty)
        set_dataqual(symbol, new_dataqual)

        if new_dataqual < 0.90:
            warn(f"{symbol}: DataQual降级到 {new_dataqual:.2f} (WebSocket流缺失)")
```

---

## 5. 数据对账

### 5.1 REST对账

**目的**: 确保WebSocket数据正确性

```python
async def rest_reconciliation(symbol, interval='1h', check_interval=300):
    """
    REST数据对账

    每5分钟检查一次WebSocket数据与REST数据是否一致
    """
    while True:
        await asyncio.sleep(check_interval)

        try:
            # 1. 获取WebSocket最新K线
            ws_kline = get_latest_kline_from_ws(symbol, interval)

            # 2. 获取REST K线
            rest_klines = get_klines_rest(symbol, interval, limit=2)
            rest_kline = rest_klines[-2]  # 倒数第二根（最新完成的）

            # 3. 对比
            if ws_kline and rest_kline:
                mismatch = check_kline_mismatch(ws_kline, rest_kline)

                if mismatch:
                    warn(f"{symbol}/{interval}: K线数据不一致")
                    warn(f"  WS: {ws_kline}")
                    warn(f"  REST: {rest_kline}")

                    # 更新DataQual（mismatch分量）
                    update_dataqual_mismatch(symbol, mismatch)

                    # 使用REST数据覆盖
                    replace_ws_kline_with_rest(symbol, interval, rest_kline)

        except Exception as e:
            error(f"{symbol}/{interval}: 对账失败 - {e}")

def check_kline_mismatch(ws_kline, rest_kline):
    """
    检查K线是否不一致

    检查字段: close, volume, high, low
    容忍度: 0.01% (close/high/low), 1% (volume)
    """
    mismatches = []

    # Close price
    close_diff = abs(ws_kline['close'] - rest_kline['close']) / rest_kline['close']
    if close_diff > 0.0001:  # 0.01%
        mismatches.append(f"close差异{close_diff:.4%}")

    # Volume
    vol_diff = abs(ws_kline['volume'] - rest_kline['volume']) / rest_kline['volume']
    if vol_diff > 0.01:  # 1%
        mismatches.append(f"volume差异{vol_diff:.2%}")

    # High
    high_diff = abs(ws_kline['high'] - rest_kline['high']) / rest_kline['high']
    if high_diff > 0.0001:
        mismatches.append(f"high差异{high_diff:.4%}")

    # Low
    low_diff = abs(ws_kline['low'] - rest_kline['low']) / rest_kline['low']
    if low_diff > 0.0001:
        mismatches.append(f"low差异{low_diff:.4%}")

    return mismatches if mismatches else None
```

### 5.2 深度快照对账

**目的**: 确保订单簿数据正确性

```python
async def depth_reconciliation(symbol, check_interval=60):
    """
    深度快照对账

    每1分钟检查WebSocket增量更新是否正确
    """
    while True:
        await asyncio.sleep(check_interval)

        try:
            # 1. 获取WebSocket订单簿状态
            ws_orderbook = get_orderbook_from_ws(symbol)
            ws_last_update_id = ws_orderbook['lastUpdateId']

            # 2. 获取REST快照
            rest_snapshot = get_depth_snapshot_rest(symbol, limit=100)
            rest_last_update_id = rest_snapshot['lastUpdateId']

            # 3. 检查差距
            id_gap = rest_last_update_id - ws_last_update_id

            if id_gap > 100:
                # 差距过大，重新同步
                warn(f"{symbol}: 订单簿更新ID差距过大 ({id_gap})")
                resync_orderbook(symbol, rest_snapshot)

            elif id_gap < 0:
                # WebSocket领先（正常）
                pass

        except Exception as e:
            error(f"{symbol}: 订单簿对账失败 - {e}")

def resync_orderbook(symbol, rest_snapshot):
    """使用REST快照重新同步订单簿"""
    orderbook_cache[symbol] = {
        'bids': rest_snapshot['bids'],
        'asks': rest_snapshot['asks'],
        'lastUpdateId': rest_snapshot['lastUpdateId'],
        'synced_at': time.time(),
    }
    log(f"{symbol}: 订单簿已重新同步")
```

---

## 6. 组合流订阅

### 6.1 组合流设计

**目标**: 减少连接数，提高稳定性

```python
def create_combined_streams(symbols, intervals):
    """
    创建组合流

    策略: 将多个流合并到一个WebSocket连接
    限制: 每个连接最多200个流
    """
    combined_streams = []

    # 构建流名称
    for symbol in symbols:
        for interval in intervals:
            stream_name = f"{symbol.lower()}@kline_{interval}"
            combined_streams.append(stream_name)

    # 分组（每200个流一组）
    stream_groups = [
        combined_streams[i:i+200]
        for i in range(0, len(combined_streams), 200)
    ]

    return stream_groups
```

**推荐配置**:
```python
# 配置1: 少量币种（<40个）
stream_groups = [
    ["btcusdt@kline_1m", "btcusdt@kline_5m", "btcusdt@kline_15m",
     "btcusdt@kline_1h", "btcusdt@kline_4h",
     "ethusdt@kline_1m", "ethusdt@kline_5m", ...],  # 所有流在1个连接
]

# 配置2: 大量币种（200个）
stream_groups = [
    # 连接1: 1m K线
    [f"{s}@kline_1m" for s in symbols],

    # 连接2: 5m + 15m K线
    [f"{s}@kline_5m" for s in symbols] + [f"{s}@kline_15m" for s in symbols],

    # 连接3: 1h + 4h K线
    [f"{s}@kline_1h" for s in symbols] + [f"{s}@kline_4h" for s in symbols],

    # 连接4: aggTrade
    [f"{s}@aggTrade" for s in symbols[:100]],

    # 连接5: aggTrade (剩余)
    [f"{s}@aggTrade" for s in symbols[100:]],
]
```

### 6.2 URL构建

```python
def build_websocket_url(streams, use_combined=True):
    """
    构建WebSocket URL

    组合流: wss://fstream.binance.com/stream?streams=xxx
    单流: wss://fstream.binance.com/ws/xxx
    """
    base_url = "wss://fstream.binance.com"

    if use_combined and len(streams) > 1:
        # 组合流
        streams_param = "/".join(streams)
        url = f"{base_url}/stream?streams={streams_param}"
    else:
        # 单流
        stream_name = streams[0]
        url = f"{base_url}/ws/{stream_name}"

    return url
```

---

## 7. 缓存管理

### 7.1 本地K线缓存

**数据结构**: deque（双端队列）

```python
from collections import deque

class KlineCache:
    """K线缓存"""

    def __init__(self, max_size=500):
        self.cache = {}  # {(symbol, interval): deque}
        self.max_size = max_size

    def add(self, symbol, interval, kline):
        """添加K线"""
        key = (symbol, interval)

        if key not in self.cache:
            self.cache[key] = deque(maxlen=self.max_size)

        # 检查是否已存在（避免重复）
        if self.cache[key] and self.cache[key][-1]['t'] == kline['t']:
            # 更新最后一根（未完成的K线）
            self.cache[key][-1] = kline
        else:
            # 添加新K线
            self.cache[key].append(kline)

    def get(self, symbol, interval, limit=None):
        """获取K线"""
        key = (symbol, interval)

        if key not in self.cache:
            return []

        klines = list(self.cache[key])

        if limit:
            return klines[-limit:]
        else:
            return klines

    def get_latest(self, symbol, interval):
        """获取最新K线"""
        key = (symbol, interval)

        if key not in self.cache or not self.cache[key]:
            return None

        return self.cache[key][-1]
```

### 7.2 aggTrade缓存

```python
class AggTradeCache:
    """聚合成交缓存"""

    def __init__(self, max_size=1000, time_window=60):
        self.cache = {}  # {symbol: deque}
        self.max_size = max_size
        self.time_window = time_window  # 保留最近60秒

    def add(self, symbol, trade):
        """添加成交"""
        if symbol not in self.cache:
            self.cache[symbol] = deque(maxlen=self.max_size)

        self.cache[symbol].append(trade)

        # 清理过期数据
        self.cleanup(symbol)

    def cleanup(self, symbol):
        """清理过期数据（超过time_window秒）"""
        if symbol not in self.cache:
            return

        current_time = time.time() * 1000  # 毫秒
        cutoff_time = current_time - self.time_window * 1000

        # 移除过期数据
        while self.cache[symbol] and self.cache[symbol][0]['T'] < cutoff_time:
            self.cache[symbol].popleft()

    def get_recent(self, symbol, seconds=60):
        """获取最近N秒的成交"""
        self.cleanup(symbol)

        if symbol not in self.cache:
            return []

        return list(self.cache[symbol])
```

---

## 8. 消息处理

### 8.1 消息分发

```python
async def process_message(connection, message):
    """
    处理WebSocket消息

    消息格式:
    {
        "stream": "btcusdt@kline_1m",
        "data": {...}
    }
    """
    try:
        msg = json.loads(message)

        # 组合流消息
        if 'stream' in msg:
            stream_name = msg['stream']
            data = msg['data']
        else:
            # 单流消息（不推荐）
            stream_name = connection.streams[0] if connection.streams else None
            data = msg

        # 更新心跳
        connection.last_message_time[stream_name] = time.time()

        # 分发到处理器
        if '@kline_' in stream_name:
            await process_kline_message(stream_name, data)
        elif '@aggTrade' in stream_name:
            await process_aggtrade_message(stream_name, data)
        elif '@depth' in stream_name:
            await process_depth_message(stream_name, data)
        elif '@markPrice' in stream_name:
            await process_markprice_message(stream_name, data)

    except Exception as e:
        error(f"{connection.conn_id}: 消息处理失败 - {e}")

async def process_kline_message(stream_name, data):
    """处理K线消息"""
    # 解析stream_name: "btcusdt@kline_1m"
    parts = stream_name.split('@')
    symbol = parts[0].upper()
    interval = parts[1].replace('kline_', '')

    # 提取K线数据
    kline = data['k']
    kline_data = {
        't': kline['t'],           # 开盘时间
        'o': float(kline['o']),    # 开盘价
        'h': float(kline['h']),    # 最高价
        'l': float(kline['l']),    # 最低价
        'c': float(kline['c']),    # 收盘价
        'v': float(kline['v']),    # 成交量
        'x': kline['x'],           # K线是否完结
    }

    # 添加到缓存
    kline_cache.add(symbol, interval, kline_data)

    # 如果K线完结，触发回调
    if kline_data['x']:
        await on_kline_close(symbol, interval, kline_data)
```

---

## 9. 配置示例

### 9.1 config/websocket.json

```json
{
  "websocket": {
    "base_url": "wss://fstream.binance.com",
    "connection_pool": {
      "max_connections": 5,
      "max_streams_per_connection": 200
    },
    "reconnect": {
      "base_delay": 1.0,
      "max_delay": 60.0,
      "jitter_ratio": 0.1,
      "max_retries": 10
    },
    "heartbeat": {
      "check_interval": 30,
      "timeout": 60
    },
    "reconciliation": {
      "kline_interval": 300,
      "depth_interval": 60,
      "mismatch_tolerance": {
        "price": 0.0001,
        "volume": 0.01
      }
    },
    "cache": {
      "kline_max_size": 500,
      "aggtrade_max_size": 1000,
      "aggtrade_time_window": 60
    },
    "ping": {
      "interval": 20,
      "timeout": 10
    }
  }
}
```

---

## 10. 实现模块

**代码位置**: `ats_core/data_feeds/`

```
ats_core/data_feeds/
├── ws_manager.py          # WebSocket管理器
├── ws_connection.py       # 连接类
├── ws_pool.py             # 连接池
├── ws_backoff.py          # 指数回退
├── ws_heartbeat.py        # 心跳监控
├── ws_reconciliation.py   # 数据对账
├── kline_cache.py         # K线缓存
└── aggtrade_cache.py      # aggTrade缓存
```

---

## 11. 新币WebSocket (Phase 2已实现)

**特殊处理**: 新币需要1m/5m/15m高频数据

```python
class NewCoinWSFeed:
    """
    新币WebSocket订阅

    订阅: kline_1m/5m/15m
    心跳: 30秒检查
    降级: 缺失流 → DataQual下降
    """

    async def subscribe_newcoin(self, symbol):
        """订阅新币流"""
        streams = [
            f"{symbol.lower()}@kline_1m",
            f"{symbol.lower()}@kline_5m",
            f"{symbol.lower()}@kline_15m",
        ]

        conn_id = self.pool.allocate_stream(f"newcoin_{symbol}")
        await self.pool.connections[conn_id].subscribe(streams)
```

**详见**: [NEWCOIN.md § 8 WebSocket稳定性](NEWCOIN.md#8-websocket稳定性phase-2-部分实现)

---

## 12. 相关文档

- **数据层**: [DATA_LAYER.md](DATA_LAYER.md)
- **DataQual**: [DATAQUAL.md](DATAQUAL.md)
- **新币通道**: [NEWCOIN.md](NEWCOIN.md)
- **核心规范**: [../CORE_STANDARDS.md](../CORE_STANDARDS.md)

---

**规范版本**: v6.4-phase2-websocket
**维护**: 数据基础设施团队
**审核**: 系统架构师
**最后更新**: 2025-11-02
