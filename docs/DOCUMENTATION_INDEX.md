# CryptoSignal v7.2 文档索引

**版本**: v7.2.24
**更新日期**: 2025-11-11

---

## 📚 文档导航

### 🚀 快速开始 (5分钟上手)

1. **[快速参考卡](./QUICK_REFERENCE_CARD.md)** ⭐ 推荐首读
   - 一键启动命令
   - 核心指标速查表
   - 五道闸门阈值
   - Telegram消息解读
   - 常用命令速查
   - 故障排查

---

### 📖 核心文档 (深入理解系统)

2. **[完整系统架构](./SYSTEM_ARCHITECTURE_COMPLETE.md)** ⭐ 核心文档
   - 系统启动流程 (setup.sh → 数据库 → 扫描器)
   - 信号生成完整流程 (5阶段详解)
   - 10个因子详细计算 (A层6个 + B层4个)
   - 阈值配置体系 (3个配置文件)
   - 权重分配机制 (v7.2分组 + v6.7旧版)
   - 五道闸门系统 (逻辑 + 代码示例)
   - Telegram消息发布 (模板 + Emoji方案)
   - 配置文件索引

3. **[实战示例](./PRACTICAL_EXAMPLES.md)** ⭐ 实用指南
   - 实际扫描流程 (日志示例)
   - 完美信号案例分析 (ETHUSDT)
   - 拒绝信号案例 (Gate 2/4/5失败)
   - 配置调优实战 (增加/减少信号)
   - 真实交易场景 (完整周期)

---

### 🔧 配置与调优

4. **配置文件说明**
   - `config/signal_thresholds.json` - v7.2主配置
   - `config/params.json` - 因子参数
   - `config/factors_unified.json` - 统一框架
   - `config/telegram.json` - Telegram配置
   - `config/binance_credentials.json` - API密钥

5. **阈值调优指南** (在[快速参考卡](./QUICK_REFERENCE_CARD.md#配置调整建议)中)
   - 提高信号质量 (减少数量)
   - 增加信号数量 (降低质量)
   - 平衡质量与数量

---

### 📊 版本历史与更新日志

6. **[v7.2.24 因子描述UX优化](./v7.2.24_FACTOR_DESCRIPTION_UX_IMPROVEMENT.md)**
   - 所有因子通俗化描述
   - 统一5色Emoji方案
   - 不同区域差异化图形
   - 消息示例对比

7. **[v7.2.23 Telegram模板回滚](./v7.2.23_TELEGRAM_TEMPLATE_ROLLBACK.md)**
   - v7.2.22回滚原因
   - F因子描述优化
   - 消息格式恢复

8. **[v7.2.21 Calibration日志修复](./v7.2.21_CALIBRATION_LOG_FIX.md)**
   - 单例模式实现
   - 日志污染消除 (406→1)

9. **配置变更日志** (`config/CHANGELOG.md`)
   - 完整配置历史
   - 阈值演变记录

---

### 🧑‍💻 开发文档

10. **[开发规范索引](../standards/00_INDEX.md)**
    - 代码规范
    - Git工作流
    - 文档规范
    - 测试规范

11. **[系统重组总结](../REORGANIZATION_SUMMARY.md)**
    - v7.2目录结构
    - tests/ 测试文件
    - diagnose/ 诊断工具
    - docs/ 文档组织

---

### 🗄️ 数据库文档

12. **数据库架构**
    - **TradeRecorder** (`data/trade_history.db`)
      - signals表: 交易信号记录
      - outcomes表: 实际结果跟踪
    - **AnalysisDB** (`data/analysis.db`)
      - market_data: 市场原始数据
      - factor_scores: 因子计算结果
      - signal_analysis: 信号分析数据
      - gate_evaluation: 闸门评估结果
      - modulator_effects: 调制器影响
      - signal_outcomes: 实际结果跟踪
      - scan_statistics: 扫描历史统计

---

## 🎯 按使用场景查找文档

### 场景1: 首次部署系统

**阅读顺序**:
1. [快速参考卡](./QUICK_REFERENCE_CARD.md) - 了解基本概念
2. 执行 `./setup.sh` - 一键启动
3. [实战示例](./PRACTICAL_EXAMPLES.md) - 查看实际运行

---

### 场景2: 理解信号生成逻辑

**阅读顺序**:
1. [系统架构 - 信号生成流程](./SYSTEM_ARCHITECTURE_COMPLETE.md#2-信号生成完整流程)
2. [系统架构 - 因子计算详解](./SYSTEM_ARCHITECTURE_COMPLETE.md#3-因子计算详解)
3. [系统架构 - 五道闸门系统](./SYSTEM_ARCHITECTURE_COMPLETE.md#6-五道闸门系统)

---

### 场景3: 解读Telegram消息

**阅读顺序**:
1. [快速参考卡 - Telegram消息解读](./QUICK_REFERENCE_CARD.md#telegram消息解读)
2. [快速参考卡 - 因子描述速查](./QUICK_REFERENCE_CARD.md#因子描述速查)
3. [v7.2.24文档 - Emoji配色方案](./v7.2.24_FACTOR_DESCRIPTION_UX_IMPROVEMENT.md)

---

### 场景4: 调整配置参数

**阅读顺序**:
1. [系统架构 - 阈值配置体系](./SYSTEM_ARCHITECTURE_COMPLETE.md#4-阈值配置体系)
2. [快速参考卡 - 配置调整建议](./QUICK_REFERENCE_CARD.md#配置调整建议)
3. [实战示例 - 配置调优实战](./PRACTICAL_EXAMPLES.md#4-配置调优实战)

---

### 场景5: 排查问题

**阅读顺序**:
1. [快速参考卡 - 故障排查](./QUICK_REFERENCE_CARD.md#故障排查)
2. 查看日志: `tail -100 ~/cryptosignal_*.log`
3. 检查配置: `cat config/signal_thresholds.json`

---

### 场景6: 理解历史版本变化

**阅读顺序**:
1. `config/CHANGELOG.md` - 配置变更
2. `docs/v7.2.24_*.md` - v7.2.24更新
3. `docs/v7.2.23_*.md` - v7.2.23更新
4. `docs/v7.2.21_*.md` - v7.2.21更新

---

## 📝 文档层级关系

```
docs/
├── DOCUMENTATION_INDEX.md          ← 你在这里 (总索引)
├── QUICK_REFERENCE_CARD.md         ← ⭐ 快速参考 (首读)
├── SYSTEM_ARCHITECTURE_COMPLETE.md ← ⭐ 完整架构 (核心)
├── PRACTICAL_EXAMPLES.md           ← ⭐ 实战示例 (实用)
│
├── v7.2.24_FACTOR_DESCRIPTION_UX_IMPROVEMENT.md
├── v7.2.23_TELEGRAM_TEMPLATE_ROLLBACK.md
├── v7.2.21_CALIBRATION_LOG_FIX.md
│
└── (其他历史版本文档...)
```

---

## 🔍 关键词索引

### A

- **Anti-Jitter (防抖)**: [系统架构#2.1](./SYSTEM_ARCHITECTURE_COMPLETE.md#21-流程总览图), [快速参考卡#常用命令](./QUICK_REFERENCE_CARD.md#常用命令)
- **AnalysisDB (分析数据库)**: [系统架构#8.2](./SYSTEM_ARCHITECTURE_COMPLETE.md#82-数据文件)

### B

- **Basis (基差)**: [系统架构#3.2.6](./SYSTEM_ARCHITECTURE_COMPLETE.md#326-b因子---基差资金费-basis--funding)
- **Batch Scan (批量扫描)**: [系统架构#2.1](./SYSTEM_ARCHITECTURE_COMPLETE.md#21-流程总览图), [实战示例#1.3](./PRACTICAL_EXAMPLES.md#13-扫描周期示例-12-15秒)
- **Beta (贝塔系数)**: [系统架构#3.3.2](./SYSTEM_ARCHITECTURE_COMPLETE.md#332-i因子---独立性-independence)

### C

- **Calibration (校准)**: [系统架构#4.4](./SYSTEM_ARCHITECTURE_COMPLETE.md#44-统计校准参数), [v7.2.21文档](./v7.2.21_CALIBRATION_LOG_FIX.md)
- **Capital Flow (资金流)**: [系统架构#3.2.3](./SYSTEM_ARCHITECTURE_COMPLETE.md#323-c因子---资金流-capital-flow--cvd)
- **Confidence (信心度)**: [快速参考卡#基础过滤](./QUICK_REFERENCE_CARD.md#基础过滤)
- **CVD (累积成交量差)**: [系统架构#3.2.3](./SYSTEM_ARCHITECTURE_COMPLETE.md#323-c因子---资金流-capital-flow--cvd)

### E

- **Emoji配色方案**: [快速参考卡#Emoji颜色含义](./QUICK_REFERENCE_CARD.md#emoji颜色含义), [v7.2.24文档](./v7.2.24_FACTOR_DESCRIPTION_UX_IMPROVEMENT.md)
- **EV (期望收益)**: [系统架构#6.4](./SYSTEM_ARCHITECTURE_COMPLETE.md#64-gate-3-期望收益)
- **Expected Value**: 见 EV

### F

- **Factor Groups (因子分组)**: [系统架构#5.1](./SYSTEM_ARCHITECTURE_COMPLETE.md#51-v72因子分组权重)
- **F因子 (资金领先)**: [系统架构#3.3.1](./SYSTEM_ARCHITECTURE_COMPLETE.md#331-f因子---资金领先性-fund-leading)
- **Five Gates (五道闸门)**: [系统架构#6](./SYSTEM_ARCHITECTURE_COMPLETE.md#6-五道闸门系统), [快速参考卡#五道闸门阈值](./QUICK_REFERENCE_CARD.md#五道闸门阈值)
- **Funding Rate (资金费率)**: [系统架构#3.2.6](./SYSTEM_ARCHITECTURE_COMPLETE.md#326-b因子---基差资金费-basis--funding)

### G

- **Gate 1 (数据质量)**: [系统架构#6.2](./SYSTEM_ARCHITECTURE_COMPLETE.md#62-gate-1-数据质量)
- **Gate 2 (资金支撑)**: [系统架构#6.3](./SYSTEM_ARCHITECTURE_COMPLETE.md#63-gate-2-资金支撑)
- **Gate 3 (期望收益)**: [系统架构#6.4](./SYSTEM_ARCHITECTURE_COMPLETE.md#64-gate-3-期望收益)
- **Gate 4 (胜率门槛)**: [系统架构#6.5](./SYSTEM_ARCHITECTURE_COMPLETE.md#65-gate-4-胜率门槛)
- **Gate 5 (I×Market)**: [系统架构#6.6](./SYSTEM_ARCHITECTURE_COMPLETE.md#66-gate-5-imarket对齐)

### I

- **Independence (独立性)**: [系统架构#3.3.2](./SYSTEM_ARCHITECTURE_COMPLETE.md#332-i因子---独立性-independence)
- **I因子**: 见 Independence

### K

- **Kelly仓位**: [系统架构#7.2](./SYSTEM_ARCHITECTURE_COMPLETE.md#72-消息结构解析)

### L

- **Liquidity (流动性)**: [系统架构#3.3.3](./SYSTEM_ARCHITECTURE_COMPLETE.md#333-l因子---流动性-liquidity)

### M

- **Market Regime (市场状态)**: [系统架构#6.6](./SYSTEM_ARCHITECTURE_COMPLETE.md#66-gate-5-imarket对齐)
- **Momentum (动量)**: [系统架构#3.2.2](./SYSTEM_ARCHITECTURE_COMPLETE.md#322-m因子---动量-momentum)

### O

- **Open Interest (持仓量)**: [系统架构#3.2.5](./SYSTEM_ARCHITECTURE_COMPLETE.md#325-o因子---持仓量-open-interest)

### P

- **Probability (胜率)**: [系统架构#6.5](./SYSTEM_ARCHITECTURE_COMPLETE.md#65-gate-4-胜率门槛)
- **Prime Signal**: [系统架构#2.1](./SYSTEM_ARCHITECTURE_COMPLETE.md#21-流程总览图)

### S

- **Setup.sh (启动脚本)**: [系统架构#1.1](./SYSTEM_ARCHITECTURE_COMPLETE.md#11-部署入口setupsh)
- **Structure (结构)**: [系统架构#3.3.4](./SYSTEM_ARCHITECTURE_COMPLETE.md#334-s因子---结构-structure)

### T

- **Telegram**: [系统架构#7](./SYSTEM_ARCHITECTURE_COMPLETE.md#7-telegram消息发布)
- **Threshold (阈值)**: [系统架构#4](./SYSTEM_ARCHITECTURE_COMPLETE.md#4-阈值配置体系), [快速参考卡#关键阈值表](./QUICK_REFERENCE_CARD.md#关键阈值表)
- **TradeRecorder (交易记录器)**: [系统架构#8.2](./SYSTEM_ARCHITECTURE_COMPLETE.md#82-数据文件)
- **Trend (趋势)**: [系统架构#3.2.1](./SYSTEM_ARCHITECTURE_COMPLETE.md#321-t因子---趋势强度-trend)

### V

- **Volume (量能)**: [系统架构#3.2.4](./SYSTEM_ARCHITECTURE_COMPLETE.md#324-v因子---量能-volume)
- **v7.2**: [系统架构#完整文档](./SYSTEM_ARCHITECTURE_COMPLETE.md)

### W

- **Weight (权重)**: [系统架构#5](./SYSTEM_ARCHITECTURE_COMPLETE.md#5-权重分配机制)
- **Win Rate**: 见 Probability

### 蓄

- **蓄势待发**: [快速参考卡#理解"蓄势待发"标记](./QUICK_REFERENCE_CARD.md#1-理解蓄势待发标记), [系统架构#3.3.1](./SYSTEM_ARCHITECTURE_COMPLETE.md#331-f因子---资金领先性-fund-leading)

---

## 🆘 获取帮助

### 文档问题

- **找不到需要的信息**: 使用Ctrl+F搜索本页关键词索引
- **文档过时**: 查看文件头部的"更新日期"
- **链接失效**: 检查文件路径是否正确

### 系统问题

- **启动失败**: [快速参考卡 - 故障排查](./QUICK_REFERENCE_CARD.md#故障排查)
- **无信号输出**: [实战示例 - 配置调优](./PRACTICAL_EXAMPLES.md#4-配置调优实战)
- **数据库错误**: [快速参考卡 - 问题3](./QUICK_REFERENCE_CARD.md#问题3-数据库错误)

### 社区支持

- **GitHub Issues**: https://github.com/FelixWayne0318/cryptosignal/issues
- **日志分析**: `tail -f ~/cryptosignal_*.log`

---

## 📈 文档维护

### 贡献指南

欢迎提交文档改进PR：
1. 遵循现有文档格式
2. 更新文档索引 (本文件)
3. 添加版本日期标记

### 文档版本

- **v1.0** (2025-11-11): 初始版本
  - 创建索引体系
  - 整合所有文档
  - 添加关键词索引

---

**文档索引版本**: v1.0
**最后更新**: 2025-11-11
**维护者**: CryptoSignal团队

---

## 快速跳转

- 🚀 [快速开始](./QUICK_REFERENCE_CARD.md)
- 📖 [完整架构](./SYSTEM_ARCHITECTURE_COMPLETE.md)
- 💡 [实战示例](./PRACTICAL_EXAMPLES.md)
- 🔧 [配置说明](./SYSTEM_ARCHITECTURE_COMPLETE.md#4-阈值配置体系)
- ⚠️ [故障排查](./QUICK_REFERENCE_CARD.md#故障排查)
