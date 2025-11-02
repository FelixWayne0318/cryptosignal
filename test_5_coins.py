#!/usr/bin/env python3
# coding: utf-8
"""
快速测试5个币种 - 验证分析系统修复
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ats_core.pipeline.batch_scan_optimized import OptimizedBatchScanner
from ats_core.logging import log, warn, error


async def test_5_coins():
    """测试5个币种"""

    log("=" * 60)
    log("🧪 快速测试 - 5个币种分析验证")
    log("=" * 60)

    # 创建扫描器（不接受参数）
    scanner = OptimizedBatchScanner()

    # 初始化
    log("\n初始化扫描器...")
    await scanner.initialize()

    # 获取前5个币种
    test_symbols = scanner.symbols[:5]

    log(f"\n测试币种: {', '.join(test_symbols)}")
    log("")

    # 逐个测试
    results = []
    for i, symbol in enumerate(test_symbols, 1):
        log(f"[{i}/5] 分析 {symbol}...")

        try:
            result = await scanner.analyze_single_symbol(symbol)

            if result:
                score = result.get('weighted_score', 0)
                prob = result.get('probability', 0)
                is_prime = result.get('publish', {}).get('prime', False)

                # 获取L因子验证
                scores_dict = result.get('scores', {})
                L_score = scores_dict.get('L', 0)
                L_meta = result.get('scores_meta', {}).get('L', {})

                log(f"  ✅ 成功")
                log(f"     加权分数: {score:.1f}")
                log(f"     概率: {prob:.2%}")
                log(f"     Prime: {is_prime}")
                log(f"     L因子: {L_score} (范围检查: {'✅ 正常' if -100 <= L_score <= 100 else '❌ 超出±100范围'})")

                # 显示所有因子
                log(f"     所有因子:")
                for factor, value in scores_dict.items():
                    in_range = -100 <= value <= 100
                    status = "✅" if in_range else "❌"
                    log(f"       {factor}: {value:+4.0f} {status}")

                # 检查L因子元数据
                if 'liquidity_score' in L_meta:
                    log(f"     流动性等级: {L_meta.get('liquidity_level', 'N/A')}")

                results.append({
                    'symbol': symbol,
                    'score': score,
                    'L_factor': L_score,
                    'all_factors_ok': all(-100 <= v <= 100 for v in scores_dict.values())
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
        warn(f"⚠️  部分因子超出范围")
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
            log(f"  {r['symbol']}: 分数={r['score']:.1f}, L={r['L_factor']}, 范围={'✅' if r['all_factors_ok'] else '❌'}")
        else:
            log(f"  {r['symbol']}: 无结果")


if __name__ == "__main__":
    asyncio.run(test_5_coins())
