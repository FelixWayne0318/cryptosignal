# 分支信息与部署指南

**生成时间**: 2025-11-08
**文档目的**: 说明v7.2重组分支信息和部署方式

---

## 📌 重要分支信息

### 当前使用的新分支（推荐）⭐

```
claude/reorganize-repo-structure-011CUvEzbqkdKuPnh33PSRPn
```

**创建时间**: 2025-11-08
**状态**: ✅ 最新、已推送到远程
**包含内容**:
- v7.2目录结构重组
- 环境变量控制自动提交
- 规范文档更新到v7.2
- 完整的重组说明文档

### 旧分支（已合并）

```
claude/reorganize-repo-structure-011CUrZaXUMTBXApc3jvsqTh
```

**状态**: ⚠️  已合并到主分支（见commit 700b10d）
**说明**: 这是之前的重组尝试，已被新分支取代

---

## 🚀 快速部署（一键执行）

### 统一入口：setup.sh（唯一推荐）⭐

```bash
cd /home/user/cryptosignal
./setup.sh
```

**setup.sh 自动执行**：
1. ✅ 拉取最新代码（git fetch + pull）
2. ✅ 清理Python缓存
3. ✅ 验证v7.2目录结构
4. ✅ 检测环境和依赖
5. ✅ 初始化数据库
6. ✅ 启动v7.2扫描器

### 手动执行步骤（不推荐）

```bash
cd /home/user/cryptosignal

# 1. 拉取远程分支信息
git fetch origin

# 2. 切换到新分支
git checkout claude/reorganize-repo-structure-011CUvEzbqkdKuPnh33PSRPn

# 3. 拉取最新代码
git pull origin claude/reorganize-repo-structure-011CUvEzbqkdKuPnh33PSRPn

# 4. 清理Python缓存（重要！）
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

# 5. 部署
./setup.sh
```

---

## 📋 新旧分支对比

### 主要差异

| 项目 | 旧分支 | 新分支 | 说明 |
|------|--------|--------|------|
| 环境变量控制 | ❌ 无 | ✅ 有 | `AUTO_COMMIT_REPORTS` 控制自动提交 |
| 重组总结文档 | ❌ 无 | ✅ 有 | `REORGANIZATION_SUMMARY.md` |
| 部署脚本 | ❌ 无 | ✅ 有 | `DEPLOY_V72_REORGANIZED.sh` |
| 规范文档版本 | v6.7 | v7.2 | 已更新版本号和说明 |
| 目录结构 | 相同 | 相同 | 都进行了文件重组 |

### 新分支的改进

1. **环境变量控制自动提交**
   - 添加 `AUTO_COMMIT_REPORTS` 环境变量
   - 支持手动测试时禁用自动提交
   - 解决git提交历史污染问题

2. **完善的文档**
   - `REORGANIZATION_SUMMARY.md` - 完整重组说明
   - `DEPLOY_V72_REORGANIZED.sh` - 一键部署脚本
   - `BRANCH_INFO.md` - 分支信息说明（本文档）

3. **版本更新**
   - 规范文档更新到v7.2
   - 添加v7.2新特性说明
   - 列出所有新增模块

---

## 🗂️ 重组后的目录结构

```
cryptosignal/
├── setup.sh ⭐                         # 一键部署入口
├── DEPLOY_V72_REORGANIZED.sh ⭐       # 新分支部署脚本（新增）
├── REORGANIZATION_SUMMARY.md 🆕       # 重组总结（新增）
├── BRANCH_INFO.md 🆕                  # 分支信息（本文档）
│
├── ats_core/                          # 核心代码
├── scripts/
│   ├── realtime_signal_scanner_v72.py # v7.2扫描器
│   └── auto_commit_reports.sh 🔧      # 支持环境变量控制（修改）
│
├── tests/ 🆕                          # 测试文件（重组）
│   ├── test_*.py (9个)
│   └── run_server_tests.sh
│
├── diagnose/ 🆕                       # 诊断文件（重组）
│   ├── diagnose_v72_issue.py
│   └── fix_v72_paths.py
│
├── docs/ 🆕                           # 文档文件（重组）
│   ├── SERVER_TEST_*.md
│   └── v72_*.md
│
└── standards/ 🔧                      # 规范文档（v7.2）
    └── 00_INDEX.md                    # 已更新到v7.2
```

---

## ⚙️ 环境变量控制

### AUTO_COMMIT_REPORTS

控制扫描报告是否自动提交到git。

**默认值**: `true` （自动提交）

**使用场景**:

1. **服务器自动运行**（默认）
   ```bash
   # 不需要设置，默认启用自动提交
   ./setup.sh
   ```

2. **手动测试**（禁用提交）
   ```bash
   # 设置环境变量禁用自动提交
   export AUTO_COMMIT_REPORTS=false
   python3 scripts/realtime_signal_scanner_v72.py --max-symbols 20
   ```

---

## 🔧 常见问题

### Q1: 我应该使用哪个分支？

**A**: 使用新分支 `claude/reorganize-repo-structure-011CUvEzbqkdKuPnh33PSRPn`

这是最新的分支，包含所有改进和完善的文档。

### Q2: 旧分支还能用吗？

**A**: 旧分支 `claude/reorganize-repo-structure-011CUrZaXUMTBXApc3jvsqTh` 已被合并到主分支。

建议使用新分支，因为它包含更多改进。

### Q3: 如何禁用自动提交？

**A**: 设置环境变量：
```bash
export AUTO_COMMIT_REPORTS=false
```

### Q4: 部署后如何验证？

**A**: 检查以下内容：
```bash
# 1. 查看分支
git branch --show-current

# 2. 验证目录结构
ls tests/ diagnose/ docs/

# 3. 检查v7.2扫描器
ps aux | grep realtime_signal_scanner_v72

# 4. 查看状态
./check_v72_status.sh
```

---

## 📚 参考文档

- **重组总结**: [REORGANIZATION_SUMMARY.md](REORGANIZATION_SUMMARY.md)
- **规范索引**: [standards/00_INDEX.md](standards/00_INDEX.md)
- **系统概览**: [standards/01_SYSTEM_OVERVIEW.md](standards/01_SYSTEM_OVERVIEW.md)
- **部署指南**: [standards/deployment/DEPLOYMENT_GUIDE.md](standards/deployment/DEPLOYMENT_GUIDE.md)

---

**维护者**: Claude AI Assistant
**最后更新**: 2025-11-08
