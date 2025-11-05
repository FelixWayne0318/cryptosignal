#!/usr/bin/env python3
"""
C/M/O因子生产扫描测试
验证相对历史归一化在多币种扫描中的表现
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ats_core.sources.binance import get_klines, get_open_interest_hist
from ats_core.features.cvd_flow import score_cvd_flow
from ats_core.features.momentum import score_momentum
from ats_core.features.open_interest import score_open_interest
import time

def get_cvd_series(symbol: str, limit: int = 100) -> list:
    """获取CVD序列"""
    klines = get_klines(symbol, interval='1h', limit=limit)
    if not klines:
        return []

    cvd_series = []
    cumulative = 0.0

    for k in klines:
        volume = float(k[5])
        close_price = float(k[4])
        open_price = float(k[1])

        if close_price > open_price:
            delta = volume
        elif close_price < open_price:
            delta = -volume
        else:
            delta = 0.0

        cumulative += delta
        cvd_series.append(cumulative)

    return cvd_series

def test_symbol(symbol: str) -> dict:
    """测试单个币种的C/M/O因子"""
    print(f"\n{'='*60}")
    print(f"🔍 测试币种: {symbol}")
    print(f"{'='*60}")

    results = {}

    # 获取K线数据
    klines = get_klines(symbol, interval='1h', limit=100)
    if not klines:
        print(f"❌ 获取K线失败")
        return None

    close_prices = [float(k[4]) for k in klines]
    high_prices = [float(k[2]) for k in klines]
    low_prices = [float(k[3]) for k in klines]

    # 测试C因子
    try:
        cvd_series = get_cvd_series(symbol, limit=100)
        if len(cvd_series) >= 10:
            c_result = score_cvd_flow(cvd_series)
            c_score = c_result.get('score', 0)
            c_meta = c_result.get('metadata', {})

            print(f"\n📊 C因子 (CVD流向):")
            print(f"   得分: {c_score:.1f}")
            print(f"   归一化方法: {c_meta.get('normalization_method', 'N/A')}")
            print(f"   相对强度: {c_meta.get('relative_intensity', 0):.3f}x")
            print(f"   历史平均斜率: {c_meta.get('avg_abs_slope', 0):.2e}")
            print(f"   当前斜率: {c_meta.get('slope', 0):.2e}")

            results['C'] = {
                'score': c_score,
                'method': c_meta.get('normalization_method'),
                'intensity': c_meta.get('relative_intensity')
            }
        else:
            print(f"   ⚠️ CVD数据不足")
            results['C'] = None
    except Exception as e:
        print(f"   ❌ C因子计算失败: {e}")
        results['C'] = None

    # 测试M因子
    try:
        m_result = score_momentum(high_prices, low_prices, close_prices, {})
        m_score = m_result.get('score', 0)
        m_meta = m_result.get('metadata', {})

        print(f"\n📈 M因子 (动量):")
        print(f"   得分: {m_score:.1f}")
        print(f"   归一化方法: {m_meta.get('normalization_method', 'N/A')}")
        print(f"   斜率强度: {m_meta.get('relative_slope_intensity', 0):.3f}x")
        print(f"   加速度强度: {m_meta.get('relative_accel_intensity', 0):.3f}x")

        results['M'] = {
            'score': m_score,
            'method': m_meta.get('normalization_method'),
            'slope_intensity': m_meta.get('relative_slope_intensity'),
            'accel_intensity': m_meta.get('relative_accel_intensity')
        }
    except Exception as e:
        print(f"   ❌ M因子计算失败: {e}")
        results['M'] = None

    # 测试O因子
    try:
        oi_data = get_open_interest_hist(symbol, period='1h', limit=100)
        if oi_data:
            oi_values = [float(d['sumOpenInterest']) for d in oi_data]
            oi_notional = [float(d['sumOpenInterestValue']) for d in oi_data]

            o_result = score_open_interest(
                oi=oi_values,
                oi_notional=oi_notional,
                c=close_prices,
                params={}
            )
            o_score = o_result.get('score', 0)
            o_meta = o_result.get('metadata', {})

            print(f"\n🔄 O因子 (持仓量):")
            print(f"   得分: {o_score:.1f}")
            print(f"   归一化方法: {o_meta.get('normalization_method', 'N/A')}")
            print(f"   OI强度: {o_meta.get('relative_oi_intensity', 0):.3f}x")
            print(f"   历史平均斜率: {o_meta.get('avg_abs_oi_slope', 0):.2e}")

            results['O'] = {
                'score': o_score,
                'method': o_meta.get('normalization_method'),
                'intensity': o_meta.get('relative_oi_intensity')
            }
        else:
            print(f"   ⚠️ OI数据不足")
            results['O'] = None
    except Exception as e:
        print(f"   ❌ O因子计算失败: {e}")
        results['O'] = None

    return results

def main():
    """主测试函数"""
    print("\n" + "="*70)
    print("🚀 C/M/O因子生产扫描测试")
    print("验证相对历史归一化在多币种中的表现")
    print("="*70)

    # 测试币种列表（不同市值和流动性）
    test_symbols = [
        'BTCUSDT',   # 超大市值
        'ETHUSDT',   # 大市值
        'SOLUSDT',   # 中大市值
        'BNBUSDT',   # 大市值
        'DOGEUSDT',  # 中市值
        'AVAXUSDT',  # 中市值
        'ARBUSDT',   # 中小市值
        'OPUSDT',    # 中小市值
    ]

    all_results = {}

    for symbol in test_symbols:
        try:
            results = test_symbol(symbol)
            if results:
                all_results[symbol] = results
            time.sleep(0.5)  # 避免API限流
        except Exception as e:
            print(f"\n❌ {symbol} 测试失败: {e}")
            continue

    # 汇总分析
    print(f"\n\n{'='*70}")
    print("📊 汇总分析")
    print(f"{'='*70}")

    print(f"\n{'币种':<12} {'C得分':<8} {'C方法':<20} {'M得分':<8} {'M方法':<20} {'O得分':<8} {'O方法':<20}")
    print("-"*120)

    for symbol, results in all_results.items():
        c_score = results['C']['score'] if results['C'] else 'N/A'
        c_method = results['C']['method'] if results['C'] else 'N/A'
        m_score = results['M']['score'] if results['M'] else 'N/A'
        m_method = results['M']['method'] if results['M'] else 'N/A'
        o_score = results['O']['score'] if results['O'] else 'N/A'
        o_method = results['O']['method'] if results['O'] else 'N/A'

        c_score_str = f"{c_score:.1f}" if isinstance(c_score, (int, float)) else c_score
        m_score_str = f"{m_score:.1f}" if isinstance(m_score, (int, float)) else m_score
        o_score_str = f"{o_score:.1f}" if isinstance(o_score, (int, float)) else o_score

        print(f"{symbol:<12} {c_score_str:<8} {c_method:<20} {m_score_str:<8} {m_method:<20} {o_score_str:<8} {o_method:<20}")

    # 统计归一化方法使用情况
    print(f"\n\n📈 归一化方法统计:")

    for factor in ['C', 'M', 'O']:
        methods = [r[factor]['method'] for r in all_results.values() if r[factor]]
        if methods:
            relative_hist_count = sum(1 for m in methods if m == 'relative_historical')
            total = len(methods)
            percentage = (relative_hist_count / total) * 100
            print(f"\n{factor}因子:")
            print(f"   总计: {total} 个币种")
            print(f"   使用relative_historical: {relative_hist_count} ({percentage:.1f}%)")
            print(f"   使用fallback方法: {total - relative_hist_count} ({100-percentage:.1f}%)")

    # 相对强度分析
    print(f"\n\n🎯 相对强度分析:")

    for factor, intensity_key in [('C', 'intensity'), ('M', 'slope_intensity'), ('O', 'intensity')]:
        intensities = []
        for symbol, results in all_results.items():
            if results[factor] and results[factor].get(intensity_key):
                intensities.append((symbol, results[factor][intensity_key]))

        if intensities:
            intensities.sort(key=lambda x: x[1], reverse=True)
            print(f"\n{factor}因子相对强度排名（Top 5）:")
            for i, (symbol, intensity) in enumerate(intensities[:5], 1):
                print(f"   {i}. {symbol}: {intensity:.3f}x")

    print(f"\n\n{'='*70}")
    print(f"✅ 测试完成！共测试 {len(all_results)} 个币种")
    print(f"{'='*70}\n")

if __name__ == '__main__':
    main()
