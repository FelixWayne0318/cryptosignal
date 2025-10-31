#!/usr/bin/env python3
"""
Shadow runner for testing new implementations against production code.

Usage:
    python scripts/shadow_runner.py [--duration SECONDS] [--symbols SYMBOL1,SYMBOL2]

Examples:
    # Run shadow test for 5 minutes on default test symbols
    python scripts/shadow_runner.py --duration 300

    # Run on specific symbols
    python scripts/shadow_runner.py --symbols BTCUSDT,ETHUSDT --duration 600

    # Run continuously (Ctrl-C to stop)
    python scripts/shadow_runner.py
"""

import sys
import argparse
import time
import signal
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ats_core.shadow.config import ShadowConfig
from ats_core.shadow.comparator import ShadowComparator
from ats_core.shadow.logger import ShadowLogger
from ats_core.data.quality import DataQualMonitor

# Will import old/new implementations dynamically


class ShadowRunner:
    """Orchestrates shadow testing of new implementations."""

    def __init__(
        self,
        config_path: Optional[str] = None,
        test_symbols: Optional[List[str]] = None,
        duration_seconds: Optional[int] = None
    ):
        """
        Initialize shadow runner.

        Args:
            config_path: Path to shadow.json config
            test_symbols: Override symbols to test
            duration_seconds: Run duration (None = infinite)
        """
        self.config = ShadowConfig(config_path)
        self.test_symbols = test_symbols or self.config.test_symbols
        self.duration = duration_seconds

        # Initialize components
        self.comparator = ShadowComparator()
        self.logger = ShadowLogger()
        self.dataqual_monitor = DataQualMonitor()

        # State
        self.running = True
        self.start_time = None

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Handle graceful shutdown on signal."""
        print("\n[SHADOW] Shutdown signal received, finishing...")
        self.running = False

    def run(self) -> None:
        """Main shadow testing loop."""
        if not self.config.enabled:
            print("[SHADOW] Shadow mode is disabled in config. Exiting.")
            return

        print(f"[SHADOW] Starting shadow run")
        print(f"[SHADOW] Mode: {self.config.mode}")
        print(f"[SHADOW] Test symbols: {self.test_symbols}")
        print(f"[SHADOW] Duration: {self.duration or 'infinite'} seconds")
        print(f"[SHADOW] Features enabled:")
        for feature in ['dataqual', 'standardization_chain', 'modulators_FI', 'ev_gate', 'publishing_rules']:
            enabled = self.config.is_feature_enabled(feature)
            print(f"  - {feature}: {'✓' if enabled else '✗'}")

        self.start_time = time.time()

        try:
            self._run_loop()
        except Exception as e:
            print(f"[SHADOW] Error during run: {e}")
            raise
        finally:
            self._finalize()

    def _run_loop(self) -> None:
        """Main testing loop."""
        iteration = 0

        while self.running:
            iteration += 1

            # Check duration limit
            if self.duration:
                elapsed = time.time() - self.start_time
                if elapsed >= self.duration:
                    print(f"[SHADOW] Duration limit reached ({self.duration}s)")
                    break

            # Test each symbol
            for symbol in self.test_symbols:
                if not self.running:
                    break

                try:
                    self._test_symbol(symbol, iteration)
                except Exception as e:
                    print(f"[SHADOW] Error testing {symbol}: {e}")
                    continue

            # Report progress
            if iteration % 10 == 0:
                self._report_progress()

            # Sleep between iterations
            time.sleep(1)

    def _test_symbol(self, symbol: str, iteration: int) -> None:
        """
        Test a single symbol.

        Args:
            symbol: Trading symbol
            iteration: Current iteration number
        """
        # This is a placeholder - actual implementation would:
        # 1. Fetch latest data for symbol
        # 2. Run old implementation
        # 3. Run new implementation
        # 4. Compare results
        # 5. Log to shadow logger

        # For now, simulate with dummy data for testing
        if self.config.is_feature_enabled('dataqual'):
            self._test_dataqual(symbol)

        if self.config.is_feature_enabled('standardization_chain'):
            self._test_standardization(symbol)

        if self.config.is_feature_enabled('modulators_FI'):
            self._test_modulators(symbol)

    def _test_dataqual(self, symbol: str) -> None:
        """Test DataQual monitoring."""
        # Simulate receiving data
        import random

        ts_exch = int(time.time() * 1000)
        ts_srv = ts_exch + random.randint(-500, 500)  # Simulate network delay
        is_ordered = random.random() > 0.01  # 1% out of order

        self.dataqual_monitor.record_event(
            symbol=symbol,
            ts_exch=ts_exch,
            ts_srv=ts_srv,
            is_ordered=is_ordered
        )

        # Occasionally simulate mismatch
        if random.random() < 0.001:
            self.dataqual_monitor.record_mismatch(symbol)

        # Get quality and log
        quality = self.dataqual_monitor.get_quality(symbol)
        self.logger.log_metric(f'dataqual_{symbol}', quality.dataqual)

        # Check if can publish Prime
        can_publish, score, reason = self.dataqual_monitor.can_publish_prime(symbol)
        if not can_publish:
            self.logger.log_event('quality_gate_failed', {
                'symbol': symbol,
                'dataqual': score,
                'reason': reason
            })

    def _test_standardization(self, symbol: str) -> None:
        """Test standardization chain (placeholder)."""
        # TODO: Implement when standardization chain is ready
        pass

    def _test_modulators(self, symbol: str) -> None:
        """Test F/I modulators (placeholder)."""
        # TODO: Implement when modulators are ready
        pass

    def _report_progress(self) -> None:
        """Report current progress."""
        elapsed = time.time() - self.start_time
        summary = self.comparator.get_summary()

        print(f"\n[SHADOW] Progress Report (elapsed: {elapsed:.0f}s)")
        print(f"  Comparisons: {summary.get('total', 0)}")
        print(f"  Pass rate: {summary.get('pass_rate', 0.0):.2%}")

        # DataQual summary
        all_qualities = self.dataqual_monitor.get_all_qualities()
        if all_qualities:
            avg_qual = sum(all_qualities.values()) / len(all_qualities)
            min_qual = min(all_qualities.values())
            print(f"  DataQual: avg={avg_qual:.3f}, min={min_qual:.3f}")

    def _finalize(self) -> None:
        """Finalize and write results."""
        print("\n[SHADOW] Finalizing...")

        # Get final summaries
        comp_summary = self.comparator.get_summary()
        log_summary = self.logger.get_summary()

        print(f"\n[SHADOW] Final Summary:")
        print(f"  Total comparisons: {comp_summary.get('total', 0)}")
        print(f"  Passed: {comp_summary.get('passed', 0)}")
        print(f"  Failed: {comp_summary.get('failed', 0)}")
        print(f"  Pass rate: {comp_summary.get('pass_rate', 0.0):.2%}")
        print(f"  Session duration: {log_summary['session_duration_seconds']:.0f}s")

        # Write logs
        self.logger.flush()
        print(f"\n[SHADOW] Results written to: logs/shadow/")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Shadow runner for testing new implementations"
    )
    parser.add_argument(
        '--duration',
        type=int,
        default=None,
        help='Run duration in seconds (default: infinite)'
    )
    parser.add_argument(
        '--symbols',
        type=str,
        default=None,
        help='Comma-separated list of symbols to test (default: from config)'
    )
    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='Path to shadow.json config (default: config/shadow.json)'
    )

    args = parser.parse_args()

    # Parse symbols
    symbols = None
    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(',')]

    # Create and run
    runner = ShadowRunner(
        config_path=args.config,
        test_symbols=symbols,
        duration_seconds=args.duration
    )

    runner.run()


if __name__ == '__main__':
    main()
