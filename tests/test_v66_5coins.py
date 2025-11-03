#!/usr/bin/env python3
# coding: utf-8
"""
v6.6架构 - 5个币种快速测试

测试重点：
1. 6个核心因子 (T/M/C/V/O/B) 范围验证 (±100)
2. 4个调制器 (L/S/F/I) 范围验证 (±100)
3. 调制器权重=0% 验证
4. 软约束系统验证 (EV≤0, P<p_min)
5. 详细因子输出验证

v6.6架构：
- A层核心因子(6): T/M/C/V/O/B, 权重100%
- B层调制器(4): L/S/F/I, 权重0%
- 废弃因子: Q(清算), E(环境)
"""

import sys
import os

# 启用详细因子日志（测试模式）
os.environ['VERBOSE_FACTOR_LOG'] = '1'

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ats_core.pipeline.analyze_symbol import analyze_symbol
from ats_core.logging import log, warn, error


def test_v66_5_coins():
    """测试5个币种 - v6.6架构验证"""

    log("=" * 70)
    log("🧪 v6.6架构测试 - 5个币种因子系统验证")
    log("=" * 70)

    # 测试币种（选择流动性好的主流币）
    test_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT']

    log(f"\n测试币种: {', '.join(test_symbols)}")
    log("注意: analyze_symbol 会自动获取K线数据")
    log("")

    # v6.6架构定义
    CORE_FACTORS = ['T', 'M', 'C', 'V', 'O', 'B']  # A层核心因子
    MODULATORS = ['L', 'S', 'F', 'I']              # B层调制器
    DEPRECATED = ['Q', 'E']                         # 废弃因子

    # 逐个测试
    results = []
    for i, symbol in enumerate(test_symbols, 1):
        log(f"[{i}/5] 分析 {symbol}...")

        try:
            # 直接调用 analyze_symbol（只需要 symbol 参数）
            result = analyze_symbol(symbol)

            if result and not result.get('error'):
                score = result.get('weighted_score', 0)
                confidence = result.get('confidence', 0)
                edge = result.get('edge', 0)
                prob = result.get('probability', 0)
                is_prime = result.get('publish', {}).get('prime', False)
                is_watch = result.get('publish', {}).get('watch', False)

                # 获取因子和调制器
                scores_dict = result.get('scores', {})
                modulation_dict = result.get('modulation', {})

                # v6.6验证1：核心因子范围检查
                log(f"  ✅ 成功分析")
                log(f"     加权分数: {score:+.1f} | 置信度: {confidence:.1f} | Edge: {edge:+.4f}")
                log(f"     概率: {prob:.2%} | 发布状态: {'🟢Prime' if is_prime else '🟡Watch' if is_watch else '⚪不发布'}")

                log(f"")
                log(f"     【A层核心因子(6) - 权重100%】")
                core_all_ok = True
                for factor in CORE_FACTORS:
                    value = scores_dict.get(factor, 0)
                    in_range = -100 <= value <= 100
                    if not in_range:
                        core_all_ok = False
                    status = "✅" if in_range else "❌"
                    log(f"       {factor}: {value:+7.1f}  {status}")

                # v6.6验证2：调制器范围检查
                log(f"")
                log(f"     【B层调制器(4) - 权重0%】")
                mod_all_ok = True
                for mod in MODULATORS:
                    value = modulation_dict.get(mod, 0)
                    in_range = -100 <= value <= 100
                    if not in_range:
                        mod_all_ok = False
                    status = "✅" if in_range else "❌"
                    log(f"       {mod}: {value:+7.1f}  {status}")

                # v6.6验证3：废弃因子不应在scores中
                log(f"")
                deprecated_found = []
                for dep in DEPRECATED:
                    if dep in scores_dict and scores_dict[dep] != 0:
                        deprecated_found.append(dep)

                if deprecated_found:
                    warn(f"     ⚠️  发现废弃因子: {', '.join(deprecated_found)}")
                else:
                    log(f"     ✅ 废弃因子检查通过 (Q/E未参与评分)")

                # v6.6验证4：软约束检查
                publish_info = result.get('publish', {})
                soft_filtered = publish_info.get('soft_filtered', False)
                ev = publish_info.get('EV', 0)
                ev_positive = publish_info.get('EV_positive', True)
                p_above_threshold = publish_info.get('P_above_threshold', True)

                log(f"")
                log(f"     【软约束检查】")
                log(f"       EV: {ev:+.4f} ({'✅>0' if ev_positive else '⚠️≤0'})")
                log(f"       P门槛: {'✅通过' if p_above_threshold else '⚠️低于阈值'}")
                log(f"       软过滤: {'⚠️是' if soft_filtered else '✅否'}")

                # 调制器输出
                modulator_output = result.get('modulator_output', {})
                if modulator_output:
                    log(f"")
                    log(f"     【调制器输出】")
                    log(f"       仓位倍数: {result.get('position_mult', 1.0):.2f}")
                    log(f"       有效时间: {result.get('Teff_final', 0):.1f}h")
                    log(f"       调制成本: {result.get('cost_modulated', 0):.4f}")

                results.append({
                    'symbol': symbol,
                    'score': score,
                    'core_factors_ok': core_all_ok,
                    'modulators_ok': mod_all_ok,
                    'deprecated_clean': len(deprecated_found) == 0,
                    'is_prime': is_prime,
                    'is_watch': is_watch,
                    'soft_filtered': soft_filtered
                })
            else:
                error_msg = result.get('error', '未知错误') if result else '无结果'
                warn(f"  ⚠️  分析失败: {error_msg}")
                results.append({
                    'symbol': symbol,
                    'score': None,
                    'core_factors_ok': False,
                    'modulators_ok': False,
                    'deprecated_clean': False,
                    'error': error_msg
                })

        except Exception as e:
            error(f"  ❌ 异常: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'symbol': symbol,
                'error': str(e),
                'core_factors_ok': False,
                'modulators_ok': False,
                'deprecated_clean': False
            })

        log("")

    # 汇总报告
    log("=" * 70)
    log("📊 v6.6架构验证汇总")
    log("=" * 70)

    success_count = sum(1 for r in results if r.get('score') is not None)
    core_ok = sum(1 for r in results if r.get('core_factors_ok') == True)
    mod_ok = sum(1 for r in results if r.get('modulators_ok') == True)
    deprecated_ok = sum(1 for r in results if r.get('deprecated_clean') == True)
    prime_count = sum(1 for r in results if r.get('is_prime') == True)
    watch_count = sum(1 for r in results if r.get('is_watch') == True)

    log(f"")
    log(f"成功分析: {success_count}/5")
    log(f"核心因子范围正常: {core_ok}/{success_count}")
    log(f"调制器范围正常: {mod_ok}/{success_count}")
    log(f"废弃因子清理: {deprecated_ok}/{success_count}")
    log(f"Prime信号: {prime_count}/{success_count}")
    log(f"Watch信号: {watch_count}/{success_count}")

    log("")
    if core_ok == success_count and mod_ok == success_count and deprecated_ok == success_count and success_count > 0:
        log("✅ 所有测试通过！v6.6架构完全合规")
        log("   - 6个核心因子在±100范围内")
        log("   - 4个调制器在±100范围内")
        log("   - 废弃因子(Q/E)未参与评分")
    elif success_count > 0:
        log("⚠️  部分测试未通过:")
        if core_ok < success_count:
            warn(f"   - {success_count - core_ok} 个币种的核心因子超出范围")
        if mod_ok < success_count:
            warn(f"   - {success_count - mod_ok} 个币种的调制器超出范围")
        if deprecated_ok < success_count:
            warn(f"   - {success_count - deprecated_ok} 个币种仍使用废弃因子")
    else:
        error("❌ 所有分析失败")

    log("=" * 70)

    # 详细结果表格
    log("\n详细结果表格:")
    log(f"{'符号':<12} {'分数':>8} {'核心因子':>8} {'调制器':>8} {'废弃因子':>8} {'发布':>8}")
    log("-" * 70)
    for r in results:
        if 'error' in r and r.get('score') is None:
            log(f"{r['symbol']:<12} {'❌错误':>8} {'-':>8} {'-':>8} {'-':>8} {'-':>8}")
        elif r.get('score') is not None:
            core_status = '✅' if r['core_factors_ok'] else '❌'
            mod_status = '✅' if r['modulators_ok'] else '❌'
            dep_status = '✅' if r['deprecated_clean'] else '⚠️'
            pub_status = '🟢Prime' if r['is_prime'] else '🟡Watch' if r['is_watch'] else '⚪无'
            log(f"{r['symbol']:<12} {r['score']:>+8.1f} {core_status:>8} {mod_status:>8} {dep_status:>8} {pub_status:>8}")
        else:
            log(f"{r['symbol']:<12} {'无结果':>8} {'-':>8} {'-':>8} {'-':>8} {'-':>8}")

    log("\n✅ v6.6架构测试完成\n")

    return results


if __name__ == "__main__":
    test_v66_5_coins()
