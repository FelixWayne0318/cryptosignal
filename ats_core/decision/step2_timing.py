"""
v7.4 Step2: 时机判断层 - Timing Judgment Layer (Enhanced F v2)

Purpose:
    基于资金流动量vs价格动量，判断入场时机质量

Key Correction (vs Enhanced F v1.0):
    v1.0错误: 使用A层总分（包含T/M 33%价格）→ 价格vs价格自相关
    v2.0正确: 只使用Flow因子（C/O/V/B）→ 资金流vs价格，正交信息

Enhanced F v2 Formula:
    flow_score = C×0.40 + O×0.30 + V×0.20 + B×0.10  (仅非价格因子)
    flow_momentum = (flow_score_now - flow_score_6h_ago) / base × 100
    price_momentum = (close_now - close_6h_ago) / close_6h_ago × 100 / 6
    Enhanced_F = flow_momentum - price_momentum
    Enhanced_F_normalized = 100 * tanh(Enhanced_F / scale)

Timing Quality Levels:
    Enhanced_F >= 80  → "Excellent" (强吸筹)
    Enhanced_F >= 60  → "Good" (中等吸筹)
    Enhanced_F >= 30  → "Fair" (轻度吸筹)
    Enhanced_F >= -30 → "Mediocre" (中性)
    Enhanced_F >= -60 → "Poor" (追涨)
    Enhanced_F < -60  → "Chase" (严重追涨)

Author: Claude Code (based on Expert Plan)
Version: v7.4.4
Created: 2025-11-16
Updated: 2025-11-20

v7.4.4 Enhancements:
    - TrendStage module: move_atr, pos_in_range, delta_T
    - Chase zone hard rejection rule
    - Parameterized delta_T thresholds for blowoff detection
"""

from typing import Dict, Any, List, Optional
import math
from ats_core.logging import log, warn


# ============ TrendStage Module (v7.4.4) ============

# TODO: calculate_simple_atr与Step3中的实现重复，未来可合并为公共工具函数
# (如 ats_core/utils/volatility.py)，以避免长期漂移
def calculate_simple_atr(klines: List[Dict], period: int = 14) -> float:
    """
    计算简单ATR (Average True Range)

    Args:
        klines: K线数据（至少period+1根）
        period: ATR周期

    Returns:
        atr: 平均真实波动幅度
    """
    if len(klines) < period + 1:
        return 0.0

    trs = []
    for i in range(-period, 0):
        high = float(klines[i].get("high", 0))
        low = float(klines[i].get("low", 0))
        prev_close = float(klines[i-1].get("close", 0))

        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )
        trs.append(tr)

    return sum(trs) / len(trs) if trs else 0.0


def calculate_move_atr(
    klines: List[Dict],
    window_hours: int,
    atr: float
) -> float:
    """
    计算累积ATR距离（趋势走了多远）

    Formula:
        move = abs(close_now - close_N_ago)
        move_atr = move / atr

    Args:
        klines: K线数据
        window_hours: 回看窗口
        atr: ATR值

    Returns:
        move_atr: 累积ATR距离

    Interpretation:
        1-2: 早期
        2-4: 中段
        4-6: 尾声
        >6: 透支
    """
    if len(klines) < window_hours + 1 or atr <= 0:
        return 0.0

    close_now = float(klines[-1].get("close", 0))
    close_ago = float(klines[-(window_hours+1)].get("close", 0))
    move = abs(close_now - close_ago)

    return move / atr


def calculate_pos_in_range(
    klines: List[Dict],
    window_hours: int
) -> float:
    """
    计算区间位置（当前价格在近期高低区间的位置）

    Formula:
        pos = (close_now - lowest) / (highest - lowest)

    Args:
        klines: K线数据
        window_hours: 回看窗口

    Returns:
        pos_in_range: [0, 1]，1=顶部，0=底部
    """
    if len(klines) < window_hours:
        return 0.5  # 默认中间

    closes = [float(k.get("close", 0)) for k in klines[-window_hours:]]
    highest = max(closes) if closes else 0
    lowest = min(closes) if closes else 0
    close_now = closes[-1] if closes else 0

    range_size = highest - lowest
    if range_size <= 0:
        return 0.5

    return (close_now - lowest) / range_size


def calculate_delta_T(
    factor_scores_series: List[Dict],
    lookback: int
) -> float:
    """
    计算趋势加速度（T因子变化，类似二阶导）

    Formula:
        delta_T = T_now - T_k_ago

    Args:
        factor_scores_series: 因子历史序列
        lookback: 回看K线数

    Returns:
        delta_T: 趋势变化量
        - 多头时delta_T > 0: 趋势加速
        - 多头时delta_T < 0: 趋势减速（见顶前钝化）
    """
    if len(factor_scores_series) < lookback + 1:
        return 0.0

    T_now = factor_scores_series[-1].get("T", 0.0)
    T_ago = factor_scores_series[-(lookback+1)].get("T", 0.0)

    return T_now - T_ago


def determine_trend_stage(
    move_atr: float,
    pos_in_range: float,
    delta_T: float,
    direction_sign: int,
    params: Dict
) -> str:
    """
    判断趋势阶段

    Args:
        move_atr: 累积ATR距离
        pos_in_range: 区间位置
        delta_T: 趋势加速度
        direction_sign: 方向符号（+1多头, -1空头）
        params: 配置

    Returns:
        stage: "early" | "mid" | "late" | "blowoff"
    """
    cfg = params.get("four_step_system", {}).get("step2_timing", {}).get("trend_stage", {})

    thresholds = cfg.get("move_atr_thresholds", {
        "early": 2.0, "mid": 4.0, "late": 6.0
    })
    pos_thresholds = cfg.get("pos_thresholds", {
        "low": 0.15, "high": 0.85
    })

    # v7.4.4: 参数化blowoff阈值（原硬编码-5/5）
    delta_T_thresholds = cfg.get("delta_T_thresholds", {
        "blowoff_long": -5.0, "blowoff_short": 5.0
    })

    early_th = thresholds.get("early", 2.0)
    mid_th = thresholds.get("mid", 4.0)
    late_th = thresholds.get("late", 6.0)
    pos_high = pos_thresholds.get("high", 0.85)
    pos_low = pos_thresholds.get("low", 0.15)
    blowoff_long_th = delta_T_thresholds.get("blowoff_long", -5.0)
    blowoff_short_th = delta_T_thresholds.get("blowoff_short", 5.0)

    # 多头方向
    if direction_sign > 0:
        # Blowoff: 极端透支
        if move_atr > late_th and pos_in_range > 0.9 and delta_T < blowoff_long_th:
            return "blowoff"

        # Late: 尾声
        if move_atr > mid_th and pos_in_range > pos_high and delta_T < 0:
            return "late"

        # Early: 早期
        if move_atr <= early_th and delta_T >= 0:
            return "early"

        # 中段（默认）
        return "mid"

    # 空头方向（对称）
    else:
        # Blowoff: 极端透支
        if move_atr > late_th and pos_in_range < 0.1 and delta_T > blowoff_short_th:
            return "blowoff"

        # Late: 尾声
        if move_atr > mid_th and pos_in_range < pos_low and delta_T > 0:
            return "late"

        # Early: 早期
        if move_atr <= early_th and delta_T <= 0:
            return "early"

        # 中段（默认）
        return "mid"


def calculate_trend_stage_adjustment(
    klines: List[Dict],
    factor_scores_series: List[Dict],
    direction_sign: int,
    params: Dict
) -> Dict[str, Any]:
    """
    计算趋势阶段及其调整值

    Args:
        klines: K线数据
        factor_scores_series: 因子历史序列
        direction_sign: 方向符号（+1多头, -1空头）
        params: 配置

    Returns:
        dict: {
            "trend_stage": str,
            "trend_stage_adjustment": float,
            "move_atr": float,
            "pos_in_range": float,
            "delta_T": float,
            "atr": float
        }
    """
    cfg = params.get("four_step_system", {}).get("step2_timing", {}).get("trend_stage", {})

    # 检查是否启用
    if not cfg.get("enabled", True):
        return {
            "trend_stage": "unknown",
            "trend_stage_adjustment": 0.0,
            "move_atr": 0.0,
            "pos_in_range": 0.5,
            "delta_T": 0.0,
            "atr": 0.0
        }

    # 获取配置
    atr_lookback = cfg.get("atr_lookback", 14)
    move_atr_window = cfg.get("move_atr_window_hours", 6)
    pos_window = cfg.get("pos_window_hours", 24)
    delta_T_lookback = cfg.get("delta_T_lookback", 3)
    penalty_by_stage = cfg.get("penalty_by_stage", {
        "early": 5.0, "mid": 0.0, "late": -15.0, "blowoff": -35.0
    })

    # 计算中间量
    atr = calculate_simple_atr(klines, atr_lookback)
    move_atr = calculate_move_atr(klines, move_atr_window, atr)
    pos_in_range = calculate_pos_in_range(klines, pos_window)
    delta_T = calculate_delta_T(factor_scores_series, delta_T_lookback)

    # 判断阶段
    trend_stage = determine_trend_stage(
        move_atr, pos_in_range, delta_T, direction_sign, params
    )

    # 获取调整值
    adjustment = penalty_by_stage.get(trend_stage, 0.0)

    return {
        "trend_stage": trend_stage,
        "trend_stage_adjustment": adjustment,
        "move_atr": round(move_atr, 2),
        "pos_in_range": round(pos_in_range, 3),
        "delta_T": round(delta_T, 2),
        "atr": round(atr, 6)
    }


# ============ Original Enhanced F Functions ============


def calculate_flow_score(
    factor_scores: Dict[str, float],
    weights: Dict[str, float]
) -> float:
    """
    计算Flow得分（仅非价格因子）

    Key: 只使用C/O/V/B，不使用T/M（避免价格自相关）

    Args:
        factor_scores: 因子得分 {"C": float, "O": float, "V": float, "B": float}
        weights: Flow权重 {"C": 0.40, "O": 0.30, "V": 0.20, "B": 0.10}

    Returns:
        flow_score: Flow加权得分（-100到+100）
    """
    C = factor_scores.get("C", 0.0)
    O = factor_scores.get("O", 0.0)
    V = factor_scores.get("V", 0.0)
    B = factor_scores.get("B", 0.0)

    w_C = weights.get("C", 0.40)
    w_O = weights.get("O", 0.30)
    w_V = weights.get("V", 0.20)
    w_B = weights.get("B", 0.10)

    flow_score = C * w_C + O * w_O + V * w_V + B * w_B

    return flow_score


def calculate_flow_momentum(
    factor_scores_series: List[Dict[str, float]],
    weights: Dict[str, float],
    lookback_hours: int = 6,
    flow_weak_threshold: float = 1.0,
    base_min_value: float = 10.0
) -> float:
    """
    计算Flow动量（6小时变化百分比）

    Formula:
        flow_now = flow_series[-1]
        flow_6h_ago = flow_series[0]
        flow_change = flow_now - flow_6h_ago
        base = max(abs(flow_now), abs(flow_6h_ago), base_min_value)
        flow_momentum = (flow_change / base) * 100

    Args:
        factor_scores_series: 历史因子得分序列（7个时间点）
        weights: Flow权重
        lookback_hours: 回溯小时数（默认6）
        flow_weak_threshold: Flow弱阈值（v7.4.2配置化，默认1.0）
        base_min_value: base最小值（v7.4.2配置化，默认10.0）

    Returns:
        flow_momentum: Flow动量百分比
    """
    if len(factor_scores_series) < lookback_hours + 1:
        warn(f"⚠️  因子历史不足: 需要{lookback_hours+1}个点，实际{len(factor_scores_series)}个")
        return 0.0

    # 计算每个时间点的flow_score
    flow_series = [
        calculate_flow_score(scores, weights)
        for scores in factor_scores_series
    ]

    flow_now = flow_series[-1]
    flow_6h_ago = flow_series[0]

    # v7.4.2配置化：flow值都很弱（接近0）时认为无动量
    if abs(flow_now) < flow_weak_threshold and abs(flow_6h_ago) < flow_weak_threshold:
        return 0.0

    # v7.4.2配置化：计算变化百分比，使用配置的base_min_value避免除0
    flow_change = flow_now - flow_6h_ago
    base = max(abs(flow_now), abs(flow_6h_ago), base_min_value)
    flow_momentum = (flow_change / base) * 100.0

    return flow_momentum


def calculate_price_momentum(
    klines: List[Dict[str, Any]],
    lookback_hours: int = 6
) -> float:
    """
    计算价格动量（6小时涨跌幅，每小时百分比）

    Formula:
        close_now = klines[-1].close
        close_6h_ago = klines[-7].close
        price_change_pct = (close_now - close_6h_ago) / close_6h_ago * 100
        price_momentum = price_change_pct / 6.0  # 每小时百分比

    Args:
        klines: 1小时K线数据（至少7根）
        lookback_hours: 回溯小时数（默认6）

    Returns:
        price_momentum: 价格每小时动量百分比
    """
    if len(klines) < lookback_hours + 1:
        warn(f"⚠️  K线不足: 需要{lookback_hours+1}根，实际{len(klines)}根")
        return 0.0

    close_now = klines[-1].get("close", 0.0)
    close_6h_ago = klines[-(lookback_hours+1)].get("close", 0.0)

    if close_6h_ago <= 0:
        warn("⚠️  价格历史异常: close_6h_ago <= 0")
        return 0.0

    price_change_pct = (close_now - close_6h_ago) / close_6h_ago * 100.0
    price_momentum = price_change_pct / lookback_hours

    return price_momentum


def calculate_enhanced_f_v2(
    factor_scores_series: List[Dict[str, float]],
    klines: List[Dict[str, Any]],
    params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    计算Enhanced F v2（修正版：避免价格自相关）

    Key Correction:
        v1.0: signal_momentum用A层总分（含T/M 33%价格）
        v2.0: flow_momentum只用C/O/V/B（纯资金流）

    Formula:
        Enhanced_F_raw = flow_momentum - price_momentum
        Enhanced_F = 100 * tanh(Enhanced_F_raw / scale)

    Args:
        factor_scores_series: 历史因子得分序列
        klines: 1小时K线数据
        params: 配置参数

    Returns:
        dict: {
            "enhanced_f": float,           # -100到+100
            "flow_momentum": float,        # Flow动量百分比
            "price_momentum": float,       # 价格动量百分比
            "timing_quality": str,         # 时机质量评级
            "flow_weights": dict,          # 使用的权重
            "pass": bool,                  # 是否通过
            "reject_reason": str or None
        }
    """
    # 获取配置
    step2_cfg = params.get("four_step_system", {}).get("step2_timing", {})
    enhanced_f_cfg = step2_cfg.get("enhanced_f", {})

    scale = enhanced_f_cfg.get("scale", 20.0)
    min_threshold = enhanced_f_cfg.get("min_threshold", 30.0)
    flow_weights = enhanced_f_cfg.get("flow_weights", {
        "C": 0.40, "O": 0.30, "V": 0.20, "B": 0.10
    })
    lookback_hours = enhanced_f_cfg.get("lookback_hours", 6)

    # v7.4.2新增：Flow动量计算参数（消除硬编码）
    flow_weak_threshold = enhanced_f_cfg.get("flow_weak_threshold", 1.0)
    base_min_value = enhanced_f_cfg.get("base_min_value", 10.0)

    # 数据验证
    if len(factor_scores_series) < lookback_hours + 1:
        return {
            "enhanced_f": 0.0,
            "flow_momentum": 0.0,
            "price_momentum": 0.0,
            "timing_quality": "Unknown",
            "flow_weights": flow_weights,
            "pass": False,
            "reject_reason": f"因子历史不足: 需要{lookback_hours+1}个点，实际{len(factor_scores_series)}个"
        }

    if len(klines) < lookback_hours + 1:
        return {
            "enhanced_f": 0.0,
            "flow_momentum": 0.0,
            "price_momentum": 0.0,
            "timing_quality": "Unknown",
            "flow_weights": flow_weights,
            "pass": False,
            "reject_reason": f"K线不足: 需要{lookback_hours+1}根，实际{len(klines)}根"
        }

    # 计算Flow动量（v7.4.2: 传入配置参数，消除硬编码）
    flow_momentum = calculate_flow_momentum(
        factor_scores_series,
        flow_weights,
        lookback_hours,
        flow_weak_threshold,
        base_min_value
    )

    # 计算价格动量
    price_momentum = calculate_price_momentum(
        klines,
        lookback_hours
    )

    # 计算Enhanced F v2
    enhanced_f_raw = flow_momentum - price_momentum
    enhanced_f = 100.0 * math.tanh(enhanced_f_raw / scale)

    # 时机质量评级
    timing_quality_cfg = step2_cfg.get("timing_quality", {})
    excellent = timing_quality_cfg.get("excellent", 80)
    good = timing_quality_cfg.get("good", 60)
    fair = timing_quality_cfg.get("fair", 30)
    mediocre = timing_quality_cfg.get("mediocre", -30)
    poor = timing_quality_cfg.get("poor", -60)

    if enhanced_f >= excellent:
        timing_quality = "Excellent"
    elif enhanced_f >= good:
        timing_quality = "Good"
    elif enhanced_f >= fair:
        timing_quality = "Fair"
    elif enhanced_f >= mediocre:
        timing_quality = "Mediocre"
    elif enhanced_f >= poor:
        timing_quality = "Poor"
    else:
        timing_quality = "Chase"

    # 判断是否通过
    pass_step2 = enhanced_f >= min_threshold

    reject_reason = None
    if not pass_step2:
        reject_reason = f"时机不佳: Enhanced_F={enhanced_f:.1f} < {min_threshold}"

    return {
        "enhanced_f": enhanced_f,
        "flow_momentum": flow_momentum,
        "price_momentum": price_momentum,
        "timing_quality": timing_quality,
        "flow_weights": flow_weights,
        "pass": pass_step2,
        "reject_reason": reject_reason
    }


def step2_timing_judgment(
    factor_scores_series: List[Dict[str, float]],
    klines: List[Dict[str, Any]],
    s_factor_meta: Dict[str, Any],
    params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Step2主函数：时机判断层（v7.4.4增强版）

    Pipeline:
        1. 计算Enhanced F v2（flow vs price momentum）
        2. 计算TrendStage调整（防追高/追跌）
        3. 基于S因子调整时机评分
        4. 合成最终得分并判断

    v7.4.4 Enhancements:
        - TrendStage模块（move_atr, pos_in_range, delta_T）
        - Chase zone硬拒绝规则
        - enhanced_f_final = enhanced_f_flow_price + trend_stage_adjustment + s_adjustment

    Note (v7.4.3):
        L因子不再在Step2中使用。根据设计文档，L因子仅用于Step3风险管理层
        调整止损宽度（流动性差→更宽止损），而非时机评分惩罚。

    Args:
        factor_scores_series: 历史因子得分序列（7个时间点）
        klines: 1小时K线数据
        s_factor_meta: S因子元数据（包含theta、timing等）
        params: 配置参数

    Returns:
        dict: {
            "pass": bool,
            "enhanced_f": float,              # 原始Enhanced F (flow_price)
            "enhanced_f_final": float,        # 最终得分
            "flow_momentum": float,
            "price_momentum": float,
            "trend_stage": str,
            "trend_stage_adjustment": float,
            "s_adjustment": float,
            "timing_quality": str,
            "is_chase_zone": bool,
            "reject_reason": str or None,
            "metadata": dict
        }
    """
    # 1. 计算Enhanced F v2
    enhanced_f_result = calculate_enhanced_f_v2(
        factor_scores_series,
        klines,
        params
    )

    step2_cfg = params.get("four_step_system", {}).get("step2_timing", {})
    enhanced_f_flow_price = enhanced_f_result["enhanced_f"]

    # 2. 计算TrendStage调整
    # 从当前因子确定方向符号
    current_factors = factor_scores_series[-1] if factor_scores_series else {}
    T_now = current_factors.get("T", 0.0)
    direction_sign = 1 if T_now >= 0 else -1

    trend_stage_result = calculate_trend_stage_adjustment(
        klines, factor_scores_series, direction_sign, params
    )

    # 3. S因子调整
    s_cfg = step2_cfg.get("S_factor", {})
    s_adjustment = 0.0
    theta = s_factor_meta.get("theta", 0.0)
    theta_threshold = s_cfg.get("theta_threshold", 0.65)
    timing_boost = s_cfg.get("timing_boost", 10)

    if theta >= theta_threshold:
        s_adjustment = timing_boost
        log(f"✅ S因子结构良好(theta={theta:.2f}), 时机+{timing_boost}")

    # 4. 合成最终得分
    # v7.4.4: enhanced_f_final = enhanced_f_flow_price + trend_stage_adjustment + s_adjustment
    enhanced_f_final = (
        enhanced_f_flow_price
        + trend_stage_result["trend_stage_adjustment"]
        + s_adjustment
    )

    # 5. 判定是否通过
    trend_stage_cfg = step2_cfg.get("trend_stage", {})
    chase_reject_threshold = trend_stage_cfg.get("chase_reject_threshold", -60.0)
    min_threshold = step2_cfg.get("enhanced_f", {}).get("min_threshold", -30.0)

    # Chase zone检测
    is_chase_zone = enhanced_f_final <= chase_reject_threshold

    if is_chase_zone:
        pass_step2 = False
        reject_reason = (
            f"Chase zone: enhanced_f_final={enhanced_f_final:.1f} <= {chase_reject_threshold}, "
            f"stage={trend_stage_result['trend_stage']}, "
            f"move_atr={trend_stage_result['move_atr']:.1f}, "
            f"pos={trend_stage_result['pos_in_range']:.2f}, "
            f"delta_T={trend_stage_result['delta_T']:.1f}"
        )
    elif enhanced_f_final >= min_threshold:
        pass_step2 = True
        reject_reason = None
    else:
        pass_step2 = False
        reject_reason = (
            f"Timing not attractive: enhanced_f_final={enhanced_f_final:.1f} < {min_threshold} "
            f"(flow_price={enhanced_f_flow_price:.1f}, "
            f"stage_adj={trend_stage_result['trend_stage_adjustment']:+.0f}, "
            f"S_adj={s_adjustment:+.0f})"
        )

    # 6. 基于enhanced_f_final重新评级timing_quality
    timing_quality_cfg = step2_cfg.get("timing_quality", {})
    if enhanced_f_final >= timing_quality_cfg.get("excellent", 80):
        timing_quality = "Excellent"
    elif enhanced_f_final >= timing_quality_cfg.get("good", 60):
        timing_quality = "Good"
    elif enhanced_f_final >= timing_quality_cfg.get("fair", 30):
        timing_quality = "Fair"
    elif enhanced_f_final >= timing_quality_cfg.get("mediocre", -30):
        timing_quality = "Mediocre"
    elif enhanced_f_final >= timing_quality_cfg.get("poor", -60):
        timing_quality = "Poor"
    else:
        timing_quality = "Chase"

    return {
        "pass": pass_step2,
        "enhanced_f": enhanced_f_flow_price,
        "enhanced_f_final": enhanced_f_final,
        "flow_momentum": enhanced_f_result["flow_momentum"],
        "price_momentum": enhanced_f_result["price_momentum"],
        "trend_stage": trend_stage_result["trend_stage"],
        "trend_stage_adjustment": trend_stage_result["trend_stage_adjustment"],
        "s_adjustment": s_adjustment,
        "timing_quality": timing_quality,
        "is_chase_zone": is_chase_zone,
        "reject_reason": reject_reason,
        "metadata": {
            "flow_weights": enhanced_f_result["flow_weights"],
            "s_theta": theta,
            "move_atr": trend_stage_result["move_atr"],
            "pos_in_range": trend_stage_result["pos_in_range"],
            "delta_T": trend_stage_result["delta_T"],
            "atr": trend_stage_result.get("atr", 0.0),
            "direction_sign": direction_sign,
            "min_threshold": min_threshold,
            "chase_reject_threshold": chase_reject_threshold
        }
    }


# ============ 测试用例 ============

if __name__ == "__main__":
    """
    测试Step2时机判断层

    Usage:
        python3 -m ats_core.decision.step2_timing
    """
    print("="*70)
    print("v7.4 Step2: 时机判断层测试（Enhanced F v2）")
    print("="*70)

    # 模拟配置
    test_params = {
        "four_step_system": {
            "step2_timing": {
                "enhanced_f": {
                    "scale": 20.0,
                    "min_threshold": 30.0,
                    "flow_weights": {
                        "C": 0.40,
                        "O": 0.30,
                        "V": 0.20,
                        "B": 0.10
                    },
                    "lookback_hours": 6
                },
                "timing_quality": {
                    "excellent": 80,
                    "good": 60,
                    "fair": 30,
                    "mediocre": -30,
                    "poor": -60
                },
                "S_factor": {
                    "theta_threshold": 0.65,
                    "timing_boost": 10
                }
            }
        }
    }

    # 模拟历史因子得分（强吸筹场景）
    factor_series_strong = [
        {"C": 60, "O": 55, "V": 50, "B": 45},  # 6h前
        {"C": 65, "O": 60, "V": 55, "B": 50},
        {"C": 70, "O": 65, "V": 60, "B": 55},
        {"C": 75, "O": 70, "V": 65, "B": 60},
        {"C": 80, "O": 75, "V": 70, "B": 65},
        {"C": 85, "O": 80, "V": 75, "B": 70},
        {"C": 90, "O": 85, "V": 80, "B": 75},  # 当前
    ]

    # 模拟K线（价格平稳）
    klines_flat = [
        {"close": 100 + i * 0.1} for i in range(7)
    ]

    # 测试用例1：强吸筹（Flow上升，价格平稳）
    print("\n📊 测试用例1：强吸筹场景（Flow↑，Price→）")
    result1 = step2_timing_judgment(
        factor_scores_series=factor_series_strong,
        klines=klines_flat,
        s_factor_meta={"theta": 0.70, "timing": 0.8},
        params=test_params
    )
    print(f"   通过: {result1['pass']}")
    print(f"   Enhanced F: {result1['enhanced_f']:.1f}")
    print(f"   Flow动量: {result1['flow_momentum']:.1f}%")
    print(f"   Price动量: {result1['price_momentum']:.1f}%")
    print(f"   时机质量: {result1['timing_quality']}")
    print(f"   最终得分: {result1['final_timing_score']:.1f}")

    # 模拟历史因子得分（追涨场景）
    factor_series_chase = [
        {"C": 40, "O": 35, "V": 30, "B": 25},  # 6h前
        {"C": 38, "O": 33, "V": 28, "B": 23},
        {"C": 36, "O": 31, "V": 26, "B": 21},
        {"C": 34, "O": 29, "V": 24, "B": 19},
        {"C": 32, "O": 27, "V": 22, "B": 17},
        {"C": 30, "O": 25, "V": 20, "B": 15},
        {"C": 28, "O": 23, "V": 18, "B": 13},  # 当前
    ]

    # 模拟K线（价格大幅上涨）
    klines_rally = [
        {"close": 100 * (1 + i * 0.03)} for i in range(7)
    ]

    # 测试用例2：追涨（Flow下降，价格上涨）
    print("\n🚫 测试用例2：追涨场景（Flow↓，Price↑）")
    result2 = step2_timing_judgment(
        factor_scores_series=factor_series_chase,
        klines=klines_rally,
        s_factor_meta={"theta": 0.40, "timing": 0.3},
        params=test_params
    )
    print(f"   通过: {result2['pass']}")
    print(f"   Enhanced F: {result2['enhanced_f']:.1f}")
    print(f"   Flow动量: {result2['flow_momentum']:.1f}%")
    print(f"   Price动量: {result2['price_momentum']:.1f}%")
    print(f"   时机质量: {result2['timing_quality']}")
    print(f"   拒绝原因: {result2['reject_reason']}")

    print("\n" + "="*70)
    print("✅ Step2测试完成")
    print("="*70)
