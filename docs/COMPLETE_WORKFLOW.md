# 加密货币交易信号系统 - 完整流程总结

## 📋 **系统架构概览**

```
┌─────────────────────────────────────────────────────────────┐
│                    币安全市场 (~400 USDT合约)                 │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┴──────────┐
         │                      │
    【每日更新】            【每小时更新】
         │                      │
         ▼                      ▼
  ┌──────────────┐      ┌──────────────┐
  │  Base Pool   │      │ Overlay Pool │
  │  (基础池)     │      │  (异动层)     │
  ├──────────────┤      ├──────────────┤
  │ • 流动性      │      │ • 三重共振    │
  │ • 波动性      │      │ • 新币检测    │
  │ • 33天历史    │      │ • 回撤过滤    │
  │              │      │              │
  │ ~60个成熟币  │      │ ~10-20个热币 │
  └──────┬───────┘      └──────┬───────┘
         │                      │
         └──────────┬───────────┘
                    │
                    ▼
          ┌─────────────────┐
          │   最终候选池      │
          │  60-80个币种     │
          └─────────┬───────┘
                    │
                    ▼
        ┌───────────────────────┐
        │  并发分析（8线程）      │
        │  • 7维特征计算         │
        │  • 双向评分            │
        │  • F调节器             │
        │  • 新币识别            │
        └───────────┬───────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
        ▼           ▼           ▼
    ┌────────┐ ┌────────┐ ┌────────┐
    │ Prime  │ │ Watch  │ │ Skip   │
    │        │ │        │ │        │
    │ ✅发送  │ │ ❌不发  │ │ ❌丢弃 │
    └────┬───┘ └────────┘ └────────┘
         │
         ▼
    ┌──────────┐
    │ Telegram │
    │ 交易信号  │
    └──────────┘
```

---

## 🔄 **三层更新策略**

| 层级 | 更新频率 | 触发时间 | 数据来源 | API调用 | 耗时 |
|-----|---------|---------|---------|---------|-----|
| **Base Pool** | 每日1次 | UTC 00:00 | 全市场扫描 | 401次 | ~5分钟 |
| **Overlay Pool** | 每小时1次 | 每小时:00 | Base Pool | 120次 | ~1.2分钟 |
| **实时分析** | 按需/15分钟 | 随时 | 读取缓存 | 180次 | ~2分钟 |

**Crontab配置**：
```bash
# Base Pool: 每日北京时间08:00
0 0 * * * cd ~/cryptosignal && python3 tools/update_pools.py --base

# Overlay Pool: 每小时
0 * * * * cd ~/cryptosignal && python3 tools/update_pools.py --overlay

# 实时扫描: 每15分钟
*/15 * * * * cd ~/cryptosignal && python3 tools/full_run_v2_fast.py --send
```

---

## 📊 **选币策略详解**

### **1. Base Pool（基础池）- 每日更新**

**目标**：筛选成熟、流动性好、有波动的币种

```python
全市场USDT合约 (~400个)
  ↓
[筛选1] 24h成交额 >= 500万USDT
  ↓ (~150个)
[筛选2] 获取800根1h K线（33天历史）
  ↓ (~120个，排除新币)
[筛选3] 计算Z24波动性 (MAD标准化)
  |Z24| = |24h收益率 - 中位数| / MAD
  ↓
[筛选4] |Z24| >= 0.5
  ↓ (~60个)
[保底] 如果<20个，添加Top流动性币
  ↓
[排序] 按24h成交额降序
  ↓
保存: data/base_pool.json
```

**参数**：
```json
{
  "base": {
    "min_quote_volume": 5000000,  // 500万USDT
    "min_z24_abs": 0.5,            // 波动性阈值
    "min_pool_size": 20            // 保底数量
  }
}
```

---

### **2. Overlay Pool（异动层）- 每小时更新**

**目标**：捕捉短期异动 + 新币

```python
Base Pool (~60个) + 全市场USDT合约（新币检测）
  ↓
【分支A：新币快速通道】
  ├─ 检测币龄: 7-30天
  ├─ 24h成交额 >= 1000万USDT
  └─ 直接加入Overlay → 跳过三重共振
  ↓
【分支B：常规三重共振】
  ├─ 获取1h K线60根 + 1h OI 60根
  │
  ├─ 计算三个指标：
  │   [1] dP1h = |1小时价格变动| >= 1.5%
  │   [2] v5/v20 = 短期/长期量能比 >= 1.2
  │   [3] cvd = CVD资金流强度 >= 2.5%
  │
  ├─ 三选二模式：满足2个条件即可
  │
  └─ 回撤过滤（可选）：
      • 距离72h高点<5% → 跳过
      • 距离72h低点<5% → 跳过
  ↓
保存: data/overlay_pool.json
输出: 🆕 检测到X个新币: ...
```

**参数**：
```json
{
  "overlay": {
    "triple_sync": {
      "mode": "2of3",              // 三选二
      "dP1h_abs_pct": 0.015,       // 1.5%
      "v5_over_v20": 1.2,          // 1.2倍
      "cvd_mix_abs_per_h": 0.025,  // 2.5%
      "anti_chase": {
        "enabled": true,
        "lookback": 72,
        "max_distance_pct": 0.05   // 5%
      }
    }
  }
}
```

---

## 🔍 **信号分析流程**

### **步骤1：数据获取**

```python
for symbol in 候选池:
    k1h = get_klines(symbol, "1h", 300)  # 12.5天
    k4h = get_klines(symbol, "4h", 200)  # 33天
    oi  = get_open_interest_hist(symbol, "1h", 300)
```

---

### **步骤2：新币识别**

```python
coin_age_days = len(k1h) / 24

if coin_age_days <= 14:
    phase = "phaseA"  # 极度谨慎
elif coin_age_days <= 30:
    phase = "phaseB"  # 谨慎
else:
    phase = "mature"  # 正常
```

---

### **步骤3：7维特征计算（双向）**

| 维度 | 说明 | 做多逻辑 | 做空逻辑 |
|------|------|---------|---------|
| **T (趋势)** | EMA排列+斜率 | 上涨趋势=高分 | 下跌趋势=高分 |
| **M (动量)** | 价格动量 | 正动量=高分 | 负动量=高分 |
| **C (资金流)** | CVD变化 | 资金流入=高分 | 资金流出=高分 |
| **S (结构)** | 多周期一致性 | 多头结构=高分 | 空头结构=高分 |
| **V (量能)** | 量能比 | 放量=高分 | 放量=高分 |
| **O (持仓)** | OI变化 | 多头OI增=高分 | 空头OI增=高分 |
| **E (环境)** | 波动性 | 低波动=高分 | 低波动=高分 |

```python
long_scores = {"T": T_long, "M": M_long, ...}
short_scores = {"T": T_short, "M": M_short, ...}
```

---

### **步骤4：方向决策**

```python
long_weighted = Σ(long_scores[i] * weight[i])
short_weighted = Σ(short_scores[i] * weight[i])

if long_weighted > short_weighted:
    side = "long"
    chosen_scores = long_scores
else:
    side = "short"
    chosen_scores = short_scores
```

**权重配置**：
```json
{
  "weights": {
    "T": 20,  // 趋势最重要
    "M": 10,
    "C": 10,
    "S": 10,
    "V": 20,  // 量能重要
    "O": 15,
    "E": 15
  }
}
```

---

### **步骤5：基础概率计算**

```python
edge = (加权分数 - 50) / 50  # 归一化到[-1, 1]
Q = quality_score(数据完整性, 数据量)

P_base = map_probability(edge, prior=0.5, Q)
```

---

### **步骤6：F调节器（资金领先性）**

```python
F_score = calc_fund_leading(OI变化, 量能比, CVD, 价格变化)

if F >= 70:    adjustment = 1.15  # 资金领先，蓄势待发
elif F >= 50:  adjustment = 1.0   # 同步
elif F >= 30:  adjustment = 0.9   # 价格略领先
else:          adjustment = 0.7   # 价格远超，追高风险

P_final = min(P_base * adjustment, 0.95)
```

---

### **步骤7：发布判定（分级标准）**

#### **新币阶段A（0-14天）**
```
门槛: P >= 65% AND 5维 >= 65分
原因: 新币波动大，风险高，极度谨慎
Watch: 不发送
```

#### **新币阶段B（15-30天）**
```
门槛: P >= 63% AND 4维 >= 65分
原因: 略有历史，但仍需谨慎
Watch: 不发送
```

#### **成熟币（30天+）**
```
Prime: P >= 62% AND 4维 >= 65分 → 发送Telegram
Watch: 58% <= P < 62% → 仅保存数据库
Skip:  P < 58% → 丢弃
```

---

### **步骤8：给价计划（仅Prime信号）**

**做多示例**：
```python
# 入场区间
entry_lo = EMA10 - (0.02 + 0.10*偏离度) * ATR
entry_hi = EMA10 + 0.01 * ATR

# 止损（双重保护）
pivot_low = min(low[-12:])
sl = max(
    pivot_low - 0.1*ATR,        # 支点下方
    entry_mid - 1.8*ATR          # 固定距离
)

# 止盈
R = entry_mid - sl
tp1 = entry_mid + 1.0*R          # 1:1盈亏比
tp2 = entry_mid + min(2.5*R, donchian_cap)  # 最大2.5R

# 做空逻辑镜像对称
```

---

## 📤 **Telegram消息格式**

```
🔹 BTCUSDT · 现价 65,234
📣 正式 · 🟩 做多 68% · 有效期8h

六维分析
• 趋势 🟢 88 —— 强势/上行倾向 [多头]
• 动量 🟢 85 —— 价格动量
• 资金流 🟢 82 —— CVD变化
• 结构 🟢 75 —— 结构尚可/回踩确认
• 量能 🟢 70 —— 量能偏强/逐步释放
• 持仓 🟡 55 —— 多头持仓温和上升/活跃
• 环境 🟢 80 —— 环境友好/空间充足

📍 入场区间: 64,500 - 64,800
🛑 止损: 62,300
🎯 止盈1: 67,200
🎯 止盈2: 71,500

#trade #BTCUSDT
```

**新币标注（可选）**：
```
🆕 新币 (12天) - 阶段A
```

---

## 🆕 **新币处理完整流程**

```
币安上币
   ↓
第1-6天: 观察期
   ├─ 不处理
   └─ 等待数据积累
   ↓
第7-14天: 阶段A（极度谨慎）
   ├─ Overlay自动检测
   │   条件: 成交额>1000万 + 币龄7-14天
   ├─ 直接加入候选池
   ├─ 分析时识别为phaseA
   ├─ 应用严格标准:
   │   • 概率 >= 65%
   │   • 5维 >= 65分
   ├─ Prime → Telegram 🆕
   └─ 不发送Watch信号
   ↓
第15-30天: 阶段B（谨慎）
   ├─ 继续在Overlay中
   ├─ 识别为phaseB
   ├─ 略微放松:
   │   • 概率 >= 63%
   │   • 4维 >= 65分
   └─ Prime → Telegram
   ↓
第31天+: 成熟币
   ├─ 可能进入Base Pool
   │   (如果|Z24|>=0.5)
   ├─ 正常标准:
   │   • 概率 >= 62%
   │   • 4维 >= 65分
   └─ 正常处理（Prime/Watch）
```

---

## 🔧 **工具集**

### **1. 候选池管理**
```bash
# 检查缓存状态
python3 tools/update_pools.py --check

# 更新Base Pool
python3 tools/update_pools.py --base

# 更新Overlay Pool
python3 tools/update_pools.py --overlay

# 强制更新全部
python3 tools/update_pools.py --all --force
```

### **2. 新币检测**
```bash
# 检测全市场新币
python3 tools/test_new_coin.py

# 分析新币信号
python3 tools/test_new_coin.py --analyze

# 测试指定币种
python3 tools/test_new_coin.py AIUSDT
```

### **3. 实时扫描**
```bash
# 快速扫描（读取缓存）
python3 tools/full_run_v2_fast.py

# 发送Prime信号到Telegram
python3 tools/full_run_v2_fast.py --send

# 调试单个币种
python3 tools/debug_scan.py
```

---

## 📈 **性能指标**

### **API调用量**
| 场景 | 请求数 | Weight | 耗时 | 风控风险 |
|-----|-------|--------|-----|---------|
| Base Pool | 401次 | 440 | 5分钟 | ✅ 安全 |
| Overlay Pool | 120次 | 120 | 1.2分钟 | ✅ 安全 |
| 实时扫描 | 180次 | 180 | 2分钟 | ✅ 安全 |

**币安限制**：1200 req/min, 3000 weight/min

### **信号质量预期**

| 市场环境 | 候选池 | Prime信号/天 | 胜率预期 | 盈亏比 |
|---------|-------|-------------|---------|-------|
| 牛市 | 80个 | 10-20个 | 60-70% | 1.5-2.5R |
| 震荡市 | 60个 | 3-8个 | 55-65% | 1.2-2.0R |
| 熊市 | 70个 | 8-15个 | 60-70% | 1.5-2.5R |

---

## ⚙️ **关键配置参数**

```json
{
  "base": {
    "min_quote_volume": 5000000,
    "min_z24_abs": 0.5,
    "min_pool_size": 20
  },

  "overlay": {
    "triple_sync": {
      "mode": "2of3",
      "dP1h_abs_pct": 0.015,
      "v5_over_v20": 1.2,
      "cvd_mix_abs_per_h": 0.025,
      "anti_chase": {
        "enabled": true,
        "lookback": 72,
        "max_distance_pct": 0.05
      }
    }
  },

  "new_coin": {
    "enabled": true,
    "min_days": 7,
    "phaseA_days": 14,
    "phaseB_days": 30,
    "min_volume_24h": 10000000,
    "phaseA_prime_prob_min": 0.65,
    "phaseA_dims_ok_min": 5,
    "phaseB_prime_prob_min": 0.63,
    "phaseB_dims_ok_min": 4
  },

  "publish": {
    "prime_prob_min": 0.62,
    "prime_dims_ok_min": 4,
    "prime_dim_threshold": 65,
    "watch_prob_min": 0.58
  },

  "pricing": {
    "sl_atr_back": 1.8,
    "tp1_R": 1.0,
    "tp2_R_max": 2.5
  },

  "weights": {
    "T": 20, "M": 10, "C": 10, "S": 10,
    "V": 20, "O": 15, "E": 15
  }
}
```

---

## 🚀 **部署建议**

### **服务器配置**
```bash
# 创建日志目录
mkdir -p ~/cryptosignal/logs

# 设置Crontab
crontab -e
# 粘贴3条定时任务

# 首次建立缓存
cd ~/cryptosignal
python3 tools/update_pools.py --all --force

# 验证
python3 tools/update_pools.py --check
python3 tools/test_new_coin.py
```

### **监控建议**
```bash
# 实时监控扫描日志
tail -f logs/scan.log

# 监控候选池更新
tail -f logs/pool_update.log

# 检查信号数据库
python3 -c "
import sqlite3
conn = sqlite3.connect('data/signals.db')
cursor = conn.cursor()
cursor.execute('SELECT side, COUNT(*) FROM signals WHERE created_at >= datetime(\"now\", \"-1 day\") GROUP BY side')
for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]}条')
"
```

---

## 📚 **相关文档**

- **docs/POOL_UPDATE_STRATEGY.md** - 候选池更新策略
- **docs/PERFORMANCE_OPTIMIZATION.md** - 性能优化指南
- **config/params.json** - 完整配置参数

---

## ✅ **系统特性总结**

| 特性 | 状态 | 说明 |
|-----|------|------|
| **多空对称** | ✅ 完整实现 | 真正的双向信号，不偏向多头 |
| **新币支持** | ✅ 完整实现 | 自动检测7-30天新币，分级处理 |
| **速度优化** | ✅ 完整实现 | 2分钟完成扫描（原5.2分钟） |
| **风控安全** | ✅ 完整实现 | 180 weight/次，不触发限制 |
| **回撤过滤** | ✅ 完整实现 | 避免追高追跌，降低风险 |
| **止盈止损** | ✅ 完整实现 | ATR归一化，动态适应市场 |
| **缓存机制** | ✅ 完整实现 | Base日更新，Overlay时更新 |
| **并发分析** | ✅ 完整实现 | 8线程并发，提升效率 |

---

**版本**: v2.0
**最后更新**: 2025-10-25
**维护者**: Claude Code
