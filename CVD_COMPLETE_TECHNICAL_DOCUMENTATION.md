# CVD完整技术文档

**创建日期**: 2025-11-12
**追踪起点**: `./setup.sh`
**追踪方法**: 完整代码审查（非拍脑袋）

---

## 执行摘要

本文档从系统启动入口`setup.sh`出发，完整追踪CVD（Cumulative Volume Delta）的：
1. **计算位置** - CVD计算在哪个文件
2. **数据获取** - 数据是否符合要求（真实takerBuyVolume）
3. **计算公式** - 详细的数学公式
4. **应用方式** - CVD在系统中如何被使用

---

## 1. CVD计算位置（从setup.sh追踪）

### 1.1 系统启动流程

```bash
# setup.sh:184 - 系统启动入口
nohup python3 scripts/realtime_signal_scanner.py --interval 300 > "$LOG_FILE" 2>&1 &
```

**追踪路径**:
```
setup.sh (line 184)
  ↓
scripts/realtime_signal_scanner.py
  ↓ (line 54)
ats_core/pipeline/batch_scan_optimized.py → OptimizedBatchScanner
  ↓ (line 1168)
ats_core/pipeline/analyze_symbol.py → analyze_symbol()
  ↓ (line 490)
ats_core/features/cvd.py → cvd_mix_with_oi_price()
  ↓ (line 272)
ats_core/features/cvd.py → cvd_from_klines()
```

### 1.2 CVD计算核心文件

**主要文件**: `ats_core/features/cvd.py`

**核心函数**:
1. `cvd_from_klines()` - 单一市场CVD计算（期货或现货）
2. `cvd_combined()` - 现货+期货组合CVD
3. `cvd_mix_with_oi_price()` - CVD + OI + 价格综合信号

**调用文件**:
- `ats_core/pipeline/analyze_symbol.py:490` - 主分析流程
- `ats_core/features/fund_leading.py:229` - F因子计算
- `ats_core/features/multi_timeframe.py:50` - 多时间框架分析

---

## 2. 数据获取方式（从源头追踪）

### 2.1 K线数据获取流程

```python
# analyze_symbol.py:1677-1694
k1 = get_klines(symbol, "1h", 300)              # 期货1h K线
spot_k1 = get_spot_klines(symbol, "1h", 300)   # 现货1h K线

# ↓ 调用 ↓

# ats_core/sources/binance.py:121
def get_klines(symbol: str, interval: str, limit: int = 300) -> List[list]:
    """
    返回符合 Binance /fapi/v1/klines 规范的二维数组

    API端点: GET /fapi/v1/klines (Binance Futures API)

    每条记录字段（12列）：
      [0]  openTime             - 开盘时间（毫秒时间戳）
      [1]  open                 - 开盘价
      [2]  high                 - 最高价
      [3]  low                  - 最低价
      [4]  close                - 收盘价
      [5]  volume               - 成交量（按币种计价）
      [6]  closeTime            - 收盘时间
      [7]  quoteAssetVolume     - 成交额（按USDT计价）
      [8]  numberOfTrades       - 成交笔数
      [9]  takerBuyBaseVolume   - 主动买入量（按币种计价）✅ CVD关键数据
      [10] takerBuyQuoteVolume  - 主动买入额（按USDT计价）
      [11] ignore               - 忽略字段
    """
    return _get("/fapi/v1/klines", params, timeout=10.0, retries=2)
```

### 2.2 数据质量验证

**验证点1**: K线数据包含`takerBuyVolume`（第9列）
```python
# cvd.py:71 - 数据格式检查
if use_taker_buy and klines and len(klines[0]) >= 10:
    taker_buy = _col(klines, 9)  # ✅ 使用真实主动买入量
```

**验证点2**: Binance API原生支持
- **期货API**: `/fapi/v1/klines` - 支持takerBuyBaseVolume
- **现货API**: `/api/v3/klines` - 支持takerBuyBaseVolume
- **数据来源**: 逐笔成交的`isBuyerMaker`字段聚合而成

**结论**: ✅ **数据获取符合要求**
- 使用Binance官方API提供的真实`takerBuyVolume`
- **不是**基于K线阳线阴线的估算
- 每笔成交都有真实的买卖方向标记

---

## 3. CVD计算公式（详细数学定义）

### 3.1 基础CVD计算

**函数**: `cvd_from_klines()`
**位置**: `ats_core/features/cvd.py:43-101`

#### 3.1.1 输入数据

```python
klines = [
    [openTime, open, high, low, close, volume, closeTime, quoteVolume,
     trades, takerBuyVolume, takerBuyQuoteVolume, ignore],
    # ... 更多K线
]
```

#### 3.1.2 计算公式

**步骤1**: 提取关键数据
```python
taker_buy[i] = klines[i][9]  # 主动买入量
total_vol[i] = klines[i][5]  # 总成交量
```

**步骤2**: 计算每根K线的CVD增量
```python
# 理论推导：
# buy_vol + sell_vol = total_vol
# sell_vol = total_vol - buy_vol
# delta = buy_vol - sell_vol
#       = buy_vol - (total_vol - buy_vol)
#       = 2 * buy_vol - total_vol

delta[i] = 2.0 * taker_buy[i] - total_vol[i]
```

**步骤3**: 累积CVD
```python
CVD[0] = delta[0]
CVD[i] = CVD[i-1] + delta[i]  # for i > 0

# 数学表达式：
CVD[i] = Σ(j=0 to i) delta[j]
       = Σ(j=0 to i) (2 * takerBuy[j] - totalVol[j])
```

#### 3.1.3 完整代码实现

```python
# cvd.py:71-100
if use_taker_buy and klines and len(klines[0]) >= 10:
    # 提取数据
    taker_buy = _col(klines, 9)  # 主动买入量
    total_vol = _col(klines, 5)  # 总成交量
    n = min(len(taker_buy), len(total_vol))

    # 计算delta序列
    deltas: List[float] = []
    for i in range(n):
        buy = taker_buy[i]
        total = total_vol[i]
        if not (math.isfinite(buy) and math.isfinite(total)):
            deltas.append(0.0)
        else:
            delta = 2.0 * buy - total  # buy_vol - sell_vol
            deltas.append(delta)

    # 异常值处理（可选）
    if filter_outliers and n >= 20:
        outlier_mask = detect_volume_outliers(total_vol, deltas, multiplier=1.5)
        deltas = apply_outlier_weights(deltas, outlier_mask, outlier_weight)

    # 累积CVD
    s = 0.0
    cvd: List[float] = []
    for delta in deltas:
        s += delta
        cvd.append(s)

    return cvd
```

#### 3.1.4 异常值处理（v2.1新增）

**目的**: 对巨量K线降权，避免被单笔大额交易误导

**方法**: IQR（Interquartile Range）检测
```python
# cvd.py:77-92
if filter_outliers and n >= 20:
    # 1. 检测成交量异常值（IQR方法）
    outlier_mask = detect_volume_outliers(
        total_vol,      # 成交量序列
        deltas,         # CVD增量序列
        multiplier=1.5  # IQR倍数（1.5表示温和异常值）
    )

    # 2. 对异常值降权
    deltas = apply_outlier_weights(
        deltas,
        outlier_mask,
        outlier_weight=0.5  # 降低到50%权重
    )
```

**公式**:
```
Q1 = 第25百分位数
Q3 = 第75百分位数
IQR = Q3 - Q1

异常值定义:
  volume > Q3 + 1.5 * IQR  或  volume < Q1 - 1.5 * IQR

降权处理:
  delta_adjusted = delta * outlier_weight  (若为异常值)
  delta_adjusted = delta                   (若为正常值)
```

---

### 3.2 现货+期货组合CVD

**函数**: `cvd_combined()`
**位置**: `ats_core/features/cvd.py:150-245`

#### 3.2.1 动态权重计算

**方法**: 按成交额（USDT）比例动态计算权重

```python
# cvd.py:189-206
if use_dynamic_weight:
    # K线第7列：quoteAssetVolume（成交额，单位USDT）
    futures_quote_volume = Σ klines_futures[i][7]
    spot_quote_volume = Σ klines_spot[i][7]
    total_quote = futures_quote_volume + spot_quote_volume

    futures_weight = futures_quote_volume / total_quote
    spot_weight = spot_quote_volume / total_quote
else:
    # 固定权重（降级方案）
    futures_weight = 0.7
    spot_weight = 0.3
```

**示例计算**:
```
假设某币种：
  期货日成交额: 10亿USDT
  现货日成交额: 1亿USDT

动态权重：
  futures_weight = 10亿 / 11亿 = 90.9%
  spot_weight = 1亿 / 11亿 = 9.1%
```

#### 3.2.2 加权组合公式

**步骤1**: 分别计算期货和现货CVD
```python
cvd_futures = cvd_from_klines(futures_klines, use_taker_buy=True)
cvd_spot = cvd_from_klines(spot_klines, use_taker_buy=True)
```

**步骤2**: 计算每根K线的CVD增量
```python
for i in range(n):
    if i == 0:
        delta_f = cvd_futures[i]
        delta_s = cvd_spot[i]
    else:
        delta_f = cvd_futures[i] - cvd_futures[i-1]
        delta_s = cvd_spot[i] - cvd_spot[i-1]
```

**步骤3**: 加权混合增量
```python
combined_delta[i] = futures_weight * delta_f + spot_weight * delta_s
```

**步骤4**: 累积组合CVD
```python
CVD_combined[0] = combined_delta[0]
CVD_combined[i] = CVD_combined[i-1] + combined_delta[i]
```

**完整数学表达式**:
```
设：
  w_f = futures_weight
  w_s = spot_weight
  Δ_f[i] = cvd_futures[i] - cvd_futures[i-1]
  Δ_s[i] = cvd_spot[i] - cvd_spot[i-1]

则：
  CVD_combined[i] = Σ(j=0 to i) (w_f * Δ_f[j] + w_s * Δ_s[j])
```

---

### 3.3 CVD + OI + 价格综合信号

**函数**: `cvd_mix_with_oi_price()`
**位置**: `ats_core/features/cvd.py:248-304`

#### 3.3.1 输入数据

```python
klines          # 期货K线数据
oi_hist         # 持仓量历史数据 [{"sumOpenInterest": value}, ...]
spot_klines     # 现货K线数据（可选）
```

#### 3.3.2 计算流程

**步骤1**: 计算CVD（现货+期货组合，如果有现货数据）
```python
if spot_klines and len(spot_klines) > 0:
    cvd = cvd_combined(klines, spot_klines)  # 组合CVD
else:
    cvd = cvd_from_klines(klines, use_taker_buy=True)  # 仅期货CVD
```

**步骤2**: 提取价格收益率序列
```python
closes = [float(k[4]) for k in klines]  # 收盘价
ret_p = pct_change(closes)              # 价格变化率

# pct_change定义：
ret_p[0] = 0
ret_p[i] = (closes[i] - closes[i-1]) / closes[i-1]  # for i > 0
```

**步骤3**: 提取OI变化率序列
```python
oi_vals = [d["sumOpenInterest"] for d in oi_hist]
d_oi = pct_change(oi_vals)  # OI变化率
```

**步骤4**: Z-score标准化
```python
# 标准化公式：
# z[i] = (x[i] - mean(x)) / std(x)

z_cvd = z_all(cvd)    # CVD标准化
z_p = z_all(ret_p)    # 价格收益率标准化
z_oi = z_all(d_oi)    # OI变化率标准化
```

**步骤5**: 加权组合
```python
# cvd.py:303 - CVD权重提升（更重要）
mix[i] = 1.2 * z_cvd[i] + 0.4 * z_p[i] + 0.4 * z_oi[i]

# 权重配置：
#   CVD: 60% (1.2 / 2.0)
#   价格: 20% (0.4 / 2.0)
#   OI: 20% (0.4 / 2.0)
```

#### 3.3.3 返回值

```python
return (cvd_series, mix_series)

# cvd_series: 原始CVD序列（现货+期货组合）
# mix_series: 综合强度（标准化），越大代表量价+OI同向越强
```

#### 3.3.4 完整数学定义

```
设：
  C[i] = CVD值
  P[i] = 价格
  O[i] = OI值

价格收益率：
  r_p[i] = (P[i] - P[i-1]) / P[i-1]

OI变化率：
  r_o[i] = (O[i] - O[i-1]) / O[i-1]

Z-score标准化：
  z_C[i] = (C[i] - μ_C) / σ_C
  z_p[i] = (r_p[i] - μ_p) / σ_p
  z_o[i] = (r_o[i] - μ_o) / σ_o

综合强度：
  mix[i] = 1.2 * z_C[i] + 0.4 * z_p[i] + 0.4 * z_o[i]
```

---

## 4. CVD应用方式（在系统中的使用）

### 4.1 应用位置汇总

| 应用位置 | 函数/模块 | 用途 | 重要性 |
|---------|----------|------|--------|
| C因子（CVD流向） | `analyze_symbol.py:509` | 方向因子评分 | 核心 |
| F因子（资金领先性） | `fund_leading.py:229` | 资金动量计算 | 核心 |
| O因子（持仓量） | `analyze_symbol.py:526` | 辅助OI判断 | 辅助 |
| 多时间框架 | `multi_timeframe.py:50` | C维度得分 | 次要 |

### 4.2 应用1: C因子（CVD Flow）

**位置**: `ats_core/pipeline/analyze_symbol.py:509`

**流程**:
```python
# 1. 计算CVD序列
cvd_series, cvd_mix = cvd_mix_with_oi_price(k1, oi_data, spot_klines=spot_k1)

# 2. 计算C因子得分
C, C_meta = _calc_cvd_flow(cvd_series, c, params, klines=k1)
  ↓
# ats_core/features/cvd_flow.py:score_cvd_flow()
```

**C因子计算逻辑**:
```python
# cvd_flow.py（简化）

# 1. CVD动量（最近7期的变化速度）
cvd_momentum = [
    (cvd_series[i] - cvd_series[i-7]) / 7
    for i in range(-4, 0)  # 最近4期
]

# 2. CVD加速度（动量的变化）
cvd_accel = [
    cvd_momentum[i] - cvd_momentum[i-1]
    for i in range(1, len(cvd_momentum))
]

# 3. 综合评分（-100到+100）
C_score = f(cvd_change, cvd_momentum, cvd_accel)
```

**C因子意义**:
- **C > 0**: 资金流入（买盘主导）
- **C < 0**: 资金流出（卖盘主导）
- **C的权重**: 在6因子系统中占25%（与T、M、V、O、B共同决定方向）

---

### 4.3 应用2: F因子（资金领先性）

**位置**: `ats_core/features/fund_leading.py:229`

**流程**:
```python
# analyze_symbol.py:622
F, F_meta = score_fund_leading_v2(
    cvd_series=cvd_series,
    oi_data=oi_data,
    klines=k1,
    atr_now=atr_now,
    params=params
)
```

**F因子计算公式**:
```python
# fund_leading.py:306-330（简化）

# 1. 价格变化（6小时窗口）
price_6h_ago = closes[-7]
price_change_6h = close_now - price_6h_ago
price_momentum = price_change_6h / atr_now  # 归一化到ATR

# 2. CVD变化（6小时窗口）
cvd_6h_ago = cvd_series[-7]
cvd_change_6h = cvd_series[-1] - cvd_6h_ago
cvd_momentum = cvd_change_6h / close_now  # 归一化到价格

# 3. OI变化（6小时窗口）
oi_change_6h = oi_now - oi_6h_ago
oi_momentum = oi_change_6h / oi_6h_ago  # 百分比变化

# 4. 资金动量（CVD + OI加权）
fund_momentum = cvd_weight * cvd_momentum + oi_weight * oi_momentum
# 默认：cvd_weight=0.6, oi_weight=0.4

# 5. F因子 = 资金动量 - 价格动量
F = (fund_momentum - price_momentum) * scale
# scale=2.0，归一化到±100

# F > 0: 资金领先价格（蓄势待发）✅
# F < 0: 价格领先资金（追高风险）⚠️
```

**F因子意义**:
- **F ≥ +60**: 资金强势领先价格（蓄势待发）✅✅✅
- **F ≥ +30**: 资金温和领先价格（机会较好）✅
- **-30 < F < +30**: 资金价格同步（一般）
- **F ≤ -30**: 价格温和领先资金（追高风险）⚠️
- **F ≤ -60**: 价格强势领先资金（风险很大）❌

**F因子应用**:
- 作为B层调制器，不参与方向评分
- 用于v7.2动量分级（F≥35/60触发阈值降低）
- Gate2（资金支持闸门）检查

---

### 4.4 应用3: O因子辅助（持仓量）

**位置**: `ats_core/pipeline/analyze_symbol.py:526-528`

```python
# 计算6小时CVD变化率（归一化到价格）
cvd6 = (cvd_series[-1] - cvd_series[-7]) / abs(close_now) if len(cvd_series) >= 7 else 0.0

# 传递给O因子计算，辅助判断OI变化的资金流向
O, O_meta = _calc_oi(symbol, c, params, cvd6, oi_data=oi_data)
```

**cvd6的作用**:
- 辅助判断OI增加是多头还是空头
- 如果OI↑且cvd6>0 → 多头建仓
- 如果OI↑且cvd6<0 → 空头建仓

---

### 4.5 应用4: 多时间框架C维度

**位置**: `ats_core/features/multi_timeframe.py:50-72`

**用途**: 计算多个时间框架（15m/1h/4h/1d）的CVD一致性

**已修复**: v7.2.32修复了错误的阳线阴线计算，改用真实`takerBuyVolume`

```python
# multi_timeframe.py:55-69（v7.2.32修复后）
if len(klines) > 0 and len(klines[0]) >= 10:
    taker_buy_volumes = [float(k[9]) for k in klines]
    total_volumes = [float(k[5]) for k in klines]
    cvd = 0
    for i in range(len(taker_buy_volumes)):
        delta = 2.0 * taker_buy_volumes[i] - total_volumes[i]
        cvd += delta
    cvd_change = cvd / sum(total_volumes)
    return min(100, max(-100, cvd_change * 500))
```

---

## 5. CVD数据流完整示意图

```
┌─────────────────────────────────────────────────────────────┐
│                     系统启动入口                              │
│                    ./setup.sh:184                            │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│           scripts/realtime_signal_scanner.py                 │
│           （实时信号扫描器）                                  │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│    ats_core/pipeline/batch_scan_optimized.py:1168           │
│    OptimizedBatchScanner → analyze_symbol()                 │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│             数据获取层（Binance API）                         │
│                                                              │
│  ats_core/sources/binance.py:121                            │
│    ┌─────────────────────────────────────┐                 │
│    │ GET /fapi/v1/klines (期货)           │                 │
│    │ GET /api/v3/klines (现货)            │                 │
│    │                                      │                 │
│    │ 返回12列K线数据：                     │                 │
│    │ [0]  openTime                        │                 │
│    │ [1]  open                            │                 │
│    │ ...                                  │                 │
│    │ [9]  takerBuyBaseVolume ✅ CVD关键   │                 │
│    │ ...                                  │                 │
│    └─────────────────────────────────────┘                 │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│             CVD计算层（ats_core/features/cvd.py）            │
│                                                              │
│  cvd_from_klines(klines, use_taker_buy=True):               │
│    ├─ 提取: taker_buy = klines[:,9]                         │
│    ├─ 提取: total_vol = klines[:,5]                         │
│    ├─ 计算: delta[i] = 2*taker_buy[i] - total_vol[i]       │
│    ├─ 异常值处理（IQR方法）                                  │
│    └─ 累积: CVD[i] = Σ delta[0..i]                         │
│                                                              │
│  cvd_combined(futures_klines, spot_klines):                 │
│    ├─ 计算期货CVD                                           │
│    ├─ 计算现货CVD                                           │
│    ├─ 动态权重（按成交额比例）                               │
│    └─ 加权组合                                              │
│                                                              │
│  cvd_mix_with_oi_price(klines, oi_hist, spot_klines):       │
│    ├─ CVD = cvd_combined() or cvd_from_klines()            │
│    ├─ Z-score标准化（CVD, 价格, OI）                        │
│    └─ mix = 1.2*z_cvd + 0.4*z_p + 0.4*z_oi                 │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                   CVD应用层                                  │
│                                                              │
│  ┌──────────────────────────────────────────┐              │
│  │ 应用1: C因子（CVD Flow）                  │              │
│  │ analyze_symbol.py:509                     │              │
│  │ → score_cvd_flow(cvd_series)             │              │
│  │ → C得分（-100到+100）                     │              │
│  │ → 权重25%参与方向评分                     │              │
│  └──────────────────────────────────────────┘              │
│                                                              │
│  ┌──────────────────────────────────────────┐              │
│  │ 应用2: F因子（资金领先性）                 │              │
│  │ fund_leading.py:229                       │              │
│  │ → score_fund_leading_v2(cvd_series)      │              │
│  │ → F = 资金动量 - 价格动量                 │              │
│  │ → 用于v7.2动量分级和Gate2检查             │              │
│  └──────────────────────────────────────────┘              │
│                                                              │
│  ┌──────────────────────────────────────────┐              │
│  │ 应用3: O因子辅助（持仓量）                 │              │
│  │ analyze_symbol.py:526                     │              │
│  │ → cvd6 = CVD 6h变化率                    │              │
│  │ → 辅助判断OI增加的多空方向                │              │
│  └──────────────────────────────────────────┘              │
│                                                              │
│  ┌──────────────────────────────────────────┐              │
│  │ 应用4: 多时间框架C维度                     │              │
│  │ multi_timeframe.py:50                     │              │
│  │ → 15m/1h/4h/1d CVD一致性                 │              │
│  │ → v7.2.32已修复（真实takerBuyVolume）    │              │
│  └──────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. 关键问题回答

### 6.1 CVD计算在哪里？

**回答**: `ats_core/features/cvd.py`

**核心函数**:
- `cvd_from_klines()` - 单一市场CVD
- `cvd_combined()` - 现货+期货组合CVD
- `cvd_mix_with_oi_price()` - CVD+OI+价格综合

**调用位置**:
- `ats_core/pipeline/analyze_symbol.py:490` （主流程）
- `ats_core/features/fund_leading.py:229` （F因子）
- `ats_core/features/multi_timeframe.py:50` （多时间框架）

---

### 6.2 数据获取是否符合要求？

**回答**: ✅ **完全符合要求**

**数据来源**:
- Binance Futures API: `/fapi/v1/klines`
- Binance Spot API: `/api/v3/klines`
- **第9列**: `takerBuyBaseVolume` - 真实主动买入量

**数据质量**:
- ✅ 基于逐笔成交的`isBuyerMaker`字段
- ✅ **不是估算**，是真实数据
- ✅ 每笔成交都有明确的买卖方向标记

**验证**:
```python
# cvd.py:71 - 数据格式检查
if use_taker_buy and klines and len(klines[0]) >= 10:
    taker_buy = _col(klines, 9)  # ✅ 使用真实主动买入量
else:
    # ⚠️ 降级方案（仅用于兼容，会触发DeprecationWarning）
```

---

### 6.3 CVD获取方式、计算公式、应用方式（详细）

#### 6.3.1 获取方式

**完整流程**:
```
1. setup.sh 启动 realtime_signal_scanner.py
   ↓
2. batch_scan_optimized.py 扫描所有币种
   ↓
3. analyze_symbol.py 对每个币种调用:
   - get_klines(symbol, "1h", 300)       # 期货K线
   - get_spot_klines(symbol, "1h", 300)  # 现货K线
   ↓
4. binance.py 调用Binance API:
   - GET /fapi/v1/klines (期货)
   - GET /api/v3/klines (现货)
   ↓
5. 返回12列K线数据，包含takerBuyVolume（第9列）
   ↓
6. cvd.py 使用takerBuyVolume计算CVD
```

#### 6.3.2 计算公式（数学定义）

**基础公式**:
```
输入：
  K线数据 klines[i] = [openTime, ..., takerBuyVolume, ...]

提取：
  buy[i] = klines[i][9]  # 主动买入量
  vol[i] = klines[i][5]  # 总成交量

计算单根K线的CVD增量：
  delta[i] = buy[i] - sell[i]
           = buy[i] - (vol[i] - buy[i])
           = 2 * buy[i] - vol[i]

累积CVD：
  CVD[0] = delta[0]
  CVD[i] = CVD[i-1] + delta[i]

数学表达式：
  CVD[i] = Σ(j=0 to i) (2 * buy[j] - vol[j])
```

**异常值处理**:
```
IQR方法：
  Q1 = 第25百分位数(vol)
  Q3 = 第75百分位数(vol)
  IQR = Q3 - Q1

  if vol[i] > Q3 + 1.5*IQR:
      delta[i] = delta[i] * 0.5  # 降权50%
```

**现货+期货组合**:
```
动态权重：
  w_f = 期货成交额 / (期货成交额 + 现货成交额)
  w_s = 现货成交额 / (期货成交额 + 现货成交额)

组合CVD：
  CVD_combined[i] = Σ(j=0 to i) (w_f * Δ_f[j] + w_s * Δ_s[j])

  其中：
    Δ_f[j] = 期货CVD第j期增量
    Δ_s[j] = 现货CVD第j期增量
```

**综合信号（CVD+OI+价格）**:
```
Z-score标准化：
  z_C[i] = (C[i] - μ_C) / σ_C
  z_p[i] = (r_p[i] - μ_p) / σ_p
  z_o[i] = (r_o[i] - μ_o) / σ_o

加权组合：
  mix[i] = 1.2 * z_C[i] + 0.4 * z_p[i] + 0.4 * z_o[i]

  权重比例：
    CVD: 60%
    价格: 20%
    OI: 20%
```

#### 6.3.3 应用方式（详细）

**应用1: C因子（CVD Flow）**
- **位置**: analyze_symbol.py:509
- **计算**: `score_cvd_flow(cvd_series, closes, params, klines)`
- **输出**: C得分（-100到+100）
- **意义**:
  - C > 0：资金流入
  - C < 0：资金流出
- **权重**: 25%参与6因子方向评分

**应用2: F因子（资金领先性）**
- **位置**: fund_leading.py:229
- **计算**:
  ```
  资金动量 = 0.6*CVD动量 + 0.4*OI动量
  价格动量 = 价格6h变化 / ATR
  F = (资金动量 - 价格动量) * 2.0
  ```
- **输出**: F得分（-100到+100）
- **意义**:
  - F > +60：资金强势领先（蓄势待发）
  - F > +30：资金温和领先
  - F < -30：价格领先资金（追高风险）
- **应用**: v7.2动量分级、Gate2检查

**应用3: O因子辅助**
- **位置**: analyze_symbol.py:526
- **计算**: `cvd6 = (CVD[-1] - CVD[-7]) / close`
- **用途**: 辅助判断OI增加的多空方向

**应用4: 多时间框架C维度**
- **位置**: multi_timeframe.py:50
- **计算**: 多个时间框架的CVD一致性
- **状态**: v7.2.32已修复（使用真实takerBuyVolume）

---

## 7. 技术亮点

### 7.1 数据质量

✅ **真实成交方向**
- 使用Binance API提供的`takerBuyVolume`
- 基于逐笔成交的`isBuyerMaker`字段
- 不是基于K线颜色的估算

✅ **异常值处理**
- IQR方法检测巨量K线
- 对异常值降权，避免被单笔大额交易误导

✅ **多市场组合**
- 现货+期货动态权重
- 按成交额比例自动调整

### 7.2 计算优化

✅ **高效实现**
- 单次遍历计算CVD
- 向量化操作（NumPy）
- 缓存重复计算

✅ **数值稳定性**
- 处理NaN和Inf
- 除零保护
- ATR归一化

### 7.3 应用灵活性

✅ **多维度应用**
- C因子：资金流向（方向维度）
- F因子：资金领先性（调制器）
- O因子：辅助持仓判断
- 多时间框架：一致性分析

✅ **配置驱动**
- 权重可配置
- 窗口大小可调
- 参数灵活

---

## 8. 总结

### 8.1 追踪结果

从`setup.sh`出发，完整追踪了CVD在系统中的：
1. ✅ **计算位置** - `ats_core/features/cvd.py`
2. ✅ **数据获取** - Binance API的真实`takerBuyVolume`
3. ✅ **计算公式** - 详细的数学定义和代码实现
4. ✅ **应用方式** - C因子、F因子、O因子、多时间框架

### 8.2 数据质量确认

✅ **完全符合要求**:
- 使用真实的逐笔成交方向（`takerBuyVolume`）
- **不是**基于K线阳线阴线的估算
- Binance官方API原生支持

### 8.3 技术优势

✅ **真实数据驱动** - 基于真实成交方向
✅ **多市场组合** - 现货+期货动态权重
✅ **异常值处理** - IQR方法降权巨量K线
✅ **多维度应用** - C/F/O因子，多时间框架
✅ **配置灵活** - 参数、权重可调

---

**文档版本**: v1.0
**最后更新**: 2025-11-12
**追踪方法**: 从setup.sh出发，完整代码审查
**验证方式**: 逐行代码追踪，非拍脑袋回答
