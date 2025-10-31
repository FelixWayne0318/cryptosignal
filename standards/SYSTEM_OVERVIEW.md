# CryptoSignal v6.0 系统总览

> **新对话框必读文档** - 快速了解整个系统架构

---

## 📌 项目概述

**CryptoSignal v6.0** 是一个基于币安合约市场的加密货币信号分析系统。

### 核心功能
- 实时扫描200个高流动性币种
- 9因子方向评分系统（A层：T/M/C/S/V/O/L/B/Q）
- F/I调制器系统（B层：不参与评分，调整Teff/cost/阈值）
- 四门验证系统（DataQual/EV/执行/概率）
- WebSocket优化（0次API调用/扫描，12-15秒/200币种）
- 自动发送Prime信号到Telegram

### 系统版本
- **当前版本**: v6.0 newstandards整合版
- **升级时间**: 2025-10
- **主要变更**: A/B/C/D分层架构，F/I从评分层移除改为调制器，四门验证系统

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

### 1. **A/B/C/D 分层架构**

**A层 - 方向评分层（9因子，总权重100%）**：
- **价格行为维度**
  - T（趋势，18.0%）：EMA趋势强度
  - M（动量，12.0%）：价格动量和加速度
  - S（结构，10.0%）：支撑阻力位
  - V（量能，10.0%）：成交量强度

- **资金流维度**
  - C（资金流，18.0%）：CVD累积成交量差值
  - O（持仓，18.0%）：OI持仓量变化

- **微观结构维度**
  - L（流动性，8.0%）：订单簿深度和滑点
  - B（基差，2.0%）：现货-合约基差+资金费率
  - Q（清算，4.0%）：清算密度热图

**B层 - 调制器层（F/I，不参与评分）**：
- **F（资金领先）调制器**：
  - 调整 Teff（有效持仓时间）
  - 调整 cost_eff（有效成本）
  - 不参与方向评分

- **I（独立性）调制器**：
  - 调整概率阈值 p_min 和 Δp_min
  - 不参与方向评分

**C层 - 执行层（spread/impact/OBI）**：
- 评估订单簿深度和滑点成本
- 确保信号可执行性

**D层 - 发布层（四门验证）**：
- Gate 1: DataQual ≥ 0.90
- Gate 2: EV > 0
- Gate 3: 执行指标达标
- Gate 4: 概率阈值

### 2. **v6.0 newstandards 权重系统**

**总权重**：100%（A层9因子评分）

**权重配置**：`config/params.json` → `weights` 字段
```json
{
  "weights": {
    "T": 18.0, "M": 12.0, "C": 18.0, "S": 10.0,
    "V": 10.0, "O": 18.0, "L": 8.0, "B": 2.0,
    "Q": 4.0, "I": 0, "E": 0, "F": 0
  }
}
```

**评分公式**：
```python
# A层：方向评分
weighted_score = Σ(score_i × weight_i) / Σ(weight_i)
# 范围：-100到+100（负数=看空，正数=看多）

# B层：调制
Teff = T0 × (1 + βF·gF) / (1 + βI·gI)
cost_eff = pen_F + pen_I - rew_I
p_min = p0 + θF·max(0,gF) + θI·min(0,gI)
```

### 3. **Prime信号判定（四门系统）**

**Gate 1 - 数据质量门**：
```python
DataQual ≥ 0.90
```

**Gate 2 - 期望值门**：
```python
EV = P·μ_win - (1-P)·μ_loss - cost_eff > 0
```

**Gate 3 - 执行指标门**：
```python
spread_bps ≤ 20 (新币 50)
impact_bps ≤ 10 (新币 20)
OBI 在 0.4-0.6 范围内
```

**Gate 4 - 概率阈值门**：
```python
P ≥ p_min（经F/I调制后的动态阈值）
ΔP ≥ Δp_min（概率增益阈值）
```

**判定条件**：
```python
is_prime = (all_gates_passed == True)
```

### 4. **自适应权重系统**

根据市场状态动态调整因子权重：
- **强势趋势**（|regime| > 60）：趋势因子权重↑
- **震荡市场**（|regime| < 30）：资金流因子权重↑
- **高波动**（vol > 0.03）：持仓量因子权重↑
- **低波动**（vol < 0.01）：趋势稳定性因子权重↑

**混合策略**：70%自适应 + 30%基础权重

---

## ⚖️ 多空对称性说明

> **重要**: 系统存在系统性做多偏向，详见 `docs/archive/SYMMETRY_ANALYSIS_REPORT.md`

### 对称因子（✅ 无问题）

| 因子 | 权重 | 对称性 | 说明 |
|-----|------|-------|------|
| T（趋势） | 18% | ✅ 完全对称 | 基于EMA和斜率，上涨=正分，下跌=负分 |
| M（动量） | 12% | ✅ 完全对称 | 基于加速度，加速上涨=正分，加速下跌=负分 |
| C（CVD） | 18% | ✅ 理论对称 | tanh映射，资金流入=正分，流出=负分 |
| S（结构） | 10% | ✅ 对称 | 上涨结构好=正分，下跌结构好=负分 |
| B（基差） | 2% | ✅ 完全对称 | 正基差+正费率=看涨=正分 |
| L（流动性） | 8% | ✅ 中性因子 | 高流动性=好，不影响多空方向 |
| Q（清算） | 4% | ✅ 对称 | 多单清算=看多=正分，空单清算=看空=负分 |

### 不对称因子（⚠️ 存在偏向）

#### V（量能）- **严重偏向** 🚨

**当前逻辑**（权重10%）：
```
放量 = 正分（好）
缩量 = 负分（差）
```

**问题**：
- **放量上涨**：T(+80) + V(+60) → 总贡献 +20.4 ✅
- **放量下跌**：T(-80) + V(+60) → 总贡献 -8.4 ❌（应该是-20.4）

**影响**：做空信号被系统性低估约 **12-15分**

---

#### O（持仓）- **严重偏向** 🚨

**当前逻辑**（权重18%）：
```
OI增加 = 正分
OI减少 = 负分
```

**问题**：
- **OI增+价格涨**：T(+80) + O(+70) → 总贡献 +27.0 ✅
- **OI增+价格跌**：T(-80) + O(+70) → 总贡献 -1.8 ❌（应该是-27.0，空头建仓）

**影响**：做空信号被系统性低估约 **25-30分**

---

### 量化影响评估

**典型做空信号对比**（价格下跌+放量+OI增）：

| 系统 | 总分 | 概率 | 偏差 |
|-----|------|------|------|
| 当前系统 | -20.6 | ~53% | -15% |
| 理想系统 | -57.8 | ~72% | 基准 |

**结论**：做空信号概率被系统性低估约 **15-20个百分点**

---

### 选币逻辑偏向

**当前阈值**：24h成交额 ≥ 3M USDT（绝对阈值）

**市场影响**：
- **牛市**：成交额普遍高，140个币种全部达标 → 信号数量↑
- **震荡市**：80-100个币种达标 → 信号数量正常
- **熊市**：40-60个币种达标 → 信号数量↓

**原因**：
1. 大涨币种成交额高（FOMO+获利盘）→ 易入选
2. 熊市成交萎缩 → 优质做空机会可能被排除

**注意**：这不一定是坏事，熊市中低流动性交易风险更高。

---

### 改进方案

#### 方案A：彻底修复（推荐，1-2个月）
修改V和O因子逻辑，使其成为真正的方向因子。

**V因子修复**：
```python
# 放量配合价格方向
if vlevel > 1.0:  # 放量
    price_direction = 1 if price_up else -1
    V = vlevel_score * price_direction
```

**O因子修复**：
```python
# OI增配合价格方向
if oi24 > 0:  # OI增
    price_direction = 1 if price_up else -1
    O = oi_score * price_direction
```

---

#### 方案B：权重调整（折中，1-2周）
保持现有逻辑，但降低V和O的权重：

```json
{
  "weights": {
    "T": 24.0,  // +6 (18→24)
    "M": 16.0,  // +4 (12→16)
    "C": 24.0,  // +6 (18→24)
    "S": 12.0,  // +2 (10→12)
    "V": 4.0,   // -6 (10→4) ← 大幅降权
    "O": 8.0,   // -10 (18→8) ← 大幅降权
    "L": 8.0,
    "B": 2.0,
    "Q": 2.0    // -2 (4→2)
  }
}
```

**效果**：偏向降低约57%（16.8分 → 7.2分）

---

### 当前状态

**系统版本**: v6.0 newstandards整合版
**对称性审计**: 2025-10-31
**已知偏向**: V(10%)和O(18%)因子存在做多偏向
**计划优化**: 短期权重调整 + 中期逻辑重构

**详细分析**: 参见 `docs/archive/SYMMETRY_ANALYSIS_REPORT.md`

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
- `weights`: 9因子权重（A层，总和100%，F/I权重为0）
- `publish`: Prime/Watch信号阈值（已被四门系统替代）
- `trend`, `momentum`, `cvd_flow`, ... : 各因子具体参数
- `liquidity`, `basis_funding`, `liquidation`, `independence`: L/B/Q/I因子参数

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

- **v6.0 newstandards整合版** (2025-10): A/B/C/D分层架构，F/I改为调制器，四门验证系统
- **v6.0** (2025-10): 权重百分比系统，F因子参与评分，Prime阈值调整
- **v5.0** (2025-09): 10+1维因子系统，新增L/B/Q/I四维
- **v4.0** (2025-08): WebSocket优化，0 API调用
- **v3.0** (2025-07): 自适应权重系统

---

**最后更新**: 2025-10-31
**维护者**: CryptoSignal Team
**对称性审计**: 2025-10-31 - 发现V和O因子存在系统性做多偏向
