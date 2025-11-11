# CryptoSignal v7.2 快速参考卡

**版本**: v7.2.24 | **更新**: 2025-11-11

---

## 🚀 一键启动

```bash
cd ~/cryptosignal
./setup.sh
```

**预计耗时**: 首次3-4分钟，后续30秒

---

## 📊 核心指标速查

### 因子权重分配

```
┌─────────────────────────────────────────┐
│         A层因子 (100%权重)               │
├─────────────────────────────────────────┤
│ TC组 (50%)                              │
│   ├─ T 趋势      35.0%  (70% × 50%)    │
│   └─ C 资金流    15.0%  (30% × 50%)    │
├─────────────────────────────────────────┤
│ VOM组 (35%)                             │
│   ├─ V 量能      17.5%  (50% × 35%)    │
│   ├─ O 持仓量    10.5%  (30% × 35%)    │
│   └─ M 动量       7.0%  (20% × 35%)    │
├─────────────────────────────────────────┤
│ B组 (15%)                               │
│   └─ B 基差      15.0%  (100% × 15%)   │
└─────────────────────────────────────────┘

B层调制器 (0%权重，仅调制)
  F: 资金领先    I: 独立性
  L: 流动性      S: 结构
```

---

## 🚪 五道闸门阈值

| # | 名称 | 阈值 | 结果 |
|---|------|------|------|
| 1️⃣ | 数据质量 | K线 ≥ 150根 | 不通过→❌拒绝 |
| 2️⃣ | 资金支撑 | F ≥ -10 | 不通过→❌拒绝 |
| 3️⃣ | 期望收益 | EV ≥ 1.5% | 不通过→❌拒绝 |
| 4️⃣ | 胜率门槛 | P ≥ 50% | 不通过→⚠️不发布 |
| 5️⃣ | I×Market | 对齐检查 | 顺势→✅×1.2加成 |

---

## 🎯 关键阈值表

### 基础过滤

```yaml
confidence_min: 15        # 候选信号最低信心度
prime_strength_min: 42    # Prime信号最低强度
edge_min: 0.12           # 最低优势 12%
```

### F因子阈值

```yaml
F_min: -10               # Gate 2最低值
F_moderate: 20           # 中等动量
F_strong: 40             # 强势动量 → 🚀 蓄势待发
```

### I因子阈值

```yaml
I_high: 60               # 高独立性 → 免检市场
I_min: 0                 # Gate 5最低值
market_regime: ±30       # 强趋势阈值
```

### 统计校准

```yaml
bootstrap_base_p: 60%    # 基准胜率
F_bonus: +5%            # F>40加成
I_bonus: +3%            # I>60加成
max_p: 75%              # 胜率上限
```

---

## 📱 Telegram消息解读

### 消息头部

```
🚀 蓄势待发               ← F>40时显示
🔹 BTCUSDT · 现价 50,000
🟩 做多 胜率65% · 有效期8h  ← 🟩多/🔴空, 胜率, TTL
期望收益 +2.5% · 盈亏比 2.0:1 ✅
```

### 核心因子

```
🔥 F资金领先   72  偏强资金流入 [即将爆发]
   ↑ 分数      ↑ 描述          ↑ 动量标签

💎 I市场独立   96  完全独立走势
   Beta: BTC=0.39 ETH=-0.46
   ↔️ 大盘震荡(+0)
```

### 因子分组

```
TC组(50%)   78  [趋势+资金流]
  🟩 趋势 T   85  强劲上涨      ← Emoji + 分数 + 描述
  🟩 动量 M   65  稳步上涨
  🟢 资金 C   55  温和上涨
```

### Emoji颜色含义

| Emoji | TC组 | VOM组 | B组 | 分数范围 | 语义 |
|-------|------|-------|-----|---------|------|
| 🟩/💚/⬆️ | ✓ | ✓ | ✓ | ≥ +60 | **强势** |
| 🟢 | ✓ | ✓ | ✓ | +20~+60 | 偏强 |
| 🟡 | ✓ | ✓ | ✓ | -20~+20 | 中性 |
| 🟠 | ✓ | ✓ | ✓ | -60~-20 | 偏弱 |
| 🔴/🔻/⬇️ | ✓ | ✓ | ✓ | ≤ -60 | **弱势** |

**特殊Emoji**:
- 🚀 F≥80 (强劲资金流入)
- 🔥 F≥60 (偏强资金流入)
- 💎 I≥80 (完全独立)
- ✨ I≥60 (强独立)

---

## 🔧 常用命令

### 启动/停止

```bash
# 启动系统
./setup.sh

# 查看状态
ps aux | grep realtime_signal_scanner

# 停止程序
pkill -f realtime_signal_scanner.py

# 重新启动
~/cryptosignal/auto_restart.sh
```

### 日志查看

```bash
# 实时日志
tail -f ~/cryptosignal_*.log

# 最新日志文件
ls -lt ~/cryptosignal_*.log | head -1

# 查看最近100行
tail -100 ~/cryptosignal_*.log
```

### 数据库查询

```bash
# 进入TradeRecorder数据库
sqlite3 data/trade_history.db

# 查询最近10条信号
SELECT * FROM signals ORDER BY timestamp DESC LIMIT 10;

# 统计胜率
SELECT
  COUNT(*) as total,
  SUM(CASE WHEN outcome='win' THEN 1 ELSE 0 END) as wins,
  ROUND(SUM(CASE WHEN outcome='win' THEN 1 ELSE 0 END)*100.0/COUNT(*), 2) as win_rate
FROM signals WHERE outcome IS NOT NULL;
```

---

## 📁 关键文件路径

### 配置文件

```
config/
├── signal_thresholds.json     ← ★ 主配置 (v7.2阈值)
├── params.json                ← 因子参数
├── factors_unified.json       ← 统一框架 (v3.0)
├── telegram.json              ← Telegram配置
└── binance_credentials.json   ← API密钥
```

### 数据文件

```
data/
├── trade_history.db           ← 交易记录
├── analysis.db                ← 分析数据 (7张表)
└── calibration_history.json   ← 校准历史
```

### 日志文件

```
~/cryptosignal_20251111_143022.log  ← 运行日志
reports/latest/scan_summary.json    ← 扫描报告
```

---

## 🎨 因子描述速查

### F因子 (资金领先)

| 分数 | Emoji | 描述 |
|------|-------|------|
| ≥ 80 | 🚀 | 强劲资金流入 [蓄势待发] |
| 60-80 | 🔥 | 偏强资金流入 [即将爆发] |
| 40-60 | 🟢 | 中等资金流入 |
| 20-40 | 🟢 | 轻微资金流入 |
| -20~20 | 🟡 | 资金流平衡 |
| -40~-20 | 🟠 | 轻微资金流出 |
| -60~-40 | 🟠 | 中等资金流出 |
| -80~-60 | 🔴 | 偏强资金流出 |
| < -80 | 🔴 | 强劲资金流出 |

### I因子 (市场独立性)

| 分数 | Emoji | 描述 |
|------|-------|------|
| ≥ 80 | 💎 | 完全独立走势 |
| 60-80 | ✨ | 强独立走势 |
| 40-60 | 🟢 | 中度独立 |
| 20-40 | 🟢 | 轻度独立 |
| -20~20 | 🟡 | 跟随大盘 |
| -40~-20 | 🟠 | 高度跟随 |
| -60~-40 | 🟠 | 强烈跟随 |
| -80~-60 | 🔴 | 完全跟随 |
| < -80 | 🔴 | 极端跟随 |

### TC组 (趋势描述)

| 分数 | Emoji | 描述 |
|------|-------|------|
| > 75 | 🟩 | 强劲上涨 |
| 60-75 | 🟩 | 稳步上涨 |
| 20-60 | 🟢 | 温和上涨 |
| -20~20 | 🟡 | 横盘震荡 |
| -60~-20 | 🟠 | 温和下跌 |
| -75~-60 | 🔴 | 稳步下跌 |
| < -75 | 🔴 | 强劲下跌 |

### VOM组 (量能描述)

| 分数 | Emoji | 描述 |
|------|-------|------|
| > 75 | 💚 | 活跃放量 |
| 60-75 | 💚 | 温和放量 |
| 20-60 | 🟢 | 小幅放量 |
| -20~20 | 🟡 | 量能平衡 |
| -60~-20 | 🟠 | 小幅缩量 |
| -75~-60 | 🔻 | 温和缩量 |
| < -75 | 🔻 | 显著缩量 |

### B组 (溢价描述)

| 分数 | Emoji | 描述 |
|------|-------|------|
| > 75 | ⬆️ | 强烈正溢价 |
| 60-75 | ⬆️ | 明显正溢价 |
| 20-60 | 🟢 | 温和正溢价 |
| -20~20 | 🟡 | 溢价平衡 |
| -60~-20 | 🟠 | 温和负溢价 |
| -75~-60 | ⬇️ | 明显负溢价 |
| < -75 | ⬇️ | 强烈负溢价 |

---

## ⚡ 性能指标

### 扫描性能

```
初始化时间:        3-4 分钟 (首次)
                  30 秒 (后续)
扫描周期:         5 分钟
扫描速度:         12-15 秒/周期
API调用:          0 次/扫描 (WebSocket缓存)
```

### 信号漏斗

```
140+ 币种扫描
    ↓ 10-20% 通过
40-80 候选信号 (confidence≥15)
    ↓ 约12-37% 通过
5-15 Prime信号 (5道闸门)
    ↓ 选Top 1
1 条Telegram消息
```

### 预期结果

```
胜率:             58-65%
期望收益:         1.5-3.0%
盈亏比:           2:1
信号频率:         1-3 条/小时
```

---

## 🔍 故障排查

### 问题1: 扫描器无法启动

```bash
# 检查Python版本
python3 --version  # 需要 3.11+

# 检查依赖
pip3 list | grep -E "numpy|pandas|aiohttp"

# 重新安装依赖
pip3 install -r requirements.txt
```

### 问题2: 无信号输出

```bash
# 检查Telegram配置
cat config/telegram.json

# 查看日志
tail -100 ~/cryptosignal_*.log | grep -i error

# 手动测试
python3 -c "
from ats_core.outputs.telegram_fmt import render_trade_v72
print('Telegram模块加载正常')
"
```

### 问题3: 数据库错误

```bash
# 重新初始化数据库
python3 scripts/init_databases.py

# 检查数据库完整性
sqlite3 data/trade_history.db "PRAGMA integrity_check;"
sqlite3 data/analysis.db "PRAGMA integrity_check;"
```

### 问题4: API限流

```bash
# 检查Binance API状态
curl -s https://api.binance.com/api/v3/ping

# 查看API调用频率
tail -100 ~/cryptosignal_*.log | grep -i "rate limit"

# 调整扫描间隔 (在setup.sh中)
--interval 300  →  --interval 600  # 改为10分钟
```

---

## 📊 配置调整建议

### 提高信号质量 (减少数量)

**编辑** `config/signal_thresholds.json`:

```json
{
  "基础分析阈值": {
    "mature_coin": {
      "confidence_min": 20,      // 15 → 20
      "prime_strength_min": 50,  // 42 → 50
      "edge_min": 0.15          // 0.12 → 0.15
    }
  },
  "v72闸门阈值": {
    "gate3_ev": {
      "EV_min": 0.020           // 1.5% → 2.0%
    },
    "gate4_probability": {
      "P_min": 0.55             // 50% → 55%
    }
  }
}
```

**预期**: 信号数量 -30%, 质量 +15%

---

### 增加信号数量 (降低质量)

**编辑** `config/signal_thresholds.json`:

```json
{
  "基础分析阈值": {
    "mature_coin": {
      "confidence_min": 12,      // 15 → 12
      "prime_strength_min": 38,  // 42 → 38
      "edge_min": 0.10          // 0.12 → 0.10
    }
  },
  "v72闸门阈值": {
    "gate2_fund_support": {
      "F_min": -20              // -10 → -20
    },
    "gate3_ev": {
      "EV_min": 0.012           // 1.5% → 1.2%
    },
    "gate4_probability": {
      "P_min": 0.45             // 50% → 45%
    }
  }
}
```

**预期**: 信号数量 +50%, 质量 -10%

---

## 🎓 使用技巧

### 1. 理解"蓄势待发"标记

```
🚀 蓄势待发  ← F > 40

含义: 资金动量领先价格动量
解读: 机构资金正在吸筹，价格即将突破
优势: 胜率 +5%, 期望收益更高
风险: 需确认Gate 5市场对齐
```

### 2. 独立性因子的应用

```
I ≥ 60:  高独立性 → 可忽略大盘走势
I < 0:   高相关性 → 必须检查大盘对齐

示例:
  LONG信号 + I=-15 + 大盘+45 → 顺势加成×1.2 ✅
  LONG信号 + I=-15 + 大盘-50 → 逆势风险拒绝 ❌
```

### 3. 因子分组权重理解

```
TC组 78分 (50%权重) → 贡献 39分
VOM组 55分 (35%权重) → 贡献 19.25分
B组 20分 (15%权重) → 贡献 3分
─────────────────────────────────
加权分数 = 39 + 19.25 + 3 = 61.25
```

### 4. Gate 3 期望收益计算

```
假设:
  P = 60%
  ATR = $500
  SL = 1.5×ATR = $750
  TP = 3.0×ATR = $1500 (RR=2:1)
  成本 = 0.8%

EV = 0.60×(1500/50000) - 0.40×(750/50000) - 0.008
   = 0.018 - 0.006 - 0.008
   = 0.004 = 0.4%

结论: EV=0.4% < 1.5% → Gate 3不通过 ❌
```

---

## 📚 延伸阅读

- `docs/SYSTEM_ARCHITECTURE_COMPLETE.md` - 完整架构文档
- `docs/v7.2.24_FACTOR_DESCRIPTION_UX_IMPROVEMENT.md` - 因子描述优化
- `docs/v7.2.23_TELEGRAM_TEMPLATE_ROLLBACK.md` - 消息模板历史
- `docs/v7.2.21_CALIBRATION_LOG_FIX.md` - 校准系统修复
- `standards/00_INDEX.md` - 开发规范索引

---

## 🆘 获取帮助

### 社区支持

- **Issues**: https://github.com/FelixWayne0318/cryptosignal/issues
- **文档**: `docs/` 目录
- **日志**: `~/cryptosignal_*.log`

### 调试模式

```bash
# 启用详细日志
export DEBUG=1
./setup.sh

# 单次扫描测试
python3 scripts/realtime_signal_scanner.py --interval 0 --once
```

---

**快速参考卡版本**: v1.0
**最后更新**: 2025-11-11
**维护**: CryptoSignal团队
