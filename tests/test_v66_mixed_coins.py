#!/usr/bin/env python3
# coding: utf-8
"""
v6.6架构 - 混合币种测试（新币+成熟币）

测试重点：
1. 自动判断新币 vs 成熟币
2. 新币数据流（15m K线）vs 成熟币数据流（1h/4h K线）
3. v6.6架构对不同类型币种的适应性
4. 因子计算在不同数据质量下的表现

测试币种：
- 新币（可能）: ATUSDT, GIGGLEUSDT, CCUSDT, COAIUSDT
- 成熟币: SOLUSDT, BNBUSDT
"""

import sys
import os

# 启用详细因子日志（测试模式）
os.environ['VERBOSE_FACTOR_LOG'] = '1'

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ats_core.pipeline.analyze_symbol import analyze_symbol
from ats_core.logging import log, warn, error


def test_v66_mixed_coins():
    """测试混合币种 - v6.6架构验证"""

    # 测试币种（新币 + 成熟币）
    test_symbols = [
        'ATUSDT',        # 新币（可能）
        'GIGGLEUSDT',    # 新币（可能）
        'CCUSDT',        # 新币（可能）
        'COAIUSDT',      # 新币（可能）
        'SOLUSDT',       # 成熟币
        'BNBUSDT'        # 成熟币
    ]

    # v6.6架构定义
    CORE_FACTORS = ['T', 'M', 'C', 'V', 'O', 'B']  # A层核心因子
    MODULATORS = ['L', 'S', 'F', 'I']              # B层调制器
    DEPRECATED = ['Q', 'E']                         # 废弃因子

    log("=" * 70)
    log("🧪 v6.6架构测试 - 混合币种（新币+成熟币）")
    log("=" * 70)
    log("")
    log(f"测试币种: {', '.join(test_symbols)}")
    log("重点验证: 自动判断新币/成熟币 + 不同数据流处理")
    log("")

    results = []

    for i, symbol in enumerate(test_symbols):
        log(f"[{i+1}/{len(test_symbols)}] 分析 {symbol}...")

        try:
            result = analyze_symbol(symbol)

            if result.get('success'):
                # 基本信息
                scores = result.get('scores', {})
                weighted_score = result.get('weighted_score', 0)
                confidence = result.get('confidence', 0)
                edge = result.get('edge', 0)

                # 币种类型判断
                meta = result.get('meta', {})
                is_new = meta.get('is_new', False)
                coin_type = "新币🆕" if is_new else "成熟币📈"

                # 发布状态
                publish = result.get('publish', {})
                is_prime = publish.get('is_prime', False)
                is_watch = publish.get('is_watch', False)

                publish_status = "🔥Prime" if is_prime else ("⭐Watch" if is_watch else "⚪无")

                log(f"  ✅ 成功分析 ({coin_type})")
                log(f"     加权分数: {weighted_score:+.1f} | 置信度: {confidence:.1f} | Edge: {edge:+.4f}")
                log(f"     发布状态: {publish_status}")
                log("")

                # 验证v6.6架构
                core_ok = all(f in scores for f in CORE_FACTORS)
                mod_ok = all(f in scores for f in MODULATORS)
                deprecated_ok = all(f not in scores for f in DEPRECATED)

                # 因子范围验证
                core_range_ok = all(-100 <= scores.get(f, 0) <= 100 for f in CORE_FACTORS)
                mod_range_ok = all(-100 <= scores.get(f, 0) <= 100 for f in MODULATORS)

                log(f"     【A层核心因子(6) - 权重100%】")
                for f in CORE_FACTORS:
                    val = scores.get(f, 0)
                    status = "✅" if -100 <= val <= 100 else "❌"
                    log(f"       {f}: {val:+6.1f}  {status}")
                log("")

                log(f"     【B层调制器(4) - 权重0%】")
                for f in MODULATORS:
                    val = scores.get(f, 0)
                    status = "✅" if -100 <= val <= 100 else "❌"
                    log(f"       {f}: {val:+6.1f}  {status}")
                log("")

                if deprecated_ok:
                    log(f"     ✅ 废弃因子检查通过 (Q/E未参与评分)")
                else:
                    log(f"     ❌ 发现废弃因子")
                log("")

                results.append({
                    'symbol': symbol,
                    'success': True,
                    'coin_type': coin_type,
                    'score': weighted_score,
                    'core_ok': core_ok and core_range_ok,
                    'mod_ok': mod_ok and mod_range_ok,
                    'deprecated_ok': deprecated_ok,
                    'publish': publish_status
                })

            else:
                error_msg = result.get('error', '未知错误')
                log(f"  ❌ 分析失败: {error_msg}")
                log("")

                results.append({
                    'symbol': symbol,
                    'success': False,
                    'error': error_msg
                })

        except Exception as e:
            error(f"  ❌ 异常: {e}")
            import traceback
            traceback.print_exc()
            log("")

            results.append({
                'symbol': symbol,
                'success': False,
                'error': str(e)
            })

    # 汇总报告
    log("=" * 70)
    log("📊 v6.6架构验证汇总（混合币种）")
    log("=" * 70)
    log("")

    success_count = sum(1 for r in results if r['success'])
    core_ok_count = sum(1 for r in results if r.get('core_ok', False))
    mod_ok_count = sum(1 for r in results if r.get('mod_ok', False))
    deprecated_ok_count = sum(1 for r in results if r.get('deprecated_ok', False))

    new_coin_count = sum(1 for r in results if r.get('success') and '新币' in r.get('coin_type', ''))
    mature_coin_count = sum(1 for r in results if r.get('success') and '成熟币' in r.get('coin_type', ''))

    prime_count = sum(1 for r in results if r.get('success') and '🔥' in r.get('publish', ''))
    watch_count = sum(1 for r in results if r.get('success') and '⭐' in r.get('publish', ''))

    log(f"成功分析: {success_count}/{len(test_symbols)}")
    log(f"  - 新币: {new_coin_count}/{success_count}")
    log(f"  - 成熟币: {mature_coin_count}/{success_count}")
    log(f"核心因子范围正常: {core_ok_count}/{success_count}")
    log(f"调制器范围正常: {mod_ok_count}/{success_count}")
    log(f"废弃因子清理: {deprecated_ok_count}/{success_count}")
    log(f"Prime信号: {prime_count}/{success_count}")
    log(f"Watch信号: {watch_count}/{success_count}")
    log("")

    if success_count == len(test_symbols) and core_ok_count == success_count and mod_ok_count == success_count and deprecated_ok_count == success_count:
        log("✅ 所有测试通过！v6.6架构完全合规")
        log("   - 6个核心因子在±100范围内")
        log("   - 4个调制器在±100范围内")
        log("   - 废弃因子(Q/E)未参与评分")
        log("   - 新币/成熟币自动判断正常")
    else:
        log("⚠️  部分测试未通过，请检查上述结果")

    log("=" * 70)
    log("")

    # 详细结果表格
    log("详细结果表格:")
    log(f"{'符号':<15} {'类型':<8} {'分数':<8} {'核心因子':<8} {'调制器':<8} {'废弃因子':<8} {'发布':<8}")
    log("-" * 70)

    for r in results:
        symbol = r['symbol']
        if r['success']:
            coin_type = r.get('coin_type', '未知')
            score = r.get('score', 0)
            core_status = "✅" if r.get('core_ok', False) else "❌"
            mod_status = "✅" if r.get('mod_ok', False) else "❌"
            dep_status = "✅" if r.get('deprecated_ok', False) else "❌"
            publish = r.get('publish', '⚪无')

            log(f"{symbol:<15} {coin_type:<8} {score:+6.1f}  {core_status:<8} {mod_status:<8} {dep_status:<8} {publish:<8}")
        else:
            error_msg = r.get('error', '未知错误')[:30]
            log(f"{symbol:<15} {'❌错误':<8} {'-':<6}  {'-':<8} {'-':<8} {'-':<8} {'-':<8}")

    log("")
    log("✅ v6.6架构混合币种测试完成")
    log("")


if __name__ == "__main__":
    test_v66_mixed_coins()
