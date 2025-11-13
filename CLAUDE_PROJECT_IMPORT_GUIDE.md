# Claude Project 导入指南

**系统版本**: v7.2.36  
**最后更新**: 2025-11-13  
**仓库大小**: 18M  
**文件总数**: 480个

---

## 📋 导入方案选择

### 方案A: 完整导入（推荐）✅

**适合**: 深度开发、系统重构、全面分析

**导入内容**:
```
✅ ats_core/ (103个Python文件) - 核心算法
✅ scripts/ (10个Python文件) - 运行脚本
✅ config/ (5个配置文件) - 系统配置
✅ docs/ (120个文档) - 完整文档
✅ standards/ (36个规范文档) - 开发规范
✅ tests/ (38个测试文件) - 测试代码
✅ diagnose/ (19个诊断文件) - 诊断工具
✅ README.md, setup.sh 等根文件

❌ data/ - 运行时数据（已排除）
❌ reports/ - 扫描报告（已排除）
❌ .git/ - Git仓库（已排除）
❌ __pycache__/ - Python缓存（已排除）
❌ archived/ - 归档文件（已排除）
```

**预计导入**:
- 文件数: ~340个
- 大小: ~12M
- 导入时间: 2-3分钟

**操作步骤**:
```bash
# 1. 确认.claudeignore已创建
cat .claudeignore

# 2. 清理Python缓存（可选）
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null

# 3. 在Claude.ai创建新Project
# 4. 上传整个cryptosignal目录
# 5. Claude会自动应用.claudeignore规则
```

---

### 方案B: 精简导入（轻量级）

**适合**: 快速开发、代码审查、配置调整

**导入内容**:
```
✅ ats_core/ - 核心算法（必需）
✅ scripts/realtime_signal_scanner.py - 主扫描器（必需）
✅ config/signal_thresholds.json - 阈值配置（必需）
✅ standards/SYSTEM_ENHANCEMENT_STANDARD.md - 开发规范（必需）
✅ docs/REPOSITORY_REORGANIZATION_REPORT.md - 系统报告（推荐）
✅ README.md, setup.sh - 入口文件（必需）

❌ tests/ - 测试文件
❌ diagnose/ - 诊断工具
❌ docs/analysis/ - 历史分析报告
❌ docs/version_updates/ - 版本更新文档
```

**预计导入**:
- 文件数: ~150个
- 大小: ~5M
- 导入时间: 1分钟

**操作步骤**:
```bash
# 创建精简版.claudeignore
cat > .claudeignore.minimal << 'EOF'
.git/
__pycache__/
*.pyc
data/
reports/
archived/
tests/
diagnose/
docs/analysis/
docs/version_updates/
docs/archive/
