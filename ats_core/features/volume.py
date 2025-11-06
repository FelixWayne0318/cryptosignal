# coding: utf-8
"""
V（量能）评分 - 统一±100系统（多空对称修复版 v2.0）

改进v2.0（修复多空对称性）：
- 上涨+放量 = 正分（做多信号）
- 下跌+放量 = 负分（做空信号） ⭐ 修复重点
- 上涨+缩量 = 负分（做多信号弱）
- 下跌+缩量 = 正分（做空信号弱，可能见底）

核心思想：
量能配合价格方向才有意义！
- 放量本身不代表方向，需要结合价格
- 下跌放量（恐慌盘、止损盘、抄底盘）= 做空信号
- 上涨放量（追涨盘、突破盘、FOMO盘）= 做多信号

P0.2改进（自适应阈值）：
- 价格方向阈值不再固定为0.5%
- 根据历史波动率自适应调整

P2.3改进（2025-11-05，scale参数优化）：
- 问题：scale=0.3过小，导致tanh函数过早饱和，V分数聚集在±80
- 方案：scale增加3倍（0.3→0.9），避免饱和，使V分数更均匀分布
- 效果：vlevel=1.3给60分（vs旧版88分），vlevel=1.5给75分（vs旧版97分）
"""
import math
import numpy as np
from ats_core.features.scoring_utils import directional_score  # 保留用于内部计算
from ats_core.scoring.scoring_utils import StandardizationChain

# 模块级StandardizationChain实例
_volume_chain = StandardizationChain(alpha=0.15, tau=3.0, z0=2.5, zmax=6.0, lam=1.5)


def get_adaptive_price_threshold(
    closes: list,
    lookback: int = 20,
    mode: str = 'hybrid',
    min_data_points: int = 50
) -> float:
    """
    计算自适应价格方向阈值（P0.2修复）

    Args:
        closes: 历史收盘价列表
        lookback: 计算变化率的回溯周期（默认20）
        mode: 'adaptive' | 'legacy' | 'hybrid'
        min_data_points: 最小数据点数（默认50）

    Returns:
        price_threshold: 价格方向判定阈值（如0.005表示±0.5%）
    """
    # Legacy模式或数据不足时使用固定阈值
    if mode == 'legacy' or len(closes) < min_data_points:
        return 0.005  # 固定0.5%

    # 计算历史价格变化率
    closes_array = np.array(closes)
    price_changes = []

    # 计算每个lookback周期的涨跌幅
    for i in range(lookback, len(closes_array)):
        price_start = closes_array[i - lookback]
        price_end = closes_array[i]
        if price_start != 0:
            change_pct = (price_end - price_start) / abs(price_start)
            price_changes.append(change_pct)

    if len(price_changes) < 10:
        return 0.005  # 数据不足，fallback

    # 使用价格变化的中位数绝对值作为阈值
    abs_changes = np.abs(price_changes)
    threshold = float(np.percentile(abs_changes, 50))  # 中位数

    # 边界保护
    threshold = np.clip(threshold, 0.001, 0.02)  # 0.1% - 2%

    return threshold


def score_volume(vol, closes=None, params=None):
    """
    V（量能）评分 - 统一±100系统（多空对称修复版）

    核心逻辑：
    1. 计算量能强度（绝对值）：vlevel = v5/v20
    2. 计算价格方向：最近5根K线的涨跌幅
    3. 量能强度 × 价格方向 = 最终分数

    示例：
    - 上涨5% + 放量30%（v5/v20=1.3） → V = +60（做多信号）
    - 下跌5% + 放量30%（v5/v20=1.3） → V = -60（做空信号） ⭐ 修复
    - 上涨5% + 缩量20%（v5/v20=0.8） → V = -40（做多信号弱）
    - 下跌5% + 缩量20%（v5/v20=0.8） → V = +40（做空信号弱）

    Args:
        vol: 量能列表
        closes: 收盘价列表（用于判断价格方向）
        params: 参数配置

    Returns:
        (V分数 [-100, +100], 元数据)
    """
    # 默认参数
    # P2.3修复（2025-11-05）：scale参数优化，避免±80聚集
    # 诊断发现：scale=0.3过小导致tanh过早饱和，推荐0.89（3倍增加）
    default_params = {
        "vlevel_scale": 0.9,      # P2.3修复: 0.3→0.9，避免饱和（v5/v20=1.3给约60分，1.5给75分）
        "vroc_scale": 0.9,        # P2.3修复: 0.3→0.9，保持一致性
        "vlevel_weight": 0.6,     # vlevel 权重
        "vroc_weight": 0.4,       # vroc 权重
        "price_lookback": 5,      # 价格方向回溯周期
        "adaptive_threshold_mode": "hybrid",  # P0.2: 自适应阈值模式
    }

    p = dict(default_params)
    if isinstance(params, dict):
        p.update(params)

    if len(vol) < 25:
        return 0, {"v5v20": 1.0, "vroc": 0.0, "price_trend_pct": 0.0}

    v5 = sum(vol[-5:]) / 5.0
    v20 = sum(vol[-20:]) / 20.0
    vlevel = v5 / max(1e-12, v20)

    # vroc: ln(v/sma20) - ln(prev) - 保留方向信息
    # 正值 = 量能加速，负值 = 量能减速
    cur = math.log(max(1e-9, vol[-1] / max(1e-9, v20)))
    prv = math.log(max(1e-9, vol[-2] / max(1e-9, sum(vol[-21:-1]) / 20.0)))
    vroc = cur - prv

    # 软映射评分（0-100）
    vlevel_score_raw = directional_score(vlevel, neutral=1.0, scale=p["vlevel_scale"])
    vroc_score_raw = directional_score(vroc, neutral=0.0, scale=p["vroc_scale"])

    # 映射到 -100 到 +100
    vlevel_score = (vlevel_score_raw - 50) * 2
    vroc_score = (vroc_score_raw - 50) * 2

    # 加权平均（量能强度，未考虑方向）
    V_strength = p["vlevel_weight"] * vlevel_score + p["vroc_weight"] * vroc_score
    V_strength = max(-100, min(100, V_strength))

    # ========== v2.0 修复：考虑价格方向 ==========

    # 计算价格趋势（最近N根K线的涨跌幅）
    price_trend_pct = 0.0
    price_direction = 0  # -1=下跌, 0=中性, +1=上涨
    price_threshold = 0.005  # 默认阈值
    threshold_source = 'legacy'

    if closes is not None and len(closes) >= p["price_lookback"] + 1:
        # P0.2: 计算自适应阈值
        adaptive_mode = p["adaptive_threshold_mode"]
        if adaptive_mode != 'legacy' and len(closes) >= 50:
            price_threshold = get_adaptive_price_threshold(
                closes,
                lookback=p["price_lookback"],
                mode=adaptive_mode
            )
            threshold_source = 'adaptive'
        else:
            price_threshold = 0.005  # Fallback到固定阈值

        # 使用最近5根K线（或配置的回溯周期）
        lookback = p["price_lookback"]
        price_start = closes[-(lookback + 1)]
        price_end = closes[-1]

        # 计算涨跌幅
        price_trend_pct = (price_end - price_start) / max(1e-12, abs(price_start))

        # 判断价格方向（使用自适应阈值）
        if price_trend_pct > price_threshold:
            price_direction = 1   # 上涨
        elif price_trend_pct < -price_threshold:
            price_direction = -1  # 下跌
        else:
            price_direction = 0   # 中性（小幅波动）

    # ========== 应用价格方向修正 ==========

    if price_direction != 0:
        # 情况1：价格上涨 + 放量（V_strength > 0） → 保持正分（做多信号）
        # 情况2：价格上涨 + 缩量（V_strength < 0） → 保持负分（做多信号弱）
        # 情况3：价格下跌 + 放量（V_strength > 0） → 反转为负分（做空信号）⭐ 修复
        # 情况4：价格下跌 + 缩量（V_strength < 0） → 反转为正分（做空信号弱）

        if price_direction == -1:
            # 价格下跌：反转V的符号
            V_raw = -V_strength
        else:
            # 价格上涨：保持V的符号
            V_raw = V_strength
    else:
        # 价格中性（横盘）：使用原始量能分数（放量=正，缩量=负）
        V_raw = V_strength

    # v2.0合规：应用StandardizationChain
    # ⚠️ 2025-11-04紧急修复：禁用StandardizationChain，过度压缩导致信号丢失
    # V_pub, diagnostics = _volume_chain.standardize(V_raw)
    V_pub = max(-100, min(100, V_raw))  # 直接使用原始值
    V = int(round(V_pub))

    # ========== 解释文本（考虑价格方向）==========

    if closes is not None and len(closes) >= 6:
        # 有价格数据：使用方向性描述
        if V >= 40:
            if price_direction == 1:
                interpretation = "上涨放量（做多信号）"
            elif price_direction == -1:
                interpretation = "下跌放量（做空信号）"
            else:
                interpretation = "横盘放量"
        elif V >= 10:
            if price_direction == 1:
                interpretation = "上涨温和放量"
            elif price_direction == -1:
                interpretation = "下跌温和放量"
            else:
                interpretation = "温和放量"
        elif V >= -10:
            interpretation = "量能平稳"
        elif V >= -40:
            if price_direction == 1:
                interpretation = "上涨缩量（信号弱）"
            elif price_direction == -1:
                interpretation = "下跌缩量（可能见底）"
            else:
                interpretation = "温和缩量"
        else:
            if price_direction == 1:
                interpretation = "上涨大幅缩量（警告）"
            elif price_direction == -1:
                interpretation = "下跌大幅缩量（可能见底）"
            else:
                interpretation = "大幅缩量"
    else:
        # 无价格数据：使用传统描述（向后兼容）
        if V >= 40:
            interpretation = "强势放量"
        elif V >= 10:
            interpretation = "温和放量"
        elif V >= -10:
            interpretation = "量能平稳"
        elif V >= -40:
            interpretation = "温和缩量"
        else:
            interpretation = "大幅缩量"

    return V, {
        "v5v20": round(vlevel, 2),
        "vroc": round(vroc, 4),
        "vlevel_score": int(vlevel_score),
        "vroc_score": int(vroc_score),
        "V_strength_raw": int(V_strength),  # v2.0: 原始量能强度（未考虑方向）
        "price_trend_pct": round(price_trend_pct * 100, 2),  # v2.0: 价格涨跌幅（%）
        "price_direction": price_direction,  # v2.0: 价格方向（-1/0/+1）
        "interpretation": interpretation,
        "symmetry_fixed": True,  # v2.0: 标记已修复多空对称性
        # P0.2: 自适应阈值信息
        "price_threshold": round(price_threshold * 100, 3),  # 阈值（%）
        "threshold_source": threshold_source,  # 'adaptive' or 'legacy'
    }
