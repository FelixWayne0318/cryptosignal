# CryptoSignal v7.4 · 四步分层决策系统 - 完整实施指南
# Four-Step Layered Decision System - Complete Implementation Guide

**版本**: v7.4.4-DS (TrendStage模块)
**来源**: 专家提供的完整实施方案
**日期**: 2025-11-16
**更新**: 2025-11-20 (v7.4.4 TrendStage防追高模块)
**状态**: ✅ 已评估，可直接实施

---

## 🎯 方案评估结果

根据`EXPERT_IMPLEMENTATION_PLAN_ASSESSMENT.md`评估：

- ✅ **理论正确性**: 与三点核心修正100%一致
- ✅ **工程完整性**: ⭐⭐⭐⭐⭐ (5/5星)
- ✅ **可执行性**: 可直接交给Claude Code实施
- ✅ **风险控制**: 8步checklist + dual run策略

---

==================================================
0. 模块规划与总入口
==================================================

建议在仓库增加以下模块（文件名仅建议，可调整，但功能边界尽量保持一致）：

- ats_core/decision/step1_direction.py
  Step1 · 方向确认层（A 层 + I 因子 + BTC 方向 + 硬 veto）

- ats_core/decision/step2_timing.py
  Step2 · 时机判断层（Enhanced F v2：Flow(C/O/V/B) vs Price）

- ats_core/decision/step3_risk.py
  Step3 · 风险管理层（支撑/阻力 + ATR + 流动性 + 订单簿占位）

- ats_core/decision/step4_quality.py
  Step4 · 质量控制层（四道门：成交量 / 噪声 / 强度 / 矛盾）

- ats_core/decision/four_step_system.py
  四步系统总入口：run_four_step_decision()
  在现有信号生成流程里加一个开关：
    如果 four_step_system.enabled = true → 走新链路
    否则继续走旧版加权打分链路

配置文件：

- config/params.json
  新增 "four_step_system" 配置块（第 7 节给出示例）


==================================================
1. 统一数据约定（所有 Step 收 / 传 的结构）
==================================================

1.1 因子结构（已存在）

  factor_scores: Dict[str, float]  单时刻因子打分（当前 K 线）
    # A 层方向因子：-100 ~ +100，有符号
    "T": 趋势
    "M": 动量
    "C": CVD / 主动成交流向
    "V": 量能
    "O": 持仓量（OI）
    "B": 基差 / 资金费 / basis

    # B 层调节因子：
    "L": 流动性（0~100 或 -100~+100）
    "S": 结构因子（支撑阻力等，通常带 meta）
    "F": 原时机因子（旧版，可保留但不再参与 Enhanced F）
    "I": 独立性因子 ∈ [0,100]，越高说明对 BTC beta 越低，越独立

  factor_scores_series: List[Dict[str, float]]
    - 过去 N=7 根 1h K 线对应的因子序列（从旧到新）
    - 至少需要 C / O / V / B 这四个维度完整，用于 Flow 动量计算

1.2 BTC 方向数据（用于 Step1）

  btc_factor_scores: Dict[str, float]
    至少：
      "T": float  # BTC 趋势因子（方向 + 强度）
    也可以预先提供：
      btc_direction_score: float  # 通常直接用 T_BTC
      btc_trend_strength: float   # 通常用 abs(T_BTC)

1.3 K 线数据（1h）

  kline = {
      "open_time": int,  # ms
      "open": float,
      "high": float,
      "low": float,
      "close": float,
      "volume": float,
      "atr": float | None,  # 可选；若为空，Step3 内部自己算 ATR
  }
  klines: List[kline]
    - 至少 24 根
    - 用来：
      * 24h 成交量（Gate1）
      * 6h 价格动量（Step2）
      * 最新 atr / 噪声比（Step3 & Gate2）

1.4 S 因子 meta（支撑 / 阻力）

  s_factor_meta: Dict
    推荐格式：
      {
        "zigzag_points": [
          # dt：距当前多少根 K，越小越近（可选）
          {"type": "L", "price": 98.5, "dt": 5},
          {"type": "H", "price": 103.2, "dt": 4},
          {"type": "L", "price": 99.8, "dt": 2},
          {"type": "H", "price": 104.5, "dt": 1},
        ],
        ...
      }

  实际实现可由 S 因子计算模块负责，这里只约定读取方式。

1.5 订单簿分析（本版只放占位）

  orderbook_analysis: Dict
    {
      "buy_wall_price": float | None,
      "sell_wall_price": float | None,
      "buy_depth_score": float,   # 0~100，
      "sell_depth_score": float,  # 0~100，
      "imbalance": float,         # -1 ~ +1（买盘-卖盘失衡）
    }

  本版先做「返回默认值」的占位函数，将真实实现推迟到以后一个版本。

1.6 Step 调用参数统一约定

  所有 Step 统一以 params["four_step_system"] 子树下的配置为主：
    params["four_step_system"]["step1"][...]
    params["four_step_system"]["step2"][...]
    ...

==================================================
2. Step1 · 方向确认层（Direction Confirmation）
==================================================

目标：

  1）用 A 层（T/M/C/V/O/B）算出方向与基础强度
  2）用 I 因子修正置信度（I 高 → 独立 → 高置信度）
  3）用 BTC 方向做 alignment
  4）对「高 Beta 币 + 强 BTC 趋势 + 反向做」触发硬 veto，直接拒绝

----------------------------------------
2.1 A 层方向得分
----------------------------------------

  def calculate_direction_score(factor_scores: dict, weights: dict) -> float:
      """
      A 层综合方向得分：-100 ~ +100
      weights 示例（放在配置里）：
          {
              "T": 0.23,
              "M": 0.10,
              "C": 0.26,
              "V": 0.11,
              "O": 0.20,
              "B": 0.10,
          }
      """
      score = 0.0
      for name in ("T", "M", "C", "V", "O", "B"):
          score += factor_scores.get(name, 0.0) * weights.get(name, 0.0)
      return score

----------------------------------------
2.2 I 因子 → 方向置信度（修正版）
----------------------------------------

语义对齐 independence.py（I ∈ [0,100]，越大越独立，Beta 越低）：

  def calculate_direction_confidence_v2(
      direction_score: float,
      I_score: float,
      params: dict
  ) -> float:
      """
      输出方向置信度 ∈ [0.5, 1.0]
      I_score 高 → 越独立 → 置信度越高
      I_score 低 → 越跟随 BTC → 置信度越低
      """

      high_beta_th = params.get("I_high_beta_threshold", 15)         # 严重跟随
      moderate_beta_th = params.get("I_moderate_beta_threshold", 30) # 中度跟随
      low_beta_th = params.get("I_low_beta_threshold", 50)           # 轻度跟随

      if I_score < high_beta_th:
          # 严重跟随：0.60~0.70
          confidence = 0.60 + (I_score / max(high_beta_th, 1e-6)) * 0.10
      elif I_score < moderate_beta_th:
          # 中度跟随：0.70~0.85
          rng = max(moderate_beta_th - high_beta_th, 1e-6)
          confidence = 0.70 + ((I_score - high_beta_th) / rng) * 0.15
      elif I_score < low_beta_th:
          # 轻度跟随：0.85~0.95
          rng = max(low_beta_th - moderate_beta_th, 1e-6)
          confidence = 0.85 + ((I_score - moderate_beta_th) / rng) * 0.10
      else:
          # 低 Beta，高独立：0.95~1.00
          rng = max(100.0 - low_beta_th, 1e-6)
          confidence = 0.95 + ((I_score - low_beta_th) / rng) * 0.05

      # 保险裁剪
      if confidence < 0.50:
          confidence = 0.50
      if confidence > 1.00:
          confidence = 1.00
      return confidence

----------------------------------------
2.3 BTC 对齐系数（alignment v2）
----------------------------------------

  def calculate_btc_alignment_v2(
      direction_score: float,
      btc_direction_score: float,
      I_score: float,
      params: dict
  ) -> float:
      """
      输出 btc_alignment ∈ [0.70, 1.00]

      逻辑：
        - 方向一致 + 高独立 → 接近 1.0
        - 方向一致 + 高跟随 → 0.9 ~ 0.95（说明只是跟着 BTC 走）
        - 方向相反 + 高独立 → 0.85 ~ 0.95（真独立，可以接受）
        - 方向相反 + 高跟随 → 0.70 ~ 0.80（可疑，可能是假独立）
      """
      same_direction = (direction_score * btc_direction_score) > 0.0
      independence_factor = max(0.0, min(1.0, I_score / 100.0))

      if same_direction:
          # 一致：0.90 ~ 1.00
          alignment = 0.90 + independence_factor * 0.10
      else:
          # 不一致：0.70 ~ 0.95（独立性越高，越能接受逆 BTC）
          alignment = 0.70 + independence_factor * 0.25

      if alignment < 0.70:
          alignment = 0.70
      if alignment > 1.00:
          alignment = 1.00
      return alignment

----------------------------------------
2.4 高 Beta 逆势的硬 veto
----------------------------------------

条件：

  is_high_beta = I_score < step1_high_beta_threshold（默认 30）
  is_strong_btc_trend = |T_BTC| > step1_strong_btc_threshold（默认 70）
  is_opposite_direction = direction_score * btc_direction_score < 0

三者同时满足 → 直接 hard_veto，Step1 不通过。

----------------------------------------
2.5 Step1 总流程封装
----------------------------------------

  def step1_direction_confirmation_v2(
      factor_scores: dict,
      btc_factor_scores: dict,
      params: dict
  ) -> dict:
      """
      返回：
        {
          "direction_score": float,
          "direction_strength": float,        # |direction_score|
          "direction_confidence": float,      # 0.5~1.0
          "btc_alignment": float,             # 0.7~1.0
          "final_strength": float,            # strength * confidence * alignment
          "pass": bool,
          "reject_reason": str | None,
          "hard_veto": bool,
        }
      """
      cfg = params["four_step_system"]["step1"]
      weights = cfg["weights"]  # A 层权重

      # 1. A 层方向得分
      direction_score = calculate_direction_score(factor_scores, weights)
      direction_strength = abs(direction_score)

      # 2. BTC 方向 / 趋势强度 (明确取绝对值 ✅)
      btc_direction_score = btc_factor_scores.get("T", 0.0)
      btc_trend_strength = abs(btc_direction_score)  # 确保非负

      # 3. I 因子置信度
      I_score = factor_scores.get("I", 50.0)
      direction_confidence = calculate_direction_confidence_v2(
          direction_score, I_score, cfg
      )

      # 4. BTC 对齐
      btc_alignment = calculate_btc_alignment_v2(
          direction_score, btc_direction_score, I_score, cfg
      )

      # 5. 硬 veto 检查
      high_beta_threshold = cfg.get("high_beta_threshold", 30.0)
      strong_btc_threshold = cfg.get("strong_btc_threshold", 70.0)

      is_high_beta = I_score < high_beta_threshold
      is_strong_btc = btc_trend_strength > strong_btc_threshold
      is_opposite = (direction_score * btc_direction_score) < 0.0

      if is_high_beta and is_strong_btc and is_opposite:
          return {
              "direction_score": direction_score,
              "direction_strength": direction_strength,
              "direction_confidence": direction_confidence,
              "btc_alignment": btc_alignment,
              "final_strength": 0.0,
              "pass": False,
              "reject_reason": (
                  f"High Beta coin (I={I_score:.1f}) vs strong BTC trend "
                  f"(|T_BTC|={btc_trend_strength:.1f}) - Hard Veto"
              ),
              "hard_veto": True,
          }

      # 6. 最终强度
      final_strength = direction_strength * direction_confidence * btc_alignment
      min_final_strength = cfg.get("min_final_strength", 20.0)
      pass_step1 = final_strength >= min_final_strength

      return {
          "direction_score": direction_score,
          "direction_strength": direction_strength,
          "direction_confidence": direction_confidence,
          "btc_alignment": btc_alignment,
          "final_strength": final_strength,
          "pass": pass_step1,
          "reject_reason": None if pass_step1 else (
              f"方向强度不足: {final_strength:.1f} < {min_final_strength:.1f}"
          ),
          "hard_veto": False,
      }

==================================================
3. Step2 · 时机判断层（Enhanced F v2）
==================================================

核心修正点：

  - 不再用「A 层总分」做 signal_momentum，避免价格自相关；
  - 改为只用 Flow 因子（C/O/V/B）的组合做 flow_momentum；
  - Enhanced_F = flow_momentum - price_momentum；
  - 正数 → 吸筹，负数 → 追高 / 杀跌。

----------------------------------------
3.1 Flow 综合得分（只用 C/O/V/B）
----------------------------------------

  def calculate_flow_score(factor_scores: dict, weights: dict | None) -> float:
      """
      资金/仓位/量能/基差的综合流动得分：-100~+100
      默认权重建议配置在 params["four_step_system"]["step2"]["enhanced_f_flow_weights"]：
        {
          "C": 0.40,
          "O": 0.30,
          "V": 0.20,
          "B": 0.10
        }
      """
      default_w = {
          "C": 0.40,
          "O": 0.30,
          "V": 0.20,
          "B": 0.10,
      }
      w = weights or default_w

      return (
          factor_scores.get("C", 0.0) * w.get("C", 0.0)
          + factor_scores.get("O", 0.0) * w.get("O", 0.0)
          + factor_scores.get("V", 0.0) * w.get("V", 0.0)
          + factor_scores.get("B", 0.0) * w.get("B", 0.0)
      )

----------------------------------------
3.2 Flow 动量（6h 窗口）
----------------------------------------

  def calculate_flow_momentum(
      factor_scores_series: list,
      weights: dict,
      window_hours: int = 6
  ) -> float:
      """
      计算过去 6h 的 Flow 百分比变化（%）

      输入：factor_scores_series 长度至少 7（0~6 小时）
      返回：flow_momentum，单位：百分比（例如 25.0 表示 +25%）
      """
      if len(factor_scores_series) < window_hours + 1:
          return 0.0

      flow_series = [
          calculate_flow_score(scores, weights)
          for scores in factor_scores_series[-(window_hours+1):]
      ]
      flow_ago = flow_series[0]
      flow_now = flow_series[-1]

      # 若两端都很接近 0，认为动量无意义
      if abs(flow_now) < 1.0 and abs(flow_ago) < 1.0:
          return 0.0

      flow_change = flow_now - flow_ago
      base = max(abs(flow_now), abs(flow_ago), 10.0)  # 防止除 0、过小放大

      return (flow_change / base) * 100.0

----------------------------------------
3.3 价格动量（6h）
----------------------------------------

  def calculate_price_momentum(klines: list, window_hours: int = 6) -> float:
      """
      过去 6h 的价格每小时平均变化率（%/h）

      用 close_now / close_6h_ago 计算总收益，再除以 6。
      """
      if len(klines) < window_hours + 1:
          return 0.0

      close_now = float(klines[-1]["close"])
      close_ago = float(klines[-(window_hours+1)]["close"])
      if close_ago <= 0.0:
          return 0.0

      pct_total = (close_now - close_ago) / close_ago * 100.0
      return pct_total / window_hours

----------------------------------------
3.4 Enhanced F v2：Flow vs Price
----------------------------------------

  import math

  def calculate_enhanced_f_factor_v2(
      factor_scores_series: list,
      klines: list,
      params: dict
  ) -> dict:
      """
      返回：
        {
          "enhanced_f": float,      # -100 ~ +100
          "flow_momentum": float,   # %
          "price_momentum": float,  # %/h
          "timing_quality": str,    # "Excellent" / ... / "Chase"
          "flow_weights": dict,     # 实际使用的权重
        }
      """
      cfg = params["four_step_system"]["step2"]
      flow_weights = cfg.get("enhanced_f_flow_weights", {
          "C": 0.40, "O": 0.30, "V": 0.20, "B": 0.10
      })
      window_hours = cfg.get("signal_momentum_window_hours", 6)
      scale = cfg.get("enhanced_f_scale", 20.0)

      flow_momentum = calculate_flow_momentum(
          factor_scores_series,
          flow_weights,
          window_hours=window_hours,
      )
      price_momentum = calculate_price_momentum(
          klines,
          window_hours=window_hours,
      )

      raw = flow_momentum - price_momentum  # 真正的「资金 vs 价格」速度差
      enhanced_f = 100.0 * math.tanh(raw / max(scale, 1e-6))

      # 时机评级
      if enhanced_f >= 80:
          timing_quality = "Excellent"
      elif enhanced_f >= 60:
          timing_quality = "Good"
      elif enhanced_f >= 30:
          timing_quality = "Fair"
      elif enhanced_f >= -30:
          timing_quality = "Mediocre"
      elif enhanced_f >= -60:
          timing_quality = "Poor"
      else:
          timing_quality = "Chase"

      return {
          "enhanced_f": enhanced_f,
          "flow_momentum": flow_momentum,
          "price_momentum": price_momentum,
          "timing_quality": timing_quality,
          "flow_weights": flow_weights,
      }

----------------------------------------
3.5 Step2 总流程封装
----------------------------------------

  def step2_timing_judgment_v2(
      factor_scores_series: list,
      klines: list,
      params: dict
  ) -> dict:
      """
      返回：
        {
          "enhanced_f": float,
          "flow_momentum": float,
          "price_momentum": float,
          "timing_quality": str,
          "entry_signal": bool,
          "pass": bool,
          "reject_reason": str | None,
        }
      """
      cfg = params["four_step_system"]["step2"]
      min_enhanced_f = cfg.get("min_enhanced_f", 30.0)

      res = calculate_enhanced_f_factor_v2(
          factor_scores_series,
          klines,
          params,
      )
      ef = res["enhanced_f"]
      entry_signal = ef >= min_enhanced_f

      res["entry_signal"] = entry_signal
      res["pass"] = entry_signal
      res["reject_reason"] = None if entry_signal else (
          f"时机不佳: Enhanced_F={ef:.1f} < {min_enhanced_f:.1f}"
      )
      return res

----------------------------------------
3.6 TrendStage 模块（v7.4.4 新增）
----------------------------------------

**目的**: 防止追高/追跌，识别趋势阶段并调整时机得分

### 3.6.1 核心概念

TrendStage 通过三个中间量判断当前趋势所处阶段：

| 中间量 | 含义 | 计算方式 |
|--------|------|----------|
| move_atr | 累积ATR距离 | 6h内价格累积位移 / ATR |
| pos_in_range | 区间位置 | 当前价格在24h范围内的位置(0~1) |
| delta_T | 趋势加速度 | T因子最近3根K线的变化 |

### 3.6.2 阶段判断逻辑

```python
def determine_trend_stage(move_atr, pos_in_range, delta_T, direction_sign, params):
    """
    判断趋势阶段: early / mid / late / blowoff

    direction_sign: +1=多头方向, -1=空头方向 (来源于当前T因子符号)
    """
    thresholds = params["trend_stage"]

    # Blowoff检测: 趋势加速度反转
    if direction_sign > 0 and delta_T < thresholds["delta_T_thresholds"]["blowoff_long"]:
        return "blowoff"  # 多头末期，T减速
    if direction_sign < 0 and delta_T > thresholds["delta_T_thresholds"]["blowoff_short"]:
        return "blowoff"  # 空头末期，T减速

    # 基于move_atr和pos_in_range综合判断
    move_th = thresholds["move_atr_thresholds"]
    pos_th = thresholds["pos_thresholds"]

    # Late阶段: 价格已经移动很远 + 处于极端位置
    if move_atr >= move_th["late"]:
        if (direction_sign > 0 and pos_in_range > pos_th["high"]) or \
           (direction_sign < 0 and pos_in_range < pos_th["low"]):
            return "late"

    # Mid阶段: 中等位移
    if move_atr >= move_th["mid"]:
        return "mid"

    # Early阶段: 小位移 + 靠近起点
    if move_atr < move_th["early"]:
        if (direction_sign > 0 and pos_in_range < pos_th["high"]) or \
           (direction_sign < 0 and pos_in_range > pos_th["low"]):
            return "early"

    return "mid"  # 默认
```

### 3.6.3 阶段调整分数

| 阶段 | penalty_by_stage | 含义 |
|------|------------------|------|
| early | +5 | 鼓励早期入场 |
| mid | 0 | 正常 |
| late | -15 | 惩罚追高/追跌 |
| blowoff | -35 | 强烈惩罚末期入场 |

### 3.6.4 Enhanced F 最终公式

```python
# v7.4.4 完整公式
enhanced_f_flow_price = 100 * tanh((flow_momentum - price_momentum) / scale)
s_adjustment = s_timing_boost if theta > theta_threshold else 0

trend_stage_adjustment = penalty_by_stage[trend_stage]

enhanced_f_final = enhanced_f_flow_price + trend_stage_adjustment + s_adjustment

# Chase Zone 硬拒绝
if enhanced_f_final <= chase_reject_threshold:  # 默认 -60
    return REJECT("追高区: enhanced_f_final <= -60")
```

### 3.6.5 Direction Sign 观测点

**重要**: v7.4.4 增加了 direction_sign 来源对齐的观测日志。

- Step1 的 direction_sign: 来自 A层加权合成得分 的符号
- Step2 的 direction_sign: 来自 T因子 的符号

两者可能不一致（例如：A层整体看多但T趋势为负）。当前版本只记录观测，不影响判定逻辑。

### 3.6.6 TrendStage 配置示例

```json
"trend_stage": {
    "_comment": "v7.4.4新增: 趋势阶段判断（防追高/追跌）",
    "enabled": true,
    "atr_lookback": 14,
    "move_atr_window_hours": 6,
    "move_atr_thresholds": {
        "early": 2.0,
        "mid": 4.0,
        "late": 6.0
    },
    "pos_window_hours": 24,
    "pos_thresholds": {
        "low": 0.15,
        "high": 0.85
    },
    "delta_T_lookback": 3,
    "delta_T_thresholds": {
        "blowoff_long": -5.0,
        "blowoff_short": 5.0
    },
    "penalty_by_stage": {
        "early": 5.0,
        "mid": 0.0,
        "late": -15.0,
        "blowoff": -35.0
    },
    "chase_reject_threshold": -60.0
}
```

### 3.6.7 返回结构扩展

v7.4.4 的 step2_timing_judgment 返回结构增加：

```python
{
    # 原有字段...
    "enhanced_f": float,        # flow vs price 基础分
    "enhanced_f_final": float,  # 最终分（含TrendStage调整）
    "trend_stage": str,         # "early" / "mid" / "late" / "blowoff"
    "is_chase_zone": bool,      # 是否触发追高区硬拒绝
    "metadata": {
        "direction_sign": int,  # T因子方向符号
        "move_atr": float,
        "pos_in_range": float,
        "delta_T": float,
        "trend_stage_adjustment": float
    }
}
```

==================================================
4. Step3 · 风险管理层（Risk Management）
==================================================

目标：

  - 给出可执行的：
      entry_price（入场价）
      stop_loss（止损价）
      take_profit（止盈价）
  - 同时输出 risk_pct / reward_pct / risk_reward_ratio；
  - 使用：
      S 因子 ZigZag 结构（支撑阻力）
      ATR 动态波动率
      L 因子（流动性）调节止损宽度
      （订单簿目前只作为占位）

----------------------------------------
4.1 提取支撑 / 阻力（来自 S meta）
----------------------------------------

  def extract_support_resistance(s_factor_meta: dict) -> dict:
      """
      从 S 因子 meta 中抽取最近支撑位 / 阻力位及其简单「强度」。
      返回：
        {
          "support": float | None,
          "resistance": float | None,
          "support_strength": int,
          "resistance_strength": int,
        }
      """
      points = (s_factor_meta or {}).get("zigzag_points", [])
      if not points:
          return {
              "support": None,
              "resistance": None,
              "support_strength": 0,
              "resistance_strength": 0,
          }

      lows = [p["price"] for p in points if p.get("type") == "L"]
      highs = [p["price"] for p in points if p.get("type") == "H"]

      support = lows[-1] if lows else None
      resistance = highs[-1] if highs else None

      recent = points[-3:]
      support_strength = sum(1 for p in recent if p.get("type") == "L")
      resistance_strength = sum(1 for p in recent if p.get("type") == "H")

      return {
          "support": support,
          "resistance": resistance,
          "support_strength": support_strength,
          "resistance_strength": resistance_strength,
      }

----------------------------------------
4.2 订单簿分析占位实现
----------------------------------------

  def analyze_orderbook_placeholder(symbol: str, exchange: str) -> dict:
      """
      占位版本：
        - 暂时不连交易所
        - 后续版本再替换为真实实现
      """
      return {
          "buy_wall_price": None,
          "sell_wall_price": None,
          "buy_depth_score": 50.0,
          "sell_depth_score": 50.0,
          "imbalance": 0.0,
      }

----------------------------------------
4.3 简易ATR计算（如果K线中没有atr字段）
----------------------------------------

  def calculate_simple_atr(klines: list, period: int = 14) -> float:
      """
      简易ATR计算 (如果K线中没有atr字段)
      """
      if len(klines) < period + 1:
          return 0.0

      trs = []
      for i in range(-period, 0):
          high = float(klines[i]["high"])
          low = float(klines[i]["low"])
          prev_close = float(klines[i-1]["close"])

          tr = max(
              high - low,
              abs(high - prev_close),
              abs(low - prev_close)
          )
          trs.append(tr)

      return sum(trs) / len(trs)

----------------------------------------
4.4 计算入场价 entry_price
----------------------------------------

  def calculate_entry_price(
      current_price: float,
      support: float | None,
      resistance: float | None,
      enhanced_f: float,
      direction_score: float,
      orderbook: dict,
      params: dict
  ) -> float:
      """
      做多：
        Enhanced_F >= 70 → 直接现价入场
        Enhanced_F >= 40 → 等支撑附近 0.2%（有支撑）；否则现价下方 0.2%
        Else           → 等支撑附近 0.5%；否则现价下方 0.5%
        若存在买墙，则 entry_price 不低于买墙略上方

      做空对称。
      """
      is_long = direction_score > 0.0
      buy_wall = (orderbook or {}).get("buy_wall_price")
      sell_wall = (orderbook or {}).get("sell_wall_price")

      if is_long:
          if enhanced_f >= 70:
              entry = current_price
          elif enhanced_f >= 40:
              if support is not None:
                  entry = support * 1.002
              else:
                  entry = current_price * 0.998
          else:
              if support is not None:
                  entry = support * 1.005
              else:
                  entry = current_price * 0.995

          if buy_wall and entry < buy_wall:
              entry = buy_wall * 1.001

      else:
          if enhanced_f >= 70:
              entry = current_price
          elif enhanced_f >= 40:
              if resistance is not None:
                  entry = resistance * 0.998
              else:
                  entry = current_price * 1.002
          else:
              if resistance is not None:
                  entry = resistance * 0.995
              else:
                  entry = current_price * 1.005

          if sell_wall and entry > sell_wall:
              entry = sell_wall * 0.999

      return entry

----------------------------------------
4.5 止损价 stop_loss（结构 + ATR）
----------------------------------------

  def calculate_stop_loss(
      entry_price: float,
      support: float | None,
      resistance: float | None,
      atr: float,
      direction_score: float,
      l_score: float,
      params: dict
  ) -> float:
      """
      综合两种：
        1）结构止损（支撑 / 阻力附近 0.2%）
        2）ATR * 倍数（倍数随 L 因子调节）

      最终取更「保守」的那个：
        多头：取更高的止损（离 entry 更近）；
        空头：取更低的止损（离 entry 更近）。
      """
      cfg = params["four_step_system"]["step3"]
      base_mult = cfg.get("stop_loss_atr_multiplier", 2.0)

      # L 因子调节倍数
      if l_score < -30:
          atr_mult = base_mult * 1.5   # 低流动性 → 止损放宽
      elif l_score > 30:
          atr_mult = base_mult * 0.8   # 高流动性 → 止损收紧
      else:
          atr_mult = base_mult

      is_long = direction_score > 0.0

      if is_long:
          structure_stop = support * 0.998 if support is not None else None
          vol_stop = entry_price - atr * atr_mult

          if structure_stop is not None:
              stop_loss = max(structure_stop, vol_stop)
          else:
              stop_loss = vol_stop
      else:
          structure_stop = resistance * 1.002 if resistance is not None else None
          vol_stop = entry_price + atr * atr_mult

          if structure_stop is not None:
              stop_loss = min(structure_stop, vol_stop)
          else:
              stop_loss = vol_stop

      return stop_loss

----------------------------------------
4.6 止盈价 take_profit（赔率约束 + 结构）
----------------------------------------

  def calculate_take_profit(
      entry_price: float,
      stop_loss: float,
      resistance: float | None,
      support: float | None,
      direction_score: float,
      params: dict
  ) -> float:
      """
      最低赔率要求：min_risk_reward_ratio（默认 ≥1.5）
      若有结构位（阻力 / 支撑），在此基础上再对齐结构。
      """
      cfg = params["four_step_system"]["step3"]
      min_rr = cfg.get("min_risk_reward_ratio", 1.5)

      is_long = direction_score > 0.0
      risk = abs(entry_price - stop_loss)

      if risk <= 0:
          # 防御性处理，避免 0 除
          risk = entry_price * 0.005  # 0.5%

      if is_long:
          min_target = entry_price + risk * min_rr
          if resistance is not None:
              structure_target = resistance * 0.998
          else:
              structure_target = min_target
          take_profit = max(min_target, structure_target)
      else:
          min_target = entry_price - risk * min_rr
          if support is not None:
              structure_target = support * 1.002
          else:
              structure_target = min_target
          take_profit = min(min_target, structure_target)

      return take_profit

----------------------------------------
4.7 Step3 总流程封装
----------------------------------------

  def step3_risk_management(
      symbol: str,
      exchange: str,
      klines: list,
      s_factor_meta: dict,
      l_score: float,
      direction_score: float,
      enhanced_f: float,
      params: dict
  ) -> dict:
      """
      返回：
        {
          "entry_price": float,
          "stop_loss": float,
          "take_profit": float,
          "risk_pct": float,
          "reward_pct": float,
          "risk_reward_ratio": float,
          "support": float | None,
          "resistance": float | None,
          "pass": bool,
          "reject_reason": str | None,
        }
      """
      current_price = float(klines[-1]["close"])
      atr = float(klines[-1].get("atr") or 0.0)

      # 如果当前没有 ATR，用简易版计算
      if atr <= 0:
          atr = calculate_simple_atr(klines)

      sr = extract_support_resistance(s_factor_meta)
      orderbook = analyze_orderbook_placeholder(symbol, exchange)

      entry_price = calculate_entry_price(
          current_price=current_price,
          support=sr["support"],
          resistance=sr["resistance"],
          enhanced_f=enhanced_f,
          direction_score=direction_score,
          orderbook=orderbook,
          params=params,
      )
      stop_loss = calculate_stop_loss(
          entry_price=entry_price,
          support=sr["support"],
          resistance=sr["resistance"],
          atr=atr,
          direction_score=direction_score,
          l_score=l_score,
          params=params,
      )
      take_profit = calculate_take_profit(
          entry_price=entry_price,
          stop_loss=stop_loss,
          resistance=sr["resistance"],
          support=sr["support"],
          direction_score=direction_score,
          params=params,
      )

      # 风险 / 收益百分比
      risk_pct = abs(entry_price - stop_loss) / entry_price * 100.0
      reward_pct = abs(take_profit - entry_price) / entry_price * 100.0
      rr = reward_pct / max(risk_pct, 0.01)

      cfg = params["four_step_system"]["step3"]
      min_rr = cfg.get("min_risk_reward_ratio", 1.5)
      pass_step3 = rr >= min_rr

      return {
          "entry_price": round(entry_price, 6),
          "stop_loss": round(stop_loss, 6),
          "take_profit": round(take_profit, 6),
          "risk_pct": round(risk_pct, 2),
          "reward_pct": round(reward_pct, 2),
          "risk_reward_ratio": round(rr, 2),
          "support": sr["support"],
          "resistance": sr["resistance"],
          "pass": pass_step3,
          "reject_reason": None if pass_step3 else (
              f"赔率不足: {rr:.2f} < {min_rr:.2f}"
          ),
      }

==================================================
5. Step4 · 质量控制层（Quality Control）
==================================================

复用现有「四道门」思想，但与四步结构对齐：

  Gate1：基础筛选（24h 成交量、价格范围等）
  Gate2：噪声过滤（ATR / Price）
  Gate3：信号强度（Prime_Strength or final_strength）
  Gate4：矛盾检测（因子之间、趋势 vs F 因子）

----------------------------------------
5.1 Step4 总流程
----------------------------------------

  def step4_quality_control(
      symbol: str,
      klines: list,
      factor_scores: dict,
      prime_strength: float,
      step1_result: dict,
      step2_result: dict,
      step3_result: dict,
      params: dict
  ) -> dict:
      """
      返回：
        {
          "gate1_pass": bool,
          "gate2_pass": bool,
          "gate3_pass": bool,
          "gate4_pass": bool,
          "all_gates_pass": bool,
          "final_decision": "ACCEPT" | "REJECT",
          "reject_reason": str | None,
        }
      """
      cfg = params["four_step_system"]["step4"]

      # Gate1：24h 成交量
      volume_24h = sum(float(k["volume"]) for k in klines[-24:])
      min_vol = cfg.get("gate1_min_volume_24h", 1_000_000.0)
      gate1_pass = volume_24h >= min_vol
      gate1_reason = None if gate1_pass else (
          f"24h 成交量不足: {volume_24h:.0f} < {min_vol:.0f}"
      )

      # Gate2：噪声（ATR / Price）
      close_now = float(klines[-1]["close"])
      atr = float(klines[-1].get("atr") or 0.0)
      noise_ratio = (atr / close_now) if close_now > 0 else 1.0
      max_noise = cfg.get("gate2_max_noise_ratio", 0.15)  # 15%
      gate2_pass = noise_ratio <= max_noise
      gate2_reason = None if gate2_pass else (
          f"噪声过高: {noise_ratio:.2%} > {max_noise:.2%}"
      )

      # Gate3：信号强度
      min_strength = cfg.get("gate3_min_prime_strength", 35.0)
      gate3_pass = prime_strength >= min_strength
      gate3_reason = None if gate3_pass else (
          f"信号强度不足: {prime_strength:.1f} < {min_strength:.1f}"
      )

      # Gate4：矛盾检测
      c_score = factor_scores.get("C", 0.0)
      o_score = factor_scores.get("O", 0.0)
      t_score = factor_scores.get("T", 0.0)
      ef = step2_result.get("enhanced_f", 0.0)

      # 矛盾1：C 与 O 强烈对冲（方向相反且都绝对值较大）
      contradiction1 = (abs(c_score) > 60 and abs(o_score) > 60 and (c_score * o_score) < 0)

      # 矛盾2：趋势强 + Enhanced_F 很负（强趋势但明显追高）
      contradiction2 = (abs(t_score) > 70 and ef < -40)

      gate4_pass = not (contradiction1 or contradiction2)
      if contradiction1:
          gate4_reason = (
              f"C 与 O 因子方向矛盾: C={c_score:.1f}, O={o_score:.1f}"
          )
      elif contradiction2:
          gate4_reason = (
              f"趋势与时机矛盾: T={t_score:.1f}, Enhanced_F={ef:.1f}"
          )
      else:
          gate4_reason = None

      all_gates_pass = gate1_pass and gate2_pass and gate3_pass and gate4_pass

      if all_gates_pass:
          final_decision = "ACCEPT"
          reject_reason = None
      else:
          final_decision = "REJECT"
          reject_reason = (
              gate1_reason
              or gate2_reason
              or gate3_reason
              or gate4_reason
          )

      return {
          "gate1_pass": gate1_pass,
          "gate2_pass": gate2_pass,
          "gate3_pass": gate3_pass,
          "gate4_pass": gate4_pass,
          "all_gates_pass": all_gates_pass,
          "final_decision": final_decision,
          "reject_reason": reject_reason,
      }

==================================================
6. 四步系统总入口 · run_four_step_decision
==================================================

放在：ats_core/decision/four_step_system.py

----------------------------------------
6.1 总入口函数定义
----------------------------------------

  def run_four_step_decision(
      symbol: str,
      exchange: str,
      klines: list,
      factor_scores: dict,
      factor_scores_series: list,
      btc_factor_scores: dict,
      s_factor_meta: dict,
      prime_strength: float,
      params: dict,
  ) -> dict:
      """
      高层总入口：
        - 如果某一步 fail，则返回 REJECT + 原因
        - 如果全部通过，返回 ACCEPT + 完整的四步结果 + 交易建议

      返回示例结构：
        {
          "symbol": "ETHUSDT",
          "decision": "ACCEPT" | "REJECT",
          "reason": str | None,

          "step1_direction": {...},
          "step2_timing": {...},
          "step3_risk": {...} or None,
          "step4_quality": {...} or None,

          "action": "LONG" | "SHORT" | None,
          "entry_price": float | None,
          "stop_loss": float | None,
          "take_profit": float | None,
          "risk_pct": float | None,
          "reward_pct": float | None,
          "risk_reward_ratio": float | None,
        }
      """
      fs = factor_scores
      four_cfg = params.get("four_step_system", {})

      # Step1：方向确认
      from ats_core.decision.step1_direction import step1_direction_confirmation_v2
      s1 = step1_direction_confirmation_v2(
          factor_scores=fs,
          btc_factor_scores=btc_factor_scores,
          params=params,
      )
      if not s1["pass"]:
          return {
              "symbol": symbol,
              "decision": "REJECT",
              "reason": s1["reject_reason"],
              "step1_direction": s1,
              "step2_timing": None,
              "step3_risk": None,
              "step4_quality": None,
              "action": None,
              "entry_price": None,
              "stop_loss": None,
              "take_profit": None,
              "risk_pct": None,
              "reward_pct": None,
              "risk_reward_ratio": None,
          }

      # Step2：时机判断
      from ats_core.decision.step2_timing import step2_timing_judgment_v2
      s2 = step2_timing_judgment_v2(
          factor_scores_series=factor_scores_series,
          klines=klines,
          params=params,
      )
      if not s2["pass"]:
          return {
              "symbol": symbol,
              "decision": "REJECT",
              "reason": s2["reject_reason"],
              "step1_direction": s1,
              "step2_timing": s2,
              "step3_risk": None,
              "step4_quality": None,
              "action": None,
              "entry_price": None,
              "stop_loss": None,
              "take_profit": None,
              "risk_pct": None,
              "reward_pct": None,
              "risk_reward_ratio": None,
          }

      # Step3：风险管理（生成具体价位）
      from ats_core.decision.step3_risk import step3_risk_management
      s3 = step3_risk_management(
          symbol=symbol,
          exchange=exchange,
          klines=klines,
          s_factor_meta=s_factor_meta,
          l_score=fs.get("L", 0.0),
          direction_score=s1["direction_score"],
          enhanced_f=s2["enhanced_f"],
          params=params,
      )
      if not s3["pass"]:
          return {
              "symbol": symbol,
              "decision": "REJECT",
              "reason": s3["reject_reason"],
              "step1_direction": s1,
              "step2_timing": s2,
              "step3_risk": s3,
              "step4_quality": None,
              "action": None,
              "entry_price": None,
              "stop_loss": None,
              "take_profit": None,
              "risk_pct": None,
              "reward_pct": None,
              "risk_reward_ratio": None,
          }

      # Step4：质量控制
      from ats_core.decision.step4_quality import step4_quality_control
      s4 = step4_quality_control(
          symbol=symbol,
          klines=klines,
          factor_scores=factor_scores,
          prime_strength=prime_strength,
          step1_result=s1,
          step2_result=s2,
          step3_result=s3,
          params=params,
      )
      if s4["final_decision"] != "ACCEPT":
          return {
              "symbol": symbol,
              "decision": "REJECT",
              "reason": s4["reject_reason"],
              "step1_direction": s1,
              "step2_timing": s2,
              "step3_risk": s3,
              "step4_quality": s4,
              "action": None,
              "entry_price": None,
              "stop_loss": None,
              "take_profit": None,
              "risk_pct": None,
              "reward_pct": None,
              "risk_reward_ratio": None,
          }

      # 四步全部通过 → 输出最终交易建议
      action = "LONG" if s1["direction_score"] > 0 else "SHORT"

      return {
          "symbol": symbol,
          "decision": "ACCEPT",
          "reason": None,
          "step1_direction": s1,
          "step2_timing": s2,
          "step3_risk": s3,
          "step4_quality": s4,
          "action": action,
          "entry_price": s3["entry_price"],
          "stop_loss": s3["stop_loss"],
          "take_profit": s3["take_profit"],
          "risk_pct": s3["risk_pct"],
          "reward_pct": s3["reward_pct"],
          "risk_reward_ratio": s3["risk_reward_ratio"],
      }

==================================================
7. 配置示例（config/params.json 片段）
==================================================

  "four_step_system": {
    "enabled": true,

    "step1": {
      "min_final_strength": 20.0,

      "weights": {
        "T": 0.23,
        "M": 0.10,
        "C": 0.26,
        "V": 0.11,
        "O": 0.20,
        "B": 0.10
      },

      "I_high_beta_threshold": 15,
      "I_moderate_beta_threshold": 30,
      "I_low_beta_threshold": 50,

      "high_beta_threshold": 30,
      "strong_btc_threshold": 70
    },

    "step2": {
      "enhanced_f_scale": 20.0,
      "min_enhanced_f": 30.0,
      "signal_momentum_window_hours": 6,

      "enhanced_f_flow_weights": {
        "C": 0.40,
        "O": 0.30,
        "V": 0.20,
        "B": 0.10
      }
    },

    "step3": {
      "stop_loss_atr_multiplier": 2.0,
      "min_risk_reward_ratio": 1.5
    },

    "step4": {
      "gate1_min_volume_24h": 1000000,
      "gate2_max_noise_ratio": 0.15,
      "gate3_min_prime_strength": 35
    }
  }

==================================================
8. 实施 Checklist（8步执行指南）
==================================================

1）新增文件并复制对应函数骨架：
   - ats_core/decision/step1_direction.py
   - ats_core/decision/step2_timing.py
   - ats_core/decision/step3_risk.py
   - ats_core/decision/step4_quality.py
   - ats_core/decision/four_step_system.py

2）严格按上面函数签名 & 返回结构实现代码（可以加日志 / type hints / 单测）。

3）在现有信号生成主流程（例如 ats_core/pipeline/analyze_symbol.py 或 realtime_signal_scanner 里）：
   - 计算所有因子（现有逻辑不动）；
   - 构造 factor_scores, factor_scores_series, btc_factor_scores, s_factor_meta, prime_strength；
   - 如果 params["four_step_system"]["enabled"] 为真：
       调用 run_four_step_decision()；
       用返回的结果决定是否生成 Telegram 信号 + 文案；
     否则：
       走旧版加权打分 → 保持向后兼容。

4）先在「回测 / 仿真环境」接入四步系统，跑一段时间对比：
   - 吸筹识别率、追高拦截率；
   - 胜率变化、赔率分布；
   - 信号数量变化。

5）确认回测 OK 后，再切换生产环境开关：
   - 先「dual run」一段时间（新旧系统并行，旧系统仍负责真实出信号）；
   - 观察差异，再考虑让四步系统接管生产信号。

6）添加单元测试：
   - 每个Step的核心函数都要有单测
   - 测试边界情况（空数据、极端值）
   - 测试硬veto触发条件

7）添加日志和监控：
   - 每个Step的决策结果
   - 拒绝原因统计
   - 关键参数分布（Enhanced_F, confidence, alignment等）

8）文档更新：
   - 更新用户文档，说明新系统特性
   - 更新开发文档，说明模块职责
   - 记录关键参数的调优历史

==================================================
9. 注意事项与风险控制
==================================================

### 风险点1: 参数调优

- 所有阈值（min_final_strength, min_enhanced_f等）都需要回测验证
- 避免过度拟合历史数据
- 建议使用walk-forward analysis

### 风险点2: 数据依赖

- factor_scores_series必须完整（至少7根K线的所有因子）
- BTC数据可能缺失，需要降级处理
- S因子ZigZag可能为空，已有降级逻辑

### 风险点3: 性能影响

- 四步系统比旧系统复杂，计算量更大
- 建议做性能profiling
- 考虑缓存factor_scores_series

### 风险点4: 向后兼容

- 保持旧系统并行运行一段时间
- 新旧系统输出对比分析
- 渐进式切换策略

---

## ✅ 总结

这是一个**可以直接执行**的完整实施方案，包含：

1. ✅ 完整的代码模板（带类型提示和错误处理）
2. ✅ 统一的数据约定
3. ✅ 详细的配置示例
4. ✅ 8步实施checklist
5. ✅ 风险控制策略

**下一步**: 按照第8节的checklist开始实施！
