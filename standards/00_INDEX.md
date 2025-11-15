# CryptoSignal 规范文档索引

**当前版本**: v7.3.2
**最后更新**: 2025-11-15
**文档类型**: 总索引（系统工程入口）

---

## 📚 文档体系说明

本文档体系遵循系统工程规范设计原则：
- **层次化**: 总索引 → 子系统规范 → 具体实现
- **唯一性**: 每个功能只在一个文件中描述
- **可追溯性**: 从需求到实现完全可追溯
- **完整性**: 可通过文档重建整个系统
- **版本化**: 明确的版本历史和变更记录

---

## 🔝 核心文档（按优先级）

### 1. 系统概览
- **[01_SYSTEM_OVERVIEW.md](01_SYSTEM_OVERVIEW.md)** - 系统整体架构和核心概念
- **[02_ARCHITECTURE.md](02_ARCHITECTURE.md)** - 技术架构和模块设计
- **[03_VERSION_HISTORY.md](03_VERSION_HISTORY.md)** - 版本历史和变更记录

### 2. 规范子系统 ([specifications/](specifications/))
- **[FACTOR_SYSTEM.md](specifications/FACTOR_SYSTEM.md)** - 6因子系统规范（T/M/C/V/O/B）
- **[MODULATORS.md](specifications/MODULATORS.md)** - L/S/F/I调制器规范（连续调节）
- **[PUBLISHING.md](specifications/PUBLISHING.md)** - Prime/Watch发布规范（v6.6软约束）
- **[NEWCOIN.md](specifications/NEWCOIN.md)** - 新币通道完整规范
- **[DATA_LAYER.md](specifications/DATA_LAYER.md)** - 数据层规范
- **[STOP_LOSS.md](specifications/STOP_LOSS.md)** - 三层止损系统规范（v6.6新增）
- **[INDEX.md](specifications/INDEX.md)** - 规范索引

### 3. 部署运维 ([deployment/](deployment/))
- **[QUICK_START.md](deployment/QUICK_START.md)** - 快速开始（新用户）
- **[DEPLOYMENT_GUIDE.md](deployment/DEPLOYMENT_GUIDE.md)** - 完整部署指南
- **[SERVER_OPERATIONS.md](deployment/SERVER_OPERATIONS.md)** - 服务器运维
- **[TELEGRAM_SETUP.md](deployment/TELEGRAM_SETUP.md)** - Telegram配置
- **[INDEX.md](deployment/INDEX.md)** - 部署索引

### 4. 配置管理 ([configuration/](configuration/))
- **[PARAMS_SPEC.md](configuration/PARAMS_SPEC.md)** - params.json配置规范
- **[CREDENTIALS.md](configuration/CREDENTIALS.md)** - API凭证配置
- **[WEIGHTS_TUNING.md](configuration/WEIGHTS_TUNING.md)** - 权重调优指南
- **[INDEX.md](configuration/INDEX.md)** - 配置索引

### 5. 开发指南
- **[DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md)** - Git提交规范和测试流程
- **[MODIFICATION_RULES.md](MODIFICATION_RULES.md)** - 日常配置和功能修改规范
- **[SYSTEM_ENHANCEMENT_STANDARD.md](SYSTEM_ENHANCEMENT_STANDARD.md)** - 🆕 系统性升级标准化流程（v3.2.0 - 含硬编码清理案例）
- **[DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md)** - 文档编写规范
- **[CORE_STANDARDS.md](CORE_STANDARDS.md)** - 核心开发标准

### 6. 参考资料 ([reference/](reference/))
- **[QUICK_REFERENCE.md](reference/QUICK_REFERENCE.md)** - 快速参考手册
- **[SCHEMAS.md](reference/SCHEMAS.md)** - 数据结构和接口定义
- **[INDEX.md](reference/INDEX.md)** - 参考索引

### 7. 补充文档（根目录）

> **注意**: 以下文档位于 standards/ 根目录，部分与子目录文档重复或为旧版本

#### 部署运维
- **[DEPLOYMENT_STANDARD.md](DEPLOYMENT_STANDARD.md)** - 服务器部署标准规范
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - 部署流程说明
- **[QUICK_DEPLOY.md](QUICK_DEPLOY.md)** - 快速部署参考卡
- **[SERVER_OPERATIONS.md](SERVER_OPERATIONS.md)** - 服务器运维指南
- **[TELEGRAM_SETUP.md](TELEGRAM_SETUP.md)** - Telegram配置指南

#### 配置管理
- **[CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)** - params.json 配置参数详解

#### 架构参考
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - 系统架构说明（v6.0版本，推荐阅读 02_ARCHITECTURE.md）

#### 其他
- **[STANDARDIZATION_REPORT.md](STANDARDIZATION_REPORT.md)** - 代码库规范化报告（2025-10-30）

---

## 🎯 快速导航

### 我是...

#### 新用户/运维人员
1. 开始 → [deployment/QUICK_START.md](deployment/QUICK_START.md)
2. 部署 → [deployment/DEPLOYMENT_GUIDE.md](deployment/DEPLOYMENT_GUIDE.md)
3. 配置 → [configuration/PARAMS_SPEC.md](configuration/PARAMS_SPEC.md)

#### 开发人员
1. 了解系统 → [01_SYSTEM_OVERVIEW.md](01_SYSTEM_OVERVIEW.md)
2. 架构设计 → [02_ARCHITECTURE.md](02_ARCHITECTURE.md)
3. 核心规范 → [specifications/FACTOR_SYSTEM.md](specifications/FACTOR_SYSTEM.md)
4. 日常开发 → [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md)
5. 配置修改 → [MODIFICATION_RULES.md](MODIFICATION_RULES.md)
6. 🆕 系统升级 → [SYSTEM_ENHANCEMENT_STANDARD.md](SYSTEM_ENHANCEMENT_STANDARD.md) (v3.2.0)

#### 想了解变更历史
→ [03_VERSION_HISTORY.md](03_VERSION_HISTORY.md)

#### 查找特定功能
→ 使用对应子目录的INDEX.md索引

---

## 📋 系统工程追溯矩阵

| 需求 | 规范文档 | 实现模块 | 测试 | 部署脚本 |
|------|---------|---------|------|---------|
| 6因子系统 | [FACTOR_SYSTEM.md](specifications/FACTOR_SYSTEM.md) | `ats_core/factors_v2/` | - | - |
| L/S/F/I调制器 | [MODULATORS.md](specifications/MODULATORS.md) | `ats_core/modulators/modulator_chain.py` | - | - |
| Prime发布（软约束） | [PUBLISHING.md](specifications/PUBLISHING.md) | `ats_core/publishing/anti_jitter.py` | - | - |
| 新币通道 | [NEWCOIN.md](specifications/NEWCOIN.md) | `ats_core/data_feeds/newcoin_data.py` | `test_phase2.py` | - |
| 三层止损 | [STOP_LOSS.md](specifications/STOP_LOSS.md) | `ats_core/execution/stop_loss_calculator.py` | - | - |
| 实时扫描 | [01_SYSTEM_OVERVIEW.md](01_SYSTEM_OVERVIEW.md) | `scripts/realtime_signal_scanner.py` | - | `deploy_and_run.sh` |
| Telegram富媒体 | [PUBLISHING.md](specifications/PUBLISHING.md) | `ats_core/outputs/telegram_fmt_v66.py` | - | - |

---

## 📝 文档维护规范

### 修改原则
1. **唯一性**: 每个功能点只在一处描述
2. **完整性**: 修改时同步更新所有相关文档
3. **版本化**: 重大变更必须更新VERSION_HISTORY.md
4. **可追溯**: 在追溯矩阵中记录文档-代码映射

### 新增文档
1. 确定所属子目录
2. 更新对应INDEX.md
3. 在本文档（00_INDEX.md）中添加链接
4. 如涉及新功能，更新追溯矩阵

### 废弃文档
1. 不删除，移至 `archive/` 目录
2. 在原位置留下重定向说明
3. 更新所有索引文件

---

## 🔗 外部资源

- **项目仓库**: https://github.com/FelixWayne0318/cryptosignal
- **当前分支**: `claude/reorganize-repo-structure-011CUrZaXUMTBXApc3jvsqTh`
- **问题追踪**: GitHub Issues

---

## 📞 帮助与支持

如果您在使用文档时遇到问题：
1. 检查对应子目录的INDEX.md
2. 查看VERSION_HISTORY.md了解最新变更
3. 参考QUICK_REFERENCE.md快速手册
4. 在GitHub提交Issue

---

**文档版本**: v7.2
**生效日期**: 2025-11-08
**维护责任**: 系统架构师

---

## 🆕 v7.2 版本更新说明

### 核心改进
1. **F因子v2**：精确定义的资金流因子（基于CVD动量）
2. **因子分组**：TC/VOM/B三组因子（提升稳健性）
3. **四道闸门**：数据质量/EV/执行性/概率四重过滤
4. **统计校准**：经验校准器（真实胜率预测）
5. **完善数据库**：7张表系统（analysis.db）支持全量数据采集

### 新增模块
- `ats_core/features/fund_leading.py` - F因子v2计算
- `ats_core/scoring/factor_groups.py` - 因子分组评分
- `ats_core/pipeline/gates.py` - 四道闸门过滤
- `ats_core/calibration/empirical_calibration.py` - 统计校准
- `ats_core/data/analysis_db.py` - 完善分析数据库
- `scripts/realtime_signal_scanner_v72.py` - v7.2集成扫描器

### 启动方式
```bash
# 使用 setup.sh 一键部署（推荐）
./setup.sh

# 或手动启动v7.2扫描器
python3 scripts/realtime_signal_scanner_v72.py --interval 300
```
