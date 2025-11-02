#!/usr/bin/env python3
# coding: utf-8
"""
快速测试5个币种 - 直接测试 analyze_symbol 函数
不加载市场数据，只测试核心分析逻辑
"""

import sys
import os
import json

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ats_core.pipeline.analyze_symbol import analyze_symbol
from ats_core.api.binance_client import BinanceClient
from ats_core.logging import log, warn, error


def load_params():
    """加载配置参数"""
    try:
        with open('config/params.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        error(f"加载配置失败: {e}")
        return {}


async def test_5_coins():
    """测试5个币种"""

    log("=" * 60)
    log("🧪 快速测试 - 5个币种因子范围验证")
    log("=" * 60)

    # 测试币种
    test_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT']

    # 加载配置
    params = load_params()
    if not params:
        error("无法加载配置，退出测试")
        return

    # 初始化客户端
    log("\n初始化Binance客户端...")
    client = BinanceClient()
    await client.initialize()
    log("✅ 客户端初始化完成")

    log(f"\n测试币种: {', '.join(test_symbols)}")
    log("注意: 只测试K线分析，不加载订单簿等额外数据")
    log("")

    # 逐个测试
    results = []
    for i, symbol in enumerate(test_symbols, 1):
        log(f"[{i}/5] 分析 {symbol}...")

        try:
            # 直接调用 analyze_symbol（不传orderbook等可选参数）
            result = await analyze_symbol(
                symbol=symbol,
                client=client,
                params=params,
                # 不传这些可选参数，加快测试速度
                # orderbook=None,
                # mark_price=None,
                # spot_price=None,
                # funding_rate=None,
                # oi_data=None,
                # agg_trades=None
            )

            if result:
                score = result.get('weighted_score', 0)
                prob = result.get('probability', 0)
                is_prime = result.get('publish', {}).get('prime', False)

                # 获取因子
                scores_dict = result.get('scores', {})
                L_score = scores_dict.get('L', 0)

                log(f"  ✅ 成功")
                log(f"     加权分数: {score:.1f}")
                log(f"     概率: {prob:.2%}")
                log(f"     Prime: {is_prime}")
                log(f"     L因子: {L_score} (范围: {'✅ 正常' if -100 <= L_score <= 100 else '❌ 超出±100'})")

                # 显示所有因子并检查范围
                log(f"     所有因子范围检查:")
                all_in_range = True
                for factor in ['T', 'M', 'C', 'S', 'V', 'O', 'L', 'B', 'Q']:
                    value = scores_dict.get(factor, 0)
                    in_range = -100 <= value <= 100
                    if not in_range:
                        all_in_range = False
                    status = "✅" if in_range else "❌"
                    log(f"       {factor}: {value:+7.1f}  {status}")

                results.append({
                    'symbol': symbol,
                    'score': score,
                    'L_factor': L_score,
                    'all_factors_ok': all_in_range
                })
            else:
                warn(f"  ⚠️  无结果")
                results.append({
                    'symbol': symbol,
                    'score': None,
                    'all_factors_ok': False
                })

        except Exception as e:
            error(f"  ❌ 失败: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'symbol': symbol,
                'error': str(e),
                'all_factors_ok': False
            })

        log("")

    # 汇总报告
    log("=" * 60)
    log("📊 测试汇总")
    log("=" * 60)

    success_count = sum(1 for r in results if r.get('score') is not None)
    all_factors_ok = sum(1 for r in results if r.get('all_factors_ok') == True)

    log(f"成功分析: {success_count}/5")
    log(f"因子范围正常: {all_factors_ok}/{success_count}")

    if all_factors_ok == success_count and success_count > 0:
        log("")
        log("✅ 所有测试通过！所有因子在±100范围内")
    elif success_count > 0:
        log("")
        warn(f"⚠️  有 {success_count - all_factors_ok} 个币种的因子超出范围")
    else:
        log("")
        error("❌ 所有分析失败")

    log("=" * 60)

    # 详细结果
    log("\n详细结果:")
    for r in results:
        if 'error' in r:
            log(f"  {r['symbol']}: ❌ {r['error']}")
        elif r['score'] is not None:
            log(f"  {r['symbol']}: 分数={r['score']:+6.1f}, L={r['L_factor']:+6.1f}, 范围={'✅' if r['all_factors_ok'] else '❌'}")
        else:
            log(f"  {r['symbol']}: 无结果")

    await client.close()
    log("\n✅ 测试完成")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_5_coins())
