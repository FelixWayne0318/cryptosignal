# CryptoSignal v7.3.2-Full

> **加密货币信号分析系统 - v7.3.2-Full I因子重构版**
> v7.3.2-Full: I因子BTC-only回归 + MarketContext全局优化 + veto风控
>
> **核心改进**: I因子零硬编码 + BTC-only回归 + MarketContext 400x性能提升 + I因子veto风控

---

## 🚀 快速部署

### 一键全自动部署（推荐）⭐⭐⭐

```bash
cd ~/cryptosignal
./setup.sh  # 全自动：检测环境、安装依赖、部署、启动
```

**功能**:
- ✅ 自动环境检测（Python、pip、git、screen）
- ✅ 自动依赖安装
- ✅ 自动配置检查
- ✅ 自动启动系统

详细文档见: [standards/deployment/DEPLOYMENT_GUIDE.md](standards/deployment/DEPLOYMENT_GUIDE.md)

---

## 📚 规范文档体系

> ⚠️ **重要**: 所有规范文档已统一到 `standards/` 目录

### 快速导航

| 角色 | 推荐文档 | 优先级 |
|------|---------|--------|
| **新用户** | [standards/deployment/QUICK_START.md](standards/deployment/QUICK_START.md) | ⭐⭐⭐⭐⭐ |
| **运维人员** | [standards/deployment/DEPLOYMENT_GUIDE.md](standards/deployment/DEPLOYMENT_GUIDE.md) | ⭐⭐⭐⭐⭐ |
| **开发人员** | [standards/01_SYSTEM_OVERVIEW.md](standards/01_SYSTEM_OVERVIEW.md) | ⭐⭐⭐⭐⭐ |
| **量化研究** | [standards/specifications/FACTOR_SYSTEM.md](standards/specifications/FACTOR_SYSTEM.md) | ⭐⭐⭐⭐ |

### 完整索引

→ **[standards/00_INDEX.md](standards/00_INDEX.md)** - 规范文档总索引（入口）

---

## 🎯 系统版本

**当前版本**: v7.3.2-Full (I因子BTC-only重构 + MarketContext优化)
**更新日期**: 2025-11-15

### v7.3.2-Full: I因子系统重构

✅ **I因子BTC-only回归**
- 移除ETH依赖，使用纯BTC Beta回归
- alt_ret = α + β_BTC * btc_ret + ε
- 更清晰的统计模型，log-return计算

✅ **I因子veto风控逻辑**
- 规则1: 高Beta币逆BTC强趋势 → 自动拦截
- 规则2: 高Beta币弱信号 → 不交易
- 规则3: 高独立币 → 放宽阈值（50→45）

✅ **MarketContext全局优化**
- BTC趋势全局计算1次/扫描（vs 400次重复）
- 性能提升：~400x（BTC趋势计算部分）
- 统一market_meta传递到所有analyze_symbol调用

✅ **零硬编码架构**
- 所有因子参数从配置文件读取
- RuntimeConfig统一管理，支持验证和缓存
- 易于调优和维护

---

### v7.2 Stage 1: 规则增强（历史版本）

✅ **F因子v2：精确资金主导判断**
- F_v2 = (fund_momentum - price_momentum) / ATR
- 标准化后取tanh()映射到[-1, 1]
- 精确识别资金领先/滞后情况

✅ **因子分组：降低共线性**
- TC组 (50%): T因子 + C因子（趋势+资金）
- VOM组 (35%): V因子 + O因子 + M因子（流动性+订单簿+动量）
- B组 (15%): B因子（基础面）

✅ **统计校准：Bootstrap模式**
- P = 0.40 + (confidence/100) × 0.30
- 基于历史数据的置信度映射
- 避免过度自信

✅ **四重门控：硬过滤机制**
- 数据质量门：OHLCV有效性
- 资金支撑门：F_v2 > 阈值
- 市场风险门：波动率控制
- 执行成本门：滑点可承受

✅ **数据采集：为Stage 2准备**
- 自动记录所有信号到SQLite数据库
- 目标：500+样本用于统计优化
- 路径：data/trade_history.db

详见: [docs/v72_stage1_detailed_plan.md](docs/v72_stage1_detailed_plan.md)

---

## 📦 主要功能

### 核心系统

- **6+4因子系统**
  - A层6因子: T/M/C/V/O/B (权重总和100%，方向评分)
  - B层4调制器: L/S/F/I (权重0%，调节position/Teff/cost/confidence)
- **四门系统** (DataQual/EV/Execution/Probability)
- **防抖动机制** (K/N=1/2入场确认)
- **三层止损** (结构>订单簿>ATR)

---

## 🏃 运行方式

### 主入口文件

```bash
# 单次扫描
python3 scripts/realtime_signal_scanner.py

# 定期扫描（每5分钟）
python3 scripts/realtime_signal_scanner.py --interval 300

# 测试模式（10个币种）
python3 scripts/realtime_signal_scanner.py --max-symbols 10
```

### 后台运行（Screen）

```bash
# 启动Screen会话
screen -S cryptosignal
python3 scripts/realtime_signal_scanner.py --interval 300

# 分离会话: Ctrl+A 然后 D
# 重连会话: screen -r cryptosignal
```

---

## ⚙️ 配置文件

### 核心配置

- **`config/params.json`** - 权重、阈值、发布参数
- **`config/telegram.json`** - Telegram通知配置
- **`config/binance_credentials.json`** - Binance API凭证

### 当前权重配置（v6.7 P2.2）

```json
{
  "weights": {
    "T": 24.0,  "M": 10.0,  "C": 27.0,
    "V": 12.0,  "O": 21.0,  "B": 6.0,
    "L": 0.0,   "S": 0.0,   "F": 0.0,   "I": 0.0
  }
}
```

**要求**: A层6因子总和必须=100.0%，B层调制器(L/S/F/I)=0%

**权重分层**:
- Layer 1 (价格行为 46%): T(24%) + M(10%) + V(12%)
- Layer 2 (资金流 48%): C(27%) + O(21%)
- Layer 3 (微观结构 6%): B(6%)

详见: [standards/configuration/PARAMS_SPEC.md](standards/configuration/PARAMS_SPEC.md)

---

## 📊 项目结构

```
cryptosignal/
├── standards/                    # ⭐ 规范文档（统一入口）
│   ├── 00_INDEX.md              # 总索引
│   ├── 01_SYSTEM_OVERVIEW.md    # 系统概览
│   ├── 03_VERSION_HISTORY.md    # 版本历史
│   ├── specifications/          # 规范子系统
│   ├── deployment/              # 部署运维
│   ├── configuration/           # 配置管理
│   └── development/             # 开发指南
│
├── scripts/
│   └── realtime_signal_scanner.py   # ⭐ 主入口
│
├── ats_core/                    # 核心代码
│   ├── pipeline/                # 分析流水线
│   ├── factors_v2/              # 因子计算
│   ├── modulators/              # 调制器
│   ├── gates/                   # 四门系统
│   ├── publishing/              # 发布系统
│   └── outputs/                 # 输出格式化
│
├── config/                      # 配置文件
│   ├── params.json
│   ├── telegram.json
│   └── binance_credentials.json
│
├── tests/                       # 测试文件
├── diagnose/                    # 诊断工具
├── docs/                        # 文档
│   ├── analysis/               # 分析报告
│   └── archive/                # 历史文档
│
├── setup.sh                     # ⭐ 一键部署脚本
└── deploy_and_run.sh            # 部署并运行脚本
```

---

## 🔬 测试

### 快速测试

```bash
# 测试10个币种
python3 scripts/realtime_signal_scanner.py --max-symbols 10 --no-telegram

# 运行诊断
python3 diagnose/diagnostic_scan.py
```

详见: [tests/README.md](tests/README.md)

---

## 🎓 学习路径

### 新用户

1. 阅读: [01_SYSTEM_OVERVIEW.md](standards/01_SYSTEM_OVERVIEW.md)
2. 部署: `./setup.sh`
3. 配置: [deployment/TELEGRAM_SETUP.md](standards/deployment/TELEGRAM_SETUP.md)

### 开发人员

1. 系统概览: [01_SYSTEM_OVERVIEW.md](standards/01_SYSTEM_OVERVIEW.md)
2. 架构设计: [02_ARCHITECTURE.md](standards/02_ARCHITECTURE.md)
3. 因子规范: [specifications/FACTOR_SYSTEM.md](standards/specifications/FACTOR_SYSTEM.md)
4. 开发流程: [development/WORKFLOW.md](standards/development/WORKFLOW.md)

---

## ⚠️ 注意事项

1. **规范文档**：所有规范已统一到 `standards/` 目录
2. **版本**: 当前为v6.7 P2.2（权重优化版本）
3. **主入口**: `scripts/realtime_signal_scanner.py`
4. **部署脚本**: `setup.sh` → `deploy_and_run.sh`
5. **配置**: 修改 `config/params.json` 后需清除缓存

---

## 📞 支持

- **规范文档**: [standards/00_INDEX.md](standards/00_INDEX.md)
- **快速参考**: [standards/reference/QUICK_REFERENCE.md](standards/reference/QUICK_REFERENCE.md)
- **问题反馈**: GitHub Issues

---

**版本**: v6.7 P2.2
**最后更新**: 2025-11-05
**分支**: claude/reorganize-repo-structure-011CUrZaXUMTBXApc3jvsqTh
