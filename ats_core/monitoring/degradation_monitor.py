# coding: utf-8
"""
降级事件监控系统（v3.1）

提供全局降级事件记录、统计和分析功能。

主要功能：
- 记录所有因子的降级事件
- 按因子、级别、时间范围统计降级次数
- 导出降级报告（JSON/CSV格式）
- 实时降级告警

使用示例：
    from ats_core.monitoring import record_degradation, get_degradation_stats

    # 记录降级事件
    record_degradation(
        factor_name="M",
        level="degraded",
        confidence=0.6,
        actual_data=12,
        required_data=20,
        reason="insufficient_data"
    )

    # 获取统计信息
    stats = get_degradation_stats(factor_name="M", last_n_hours=24)
    print(f"M因子24小时内降级{stats['total_events']}次")
"""

import time
import json
from typing import Dict, List, Any, Optional
from collections import defaultdict
from threading import Lock


class DegradationMonitor:
    """降级事件监控器

    全局单例，记录和分析所有因子的降级事件。

    线程安全：使用Lock保护共享数据。
    """

    def __init__(self, max_events: int = 10000):
        """
        Args:
            max_events: 最大事件记录数（超过后自动清理旧事件）
        """
        self.max_events = max_events
        self._events = []  # 所有降级事件列表
        self._lock = Lock()  # 线程锁

        # 统计缓存（按因子名称）
        self._stats_cache = {}
        self._cache_timestamp = 0
        self._cache_ttl = 60  # 缓存有效期60秒

    def record_event(
        self,
        factor_name: str,
        level: str,
        confidence: float,
        actual_data: int,
        required_data: int,
        reason: str,
        symbol: Optional[str] = None,
        additional_info: Optional[Dict[str, Any]] = None
    ):
        """记录降级事件

        Args:
            factor_name: 因子名称（如"M", "C+", "V+"等）
            level: 降级级别（"normal", "warning", "degraded", "disabled"）
            confidence: 置信度（0.0 - 1.0）
            actual_data: 实际数据量
            required_data: 最小要求数据量
            reason: 降级原因（如"insufficient_data"）
            symbol: 交易对符号（可选）
            additional_info: 额外信息（可选）
        """
        with self._lock:
            event = {
                "timestamp": time.time(),
                "factor_name": factor_name,
                "level": level,
                "confidence": round(confidence, 3),
                "actual_data": actual_data,
                "required_data": required_data,
                "data_ratio": round(actual_data / max(1, required_data), 3),
                "reason": reason,
                "symbol": symbol
            }

            # 合并额外信息
            if additional_info:
                event.update(additional_info)

            self._events.append(event)

            # 自动清理旧事件
            if len(self._events) > self.max_events:
                # 保留最近50%的事件
                self._events = self._events[-(self.max_events // 2):]

            # 清除统计缓存
            self._invalidate_cache()

    def get_stats(
        self,
        factor_name: Optional[str] = None,
        last_n_hours: Optional[int] = None,
        min_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取降级统计信息

        Args:
            factor_name: 筛选特定因子（None表示所有因子）
            last_n_hours: 筛选最近N小时的事件（None表示所有时间）
            min_level: 最小降级级别（"warning", "degraded", "disabled"）

        Returns:
            统计信息字典，包含：
            - total_events: 总事件数
            - by_factor: 按因子分组的事件数
            - by_level: 按级别分组的事件数
            - avg_confidence: 平均置信度
            - avg_data_ratio: 平均数据充足率
            - recent_events: 最近10个事件
        """
        with self._lock:
            # 筛选事件
            filtered_events = self._filter_events(
                factor_name=factor_name,
                last_n_hours=last_n_hours,
                min_level=min_level
            )

            if not filtered_events:
                return {
                    "total_events": 0,
                    "by_factor": {},
                    "by_level": {},
                    "avg_confidence": 1.0,
                    "avg_data_ratio": 1.0,
                    "recent_events": []
                }

            # 按因子和级别统计
            by_factor = defaultdict(int)
            by_level = defaultdict(int)
            total_confidence = 0.0
            total_data_ratio = 0.0

            for event in filtered_events:
                by_factor[event["factor_name"]] += 1
                by_level[event["level"]] += 1
                total_confidence += event["confidence"]
                total_data_ratio += event["data_ratio"]

            return {
                "total_events": len(filtered_events),
                "by_factor": dict(by_factor),
                "by_level": dict(by_level),
                "avg_confidence": round(total_confidence / len(filtered_events), 3),
                "avg_data_ratio": round(total_data_ratio / len(filtered_events), 3),
                "recent_events": filtered_events[-10:]  # 最近10个
            }

    def _filter_events(
        self,
        factor_name: Optional[str] = None,
        last_n_hours: Optional[int] = None,
        min_level: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """筛选事件（内部方法）

        Args:
            factor_name: 因子名称筛选
            last_n_hours: 时间范围筛选（小时）
            min_level: 最小级别筛选

        Returns:
            筛选后的事件列表
        """
        # 级别优先级映射
        level_priority = {
            "normal": 0,
            "warning": 1,
            "degraded": 2,
            "disabled": 3
        }
        min_priority = level_priority.get(min_level, 0) if min_level else 0

        # 时间戳阈值
        time_threshold = time.time() - (last_n_hours * 3600) if last_n_hours else 0

        filtered = []
        for event in self._events:
            # 因子名称筛选
            if factor_name and event["factor_name"] != factor_name:
                continue

            # 时间范围筛选
            if last_n_hours and event["timestamp"] < time_threshold:
                continue

            # 级别筛选
            if min_level:
                event_priority = level_priority.get(event["level"], 0)
                if event_priority < min_priority:
                    continue

            filtered.append(event)

        return filtered

    def export_to_json(
        self,
        file_path: str,
        factor_name: Optional[str] = None,
        last_n_hours: Optional[int] = None
    ):
        """导出降级事件到JSON文件

        Args:
            file_path: 输出文件路径
            factor_name: 筛选特定因子（None表示所有因子）
            last_n_hours: 筛选最近N小时的事件（None表示所有时间）
        """
        with self._lock:
            filtered_events = self._filter_events(
                factor_name=factor_name,
                last_n_hours=last_n_hours
            )

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "export_time": time.time(),
                    "total_events": len(filtered_events),
                    "filter": {
                        "factor_name": factor_name,
                        "last_n_hours": last_n_hours
                    },
                    "events": filtered_events
                }, f, indent=2, ensure_ascii=False)

    def export_to_csv(
        self,
        file_path: str,
        factor_name: Optional[str] = None,
        last_n_hours: Optional[int] = None
    ):
        """导出降级事件到CSV文件

        Args:
            file_path: 输出文件路径
            factor_name: 筛选特定因子（None表示所有因子）
            last_n_hours: 筛选最近N小时的事件（None表示所有时间）
        """
        import csv

        with self._lock:
            filtered_events = self._filter_events(
                factor_name=factor_name,
                last_n_hours=last_n_hours
            )

            if not filtered_events:
                return

            # 获取所有字段名（从第一个事件）
            fieldnames = list(filtered_events[0].keys())

            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(filtered_events)

    def get_alert_summary(self, threshold_hours: int = 1) -> Dict[str, Any]:
        """获取降级告警摘要

        识别最近N小时内频繁降级的因子，用于实时告警。

        Args:
            threshold_hours: 时间阈值（小时）

        Returns:
            告警摘要，包含：
            - critical_factors: 严重降级的因子列表
            - warning_factors: 警告级别的因子列表
            - summary: 文本摘要
        """
        stats = self.get_stats(last_n_hours=threshold_hours)

        critical_factors = []
        warning_factors = []

        for factor, count in stats["by_factor"].items():
            # 获取该因子的详细统计
            factor_stats = self.get_stats(
                factor_name=factor,
                last_n_hours=threshold_hours
            )

            # 判断严重程度
            disabled_count = factor_stats["by_level"].get("disabled", 0)
            degraded_count = factor_stats["by_level"].get("degraded", 0)

            if disabled_count > 0:
                critical_factors.append({
                    "factor": factor,
                    "disabled_count": disabled_count,
                    "avg_confidence": factor_stats["avg_confidence"]
                })
            elif degraded_count > 0:
                warning_factors.append({
                    "factor": factor,
                    "degraded_count": degraded_count,
                    "avg_confidence": factor_stats["avg_confidence"]
                })

        # 生成文本摘要
        summary_parts = []
        if critical_factors:
            summary_parts.append(f"🚨 严重: {len(critical_factors)}个因子完全禁用")
        if warning_factors:
            summary_parts.append(f"⚠️ 警告: {len(warning_factors)}个因子降级")

        return {
            "critical_factors": critical_factors,
            "warning_factors": warning_factors,
            "summary": " | ".join(summary_parts) if summary_parts else "✅ 正常",
            "total_events": stats["total_events"]
        }

    def clear_all(self):
        """清空所有事件记录"""
        with self._lock:
            self._events = []
            self._invalidate_cache()

    def _invalidate_cache(self):
        """清除统计缓存"""
        self._stats_cache = {}
        self._cache_timestamp = 0


# ========== 全局单例 ==========

_global_monitor: Optional[DegradationMonitor] = None
_monitor_lock = Lock()


def get_global_monitor() -> DegradationMonitor:
    """获取全局降级监控器单例

    Returns:
        全局DegradationMonitor实例
    """
    global _global_monitor

    if _global_monitor is None:
        with _monitor_lock:
            if _global_monitor is None:
                _global_monitor = DegradationMonitor()

    return _global_monitor


# ========== 便捷函数 ==========

def record_degradation(
    factor_name: str,
    level: str,
    confidence: float,
    actual_data: int,
    required_data: int,
    reason: str,
    symbol: Optional[str] = None,
    **kwargs
):
    """记录降级事件（便捷函数）

    Args:
        factor_name: 因子名称
        level: 降级级别
        confidence: 置信度
        actual_data: 实际数据量
        required_data: 要求数据量
        reason: 降级原因
        symbol: 交易对（可选）
        **kwargs: 额外信息
    """
    monitor = get_global_monitor()
    monitor.record_event(
        factor_name=factor_name,
        level=level,
        confidence=confidence,
        actual_data=actual_data,
        required_data=required_data,
        reason=reason,
        symbol=symbol,
        additional_info=kwargs
    )


def get_degradation_stats(
    factor_name: Optional[str] = None,
    last_n_hours: Optional[int] = None
) -> Dict[str, Any]:
    """获取降级统计信息（便捷函数）

    Args:
        factor_name: 因子名称（可选）
        last_n_hours: 时间范围（小时，可选）

    Returns:
        统计信息字典
    """
    monitor = get_global_monitor()
    return monitor.get_stats(
        factor_name=factor_name,
        last_n_hours=last_n_hours
    )
