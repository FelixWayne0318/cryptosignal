# 代码修改标准化流程

**版本**: v1.0
**创建日期**: 2025-11-15
**适用范围**: CryptoSignal项目所有代码修改
**基于经验**: Phase 1 + Phase 2 成功实践总结

---

## 📋 使用方法

**用户**: 当需要修改代码时，直接给我发送：

```
请按照 docs/CODE_MODIFICATION_PROTOCOL.md 执行以下修改：
[具体修改需求]
```

**AI Agent**: 我会严格按照本文档的流程执行。

---

## 🎯 核心原则

1. **验证先行**: 先测试后修改，确保不破坏现有功能
2. **小步快跑**: 每次修改聚焦1-3个相关问题
3. **可追溯性**: 每个修改都有明确的问题编号和验证结果
4. **零破坏**: 所有修改必须通过集成测试验证

---

## 📝 标准工作流程

### 阶段1: 需求理解与上下文收集 (5-10分钟)

#### 1.1 读取必要文档

按顺序读取以下文件（如果存在）：

```bash
# 1. 读取问题描述（用户提供）
# 2. 读取系统架构
standards/00_INDEX.md
standards/01_SYSTEM_OVERVIEW.md
standards/02_ARCHITECTURE.md

# 3. 读取相关模块代码
[用户指定的文件或通过Grep查找]

# 4. 读取最近的健康检查报告（如果有）
docs/health_checks/*_health_check_*.md
```

#### 1.2 明确修改范围

回答以下问题：
- **目标**: 要解决什么问题？
- **范围**: 影响哪些文件？
- **优先级**: P0/P1/P2？
- **估时**: 预计需要多长时间？
- **风险**: 可能破坏什么？

#### 1.3 确认理解（如有疑问）

如果不确定，使用 `AskUserQuestion` 工具确认：
- 具体的修改意图
- 期望的行为
- 边界条件

---

### 阶段2: 修改前验证 (5-15分钟)

#### 2.1 运行现有测试（如果存在）

```bash
# 集成测试
./tests/integration_basic.sh

# 配置校验
python3 scripts/validate_config.py

# 单元测试（如果有）
pytest tests/
```

**成功标准**: 所有测试通过 ✅

**如果失败**: 先修复现有问题，再继续新修改

#### 2.2 使用TodoWrite创建任务计划

```json
[
  {
    "content": "理解并分析现有代码",
    "status": "in_progress",
    "activeForm": "分析现有代码"
  },
  {
    "content": "修改 [文件1]: [具体修改内容]",
    "status": "pending",
    "activeForm": "修改 [文件1]"
  },
  {
    "content": "修改 [文件2]: [具体修改内容]",
    "status": "pending",
    "activeForm": "修改 [文件2]"
  },
  {
    "content": "运行测试验证修改",
    "status": "pending",
    "activeForm": "验证修改"
  },
  {
    "content": "提交代码（符合规范的commit message）",
    "status": "pending",
    "activeForm": "提交代码"
  }
]
```

---

### 阶段3: 执行修改 (30-120分钟)

#### 3.1 修改顺序（严格遵守）

按照以下顺序修改文件，**绝不颠倒**：

```
1. config/        - 配置文件
2. ats_core/config/    - 配置管理模块
3. ats_core/factors_v2/  - 因子计算模块
4. ats_core/pipeline/    - 流水线模块
5. ats_core/outputs/     - 输出模块
6. scripts/       - 脚本文件
7. docs/          - 文档文件
8. standards/     - 规范文档
```

**原因**: 依赖关系，从底层到上层，避免循环依赖错误

#### 3.2 单个文件修改流程

对于每个文件：

**步骤1**: 使用 `Read` 工具读取完整文件
```python
Read(file_path="/home/user/cryptosignal/path/to/file.py")
```

**步骤2**: 使用 `Edit` 工具精确修改
```python
Edit(
    file_path="/home/user/cryptosignal/path/to/file.py",
    old_string="[精确的旧代码，包含缩进]",
    new_string="[精确的新代码，包含缩进]"
)
```

**关键注意事项**:
- ✅ 保持原有缩进（空格或Tab）
- ✅ 包含足够上下文使 `old_string` 唯一
- ✅ 保持代码风格一致
- ❌ 不要包含行号前缀（Read工具的输出有行号，但old_string不要包含）

**步骤3**: 立即验证修改

```bash
# 语法检查（Python）
python3 -m py_compile path/to/file.py

# 导入测试
python3 -c "import module_name; print('✅ Import OK')"
```

**步骤4**: 更新TodoWrite状态
```python
TodoWrite(todos=[
    # ...
    {"content": "修改 [文件1]", "status": "completed", "activeForm": "..."},
    {"content": "修改 [文件2]", "status": "in_progress", "activeForm": "..."},
    # ...
])
```

#### 3.3 文档同步更新

如果修改了代码逻辑，**必须**同步更新：

1. **Docstring**: 函数/类的文档字符串
2. **README**: 如果影响使用方式
3. **standards/**: 如果影响架构或规范
4. **CHANGELOG**: 重大变更必须记录

---

### 阶段4: 验证修改 (10-30分钟)

#### 4.1 运行所有测试

```bash
# 1. 集成测试（必须）
./tests/integration_basic.sh
# 期望: 13/13测试通过 ✅

# 2. 配置校验（必须）
python3 scripts/validate_config.py
# 期望: 7/7配置文件验证通过 ✅

# 3. 单元测试（如果有）
pytest tests/ -v
# 期望: 所有测试通过 ✅

# 4. 类型检查（如果启用）
mypy ats_core/
```

#### 4.2 手动功能测试

如果修改了核心逻辑，进行手动测试：

```python
# 测试修改的模块
python3 -c "
from ats_core.xxx import modified_function
result = modified_function(test_input)
print(f'Result: {result}')
assert result == expected_output, 'Test failed!'
print('✅ Manual test passed')
"
```

#### 4.3 验证不破坏现有功能

```bash
# 测试配置加载
python3 -c "
from ats_core.cfg import CFG
from ats_core.config.runtime_config import RuntimeConfig
print('✅ Config loading OK')
"

# 测试因子计算（如果修改了因子）
python3 -c "
from ats_core.factors_v2.xxx import calculate_xxx_factor
print('✅ Factor calculation OK')
"
```

---

### 阶段5: 提交代码 (5-10分钟)

#### 5.1 Git提交规范

**Commit Message格式**:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**类型（type）**:
- `feat`: 新功能
- `fix`: Bug修复
- `refactor`: 重构（不改变功能）
- `docs`: 文档修改
- `test`: 测试相关
- `chore`: 构建/工具链修改

**范围（scope）**: P0-1, P1-2, 或模块名

**主题（subject）**: 50字以内，描述修改内容

**正文（body）**: 详细说明（使用HEREDOC避免格式问题）

**示例**:

```bash
git add [修改的文件]

git commit -m "$(cat <<'EOF'
fix(P1-4): 统一配置路径解析

**问题**: cfg.py和RuntimeConfig路径解析逻辑不一致
- cfg.py: 使用 os.path.join(_REPO_ROOT, "config")
- RuntimeConfig: 使用 Path(__file__).parent.parent.parent

**解决方案**: 创建统一路径解析器 path_resolver.py

**修改内容**:
1. 新增 ats_core/config/path_resolver.py (259行)
   - get_config_root(): 统一路径解析
   - 支持环境变量 CRYPTOSIGNAL_CONFIG_ROOT

2. 修改 ats_core/cfg.py
   - 使用 get_params_file() 替代硬编码

3. 修改 ats_core/config/runtime_config.py
   - 委托给 path_resolver

**测试验证**:
- ✅ 集成测试 13/13 通过
- ✅ 配置文件加载成功
- ✅ 环境变量支持验证

**影响范围**: 配置路径解析（低风险）

**参考**: /tmp/revised_fix_plan.md#Phase2-3
EOF
)"
```

#### 5.2 推送到远程

```bash
# 推送到指定分支
git push -u origin <branch-name>

# 如果push失败（网络问题），重试最多4次，指数退避
# 2s, 4s, 8s, 16s
```

#### 5.3 更新TodoWrite状态

```python
TodoWrite(todos=[
    # 所有任务标记为 completed
])
```

---

## ⚠️ 常见错误与避免方法

### 错误1: 修改顺序错误

❌ **错误**: 先修改 `pipeline/`，再修改 `config/`
✅ **正确**: 先修改 `config/`，再修改 `pipeline/`

**原因**: pipeline依赖config，颠倒顺序会导致导入错误

---

### 错误2: old_string不唯一

❌ **错误**:
```python
Edit(old_string="def foo():", new_string="def foo(x):")
# 如果文件中有多个 "def foo():"，会失败
```

✅ **正确**:
```python
Edit(
    old_string="""def foo():
    \"\"\"Original docstring\"\"\"
    return 1""",
    new_string="""def foo(x):
    \"\"\"Updated docstring\"\"\"
    return x"""
)
# 包含足够上下文，确保唯一
```

---

### 错误3: 缩进不一致

❌ **错误**: 使用空格替代Tab，或反之
✅ **正确**: 使用Read工具读取文件，复制原始缩进

**验证方法**:
```bash
# 检查文件使用Tab还是空格
cat -A file.py | head -20
# ^I = Tab, 多个空格 = 空格缩进
```

---

### 错误4: 没有测试就提交

❌ **错误**: 修改完直接git commit
✅ **正确**: 先运行所有测试，确保通过后再提交

**检查清单**:
- [ ] 集成测试通过
- [ ] 配置校验通过
- [ ] 手动功能测试通过
- [ ] 不破坏现有功能

---

### 错误5: Commit message不规范

❌ **错误**: `git commit -m "fix bug"`
✅ **正确**: 使用HEREDOC，包含问题、解决方案、验证结果

---

## 📊 成功标准检查清单

在说"完成"之前，确保以下所有项都打勾：

### 修改前
- [ ] 已读取相关文档和代码
- [ ] 已运行现有测试，全部通过
- [ ] 已创建TodoWrite任务计划
- [ ] 已明确修改范围和风险

### 修改中
- [ ] 按照正确顺序修改文件（config → core → pipeline → output → docs → standards）
- [ ] 每个文件修改后立即验证（语法检查+导入测试）
- [ ] 及时更新TodoWrite状态
- [ ] 同步更新相关文档

### 修改后
- [ ] ✅ 集成测试 13/13 通过
- [ ] ✅ 配置校验 7/7 通过
- [ ] ✅ 手动功能测试通过
- [ ] ✅ 不破坏现有功能
- [ ] ✅ Git commit message符合规范
- [ ] ✅ 代码已推送到远程
- [ ] ✅ 所有TodoWrite任务标记为completed

---

## 🎯 快速参考

### 最小修改流程（简化版）

```bash
# 1. 读取上下文
Read(相关文件)

# 2. 运行测试
./tests/integration_basic.sh

# 3. 创建TodoWrite计划

# 4. 修改文件（按顺序）
Read → Edit → 验证

# 5. 运行所有测试
./tests/integration_basic.sh
python3 scripts/validate_config.py

# 6. 提交
git add .
git commit -m "$(cat <<'EOF'
<type>(<scope>): <subject>
<详细说明>
EOF
)"
git push

# 7. 完成TodoWrite
```

---

## 📖 相关文档

- **系统概览**: `standards/01_SYSTEM_OVERVIEW.md`
- **架构文档**: `standards/02_ARCHITECTURE.md`
- **开发流程**: `standards/DEVELOPMENT_WORKFLOW.md`
- **修改规范**: `standards/MODIFICATION_RULES.md`
- **系统升级**: `standards/SYSTEM_ENHANCEMENT_STANDARD.md`

---

## 🔄 文档维护

**版本历史**:
- v1.0 (2025-11-15): 初始版本，基于Phase 1+2成功实践

**更新时机**:
- 发现新的最佳实践时
- 流程有重大改进时
- 发现常见错误需要补充时

**维护责任**: 系统架构师

---

**最后更新**: 2025-11-15
**作者**: Claude Code (AI Agent)
**审核**: 待用户确认
**状态**: v1.0 - 生产就绪
