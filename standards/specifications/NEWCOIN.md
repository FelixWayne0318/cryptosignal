# 新币通道完整规范

**规范版本**: v6.4 Phase 2
**生效日期**: 2025-11-02
**状态**: 部分实施（Phase 2完成，Phase 3-4待实现）

---

## 📋 目录

1. [总体原则](#1-总体原则)
2. [进入与回切标准](#2-进入与回切标准)
3. [数据流规范](#3-数据流规范phase-2-已实现)
4. [新币专用因子](#4-新币专用因子phase-3-待实现)
5. [点火-成势-衰竭模型](#5-点火-成势-衰竭模型phase-3-待实现)
6. [调制器参数](#6-调制器参数phase-3-待实现)
7. [执行与闸门](#7-执行与闸门)
8. [WebSocket稳定性](#8-websocket稳定性phase-2-部分实现)
9. [实施进度](#9-实施进度phase-2-phase-4)

---

## 1. 总体原则

### 1.1 设计理念

**新币通道与成熟币通道彻底隔离**：
- 不同的数据粒度（1m/5m/15m vs 1h/4h）
- 不同的因子计算（ZLEMA vs EMA）
- 不同的判定模型（点火-成势 vs Prime）
- 不同的执行策略（更严格）

### 1.2 核心特点

- **分钟级快反**: 使用1m/5m/15m数据捕捉快速波动
- **锚点定价**: AVWAP_from_listing作为价格基准
- **非线性判定**: 点火-成势-衰竭三阶段模型
- **更严闸门**: 流动性和执行要求更高

---

## 2. 进入与回切标准

### 2.1 进入条件（任一满足）

```python
is_new_coin = (
    bars_1h < 400 or                    # K线数量 < 400根（≈16.7天）
    since_listing < 14d or              # 上币时间 < 14天
    not has_OI_funding                  # 无OI/Funding数据
)
```

**Phase 2实现**: ✅
- 使用`bars_1h < 400`作为主判断条件
- 使用`coin_age_days < 14`作为辅助条件
- 在数据获取**前**进行预判（关键架构改进）

**实现模块**: `ats_core/data_feeds/newcoin_data.py::quick_newcoin_check()`

### 2.2 回切条件（全部满足）

```python
is_mature = (
    bars_1h >= 400 and                  # K线数量 ≥ 400根
    (
        (has_OI and OI_continuous >= 3d) or  # OI/Funding连续≥3天
        since_listing >= 14d                  # 或上币时间≥14天
    )
)
```

**Phase 2实现**: ⚠️ 部分
- 使用`bars_1h >= 400`判断
- OI连续性检查未实现（Phase 4）

### 2.3 渐变切换（Phase 4待实现）

**48小时线性混合**：
```python
# 回切开始时记录时间
transition_start = datetime.now()

# 计算混合权重（48小时线性过渡）
elapsed_hours = (datetime.now() - transition_start).total_seconds() / 3600
w = min(elapsed_hours / 48, 1.0)  # 0.0 → 1.0

# 混合参数
weights = w * weights_mature + (1-w) * weights_new
temperature = w * T_mature + (1-w) * T_new
thresholds = w * thresh_mature + (1-w) * thresh_new
ttl = w * ttl_mature + (1-w) * ttl_new
```

**Phase 4实现**: ❌
- 需要状态持久化（记录transition_start）
- 需要混合计算逻辑

---

## 3. 数据流规范（Phase 2 已实现）

### 3.1 数据源（Binance USDT-M）

#### REST API
- **exchangeInfo**: 获取上币时间（`onboardDate`）
- **klines**:
  - 1m: 最多1440根（24小时）
  - 5m: 最多1200根（≈100小时）
  - 15m: 最多1000根（≈250小时）
  - 1h: 最多400根（≈16.7天）
- **premiumIndex**: 标记价格和资金费率
- **openInterest**: 持仓量

**Phase 2实现**: ✅
- 实现智能limit计算（根据bars_1h动态调整）
- 实现AVWAP锚点计算

**实现模块**: `ats_core/data_feeds/newcoin_data.py::fetch_newcoin_data()`

#### WebSocket
- **@kline_1m/5m/15m**: 实时K线流
- **@aggTrade**: 聚合成交（Phase 4）
- **@depth@100ms**: 深度数据（Phase 4）
- **@markPrice@1s**: 标记价格（Phase 4）

**Phase 2实现**: ✅ 基础版
- 实现kline_1m/5m/15m订阅
- 实现心跳监控和DataQual降级
- 实现指数回退重连

**Phase 4扩展**: ⏸️
- aggTrade（计算speed/agg_buy/sell）
- depth@100ms（计算OBI）

**实现模块**: `ats_core/data_feeds/ws_newcoin.py::NewCoinWSFeed`

### 3.2 AVWAP锚点计算

**定义**: 从上币第一分钟开始的累计成交量加权平均价

```python
# 计算公式
AVWAP = Σ(P_typical * V) / ΣV

# 其中
P_typical = (High + Low + Close) / 3  # 典型价格
V = volume                             # 成交量
```

**Phase 2实现**: ✅
- 从listing_time或首根K线开始计算
- 使用典型价格加权
- Fallback机制（零成交量时使用收盘价）

**实现模块**: `ats_core/data_feeds/newcoin_data.py::calculate_avwap()`

### 3.3 数据获取架构（Phase 2核心改进）

```
阶段0: 快速预判（数据获取前）⬅️ Phase 2关键改进
  ├─ quick_newcoin_check(symbol)
  ├─ 返回: is_new_coin, listing_time, bars_1h_approx
  └─ 判断条件: bars_1h < 400 或 since_listing < 14d

阶段1: 分别获取数据
  ├─ 新币: fetch_newcoin_data()  → 1m/5m/15m/1h + AVWAP
  └─ 成熟币: fetch_standard_data() → 1h/4h

阶段2: 精准判断
  └─ 使用实际len(k1h)确认

阶段3-4: 因子计算和判定（Phase 3实现）
  └─ 新币: 使用T_new/M_new/S_new + 点火-成势模型
```

**Phase 2实现**: ✅
- 解决了架构性缺陷（数据获取顺序倒置）
- 新币可以获取1m/5m/15m数据
- AVWAP锚点可用

---

## 4. 新币专用因子（Phase 3 待实现）

### 4.1 因子定义

| 因子 | 名称 | 数据源 | 计算方法 |
|------|------|--------|---------|
| **T_new** | 趋势 | 1m | ZLEMA_1m(HL=5)斜率 |
| **M_new** | 动量 | 5m | ZLEMA_5m(HL=8)斜率 |
| **S_new** | 结构/速度 | 15m | EWMA_15m(HL=20)斜率 |
| **V_new** | 量能 | 1m/5m | RVOL + 买卖差 |
| **C_new** | CVD | aggTrade | 累计成交量差 |
| **O_new** | OI | 1h | OI斜率（无OI时权重0） |
| **Q_sig_new** | 清算密度 | aggTrade | 清算分布 |

### 4.2 权重配置

**基础权重** (总和100%):
```python
weights_newcoin = {
    "T": 22,  # 趋势（1m）
    "M": 15,  # 动量（5m）
    "S": 15,  # 结构/速度（15m）
    "V": 16,  # 量能
    "C": 20,  # CVD
    "O": 8,   # OI（无OI时权重0）
    "Q": 4,   # 清算密度
}
```

**无OI时归一化**:
```python
if not has_OI:
    # 按比例重新分配O的权重
    weights_newcoin["O"] = 0
    total = sum(weights_newcoin.values())
    weights_newcoin = {k: v*100/total for k, v in weights_newcoin.items()}
```

### 4.3 ZLEMA计算

**零延迟EMA**（减少滞后）:
```python
def calc_zlema(prices, halflife):
    """
    Zero-Lag EMA

    ZLEMA_t = α(2*P_t - P_{t-lag}) + (1-α)ZLEMA_{t-1}
    其中 lag = (halflife - 1) / 2
    """
    lag = int((halflife - 1) / 2)
    alpha = 1 - exp(-log(2) / halflife)

    zlema = [0] * len(prices)
    zlema[lag] = prices[lag]  # 初始化

    for i in range(lag+1, len(prices)):
        delagged_price = 2*prices[i] - prices[i-lag]
        zlema[i] = alpha*delagged_price + (1-alpha)*zlema[i-1]

    return zlema
```

### 4.4 实施计划（Phase 3）

**新增模块**: `ats_core/factors/newcoin_factors.py`

```python
def calc_T_new(k1m, hl=5) -> Tuple[float, dict]:
    """趋势因子（ZLEMA_1m斜率）"""
    zlema = calc_zlema(k1m, halflife=hl)
    slope = standardize_slope(zlema)
    return slope, {"method": "ZLEMA_1m", "hl": hl}

def calc_M_new(k5m, hl=8) -> Tuple[float, dict]:
    """动量因子（ZLEMA_5m斜率）"""
    zlema = calc_zlema(k5m, halflife=hl)
    slope = standardize_slope(zlema)
    return slope, {"method": "ZLEMA_5m", "hl": hl}

def calc_S_new(k15m, hl=20) -> Tuple[float, dict]:
    """强度因子（EWMA_15m斜率）"""
    ewma = calc_ewma(k15m, halflife=hl)
    slope = standardize_slope(ewma)
    return slope, {"method": "EWMA_15m", "hl": hl}
```

---

## 5. 点火-成势-衰竭模型（Phase 3 待实现）

### 5.1 点火检测（≥3条成立）

| # | 条件 | 阈值 | 数据依赖 |
|---|------|------|---------|
| 1 | 价格偏离锚点 | `(P-AVWAP)/ATR_1m ≥ 0.8` | k1m + AVWAP |
| 2 | 速度持续 | `speed ≥ 0.25 ATR/min (≥2min)` | aggTrade |
| 3 | 主动买入占比 | `agg_buy ≥ 0.62`（多）<br>`agg_sell ≥ 0.62`（空） | aggTrade |
| 4 | 订单簿失衡 | `OBI10 ≥ 0.05`（多）<br>`≤ -0.05`（空） | depth |
| 5 | 相对成交量 | `RVOL_10m ≥ 3.0`<br>或 `RVOL_5m ≥ 2.0` | k1m/k5m |
| 6 | CVD方向 | `slope_CVD > 0`（多）<br>`< 0`（空） | aggTrade |

**判定逻辑**:
```python
def check_ignition(k1m, k5m, avwap, atr_1m, agg_trades, depth) -> Tuple[bool, List[str]]:
    """检测点火条件"""
    conditions_met = []

    # 1. 价格偏离AVWAP
    price = k1m[-1][4]  # close
    if abs(price - avwap) / atr_1m >= 0.8:
        conditions_met.append("price_divergence")

    # 2. 速度检测（需aggTrade）
    speed = calc_speed(agg_trades, atr_1m)
    if speed >= 0.25 and speed_duration >= 2:  # 持续2分钟
        conditions_met.append("speed")

    # 3. 主动买入占比
    agg_buy = calc_agg_buy_ratio(agg_trades)
    if agg_buy >= 0.62:  # 多头
        conditions_met.append("agg_buy")
    elif agg_buy <= 0.38:  # 空头
        conditions_met.append("agg_sell")

    # 4. OBI
    obi = calc_obi(depth, levels=10)
    if abs(obi) >= 0.05:
        conditions_met.append("obi")

    # 5. RVOL
    rvol_10m = calc_rvol(k1m, window=10)
    rvol_5m = calc_rvol(k5m, window=1)
    if rvol_10m >= 3.0 or rvol_5m >= 2.0:
        conditions_met.append("rvol")

    # 6. CVD
    cvd_slope = calc_cvd_slope(agg_trades)
    if abs(cvd_slope) > 0:
        conditions_met.append("cvd")

    is_ignition = len(conditions_met) >= 3
    return is_ignition, conditions_met
```

### 5.2 成势确认

**多时间框架斜率同向**:
```python
def check_momentum(k1m, k5m, k15m) -> bool:
    """成势确认"""
    # 计算各时间框架斜率
    slope_1m = calc_slope(k1m, method="ZLEMA", hl=5)
    slope_5m = calc_slope(k5m, method="ZLEMA", hl=8)
    slope_15m = calc_slope(k15m, method="EWMA", hl=20)

    # 判断：1m/5m同向，15m ≥ 0
    return (slope_1m * slope_5m > 0) and (slope_15m >= 0)
```

### 5.3 衰竭/反转检测

**任一满足即判定衰竭**:

| # | 衰竭信号 | 阈值 | 说明 |
|---|---------|------|------|
| 1 | 失锚 + CVD翻转 | `\|P-AVWAP\| > 2*ATR` + `slope_CVD`翻转 | 价格脱离锚点且CVD反向 |
| 2 | 速度反转 | `speed < 0` 连续2-3根1m | 价格开始回调 |
| 3 | OBI反号 | OBI反号 且 对侧`agg ≥ 0.60` | 订单簿和主动成交反向 |
| 4 | 异常成交 | `qvol/ATR > 0.6` | 单笔大额成交 |

```python
def check_exhaustion(k1m, avwap, atr_1m, cvd_slope, speed_history, obi, agg_ratio, qvol) -> Tuple[bool, str]:
    """衰竭/反转检测"""
    price = k1m[-1][4]

    # 1. 失锚 + CVD翻转
    if abs(price - avwap) > 2*atr_1m and cvd_slope * prev_cvd_slope < 0:
        return True, "anchor_lost_cvd_flip"

    # 2. 速度反转（连续2-3根）
    if all(s < 0 for s in speed_history[-3:]):
        return True, "speed_reversal"

    # 3. OBI反号
    if obi * prev_obi < 0 and agg_ratio >= 0.60:
        return True, "obi_flip_agg_confirm"

    # 4. 异常成交
    if qvol / atr_1m > 0.6:
        return True, "abnormal_volume"

    return False, ""
```

### 5.4 实施计划（Phase 3）

**新增模块**: `ats_core/models/point_fire_momentum.py`

**依赖数据**:
- ✅ k1m/k5m/k15m: Phase 2已实现
- ✅ AVWAP: Phase 2已实现
- ❌ aggTrade: Phase 4实现
- ❌ depth: Phase 4实现

**工作量估算**: 4-6天

---

## 6. 调制器参数（Phase 3 待实现）

### 6.1 F因子特殊处理

**问题**: 新币初期资金费率常失真

**解决方案**: 初期置0.5（中性），稳定≥3天再启用

```python
if is_new_coin:
    if bars_1h < 72:  # < 3天
        F = 0.5  # 中性值，不影响概率
    else:
        F = calc_fund_leading(...)  # 正常计算
```

### 6.2 I因子降权

**问题**: 新币与BTC/ETH相关性不稳定

**解决方案**: 使用15m-1h粗相关，降低权重

```python
# 标准币（1h相关）
beta_weights = {
    "BTC": 0.60,
    "ETH": 0.40
}

# 新币（15m-1h粗相关）
beta_weights_new = {
    "BTC": 0.50,  # 降低
    "ETH": 0.30   # 降低
}
```

### 6.3 温度参数

```python
# 新币专用温度
T_newcoin = {
    "T0": 60,       # 基础温度
    "beta_F": 0.20, # F调节强度
    "beta_I": 0.15, # I调节强度
    "T_min": 40,    # 最低温度
    "T_max": 95,    # 最高温度
}
```

### 6.4 成本/门槛参数

```python
# 新币专用成本参数
cost_newcoin = {
    "lambda_F": 0.40,       # F成本系数
    "lambda_I_pen": 0.35,   # I惩罚成本
    "lambda_I_rew": 0.20,   # I奖励成本
}

# 新币专用门槛参数
threshold_newcoin = {
    "p0": 0.60,    # 基础概率阈值
    "dp0": 0.06,   # 概率调整幅度
    "theta_F": 0.03,
    "theta_I_pen": 0.02,
    "theta_I_rew": 0.008,
    "phi_F": 0.02,
    "phi_I_pen": 0.01,
    "phi_I_rew": 0.004,
}
```

### 6.5 概率收缩

**原因**: 新币数据少，概率估计不确定性高

**公式**:
```python
# 概率收缩到中性值
P_tilde = 0.5 + w_eff * (P - 0.5)

# 有效权重（随K线数增加而增加）
w_eff = min(1.0, bars_1h / 400)
```

**效果**:
- bars_1h = 100: w_eff = 0.25 → P收缩75%到中性
- bars_1h = 200: w_eff = 0.50 → P收缩50%到中性
- bars_1h = 400: w_eff = 1.00 → P无收缩

---

## 7. 执行与闸门

### 7.1 更严硬闸（开仓/维持滞回）

| 闸门 | 成熟币 | 新币 | 说明 |
|------|--------|------|------|
| **Impact** | ≤ 7/8 bps | ≤ 7/8 bps | 相同 |
| **Spread** | ≤ 35/38 bps | ≤ 35/38 bps | 相同 |
| **OBI** | ≤ 0.30/0.33 | ≤ 0.30/0.33 | 相同 |
| **DataQual** | ≥ 0.90/0.88 | ≥ 0.90/0.88 | 相同 |
| **Room** | R*·ATR_1h | R*·ATR_1m | 新币用1m粒度 |

**开仓/维持滞回**: 防止边界抖动
- 开仓: 必须**严格**满足阈值
- 维持: 允许略微放宽（+10%容忍）
- 关闸冷却: 60-120秒

### 7.2 入场策略

**回撤接力（优先）**:
```python
# 锚点选择
anchor = AVWAP  # 或 ZLEMA_5m

# 挂单带宽
bandwidth = 0.05 * ATR_1m  # 新币用1m ATR

# 挂单价格
entry_price = anchor ± bandwidth  # 多/空
```

**突破带（备选）**:
```python
delta_in = 0.05 * ATR + min(0.10 * ATR, c * impact)
```

### 7.3 止损/止盈

**SL0（可成交优先）**:
```python
d_struct = abs(entry - structural_low_high)  # 结构保护
d_atr = 1.8 * ATR_1m                         # 新币用1m ATR

# 软最小值（避免硬切）
SL0 = softmin(d_struct, d_atr, tau=0.1*ATR_1m)
```

**追踪SL**:
```python
# Chandelier追踪
SL = softmin(
    HH_N - k_long * ATR_1m,    # 多头（新币用1m ATR）
    structural_protection,
    break_even
)

# 新币参数
N: 8 → 14  # 窗口逐渐扩大
k_long = 1.6
k_short = 1.4
```

**止盈**:
- 厚区入口/中段挂maker单
- 20秒无成交上移1-2 tick
- 无厚区不挂TP，手动平仓

### 7.4 TTL（持仓时间限制）

```python
# 成熟币: 4-8h
# 新币: 2-4h（更短，快进快出）
ttl_newcoin = 2-4h
```

### 7.5 Prime窗口限制

**防止新币刚上线时的数据不稳定**:

```python
minutes_since_listing = (current_time - listing_time) / 60000

if minutes_since_listing < 3:
    signal_type = "Watch"  # 0-3分钟：强制Watch
elif minutes_since_listing < 8:
    signal_type = "Prime" if meets_higher_threshold else "Watch"  # 3-8分钟：首批Prime
else:  # 8-15分钟
    signal_type = "Prime" if meets_standard_threshold else "Watch"  # 主力窗口
```

---

## 8. WebSocket稳定性（Phase 2 部分实现）

### 8.1 组合流订阅

**策略**: 合并多个流到一个WebSocket连接

```python
# 建议连接数: 3-5个
conn1: kline_1m + kline_5m + kline_15m
conn2: aggTrade
conn3: depth@100ms + markPrice@1s
```

**Phase 2实现**: ⚠️ 简化版
- 每个interval一个独立连接（kline_1m/5m/15m）
- 未实现组合流（Phase 4优化）

**实现模块**: `ats_core/data_feeds/ws_newcoin.py::NewCoinWSFeed`

### 8.2 指数回退重连

**Phase 2实现**: ✅

```python
class ExponentialBackoff:
    def get_delay(self) -> float:
        # delay = base * 2^retry_count + jitter
        delay = min(base_delay * (2 ** retry_count), max_delay)
        jitter_amount = delay * jitter_ratio * (random() * 2 - 1)
        return max(0.1, delay + jitter_amount)
```

**参数**:
- base_delay: 1.0秒
- max_delay: 60秒
- jitter_ratio: 0.1 (±10%)

### 8.3 REST深度快照对账

**目的**: 防止WS增量更新丢失导致订单簿不一致

**Phase 4实现**: ❌

```python
async def reconcile_depth():
    """定期REST对账"""
    ws_last_update_id = depth_snapshot['lastUpdateId']
    rest_snapshot = await fetch_depth_snapshot(symbol, limit=100)

    if rest_snapshot['lastUpdateId'] > ws_last_update_id + 100:
        # 差距过大，重新同步
        depth_snapshot = rest_snapshot
```

### 8.4 心跳监控与DataQual降级

**Phase 2实现**: ✅

```python
async def heartbeat_monitor():
    """心跳监控"""
    while running:
        await asyncio.sleep(heartbeat_interval)  # 30秒

        missing_count = 0
        for interval in ["1m", "5m", "15m"]:
            time_since_last = current_time - last_message_time[interval]
            if time_since_last > heartbeat_timeout:  # 60秒
                missing_count += 1

        # DataQual降级
        if missing_count == 0:
            data_quality = 1.0
        elif missing_count == 1:
            data_quality = 0.8
        elif missing_count == 2:
            data_quality = 0.5
        else:  # 全部缺失
            data_quality = 0.2
```

---

## 9. 实施进度（Phase 2 - Phase 4）

### Phase 1: v7.3.4 ✅ COMPLETED

**已实现**:
- ✅ 新币判断: bars_1h < 400 或 coin_age_days < 14
- ✅ 币种特定阈值: prime_strength 35/32/28/25
- ✅ 质量评分补偿: 10-13%

**限制**:
- ⚠️ 权宜之计，使用统一1h/4h数据和标准因子
- ⚠️ 通过提高阈值来补偿粒度不足

**合规度**: 12.8%（6/47项）

---

### Phase 2: v6.4 ✅ COMPLETED (当前版本)

**目标**: 解决P0级数据粒度问题

**已实现**:

1. **阶段0预判（数据获取前）** ✅
   - `quick_newcoin_check()`: 调用exchangeInfo判断是否为新币
   - 判断: `bars_1h < 400` 或 `since_listing < 14d`
   - **关键架构改进**: 在数据获取前预判

2. **新币数据获取模块** ✅
   - `fetch_newcoin_data()`: 获取1m/5m/15m/1h K线
   - 智能limit计算（根据bars_1h动态调整）
   - AVWAP锚点计算
   - 返回: k1m, k5m, k15m, k1h, avwap, listing_time

3. **WS实时订阅（初版）** ✅
   - 订阅kline_1m/5m/15m
   - 指数回退重连
   - 心跳监控 → DataQual动态调整
   - 本地K线缓存（deque，500根）

4. **数据获取流程重构** ✅
   - 修改`analyze_symbol()`，添加4阶段流程
   - 传递k15m到`_analyze_symbol_core()`
   - 存储新币元数据到result

**合规度提升**: 12.8% → **40%** (+27项，+213%提升)

**关键文件**:
- `ats_core/data_feeds/newcoin_data.py` (312 lines)
- `ats_core/data_feeds/ws_newcoin.py` (380 lines)
- `ats_core/pipeline/analyze_symbol.py` (重构)
- `test_phase2.py` (测试脚本)

---

### Phase 3: 新币专用因子与模型 🔴 HIGH PRIORITY

**目标**: 实现新币专用因子和点火-成势模型

**合规度目标**: 40% → **65%** (+12项)

**实施步骤**:

1. **新币专用因子实现** ❌
   - 新增: `ats_core/factors/newcoin_factors.py`
   - T_new (ZLEMA_1m, HL=5)
   - M_new (ZLEMA_5m, HL=8)
   - S_new (EWMA_15m, HL=20)
   - V_new, C_new (复用标准实现)

2. **点火-成势-衰竭模型** ❌
   - 新增: `ats_core/models/point_fire_momentum.py`
   - 点火检测: `check_ignition()` (≥3条件成立)
   - 成势确认: `check_momentum()` (多时间框架斜率)
   - 衰竭检测: `check_exhaustion()` (动态追踪)
   - **依赖**: k1m/k5m/k15m (✅), AVWAP (✅), aggTrade (❌), depth (❌)

3. **新币专用权重配置** ❌
   - 修改: `config/params.json`
   - 添加`weights_newcoin`配置段
   - T22/M15/S15/V16/C20/O8/Q4

4. **在analyze_symbol中集成** ❌
   - 修改`_analyze_symbol_core()`
   - 添加新币分支逻辑
   - 使用新币因子和点火-成势模型

**工作量估算**: 4-6天

**阻塞因素**: aggTrade和depth数据（Phase 4提供）

---

### Phase 4: 完整新币通道（生产级） 🟡 MEDIUM PRIORITY

**目标**: 实现规范全部要求，达到90%+合规度

**合规度目标**: 65% → **90%+** (+13项)

**实施步骤**:

1. **WS完整订阅（aggTrade + depth）** ❌
   - 扩展: `ats_core/data_feeds/ws_newcoin.py`
   - 添加aggTrade处理（计算agg_buy/sell、speed）
   - 添加depth@100ms处理（计算OBI）
   - 实现组合流（3-5个连接）
   - REST深度快照对账

2. **点火模型完整实现（依赖WS数据）** ❌
   - 扩展: `ats_core/models/point_fire_momentum.py`
   - 添加speed检测（需aggTrade）
   - 添加agg_buy/sell检测（需aggTrade）
   - 添加OBI检测（需depth）
   - 添加RVOL、CVD检测

3. **48h渐变切换机制** ❌
   - 新增: `ats_core/pipeline/transition_manager.py`
   - 状态记录: 回切开始时间（需持久化）
   - 线性混合: `w = (elapsed_hours / 48)`
   - 混合内容: 权重、温度、阈值、TTL

4. **新币专用执行闸门** ❌
   - 修改: `ats_core/gates/integrated_gates.py`
   - 新币硬闸: impact≤7/8bps, spread≤35/38bps, OBI≤0.30/0.33, DataQual≥0.90/0.88
   - Prime时间窗口: 0-3m/3-8m/8-15m分段逻辑
   - Room检测: R*·ATR_1m

5. **新币专用调节器参数** ❌
   - F初期置0.5（稳定≥3d再启用）
   - I降权（15m-1h粗相关）
   - 温度/成本/门槛专用参数（§6完整参数表）
   - 概率收缩: `w_eff = min(1, bars_1h/400)`

6. **独立新币pipeline（可选）** ❌
   - 新增: `scripts/newcoin_scanner.py`
   - 完全独立的扫描器（与标准通道隔离）
   - 专用配置: `config/params_newcoin.json`

**工作量估算**: 7-10天

---

## 📊 合规性进度总览

| Phase | 版本 | 合规度 | 状态 | 关键里程碑 |
|-------|------|--------|------|-----------|
| Phase 1 | v7.3.4 | 12.8% (6/47) | ✅ 完成 | 基础判断和阈值 |
| Phase 2 | v6.4 | 40% (19/47) | ✅ 完成 | 数据流分离 |
| Phase 3 | v6.5 (计划) | 65% (31/47) | ❌ 待实现 | 新币因子和模型 |
| Phase 4 | v7.0 (计划) | 90%+ (43/47) | ❌ 待实现 | 生产级完整功能 |

---

## 🔗 相关文档

- **因子系统**: [FACTOR_SYSTEM.md](FACTOR_SYSTEM.md)
- **数据层**: [DATA_LAYER.md](DATA_LAYER.md)
- **版本历史**: [../03_VERSION_HISTORY.md](../03_VERSION_HISTORY.md)
- **系统概览**: [../01_SYSTEM_OVERVIEW.md](../01_SYSTEM_OVERVIEW.md)

---

**规范版本**: v6.4-phase2
**维护**: 系统架构师
**审核**: 技术负责人
