#!/usr/bin/env python3
# coding: utf-8
"""
P0 Bug Fix Validation Script
验证回测0信号问题的修复

Usage:
    python3 scripts/validate_p0_fix.py

This script:
1. Validates config changes (min_final_strength: 20.0 → 5.0)
2. Runs a quick backtest (1 week, 1 symbol)
3. Verifies signals are now generated
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ats_core.cfg import CFG
from ats_core.backtest import HistoricalDataLoader, BacktestEngine, BacktestMetrics


def validate_config():
    """验证配置修改"""
    print("="*70)
    print("Step 1: 验证配置修改")
    print("="*70)

    params = CFG.params
    step1_cfg = params.get("four_step_system", {}).get("step1_direction", {})
    min_strength = step1_cfg.get("min_final_strength")

    print(f"\n✓ Config Path: four_step_system.step1_direction.min_final_strength")
    print(f"✓ Current Value: {min_strength}")

    if min_strength == 5.0:
        print(f"✅ SUCCESS: Threshold updated to 5.0 (was 20.0)")
        return True
    elif min_strength == 20.0:
        print(f"❌ FAILED: Still using old threshold 20.0!")
        return False
    else:
        print(f"⚠️  WARNING: Unexpected value {min_strength}")
        return False


def run_quick_backtest():
    """运行快速回测验证"""
    print("\n" + "="*70)
    print("Step 2: 运行快速回测 (1周数据)")
    print("="*70)

    # Setup - convert to timestamps (milliseconds)
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=7)

    # Convert to timestamp (milliseconds)
    end_time = int(end_dt.timestamp() * 1000)
    start_time = int(start_dt.timestamp() * 1000)
    symbols = ["ETHUSDT"]

    print(f"\n配置:")
    print(f"  Symbol: {symbols[0]}")
    print(f"  Period: {start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')}")
    print(f"  Interval: 1h")

    try:
        # Initialize components
        print("\n初始化回测组件...")
        data_loader = HistoricalDataLoader(CFG.params.get("backtest", {}).get("data_loader", {}))
        engine = BacktestEngine(CFG.params.get("backtest", {}).get("engine", {}), data_loader)

        # Run backtest
        print("运行回测...")
        result = engine.run(
            symbols=symbols,
            start_time=start_time,
            end_time=end_time
        )

        # Check results
        signal_count = len(result.signals)
        print(f"\n回测结果:")
        print(f"  Total Signals: {signal_count}")

        if signal_count > 0:
            print(f"✅ SUCCESS: 生成了 {signal_count} 个信号 (修复前为0)")

            # Show sample signal
            sample = result.signals[0]
            print(f"\n示例信号:")
            print(f"  Symbol: {sample.symbol}")
            print(f"  Direction: {sample.direction}")
            print(f"  Entry Price: {sample.entry_price:.2f}")
            print(f"  Final Strength: {sample.metadata.get('final_strength', 'N/A'):.2f}")

            return True
        else:
            print(f"⚠️  WARNING: 仍然是0个信号，可能需要更长时间段或其他符号")
            return False

    except Exception as e:
        print(f"\n❌ 回测失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "="*70)
    print("P0 Bug Fix Validation - CryptoSignal v7.4.2")
    print("问题: 回测产生0个信号 (min_final_strength过高)")
    print("修复: config/params.json - min_final_strength: 20.0 → 5.0")
    print("="*70 + "\n")

    # Step 1: Validate config
    config_ok = validate_config()
    if not config_ok:
        print("\n❌ 配置验证失败，请检查config/params.json")
        sys.exit(1)

    # Step 2: Run quick backtest
    backtest_ok = run_quick_backtest()

    # Final summary
    print("\n" + "="*70)
    print("验证总结")
    print("="*70)
    print(f"✓ Config Update: {'✅ PASS' if config_ok else '❌ FAIL'}")
    print(f"✓ Backtest Test: {'✅ PASS' if backtest_ok else '⚠️  WARN'}")

    if config_ok and backtest_ok:
        print("\n✅ P0 修复验证成功！建议运行完整回测:")
        print("   ./RUN_BACKTEST.sh")
    elif config_ok:
        print("\n✅ 配置修复成功，建议运行更长时间段的回测:")
        print("   python3 scripts/backtest_four_step.py --symbols ETHUSDT --start 2024-10-01 --end 2024-11-01")
    else:
        print("\n❌ 修复验证失败，请检查配置")
        sys.exit(1)


if __name__ == "__main__":
    main()
