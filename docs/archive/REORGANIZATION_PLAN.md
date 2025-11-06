# 仓库重组计划

**执行时间**: 2025-11-05
**目标**: 清理根目录，规范文件结构

## 📁 文件分类

### 保留在根目录（关键运行文件）
- ✅ setup.sh - 系统入口
- ✅ deploy_and_run.sh - 部署脚本
- ✅ auto_restart.sh - 定时重启
- ✅ README.md - 项目说明
- ✅ requirements.txt - 依赖文件

### 移动到 diagnose/（诊断系统）
- diagnostic_scan.py
- diagnostic_with_telegram.py
- run_diagnostic.sh
- run_diagnostic_telegram.sh
- DIAGNOSTIC_GUIDE.md
- DIAGNOSTIC_README.md
- CRITICAL_DIAGNOSIS_REPORT.md

### 移动到 docs/analysis/（分析报告）
- AUDIT_EXECUTIVE_SUMMARY.md
- COMPLIANCE_AUDIT_REPORT.md
- COMPREHENSIVE_AUDIT_SUMMARY.md
- COMPREHENSIVE_SYSTEM_AUDIT_2025-11-04.md
- SYSTEM_AUDIT_COMPREHENSIVE.md
- SYSTEM_AUDIT_REPORT_20251104.md
- SYSTEM_STATUS_REPORT.md
- RUNTIME_ANALYSIS_REPORT.md
- MARKET_FILTER_ANALYSIS.md
- PHASE1_COMPARISON_ANALYSIS.md
- PHASE1_DATA_LAYERS.md
- PHASE1_EVALUATION_AND_FIXES.md
- PHASE1_VERIFICATION_REPORT.md

### 移动到 docs/legacy/（过时文档/修复记录）
- EV_CALCULATION_BUG_FIX.md
- PROB_BONUS_THRESHOLD_FIX.md
- P_MIN_CALCULATION_FIX.md
- ORDERBOOK_UPDATE_SOLUTION.md
- PRIME_STRENGTH_AND_MODULATORS_EXPLAINED.md
- REPOSITORY_REFACTORING_PLAN.md
- TODO_GATE_INTEGRATION.md

### 移动到 docs/deployment/（部署文档）
- DEPLOYMENT_GUIDE.md (检查是否与standards重复)
- DEPLOY_AUDIT_BRANCH.md
- DATA_UPDATE_SCHEDULE.md
- QUICKSTART.md (检查是否与standards重复)

### 移动到 tests/（测试相关）
- TEST_GUIDE_V66.md
- test_scan.sh
- test_verbose_output.sh
- verify_phase1_code.sh

### 删除（过时/重复文件）
- deploy_v6.1.sh (过时版本)
- execute_refactoring.sh (临时脚本)
- fix_compliance_issues.sh (临时脚本)
- verify_refactoring.sh (临时脚本)
- run_background.sh (被deploy_and_run.sh替代)
- run_production.sh (被deploy_and_run.sh替代)
- run_with_screen.sh (被deploy_and_run.sh替代)
- start.sh (被setup.sh替代)
- start_production.sh (被deploy_and_run.sh替代)
- stop.sh (功能简单，可用pkill替代)

### 保留的工具脚本
- check_status.sh - 状态检查工具
- view_logs.sh - 日志查看工具

## 🗑️ 代码清理

### 删除未使用的代码
- ats_core/outputs/telegram_fmt_v66.py (未被引用，实际用的是telegram_fmt.py)

### 检查deprecated目录
- deprecated/pipeline/ - 确认是否全部过时

## ✅ 验证清单

- [ ] 所有规范文档在 standards/
- [ ] 所有说明文档在 docs/
- [ ] 所有测试文件在 tests/
- [ ] 所有诊断文件在 diagnose/
- [ ] 根目录只保留关键运行文件
- [ ] 删除所有过时文件
- [ ] 系统仍能正常运行

