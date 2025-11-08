#!/usr/bin/env python3
# coding: utf-8
"""
Shadow Runner - Independent Shadow Run Entry Point (Deliverable C.2)

Purpose:
    Shadow run mode for testing cryptosignal v2.0 compliance without real trading.
    Collects signal data, gate checks, and quality metrics for analysis.

Features:
    - No trading functionality (shadow mode only)
    - Public endpoints only (no API keys required)
    - Fixed test symbol set (BTC/ETH + high liquidity + 1 new coin)
    - Output to shadow_out/ directory (Parquet + JSON)
    - Comprehensive logging for compliance review

Usage:
    # Single scan
    python scripts/shadow_runner.py

    # Continuous run (24 hours)
    python scripts/shadow_runner.py --duration 24

    # Quick test (5 symbols, 10 minutes)
    python scripts/shadow_runner.py --duration 0.17 --symbols 5

Output:
    shadow_out/signals_{timestamp}.parquet    - Signal records
    shadow_out/gates_{timestamp}.parquet      - Gate check results
    shadow_out/metrics_{timestamp}.json       - Summary metrics

Specification:
    IMPLEMENTATION_PLAN_v2.md § C.2 - Shadow runner requirements
"""

import os
import sys
import asyncio
import argparse
import json
import signal
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
except ImportError:
    print("⚠️  Warning: pandas/pyarrow not installed, will use JSON only")
    pd = None
    pq = None

from ats_core.pipeline.batch_scan_optimized import OptimizedBatchScanner
from ats_core.gates.integrated_gates import FourGatesChecker
from ats_core.execution.metrics_estimator import ExecutionMetricsEstimator
from ats_core.data.quality import DataQualMonitor
from ats_core.publishing.anti_jitter import AntiJitter
from ats_core.config.anti_jitter_config import get_config
from ats_core.logging import log, warn, error


class ShadowRunner:
    """
    Shadow runner for testing signals without real trading.

    Collects:
        - Signal records (S_total, side, probability, EV, etc.)
        - Gate check results (DataQual, EV, Execution, Probability)
        - Quality metrics (miss rate, drift, mismatch)
        - Anti-jitter state transitions
    """

    # Test symbol configuration
    DEFAULT_SYMBOLS = [
        # Core pairs (always tested)
        'BTCUSDT',
        'ETHUSDT',

        # High liquidity (3-5 symbols)
        'BNBUSDT',
        'SOLUSDT',
        'ADAUSDT',
        'XRPUSDT',
        'DOGEUSDT',

        # New coin placeholder (will be replaced with actual new listings)
        # For testing, use a recent volatile coin
        'ARBUSDT',  # Relatively new, high volatility
    ]

    def __init__(
        self,
        output_dir: str = "shadow_out",
        symbols: List[str] = None,
        scan_interval: int = 60  # seconds
    ):
        """
        Initialize shadow runner.

        Args:
            output_dir: Output directory for results
            symbols: Test symbol list (default: DEFAULT_SYMBOLS)
            scan_interval: Seconds between scans
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.symbols = symbols or self.DEFAULT_SYMBOLS
        self.scan_interval = scan_interval

        # Initialize components
        log("🔧 Initializing shadow runner components...")
        self.scanner = OptimizedBatchScanner()
        self.gate_checker = FourGatesChecker()
        self.metrics_estimator = ExecutionMetricsEstimator()
        self.quality_monitor = DataQualMonitor()

        # v6.7: 使用统一防抖配置（1h标准配置，更适合shadow测试）
        aj_config = get_config("1h")
        self.anti_jitter = AntiJitter(config=aj_config)
        log(f"   防抖配置: {aj_config.kline_period} K线, K/N={aj_config.confirmation_bars}/{aj_config.total_bars}, cooldown={aj_config.cooldown_bars} bars")

        # Data collection buffers
        self.signal_records = []
        self.gate_records = []
        self.quality_records = []

        # Statistics
        self.scan_count = 0
        self.signal_count = 0
        self.prime_count = 0
        self.watch_count = 0

        # Control flags
        self.running = False
        self.start_time = None

        log(f"✅ Shadow runner initialized")
        log(f"   Symbols: {len(self.symbols)}")
        log(f"   Interval: {self.scan_interval}s")
        log(f"   Output: {self.output_dir}/")

    async def initialize(self):
        """Initialize scanner with symbol data."""
        log("🔄 Initializing scanner (may take 2-3 minutes)...")
        await self.scanner.initialize(self.symbols)
        log("✅ Scanner ready")

    async def scan_once(self) -> Dict[str, Any]:
        """
        Perform one scan cycle and collect data.

        Returns:
            summary: {
                'timestamp': scan timestamp,
                'symbols_scanned': count,
                'signals_generated': count,
                'prime_signals': count,
                'watch_signals': count
            }
        """
        scan_start = datetime.now()
        self.scan_count += 1

        log(f"\n{'='*60}")
        log(f"🔍 Shadow Scan #{self.scan_count} - {scan_start.strftime('%H:%M:%S')}")
        log(f"{'='*60}")

        # Run batch scan
        results = await self.scanner.scan_all(min_score=None)

        symbols_scanned = 0
        signals_generated = 0
        prime_signals = 0
        watch_signals = 0

        for result in results:
            symbol = result.get('symbol', 'UNKNOWN')
            symbols_scanned += 1

            # Extract core data
            S_total = result.get('S_total', 0)
            scores = result.get('scores', {})
            modulation = result.get('modulation', {})
            is_newcoin = result.get('is_newcoin', False)
            newcoin_phase = result.get('newcoin_phase', 'mature')

            # Check gates
            gate_result = self.gate_checker.check_all_gates(
                data=result,
                is_newcoin=is_newcoin,
                newcoin_phase=newcoin_phase
            )

            # Extract metrics
            dataqual = result.get('dataqual', 0.0)
            probability = result.get('publish', {}).get('probability', 0.0)
            ev = result.get('publish', {}).get('ev', 0.0)
            metrics = result.get('metrics', {})

            # Apply anti-jitter
            final_level, should_publish = self.anti_jitter.update(
                symbol=symbol,
                probability=probability,
                ev=ev,
                gates_passed=gate_result.all_passed
            )

            # Record signal
            signal_record = {
                'timestamp': scan_start.isoformat(),
                'scan_id': self.scan_count,
                'symbol': symbol,
                'is_newcoin': is_newcoin,
                'newcoin_phase': newcoin_phase,
                'S_total': S_total,
                'side': result.get('side', 'NONE'),
                'probability': probability,
                'ev': ev,
                'dataqual': dataqual,
                'final_level': final_level,
                'should_publish': should_publish,
                'gates_all_passed': gate_result.all_passed,
                **scores,  # T, M, C, S, V, O, L, B, Q, I
                **{f'mod_{k}': v for k, v in modulation.items()},  # F, I
                **{f'metric_{k}': v for k, v in metrics.items()}  # impact_bps, spread_bps, etc.
            }
            self.signal_records.append(signal_record)

            # Record gate details
            gate_record = {
                'timestamp': scan_start.isoformat(),
                'scan_id': self.scan_count,
                'symbol': symbol,
                'gate1_dataqual_passed': gate_result.gate1.passed,
                'gate1_reason': gate_result.gate1.reason,
                'gate2_ev_passed': gate_result.gate2.passed,
                'gate2_reason': gate_result.gate2.reason,
                'gate3_execution_passed': gate_result.gate3.passed,
                'gate3_reason': gate_result.gate3.reason,
                'gate4_probability_passed': gate_result.gate4.passed,
                'gate4_reason': gate_result.gate4.reason,
                'all_gates_passed': gate_result.all_passed,
            }
            self.gate_records.append(gate_record)

            # Record quality
            quality_record = {
                'timestamp': scan_start.isoformat(),
                'scan_id': self.scan_count,
                'symbol': symbol,
                'dataqual': dataqual,
                'miss_rate': result.get('quality_details', {}).get('miss_rate', 0.0),
                'oo_order_rate': result.get('quality_details', {}).get('oo_order_rate', 0.0),
                'drift_rate': result.get('quality_details', {}).get('drift_rate', 0.0),
                'mismatch_rate': result.get('quality_details', {}).get('mismatch_rate', 0.0),
            }
            self.quality_records.append(quality_record)

            # Update statistics
            if should_publish:
                signals_generated += 1
                if final_level == 'PRIME':
                    prime_signals += 1
                    self.prime_count += 1
                    log(f"   ⭐ {symbol}: PRIME (S={S_total:.1f}, P={probability:.2f}, EV={ev:.2f})")
                elif final_level == 'WATCH':
                    watch_signals += 1
                    self.watch_count += 1
                    log(f"   👀 {symbol}: WATCH (S={S_total:.1f}, P={probability:.2f})")

        self.signal_count += signals_generated

        # Summary
        scan_duration = (datetime.now() - scan_start).total_seconds()
        summary = {
            'timestamp': scan_start.isoformat(),
            'scan_id': self.scan_count,
            'duration_seconds': scan_duration,
            'symbols_scanned': symbols_scanned,
            'signals_generated': signals_generated,
            'prime_signals': prime_signals,
            'watch_signals': watch_signals,
        }

        log(f"\n📊 Scan Summary:")
        log(f"   Symbols: {symbols_scanned}")
        log(f"   Signals: {signals_generated} (Prime: {prime_signals}, Watch: {watch_signals})")
        log(f"   Duration: {scan_duration:.1f}s")

        return summary

    async def run(self, duration_hours: float = None):
        """
        Run shadow mode continuously.

        Args:
            duration_hours: Run duration in hours (None = run once)
        """
        self.running = True
        self.start_time = datetime.now()

        # Register signal handlers for graceful shutdown
        def signal_handler(sig, frame):
            log("\n⚠️  Received interrupt signal, shutting down gracefully...")
            self.running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Initialize
        await self.initialize()

        # Single scan mode
        if duration_hours is None:
            log("🔍 Single scan mode")
            await self.scan_once()
            await self.save_results()
            log("✅ Shadow run complete")
            return

        # Continuous mode
        log(f"🔄 Continuous mode: {duration_hours:.1f} hours")
        end_time = self.start_time + timedelta(hours=duration_hours)

        while self.running and datetime.now() < end_time:
            try:
                # Scan
                await self.scan_once()

                # Check if should continue
                remaining = (end_time - datetime.now()).total_seconds()
                if remaining <= 0:
                    break

                # Wait for next scan
                wait_time = min(self.scan_interval, remaining)
                log(f"⏳ Next scan in {wait_time:.0f}s (remaining: {remaining/60:.1f}min)")
                await asyncio.sleep(wait_time)

            except Exception as e:
                error(f"Scan error: {e}")
                await asyncio.sleep(self.scan_interval)

        # Save results
        await self.save_results()

        # Final summary
        total_duration = (datetime.now() - self.start_time).total_seconds() / 3600
        log(f"\n{'='*60}")
        log(f"🎯 Shadow Run Complete")
        log(f"{'='*60}")
        log(f"   Duration: {total_duration:.2f} hours")
        log(f"   Scans: {self.scan_count}")
        log(f"   Signals: {self.signal_count} (Prime: {self.prime_count}, Watch: {self.watch_count})")
        log(f"   Output: {self.output_dir}/")

    async def save_results(self):
        """Save collected data to output directory."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        log("\n💾 Saving results...")

        # Save signals
        if self.signal_records:
            if pd is not None:
                # Parquet format (preferred)
                df_signals = pd.DataFrame(self.signal_records)
                signals_file = self.output_dir / f"signals_{timestamp}.parquet"
                df_signals.to_parquet(signals_file, index=False)
                log(f"   ✅ Signals: {signals_file} ({len(self.signal_records)} records)")
            else:
                # JSON fallback
                signals_file = self.output_dir / f"signals_{timestamp}.json"
                with open(signals_file, 'w') as f:
                    json.dump(self.signal_records, f, indent=2)
                log(f"   ✅ Signals: {signals_file} ({len(self.signal_records)} records)")

        # Save gates
        if self.gate_records:
            if pd is not None:
                df_gates = pd.DataFrame(self.gate_records)
                gates_file = self.output_dir / f"gates_{timestamp}.parquet"
                df_gates.to_parquet(gates_file, index=False)
                log(f"   ✅ Gates: {gates_file} ({len(self.gate_records)} records)")
            else:
                gates_file = self.output_dir / f"gates_{timestamp}.json"
                with open(gates_file, 'w') as f:
                    json.dump(self.gate_records, f, indent=2)
                log(f"   ✅ Gates: {gates_file} ({len(self.gate_records)} records)")

        # Save quality
        if self.quality_records:
            if pd is not None:
                df_quality = pd.DataFrame(self.quality_records)
                quality_file = self.output_dir / f"quality_{timestamp}.parquet"
                df_quality.to_parquet(quality_file, index=False)
                log(f"   ✅ Quality: {quality_file} ({len(self.quality_records)} records)")
            else:
                quality_file = self.output_dir / f"quality_{timestamp}.json"
                with open(quality_file, 'w') as f:
                    json.dump(self.quality_records, f, indent=2)
                log(f"   ✅ Quality: {quality_file} ({len(self.quality_records)} records)")

        # Save summary metrics
        metrics = {
            'run_info': {
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'end_time': datetime.now().isoformat(),
                'duration_hours': (datetime.now() - self.start_time).total_seconds() / 3600 if self.start_time else 0,
            },
            'scan_stats': {
                'total_scans': self.scan_count,
                'total_signals': self.signal_count,
                'prime_signals': self.prime_count,
                'watch_signals': self.watch_count,
                'prime_rate': self.prime_count / self.signal_count if self.signal_count > 0 else 0,
                'watch_rate': self.watch_count / self.signal_count if self.signal_count > 0 else 0,
            },
            'symbols': self.symbols,
            'config': {
                'scan_interval': self.scan_interval,
                'anti_jitter_prime_entry': 0.80,
                'anti_jitter_confirmation': '2/3 bars',
                'anti_jitter_cooldown': '90s',
            }
        }

        metrics_file = self.output_dir / f"metrics_{timestamp}.json"
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2)
        log(f"   ✅ Metrics: {metrics_file}")

        log("✅ All results saved")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Shadow Runner - Shadow run mode for testing signals without trading",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Single scan
    python scripts/shadow_runner.py

    # 24-hour continuous run
    python scripts/shadow_runner.py --duration 24

    # 10-minute test run with 5 symbols
    python scripts/shadow_runner.py --duration 0.17 --symbols 5

    # Custom symbol list
    python scripts/shadow_runner.py --custom-symbols BTCUSDT,ETHUSDT,SOLUSDT

Output:
    shadow_out/signals_YYYYMMDD_HHMMSS.parquet
    shadow_out/gates_YYYYMMDD_HHMMSS.parquet
    shadow_out/quality_YYYYMMDD_HHMMSS.parquet
    shadow_out/metrics_YYYYMMDD_HHMMSS.json
        """
    )

    parser.add_argument(
        '--duration',
        type=float,
        default=None,
        help='Run duration in hours (default: single scan)'
    )

    parser.add_argument(
        '--symbols',
        type=int,
        default=None,
        help='Number of symbols to test (default: 8, uses DEFAULT_SYMBOLS)'
    )

    parser.add_argument(
        '--custom-symbols',
        type=str,
        default=None,
        help='Custom symbol list (comma-separated, e.g., BTCUSDT,ETHUSDT,SOLUSDT)'
    )

    parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='Scan interval in seconds (default: 60)'
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        default='shadow_out',
        help='Output directory (default: shadow_out)'
    )

    args = parser.parse_args()

    # Determine symbol list
    if args.custom_symbols:
        symbols = [s.strip() for s in args.custom_symbols.split(',')]
    elif args.symbols:
        symbols = ShadowRunner.DEFAULT_SYMBOLS[:args.symbols]
    else:
        symbols = ShadowRunner.DEFAULT_SYMBOLS

    # Create runner
    runner = ShadowRunner(
        output_dir=args.output_dir,
        symbols=symbols,
        scan_interval=args.interval
    )

    # Banner
    print("\n" + "="*60)
    print("🌑 SHADOW RUNNER v2.0")
    print("="*60)
    print(f"Mode: Shadow (no trading)")
    print(f"Symbols: {len(symbols)}")
    print(f"Duration: {args.duration or 'single scan'} hours")
    print(f"Interval: {args.interval}s")
    print(f"Output: {args.output_dir}/")
    print("="*60 + "\n")

    # Force shadow mode
    os.environ['CRYPTOSIGNAL_SHADOW_MODE'] = '1'
    os.environ['CRYPTOSIGNAL_REAL_TRADING'] = '0'

    # Run
    try:
        asyncio.run(runner.run(duration_hours=args.duration))
    except KeyboardInterrupt:
        log("\n⚠️  Interrupted by user")
    except Exception as e:
        error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
