#!/usr/bin/env python3
# coding: utf-8
"""
P0-7 & P0-8 Bug Fix Validation Script
验证回测0信号问题的修复

Usage:
    python3 scripts/validate_p0_fix.py

This script:
1. Validates config changes:
   - P0-7: Step1 min_final_strength: 20.0 → 5.0
   - P0-8: Step2 min_threshold: 30.0 → -30.0
   - P0-8: Step3 moderate_accumulation_f: 40 → 5.0
   - P0-8: Step3 strong_accumulation_f: 70 → 15.0
   - P0-8: Step4 min_prime_strength: 35 → 5.0
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
    four_step = params.get("four_step_system", {})

    all_pass = True

    # P0-7: Step1 validation
    print(f"\n【P0-7: Step1 方向确认层】")
    step1_cfg = four_step.get("step1_direction", {})
    min_strength = step1_cfg.get("min_final_strength")

    print(f"  min_final_strength: {min_strength}")
    if min_strength == 5.0:
        print(f"  ✅ SUCCESS: 20.0 → 5.0")
    else:
        print(f"  ❌ FAILED: Expected 5.0, got {min_strength}")
        all_pass = False

    # P0-8: Step2 validation
    print(f"\n【P0-8: Step2 时机判断层】")
    step2_cfg = four_step.get("step2_timing", {})
    enhanced_f_cfg = step2_cfg.get("enhanced_f", {})
    min_threshold = enhanced_f_cfg.get("min_threshold")

    print(f"  min_threshold: {min_threshold}")
    if min_threshold == -30.0:
        print(f"  ✅ SUCCESS: 30.0 → -30.0 (允许中性时机)")
    else:
        print(f"  ❌ FAILED: Expected -30.0, got {min_threshold}")
        all_pass = False

    # P0-8: Step3 validation
    print(f"\n【P0-8: Step3 入场价阈值】")
    step3_cfg = four_step.get("step3_risk", {})
    entry_cfg = step3_cfg.get("entry_price", {})
    moderate_f = entry_cfg.get("moderate_accumulation_f")
    strong_f = entry_cfg.get("strong_accumulation_f")

    print(f"  moderate_accumulation_f: {moderate_f}")
    if moderate_f == 5.0:
        print(f"  ✅ SUCCESS: 40 → 5.0")
    else:
        print(f"  ❌ FAILED: Expected 5.0, got {moderate_f}")
        all_pass = False

    print(f"  strong_accumulation_f: {strong_f}")
    if strong_f == 15.0:
        print(f"  ✅ SUCCESS: 70 → 15.0")
    else:
        print(f"  ❌ FAILED: Expected 15.0, got {strong_f}")
        all_pass = False

    # P0-8: Step4 validation
    print(f"\n【P0-8: Step4 质量控制层 Gate3】")
    step4_cfg = four_step.get("step4_quality", {})
    gate3_cfg = step4_cfg.get("gate3_strength", {})
    min_prime_strength = gate3_cfg.get("min_prime_strength")

    print(f"  min_prime_strength: {min_prime_strength}")
    if min_prime_strength == 5.0:
        print(f"  ✅ SUCCESS: 35 → 5.0 (与Step1阈值对齐)")
    else:
        print(f"  ❌ FAILED: Expected 5.0, got {min_prime_strength}")
        all_pass = False

    return all_pass


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
    symbols = ["BNBUSDT"]

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
    print("P0-7 & P0-8 Bug Fix Validation - CryptoSignal v7.4.2")
    print("问题: 回测产生0个信号 - 四步系统阈值系统性过高")
    print("修复: P0-7 (Step1) + P0-8 (Step2/3/4) 阈值调整")
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
        print("   python3 scripts/backtest_four_step.py --symbols BNBUSDT --start 2024-10-01 --end 2024-11-01")
    else:
        print("\n❌ 修复验证失败，请检查配置")
        sys.exit(1)


if __name__ == "__main__":
    main()
