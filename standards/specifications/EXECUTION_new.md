# 执行系统详细规范

**规范版本**: v6.4 Phase 2
**生效日期**: 2025-11-02
**状态**: 生效中

> ⚠️ **核心原则**: 执行可成交优先
> - 止损必须可成交（stop-market/分片）
> - 止盈优先厚区maker单
> - 硬闸控制执行风险

---

## 📋 目录

1. [总体原则](#1-总体原则)
2. [硬闸系统](#2-硬闸系统)
3. [入场策略](#3-入场策略)
4. [止损系统](#4-止损系统)
5. [止盈系统](#5-止盈系统)
6. [订单管理](#6-订单管理)
7. [滑点控制](#7-滑点控制)
8. [厚区检测](#8-厚区检测)

---

## 1. 总体原则

### 1.1 设计理念

**核心思想**: 执行可成交 > 完美价格

```
优先级排序:
1. 止损可成交 (生存第一)
2. 开仓合理性 (控制滑点)
3. 止盈优化 (提高收益)
```

### 1.2 执行链路

```
信号生成 → 硬闸检查 → 入场执行 → 止损设置 → 止盈设置 → 持仓管理 → 平仓执行
    ↓          ↓          ↓          ↓          ↓          ↓          ↓
  概率分      四门       订单       追踪SL     厚区TP     TTL监控    成交确认
```

---

## 2. 硬闸系统

### 2.1 硬闸定义

**目的**: 在执行前拦截高风险交易

**四个硬闸** (全部通过才能开仓):
1. **Impact闸** - 冲击成本控制
2. **Spread闸** - 点差控制
3. **OBI闸** - 订单簿失衡控制
4. **DataQual闸** - 数据质量控制

### 2.2 开仓/维持滞回

**目的**: 防止边界抖动

| 硬闸 | 开仓阈值 | 维持阈值 | 说明 |
|------|----------|----------|------|
| **Impact** | ≤ 7 bps | ≤ 8 bps | 冲击成本 |
| **Spread** | ≤ 35 bps | ≤ 38 bps | 买卖价差 |
| **OBI** | \|OBI\| ≤ 0.30 | \|OBI\| ≤ 0.33 | 订单簿失衡 |
| **DataQual** | ≥ 0.90 | ≥ 0.88 | 数据质量 |
| **Room** | ≥ R* · ATR | ≥ R* · ATR * 0.9 | 空间充足度 |

**R*系数**:
```python
R_star = {
    "1h": 0.6,   # 成熟币1h粒度
    "1m": 0.6,   # 新币1m粒度
}
```

### 2.3 冷却期

**关闸后冷却**: 任一硬闸失败后，等待N秒再检查

```python
cooldown_config = {
    "impact_fail": 120,      # 冲击成本过高，等待2分钟
    "spread_fail": 90,       # 点差过大，等待1.5分钟
    "obi_fail": 60,          # OBI失衡，等待1分钟
    "dataqual_fail": 180,    # 数据质量差，等待3分钟
}
```

### 2.4 硬闸计算

#### 2.4.1 Impact (冲击成本)

```python
def calculate_impact_bps(orderbook, notional_usdt: float) -> float:
    """
    计算指定名义金额的冲击成本

    Args:
        orderbook: 订单簿数据
        notional_usdt: 名义金额（USDT）

    Returns:
        impact_bps: 冲击成本（基点）
    """
    mid_price = (orderbook['best_bid'] + orderbook['best_ask']) / 2

    # 计算买入/卖出的平均成交价
    avg_buy_price = calculate_vwap(orderbook['asks'], notional_usdt)
    avg_sell_price = calculate_vwap(orderbook['bids'], notional_usdt)

    # 冲击成本 = |avg_price - mid_price| / mid_price * 10000
    impact_buy_bps = abs(avg_buy_price - mid_price) / mid_price * 10000
    impact_sell_bps = abs(avg_sell_price - mid_price) / mid_price * 10000

    # 返回最大值（最坏情况）
    return max(impact_buy_bps, impact_sell_bps)

def calculate_vwap(orders, notional: float) -> float:
    """计算指定金额的VWAP"""
    total_value = 0
    total_volume = 0

    for price, volume in orders:
        available = min(volume * price, notional - total_value)
        total_value += available
        total_volume += available / price

        if total_value >= notional:
            break

    return total_value / total_volume if total_volume > 0 else orders[0][0]
```

**标准名义金额**: 100,000 USDT

#### 2.4.2 Spread (点差)

```python
def calculate_spread_bps(orderbook) -> float:
    """
    计算买卖价差

    Returns:
        spread_bps: 价差（基点）
    """
    best_bid = orderbook['best_bid']
    best_ask = orderbook['best_ask']
    mid_price = (best_bid + best_ask) / 2

    spread_bps = (best_ask - best_bid) / mid_price * 10000
    return spread_bps
```

#### 2.4.3 OBI (订单簿失衡)

```python
def calculate_obi(orderbook, levels: int = 10) -> float:
    """
    计算订单簿失衡指标

    Args:
        orderbook: 订单簿
        levels: 深度层数（默认10档）

    Returns:
        OBI ∈ [-1, 1]
        > 0: 买盘强（多头优势）
        < 0: 卖盘强（空头优势）
    """
    bid_volume = sum(vol for price, vol in orderbook['bids'][:levels])
    ask_volume = sum(vol for price, vol in orderbook['asks'][:levels])

    total_volume = bid_volume + ask_volume
    if total_volume == 0:
        return 0.0

    obi = (bid_volume - ask_volume) / total_volume
    return obi
```

#### 2.4.4 Room (空间充足度)

```python
def calculate_room(symbol, direction: str, entry_price: float, atr: float) -> float:
    """
    计算到阻力/支撑的距离

    Args:
        symbol: 交易对
        direction: 'long' or 'short'
        entry_price: 入场价格
        atr: ATR值

    Returns:
        room_atr_ratio: 空间/ATR比值
    """
    # 获取最近72根K线的高低点
    klines = get_klines(symbol, interval='1h', limit=72)

    if direction == 'long':
        # 多头：到上方阻力的距离
        resistance = find_resistance(klines, entry_price)
        room = resistance - entry_price
    else:
        # 空头：到下方支撑的距离
        support = find_support(klines, entry_price)
        room = entry_price - support

    room_atr_ratio = room / atr
    return room_atr_ratio

def find_resistance(klines, entry_price):
    """查找上方最近阻力位"""
    highs = [k['high'] for k in klines]

    # 查找entry_price上方的高点
    resistance_levels = [h for h in highs if h > entry_price]

    if not resistance_levels:
        # 无阻力，返回最高价 * 1.05
        return max(highs) * 1.05

    # 返回最近的阻力（最小的那个）
    return min(resistance_levels)
```

---

## 3. 入场策略

### 3.1 回撤接力（优先）

**理念**: 在价格回调时以更好价格入场

```python
def entry_pullback(signal, klines, atr):
    """
    回撤接力入场

    逻辑:
    1. 计算锚点价格（AVWAP或ZLEMA）
    2. 设置挂单带宽（±0.1 ATR）
    3. 等待价格回调到挂单区
    4. maker单成交
    """
    # 1. 选择锚点
    if signal['new_coin']['is_new']:
        anchor = signal['new_coin']['avwap']  # 新币用AVWAP
    else:
        zlema_10 = calculate_zlema(klines, halflife=10)
        anchor = zlema_10[-1]  # 成熟币用ZLEMA(10, 1h)

    # 2. 挂单带宽
    bandwidth = 0.1 * atr

    # 3. 挂单价格
    if signal['direction'] == 'long':
        entry_price = anchor - bandwidth  # 多头：锚点下方挂单
    else:
        entry_price = anchor + bandwidth  # 空头：锚点上方挂单

    # 4. 限价单（maker）
    order = {
        'type': 'LIMIT',
        'side': 'BUY' if signal['direction'] == 'long' else 'SELL',
        'price': entry_price,
        'quantity': calculate_position_size(signal, entry_price),
        'timeInForce': 'GTC',  # Good Till Cancel
    }

    return order
```

**挂单超时**: 5分钟未成交 → 取消 → 转突破带策略

### 3.2 突破带（备选）

**理念**: 价格突破关键位时追踪入场

```python
def entry_breakout(signal, current_price, atr, impact_bps):
    """
    突破带入场

    逻辑:
    1. 计算突破带宽度
    2. 市价单入场
    3. 限制滑点
    """
    # 1. 突破带宽度
    delta_atr = 0.05 * atr
    delta_impact = min(0.10 * atr, 3 * impact_bps / 10000 * current_price)
    delta_in = delta_atr + delta_impact

    # 2. 入场价格（限价保护）
    if signal['direction'] == 'long':
        max_entry_price = current_price + delta_in
        order_type = 'LIMIT'
        price = max_entry_price
    else:
        min_entry_price = current_price - delta_in
        order_type = 'LIMIT'
        price = min_entry_price

    # 3. 订单
    order = {
        'type': order_type,
        'side': 'BUY' if signal['direction'] == 'long' else 'SELL',
        'price': price,
        'quantity': calculate_position_size(signal, price),
        'timeInForce': 'IOC',  # Immediate or Cancel
    }

    return order
```

### 3.3 仓位计算

```python
def calculate_position_size(signal, entry_price):
    """
    计算仓位大小

    考虑因素:
    1. 账户权益
    2. 单笔风险限制（1-2%）
    3. 信号强度
    4. 杠杆
    """
    account_equity = get_account_equity()  # 账户权益（USDT）

    # 单笔风险（账户权益的1%）
    risk_per_trade = account_equity * 0.01

    # 预计止损距离（ATR的1.8倍）
    stop_distance = signal['pricing']['sl0']

    # 仓位大小 = 风险金额 / 止损距离
    position_size_base = risk_per_trade / stop_distance

    # 根据信号强度调整（0.5x - 1.5x）
    strength_multiplier = map_strength_to_multiplier(signal['probability'])

    position_size = position_size_base * strength_multiplier

    # 转换为合约张数（向下取整）
    contract_size = get_contract_size(signal['symbol'])
    quantity = int(position_size / (entry_price * contract_size)) * contract_size

    return quantity

def map_strength_to_multiplier(probability):
    """
    根据概率映射仓位倍数

    p=0.50 → 0.5x
    p=0.60 → 0.8x
    p=0.70 → 1.0x
    p=0.80 → 1.2x
    p=0.90 → 1.5x
    """
    if probability < 0.60:
        return 0.5
    elif probability < 0.70:
        return 0.5 + (probability - 0.60) * 3  # 0.5 → 0.8
    elif probability < 0.80:
        return 0.8 + (probability - 0.70) * 2  # 0.8 → 1.0
    elif probability < 0.90:
        return 1.0 + (probability - 0.80) * 2  # 1.0 → 1.2
    else:
        return 1.2 + (probability - 0.90) * 3  # 1.2 → 1.5
```

---

## 4. 止损系统

### 4.1 SL0 (初始止损)

**原则**: 可成交优先

```python
def calculate_sl0(signal, entry_price, atr, klines):
    """
    计算初始止损

    使用softmin选择结构保护和ATR保护的较小值
    """
    direction = signal['direction']

    # 1. 结构保护距离
    if direction == 'long':
        # 多头：最近的结构低点
        structural_low = find_swing_low(klines, lookback=14)
        d_struct = entry_price - structural_low
    else:
        # 空头：最近的结构高点
        structural_high = find_swing_high(klines, lookback=14)
        d_struct = structural_high - entry_price

    # 2. ATR保护距离
    d_atr = 1.8 * atr

    # 3. softmin（连续过渡，避免硬切换）
    tau = 0.1 * atr  # 软化参数
    sl_distance = softmin(d_struct, d_atr, tau)

    # 4. 止损价格
    if direction == 'long':
        sl_price = entry_price - sl_distance
    else:
        sl_price = entry_price + sl_distance

    return sl_price, sl_distance

def softmin(a, b, tau):
    """
    软最小值（连续可微）

    当a≈b时，返回值平滑过渡
    """
    import math
    exp_a = math.exp(-a / tau)
    exp_b = math.exp(-b / tau)
    return -tau * math.log(exp_a + exp_b)

def find_swing_low(klines, lookback=14):
    """查找最近的摆动低点"""
    lows = [k['low'] for k in klines[-lookback:]]
    return min(lows)

def find_swing_high(klines, lookback=14):
    """查找最近的摆动高点"""
    highs = [k['high'] for k in klines[-lookback:]]
    return max(highs)
```

### 4.2 追踪止损 (Chandelier)

**动态调整**: 随价格有利移动而收紧止损

```python
def update_trailing_stop(position, klines, atr):
    """
    更新追踪止损（Chandelier方法）

    逻辑:
    1. 计算最高/最低点（窗口N）
    2. 减去/加上k倍ATR
    3. 与结构保护、盈亏平衡比较
    4. 使用softmin选择
    """
    direction = position['direction']
    entry_price = position['entry_price']
    current_price = klines[-1]['close']

    # 1. 窗口大小（随持仓时间增加）
    bars_held = position['bars_held']
    N = min(8 + bars_held // 10, 14)  # 8 → 14逐渐扩大

    # 2. ATR倍数
    if direction == 'long':
        k = 1.6  # 多头k稍大（给更多空间）
    else:
        k = 1.4  # 空头k稍小（收紧更快）

    # 3. Chandelier止损
    if direction == 'long':
        highest_high = max(k['high'] for k in klines[-N:])
        chandelier_sl = highest_high - k * atr
    else:
        lowest_low = min(k['low'] for k in klines[-N:])
        chandelier_sl = lowest_low + k * atr

    # 4. 结构保护（最近的支撑/阻力）
    if direction == 'long':
        structural_sl = find_swing_low(klines, lookback=N) * 0.995  # 稍低于结构
    else:
        structural_sl = find_swing_high(klines, lookback=N) * 1.005  # 稍高于结构

    # 5. 盈亏平衡（BE）
    be_price = entry_price

    # 6. softmin选择（取最有利的）
    tau = 0.05 * atr
    if direction == 'long':
        sl_price = max(
            softmin(chandelier_sl, structural_sl, tau),
            be_price  # 不低于BE
        )
    else:
        sl_price = min(
            softmax(chandelier_sl, structural_sl, tau),
            be_price  # 不高于BE
        )

    # 7. 确保止损只能收紧，不能放宽
    current_sl = position['stop_loss']
    if direction == 'long':
        new_sl = max(sl_price, current_sl)
    else:
        new_sl = min(sl_price, current_sl)

    return new_sl

def softmax(a, b, tau):
    """软最大值"""
    import math
    exp_a = math.exp(a / tau)
    exp_b = math.exp(b / tau)
    return tau * math.log(exp_a + exp_b)
```

### 4.3 止损触发与执行

**触发条件** (全部满足):
```python
def check_stop_loss_trigger(position, current_kline, orderbook):
    """
    检查止损是否触发

    条件（全部满足）:
    1. 价格穿越止损价 ≥ 2 tick
    2. 持续时间 ≥ 300ms
    3. AggTrade/OBI同向确认
    """
    sl_price = position['stop_loss']
    direction = position['direction']

    # 1. 价格穿越
    if direction == 'long':
        price_breach = (current_kline['low'] <= sl_price)
        tick_breach = (sl_price - current_kline['low']) >= 2 * get_tick_size(position['symbol'])
    else:
        price_breach = (current_kline['high'] >= sl_price)
        tick_breach = (current_kline['high'] - sl_price) >= 2 * get_tick_size(position['symbol'])

    if not (price_breach and tick_breach):
        return False, "价格未充分穿越"

    # 2. 持续时间
    if current_kline['close_time'] - position['sl_touch_time'] < 300:
        return False, "持续时间不足"

    # 3. AggTrade/OBI确认
    agg_trades = get_recent_agg_trades(position['symbol'], seconds=5)
    obi = calculate_obi(orderbook)

    if direction == 'long':
        # 多头止损：需要卖压
        agg_sell_ratio = sum(t['qty'] for t in agg_trades if not t['is_buyer_maker']) / sum(t['qty'] for t in agg_trades)
        confirmed = (agg_sell_ratio >= 0.55) or (obi <= -0.10)
    else:
        # 空头止损：需要买压
        agg_buy_ratio = sum(t['qty'] for t in agg_trades if t['is_buyer_maker']) / sum(t['qty'] for t in agg_trades)
        confirmed = (agg_buy_ratio >= 0.55) or (obi >= 0.10)

    if not confirmed:
        return False, "AggTrade/OBI未确认"

    return True, "止损触发"
```

**执行方式**:
```python
def execute_stop_loss(position):
    """
    执行止损

    方式: STOP_MARKET（确保成交）
    """
    direction = position['direction']
    sl_price = position['stop_loss']
    quantity = position['quantity']

    # STOP_MARKET订单（价格到达即市价成交）
    order = {
        'type': 'STOP_MARKET',
        'side': 'SELL' if direction == 'long' else 'BUY',
        'stopPrice': sl_price,
        'quantity': quantity,
    }

    # 提交订单
    result = submit_order(position['symbol'], order)

    # 记录
    log_stop_loss(position, result)

    return result
```

---

## 5. 止盈系统

### 5.1 厚区检测

**目的**: 找到订单簿深度峰值位置，作为TP目标

```python
def detect_shelves(orderbook, atr, direction):
    """
    检测厚区（订单簿深度峰值）

    方法:
    1. 将订单簿分桶（每±5 bps一个桶）
    2. 计算每个桶的深度
    3. 找到深度 ≥ μ + 2σ 的桶
    4. 返回厚区价格
    """
    mid_price = (orderbook['best_bid'] + orderbook['best_ask']) / 2
    bucket_size_bps = 5  # 5个基点一个桶

    # 选择买盘或卖盘
    if direction == 'long':
        # 多头：在卖盘（ask）中找厚区
        orders = orderbook['asks']
        search_range = (mid_price, mid_price + 3 * atr)  # 向上3倍ATR
    else:
        # 空头：在买盘（bid）中找厚区
        orders = orderbook['bids']
        search_range = (mid_price - 3 * atr, mid_price)  # 向下3倍ATR

    # 分桶
    buckets = {}
    for price, volume in orders:
        if not (search_range[0] <= price <= search_range[1]):
            continue

        # 计算桶索引
        bps_from_mid = (price - mid_price) / mid_price * 10000
        bucket_idx = int(bps_from_mid / bucket_size_bps)

        if bucket_idx not in buckets:
            buckets[bucket_idx] = {'total_volume': 0, 'avg_price': 0, 'count': 0}

        buckets[bucket_idx]['total_volume'] += volume
        buckets[bucket_idx]['avg_price'] += price * volume
        buckets[bucket_idx]['count'] += 1

    # 计算平均价格
    for idx in buckets:
        buckets[idx]['avg_price'] /= buckets[idx]['total_volume']

    # 找峰值桶（深度 ≥ μ + 2σ）
    volumes = [b['total_volume'] for b in buckets.values()]
    mean_volume = sum(volumes) / len(volumes)
    std_volume = (sum((v - mean_volume) ** 2 for v in volumes) / len(volumes)) ** 0.5

    threshold = mean_volume + 2 * std_volume

    shelves = []
    for idx, bucket in buckets.items():
        if bucket['total_volume'] >= threshold:
            shelves.append({
                'price': bucket['avg_price'],
                'volume': bucket['total_volume'],
                'bps_from_mid': idx * bucket_size_bps,
            })

    # 按距离排序（最近的优先）
    shelves.sort(key=lambda s: abs(s['price'] - mid_price))

    return shelves
```

### 5.2 止盈策略

```python
def calculate_take_profit(position, entry_price, atr, orderbook, room):
    """
    计算止盈价格

    策略:
    1. 检测厚区
    2. 如果有厚区：在入口/中段挂maker单
    3. 如果无厚区：不挂TP，手动平仓
    """
    direction = position['direction']

    # 1. 检测厚区
    shelves = detect_shelves(orderbook, atr, direction)

    if not shelves:
        # 无厚区：不设止盈
        return None, "no_shelf"

    # 2. 选择厚区（最近的，且R ≥ 1.0）
    min_r = 1.0
    selected_shelf = None

    for shelf in shelves:
        # 计算R倍数
        if direction == 'long':
            r = (shelf['price'] - entry_price) / (entry_price - position['stop_loss'])
        else:
            r = (entry_price - shelf['price']) / (position['stop_loss'] - entry_price)

        if r >= min_r:
            selected_shelf = shelf
            break

    if not selected_shelf:
        return None, "r_too_small"

    # 3. TP价格（厚区入口或中段）
    shelf_price = selected_shelf['price']

    # 入口策略：厚区前5 bps
    if direction == 'long':
        tp_price = shelf_price * (1 - 0.0005)  # 稍低于厚区
    else:
        tp_price = shelf_price * (1 + 0.0005)  # 稍高于厚区

    return tp_price, selected_shelf

def execute_take_profit(position, tp_price):
    """
    执行止盈

    方式: LIMIT（maker单，降低手续费）
    """
    direction = position['direction']
    quantity = position['quantity']

    # 限价单（maker）
    order = {
        'type': 'LIMIT',
        'side': 'SELL' if direction == 'long' else 'BUY',
        'price': tp_price,
        'quantity': quantity,
        'timeInForce': 'GTC',
    }

    result = submit_order(position['symbol'], order)

    return result

def manage_take_profit(position, orderbook):
    """
    管理止盈订单

    逻辑: 20秒无成交 → 上移1-2 tick
    """
    tp_order = position.get('tp_order')
    if not tp_order:
        return

    # 检查成交状态
    order_status = get_order_status(tp_order['orderId'])

    if order_status['status'] == 'FILLED':
        # 已成交
        log_take_profit(position, order_status)
        return

    # 检查时长
    elapsed = time.time() - tp_order['created_at']
    if elapsed < 20:
        return  # 未到20秒

    # 上移1-2 tick
    direction = position['direction']
    tick_size = get_tick_size(position['symbol'])
    current_tp = tp_order['price']

    if direction == 'long':
        new_tp = current_tp + 2 * tick_size  # 向上移动
    else:
        new_tp = current_tp - 2 * tick_size  # 向下移动

    # 取消旧订单，下新订单
    cancel_order(tp_order['orderId'])
    new_order = execute_take_profit(position, new_tp)

    position['tp_order'] = new_order
```

---

## 6. 订单管理

### 6.1 订单状态机

```
PENDING → SUBMITTED → PARTIAL_FILLED → FILLED
   ↓          ↓             ↓              ↓
CANCELLED  REJECTED      CANCELLED     CLOSED
```

### 6.2 订单跟踪

```python
class OrderManager:
    """订单管理器"""

    def __init__(self):
        self.active_orders = {}  # {order_id: order_data}
        self.order_history = []

    def submit_order(self, symbol, order_params):
        """提交订单"""
        # 1. 提交到交易所
        result = exchange_api.create_order(symbol, **order_params)

        # 2. 记录订单
        order_data = {
            'orderId': result['orderId'],
            'symbol': symbol,
            'type': order_params['type'],
            'side': order_params['side'],
            'price': order_params.get('price'),
            'quantity': order_params['quantity'],
            'status': 'SUBMITTED',
            'created_at': time.time(),
            'fills': [],
        }

        self.active_orders[result['orderId']] = order_data

        # 3. 异步监控
        asyncio.create_task(self.monitor_order(result['orderId']))

        return order_data

    async def monitor_order(self, order_id):
        """监控订单状态"""
        while order_id in self.active_orders:
            # 查询订单状态
            status = exchange_api.get_order(order_id)

            # 更新本地状态
            self.active_orders[order_id]['status'] = status['status']

            if status['status'] in ['FILLED', 'CANCELED', 'REJECTED', 'EXPIRED']:
                # 订单结束
                self.order_history.append(self.active_orders[order_id])
                del self.active_orders[order_id]
                break

            # 检查部分成交
            if status['status'] == 'PARTIALLY_FILLED':
                self.active_orders[order_id]['fills'].append({
                    'price': status['avgPrice'],
                    'quantity': status['executedQty'],
                    'time': time.time(),
                })

            await asyncio.sleep(1)  # 1秒检查一次

    def cancel_order(self, order_id):
        """取消订单"""
        exchange_api.cancel_order(order_id)
        if order_id in self.active_orders:
            self.active_orders[order_id]['status'] = 'CANCELING'
```

### 6.3 订单分片（大单）

```python
def slice_large_order(symbol, side, total_quantity, max_quantity_per_order):
    """
    大单分片执行

    目的: 减少市场冲击
    """
    slices = []
    remaining = total_quantity

    while remaining > 0:
        slice_qty = min(remaining, max_quantity_per_order)
        slices.append(slice_qty)
        remaining -= slice_qty

    # 执行分片
    for i, qty in enumerate(slices):
        order = {
            'type': 'LIMIT',
            'side': side,
            'quantity': qty,
            'price': get_adaptive_price(symbol, side, i),  # 价格略微调整
            'timeInForce': 'IOC',  # 立即成交或取消
        }

        result = submit_order(symbol, order)

        # 间隔100-200ms
        time.sleep(0.1 + random.random() * 0.1)

    return slices
```

---

## 7. 滑点控制

### 7.1 预期滑点

```python
def estimate_slippage(symbol, side, quantity, orderbook):
    """
    估算滑点

    Returns:
        slippage_bps: 预期滑点（基点）
    """
    mid_price = (orderbook['best_bid'] + orderbook['best_ask']) / 2

    # 计算VWAP
    if side == 'BUY':
        avg_price = calculate_vwap(orderbook['asks'], quantity * mid_price)
    else:
        avg_price = calculate_vwap(orderbook['bids'], quantity * mid_price)

    slippage_bps = abs(avg_price - mid_price) / mid_price * 10000
    return slippage_bps
```

### 7.2 滑点限制

```python
# 滑点限制配置
slippage_limits = {
    'entry': 15,      # 入场最大滑点 15 bps
    'exit': 20,       # 出场最大滑点 20 bps
    'stop_loss': 50,  # 止损最大滑点 50 bps（优先成交）
}

def check_slippage_limit(order_type, estimated_slippage):
    """检查滑点是否在限制内"""
    limit = slippage_limits.get(order_type, 20)
    return estimated_slippage <= limit
```

---

## 8. 厚区检测

### 8.1 动态桶宽

```python
def get_bucket_size(symbol, volatility):
    """
    根据波动性动态调整桶宽

    低波动: 3 bps
    中波动: 5 bps
    高波动: 10 bps
    """
    if volatility < 0.01:  # 1%
        return 3
    elif volatility < 0.03:  # 3%
    return 5
    else:
        return 10
```

### 8.2 厚区质量评分

```python
def score_shelf_quality(shelf, orderbook, atr):
    """
    评估厚区质量

    考虑因素:
    1. 深度（volume）
    2. 宽度（价格范围）
    3. 位置（距离当前价）
    """
    # 1. 深度评分（0-10）
    volumes = [order[1] for order in orderbook['asks']]
    mean_vol = sum(volumes) / len(volumes)
    depth_score = min(10, shelf['volume'] / mean_vol)

    # 2. 宽度评分（0-10）
    # 厚区越宽越好
    shelf_width = shelf.get('width', 0.0005)  # 默认5 bps
    width_score = min(10, shelf_width / 0.001 * 10)

    # 3. 位置评分（0-10）
    # 距离适中最好（0.5 - 2.0 ATR）
    mid_price = (orderbook['best_bid'] + orderbook['best_ask']) / 2
    distance = abs(shelf['price'] - mid_price)
    distance_atr = distance / atr

    if 0.5 <= distance_atr <= 2.0:
        position_score = 10
    elif distance_atr < 0.5:
        position_score = distance_atr / 0.5 * 10
    else:
        position_score = max(0, 10 - (distance_atr - 2.0) * 2)

    # 总分
    total_score = (depth_score * 0.5 + width_score * 0.3 + position_score * 0.2)

    return total_score
```

---

## 9. 持仓管理

### 9.1 TTL（持仓时间限制）

```python
# TTL配置
ttl_config = {
    'mature_coin_1h': (4 * 3600, 8 * 3600),  # 成熟币: 4-8小时
    'newcoin_1m': (2 * 3600, 4 * 3600),      # 新币: 2-4小时
}

def check_ttl(position):
    """检查是否超过TTL"""
    elapsed = time.time() - position['entry_time']

    if position.get('is_newcoin'):
        ttl_min, ttl_max = ttl_config['newcoin_1m']
    else:
        ttl_min, ttl_max = ttl_config['mature_coin_1h']

    if elapsed >= ttl_max:
        return 'FORCE_CLOSE', "超过最大持仓时间"
    elif elapsed >= ttl_min:
        return 'CONSIDER_CLOSE', "接近持仓时间上限"
    else:
        return 'OK', ""
```

### 9.2 持仓监控

```python
async def monitor_position(position):
    """持仓实时监控"""
    while position['status'] == 'OPEN':
        # 1. 更新市场数据
        klines = get_klines(position['symbol'], interval='1m', limit=60)
        orderbook = get_orderbook(position['symbol'])
        atr = calculate_atr(klines)

        # 2. 更新追踪止损
        new_sl = update_trailing_stop(position, klines, atr)
        if new_sl != position['stop_loss']:
            update_stop_loss_order(position, new_sl)

        # 3. 管理止盈
        manage_take_profit(position, orderbook)

        # 4. 检查TTL
        ttl_status, reason = check_ttl(position)
        if ttl_status == 'FORCE_CLOSE':
            close_position(position, reason)

        # 5. 检查止损触发
        triggered, reason = check_stop_loss_trigger(position, klines[-1], orderbook)
        if triggered:
            execute_stop_loss(position)

        await asyncio.sleep(5)  # 每5秒检查一次
```

---

## 10. 配置示例

### 10.1 config/params.json

```json
{
  "execution": {
    "gates": {
      "impact_bps": {"entry": 7, "maintain": 8},
      "spread_bps": {"entry": 35, "maintain": 38},
      "obi_abs": {"entry": 0.30, "maintain": 0.33},
      "dataqual": {"entry": 0.90, "maintain": 0.88},
      "room_atr_ratio": {"min": 0.6}
    },
    "entry": {
      "pullback_bandwidth_atr": 0.1,
      "breakout_delta_atr": 0.05,
      "pullback_timeout_seconds": 300
    },
    "stop_loss": {
      "sl0_atr_multiple": 1.8,
      "chandelier_k_long": 1.6,
      "chandelier_k_short": 1.4,
      "chandelier_n_min": 8,
      "chandelier_n_max": 14
    },
    "take_profit": {
      "bucket_size_bps": 5,
      "shelf_threshold_sigma": 2.0,
      "min_r_ratio": 1.0,
      "tp_adjust_interval_seconds": 20,
      "tp_adjust_ticks": 2
    },
    "position_sizing": {
      "risk_per_trade_pct": 0.01,
      "strength_multiplier_range": [0.5, 1.5]
    },
    "ttl": {
      "mature_coin_hours": [4, 8],
      "newcoin_hours": [2, 4]
    },
    "slippage": {
      "entry_max_bps": 15,
      "exit_max_bps": 20,
      "stop_loss_max_bps": 50
    }
  }
}
```

---

## 11. 实现模块

**代码位置**: `ats_core/execution/`

```
ats_core/execution/
├── gates.py                # 硬闸检查
├── entry.py                # 入场策略
├── stop_loss.py            # 止损系统
├── take_profit.py          # 止盈系统
├── order_manager.py        # 订单管理
├── position_manager.py     # 持仓管理
├── slippage.py            # 滑点控制
└── shelf_detector.py      # 厚区检测
```

---

## 12. 相关文档

- **四门系统**: [GATES.md](GATES.md)
- **DataQual**: [DATAQUAL.md](DATAQUAL.md)
- **新币通道**: [NEWCOIN.md](NEWCOIN.md)
- **核心规范**: [../CORE_STANDARDS.md](../CORE_STANDARDS.md)

---

**规范版本**: v6.4-phase2-execution
**维护**: 执行系统团队
**审核**: 系统架构师
**最后更新**: 2025-11-02
