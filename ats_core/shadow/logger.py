"""
Shadow logger for structured logging of shadow run results.

Logs comparisons, divergences, and metrics to JSON files for analysis.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, timezone
from collections import defaultdict

# UTC+8时区（北京时间）
TZ_UTC8 = timezone(timedelta(hours=8))


class ShadowLogger:
    """Structured logger for shadow testing results."""

    def __init__(self, output_dir: str = "logs/shadow", console_log: bool = True):
        """
        Initialize shadow logger.

        Args:
            output_dir: Directory to write log files
            console_log: Whether to also log to console
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Setup console logger
        self.logger = logging.getLogger('shadow')
        self.logger.setLevel(logging.INFO)

        if console_log and not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s [SHADOW] %(levelname)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # In-memory accumulation
        self.comparisons: List[Dict[str, Any]] = []
        self.divergences: List[Dict[str, Any]] = []
        self.metrics: Dict[str, List[float]] = defaultdict(list)

        self.session_start = datetime.now(TZ_UTC8)

    def log_comparison(self, comparison_result) -> None:
        """
        Log a comparison result.

        Args:
            comparison_result: ComparisonResult object from ShadowComparator
        """
        result_dict = comparison_result.to_dict()
        self.comparisons.append(result_dict)

        # Track divergences (failures)
        if not comparison_result.within_threshold:
            self.divergences.append(result_dict)
            self.logger.warning(
                f"Divergence detected: {comparison_result.symbol} "
                f"{comparison_result.metric_name} "
                f"old={comparison_result.old_value:.4f} "
                f"new={comparison_result.new_value:.4f} "
                f"diff={comparison_result.absolute_diff:.4f}"
            )

    def log_metric(self, metric_name: str, value: float) -> None:
        """
        Log a single metric value.

        Args:
            metric_name: Name of metric
            value: Metric value
        """
        self.metrics[metric_name].append(value)

    def log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Log a custom event.

        Args:
            event_type: Type of event
            data: Event data
        """
        event = {
            'timestamp': datetime.now(TZ_UTC8).isoformat(),
            'type': event_type,
            **data
        }

        # Write to event log
        event_file = self.output_dir / f"events_{datetime.now(TZ_UTC8).strftime('%Y%m%d')}.jsonl"
        with open(event_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event, ensure_ascii=False) + '\n')

    def flush(self) -> None:
        """Write accumulated data to disk."""
        timestamp = datetime.now(TZ_UTC8).strftime('%Y%m%d_%H%M%S')

        # Write comparisons
        if self.comparisons:
            comp_file = self.output_dir / f"comparisons_{timestamp}.json"
            with open(comp_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'session_start': self.session_start.isoformat(),
                    'session_end': datetime.now(TZ_UTC8).isoformat(),
                    'total': len(self.comparisons),
                    'comparisons': self.comparisons
                }, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Wrote {len(self.comparisons)} comparisons to {comp_file}")

        # Write divergences
        if self.divergences:
            div_file = self.output_dir / f"divergences_{timestamp}.json"
            with open(div_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'session_start': self.session_start.isoformat(),
                    'session_end': datetime.now(TZ_UTC8).isoformat(),
                    'total': len(self.divergences),
                    'divergences': self.divergences
                }, f, indent=2, ensure_ascii=False)

            self.logger.warning(f"Wrote {len(self.divergences)} divergences to {div_file}")

        # Write metrics summary
        if self.metrics:
            metrics_file = self.output_dir / f"metrics_{timestamp}.json"
            metrics_summary = {
                metric: {
                    'count': len(values),
                    'mean': sum(values) / len(values) if values else 0,
                    'min': min(values) if values else 0,
                    'max': max(values) if values else 0,
                }
                for metric, values in self.metrics.items()
            }

            with open(metrics_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'session_start': self.session_start.isoformat(),
                    'session_end': datetime.now(TZ_UTC8).isoformat(),
                    'metrics': metrics_summary
                }, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Wrote metrics summary to {metrics_file}")

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of current session."""
        total = len(self.comparisons)
        divergent = len(self.divergences)

        return {
            'session_duration_seconds': (datetime.now(TZ_UTC8) - self.session_start).total_seconds(),
            'total_comparisons': total,
            'divergences': divergent,
            'pass_rate': (total - divergent) / total if total > 0 else 0.0,
            'metrics_tracked': len(self.metrics),
        }

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - auto flush."""
        self.flush()
