"""
扫描报告写入模块
将扫描结果写入仓库，便于分析和历史追踪
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List


class ReportWriter:
    """扫描报告写入器"""

    def __init__(self, base_dir: str = None):
        """
        初始化报告写入器

        Args:
            base_dir: 报告基础目录，默认为项目根目录/reports
        """
        if base_dir is None:
            # 默认使用项目根目录/reports
            project_root = Path(__file__).parent.parent.parent
            base_dir = project_root / "reports"

        self.base_dir = Path(base_dir)
        self.latest_dir = self.base_dir / "latest"
        self.history_dir = self.base_dir / "history"

        # 确保目录存在
        self.latest_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def write_scan_report(
        self,
        summary: Dict[str, Any],
        detail: Dict[str, Any],
        text_report: str
    ) -> Dict[str, str]:
        """
        写入扫描报告

        Args:
            summary: 摘要数据（统计信息）
            detail: 详细数据（所有币种）
            text_report: 文本格式报告

        Returns:
            写入的文件路径
        """
        timestamp = datetime.now()
        ts_str = timestamp.strftime("%Y-%m-%d_%H-%M-%S")

        files_written = {}

        # 1. 写入最新摘要（JSON）
        latest_summary = self.latest_dir / "scan_summary.json"
        with open(latest_summary, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        files_written['latest_summary_json'] = str(latest_summary)

        # 2. 写入最新摘要（Markdown）
        latest_md = self.latest_dir / "scan_summary.md"
        with open(latest_md, 'w', encoding='utf-8') as f:
            f.write(text_report)
        files_written['latest_summary_md'] = str(latest_md)

        # 3. 写入最新详细数据
        latest_detail = self.latest_dir / "scan_detail.json"
        with open(latest_detail, 'w', encoding='utf-8') as f:
            json.dump(detail, f, indent=2, ensure_ascii=False)
        files_written['latest_detail_json'] = str(latest_detail)

        # 4. 写入历史记录（只保留摘要）
        history_file = self.history_dir / f"{ts_str}_scan.json"
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        files_written['history_json'] = str(history_file)

        # 5. 更新趋势文件
        self._update_trends(summary)

        return files_written

    def _update_trends(self, summary: Dict[str, Any]):
        """更新趋势文件"""
        trends_file = self.base_dir / "trends.json"

        # 读取现有趋势
        if trends_file.exists():
            with open(trends_file, 'r', encoding='utf-8') as f:
                trends = json.load(f)
        else:
            trends = {
                "signals_count": [],
                "avg_edge": [],
                "avg_confidence": [],
                "scan_times": [],
                "rejection_reasons_history": []
            }

        # 添加新数据点
        trends["signals_count"].append(summary.get("signals_found", 0))
        trends["avg_edge"].append(summary.get("avg_edge", 0))
        trends["avg_confidence"].append(summary.get("avg_confidence", 0))
        trends["scan_times"].append(summary.get("timestamp", ""))
        trends["rejection_reasons_history"].append(summary.get("rejection_reasons", {}))

        # 只保留最近30次
        max_history = 30
        for key in trends:
            if isinstance(trends[key], list) and len(trends[key]) > max_history:
                trends[key] = trends[key][-max_history:]

        # 写入
        with open(trends_file, 'w', encoding='utf-8') as f:
            json.dump(trends, f, indent=2, ensure_ascii=False)

    def write_setup_log(self, log_content: str):
        """写入setup.sh日志"""
        log_file = self.latest_dir / "setup_log.txt"
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(log_content)

    def write_scan_progress(self, progress_data: Dict[str, Any]):
        """写入扫描进度（实时更新）"""
        progress_file = self.latest_dir / "scan_progress.json"
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, indent=2, ensure_ascii=False)

    def cleanup_old_history(self, keep_days: int = 30):
        """清理旧历史记录"""
        import time
        cutoff_time = time.time() - (keep_days * 86400)

        for file in self.history_dir.glob("*.json"):
            if file.stat().st_mtime < cutoff_time:
                file.unlink()


# 全局单例
_global_writer = ReportWriter()


def get_report_writer() -> ReportWriter:
    """获取全局报告写入器"""
    return _global_writer
