# coding: utf-8
"""
Q 因子: Liquidation（清算密度）

整合 #7 清算密度倾斜

理论基础:
1. LTI (Liquidation Tilt Index):
   - LTI = (long_liq - short_liq) / total_liq
   - 正值：多头清算占主导（空头胜利，可能超跌反弹）
   - 负值：空头清算占主导（多头胜利，可能超涨回调）

2. 级联风险（Cascade Risk）:
   - 大量清算头寸聚集在接近当前价格的位置
   - 价格触及清算墙 → 级联清算 → 价格加速运动

3. 清算墙（Liquidation Wall）:
   - 某一价格区间内清算密度显著高于其他区域
   - 多头墙：下方有大量多单清算（下跌风险）
   - 空头墙：上方有大量空单清算（上涨风险）

评分逻辑:
- LTI Z-score归一化到±100
- 正值：多头清算（看跌后反弹）
- 负值：空头清算（看涨后回调）

Range: -100 到 +100
"""

from __future__ import annotations
from typing import Tuple, Dict, Any, List, Optional
import numpy as np


def _to_f(x) -> float:
    """安全转换为float"""
    try:
        return float(x)
    except Exception:
        return 0.0


def _z_score(value: float, history: List[float]) -> float:
    """计算z-score"""
    if not history or len(history) < 2:
        return 0.0

    mean = np.mean(history)
    std = np.std(history)

    if std == 0:
        return 0.0

    return (value - mean) / std


def _detect_liquidation_walls(
    liquidation_map: Dict[float, Dict[str, float]],
    current_price: float,
    wall_min_volume: float,
    cluster_pct: float
) -> Tuple[Optional[float], Optional[float], Dict[str, Any]]:
    """
    检测清算墙

    Args:
        liquidation_map: 清算地图 {price: {'long': vol, 'short': vol}}
        current_price: 当前价格
        wall_min_volume: 最小墙体积（USDT）
        cluster_pct: 聚集百分比阈值

    Returns:
        (long_wall_price, short_wall_price, metadata)
    """
    if not liquidation_map:
        return None, None, {}

    # 分离多空清算
    long_liq = {}
    short_liq = {}

    for price, data in liquidation_map.items():
        long_vol = _to_f(data.get('long', 0))
        short_vol = _to_f(data.get('short', 0))

        if long_vol > 0:
            long_liq[price] = long_vol
        if short_vol > 0:
            short_liq[price] = short_vol

    # 检测多头墙（下方）
    long_wall_price = None
    long_wall_volume = 0.0

    for price, volume in long_liq.items():
        # 只看下方（价格低于当前价）
        if price < current_price:
            distance_pct = (current_price - price) / current_price
            # 在2%范围内且体积足够大
            if distance_pct <= cluster_pct and volume >= wall_min_volume:
                if volume > long_wall_volume:
                    long_wall_volume = volume
                    long_wall_price = price

    # 检测空头墙（上方）
    short_wall_price = None
    short_wall_volume = 0.0

    for price, volume in short_liq.items():
        # 只看上方（价格高于当前价）
        if price > current_price:
            distance_pct = (price - current_price) / current_price
            # 在2%范围内且体积足够大
            if distance_pct <= cluster_pct and volume >= wall_min_volume:
                if volume > short_wall_volume:
                    short_wall_volume = volume
                    short_wall_price = price

    metadata = {
        'long_wall_price': long_wall_price,
        'long_wall_volume': long_wall_volume,
        'short_wall_price': short_wall_price,
        'short_wall_volume': short_wall_volume
    }

    return long_wall_price, short_wall_price, metadata


def calculate_liquidation(
    liquidations: List[Dict[str, Any]],
    current_price: float,
    liquidation_map: Optional[Dict[float, Dict[str, float]]] = None,
    params: Dict[str, Any] = None
) -> Tuple[float, Dict[str, Any]]:
    """
    计算清算密度评分

    Args:
        liquidations: 清算事件列表，格式:
            [
                {'side': 'long', 'volume': 100000, 'price': 50000, 'timestamp': ...},
                {'side': 'short', 'volume': 80000, 'price': 50100, 'timestamp': ...},
                ...
            ]
        current_price: 当前价格
        liquidation_map: 清算密度地图（可选，用于墙检测）
        params: 参数字典，包含:
            - interval_minutes: 统计区间（默认5分钟）
            - zscore_window_hours: z-score窗口（默认1小时）
            - lti_multiplier: LTI乘数（默认50）
            - wall_detection_enabled: 是否启用墙检测（默认True）
            - wall_min_volume_usdt: 最小墙体积（默认1,000,000）
            - wall_cluster_pct: 聚集百分比（默认0.02）

    Returns:
        (liquidation_score, metadata)
        - liquidation_score: -100 到 +100
          - 正值：多头清算占优（看跌后可能反弹）
          - 负值：空头清算占优（看涨后可能回调）
        - metadata: 详细信息
    """
    if params is None:
        params = {}

    # 默认参数
    interval_min = params.get('interval_minutes', 5)
    zscore_window_hours = params.get('zscore_window_hours', 1)
    lti_multiplier = params.get('lti_multiplier', 50)
    wall_detection = params.get('wall_detection_enabled', True)
    wall_min_vol = params.get('wall_min_volume_usdt', 1000000)
    wall_cluster_pct = params.get('wall_cluster_pct', 0.02)

    # === 1. 数据验证 ===
    if not liquidations:
        return 0.0, {'error': 'No liquidation data'}

    # === 2. 计算LTI（Liquidation Tilt Index）===
    long_volume = 0.0
    short_volume = 0.0

    for liq in liquidations:
        side = liq.get('side', '').lower()
        volume = _to_f(liq.get('volume', 0))

        if side == 'long':
            long_volume += volume
        elif side == 'short':
            short_volume += volume

    total_volume = long_volume + short_volume

    if total_volume == 0:
        return 0.0, {'error': 'Zero liquidation volume'}

    # LTI = (long_liq - short_liq) / total_liq
    # 正值：多头清算多（空头占优）
    # 负值：空头清算多（多头占优）
    lti = (long_volume - short_volume) / total_volume

    # === 3. Z-score归一化（如果有历史数据）===
    # 简化版：直接使用LTI * 乘数
    # 在实际应用中，应该使用历史LTI序列计算z-score
    liquidation_score = lti * lti_multiplier

    # 限制到±100
    liquidation_score = max(-100, min(100, liquidation_score))

    # === 4. 清算墙检测（可选）===
    long_wall = None
    short_wall = None
    wall_info = {}

    if wall_detection and liquidation_map:
        long_wall, short_wall, wall_info = _detect_liquidation_walls(
            liquidation_map,
            current_price,
            wall_min_vol,
            wall_cluster_pct
        )

        # 调整评分：如果检测到墙，增强信号
        if long_wall:
            # 下方有多头墙 → 下跌风险增加
            distance_pct = (current_price - long_wall) / current_price
            wall_bonus = min(20, 20 * (1.0 - distance_pct / wall_cluster_pct))
            liquidation_score += wall_bonus

        if short_wall:
            # 上方有空头墙 → 上涨风险增加
            distance_pct = (short_wall - current_price) / current_price
            wall_penalty = min(20, 20 * (1.0 - distance_pct / wall_cluster_pct))
            liquidation_score -= wall_penalty

        # 再次限制到±100
        liquidation_score = max(-100, min(100, liquidation_score))

    # === 5. 风险等级 ===
    if liquidation_score > 50:
        risk_level = 'high_long_cascade'
        interpretation = 'High long liquidation risk (potential cascade down then bounce)'
    elif liquidation_score > 20:
        risk_level = 'moderate_long_cascade'
        interpretation = 'Moderate long liquidation pressure'
    elif liquidation_score > -20:
        risk_level = 'balanced'
        interpretation = 'Balanced liquidation environment'
    elif liquidation_score > -50:
        risk_level = 'moderate_short_cascade'
        interpretation = 'Moderate short liquidation pressure'
    else:
        risk_level = 'high_short_cascade'
        interpretation = 'High short liquidation risk (potential cascade up then pullback)'

    # === 6. 元数据 ===
    metadata = {
        'liquidation_score': liquidation_score,
        'lti': lti,
        'long_volume': long_volume,
        'short_volume': short_volume,
        'total_volume': total_volume,
        'risk_level': risk_level,
        'interpretation': interpretation,
        'long_wall_detected': long_wall is not None,
        'short_wall_detected': short_wall is not None
    }

    # 添加墙信息
    if wall_info:
        metadata.update(wall_info)

    return liquidation_score, metadata


# ========== 测试代码 ==========

if __name__ == "__main__":
    print("=" * 60)
    print("Q 因子测试 - Liquidation（清算密度）")
    print("=" * 60)

    # 场景1: 多头清算占优（空头胜利）
    print("\n[场景1] 多头清算占优（看跌信号）")
    liquidations_1 = [
        {'side': 'long', 'volume': 800000, 'price': 49900},
        {'side': 'long', 'volume': 600000, 'price': 49850},
        {'side': 'long', 'volume': 700000, 'price': 49800},
        {'side': 'short', 'volume': 200000, 'price': 50100},
        {'side': 'short', 'volume': 100000, 'price': 50150},
    ]
    score_1, meta_1 = calculate_liquidation(liquidations_1, current_price=50000)
    print(f"  清算评分: {score_1:.1f}")
    print(f"  LTI: {meta_1['lti']:.3f}")
    print(f"  多头清算: ${meta_1['long_volume']:,.0f}")
    print(f"  空头清算: ${meta_1['short_volume']:,.0f}")
    print(f"  风险等级: {meta_1['risk_level']}")
    print(f"  解读: {meta_1['interpretation']}")

    # 场景2: 空头清算占优（多头胜利）
    print("\n[场景2] 空头清算占优（看涨信号）")
    liquidations_2 = [
        {'side': 'short', 'volume': 900000, 'price': 50100},
        {'side': 'short', 'volume': 700000, 'price': 50150},
        {'side': 'short', 'volume': 800000, 'price': 50200},
        {'side': 'long', 'volume': 300000, 'price': 49900},
        {'side': 'long', 'volume': 200000, 'price': 49850},
    ]
    score_2, meta_2 = calculate_liquidation(liquidations_2, current_price=50000)
    print(f"  清算评分: {score_2:.1f}")
    print(f"  LTI: {meta_2['lti']:.3f}")
    print(f"  多头清算: ${meta_2['long_volume']:,.0f}")
    print(f"  空头清算: ${meta_2['short_volume']:,.0f}")
    print(f"  风险等级: {meta_2['risk_level']}")
    print(f"  解读: {meta_2['interpretation']}")

    # 场景3: 平衡清算
    print("\n[场景3] 平衡清算（中性）")
    liquidations_3 = [
        {'side': 'long', 'volume': 500000, 'price': 49900},
        {'side': 'short', 'volume': 480000, 'price': 50100},
        {'side': 'long', 'volume': 520000, 'price': 49850},
        {'side': 'short', 'volume': 510000, 'price': 50150},
    ]
    score_3, meta_3 = calculate_liquidation(liquidations_3, current_price=50000)
    print(f"  清算评分: {score_3:.1f}")
    print(f"  LTI: {meta_3['lti']:.3f}")
    print(f"  多头清算: ${meta_3['long_volume']:,.0f}")
    print(f"  空头清算: ${meta_3['short_volume']:,.0f}")
    print(f"  风险等级: {meta_3['risk_level']}")

    # 场景4: 清算墙检测
    print("\n[场景4] 清算墙检测")
    liquidations_4 = [
        {'side': 'long', 'volume': 1500000, 'price': 49000},
        {'side': 'long', 'volume': 500000, 'price': 49800},
        {'side': 'short', 'volume': 200000, 'price': 50100},
    ]
    liquidation_map_4 = {
        49000: {'long': 5000000, 'short': 0},  # 大量多头墙（下方）
        49500: {'long': 1000000, 'short': 0},
        50500: {'long': 0, 'short': 3000000},  # 大量空头墙（上方）
    }
    score_4, meta_4 = calculate_liquidation(
        liquidations_4,
        current_price=50000,
        liquidation_map=liquidation_map_4
    )
    print(f"  清算评分: {score_4:.1f}")
    print(f"  多头墙检测: {meta_4['long_wall_detected']}")
    print(f"  多头墙价格: ${meta_4.get('long_wall_price', 'N/A')}")
    print(f"  多头墙体积: ${meta_4.get('long_wall_volume', 0):,.0f}")
    print(f"  空头墙检测: {meta_4['short_wall_detected']}")
    print(f"  空头墙价格: ${meta_4.get('short_wall_price', 'N/A')}")
    print(f"  空头墙体积: ${meta_4.get('short_wall_volume', 0):,.0f}")

    print("\n" + "=" * 60)
    print("✅ Liquidation因子测试完成")
    print("=" * 60)
