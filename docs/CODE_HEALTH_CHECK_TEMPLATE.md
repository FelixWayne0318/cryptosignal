# [子系统名称] 代码级体检报告

**体检日期**: YYYY-MM-DD
**体检范围**: [具体模块/功能，如 "I 因子系统 + 零硬编码落地情况"]
**体检工程师**: [姓名/ID]
**代码版本**: [Git commit hash / 版本号]
**参考文档**: [设计文档路径，如 `docs/FACTOR_SYSTEM_COMPLETE_DESIGN.md`]

---

## 📋 体检说明

**本次体检目标**：
> [简述本次体检的目的，如 "验证 v7.3.2-Full I 因子重构是否按设计落地，检查零硬编码实现情况"]

**检查范围**：
- [ ] 核心实现（算法、逻辑）
- [ ] 调用链（接口对接）
- [ ] 配置管理（零硬编码）
- [ ] 错误处理（稳定性）

---

## 一、当前状态评估（基于真实代码）

### 1.1 [核心模块 A，如 independence.py] 结构分析

#### ✅ **[检查项 1，如 BTC-only 回归]**：已满足 / 未满足
- **检查内容**: [具体检查什么，如 "是否只使用 BTC 做回归，无 ETH 参数"]
- **核心函数**: `function_name()` (Line XXX-YYY)
- **函数签名**:
  ```python
  def function_name(param1: Type1, param2: Type2) -> ReturnType:
  ```
- **证据**:
  ```python
  # 关键代码片段（5-10 行即可）
  # Line XXX
  ```
- **结论**: [满足/不满足，原因]

#### ❌ **[检查项 2，如 时间戳对齐]**：未实现（P0 级硬伤）
- **检查内容**: [具体检查什么]
- **当前实现**:
  ```python
  # Line XXX
  # 当前代码片段
  ```
- **问题**: [详细描述问题]
- **预期实现**:
  ```python
  # 应该是这样的代码
  ```
- **影响**: [对系统的影响，如 "β 值计算可能错位，I 因子失效"]
- **优先级**: P0 / P1 / P2 / P3

#### ⚠️ **[检查项 3，如 零硬编码]**：部分满足（X%）
- **检查内容**: ...
- **已配置化**: [列出已从配置读取的参数]
- **仍硬编码**: [列出仍然硬编码的参数]
- **优先级**: P1 / P2

---

### 1.2 [调用模块 B，如 analyze_symbol.py] 调用链分析

#### ✅ **调用参数**：正确 / 不正确
- **调用位置**: `file_path.py` Line XXX-YYY
- **调用形式**:
  ```python
  result = function_name(arg1, arg2, ...)
  ```
- **参数匹配**:
  - [ ] 参数数量正确？
  - [ ] 参数类型正确？
  - [ ] 参数顺序正确？
- **问题**: [如果有问题，详细说明]

#### ✅ **返回值解构**：匹配 / 不匹配
- **解构形式**:
  ```python
  var1, var2 = function_name(...)
  ```
- **期望返回值**: `(Type1, Type2)` - X 个值
- **实际返回值**: `(Type1, Type2, Type3)` - Y 个值
- **问题**: [如果不匹配，说明错误类型]

---

### 1.3 [配置模块 C，如 RuntimeConfig] 配置管理状态

#### ✅ **RuntimeConfig 类**：存在 / 不存在
- **文件路径**: `path/to/runtime_config.py`
- **核心方法**:
  - [ ] `get_numeric_stability(scope)` - 存在/缺失
  - [ ] `get_factor_range(factor_name)` - 存在/缺失
  - [ ] `get_logging_float_format()` - 存在/缺失
  - [ ] [其他方法]

#### ✅ **配置文件**：全部存在 / 部分缺失
| 文件 | 路径 | 大小 | 状态 | 结构完整性 |
|------|------|------|------|----------|
| `numeric_stability.json` | `config/numeric_stability.json` | XXX bytes | ✅ 存在 / ❌ 缺失 | ✅ 完整 / ⚠️ 缺少字段 |
| `factor_ranges.json` | `config/factor_ranges.json` | XXX bytes | ✅ / ❌ | ✅ / ⚠️ |
| `logging.json` | `config/logging.json` | XXX bytes | ✅ / ❌ | ✅ / ⚠️ |

#### ⚠️ **配置实际使用情况**
**已使用 RuntimeConfig**：
- Line XXX: `RuntimeConfig.get_numeric_stability("scope")` ✅
- Line YYY: `RuntimeConfig.get_factor_range("F")` ✅

**未使用（仍硬编码）**：
- Line ZZZ: `param = 24` ❌ 应该从配置读取

---

## 二、是否存在"会导致程序直接崩"的硬伤

### 🚨 **P0 Critical 级硬伤**：X 个

#### **P0-1: [问题标题，如 "时间戳对齐缺失"]**

**文件**: `path/to/file.py`
**位置**: Line XXX-YYY (`function_name` 函数)

**问题描述**：
```python
# 当前实现（错误）
# Line XXX
current_code_snippet_here
```
- [详细说明问题，如 "假设 alt 和 BTC 的数据点完全对齐（按索引位置对齐）"]
- [说明实际情况，如 "但实际上 WebSocket 数据可能有缺失/延迟"]

**后果**: [对系统的影响，如 "计算出的 β 值不准确，I 因子失效"]

**错误类型**: 逻辑错误 / 接口不匹配 / 数据对齐错误 / ...
**影响范围**: [哪些功能受影响]
**修复优先级**: **P0 (Immediate)** - [原因]

**预期实现**（需要添加/修改）：
```python
# 正确的实现应该是...
def function_name(
    param1: Type1,
    param2: Type2,  # ← 新增参数
    ...
):
    # 新增逻辑...
```

---

#### **P0-2: [第二个 P0 问题（如果有）]**
[同上格式]

---

### ⚠️ **P1 High 级问题**：X 个

#### **P1-1: [问题标题]**

**文件**: `path/to/file.py`
**位置**: Line XXX

**问题描述**：
```python
# Line XXX
problematic_code_here
```
[详细说明问题]

**后果**: [影响，如 "veto 规则失效，风控失效"]

**错误类型**: 功能缺失 / 配置缺失 / ...
**影响范围**: [具体影响]
**修复优先级**: **P1 (High)** - [原因]

**修复方案**（Patch）：
```python
# 修改建议
fixed_code_here
```

---

### ✅ **接口层面自洽性**：通过 / 未通过

- [ ] independence.py 和 analyze_symbol.py 之间的函数签名是否匹配？
- [ ] 返回值数量和类型是否一致？
- [ ] ModulatorChain 的接口与调用端是否一致？

**结论**：[通过/未通过，如果未通过列出具体问题]

---

## 三、是否满足"零硬编码"目标

### 📊 **零硬编码达成度**：X% (完全满足 / 部分满足 / 未满足)

#### ✅ **已实现零硬编码的部分**（X/Y）：

1. **[配置项 1，如 eps 系列数值稳定性常量]** ✅
   - **配置文件**: `config/numeric_stability.json`
   - **使用位置**: `module.py` Line XXX
   - **读取方式**: `RuntimeConfig.get_numeric_stability("scope")`
   - **涉及参数**: `eps_var_min, eps_log_price, ...`

2. **[配置项 2]** ✅
   - ...

#### ❌ **仍然硬编码的部分**（Y/Y）：

1. **[配置项 1，如 regression 参数]** ❌
   - **硬编码位置**:
     - `module.py` Line XXX (默认 params)
     - `module.py` Line YYY (params.get 默认值)
   - **涉及参数**:
     ```python
     window_hours = 24  # ← 硬编码
     min_points = 16    # ← 硬编码
     ```
   - **应该从哪里读取**: `config/factors_unified.json` → `Factor.regression` 节点

2. **[配置项 2]** ❌
   - ...

---

### 🎯 **要完全满足零硬编码目标，需要动的地方**：

#### **配置文件层面**（新增 X 个配置节点）：

1. **`config/some_config.json`** 需要新增：
   ```json
   {
     "new_section": {
       "param1": value1,
       "param2": value2
     }
   }
   ```

#### **代码层面**（修改 X 个文件）：

1. **`path/to/file1.py`**：[需要做什么修改]
2. **`path/to/file2.py`**：[需要做什么修改]

---

## 四、修复路线图

### 🚨 **P0 级（会导致计算错误，必须立即修）**：X 项

#### **P0-1: [问题标题]**

**影响**: [简述影响，如 "I 因子计算结果可能完全错误"]
**修复难度**: 🔴 High / 🟡 Medium / 🟢 Low
**预计工时**: X 小时

**修复步骤**：

1. **[步骤 1]**：[详细说明]
   ```python
   # 示例代码
   ```

2. **[步骤 2]**：[详细说明]

3. **[步骤 3]**：[详细说明]

**验证方式**：
```python
# 测试用例
test_code_here
```

**涉及文件**：
- `file1.py` (修改 Line XXX-YYY)
- `file2.py` (修改 Line AAA-BBB)

---

### ⚠️ **P1 级（违背工程规范，本周内修复）**：X 项

#### **P1-1: [问题标题]**

**影响**: [简述影响]
**修复难度**: 🟡 Medium / 🟢 Low
**预计工时**: X 分钟/小时

**修复方案**（Patch）：
```python
# 文件：path/to/file.py
# Line XXX

# 修改前
old_code_here

# 修改后
new_code_here
```

**验证方式**：
```bash
# 测试命令
```

---

### 📋 **P2 级（非核心功能，下个迭代修复）**：X 项

#### **P2-1: [问题标题]**
[简述问题和修复建议]

---

### 🎯 **修复优先级建议**

| 优先级 | 项目 | 理由 | 推荐时间窗口 |
|--------|------|------|--------------|
| **P0** | [问题 1] | [理由，如 "影响计算正确性"] | 立即修复（当前 sprint） |
| **P1-1** | [问题 2] | [理由] | 下一个 patch（本周内） |
| **P1-2** | [问题 3] | [理由] | 下一个 patch（本周内） |
| **P2-1** | [问题 4] | [理由] | 下一个迭代（下周） |

---

## 五、总结 & 建议

### ✅ **做得好的地方**：

1. **[优点 1]**: [详细说明，如 "RuntimeConfig + JSON 配置的设计非常好，实现了关注点分离"]
2. **[优点 2]**: ...
3. **[优点 3]**: ...

### ❌ **需要改进的地方**：

1. **P0 Critical**: [问题描述] - **必须立即修复**
2. **P1 High**: [问题描述] - [建议时间窗口]
3. **P2 Medium**: [问题描述] - [建议]

### 🎯 **[某目标] 达成路径**：

```
当前状态: X% (已完成部分)
         ↓
[里程碑 1]: Y% (完成 P1-1, P1-2)
         ↓
[里程碑 2]: 100% (完成 P2-X)
```

### 📝 **行动建议**：

1. **立即执行 P0-X**（[问题描述]）- [理由，如 "这是计算正确性的基础"]
2. **本周内完成 P1-X**（[问题描述]）- [理由]
3. **下周迭代完成 P2-X**（[问题描述]）- [理由]

### 💡 **长期改进建议**：

1. [建议 1，如 "添加时间戳对齐的单元测试"]
2. [建议 2]
3. [建议 3]

---

## 六、附录

### 魔法数字扫描结果

| 位置 | 数字 | 用途 | 状态 |
|------|------|------|------|
| Line XXX | `24` | window_hours 默认值 | ⚠️ 硬编码 |
| Line YYY | `0.6` | beta_low 边界 | ⚠️ 硬编码 |
| Line ZZZ | `1e-10` | 降级 epsilon | ✅ 仅降级用 |

### 函数调用图

```
[上游模块]
    ↓
[核心模块 A] → function_1(param1, param2) → returns (val1, val2)
    ↓                                              ↓
[核心模块 B]                                 解构：var1, var2 = ...
    ↓
[下游模块]
```

### 配置文件依赖图

```
RuntimeConfig
    ├─ numeric_stability.json
    │   └─ independence.eps_var_min
    ├─ factor_ranges.json
    │   └─ I.min, I.max, I.neutral
    └─ logging.json
        └─ float_format.decimals
```

---

**体检完毕！** 🏁

---

## 修订历史

| 版本 | 日期 | 修改内容 | 修改人 |
|------|------|---------|--------|
| v1.0 | YYYY-MM-DD | 初始体检 | [姓名] |
| v1.1 | YYYY-MM-DD | [修改内容] | [姓名] |

---

## 参考资料

- [CODE_HEALTH_CHECK_GUIDE.md](./CODE_HEALTH_CHECK_GUIDE.md) - 代码体检方法论指南
- [设计文档路径] - 本次体检的参考设计文档
- [相关规范文档] - 工程规范、编码规范等
