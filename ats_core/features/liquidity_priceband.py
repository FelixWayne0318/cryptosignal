# coding: utf-8
"""
价格带法流动性分析（Price Band Method）
P2.5: 替代固定档位数，使用±bps价格带聚合

专家建议：
- 不使用"前10档/20档"
- 全部切换到±bps聚合
- Coverage(q,B)、impact_bps(q)、OBI_B在±B bps内计算
- B=30-50实盘最有用
- 对齐"四道闸"：impact≤10bps、OBI≤0.30、spread≤25bps、Room≥0.6×ATR
"""

from typing import Dict, Any, List, Tuple, Optional
import math


def _to_f(x) -> float:
    """安全转换为float"""
    try:
        return float(x)
    except Exception:
        return 0.0


def aggregate_within_band(
    levels: List[List[float]],
    mid_price: float,
    band_bps: float,
    side: str
) -> Tuple[float, float, List[Tuple[float, float]]]:
    """
    聚合价格带内的订单簿数据

    Args:
        levels: 订单簿档位 [[price, qty], ...]
        mid_price: 中间价
        band_bps: 价格带宽度（bps）
        side: 'bid' or 'ask'

    Returns:
        (total_qty, total_notional_usdt, filtered_levels)
        - total_qty: 价格带内总数量
        - total_notional_usdt: 价格带内总名义价值（USDT）
        - filtered_levels: 价格带内的档位列表 [(price, qty), ...]
    """
    if mid_price <= 0:
        return 0.0, 0.0, []

    # 计算价格带边界
    band_ratio = band_bps / 10000.0

    if side == 'bid':
        # 买盘：mid * (1 - band_bps/10000) 到 mid
        price_min = mid_price * (1.0 - band_ratio)
        price_max = mid_price
    else:  # ask
        # 卖盘：mid 到 mid * (1 + band_bps/10000)
        price_min = mid_price
        price_max = mid_price * (1.0 + band_ratio)

    total_qty = 0.0
    total_notional = 0.0
    filtered_levels = []

    for level in levels:
        price = _to_f(level[0])
        qty = _to_f(level[1])

        if price_min <= price <= price_max:
            total_qty += qty
            total_notional += price * qty
            filtered_levels.append((price, qty))

    return total_qty, total_notional, filtered_levels


def calculate_coverage(
    levels: List[List[float]],
    target_qty: float,
    mid_price: float,
    band_bps: float,
    side: str
) -> Tuple[bool, float, float]:
    """
    计算Coverage(q,B): 目标数量q能否在±B bps内被吸收

    Args:
        levels: 订单簿档位
        target_qty: 目标数量（币数）
        mid_price: 中间价
        band_bps: 价格带宽度（bps）
        side: 'bid' (卖出需求) or 'ask' (买入需求)

    Returns:
        (covered, available_qty, available_notional_usdt)
        - covered: 是否完全覆盖
        - available_qty: 价格带内可用数量
        - available_notional_usdt: 价格带内可用名义价值
    """
    total_qty, total_notional, _ = aggregate_within_band(
        levels, mid_price, band_bps, side
    )

    covered = total_qty >= target_qty

    return covered, total_qty, total_notional


def calculate_impact_bps(
    levels: List[List[float]],
    notional_usdt: float,
    mid_price: float,
    side: str
) -> Tuple[float, float, bool]:
    """
    计算impact_bps(q): 执行q USDT订单的价格冲击（bps）

    Args:
        levels: 订单簿档位 [[price, qty], ...]
        notional_usdt: 交易名义价值（USDT）
        mid_price: 中间价
        side: 'ask' (买入吃ask) or 'bid' (卖出吃bid)

    Returns:
        (impact_bps, avg_exec_price, sufficient_depth)
        - impact_bps: 价格冲击（基点）
        - avg_exec_price: 平均成交价
        - sufficient_depth: 深度是否足够
    """
    if mid_price <= 0 or notional_usdt <= 0:
        return 0.0, mid_price, True

    remaining_notional = notional_usdt
    total_cost_or_revenue = 0.0
    executed_qty = 0.0

    for level in levels:
        price = _to_f(level[0])
        qty = _to_f(level[1])

        if price <= 0:
            continue

        notional_at_level = price * qty

        if notional_at_level >= remaining_notional:
            # 足够满足剩余需求
            qty_needed = remaining_notional / price
            executed_qty += qty_needed

            if side == 'ask':
                # 买入：计算总花费
                total_cost_or_revenue += remaining_notional
            else:
                # 卖出：计算总收入
                total_cost_or_revenue += remaining_notional

            remaining_notional = 0
            break
        else:
            # 吃完这一档
            executed_qty += qty

            if side == 'ask':
                total_cost_or_revenue += notional_at_level
            else:
                total_cost_or_revenue += notional_at_level

            remaining_notional -= notional_at_level

    # 检查深度是否足够
    sufficient_depth = (remaining_notional <= 0)

    if not sufficient_depth:
        # 深度不足，返回惩罚性冲击
        return 1000.0, mid_price * 2.0, False

    # 计算平均成交价
    if side == 'ask':
        avg_exec_price = total_cost_or_revenue / (notional_usdt / mid_price)
        impact_bps = ((avg_exec_price - mid_price) / mid_price) * 10000.0
    else:
        avg_exec_price = total_cost_or_revenue / (notional_usdt / mid_price)
        impact_bps = ((mid_price - avg_exec_price) / mid_price) * 10000.0

    return impact_bps, avg_exec_price, sufficient_depth


def calculate_obi_in_band(
    bids: List[List[float]],
    asks: List[List[float]],
    mid_price: float,
    band_bps: float
) -> Tuple[float, float, float]:
    """
    计算价格带内的订单簿失衡度 OBI_B

    OBI = (bid_vol - ask_vol) / (bid_vol + ask_vol)

    Args:
        bids: 买单列表
        asks: 卖单列表
        mid_price: 中间价
        band_bps: 价格带宽度（bps）

    Returns:
        (obi_value, bid_qty_in_band, ask_qty_in_band)
        - obi_value: -1 到 +1，正值表示买盘优势
        - bid_qty_in_band: 价格带内买盘数量
        - ask_qty_in_band: 价格带内卖盘数量
    """
    bid_qty, _, _ = aggregate_within_band(bids, mid_price, band_bps, 'bid')
    ask_qty, _, _ = aggregate_within_band(asks, mid_price, band_bps, 'ask')

    total_qty = bid_qty + ask_qty

    if total_qty == 0:
        return 0.0, 0.0, 0.0

    obi_value = (bid_qty - ask_qty) / total_qty

    return obi_value, bid_qty, ask_qty


def calculate_spread_bps(
    bid_price: float,
    ask_price: float
) -> float:
    """
    计算买卖价差（bps）

    Args:
        bid_price: 最佳买价
        ask_price: 最佳卖价

    Returns:
        spread_bps: 价差（基点）
    """
    if bid_price <= 0 or ask_price <= 0:
        return 0.0

    mid_price = (bid_price + ask_price) / 2.0

    if mid_price <= 0:
        return 0.0

    spread = ask_price - bid_price
    spread_bps = (spread / mid_price) * 10000.0

    return spread_bps


def score_liquidity_priceband(
    orderbook: Dict[str, Any],
    params: Dict[str, Any] = None
) -> Tuple[float, Dict[str, Any]]:
    """
    使用价格带法计算流动性评分

    Args:
        orderbook: 订单簿数据 {'bids': [[price, qty], ...], 'asks': [...]}
        params: 参数字典，包含:
            - band_bps: 价格带宽度（默认40 bps，专家建议30-50）
            - impact_notional_usdt: 冲击测试规模（默认50,000 USDT）
            - impact_threshold_bps: 冲击阈值（默认10 bps，对齐四道闸）
            - obi_threshold: OBI阈值（默认0.30，对齐四道闸）
            - spread_threshold_bps: 价差阈值（默认25 bps，对齐四道闸）

    Returns:
        (liquidity_score 0-100, metadata)
    """
    if params is None:
        params = {}

    # 参数（专家建议）
    band_bps = params.get('band_bps', 40.0)  # 30-50最有用
    impact_notional = params.get('impact_notional_usdt', 50000.0)
    impact_threshold = params.get('impact_threshold_bps', 10.0)  # 四道闸
    obi_threshold = params.get('obi_threshold', 0.30)  # 四道闸
    spread_threshold = params.get('spread_threshold_bps', 25.0)  # 四道闸

    # 权重
    w_spread = params.get('spread_weight', 0.25)
    w_impact = params.get('impact_weight', 0.40)  # 提高冲击权重（最关键）
    w_obi = params.get('obi_weight', 0.20)
    w_coverage = params.get('coverage_weight', 0.15)

    # === 1. 数据验证 ===
    if not orderbook or 'bids' not in orderbook or 'asks' not in orderbook:
        return 0.0, {'error': 'Invalid orderbook data'}

    bids = orderbook['bids']
    asks = orderbook['asks']

    if not bids or not asks:
        return 0.0, {'error': 'Empty orderbook'}

    best_bid = _to_f(bids[0][0])
    best_ask = _to_f(asks[0][0])

    if best_bid <= 0 or best_ask <= 0:
        return 0.0, {'error': 'Invalid prices'}

    mid_price = (best_bid + best_ask) / 2.0

    # === 2. 计算各维度指标 ===

    # 2.1 Spread（价差）
    spread_bps = calculate_spread_bps(best_bid, best_ask)

    if spread_bps <= spread_threshold:
        spread_score = 100.0
    elif spread_bps >= spread_threshold * 3:
        spread_score = 0.0
    else:
        # 线性递减
        spread_score = 100.0 * (1.0 - (spread_bps - spread_threshold) / (spread_threshold * 2))

    # 2.2 Impact（冲击成本）
    buy_impact_bps, buy_avg_price, buy_sufficient = calculate_impact_bps(
        asks, impact_notional, mid_price, 'ask'
    )
    sell_impact_bps, sell_avg_price, sell_sufficient = calculate_impact_bps(
        bids, impact_notional, mid_price, 'bid'
    )

    max_impact_bps = max(buy_impact_bps, sell_impact_bps)

    if max_impact_bps <= impact_threshold:
        impact_score = 100.0
    elif max_impact_bps >= impact_threshold * 5:
        impact_score = 0.0
    else:
        # 线性递减
        impact_score = 100.0 * (1.0 - (max_impact_bps - impact_threshold) / (impact_threshold * 4))

    # 2.3 OBI（订单簿失衡度）
    obi_value, bid_qty_band, ask_qty_band = calculate_obi_in_band(
        bids, asks, mid_price, band_bps
    )

    abs_obi = abs(obi_value)

    if abs_obi <= obi_threshold:
        obi_score = 100.0
    elif abs_obi >= 0.7:
        obi_score = 0.0
    else:
        # 线性递减
        obi_score = 100.0 * (1.0 - (abs_obi - obi_threshold) / (0.7 - obi_threshold))

    # 2.4 Coverage（覆盖度）
    # 检查价格带内能否容纳测试订单
    target_qty = impact_notional / mid_price

    buy_covered, buy_avail_qty, buy_avail_notional = calculate_coverage(
        asks, target_qty, mid_price, band_bps, 'ask'
    )
    sell_covered, sell_avail_qty, sell_avail_notional = calculate_coverage(
        bids, target_qty, mid_price, band_bps, 'bid'
    )

    both_covered = buy_covered and sell_covered

    if both_covered:
        coverage_score = 100.0
    else:
        # 部分覆盖
        buy_ratio = min(1.0, buy_avail_notional / impact_notional)
        sell_ratio = min(1.0, sell_avail_notional / impact_notional)
        min_ratio = min(buy_ratio, sell_ratio)
        coverage_score = 100.0 * min_ratio

    # === 3. 加权融合 ===
    raw_score = (
        spread_score * w_spread +
        impact_score * w_impact +
        obi_score * w_obi +
        coverage_score * w_coverage
    )

    liquidity_score = int(round(max(0.0, min(100.0, raw_score))))

    # === 4. 流动性等级 ===
    if liquidity_score >= 80:
        liquidity_level = 'excellent'
    elif liquidity_score >= 70:
        liquidity_level = 'good'
    elif liquidity_score >= 60:
        liquidity_level = 'moderate'
    elif liquidity_score >= 50:
        liquidity_level = 'fair'
    else:
        liquidity_level = 'poor'

    # === 5. 四道闸判断 ===
    gate_impact = max_impact_bps <= impact_threshold
    gate_obi = abs_obi <= obi_threshold
    gate_spread = spread_bps <= spread_threshold
    # Room ≥ 0.6×ATR 需要ATR数据，这里暂时不判断

    gates_passed = sum([gate_impact, gate_obi, gate_spread])
    gates_status = f"{gates_passed}/3 (impact={gate_impact}, OBI={gate_obi}, spread={gate_spread})"

    # === 6. 元数据 ===
    metadata = {
        'liquidity_score': liquidity_score,
        'liquidity_level': liquidity_level,
        'band_bps': band_bps,

        # Spread
        'spread_bps': spread_bps,
        'spread_score': spread_score,
        'spread_threshold_bps': spread_threshold,

        # Impact
        'buy_impact_bps': buy_impact_bps,
        'sell_impact_bps': sell_impact_bps,
        'max_impact_bps': max_impact_bps,
        'impact_score': impact_score,
        'impact_threshold_bps': impact_threshold,

        # OBI
        'obi_value': obi_value,
        'obi_score': obi_score,
        'obi_threshold': obi_threshold,
        'bid_qty_in_band': bid_qty_band,
        'ask_qty_in_band': ask_qty_band,

        # Coverage
        'buy_covered': buy_covered,
        'sell_covered': sell_covered,
        'both_covered': both_covered,
        'coverage_score': coverage_score,

        # 四道闸
        'gates_passed': gates_passed,
        'gates_status': gates_status,
        'gate_impact': gate_impact,
        'gate_obi': gate_obi,
        'gate_spread': gate_spread,

        # 基础信息
        'best_bid': best_bid,
        'best_ask': best_ask,
        'mid_price': mid_price
    }

    return liquidity_score, metadata


# ========== 测试代码 ==========

if __name__ == "__main__":
    print("=" * 60)
    print("价格带法流动性测试（P2.5）")
    print("=" * 60)

    # 场景1: 优秀流动性
    print("\n[场景1] 优秀流动性")
    orderbook_1 = {
        'bids': [
            [50000.0, 10.0], [49995.0, 15.0], [49990.0, 20.0], [49985.0, 25.0],
            [49980.0, 30.0], [49975.0, 35.0], [49970.0, 40.0], [49965.0, 45.0],
            [49960.0, 50.0], [49950.0, 55.0]
        ],
        'asks': [
            [50005.0, 10.0], [50010.0, 15.0], [50015.0, 20.0], [50020.0, 25.0],
            [50025.0, 30.0], [50030.0, 35.0], [50035.0, 40.0], [50040.0, 45.0],
            [50045.0, 50.0], [50050.0, 55.0]
        ]
    }
    score_1, meta_1 = score_liquidity_priceband(orderbook_1)
    print(f"  流动性评分: {score_1}")
    print(f"  等级: {meta_1['liquidity_level']}")
    print(f"  价差: {meta_1['spread_bps']:.2f} bps (阈值≤{meta_1['spread_threshold_bps']:.0f})")
    print(f"  买入冲击: {meta_1['buy_impact_bps']:.2f} bps")
    print(f"  卖出冲击: {meta_1['sell_impact_bps']:.2f} bps")
    print(f"  最大冲击: {meta_1['max_impact_bps']:.2f} bps (阈值≤{meta_1['impact_threshold_bps']:.0f})")
    print(f"  OBI: {meta_1['obi_value']:.3f} (阈值≤{meta_1['obi_threshold']:.2f})")
    print(f"  四道闸: {meta_1['gates_status']}")

    # 场景2: 较差流动性（宽价差+高冲击）
    print("\n[场景2] 较差流动性（宽价差）")
    orderbook_2 = {
        'bids': [
            [50000.0, 1.0], [49900.0, 2.0], [49800.0, 3.0], [49700.0, 4.0],
            [49600.0, 5.0]
        ],
        'asks': [
            [50150.0, 1.0], [50250.0, 2.0], [50350.0, 3.0], [50450.0, 4.0],
            [50550.0, 5.0]
        ]
    }
    score_2, meta_2 = score_liquidity_priceband(orderbook_2)
    print(f"  流动性评分: {score_2}")
    print(f"  等级: {meta_2['liquidity_level']}")
    print(f"  价差: {meta_2['spread_bps']:.2f} bps")
    print(f"  最大冲击: {meta_2['max_impact_bps']:.2f} bps")
    print(f"  OBI: {meta_2['obi_value']:.3f}")
    print(f"  四道闸: {meta_2['gates_status']}")

    # 场景3: 失衡订单簿
    print("\n[场景3] 失衡订单簿（买盘优势）")
    orderbook_3 = {
        'bids': [
            [50000.0, 100.0], [49995.0, 80.0], [49990.0, 70.0], [49985.0, 60.0]
        ],
        'asks': [
            [50005.0, 10.0], [50010.0, 8.0], [50015.0, 7.0], [50020.0, 6.0]
        ]
    }
    score_3, meta_3 = score_liquidity_priceband(orderbook_3)
    print(f"  流动性评分: {score_3}")
    print(f"  等级: {meta_3['liquidity_level']}")
    print(f"  OBI: {meta_3['obi_value']:.3f} (买盘:{meta_3['bid_qty_in_band']:.1f}, 卖盘:{meta_3['ask_qty_in_band']:.1f})")
    print(f"  价差: {meta_3['spread_bps']:.2f} bps")
    print(f"  四道闸: {meta_3['gates_status']}")

    print("\n" + "=" * 60)
    print("✅ 价格带法测试完成")
    print("=" * 60)
