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

    # 创建扫描器
    scanner = OptimizedBatchScanner(
        min_score=60,  # 降低阈值以便看到结果
        enable_websocket=False,  # 禁用WebSocket
        enable_telegram=False   # 禁用Telegram通知
    )

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
                L_score = result.get('scores', {}).get('L', 0)
                L_meta = result.get('scores_meta', {}).get('L', {})

                log(f"  ✅ 成功")
                log(f"     分数: {score:.1f}, 概率: {prob:.2%}, Prime: {is_prime}")
                log(f"     L因子: {L_score} (范围检查: {'✅' if -100 <= L_score <= 100 else '❌ 超出范围'})")

                # 检查L因子元数据
                if 'liquidity_score' in L_meta:
                    log(f"     流动性分数: {L_meta['liquidity_score']}")
                    log(f"     流动性等级: {L_meta.get('liquidity_level', 'N/A')}")

                results.append({
                    'symbol': symbol,
                    'score': score,
                    'L_factor': L_score,
                    'L_in_range': -100 <= L_score <= 100
                })
            else:
                warn(f"  ⚠️  无结果")
                results.append({
                    'symbol': symbol,
                    'score': None,
                    'L_factor': None,
                    'L_in_range': None
                })

        except Exception as e:
            error(f"  ❌ 失败: {e}")
            results.append({
                'symbol': symbol,
                'error': str(e),
                'L_in_range': False
            })

        log("")

    # 汇总报告
    log("=" * 60)
    log("📊 测试汇总")
    log("=" * 60)

    success_count = sum(1 for r in results if r.get('score') is not None)
    l_factor_ok = sum(1 for r in results if r.get('L_in_range') == True)

    log(f"成功分析: {success_count}/5")
    log(f"L因子正常: {l_factor_ok}/{success_count}")

    if l_factor_ok == success_count and success_count > 0:
        log("")
        log("✅ 所有测试通过！L因子范围验证正常")
    elif success_count > 0:
        log("")
        warn(f"⚠️  部分L因子超出范围")
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
            log(f"  {r['symbol']}: 分数={r['score']:.1f}, L={r['L_factor']}, 范围={'✅' if r['L_in_range'] else '❌'}")
        else:
            log(f"  {r['symbol']}: 无结果")


if __name__ == "__main__":
    asyncio.run(test_5_coins())
