"""
v7.4 四步分层决策系统 - Step3: 风险管理层

Purpose:
    计算具体的Entry/Stop-Loss/Take-Profit价格，实现精确风险管理

Functions:
    - extract_support_resistance(): 从S因子ZigZag点提取支撑/阻力位
    - extract_orderbook_from_L_meta(): 从L因子元数据提取订单簿信息
    - calculate_simple_atr(): 简易ATR计算（如果K线缺少atr字段）
    - calculate_entry_price(): 入场价计算（基于Enhanced F和结构）
    - calculate_stop_loss(): 止损价计算（支持两种模式）
    - calculate_take_profit(): 止盈价计算（确保RR ≥ min_risk_reward_ratio）
    - step3_risk_management(): 主函数

Key Features:
    - 支撑/阻力位识别（ZigZag points）
    - 动态ATR波动率计算
    - L因子流动性调节止损宽度
    - 订单簿墙识别（初版占位，后续启用）
    - 两种止损模式：tight / structure_above_or_below
    - 赔率约束（min RR = 1.5）

Author: Claude Code (based on Expert Implementation Plan)
Version: v7.4.0
Created: 2025-11-16
"""

from typing import Dict, Any, List, Optional
from ats_core.logging import log, warn


def extract_support_resistance(s_factor_meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    从S因子元数据中提取支撑位/阻力位

    Args:
        s_factor_meta: S因子元数据，包含zigzag_points列表
            zigzag_points格式: [
                {"type": "L", "price": 98.5, "dt": 5},  # L=低点(支撑)
                {"type": "H", "price": 103.2, "dt": 4}, # H=高点(阻力)
                ...
            ]

    Returns:
        dict: {
            "support": float | None,        # 最近支撑位
            "resistance": float | None,     # 最近阻力位
            "support_strength": int,        # 支撑强度（近3个点中L点数量）
            "resistance_strength": int      # 阻力强度（近3个点中H点数量）
        }
    """
    points = (s_factor_meta or {}).get("zigzag_points", [])

    if not points:
        return {
            "support": None,
            "resistance": None,
            "support_strength": 0,
            "resistance_strength": 0
        }

    # 提取所有低点（支撑）和高点（阻力）
    lows = [p["price"] for p in points if p.get("type") == "L"]
    highs = [p["price"] for p in points if p.get("type") == "H"]

    # 取最近的支撑/阻力
    support = lows[-1] if lows else None
    resistance = highs[-1] if highs else None

    # 计算支撑/阻力强度（最近3个点中L/H的数量）
    recent = points[-3:] if len(points) >= 3 else points
    support_strength = sum(1 for p in recent if p.get("type") == "L")
    resistance_strength = sum(1 for p in recent if p.get("type") == "H")

    return {
        "support": support,
        "resistance": resistance,
        "support_strength": support_strength,
        "resistance_strength": resistance_strength
    }


def extract_orderbook_from_L_meta(
    l_factor_meta: Optional[Dict[str, Any]],
    params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    从L因子元数据中提取订单簿信息（v7.4.0完整版 - 利用价格带法全部分析结果）

    Args:
        l_factor_meta: L因子元数据，包含价格带法的完整分析结果
            - buy_impact_bps/sell_impact_bps: 价格冲击
            - spread_bps: 买卖价差
            - obi_value: 订单簿失衡度
            - buy_covered/sell_covered: 深度覆盖度
            - gates_passed/gates_status: 四道闸通过情况
            - liquidity_level: 流动性等级
        params: 配置参数

    Returns:
        dict: {
            "buy_wall_price": float | None,   # 买墙价格
            "sell_wall_price": float | None,  # 卖墙价格
            "buy_depth_score": float,         # 买盘深度得分（综合OBI+覆盖+冲击）
            "sell_depth_score": float,        # 卖盘深度得分（综合OBI+覆盖+冲击）
            "imbalance": float,               # OBI失衡度
            "buy_impact_bps": float,          # 买入价格冲击
            "sell_impact_bps": float,         # 卖出价格冲击
            "spread_bps": float,              # 买卖价差
            "liquidity_level": str,           # 流动性等级
            "gates_passed": int               # 通过的闸门数量
        }

    Note:
        v7.4.0完整版：充分利用L因子价格带法的全部分析结果
        深度得分 = OBI基础分(50%) + 覆盖度(25%) + 冲击成本(25%)
    """
    orderbook_cfg = params.get("four_step_system", {}).get("step3_risk", {}).get("orderbook", {})
    enabled = orderbook_cfg.get("enabled", True)

    if not enabled or not l_factor_meta:
        # 降级处理：返回中性值
        return {
            "buy_wall_price": None,
            "sell_wall_price": None,
            "buy_depth_score": 50.0,
            "sell_depth_score": 50.0,
            "imbalance": 0.0,
            "buy_impact_bps": 0.0,
            "sell_impact_bps": 0.0,
            "spread_bps": 0.0,
            "liquidity_level": "unknown",
            "gates_passed": 0
        }

    # ====================
    # 1. 从L因子元数据提取完整信息
    # ====================
    # 基础价格
    best_bid = l_factor_meta.get("best_bid")
    best_ask = l_factor_meta.get("best_ask")

    # OBI失衡度
    obi_value = l_factor_meta.get("obi_value", 0.0)

    # 价格冲击（关键！）
    buy_impact_bps = l_factor_meta.get("buy_impact_bps", 0.0)
    sell_impact_bps = l_factor_meta.get("sell_impact_bps", 0.0)

    # 价差
    spread_bps = l_factor_meta.get("spread_bps", 0.0)

    # 深度覆盖度
    buy_covered = l_factor_meta.get("buy_covered", False)
    sell_covered = l_factor_meta.get("sell_covered", False)

    # 四道闸通过情况
    gates_passed = l_factor_meta.get("gates_passed", 0)

    # 流动性等级
    liquidity_level = l_factor_meta.get("liquidity_level", "unknown")

    # ====================
    # 2. 买墙/卖墙检测（增强版：需要OBI显著 + 深度覆盖）
    # ====================
    buy_wall_threshold = orderbook_cfg.get("obi_buy_wall_threshold", 0.3)
    sell_wall_threshold = orderbook_cfg.get("obi_sell_wall_threshold", -0.3)

    # 买墙：OBI显著为正 且 买盘深度覆盖良好
    buy_wall_price = best_bid if (obi_value > buy_wall_threshold and buy_covered) else None
    # 卖墙：OBI显著为负 且 卖盘深度覆盖良好
    sell_wall_price = best_ask if (obi_value < sell_wall_threshold and sell_covered) else None

    # ====================
    # 3. 深度得分（综合版：OBI基础分50% + 覆盖度25% + 冲击成本25%）
    # ====================
    # 3.1 OBI基础分 ∈ [0, 100]
    obi_buy_base = max(0.0, min(100.0, 50.0 + obi_value * 50.0))
    obi_sell_base = max(0.0, min(100.0, 50.0 - obi_value * 50.0))

    # 3.2 覆盖度分 ∈ [0, 100]
    coverage_buy_score = 100.0 if buy_covered else 0.0
    coverage_sell_score = 100.0 if sell_covered else 0.0

    # 3.3 冲击成本分 ∈ [0, 100] (冲击越小越好)
    # 冲击阈值: 10 bps为优秀, 50 bps为可接受, >50 bps为差
    # 分数 = max(0, 100 - impact_bps * 2)
    impact_buy_score = max(0.0, min(100.0, 100.0 - buy_impact_bps * 2.0))
    impact_sell_score = max(0.0, min(100.0, 100.0 - sell_impact_bps * 2.0))

    # 3.4 综合深度得分（加权平均）
    buy_depth_score = (
        obi_buy_base * 0.50 +        # OBI基础分占50%
        coverage_buy_score * 0.25 +  # 覆盖度占25%
        impact_buy_score * 0.25      # 冲击成本占25%
    )

    sell_depth_score = (
        obi_sell_base * 0.50 +       # OBI基础分占50%
        coverage_sell_score * 0.25 + # 覆盖度占25%
        impact_sell_score * 0.25     # 冲击成本占25%
    )

    # ====================
    # 4. 返回完整分析结果
    # ====================
    return {
        # 墙价格
        "buy_wall_price": buy_wall_price,
        "sell_wall_price": sell_wall_price,

        # 深度得分（综合）
        "buy_depth_score": buy_depth_score,
        "sell_depth_score": sell_depth_score,

        # OBI失衡度
        "imbalance": obi_value,

        # 价格冲击（新增！）
        "buy_impact_bps": buy_impact_bps,
        "sell_impact_bps": sell_impact_bps,

        # 价差（新增！）
        "spread_bps": spread_bps,

        # 流动性等级（新增！）
        "liquidity_level": liquidity_level,

        # 四道闸通过数（新增！）
        "gates_passed": gates_passed
    }


def calculate_simple_atr(klines: List[Dict[str, Any]], period: int = 14) -> float:
    """
    简易ATR计算（如果K线中没有atr字段）

    Args:
        klines: K线数据列表
        period: ATR周期（默认14）

    Returns:
        float: ATR值（如果数据不足返回0.0）
    """
    if len(klines) < period + 1:
        return 0.0

    trs = []
    for i in range(-period, 0):
        high = float(klines[i]["high"])
        low = float(klines[i]["low"])
        prev_close = float(klines[i - 1]["close"])

        # True Range = max(H-L, |H-Prev_C|, |L-Prev_C|)
        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )
        trs.append(tr)

    return sum(trs) / len(trs) if trs else 0.0


def calculate_entry_price(
    current_price: float,
    support: Optional[float],
    resistance: Optional[float],
    enhanced_f: float,
    direction_score: float,
    orderbook: Dict[str, Any],
    params: Dict[str, Any]
) -> float:
    """
    计算入场价

    Logic:
        做多（LONG）:
            Enhanced_F >= 70 → 强吸筹 → 现价入场
            Enhanced_F >= 40 → 中度吸筹 → 等支撑附近0.2%（有支撑）否则现价下方0.2%
            Enhanced_F < 40  → 弱吸筹 → 等支撑附近0.5%（有支撑）否则现价下方0.5%
            若存在买墙 → entry不低于买墙略上方

        做空（SHORT）: 对称逻辑

    Args:
        current_price: 当前价格
        support: 支撑位
        resistance: 阻力位
        enhanced_f: Enhanced F v2得分 (-100 ~ +100)
        direction_score: 方向得分（正=做多，负=做空）
        orderbook: 订单簿信息
        params: 配置参数

    Returns:
        float: 入场价格
    """
    entry_cfg = params.get("four_step_system", {}).get("step3_risk", {}).get("entry_price", {})

    # 从配置读取阈值和buffer
    strong_f = entry_cfg.get("strong_accumulation_f", 70)
    moderate_f = entry_cfg.get("moderate_accumulation_f", 40)
    buffer_strong = entry_cfg.get("buffer_strong", 1.000)
    buffer_moderate = entry_cfg.get("buffer_moderate", 1.002)
    buffer_weak = entry_cfg.get("buffer_weak", 1.005)

    is_long = direction_score > 0.0
    buy_wall = orderbook.get("buy_wall_price")
    sell_wall = orderbook.get("sell_wall_price")

    # 计算入场价
    if is_long:
        # 做多逻辑
        if enhanced_f >= strong_f:
            # 强吸筹 → 现价入场
            entry = current_price * buffer_strong
        elif enhanced_f >= moderate_f:
            # 中度吸筹
            if support is not None:
                entry = support * buffer_moderate
            else:
                entry = current_price * 0.998
        else:
            # 弱吸筹
            if support is not None:
                entry = support * buffer_weak
            else:
                entry = current_price * 0.995

        # 买墙调整（初版不启用，但预留逻辑）
        wall_adjustment_enabled = params.get("four_step_system", {}).get("step3_risk", {}).get("orderbook", {}).get("wall_adjustment_enabled", False)
        if wall_adjustment_enabled and buy_wall and entry < buy_wall:
            entry = buy_wall * 1.001

    else:
        # 做空逻辑（对称）
        if enhanced_f >= strong_f:
            entry = current_price * buffer_strong
        elif enhanced_f >= moderate_f:
            if resistance is not None:
                entry = resistance * (2.0 - buffer_moderate)  # 0.998
            else:
                entry = current_price * 1.002
        else:
            if resistance is not None:
                entry = resistance * (2.0 - buffer_weak)  # 0.995
            else:
                entry = current_price * 1.005

        # 卖墙调整
        wall_adjustment_enabled = params.get("four_step_system", {}).get("step3_risk", {}).get("orderbook", {}).get("wall_adjustment_enabled", False)
        if wall_adjustment_enabled and sell_wall and entry > sell_wall:
            entry = sell_wall * 0.999

    return entry


def calculate_stop_loss(
    entry_price: float,
    support: Optional[float],
    resistance: Optional[float],
    atr: float,
    direction_score: float,
    l_score: float,
    params: Dict[str, Any]
) -> float:
    """
    计算止损价（支持两种模式）

    Mode 1: tight（紧止损）
        - 结构止损：支撑/阻力 × 0.998
        - ATR止损：entry ± ATR × 倍数
        - 最终：取max(结构, ATR)（多头）或min(结构, ATR)（空头）

    Mode 2: structure_above_or_below（结构上下模式）
        - 结构止损：支撑下方0.6%（多）/ 阻力上方0.6%（空）
        - ATR止损：entry ± ATR × 倍数
        - 最终：取min(结构, ATR)（多头，降低被扫概率）

    ATR倍数调节（基于L因子）:
        L < -30 → 倍数 × 1.5（低流动性，止损放宽）
        L > 30  → 倍数 × 0.8（高流动性，止损收紧）
        其他    → 倍数 × 1.0

    Args:
        entry_price: 入场价
        support: 支撑位
        resistance: 阻力位
        atr: ATR值
        direction_score: 方向得分
        l_score: L因子流动性得分
        params: 配置参数

    Returns:
        float: 止损价格
    """
    sl_cfg = params.get("four_step_system", {}).get("step3_risk", {}).get("stop_loss", {})

    # 读取配置
    mode = sl_cfg.get("mode", "structure_above_or_below")
    base_mult = sl_cfg.get("base_atr_multiplier", 2.0)

    # L因子流动性调节
    liq_adj = sl_cfg.get("liquidity_adjustment", {})
    low_liq_threshold = liq_adj.get("low_liquidity_threshold", -30)
    high_liq_threshold = liq_adj.get("high_liquidity_threshold", 30)
    low_liq_mult = liq_adj.get("low_liquidity_multiplier", 1.5)
    high_liq_mult = liq_adj.get("high_liquidity_multiplier", 0.8)

    if l_score < low_liq_threshold:
        atr_mult = base_mult * low_liq_mult
    elif l_score > high_liq_threshold:
        atr_mult = base_mult * high_liq_mult
    else:
        atr_mult = base_mult

    is_long = direction_score > 0.0

    # 计算止损
    if mode == "tight":
        # 紧止损模式
        tight_cfg = sl_cfg.get("tight_mode", {})
        structure_buffer = tight_cfg.get("structure_buffer", 0.998)
        use_max = tight_cfg.get("use_max_of_structure_and_volatility", True)

        if is_long:
            structure_stop = support * structure_buffer if support is not None else None
            vol_stop = entry_price - atr * atr_mult

            if structure_stop is not None and use_max:
                stop_loss = max(structure_stop, vol_stop)
            else:
                stop_loss = structure_stop if structure_stop is not None else vol_stop
        else:
            structure_stop = resistance * (2.0 - structure_buffer) if resistance is not None else None  # 1.002
            vol_stop = entry_price + atr * atr_mult

            if structure_stop is not None and use_max:
                stop_loss = min(structure_stop, vol_stop)
            else:
                stop_loss = structure_stop if structure_stop is not None else vol_stop

    else:  # structure_above_or_below
        # 结构上下模式（降低被扫概率）
        struct_cfg = sl_cfg.get("structure_above_or_below_mode", {})
        buffer_long = struct_cfg.get("structure_buffer_long", 0.994)
        buffer_short = struct_cfg.get("structure_buffer_short", 1.006)
        use_min = struct_cfg.get("use_min_of_structure_and_volatility", True)

        if is_long:
            structure_stop = support * buffer_long if support is not None else None  # 支撑下方0.6%
            vol_stop = entry_price - atr * atr_mult

            if structure_stop is not None and use_min:
                stop_loss = min(structure_stop, vol_stop)  # 取更远的（降低被扫）
            else:
                stop_loss = structure_stop if structure_stop is not None else vol_stop
        else:
            structure_stop = resistance * buffer_short if resistance is not None else None  # 阻力上方0.6%
            vol_stop = entry_price + atr * atr_mult

            if structure_stop is not None and use_min:
                stop_loss = max(structure_stop, vol_stop)  # 取更远的
            else:
                stop_loss = structure_stop if structure_stop is not None else vol_stop

    return stop_loss


def calculate_take_profit(
    entry_price: float,
    stop_loss: float,
    resistance: Optional[float],
    support: Optional[float],
    direction_score: float,
    params: Dict[str, Any]
) -> float:
    """
    计算止盈价（赔率约束 + 结构对齐）

    Logic:
        1. 计算最小赔率要求：reward = risk × min_risk_reward_ratio (默认1.5)
        2. 若有结构位（阻力/支撑），对齐到结构
        3. 最终：取max(最小赔率, 结构目标)（多头）或min(最小赔率, 结构目标)（空头）

    Args:
        entry_price: 入场价
        stop_loss: 止损价
        resistance: 阻力位
        support: 支撑位
        direction_score: 方向得分
        params: 配置参数

    Returns:
        float: 止盈价格
    """
    tp_cfg = params.get("four_step_system", {}).get("step3_risk", {}).get("take_profit", {})

    min_rr = tp_cfg.get("min_risk_reward_ratio", 1.5)
    structure_buffer = tp_cfg.get("structure_buffer", 0.998)
    use_max = tp_cfg.get("use_max_of_min_and_structure", True)

    is_long = direction_score > 0.0
    risk = abs(entry_price - stop_loss)

    # 防御性处理：避免除0
    if risk <= 0:
        risk = entry_price * 0.005  # 0.5%

    if is_long:
        # 做多：止盈在entry上方
        min_target = entry_price + risk * min_rr

        if resistance is not None:
            structure_target = resistance * structure_buffer  # 阻力下方0.2%
        else:
            structure_target = min_target

        # 取较大值（确保满足最小赔率）
        if use_max:
            take_profit = max(min_target, structure_target)
        else:
            take_profit = structure_target if resistance is not None else min_target

    else:
        # 做空：止盈在entry下方
        min_target = entry_price - risk * min_rr

        if support is not None:
            structure_target = support * (2.0 - structure_buffer)  # 支撑上方0.2%
        else:
            structure_target = min_target

        # 取较小值（确保满足最小赔率）
        if use_max:
            take_profit = min(min_target, structure_target)
        else:
            take_profit = structure_target if support is not None else min_target

    return take_profit


def step3_risk_management(
    symbol: str,
    klines: List[Dict[str, Any]],
    s_factor_meta: Dict[str, Any],
    l_factor_meta: Optional[Dict[str, Any]],
    l_score: float,
    direction_score: float,
    enhanced_f: float,
    params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Step3风险管理层主函数

    Pipeline:
        1. 提取支撑/阻力位（S因子ZigZag）
        2. 提取订单簿信息（L因子元数据）
        3. 计算/获取ATR
        4. 计算入场价
        5. 计算止损价
        6. 计算止盈价
        7. 验证赔率是否满足最小要求

    Args:
        symbol: 交易对符号
        klines: K线数据（至少24根1h K线）
        s_factor_meta: S因子元数据（包含zigzag_points）
        l_factor_meta: L因子元数据（包含obi_value等）
        l_score: L因子流动性得分
        direction_score: 方向得分（Step1输出）
        enhanced_f: Enhanced F v2得分（Step2输出）
        params: 配置参数

    Returns:
        dict: {
            "entry_price": float,           # 入场价
            "stop_loss": float,             # 止损价
            "take_profit": float,           # 止盈价
            "risk_pct": float,              # 风险百分比
            "reward_pct": float,            # 收益百分比
            "risk_reward_ratio": float,     # 赔率
            "support": float | None,        # 支撑位
            "resistance": float | None,     # 阻力位
            "atr": float,                   # ATR值
            "pass": bool,                   # 是否通过Step3
            "reject_reason": str | None     # 拒绝原因
        }
    """
    # 获取当前价格
    current_price = float(klines[-1]["close"])

    # 获取/计算ATR
    atr = float(klines[-1].get("atr") or 0.0)
    if atr <= 0:
        atr_period = params.get("four_step_system", {}).get("step3_risk", {}).get("volatility", {}).get("atr_period", 14)
        atr = calculate_simple_atr(klines, period=atr_period)
        if atr <= 0:
            # 极端情况：数据不足，使用价格的0.5%作为ATR估计
            atr = current_price * 0.005

    # 提取支撑/阻力
    sr = extract_support_resistance(s_factor_meta)

    # 提取订单簿信息
    orderbook = extract_orderbook_from_L_meta(l_factor_meta, params)

    # 计算入场价
    entry_price = calculate_entry_price(
        current_price=current_price,
        support=sr["support"],
        resistance=sr["resistance"],
        enhanced_f=enhanced_f,
        direction_score=direction_score,
        orderbook=orderbook,
        params=params
    )

    # 计算止损价
    stop_loss = calculate_stop_loss(
        entry_price=entry_price,
        support=sr["support"],
        resistance=sr["resistance"],
        atr=atr,
        direction_score=direction_score,
        l_score=l_score,
        params=params
    )

    # 计算止盈价
    take_profit = calculate_take_profit(
        entry_price=entry_price,
        stop_loss=stop_loss,
        resistance=sr["resistance"],
        support=sr["support"],
        direction_score=direction_score,
        params=params
    )

    # 计算风险/收益百分比
    risk_pct = abs(entry_price - stop_loss) / entry_price * 100.0
    reward_pct = abs(take_profit - entry_price) / entry_price * 100.0
    rr = reward_pct / max(risk_pct, 0.01)  # 防除0

    # 验证赔率（添加小容差避免浮点数精度问题）
    min_rr = params.get("four_step_system", {}).get("step3_risk", {}).get("take_profit", {}).get("min_risk_reward_ratio", 1.5)
    pass_step3 = rr >= (min_rr - 0.01)  # 容差0.01，避免边界case

    reject_reason = None if pass_step3 else f"赔率不足: {rr:.2f} < {min_rr:.2f}"

    if pass_step3:
        log(f"✅ {symbol} - Step3通过: Entry={entry_price:.6f}, SL={stop_loss:.6f}, TP={take_profit:.6f}, RR={rr:.2f}")
    else:
        log(f"❌ {symbol} - Step3拒绝: {reject_reason}")

    return {
        "entry_price": round(entry_price, 6),
        "stop_loss": round(stop_loss, 6),
        "take_profit": round(take_profit, 6),
        "risk_pct": round(risk_pct, 2),
        "reward_pct": round(reward_pct, 2),
        "risk_reward_ratio": round(rr, 2),
        "support": sr["support"],
        "resistance": sr["resistance"],
        "atr": round(atr, 6),
        "pass": pass_step3,
        "reject_reason": reject_reason
    }


# ============ 测试用例 ============

if __name__ == "__main__":
    """
    测试Step3风险管理层

    Usage:
        python3 -m ats_core.decision.step3_risk
    """
    print("=" * 70)
    print("v7.4 Step3风险管理层测试")
    print("=" * 70)

    # 模拟配置
    from ats_core.cfg import CFG
    test_params = CFG.params

    # 确保step3_risk配置存在
    if "four_step_system" not in test_params or "step3_risk" not in test_params["four_step_system"]:
        print("⚠️  配置缺失，使用默认配置")
        test_params["four_step_system"] = test_params.get("four_step_system", {})
        test_params["four_step_system"]["step3_risk"] = {
            "volatility": {"atr_period": 14, "max_loss_fraction": 0.02},
            "entry_price": {
                "strong_accumulation_f": 70,
                "moderate_accumulation_f": 40,
                "buffer_strong": 1.000,
                "buffer_moderate": 1.002,
                "buffer_weak": 1.005
            },
            "stop_loss": {
                "mode": "structure_above_or_below",
                "base_atr_multiplier": 2.0,
                "liquidity_adjustment": {
                    "low_liquidity_threshold": -30,
                    "high_liquidity_threshold": 30,
                    "low_liquidity_multiplier": 1.5,
                    "high_liquidity_multiplier": 0.8
                },
                "structure_above_or_below_mode": {
                    "structure_buffer_long": 0.994,
                    "structure_buffer_short": 1.006,
                    "use_min_of_structure_and_volatility": True
                }
            },
            "take_profit": {
                "min_risk_reward_ratio": 1.5,
                "structure_buffer": 0.998,
                "use_max_of_min_and_structure": True
            },
            "orderbook": {
                "enabled": True,
                "wall_adjustment_enabled": False
            }
        }

    # 模拟K线数据
    base_price = 100.0
    klines_test = []
    for i in range(24):
        klines_test.append({
            "open_time": 1700000000000 + i * 3600000,
            "open": base_price + i * 0.1,
            "high": base_price + i * 0.1 + 0.5,
            "low": base_price + i * 0.1 - 0.5,
            "close": base_price + i * 0.1 + 0.2,
            "volume": 1000000.0,
            "atr": 0.8
        })

    # 测试场景1：完美做多机会（强吸筹 + 清晰支撑）
    print("\n📊 测试场景1：完美做多机会（强吸筹 + 清晰支撑）")
    print("-" * 70)

    s_meta_1 = {
        "theta": 0.75,
        "timing": 0.9,
        "zigzag_points": [
            {"type": "L", "price": 99.5, "dt": 5},
            {"type": "H", "price": 102.8, "dt": 3},
            {"type": "L", "price": 100.2, "dt": 2},
            {"type": "H", "price": 103.5, "dt": 1}
        ]
    }

    l_meta_1 = {
        "obi_value": 0.4,
        "best_bid": 102.0,
        "best_ask": 102.1
    }

    result1 = step3_risk_management(
        symbol="ETHUSDT",
        klines=klines_test,
        s_factor_meta=s_meta_1,
        l_factor_meta=l_meta_1,
        l_score=50.0,
        direction_score=75.0,  # 做多
        enhanced_f=80.0,  # 强吸筹
        params=test_params
    )

    print(f"\n结果: {'✅ 通过' if result1['pass'] else '❌ 拒绝'}")
    print(f"Entry: {result1['entry_price']:.6f}")
    print(f"Stop Loss: {result1['stop_loss']:.6f}")
    print(f"Take Profit: {result1['take_profit']:.6f}")
    print(f"风险: {result1['risk_pct']:.2f}%")
    print(f"收益: {result1['reward_pct']:.2f}%")
    print(f"赔率: {result1['risk_reward_ratio']:.2f}")
    print(f"支撑: {result1['support']}")
    print(f"阻力: {result1['resistance']}")

    # 测试场景2：做空机会（中度放空 + 阻力）
    print("\n\n📊 测试场景2：做空机会（中度放空 + 阻力）")
    print("-" * 70)

    s_meta_2 = {
        "theta": 0.60,
        "timing": 0.7,
        "zigzag_points": [
            {"type": "H", "price": 102.5, "dt": 4},
            {"type": "L", "price": 98.8, "dt": 3},
            {"type": "H", "price": 102.0, "dt": 1}
        ]
    }

    result2 = step3_risk_management(
        symbol="BTCUSDT",
        klines=klines_test,
        s_factor_meta=s_meta_2,
        l_factor_meta=None,
        l_score=-20.0,  # 低流动性
        direction_score=-60.0,  # 做空
        enhanced_f=50.0,  # 中度放空
        params=test_params
    )

    print(f"\n结果: {'✅ 通过' if result2['pass'] else '❌ 拒绝'}")
    print(f"Entry: {result2['entry_price']:.6f}")
    print(f"Stop Loss: {result2['stop_loss']:.6f}")
    print(f"Take Profit: {result2['take_profit']:.6f}")
    print(f"赔率: {result2['risk_reward_ratio']:.2f}")

    # 测试场景3：赔率不足被拒（止损太大）
    print("\n\n📊 测试场景3：赔率不足被拒（止损太大）")
    print("-" * 70)

    # 模拟高波动K线（大ATR）
    klines_volatile = []
    for i in range(24):
        klines_volatile.append({
            "open_time": 1700000000000 + i * 3600000,
            "open": base_price + i * 0.5,
            "high": base_price + i * 0.5 + 3.0,
            "low": base_price + i * 0.5 - 3.0,
            "close": base_price + i * 0.5 + 0.2,
            "volume": 1000000.0,
            "atr": 5.0  # 大ATR
        })

    s_meta_3 = {
        "theta": 0.50,
        "timing": 0.5,
        "zigzag_points": [
            {"type": "L", "price": 95.0, "dt": 3},
            {"type": "H", "price": 108.0, "dt": 1}
        ]
    }

    result3 = step3_risk_management(
        symbol="SOLUSDT",
        klines=klines_volatile,
        s_factor_meta=s_meta_3,
        l_factor_meta=None,
        l_score=0.0,
        direction_score=40.0,
        enhanced_f=35.0,  # 弱吸筹
        params=test_params
    )

    print(f"\n结果: {'✅ 通过' if result3['pass'] else '❌ 拒绝'}")
    if not result3['pass']:
        print(f"拒绝原因: {result3['reject_reason']}")
    print(f"赔率: {result3['risk_reward_ratio']:.2f}")

    print("\n" + "=" * 70)
    print("✅ Step3风险管理层测试完成")
    print("=" * 70)
