# coding: utf-8
"""
L 因子: Liquidity（流动性）

整合 #2 订单簿承载力

理论基础:
流动性质量评估通过4个维度：

1. Spread（买卖价差）：
   - Spread (bps) = (ask - bid) / mid_price * 10000
   - 价差越小，流动性越好

2. Depth（订单簿深度）：
   - 买卖双方的累积挂单量
   - 深度越大，承载能力越强

3. Impact Cost（冲击成本）：
   - 执行指定规模订单的滑点
   - 冲击成本越低，流动性越好

4. OBI（订单簿失衡度）：
   - OBI = (bid_vol - ask_vol) / (bid_vol + ask_vol)
   - 正值：买盘优势；负值：卖盘优势

评分逻辑:
- 各维度独立评分 0-100
- 加权融合：Spread 30% + Depth 30% + Impact 30% + OBI 10%

Range: 0 到 100（质量维度，非方向）
"""

from __future__ import annotations
from typing import Tuple, Dict, Any, Optional, List
import numpy as np


def _to_f(x) -> float:
    """安全转换为float"""
    try:
        return float(x)
    except Exception:
        return 0.0


def _calculate_spread_score(
    bid_price: float,
    ask_price: float,
    spread_good_bps: float,
    spread_bad_bps: float
) -> Tuple[float, float]:
    """
    计算价差评分

    Args:
        bid_price: 最佳买价
        ask_price: 最佳卖价
        spread_good_bps: 良好价差阈值（bps）
        spread_bad_bps: 较差价差阈值（bps）

    Returns:
        (spread_score 0-100, spread_bps)
    """
    if bid_price == 0 or ask_price == 0:
        return 0.0, 0.0

    mid_price = (bid_price + ask_price) / 2.0
    spread = ask_price - bid_price

    if mid_price == 0:
        return 0.0, 0.0

    # 价差（基点）
    spread_bps = (spread / mid_price) * 10000

    # 评分：越小越好
    if spread_bps <= spread_good_bps:
        # 优秀：100分
        score = 100.0
    elif spread_bps >= spread_bad_bps:
        # 较差：0分
        score = 0.0
    else:
        # 线性插值
        score = 100.0 * (1.0 - (spread_bps - spread_good_bps) / (spread_bad_bps - spread_good_bps))

    return score, spread_bps


def _calculate_depth_score(
    bids: List[List[float]],
    asks: List[List[float]],
    depth_target: float
) -> Tuple[float, float, float]:
    """
    计算深度评分

    Args:
        bids: 买单列表 [[price, quantity], ...]
        asks: 卖单列表 [[price, quantity], ...]
        depth_target: 目标深度（USDT）

    Returns:
        (depth_score 0-100, bid_depth_usdt, ask_depth_usdt)
    """
    if not bids or not asks:
        return 0.0, 0.0, 0.0

    # 计算买单深度（USDT）
    bid_depth_usdt = sum(_to_f(price) * _to_f(qty) for price, qty in bids)

    # 计算卖单深度（USDT）
    ask_depth_usdt = sum(_to_f(price) * _to_f(qty) for price, qty in asks)

    # 取较小值（双边流动性的瓶颈）
    min_depth = min(bid_depth_usdt, ask_depth_usdt)

    # 评分：相对于目标深度
    if min_depth >= depth_target:
        score = 100.0
    else:
        score = 100.0 * (min_depth / depth_target)

    return score, bid_depth_usdt, ask_depth_usdt


def _calculate_impact_score(
    bids: List[List[float]],
    asks: List[List[float]],
    notional: float,
    impact_max_pct: float
) -> Tuple[float, float, float]:
    """
    计算冲击成本评分

    Args:
        bids: 买单列表
        asks: 卖单列表
        notional: 交易规模（USDT）
        impact_max_pct: 最大冲击百分比

    Returns:
        (impact_score 0-100, buy_impact_pct, sell_impact_pct)
    """
    if not bids or not asks:
        return 0.0, 0.0, 0.0

    # 计算买入冲击（需要吃ask）
    remaining_notional = notional
    total_cost = 0.0
    for price, qty in asks:
        price = _to_f(price)
        qty = _to_f(qty)

        notional_at_level = price * qty

        if notional_at_level >= remaining_notional:
            # 足够满足剩余需求
            total_cost += remaining_notional
            remaining_notional = 0
            break
        else:
            # 吃完这一档
            total_cost += notional_at_level
            remaining_notional -= notional_at_level

    if remaining_notional > 0:
        # 订单簿深度不足
        buy_impact_pct = impact_max_pct  # 惩罚：最大冲击
    else:
        # 平均成交价
        avg_buy_price = total_cost / notional if notional > 0 else 0.0
        best_ask = _to_f(asks[0][0])

        if best_ask > 0:
            buy_impact_pct = (avg_buy_price - best_ask) / best_ask
        else:
            buy_impact_pct = 0.0

    # 计算卖出冲击（需要吃bid）
    remaining_qty_usdt = notional
    total_revenue = 0.0
    for price, qty in bids:
        price = _to_f(price)
        qty = _to_f(qty)

        notional_at_level = price * qty

        if notional_at_level >= remaining_qty_usdt:
            total_revenue += remaining_qty_usdt
            remaining_qty_usdt = 0
            break
        else:
            total_revenue += notional_at_level
            remaining_qty_usdt -= notional_at_level

    if remaining_qty_usdt > 0:
        sell_impact_pct = impact_max_pct
    else:
        avg_sell_price = total_revenue / notional if notional > 0 else 0.0
        best_bid = _to_f(bids[0][0])

        if best_bid > 0:
            sell_impact_pct = (best_bid - avg_sell_price) / best_bid
        else:
            sell_impact_pct = 0.0

    # 取最大冲击（最不利）
    max_impact_pct = max(buy_impact_pct, sell_impact_pct)

    # 评分：冲击越小越好
    if max_impact_pct <= 0:
        score = 100.0
    elif max_impact_pct >= impact_max_pct:
        score = 0.0
    else:
        score = 100.0 * (1.0 - max_impact_pct / impact_max_pct)

    return score, buy_impact_pct, sell_impact_pct


def _calculate_obi_score(
    bids: List[List[float]],
    asks: List[List[float]]
) -> Tuple[float, float]:
    """
    计算订单簿失衡度（OBI）评分

    Args:
        bids: 买单列表
        asks: 卖单列表

    Returns:
        (obi_score 0-100, obi_value -1 to +1)
    """
    if not bids or not asks:
        return 50.0, 0.0

    # 计算买卖双方总量
    bid_volume = sum(_to_f(qty) for price, qty in bids)
    ask_volume = sum(_to_f(qty) for price, qty in asks)

    total_volume = bid_volume + ask_volume

    if total_volume == 0:
        return 50.0, 0.0

    # OBI = (bid - ask) / (bid + ask)
    obi_value = (bid_volume - ask_volume) / total_volume

    # 评分：失衡度越接近平衡，流动性质量越高
    # 但这里OBI主要作为辅助指标，中性即可
    # 极端失衡（>0.5或<-0.5）降低评分
    if abs(obi_value) < 0.3:
        # 相对平衡：高分
        score = 100.0
    elif abs(obi_value) < 0.5:
        # 中度失衡：中等分
        score = 70.0
    else:
        # 极度失衡：低分
        score = 40.0

    return score, obi_value


def calculate_liquidity(
    orderbook: Dict[str, Any],
    params: Dict[str, Any] = None
) -> Tuple[float, Dict[str, Any]]:
    """
    计算流动性评分

    Args:
        orderbook: 订单簿数据，格式:
            {
                'bids': [[price, quantity], ...],  # 按价格降序
                'asks': [[price, quantity], ...]   # 按价格升序
            }
        params: 参数字典，包含:
            - spread_good_bps: 良好价差（默认2.0 bps）
            - spread_bad_bps: 较差价差（默认10.0 bps）
            - depth_target_usdt: 目标深度（默认1,000,000）
            - impact_notional_usdt: 冲击测试规模（默认100,000）
            - impact_max_pct: 最大冲击（默认1%）
            - orderbook_depth_levels: 深度层数（默认10）
            - spread_weight: 价差权重（默认0.3）
            - depth_weight: 深度权重（默认0.3）
            - impact_weight: 冲击权重（默认0.3）
            - obi_weight: OBI权重（默认0.1）

    Returns:
        (liquidity_score, metadata)
        - liquidity_score: 0 到 100（越高越好）
        - metadata: 详细信息
    """
    if params is None:
        params = {}

    # 默认参数
    spread_good = params.get('spread_good_bps', 2.0)
    spread_bad = params.get('spread_bad_bps', 10.0)
    depth_target = params.get('depth_target_usdt', 1000000)
    impact_notional = params.get('impact_notional_usdt', 100000)
    impact_max = params.get('impact_max_pct', 0.01)
    depth_levels = params.get('orderbook_depth_levels', 10)

    w_spread = params.get('spread_weight', 0.3)
    w_depth = params.get('depth_weight', 0.3)
    w_impact = params.get('impact_weight', 0.3)
    w_obi = params.get('obi_weight', 0.1)

    # === 1. 数据验证 ===
    if not orderbook or 'bids' not in orderbook or 'asks' not in orderbook:
        return 50.0, {'error': 'Invalid orderbook data'}

    bids = orderbook['bids'][:depth_levels]
    asks = orderbook['asks'][:depth_levels]

    if not bids or not asks:
        return 0.0, {'error': 'Empty orderbook'}

    # === 2. 计算各维度评分 ===

    # Spread评分
    best_bid = _to_f(bids[0][0])
    best_ask = _to_f(asks[0][0])
    spread_score, spread_bps = _calculate_spread_score(best_bid, best_ask, spread_good, spread_bad)

    # Depth评分
    depth_score, bid_depth, ask_depth = _calculate_depth_score(bids, asks, depth_target)

    # Impact评分
    impact_score, buy_impact, sell_impact = _calculate_impact_score(bids, asks, impact_notional, impact_max)

    # OBI评分
    obi_score, obi_value = _calculate_obi_score(bids, asks)

    # === 3. 加权融合 ===
    liquidity_score = (
        spread_score * w_spread +
        depth_score * w_depth +
        impact_score * w_impact +
        obi_score * w_obi
    )

    # 限制到0-100
    liquidity_score = max(0, min(100, liquidity_score))

    # === 4. 流动性等级 ===
    if liquidity_score >= 80:
        liquidity_level = 'excellent'
        interpretation = 'Excellent liquidity'
    elif liquidity_score >= 70:
        liquidity_level = 'good'
        interpretation = 'Good liquidity'
    elif liquidity_score >= 60:
        liquidity_level = 'moderate'
        interpretation = 'Moderate liquidity'
    elif liquidity_score >= 50:
        liquidity_level = 'fair'
        interpretation = 'Fair liquidity'
    else:
        liquidity_level = 'poor'
        interpretation = 'Poor liquidity'

    # === 5. 元数据 ===
    metadata = {
        'liquidity_score': liquidity_score,
        'liquidity_level': liquidity_level,
        'interpretation': interpretation,
        'spread_bps': spread_bps,
        'spread_score': spread_score,
        'bid_depth_usdt': bid_depth,
        'ask_depth_usdt': ask_depth,
        'depth_score': depth_score,
        'buy_impact_pct': buy_impact,
        'sell_impact_pct': sell_impact,
        'impact_score': impact_score,
        'obi_value': obi_value,
        'obi_score': obi_score,
        'best_bid': best_bid,
        'best_ask': best_ask
    }

    return liquidity_score, metadata


# ========== 测试代码 ==========

if __name__ == "__main__":
    print("=" * 60)
    print("L 因子测试 - Liquidity（流动性）")
    print("=" * 60)

    # 场景1: 优秀流动性（紧密价差+深度+低冲击）
    print("\n[场景1] 优秀流动性")
    orderbook_1 = {
        'bids': [
            [50000, 10], [49990, 15], [49980, 20], [49970, 25],
            [49960, 30], [49950, 35], [49940, 40], [49930, 45],
            [49920, 50], [49910, 55]
        ],
        'asks': [
            [50010, 10], [50020, 15], [50030, 20], [50040, 25],
            [50050, 30], [50060, 35], [50070, 40], [50080, 45],
            [50090, 50], [50100, 55]
        ]
    }
    score_1, meta_1 = calculate_liquidity(orderbook_1)
    print(f"  流动性评分: {score_1:.1f}")
    print(f"  等级: {meta_1['liquidity_level']}")
    print(f"  价差: {meta_1['spread_bps']:.2f} bps")
    print(f"  买单深度: ${meta_1['bid_depth_usdt']:,.0f}")
    print(f"  卖单深度: ${meta_1['ask_depth_usdt']:,.0f}")
    print(f"  买入冲击: {meta_1['buy_impact_pct']:.4%}")
    print(f"  OBI: {meta_1['obi_value']:.3f}")

    # 场景2: 较差流动性（宽价差+浅深度）
    print("\n[场景2] 较差流动性（宽价差）")
    orderbook_2 = {
        'bids': [
            [50000, 1], [49800, 2], [49600, 3], [49400, 4],
            [49200, 5]
        ],
        'asks': [
            [50500, 1], [50700, 2], [50900, 3], [51100, 4],
            [51300, 5]
        ]
    }
    score_2, meta_2 = calculate_liquidity(orderbook_2)
    print(f"  流动性评分: {score_2:.1f}")
    print(f"  等级: {meta_2['liquidity_level']}")
    print(f"  价差: {meta_2['spread_bps']:.2f} bps")
    print(f"  买单深度: ${meta_2['bid_depth_usdt']:,.0f}")
    print(f"  卖单深度: ${meta_2['ask_depth_usdt']:,.0f}")
    print(f"  买入冲击: {meta_2['buy_impact_pct']:.4%}")

    # 场景3: 失衡订单簿（买盘优势）
    print("\n[场景3] 失衡订单簿（买盘优势）")
    orderbook_3 = {
        'bids': [
            [50000, 50], [49990, 50], [49980, 50], [49970, 50],
            [49960, 50]
        ],
        'asks': [
            [50010, 5], [50020, 5], [50030, 5], [50040, 5],
            [50050, 5]
        ]
    }
    score_3, meta_3 = calculate_liquidity(orderbook_3)
    print(f"  流动性评分: {score_3:.1f}")
    print(f"  等级: {meta_3['liquidity_level']}")
    print(f"  价差: {meta_3['spread_bps']:.2f} bps")
    print(f"  OBI: {meta_3['obi_value']:.3f} (买盘优势)")
    print(f"  深度评分: {meta_3['depth_score']:.1f} (受限于卖盘)")

    print("\n" + "=" * 60)
    print("✅ Liquidity因子测试完成")
    print("=" * 60)
