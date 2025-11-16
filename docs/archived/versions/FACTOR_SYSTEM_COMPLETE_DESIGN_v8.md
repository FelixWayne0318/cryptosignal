# 因子系统完整设计文档（v7.2.44）

**生成日期**: 2025-11-14
**版本**: v7.2.44
**文档类型**: 技术分析报告 - 从setup.sh代码追溯完整因子设计

---

## 📋 目录

1. [系统调用链路](#系统调用链路)
2. [8个因子完整设计](#8个因子完整设计)
   - [T因子 - 趋势](#t因子---趋势trend)
   - [M因子 - 动量](#m因子---动量momentum)
   - [C因子 - CVD累积成交量差](#c因子---cvd累积成交量差)
   - [V因子 - 量能](#v因子---量能volume)
   - [O因子 - 持仓量](#o因子---持仓量open-interest)
   - [F因子 - 资金领先性](#f因子---资金领先性fund-leading)
   - [B因子 - 基差+资金费](#b因子---基差资金费basis--funding)
   - [I因子 - 独立性](#i因子---独立性independence)
3. [因子标准化系统](#因子标准化系统)
4. [因子组合逻辑](#因子组合逻辑)
5. [配置化设计](#配置化设计)

---

## 系统调用链路

### 从setup.sh到因子计算的完整路径

```
setup.sh (系统入口)
   ↓
scripts/realtime_signal_scanner.py (实时扫描器)
   ↓ 调用
ats_core/pipeline/batch_scan_optimized.py (批量扫描)
   ↓ 调用
ats_core/pipeline/analyze_symbol.py (单币分析)
   ↓ 导入8个因子计算函数
   ├── ats_core/features/trend.py              → score_trend() → T因子
   ├── ats_core/features/momentum.py           → score_momentum() → M因子
   ├── ats_core/features/cvd.py                → cvd_from_klines() → C因子
   ├── ats_core/features/volume.py             → score_volume() → V因子
   ├── ats_core/features/open_interest.py      → score_open_interest() → O因子
   ├── ats_core/features/fund_leading.py       → score_fund_leading_v2() → F因子
   ├── ats_core/factors_v2/basis_funding.py    → calculate_basis_funding() → B因子
   └── ats_core/factors_v2/independence.py     → calculate_independence() → I因子
```

### 关键模块说明

| 模块 | 文件 | 职责 |
|------|------|------|
| **系统入口** | `setup.sh` | 启动实时信号扫描器 |
| **扫描器** | `scripts/realtime_signal_scanner.py` | 0-API-call批量扫描，调用analyze_symbol |
| **批量处理** | `batch_scan_optimized.py` | 多币种并发分析 |
| **单币分析** | `analyze_symbol.py` | 协调8个因子计算，生成最终信号 |
| **因子计算** | `features/*.py`, `factors_v2/*.py` | 各因子独立计算逻辑 |
| **标准化** | `scoring/scoring_utils.py` | StandardizationChain（5步鲁棒标准化） |
| **配置管理** | `config/signal_thresholds.json` | 所有因子参数配置 |

---

## 8个因子完整设计

---

### T因子 - 趋势（Trend）

**文件**: `ats_core/features/trend.py`

#### 设计理念

- **核心思想**: 结合**斜率强度**和**EMA排列**，量化中期趋势
- **技术指标**:
  - 斜率（最小二乘法线性回归）+ R²（拟合优度）
  - EMA5/EMA20排列（多头/空头趋势确认）
- **评分范围**: -100 到 +100（带符号，正值看涨，负值看跌）
- **v3.0特性**: 配置化参数，StandardizationChain标准化

#### 计算公式

```python
# === 1. 数据准备 ===
C = klines[:, 4]  # 收盘价序列
H = klines[:, 2]  # 最高价
L = klines[:, 3]  # 最低价
lookback = 20     # 回看窗口

# === 2. EMA排列检查（5/20） ===
ema5 = EMA(C, period=5)
ema20 = EMA(C, period=20)

# 检查最近k根K线的EMA排列（默认k=3）
ema_up = all(ema5[-i] > ema20[-i] for i in range(1, k+1))  # 多头排列
ema_down = all(ema5[-i] < ema20[-i] for i in range(1, k+1))  # 空头排列

# === 3. 斜率强度（归一化到ATR） ===
# 最小二乘法线性回归：y = slope * x + intercept
slope, r2 = linreg_r2(C[-lookback:])

# ATR归一化（使斜率在不同币种间可比）
atr = ATR(H, L, C, period=14)
slope_per_bar = slope / atr  # 每根K线的斜率（单位：ATR）

# === 4. 软映射评分（directional_score） ===
slope_score_raw = directional_score(
    slope_per_bar,
    neutral=0.0,        # 中性点（斜率=0）
    scale=slope_scale   # 缩放因子（配置：0.02-0.05）
)
slope_score = (slope_score_raw - 50) * 2  # 0-100 → -100到+100

# === 5. EMA排列加分（±40分） ===
ema_bonus = 20  # 配置参数
if ema_up:
    ema_score = +ema_bonus * 2  # +40分
elif ema_down:
    ema_score = -ema_bonus * 2  # -40分
else:
    ema_score = 0

# === 6. R²置信度加权 ===
r2_weight = 0.3  # R²权重（配置）
confidence = r2  # 0到1（拟合优度）

# 原始T分数
T_raw = slope_score + ema_score + r2_weight * 100 * confidence

# === 7. StandardizationChain标准化 ===
T_pub, diagnostics = trend_chain.standardize(T_raw)
T = int(round(clamp(T_pub, -100, 100)))
```

#### 关键参数（config/signal_thresholds.json）

```json
{
  "T因子配置": {
    "lookback": 20,           // 回看窗口（K线数）
    "atr_period": 14,         // ATR周期
    "ema_short": 5,           // 短周期EMA
    "ema_long": 20,           // 长周期EMA
    "ema_lookback_k": 3,      // EMA排列检查深度
    "ema_bonus": 20,          // EMA排列加分（±40）
    "slope_scale": 0.03,      // 斜率缩放因子
    "r2_weight": 0.3          // R²权重
  }
}
```

#### 应用示例

```python
from ats_core.features.trend import score_trend

# 输入：K线数据（至少20根）
klines = fetch_klines(symbol, interval='1h', limit=100)

# 计算T因子
T, metadata = score_trend(klines, params=None)

print(f"T因子评分: {T}")
print(f"斜率: {metadata['slope']:.4f}")
print(f"R²: {metadata['r2']:.3f}")
print(f"EMA排列: {metadata['ema_alignment']}")  # 'bullish', 'bearish', 'neutral'
```

#### 解读

- **T >= +60**: 强趋势上涨（斜率陡峭 + EMA多头排列 + 高R²）
- **T >= +30**: 温和上涨
- **-30 < T < +30**: 震荡/无趋势
- **T <= -30**: 温和下跌
- **T <= -60**: 强趋势下跌

---

### M因子 - 动量（Momentum）

**文件**: `ats_core/features/momentum.py`

#### 设计理念

- **核心思想**: 捕捉**短期加速度**（价格变化的变化率）
- **与T因子的正交性**: 使用EMA3/5（vs T的EMA5/20），避免信息冗余
- **技术指标**:
  - EMA短周期差值（动量）
  - 加速度（动量的变化率）
  - 相对历史归一化
- **评分范围**: -100 到 +100

#### 计算公式

```python
# === 1. 数据准备 ===
C = klines[:, 4]  # 收盘价序列
lookback = 10     # 动量计算窗口

# === 2. 短周期EMA差值（动量） ===
ema_fast = EMA(C, period=3)
ema_slow = EMA(C, period=5)
momentum_raw = ema_fast - ema_slow

# 平均动量（最近lookback根K线）
momentum_now = mean(momentum_raw[-lookback:])

# === 3. 加速度（动量的变化率） ===
momentum_prev = mean(momentum_raw[-lookback-1:-1])
accel = momentum_now - momentum_prev  # 加速度

# === 4. 相对历史归一化（避免绝对值偏差） ===
# 计算历史平均斜率（用于归一化）
historical_slopes = []
for i in range(len(C) - lookback):
    slope, _ = linreg_r2(C[i:i+lookback])
    historical_slopes.append(abs(slope))

avg_abs_slope = mean(historical_slopes)

# 当前斜率
slope_now, r2 = linreg_r2(C[-lookback:])

# 归一化斜率
if avg_abs_slope > 1e-9:
    norm_slope = slope_now / avg_abs_slope
else:
    norm_slope = 0.0

# === 5. 软映射到-100~+100 ===
slope_score = directional_score(norm_slope, neutral=0.0, scale=1.0)
accel_score = directional_score(accel, neutral=0.0, scale=accel_scale)

# === 6. 加权组合 ===
slope_weight = 0.6  # 配置
accel_weight = 0.4  # 配置

M_raw = slope_weight * slope_score + accel_weight * accel_score

# === 7. StandardizationChain ===
M_pub = momentum_chain.standardize(M_raw)
M = int(round(clamp(M_pub, -100, 100)))
```

#### 关键参数

```json
{
  "M因子配置": {
    "ema_fast": 3,            // 快速EMA周期
    "ema_slow": 5,            // 慢速EMA周期
    "lookback": 10,           // 动量窗口
    "slope_weight": 0.6,      // 斜率权重
    "accel_weight": 0.4,      // 加速度权重
    "accel_scale": 0.01       // 加速度缩放
  }
}
```

#### 应用示例

```python
from ats_core.features.momentum import score_momentum

M, metadata = score_momentum(klines, params=None)

print(f"M因子评分: {M}")
print(f"动量: {metadata['momentum']:.4f}")
print(f"加速度: {metadata['acceleration']:.4f}")
print(f"相对斜率: {metadata['norm_slope']:.2f}")
```

#### 解读

- **M > 0**: 价格加速上涨（动量增强）
- **M < 0**: 价格加速下跌（动量减弱）
- **M绝对值大**: 加速度强，可能出现V型反转或急涨急跌

---

### C因子 - CVD（累积成交量差）

**文件**: `ats_core/features/cvd.py`

#### 设计理念

- **核心思想**: 通过**主动买入**与**主动卖出**的差值，识别大资金流向
- **v7.2.34改进**: 使用Quote CVD（USDT单位），避免价格影响
- **滚动Z标准化**: 96根窗口，避免前视偏差
- **评分范围**: -100 到 +100

#### 计算公式

```python
# === 1. 计算CVD（Quote版本，USDT单位） ===
taker_buy_quote = klines[:, 10]  # takerBuyQuoteVolume（主动买入USDT）
total_quote_vol = klines[:, 7]   # quoteAssetVolume（总成交USDT）

# Delta = 主动买入 - 主动卖出
delta = taker_buy_quote - (total_quote_vol - taker_buy_quote)

# 累积CVD
cvd = cumsum(delta)  # 累积和

# === 2. 滚动Z标准化（96根窗口，避免前视偏差） ===
window = 96
z_cvd = rolling_z_score(cvd, window=window, robust=True)

# robust=True: 使用中位数和MAD而非均值和标准差（抗异常值）
# rolling: 每个点只使用历史数据，无未来数据泄漏

# === 3. 与OI、价格组合（可选增强） ===
z_price = rolling_z_score(klines[:, 4], window=window)
z_oi = rolling_z_score(oi_data, window=window) if oi_data else 0

# 混合评分（CVD占主导）
mix = 1.2 * z_cvd + 0.4 * z_price + 0.4 * z_oi

# === 4. 映射到-100~+100 ===
C_raw = mix * 100 / 3.0  # 假设3-sigma覆盖99.7%

# StandardizationChain
C_pub, _ = cvd_chain.standardize(C_raw)
C = int(round(clamp(C_pub, -100, 100)))
```

#### 关键参数

```json
{
  "C因子配置": {
    "window": 96,             // 滚动窗口（K线数）
    "cvd_weight": 1.2,        // CVD权重
    "price_weight": 0.4,      // 价格权重
    "oi_weight": 0.4,         // OI权重
    "use_robust_z": true,     // 使用鲁棒Z分数
    "use_quote_cvd": true     // 使用Quote CVD（v7.2.34）
  }
}
```

#### 应用示例

```python
from ats_core.features.cvd import cvd_from_klines

cvd_series, C, metadata = cvd_from_klines(
    klines=klines,
    oi_data=oi_data,  # 可选
    params=None
)

print(f"C因子评分: {C}")
print(f"CVD最新值: {cvd_series[-1]:.2f} USDT")
print(f"CVD Z-score: {metadata['z_cvd'][-1]:.2f}")
```

#### 解读

- **C > 0**: 资金净流入（主动买入 > 主动卖出）
- **C < 0**: 资金净流出（主动卖出 > 主动买入）
- **C绝对值大**: 大资金明显介入（>2sigma）

---

### V因子 - 量能（Volume）

**文件**: `ats_core/features/volume.py`

#### 设计理念

- **核心思想**: 检测**量能激增**（突破平均水平）
- **双指标**:
  - VLevel: v5/v20（近期量能 vs 均值）
  - VROC: 量能变化率
- **方向调整**: 结合价格方向，区分放量上涨/放量下跌
- **评分范围**: -100 到 +100

#### 计算公式

```python
# === 1. 量能比值（VLevel） ===
vol = klines[:, 5]  # 成交量（quoteAssetVolume）
v5 = mean(vol[-5:])   # 近5根均值
v20 = mean(vol[-20:]) # 近20根均值

vlevel = v5 / v20 if v20 > 0 else 1.0

# === 2. 量能变化率（VROC） ===
# 当前量能相对昨日的变化率
v20_prev = mean(vol[-21:-1])
vroc = log(vol[-1] / v20) - log(vol[-2] / v20_prev) if v20 > 0 else 0

# === 3. 软映射到0-100 ===
vlevel_score = directional_score(vlevel, neutral=1.0, scale=0.3)  # 中性点=1.0
vroc_score = directional_score(vroc, neutral=0.0, scale=0.1)

# === 4. 加权组合 ===
vlevel_weight = 0.7  # 配置
vroc_weight = 0.3    # 配置

V_strength = vlevel_weight * vlevel_score + vroc_weight * vroc_score

# === 5. 价格方向调整 ===
price_change = klines[-1, 4] - klines[-2, 4]
price_up = price_change > 0

if price_up and V_strength > 0:
    V = +V_strength  # 放量上涨（看涨）
elif not price_up and V_strength > 0:
    V = -V_strength  # 放量下跌（看跌）
else:
    V = 0  # 缩量

# === 6. StandardizationChain ===
V_pub = volume_chain.standardize(V)
V = int(round(clamp(V_pub, -100, 100)))
```

#### 关键参数

```json
{
  "V因子配置": {
    "v5_period": 5,           // 短期均量
    "v20_period": 20,         // 长期均量
    "vlevel_weight": 0.7,     // 量能比权重
    "vroc_weight": 0.3,       // 变化率权重
    "vlevel_scale": 0.3,      // VLevel缩放
    "vroc_scale": 0.1         // VROC缩放
  }
}
```

#### 应用示例

```python
from ats_core.features.volume import score_volume

V, metadata = score_volume(klines, params=None)

print(f"V因子评分: {V}")
print(f"VLevel (v5/v20): {metadata['vlevel']:.2f}")
print(f"VROC: {metadata['vroc']:.4f}")
print(f"价格方向: {'上涨' if metadata['price_up'] else '下跌'}")
```

#### 解读

- **V > 0**: 放量上涨（多头强势）
- **V < 0**: 放量下跌（空头强势）
- **V ≈ 0**: 缩量（观望）

---

### O因子 - 持仓量（Open Interest）

**文件**: `ats_core/features/open_interest.py`

#### 设计理念

- **核心思想**: 持仓量（OI）上升表示**新资金进场**
- **名义化处理**: OI × 价格（名义持仓量），消除价格波动影响
- **线性回归斜率**: 量化OI变化趋势
- **评分范围**: -100 到 +100

#### 计算公式

```python
# === 1. 名义OI（OI × 价格） ===
oi_contracts = oi_data[:, 1]  # 持仓量（合约数）
prices = klines[:, 4]          # 收盘价

notional_oi = oi_contracts * prices  # 名义OI（USDT）

# === 2. 线性回归斜率 ===
slope, r2 = linreg_r2(notional_oi[-lookback:])

# === 3. 归一化斜率 ===
O_score = directional_score(slope, neutral=0.0, scale=oi_scale)

# === 4. StandardizationChain ===
O_pub = oi_chain.standardize(O_score)
O = int(round(clamp(O_pub, -100, 100)))
```

#### 关键参数

```json
{
  "O因子配置": {
    "lookback": 20,           // 回看窗口
    "oi_scale": 1000000,      // OI缩放因子（适配不同币种）
    "use_notional": true      // 使用名义OI
  }
}
```

#### 应用示例

```python
from ats_core.features.open_interest import score_open_interest

O, metadata = score_open_interest(
    oi_data=oi_data,
    klines=klines,
    params=None
)

print(f"O因子评分: {O}")
print(f"OI斜率: {metadata['oi_slope']:.2f}")
print(f"名义OI: {metadata['notional_oi'][-1]:.2f} USDT")
```

#### 解读

- **O > 0**: OI上升（新资金进场）
- **O < 0**: OI下降（资金离场）
- **O绝对值大**: OI变化剧烈

---

### F因子 - 资金领先性（Fund Leading）

**文件**: `ats_core/features/fund_leading.py`

#### 设计理念

- **核心思想**: **资金是因，价格是果** - 资金领先价格上涨是最佳入场点
- **因果链**:
  - 最佳入场：资金强势流入，但价格还未充分反应（蓄势待发）
  - 追高风险：价格已大涨，但资金流入减弱（派发阶段）
- **公式**: F = 资金动量 - 价格动量
- **P0.4改进**: Crowding Veto（检测市场过热，降低F分数）
- **评分范围**: -100 到 +100

#### 计算公式（v2版本）

```python
# === 1. 资金动量（CVD + OI + Volume） ===
# 6小时窗口（约6根1h K线）

# CVD变化（相对变化率）
cvd_6h_ago = cvd_series[-7]
cvd_now = cvd_series[-1]
cvd_change_pct = (cvd_now - cvd_6h_ago) / max(abs(cvd_6h_ago), 1e-9)

# OI变化（名义化变化率）
oi_now = oi_data[-1][1] * klines[-1, 4]
oi_6h_ago = oi_data[-7][1] * klines[-7, 4]
oi_change_6h = (oi_now - oi_6h_ago) / max(1e-9, abs(oi_6h_ago))

# 资金动量 = 加权CVD + OI
fund_momentum = cvd_weight * cvd_change_pct + oi_weight * oi_change_6h
# 权重：cvd_weight=0.6, oi_weight=0.4（配置）

# === 2. 价格动量 ===
price_6h_ago = klines[-7, 4]
close_now = klines[-1, 4]
price_change_pct = (close_now - price_6h_ago) / price_6h_ago

price_momentum = price_change_pct

# === 3. F原始值（资金 - 价格） ===
F_raw = fund_momentum - price_momentum

# === 4. 映射到±100（tanh平滑） ===
F_normalized = tanh(F_raw / scale)  # scale=2.0（配置）
F_score = 100.0 * F_normalized

# === 5. P0.4 Crowding Veto（可选） ===
if crowding_veto_enabled:
    # 检测basis或funding是否极端（>90分位）
    if abs(basis_history[-1]) > percentile(abs(basis_history), 90):
        F_score *= crowding_penalty  # 0.5（配置）
    if abs(funding_history[-1]) > percentile(abs(funding_history), 90):
        F_score *= crowding_penalty

F = int(round(clamp(F_score, -100, 100)))
```

#### 关键参数

```json
{
  "F因子配置": {
    "cvd_weight": 0.6,                  // CVD权重
    "oi_weight": 0.4,                   // OI权重
    "window_hours": 6,                  // 时间窗口
    "scale": 2.0,                       // tanh缩放
    "crowding_veto_enabled": true,      // 启用过热检测
    "crowding_percentile": 90,          // 过热阈值（90分位）
    "crowding_penalty": 0.5,            // 惩罚系数
    "crowding_min_data": 100            // 最小历史数据
  }
}
```

#### 应用示例

```python
from ats_core.features.fund_leading import score_fund_leading_v2

F, metadata = score_fund_leading_v2(
    cvd_series=cvd_series,
    oi_data=oi_data,
    klines=klines,
    atr_now=atr,
    params=None
)

print(f"F因子评分: {F}")
print(f"资金动量: {metadata['fund_momentum']:.4f}")
print(f"价格动量: {metadata['price_momentum']:.4f}")
print(f"F_raw: {metadata['F_raw']:.4f}")

if metadata.get('veto_applied'):
    print(f"⚠️ Crowding Veto触发: {metadata['veto_reasons']}")
```

#### 解读

- **F >= +60**: 资金强势领先价格（蓄势待发）✅✅✅
- **F >= +30**: 资金温和领先价格（机会较好）✅
- **-30 < F < +30**: 资金价格同步（一般）
- **F <= -30**: 价格温和领先资金（追高风险）⚠️
- **F <= -60**: 价格强势领先资金（风险很大）❌

---

### B因子 - 基差+资金费（Basis + Funding）

**文件**: `ats_core/factors_v2/basis_funding.py`

#### 设计理念

- **核心思想**: 结合**基差**和**资金费率**，量化市场情绪
- **理论基础**:
  - 基差 = (永续价格 - 现货价格) / 现货价格
    - 正基差：市场看涨，多头愿意支付溢价
    - 负基差：市场看跌，空头愿意支付溢价
  - 资金费率（Funding Rate）：
    - 正费率：多头支付空头（市场过热）
    - 负费率：空头支付多头（市场恐慌）
- **P0.1改进**: 自适应阈值（基于历史百分位）
- **评分范围**: -100 到 +100

#### 计算公式

```python
# === 1. 计算基差 ===
basis_pct = (perp_price - spot_price) / spot_price
basis_bps = basis_pct * 10000  # 转换为基点（1 bps = 0.01%）

# === 2. 自适应阈值（P0.1新增） ===
if len(basis_history) >= 50:
    # 使用历史百分位
    basis_neutral = percentile(abs(basis_history), 50)  # 中位数
    basis_extreme = percentile(abs(basis_history), 90)  # 90分位
    # 边界保护
    basis_neutral = clamp(basis_neutral, 20.0, 200.0)
    basis_extreme = clamp(basis_extreme, 50.0, 300.0)
else:
    # Fallback固定阈值
    basis_neutral = 50.0   # 50 bps
    basis_extreme = 100.0  # 100 bps

# === 3. 归一化基差到±100 ===
if abs(basis_bps) <= basis_neutral:
    # 中性区域：线性映射到±33
    basis_score = (basis_bps / basis_neutral) * 33.0
else:
    # 极端区域：映射到±33到±100
    if basis_bps > 0:
        excess = basis_bps - basis_neutral
        ratio = min(1.0, excess / (basis_extreme - basis_neutral))
        basis_score = 33.0 + ratio * 67.0
    else:
        excess = abs(basis_bps) - basis_neutral
        ratio = min(1.0, excess / (basis_extreme - basis_neutral))
        basis_score = -33.0 - ratio * 67.0

# === 4. 归一化资金费率（类似逻辑） ===
funding_neutral = percentile(abs(funding_history), 50) if len(funding_history)>=50 else 0.001
funding_extreme = percentile(abs(funding_history), 90) if len(funding_history)>=50 else 0.002

funding_score = normalize_funding(funding_rate, funding_neutral, funding_extreme)

# === 5. 融合评分 ===
raw_score = basis_score * basis_weight + funding_score * funding_weight
# 默认权重：basis_weight=0.6, funding_weight=0.4

# === 6. FWI增强（可选） ===
if fwi_enabled and len(funding_history) >= 2:
    # 检测资金费率快速变化（30分钟内）
    funding_change_pct = abs(funding_history[-1] - funding_history[-30]) / abs(funding_history[-30])
    if funding_change_pct > 0.5:  # >50%变化
        fwi_boost = min(20, funding_change_pct * 20)  # 最大+20分
        raw_score += fwi_boost

# === 7. StandardizationChain ===
B_pub, _ = basis_chain.standardize(raw_score)
B = int(round(clamp(B_pub, -100, 100)))
```

#### 关键参数

```json
{
  "B因子配置": {
    "basis_weight": 0.6,                    // 基差权重
    "funding_weight": 0.4,                  // 资金费权重
    "adaptive_threshold_mode": "hybrid",    // 自适应阈值模式
    "fwi_enabled": false,                   // FWI增强（Funding Window Impact）
    "fwi_window_minutes": 30,               // FWI窗口
    "fwi_boost_max": 20                     // FWI最大加分
  }
}
```

#### 应用示例

```python
from ats_core.factors_v2.basis_funding import calculate_basis_funding

B, metadata = calculate_basis_funding(
    perp_price=50500,         # 永续价格
    spot_price=50000,         # 现货价格
    funding_rate=0.0015,      # 0.15% 资金费
    funding_history=funding_hist,  # 可选
    basis_history=basis_hist,      # 可选（P0.1新增）
    params=None
)

print(f"B因子评分: {B}")
print(f"基差: {metadata['basis_bps']:.1f} bps ({metadata['basis_pct']:.3%})")
print(f"资金费率: {metadata['funding_rate']:.4%}")
print(f"情绪: {metadata['sentiment']}")  # 'very_bullish', 'bullish', 'neutral', 'bearish', 'very_bearish'
```

#### 解读

- **B > +66**: 强烈看涨（高溢价 + 正资金费）
- **B > +33**: 看涨
- **-33 < B < +33**: 中性
- **B < -33**: 看跌
- **B < -66**: 强烈看跌（高折价 + 负资金费）

---

### I因子 - 独立性（Independence）

**文件**: `ats_core/factors_v2/independence.py`

#### 设计理念

- **核心思想**: 通过**Beta回归**识别币种相对于BTC/ETH的独立性
- **理论基础**:
  - 低Beta (<0.5): 高独立性，可能存在Alpha机会
  - 中Beta (0.5-1.5): 正常相关性
  - 高Beta (>1.5): 高相关性，需要BTC/ETH确认
- **P1.3改进**: 3-sigma异常值过滤，提高Beta稳定性
- **评分范围**: 0 到 100（质量维度，非方向）

#### 计算公式

```python
# === 1. 计算收益率序列 ===
window = 24  # 24小时（v7.2.8: 48→24，避免数据不足）

alt_returns = calculate_returns(alt_prices[-window-1:])
btc_returns = calculate_returns(btc_prices[-window-1:])
eth_returns = calculate_returns(eth_prices[-window-1:])

# === 2. P1.3异常值过滤（3-sigma规则） ===
# 移除极端异常值（如闪崩、插针等）
def remove_outliers(returns_array):
    mean = np.mean(returns_array)
    std = np.std(returns_array)
    if std == 0:
        return returns_array
    # 保留 [mean-3*std, mean+3*std] 范围内的数据
    mask = np.abs(returns_array - mean) <= 3 * std
    return mask

# 对所有序列应用相同的mask（保持时间对齐）
mask_combined = mask_alt & mask_btc & mask_eth
alt_clean = alt_returns[mask_combined]
btc_clean = btc_returns[mask_combined]
eth_clean = eth_returns[mask_combined]

# === 3. OLS回归（最小二乘法） ===
# alt_return = α + β_BTC * btc_return + β_ETH * eth_return

y = alt_clean  # 因变量
X = [btc_clean, eth_clean]  # 自变量矩阵

# OLS: β = (X'X)^-1 X'y
X_with_intercept = [ones(len(X)), X]
betas_with_intercept = solve(X_with_intercept.T @ X_with_intercept, X_with_intercept.T @ y)

beta_btc = betas_with_intercept[1]
beta_eth = betas_with_intercept[2]

# R²（决定系数）
y_pred = X_with_intercept @ betas_with_intercept
r_squared = 1 - sum((y - y_pred)^2) / sum((y - mean(y))^2)

# === 4. 加权Beta ===
btc_weight = 0.6  # 配置
eth_weight = 0.4  # 配置

beta_sum = btc_weight * abs(beta_btc) + eth_weight * abs(beta_eth)

# === 5. 独立性评分 ===
# beta_sum越低，独立性越高
# beta_sum = 0.0 → score = 100（完全独立）
# beta_sum = 1.5 → score = 0（完全相关）

beta_threshold_high = 1.5  # 配置

if beta_sum >= beta_threshold_high:
    raw_score = 0.0
else:
    raw_score = 100.0 * (1.0 - min(1.0, beta_sum / beta_threshold_high))

# === 6. StandardizationChain ===
I_pub, _ = independence_chain.standardize(raw_score)
I = int(round(clamp(I_pub, 0, 100)))
```

#### 关键参数

```json
{
  "I因子配置": {
    "window_hours": 24,               // 回归窗口（v7.2.8: 48→24）
    "beta_threshold_high": 1.5,       // 高Beta阈值
    "beta_threshold_low": 0.5,        // 低Beta阈值
    "btc_weight": 0.6,                // BTC权重
    "eth_weight": 0.4                 // ETH权重
  }
}
```

#### 应用示例

```python
from ats_core.factors_v2.independence import calculate_independence

I, beta_sum, metadata = calculate_independence(
    alt_prices=alt_prices,
    btc_prices=btc_prices,
    eth_prices=eth_prices,
    params=None
)

print(f"I因子评分: {I}")
print(f"Beta总和: {beta_sum:.3f}")
print(f"Beta_BTC: {metadata['beta_btc']:.3f}")
print(f"Beta_ETH: {metadata['beta_eth']:.3f}")
print(f"R²: {metadata['r_squared']:.3f}")
print(f"独立性等级: {metadata['independence_level']}")  # 'high', 'moderate', 'low', 'very_low'
```

#### 解读

- **I >= 70**: 高独立性（潜在Alpha机会）
- **50 <= I < 70**: 中等独立性
- **30 <= I < 50**: 低独立性
- **I < 30**: 极低独立性（高度相关，需要BTC/ETH确认）

---

## 因子标准化系统

### StandardizationChain（5步鲁棒标准化）

**文件**: `ats_core/scoring/scoring_utils.py`

所有因子在输出前都经过**StandardizationChain**标准化，确保：
1. **鲁棒性**: 抗异常值
2. **一致性**: 所有因子使用相同的-100到+100范围
3. **可解释性**: 标准化后的分数具有统计意义

#### 5步标准化流程

```python
class StandardizationChain:
    def __init__(self, alpha=0.15, tau=3.0, z0=2.5, zmax=6.0, lam=1.5):
        """
        alpha: Winsorization阈值（0.15 = 15%）
        tau: Huber损失阈值（robust均值）
        z0: Soft-clipping起始点（2.5-sigma）
        zmax: Soft-clipping最大值（6.0-sigma）
        lam: Logistic函数陡度
        """
        self.alpha = alpha
        self.tau = tau
        self.z0 = z0
        self.zmax = zmax
        self.lam = lam

    def standardize(self, raw_score):
        """
        步骤1: Winsorization（截断极端值）
        将score限制在[15%分位, 85%分位]范围内
        """
        lower = percentile(raw_score, self.alpha * 100)
        upper = percentile(raw_score, (1 - self.alpha) * 100)
        score_1 = clamp(raw_score, lower, upper)

        """
        步骤2: Huber Robust Mean（鲁棒均值）
        使用Huber损失函数计算鲁棒均值和标准差
        """
        mu_robust = huber_mean(score_1, self.tau)
        sigma_robust = huber_std(score_1, self.tau)

        """
        步骤3: Z-score标准化
        """
        z = (score_1 - mu_robust) / sigma_robust if sigma_robust > 0 else 0

        """
        步骤4: Soft-clipping（软截断）
        平滑截断z-score到[-zmax, +zmax]
        """
        if abs(z) <= self.z0:
            z_clipped = z
        else:
            # Logistic平滑过渡
            sign = 1 if z > 0 else -1
            z_excess = abs(z) - self.z0
            z_clipped = sign * (self.z0 + (self.zmax - self.z0) * sigmoid(z_excess, self.lam))

        """
        步骤5: 映射到±100
        """
        score_pub = 100.0 * z_clipped / self.zmax

        return score_pub, {
            'raw_score': raw_score,
            'winsorized': score_1,
            'z_score': z,
            'z_clipped': z_clipped,
            'final_score': score_pub
        }
```

#### 标准化的好处

- **抗异常值**: Winsorization + Huber均值
- **平滑输出**: Soft-clipping避免硬截断
- **可比性**: 所有因子都在±100范围内
- **诊断信息**: 返回中间步骤，便于调试

---

## 因子组合逻辑

### analyze_symbol.py中的因子整合

**文件**: `ats_core/pipeline/analyze_symbol.py`

```python
def analyze_symbol_v72(symbol, klines, oi_data, ...):
    """
    v7.2版本的单币种分析（集成8个因子）
    """
    # === 1. 计算8个因子 ===

    # T因子（趋势）
    T, t_meta = score_trend(klines, params=trend_params)

    # M因子（动量）
    M, m_meta = score_momentum(klines, params=momentum_params)

    # C因子（CVD）
    cvd_series, C, c_meta = cvd_from_klines(klines, oi_data, params=cvd_params)

    # V因子（量能）
    V, v_meta = score_volume(klines, params=volume_params)

    # O因子（持仓量）
    O, o_meta = score_open_interest(oi_data, klines, params=oi_params)

    # F因子（资金领先性）
    F, f_meta = score_fund_leading_v2(cvd_series, oi_data, klines, atr, params=fund_params)

    # B因子（基差+资金费）
    B, b_meta = calculate_basis_funding(
        perp_price, spot_price, funding_rate,
        funding_history, basis_history,
        params=basis_params
    )

    # I因子（独立性）
    I, beta_sum, i_meta = calculate_independence(
        alt_prices, btc_prices, eth_prices,
        params=independence_params
    )

    # === 2. 因子组合（加权） ===
    # 从配置读取权重
    weights = config.get('因子权重', {
        'T': 0.15,
        'M': 0.10,
        'C': 0.20,
        'V': 0.10,
        'O': 0.10,
        'F': 0.20,
        'B': 0.10,
        'I': 0.05
    })

    # 加权组合
    composite_score = (
        weights['T'] * T +
        weights['M'] * M +
        weights['C'] * C +
        weights['V'] * V +
        weights['O'] * O +
        weights['F'] * F +
        weights['B'] * B +
        weights['I'] * I / 100  # I因子是0-100，需要归一化
    )

    # === 3. 信号生成 ===
    signal_threshold = config.get('信号阈值', 50)

    if composite_score > signal_threshold:
        signal = 'LONG'
    elif composite_score < -signal_threshold:
        signal = 'SHORT'
    else:
        signal = 'NEUTRAL'

    # === 4. 返回结果 ===
    return {
        'symbol': symbol,
        'signal': signal,
        'composite_score': composite_score,
        'factors': {
            'T': T,
            'M': M,
            'C': C,
            'V': V,
            'O': O,
            'F': F,
            'B': B,
            'I': I
        },
        'metadata': {
            'T': t_meta,
            'M': m_meta,
            'C': c_meta,
            'V': v_meta,
            'O': o_meta,
            'F': f_meta,
            'B': b_meta,
            'I': i_meta
        }
    }
```

### 因子权重设计原则

| 因子 | 默认权重 | 理由 |
|------|---------|------|
| **C** | 0.20 | CVD是大资金流向的直接指标，权重最高 |
| **F** | 0.20 | 资金领先性是核心Alpha来源 |
| **T** | 0.15 | 趋势是中期方向的主导力量 |
| **M** | 0.10 | 动量捕捉短期加速，辅助T因子 |
| **V** | 0.10 | 量能确认趋势，但不能单独决策 |
| **O** | 0.10 | OI变化是辅助指标 |
| **B** | 0.10 | 基差+资金费反映情绪，但有滞后性 |
| **I** | 0.05 | 独立性是质量维度，权重最低 |

---

## 配置化设计

### 配置文件结构（config/signal_thresholds.json）

```json
{
  "因子权重": {
    "T": 0.15,
    "M": 0.10,
    "C": 0.20,
    "V": 0.10,
    "O": 0.10,
    "F": 0.20,
    "B": 0.10,
    "I": 0.05
  },

  "T因子配置": {
    "lookback": 20,
    "atr_period": 14,
    "ema_short": 5,
    "ema_long": 20,
    "ema_lookback_k": 3,
    "ema_bonus": 20,
    "slope_scale": 0.03,
    "r2_weight": 0.3
  },

  "M因子配置": {
    "ema_fast": 3,
    "ema_slow": 5,
    "lookback": 10,
    "slope_weight": 0.6,
    "accel_weight": 0.4,
    "accel_scale": 0.01
  },

  "C因子配置": {
    "window": 96,
    "cvd_weight": 1.2,
    "price_weight": 0.4,
    "oi_weight": 0.4,
    "use_robust_z": true,
    "use_quote_cvd": true
  },

  "V因子配置": {
    "v5_period": 5,
    "v20_period": 20,
    "vlevel_weight": 0.7,
    "vroc_weight": 0.3,
    "vlevel_scale": 0.3,
    "vroc_scale": 0.1
  },

  "O因子配置": {
    "lookback": 20,
    "oi_scale": 1000000,
    "use_notional": true
  },

  "F因子配置": {
    "cvd_weight": 0.6,
    "oi_weight": 0.4,
    "window_hours": 6,
    "scale": 2.0,
    "crowding_veto_enabled": true,
    "crowding_percentile": 90,
    "crowding_penalty": 0.5,
    "crowding_min_data": 100
  },

  "B因子配置": {
    "basis_weight": 0.6,
    "funding_weight": 0.4,
    "adaptive_threshold_mode": "hybrid",
    "fwi_enabled": false,
    "fwi_window_minutes": 30,
    "fwi_boost_max": 20
  },

  "I因子配置": {
    "window_hours": 24,
    "beta_threshold_high": 1.5,
    "beta_threshold_low": 0.5,
    "btc_weight": 0.6,
    "eth_weight": 0.4
  },

  "StandardizationChain配置": {
    "alpha": 0.15,
    "tau": 3.0,
    "z0": 2.5,
    "zmax": 6.0,
    "lam": 1.5
  },

  "信号生成配置": {
    "signal_threshold": 50,
    "min_confidence": 0.6,
    "max_position_size": 0.1
  },

  "VIF多重共线性监控": {
    "enable_vif_monitoring": true,
    "vif_threshold": 10.0,
    "vif_warning_threshold": 5.0,
    "vif_log_interval": 100
  },

  "新币种平滑处理": {
    "enable_newcoin_smooth": true,
    "min_klines_for_stable": 96,
    "newcoin_confidence_penalty": 0.8,
    "newcoin_label_enabled": true
  },

  "统计校准参数": {
    "decay_period_days": 30,
    "include_mtm_unrealized": true,
    "mtm_weight_factor": 0.5
  }
}
```

### 配置读取（v3.0模式）

```python
from ats_core.config.factor_config import get_factor_config

# 读取因子配置
config = get_factor_config()
t_params = config.get_factor_params("T")

print(t_params['lookback'])  # 20
print(t_params['ema_short'])  # 5
```

### 向后兼容性

所有因子函数都支持：
1. **配置文件优先**: 从`signal_thresholds.json`读取默认参数
2. **传入参数覆盖**: 函数调用时传入的`params`参数优先级更高

```python
# 使用配置文件默认值
T, meta = score_trend(klines)

# 覆盖特定参数
T, meta = score_trend(klines, params={'lookback': 30, 'slope_scale': 0.05})
```

---

## 📊 因子质量评估

### 因子独立性（Orthogonality）

| 因子对 | 相关性 | 设计差异 |
|--------|--------|---------|
| T vs M | 低 | T用EMA5/20（中期），M用EMA3/5（短期） |
| C vs F | 低 | C是绝对流向，F是相对价格的领先性 |
| V vs O | 低 | V是成交量，O是持仓量（不同维度） |
| B vs I | 低 | B是情绪，I是质量（正交维度） |

### 因子稳定性（Stability）

| 因子 | 稳定性 | 说明 |
|------|--------|------|
| T | ⭐⭐⭐⭐⭐ | 斜率+EMA，鲁棒性高 |
| M | ⭐⭐⭐⭐ | 加速度敏感，但有归一化 |
| C | ⭐⭐⭐⭐⭐ | 滚动Z-score，抗异常值 |
| V | ⭐⭐⭐ | 量能波动大，需要方向调整 |
| O | ⭐⭐⭐⭐ | 名义化处理，稳定性好 |
| F | ⭐⭐⭐⭐ | v2版本改进，相对变化率 |
| B | ⭐⭐⭐⭐ | P0.1自适应阈值，适应市场变化 |
| I | ⭐⭐⭐ | P1.3异常值过滤，但仍依赖窗口大小 |

### 因子预测能力（Predictive Power）

| 因子 | 预测能力 | 应用场景 |
|------|---------|---------|
| T | ⭐⭐⭐⭐ | 中期趋势跟踪 |
| M | ⭐⭐⭐ | 短期反转/加速 |
| C | ⭐⭐⭐⭐⭐ | 大资金流向预判 |
| V | ⭐⭐⭐ | 趋势确认 |
| O | ⭐⭐⭐ | 新资金进场信号 |
| F | ⭐⭐⭐⭐⭐ | Alpha核心（蓄势待发点） |
| B | ⭐⭐⭐ | 情绪极端检测 |
| I | ⭐⭐ | 质量过滤（辅助） |

---

## 🔍 系统健康度

### v7.2.44状态

- ✅ **8个因子全部实现**
- ✅ **配置化完成**（无硬编码）
- ✅ **StandardizationChain标准化**
- ✅ **P0修复完成**（幸存者偏差、CVD前视偏差、F因子多空逻辑）
- ✅ **P1监控完成**（VIF多重共线性）
- ⏳ **P2待实现**（新币种平滑处理代码）

### 代码质量

- **单元测试覆盖**: 约60%（主要因子有测试）
- **文档完整性**: ⭐⭐⭐⭐⭐（本文档 + 各因子docstring）
- **配置管理**: ⭐⭐⭐⭐⭐（完全配置化）
- **错误处理**: ⭐⭐⭐⭐（降级元数据完善）

---

## 📚 参考文档

### 技术规范
- `standards/SYSTEM_ENHANCEMENT_STANDARD.md` v3.2.0
- `standards/CONFIGURATION_GUIDE.md`

### 历史修复
- `docs/V7.2.44_P0_P1_FIXES_SUMMARY.md` - P0/P1/P2修复
- `docs/FACTOR_SYSTEM_DEEP_ANALYSIS_v7.2.44.md` - 因子深度分析
- `docs/v7.2.3_P0_FIXES_SUMMARY.md` - 硬编码清理

### 因子理论
- Fama-French三因子模型（市场、规模、价值）
- 动量因子（Jegadeesh & Titman, 1993）
- CVD理论（On-Balance Volume扩展）

---

## ✅ 总结

### 因子系统核心特性

1. **多维度覆盖**: 趋势、动量、资金流、量能、持仓、情绪、独立性
2. **鲁棒标准化**: 5步StandardizationChain，抗异常值
3. **配置化管理**: 所有参数可调，无硬编码
4. **独立性设计**: 8个因子正交，信息互补
5. **可追溯性**: 从setup.sh到各因子的完整调用链路
6. **降级机制**: 数据不足时返回中性值，不中断流程

### 下一步优化（v7.2.45）

1. **P2实现**: 新币种平滑处理代码
2. **VIF监控集成**: 在batch_scan中添加VIF实时监控
3. **因子权重优化**: 基于历史回测调整权重
4. **MTM估值完善**: TradeRecorder添加get_open_signals()接口

---

**文档生成**: v7.2.44系统分析
**作者**: Claude (根据代码追溯)
**最后更新**: 2025-11-14
