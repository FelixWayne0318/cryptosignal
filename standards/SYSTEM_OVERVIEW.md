# CryptoSignal v6.0 系统总览

> **新对话框必读文档** - 快速了解整个系统架构

---

## 📌 项目概述

**CryptoSignal v6.0** 是一个基于币安合约市场的加密货币信号分析系统。

### 核心功能
- 实时扫描200个高流动性币种
- 10+1维因子分析系统（T/M/C/S/V/O/L/B/Q/I + F调节器）
- WebSocket优化（0次API调用/扫描，12-15秒/200币种）
- 自动发送Prime信号到Telegram
- v6.0权重百分比系统（总权重100%）

### 系统版本
- **当前版本**: v6.0（权重百分比模式）
- **升级时间**: 2025-10
- **主要变更**: 180分制 → 100%百分比系统，F因子参与评分

---

## 🚀 主文件入口

### **唯一运行主文件**
```
scripts/realtime_signal_scanner.py
```

**功能**：
- WebSocket实时扫描 + Telegram通知
- 支持单次扫描/持续扫描/定时扫描
- 性能：12-15秒/200币种，0 API调用

**运行方式**：
```bash
# 单次扫描
python3 scripts/realtime_signal_scanner.py --once

# 持续扫描（每5分钟）
python3 scripts/realtime_signal_scanner.py --interval 300

# 测试模式（只扫描20个币种）
python3 scripts/realtime_signal_scanner.py --max-symbols 20 --once
```

**命令行参数**：
- `--interval N`: 扫描间隔（秒），0=单次扫描
- `--min-score N`: 最低信号分数（默认70）
- `--max-symbols N`: 最大扫描币种数（测试用）
- `--no-telegram`: 不发送Telegram通知

---

## 📁 目录结构

```
cryptosignal/
│
├── scripts/                          # 脚本目录
│   ├── realtime_signal_scanner.py    # ⭐ 主文件（唯一运行入口）
│   ├── run_auto_trader.py            # 自动交易器（暂未使用）
│   ├── diagnose_network.py           # 网络诊断工具
│   ├── init_database.py              # 数据库初始化
│   └── query_stats.py                # 统计查询工具
│
├── ats_core/                         # 核心代码库
│   │
│   ├── pipeline/                     # 分析管道
│   │   ├── batch_scan_optimized.py   # ⭐ WebSocket批量扫描器
│   │   └── analyze_symbol.py         # ⭐ 单币种完整分析
│   │
│   ├── factors_v2/                   # 新增4维因子（v4.0+）
│   │   ├── liquidity.py              # L因子（流动性）
│   │   ├── basis_funding.py          # B因子（基差+资金费）
│   │   ├── liquidation.py            # Q因子（清算密度）
│   │   └── independence.py           # I因子（独立性）
│   │
│   ├── features/                     # 特征计算（6维基础因子+辅助）
│   │   ├── trend.py                  # T因子（趋势）
│   │   ├── momentum.py               # M因子（动量）
│   │   ├── cvd.py                    # C因子（资金流CVD）
│   │   ├── structure_sq.py           # S因子（结构）
│   │   ├── volume.py                 # V因子（量能）
│   │   ├── open_interest.py          # O因子（持仓量）
│   │   ├── fund_leading.py           # F因子（资金领先）
│   │   ├── multi_timeframe.py        # 多时间框架验证
│   │   ├── market_regime.py          # 市场趋势计算
│   │   └── ... （其他辅助特征）
│   │
│   ├── scoring/                      # 评分系统
│   │   ├── scorecard.py              # ⭐ 加权评分（10+1维）
│   │   ├── adaptive_weights.py       # ⭐ 自适应权重系统
│   │   ├── probability.py            # 概率映射
│   │   └── probability_v2.py         # 概率映射v2（sigmoid）
│   │
│   ├── sources/                      # 数据源
│   │   ├── binance.py                # 币安API封装
│   │   ├── binance_safe.py           # 安全模式API
│   │   ├── klines.py                 # K线数据
│   │   └── oi.py                     # 持仓量数据
│   │
│   ├── data/                         # 数据缓存
│   │   └── realtime_kline_cache.py   # ⭐ WebSocket K线缓存
│   │
│   ├── outputs/                      # 输出模块
│   │   └── telegram_fmt.py           # ⭐ Telegram消息格式化
│   │
│   ├── execution/                    # 交易执行
│   │   └── binance_futures_client.py # 币安合约客户端
│   │
│   ├── utils/                        # 工具库
│   │   ├── outlier_detection.py      # 离群点检测
│   │   ├── adaptive_params.py        # 自适应参数
│   │   └── rate_limiter.py           # 速率限制器
│   │
│   ├── cfg.py                        # ⭐ 配置加载器
│   ├── logging.py                    # 日志系统
│   └── backoff.py                    # 指数退避重试
│
├── config/                           # 配置文件
│   ├── params.json                   # ⭐ 核心参数配置（权重、阈值等）
│   └── telegram.json                 # Telegram配置（bot_token, chat_id）
│
├── docs/                             # 📚 说明文档（新增）
│   ├── SYSTEM_OVERVIEW.md            # ⭐ 系统总览（本文档）
│   ├── ARCHITECTURE.md               # 架构说明
│   ├── CONFIGURATION_GUIDE.md        # 配置指南
│   └── MODIFICATION_RULES.md         # 修改规范
│
├── tests/                            # 单元测试
│   ├── test_factors_v2.py
│   └── test_auto_trader.py
│
├── .gitignore                        # Git忽略配置
├── requirements.txt                  # Python依赖
└── README.md                         # 项目说明

```

---

## 🧠 核心概念

### 1. **10+1维因子系统**

**10维评分因子**：
- **Layer 1 - 价格行为层（36.1%）**
  - T（趋势，13.9%）：EMA趋势强度
  - M（动量，8.3%）：价格动量和加速度
  - S（结构，5.6%）：支撑阻力位
  - V（量能，8.3%）：成交量强度

- **Layer 2 - 资金流层（32.2%）**
  - C（资金流，11.1%）：CVD累积成交量差值
  - O（持仓，11.1%）：OI持仓量变化
  - F（资金领先，10.0%）：资金vs价格领先性 ⭐

- **Layer 3 - 微观结构层（25.0%）**
  - L（流动性，11.1%）：订单簿深度和滑点
  - B（基差，8.3%）：现货-合约基差+资金费率
  - Q（清算，5.6%）：清算密度热图

- **Layer 4 - 市场环境层（6.7%）**
  - I（独立性，6.7%）：与BTC/ETH相关性

**+1调节器**：
- F因子双重作用：
  1. 参与评分（权重10.0%）
  2. 极端值否决（F_aligned < -70时×0.7惩罚）

### 2. **v6.0权重百分比系统**

**总权重**：100%（从v5.0的180分制升级）

**权重配置**：`config/params.json` → `weights` 字段
```json
{
  "weights": {
    "T": 13.9, "M": 8.3, "C": 11.1, "S": 5.6,
    "V": 8.3, "O": 11.1, "L": 11.1, "B": 8.3,
    "Q": 5.6, "I": 6.7, "E": 0, "F": 10.0
  }
}
```

**评分公式**：
```python
weighted_score = Σ(score_i × weight_i) / Σ(weight_i)
```
范围：-100到+100（负数=看空，正数=看多）

### 3. **Prime信号判定**

**Prime强度计算**：
```python
prime_strength = confidence × 0.6 + prob_bonus
# confidence = abs(weighted_score)，范围0-100
# prob_bonus = (P_chosen - 0.60) / 0.15 × 40，最高40分
```

**Prime阈值**：
- v6.0：≥35分（适配100-base系统）
- v5.0：≥65分（180-base系统）

**判定条件**：
```python
is_prime = (prime_strength >= 35)
```

### 4. **自适应权重系统**

根据市场状态动态调整因子权重：
- **强势趋势**（|regime| > 60）：趋势因子权重↑
- **震荡市场**（|regime| < 30）：资金流因子权重↑
- **高波动**（vol > 0.03）：持仓量因子权重↑
- **低波动**（vol < 0.01）：趋势稳定性因子权重↑

**混合策略**：70%自适应 + 30%基础权重

---

## 🔑 关键文件

### **必读文件**（新对话框优先读取）
1. `docs/SYSTEM_OVERVIEW.md` - 本文档（系统总览）
2. `scripts/realtime_signal_scanner.py` - 主文件
3. `config/params.json` - 核心参数配置
4. `docs/MODIFICATION_RULES.md` - 修改规范

### **核心逻辑文件**
1. `ats_core/pipeline/analyze_symbol.py` - 单币种分析管道
2. `ats_core/pipeline/batch_scan_optimized.py` - 批量扫描器
3. `ats_core/scoring/scorecard.py` - 加权评分
4. `ats_core/scoring/adaptive_weights.py` - 自适应权重
5. `ats_core/outputs/telegram_fmt.py` - Telegram格式化

---

## ⚙️ 配置文件

### 1. **config/params.json**
**核心参数配置**（修改频率：中）

关键字段：
- `weights`: 10+1维因子权重（总和100%）
- `publish`: Prime/Watch信号阈值
- `trend`, `momentum`, `cvd_flow`, ... : 各因子具体参数
- `liquidity`, `basis_funding`, `liquidation`, `independence`: 新增4维参数

### 2. **config/telegram.json**
**Telegram配置**（修改频率：低）

```json
{
  "bot_token": "YOUR_BOT_TOKEN",
  "chat_id": "YOUR_CHAT_ID",
  "enabled": true
}
```

---

## 🔄 数据流

```
1. 数据获取
   sources/binance* → data/realtime_kline_cache (WebSocket)

2. 因子计算
   analyze_symbol.py → features/* + factors_v2/*

3. 评分系统
   scoring/scorecard.py + scoring/adaptive_weights.py

4. Prime判定
   analyze_symbol.py (prime_strength >= 35)

5. 批量扫描
   batch_scan_optimized.py (200个币种)

6. Prime过滤
   realtime_signal_scanner.py (s.get('publish', {}).get('prime'))

7. Telegram发送
   outputs/telegram_fmt.py → Telegram API
```

---

## 📊 性能指标

- **初始化时间**: 3-4分钟（首次WebSocket缓存）
- **扫描速度**: 12-15秒/200币种
- **API调用**: 0次/扫描（使用WebSocket缓存）
- **内存占用**: ~100-200MB
- **推荐扫描间隔**: 5分钟（300秒）

---

## 🚨 常见问题

### Q1: 修改权重后没有生效？
**A**: 清除Python缓存：
```bash
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
```

### Q2: Prime信号没有发送到Telegram？
**A**: 检查以下几点：
1. `config/telegram.json` 配置是否正确
2. Prime信号是否真的产生（查看日志："Prime信号: X 个"）
3. Telegram bot是否有发送权限

### Q3: 想调整Prime信号的敏感度？
**A**: 修改 `config/params.json` 中的 `publish.prime_prob_min`：
- 提高敏感度：降低阈值（例如：0.62 → 0.58）
- 降低敏感度：提高阈值（例如：0.62 → 0.68）

### Q4: 如何只测试特定币种？
**A**: 使用 `--max-symbols` 参数：
```bash
python3 scripts/realtime_signal_scanner.py --max-symbols 10 --once
```

---

## 📚 延伸阅读

- [ARCHITECTURE.md](./ARCHITECTURE.md) - 详细技术架构
- [CONFIGURATION_GUIDE.md](./CONFIGURATION_GUIDE.md) - 配置参数详解
- [MODIFICATION_RULES.md](./MODIFICATION_RULES.md) - 代码修改规范

---

## 🔖 版本历史

- **v6.0** (2025-10): 权重百分比系统，F因子参与评分，Prime阈值调整
- **v5.0** (2025-09): 10+1维因子系统，新增L/B/Q/I四维
- **v4.0** (2025-08): WebSocket优化，0 API调用
- **v3.0** (2025-07): 自适应权重系统

---

**最后更新**: 2025-10-30
**维护者**: CryptoSignal Team
