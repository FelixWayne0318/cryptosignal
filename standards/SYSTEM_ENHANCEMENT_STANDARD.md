# 系统增强标准化流程 (System Enhancement Standard)

> **v3.1规范 - 确保每次系统升级都有序、可追溯、无遗漏**

---

## 📋 目录

1. [核心原则](#核心原则)
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

## 📌 重要原则

1. **配置优先**: 先定义配置，后实现代码
2. **顺序严格**: 严格遵守文件修改顺序
3. **依赖明确**: 修改A文件必须同步修改依赖文件
4. **测试充分**: 配置 + 逻辑 + 导入 + 集成
5. **文档同步**: 代码与文档同步提交
6. **版本规范**: 遵循版本命名规范

---

**版本**: v3.1
**最后更新**: 2025-11-09
**适用范围**: 所有系统性增强/优化项目
