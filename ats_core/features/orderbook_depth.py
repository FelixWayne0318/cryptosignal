# coding: utf-8
"""
订单簿深度指标（D指标）

世界级微观结构指标：
- OBI (Order Book Imbalance): 买卖盘深度失衡
- Spread: 买卖价差（流动性成本）
- Depth: Top 20档深度（抗冲击能力）

逻辑：
- OBI > 0 → 买盘堆积，潜在上涨
- OBI < 0 → 卖盘堆积，潜在下跌
- Spread小 → 流动性好，信号可信
- Spread大 → 流动性差，风险高
"""
from typing import Dict, Tuple
import math


def directional_score(
    value: float,
    neutral: float = 0.0,
    scale: float = 1.0
) -> float:
    """
    方向性评分函数

    Args:
        value: 输入值
        neutral: 中性点
        scale: 缩放系数

    Returns:
        -100 到 +100 的分数
    """
    normalized = (value - neutral) / scale

    # tanh压缩到(-1, 1)
    score = math.tanh(normalized) * 100

    return score


def calculate_orderbook_imbalance(orderbook: dict, depth: int = 20) -> Tuple[float, float, float]:
    """
    计算订单簿失衡（OBI）

    Args:
        orderbook: 订单簿数据，格式:
            {
                'bids': [[price, qty], ...],
                'asks': [[price, qty], ...]
            }
        depth: 计算深度（档位数量）

    Returns:
        (OBI, 买盘深度, 卖盘深度)

    公式:
        OBI = (买盘深度 - 卖盘深度) / (买盘深度 + 卖盘深度)

        深度 = Σ(price × quantity)  # 美元价值
    """
    bids = orderbook.get('bids', [])
    asks = orderbook.get('asks', [])

    # 计算买盘深度（美元价值）
    depth_bid = 0.0
    for i in range(min(depth, len(bids))):
        price = float(bids[i][0])
        qty = float(bids[i][1])
        depth_bid += price * qty

    # 计算卖盘深度（美元价值）
    depth_ask = 0.0
    for i in range(min(depth, len(asks))):
        price = float(asks[i][0])
        qty = float(asks[i][1])
        depth_ask += price * qty

    # 计算OBI
    total_depth = depth_bid + depth_ask
    if total_depth > 0:
        obi = (depth_bid - depth_ask) / total_depth
    else:
        obi = 0.0

    return obi, depth_bid, depth_ask


def calculate_spread(orderbook: dict) -> Tuple[float, float]:
    """
    计算买卖价差

    Args:
        orderbook: 订单簿数据

    Returns:
        (价差基点, 中间价)

    公式:
        Spread (bps) = (ask1 - bid1) / mid × 10000
    """
    bids = orderbook.get('bids', [])
    asks = orderbook.get('asks', [])

    if not bids or not asks:
        return 0.0, 0.0

    bid1 = float(bids[0][0])
    ask1 = float(asks[0][0])

    mid = (bid1 + ask1) / 2

    if mid > 0:
        spread_bps = (ask1 - bid1) / mid * 10000
    else:
        spread_bps = 0.0

    return spread_bps, mid


def score_orderbook_depth(
    orderbook: dict,
    params: dict = None
) -> Tuple[int, dict]:
    """
    D（订单簿深度）评分

    Args:
        orderbook: 订单簿数据，格式:
            {
                'bids': [[price, qty], ...],
                'asks': [[price, qty], ...]
            }
        params: 参数配置（可选）

    Returns:
        (D分数 [-100, +100], 元数据)

    评分逻辑:
        1. OBI分数（70%权重）:
           - OBI直接映射到-100到+100
           - OBI > 0 → 买盘堆积 → 正分
           - OBI < 0 → 卖盘堆积 → 负分

        2. 价差分数（30%权重）:
           - Spread越小越好（流动性好）
           - Spread < 5bps → 正常（0分调整）
           - Spread > 5bps → 负向调整

        3. 综合分数:
           D = 0.7 × OBI分数 + 0.3 × 价差分数

    风险警告:
        - spread_bps > 10: 流动性枯竭风险
        - spread_bps > 20: 严重流动性风险（应跳过信号）
    """
    if params is None:
        params = {}

    # 默认参数
    obi_depth = params.get('obi_depth', 20)  # OBI计算深度
    spread_neutral = params.get('spread_neutral', 5.0)  # 价差中性点（bps）
    spread_scale = params.get('spread_scale', 3.0)  # 价差缩放系数

    # 1. 计算OBI
    obi, depth_bid, depth_ask = calculate_orderbook_imbalance(orderbook, depth=obi_depth)

    # OBI分数（直接映射，-1到+1 → -100到+100）
    obi_score = obi * 100

    # 2. 计算价差
    spread_bps, mid_price = calculate_spread(orderbook)

    # 价差分数（反向指标：越小越好）
    # 负号表示反向，spread越大分数越低
    spread_score = directional_score(
        -spread_bps,
        neutral=-spread_neutral,
        scale=spread_scale
    )

    # 3. 综合评分（70% OBI + 30% 价差）
    D_raw = 0.7 * obi_score + 0.3 * spread_score

    # 限制到[-100, +100]
    D = int(round(max(-100, min(100, D_raw))))

    # 4. 元数据
    meta = {
        "obi": round(obi, 4),
        "depth_bid": int(depth_bid),
        "depth_ask": int(depth_ask),
        "spread_bps": round(spread_bps, 2),
        "mid_price": round(mid_price, 2),
        "obi_score": round(obi_score, 1),
        "spread_score": round(spread_score, 1),
        "liquidity_warning": spread_bps > 10,  # 流动性风险警告
        "severe_liquidity_risk": spread_bps > 20  # 严重流动性风险
    }

    return D, meta


def validate_orderbook(orderbook: dict) -> bool:
    """
    验证订单簿数据有效性

    Args:
        orderbook: 订单簿数据

    Returns:
        True = 有效, False = 无效
    """
    if not isinstance(orderbook, dict):
        return False

    bids = orderbook.get('bids', [])
    asks = orderbook.get('asks', [])

    if not bids or not asks:
        return False

    if len(bids) < 5 or len(asks) < 5:
        # 至少需要5档数据
        return False

    try:
        bid1 = float(bids[0][0])
        ask1 = float(asks[0][0])

        # 买1应该小于卖1
        if bid1 >= ask1:
            return False

        return True
    except (ValueError, IndexError, TypeError):
        return False
