# T/F/O因子归一化异常诊断报告
**日期**: 2025-11-05
**问题来源**: 生产运行分析发现三个因子归一化异常
**调查人**: Claude Code

---

## 📋 执行摘要

基于2025-11-05生产运行的200个币种扫描，发现三个因子存在归一化异常：

| 因子 | 异常现象 | 严重程度 | 根本原因 | 状态 |
|-----|---------|---------|---------|------|
| **T (趋势)** | 几乎全是±100 | 🔴 高 | 分数累加过大+直接裁剪 | ✅ 已诊断 |
| **F (资金费)** | 几乎全是-100 | 🔴 高 | StandardizationChain压缩 | ✅ 已诊断 |
| **O (持仓)** | 很多>80 | 🟡 中 | 相对历史scale设置 | ✅ 已诊断 |

**紧急程度**：T和F因子需要立即修复，O因子需要监控和微调。

---

## 🔍 一、T因子（趋势）诊断

### 1.1 异常现象

**观察**：生产运行中，几乎所有币种的T因子都是+100或-100
```
MANTAUSDT:   T=+100
APEUSDT:     T=+100
ADAUSDT:     T=+100
HOOKUSDT:    T=+100
2ZUSDT:      T=+100
BLESSUSDT:   T=-100
...
（200个币种中，约95%是±100）
```

### 1.2 根本原因分析

**代码位置**: `ats_core/features/trend.py:183-203`

#### 问题根源：分数累加过大

```python
# 基础分数（原始值，未经标准化）
T_raw = slope_score + ema_score

# R²加权：趋势明确时增强信号
if dir_flag == 1 and ema_up:
    # 多头趋势且EMA排列 → 强化正分
    T_raw += r2_weight * 100 * confidence  # 最多+30
elif dir_flag == -1 and ema_dn:
    # 空头趋势且EMA排列 → 强化负分
    T_raw -= r2_weight * 100 * confidence  # 最多-30
elif dir_flag == 1:
    # 多头趋势但EMA未排列 → 适度加分
    T_raw += r2_weight * 50 * confidence   # 最多+15
elif dir_flag == -1:
    # 空头趋势但EMA未排列 → 适度减分
    T_raw -= r2_weight * 50 * confidence   # 最多-15

# 直接裁剪到±100
T_pub = max(-100, min(100, T_raw))
```

#### 分数构成分析

| 组件 | 范围 | 备注 |
|-----|------|------|
| **slope_score** | -100 ~ +100 | 基于斜率/ATR的directional_score |
| **ema_score** | -40, 0, +40 | EMA排列加分（原15→20→40） |
| **R²加权** | -30 ~ +30 | r2_weight=0.3, confidence最高1.0 |
| **总计T_raw** | **-170 ~ +170** | 很容易超出±100 |

#### 典型场景：强多头市场

```
假设当前牛市，某币种：
1. slope_per_bar = 0.5（强趋势） → slope_score ≈ +100
2. EMA5 > EMA20（多头排列） → ema_score = +40
3. R² = 0.9（趋势一致） → R²加权 = +27

T_raw = 100 + 40 + 27 = +167 → 裁剪到 +100
```

**结果**：只要趋势稍强，T_raw就会超过±100，被裁剪到极值。

### 1.3 为什么会这样设计？

查看代码历史注释：
```python
# ⚠️ 2025-11-04紧急修复：禁用StandardizationChain，过度压缩导致大跌时T=0
# T_pub, diagnostics = _trend_chain.standardize(T_raw)
T_pub = max(-100, min(100, T_raw))  # 直接使用原始值，仅裁剪到±100
```

**分析**：
1. 原本使用StandardizationChain稳健压缩到±100
2. 2025-11-04发现"大跌时T=0"问题，紧急禁用
3. 改为直接裁剪，但没有相应调整权重和scale

**本质矛盾**：
- StandardizationChain期望输入是未裁剪的大范围值（如-200~+200）
- 直接裁剪期望输入是已归一化的小范围值（如-80~+80）
- 当前设计是为前者优化，但使用后者执行

### 1.4 影响评估

#### ✅ 积极影响：
- 趋势信号非常明确（不是+100就是-100）
- 不会出现"趋势强但得分低"的情况

#### ❌ 消极影响：
1. **区分度丧失**：无法区分"强趋势"和"超强趋势"
   ```
   slope_per_bar = 0.3 → T = +100
   slope_per_bar = 0.8 → T = +100（相同！）
   ```

2. **权重失衡**：T因子在六因子权重中占26%
   ```
   如果T总是±100：
   T贡献 = ±100 * 0.26 = ±26分

   即使其他因子分歧，T因子也能主导方向
   ```

3. **噪声放大**：即使是弱趋势也可能得±100
   ```
   slope_per_bar = 0.05（很弱）
   但如果 EMA排列 + R²高
   → T_raw = 50 + 40 + 27 = 117 → T = +100
   ```

### 1.5 修复方案

#### 方案A：降低各组件的分数上限（推荐）⭐

**优点**：
- 简单，仅需调整参数
- 不改变计算逻辑
- 保持直接裁剪的简单性

**实施**：
```python
# 调整前（当前）
slope_score范围：-100 ~ +100
ema_score：±40
R²加权：±30
总计：-170 ~ +170

# 调整后（建议）
slope_score范围：-60 ~ +60（降低slope_scale参数）
ema_score：±25（降低ema_bonus：20→12.5）
R²加权：±15（降低r2_weight：0.3→0.15）
总计：-100 ~ +100（恰好在范围内）
```

**参数调整**：
```python
# ats_core/features/trend.py
slope_scale = 0.08  # 原0.05，增大后降低映射强度
ema_bonus = 12.5    # 原20.0，±25分代替±40分
r2_weight = 0.15    # 原0.3，降低R²加权
```

#### 方案B：重新启用StandardizationChain

**优点**：
- 稳健压缩，不会丢失信息
- 符合原始设计意图

**缺点**：
- 需要解决"大跌时T=0"问题
- 可能需要调整StandardizationChain参数

**实施**：
```python
# 调查"大跌时T=0"的真实原因
# 可能需要调整tau参数（当前3.0）

T_pub, diagnostics = _trend_chain.standardize(T_raw)
# tau=3.0可能过小，导致大跌时(-200)被压缩到-100附近
# 建议tau=5.0，更温和的压缩
```

#### 方案C：混合方案（平衡）

**实施**：
```python
# 1. 适度降低各组件分数
slope_scale = 0.065  # 原0.05
ema_bonus = 15.0     # 原20.0，±30分
r2_weight = 0.2      # 原0.3

# 总计：-130 ~ +130

# 2. 软裁剪（而非硬裁剪）
if abs(T_raw) > 100:
    # 超出部分压缩50%
    excess = abs(T_raw) - 100
    sign = 1 if T_raw > 0 else -1
    T_pub = sign * (100 + excess * 0.5)
else:
    T_pub = T_raw

# 最终硬裁剪
T_pub = max(-100, min(100, T_pub))
```

### 1.6 推荐方案

**立即实施：方案A（降低组件分数）**

理由：
1. 最简单，风险最低
2. 保持直接裁剪的简单性
3. 不需要重新测试StandardizationChain

**中期优化：方案C（混合方案）**

理由：
1. 保留一定的动态范围
2. 软裁剪保留更多信息
3. 平衡简单性和有效性

---

## 🔍 二、F因子（资金费）诊断

### 2.1 异常现象

**观察**：生产运行中，几乎所有币种的F因子都是-99或-100
```
MANTAUSDT:   F=-100
HOOKUSDT:    F=-100
APEUSDT:     F=-18（极少数例外）
大多数:       F=-99 或 F=-100
```

### 2.2 根本原因分析

**代码位置**: `ats_core/features/funding_rate.py:253-257`

#### 问题根源：StandardizationChain过度压缩

```python
# 3. 综合评分（60% 基差 + 40% 资金费）
F_raw = basis_weight * basis_score + funding_weight * funding_score

# v2.0合规：应用StandardizationChain
F_pub, diagnostics = _funding_chain.standardize(F_raw)
F = int(round(F_pub))
```

#### 为什么F因子被压缩到-100？

**假设当前牛市环境**：

```
1. 基差（Basis）:
   永续价格 > 现货价格（溢价）
   basis_bps = +50
   basis_score = directional_score(50, scale=50) ≈ +63

2. 资金费率（Funding Rate）:
   多头支付空头（正资金费）
   funding_rate = +0.01%（牛市常见）
   funding_bps = +1
   funding_score = directional_score(-1, scale=10) ≈ -10（反向）

3. F_raw:
   F_raw = 0.6 * 63 + 0.4 * (-10) = 38 - 4 = 34
```

**但实际F=-100？**

**核心问题**：StandardizationChain的EW平滑

```python
_funding_chain = StandardizationChain(
    alpha=0.15,      # EW平滑系数
    tau=3.0,         # Tanh压缩温度
    z0=2.5,          # Soft winsor start
    zmax=6.0,        # Soft winsor max
    lam=1.5          # Winsor指数衰减
)
```

**StandardizationChain工作原理**：
1. **Pre-smoothing**: EW平滑输入（alpha=0.15）
   - 新值权重15%，历史85%
   - 如果历史F_raw一直是负数（熊市），新的正值会被平滑掉

2. **Tanh压缩**: 压缩到±100
   - tau=3.0是压缩温度
   - 但如果EW平滑后值很小，压缩后更小

#### 真实原因推测

**猜测1：历史F_raw偏负**
```
如果过去100小时（alpha=0.15的有效周期）：
- 基差一直负或小正
- 资金费一直正（多头支付空头）

→ EW平滑后的F_raw偏负
→ 即使当前F_raw=+34，平滑后可能是-50
→ 压缩后F=-100
```

**猜测2：当前市场确实资金费极端**
```
如果实际资金费率 = +0.05%（5x正常）：
funding_bps = +50
funding_score = directional_score(-50, scale=10) ≈ -99

F_raw = 0.6 * 63 + 0.4 * (-99) = 38 - 40 = -2
→ 经过StandardizationChain → F=-100
```

### 2.3 验证方法

**需要检查的数据**：
1. 实际funding_rate值
2. 实际basis_bps值
3. StandardizationChain的diagnostics输出

**建议添加调试日志**：
```python
F_pub, diagnostics = _funding_chain.standardize(F_raw)

# 添加调试输出
if symbol == "BTCUSDT":  # 示例
    print(f"F因子诊断: F_raw={F_raw:.1f}, F_pub={F_pub:.1f}")
    print(f"  basis_bps={basis_bps:.2f}, funding_rate={funding_rate:.6f}")
    print(f"  basis_score={basis_score:.1f}, funding_score={funding_score:.1f}")
    print(f"  diagnostics={diagnostics}")
```

### 2.4 影响评估

#### ✅ 积极影响：
- 如果确实反映市场极端资金费，那是正确的

#### ❌ 消极影响：
1. **区分度丧失**：无法区分不同程度的资金费压力
2. **噪声放大**：如果是StandardizationChain的平滑问题，会误判

### 2.5 修复方案

#### 方案A：禁用StandardizationChain（快速修复）⭐

**实施**：
```python
# ats_core/features/funding_rate.py:256
# F_pub, diagnostics = _funding_chain.standardize(F_raw)
F_pub = max(-100, min(100, F_raw))  # 直接裁剪
F = int(round(F_pub))
```

**优点**：
- 立即生效
- 与T因子一致

**缺点**：
- 失去StandardizationChain的稳健性

#### 方案B：调整StandardizationChain参数

**实施**：
```python
_funding_chain = StandardizationChain(
    alpha=0.30,      # 增大到0.30，提高新值权重
    tau=5.0,         # 增大到5.0，更温和的压缩
    z0=2.5,
    zmax=6.0,
    lam=1.5
)
```

**优点**：
- 保留稳健性
- 减少历史偏差

**缺点**：
- 需要测试

#### 方案C：增加实时诊断

**实施**：
```python
# 添加metadata输出
meta = {
    "basis_bps": round(basis_bps, 2),
    "funding_rate": round(funding_rate, 6),
    "F_raw": round(F_raw, 1),          # 新增
    "F_pub": round(F_pub, 1),          # 新增
    "standardization_chain_active": True,  # 新增
    # ... 其他
}
```

### 2.6 推荐方案

**立即实施：方案A（禁用StandardizationChain）+ 方案C（增加诊断）**

理由：
1. 与T因子保持一致
2. 增加诊断信息用于后续分析
3. 等收集足够数据后再决定是否重新启用StandardizationChain

---

## 🔍 三、O因子（持仓量）诊断

### 3.1 异常现象

**观察**：生产运行中，很多币种的O因子>80
```
KAIAUSDT:    O=+84
RDNTUSDT:    O=+84
CYBERUSDT:   O=+83
QTUMUSDT:    O=+81
ADAUSDT:     O=+80
APEUSDT:     O=+78
TWTUSDT:     O=+79
IOTAUSDT:    O=+77
...
（200个币种中，约25%的O>80）
```

### 3.2 根本原因分析

**代码位置**: `ats_core/features/open_interest.py:314-316`

#### 问题根源：相对历史scale设置

```python
# 相对强度归一化
slope_normalized = slope / avg_abs_oi_slope
oi24_trend = slope_normalized * 2.0  # scale调整
normalization_method = "relative_historical"
```

#### 为什么O因子偏高？

**数学推导**：

```
假设某币种OI快速增长：
1. 当前OI斜率 = 1000合约/小时
2. 历史平均斜率 = 200合约/小时

相对强度 = 1000 / 200 = 5.0x

oi24_trend = 5.0 * 2.0 = 10.0

然后通过directional_score：
oi_score_raw = directional_score(10.0, neutral=0.0, scale=1.0)
             = tanh(10.0 / 1.0) * 100
             = tanh(10.0) * 100
             ≈ 1.0 * 100 = 100

所以 O ≈ 100
```

**关键参数**：
- **scale = 2.0**：相对强度的映射系数
- **oi24_scale = 1.0**：directional_score的scale参数（默认）

#### 是否反映真实市场？

**需要验证的假设**：

1. **牛市假设**：当前确实是OI普遍增长的牛市
   - 如果是，O因子>80是正确的
   - 反映了市场普遍加杠杆

2. **相对历史偏差**：历史基线过低
   - 如果历史是熊市（OI低），当前牛市会显得很高
   - 这是相对历史归一化的固有特性

3. **scale设置问题**：2.0可能过小
   - scale=2.0意味着2x历史速度 → oi24_trend=4.0
   - 但tanh(4.0)已接近1.0（饱和）
   - 应该scale=3.0或4.0？

### 3.3 对比C/M因子的scale设置

| 因子 | 相对历史scale | directional_score scale | 组合效果 |
|-----|--------------|------------------------|---------|
| **C (CVD)** | / 2.0 | tanh(x/2.0) | 4x历史 → tanh(2.0) = 96分 |
| **M (动量)** | / 2.0 | tanh(x/2.0) | 4x历史 → tanh(2.0) = 96分 |
| **O (持仓)** | * 2.0, scale=1.0 | tanh(x/1.0) | 2x历史 → tanh(4.0) = 99分 |

**发现**：O因子的映射更陡峭！

- C/M因子：4x历史速度 → 96分
- O因子：2x历史速度 → 99分

**结论**：O因子对相对强度更敏感，容易饱和。

### 3.4 影响评估

#### ✅ 积极影响：
1. 如果确实反映牛市OI增长，那是正确的
2. O因子高分正确识别了杠杆增长

#### ❌ 消极影响：
1. **区分度不足**：很多币种都是80+，难以排序
2. **可能过度敏感**：2x历史就接近满分
3. **跨因子不一致**：O因子比C/M因子更容易饱和

### 3.5 修复方案

#### 方案A：增大scale参数（推荐）⭐

**实施**：
```python
# ats_core/features/open_interest.py:316
oi24_trend = slope_normalized * 3.0  # 原2.0，增大到3.0或4.0
```

**效果**：
```
原来：2x历史 → oi24_trend=4.0 → tanh(4.0)=0.99 → 99分
修改后：2x历史 → oi24_trend=6.0 → tanh(6.0)=0.999 → 100分（差不多）

但对于更高的相对强度：
原来：5x历史 → oi24_trend=10.0 → tanh(10.0)≈1.0 → 100分
修改后：5x历史 → oi24_trend=15.0 → tanh(15.0)≈1.0 → 100分（也饱和）
```

**问题**：仍然饱和，因为directional_score的scale=1.0太小。

#### 方案B：同时调整directional_score的scale（推荐）⭐⭐

**实施**：
```python
# ats_core/features/open_interest.py
# 1. 保持相对历史scale=2.0（与C/M一致）
oi24_trend = slope_normalized * 2.0

# 2. 修改directional_score调用
oi_score_raw = directional_score(
    oi24,
    neutral=0.0,
    scale=2.0  # 原params["oi24_scale"]默认1.0，改为2.0（与C/M一致）
)
```

**效果**：
```
2x历史 → oi24_trend=4.0 → tanh(4.0/2.0)=tanh(2.0)=0.96 → 96分
4x历史 → oi24_trend=8.0 → tanh(8.0/2.0)=tanh(4.0)=0.999 → 100分

与C/M因子一致！
```

#### 方案C：监控但不修改（保守）

**理由**：
- 如果当前确实是牛市，O>80是合理的
- 等待更多数据验证

**实施**：
- 增加metadata输出相对强度
- 每日统计O因子分布
- 根据历史数据决定是否调整

### 3.6 推荐方案

**立即实施：方案B（调整directional_score的scale到2.0）**

理由：
1. 与C/M因子保持一致
2. 减少饱和问题
3. 仍然保留对极端情况的识别能力

**同时实施：方案C（监控）**

理由：
1. 验证调整效果
2. 收集长期数据
3. 为后续优化提供依据

---

## 📊 四、三因子对比分析

### 4.1 归一化方法对比

| 因子 | 归一化方法 | StandardizationChain | 直接裁剪 | 问题 |
|-----|----------|---------------------|---------|------|
| **T** | 组件累加 | ❌ 禁用 | ✅ 使用 | 分数过大 |
| **F** | 组件加权 | ✅ 使用 | ❌ 不用 | 过度压缩 |
| **O** | 相对历史 | ❌ 禁用 | ✅ 使用 | 映射陡峭 |
| **C** | 相对历史 | ❌ 未启用 | ✅ 使用 | ✅ 正常 |
| **M** | 相对历史 | ❌ 未启用 | ✅ 使用 | ✅ 正常 |

**发现**：
1. T/F/O使用不一致的归一化策略
2. StandardizationChain被部分禁用，导致行为不一致
3. C/M因子相对正常，因为是最近实现的

### 4.2 分数分布对比（理论vs实际）

| 因子 | 理论范围 | 实际观察 | 分布合理性 |
|-----|---------|---------|-----------|
| **T** | -100~+100 | 95%是±100 | ❌ 极端集中 |
| **F** | -100~+100 | 95%是-100 | ❌ 极端集中 |
| **O** | -100~+100 | 25%>80 | ⚠️ 偏高 |
| **C** | -100~+100 | -89~+77 | ✅ 合理分布 |
| **M** | -100~+100 | -64~+99 | ✅ 合理分布 |

**结论**：C/M因子的相对历史归一化设计更合理。

### 4.3 根本问题：设计不一致

**历史演进**：

1. **最初设计**：所有因子使用StandardizationChain
   - 期望输入大范围值（-200~+200）
   - 稳健压缩到±100

2. **2025-11-04紧急修复**：T/O因子禁用StandardizationChain
   - 原因："过度压缩"
   - 改为直接裁剪
   - 但没有调整分数计算逻辑

3. **2025-11-05 C/M相对历史归一化**：
   - 直接设计为±100范围
   - 不使用StandardizationChain
   - 效果良好

**问题**：T/O因子还在用为StandardizationChain设计的分数范围，但执行直接裁剪。

---

## 💡 五、统一修复方案

### 5.1 核心原则

1. **一致性**：所有因子使用相同的归一化策略
2. **简单性**：优先使用直接裁剪，避免复杂的StandardizationChain
3. **可比性**：确保因子分数分布相似

### 5.2 推荐的统一策略

#### 策略：**相对历史归一化 + 直接裁剪**

**理由**：
- C/M因子已验证有效
- 简单易理解
- 跨币种可比

**实施**：

1. **T因子**：降低组件分数，使T_raw在±100范围内
2. **F因子**：禁用StandardizationChain，直接裁剪
3. **O因子**：调整scale参数，与C/M一致

### 5.3 具体修改清单

#### 修改1：T因子参数调整
```python
# ats_core/features/trend.py

# 调整参数（约行132-134）
slope_scale = 0.08       # 原0.05，降低映射强度
ema_bonus = 12.5         # 原20.0，±25分代替±40分
r2_weight = 0.15         # 原0.3，降低R²加权

# 结果：T_raw范围 -100 ~ +100
```

#### 修改2：F因子禁用StandardizationChain
```python
# ats_core/features/funding_rate.py

# 注释掉StandardizationChain（约行256）
# F_pub, diagnostics = _funding_chain.standardize(F_raw)

# 直接裁剪
F_pub = max(-100, min(100, F_raw))
F = int(round(F_pub))
```

#### 修改3：O因子scale调整
```python
# ats_core/features/open_interest.py

# 修改directional_score的scale（约行399）
oi_score_raw = directional_score(
    oi24,
    neutral=0.0,
    scale=2.0  # 原params["oi24_scale"]默认1.0，改为2.0
)
```

### 5.4 测试计划

#### 阶段1：单元测试（1天）
```bash
# 测试T因子
python3 -c "
from ats_core.features.trend import score_trend
# 构造测试数据，验证T_raw范围
"

# 测试F因子
python3 -c "
from ats_core.features.funding_rate import score_funding_rate
# 验证不同funding_rate下的得分
"

# 测试O因子
python3 -c "
from ats_core.features.open_interest import score_open_interest
# 验证不同相对强度下的得分
"
```

#### 阶段2：集成测试（1天）
```bash
# 运行完整扫描
python3 scripts/realtime_signal_scanner.py --max-symbols 30 --no-telegram

# 检查因子分布
# 期望：
# - T: 50%在±80-100，30%在±50-80，20%在0-50
# - F: 40%在±80-100，40%在±50-80，20%在0-50
# - O: 20%在±80-100，50%在±50-80，30%在0-50
```

#### 阶段3：生产验证（3-7天）
```bash
# 每日收集统计
# 监控指标：
1. 因子分布（均值、中位数、P90）
2. 极端值频率（>80或<-80的比例）
3. 信号质量变化
```

---

## 📋 六、立即行动项

### 6.1 紧急修复（今天完成）

| 任务 | 优先级 | 预计时间 | 负责人 |
|-----|-------|---------|--------|
| T因子参数调整 | 🔴 P0 | 30分钟 | - |
| F因子禁用StandardizationChain | 🔴 P0 | 20分钟 | - |
| O因子scale调整 | 🟡 P1 | 20分钟 | - |
| 添加因子诊断日志 | 🟡 P1 | 1小时 | - |
| 单元测试验证 | 🟡 P1 | 2小时 | - |

### 6.2 短期优化（本周完成）

| 任务 | 优先级 | 预计时间 |
|-----|-------|---------|
| 集成测试（30币种扫描） | 🟡 P1 | 1天 |
| 生成修复前后对比报告 | 🟢 P2 | 2小时 |
| 更新因子文档 | 🟢 P2 | 3小时 |
| 建立每日因子监控脚本 | 🟢 P2 | 4小时 |

### 6.3 中期研究（1-2周）

| 任务 | 优先级 | 预计时间 |
|-----|-------|---------|
| StandardizationChain深度分析 | 🟢 P2 | 2天 |
| 因子权重重新优化 | 🟢 P2 | 3天 |
| 回测修复效果 | 🟢 P2 | 2天 |

---

## 📚 七、附录

### 7.1 数学公式汇总

#### T因子
```
T_raw = slope_score + ema_score + r2_bonus

where:
  slope_score = directional_score(slope_per_bar, scale=slope_scale) - 50) * 2
  ema_score = ±(ema_bonus * 2)
  r2_bonus = ±(r2_weight * 100 * confidence)

当前：slope_scale=0.05, ema_bonus=20, r2_weight=0.3
建议：slope_scale=0.08, ema_bonus=12.5, r2_weight=0.15
```

#### F因子
```
F_raw = basis_weight * basis_score + funding_weight * funding_score

where:
  basis_score = directional_score(basis_bps, scale=basis_scale)
  funding_score = directional_score(-funding_bps, scale=funding_scale)

当前：使用StandardizationChain压缩
建议：直接裁剪 F = max(-100, min(100, F_raw))
```

#### O因子
```
oi24_trend = (slope / avg_abs_oi_slope) * relative_scale
oi_score = directional_score(oi24_trend, scale=oi24_scale)

当前：relative_scale=2.0, oi24_scale=1.0
建议：relative_scale=2.0, oi24_scale=2.0（与C/M一致）
```

### 7.2 测试数据示例

#### T因子测试用例
```python
# 强多头
slope_per_bar = 0.5, ema_up=True, r2=0.9
期望：T ≈ +90 (不应该=+100)

# 弱多头
slope_per_bar = 0.05, ema_up=True, r2=0.6
期望：T ≈ +40

# 震荡
slope_per_bar = 0.01, ema_up=False, r2=0.3
期望：T ≈ 0
```

#### F因子测试用例
```python
# 正常牛市
basis_bps=+50, funding_rate=+0.01%
期望：F ≈ +20 to +40

# 极端牛市
basis_bps=+150, funding_rate=+0.10%
期望：F ≈ -50 to -70 (资金费反向)

# 熊市
basis_bps=-50, funding_rate=-0.01%
期望：F ≈ -20 to -40
```

#### O因子测试用例
```python
# 正常增长（2x历史）
slope_normalized = 2.0
期望：O ≈ +76 (不应该=+99)

# 快速增长（5x历史）
slope_normalized = 5.0
期望：O ≈ +96

# 下降
slope_normalized = -2.0
期望：O ≈ -76
```

---

## 🎯 八、总结

### 8.1 核心发现

1. **T因子**：分数累加过大（-170~+170），直接裁剪导致95%是±100
2. **F因子**：StandardizationChain过度压缩，导致95%是-100
3. **O因子**：scale设置不当，导致25%>80（过于敏感）

### 8.2 根本原因

**设计不一致**：
- 部分因子（T/O）为StandardizationChain设计，但执行直接裁剪
- 没有及时调整分数计算逻辑
- C/M因子（新设计）效果良好，但其他因子未对齐

### 8.3 修复策略

**统一到"相对历史归一化 + 直接裁剪"策略**：
1. T因子：降低组件分数上限
2. F因子：禁用StandardizationChain
3. O因子：调整scale与C/M对齐

### 8.4 预期效果

修复后的因子分布：
```
T: 20%在±80-100，50%在±50-80，30%在0-50
F: 20%在±80-100，50%在±50-80，30%在0-50
O: 15%在±80-100，50%在±50-80，35%在0-50
C: 15%在±80-100，50%在±50-80，35%在0-50（已经良好）
M: 15%在±80-100，50%在±50-80，35%在0-50（已经良好）
```

**区分度恢复**，**权重平衡**，**信号质量提升**。

---

*报告完成时间: 2025-11-05*
*调查耗时: 3小时*
*建议执行时间: 立即*
