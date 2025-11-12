# 信号生成完整流程图

**版本**: v7.2.29
**日期**: 2025-11-12

---

## 📋 目录

1. [系统架构总览](#系统架构总览)
2. [阶段1：数据采集](#阶段1数据采集)
3. [阶段2：因子计算](#阶段2因子计算)
4. [阶段3：因子分组与加权](#阶段3因子分组与加权)
5. [阶段4：蓄势分级](#阶段4蓄势分级)
6. [阶段5：五道闸门检查](#阶段5五道闸门检查)
7. [阶段6：概率校准与EV计算](#阶段6概率校准与ev计算)
8. [阶段7：AntiJitter过滤](#阶段7antijitter过滤)
9. [阶段8：Telegram消息生成](#阶段8telegram消息生成)
10. [阶段9：信号发布](#阶段9信号发布)
11. [关键文件索引](#关键文件索引)

---

## 系统架构总览

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                      信号生成完整流程
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【阶段1：数据采集】 ~/scripts/realtime_signal_scanner.py
    ├─ 获取币种列表（~400个）
    ├─ 获取K线数据（150-300根）
    ├─ 获取BTC/ETH参考数据（用于I因子）
    ├─ 获取资金费率、CVD、OI等衍生数据
    └─ 数据清洗与验证
         ↓

【阶段2：因子计算】 ~/ats_core/pipeline/analyze_symbol.py
    │
    ├─ A层：基础6维因子（原始信号）
    │   ├─ T（趋势）    ~/ats_core/features/trend.py
    │   ├─ M（动量）    ~/ats_core/features/momentum.py
    │   ├─ C（资金流）  ~/ats_core/features/capital.py
    │   ├─ V（量能）    ~/ats_core/features/volume.py
    │   ├─ O（持仓）    ~/ats_core/features/openinterest.py
    │   └─ B（基差）    ~/ats_core/features/basis.py
    │
    └─ B层：增强4维因子（统计/关系）
        ├─ F（资金领先性） ~/ats_core/factors_v2/fund_leading.py
        ├─ I（市场独立性） ~/ats_core/factors_v2/independence.py
        ├─ L（流动性深度） ~/ats_core/factors_v2/liquidity.py
        └─ Q（数据质量）   ~/ats_core/factors_v2/quality.py
         ↓

【阶段3：因子分组与加权】 ~/ats_core/scoring/factor_groups.py
    │
    ├─ TC组（50%）：趋势 + 资金流
    │   └─ 组内：T×50% + C×50%
    │   └─ 等效：T=25%, C=25%
    │
    ├─ VOM组（38%）：量能 + 持仓 + 动量
    │   └─ 组内：V×55% + O×30% + M×15%
    │   └─ 等效：V=20.9%, O=11.4%, M=5.7%
    │
    └─ B组（12%）：基差/情绪
        └─ 等效：B=12%
         ↓
    weighted_score = TC×0.50 + VOM×0.38 + B×0.12
    confidence = abs(weighted_score)
    side_long = (weighted_score > 0)
         ↓

【阶段4：蓄势分级】 ~/ats_core/pipeline/analyze_symbol_v72.py:200-350
    │
    ├─ 计算F_effective = get_effective_F(F, side_long)
    │   └─ 做多：F_effective = F
    │   └─ 做空：F_effective = -F
    │
    ├─ 判断蓄势级别（线性模式，v7.2.29优化）:
    │   ├─ F≥75：极值警戒（conservative模式，提高质量要求）
    │   ├─ F≥60：极早期蓄势（完全降低阈值）
    │   ├─ 35≤F<60：线性降低阈值
    │   │   └─ reduction_ratio = (F - 35) / (60 - 35)
    │   │   └─ confidence_min = 15 - 5×ratio
    │   │   └─ P_min = 0.50 - 0.08×ratio
    │   │   └─ EV_min = 0.015 - 0.007×ratio
    │   │   └─ F_min = -10 + 60×ratio
    │   └─ F<35：正常模式（使用基准阈值）
    │
    └─ 输出调整后的阈值（用于后续闸门检查）
         ↓

【阶段5：五道闸门检查】 ~/ats_core/pipeline/analyze_symbol_v72.py:380-550
    │
    ├─ Gate 1：数据质量闸门
    │   └─ min_klines ≥ 150
    │   └─ 无异常值、缺失值
    │
    ├─ Gate 2：资金支持闸门
    │   └─ F_effective ≥ F_min（蓄势分级调整后）
    │   └─ 做多+F<0 或 做空+F>0 → 拒绝
    │
    ├─ Gate 3：期望收益闸门
    │   └─ EV ≥ EV_min（蓄势分级调整后）
    │   └─ EV = (P×盈利) - ((1-P)×亏损) - 成本
    │
    ├─ Gate 4：概率闸门
    │   └─ P_calibrated ≥ P_min（蓄势分级调整后）
    │   └─ P_calibrated = 统计校准概率（见阶段6）
    │
    └─ Gate 5：独立性×市场闸门
        ├─ I ≥ 60：高独立性 → 直接通过
        ├─ 0 ≤ I < 60：中等独立性
        │   └─ 检查是否逆势（做多+熊市 或 做空+牛市）
        │   └─ 逆势 → 拒绝，顺势 → 放大confidence×1.2
        └─ I < 0：强相关
            └─ 逆势 → 拒绝，顺势 → 正常通过
         ↓
    gates_passed = (gate1 & gate2 & gate3 & gate4 & gate5)
    conflict_mult = [0.0, 1.0, 1.2]  # 根据I×Market结果
         ↓

【阶段6：概率校准与EV计算】 ~/ats_core/calibration/empirical_calibration.py
    │
    ├─ 基准概率（confidence驱动）:
    │   └─ P_base = 0.45 + (confidence / 100) × 0.23
    │   └─ 例：confidence=50 → P_base=0.565
    │
    ├─ F因子线性校准（v7.2.29优化）:
    │   ├─ F≥60：+5%
    │   ├─ 0<F<60：线性插值（例：F=40 → +3.3%）
    │   ├─ -20<F<0：线性插值（例：F=-10 → -1.5%）
    │   └─ F≤-20：-3%
    │
    ├─ I因子线性校准:
    │   ├─ I≥80：+3%
    │   ├─ 20<I<80：线性插值
    │   ├─ 0<I<20：线性插值
    │   └─ I≤0：-2%
    │
    └─ P_calibrated = P_base + F_bonus + I_bonus
         ↓
    EV计算:
    ├─ 盈利目标 = confidence × target_mult（根据F分级调整）
    ├─ 止损 = -8% ~ -10%（蓄势信号收紧）
    ├─ 成本 = spread + slippage + fee ≈ 0.1%
    └─ EV = (P_calibrated × 盈利) - ((1-P_calibrated) × 止损) - 成本
         ↓

【阶段7：AntiJitter过滤】 ~/scripts/realtime_signal_scanner.py:600-800
    │
    ├─ 层级1：基础过滤
    │   ├─ gates_passed == True
    │   ├─ confidence ≥ confidence_min（蓄势分级调整后）
    │   └─ 币种不在黑名单
    │
    ├─ 层级2：Hysteresis（滞后）
    │   ├─ 首次进入：confidence ≥ threshold_high（例：20）
    │   ├─ 持续保持：confidence ≥ threshold_low（例：15）
    │   └─ 退出：confidence < threshold_low
    │
    ├─ 层级3：Persistence（持久性）
    │   ├─ 信号需持续N次扫描（例：3次，约15分钟）
    │   └─ 避免瞬时波动导致的假信号
    │
    └─ 层级4：Cooldown（冷却期）
        ├─ 同币种信号发送后，冷却X小时（例：12小时）
        └─ 避免过度交易
         ↓
    filtered_signals = [信号1, 信号2, ...]
    sorted_by_confidence_adjusted = sorted(filtered_signals, key=confidence×conflict_mult)
         ↓

【阶段8：Telegram消息生成】 ~/ats_core/outputs/telegram_fmt.py
    │
    ├─ 基本信息
    │   ├─ 币种、方向、价格
    │   ├─ Confidence（confidence × conflict_mult）
    │   └─ 胜率（P_calibrated）、期望收益（EV）
    │
    ├─ 因子分析（6+4维）
    │   ├─ A层：T/M/C/V/O/B（带描述和emoji）
    │   └─ B层：F/I/L/Q（带蓄势分级标记）
    │
    ├─ 质量检查
    │   ├─ ✅ Gate 1-5通过情况
    │   └─ ⚠️ 风险提示（如逆势、低独立性）
    │
    ├─ 蓄势分级标记（v7.2.29）
    │   ├─ F≥60：🚀🚀🚀 极早期蓄势（仓位×0.7）
    │   ├─ F≥50：🚀🚀 早期蓄势（仓位×0.8）
    │   ├─ F≥35：🚀 蓄势待发（仓位×0.9）
    │   └─ F<35：正常模式
    │
    └─ 操作建议
        ├─ 入场价格、止损价格
        ├─ 目标价格（根据confidence）
        └─ 仓位建议（根据F分级）
         ↓

【阶段9：信号发布】 ~/scripts/realtime_signal_scanner.py:900-1000
    │
    ├─ 发送到Telegram频道
    │   └─ telegram_bot.send_message(chat_id, message)
    │
    ├─ 记录信号日志
    │   └─ signal_history.json（用于统计和回测）
    │
    └─ 更新AntiJitter状态
        ├─ 更新hysteresis状态
        ├─ 更新persistence计数器
        └─ 更新cooldown时间戳

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 阶段1：数据采集

### 入口文件
`scripts/realtime_signal_scanner.py`

### 关键函数
```python
def scan_binance_perpetual():
    """扫描币安永续合约市场"""
    # 1. 获取交易对列表
    symbols = exchange.fetch_markets()
    symbols = [s for s in symbols if s.endswith('USDT') and 'PERP' in s]

    # 2. 批量获取K线数据
    for symbol in symbols:
        klines = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=300)

        # 3. 获取衍生数据
        funding_rate = exchange.fetch_funding_rate(symbol)
        cvd_data = calculate_cvd(klines, volume_data)
        oi_data = exchange.fetch_open_interest(symbol)

    return raw_data
```

### 数据结构
```python
raw_data = {
    "symbol": "BTCUSDT",
    "klines": [
        [timestamp, open, high, low, close, volume],
        ...  # 150-300根K线
    ],
    "funding_rate": 0.0001,
    "cvd": [...],  # Cumulative Volume Delta
    "oi": [...],   # Open Interest
    "orderbook": {  # 订单簿（用于L因子）
        "bids": [[price, size], ...],
        "asks": [[price, size], ...]
    }
}
```

### 数据验证
- ✅ K线数量 ≥ 150根
- ✅ 无异常值（价格跳变>50%）
- ✅ 无缺失值（NaN、None）
- ✅ 时间戳连续性

---

## 阶段2：因子计算

### 入口文件
`ats_core/pipeline/analyze_symbol.py`

### A层：基础6维因子

#### 1. T因子（趋势）
**文件**: `ats_core/features/trend.py`

```python
def calculate_trend(klines):
    """
    趋势因子：EMA交叉 + 线性回归斜率

    范围：-100 ~ +100
    - T > 0：上升趋势
    - T < 0：下降趋势
    - |T| 越大，趋势越强
    """
    # 1. EMA交叉（短期vs长期）
    ema_short = talib.EMA(close, timeperiod=20)
    ema_long = talib.EMA(close, timeperiod=50)
    ema_cross = (ema_short[-1] - ema_long[-1]) / ema_long[-1] * 100

    # 2. 线性回归斜率
    x = np.arange(len(close[-50:]))
    y = close[-50:]
    slope, _ = np.polyfit(x, y, 1)
    lr_slope = slope / close[-1] * 100

    # 3. 加权组合（EMA 60%, 斜率 40%）
    T = ema_cross * 0.6 + lr_slope * 0.4

    return np.clip(T, -100, 100)
```

**时序特性**：🔴 **滞后指标**（+2~6h）
- EMA交叉需要价格已经上涨一段时间
- 线性回归基于历史数据，反应价格已发生的变化

---

#### 2. M因子（动量）
**文件**: `ats_core/features/momentum.py`

```python
def calculate_momentum(klines):
    """
    动量因子：价格加速度 + RSI

    范围：-100 ~ +100
    - M > 0：正动量（加速上涨）
    - M < 0：负动量（加速下跌）
    """
    # 1. 价格变化率的变化率（加速度）
    returns = np.diff(close) / close[:-1]
    acceleration = np.diff(returns)

    # 2. RSI（相对强弱指标）
    rsi = talib.RSI(close, timeperiod=14)
    rsi_normalized = (rsi[-1] - 50) * 2  # 转换到-100~+100

    # 3. 加权组合
    M = acceleration[-1] * 50 + rsi_normalized * 0.5

    return np.clip(M, -100, 100)
```

**时序特性**：🟡 **同步指标**（±0h）
- 加速度与价格变化同步
- RSI略有滞后但基本同步

---

#### 3. C因子（资金流）
**文件**: `ats_core/features/capital.py`

```python
def calculate_capital_flow(klines, cvd_data):
    """
    资金流因子：CVD（累积成交量增量）

    范围：-100 ~ +100
    - C > 0：资金净流入
    - C < 0：资金净流出
    """
    # 1. CVD计算（买量 - 卖量的累积）
    cvd = []
    for i, candle in enumerate(klines):
        if candle['close'] > candle['open']:
            # 阳线：买入为主
            buy_vol = candle['volume']
            sell_vol = 0
        else:
            # 阴线：卖出为主
            buy_vol = 0
            sell_vol = candle['volume']

        cvd_delta = buy_vol - sell_vol
        cvd.append(sum(cvd_delta[-20:]))  # 20期累积

    # 2. CVD斜率（资金流入速度）
    cvd_slope = (cvd[-1] - cvd[-20]) / cvd[-20] * 100

    # 3. 标准化
    C = np.clip(cvd_slope, -100, 100)

    return C
```

**时序特性**：🟢 **领先指标**（-2~4h）
- 资金流入积累，价格尚未完全反应
- 买盘压力建立，预示价格即将上涨

---

#### 4. V因子（量能）
**文件**: `ats_core/features/volume.py`

```python
def calculate_volume(klines):
    """
    量能因子：成交量放大 + 量价配合

    范围：-100 ~ +100
    - V > 0：量能放大（配合上涨）
    - V < 0：量能放大（配合下跌）
    """
    # 1. 成交量相对变化
    vol = np.array([k['volume'] for k in klines])
    vol_ma = talib.SMA(vol, timeperiod=20)
    vol_ratio = (vol[-1] - vol_ma[-1]) / vol_ma[-1] * 100

    # 2. 量价配合度
    price_change = (close[-1] - close[-20]) / close[-20]
    vol_change = (vol[-1] - vol[-20]) / vol[-20]

    if price_change > 0 and vol_change > 0:
        # 价涨量增：正向放大
        vp_sync = 1.2
    elif price_change < 0 and vol_change > 0:
        # 价跌量增：负向放大
        vp_sync = -1.2
    else:
        vp_sync = 0.8

    # 3. 综合
    V = vol_ratio * vp_sync

    return np.clip(V, -100, 100)
```

**时序特性**：🟢 **领先指标**（-0.5~2h）
- 量能放大预示突破即将发生
- 成交活跃是价格启动的前兆

---

#### 5. O因子（持仓量）
**文件**: `ats_core/features/openinterest.py`

```python
def calculate_oi(oi_data):
    """
    持仓量因子：OI变化 + OI/成交量比

    范围：-100 ~ +100
    - O > 0：持仓增加（建仓）
    - O < 0：持仓减少（平仓）
    """
    # 1. OI变化率
    oi = np.array(oi_data)
    oi_change = (oi[-1] - oi[-20]) / oi[-20] * 100

    # 2. OI/成交量比（持仓深度）
    oi_vol_ratio = oi[-1] / vol[-1]
    oi_vol_ratio_norm = (oi_vol_ratio - np.mean(oi_vol_ratio[-20:])) / np.std(oi_vol_ratio[-20:])

    # 3. 综合
    O = oi_change * 0.7 + oi_vol_ratio_norm * 30 * 0.3

    return np.clip(O, -100, 100)
```

**时序特性**：🟢 **领先指标**（-1~3h）
- 持仓建立表明大户布局
- 筹码转移预示价格启动

---

#### 6. B因子（基差）
**文件**: `ats_core/features/basis.py`

```python
def calculate_basis(spot_price, futures_price, funding_rate):
    """
    基差因子：现货-期货价差 + 资金费率

    范围：-100 ~ +100
    - B > 0：市场乐观（正溢价）
    - B < 0：市场悲观（负溢价）
    """
    # 1. 现货-期货价差
    basis = (futures_price - spot_price) / spot_price * 100

    # 2. 资金费率（市场情绪）
    funding_normalized = funding_rate * 100 / 0.01  # 标准化到-100~+100

    # 3. 综合
    B = basis * 0.5 + funding_normalized * 0.5

    return np.clip(B, -100, 100)
```

**时序特性**：🔴 **滞后指标**（+3~8h）
- 价格上涨后，市场情绪才乐观
- 资金费率反应已发生的价格变化

---

### B层：增强4维因子

#### 7. F因子（资金领先性）
**文件**: `ats_core/factors_v2/fund_leading.py`

```python
def calculate_fund_leading(C_score, price_momentum):
    """
    资金领先性：资金动量 vs 价格动量

    范围：-100 ~ +100
    - F > 0：资金领先价格（蓄势待发）
    - F < 0：价格领先资金（追高/派发）
    """
    # 1. 资金动量（C因子的变化率）
    cvd_momentum = (C_score[-1] - C_score[-10]) / 10

    # 2. 价格动量
    price_momentum = (close[-1] - close[-10]) / close[-10] * 100

    # 3. 资金领先度 = 资金动量 - 价格动量
    F = cvd_momentum - price_momentum

    return np.clip(F, -100, 100)
```

**时序特性**：🟢⭐ **超前指标**（-4~8h）
- F>0：资金大量流入，但价格未动（隐秘建仓）
- F<0：价格已涨，但资金流出（获利派发）
- **最领先的指标，v7.2.29重点优化**

---

#### 8. I因子（市场独立性）
**文件**: `ats_core/factors_v2/independence.py`

```python
def calculate_independence(symbol_returns, btc_returns, eth_returns):
    """
    市场独立性：与BTC/ETH的相关性

    范围：-100 ~ +100
    - I > 60：高独立性（Alpha机会）
    - 0 < I < 60：中等独立性
    - I < 0：强相关（Beta风险）
    """
    # 1. 计算Beta（回归系数）
    X = np.column_stack([btc_returns, eth_returns])
    y = symbol_returns
    beta_btc, beta_eth = np.linalg.lstsq(X, y, rcond=None)[0]

    # 2. R²（拟合优度）
    y_pred = beta_btc * btc_returns + beta_eth * eth_returns
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = 1 - (ss_res / ss_tot)

    # 3. 独立性 = 1 - R²（转换到-100~+100）
    independence = (1 - r_squared) * 100

    # 4. 考虑Beta方向（同向=正，反向=负）
    if beta_btc < -0.5 or beta_eth < -0.5:
        I = -independence  # 强反向相关
    else:
        I = independence

    return I
```

**用途**：
- Gate 5：过滤"低独立性+逆势"的危险信号
- 概率校准：I高时+3%胜率

---

#### 9. L因子（流动性深度）
**文件**: `ats_core/factors_v2/liquidity.py`

```python
def calculate_liquidity(orderbook):
    """
    流动性深度：订单簿深度 + 价差

    范围：0 ~ 100（只有正值）
    - L > 80：流动性极好
    - L < 30：流动性差（滑点风险）
    """
    # 1. 买卖价差
    best_bid = orderbook['bids'][0][0]
    best_ask = orderbook['asks'][0][0]
    spread = (best_ask - best_bid) / best_bid * 100

    # 2. 订单簿深度（前10档）
    bid_depth = sum([order[1] for order in orderbook['bids'][:10]])
    ask_depth = sum([order[1] for order in orderbook['asks'][:10]])
    depth_score = min(bid_depth, ask_depth) / max(bid_depth, ask_depth) * 100

    # 3. 综合
    L = (100 - spread * 50) * 0.3 + depth_score * 0.7

    return np.clip(L, 0, 100)
```

**用途**：
- 避免流动性差的币种（滑点大）
- 影响EV计算中的成本估算

---

#### 10. Q因子（数据质量）
**文件**: `ats_core/factors_v2/quality.py`

```python
def calculate_quality(klines):
    """
    数据质量：K线数量 + 数据完整性

    范围：0 ~ 100（只有正值）
    - Q > 80：数据质量优秀
    - Q < 50：数据质量差（不可信）
    """
    # 1. K线数量
    kline_count = len(klines)
    kline_score = min(kline_count / 300, 1.0) * 100

    # 2. 数据完整性（无缺失、无异常）
    completeness = 1.0
    if np.any(np.isnan(close)):
        completeness -= 0.3
    if np.any(np.diff(close) / close[:-1] > 0.5):  # 跳变>50%
        completeness -= 0.5

    # 3. 综合
    Q = kline_score * 0.5 + completeness * 100 * 0.5

    return np.clip(Q, 0, 100)
```

**用途**：
- Gate 1：数据质量闸门（Q必须>50）

---

## 阶段3：因子分组与加权

### 文件
`ats_core/scoring/factor_groups.py`

### 分组方案（v7.2.29优化）

```python
def calculate_grouped_score(T, M, C, V, O, B, params=None):
    """
    因子分组加权（v7.2.29）

    设计理念：
    - 提高领先指标（C/V/O）权重：43% → 57.3%
    - 降低滞后指标（T/B）权重：50% → 37%
    - 改善因果关系：领先指标主导
    """
    # 从配置读取权重
    if params is None:
        from ats_core.config.threshold_config import get_thresholds
        config = get_thresholds()
        params = config.get_factor_weights()

    # TC组（50%）：趋势 + 资金流
    TC_T_weight = params.get('TC_T_weight', 0.50)  # v7.2.29: 0.70→0.50
    TC_C_weight = params.get('TC_C_weight', 0.50)  # v7.2.29: 0.30→0.50
    TC_group = TC_T_weight * T + TC_C_weight * C

    # VOM组（38%）：量能 + 持仓 + 动量
    VOM_V_weight = params.get('VOM_V_weight', 0.55)  # v7.2.29: 0.50→0.55
    VOM_O_weight = params.get('VOM_O_weight', 0.30)
    VOM_M_weight = params.get('VOM_M_weight', 0.15)  # v7.2.29: 0.20→0.15
    VOM_group = VOM_V_weight * V + VOM_O_weight * O + VOM_M_weight * M

    # B组（12%）：基差
    B_group = B

    # 最终加权
    TC_weight = params.get('TC_weight', 0.50)
    VOM_weight = params.get('VOM_weight', 0.38)  # v7.2.29: 0.35→0.38
    B_weight = params.get('B_weight', 0.12)      # v7.2.29: 0.15→0.12

    weighted_score = TC_weight * TC_group + VOM_weight * VOM_group + B_weight * B_group

    return weighted_score, {
        'TC_group': TC_group,
        'VOM_group': VOM_group,
        'B_group': B_group
    }
```

### 等效权重对比

| 因子 | v7.2.28 | v7.2.29 | 变化 | 类型 |
|------|---------|---------|------|------|
| T | 35% | **25%** | -10% | 🔴 滞后 |
| C | 15% | **25%** | +10% | 🟢 领先 |
| V | 17.5% | **20.9%** | +3.4% | 🟢 领先 |
| O | 10.5% | **11.4%** | +0.9% | 🟢 领先 |
| M | 7% | **5.7%** | -1.3% | 🟡 同步 |
| B | 15% | **12%** | -3% | 🔴 滞后 |

**指标类型统计**：
- 🟢 领先指标（C+V+O）：43% → **57.3%** ✅
- 🔴 滞后指标（T+B）：50% → **37%** ✅
- 🟡 同步指标（M）：7% → 5.7%

---

## 阶段4：蓄势分级

### 文件
`ats_core/pipeline/analyze_symbol_v72.py:200-350`

### 核心逻辑（v7.2.29优化）

```python
# 1. 计算有效F（考虑多空方向）
F_effective = get_effective_F(F_v2, side_long_v72)
# 做多：F_effective = F
# 做空：F_effective = -F

# 2. 读取线性模式参数
linear_params = momentum_config.get('线性模式参数', {})
F_threshold_min = linear_params.get('F_threshold_min', 35)  # v7.2.29: 50→35
F_threshold_max = linear_params.get('F_threshold_max', 60)  # v7.2.29: 70→60
F_extreme_threshold = extreme_config.get('F_extreme_threshold', 75)  # v7.2.29: 90→75

# 3. 判断蓄势级别
if F_effective >= F_extreme_threshold:
    # F≥75：极值警戒（保守策略）
    momentum_level = 3
    momentum_desc = "极限蓄势（警戒）"
    momentum_confidence_min = 12
    momentum_P_min = 0.50
    momentum_position_mult = 0.5

elif F_effective >= F_threshold_max:
    # F≥60：完全降低阈值
    momentum_level = 3
    momentum_desc = "极早期蓄势"

    base_confidence = config.get_mature_threshold('confidence_min', 15)
    base_P = config.get_gate_threshold('gate4_probability', 'P_min', 0.50)

    momentum_confidence_min = base_confidence - 5  # 15→10
    momentum_P_min = base_P - 0.08                 # 0.50→0.42
    momentum_position_mult = 0.5

elif F_effective >= F_threshold_min:
    # 35≤F<60：线性插值
    from ats_core.utils.math_utils import linear_reduce

    # 计算reduction_ratio
    reduction_ratio = (F_effective - F_threshold_min) / (F_threshold_max - F_threshold_min)
    # F=35 → ratio=0.0
    # F=47.5 → ratio=0.5
    # F=60 → ratio=1.0

    # 线性降低阈值
    momentum_confidence_min = linear_reduce(
        F_effective, F_threshold_min, F_threshold_max,
        15, 10  # 从15线性降低到10
    )
    momentum_P_min = linear_reduce(
        F_effective, F_threshold_min, F_threshold_max,
        0.50, 0.42  # 从0.50线性降低到0.42
    )
    momentum_position_mult = linear_reduce(
        F_effective, F_threshold_min, F_threshold_max,
        1.0, 0.5  # 从1.0线性降低到0.5
    )

    # 显示级别（仅用于Telegram）
    if F_effective >= 55:
        momentum_level = 2
        momentum_desc = "早期蓄势"
    else:
        momentum_level = 1
        momentum_desc = "蓄势待发"

else:
    # F<35：正常模式
    momentum_level = 0
    momentum_desc = "正常模式"
    momentum_confidence_min = None  # 使用基准阈值
```

### 阈值降低示例

| F值 | 级别 | confidence_min | P_min | position_mult |
|-----|------|---------------|-------|---------------|
| **F=35** | 开始降低 | 15 | 0.50 | 1.0 |
| **F=40** | 蓄势初显 | 14 | 0.48 | 0.9 |
| **F=47.5** | 蓄势待发 | 12.5 | 0.46 | 0.75 |
| **F=55** | 早期蓄势 | 11 | 0.44 | 0.6 |
| **F=60** | 极早期蓄势 | 10 | 0.42 | 0.5 |
| **F=75** | 极值警戒 | 12 | 0.50 | 0.5 |

### 优化效果

| 指标 | v7.2.28 | v7.2.29 | 改善 |
|------|---------|---------|------|
| **触发率（F≥min）** | 10-15% | **15-25%** | +5-10% |
| **提前量** | 正常 | **提前2-4h** | 显著改善 |
| **覆盖阶段** | 阶段3 | **阶段2** | 更早入场 |

---

## 阶段5：五道闸门检查

### 文件
`ats_core/pipeline/analyze_symbol_v72.py:380-550`

### Gate 1：数据质量闸门

```python
# Q因子检查
Q_score = original_result.get('Q', 50)
kline_count = len(klines)

gate1_passed = (
    Q_score >= 50 and
    kline_count >= 150
)

if not gate1_passed:
    return {
        'gates_passed': False,
        'reason': 'Gate 1: 数据质量不足'
    }
```

**拒绝原因**：
- K线数量不足（<150根）
- 数据有缺失或异常值
- Q因子<50

---

### Gate 2：资金支持闸门

```python
# 使用F_effective（已考虑多空方向）
F_min = momentum_F_min if momentum_level > 0 else config.get_gate_threshold('gate2_fund_support', 'F_min', -10)

gate2_passed = (F_effective >= F_min)

if not gate2_passed:
    return {
        'gates_passed': False,
        'reason': f'Gate 2: 资金支持不足（F={F_effective:.0f} < {F_min}）'
    }
```

**拒绝原因**：
- 做多时F<-10（资金流出）
- 做空时F>10（资金流入，有人抄底）
- 蓄势模式下F未达到更高要求

**v7.2.29改进**：
- 正常模式：F_min = -10
- F≥35模式：F_min线性提高（-10 → 50）
- F≥60模式：F_min = 50（强制要求蓄势）

---

### Gate 3：期望收益闸门

```python
# EV计算（考虑蓄势分级）
盈利目标 = confidence_v72 * 0.01 * 0.5  # 例：confidence=50 → 25%盈利目标
止损 = -0.08 if momentum_level > 0 else -0.10  # 蓄势信号收紧止损
成本 = 0.001  # spread + slippage + fee

EV = P_calibrated * 盈利目标 - (1 - P_calibrated) * abs(止损) - 成本

EV_min = momentum_EV_min if momentum_level > 0 else config.get_gate_threshold('gate3_ev', 'EV_min', 0.015)

gate3_passed = (EV >= EV_min)
```

**拒绝原因**：
- EV < 1.5%（正常模式）
- EV < 0.8%（F≥60模式，降低要求）

---

### Gate 4：概率闸门

```python
# 使用统计校准后的概率（见阶段6）
P_min = momentum_P_min if momentum_level > 0 else config.get_gate_threshold('gate4_probability', 'P_min', 0.50)

gate4_passed = (P_calibrated >= P_min)
```

**拒绝原因**：
- P < 50%（正常模式）
- P < 42%（F≥60模式，降低要求）

---

### Gate 5：独立性×市场闸门

```python
I_v2 = original_result.get('I', 50)
market_regime = original_result.get('market_regime', 0)  # BTC趋势强度

if I_v2 >= 60:
    # 高独立性：直接通过
    gates_independence_market = 1.0
    conflict_mult = 1.0

elif I_v2 >= 0:
    # 中等独立性：检查是否逆势
    I_min = config.get_gate_threshold('gate5_independence_market', 'I_min', 0)
    market_regime_threshold = config.get_gate_threshold('gate5_independence_market', 'market_regime_threshold', 30)

    if side_long_v72 and market_regime < -market_regime_threshold:
        # 做多 + 熊市 → 逆势，拒绝
        gates_independence_market = 0.0
        conflict_mult = 0.0
        reason = "Gate 5: 低独立性+做多逆势（熊市中做多）"
    elif not side_long_v72 and market_regime > market_regime_threshold:
        # 做空 + 牛市 → 逆势，拒绝
        gates_independence_market = 0.0
        conflict_mult = 0.0
        reason = "Gate 5: 低独立性+做空逆势（牛市中做空）"
    else:
        # 顺势 → 放大confidence
        gates_independence_market = 1.0
        conflict_mult = 1.2  # 顺势信号更可靠

else:
    # I<0：强相关
    # 同样检查逆势
    if (side_long_v72 and market_regime < -30) or (not side_long_v72 and market_regime > 30):
        gates_independence_market = 0.0
        conflict_mult = 0.0
    else:
        gates_independence_market = 1.0
        conflict_mult = 1.0

gate5_passed = (gates_independence_market > 0)
```

**拒绝原因**：
- 低独立性（0≤I<30）+ 做多逆势（熊市）
- 低独立性（0≤I<30）+ 做空逆势（牛市）

---

### 闸门通过汇总

```python
all_gates_passed = (
    gate1_passed and
    gate2_passed and
    gate3_passed and
    gate4_passed and
    gate5_passed
)

confidence_adjusted = confidence_v72 * conflict_mult
```

---

## 阶段6：概率校准与EV计算

### 文件
`ats_core/calibration/empirical_calibration.py`

### 概率校准公式（v7.2.29优化）

```python
def _bootstrap_probability(self, confidence, F_score, I_score, side_long=True):
    """
    概率校准（v7.2.28修复：支持side_long参数）

    P_calibrated = P_base + F_bonus + I_bonus
    """
    from ats_core.utils.math_utils import linear_reduce, get_effective_F

    # 1. 基准概率（confidence驱动）
    P_base = 0.45 + (confidence / 100.0) * 0.23
    # confidence=0 → P=0.45
    # confidence=50 → P=0.565
    # confidence=100 → P=0.68

    # 2. F因子线性校准（v7.2.29优化）
    F_effective = get_effective_F(F_score, side_long)

    F_bonus_max = 60  # v7.2.29: 70→60
    F_bonus_min = -20  # v7.2.29: -30→-20

    if F_effective >= F_bonus_max:
        P_bonus_F = 0.05  # +5%
    elif F_effective >= 0:
        # 0<F<60：线性插值
        P_bonus_F = linear_reduce(F_effective, 0, F_bonus_max, 0, 0.05)
        # F=30 → +2.5%
        # F=40 → +3.3%
        # F=50 → +4.2%
    elif F_effective >= F_bonus_min:
        # -20<F<0：线性插值
        P_bonus_F = linear_reduce(F_effective, F_bonus_min, 0, -0.03, 0)
        # F=-10 → -1.5%
    else:
        P_bonus_F = -0.03  # -3%

    # 3. I因子线性校准
    I_bonus_max = 80
    I_bonus_min = 20

    if I_score >= I_bonus_max:
        P_bonus_I = 0.03  # +3%
    elif I_score >= 50:
        P_bonus_I = linear_reduce(I_score, 50, I_bonus_max, 0, 0.03)
    elif I_score >= I_bonus_min:
        P_bonus_I = linear_reduce(I_score, I_bonus_min, 50, 0, 0)
    elif I_score >= 0:
        P_bonus_I = linear_reduce(I_score, 0, I_bonus_min, -0.02, 0)
    else:
        P_bonus_I = -0.02  # -2%

    # 4. 最终概率
    P_calibrated = P_base + P_bonus_F + P_bonus_I
    P_calibrated = np.clip(P_calibrated, 0.35, 0.85)

    return P_calibrated
```

### 概率校准示例

| confidence | F | I | P_base | F_bonus | I_bonus | P_calibrated |
|-----------|---|---|--------|---------|---------|--------------|
| 50 | 60 | 70 | 0.565 | +0.05 | +0.025 | **0.64** |
| 40 | 40 | 50 | 0.542 | +0.033 | 0 | **0.575** |
| 30 | 20 | 30 | 0.519 | +0.017 | 0 | **0.536** |
| 50 | -10 | 40 | 0.565 | -0.015 | +0.01 | **0.56** |

### EV计算

```python
def calculate_ev(P_calibrated, confidence, momentum_level):
    """
    期望收益计算
    """
    # 盈利目标（根据confidence）
    profit_target = confidence * 0.01 * 0.5  # confidence=50 → 25%盈利

    # 止损（根据蓄势级别）
    if momentum_level > 0:
        stop_loss = -0.08  # 蓄势信号收紧
    else:
        stop_loss = -0.10  # 正常止损

    # 成本（spread + slippage + fee）
    cost = 0.001  # 0.1%

    # EV
    EV = P_calibrated * profit_target - (1 - P_calibrated) * abs(stop_loss) - cost

    return EV
```

---

## 阶段7：AntiJitter过滤

### 文件
`scripts/realtime_signal_scanner.py:600-800`

### 三层防抖机制

#### Layer 1：Hysteresis（滞后）

```python
class HysteresisFilter:
    """滞后过滤器：防止信号在阈值附近反复进出"""

    def __init__(self):
        self.threshold_high = 20  # 进入阈值
        self.threshold_low = 15   # 退出阈值
        self.current_state = {}   # {symbol: bool}

    def filter(self, symbol, confidence):
        current = self.current_state.get(symbol, False)

        if not current:
            # 当前不在信号中：需要超过threshold_high才进入
            if confidence >= self.threshold_high:
                self.current_state[symbol] = True
                return True
            else:
                return False
        else:
            # 当前在信号中：低于threshold_low才退出
            if confidence < self.threshold_low:
                self.current_state[symbol] = False
                return False
            else:
                return True
```

**示例**：
```
Time  Confidence  State    Action
t0    18          False    → 拒绝（<20）
t1    21          False    → 进入（≥20）
t2    19          True     → 保持（≥15）
t3    17          True     → 保持（≥15）
t4    14          True     → 退出（<15）
```

---

#### Layer 2：Persistence（持久性）

```python
class PersistenceFilter:
    """持久性过滤器：信号需持续N次扫描才发布"""

    def __init__(self, required_count=3):
        self.required_count = required_count  # 需要3次确认
        self.counter = {}  # {symbol: count}

    def filter(self, symbol, passed):
        if passed:
            # 信号通过：计数+1
            self.counter[symbol] = self.counter.get(symbol, 0) + 1

            if self.counter[symbol] >= self.required_count:
                return True  # 持续3次，发布
            else:
                return False  # 还未持续足够次数
        else:
            # 信号未通过：重置计数
            self.counter[symbol] = 0
            return False
```

**示例**（扫描间隔5分钟）：
```
Time  Passed  Count  Publish
t0    True    1      → 否（需要3次）
t5    True    2      → 否（需要3次）
t10   True    3      → 是（持续15分钟）✅
t15   True    3      → 是（持续发布）
t20   False   0      → 否（重置）
```

---

#### Layer 3：Cooldown（冷却期）

```python
class CooldownFilter:
    """冷却期过滤器：同币种信号间隔X小时"""

    def __init__(self, cooldown_hours=12):
        self.cooldown_hours = cooldown_hours
        self.last_signal_time = {}  # {symbol: timestamp}

    def filter(self, symbol):
        now = datetime.now()
        last_time = self.last_signal_time.get(symbol)

        if last_time is None:
            # 首次信号
            self.last_signal_time[symbol] = now
            return True
        else:
            # 检查是否过了冷却期
            elapsed = (now - last_time).total_seconds() / 3600

            if elapsed >= self.cooldown_hours:
                self.last_signal_time[symbol] = now
                return True
            else:
                return False  # 冷却期内，拒绝
```

**示例**：
```
Time         Action              Result
00:00        BTCUSDT发信号        → 发布✅
04:00        BTCUSDT再次出现      → 拒绝（冷却期12h）
12:00        BTCUSDT再次出现      → 发布✅（过了冷却期）
```

---

### 综合过滤流程

```python
def filter_prime_signals_v72(results):
    """综合过滤流程"""
    filtered = []

    for result in results:
        symbol = result['symbol']
        confidence = result['confidence_adjusted']
        gates_passed = result['all_gates_passed']

        # 基础检查
        if not gates_passed:
            continue

        # Layer 1: Hysteresis
        if not hysteresis_filter.filter(symbol, confidence):
            continue

        # Layer 2: Persistence
        if not persistence_filter.filter(symbol, True):
            continue

        # Layer 3: Cooldown
        if not cooldown_filter.filter(symbol):
            continue

        # 通过所有过滤
        filtered.append(result)

    # 按confidence_adjusted排序
    filtered.sort(key=lambda x: x['confidence_adjusted'], reverse=True)

    return filtered
```

---

## 阶段8：Telegram消息生成

### 文件
`ats_core/outputs/telegram_fmt.py`

### 消息模板

```python
def render_trade_v72(result):
    """
    生成Telegram交易信号消息（v7.2增强版）
    """
    # === 1. 基本信息 ===
    symbol = result['symbol']
    side = "🟢 做多" if result['side_long'] else "🔴 做空"
    price = result['price']

    confidence = result['confidence_adjusted']  # 已包含conflict_mult
    P_calibrated = result['P_calibrated']
    EV = result['EV']

    # === 2. 蓄势分级标记（v7.2.29） ===
    F_v2 = result.get('F', 0)
    momentum_level = result.get('momentum_level', 0)
    momentum_desc = result.get('momentum_desc', '正常模式')

    if momentum_level >= 3:
        momentum_emoji = "🚀🚀🚀"
        position_mult = 0.5
    elif momentum_level == 2:
        momentum_emoji = "🚀🚀"
        position_mult = 0.7
    elif momentum_level == 1:
        momentum_emoji = "🚀"
        position_mult = 0.9
    else:
        momentum_emoji = ""
        position_mult = 1.0

    # === 3. 消息头部 ===
    msg = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{momentum_emoji} {symbol} {side} 信号 {momentum_emoji}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 当前价格: ${price:.4f}
📊 信心度: {confidence:.1f}
🎯 胜率: {P_calibrated*100:.1f}%
💵 期望收益: {EV*100:.2f}%
"""

    if momentum_level > 0:
        msg += f"\n⚡ 蓄势状态: {momentum_desc}\n"
        msg += f"📦 建议仓位: {position_mult*100:.0f}%（蓄势信号降低仓位）\n"

    # === 4. 因子分析 ===
    msg += "\n📈 因子分析（A层6+B层4）:\n"

    # A层因子
    T = result.get('T', 0)
    M = result.get('M', 0)
    C = result.get('C', 0)
    V = result.get('V', 0)
    O = result.get('O', 0)
    B = result.get('B', 0)

    msg += f"  T 趋势强度  {T:+4.0f}  {get_factor_desc(T)}\n"
    msg += f"  M 价格动量  {M:+4.0f}  {get_factor_desc(M)}\n"
    msg += f"  C 资金流向  {C:+4.0f}  {get_factor_desc(C)}\n"
    msg += f"  V 量能放大  {V:+4.0f}  {get_factor_desc(V)}\n"
    msg += f"  O 持仓变化  {O:+4.0f}  {get_factor_desc(O)}\n"
    msg += f"  B 基差情绪  {B:+4.0f}  {get_factor_desc(B)}\n"

    # B层因子
    F_v2 = result.get('F', 0)
    I_v2 = result.get('I', 0)
    L_v2 = result.get('L', 0)
    Q_v2 = result.get('Q', 0)

    msg += f"\n  F 资金领先  {F_v2:+4.0f}  {get_factor_desc(F_v2)}"
    if momentum_level > 0:
        msg += f" {momentum_emoji}"
    msg += "\n"

    msg += f"  I 市场独立  {I_v2:+4.0f}  {get_factor_desc(I_v2)}\n"

    # I因子详细信息（Beta值）
    I_meta = result.get('I_meta', {})
    beta_btc = I_meta.get('beta_btc', 0)
    beta_eth = I_meta.get('beta_eth', 0)
    msg += f"     Beta: BTC={beta_btc:.2f} ETH={beta_eth:.2f}\n"

    # 大盘对齐分析
    market_regime = result.get('market_regime', 0)
    if market_regime > 30:
        market_trend = "牛市"
        market_icon = "🐂"
    elif market_regime < -30:
        market_trend = "熊市"
        market_icon = "🐻"
    else:
        market_trend = "震荡"
        market_icon = "🦀"

    msg += f"     {market_icon} 大盘{market_trend}({market_regime:+.0f})"

    # 对齐分析
    if result.get('conflict_mult', 1.0) > 1.0:
        msg += f" ✅ 顺势而为\n"
    elif result.get('conflict_mult', 1.0) == 0:
        msg += f" ⚠️ 逆势风险（已拒绝）\n"
    else:
        msg += "\n"

    msg += f"  L 流动性  {L_v2:+4.0f}  {get_factor_desc(L_v2)}\n"
    msg += f"  Q 数据质量  {Q_v2:+4.0f}  {get_factor_desc(Q_v2)}\n"

    # === 5. 质量检查（5道闸门） ===
    msg += "\n🔒 质量检查（5道闸门）:\n"

    gates_detail = result.get('gates_detail', {})
    gate1 = gates_detail.get('gate1_data_quality', False)
    gate2 = gates_detail.get('gate2_fund_support', False)
    gate3 = gates_detail.get('gate3_ev', False)
    gate4 = gates_detail.get('gate4_probability', False)
    gate5 = gates_detail.get('gate5_independence_market', False)

    msg += f"  {'✅' if gate1 else '❌'} Gate 1: 数据质量\n"
    msg += f"  {'✅' if gate2 else '❌'} Gate 2: 资金支持\n"
    msg += f"  {'✅' if gate3 else '❌'} Gate 3: 期望收益\n"
    msg += f"  {'✅' if gate4 else '❌'} Gate 4: 胜率达标\n"
    msg += f"  {'✅' if gate5 else '❌'} Gate 5: 独立性×市场\n"

    # === 6. 操作建议 ===
    msg += "\n💡 操作建议:\n"

    # 入场价格
    entry_price = price
    msg += f"  📍 入场: ${entry_price:.4f}\n"

    # 止损（根据蓄势级别调整）
    if momentum_level > 0:
        stop_loss_pct = 0.08  # 蓄势信号收紧
    else:
        stop_loss_pct = 0.10

    if result['side_long']:
        stop_loss = entry_price * (1 - stop_loss_pct)
        target = entry_price * (1 + confidence * 0.01 * 0.5)
    else:
        stop_loss = entry_price * (1 + stop_loss_pct)
        target = entry_price * (1 - confidence * 0.01 * 0.5)

    msg += f"  🛑 止损: ${stop_loss:.4f} ({stop_loss_pct*100:.0f}%)\n"
    msg += f"  🎯 目标: ${target:.4f} ({confidence*0.5:.1f}%)\n"

    # 仓位建议
    msg += f"  📦 仓位: {position_mult*100:.0f}%"
    if momentum_level > 0:
        msg += " （蓄势信号降低仓位）"
    msg += "\n"

    # === 7. 风险提示 ===
    if momentum_level > 0:
        msg += "\n⚠️ 蓄势信号风险提示:\n"
        msg += "  • 入场时机更早，短期波动可能更大\n"
        msg += "  • 建议降低仓位以控制风险\n"
        msg += "  • 止损比正常信号收紧20%\n"

    if I_v2 < 30 and result.get('conflict_mult', 1.0) == 1.0:
        msg += "\n⚠️ 低独立性提示:\n"
        msg += f"  • 该币种与大盘相关性较高（I={I_v2:.0f}）\n"
        msg += f"  • 需密切关注BTC走势\n"

    msg += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"🕐 信号时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

    return msg
```

### 因子描述函数

```python
def get_factor_desc(score):
    """根据分数返回描述"""
    abs_score = abs(score)

    if abs_score >= 80:
        level = "极强"
        emoji = "🔥🔥🔥"
    elif abs_score >= 60:
        level = "很强"
        emoji = "🔥🔥"
    elif abs_score >= 40:
        level = "较强"
        emoji = "🔥"
    elif abs_score >= 20:
        level = "中等"
        emoji = "➡️"
    else:
        level = "较弱"
        emoji = "💤"

    direction = "看涨" if score > 0 else "看跌"

    return f"{emoji} {direction}{level}"
```

---

## 阶段9：信号发布

### 文件
`scripts/realtime_signal_scanner.py:900-1000`

### 发布流程

```python
def send_signals_to_telegram_v72(signals):
    """发送信号到Telegram"""

    if len(signals) == 0:
        logging.info("无信号发送")
        return

    # 按confidence_adjusted排序（已包含conflict_mult）
    sorted_signals = sorted(
        signals,
        key=lambda s: s['confidence_adjusted'],
        reverse=True
    )

    # 限制每次发送数量（避免刷屏）
    max_signals_per_scan = 5
    signals_to_send = sorted_signals[:max_signals_per_scan]

    logging.info(f"本次扫描发现 {len(signals)} 个信号，发送前 {len(signals_to_send)} 个")

    for i, signal in enumerate(signals_to_send):
        try:
            # 生成消息
            message = render_trade_v72(signal)

            # 发送到Telegram
            bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=message,
                parse_mode='Markdown'
            )

            # 记录日志
            logging.info(f"✅ 已发送信号 {i+1}/{len(signals_to_send)}: {signal['symbol']} {signal['side']}")

            # 更新AntiJitter状态
            cooldown_filter.mark_sent(signal['symbol'])

            # 间隔发送（避免触发Telegram限流）
            if i < len(signals_to_send) - 1:
                time.sleep(2)

        except Exception as e:
            logging.error(f"❌ 发送信号失败: {signal['symbol']} - {e}")
            continue

    # 保存信号历史（用于统计和回测）
    save_signal_history(signals_to_send)
```

### 信号历史记录

```python
def save_signal_history(signals):
    """保存信号到历史文件"""
    history_file = 'data/signal_history.json'

    # 加载现有历史
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            history = json.load(f)
    else:
        history = []

    # 添加新信号
    for signal in signals:
        history.append({
            'timestamp': datetime.now().isoformat(),
            'symbol': signal['symbol'],
            'side': 'LONG' if signal['side_long'] else 'SHORT',
            'price': signal['price'],
            'confidence': signal['confidence_adjusted'],
            'P_calibrated': signal['P_calibrated'],
            'EV': signal['EV'],
            'F': signal.get('F', 0),
            'I': signal.get('I', 0),
            'momentum_level': signal.get('momentum_level', 0)
        })

    # 保存（保留最近1000条）
    history = history[-1000:]
    with open(history_file, 'w') as f:
        json.dump(history, f, indent=2)
```

---

## 关键文件索引

### 数据采集
- `scripts/realtime_signal_scanner.py`: 主扫描器（入口）

### 因子计算
- `ats_core/features/trend.py`: T因子
- `ats_core/features/momentum.py`: M因子
- `ats_core/features/capital.py`: C因子
- `ats_core/features/volume.py`: V因子
- `ats_core/features/openinterest.py`: O因子
- `ats_core/features/basis.py`: B因子
- `ats_core/factors_v2/fund_leading.py`: F因子
- `ats_core/factors_v2/independence.py`: I因子
- `ats_core/factors_v2/liquidity.py`: L因子
- `ats_core/factors_v2/quality.py`: Q因子

### 评分与闸门
- `ats_core/pipeline/analyze_symbol.py`: 基础分析
- `ats_core/pipeline/analyze_symbol_v72.py`: v7.2增强分析（蓄势分级+5闸门）
- `ats_core/scoring/factor_groups.py`: 因子分组加权
- `ats_core/calibration/empirical_calibration.py`: 概率校准

### 输出格式
- `ats_core/outputs/telegram_fmt.py`: Telegram消息格式化

### 配置文件
- `config/signal_thresholds.json`: 所有阈值和权重配置

### 工具函数
- `ats_core/utils/math_utils.py`: 数学工具（linear_reduce, get_effective_F等）
- `ats_core/config/threshold_config.py`: 配置管理器

---

## 总结

整个系统从数据采集到信号发布，经历了9个阶段：

1. **数据采集**：获取K线、CVD、OI等原始数据
2. **因子计算**：计算10维因子（6+4）
3. **因子分组与加权**：v7.2.29优化，领先指标主导（57.3%）
4. **蓄势分级**：v7.2.29优化，F≥35就开始降低阈值
5. **五道闸门检查**：数据质量、资金支持、EV、概率、独立性×市场
6. **概率校准与EV计算**：F/I因子线性校准
7. **AntiJitter过滤**：Hysteresis + Persistence + Cooldown三层防抖
8. **Telegram消息生成**：包含因子分析、蓄势标记、操作建议
9. **信号发布**：发送到Telegram + 记录历史

**v7.2.29核心优化**：
- ✅ 提高领先指标（C/V/O）权重：43% → 57.3%
- ✅ 降低F阈值：F≥50 → F≥35（提前2-4h捕捉信号）
- ✅ 改善概率激励：F≥60 → +5%（原F≥70）

**系统优势**：
- 🎯 多维度评估（10维因子）
- 🔒 严格质量控制（5道闸门）
- 🚀 提前信号捕捉（蓄势分级）
- 🛡️ 防抖机制完善（3层过滤）
- 📊 透明度高（完整因子展示）
