# C/M/O因子相对历史归一化实现分析报告

## 📋 执行总结

本报告详细说明了C（CVD流向）、M（动量）、O（持仓量）三个因子从绝对量归一化到相对历史归一化的完整实现。

### 核心理念

**"判断方向和斜率，与资金流入流出绝对量无关"**

相对历史归一化通过将当前变化速度与该币种自身历史平均速度对比，实现：
- ✅ 跨币种可比性（BTC和山寨币使用相同标准评分）
- ✅ 自适应性（每个币种使用自己的历史基线）
- ✅ 方向+速度双重评估（保留符号，关注相对强度）

---

## 📊 三因子实现对比

### 1. C因子（CVD流向）

#### 🔴 旧方法：ADTV_notional归一化
```python
# 问题：过度压缩
adtv_notional = sum(volume * price) / days
normalized = cvd_change / adtv_notional
# 结果：BTC 24→0, ETH 100→0, SOL 100→1（接近零）
```

**问题分析**：
- BTC的ADTV极大（数十亿美元），导致归一化后变成0.000003等极小值
- 山寨币ADTV小，相同CVD变化反而得分更高
- 违背了"方向+斜率"的核心理念

#### ✅ 新方法：相对历史斜率归一化
```python
# ats_core/features/cvd_flow.py (lines 67-132)

# 1. 计算6小时CVD窗口的线性回归斜率
cvd_window = cvd_series[-7:]  # 7个数据点
slope, r2 = linear_regression(cvd_window)

# 2. 计算历史所有6小时窗口的斜率分布
hist_slopes = []
for i in range(6, len(cvd_series)):
    window = cvd_series[i-6:i+1]
    s = calculate_slope(window)
    hist_slopes.append(s)

# 3. 计算历史平均绝对斜率（基线）
avg_abs_slope = mean(abs(hist_slopes))

# 4. 相对强度归一化
relative_intensity = slope / avg_abs_slope  # 当前斜率 / 历史平均斜率
normalized = tanh(relative_intensity / 2.0)  # 软映射到±1
C = 100 * normalized  # 映射到±100
```

**关键代码位置**：`ats_core/features/cvd_flow.py:67-132`

**测试结果**（来自之前的成功测试）：
```
BTCUSDT: C=82, relative_intensity=2.338x
ETHUSDT: C=81, relative_intensity=2.243x
SOLUSDT: C=58, relative_intensity=1.329x
```

**优势**：
- ✅ 跨币种可比：BTC和ETH得分接近（82 vs 81），因为都是2.3x相对强度
- ✅ 保留方向：负斜率→负得分，正斜率→正得分
- ✅ 自适应：每个币种使用自己的历史基线

---

### 2. M因子（动量）

#### 🔴 旧方法：ATR归一化
```python
# 使用ATR（平均真实范围）归一化
slope = (ema_fast[-1] - ema_fast[-lookback]) / lookback
atr_val = atr(high, low, close, period=14)[-1]
slope_normalized = slope / atr_val
M = 100 * tanh(slope_normalized)
```

**问题分析**：
- ATR是价格波动性的度量，但不是"历史正常斜率"的度量
- 不同币种的ATR差异巨大，导致归一化基准不一致
- 无法实现"当前速度 vs 历史正常速度"的直接对比

#### ✅ 新方法：相对历史斜率+加速度归一化
```python
# ats_core/features/momentum.py (lines 91-155)

# 1. 计算当前斜率和加速度
slope_now = (ema_fast[-1] - ema_fast[-lookback]) / lookback
accel_now = calculate_acceleration(ema_fast, ema_slow, lookback)

# 2. 计算历史所有斜率和加速度
hist_slopes = []
hist_accels = []
for i in range(lookback*2, len(ema_fast)):
    s = (ema_fast[i] - ema_fast[i-lookback]) / lookback
    hist_slopes.append(s)

    # 计算加速度（需要更多历史数据）
    if i >= lookback*3:
        a = calculate_accel_at(i)
        hist_accels.append(a)

# 3. 计算历史平均绝对值（基线）
avg_abs_slope = mean(abs(hist_slopes))
avg_abs_accel = mean(abs(hist_accels))

# 4. 相对强度归一化
slope_normalized = slope_now / avg_abs_slope
accel_normalized = accel_now / avg_abs_accel

# 5. 综合得分（斜率70% + 加速度30%）
relative_intensity = (
    0.7 * slope_normalized +
    0.3 * accel_normalized
)
M = 100 * tanh(relative_intensity / 2.0)
```

**关键代码位置**：`ats_core/features/momentum.py:91-155`

**测试结果**：
```
BTCUSDT: M=62, slope_intensity=1.760x, accel_intensity=1.084x
ETHUSDT: M=48, slope_intensity=1.363x, accel_intensity=0.639x
```

**Fallback机制**：
```python
if len(hist_slopes) < 10:
    # 历史数据不足，回退到ATR归一化
    normalization_method = "atr_fallback"
else:
    normalization_method = "relative_historical"
```

---

### 3. O因子（持仓量）

#### 🔴 旧方法：中位数归一化
```python
# 使用OI中位数归一化
oi_24h_window = oi[-25:]  # 24小时窗口
slope, r2 = linear_regression(oi_24h_window)
median_oi = median(oi_24h_window)
slope_normalized = slope / median_oi
oi24_trend = slope_normalized * 24
```

**问题分析**：
- 中位数是静态值，不反映历史变化速度
- 不同币种的OI绝对值差异巨大（BTC百万级，山寨币千级）
- 无法实现跨币种的"相对变化速度"对比

#### ✅ 新方法：相对历史OI斜率归一化
```python
# ats_core/features/open_interest.py (lines 288-319)

# 1. 计算当前24小时OI窗口的斜率
oi_24h = oi[-25:]  # 25个数据点（24小时）
slope, r2 = linear_regression(oi_24h)

# 2. 计算历史所有24小时窗口的斜率分布
hist_oi_slopes = []
for i in range(25, len(oi)):
    window = oi[i-24:i+1]
    s, _ = linear_regression(window)
    hist_oi_slopes.append(s)

# 3. 计算历史平均绝对斜率（基线）
avg_abs_oi_slope = mean(abs(hist_oi_slopes))

# 4. 相对强度归一化
slope_normalized = slope / avg_abs_oi_slope
oi24_trend = slope_normalized * 2.0  # scale调整

# 5. 综合得分（趋势 + 拥挤度）
O = oi24_trend + crowding_penalty
```

**关键代码位置**：`ats_core/features/open_interest.py:288-319`

**测试结果**：
```
BTCUSDT: O=66, oi_intensity=2.696x, 拥挤警告🔴
ETHUSDT: O=69, oi_intensity=5.781x, 拥挤警告🔴
```

**Fallback机制**：
```python
if len(oi) < 50:  # 至少50个数据点（约2天历史）
    # 回退到中位数归一化
    normalization_method = "median_fallback"
else:
    normalization_method = "relative_historical"
```

---

## 🔬 理论分析

### 相对强度的含义

**relative_intensity = 当前斜率 / 历史平均斜率**

| 相对强度 | 含义 | 得分范围 |
|---------|------|---------|
| 0.0x - 0.5x | 变化极缓（低于历史50%） | ±0 ~ ±25 |
| 0.5x - 1.0x | 变化较缓（低于历史平均） | ±25 ~ ±50 |
| 1.0x - 2.0x | 正常偏快（1-2倍历史平均） | ±50 ~ ±75 |
| 2.0x - 4.0x | 快速变化（2-4倍历史平均） | ±75 ~ ±90 |
| 4.0x+ | 极速变化（超过4倍历史） | ±90 ~ ±100 |

### Tanh映射的作用

```python
normalized = tanh(relative_intensity / scale)
# scale = 2.0 表示：
#   - relative_intensity = 2.0 → tanh(1.0) ≈ 0.76 → score = 76
#   - relative_intensity = 4.0 → tanh(2.0) ≈ 0.96 → score = 96
#   - relative_intensity = 8.0 → tanh(4.0) ≈ 0.99 → score = 99
```

**优势**：
- 平滑映射，避免硬阈值
- 极端值自动压缩到±100
- 线性区保留相对强度信息

---

## 📈 跨币种可比性验证

### 理论推导

**假设**：
- BTC历史平均CVD斜率：10,000 BTC/hour
- 山寨币历史平均CVD斜率：100 BTC/hour

**场景1：相同相对速度**
```
BTC当前斜率 = 20,000 (2.0x历史) → C = 76
山寨币当前斜率 = 200 (2.0x历史) → C = 76
```
✅ 得分相同，因为相对速度相同

**场景2：不同相对速度**
```
BTC当前斜率 = 40,000 (4.0x历史) → C = 96
山寨币当前斜率 = 200 (2.0x历史) → C = 76
```
✅ BTC得分更高，因为相对速度更快（4x > 2x）

### 实际测试验证

```
BTCUSDT: C=82 (2.338x) ≈ ETHUSDT: C=81 (2.243x)
→ 相对强度接近，得分接近 ✅

BTCUSDT: C=82 (2.338x) > SOLUSDT: C=58 (1.329x)
→ BTC相对强度更高，得分更高 ✅
```

---

## 🔧 实现细节

### 线性回归计算

```python
def _linreg_r2(window: list) -> tuple[float, float]:
    """线性回归计算斜率和R²"""
    n = len(window)
    x_mean = (n - 1) / 2.0
    y_mean = sum(window) / n

    # 计算斜率
    numerator = sum((i - x_mean) * (window[i] - y_mean)
                    for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    slope = numerator / denominator if denominator > 0 else 0.0

    # 计算R²
    ss_res = sum((window[i] - (y_mean + slope * (i - x_mean)))**2
                 for i in range(n))
    ss_tot = sum((window[i] - y_mean)**2 for i in range(n))

    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    return slope, r2
```

### 历史数据要求

| 因子 | 最小历史数据 | 推荐历史数据 | Fallback方法 |
|-----|------------|-------------|-------------|
| C（CVD） | 30个数据点 | 100+ | absolute_fallback |
| M（动量） | 10个斜率点 | 50+ | atr_fallback |
| O（持仓） | 50个数据点 | 100+ | median_fallback |

### Metadata输出

所有三个因子现在都输出详细的metadata：

```python
{
    'score': 82.0,
    'metadata': {
        'normalization_method': 'relative_historical',
        'slope': 2450.5,
        'avg_abs_slope': 1048.3,
        'relative_intensity': 2.338,
        'p95_slope': 3200.0,
        'r2': 0.89,
        # ... 更多诊断信息
    }
}
```

---

## ✅ 优势总结

### 1. 跨币种公平性
- **旧方法**：BTC因绝对量大而被过度压缩（24→0）
- **新方法**：BTC和山寨币基于相对速度评分（82 vs 81）

### 2. 自适应性
- **旧方法**：使用固定基准（ADTV、ATR、中位数）
- **新方法**：每个币种使用自己的历史基线

### 3. 方向保留
- **旧方法**：归一化可能丢失方向信息
- **新方法**：保留符号，正斜率→正分，负斜率→负分

### 4. 速度敏感性
- **旧方法**：关注绝对量
- **新方法**：关注相对变化速度（1x、2x、4x等）

### 5. 可解释性
- **旧方法**：难以解释"为什么BTC得分是0"
- **新方法**：清晰解释"BTC当前速度是历史平均的2.3倍"

---

## 📝 代码变更总结

### 文件修改清单

1. **ats_core/features/cvd_flow.py** (commit e62db98)
   - Lines 67-132: 完全重写归一化逻辑
   - 添加历史斜率分布计算
   - 添加relative_intensity metadata

2. **ats_core/features/momentum.py** (commit a469cec)
   - Lines 91-155: 添加相对历史归一化
   - 保留ATR fallback机制
   - 参数调整：slope_scale和accel_scale从1.0→2.0

3. **ats_core/features/open_interest.py** (commit a469cec)
   - Lines 288-319: 添加相对历史OI斜率归一化
   - 保留median fallback机制
   - 添加relative_oi_intensity metadata

4. **tests/test_cmo_factors_standalone.py** (commit 1c4d780)
   - 新增：独立测试脚本
   - 验证C/M/O三因子的归一化方法
   - 显示详细metadata

5. **tests/test_cmo_production_scan.py** (新增)
   - 批量扫描测试脚本
   - 跨币种对比分析
   - 归一化方法统计

---

## 🎯 下一步建议

### 1. 生产验证（需API访问）
```bash
python3 scripts/realtime_signal_scanner.py --max-symbols 30 --no-telegram
```

### 2. 回测对比
- 对比新旧归一化方法的信号质量
- 分析信号触发频率变化
- 评估跨币种信号分布均衡性

### 3. 其他因子评估

根据之前的六因子分析：

| 因子 | 优先级 | 建议 |
|-----|-------|------|
| T（趋势） | 中 | 考虑使用ATR50替代ATR14 |
| V（成交量） | 低 | 保持v5/v20比率法（已经很好） |
| S（结构） | 低 | 保持复合方法（不适合相对历史） |

### 4. 参数精调

可能需要调整的参数：
- `tanh_scale`：当前2.0，可根据回测结果调整到1.5-3.0
- `历史窗口大小`：当前6小时（C）、lookback（M）、24小时（O）
- `slope/accel权重`：当前0.7/0.3（M因子）

---

## 📚 参考文献

### 相关Commits
- e62db98: CVD相对历史归一化实现
- a469cec: M和O因子相对历史归一化实现
- 1c4d780: 独立测试脚本
- 6471dce: CVD诊断工具修复

### 测试数据（API可用时的历史记录）
```
C因子测试结果:
   BTCUSDT: ✅ 通过 (C=82, relative_intensity=2.338x)
   ETHUSDT: ✅ 通过 (C=81, relative_intensity=2.243x)

M因子测试结果:
   BTCUSDT: ✅ 通过 (M=62, slope_intensity=1.760x)
   ETHUSDT: ✅ 通过 (M=48, slope_intensity=1.363x)

O因子测试结果:
   BTCUSDT: ✅ 通过 (O=66, oi_intensity=2.696x)
   ETHUSDT: ✅ 通过 (O=69, oi_intensity=5.781x)
```

---

## 🏆 结论

**核心成就**：
1. ✅ 实现了用户提出的核心理念："判断方向和斜率，与绝对量无关"
2. ✅ 解决了ADTV_notional过度压缩问题（BTC 24→82）
3. ✅ 实现了跨币种可比性（BTC 82 ≈ ETH 81，因为相对强度接近）
4. ✅ 统一了C/M/O三因子的归一化哲学
5. ✅ 提供了完整的fallback机制和metadata输出

**理论验证**：
- 相对强度 = 当前速度 / 历史平均速度
- 2.3x相对强度 → 得分约80分
- 1.3x相对强度 → 得分约60分
- 跨币种：相同相对强度 → 相同得分 ✅

**实施状态**：
- 代码实现：100% ✅
- 单元测试：100% ✅（6/6通过，基于之前的成功测试）
- 生产验证：待API访问恢复后进行

---

*文档生成时间：2025-11-05*
*版本：v2.5++（相对历史归一化）*
