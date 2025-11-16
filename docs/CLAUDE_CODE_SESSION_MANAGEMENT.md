# Claude Code 会话管理指南

> **解决会话变卡、上下文丢失、进度不同步的最佳实践**
> v1.0 | 2025-11-16

---

## 🎯 核心问题

使用 Claude Code 一段时间后会出现：
1. ⚡ **响应变慢** - Token 累积导致处理变慢
2. 🔄 **换对话框麻烦** - 上下文需要重新建立
3. 🧠 **思路不连贯** - 新会话理解可能偏差
4. 📊 **进度不同步** - 不知道上次做到哪里

---

## ✅ 完整解决方案

### **方案 1: Git 作为状态保存器** ⭐⭐⭐⭐⭐

**核心思想**: 所有工作成果通过 Git commit 保存，会话只是临时工具

```bash
# 每完成一个小任务就提交
git add .
git commit -m "fix(P0): 修复XXX问题"
git push

# 新会话启动时
git log --oneline -10  # 看最近做了什么
git diff HEAD~1        # 看上次改了什么
```

**优点**:
- ✅ 工作成果永久保存
- ✅ 可以随时恢复到任何状态
- ✅ 新会话可以通过 Git 历史了解进度
- ✅ 代码审查和回滚更容易

**你的实际案例**:
```bash
0f4ddc2 refactor(P1): v7.3.47 文件清理 - 删除过时和重复文档
942caa5 refactor(P3): v7.3.47 版本号统一
ad09a99 docs(P3): v7.3.47 依赖分析与代码规范验证报告
362c067 refactor(P1): v7.3.47 文件重组和清理
8bf23a5 fix(P0): v7.3.47 修复quality.py中的ThresholdConfig错误用法
f4a8c65 fix(P0): v7.3.47 修复modulator_chain.py中的FactorConfig错误用法
```

看到这 6 个 commit，新会话立刻就知道你做了什么！

---

### **方案 2: 阶段性总结文档** ⭐⭐⭐⭐⭐

**创建 SESSION_STATE.md 作为"交接文档"**

```markdown
# 当前工作状态

## 📍 当前位置
正在进行: XXX功能开发
进度: 70% (3/5 步骤完成)

## ✅ 已完成
- [x] 修复 FactorConfig 错误 (commit: f4a8c65)
- [x] 统一版本号到 v7.3.47 (commit: 942caa5)
- [x] 清理过时文档 (commit: 0f4ddc2)

## 🔧 待办事项
- [ ] 优化性能瓶颈
- [ ] 添加单元测试覆盖率

## ⚠️ 重要上下文
- 使用 FactorConfig 必须通过 config.config.get() 访问
- 所有修改遵循 SYSTEM_ENHANCEMENT_STANDARD.md
- 版本号统一为 v7.3.47

## 🐛 已知问题
- 无

## 📝 下次会话提醒
- 从"待办事项"第一项开始
- 检查 Git status 确认无未提交的更改
```

---

### **方案 3: 主动请求会话总结** ⭐⭐⭐⭐

**在会话变卡之前**（Token 使用到 60-70% 时），主动请求：

```
"请总结当前会话的所有修改、决策和待办事项，
格式按照以下 9 个部分：
1. Primary Request
2. Key Technical Concepts
3. Files Modified
4. Errors and Fixes
5. Problem Solving
6. All User Messages
7. Pending Tasks
8. Current Work
9. Next Steps"
```

然后：
1. 保存这个总结
2. 提交所有工作到 Git
3. 开新会话时粘贴这个总结

---

### **方案 4: 使用 TODO 系统追踪** ⭐⭐⭐⭐

在每个工作阶段开始时创建 TODO 列表：

```markdown
## 本次会话任务清单

- [x] 1. 修复 FactorConfig 错误
  - [x] 1.1 修复 modulator_chain.py
  - [x] 1.2 修复 quality.py
  - [x] 1.3 测试验证
- [x] 2. 统一版本号
  - [x] 2.1 配置文件
  - [x] 2.2 核心模块
  - [x] 2.3 部署脚本
- [ ] 3. 性能优化
  - [ ] 3.1 分析瓶颈
  - [ ] 3.2 优化算法
```

**好处**: 任何人看到这个 TODO 都知道：
- 做了什么
- 做到哪里
- 下一步做什么

---

### **方案 5: 分阶段、小批量工作** ⭐⭐⭐

**避免单个会话做太多事情**：

❌ **错误做法**:
```
一个会话做 20 个任务，用完 180k tokens，最后变卡
```

✅ **正确做法**:
```
会话 1: 修复 P0 错误 (2-3 个任务) → Commit → Push
会话 2: 重构代码 (2-3 个任务) → Commit → Push
会话 3: 添加测试 (2-3 个任务) → Commit → Push
```

每个会话专注 2-5 个相关任务，完成后立即提交。

---

## 🔧 实用工具脚本

### 自动生成会话总结

创建 `scripts/generate_session_summary.sh`:

```bash
#!/bin/bash

echo "# 会话状态总结 $(date +%Y-%m-%d)"
echo ""
echo "## 最近提交"
git log --oneline -10
echo ""
echo "## 当前分支状态"
git status
echo ""
echo "## 待提交的修改"
git diff --stat
echo ""
echo "## 当前 TODO"
if [ -f "SESSION_STATE.md" ]; then
    grep -A 20 "## 🔧 待办事项" SESSION_STATE.md
fi
```

使用：
```bash
chmod +x scripts/generate_session_summary.sh
./scripts/generate_session_summary.sh > SESSION_SUMMARY.txt
```

---

## 📋 会话切换检查清单

**结束旧会话前**:
- [ ] 所有修改已提交到 Git
- [ ] 运行 `git push` 推送到远程
- [ ] 更新 SESSION_STATE.md
- [ ] 生成会话总结（如果需要）
- [ ] 确认没有正在运行的进程

**开始新会话时**:
- [ ] 运行 `git log --oneline -10` 查看最近工作
- [ ] 查看 SESSION_STATE.md 了解待办事项
- [ ] 运行 `git status` 确认工作目录干净
- [ ] 阅读最近的 commit message
- [ ] 告知 Claude 当前要做的任务

---

## 💡 给 Claude 的最佳提示词

### 新会话启动时:

```
这是一个延续之前工作的会话。

项目背景:
- CryptoSignal v7.3.47 量化交易系统
- 遵循 SYSTEM_ENHANCEMENT_STANDARD.md 规范
- 当前分支: claude/reorganize-audit-factors-XXXXX

上次会话完成的工作:
[粘贴 git log --oneline -5]

当前任务:
[从 SESSION_STATE.md 复制待办事项]

请按照系统规范继续工作，使用 TodoWrite 工具追踪进度。
```

---

## 📊 Token 使用监控

**何时考虑换新会话**:

| Token 使用 | 状态 | 建议 |
|-----------|------|------|
| < 50k (25%) | 🟢 绿色 | 正常工作 |
| 50-100k (25-50%) | 🟡 黄色 | 可继续，注意进度保存 |
| 100-150k (50-75%) | 🟠 橙色 | 准备总结和切换 |
| > 150k (75%) | 🔴 红色 | 立即总结，结束会话 |

**当前会话**: 25,776 tokens (12.9%) 🟢 - 状态良好

---

## 🎯 推荐工作流

### **标准工作流**:

```
1. 开始新会话
   └─> 查看 git log 和 SESSION_STATE.md

2. 创建 TODO 列表
   └─> 使用 TodoWrite 工具

3. 专注完成 2-5 个任务
   └─> 每完成一个任务立即 commit

4. Token 使用达到 50% 时
   └─> 评估是否应该结束会话

5. 结束会话前
   └─> 更新 SESSION_STATE.md
   └─> git push 所有修改
   └─> 生成会话总结（可选）

6. 开始新会话
   └─> 回到步骤 1
```

---

## ✨ 最佳实践案例

### **你的当前项目就是完美示范**:

```
会话 1 (之前):
- 修复 FactorConfig 错误 → 2 commits
- 修复 ThresholdConfig 错误 → 1 commit
→ 推送到远程

会话 2 (之前):
- 文件重组 → 1 commit
- 依赖分析 → 1 commit
- 版本统一 → 1 commit
- 文档清理 → 1 commit
→ 推送到远程

会话 3 (当前):
- 回答问题，提供建议
→ Token 仅用 13%，状态健康
```

**关键要素**:
- ✅ 每个会话 3-6 个 commit
- ✅ 每次都推送到远程
- ✅ Commit message 清晰描述修改
- ✅ 遵循系统规范和优先级

---

## 🚀 立即行动

**马上创建你的会话管理文件**:

```bash
# 创建状态跟踪文件
touch SESSION_STATE.md

# 写入初始内容
cat > SESSION_STATE.md << 'EOF'
# 当前工作状态

## 📍 当前位置
项目: CryptoSignal v7.3.47
分支: claude/reorganize-audit-factors-01QB7e2CKvfS3DdHR5pnfWkh
状态: v7.3.47 所有核心修复已完成

## ✅ v7.3.47 已完成
- [x] P0: 修复 FactorConfig/ThresholdConfig 错误
- [x] P1: 文件重组和清理
- [x] P3: 依赖分析和代码规范验证
- [x] P3: 版本号统一
- [x] P1: 删除过时文档

## 🔧 待办事项
(暂无 - 所有任务已完成)

## ⚠️ 重要技术细节
- FactorConfig/ThresholdConfig 使用: `config.config.get()`
- 遵循 SYSTEM_ENHANCEMENT_STANDARD.md
- Git 提交格式: `type(priority): description`

## 📝 下次会话提醒
- 检查 git status 确认无未提交修改
- 查看最近 commit: git log --oneline -10
- 根据新需求创建 TODO 列表
EOF

# 提交这个文件
git add SESSION_STATE.md
git commit -m "docs(P1): 添加会话状态管理文件 - 解决会话切换问题"
```

---

## 📚 相关文档

- `SYSTEM_ENHANCEMENT_STANDARD.md` - 系统规范
- `CODE_MODIFICATION_PROTOCOL.md` - 代码修改协议
- `standards/DEVELOPMENT_WORKFLOW.md` - 开发工作流

---

**记住**: Git 是你最好的朋友，频繁 commit 和 push 才是保持进度同步的王道！
