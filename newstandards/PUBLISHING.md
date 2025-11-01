# PUBLISHING.md
概率→EV→发布：证据平滑，决策离散，但防抖

## 1. 分边概率、温度与校准

### 1.1 原始概率计算
`Teff = clip( T0 * (1 + βF*gF) / (1 + βI*gI), Tmin, Tmax )`
`P_long=σ( S/Teff )`；`P_short=σ( -S/Teff )`
短样本收缩：`P̃ = 0.5 + w_eff*(P-0.5)`，`w_eff = min(1, bars_1h/400)`

### 1.2 概率分箱校准（Platt-like Calibration）
**目的**：修正模型偏差，将理论概率映射到真实胜率

**方法**：S_total（加权分数）→ 分箱查表 → 校准概率
```
calibration_table = [
    (s_min, s_max, p_calibrated),
    ...
]

def calibrate(s_total):
    for (s_min, s_max, p_cal) in calibration_table:
        if s_min <= s_total < s_max:
            return p_cal  # 或线性插值
    return 0.50  # 默认中性
```

**默认分箱表**（基于历史回测，需定期更新）：
```
s_total ∈ (-∞, -50]  → p = 0.40  (强空信号)
s_total ∈ (-50, -25] → p = 0.45
s_total ∈ (-25, -10] → p = 0.48
s_total ∈ (-10, 0]   → p = 0.50
s_total ∈ (0, 10]    → p = 0.52
s_total ∈ (10, 25]   → p = 0.56
s_total ∈ (25, 50]   → p = 0.60
s_total ∈ (50, 100]  → p = 0.64
s_total ∈ (100, ∞)   → p = 0.68  (强多信号)
```

**更新机制**：
- 每月回测最近90天交易
- 计算实际胜率 vs 预测概率
- 调整分箱边界和映射值
- 评估指标：MAE（Mean Absolute Error）、Brier Score

**存储格式**：
```json
{
  "version": "v1.2",
  "updated": "2025-11-01",
  "bins": [
    {"s_min": -100, "s_max": -50, "p_calibrated": 0.40},
    ...
  ],
  "metrics": {
    "mae": 0.032,
    "brier_score": 0.018
  }
}
```

## 2. 期望收益 EV（单边）
`EV = P * μ_win - (1-P) * μ_loss - cost_eff`
`μ_win, μ_loss` 用历史分桶条件均值（多空镜像）

## 3. 发布规则（离散 + 防抖）
- Prime（发布）：`EV*>0  ∧  p*≥p_min  ∧  ΔP≥Δp_min`
- 维持 Prime（滞回）：门槛降低 0.01~0.02
- 时间持久：K/N 连续满足（如 2/3 根确认）才升/降级
- 冷却：降级/撤信后 60–120s 再评估，防锯齿
- Watch：`EV*>0` 但未达 Prime 门槛，或闸门临界

### 3.1 执行硬闸门（必须全部通过）
- Gate 1: 数据质量 `DataQual ≥ 0.90`
- Gate 2: 期望值 `EV > 0`
- Gate 3: 执行成本（价差、冲击、失衡）
- Gate 4: 概率阈值 `p ≥ p_min ∧ ΔP ≥ Δp_min`
- Gate 5: 执行容纳度 `room_atr_ratio ≥ room_min`（v2.1新增）

### 3.2 执行时机保护（v2.1新增）
**资金费结算窗口保护**：
- Binance合约每8小时结算：00:00、08:00、16:00 UTC
- 保护窗口：结算时间 ± 5分钟（共10分钟）
- 规则：在保护窗口内**禁止开仓**（允许平仓）

**理由**：
1. 结算前后流动性骤变（大户对冲、套利平仓）
2. 滑点激增（点差可扩大2-5倍）
3. "窗边被打"风险（成交价格偏离预期）

**实现**：
```python
def is_near_settlement(now_ts,
                       funding_interval=28800,  # 8h in seconds
                       guard_window=300):       # ±5min
    """
    检查当前时间是否在结算窗口内

    Returns:
        True: 在保护窗口内，禁止开仓
        False: 安全时段，允许交易
    """
    seconds_since_epoch = now_ts
    seconds_since_last_settlement = seconds_since_epoch % funding_interval

    # 距离上次结算 < 5min 或 距离下次结算 < 5min
    if seconds_since_last_settlement < guard_window:
        return True
    if (funding_interval - seconds_since_last_settlement) < guard_window:
        return True

    return False
```

### 3.3 执行容纳度检查（v2.1新增）
**指标定义**：
```
room_atr_ratio = orderbook_depth_usdt / (ATR * position_size_usdt)
```

**含义**：
- 分子：订单簿可用深度（USDT）
- 分母：仓位规模 × 波动范围
- 比值：订单簿能否容纳该仓位的执行

**阈值**：
```python
# 标准币种
room_atr_ratio >= 0.6  # 订单簿深度至少为(ATR×仓位)的60%

# 新币（更严格）
room_atr_ratio >= 0.8  # 新币波动大，需更多深度
```

**失败时行为**：
- 降级为 Watch（或拒绝发布）
- 日志记录：订单簿深度不足，无法安全执行

**深度估算**（无实时深度流时的近似）：
```python
# 基于成交量估算
volume_usdt = volume * close_price
depth_factor = 0.08  # 假设深度为成交量的8%
spread_adjustment = max(0.5, min(1.5, 1.5 - (spread_bps - 5) / 50))
orderbook_depth_usdt = volume_usdt * depth_factor * spread_adjustment
```

## 4. 强度展示（可选）
`prime_strength = 0.6*|S| + 40*clip((p* - 0.60)/0.15, 0, 1)`
`prime_signed = 100*(P_long - P_short) ∈ [-100, 100]`

## 5. 断言与监控
- 断言：坏环境（F↑或 I↓）应观测到 `Teff↑、cost_eff↑、门槛↑`；否则回退中性并告警
- 评测：十分位单调性、可靠性曲线（校准）、事件窗（点火/失锚/清算带）
- 漂移报警：7/14 天 Brier/NLL 恶化、或流动性闸常红 → 自动降频/收紧门槛

## 6. TTL 与并发
标准通道：TTL 8h；新币通道：TTL 2–4h；新币并发=1

## 7. 风险管理规范（v2.1新增）

### 7.1 固定R值法则
**核心原则**：每笔交易风险固定为账户权益的百分比

**参数**：
```python
RISK_PCT = 0.005           # 0.5% per trade
RISK_USDT_CAP = 6.0        # 单笔最大风险$6 USDT
MIN_POSITION_SIZE = 0.001  # 最小仓位（防止过小）
```

**仓位计算**：
```
R_dollar = min(account_equity * RISK_PCT, RISK_USDT_CAP)
position_size = (R_dollar * phase_multiplier * overlay_multiplier) / (ATR * tick_value)
```

### 7.2 新币Phase差异化乘数
**目的**：新币波动大、数据少，需降低风险敞口

**Phase定义**：
```python
ultra_new_0: 0-3分钟   → multiplier = 0.3  (强制保守)
ultra_new_1: 3-8分钟   → multiplier = 0.5
ultra_new_2: 8-15分钟  → multiplier = 0.7
mature:      >15分钟   → multiplier = 1.0  (正常风险)
```

**Phase判定逻辑**：
```python
def get_newcoin_phase(listing_age_minutes, has_history_7d):
    if has_history_7d:
        return "mature"

    if listing_age_minutes < 3:
        return "ultra_new_0"
    elif listing_age_minutes < 8:
        return "ultra_new_1"
    elif listing_age_minutes < 15:
        return "ultra_new_2"
    else:
        return "mature"
```

### 7.3 冷却机制（Cooldown）
**目的**：避免连续止损、情绪化交易

**规则**：
```python
COOLDOWN_AFTER_STOP_LOSS = 8 * 3600   # 8小时
COOLDOWN_AFTER_TAKE_PROFIT = 3 * 3600 # 3小时
COOLDOWN_AFTER_MANUAL = 1 * 3600      # 1小时
```

**实现**：
```python
class RiskManager:
    def __init__(self):
        self.last_exit_time = {}  # {symbol: (exit_reason, timestamp)}

    def check_cooldown(self, symbol, now_ts):
        if symbol not in self.last_exit_time:
            return True, "No cooldown"

        reason, exit_ts = self.last_exit_time[symbol]
        elapsed = now_ts - exit_ts

        if reason == "stop_loss" and elapsed < COOLDOWN_AFTER_STOP_LOSS:
            return False, f"Cooldown: {elapsed/3600:.1f}h < 8h"
        elif reason == "take_profit" and elapsed < COOLDOWN_AFTER_TAKE_PROFIT:
            return False, f"Cooldown: {elapsed/3600:.1f}h < 3h"
        elif reason == "manual" and elapsed < COOLDOWN_AFTER_MANUAL:
            return False, f"Cooldown: {elapsed/3600:.1f}h < 1h"

        return True, "Cooldown expired"
```

### 7.4 并发持仓限制
**规则**：
```python
MAX_CONCURRENT_POSITIONS = 3  # 最多同时持有3个仓位
```

**检查逻辑**：
```python
def can_open_position(self, symbol):
    active_positions = [s for s in self.positions if self.positions[s]["active"]]

    if len(active_positions) >= MAX_CONCURRENT_POSITIONS:
        return False, f"Max concurrent limit: {len(active_positions)}/3"

    return True, "OK"
```

### 7.5 叠加多空保护（Overlay）
**规则**：同一Symbol不能同时持有多空仓位

**保护**：
```python
if symbol in active_positions and positions[symbol]["side"] != new_side:
    return False, "Cannot overlay opposite direction"
```

**例外**：对冲模式（需显式启用，默认禁止）

---

**变更日志**：
- v2.0: 初始版本（§1-6）
- v2.1: 新增概率校准（§1.2）、执行时机保护（§3.2）、执行容纳度（§3.3）、风险管理（§7）
