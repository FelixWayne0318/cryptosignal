# CryptoSignal - 自动化加密货币交易系统

![Version](https://img.shields.io/badge/version-2.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![Status](https://img.shields.io/badge/status-production--ready-success.svg)

## 🎯 项目简介

CryptoSignal 是一个世界级的加密货币自动交易系统，采用多维度因子分析、智能候选池管理和实时风险控制。

### 核心特性

- ✅ **14维度因子分析** (7基础 + 7增强因子)
- ✅ **WebSocket实时优化** (17倍提速，<200ms延迟)
- ✅ **智能候选池** (4层过滤 + 异常检测)
- ✅ **自动交易执行** (动态止损/止盈 + RL优化)
- ✅ **完整回测系统** (历史验证 + 性能分析)
- ✅ **Telegram实时推送** (专业6D消息格式)

---

## 📂 项目结构

```
/cryptosignal/
├── ats_core/        # 核心交易系统 (14,766 LOC)
├── ats_backtest/    # 回测框架
├── tests/           # 测试套件 (单元/集成/诊断)
├── tools/           # 开发工具
├── scripts/         # 生产脚本
├── deploy/          # 部署脚本
├── config/          # 配置文件
├── data/            # 数据存储
└── docs/            # 文档 (50+ MD文件)
```

**详细结构说明**: 请查看 [PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md)

---

## 🚀 快速开始

### 1. 环境要求

- Python 3.11+
- 币安API账户
- Telegram Bot Token

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

创建 `.env` 文件：

```bash
# 币安API
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# 交易模式
ENABLE_REAL_TRADING=false  # true=真实交易
USE_OPTIMIZED_SCAN=true    # WebSocket优化
```

### 4. 运行系统

```bash
# 开发模式 (快速测试)
python tools/full_run_v2_fast.py

# 生产模式 (自动交易)
python scripts/run_auto_trader.py

# systemd服务 (推荐)
systemctl start cryptosignal
```

---

## 📊 系统架构

### 14维度因子系统

#### 基础因子 (7+1)
- **T** (Trend): 趋势分析
- **M** (Momentum): 动量
- **C** (CVD): 累积成交量差
- **V** (Volume): 成交量
- **S** (Structure): 结构质量
- **O** (OI): 持仓量
- **E** (Environment): 市场环境
- **F** (Fund Leading): 资金领先 (调节器)

#### 增强因子 (7)
- **C+** (Enhanced CVD): 动态加权CVD
- **O+** (OI Regime): OI四象限系统
- **V+** (Volume Trigger): 成交量+触发K
- **L** (Liquidity): 订单簿流动性
- **B** (Basis+Funding): 基差+资金费率
- **Q** (Liquidation): 清算密度
- **I** (Independence): 独立性 (Alpha)

### 核心工作流

```
数据获取 → 因子计算 → 统一评分 → 信号生成 → 自动执行 → 风险管理
   ↓           ↓          ↓          ↓          ↓          ↓
Binance → 14维度分析 → ±100评分 → TRADE/WATCH → 开仓/平仓 → TP/SL动态调整
```

---

## 🧪 测试

```bash
# 单元测试
pytest tests/ -v

# 集成测试
python tests/integration/test_seven_dimensions.py

# 诊断工具
python tests/diagnostics/diagnose_and_fix.py

# 回测
python tools/run_backtest.py
```

---

## 🚢 部署

### 服务器部署 (一键部署)

```bash
cd deploy
chmod +x deploy_to_server.sh
./deploy_to_server.sh
```

### 手动部署

```bash
# 1. 克隆仓库
git clone https://github.com/FelixWayne0318/cryptosignal.git
cd cryptosignal

# 2. 安装依赖
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. 配置环境
cp .env.example .env
# 编辑.env填入API密钥

# 4. 启动服务
python scripts/run_auto_trader.py
```

详细部署指南: [docs/SERVER_DEPLOYMENT_GUIDE.md](./docs/SERVER_DEPLOYMENT_GUIDE.md)

---

## 📚 文档

| 文档 | 说明 |
|------|------|
| [PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md) | 项目结构详解 |
| [docs/UNIFIED_SYSTEM_ARCHITECTURE.md](./docs/UNIFIED_SYSTEM_ARCHITECTURE.md) | 系统架构 |
| [docs/AUTO_TRADING_DEPLOYMENT.md](./docs/AUTO_TRADING_DEPLOYMENT.md) | 自动交易部署 |
| [docs/WEBSOCKET_OPTIMIZATION_ANALYSIS.md](./docs/WEBSOCKET_OPTIMIZATION_ANALYSIS.md) | WebSocket优化 |
| [docs/BACKTEST_SYSTEM.md](./docs/BACKTEST_SYSTEM.md) | 回测系统 |

**完整文档列表**: 查看 [docs/](./docs/) 目录 (50+ 文档)

---

## 🔧 开发

### 目录规范

- 核心功能 → `ats_core/`
- 单元测试 → `tests/`
- 集成测试 → `tests/integration/`
- 诊断工具 → `tests/diagnostics/`
- 开发工具 → `tools/`
- 生产脚本 → `scripts/`
- 部署脚本 → `deploy/`

### 提交规范

```bash
# 功能开发
git commit -m "feat: 添加新因子X"

# 修复bug
git commit -m "fix: 修复候选池缓存问题"

# 重构
git commit -m "refactor: 重组项目结构"

# 文档
git commit -m "docs: 更新部署指南"
```

---

## 📈 性能指标

| 指标 | 数值 |
|------|------|
| 扫描速度 | 5秒/100币种 (17x提速) |
| API调用 | 0次/扫描 (WebSocket缓存) |
| 信号延迟 | <200ms (实时监控) |
| 代码行数 | 27,709行 Python |
| 测试覆盖 | 25+ 测试文件 |

---

## ⚠️ 风险提示

- 加密货币交易存在高风险，可能导致本金损失
- 系统默认为**模拟模式**，请充分测试后再启用真实交易
- 建议设置合理的风险参数 (止损、最大仓位、日损失上限)

---

## 📝 版本历史

- **v2.0** (2025-10-27): 项目结构重组 + 14维度集成系统
- **v1.5** (2025-10): WebSocket优化 + 候选池机制
- **v1.0** (2025-09): 初始发布

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📄 许可证

本项目为私有项目，未经授权禁止商业使用。

---

**当前分支**: `claude/system-repo-analysis-011CUXnjHZshGm6qPffCn8Ya`
**最后更新**: 2025-10-27
**系统状态**: ✅ 生产就绪
