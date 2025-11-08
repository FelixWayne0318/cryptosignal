#!/usr/bin/env python3
# coding: utf-8
"""
测试v7.2集成和数据采集

功能:
1. 测试TradeRecorder数据库创建
2. 测试v7.2扫描器（不发送Telegram）
3. 验证数据记录
4. 显示统计信息
"""

import sys
import asyncio
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from ats_core.data.trade_recorder import get_recorder
from ats_core.logging import log, error


def test_trade_recorder():
    """测试1: TradeRecorder基础功能"""
    log("\n" + "=" * 60)
    log("测试1: TradeRecorder基础功能")
    log("=" * 60)

    try:
        # 初始化recorder
        recorder = get_recorder("data/test_trade_history.db")
        log("✅ TradeRecorder初始化成功")

        # 创建测试信号
        test_signal = {
            "symbol": "BTCUSDT_TEST",
            "timestamp": 1699364400000,
            "side": "long",
            "weighted_score": 65.5,
            "scores": {
                "T": 70,
                "M": 60,
                "C": 65,
                "V": 55,
                "O": 58,
                "B": 15,
                "I": 55
            },
            "v72_enhancements": {
                "F_v2": 94,
                "group_scores": {
                    "TC": 78.5,
                    "VOM": 63.5,
                    "B": 20
                },
                "confidence_v72": 65.5,
                "P_calibrated": 0.630,
                "EV_net": 0.0128,
                "gate_results": {
                    "gate1": {"pass": True, "bars": 200},
                    "gate2": {"pass": True, "F_directional": 94},
                    "gate3": {"pass": True},
                    "gate4": {"pass": True}
                },
                "all_gates_passed": True
            },
            "price": 95234.50,
            "atr": 750.0,
            "market_regime": -15,
            "tp_pct": 0.03,
            "sl_pct": 0.015
        }

        # 记录信号
        signal_id = recorder.record_signal_snapshot(test_signal)
        log(f"✅ 测试信号已记录: {signal_id}")

        # 获取统计
        stats = recorder.get_statistics()
        log(f"✅ 数据库统计:")
        log(f"   总信号数: {stats['total_signals']}")
        log(f"   通过闸门: {stats['gates_passed']}")

        # 获取最近信号
        recent = recorder.get_recent_signals(limit=5)
        log(f"✅ 最近{len(recent)}个信号:")
        for sig in recent:
            log(f"   {sig['symbol']:15s} {sig['side']:5s} conf={sig['confidence']:5.1f} P={sig['predicted_p']:.3f}")

        log("\n✅ TradeRecorder测试通过")
        return True

    except Exception as e:
        error(f"❌ TradeRecorder测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_v72_scanner():
    """测试2: v7.2扫描器（小规模测试）"""
    log("\n" + "=" * 60)
    log("测试2: v7.2扫描器（小规模测试）")
    log("=" * 60)

    try:
        # 动态导入（避免在测试1失败时导入）
        from scripts.realtime_signal_scanner_v72 import RealtimeSignalScannerV72

        # 创建扫描器（不发送Telegram，但记录数据）
        scanner = RealtimeSignalScannerV72(
            min_score=35,
            send_telegram=False,  # 测试时不发送
            record_data=True,     # 记录数据
            verbose=True
        )

        log("✅ v7.2扫描器创建成功")

        # 执行一次扫描（只扫描5个币种进行测试）
        log("开始扫描5个币种...")
        await scanner.scan_once(max_symbols=5)

        log("✅ v7.2扫描测试完成")

        # 显示统计
        scanner.show_statistics()

        return True

    except ImportError as e:
        error(f"❌ 导入失败: {e}")
        error("请确保所有v7.2模块都已正确安装")
        return False
    except Exception as e:
        error(f"❌ v7.2扫描器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_access():
    """测试3: 数据访问和查询"""
    log("\n" + "=" * 60)
    log("测试3: 数据访问和查询")
    log("=" * 60)

    try:
        import sqlite3

        # 连接数据库
        db_path = "data/trade_history.db"
        if not Path(db_path).exists():
            log(f"⚠️ 数据库不存在: {db_path}")
            log("请先运行扫描器积累数据")
            return True

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 查询总信号数
        cursor.execute("SELECT COUNT(*) FROM signal_snapshots")
        total = cursor.fetchone()[0]
        log(f"✅ 总信号数: {total}")

        # 查询通过闸门的信号
        cursor.execute("SELECT COUNT(*) FROM signal_snapshots WHERE all_gates_passed = 1")
        gates_passed = cursor.fetchone()[0]
        log(f"✅ 通过闸门: {gates_passed} ({gates_passed/total*100:.1f}%)" if total > 0 else "✅ 通过闸门: 0")

        # 查询不同confidence区间的分布
        cursor.execute("""
        SELECT
            CAST(confidence / 10 AS INT) * 10 AS bucket,
            COUNT(*) AS count
        FROM signal_snapshots
        WHERE all_gates_passed = 1
        GROUP BY bucket
        ORDER BY bucket DESC
        """)

        log(f"✅ Confidence分布:")
        for row in cursor.fetchall():
            bucket = row[0]
            count = row[1]
            log(f"   {bucket}-{bucket+10}: {count}个信号")

        # 查询多空分布
        cursor.execute("""
        SELECT side, COUNT(*) as count
        FROM signal_snapshots
        WHERE all_gates_passed = 1
        GROUP BY side
        """)

        log(f"✅ 多空分布:")
        for row in cursor.fetchall():
            log(f"   {row[0]}: {row[1]}个")

        conn.close()

        log("\n✅ 数据访问测试通过")
        return True

    except Exception as e:
        error(f"❌ 数据访问测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试流程"""
    log("=" * 60)
    log("🧪 v7.2集成测试套件")
    log("=" * 60)

    results = []

    # 测试1: TradeRecorder
    result1 = test_trade_recorder()
    results.append(("TradeRecorder基础功能", result1))

    # 测试2: v7.2扫描器（可选，因为需要网络和API）
    try:
        result2 = await test_v72_scanner()
        results.append(("v7.2扫描器", result2))
    except Exception as e:
        error(f"v7.2扫描器测试跳过: {e}")
        results.append(("v7.2扫描器", False))

    # 测试3: 数据访问
    result3 = test_data_access()
    results.append(("数据访问和查询", result3))

    # 总结
    log("\n" + "=" * 60)
    log("📊 测试总结")
    log("=" * 60)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        log(f"{status}: {name}")

    passed = sum(1 for _, r in results if r)
    total = len(results)

    log(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        log("\n🎉 所有测试通过！v7.2集成就绪")
        return 0
    else:
        log("\n⚠️ 部分测试失败，请检查错误信息")
        return 1


if __name__ == '__main__':
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        log("\n⚠️ 测试被中断")
        sys.exit(1)
    except Exception as e:
        error(f"测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
