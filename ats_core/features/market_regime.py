# coding: utf-8
"""
BTC/ETH市场大盘趋势过滤器（方案B - 独立过滤器）

设计逻辑：
1. 计算BTC和ETH的趋势分数（使用与个币相同的趋势逻辑）
2. Market_Regime = BTC_trend × 0.7 + ETH_trend × 0.3
3. 当信号与市场方向冲突时施加惩罚：
   - 做多但Market < -30: 概率×0.7, Prime×0.8
   - 做空但Market > +30: 概率×0.7, Prime×0.8
4. 不影响七维评分，仅作为最后的风险过滤

目标：避免在BTC强势下跌时做多山寨币
"""

from typing import Dict, Any, Tuple, Union
import math

# 缓存市场趋势结果（避免重复计算）
_market_cache = {}


def _get_kline_field(kline: Union[dict, list], field: str) -> float:
    """
    从K线中提取字段值（兼容字典和列表两种格式）

    P0 Bugfix: 支持回测引擎返回的字典格式K线
    """
    if isinstance(kline, dict):
        return kline.get(field, 0)
    else:
        field_map = {
            "timestamp": 0, "open": 1, "high": 2, "low": 3, "close": 4,
            "volume": 5, "close_time": 6, "quote_volume": 7
        }
        index = field_map.get(field, 0)
        if isinstance(kline, (list, tuple)) and len(kline) > index:
            return kline[index]
        else:
            return 0


def _calc_single_trend(closes: list) -> int:
    """
    计算单个币种的趋势分数（±100系统）

    改进：使用与个币一致的1小时级别趋势计算
    - EMA5/20排列判断（±40分）
    - 12小时斜率/ATR强度（±60分）
    - 时间尺度与个币对齐，响应更快

    Returns:
        -100（强势下跌）到 +100（强势上涨）
    """
    if not closes or len(closes) < 30:
        return 0

    try:
        closes_arr = [float(c) for c in closes]

        # 计算EMA5和EMA20
        ema5 = _ema(closes_arr, 5)
        ema20 = _ema(closes_arr, 20)

        # 1. EMA排列判断（±40分）
        # 检查最近6根K线的EMA排列
        ema_order_bars = min(6, len(ema5))
        ema_up = all(ema5[-i] > ema20[-i] for i in range(1, ema_order_bars + 1))
        ema_dn = all(ema5[-i] < ema20[-i] for i in range(1, ema_order_bars + 1))

        if ema_up:
            ema_score = 40
        elif ema_dn:
            ema_score = -40
        else:
            ema_score = 0

        # 2. 斜率/ATR强度（±60分）
        # 计算12小时斜率
        lookback = min(12, len(closes_arr))
        if lookback >= 5:
            # 简单线性回归
            y = closes_arr[-lookback:]
            n = len(y)
            x = list(range(n))
            x_mean = (n - 1) / 2.0
            y_mean = sum(y) / n

            numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
            denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
            slope = numerator / denominator if denominator > 0 else 0.0

            # 计算ATR（简化版）
            atr = _simple_atr(closes_arr, 14)

            # 斜率归一化
            slope_per_bar = slope / max(1e-9, atr)

            # 映射到±60分
            # slope_per_bar > 0.10 → +60分（强势上涨）
            # slope_per_bar < -0.10 → -60分（强势下跌）
            import math
            slope_score = 60.0 * math.tanh(slope_per_bar / 0.05)
        else:
            slope_score = 0

        # 总分
        trend_score = int(ema_score + slope_score)
        return max(-100, min(100, trend_score))

    except Exception:
        return 0


def _simple_atr(closes: list, period: int = 14) -> float:
    """简化ATR计算（仅用close价格）"""
    if len(closes) < 2:
        return 1.0

    # 用相邻收盘价差异近似TR
    changes = [abs(closes[i] - closes[i-1]) for i in range(1, len(closes))]

    if len(changes) < period:
        return sum(changes) / len(changes) if changes else 1.0

    return sum(changes[-period:]) / period


def calculate_market_regime(cache_key: str = None) -> Tuple[int, Dict[str, Any]]:
    """
    计算BTC/ETH市场大盘趋势

    Args:
        cache_key: 缓存键（通常是时间戳），用于避免同一分钟内重复计算

    Returns:
        (market_regime, meta):
        - market_regime: -100（熊市）到 +100（牛市）
        - meta: {
            "btc_trend": BTC趋势分数,
            "eth_trend": ETH趋势分数,
            "regime_desc": 市场状态描述
          }
    """
    # 检查缓存
    if cache_key and cache_key in _market_cache:
        return _market_cache[cache_key]

    try:
        from ats_core.sources.binance import get_klines

        # 获取BTC和ETH的K线数据
        btc_k1 = get_klines("BTCUSDT", "1h", 100)
        eth_k1 = get_klines("ETHUSDT", "1h", 100)

        # 提取收盘价
        # P0 Bugfix: 使用兼容函数支持字典格式K线
        btc_closes = [float(_get_kline_field(k, "close")) for k in btc_k1]
        eth_closes = [float(_get_kline_field(k, "close")) for k in eth_k1]

        # 计算趋势分数（使用1小时级别算法）
        btc_trend = _calc_single_trend(btc_closes)
        eth_trend = _calc_single_trend(eth_closes)

        # 加权计算市场趋势（BTC 70%, ETH 30%）
        market_regime = int(btc_trend * 0.7 + eth_trend * 0.3)

        # 状态描述
        if market_regime >= 60:
            regime_desc = "强势牛市"
        elif market_regime >= 30:
            regime_desc = "温和牛市"
        elif market_regime >= -30:
            regime_desc = "震荡市场"
        elif market_regime >= -60:
            regime_desc = "温和熊市"
        else:
            regime_desc = "强势熊市"

        meta = {
            "btc_trend": btc_trend,
            "eth_trend": eth_trend,
            "regime_desc": regime_desc,
            "market_regime": market_regime
        }

        # 缓存结果
        result = (market_regime, meta)
        if cache_key:
            _market_cache[cache_key] = result

        return result

    except Exception as e:
        # 数据获取失败时返回中性
        return 0, {
            "btc_trend": 0,
            "eth_trend": 0,
            "regime_desc": "数据不足",
            "market_regime": 0,
            "error": str(e)
        }


def _ema(seq: list, n: int) -> list:
    """计算EMA（与analyze_symbol保持一致）"""
    out = []
    if not seq or n <= 1:
        return [float(v) for v in seq]

    k = 2.0 / (n + 1.0)
    e = None
    for v in seq:
        try:
            v = float(v)
        except Exception:
            v = 0.0
        e = v if e is None else (e + k * (v - e))
        out.append(e)
    return out


def apply_market_filter(
    side: str,
    probability: float,
    prime_strength: float,
    market_regime: int
) -> Tuple[float, float, str]:
    """
    应用市场过滤器（对称奖惩机制）

    改进：
    1. 顺势奖励 + 逆势惩罚（对称设计）
    2. 五档分级（强势/温和/中性）
    3. 阈值放宽（±50替代±30，减少误杀）

    档位设计：
    - 强势顺势（|market| ≥ 60）：概率×1.20, Prime×1.10
    - 温和顺势（50 ≤ |market| < 60）：概率×1.10, Prime×1.05
    - 中性（|market| < 50）：无调整
    - 温和逆势（-60 < |market| ≤ -50）：概率×0.85, Prime×0.92
    - 强势逆势（|market| ≤ -60）：概率×0.70, Prime×0.85

    Args:
        side: "long" or "short"
        probability: 原始概率（0-1）
        prime_strength: Prime评分（0-100）
        market_regime: 市场趋势（-100到+100）

    Returns:
        (adjusted_prob, adjusted_prime, adjustment_reason)
    """
    adjustment_reason = ""
    prob_multiplier = 1.0
    prime_multiplier = 1.0

    if side == "long":
        # 做多：market > 0 是顺势，market < 0 是逆势
        if market_regime >= 60:
            # 强势牛市做多 → 强化信号
            prob_multiplier = 1.20
            prime_multiplier = 1.10
            adjustment_reason = f"✅ 强势顺势（大盘{market_regime:+d}）→ 概率×1.2"

        elif market_regime >= 50:
            # 温和牛市做多 → 增强信号
            prob_multiplier = 1.10
            prime_multiplier = 1.05
            adjustment_reason = f"✅ 温和顺势（大盘{market_regime:+d}）→ 概率×1.1"

        elif market_regime <= -60:
            # 强势熊市做多 → 高风险
            prob_multiplier = 0.70
            prime_multiplier = 0.85
            adjustment_reason = f"⚠️ 强势逆市（大盘{market_regime:+d}）→ 概率×0.7"

        elif market_regime <= -50:
            # 温和熊市做多 → 谨慎
            prob_multiplier = 0.85
            prime_multiplier = 0.92
            adjustment_reason = f"⚠️ 温和逆市（大盘{market_regime:+d}）→ 概率×0.85"

    else:  # side == "short"
        # 做空：market < 0 是顺势，market > 0 是逆势
        if market_regime <= -60:
            # 强势熊市做空 → 强化信号
            prob_multiplier = 1.20
            prime_multiplier = 1.10
            adjustment_reason = f"✅ 强势顺势（大盘{market_regime:+d}）→ 概率×1.2"

        elif market_regime <= -50:
            # 温和熊市做空 → 增强信号
            prob_multiplier = 1.10
            prime_multiplier = 1.05
            adjustment_reason = f"✅ 温和顺势（大盘{market_regime:+d}）→ 概率×1.1"

        elif market_regime >= 60:
            # 强势牛市做空 → 高风险
            prob_multiplier = 0.70
            prime_multiplier = 0.85
            adjustment_reason = f"⚠️ 强势逆市（大盘{market_regime:+d}）→ 概率×0.7"

        elif market_regime >= 50:
            # 温和牛市做空 → 谨慎
            prob_multiplier = 0.85
            prime_multiplier = 0.92
            adjustment_reason = f"⚠️ 温和逆市（大盘{market_regime:+d}）→ 概率×0.85"

    # 应用调整（带上限保护）
    adjusted_prob = min(0.95, probability * prob_multiplier)
    adjusted_prime = min(100.0, prime_strength * prime_multiplier)

    return adjusted_prob, adjusted_prime, adjustment_reason
