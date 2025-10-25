#!/usr/bin/env python3
# coding: utf-8
"""
新币识别测试工具

功能：
1. 检测全市场新币（7-30天）
2. 分析新币信号质量
3. 显示新币特殊处理效果

用法：
  python3 test_new_coin.py              # 检测并显示所有新币
  python3 test_new_coin.py --analyze    # 分析新币信号
  python3 test_new_coin.py SYMBOL       # 测试指定币种
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ats_core.sources.tickers import all_24h
from ats_core.sources.binance import get_klines
from ats_core.pipeline.analyze_symbol import analyze_symbol

def detect_new_coins():
    """检测全市场新币"""
    print("=" * 70)
    print("检测全市场新币（7-30天）")
    print("=" * 70)

    tickers = all_24h()
    new_coins = []

    for t in tickers:
        try:
            sym = t.get("symbol", "")
            if not sym.endswith("USDT"):
                continue

            quote = float(t.get("quoteVolume", 0))
            if quote < 10000000:  # 至少1000万USDT
                continue

            # 获取K线检测币龄
            k = get_klines(sym, "1h", 750)
            if k:
                coin_age_hours = len(k)
                coin_age_days = coin_age_hours / 24

                if 7 <= coin_age_days <= 30:
                    phase = "阶段A" if coin_age_days <= 14 else "阶段B"
                    new_coins.append({
                        "symbol": sym,
                        "age_days": round(coin_age_days, 1),
                        "phase": phase,
                        "volume": quote / 1e6  # 百万USDT
                    })

        except Exception as e:
            pass

    # 排序：按币龄排序
    new_coins.sort(key=lambda x: x["age_days"])

    # 显示结果
    if not new_coins:
        print("\n✓ 未检测到符合条件的新币（7-30天，成交额>1000万）")
        return []

    print(f"\n🆕 检测到 {len(new_coins)} 个新币：\n")
    print(f"{'币种':<15} {'币龄(天)':<12} {'阶段':<10} {'24h成交额(M)':<15}")
    print("-" * 70)

    for coin in new_coins:
        print(f"{coin['symbol']:<15} {coin['age_days']:<12.1f} "
              f"{coin['phase']:<10} ${coin['volume']:<14,.1f}")

    print()
    return new_coins

def analyze_new_coin(symbol):
    """分析新币信号"""
    print("=" * 70)
    print(f"分析新币: {symbol}")
    print("=" * 70)

    try:
        result = analyze_symbol(symbol)

        # 新币信息
        age_days = result.get("coin_age_days", 0)
        phase = result.get("coin_phase", "unknown")
        is_new = result.get("is_new_coin", False)

        print(f"\n📊 币种信息：")
        print(f"   - 币龄: {age_days} 天")
        print(f"   - 阶段: {phase}")
        print(f"   - 新币: {'是' if is_new else '否'}")

        # 7维分数
        scores = result.get("scores", {})
        print(f"\n📈 7维分数（{result.get('side', '')}方向）：")
        for dim, score in scores.items():
            emoji = "🟢" if score >= 65 else ("🟡" if score >= 50 else "🔴")
            print(f"   {dim}: {emoji} {score:.0f}")

        # 概率
        prob = result.get("probability", 0)
        prob_pct = prob * 100

        print(f"\n🎯 信号质量：")
        print(f"   - 基础概率: {result.get('P_base', 0)*100:.1f}%")
        print(f"   - F调节器: {result.get('F_adjustment', 1.0):.2f}x")
        print(f"   - 最终概率: {prob_pct:.1f}%")

        # 发布判定
        pub = result.get("publish", {})
        is_prime = pub.get("prime", False)
        dims_ok = pub.get("dims_ok", 0)

        print(f"\n📣 发布判定：")
        if phase == "phaseA":
            print(f"   - 门槛: 65% + 5维>=65分 (阶段A)")
        elif phase == "phaseB":
            print(f"   - 门槛: 63% + 4维>=65分 (阶段B)")
        else:
            print(f"   - 门槛: 62% + 4维>=65分 (成熟币)")

        print(f"   - 达标维度: {dims_ok}/7")
        print(f"   - 结果: {'✅ Prime (发送)' if is_prime else '❌ 未达标'}")

        # 给价计划
        if is_prime:
            pricing = result.get("pricing", {})
            if pricing:
                print(f"\n💰 给价计划：")
                print(f"   - 入场: {pricing.get('entry_lo'):.4f} - {pricing.get('entry_hi'):.4f}")
                print(f"   - 止损: {pricing.get('sl'):.4f}")
                print(f"   - 止盈1: {pricing.get('tp1'):.4f}")
                print(f"   - 止盈2: {pricing.get('tp2'):.4f}")

        print()
        return result

    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    import argparse
    parser = argparse.ArgumentParser(description='新币识别测试工具')
    parser.add_argument('symbol', nargs='?', help='指定币种（可选）')
    parser.add_argument('--analyze', action='store_true', help='分析所有新币')

    args = parser.parse_args()

    if args.symbol:
        # 分析指定币种
        analyze_new_coin(args.symbol.upper())
    elif args.analyze:
        # 检测并分析所有新币
        new_coins = detect_new_coins()
        if new_coins:
            print("\n" + "=" * 70)
            print("开始分析新币...")
            print("=" * 70)
            for coin in new_coins[:5]:  # 最多分析5个
                analyze_new_coin(coin["symbol"])
                print()
    else:
        # 仅检测
        detect_new_coins()

if __name__ == '__main__':
    main()
