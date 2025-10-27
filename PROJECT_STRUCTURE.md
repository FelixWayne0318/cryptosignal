# CryptoSignal 项目结构说明

## 📋 版本信息
- **重组日期**: 2025-10-27
- **当前分支**: claude/system-repo-analysis-011CUXnjHZshGm6qPffCn8Ya
- **重组目标**: 清理根目录混乱文件，建立清晰的项目结构

---

## 📂 完整目录结构

```
/home/user/cryptosignal/
│
├── 📁 ats_core/                       # 核心交易系统模块 (14,766 LOC)
│   ├── config/                        # 配置管理
│   │   └── factor_config.py           # 统一因子配置加载器
│   │
│   ├── database/                      # 数据持久化层
│   │   ├── models.py                  # SQLAlchemy ORM模型
│   │   └── operations.py              # CRUD操作
│   │
│   ├── execution/                     # 交易执行引擎
│   │   ├── auto_trader.py             # 主控制器 (WebSocket + REST)
│   │   ├── binance_futures_client.py  # 异步币安期货客户端
│   │   ├── position_manager.py        # 动态仓位管理 (带RL)
│   │   └── signal_executor.py         # 信号转交易执行
│   │
│   ├── factors_v2/                    # 10+1维度因子系统 (v2.0)
│   │   ├── basis_funding.py           # B因子: 基差+资金费率
│   │   ├── cvd_enhanced.py            # C+因子: 增强型CVD
│   │   ├── independence.py            # I因子: 独立性(Alpha)
│   │   ├── liquidation.py             # Q因子: 清算密度
│   │   ├── liquidity.py               # L因子: 订单簿流动性
│   │   ├── oi_regime.py               # O+因子: OI四象限系统
│   │   └── volume_trigger.py          # V+因子: 成交量+触发K
│   │
│   ├── features/                      # 特征计算模块 (7+1基础因子)
│   │   ├── trend.py                   # T因子: 趋势
│   │   ├── momentum.py                # M因子: 动量
│   │   ├── cvd.py                     # CVD计算核心
│   │   ├── cvd_flow.py                # C因子: CVD资金流
│   │   ├── volume.py                  # V因子: 成交量
│   │   ├── structure_sq.py            # S因子: 结构质量
│   │   ├── open_interest.py           # O因子: 持仓量
│   │   ├── environment.py             # E因子: 市场环境
│   │   ├── fund_leading.py            # F因子: 资金领先(调节器)
│   │   ├── accel.py                   # A因子: 加速度(已弃用)
│   │   ├── ta_core.py                 # 技术分析核心
│   │   ├── scoring_utils.py           # 统一评分工具
│   │   ├── market_regime.py           # 市场状态识别
│   │   ├── microconfirm_15m.py        # 15分钟微观确认
│   │   ├── multi_timeframe.py         # 多时间框架分析
│   │   └── pricing.py                 # 入场/出场价格计算
│   │
│   ├── outputs/                       # 输出/通知模块
│   │   ├── telegram_fmt.py            # 消息格式化 (6D模板)
│   │   └── publisher.py               # 电报消息发送
│   │
│   ├── pipeline/                      # 数据处理管道
│   │   ├── main.py                    # 入口点
│   │   ├── batch_scan.py              # 批量扫描 (带候选池优化)
│   │   ├── batch_scan_optimized.py    # WebSocket优化批量扫描
│   │   ├── analyze_symbol.py          # 单交易对分析核心 (7+1D)
│   │   └── analyze_symbol_v2.py       # v2.0: 10+1D集成系统
│   │
│   ├── pools/                         # 候选池管理
│   │   ├── base_builder.py            # 基础宇宙构建器
│   │   ├── elite_builder.py           # 精英池构建器 (4层过滤)
│   │   ├── overlay_builder.py         # 叠加池 (异常检测)
│   │   ├── pool_manager.py            # 统一池管理器 (缓存)
│   │   └── main.py                    # 池编排
│   │
│   ├── rl/                            # 强化学习模块
│   │   └── dynamic_stop_loss.py       # DQN止损优化
│   │
│   ├── scoring/                       # 评分系统
│   │   ├── scorecard.py               # 统一±100评分聚合
│   │   ├── probability.py             # 概率计算 v1.0
│   │   ├── probability_v2.py          # v2.0: F调整概率
│   │   └── adaptive_weights.py        # 状态依赖权重自适应
│   │
│   ├── sources/                       # 数据源模块
│   │   ├── binance.py                 # 币安REST API (urllib)
│   │   ├── binance_safe.py            # 限流币安API
│   │   ├── klines.py                  # K线数据获取
│   │   ├── oi.py                      # 持仓量数据
│   │   └── tickers.py                 # 行情数据
│   │
│   ├── streaming/                     # WebSocket流式数据
│   │   └── websocket_client.py        # 实时币安WebSocket客户端
│   │
│   ├── data/                          # 实时数据管理
│   │   └── realtime_kline_cache.py    # WebSocket K线缓存
│   │
│   ├── utils/                         # 工具模块
│   │   └── rate_limiter.py            # 令牌桶限流器
│   │
│   ├── tools/                         # 内部防过拟合工具
│   │   └── anti_overfitting/
│   │       ├── cross_validator.py
│   │       ├── factor_correlation.py
│   │       └── ic_monitor.py
│   │
│   ├── cfg.py                         # 统一配置加载器
│   ├── logging.py                     # 标准化日志工具
│   └── backoff.py                     # 指数退避重试机制
│
├── 📁 ats_backtest/                   # 回测框架
│   ├── data_loader.py                 # 历史数据加载
│   ├── engine.py                      # 回测引擎核心
│   ├── metrics.py                     # 性能指标计算
│   └── report.py                      # 回测报告生成
│
├── 📁 tests/                          # 测试套件 (重新组织)
│   ├── test_auto_trader.py            # 单元测试: 自动交易器
│   ├── test_factors_v2.py             # 单元测试: v2.0因子
│   │
│   ├── 📁 integration/                # 集成测试 (从根目录移入)
│   │   ├── test_seven_dimensions.py   # 7D系统验证
│   │   ├── test_cvd_consistency.py    # CVD一致性检查
│   │   ├── test_cvd_consistency_impl.py
│   │   ├── test_cvd_optimization.py   # CVD优化验证
│   │   ├── test_cvd_signed_score.py   # 带符号评分系统
│   │   ├── test_elite_universe.py     # 精英池构建测试
│   │   ├── test_fund_leading_signed.py # 资金领先指标测试
│   │   ├── test_gold_integration.py   # 黄金因子集成
│   │   ├── test_improved_cvd_logic.py # CVD逻辑改进
│   │   ├── test_optimizations.py      # 系统优化测试
│   │   ├── test_pool_architecture.py  # 池架构设计
│   │   ├── test_pool_build.py         # 池构建流程
│   │   └── test_spot_cvd_integration.py # 现货CVD集成
│   │
│   └── 📁 diagnostics/                # 诊断工具 (从根目录移入)
│       ├── diagnose_and_fix.py        # 系统诊断工具
│       ├── diagnose_zero_scores.py    # 零分诊断
│       └── fix_binance_access.py      # 币安API访问验证
│
├── 📁 tools/                          # 开发工具
│   ├── full_run.py                    # 完整7D分析运行器
│   ├── full_run_elite.py              # 精英池专用运行器
│   ├── full_run_v2.py                 # v2.0 10+1D管道
│   ├── full_run_v2_fast.py            # 快速WebSocket v2.0
│   ├── generate_backtest_signals.py   # 历史信号生成
│   ├── run_backtest.py                # 回测执行器
│   ├── run_real_backtest.py           # 真实回测 (实时数据)
│   ├── run_workflow_backtest.py       # 工作流回测
│   ├── manual_run.py                  # 手动信号生成
│   ├── send_symbol.py                 # 发送手动交易信号
│   ├── send_text.py                   # 发送原始电报消息
│   ├── scan_watch.py                  # 实时监控扫描
│   ├── quick_run.py                   # 快速管道测试
│   ├── self_check.py                  # 系统健康检查
│   ├── diagnose_*.py                  # 诊断工具集
│   ├── test_new_coin.py               # 新币种验证
│   ├── test_new_format.py             # 格式验证
│   ├── generate_mock_price_data.py    # 合成价格数据
│   ├── generate_test_signals.py       # 测试信号生成
│   ├── collect_six_dim_stats.py       # 维度统计收集
│   │
│   └── 📁 utilities/                  # 实用工具 (新建)
│       └── update_pools.py            # 候选池更新脚本 (从根目录移入)
│
├── 📁 scripts/                        # 生产脚本 (保持不变)
│   ├── run_auto_trader.py             # 生产启动器
│   ├── init_database.py               # 数据库初始化
│   ├── query_stats.py                 # 统计查询
│   ├── test_integrated_trader.py      # 集成测试
│   ├── test_optimized_scan.py         # WebSocket优化测试
│   └── *.sh                           # Shell实用脚本
│
├── 📁 deploy/                         # 部署脚本 (新建目录)
│   ├── deploy_to_server.sh            # 完整服务器部署 (从根目录移入)
│   ├── deploy_fixes.sh                # 热修复部署 (从根目录移入)
│   ├── setup_telegram.sh              # 电报配置 (从根目录移入)
│   └── configure_telegram_prod.sh     # 生产电报设置 (从根目录移入)
│
├── 📁 config/                         # 配置文件 (保持不变)
│   ├── params.json                    # 主参数 (200+配置项)
│   ├── factors_unified.json           # v2.0因子配置
│   └── blacklist.json                 # 交易对黑名单
│
├── 📁 data/                           # 数据目录 (保持不变)
│   ├── reports/                       # 扫描报告 (JSON)
│   ├── backtest/                      # 回测缓存和结果
│   │   └── cache/
│   └── database/                      # SQLite数据库
│
├── 📁 docs/                           # 文档 (50+ Markdown文件)
│   ├── UNIFIED_SYSTEM_ARCHITECTURE.md
│   ├── AUTO_TRADING_DEPLOYMENT.md
│   ├── WEBSOCKET_OPTIMIZATION_ANALYSIS.md
│   ├── BACKTEST_SYSTEM.md
│   ├── SERVER_DEPLOYMENT_GUIDE.md
│   ├── POOL_OPTIMIZATION_IMPLEMENTATION.md
│   ├── CRITICAL_BUGFIXES_2025.md
│   └── ... (45+ more comprehensive docs)
│
├── 📄 README.md                       # 项目概述
├── 📄 PROJECT_STRUCTURE.md            # 本文档 (项目结构说明)
├── 📄 requirements.txt                # Python依赖
└── 📄 .gitignore                      # Git忽略规则
```

---

## 🔄 本次重组变更摘要

### 移动的文件 (17个文件)

#### 测试文件 → `tests/integration/` (13个文件)
- ✅ `test_seven_dimensions.py`
- ✅ `test_cvd_consistency.py`
- ✅ `test_cvd_consistency_impl.py`
- ✅ `test_cvd_optimization.py`
- ✅ `test_cvd_signed_score.py`
- ✅ `test_elite_universe.py`
- ✅ `test_fund_leading_signed.py`
- ✅ `test_gold_integration.py`
- ✅ `test_improved_cvd_logic.py`
- ✅ `test_optimizations.py`
- ✅ `test_pool_architecture.py`
- ✅ `test_pool_build.py`
- ✅ `test_spot_cvd_integration.py`

#### 诊断工具 → `tests/diagnostics/` (3个文件)
- ✅ `diagnose_and_fix.py`
- ✅ `diagnose_zero_scores.py`
- ✅ `fix_binance_access.py`

#### 部署脚本 → `deploy/` (4个文件)
- ✅ `deploy_to_server.sh` (已更新分支名)
- ✅ `deploy_fixes.sh` (已更新分支名)
- ✅ `setup_telegram.sh`
- ✅ `configure_telegram_prod.sh`

#### 工具脚本 → `tools/utilities/` (1个文件)
- ✅ `update_pools.py` (从根目录移入，删除旧版本)

### 删除的文件 (1个文件)
- ❌ `tools/update_pools.py` (旧版本，已被utilities/下的新版本替代)

### 更新的文件 (2个文件)
- ✅ `deploy/deploy_to_server.sh` - 更新分支名为 `claude/system-repo-analysis-011CUXnjHZshGm6qPffCn8Ya`
- ✅ `deploy/deploy_fixes.sh` - 更新分支名为 `claude/system-repo-analysis-011CUXnjHZshGm6qPffCn8Ya`

---

## 📊 目录用途说明

### 核心模块

| 目录 | 用途 | 代码行数 |
|------|------|---------|
| `ats_core/` | 核心交易系统 | 14,766 |
| `ats_backtest/` | 回测框架 | ~750 |

### 测试与验证

| 目录 | 用途 | 文件数 |
|------|------|--------|
| `tests/` | 单元测试 | 2 |
| `tests/integration/` | 集成测试 | 13 |
| `tests/diagnostics/` | 诊断工具 | 3 |

### 工具与脚本

| 目录 | 用途 | 文件数 |
|------|------|--------|
| `tools/` | 开发工具 | 20+ |
| `tools/utilities/` | 实用工具 | 1 |
| `scripts/` | 生产脚本 | 10+ |
| `deploy/` | 部署脚本 | 4 |

### 配置与数据

| 目录 | 用途 | 说明 |
|------|------|------|
| `config/` | 配置文件 | JSON配置 (200+参数) |
| `data/` | 数据存储 | 报告、缓存、数据库 |
| `docs/` | 文档 | 50+ Markdown文档 |

---

## 🎯 使用指南

### 运行测试

```bash
# 单元测试
cd /home/user/cryptosignal
pytest tests/test_auto_trader.py -v
pytest tests/test_factors_v2.py -v

# 集成测试
python tests/integration/test_seven_dimensions.py
python tests/integration/test_pool_architecture.py

# 诊断工具
python tests/diagnostics/diagnose_and_fix.py
python tests/diagnostics/fix_binance_access.py
```

### 部署到服务器

```bash
# 完整部署 (首次部署)
cd /home/user/cryptosignal/deploy
chmod +x deploy_to_server.sh
./deploy_to_server.sh

# 热修复部署 (代码更新)
chmod +x deploy_fixes.sh
./deploy_fixes.sh

# 配置电报
chmod +x setup_telegram.sh
./setup_telegram.sh
```

### 运行开发工具

```bash
# 完整分析运行
python tools/full_run_v2_fast.py

# 回测
python tools/run_backtest.py

# 手动信号生成
python tools/manual_run.py BTCUSDT

# 更新候选池
python tools/utilities/update_pools.py --elite
```

### 生产运行

```bash
# 启动自动交易器
python scripts/run_auto_trader.py

# 使用systemd服务
systemctl start cryptosignal
systemctl status cryptosignal
journalctl -u cryptosignal -f
```

---

## 🔑 关键变更说明

### 1. 根目录整洁化
- **之前**: 根目录有20+个测试文件和脚本，非常混乱
- **之后**: 根目录仅保留核心模块目录和关键配置文件

### 2. 测试文件分类
- **integration/**: 集成测试（多模块交互）
- **diagnostics/**: 诊断和修复工具
- **根级tests/**: 单元测试（单模块测试）

### 3. 部署脚本独立
- 新建 `deploy/` 目录存放所有部署相关脚本
- 方便生产环境部署和维护
- 已更新分支名称以匹配当前分支

### 4. 工具脚本组织
- `tools/` - 现有开发工具保持不变
- `tools/utilities/` - 新增实用工具子目录
- `scripts/` - 生产脚本保持不变

---

## 📝 维护建议

### 新增文件时的目录选择

| 文件类型 | 推荐位置 | 示例 |
|---------|---------|------|
| 核心功能代码 | `ats_core/` | 新因子、新特征 |
| 单元测试 | `tests/` | `test_new_feature.py` |
| 集成测试 | `tests/integration/` | `test_full_pipeline.py` |
| 诊断工具 | `tests/diagnostics/` | `diagnose_xxx.py` |
| 开发工具 | `tools/` | 运行器、生成器 |
| 实用脚本 | `tools/utilities/` | 更新、清理脚本 |
| 生产脚本 | `scripts/` | 启动器、初始化 |
| 部署脚本 | `deploy/` | 部署、配置脚本 |
| 文档 | `docs/` | Markdown文档 |

### Git提交建议

```bash
# 提交本次重组
git add -A
git commit -m "refactor: 重组项目结构，清理根目录

- 移动13个测试文件到tests/integration/
- 移动3个诊断工具到tests/diagnostics/
- 移动4个部署脚本到deploy/
- 移动update_pools.py到tools/utilities/
- 删除旧版update_pools.py
- 更新部署脚本分支名称
- 创建PROJECT_STRUCTURE.md说明文档

根目录现在更加整洁，项目结构更加清晰。"
```

---

## 🚀 系统完整功能概览

### 核心能力

1. **多维度因子分析** (7+1基础 + 7增强 = 14因子)
   - 方向因子: T, M, C/C+, V/V+, O/O+
   - 质量因子: S, E, L, B, Q
   - 调节因子: F (资金领先)
   - 独立性因子: I

2. **智能候选池管理**
   - Elite Pool: 24小时缓存 (4层过滤)
   - Overlay Pool: 1小时缓存 (异常检测)
   - WebSocket优化: 17倍提速

3. **自动交易执行**
   - WebSocket实时监控 (<200ms延迟)
   - 动态止损/止盈 (RL优化)
   - 分层出场 (TP1: 50%, TP2: 50%)
   - 风险管理 (最大仓位、杠杆限制)

4. **回测系统**
   - 历史信号生成
   - OHLC模拟交易
   - 性能指标: Sharpe, Sortino, 最大回撤

5. **监控与通知**
   - 电报实时推送
   - 6D专业消息格式
   - 系统健康检查

---

## 📞 支持与反馈

如有问题或建议，请参考:
- 详细文档: `docs/UNIFIED_SYSTEM_ARCHITECTURE.md`
- 部署指南: `docs/SERVER_DEPLOYMENT_GUIDE.md`
- 问题追踪: GitHub Issues

---

**重组完成时间**: 2025-10-27
**当前版本**: v2.0 (10+1维度集成系统)
**系统状态**: ✅ 生产就绪
