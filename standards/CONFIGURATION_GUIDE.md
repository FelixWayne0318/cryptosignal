# 配置参数详解

> **config/params.json 完整配置指南**

---

## ⚠️ 配置文件层次结构（v7.2.7更新）

CryptoSignal系统使用多个配置文件，遵循以下优先级顺序：

### 配置优先级（§5.2标准）

```
1. config/signal_thresholds.json  ← 最高优先级（信号阈值配置）
2. config/factors_unified.json    ← 中等优先级（因子配置）
3. config/params.json             ← 基础优先级（系统参数）
```

### 配置文件用途

| 配置文件 | 用途 | 适用场景 |
|---------|------|---------|
| **signal_thresholds.json** | 所有信号阈值配置 | Prime判定、闸门阈值、统计校准、EV计算 |
| **factors_unified.json** | 因子计算参数 | 因子分组权重、计算窗口、缩放系数 |
| **params.json** | 系统全局参数 | 因子权重、新币配置、Overlay过滤 |

### 重要原则（v7.2.7）

1. **单一数据源**: 每个参数只在一个配置文件中定义
2. **避免硬编码**: 所有阈值必须从配置文件读取，代码中禁止硬编码
3. **默认值一致**: 代码中的fallback默认值必须与配置文件保持一致
4. **配置统一**: 优先使用signal_thresholds.json，避免混用多个配置源

### 配置读取示例

```python
# ✅ 正确：使用ThresholdConfig统一读取
from ats_core.config.threshold_config import get_thresholds

config = get_thresholds()
prime_prob_min = config.get_mature_threshold('prime_prob_min', 0.45)

# ❌ 错误：硬编码
prime_prob_min = 0.68  # 禁止！

# ❌ 错误：混用多个配置源
prime_prob_min = params.get("publish", {}).get("prime_prob_min", 0.68)
```

**详细案例**: 参考 `standards/SYSTEM_ENHANCEMENT_STANDARD.md` v7.2.3-v7.2.7硬编码清理系列

---

## 📋 配置文件位置

```
config/params.json             # 系统全局参数
config/signal_thresholds.json  # 信号阈值配置（优先）
config/factors_unified.json    # 因子计算参数
```

---

## 🎯 核心配置（必看）

### 1. weights - 因子权重配置

**路径**: `weights`

**说明**: 10+1维因子的权重分配（v6.0权重百分比系统）

**要求**: **总权重必须=100%**

```json
{
  "weights": {
    "T": 13.9,  // 趋势（Trend）
    "M": 8.3,   // 动量（Momentum）
    "C": 11.1,  // 资金流（CVD）
    "S": 5.6,   // 结构（Structure）
    "V": 8.3,   // 量能（Volume）
    "O": 11.1,  // 持仓（Open Interest）
    "L": 11.1,  // 流动性（Liquidity）⭐ v4.0新增
    "B": 8.3,   // 基差+资金费（Basis+Funding）⭐ v4.0新增
    "Q": 5.6,   // 清算密度（Liquidation）⭐ v4.0新增
    "I": 6.7,   // 独立性（Independence）⭐ v4.0新增
    "E": 0,     // 环境（已废弃）
    "F": 10.0   // 资金领先（Fund Leading）⭐ v6.0升级为评分因子
  }
}
```

**各因子权重含义**:

| 因子 | 权重 | 层级 | 含义 |
|------|------|------|------|
| T | 13.9% | Layer 1 | 价格趋势强度（EMA趋势、斜率） |
| M | 8.3% | Layer 1 | 价格动量和加速度 |
| S | 5.6% | Layer 1 | 支撑阻力位结构 |
| V | 8.3% | Layer 1 | 成交量强度和异常 |
| C | 11.1% | Layer 2 | CVD累积成交量差值 |
| O | 11.1% | Layer 2 | OI持仓量变化 |
| F | 10.0% | Layer 2 | 资金vs价格领先性⭐ |
| L | 11.1% | Layer 3 | 订单簿流动性和滑点 |
| B | 8.3% | Layer 3 | 现货-合约基差+资金费率 |
| Q | 5.6% | Layer 3 | 清算密度热图 |
| I | 6.7% | Layer 4 | 与BTC/ETH相关性 |

**调整建议**:
- **趋势市场**: 提高T、M权重（例如T=18%, M=10%）
- **震荡市场**: 提高C、O、S权重（例如C=15%, O=15%, S=8%）
- **高波动市场**: 提高V、Q权重（例如V=12%, Q=8%）
- **调整后必须保持总和=100%**

---

### 2. publish - 发布判定配置

**路径**: `publish`

**说明**: Prime和Watch信号的发布阈值

```json
{
  "publish": {
    "prime_prob_min": 0.62,        // Prime最低概率（62%）
    "prime_dims_ok_min": 4,        // Prime最低达标维度数（10维中至少4维达标）
    "prime_dim_threshold": 65,     // 单维度达标阈值（abs(score)>=65）
    "watch_prob_min": 0.58,        // Watch最低概率（58%）
    "watch_prob_max": 0.61         // Watch最高概率（61%，超过则升级为Prime）
  }
}
```

**参数详解**:

| 参数 | 默认值 | 范围 | 说明 |
|------|--------|------|------|
| `prime_prob_min` | 0.62 | 0.5-0.9 | Prime概率阈值（降低→信号更多） |
| `prime_dims_ok_min` | 4 | 2-8 | 达标维度数（降低→信号更多） |
| `prime_dim_threshold` | 65 | 40-80 | 单维度强度（降低→更容易达标） |
| `watch_prob_min` | 0.58 | 0.5-0.8 | Watch最低概率 |
| `watch_prob_max` | 0.61 | 0.55-0.85 | Watch最高概率 |

**调整场景**:

**场景A: 提高信号质量（减少数量）**
```json
{
  "prime_prob_min": 0.68,     // 0.62 → 0.68
  "prime_dims_ok_min": 5,     // 4 → 5
  "prime_dim_threshold": 70   // 65 → 70
}
```

**场景B: 增加信号数量（降低门槛）**
```json
{
  "prime_prob_min": 0.56,     // 0.62 → 0.56
  "prime_dims_ok_min": 3,     // 4 → 3
  "prime_dim_threshold": 60   // 65 → 60
}
```

---

## 🔧 因子参数配置

### 3. trend - 趋势因子配置

**路径**: `trend`

```json
{
  "trend": {
    "ema_order_min_bars": 6,      // EMA多头排列最少K线数
    "slope_atr_min_long": 0.06,   // 做多最小斜率（相对ATR）
    "slope_atr_min_short": 0.04,  // 做空最小斜率
    "slope_lookback": 12,         // 斜率计算回看周期
    "atr_period": 14              // ATR周期
  }
}
```

**参数说明**:
- `ema_order_min_bars`: EMA5/10/20/60多头排列持续至少N根K线才认为趋势成立
- `slope_atr_min_long/short`: 斜率阈值（避免假突破）
- `atr_period`: ATR计算周期（14是经典值）

**调整建议**:
- 提高`slope_atr_min_*` → 只捕捉更强的趋势
- 降低`ema_order_min_bars` → 更快响应趋势变化

---

### 4. momentum - 动量因子配置

**路径**: `momentum`

```json
{
  "momentum": {
    "slope_lookback": 30,    // 斜率计算回看周期
    "slope_scale": 0.01,     // 斜率缩放系数
    "accel_scale": 0.005,    // 加速度缩放系数
    "slope_weight": 0.6,     // 斜率权重
    "accel_weight": 0.4      // 加速度权重
  }
}
```

**参数说明**:
- `slope_lookback`: 计算价格变化率的周期
- `slope_weight` vs `accel_weight`: 斜率和加速度的相对重要性
  - 斜率=价格变化速度
  - 加速度=速度的变化（二阶导数）

---

### 5. cvd_flow - 资金流配置

**路径**: `cvd_flow`

```json
{
  "cvd_flow": {
    "lookback_hours": 6,    // 回看时间（小时）
    "cvd_scale": 0.02       // CVD变化缩放系数
  }
}
```

**参数说明**:
- `lookback_hours`: CVD累积时间窗口
  - 6小时：短期资金流
  - 12小时：中期资金流
  - 24小时：长期资金流

---

### 6. structure - 结构因子配置

**路径**: `structure`

```json
{
  "structure": {
    "theta": {
      "big": 0.35,              // 大币种theta基础值
      "small": 0.40,            // 小币种theta基础值
      "overlay_add": 0.05,      // overlay加成
      "new_phaseA_add": 0.10,   // 新币阶段A加成
      "strong_regime_sub": 0.05 // 强趋势时theta减小
    }
  }
}
```

**参数说明**:
- `theta`: 结构模糊度参数（越小越严格）
  - 大币种通常theta更小（结构更清晰）
  - 新币theta更大（允许更模糊的结构）

---

### 7. open_interest - 持仓量配置

**路径**: `open_interest`

```json
{
  "open_interest": {
    "long_oi24_lo": 1.0,          // 做多最小24h OI变化%
    "long_oi24_hi": 8.0,          // 做多最大24h OI变化%
    "short_oi24_lo": 2.0,         // 做空最小24h OI变化%
    "short_oi24_hi": 10.0,        // 做空最大24h OI变化%
    "upup12_lo": 6,               // 多头持续上升最少K线数
    "upup12_hi": 12,              // 多头持续上升最多K线数
    "dnup12_lo": 6,               // 空头持续上升最少K线数
    "dnup12_hi": 12,              // 空头持续上升最多K线数
    "crowding_p95_penalty": 10,   // 拥挤惩罚分数
    "w_change": 0.7,              // OI变化权重
    "w_align": 0.3                // OI方向一致性权重
  }
}
```

**参数说明**:
- `*_oi24_*`: OI变化百分比阈值（太小=不显著，太大=异常）
- `upup12_*`: OI持续变化周期
- `crowding_p95_penalty`: 当OI变化超过95分位数时的惩罚

---

### 8. liquidity - 流动性配置（L因子）

**路径**: `liquidity`

```json
{
  "liquidity": {
    "spread_good_bps": 2.0,         // 好的买卖价差（2个基点）
    "spread_bad_bps": 10.0,         // 差的买卖价差（10个基点）
    "depth_target_usdt": 1000000,   // 目标订单簿深度（100万USDT）
    "impact_notional_usdt": 100000, // 冲击成本测试订单量（10万USDT）
    "impact_max_pct": 0.01,         // 最大可接受冲击（1%）
    "orderbook_depth_levels": 10,   // 订单簿深度层数
    "spread_weight": 0.3,           // 价差权重
    "depth_weight": 0.3,            // 深度权重
    "impact_weight": 0.3,           // 冲击权重
    "obi_weight": 0.1               // OBI权重
  }
}
```

**参数说明**:
- **Spread（价差）**: 买卖价差越小越好
  - `spread_good_bps`: 2 bps = 0.02% → 优秀
  - `spread_bad_bps`: 10 bps = 0.10% → 较差
- **Depth（深度）**: 订单簿厚度
  - `depth_target_usdt`: 理想深度为100万USDT
- **Impact（冲击）**: 大单滑点
  - `impact_notional_usdt`: 用10万USDT测试订单
  - `impact_max_pct`: 冲击超过1%则流动性差

---

### 9. basis_funding - 基差+资金费配置（B因子）

**路径**: `basis_funding`

```json
{
  "basis_funding": {
    "basis_neutral_bps": 50,        // 中性基差（50 bps）
    "basis_extreme_bps": 100,       // 极端基差（100 bps）
    "funding_neutral_rate": 0.001,  // 中性资金费率（0.1%）
    "funding_extreme_rate": 0.002,  // 极端资金费率（0.2%）
    "basis_weight": 0.6,            // 基差权重
    "funding_weight": 0.4,          // 资金费率权重
    "fwi_enabled": false,           // 资金加权指数（已禁用）
    "fwi_window_minutes": 30,
    "fwi_boost_max": 20
  }
}
```

**参数说明**:
- **Basis（基差）**: 现货价格 - 合约价格
  - 正基差（溢价）：合约低于现货 → 看多信号
  - 负基差（折价）：合约高于现货 → 看空信号
- **Funding Rate（资金费率）**:
  - 正费率：多头支付空头 → 市场偏多
  - 负费率：空头支付多头 → 市场偏空

---

### 10. liquidation - 清算密度配置（Q因子）

**路径**: 无独立配置（使用默认逻辑）

**说明**: Q因子通过Coinglass清算热图API获取数据，计算清算密度分数。

**逻辑**:
- 价格上方清算密度高 → 多头拥挤，可能回调
- 价格下方清算密度高 → 空头拥挤，可能反弹

---

### 11. independence - 独立性配置（I因子）

**路径**: 无独立配置

**说明**: I因子计算币种与BTC/ETH的相关性，独立性越高分数越高。

**逻辑**:
- 高相关性（>0.8）→ 跟随大盘，独立性低
- 低相关性（<0.5）→ 独立行情，独立性高

---

### 12. fund_leading - 资金领先配置（F因子）

**路径**: `fund_leading`

```json
{
  "fund_leading": {
    "oi_weight": 0.4,         // OI变化权重
    "vol_weight": 0.3,        // 成交量权重
    "cvd_weight": 0.3,        // CVD权重
    "trend_weight": 0.6,      // 趋势权重
    "slope_weight": 0.4,      // 斜率权重
    "oi_scale": 3.0,          // OI缩放系数
    "vol_scale": 0.3,         // 成交量缩放系数
    "cvd_scale": 0.02,        // CVD缩放系数
    "price_scale": 3.0,       // 价格缩放系数
    "slope_scale": 0.01,      // 斜率缩放系数
    "leading_scale": 20.0     // 领先性缩放系数
  }
}
```

**参数说明**:
- **资金领先性**: 资金指标（OI+Vol+CVD）vs 价格指标（Price+Slope）
- **F > 0**: 资金领先价格（看多信号）
- **F < 0**: 价格领先资金（看空信号）
- **F < -70**: 严重背离，触发安全阀（×0.7惩罚）

---

## 🎨 高级配置

### 13. new_coin - 新币配置

**路径**: `new_coin`

```json
{
  "new_coin": {
    "enabled": true,                    // 是否启用新币检测
    "min_hours": 1,                     // 最小上线时间（小时）
    "ultra_new_hours": 24,              // 超新币阶段（1-24小时）
    "phaseA_days": 7,                   // 阶段A（1-7天）
    "phaseB_days": 30,                  // 阶段B（7-30天）
    "max_days": 30,                     // 新币最长定义（30天）
    "min_volume_24h": 10000000,         // 最小24h成交量（1000万）
    "ultra_new_prime_prob_min": 0.70,   // 超新币Prime阈值
    "ultra_new_dims_ok_min": 6,         // 超新币达标维度
    "phaseA_prime_prob_min": 0.65,      // 阶段A Prime阈值
    "phaseA_dims_ok_min": 5,            // 阶段A达标维度
    "phaseB_prime_prob_min": 0.63,      // 阶段B Prime阈值
    "phaseB_dims_ok_min": 4             // 阶段B达标维度
  }
}
```

**参数说明**:
- 新币风险更高，因此Prime阈值更严格
- 超新币（<24h）：最严格（70%概率，6维达标）
- 阶段A（1-7天）：严格（65%概率，5维达标）
- 阶段B（7-30天）：较严格（63%概率，4维达标）
- 成熟币（>30天）：正常（62%概率，4维达标）

---

### 14. overlay - 叠加过滤配置

**路径**: `overlay`

```json
{
  "overlay": {
    "oi_1h_pct_big": 0.003,         // 大币种1h OI变化阈值（0.3%）
    "oi_1h_pct_small": 0.01,        // 小币种1h OI变化阈值（1%）
    "hot_decay_hours": 2,           // 热度衰减时间（小时）
    "z_volume_1h_threshold": 3,     // 1h成交量Z分数阈值
    "min_hour_quote_usdt": 5000000, // 最小小时成交额（500万）
    "z24_and_24h_quote": {
      "z24": 1.0,                   // 24h Z分数阈值
      "quote": 5000000              // 24h最小成交额
    },
    "triple_sync": {
      "mode": "2of3",               // 三重同步模式（3个条件满足2个）
      "dP1h_abs_pct": 0.015,        // 1h价格变化阈值（1.5%）
      "v5_over_v20": 1.2,           // 成交量比率阈值
      "cvd_mix_abs_per_h": 0.025,   // CVD变化阈值（2.5%/h）
      "anti_chase": {
        "enabled": true,            // 防追高过滤
        "lookback": 72,             // 回看周期（72根K线）
        "max_distance_pct": 0.05    // 最大距离（5%）
      }
    }
  }
}
```

**参数说明**:
- **Overlay过滤**: 叠加热度过滤，捕捉异常波动
- **Triple Sync**: 三重同步（价格+量能+CVD）确认
- **Anti-chase**: 防止追高（价格已涨5%则过滤）

---

### 15. pricing - 价格信息配置

**路径**: `pricing`

```json
{
  "pricing": {
    "entry_ext_max": 0.6,         // 最大入场延展（ATR倍数）
    "delta_base": 0.02,           // 基础Delta（2%）
    "delta_coef": 0.10,           // Delta系数
    "sl_pivot_back": 0.10,        // 止损pivot回退
    "sl_atr_back": 1.8,           // 止损ATR倍数
    "tp1_R": 1.0,                 // TP1盈亏比
    "tp2_R_max": 2.5,             // TP2最大盈亏比
    "sr_band_lookback": 72,       // 支撑阻力回看周期
    "sr_margin": 0.002,           // SR边界容差（0.2%）
    "room_atr_tp2_floor": 0.6,    // TP2最小空间（ATR倍数）
    "tp2_room_floor_R": 1.8       // TP2空间不足时的保底盈亏比
  }
}
```

**参数说明**:
- **Entry**: 入场区间 = 当前价 ± delta
- **Stop Loss**: 止损 = pivot - sl_atr_back × ATR
- **Take Profit**:
  - TP1 = entry + 1R（1倍风险）
  - TP2 = entry + 2.5R（2.5倍风险，动态调整）

---

### 16. limits - 速率限制配置

**路径**: `limits`

```json
{
  "limits": {
    "per_symbol_delay_ms": 600  // 每个币种间隔（毫秒）
  }
}
```

**参数说明**:
- `per_symbol_delay_ms`: 扫描币种之间的延迟
  - 600ms：保守（避免API限流）
  - 300ms：正常
  - 100ms：激进（可能触发限流）

---

## 🔍 查看当前配置

```bash
# 查看完整配置
cat config/params.json

# 查看权重配置
cat config/params.json | jq '.weights'

# 查看发布配置
cat config/params.json | jq '.publish'

# 验证权重总和
cat config/params.json | jq '.weights | to_entries | map(.value) | add'
# 应该输出: 100
```

---

## ⚠️ 配置修改注意事项

### 1. 修改权重后
```bash
# 验证总权重=100
python3 -c "
import json
with open('config/params.json') as f:
    weights = json.load(f)['weights']
total = sum(weights.values())
print(f'总权重: {total}')
assert total == 100.0, f'总权重必须=100, 当前={total}'
"
```

### 2. 修改后清除缓存
```bash
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
```

### 3. 测试新配置
```bash
# 小规模测试
python3 scripts/realtime_signal_scanner.py --max-symbols 10 --once

# 完整测试
python3 scripts/realtime_signal_scanner.py --once
```

---

## 📊 常见配置场景

### 场景1: 趋势市场配置
```json
{
  "weights": {
    "T": 18.0,  // ↑ 提高趋势权重
    "M": 11.0,  // ↑ 提高动量权重
    "C": 10.0,
    "S": 4.0,   // ↓ 降低结构权重（趋势市结构不重要）
    "V": 7.0,
    "O": 10.0,
    "L": 9.0,
    "B": 7.0,
    "Q": 5.0,
    "I": 7.0,
    "E": 0,
    "F": 12.0   // ↑ 提高资金领先权重
  }
}
```

### 场景2: 震荡市场配置
```json
{
  "weights": {
    "T": 10.0,  // ↓ 降低趋势权重（震荡时趋势不可靠）
    "M": 6.0,
    "C": 15.0,  // ↑ 提高资金流权重
    "S": 8.0,   // ↑ 提高结构权重（支撑阻力重要）
    "V": 8.0,
    "O": 14.0,  // ↑ 提高持仓权重
    "L": 12.0,  // ↑ 流动性重要
    "B": 9.0,
    "Q": 5.0,
    "I": 6.0,
    "E": 0,
    "F": 7.0
  }
}
```

### 场景3: 高质量信号配置
```json
{
  "publish": {
    "prime_prob_min": 0.70,     // 提高到70%
    "prime_dims_ok_min": 6,     // 至少6维达标
    "prime_dim_threshold": 70   // 单维度70分以上
  }
}
```

---

## ⚠️ 配置修改最佳实践（v7.2.7新增）

### 避免硬编码的原则

根据v7.2.3-v7.2.7硬编码清理系列的经验总结：

#### 1. 禁止的做法 ❌

```python
# 错误1: 直接硬编码数值
if prime_prob < 0.58:  # ❌ 硬编码阈值
    reject()

# 错误2: 代码中定义默认值，不读取配置
p0 = 0.58  # ❌ 应该从配置文件读取

# 错误3: 混用多个配置源
prob_min = params.get("prime_prob_min", 0.68)  # params.json
F_min = config.get_gate_threshold("gate2_fund_support", "F_min", -15)  # signal_thresholds.json
# ❌ 两个不同的配置源，容易产生冲突
```

#### 2. 推荐的做法 ✅

```python
# 正确1: 从配置文件读取
from ats_core.config.threshold_config import get_thresholds

config = get_thresholds()
prime_prob_min = config.get_mature_threshold('prime_prob_min', 0.45)

# 正确2: 使用类方法从配置创建实例
params = ModulatorParams.from_config()  # 自动从配置加载所有参数

# 正确3: 统一配置源
# 所有信号阈值都从 signal_thresholds.json 读取
prime_strength_min = config.get_mature_threshold('prime_strength_min', 35)
confidence_min = config.get_mature_threshold('confidence_min', 20)
edge_min = config.get_mature_threshold('edge_min', 0.15)
```

#### 3. 默认值一致性检查

```python
# 代码中的fallback默认值必须与配置文件保持一致
#
# 示例：ThresholdConfig._get_default_config()
def _get_default_config(self) -> Dict[str, Any]:
    """默认配置（硬编码备份）

    v7.2.7修复：默认值应与signal_thresholds.json保持一致
    """
    return {
        "基础分析阈值": {
            "mature_coin": {
                "prime_strength_min": 35,  # 必须与配置文件一致
                "confidence_min": 20,      # 必须与配置文件一致
                "edge_min": 0.15,          # 必须与配置文件一致
                "prime_prob_min": 0.45     # 必须与配置文件一致
            }
        }
    }
```

#### 4. 硬编码检测方法

```bash
# 定期扫描硬编码的阈值
grep -rn "if.*>.*0\.[0-9]" ats_core/ --include="*.py" | grep -v "test"

# 查找可能的硬编码概率阈值
grep -rn "prime_prob.*=.*0\.[0-9]" ats_core/ --include="*.py"

# 查找硬编码的分数阈值
grep -rn "strength.*>=.*[0-9]" ats_core/ --include="*.py"
```

### 配置文件冲突检测

当发现系统行为与预期不符时，首先检查配置冲突：

```bash
# 1. 检查同一参数是否在多个配置文件中定义
grep -r "prime_prob_min" config/

# 2. 对比配置文件和代码中的默认值
# 配置文件值
cat config/signal_thresholds.json | jq '.基础分析阈值.mature_coin.prime_prob_min'

# 代码默认值
grep -A 5 "_get_default_config" ats_core/config/threshold_config.py | grep prime_prob_min

# 3. 验证两者是否一致
# 如果不一致，需要修复代码中的默认值
```

### 相关文档

- **硬编码清理案例**: `standards/SYSTEM_ENHANCEMENT_STANDARD.md` § 实战案例（v7.2.3-v7.2.7）
- **配置统一说明**: `docs/v7.2.7_CONFIG_UNIFICATION.md`
- **综合清理记录**: `docs/v7.2.6_COMPREHENSIVE_HARDCODE_CLEANUP.md`

---

## 🔗 相关文档

- [SYSTEM_OVERVIEW.md](./SYSTEM_OVERVIEW.md) - 系统总览
- [MODIFICATION_RULES.md](./MODIFICATION_RULES.md) - 修改规范
- [ARCHITECTURE.md](./ARCHITECTURE.md) - 技术架构
- [SYSTEM_ENHANCEMENT_STANDARD.md](./SYSTEM_ENHANCEMENT_STANDARD.md) - 系统增强标准（v3.2.0含硬编码清理）

---

**最后更新**: 2025-11-10
