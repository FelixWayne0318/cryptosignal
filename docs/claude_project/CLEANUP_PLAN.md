# v7.2.36 最终清理计划

**检查时间**: 2025-11-13
**目标**: 只保留v7.2.36版本文件，删除所有旧版本和中间产物

---

## ✅ 核心运行文件验证

### 运行链路完整性检查

```
setup.sh
  └─> scripts/realtime_signal_scanner.py ✅ 存在
        └─> ats_core/pipeline/batch_scan_optimized.py ✅ 存在
              └─> ats_core/pipeline/analyze_symbol_v72.py ✅ 存在
                    ├─> ats_core/features/fund_leading.py ✅ 存在
                    ├─> ats_core/scoring/factor_groups.py ✅ 存在
                    ├─> ats_core/gates/integrated_gates.py ✅ 存在
                    └─> ats_core/calibration/empirical_calibration.py ✅ 存在
```

**导入测试**: ✅ v7.2引擎导入成功

---

## 📋 清理清单

### 1. 根目录.md文件（11个CLAUDE_PROJECT_*.md）

**保留（3个核心文件）**:
- ✅ CLAUDE_PROJECT_CONTEXT.md (413行) - 系统完整状态说明
- ✅ CLAUDE_PROJECT_INTERFACE.md (891行) - 接口规范和依赖关系
- ✅ CLAUDE_PROJECT_IMPORT_READY.md (413行) - 最终导入指南（最全）

**删除（8个中间产物）**:
- ❌ CLAUDE_PROJECT_IMPORT_GUIDE.md (93行) - 第一版导入指南，已被IMPORT_READY替代
- ❌ CLAUDE_PROJECT_GITHUB_IMPORT_GUIDE.md (438行) - GitHub导入指南，已整合到IMPORT_READY
- ❌ CLAUDE_PROJECT_MINIMAL_IMPORT.md (455行) - 精简导入方案，已整合
- ❌ CLAUDE_PROJECT_ULTRA_MINIMAL.md (412行) - 超精简方案，已整合
- ❌ CLAUDE_PROJECT_MINIMAL_CORE.md (414行) - 极简核心方案，已整合到IMPORT_READY
- ❌ CLAUDE_PROJECT_DEVELOPER_GUIDE.md (495行) - 开发者方案，已整合到IMPORT_READY
- ❌ CLAUDE_PROJECT_DATAFLOW_GUIDE.md (611行) - 数据流指南，已整合到IMPORT_READY
- ❌ CLAUDE_PROJECT_DEPENDENCY_CHECK.md (334行) - 依赖检查报告，关键信息已整合到INTERFACE.md

**其他根目录.md**:
- ✅ README.md - 项目说明（保留）
- ❌ REPOSITORY_REORGANIZATION_REPORT.md - 重组报告（可删除，工作已完成）

---

### 2. docs/目录（3个文件）

**当前文件**:
- docs/CHANGELOG.md (4147字节)
- docs/IMPORTANT_BRANCH_FIX.md (2890字节)
- docs/README.md (829字节)

**清理策略**:
- 检查CHANGELOG.md是否只包含7.2.36版本记录
- 检查IMPORTANT_BRANCH_FIX.md是否为旧版本问题
- docs/README.md保留

---

### 3. standards/目录（20个.md文件）

**当前文件**:
```
standards/
├─ 00_INDEX.md ✅ 索引（保留）
├─ SYSTEM_ENHANCEMENT_STANDARD.md ✅ 开发规范（保留）
├─ CORE_STANDARDS.md
├─ DEVELOPMENT_WORKFLOW.md
├─ 01_SYSTEM_OVERVIEW.md
├─ 02_ARCHITECTURE.md
├─ 03_VERSION_HISTORY.md
├─ deployment/ (5个文件)
│  ├─ INDEX.md
│  ├─ QUICK_START.md
│  ├─ DEPLOYMENT_GUIDE.md
│  ├─ TELEGRAM_SETUP.md
│  └─ SERVER_OPERATIONS.md
└─ specifications/ (8个文件)
   ├─ INDEX.md
   ├─ FACTOR_SYSTEM.md
   ├─ GATES.md
   ├─ MODULATORS.md
   ├─ EXECUTION.md
   ├─ DATAQUAL.md
   ├─ WEBSOCKET.md
   └─ NEWCOIN.md
```

**清理策略**:
- 检查每个文件是否包含旧版本引用
- 检查VERSION_HISTORY.md是否只记录7.2.36相关
- 检查SYSTEM_OVERVIEW.md, ARCHITECTURE.md是否为v7.2.36

---

### 4. tests/目录（20个.py文件）

**检查策略**:
```bash
# 没有发现v6.x, v7.0, v7.1相关的测试文件
# 当前测试文件都是v7.2相关：
# - test_v72_*.py
# - test_v7236_*.py
# - test_phase*.py（v7.2阶段测试）
```

**结论**: ✅ 测试文件都是v7.2版本，无需清理

---

### 5. diagnose/目录（9个.py文件）

**当前文件**:
```
diagnose/
├─ diagnose_v72_issue.py ✅ v7.2诊断
├─ diagnose_v72_gates.py ✅ v7.2闸门诊断
├─ diagnose_server_v72.py ✅ v7.2服务器诊断
├─ verify_v728_fix.py ✅ v7.2.8修复验证
├─ fix_v72_paths.py ✅ v7.2路径修复
├─ deep_gate_diagnosis.py ✅ 闸门深度诊断
├─ verify_config.py ✅ 配置验证
├─ debug_gates.py ✅ 闸门调试
└─ debug_telegram_error.py ✅ Telegram错误调试
```

**结论**: ✅ 诊断文件都是v7.2版本，无需清理

---

### 6. ats_core/目录（103个.py文件）

**检查策略**:
```bash
# 检查是否有带版本号的文件
# 检查是否有_old, _backup, _bak后缀的文件
```

**初步检查**: 未发现明显的旧版本文件

**需要详细检查的**:
- ats_core/pipeline/ 下是否有旧的analyze_symbol.py（非v72版本）
- ats_core/factors_v2/ 是否为旧版因子系统
- 是否有其他带版本标记的文件

---

### 7. 配置文件备份

**需要检查**:
```bash
config/*.backup
config/*.bak
config/*.old
*.example（是否需要）
```

---

## 🎯 清理执行计划

### Phase 1: 删除根目录中间产物.md（8个文件）

```bash
rm -f CLAUDE_PROJECT_IMPORT_GUIDE.md
rm -f CLAUDE_PROJECT_GITHUB_IMPORT_GUIDE.md
rm -f CLAUDE_PROJECT_MINIMAL_IMPORT.md
rm -f CLAUDE_PROJECT_ULTRA_MINIMAL.md
rm -f CLAUDE_PROJECT_MINIMAL_CORE.md
rm -f CLAUDE_PROJECT_DEVELOPER_GUIDE.md
rm -f CLAUDE_PROJECT_DATAFLOW_GUIDE.md
rm -f CLAUDE_PROJECT_DEPENDENCY_CHECK.md
rm -f REPOSITORY_REORGANIZATION_REPORT.md
```

### Phase 2: 检查并清理docs/内容

```bash
# 需要详细阅读CHANGELOG.md和IMPORTANT_BRANCH_FIX.md
# 确认是否只包含v7.2.36内容
```

### Phase 3: 检查standards/内容

```bash
# 检查VERSION_HISTORY.md
# 检查SYSTEM_OVERVIEW.md
# 检查ARCHITECTURE.md
# 确认是否有旧版本引用
```

### Phase 4: 检查ats_core/是否有旧版本文件

```bash
find ats_core -name "*v6*" -o -name "*v66*" -o -name "*v70*" -o -name "*v71*"
find ats_core -name "*_old.py" -o -name "*_backup.py" -o -name "*_bak.py"
```

### Phase 5: 清理配置备份

```bash
find config -name "*.backup" -o -name "*.bak" -o -name "*.old"
```

---

## ✅ 保留的核心文件结构

```
cryptosignal/
├─ README.md
├─ setup.sh
├─ auto_restart.sh
├─ deploy_and_run.sh
│
├─ CLAUDE_PROJECT_CONTEXT.md          ← 系统状态说明
├─ CLAUDE_PROJECT_INTERFACE.md        ← 接口规范
├─ CLAUDE_PROJECT_IMPORT_READY.md     ← 最终导入指南
│
├─ .claudeignore
├─ .claudeignore.dataflow
├─ .claudeignore.minimal
├─ .claudeignore.developer
│
├─ config/
│  ├─ signal_thresholds.json
│  ├─ binance_credentials.json
│  ├─ telegram.json
│  └─ params.json
│
├─ standards/
│  ├─ 00_INDEX.md
│  ├─ SYSTEM_ENHANCEMENT_STANDARD.md
│  ├─ deployment/
│  └─ specifications/
│
├─ docs/
│  ├─ CHANGELOG.md（检查后保留）
│  └─ README.md
│
├─ ats_core/（103个.py文件）
├─ scripts/
├─ tests/
└─ diagnose/
```

---

## 📊 预计清理效果

| 类别 | 删除数量 | 释放空间 |
|------|---------|---------|
| 根目录.md | 9个 | ~100KB |
| docs/*.md | 待定 | 待定 |
| standards/*.md | 待定 | 待定 |
| ats_core旧版本 | 待定 | 待定 |
| 配置备份 | 待定 | 待定 |

---

## ⚠️ 注意事项

1. **删除前备份**: 所有删除操作通过git进行，可随时恢复
2. **逐步验证**: 每个Phase完成后验证系统可运行性
3. **文档检查**: 仔细阅读docs/和standards/的内容，确认无重要信息丢失
4. **测试导入**: 确认系统可以正常导入

---

**下一步**: 等待确认清理计划，然后逐步执行
