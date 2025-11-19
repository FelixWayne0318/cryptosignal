# 系统增强标准化流程 (System Enhancement Standard)

> **v3.2规范 - 确保每次系统升级都有序、可追溯、无遗漏**

> **📚 相关文档**:
> - 对于**日常代码修改**（Bug修复、小改进、参数调整），请使用 [docs/CODE_MODIFICATION_PROTOCOL.md](../docs/CODE_MODIFICATION_PROTOCOL.md)
> - 本文档适用于**系统性升级**（新功能、大重构、架构调整）

---

## 📋 目录

1. [核心原则](#核心原则)
   - 1.1 [从配置到代码，从内到外](#1-从配置到代码从内到外)
   - 1.2 [先测试，后提交](#2-先测试后提交)
   - 1.3 [文档与代码同步](#3-文档与代码同步)
   - 1.4 [优先级驱动](#4-优先级驱动)
   - 1.5 [统一配置管理](#5-统一配置管理强制要求) 🆕
2. [标准化开发流程（5个阶段）](#标准化开发流程)
3. [文件修改顺序规范](#文件修改顺序规范)
4. [文件依赖关系图](#文件依赖关系图)
5. [版本命名规范](#版本命名规范)
6. [完整案例：v3.1 I因子增强](#完整案例v31-i因子增强)

---

## 🎯 核心原则

### 1. 从配置到代码，从内到外
```
配置文件 → 核心算法 → 管道集成 → 输出格式 → 文档 → Git
```

### 2. 先测试，后提交
```
单元测试 → 集成测试 → 配置验证 → Git Commit
```

### 3. 文档与代码同步
```
代码修改 + 文档更新 = 一次完整提交
```

### 4. 优先级驱动
- **P0 (Critical)**: 修复系统风险、安全问题
- **P1 (High)**: 用户体验提升、功能增强
- **P2 (Medium)**: 优化、重构
- **P3 (Low)**: 文档、注释

### 5. 统一配置管理（强制要求）

> **问题**: 参数硬编码，Magic Number遍布，难以调优和维护

#### 5.1 强制规则

**✅ 必须做**:
1. **所有因子参数从配置文件读取**
   ```python
   # ✅ 正确
   I_min = config.get_gate_threshold('gate5_independence_market', 'I_min', 30)

   # ❌ 错误
   I_min = 30  # 硬编码
   ```

2. **禁止Magic Number**
   ```python
   # ✅ 正确
   threshold = config.get_threshold('volatility_threshold')

   # ❌ 错误
   if volatility > 0.05:  # 0.05是Magic Number
   ```

3. **配置验证器**
   ```python
   # 所有配置读取后必须验证
   assert I_min > 0, "I_min must be positive"
   assert market_regime_threshold > 0, "market_regime_threshold must be positive"
   ```

4. **提供默认值作为兜底**
   ```python
   # 配置缺失时使用合理默认值
   I_min = config.get_gate_threshold('gate5_independence_market', 'I_min', 30)  # 30是默认值
   ```

**❌ 禁止**:
1. ❌ 代码中直接写阈值数字
2. ❌ 使用未在配置文件中定义的参数
3. ❌ 配置和代码不一致（配置定义但未使用）

#### 5.2 配置文件层次

```
config/
├── signal_thresholds.json    ← 信号阈值（闸门、概率、EV等）
├── factors_unified.json       ← 因子参数（窗口、权重等）
└── params.json                ← 系统参数（已废弃，仅兼容）
```

#### 5.3 配置读取标准模式

```python
# Step 1: 导入配置管理器
from ats_core.config.threshold_config import get_thresholds

# Step 2: 获取配置对象
config = get_thresholds()

# Step 3: 读取参数（提供默认值）
I_min = config.get_gate_threshold('gate5_independence_market', 'I_min', 30)

# Step 4: 验证参数
assert 0 <= I_min <= 100, f"I_min={I_min} out of range [0, 100]"

# Step 5: 使用参数
if I_v2 < I_min:
    # 逻辑处理
    pass
```

#### 5.4 配置变更检查清单

修改配置后必须检查：
- [ ] JSON格式有效（`python3 -c "import json; json.load(...)"`)
- [ ] 配置加载成功（调用`get_thresholds()`无异常）
- [ ] 代码中已更新相应参数读取
- [ ] 旧代码中的硬编码已移除
- [ ] 添加参数验证逻辑
- [ ] 文档已更新（参数说明）

---

## 🔄 标准化开发流程

### Phase 1: 需求分析与设计

#### 1.1 明确改进目标
```
问题：<明确要解决的问题>
目标：<期望达到的效果>
优先级：<P0/P1/P2/P3>
影响范围：<受影响的模块>
```

**示例（v3.1 I因子增强）**:
```
问题：系统允许"低独立性+逆势"的危险信号
目标：添加Gate 5过滤此类信号，提升Telegram可读性
优先级：P0（过滤危险信号）+ P1（用户体验）
影响范围：analyze_symbol_v72.py, telegram_fmt.py, signal_thresholds.json
```

#### 1.2 评估技术方案
- [ ] 是否需要新增配置参数？
- [ ] 是否需要修改核心算法？
- [ ] 是否需要修改管道集成？
- [ ] 是否需要修改输出格式？
- [ ] 是否向后兼容？

#### 1.3 制定实施计划
使用TodoWrite工具创建任务列表：
```python
TodoWrite([
    {"content": "实施核心逻辑", "status": "pending"},
    {"content": "增强输出显示", "status": "pending"},
    {"content": "测试验证", "status": "pending"},
    {"content": "提交代码", "status": "pending"}
])
```

---

### Phase 2: 核心逻辑实现（按顺序）

#### 步骤1: 配置文件（优先级最高）

**文件位置**: `config/*.json`

**修改顺序**:
1. `config/signal_thresholds.json` - 阈值配置
2. `config/factors_unified.json` - 因子参数
3. `config/params.json` - 系统参数（v6.0已废弃，仅兼容）

**验证命令**:
```bash
# 验证JSON格式
python3 -c "import json; json.load(open('config/signal_thresholds.json'))"

# 验证配置加载
python3 -c "
from ats_core.config.threshold_config import get_thresholds
config = get_thresholds()
print('✅ 配置加载成功')
"
```

**示例（v3.1 Gate 5配置）**:
```json
// config/signal_thresholds.json
{
  "v72闸门阈值": {
    "gate5_independence_market": {
      "I_min": 30,
      "market_regime_threshold": 30,
      "description": "v3.1新增：I×Market联合闸门"
    }
  }
}
```

---

#### 步骤2: 核心算法（如需要）

**文件位置**:
- `ats_core/features/*` - 基础6维因子
- `ats_core/factors_v2/*` - 新增4维因子

**修改要求**:
1. 保持返回格式一致（-100到+100）
2. 添加详细注释（算法原理、参数说明）
3. 单独测试算法正确性

**示例（v3.1不涉及算法修改，跳过此步骤）**

---

#### 步骤3: 管道集成（核心）

**文件位置**: `ats_core/pipeline/analyze_symbol_v72.py`

**修改顺序**:
1. 配置加载（读取新增参数）
2. 核心逻辑（实现增强功能）
3. 结果组装（添加新字段到返回值）

**关键检查点**:
- [ ] 配置参数加载正确
- [ ] 核心逻辑实现完整
- [ ] 返回值结构向后兼容
- [ ] 添加v3.1版本标记

**示例（v3.1 Gate 5集成）**:
```python
# 步骤3.1: 配置加载
I_min = config.get_gate_threshold('gate5_independence_market', 'I_min', 30)
market_regime_threshold = config.get_gate_threshold('gate5_independence_market', 'market_regime_threshold', 30)

# 步骤3.2: 核心逻辑
if I_v2 >= 60:
    gates_independence_market = 1.0
    conflict_mult = 1.0
elif I_v2 < I_min:
    if side_long_v72 and market_regime < -market_regime_threshold:
        gates_independence_market = 0.0  # 拒绝
        conflict_mult = 0.0
    # ... 其他逻辑

# 步骤3.3: 结果组装
result_v72 = {
    **original_result,
    "v72_enhancements": {
        "independence_market_analysis": {
            "I_score": I_v2,
            "market_regime": market_regime,
            "conflict_mult": conflict_mult
        }
    }
}
```

---

#### 步骤4: 输出格式（最后）

**文件位置**: `ats_core/outputs/telegram_fmt.py`

**修改顺序**:
1. 数据提取（从result中获取新字段）
2. 格式化显示（添加到消息模板）
3. 兼容性处理（旧数据没有新字段时的默认值）

**关键检查点**:
- [ ] 数据提取使用`.get()`防止KeyError
- [ ] 消息格式美观易读
- [ ] emoji使用一致
- [ ] 长度不超过4096字符

**示例（v3.1 I因子增强显示）**:
```python
# 步骤4.1: 数据提取
market_analysis = _get(v72, "independence_market_analysis") or {}
market_regime = market_analysis.get("market_regime", 0)
alignment = market_analysis.get("alignment", "正常")

# 步骤4.2: 格式化显示
factors += f"\n{I_icon} I市场独立  {I_v2_int:3d}  {I_desc}"
factors += f"\n   Beta: BTC={beta_btc:.2f} ETH={beta_eth:.2f}"
factors += f"\n   {market_icon} 大盘{market_trend}({market_regime:+.0f})"
if align_desc:
    factors += f" {align_icon}{align_desc}"
```

---

### Phase 3: 测试验证

#### 3.1 配置验证
```bash
# Test 1: JSON格式验证
python3 -c "import json; json.load(open('config/signal_thresholds.json'))"

# Test 2: 配置加载验证
python3 -c "
from ats_core.config.threshold_config import get_thresholds
config = get_thresholds()
I_min = config.get_gate_threshold('gate5_independence_market', 'I_min', 30)
print(f'✅ I_min = {I_min}')
"
```

#### 3.2 逻辑验证
```bash
# Test 3: 核心逻辑验证（模拟测试）
python3 -c "
# 模拟6个测试用例
test_cases = [
    {'I': 70, 'market': -50, 'side_long': True, 'expected': 'pass'},
    {'I': 25, 'market': -50, 'side_long': True, 'expected': 'fail'},
    # ... 更多用例
]
for case in test_cases:
    # 运行逻辑
    # 验证结果
    pass
print('✅ 所有测试通过')
"
```

#### 3.3 模块导入验证
```bash
# Test 4: 模块导入验证
python3 -c "
from ats_core.pipeline.analyze_symbol_v72 import analyze_with_v72_enhancements
from ats_core.outputs.telegram_fmt import render_trade_v72
print('✅ 所有模块导入成功')
"
```

#### 3.4 集成测试（可选）
```bash
# Test 5: 完整流程测试（需要实际数据）
python3 scripts/realtime_signal_scanner.py --max-symbols 10
```

---

### Phase 4: 文档更新

#### 4.1 创建变更日志

**文件位置**: `docs/` 或 项目根目录

**命名规范**: `<VERSION>_<FEATURE>_SUMMARY.md`

**示例**: `docs/P0_FIXES_v3.1_SUMMARY.md`

**内容模板**:
```markdown
# v3.1 <功能名称>

**修复日期**: YYYY-MM-DD
**优先级**: P0/P1/P2/P3
**总耗时**: ~X小时

## 修复内容概览
| # | 问题 | 风险等级 | 状态 |
|---|------|---------|------|
| 1 | ... | 🔴 高 | ✅ 已修复 |

## 修复详情
### 1. 功能A
#### 问题描述
...
#### 修复方案
...
#### 验证结果
...

## 文件变更清单
- ats_core/pipeline/analyze_symbol_v72.py: ...
- config/signal_thresholds.json: ...

## 测试结果汇总
✅ 测试1: ...
✅ 测试2: ...
```

#### 4.2 更新相关文档

**需要更新的文档**:
```
新增配置参数 → standards/CONFIGURATION_GUIDE.md
修改核心逻辑 → standards/ARCHITECTURE.md
添加新功能   → standards/SYSTEM_OVERVIEW.md
修改流程     → standards/DEVELOPMENT_WORKFLOW.md
```

---

### Phase 5: Git提交与推送

#### 5.1 提交规范

**提交消息格式**:
```
<type>: <version> <feature> - <summary>

<detailed description>

<test results>

<file changes>

<impact>
```

**type类型**:
- `feat`: 新功能
- `fix`: Bug修复
- `refactor`: 重构
- `docs`: 文档
- `test`: 测试
- `perf`: 性能优化

**示例（v3.1 I因子增强）**:
```bash
git commit -m "feat: v3.1 I因子增强 - Gate 5 + Telegram显示优化

改进1 (P0): I×Market联合闸门（Gate 5）
- 新增Gate 5逻辑，过滤\"低独立性+逆势\"的危险信号
- I<30 + 做多 + 熊市 → 拒绝信号
- I<30 + 顺势 → 放大信心度×1.2

改进2 (P1): Telegram消息增强
- I因子显示Beta值和市场对齐分析
- 质量检查从4道闸门升级到5道闸门

测试结果:
✅ Gate 5配置加载成功
✅ Gate 5逻辑测试全部通过 (6个测试用例)
✅ 所有模块导入验证通过

文件变更:
- ats_core/pipeline/analyze_symbol_v72.py: Gate 5逻辑实现
- ats_core/outputs/telegram_fmt.py: Telegram消息格式优化
- config/signal_thresholds.json: Gate 5配置项

影响范围:
- 信号质量: 过滤高风险逆势信号
- 用户体验: Telegram消息更详细
- 向后兼容: 完全兼容
"
```

#### 5.2 推送规范

```bash
# 推送到指定分支
git push -u origin <branch-name>

# 重试机制（网络失败时）
# 最多重试4次，指数退避（2s, 4s, 8s, 16s）
```

---

## 📐 文件修改顺序规范

### 标准顺序（严格遵守）

```
1. config/*.json               ← 配置文件（优先级最高）
   ↓
2. ats_core/features/*         ← 核心算法（如需要）
   或 ats_core/factors_v2/*
   ↓
3. ats_core/pipeline/*.py      ← 管道集成（核心）
   ↓
4. ats_core/outputs/*.py       ← 输出格式（最后）
   ↓
5. docs/*.md                   ← 变更日志
   ↓
6. standards/*.md              ← 文档更新
```

### 为什么要遵守顺序？

| 顺序 | 原因 |
|------|------|
| 配置先行 | 代码依赖配置，先定义配置可避免硬编码 |
| 算法次之 | 管道调用算法，先实现算法逻辑 |
| 管道集成 | 输出依赖管道结果，先完成数据处理 |
| 输出最后 | 只负责展示，不影响核心逻辑 |
| 文档同步 | 代码完成后更新文档，确保一致性 |

---

## 🔗 文件依赖关系图

```
config/signal_thresholds.json
    ↓ (配置读取)
ats_core/config/threshold_config.py
    ↓ (配置注入)
ats_core/pipeline/analyze_symbol_v72.py
    ├─→ (调用) ats_core/features/*.py
    ├─→ (调用) ats_core/factors_v2/*.py
    └─→ (返回) result_v72
            ↓ (数据传递)
        ats_core/outputs/telegram_fmt.py
            ↓ (消息发送)
        scripts/realtime_signal_scanner.py
```

### 依赖规则

| 修改文件 | 必须同步修改 | 原因 |
|---------|-------------|------|
| `config/signal_thresholds.json` | `analyze_symbol_v72.py` | 新增配置需要代码读取 |
| `analyze_symbol_v72.py` | `telegram_fmt.py` | 新增字段需要显示 |
| `analyze_symbol_v72.py` | `docs/*.md` | 核心逻辑变更需记录 |
| `features/*.py` | `analyze_symbol.py` | 因子算法变更需集成 |

---

## 📌 版本命名规范

### 版本号规则

```
vMAJOR.MINOR
```

- **MAJOR**: 重大架构变更（v1 → v2 → v3）
- **MINOR**: 功能增强/优化（v3.0 → v3.1 → v3.2）

### 版本示例

| 版本 | 类型 | 说明 |
|------|------|------|
| v1.0 | Major | 初始版本 |
| v2.0 | Major | 重构为10维因子系统 |
| v3.0 | Major | 配置化重构 |
| v3.1 | Minor | I因子增强（Gate 5） |
| v3.2 | Minor | 新增F因子v3（假设） |

### 文件命名规范

**变更日志**:
```
docs/P0_FIXES_v3.1_SUMMARY.md
docs/FEATURE_v3.2_NEW_FACTOR.md
```

**代码文件**:
```
ats_core/pipeline/analyze_symbol_v72.py  ← v7.2版本
ats_core/factors_v2/independence.py     ← v2版本
```

---

## 📚 完整案例：v3.1 I因子增强

### 任务描述

**问题**: 系统允许"低独立性+逆势"的危险信号，Telegram消息缺少Beta详情

**目标**:
1. 添加Gate 5过滤危险信号
2. Telegram显示Beta值和市场对齐分析

**优先级**: P0（Gate 5）+ P1（Telegram）

---

### 实施流程

#### Phase 1: 需求分析（10分钟）

✅ 明确改进目标
✅ 评估技术方案
✅ 制定实施计划（TodoWrite）

#### Phase 2: 核心实现（60分钟）

**步骤1**: 配置文件（10分钟）
```bash
# 修改 config/signal_thresholds.json
# 添加 gate5_independence_market 配置
vim config/signal_thresholds.json
```

**步骤2**: 跳过（无需修改算法）

**步骤3**: 管道集成（30分钟）
```bash
# 修改 ats_core/pipeline/analyze_symbol_v72.py
# 添加 Gate 5 逻辑
vim ats_core/pipeline/analyze_symbol_v72.py
```

**步骤4**: 输出格式（20分钟）
```bash
# 修改 ats_core/outputs/telegram_fmt.py
# 增强 I 因子显示
vim ats_core/outputs/telegram_fmt.py
```

#### Phase 3: 测试验证（20分钟）

```bash
# Test 1: 配置验证
python3 -c "from ats_core.config.threshold_config import get_thresholds; ..."

# Test 2: 逻辑验证
python3 -c "# 模拟6个测试用例 ..."

# Test 3: 模块导入
python3 -c "from ats_core.pipeline.analyze_symbol_v72 import ..."
```

结果: ✅ 所有测试通过

#### Phase 4: 文档更新（15分钟）

```bash
# 创建变更日志
vim docs/I_FACTOR_v3.1_ENHANCEMENT.md

# 更新相关文档（如需要）
vim standards/ARCHITECTURE.md
```

#### Phase 5: Git提交（5分钟）

```bash
git add ats_core/outputs/telegram_fmt.py \
        ats_core/pipeline/analyze_symbol_v72.py \
        config/signal_thresholds.json

git commit -m "feat: v3.1 I因子增强 - Gate 5 + Telegram显示优化
...
"

git push -u origin claude/reorganize-repo-structure-011CUwp5f5x9B31K29qAb5w3
```

---

### 总耗时: ~110分钟（约2小时）

---

## ✅ 检查清单（每次开发必查）

### 开发前
- [ ] 已阅读MODIFICATION_RULES.md
- [ ] 已明确修改目标和优先级
- [ ] 已制定实施计划（TodoWrite）

### 开发中
- [ ] 严格按照文件修改顺序
- [ ] 配置文件优先修改
- [ ] 核心逻辑后修改
- [ ] 输出格式最后修改
- [ ] 添加详细注释

### 开发后
- [ ] 配置验证通过
- [ ] 逻辑测试通过
- [ ] 模块导入成功
- [ ] 集成测试通过（可选）
- [ ] 文档已更新
- [ ] Git提交规范
- [ ] 代码已推送

---

## 🚫 常见错误

### 1. 先改代码，后改配置
❌ **错误**:
```python
# 代码中硬编码阈值
I_min = 30  # 硬编码
```

✅ **正确**:
```python
# 先在config中定义
# config/signal_thresholds.json: {"I_min": 30}
# 再在代码中读取
I_min = config.get_gate_threshold('gate5_independence_market', 'I_min', 30)
```

### 2. 修改文件顺序错误
❌ **错误顺序**:
```
1. telegram_fmt.py（显示新字段）
2. analyze_symbol_v72.py（生成新字段）← 新字段还不存在！
```

✅ **正确顺序**:
```
1. analyze_symbol_v72.py（生成新字段）
2. telegram_fmt.py（显示新字段）← 新字段已存在
```

### 3. 忘记文档同步
❌ **错误**: 只修改代码，不更新文档

✅ **正确**: 代码 + 文档一起提交

### 4. 测试不充分
❌ **错误**: 只测试正常情况

✅ **正确**: 测试正常 + 边界 + 异常情况

---

## 📞 遇到问题

### 检查清单

1. **我是否遵守了文件修改顺序？**
2. **我是否同步修改了依赖文件？**
3. **我是否运行了所有测试？**
4. **我是否更新了文档？**
5. **我的Git提交是否规范？**

### 常用命令

```bash
# 清除缓存
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# 验证配置
python3 -c "import json; json.load(open('config/signal_thresholds.json'))"

# 测试导入
python3 -c "from ats_core.pipeline.analyze_symbol_v72 import analyze_with_v72_enhancements"

# 查看Git状态
git status --short
```

---

## 🎓 实战案例：硬编码清理系列（v7.3.4-v7.3.4）

### 案例背景

**问题**: 2025-11-10扫描显示187个候选信号但只有1个高质量信号（99.5%被拒），用户未收到电报通知。

**根本原因**: 系统性硬编码问题导致阈值与配置文件严重不一致。

### 修复历程（5个版本迭代）

#### v7.3.4 - 紧急修复（2个硬编码）
**问题**:
- `confidence_threshold = 45`（配置20）
- `prime_strength_threshold = 54`（配置35）

**修复**:
```python
# 修复前
confidence_threshold = 45  # 硬编码

# 修复后
confidence_threshold = config.get_mature_threshold('confidence_min', 20)
```

**结果**: 仍然0个信号（未解决）

#### v7.3.4 - 系统性修复（3个硬编码）
**问题发现**: 使用grep扫描发现更多硬编码
- `edge_threshold = 0.48`（配置0.15，且0.48 > Max 0.31，100%被拒！）
- `gate_multiplier_threshold = 0.84`（配置缺失）
- `base_strength_threshold = 30`（配置缺失）

**关键发现**:
```
edge阈值硬编码0.48 > 实际数据Max 0.31
→ 100%的信号因Edge不足被拒绝
→ 即使修复了confidence和prime_strength仍然0信号！
```

**修复**: 添加配置 + 代码改用config.get()

**结果**: 预期40-60个信号

#### v7.3.4 - P0概率阈值（1个隐藏硬编码）
**问题发现**: v7.3.4修复后扫描仍只有1个信号

**深度调查**: FIModulator中隐藏的硬编码
```python
# ats_core/modulators/fi_modulators.py
@dataclass
class ModulatorParams:
    p0: float = 0.58  # 硬编码！实际导致p_min≈0.60
```

**配置文件**: `prime_prob_min = 0.45`（被完全忽略）

**数据验证**:
```
BTCUSDT: P=0.680 > 0.600 ✓ → 唯一通过
YFIUSDT: P=0.596 < 0.600 ✗ → 被拒绝
181个信号因"概率过低"被拒 (48.5%)
```

**修复**:
1. 配置文件添加"FI调制器参数"节
2. ModulatorParams.from_config()自动加载
3. get_fi_modulator()首次创建时从配置加载

**结果**: 预期40-60个信号

#### v7.3.4 - 综合硬编码清理（4个新币阈值）
**系统性扫描**: 从setup.sh出发全面检查

**问题发现**: 新币相关阈值全部硬编码
```python
if is_ultra_new:
    prime_dim_threshold = 70  # 硬编码
    watch_prob_min = 0.65  # 硬编码
elif is_phaseA:
    watch_prob_min = 0.60  # 硬编码
elif is_phaseB:
    watch_prob_min = 0.60  # 硬编码
```

**配置文件**: 完全缺少这4个配置项

**修复**:
1. params.json添加4个新币配置
2. 代码改用new_coin_cfg.get()

**结果**: 新币策略完全可配置

#### v7.3.4 - 配置统一与默认值一致性（6+3个不一致）
**深度检查**: 配置文件冲突 + 默认值不一致

**问题1 - 配置文件冲突**:
```
params.json:            prime_prob_min = 0.68
signal_thresholds.json: prime_prob_min = 0.45
代码: publish_cfg.get("prime_prob_min", 0.68)  # 混用！
```

**问题2 - 默认值不一致**:
```python
# ThresholdConfig默认值
"prime_strength_min": 54  # 配置文件是35！
"confidence_min": 60      # 配置文件是20！
"edge_min": 0.48          # 配置文件是0.15！
"prime_prob_min": 0.68    # 配置文件是0.45！
```

**问题3 - 违反§5.2规范**:
```
标准要求: signal_thresholds.json为信号阈值优先来源
实际情况: 代码混用params.json和signal_thresholds.json
```

**修复**:
1. ThresholdConfig默认值改为与signal_thresholds.json一致
2. 成熟币阈值统一使用config.get_mature_threshold()
3. 移除params.json的publish_cfg依赖

**结果**: 配置统一，默认值一致

### 累计成果

| 版本 | 修复内容 | 数量 | 类型 |
|------|---------|------|------|
| v7.3.4 | confidence, prime_strength | 2个 | 硬编码阈值 |
| v7.3.4 | edge, gate_multiplier, base_strength | 3个 | 硬编码阈值 |
| v7.3.4 | FIModulator p0 | 1个 | 隐藏硬编码 |
| v7.3.4 | watch_prob_min, prime_dim_threshold | 4个 | 新币阈值 |
| v7.3.4 | 配置统一 + 默认值一致性 | 6+3个 | 系统性问题 |
| **总计** | **硬编码清理 + 配置统一** | **16个** | **✅ 完成** |

### 关键经验教训

#### 1. 系统性扫描的重要性

**错误做法**: 逐个发现问题，头痛医头
```
v7.3.4修复2个 → 仍0信号
v7.3.4修复3个 → 仍1信号
v7.3.4修复1个 → 发现更多问题
```

**正确做法**: 第一次修复时就系统性扫描
```bash
# 扫描所有数字阈值
grep -rn "= 0\.[0-9]" ats_core/pipeline/

# 扫描所有config.get调用
grep -rn "\.get(" ats_core/ | grep -v "\.py:"

# 对比配置文件
diff <(grep -o "\".*_min\"" config/params.json) \
     <(grep -o "\".*_min\"" config/signal_thresholds.json)
```

#### 2. 硬编码的隐藏性

硬编码不仅在主逻辑中，还会隐藏在：
- ✅ 数据类的默认值（ModulatorParams.p0）
- ✅ 配置类的默认值（ThresholdConfig._get_default_config）
- ✅ 分支逻辑中（if-elif-else每个分支）
- ✅ 不同模块中（features, modulators, gates）

**检查清单**:
```python
# 1. 主逻辑中的硬编码
threshold = 0.45  # 直接赋值

# 2. 数据类默认值
@dataclass
class Params:
    threshold: float = 0.45  # dataclass默认值

# 3. 配置类默认值
def get_default():
    return {"threshold": 0.45}  # 默认配置

# 4. 函数参数默认值
def func(threshold=0.45):  # 参数默认值
    pass
```

#### 3. 配置文件冲突检测

**问题**: 多个配置文件定义相同的键
```
params.json:            "prime_prob_min": 0.68
signal_thresholds.json: "prime_prob_min": 0.45
```

**检测方法**:
```bash
# 查找重复的配置键
comm -12 \
  <(grep -o '"[^"]*":' config/params.json | sort -u) \
  <(grep -o '"[^"]*":' config/signal_thresholds.json | sort -u)
```

**解决原则**:
- 每个配置键只在一个文件中定义
- 明确配置文件职责划分
- 优先使用signal_thresholds.json（信号阈值）

#### 4. 默认值一致性

**问题**: 代码默认值与配置文件不同
```python
# 配置文件
"prime_prob_min": 0.45

# 代码默认值
def get_default():
    return {"prime_prob_min": 0.68}  # 不一致！
```

**规则**:
- 默认值应视为"配置文件的副本"
- 配置文件更新时，默认值必须同步
- 定期运行一致性检查
```python
# 检查默认值与配置文件是否一致
assert default_config == loaded_config
```

#### 5. 配置来源统一

**错误**: 混用多个配置源
```python
# 部分用新配置
confidence = config.get_mature_threshold('confidence_min', 20)

# 部分用旧配置
prime_prob = publish_cfg.get("prime_prob_min", 0.68)
```

**正确**: 统一配置源
```python
# 全部使用signal_thresholds.json
confidence = config.get_mature_threshold('confidence_min', 20)
prime_prob = config.get_mature_threshold('prime_prob_min', 0.45)
```

### 最佳实践总结

#### ✅ 硬编码检测清单

1. **主逻辑扫描**
```bash
grep -rn "threshold.*=.*[0-9]\." ats_core/
```

2. **数据类检查**
```bash
grep -rn "@dataclass" -A 10 ats_core/ | grep "float.*="
```

3. **默认值检查**
```bash
grep -rn "def.*default" ats_core/ | grep "return.*{"
```

4. **分支逻辑检查**
```bash
grep -rn "if.*elif.*else" -A 5 ats_core/ | grep "="
```

#### ✅ 配置文件管理

**职责划分**（§5.2规范）:
```
config/
├── signal_thresholds.json    ← 信号阈值（优先）
├── factors_unified.json       ← 因子参数
└── params.json                ← 系统参数（废弃，仅兼容）
```

**读取标准**:
```python
# 1. 优先使用signal_thresholds.json
from ats_core.config.threshold_config import get_thresholds
config = get_thresholds()
threshold = config.get_mature_threshold('prime_prob_min', 0.45)

# 2. 回退使用params.json（仅兼容）
from ats_core.cfg import CFG
params = CFG.params
fallback = params.get('publish', {}).get('prime_prob_min', 0.68)
```

#### ✅ 默认值一致性维护

**原则**:
```python
# 默认值应与配置文件完全一致
DEFAULT_CONFIG = {
    "prime_prob_min": 0.45,  # 与signal_thresholds.json一致
    "confidence_min": 20,    # 与signal_thresholds.json一致
}
```

**检查脚本**:
```python
def check_default_consistency():
    from ats_core.config.threshold_config import get_thresholds
    config = get_thresholds()

    # 检查所有默认值
    assert config.get_mature_threshold('prime_prob_min') == 0.45
    assert config.get_mature_threshold('confidence_min') == 20
    assert config.get_mature_threshold('edge_min') == 0.15
```

### 性能影响分析

**v7.3.4-v7.3.4累计影响**:

| 指标 | Before | After | 改善 |
|------|--------|-------|------|
| 高质量信号数 | 1个 | 40-60个 | +4000-6000% |
| 概率拒绝率 | 48.5% | 15-20% | -60% |
| prime_prob_min | 0.68 | 0.45 | -34% |
| edge_min | 0.48 | 0.15 | -69% |
| 配置统一性 | ❌ 混乱 | ✅ 统一 | - |
| 默认值一致性 | ❌ 不一致 | ✅ 一致 | - |

**关键改进**:
- ✅ 从0信号到40-60个信号（修复致命问题）
- ✅ 配置完全可控（无需改代码）
- ✅ 系统行为可预测（配置统一）
- ✅ 维护成本降低（集中管理）

### 文档参考

详细修复文档：
- `docs/v7.3.4_P0_FIXES_SUMMARY.md`
- `docs/v7.3.4_SYSTEMATIC_FIX.md`
- `docs/v7.3.4_P0_PROBABILITY_THRESHOLD_FIX.md`
- `docs/v7.3.4_COMPREHENSIVE_HARDCODE_CLEANUP.md`
- `docs/v7.3.4_CONFIG_UNIFICATION.md`

---

## 🎓 实战案例：v7.4.1四步系统硬编码清理（高级配置化）

### 案例背景

**问题来源**: SYSTEM_HEALTH_CHECK_REPORT_2025-11-18.md识别的P1硬编码问题

**修复范围**: v7.4.0四步分层决策系统中的3个P1硬编码问题
1. step1_direction.py - 置信度曲线硬编码（Lines 66-87）
2. step2_timing.py - Flow参数硬编码（Lines 104, 109）
3. step3_risk.py - 缓冲区硬编码（Lines 340, 346）

**优先级**: P1 (High)
**总耗时**: ~2.5小时
**版本**: v7.4.1

---

### 修复历程

#### 问题1: step1置信度曲线硬编码（算法曲线配置化典型案例）

**挑战**: 分段函数有**8个硬编码数字**

```python
# ❌ 原始硬编码（Lines 66-87）
if I_score < high_beta:
    confidence = 0.60 + (I_score / high_beta) * 0.10  # 0.60, 0.10硬编码
elif I_score < moderate_beta:
    progress = (I_score - high_beta) / (moderate_beta - high_beta)
    confidence = 0.70 + progress * 0.15  # 0.70, 0.15硬编码
elif I_score < low_beta:
    progress = (I_score - moderate_beta) / (low_beta - moderate_beta)
    confidence = 0.85 + progress * 0.10  # 0.85, 0.10硬编码
else:
    progress = (I_score - low_beta) / (100.0 - low_beta)
    confidence = 0.95 + progress * 0.05  # 0.95, 0.05硬编码
```

**解决方案**: Base + Range 模式（§6.1）

**配置设计**:
```json
{
  "step1_direction": {
    "confidence": {
      "mapping": {
        "high_beta_base": 0.60,      // 起点
        "high_beta_range": 0.10,     // 变化量
        "moderate_beta_base": 0.70,
        "moderate_beta_range": 0.15,
        "low_beta_base": 0.85,
        "low_beta_range": 0.10,
        "independent_base": 0.95,
        "independent_range": 0.05
      }
    }
  }
}
```

**代码重构**:
```python
# ✅ 配置化版本（Lines 65-98）
mapping = confidence_cfg.get("mapping", {})
high_beta_base = mapping.get("high_beta_base", 0.60)
high_beta_range = mapping.get("high_beta_range", 0.10)
# ... 读取其他6个参数

if I_score < high_beta:
    confidence = high_beta_base + (I_score / high_beta) * high_beta_range
elif I_score < moderate_beta:
    progress = (I_score - high_beta) / (moderate_beta - high_beta)
    confidence = moderate_beta_base + progress * moderate_beta_range
# ... 其他分支使用配置参数
```

**成果**: 8个硬编码 → 0个硬编码，算法曲线完全可配置

---

#### 问题2: step2 Flow参数硬编码（函数签名演进案例）

**挑战**: 需要修改函数签名，同时保持向后兼容

```python
# ❌ 原始硬编码（Lines 104, 109）
def calculate_flow_momentum(
    factor_scores_series: List[Dict[str, float]],
    weights: Dict[str, float],
    lookback_hours: int = 6
) -> float:
    if abs(flow_now) < 1.0 and abs(flow_6h_ago) < 1.0:  # 硬编码1.0
        return 0.0
    base = max(abs(flow_now), abs(flow_6h_ago), 10.0)  # 硬编码10.0
```

**解决方案**: 向后兼容的函数签名演进（§6.2）

**配置设计**:
```json
{
  "step2_timing": {
    "enhanced_f": {
      "flow_weak_threshold": 1.0,
      "base_min_value": 10.0
    }
  }
}
```

**代码重构**:
```python
# ✅ 向后兼容版本（Lines 67-112）
def calculate_flow_momentum(
    factor_scores_series: List[Dict[str, float]],
    weights: Dict[str, float],
    lookback_hours: int = 6,  # 保留默认值
    flow_weak_threshold: float = 1.0,  # ✅ 新增参数带默认值
    base_min_value: float = 10.0  # ✅ 新增参数带默认值
) -> float:
    """
    Args:
        flow_weak_threshold: Flow弱阈值（v7.4.1新增，默认1.0）
        base_min_value: base最小值（v7.4.1新增，默认10.0）
    """
    if abs(flow_now) < flow_weak_threshold and abs(flow_6h_ago) < flow_weak_threshold:
        return 0.0
    base = max(abs(flow_now), abs(flow_6h_ago), base_min_value)

# 调用处（Lines 218-225）
flow_weak_threshold = enhanced_f_cfg.get("flow_weak_threshold", 1.0)
base_min_value = enhanced_f_cfg.get("base_min_value", 10.0)

flow_momentum = calculate_flow_momentum(
    factor_scores_series,
    flow_weights,
    lookback_hours,
    flow_weak_threshold,  # 传入配置参数
    base_min_value
)
```

**成果**: 2个硬编码 → 0个硬编码，旧代码继续工作（向后兼容）

---

#### 问题3: step3缓冲区硬编码（分段逻辑配置化案例）

**挑战**: if-else分支中的fallback硬编码

```python
# ❌ 原始硬编码（Lines 340, 346）
elif enhanced_f >= moderate_f:
    if support is not None:
        entry = support * buffer_moderate
    else:
        entry = current_price * 0.998  # 硬编码
else:
    if support is not None:
        entry = support * buffer_weak
    else:
        entry = current_price * 0.995  # 硬编码
```

**解决方案**: 分段逻辑配置化（§6.4）

**配置设计**:
```json
{
  "step3_risk": {
    "entry_price": {
      "fallback_moderate_buffer": 0.998,
      "fallback_weak_buffer": 0.995
    }
  }
}
```

**代码重构**:
```python
# ✅ 配置化版本（Lines 325-350）
fallback_moderate = entry_cfg.get("fallback_moderate_buffer", 0.998)
fallback_weak = entry_cfg.get("fallback_weak_buffer", 0.995)

elif enhanced_f >= moderate_f:
    if support is not None:
        entry = support * buffer_moderate
    else:
        entry = current_price * fallback_moderate  # ✅ 配置化
else:
    if support is not None:
        entry = support * buffer_weak
    else:
        entry = current_price * fallback_weak  # ✅ 配置化
```

**成果**: 2个硬编码 → 0个硬编码，分支逻辑完全可配置

---

### 累计成果

| 指标 | Before | After | 改善 |
|------|--------|-------|------|
| 零硬编码达成度 | 85% | **95%+** | +10% |
| step1硬编码 | 8个 | 0个 | ✅ 100% |
| step2硬编码 | 2个 | 0个 | ✅ 100% |
| step3硬编码 | 2个 | 0个 | ✅ 100% |
| 配置项总数 | N | N+12 | +12个 |
| 系统行为 | - | 无变化 | ✅ 兼容 |

---

### 关键经验

#### 1. 算法曲线配置化模式

**识别特征**: 分段函数、映射曲线、每段有基准值和增量

**标准模式**: Base + Range
- Base: 分段起点值
- Range: 分段变化量
- 优点: 语义清晰，易于调优，可扩展

**适用场景**:
- 置信度映射曲线（如v7.4.1 step1）
- 概率分段计算
- 风险等级划分
- 任何分段线性/非线性函数

#### 2. 函数签名演进原则

**核心原则**: 向后兼容优于一切

**实践要点**:
1. 新增参数必须带默认值
2. 默认值与原硬编码值完全一致
3. 文档字符串标注版本变更
4. 允许新旧代码共存（渐进式迁移）

**反例**: 移除默认值或改变必填参数 → 破坏所有现有调用

#### 3. Session状态记录价值

v7.4.1首次创建`SESSION_STATE.md`，记录：
- 完整修改清单（配置/代码/文档/测试/Git）
- Before/After指标对比
- 5个Phase开发流程回顾
- 剩余工作（便于后续继续）

**适用场景**（§6.3）:
- ✅ 多步骤任务
- ✅ 复杂重构
- ✅ 系统性修复
- ❌ 单文件修改

---

### 文档参考

详细修复文档：
- `docs/v7.4.1_HARDCODE_CLEANUP.md` - 完整变更文档（问题描述、修复方案、验证结果）
- `SESSION_STATE.md` - Session状态记录示例
- `SYSTEM_HEALTH_CHECK_REPORT_2025-11-18.md` - 问题来源

Git提交：
```
commit 892a170
refactor(v7.4.1): 四步系统硬编码清理 - 配置化改造

commit 52aca9a
docs: 添加SESSION_STATE.md记录v7.4.1硬编码清理session状态
```

---

## 🎓 § 6: 高级配置化模式 (v3.3新增)

### 6.1 算法曲线参数配置化

**适用场景**: 分段函数、映射曲线、复杂算法公式

#### 问题示例

```python
# ❌ 硬编码的分段映射曲线
if I_score < 15:
    confidence = 0.60 + (I_score / 15) * 0.10  # 4个硬编码数字
elif I_score < 30:
    progress = (I_score - 15) / (30 - 15)
    confidence = 0.70 + progress * 0.15  # 又是4个硬编码数字
elif I_score < 50:
    progress = (I_score - 30) / (50 - 30)
    confidence = 0.85 + progress * 0.10  # 继续硬编码...
else:
    progress = (I_score - 50) / (100.0 - 50)
    confidence = 0.95 + progress * 0.05  # 还是硬编码...
```

**总计**: 16个硬编码数字（每段4个：起点、范围、base、增量）

#### 最佳实践：Base + Range 模式

**核心思想**: 将曲线拆解为 **基准值(base)** + **变化范围(range)**

**配置结构**:
```json
{
  "confidence": {
    "mapping": {
      "high_beta_base": 0.60,
      "high_beta_range": 0.10,
      "moderate_beta_base": 0.70,
      "moderate_beta_range": 0.15,
      "low_beta_base": 0.85,
      "low_beta_range": 0.10,
      "independent_base": 0.95,
      "independent_range": 0.05
    }
  }
}
```

**代码实现**:
```python
# ✅ 配置化版本
mapping = confidence_cfg.get("mapping", {})
high_beta_base = mapping.get("high_beta_base", 0.60)
high_beta_range = mapping.get("high_beta_range", 0.10)
moderate_beta_base = mapping.get("moderate_beta_base", 0.70)
moderate_beta_range = mapping.get("moderate_beta_range", 0.15)
low_beta_base = mapping.get("low_beta_base", 0.85)
low_beta_range = mapping.get("low_beta_range", 0.10)
independent_base = mapping.get("independent_base", 0.95)
independent_range = mapping.get("independent_range", 0.05)

if I_score < high_beta:
    confidence = high_beta_base + (I_score / high_beta) * high_beta_range
elif I_score < moderate_beta:
    progress = (I_score - high_beta) / (moderate_beta - high_beta)
    confidence = moderate_beta_base + progress * moderate_beta_range
elif I_score < low_beta:
    progress = (I_score - moderate_beta) / (low_beta - moderate_beta)
    confidence = low_beta_base + progress * low_beta_range
else:
    progress = (I_score - low_beta) / (100.0 - low_beta)
    confidence = independent_base + progress * independent_range
```

**优点**:
- ✅ **语义清晰**: base表示起点，range表示变化量
- ✅ **易于调优**: 只需调整base/range值，公式结构不变
- ✅ **可扩展**: 添加新分段只需扩展配置，无需改代码

**实战案例**: `ats_core/decision/step1_direction.py` Lines 65-98 (v7.4.1)

---

### 6.2 函数签名演进最佳实践

**场景**: 为现有函数添加配置化参数

#### ❌ 错误做法：破坏向后兼容

```python
# v1.0
def calculate_flow_momentum(
    factor_scores_series: List[Dict[str, float]],
    weights: Dict[str, float],
    lookback_hours: int = 6
) -> float:
    # ...
    if abs(flow_now) < 1.0 and abs(flow_6h_ago) < 1.0:  # 硬编码
        return 0.0
    base = max(abs(flow_now), abs(flow_6h_ago), 10.0)  # 硬编码

# v2.0 - 破坏性修改
def calculate_flow_momentum(
    factor_scores_series: List[Dict[str, float]],
    weights: Dict[str, float],
    lookback_hours: int,  # 移除了默认值！
    flow_weak_threshold: float,  # 必填参数！
    base_min_value: float  # 必填参数！
) -> float:
    # ...
```

**问题**: 所有现有调用点都会报错！

#### ✅ 正确做法：保持向后兼容

```python
# v2.0 - 向后兼容版本
def calculate_flow_momentum(
    factor_scores_series: List[Dict[str, float]],
    weights: Dict[str, float],
    lookback_hours: int = 6,  # ✅ 保留默认值
    flow_weak_threshold: float = 1.0,  # ✅ 新增参数带默认值
    base_min_value: float = 10.0  # ✅ 新增参数带默认值
) -> float:
    """
    ...
    Args:
        ...
        flow_weak_threshold: Flow弱阈值（v2.0新增，默认1.0）
        base_min_value: base最小值（v2.0新增，默认10.0）
    """
    # v2.0配置化：flow值都很弱时认为无动量
    if abs(flow_now) < flow_weak_threshold and abs(flow_6h_ago) < flow_weak_threshold:
        return 0.0

    # v2.0配置化：使用配置的base_min_value避免除0
    base = max(abs(flow_now), abs(flow_6h_ago), base_min_value)
```

**调用方式**:

```python
# 旧代码 - 继续工作（使用默认值）
flow_momentum = calculate_flow_momentum(
    factor_scores_series,
    flow_weights,
    lookback_hours
)

# 新代码 - 使用配置化参数
flow_weak_threshold = enhanced_f_cfg.get("flow_weak_threshold", 1.0)
base_min_value = enhanced_f_cfg.get("base_min_value", 10.0)

flow_momentum = calculate_flow_momentum(
    factor_scores_series,
    flow_weights,
    lookback_hours,
    flow_weak_threshold,  # 传入配置参数
    base_min_value  # 传入配置参数
)
```

**原则**:
1. **新增参数必须带默认值**（与原硬编码值一致）
2. **默认值写在函数签名中**（不要依赖None判断）
3. **文档字符串标注版本**（v2.0新增）
4. **渐进式迁移**（允许新旧代码共存）

**实战案例**: `ats_core/decision/step2_timing.py` Lines 67-112 (v7.4.1)

---

### 6.3 Session状态记录规范

**目的**: 记录完整session工作，便于后续继续或审查

#### 标准格式：SESSION_STATE.md

**必需章节**:

```markdown
# SESSION_STATE - <项目名> <版本号>

**Session Date**: YYYY-MM-DD
**Branch**: <git-branch-name>
**Task**: <任务描述>

---

## 📋 Session Summary
### Task Completed
### Achievements (配置/代码/文档/测试/Git变更)

## 🎯 Achievements
### Configuration Changes
### Code Changes
### Documentation
### Testing
### Git Commits

## 📊 Metrics (Before/After对比)

## 🔄 Development Process (5个Phase)

## 📝 Remaining Work

## 🎓 Key Learnings

## 📚 Related Documents

## 🔗 Git Information

---

**Session Status**: ✅ Completed / ⏸️ Paused / 🚧 In Progress
**Last Updated**: YYYY-MM-DD
```

#### 何时创建

- ✅ **多步骤任务**: 需要跨session完成的任务
- ✅ **复杂重构**: 涉及多个文件、多次提交
- ✅ **系统性修复**: 修复一类问题（如v7.4.1硬编码清理）
- ❌ **单文件修改**: 简单的bug修复或小改进

#### 内容要点

1. **完整性**: 包含所有修改的文件、配置、测试
2. **可追溯**: 清晰的Git提交历史和文档链接
3. **可继续**: Remaining Work明确指出未完成任务
4. **可审查**: Metrics展示改进效果

**实战案例**: `SESSION_STATE.md` (v7.4.1)

---

### 6.4 分段逻辑配置化系统模式

**场景**: if-elif-else每个分支都有硬编码

#### 识别模式

```python
# 典型模式：多分支条件 + 每分支有硬编码
if condition_A:
    value = HARDCODED_A  # ❌
elif condition_B:
    value = HARDCODED_B  # ❌
elif condition_C:
    value = HARDCODED_C  # ❌
else:
    value = HARDCODED_DEFAULT  # ❌
```

#### 配置化步骤

1. **提取所有分支的硬编码值到配置**
```json
{
  "branch_A_value": <HARDCODED_A>,
  "branch_B_value": <HARDCODED_B>,
  "branch_C_value": <HARDCODED_C>,
  "default_value": <HARDCODED_DEFAULT>
}
```

2. **在代码中统一读取配置**
```python
cfg = config.get("branch_config", {})
value_A = cfg.get("branch_A_value", HARDCODED_A)  # 默认值保持一致
value_B = cfg.get("branch_B_value", HARDCODED_B)
value_C = cfg.get("branch_C_value", HARDCODED_C)
default = cfg.get("default_value", HARDCODED_DEFAULT)

if condition_A:
    value = value_A  # ✅ 配置化
elif condition_B:
    value = value_B  # ✅ 配置化
elif condition_C:
    value = value_C  # ✅ 配置化
else:
    value = default  # ✅ 配置化
```

**实战案例**: `ats_core/decision/step3_risk.py` Lines 325-350 (v7.4.1)

---

## 📌 重要原则

1. **配置优先**: 先定义配置，后实现代码（禁止硬编码）
2. **顺序严格**: 严格遵守文件修改顺序
3. **依赖明确**: 修改A文件必须同步修改依赖文件
4. **测试充分**: 配置 + 逻辑 + 导入 + 集成
5. **文档同步**: 代码与文档同步提交
6. **版本规范**: 遵循版本命名规范
7. **统一配置**: 强制所有参数从配置文件读取，增加配置验证器
8. **系统性扫描**: 发现一个问题，立即全面扫描同类问题
9. **默认值一致**: 代码默认值必须与配置文件保持一致
10. **向后兼容**: 函数签名演进时保持向后兼容 🆕
11. **Session记录**: 复杂任务创建SESSION_STATE.md记录完整状态 🆕

---

## 📝 版本历史

### v3.3.0 (2025-11-18)
**重大更新**:
- **新增章节 § 6**: 高级配置化模式（基于v7.4.1实战）
  - 6.1 算法曲线参数配置化（Base + Range模式）
  - 6.2 函数签名演进最佳实践（向后兼容原则）
  - 6.3 Session状态记录规范（SESSION_STATE.md标准格式）
  - 6.4 分段逻辑配置化系统模式（if-elif-else配置化）
- **新增实战案例**: v7.4.1四步系统硬编码清理
  - 算法曲线配置化（step1置信度映射，8个参数）
  - 函数签名向后兼容演进（step2 Flow动量计算）
  - 分段逻辑配置化（step3入场价fallback buffer）
  - 零硬编码达成度：85% → 95%+
- **更新核心原则**: 添加2条新原则（#10向后兼容，#11 Session记录）

**影响**:
- 提供算法曲线配置化的系统方法论
- 建立函数签名演进的标准实践
- 规范复杂任务的状态记录机制

**文档参考**:
- `docs/v7.4.1_HARDCODE_CLEANUP.md` - 完整修复文档
- `SESSION_STATE.md` - Session状态记录示例

### v3.2.0 (2025-11-10)
**重大更新**:
- 新增实战案例：硬编码清理系列（v7.3.4-v7.3.4）
  - 完整的5个版本迭代历程
  - 16个硬编码问题的修复经验
  - 配置统一与默认值一致性修复
- 新增最佳实践：硬编码检测清单
- 新增最佳实践：配置文件管理规范
- 新增最佳实践：默认值一致性维护
- 更新核心原则：添加3条新原则（系统性扫描、默认值一致、配置统一）

**影响**: 提供完整的硬编码清理方法论，避免重复犯错

### v3.1.1 (2025-11-09)
**新增**:
- 核心原则 § 5: 统一配置管理（强制要求）
  - 禁止硬编码和Magic Number
  - 配置读取标准模式
  - 配置验证器要求
  - 配置变更检查清单

**目的**: 解决参数硬编码问题，提升系统可维护性

### v3.1.0 (2025-11-09)
**初始版本**:
- 5阶段标准化开发流程
- 文件修改顺序规范
- 文件依赖关系图
- 完整案例（v3.1 I因子增强）

---

**当前版本**: v3.3.0
**最后更新**: 2025-11-18
**适用范围**: 所有系统性增强/优化项目
