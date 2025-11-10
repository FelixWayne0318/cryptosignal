# 10因子分布异常诊断与修复

## 问题概述

用户报告10因子分布数据异常，经过诊断确认以下问题：

### 问题1：F因子极端双峰分布

**用户报告数据**：
```
F: Min=-100.0, P25=-100.0, 中位=-100.0, P75=100.0, Max=100.0
```

**当前扫描数据**：
```
F: Min=-100.0, P25=-96.0, 中位=56.0, P75=98.0, Max=100.0
```

**极端值统计**：
- 32.1%的币种F=±100（极端饱和值）
- 16.5%的币种F=-100
- 15.6%的币种F=100

**结论**：虽然当前数据比用户报告的好，但仍有32%的币种出现F因子饱和，这是不正常的。

### 问题2：I因子分布（已修复）

**用户报告数据**：
```
I: Min=0.0, P25=50.0, 中位=50.0, P75=50.0, Max=50.0
```

**当前扫描数据**：
```
I: Min=-96.0, P25=-24.0, 中位=-5.0, P75=16.0, Max=56.0
```

**结论**：I因子当前分布正常，可能之前的问题已被修复，或用户看的是旧数据。

---

## 根本原因分析

### F因子饱和原因

**代码位置**：`ats_core/features/fund_leading.py:349-355`

```python
# Line 349: F原始值（资金 - 价格）
F_raw = fund_momentum - price_momentum

# Line 352-353: 映射到±100（tanh平滑）
F_normalized = math.tanh(F_raw / p["scale"])  # scale=2.0
F_score = 100.0 * F_normalized
F_score = int(round(max(-100.0, min(100.0, F_score))))
```

**饱和机制**：
- tanh函数输出范围：(-1, +1)
- 当 `F_raw / scale` >> 3 时，tanh饱和到+1
- 当 `F_raw / scale` << -3 时，tanh饱和到-1
- 饱和点：`|F_raw| > 3 × scale = 3 × 2.0 = 6.0`

**问题**：当前`scale=2.0`过小，导致：
- 32.1%的币种`|F_raw| > 6.0`，造成tanh饱和
- F因子失去区分度，无法反映真实的资金领先性差异

**数学原理**：
```
tanh(x) = (e^x - e^-x) / (e^x + e^-x)

当x > 3时：tanh(x) ≈ 1 - 2e^(-2x) ≈ 1（误差<0.01）
当x < -3时：tanh(x) ≈ -1 + 2e^(2x) ≈ -1（误差<0.01）
```

所以当`F_raw/scale > 3`时，F_score会饱和到100。

**实际案例分析**：

从诊断工具输出看，F=-100和F=100的币种具有以下特征：
- `fund_momentum`和`price_momentum`差异极大
- `|F_raw| > 6.0`，导致`F_raw/2.0 > 3`
- tanh饱和

可能的底层原因：
1. **ATR归一化不当**：`atr_norm_factor`过小，导致归一化后的值过大
2. **CVD数据异常**：CVD变化过大
3. **OI数据异常**：OI变化过大
4. **scale参数过小**：无法适应市场真实波动

---

## 修复方案

### 方案1：调整F因子scale参数（推荐，P0）

**目标**：增大scale参数，减少tanh饱和，提高F因子区分度

**修改文件**：`config/factors_unified.json`

**修改前**：
```json
"F": {
  "v2": {
    "cvd_weight": 0.6,
    "oi_weight": 0.4,
    "window_hours": 6,
    "scale": 2.0
  }
}
```

**修改后**：
```json
"F": {
  "v2": {
    "cvd_weight": 0.6,
    "oi_weight": 0.4,
    "window_hours": 6,
    "scale": 5.0
  }
}
```

**效果预测**：
- 饱和点从`|F_raw| > 6.0`提升到`|F_raw| > 15.0`
- 32.1%的极端值预计降至5-10%
- F因子分布更加连续，区分度提升

**理论依据**：
- `scale=5.0`意味着tanh在`F_raw=±15`才饱和
- 给予更大的动态范围来反映资金领先性差异
- 保持tanh的S型曲线特性（对中等值非线性平滑）

---

### 方案2：监控F因子元数据（P1）

**目的**：持续监控F因子计算的中间值，及时发现异常

**诊断工具**：`scripts/diagnose_factor_anomalies.py`

**监控指标**：
- `F_raw`：原始F值，正常范围[-10, +10]
- `fund_momentum`：资金动量
- `price_momentum`：价格动量
- `atr_norm`：ATR归一化因子
- `cvd_6h_norm`：CVD 6小时变化（归一化）
- `oi_6h_pct`：OI 6小时变化百分比

**运行方法**：
```bash
cd ~/cryptosignal
python3 scripts/diagnose_factor_anomalies.py
```

**预期输出**：
- F因子分布统计
- 饱和案例分析（F=±100）
- 元数据诊断信息

---

### 方案3：检查数据质量（P2）

如果调整scale后仍有大量饱和，需要检查底层数据：

**检查项1：CVD数据**
```bash
# 检查CVD是否有异常跳变
# 位置：ats_core/data/cvd_compute.py
```

**检查项2：OI数据**
```bash
# 检查OI数据格式是否正确
# 位置：ats_core/features/fund_leading.py:312-336
```

**检查项3：ATR计算**
```bash
# 检查ATR是否过小
# 位置：ats_core/features/fund_leading.py:341
```

---

## 实施步骤

### Step 1：修改配置文件

```bash
cd ~/cryptosignal

# 备份当前配置
cp config/factors_unified.json config/factors_unified.json.backup

# 修改F.v2.scale: 2.0 → 5.0
# 使用编辑器或sed命令
```

**配置验证**：
```bash
python3 << 'EOF'
import json
with open('config/factors_unified.json') as f:
    config = json.load(f)
scale = config['F']['v2']['scale']
print(f"F.v2.scale = {scale}")
assert scale == 5.0, "配置未生效！"
print("✅ 配置修改成功")
EOF
```

### Step 2：重启系统

```bash
bash restart_system.sh
```

### Step 3：验证修复效果

等待一次扫描完成（约5分钟），然后运行诊断：

```bash
python3 scripts/diagnose_factor_anomalies.py
```

**预期结果**：
- F因子极端值（±100）比例从32.1%降至5-10%
- F因子分布更连续，P25/P50/P75不再极端
- I因子保持正常分布

### Step 4：监控后续运行

持续监控几个周期，确保修复稳定：

```bash
# 每隔1小时运行一次诊断
watch -n 3600 "python3 scripts/diagnose_factor_anomalies.py | grep '极端值'"
```

---

## 测试验证

### 验证方法1：统计分布

```bash
python3 << 'EOF'
import json
import numpy as np
from pathlib import Path

detail_file = Path('reports/latest/scan_detail.json')
with open(detail_file) as f:
    detail = json.load(f)

F_values = [s.get('F', 0) for s in detail['symbols']]
F_extreme = [v for v in F_values if abs(v) == 100]

print(f"F因子极端值比例: {len(F_extreme)/len(F_values)*100:.1f}%")
print(f"预期: < 10%")

if len(F_extreme) / len(F_values) < 0.1:
    print("✅ 修复成功")
else:
    print("❌ 仍需进一步调整")
EOF
```

### 验证方法2：可视化分布

```bash
python3 << 'EOF'
import json
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

detail_file = Path('reports/latest/scan_detail.json')
with open(detail_file) as f:
    detail = json.load(f)

F_values = [s.get('F', 0) for s in detail['symbols']]

plt.figure(figsize=(10, 6))
plt.hist(F_values, bins=50, edgecolor='black')
plt.xlabel('F Factor')
plt.ylabel('Frequency')
plt.title('F Factor Distribution (After Fix)')
plt.axvline(-100, color='r', linestyle='--', label='Saturation (-100)')
plt.axvline(100, color='r', linestyle='--', label='Saturation (+100)')
plt.legend()
plt.savefig('reports/F_factor_distribution.png')
print("✅ 分布图已保存到 reports/F_factor_distribution.png")
EOF
```

---

## 理论背景

### tanh函数特性

**公式**：
```
f(x) = tanh(x) = (e^x - e^-x) / (e^x + e^-x)
```

**特性**：
1. 输出范围：(-1, +1)
2. S型曲线：中间陡峭，两端平缓
3. 饱和性：|x| > 3时几乎饱和
4. 对称性：tanh(-x) = -tanh(x)

**scale参数的作用**：
- `scale=2.0`：在x=±6时饱和
- `scale=5.0`：在x=±15时饱和
- `scale=10.0`：在x=±30时饱和

**trade-off**：
- scale太小：容易饱和，区分度低
- scale太大：所有值映射到中间区域，失去tanh的非线性特性
- 最优值：根据实际数据分布调整，使95%的数据在[-3×scale, +3×scale]内

---

## 常见问题

### Q1: 为什么不直接用线性映射？

**A**: tanh的S型曲线有优势：
- 对极端值不敏感（鲁棒性）
- 中等值区分度高（非线性）
- 自动归一化到[-1, +1]

线性映射需要人工设定上下界，容易被异常值影响。

### Q2: scale=5.0是否会影响信号质量？

**A**: 不会，反而会提升：
- 提高F因子区分度
- 减少因饱和导致的信息丢失
- 更准确地反映资金领先性差异

### Q3: 如果scale=5.0后仍有饱和怎么办？

**A**: 继续增大scale或检查数据质量：
1. 尝试`scale=10.0`
2. 检查CVD和OI数据是否异常
3. 检查ATR计算是否合理
4. 考虑对F_raw做异常值过滤（winsorize）

### Q4: I因子为什么现在正常了？

**A**: 可能原因：
1. 之前的I因子计算逻辑已修复
2. BTC/ETH价格数据获取已修复
3. 用户看的是旧数据（在修复之前）

当前I因子依赖BTC/ETH数据，如果数据不足会降级为50。当前扫描显示I因子分布正常，说明BTC/ETH数据充足。

---

## 相关文档

- `ats_core/features/fund_leading.py` - F因子计算实现
- `ats_core/factors_v2/independence.py` - I因子计算实现
- `config/factors_unified.json` - 因子配置文件
- `scripts/diagnose_factor_anomalies.py` - 因子诊断工具
- `docs/SIGNAL_FILTERING_DIAGNOSIS.md` - 信号过滤诊断

---

## 修改历史

**2025-11-10**:
- 识别F因子饱和问题（32.1%极端值）
- 创建诊断工具`diagnose_factor_anomalies.py`
- 提出修复方案：scale 2.0 → 5.0
- 待实施和验证

**问题严重级别**: P0 (High) - 影响F因子质量和信号准确性
**修复状态**: 🔄 诊断完成，待实施修复
**负责人**: Claude (AI Assistant)
