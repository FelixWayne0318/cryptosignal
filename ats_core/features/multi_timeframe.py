# coding: utf-8
"""
多时间框架协同分析

理论: Fractal Market Hypothesis
市场在不同时间尺度上展现相似模式

目标: 验证15m/1h/4h/1d的T/M/C一致性，减少虚假突破
"""
from typing import Dict, List
from ats_core.sources.binance import get_klines
from ats_core.logging import log, warn
import math


def calculate_timeframe_score(klines: list, dimension: str) -> float:
    """
    计算单个时间框架的维度分数

    Args:
        klines: K线数据
        dimension: 维度 ('T', 'M', 'C')

    Returns:
        分数 (-100到+100)
    """
    if not klines or len(klines) < 30:
        return 0.0

    closes = [float(k[4]) for k in klines]

    if dimension == 'T':
        # 简化趋势计算 (EMA5 vs EMA20)
        ema5 = _ema(closes, 5)
        ema20 = _ema(closes, 20)
        trend_dir = 1 if ema5[-1] > ema20[-1] else -1
        # 斜率强度
        slope = (closes[-1] - closes[-12]) / 12 if len(closes) >= 12 else 0
        return trend_dir * min(100, abs(slope) * 1000)

    elif dimension == 'M':
        # 动量 (近期加速度)
        if len(closes) < 20:
            return 0
        recent_slope = (closes[-1] - closes[-7]) / 7
        prev_slope = (closes[-7] - closes[-14]) / 7
        accel = recent_slope - prev_slope
        return min(100, max(-100, accel * 5000))

    elif dimension == 'C':
        # CVD简化版 (基于tick rule)
        opens = [float(k[1]) for k in klines]
        volumes = [float(k[5]) for k in klines]
        cvd = 0
        for i in range(len(closes)):
            sign = 1 if closes[i] >= opens[i] else -1
            cvd += sign * volumes[i]
        # 归一化CVD变化
        cvd_change = cvd / sum(volumes) if sum(volumes) > 0 else 0
        return min(100, max(-100, cvd_change * 500))

    return 0.0


def _ema(seq: List[float], period: int) -> List[float]:
    """简化EMA计算"""
    if not seq or period <= 1:
        return seq
    alpha = 2.0 / (period + 1)
    ema_val = seq[0]
    result = [ema_val]
    for v in seq[1:]:
        ema_val = alpha * v + (1 - alpha) * ema_val
        result.append(ema_val)
    return result


def multi_timeframe_coherence(symbol: str, verbose: bool = False) -> Dict:
    """
    计算多时间框架一致性

    Args:
        symbol: 交易对
        verbose: 是否打印详细日志

    Returns:
        {
            'coherence_score': 0-100,
            'details': {...},
            'dominant_direction': 'long'/'short'/'neutral',
            'recommendation': 'strong_buy'/'buy'/'neutral'/'sell'/'strong_sell'
        }
    """
    timeframes = {
        '15m': 100,
        '1h': 100,
        '4h': 100,
        '1d': 50
    }

    # 存储各维度各时间框架的分数
    scores = {
        'T': {},
        'M': {},
        'C': {}
    }

    # 获取数据并计算分数
    for tf, limit in timeframes.items():
        try:
            klines = get_klines(symbol, tf, limit)
            if not klines:
                if verbose:
                    warn(f"[MTF] {symbol} {tf}: 数据获取失败")
                continue

            for dim in ['T', 'M', 'C']:
                scores[dim][tf] = calculate_timeframe_score(klines, dim)

        except Exception as e:
            # 数据获取失败，跳过该时间框架
            if verbose:
                warn(f"[MTF] {symbol} {tf}: {e}")
            continue

    # 计算一致性
    coherence_details = {}
    overall_coherence = 0

    for dim in ['T', 'M', 'C']:
        if not scores[dim]:
            coherence_details[dim] = 0
            continue

        # 提取该维度所有时间框架的符号
        values = list(scores[dim].values())
        signs = [1 if v > 10 else -1 if v < -10 else 0 for v in values]

        # 一致性 = 同向比例
        if len(signs) == 0:
            coherence = 0
        else:
            # 计算主导方向
            dominant_sign = max(set(signs), key=signs.count)
            # 一致比例
            coherence = signs.count(dominant_sign) / len(signs)

        coherence_details[dim] = coherence
        overall_coherence += coherence

    # 平均一致性
    overall_coherence = overall_coherence / 3 * 100  # 转为0-100

    # 判断主导方向 (基于T维度)
    if 'T' in scores and scores['T']:
        t_values = list(scores['T'].values())
        avg_t = sum(t_values) / len(t_values)
        if avg_t > 20:
            dominant = 'long'
        elif avg_t < -20:
            dominant = 'short'
        else:
            dominant = 'neutral'
    else:
        dominant = 'neutral'

    # 综合建议 (考虑一致性和方向强度)
    if overall_coherence >= 80:
        # 高一致性
        if dominant == 'long':
            recommendation = 'strong_buy'
        elif dominant == 'short':
            recommendation = 'strong_sell'
        else:
            recommendation = 'neutral'
    elif overall_coherence >= 60:
        # 中等一致性
        if dominant == 'long':
            recommendation = 'buy'
        elif dominant == 'short':
            recommendation = 'sell'
        else:
            recommendation = 'neutral'
    else:
        # 低一致性：不推荐交易
        recommendation = 'neutral'

    if verbose:
        log(f"[MTF] {symbol}: 一致性={overall_coherence:.0f}%, 方向={dominant}, 建议={recommendation}")

    return {
        'coherence_score': round(overall_coherence, 1),
        'details': {
            dim: {
                'scores': scores[dim],
                'coherence': round(coherence_details[dim] * 100, 1)
            }
            for dim in ['T', 'M', 'C']
        },
        'dominant_direction': dominant,
        'recommendation': recommendation
    }


# ========== 测试 ==========

if __name__ == "__main__":
    print("=" * 60)
    print("多时间框架协同分析测试")
    print("=" * 60)

    test_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    for symbol in test_symbols:
        print(f"\n{symbol}:")
        try:
            result = multi_timeframe_coherence(symbol, verbose=True)

            print(f"  一致性得分: {result['coherence_score']:.1f}/100")
            print(f"  主导方向:   {result['dominant_direction']}")
            print(f"  交易建议:   {result['recommendation']}")
            print(f"  详细:")

            for dim in ['T', 'M', 'C']:
                dim_data = result['details'][dim]
                print(f"    {dim}维度: {dim_data['coherence']:.1f}% 一致")
                for tf, score in dim_data['scores'].items():
                    marker = "🟢" if score > 20 else "🔴" if score < -20 else "🟡"
                    print(f"      {tf}: {score:+6.1f} {marker}")

        except Exception as e:
            print(f"  错误: {e}")

    print("\n" + "=" * 60)
    print("✅ 多时间框架模块测试完成")
    print("=" * 60)
