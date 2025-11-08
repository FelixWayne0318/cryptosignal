#!/usr/bin/env python3
# coding: utf-8
"""
测试完善的分析数据库

测试内容：
1. 数据库表创建
2. 写入市场数据、因子、信号、闸门、调制器
3. 查询和统计功能
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from ats_core.data.analysis_db import get_analysis_db
from ats_core.logging import log, error
import time


def test_database_creation():
    """测试1: 数据库创建"""
    log("\n" + "=" * 60)
    log("测试1: 数据库创建和表结构")
    log("=" * 60)

    try:
        db = get_analysis_db("data/test_analysis.db")
        log("✅ 数据库创建成功")
        log(f"   路径: data/test_analysis.db")
        return True
    except Exception as e:
        error(f"❌ 数据库创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_write_complete_signal():
    """测试2: 写入完整信号数据"""
    log("\n" + "=" * 60)
    log("测试2: 写入完整信号数据")
    log("=" * 60)

    try:
        db = get_analysis_db("data/test_analysis.db")

        # 构造测试数据（模拟analyze_with_v72_enhancements的输出）
        test_signal = {
            'timestamp': int(time.time() * 1000),
            'symbol': 'BTCUSDT',
            'price': 50000.0,
            'atr': 500.0,
            'atr_pct': 1.0,
            'volume_24h': 1000000000,

            # 因子分数
            'scores': {
                'MVRV': 60,
                'Prime': 70,
                'T': 80,
                'F': 40,
                'I': 65,
                'G': 50
            },

            # 加权分数
            'direction_score': 70,
            'quality_score': 50,
            'weighted_score': 66,
            'side': 'LONG',
            'side_long': True,

            # F因子细节
            'F_components': {
                'price_momentum': 50,
                'fund_momentum': 80,
                'divergence': 30
            },

            # I因子细节
            'I_components': {
                'beta_BTC': 0.3,
                'beta_ETH': 0.2,
                'beta_sum': 0.5,
                'alpha': 0.05,
                'R_squared': 0.6
            },

            'market_regime': 45,

            # 原始输出
            'probability': 0.520,
            'expected_value': 0.015,

            # v7.2增强
            'v72_enhancements': {
                'Teff_total': 1.15,
                'cost_eff_total': -1.5,
                'P_calibrated': 0.598,
                'EV_net': 0.0123,

                'modulators': {
                    'F': {
                        'Teff': 1.08,
                        'cost_eff': -0.8
                    },
                    'I': {
                        'Teff': 1.07,
                        'cost_eff': -0.7
                    }
                },

                # 闸门结果
                'all_gates_passed': True,
                'reject_reason': '',
                'gate_results': {
                    'gate1_data_quality': {
                        'passed': True,
                        'reason': 'data_ok(...)'
                    },
                    'gate2_fund_support': {
                        'passed': True,
                        'reason': 'fund_ok(F=40.0)',
                        'F_directional': 40
                    },
                    'gate3_market_risk': {
                        'passed': True,
                        'reason': 'market_ok(...)'
                    },
                    'gate4_execution_cost': {
                        'passed': True,
                        'reason': 'ev_ok(EV=0.0123>0.005)'
                    }
                },
                'adjusted_cost_bps': 3.5
            },

            'tp_pct': 0.03,
            'sl_pct': 0.015,
            'base_cost_bps': 5.0,
            'signal_strength': 'STRONG'
        }

        # 写入完整信号
        signal_id = db.write_complete_signal(test_signal)
        log(f"✅ 写入完整信号成功: {signal_id}")

        # 写入第二个信号（未通过闸门）
        test_signal2 = test_signal.copy()
        test_signal2['timestamp'] = int(time.time() * 1000) + 1000
        test_signal2['symbol'] = 'ETHUSDT'
        test_signal2['scores']['F'] = -85  # 极端F值，会被拒绝
        test_signal2['v72_enhancements']['all_gates_passed'] = False
        test_signal2['v72_enhancements']['reject_reason'] = 'extreme_fund_divergence(F=-85.0≤-80, 派发阶段)'
        test_signal2['v72_enhancements']['gate_results']['gate2_fund_support']['passed'] = False

        signal_id2 = db.write_complete_signal(test_signal2)
        log(f"✅ 写入第二个信号成功: {signal_id2}")

        return True

    except Exception as e:
        error(f"❌ 写入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_query_functions():
    """测试3: 查询功能"""
    log("\n" + "=" * 60)
    log("测试3: 查询和统计功能")
    log("=" * 60)

    try:
        db = get_analysis_db("data/test_analysis.db")

        # 查询时间范围内的信号
        now = int(time.time() * 1000)
        signals = db.get_signals_by_timerange(now - 3600000, now + 3600000)
        log(f"✅ 查询到 {len(signals)} 个信号")

        for sig in signals:
            status = "✅通过" if sig['gates_passed'] else "❌拒绝"
            log(f"   {sig['symbol']:10s} {sig['side']:5s} conf={sig['confidence']:5.1f} P={sig['probability']:.3f} {status}")

        # 查询因子分析
        factor_history = db.get_factor_analysis('BTCUSDT', limit=10)
        log(f"\n✅ 查询到 BTCUSDT 的 {len(factor_history)} 条因子记录")
        if factor_history:
            f = factor_history[0]
            log(f"   最新: MVRV={f['mvrv']:.0f} Prime={f['prime']:.0f} T={f['t']:.0f} F={f['f']:.0f} I={f['i']:.0f}")

        # 闸门统计
        gate_stats = db.get_gate_statistics()
        log(f"\n✅ 闸门统计:")
        log(f"   总信号: {gate_stats['total_signals']}")
        log(f"   全部通过率: {gate_stats['all_gates_pass_rate']*100:.1f}%")
        for i in range(1, 5):
            log(f"   闸门{i}通过率: {gate_stats[f'gate{i}_pass_rate']*100:.1f}%")

        if gate_stats.get('reject_distribution'):
            log(f"   拒绝分布: {gate_stats['reject_distribution']}")

        # 调制器影响统计
        mod_stats = db.get_modulator_impact_stats()
        log(f"\n✅ 调制器影响统计:")
        log(f"   F平均影响: {mod_stats['avg_f_impact_pct']:+.2f}%")
        log(f"   I平均影响: {mod_stats['avg_i_impact_pct']:+.2f}%")
        log(f"   总P变化: {mod_stats['avg_total_p_change_pct']:+.2f}%")
        log(f"   总EV变化: {mod_stats['avg_total_ev_change']:+.4f}")

        return True

    except Exception as e:
        error(f"❌ 查询失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_outcome_tracking():
    """测试4: 结果跟踪"""
    log("\n" + "=" * 60)
    log("测试4: 信号结果跟踪")
    log("=" * 60)

    try:
        db = get_analysis_db("data/test_analysis.db")

        # 模拟一个信号的实际结果
        outcome_data = {
            'timestamp': int(time.time() * 1000),
            'executed': True,
            'entry_price': 50000.0,
            'entry_time': int(time.time() * 1000),
            'outcome': 'WIN',
            'exit_price': 51500.0,
            'exit_time': int(time.time() * 1000) + 3600000,  # 1小时后
            'exit_reason': 'TP',
            'pnl_pct': 3.0,
            'pnl_usdt': 30.0,
            'hold_hours': 1.0,
            'actual_entry_cost_bps': 3.5,
            'actual_exit_cost_bps': 3.5,
            'funding_cost_bps': 0.5,
            'total_cost_bps': 7.5,
            'predicted_p': 0.598,
            'actual_win': True,
            'predicted_ev': 0.0123,
            'actual_ev': 0.0293,  # 3.0% - 0.075% = 2.93%
            'notes': '测试数据'
        }

        # 获取第一个信号ID
        now = int(time.time() * 1000)
        signals = db.get_signals_by_timerange(now - 3600000, now + 3600000)
        if signals:
            signal_id = signals[0]['signal_id']
            db.update_signal_outcome(signal_id, outcome_data)
            log(f"✅ 更新信号结果成功: {signal_id}")
            log(f"   结果: {outcome_data['outcome']}")
            log(f"   收益: {outcome_data['pnl_pct']}%")
            log(f"   预测P: {outcome_data['predicted_p']:.3f} 实际赢: {outcome_data['actual_win']}")
            log(f"   预测EV: {outcome_data['predicted_ev']:.4f} 实际EV: {outcome_data['actual_ev']:.4f}")
        else:
            log("⚠️  没有找到信号，跳过结果跟踪测试")

        return True

    except Exception as e:
        error(f"❌ 结果跟踪失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    log("\n" + "=" * 60)
    log("🧪 完善分析数据库测试套件")
    log("=" * 60)

    results = []

    # 测试1: 数据库创建
    results.append(("数据库创建", test_database_creation()))

    # 测试2: 写入完整信号
    results.append(("写入完整信号", test_write_complete_signal()))

    # 测试3: 查询功能
    results.append(("查询功能", test_query_functions()))

    # 测试4: 结果跟踪
    results.append(("结果跟踪", test_outcome_tracking()))

    # 总结
    log("\n" + "=" * 60)
    log("📊 测试总结")
    log("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        log(f"{status}: {name}")

    log(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        log("\n✅ 所有测试通过！完善的分析数据库工作正常。")
    else:
        log("\n⚠️ 部分测试失败，请检查错误信息")

    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
