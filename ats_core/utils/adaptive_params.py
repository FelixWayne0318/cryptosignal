# coding: utf-8
"""
自适应参数调整工具

根据市场状态（波动率、流动性等）动态调整指标参数
提升不同市场环境下的准确率
"""
from typing import Dict, List, Tuple
import math


def calculate_atr_percentile(
    current_atr: float,
    historical_atrs: List[float]
) -> float:
    """
    计算当前ATR在历史中的百分位

    Args:
        current_atr: 当前ATR值
        historical_atrs: 历史ATR序列（建议100-200个数据点）

    Returns:
        百分位（0.0-1.0）
        0.0 = 历史最低波动
        1.0 = 历史最高波动

    示例:
        atr_percentile = 0.8 → 高波动市场（前20%）
        atr_percentile = 0.2 → 低波动市场（后20%）
    """
    if not historical_atrs or current_atr is None:
        return 0.5  # 默认中位数

    # 过滤有效值
    valid_atrs = [x for x in historical_atrs if isinstance(x, (int, float)) and math.isfinite(x) and x > 0]
    if not valid_atrs:
        return 0.5

    # 计算百分位
    sorted_atrs = sorted(valid_atrs)
    n = len(sorted_atrs)

    # 找到当前ATR的位置
    count_below = sum(1 for x in sorted_atrs if x < current_atr)
    percentile = count_below / n if n > 0 else 0.5

    return percentile


def get_adaptive_cvd_scale(atr_percentile: float) -> float:
    """
    根据ATR百分位自适应调整CVD scale

    Args:
        atr_percentile: ATR百分位（0.0-1.0）

    Returns:
        CVD scale参数

    逻辑:
        - 高波动（>0.8）: 更敏感（0.01），快速响应
        - 中波动（0.2-0.8）: 标准（0.02）
        - 低波动（<0.2）: 更保守（0.05），避免噪音
    """
    if atr_percentile >= 0.8:
        # 高波动：更敏感
        return 0.01
    elif atr_percentile >= 0.6:
        # 中高波动
        return 0.015
    elif atr_percentile >= 0.4:
        # 中等波动：标准参数
        return 0.02
    elif atr_percentile >= 0.2:
        # 中低波动
        return 0.03
    else:
        # 低波动：更保守
        return 0.05


def get_adaptive_oi_scale(atr_percentile: float) -> float:
    """
    根据ATR百分位自适应调整OI scale

    Args:
        atr_percentile: ATR百分位（0.0-1.0）

    Returns:
        OI scale参数

    逻辑:
        OI变化通常比价格更平稳，scale相对CVD更大
    """
    if atr_percentile >= 0.8:
        return 2.0  # 高波动
    elif atr_percentile >= 0.6:
        return 2.5
    elif atr_percentile >= 0.4:
        return 3.0  # 标准（默认）
    elif atr_percentile >= 0.2:
        return 3.5
    else:
        return 4.0  # 低波动


def get_adaptive_trend_window(atr_percentile: float) -> int:
    """
    根据ATR百分位自适应调整趋势窗口大小

    Args:
        atr_percentile: ATR百分位（0.0-1.0）

    Returns:
        线性回归窗口大小（K线数量）

    逻辑:
        - 高波动：缩短窗口（8），快速响应
        - 低波动：延长窗口（16），避免噪音
    """
    if atr_percentile >= 0.8:
        return 8   # 高波动：快速响应
    elif atr_percentile >= 0.6:
        return 10
    elif atr_percentile >= 0.4:
        return 12  # 标准
    elif atr_percentile >= 0.2:
        return 14
    else:
        return 16  # 低波动：更稳定


def get_adaptive_threshold_multiplier(atr_percentile: float) -> float:
    """
    根据ATR百分位自适应调整阈值乘数

    Args:
        atr_percentile: ATR百分位（0.0-1.0）

    Returns:
        阈值乘数（0.8-1.2）

    逻辑:
        - 高波动：提高阈值（1.2），更严格过滤
        - 低波动：降低阈值（0.8），更容易触发
    """
    if atr_percentile >= 0.8:
        return 1.2  # 高波动：更严格
    elif atr_percentile >= 0.6:
        return 1.1
    elif atr_percentile >= 0.4:
        return 1.0  # 标准
    elif atr_percentile >= 0.2:
        return 0.9
    else:
        return 0.8  # 低波动：更宽松


def get_market_regime(atr_percentile: float) -> str:
    """
    识别市场状态

    Args:
        atr_percentile: ATR百分位（0.0-1.0）

    Returns:
        市场状态标签
    """
    if atr_percentile >= 0.8:
        return "high_volatility"
    elif atr_percentile >= 0.6:
        return "medium_high_volatility"
    elif atr_percentile >= 0.4:
        return "normal"
    elif atr_percentile >= 0.2:
        return "medium_low_volatility"
    else:
        return "low_volatility"


def get_adaptive_params_bundle(
    current_atr: float,
    historical_atrs: List[float]
) -> Dict[str, any]:
    """
    一次性获取所有自适应参数

    Args:
        current_atr: 当前ATR值
        historical_atrs: 历史ATR序列

    Returns:
        包含所有自适应参数的字典

    示例:
        ```python
        params = get_adaptive_params_bundle(current_atr=0.05, historical_atrs=atr_history)
        # {
        #     "atr_percentile": 0.75,
        #     "market_regime": "medium_high_volatility",
        #     "cvd_scale": 0.015,
        #     "oi_scale": 2.5,
        #     "trend_window": 10,
        #     "threshold_multiplier": 1.1
        # }
        ```
    """
    atr_percentile = calculate_atr_percentile(current_atr, historical_atrs)

    return {
        "atr_percentile": round(atr_percentile, 3),
        "market_regime": get_market_regime(atr_percentile),
        "cvd_scale": get_adaptive_cvd_scale(atr_percentile),
        "oi_scale": get_adaptive_oi_scale(atr_percentile),
        "trend_window": get_adaptive_trend_window(atr_percentile),
        "threshold_multiplier": get_adaptive_threshold_multiplier(atr_percentile)
    }


def calculate_historical_atr(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14
) -> List[float]:
    """
    计算滚动ATR序列（用于建立历史分布）

    Args:
        highs: 最高价序列
        lows: 最低价序列
        closes: 收盘价序列
        period: ATR周期（默认14）

    Returns:
        ATR序列

    说明:
        用于建立ATR历史分布，计算百分位
    """
    if len(highs) < period + 1 or len(lows) < period + 1 or len(closes) < period + 1:
        return []

    n = min(len(highs), len(lows), len(closes))
    atrs = []

    # 计算TR序列
    trs = []
    prev_close = closes[0]
    for i in range(1, n):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - prev_close),
            abs(lows[i] - prev_close)
        )
        trs.append(tr)
        prev_close = closes[i]

    # 计算滚动ATR
    for i in range(period - 1, len(trs)):
        atr = sum(trs[i - period + 1:i + 1]) / period
        atrs.append(atr)

    return atrs


def should_be_conservative(
    atr_percentile: float,
    cvd_crowding: bool = False,
    oi_crowding: bool = False
) -> bool:
    """
    判断是否应该保守（降低信号敏感度）

    Args:
        atr_percentile: ATR百分位
        cvd_crowding: CVD是否拥挤
        oi_crowding: OI是否拥挤

    Returns:
        True = 应该保守（高波动或拥挤）
        False = 正常

    逻辑:
        - 高波动（>0.8）→ 保守
        - CVD或OI拥挤 → 保守
        - 低波动且不拥挤 → 正常
    """
    # 高波动市场
    if atr_percentile >= 0.8:
        return True

    # 资金流或持仓拥挤
    if cvd_crowding or oi_crowding:
        return True

    return False


def get_conservative_weight_adjustment() -> float:
    """
    保守模式下的权重调整系数

    Returns:
        权重乘数（0-1）

    说明:
        在保守模式下，降低激进指标的权重
        例如：CVD、OI权重 × 0.8
    """
    return 0.8
