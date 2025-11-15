I 因子问题分析 & 重构方案说明（给 Claude Code）

用途：把这一整段作为规格说明，交给 Claude Code 实施对 I 因子（independence）的重构，涉及：
- independence.py
- ModulatorChain（独立性相关部分）
- analyze_symbol / batch_scan_optimized（接入 MarketContext + I 闸门）

==================================================
一、现状问题诊断（I 因子）
==================================================

【目标（用户当前共识）】
1. 大盘锚定：只用 BTC 判断大盘趋势。
2. I 因子角色：
   - 衡量“币对 BTC 的独立性”（低 β = 高度跟随 BTC，高 β 表示“Beta 币”）。
   - 作为风控闸门，核心要解决：
     - 高 Beta 币在 BTC 强趋势下逆势乱搞；
     - 高 Beta + 信号不强的噪音交易。

【当前方案暴露出的主要问题】：

(1) 仍然是 BTC+ETH 双因子世界观

当前 independence 方案中类似逻辑：

    beta, r_squared = _calculate_beta(symbol_data, T_BTC, T_ETH)

说明：
- I 仍使用 BTC+ETH 作为因子输入，与“只用 BTC 做大盘锚点”的目标不一致。
- 用户已经决定：大盘只看 BTC，ETH 当普通大币处理。

(2) β 回归输入不干净

正确的统计定义应该是：

    alt_ret = α + β_BTC * btc_ret + ε

即：
- 自变量是 BTC 的收益率（价格变化），
- 因变量是该币的收益率。

当前接口不明确，很可能把 T_BTC / T_ETH 这种“已经加工过的因子输出”当自变量，这有两个问题：
- 统计含义混乱：变成“对系统自家因子的敏感度”，而不是对市场收益的敏感度。
- 信息污染：T 因子本身已经包含参数、EMA、滤波等，再用来回归会把系统结构和真实独立性搅在一起。

(3) 硬 veto 只看 β/R²，没有结合 BTC 趋势、币自身趋势和信号强度

当前类似逻辑：

    if beta > 1.5 and r_squared > 0.6:
        should_veto = True
        veto_reason = "high_beta_strong_correlation"
    elif beta > 2.0:
        should_veto = True
        veto_reason = "extreme_beta"

问题：
- 不区分“顺着 BTC 强趋势的标准 Beta 趋势单”和“逆着 BTC 强趋势乱干”。
- 不区分“高 Beta 且综合分数极强” vs “高 Beta 且只是小波动噪音”。
- 容易出现：
  - 误杀：该做的 Beta 趋势单被 veto；
  - 漏杀：不该做的逆势 Beta 单没被 veto。

(4) I 打分定义与文档不统一

实现有类似：

    I_raw = (1.0 - beta) * 100    # Beta 越低，I 越高
    I_pub = int(np.clip(I_raw, -100, 100))

而文档中：
- I 被定义为 0~100 的质量因子（非中心化）。
实际代码：
- I_raw 可能是负数，clip 到 [-100,100]。
-> 定义不统一，会给后续监控和调参带来困惑。

(5) veto / 阈值调整 / 软调制混在同一逻辑里

当前 independence 相关逻辑同时在一个函数里输出：
- should_veto / veto_reason
- threshold_adjustment
- confidence_mod / cost_multiplier

问题：
- 风控闸门逻辑与软调制逻辑耦合太紧；
- 日后 debug “为什么被 veto”“为什么阈值改变”会比较困难；
- 不利于把 I 因子当作一个清晰的风控模块来监控和调参。

==================================================
二、目标状态（I 因子想要达到的效果）
==================================================

1）统计定义干净：
- I 只基于“BTC 价格/收益率”和“本币价格/收益率”做单因子回归：
  alt_ret = α + β_BTC * btc_ret + ε。
- 得到 β_BTC、R²，β_BTC 真实反映币对 BTC 的跟随程度。

2）功能定位明确：
- I 是“独立性质量因子 + 风控闸门”，不参与 A 层方向评分。
- 高 Beta（强跟随 BTC）的币：
  - 在 BTC 强趋势下，禁止逆 BTC 趋势开仓。
  - 在信号强度不足时，一律不做，避免噪音交易。
- 高独立币（低 Beta）：
  - 可适当放宽信号阈值，给独立趋势/Alpha 更多机会。

3）逻辑分层清晰：
- β 计算层：只计算 β_BTC / R²，不做任何风控和调制。
- I 打分层：将 |β_BTC| 映射到 I∈[0,100]。
- 风控层：用 I + T_BTC + T_alt + composite_score 做 veto / 有效阈值。
- 软调制层：微调 confidence / cost，与 veto 解耦。

==================================================
三、具体重构方案（实施清单）
==================================================

-----------------------------
3.1 independence 输入与接口重构：BTC-only + 价格/收益
-----------------------------

目标：
- 让 score_independence 明确基于 alt/BTC 价格序列或收益序列；
- 不再把 T_BTC / T_ETH 当回归自变量；
- independence 不再用 ETH 参与 β 计算（ETH 保留在 MarketContext，供其他模块使用）。

建议：
1）如现有架构方便，可在 MarketContext 中增加 BTC 价格或 BTC 返回值的引用（也可以仅由调用方传入 btc_prices）：

    @dataclass
    class MarketContext:
        T_BTC: float
        M_BTC: float
        regime_BTC: str
        T_ETH: float
        M_ETH: float
        timestamp: int
        cache_key: str
        # 可选：btc_prices 或供 independence 取数的 key

2）score_independence 接口建议改为类似：

    def score_independence(
        alt_prices: np.ndarray,
        btc_prices: np.ndarray,
        params: Dict
    ) -> Tuple[int, Dict]:
        """
        I（独立性）因子 - BTC-only 版本
        - 使用 alt/BTC log-return 做回归，得到 beta_btc, r2
        - 输出 I_score (0~100) + 元数据
        """

调用端可以从 MarketContext 里或其他地方取 alt_prices / btc_prices 传入。

-----------------------------
3.2 实现 BTC-only β 回归（calculate_beta_btc_only）
-----------------------------

伪代码逻辑：

    def calculate_beta_btc_only(
        alt_prices: np.ndarray,
        btc_prices: np.ndarray,
        window_hours: int,
        min_points: int,
    ) -> Tuple[float, float, int]:
        """
        返回: beta_btc, r2, n_points
        """
        # 1) 对齐长度，截取最近 window_hours 对应的样本
        # 2) 计算 log-return:
        #    alt_ret = diff(log(alt_prices))
        #    btc_ret = diff(log(btc_prices))
        #
        # 3) 对 alt_ret / btc_ret 分别做 3σ 截断(去极值)，构造联合 mask
        # 4) 有效样本数 < min_points 时：
        #    - 返回 beta=0, r2=0, n_points
        #    - 后续 I 一律给中性值 50，不参与 veto
        #
        # 5) 用 OLS 回归:
        #    alt_ret = α + β * btc_ret + ε
        #    计算 beta_btc, r2
        #
        # 6) 返回 beta_btc, r2, n_points

要求：
- β_BTC、R² 具备正常金融统计含义；
- R² 太低时（如 <0.1），视为不可靠，后续 I 给 50。

-----------------------------
3.3 I 打分统一为 0~100 质量因子
-----------------------------

配置建议（写入 config）：

    "I调制器配置": {
      "window_hours": 24,
      "min_points": 16,
      "beta_low": 0.6,    // |β| <= 0.6 → 高独立
      "beta_high": 1.2,   // |β| >= 1.2 → 高度相关（Beta 币）
      "r2_min": 0.1
    }

映射规则：

- 若 r2 < r2_min：
  - 认为回归不可靠 → I = 50（中性，不参与硬闸门，仅用于轻微调制）。
- 否则根据 |β_BTC| 映射到 I∈[0,100]：
  - |β| ≤ beta_low → I 在 85~100 区间（高独立性），可线性或缓步上升；
  - |β| ≥ beta_high → I 在 0~30 区间（高度跟随 BTC 的 Beta 币）；
  - beta_low < |β| < beta_high → I 在 85 → 30 之间线性插值。
- 输出保证：0 <= I <= 100。

返回值示例：

    I_score  # int, 0~100

    metadata = {
        "beta_btc": float,
        "r2": float,
        "n_points": int,
        "I_raw": float,     # 未截断的原始映射前数值，便于调试
        "status": "ok" / "low_r2" / "insufficient_data"
    }

-----------------------------
3.4 I 因子风控闸门（veto）逻辑
-----------------------------

目标：
- 高 Beta 币在 BTC 强趋势下逆势 → 必 veto；
- 高 Beta 币信号不强 → 不做；
- 高独立币 → 放宽信号阈值。

配置块（写入 config）：

    "I调制器配置": {
      ...
      "gate": {
        "corr_strong_max_I": 30,        // I <= 30 → 高度相关 Beta 币
        "indep_strong_min_I": 70,       // I >= 70 → 高度独立
        "btc_trend_strong_T": 60,       // |T_BTC| >= 60 → BTC 强趋势
        "min_score_for_corr": 70,       // 高 Beta 币想做，|composite_score| 至少 70
        "relax_score_for_indep": 45     // 高独立币，阈值可从 50 放宽到 45
      }
    }

伪代码（风控层逻辑）：

    def apply_I_gate(I, T_BTC, T_alt, composite_score, cfg):
        gate_cfg = cfg["I调制器配置"]["gate"]
        corr_strong_max_I     = gate_cfg["corr_strong_max_I"]
        indep_strong_min_I    = gate_cfg["indep_strong_min_I"]
        btc_trend_strong_T    = gate_cfg["btc_trend_strong_T"]
        min_score_for_corr    = gate_cfg["min_score_for_corr"]
        relax_score_for_indep = gate_cfg["relax_score_for_indep"]

        veto = False
        veto_reasons = []

        # 规则 1：高 Beta 币逆 BTC 强趋势 → 强制 veto
        if I <= corr_strong_max_I and abs(T_BTC) >= btc_trend_strong_T:
            if np.sign(T_alt) * np.sign(T_BTC) < 0:
                veto = True
                veto_reasons.append("beta_coin_against_btc_trend")

        # 规则 2：高 Beta 币信号不够强 → 不做
        if not veto and I <= corr_strong_max_I and abs(composite_score) < min_score_for_corr:
            veto = True
            veto_reasons.append("beta_coin_weak_signal")

        # 阈值放宽：高独立币特权
        base_threshold = cfg["信号生成配置"]["signal_threshold"]  # 例如 50
        effective_threshold = base_threshold
        if I >= indep_strong_min_I:
            effective_threshold = min(base_threshold, relax_score_for_indep)

        return {
            "veto": veto,
            "veto_reasons": veto_reasons,
            "effective_threshold": effective_threshold
        }

说明：
- 规则 1 利用：I（是否 Beta 币）+ T_BTC（大盘强趋势）+ T_alt（本币趋势方向）做“逆势 Beta 币必杀”；
- 规则 2 利用：I + composite_score 做“弱信号 Beta 币一律不做”；
- 放宽阈值仅对高独立币生效，不影响 Beta 币。

-----------------------------
3.5 将 veto 与软调制逻辑解耦（ModulatorChain）
-----------------------------

在 ModulatorChain 中，将独立性相关逻辑切成两部分：

1）风控输出：

    {
      "veto": bool,
      "veto_reasons": List[str],
      "effective_threshold": float
    }

2）软调制输出（沿用原有“高独立 +conf / 高相关 +cost”逻辑）：

    {
      "confidence_boost": float,
      "cost_multiplier": float
    }

综合接口建议：

    def apply_independence_modulation(I, T_btc, T_alt, score, cfg):
        gate_info = apply_I_gate(I, T_btc, T_alt, score, cfg)

        # 软调制示例（可按原有区间逻辑调整）
        if I >= 70:
            confidence_boost = +0.15
            cost_multiplier = 1.0
        elif I >= 50:
            confidence_boost = +0.05
            cost_multiplier = 1.0
        elif I >= 30:
            confidence_boost = 0.0
            cost_multiplier = 1.1
        else:
            confidence_boost = -0.10
            cost_multiplier = 1.2

        return {
            "veto": gate_info["veto"],
            "veto_reasons": gate_info["veto_reasons"],
            "effective_threshold": gate_info["effective_threshold"],
            "confidence_boost": confidence_boost,
            "cost_multiplier": cost_multiplier
        }

-----------------------------
3.6 analyze_symbol 中的接入方式
-----------------------------

在 analyze_symbol 中按以下顺序接入 I：

1）计算 A 层 6 因子：T/M/C/V/O/B，得到 composite_score。

2）计算 I 因子：

    I_score, i_meta = score_independence(alt_prices, btc_prices, independence_params)

3）调用 ModulatorChain 获取 I 的风控 + 软调制输出：

    i_mod = modulator_chain.apply_independence_modulation(
        I=I_score,
        T_btc=market_context.T_BTC,
        T_alt=T,
        score=composite_score,
        cfg=config
    )

4）确定有效阈值 + 初步信号方向：

    base_threshold = config["信号生成配置"]["signal_threshold"]  # 如 50
    effective_threshold = i_mod.get("effective_threshold", base_threshold)

    if composite_score > effective_threshold:
        raw_signal = "LONG"
    elif composite_score < -effective_threshold:
        raw_signal = "SHORT"
    else:
        raw_signal = "NEUTRAL"

5）应用 I veto：

    if i_mod["veto"] and raw_signal != "NEUTRAL":
        signal = "NEUTRAL"
        signal_blocked_by = i_mod["veto_reasons"]
    else:
        signal = raw_signal
        signal_blocked_by = []

6）返回结果时，带上 I 的完整元数据：

    "modulators_B": {
        "L": L,
        "S": S,
        "F": F,
        "I": I_score
    },

    "execution": {
        "position_size": ...,
        "stop_loss": ...,
        "Teff": ...,
        "p_min": ...,
        "confidence": base_confidence + i_mod["confidence_boost"],
        "cost": base_cost * i_mod["cost_multiplier"]
    },

    "metadata": {
        "I": {
            **i_meta,                      # beta_btc, r2, n_points, status, I_raw等
            "veto": i_mod["veto"],
            "veto_reasons": signal_blocked_by,
            "effective_threshold": effective_threshold
        },
        ...
    }

-----------------------------
3.7 监控与调参建议（可作为 P2 实施）
-----------------------------

1）I veto 统计：
- 统计总信号数；
- 统计被 I veto 的信号数量和占比；
- 按 veto_reason 统计（如“beta_coin_against_btc_trend”“beta_coin_weak_signal”等）。

2）按照 I 区间评估策略表现：
- 将 I 分为三档： [0,30)、[30,70)、[70,100]；
- 分别统计三档的 PnL / EV / 胜率；
- 验证：
  - 低 I 区间（高 Beta）的逆势交易是否显著拖累收益（应被 veto 掉）；
  - 高 I 区间放宽阈值后，是否有明显 Alpha 增厚。

==================================================
四、总结（Claude Code 实施重点）
==================================================

1）score_independence 重写为 BTC-only 版本：
- 输入使用 alt_prices / btc_prices；
- 内部用 log-return + OLS 计算 β_BTC / R²；
- 输出 I_score ∈[0,100] + 元数据（beta_btc, r2, n_points...）。

2）ModulatorChain：
- 新增 apply_I_gate，用 I + T_BTC + T_alt + composite_score 做硬 veto；
- 对高独立币放宽 effective_threshold；
- 将 veto / threshold 与 confidence_boost / cost_multiplier 解耦。

3）analyze_symbol：
- 使用 effective_threshold 替换固定阈值；
- 统一在最终信号生成前检查 i_mod["veto"]；
- 返回值中写清楚 I 的元数据和 veto 原因，方便后续回溯和调参。

请按以上说明重构 I 因子相关模块，并保证：
- 对现有调用方式向后兼容（如 market_context 为 None 时允许降级到简化逻辑）；
- 但在重构路径中，优先遵守“BTC-only β + I 作为风控闸门”的新定义。