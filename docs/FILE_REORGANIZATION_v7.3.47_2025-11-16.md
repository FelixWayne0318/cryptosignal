# 文件重组报告 v7.3.47

**日期**: 2025-11-16
**版本**: v7.3.47
**目的**: 清理项目结构，整理文档和删除过时文件

## 📋 重组内容

### 1. 文档整理

#### 移动到 docs/ 目录
以下文档从根目录移动到 `docs/` 目录：

- `EXECUTIVE_SUMMARY_2025-11-16.md` → `docs/EXECUTIVE_SUMMARY_2025-11-16.md`
- `SYSTEM_AUDIT_REPORT_v7.3.46_2025-11-16.md` → `docs/SYSTEM_AUDIT_REPORT_v7.3.46_2025-11-16.md`
- `URGENT_FIX_NOW.md` → `docs/URGENT_FIX_NOW.md`

**原因**: 统一文档管理，保持根目录整洁

### 2. 删除过时文件

#### 临时脚本
- `IMMEDIATE_FIX.sh` - FactorConfig临时修复脚本（问题已解决）
- `cleanup_script.sh` - v7.3.46清理脚本（已过时）

#### 诊断文件
- `diagnose/test_factorconfig_fix.py` - FactorConfig诊断脚本（问题已修复，不再需要）

**原因**: 这些文件创建用于临时诊断和修复，现在相关问题已经彻底解决

### 3. 新增工具

#### 依赖分析工具
- `analyze_dependencies_v2.py` - 系统依赖分析工具
- `dependency_analysis_report.json` - 依赖分析报告

**功能**:
- 从系统入口点分析所有被使用的文件
- 识别未使用的Python文件
- 自动分类文档（standards/docs/tests/diagnose）
- 生成详细的依赖关系图

## 📊 依赖分析结果

### Python文件统计
- **总计**: 75 个
- **使用中**: 61 个
- **未使用**: 14 个

### 未使用文件说明

以下文件虽然未被直接导入，但**保留的原因**：

#### `__init__.py` 文件（10个）
- 作用：定义Python包结构
- 保留原因：即使不被导入，也是包定义必需的

#### 监控模块（2个）
- `ats_core/monitoring/vif_monitor.py` - VIF监控（多重共线性检测）
- `ats_core/monitoring/ic_monitor.py` - IC监控（因子失效检测）
- 保留原因：v7.3.47新功能，预留的监控系统

#### 工具模块（2个）
- `ats_core/config/path_resolver.py` - 统一路径解析器
- `ats_core/utils/degradation.py` - 降级策略框架
- 保留原因：工具类模块，可能被动态调用或未来使用

### 文档统计
- **规范文档**: 22 个（standards/）
- **说明文档**: 42 个（docs/）
- **测试文档**: 1 个（tests/）
- **诊断文档**: 1 个（diagnose/）

## 🗂️ 当前目录结构

```
cryptosignal/
├── ats_core/              # 核心代码
│   ├── analysis/          # 分析模块
│   ├── config/            # 配置管理
│   ├── data/              # 数据处理
│   ├── execution/         # 执行模块
│   ├── factors_v2/        # 因子系统
│   ├── modulators/        # 调制器
│   ├── monitoring/        # 监控系统 (v7.3.47新增)
│   ├── outputs/           # 输出格式化
│   ├── pipeline/          # 分析流水线
│   └── utils/             # 工具函数
├── config/                # 配置文件
├── scripts/               # 脚本文件
├── docs/                  # 📄 说明文档
├── standards/             # 📋 规范文档
├── tests/                 # 🧪 测试文件（预留）
├── diagnose/              # 🔍 诊断文件（预留）
├── reports/               # 📊 报告文件
├── setup.sh               # 一键部署脚本
├── auto_restart.sh        # 自动重启脚本
├── force_restart.sh       # 强制重启脚本（运维工具）
└── README.md              # 项目说明
```

## ✅ 重组效果

### 改进
1. **文档结构更清晰**: 所有文档按类型分类存放
2. **根目录更整洁**: 只保留必要的配置和脚本
3. **维护性提升**: 通过依赖分析工具，可以定期检查文件使用情况
4. **删除冗余**: 移除了3个过时的临时文件

### 保留的关键文件
1. **运维脚本**: `force_restart.sh` 作为完善的运维工具保留
2. **核心功能**: 所有正在使用的Python模块
3. **预留功能**: 监控系统和工具模块为未来功能预留

## 📖 相关文档

- **系统架构**: `standards/02_ARCHITECTURE.md`
- **规范索引**: `standards/00_INDEX.md`
- **文档规则**: `standards/DOCUMENTATION_RULES.md`
- **修改规则**: `standards/MODIFICATION_RULES.md`

## 🔧 使用依赖分析工具

```bash
# 运行依赖分析
python3 analyze_dependencies_v2.py

# 查看详细报告
cat dependency_analysis_report.json
```

## 📝 后续建议

1. **定期运行依赖分析**: 每次大版本发布前运行分析，清理未使用文件
2. **文档更新**: 保持文档与代码同步更新
3. **监控系统集成**: 未来版本可以集成VIF和IC监控功能
4. **测试完善**: 在`tests/`目录添加单元测试和集成测试

---

**生成工具**: analyze_dependencies_v2.py
**分析基准**: scripts/realtime_signal_scanner.py (系统入口点)
**Python文件覆盖率**: 81.3% (61/75)
