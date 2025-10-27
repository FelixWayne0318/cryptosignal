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

from typing import Dict, Any, Tuple
import math

# 缓存市场趋势结果（避免重复计算）
_market_cache = {}

def _calc_single_trend(closes: list, ema30: list) -> int:
    """
    计算单个币种的趋势分数（±100系统）

    简化版趋势计算：
    - 基于价格相对于EMA30的位置
    - 基于EMA30的斜率

    Returns:
        -100（强势下跌）到 +100（强势上涨）
    """
    if not closes or len(closes) < 30:
        return 0

    if not ema30 or len(ema30) < 30:
        return 0

    try:
        # 当前价格
        close_now = float(closes[-1])
        ema30_now = float(ema30[-1])

        # 1. 价格相对位置（50分权重）
        # close > ema30 → 正分，close < ema30 → 负分
        price_ratio = (close_now / ema30_now - 1.0) if ema30_now > 0 else 0.0
        position_score = max(-50, min(50, price_ratio * 1000))  # ±5% → ±50分

        # 2. EMA30斜率（50分权重）
        # 斜率向上 → 正分，向下 → 负分
        if len(ema30) >= 10:
            ema30_10ago = float(ema30[-10])
            if ema30_10ago > 0:
                slope = (ema30_now / ema30_10ago - 1.0) / 10  # 10小时变化率
                slope_score = max(-50, min(50, slope * 5000))  # ±1% → ±50分
            else:
                slope_score = 0
        else:
            slope_score = 0

        # 总分
        trend_score = int(position_score + slope_score)
        return max(-100, min(100, trend_score))

    except Exception:
        return 0


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
        btc_closes = [float(k[4]) for k in btc_k1]
        eth_closes = [float(k[4]) for k in eth_k1]

        # 计算EMA30
        btc_ema30 = _ema(btc_closes, 30)
        eth_ema30 = _ema(eth_closes, 30)

        # 计算趋势分数
        btc_trend = _calc_single_trend(btc_closes, btc_ema30)
        eth_trend = _calc_single_trend(eth_closes, eth_ema30)

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
    应用市场过滤器（逆势惩罚）

    Args:
        side: "long" or "short"
        probability: 原始概率（0-1）
        prime_strength: Prime评分（0-100）
        market_regime: 市场趋势（-100到+100）

    Returns:
        (adjusted_prob, adjusted_prime, penalty_reason):
        - adjusted_prob: 调整后概率
        - adjusted_prime: 调整后Prime分数
        - penalty_reason: 惩罚原因（空字符串表示无惩罚）
    """
    penalty_reason = ""

    # 检查逆势交易
    if side == "long" and market_regime < -30:
        # 做多但大盘熊市
        probability *= 0.7
        prime_strength *= 0.8
        penalty_reason = f"逆市做多（大盘{market_regime:+d}）"

    elif side == "short" and market_regime > 30:
        # 做空但大盘牛市
        probability *= 0.7
        prime_strength *= 0.8
        penalty_reason = f"逆市做空（大盘{market_regime:+d}）"

    return probability, prime_strength, penalty_reason
