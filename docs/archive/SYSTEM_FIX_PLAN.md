# CryptoSignal系统修复方案

> **诊断日期**: 2025-11-01
> **诊断人**: Claude (Session: review-system-overview)
> **系统版本**: v6.0

---

## 📊 问题总结

### 🔴 P0 - 架构缺陷（必须立即修复）

**问题**: I因子错误地放在A层（参与评分），而不是B层（调制器）

**影响**:
- 违反MODULATORS.md § 2.1规范："F/I只调制不评分"
- I既参与评分又调制，导致双重影响
- 权重配置与实际行为不一致

### 🟠 P1 - 信号稀缺（配置过严）

**问题**: 四门系统配置过于严格，导致几乎没有信号通过

**表现**:
- 偶尔检测到信号，但被四门截断
- Prime信号极其稀少
- 用户无法收到任何交易信号

**根因**:
1. Prime强度阈值过高（35分）
2. 执行门估算值偏大（无实时深度）
3. 防抖动机制过严（0.80概率+2/3确认+90s冷却）
4. DataQual门过严（0.90阈值）
5. 概率阈值叠加（0.62+0.80）

---

## 🔧 修复方案

### 修复1：I因子架构调整（P0）

#### 文件1: `ats_core/pipeline/analyze_symbol.py` (line 373-394)

**修改前**:
```python
base_weights = params.get("weights", {
    "T": 16.0, "M": 9.0, "S": 6.0, "V": 9.0,
    "C": 12.0, "O": 12.0,
    "L": 12.0, "B": 9.0, "Q": 7.0,
    "I": 8.0,  # ← 错误：I参与评分
    "E": 0,
})  # 总计: 100.0
```

**修改后**:
```python
base_weights = params.get("weights", {
    # Layer 1: 价格行为层（50%）
    "T": 18.0,  # +2.0 from I
    "M": 12.0,  #
    "S": 10.0,  # +4.0 from I
    "V": 10.0,  # +1.0 from I
    # Layer 2: 资金流层（30%）
    "C": 18.0,  #
    "O": 12.0,  #
    # Layer 3: 微观结构层（20%）
    "L": 12.0,  #
    "B": 4.0,   # -5.0 (重新平衡)
    "Q": 4.0,   # -3.0 (重新平衡)
    # B层调制器（不参与评分）
    "E": 0,     # 已废弃
    "I": 0,     # B层调制器
    "F": 0,     # B层调制器
})  # A层9因子总计: 100.0 ✓
```

#### 文件1: `ats_core/pipeline/analyze_symbol.py` (line 414-421)

**修改前**:
```python
scores = {
    "T": T, "M": M, "C": C, "S": S, "V": V, "O": O, "E": E,
    "L": L, "B": B, "Q": Q, "I": I,  # ← 错误：I在scores中
}
```

**修改后**:
```python
# v2.0合规：9维方向分数（F和I移至B层）
scores = {
    "T": T, "M": M, "C": C, "S": S, "V": V, "O": O,
    "L": L, "B": B, "Q": Q,
    # E废弃，F和I移至B层调制器
}
```

#### 文件1: `ats_core/pipeline/analyze_symbol.py` (line 430-434)

**修改前**:
```python
modulation = {
    "F": F,  # ← 缺少I
}
```

**修改后**:
```python
# v2.0合规：B层调制因子（F/I仅调节Teff/cost/thresholds）
modulation = {
    "F": F,  # Funding leading factor (拥挤度调制器)
    "I": I,  # Independence factor (独立性调制器)
}
```

#### 文件2: `config/params.json` (line 128-141)

**修改前**:
```json
"weights": {
  "T": 18.0, "M": 12.0, "C": 18.0, "S": 10.0, "V": 10.0, "O": 18.0,
  "L": 8.0, "B": 2.0, "Q": 4.0,
  "I": 0,  // ← 应完全移除或明确标记为B层
  "E": 0,
  "F": 0
}
```

**修改后**:
```json
"weights": {
  "_comment": "A层9因子权重（总和=100.0%），F/I为B层调制器",
  "T": 18.0,  // 趋势（价格行为层）
  "M": 12.0,  // 动量
  "S": 10.0,  // 结构
  "V": 10.0,  // 量能
  "C": 18.0,  // CVD资金流
  "O": 12.0,  // OI持仓量
  "L": 12.0,  // 流动性（微观结构层）
  "B": 4.0,   // 基差+资金费
  "Q": 4.0,   // 清算密度
  "E": 0,     // （废弃）
  "_b_layer_modulators": "以下因子不参与评分，仅用于调制",
  "F": 0,     // 资金领先（B层调制器）
  "I": 0      // 独立性（B层调制器）
}
```

---

### 修复2：降低Prime阈值（P1 - 增加信号）

#### 文件: `ats_core/pipeline/analyze_symbol.py` (line 591, 645)

**修改前**:
```python
is_prime = (prime_strength >= 35)  # 35分阈值过高
```

**修改后**:
```python
is_prime = (prime_strength >= 25)  # 降低到25分，提升信号量
```

**理由**:
- 当前35分需要confidence≥50且probability≥0.75
- 过于严格，导致信号极少
- 降低到25分：confidence≥35或probability≥0.70即可

---

### 修复3：放宽执行门阈值（P1）

#### 文件: `ats_core/execution/metrics_estimator.py` (line 322-337)

**修改前**:
```python
DEFAULT_THRESHOLDS = {
    "standard": {
        "impact_bps": 7.0,   # 过严
        "spread_bps": 35.0,  # 过严
        "obi_abs": 0.30,
    },
}
```

**修改后**:
```python
DEFAULT_THRESHOLDS = {
    "standard": {
        "impact_bps": 12.0,   # 放宽到12bps（估算偏大）
        "spread_bps": 50.0,   # 放宽到50bps
        "obi_abs": 0.40,      # 放宽到40%
    },
    "newcoin": {
        "impact_bps": 20.0,   # 新币更宽松
        "spread_bps": 80.0,
        "obi_abs": 0.50,
    }
}
```

**理由**:
- 当前使用估算值（无实时深度流），偏大2-3倍
- 放宽阈值补偿估算误差
- 等实现实时深度流后再收紧

---

### 修复4：放宽防抖动机制（P1）

#### 文件: `scripts/realtime_signal_scanner.py` (line 161-169)

**修改前**:
```python
self.anti_jitter = AntiJitter(
    prime_entry_threshold=0.80,      # 过严
    prime_maintain_threshold=0.70,
    confirmation_bars=2,
    total_bars=3,
    cooldown_seconds=90              # 过长
)
```

**修改后**:
```python
self.anti_jitter = AntiJitter(
    prime_entry_threshold=0.65,      # 降低到0.65（更现实）
    prime_maintain_threshold=0.58,   # 维持阈值
    confirmation_bars=1,             # 1/2确认即可（更快响应）
    total_bars=2,
    cooldown_seconds=60              # 60秒冷却（更快恢复）
)
```

**理由**:
- 0.80概率过高，配合prime_strength≥35几乎不可能达到
- 2/3确认太慢，市场机会稍纵即逝
- 90秒冷却期太长，错过后续机会

---

### 修复5：调整概率阈值配置（P1）

#### 文件: `config/params.json` (line 168-174)

**修改前**:
```json
"publish": {
  "prime_prob_min": 0.62,           // 过高
  "prime_dims_ok_min": 4,           // 过严
  "prime_dim_threshold": 35,        // 过高
  "watch_prob_min": 0.58,
  "watch_prob_max": 0.61
}
```

**修改后**:
```json
"publish": {
  "prime_prob_min": 0.55,           // 降低到55%（更现实）
  "prime_dims_ok_min": 3,           // 3个因子达标即可
  "prime_dim_threshold": 30,        // 因子阈值30分
  "watch_prob_min": 0.52,
  "watch_prob_max": 0.54
}
```

---

### 修复6：DataQual门优化（P1）

#### 方案A：临时禁用DataQual门（快速修复）

**文件**: `scripts/realtime_signal_scanner.py` (line 309-318)

在check_all_gates调用前添加：
```python
# 临时：DataQual门暂时放宽（无WebSocket实时流）
# TODO: 实现Combined Stream后恢复标准阈值
if True:  # 强制通过DataQual门
    gate_results["gate1_dataqual"] = GateResult(
        passed=True,
        gate_name="DataQual",
        value=1.0,
        threshold=0.90,
        details={"note": "临时放宽DataQual门（无实时流）"}
    )
```

#### 方案B：降低DataQual阈值（推荐）

**文件**: `ats_core/data/quality.py` (line 61-62)

**修改前**:
```python
ALLOW_PRIME_THRESHOLD = 0.90  # 90分
DEGRADE_THRESHOLD = 0.88
```

**修改后**:
```python
ALLOW_PRIME_THRESHOLD = 0.75  # 降低到75分（更宽容）
DEGRADE_THRESHOLD = 0.70
```

---

## 📋 实施步骤

### Step 1: 修复I因子架构（必须）

```bash
# 1. 修改analyze_symbol.py三处
vim ats_core/pipeline/analyze_symbol.py
# - line 373-394: 权重重新分配
# - line 414-421: scores移除I
# - line 430-434: modulation添加I

# 2. 修改params.json
vim config/params.json
# - line 128-141: 权重配置明确B层

# 3. 清除缓存
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# 4. 验证权重
python3 -c "
import json
w = json.load(open('config/params.json'))['weights']
a_layer = ['T','M','C','S','V','O','L','B','Q']
total = sum(w[k] for k in a_layer)
assert abs(total - 100.0) < 0.01, f'权重={total}'
assert w['F'] == 0 and w['I'] == 0, 'F/I必须为0'
print('✓ 权重配置正确')
"
```

### Step 2: 调整阈值（提升信号量）

选择以下任一方案：

**方案A: 保守调整（推荐开始）**
```bash
# 只修改params.json
vim config/params.json
# 修改：
# - prime_prob_min: 0.62 → 0.58
# - prime_dim_threshold: 35 → 30
# - prime_dims_ok_min: 4 → 3
```

**方案B: 激进调整（更多信号）**
```bash
# 修改所有5个文件（按修复2-6执行）
# 适合信号极度稀缺的情况
```

### Step 3: 测试验证

```bash
# 快速测试20个币种
python3 scripts/realtime_signal_scanner.py --max-symbols 20 --no-telegram

# 观察输出：
# - 有多少币种生成信号？
# - 有多少通过四门？
# - 哪个门失败最多？

# 完整测试140个币种
python3 scripts/realtime_signal_scanner.py --no-telegram
```

### Step 4: 灰度上线

```bash
# 1. 先在测试环境运行24小时
python3 scripts/realtime_signal_scanner.py --interval 300

# 2. 观察信号质量
# - 信号数量：每小时2-5个
# - Prime比例：>80%
# - 无明显误报

# 3. 正式上线（启用Telegram）
python3 scripts/realtime_signal_scanner.py --interval 300 # 默认启用Telegram
```

---

## 🎯 预期效果

### 修复前（当前状态）
```
扫描140个币种：
- 检测到信号：2-3个
- 通过四门：0-1个
- Prime信号：极少或无
- 用户体验：❌ 无信号可用
```

### 修复后（方案A保守）
```
扫描140个币种：
- 检测到信号：8-15个
- 通过四门：5-10个
- Prime信号：3-7个/小时
- 用户体验：✅ 可用但偏少
```

### 修复后（方案B激进）
```
扫描140个币种：
- 检测到信号：15-25个
- 通过四门：10-18个
- Prime信号：5-12个/小时
- 用户体验：✅✅ 信号充足
```

---

## ⚠️ 风险提示

1. **放宽阈值会增加假信号**：
   - 建议先用方案A测试3-7天
   - 根据实际胜率调整到方案B
   - 记录所有信号的胜率统计

2. **I因子架构修改影响评分**：
   - 移除I的8%权重重新分配到其他因子
   - 可能改变信号特征
   - 需要重新回测验证

3. **估算指标不如实时数据**：
   - 当前执行门使用估算值
   - 放宽阈值是临时方案
   - 最终需实现实时深度流

---

## 📊 监控指标

修复后需要监控：

```python
# 每日统计
{
  "扫描次数": 288,  # 每5分钟一次×24小时
  "信号总数": 150,
  "Prime信号": 80,
  "通过四门": 120,
  "四门失败分布": {
    "gate1_dataqual": 10,
    "gate2_ev": 5,
    "gate3_execution": 15,
    "gate4_probability": 20
  },
  "信号胜率": {
    "Prime": 0.65,   # 目标≥0.60
    "Watch": 0.55    # 目标≥0.52
  }
}
```

---

**版本**: v1.0
**生成时间**: 2025-11-01
**下次审查**: 7天后（根据信号质量）
