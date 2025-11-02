#!/usr/bin/env python3
# coding: utf-8
"""
Phase 2测试脚本

测试新币数据获取功能：
1. 快速预判（新币 vs 成熟币）
2. 新币数据获取（1m/5m/15m/1h + AVWAP）
3. analyze_symbol集成测试
"""

import sys
from ats_core.data_feeds import (
    quick_newcoin_check,
    fetch_newcoin_data,
    fetch_standard_data,
)
from ats_core.pipeline.analyze_symbol import analyze_symbol
from ats_core.logging import log, warn


def test_quick_newcoin_check(symbol: str):
    """测试快速预判功能"""
    print(f"\n{'='*60}")
    print(f"测试1: 快速预判 - {symbol}")
    print('='*60)

    is_new, listing_time, bars_approx = quick_newcoin_check(symbol)

    print(f"结果:")
    print(f"  是否为新币: {'✅ 是' if is_new else '❌ 否'}")
    print(f"  上币时间: {listing_time if listing_time else '未知'}")
    print(f"  预估bars_1h: {bars_approx}")

    return is_new


def test_fetch_data(symbol: str, is_new_coin: bool):
    """测试数据获取功能"""
    print(f"\n{'='*60}")
    print(f"测试2: 数据获取 - {symbol} ({'新币' if is_new_coin else '成熟币'})")
    print('='*60)

    if is_new_coin:
        data = fetch_newcoin_data(symbol)
        print(f"新币数据:")
        print(f"  k1m: {len(data['k1m'])}根")
        print(f"  k5m: {len(data['k5m'])}根")
        print(f"  k15m: {len(data['k15m'])}根")
        print(f"  k1h: {len(data['k1h'])}根")
        print(f"  AVWAP: {data['avwap']:.2f}")
        print(f"  AVWAP方法: {data['avwap_meta']['method']}")
    else:
        data = fetch_standard_data(symbol)
        print(f"成熟币数据:")
        print(f"  k1h: {len(data['k1h'])}根")
        print(f"  k4h: {len(data['k4h'])}根")


def test_analyze_symbol(symbol: str):
    """测试完整分析流程（含Phase 2集成）"""
    print(f"\n{'='*60}")
    print(f"测试3: 完整分析流程 - {symbol}")
    print('='*60)

    try:
        result = analyze_symbol(symbol)

        # 检查新币元数据
        newcoin_meta = result.get("metadata", {}).get("newcoin_data", {})

        print(f"分析结果:")
        print(f"  是否为新币: {'✅ 是' if newcoin_meta.get('is_new_coin') else '❌ 否'}")

        if newcoin_meta.get('is_new_coin'):
            print(f"  新币数据:")
            print(f"    bars_1h: {newcoin_meta.get('bars_1h')}")
            print(f"    AVWAP: {newcoin_meta.get('avwap', 0):.2f}")
            print(f"    k1m数量: {newcoin_meta.get('k1m_count')}")
            print(f"    k5m数量: {newcoin_meta.get('k5m_count')}")
            print(f"    k15m数量: {newcoin_meta.get('k15m_count')}")

        print(f"\n  信号判定:")
        print(f"    is_prime: {result.get('is_prime')}")
        print(f"    prime_strength: {result.get('prime_strength', 0):.1f}")
        print(f"    coin_phase: {result.get('coin_phase')}")
        print(f"    probability: {result.get('probability', 0):.3f}")

        print(f"\n✅ 测试通过")
        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    if len(sys.argv) < 2:
        print("用法: python test_phase2.py SYMBOL1 [SYMBOL2 ...]")
        print("\n示例:")
        print("  # 测试新币（假设BTCUSDT为成熟币，需手动替换实际新币）")
        print("  python test_phase2.py BTCUSDT")
        print("\n  # 同时测试多个币种")
        print("  python test_phase2.py BTCUSDT ETHUSDT")
        sys.exit(1)

    symbols = sys.argv[1:]

    print(f"Phase 2功能测试")
    print(f"测试币种: {', '.join(symbols)}")

    all_passed = True

    for symbol in symbols:
        print(f"\n{'#'*60}")
        print(f"# 币种: {symbol}")
        print(f"{'#'*60}")

        try:
            # 测试1: 快速预判
            is_new = test_quick_newcoin_check(symbol)

            # 测试2: 数据获取
            test_fetch_data(symbol, is_new)

            # 测试3: 完整分析流程
            passed = test_analyze_symbol(symbol)

            if not passed:
                all_passed = False

        except Exception as e:
            print(f"❌ {symbol} 测试失败: {e}")
            import traceback
            traceback.print_exc()
            all_passed = False

    print(f"\n{'='*60}")
    print(f"测试总结")
    print('='*60)
    if all_passed:
        print("✅ 所有测试通过")
        sys.exit(0)
    else:
        print("❌ 部分测试失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
