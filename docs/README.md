# CryptoSignal Documentation

## 📚 v7.2 核心文档（新增）

### 系统架构与接口
- **`SYSTEM_ARCHITECTURE.md`** - 系统架构与依赖关系图
  - 系统分层架构说明
  - 模块依赖关系可视化
  - 数据流向图

- **`INTERFACES.md`** - 模块接口规范
  - 所有模块的API文档
  - 函数签名、输入参数、返回值说明
  - 用于Claude Project快速理解接口

- **`CLAUDE_PROJECT_IMPORT_GUIDE.md`** - Claude Project导入指南
  - 核心文件与接口文件分类
  - 代码导入优先级建议
  - 压缩导入策略（38.6%代码量覆盖100%功能）

### 代码质量保障（v7.3.2 新增）
- **`CODE_HEALTH_CHECK_GUIDE.md`** - 代码级体检方法论指南 ⭐ **推荐**
  - 体检三原则（对照驱动、分层检查、证据链）
  - 四步检查法（核心实现、调用链、配置管理、错误处理）
  - 问题分级标准（P0-P3）
  - 工具和技巧（搜索命令、魔法数字扫描脚本）
  - **用途**: 标准化代码审查流程，发现P0级硬伤和架构偏差

- **`CODE_HEALTH_CHECK_TEMPLATE.md`** - 可复用体检报告模板
  - 标准报告结构（状态评估、硬伤识别、修复路线图）
  - 完整证据链格式（文件+行号+代码片段+影响分析）
  - **用途**: 直接复制模板，填入检查结果，生成规范报告

- **`CODE_HEALTH_CHECKLIST.md`** - 快速检查清单
  - ⚡ 10分钟快速版（PR前自查）
  - 📋 2小时完整版（子系统重构后审查）
  - **用途**: 逐项打勾，确保不遗漏关键检查点

### 因子系统设计
- **`FACTOR_SYSTEM_COMPLETE_DESIGN.md`** - 因子系统完整设计（v7.3.2-Full）
  - I因子BTC-only回归算法详解
  - I因子veto风控逻辑
  - MarketContext全局优化（400x性能提升）
  - 零硬编码架构说明

### 版本变更文档
- **`REPOSITORY_CLEANUP_v7.2.43.md`** - v7.2.43仓库清理记录
- **`V7242_P1_HIGH_GATE6_THRESHOLD_ADJUSTMENT.md`** - Gate6阈值调整方案

---

## 📂 文档组织结构

### 📂 v6.6/ - v6.6版本设计文档
- 包含v6.6架构设计、实施计划等核心文档
- 这些文档是v6.6系统的权威参考

### 📂 analysis/ - 因子分析报告
- 因子性能分析、回测报告等

### 📂 archived/ - 历史文档归档
- 旧版本的规范、重构报告等

---

## 🔗 快速导航

### 对于新用户
1. 先阅读 `SYSTEM_ARCHITECTURE.md` 了解系统架构
2. 再阅读 `../README.md` 了解快速部署方法
3. 查看 `../standards/00_INDEX.md` 获取完整规范索引

### 对于开发者
1. 阅读 `INTERFACES.md` 了解所有模块接口
2. 阅读 `CLAUDE_PROJECT_IMPORT_GUIDE.md` 了解代码导入策略
3. 查看 `../standards/DEVELOPMENT_WORKFLOW.md` 了解开发流程

### 对于代码审查/体检 ⭐ 新增
1. **快速自查**: 阅读 `CODE_HEALTH_CHECKLIST.md` → 10分钟快速版
2. **完整审查**: 阅读 `CODE_HEALTH_CHECK_GUIDE.md` → 学习方法论
3. **生成报告**: 复制 `CODE_HEALTH_CHECK_TEMPLATE.md` → 填入检查结果
4. **参考案例**: 查看本次I因子体检实践（见上文体检报告）

**使用场景**:
- ⚡ PR提交前自查（10分钟版）
- 🔍 子系统重构后审查（2小时完整版）
- 🚨 上线前P0硬伤扫描
- 📊 季度/半年度代码库健康检查

### 对于量化研究
1. 查看 `FACTOR_SYSTEM_COMPLETE_DESIGN.md` 了解v7.3.2-Full因子系统
2. 查看 `../standards/specifications/FACTOR_SYSTEM.md` 了解因子体系
3. 阅读 `analysis/` 目录下的因子分析报告

---

## 📋 主要文档索引

### v7.3.2 新增文档
- `CODE_HEALTH_CHECK_GUIDE.md` - 代码体检方法论（**质量保障必读** ⭐）
- `CODE_HEALTH_CHECK_TEMPLATE.md` - 体检报告模板
- `CODE_HEALTH_CHECKLIST.md` - 快速检查清单
- `FACTOR_SYSTEM_COMPLETE_DESIGN.md` - 因子系统完整设计（v7.3.2-Full）

### v7.2 系统文档
- `SYSTEM_ARCHITECTURE.md` - 系统架构图（**推荐**）
- `INTERFACES.md` - 接口规范（**开发必读**）
- `CLAUDE_PROJECT_IMPORT_GUIDE.md` - Claude Project导入指南

### v6.6 核心文档
- `v6.6/V6.6_FINAL_IMPLEMENTATION_PLAN.md` - v6.6最终实施计划
- `v6.6/MODULATOR_DESIGN_V6.6.md` - 调制器系统设计
- `v6.6/ARCHITECTURE_DISCUSSION_V6.6.md` - 架构讨论

### 分析报告
- `analysis/FACTOR_ANALYSIS_COMPREHENSIVE.md` - 因子综合分析
- `analysis/FACTOR_ANALYSIS_EXECUTIVE_SUMMARY.md` - 执行摘要

### 系统规范（权威）
请查看 `../standards/` 目录获取系统规范文档
