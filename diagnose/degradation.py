# coding: utf-8
"""
统一降级策略框架（v3.1）

提供标准化的降级处理逻辑，包括：
- 三级降级策略（正常/警告/降级/禁用）
- 置信度计算
- 统一元数据结构
- 降级事件监控

使用示例：
    from ats_core.utils.degradation import DegradationManager, DegradationLevel

    manager = DegradationManager(
        factor_name="M",
        min_data_required=20
    )

    result = manager.evaluate(
        actual_data_points=15,
        raw_score=75.0
    )

    # result.level: DegradationLevel枚举
    # result.confidence: 0.0 - 1.0
    # result.adjusted_score: 经过置信度加权的分数
    # result.metadata: 完整诊断信息
"""

from enum import Enum
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
import time


class DegradationLevel(Enum):
    """降级级别枚举

    定义4个降级级别，从正常到完全禁用。
    """
    NORMAL = "normal"          # 正常：数据量充足
    WARNING = "warning"        # 警告：数据量略低于要求（75%-100%）
    DEGRADED = "degraded"      # 降级：数据量严重不足（50%-75%）
    DISABLED = "disabled"      # 禁用：数据量极低（<50%）


@dataclass
class DegradationResult:
    """降级评估结果

    包含降级级别、置信度、调整后分数和完整元数据。
    """
    level: DegradationLevel        # 降级级别
    confidence: float              # 置信度（0.0 - 1.0）
    raw_score: float               # 原始分数
    adjusted_score: float          # 置信度加权后的分数
    degradation_reason: str        # 降级原因（标准字段）
    metadata: Dict[str, Any]       # 完整元数据

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（用于返回）"""
        return {
            "degradation_level": self.level.value,
            "confidence": round(self.confidence, 3),
            "raw_score": round(self.raw_score, 2),
            "adjusted_score": round(self.adjusted_score, 2),
            "degradation_reason": self.degradation_reason,
            **self.metadata
        }


class DegradationManager:
    """降级策略管理器

    为单个因子提供统一的降级评估和置信度计算。

    三级降级策略：
    - Level 0 (NORMAL):    data >= 100% min_required → confidence = 1.0
    - Level 1 (WARNING):   75% <= data < 100%        → confidence = 0.75-1.0
    - Level 2 (DEGRADED):  50% <= data < 75%         → confidence = 0.5-0.75
    - Level 3 (DISABLED):  data < 50%                → confidence = 0.0

    Args:
        factor_name: 因子名称（如"M", "C+", "V+"等）
        min_data_required: 最小数据要求（如20个数据点）
        warning_threshold: 警告阈值（默认0.75，即75%）
        degraded_threshold: 降级阈值（默认0.50，即50%）
        disabled_threshold: 禁用阈值（默认0.50，低于此值返回0分）
    """

    def __init__(
        self,
        factor_name: str,
        min_data_required: int,
        warning_threshold: float = 0.75,
        degraded_threshold: float = 0.50,
        disabled_threshold: float = 0.50
    ):
        self.factor_name = factor_name
        self.min_data_required = min_data_required
        self.warning_threshold = warning_threshold
        self.degraded_threshold = degraded_threshold
        self.disabled_threshold = disabled_threshold

        # 降级事件记录（用于监控）
        self._degradation_events = []

    def evaluate(
        self,
        actual_data_points: int,
        raw_score: float = 0.0,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> DegradationResult:
        """评估数据质量并计算置信度

        Args:
            actual_data_points: 实际数据点数量
            raw_score: 原始分数（在数据充足时计算的分数）
            additional_metadata: 额外的元数据字段

        Returns:
            DegradationResult对象，包含降级级别、置信度和调整后分数
        """
        # 计算数据充足率
        data_ratio = actual_data_points / max(1, self.min_data_required)

        # 确定降级级别和置信度
        if data_ratio >= 1.0:
            # Level 0: 正常
            level = DegradationLevel.NORMAL
            confidence = 1.0
            reason = None
        elif data_ratio >= self.warning_threshold:
            # Level 1: 警告（75%-100%）
            level = DegradationLevel.WARNING
            # 线性插值: 75% → 0.75, 100% → 1.0
            confidence = 0.75 + 0.25 * ((data_ratio - self.warning_threshold) / (1.0 - self.warning_threshold))
            reason = "partial_insufficient_data"
        elif data_ratio >= self.degraded_threshold:
            # Level 2: 降级（50%-75%）
            level = DegradationLevel.DEGRADED
            # 线性插值: 50% → 0.5, 75% → 0.75
            confidence = 0.5 + 0.25 * ((data_ratio - self.degraded_threshold) / (self.warning_threshold - self.degraded_threshold))
            reason = "critical_insufficient_data"
        else:
            # Level 3: 禁用（<50%）
            level = DegradationLevel.DISABLED
            confidence = 0.0
            reason = "insufficient_data"

        # 计算置信度加权后的分数
        if level == DegradationLevel.DISABLED:
            # 完全禁用：返回0分
            adjusted_score = 0.0
        else:
            # 部分降级：应用置信度加权
            adjusted_score = raw_score * confidence

        # 构建元数据
        metadata = {
            "min_data_required": self.min_data_required,
            "actual_data_points": actual_data_points,
            "data_ratio": round(data_ratio, 3),
            "factor_name": self.factor_name,
        }

        # 合并额外元数据
        if additional_metadata:
            metadata.update(additional_metadata)

        # 创建结果对象
        result = DegradationResult(
            level=level,
            confidence=confidence,
            raw_score=raw_score,
            adjusted_score=adjusted_score,
            degradation_reason=reason if reason else "none",
            metadata=metadata
        )

        # 记录降级事件（用于监控）
        if level != DegradationLevel.NORMAL:
            self._record_degradation_event(result)

        return result

    def _record_degradation_event(self, result: DegradationResult):
        """记录降级事件（用于监控和统计）

        Args:
            result: 降级评估结果
        """
        event = {
            "timestamp": time.time(),
            "factor_name": self.factor_name,
            "level": result.level.value,
            "confidence": result.confidence,
            "data_ratio": result.metadata.get("data_ratio", 0.0),
            "reason": result.degradation_reason
        }
        self._degradation_events.append(event)

        # 限制事件记录数量（避免内存泄漏）
        if len(self._degradation_events) > 1000:
            self._degradation_events = self._degradation_events[-500:]

    def get_degradation_stats(self) -> Dict[str, Any]:
        """获取降级统计信息

        Returns:
            包含降级事件统计的字典
        """
        if not self._degradation_events:
            return {
                "total_events": 0,
                "by_level": {},
                "avg_confidence": 1.0
            }

        # 按级别统计
        by_level = {}
        total_confidence = 0.0

        for event in self._degradation_events:
            level = event["level"]
            by_level[level] = by_level.get(level, 0) + 1
            total_confidence += event["confidence"]

        return {
            "total_events": len(self._degradation_events),
            "by_level": by_level,
            "avg_confidence": total_confidence / len(self._degradation_events),
            "recent_events": self._degradation_events[-10:]  # 最近10个事件
        }

    def clear_stats(self):
        """清空统计数据"""
        self._degradation_events = []


# ========== 便捷函数 ==========

def create_degradation_metadata(
    reason: str,
    min_required: int,
    actual: int,
    confidence: float = 0.0,
    additional: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """创建标准化的降级元数据

    便捷函数，用于快速创建符合标准的降级元数据。

    Args:
        reason: 降级原因（如"insufficient_data"）
        min_required: 最小数据要求
        actual: 实际数据量
        confidence: 置信度（默认0.0）
        additional: 额外的元数据字段

    Returns:
        标准化的元数据字典

    Example:
        >>> meta = create_degradation_metadata(
        ...     reason="insufficient_data",
        ...     min_required=20,
        ...     actual=5,
        ...     additional={"slope": 0.0, "accel": 0.0}
        ... )
        >>> # Returns: {
        ...     "degradation_reason": "insufficient_data",
        ...     "min_data_required": 20,
        ...     "actual_data_points": 5,
        ...     "confidence": 0.0,
        ...     "slope": 0.0,
        ...     "accel": 0.0
        ... }
    """
    metadata = {
        "degradation_reason": reason,
        "min_data_required": min_required,
        "actual_data_points": actual,
        "confidence": round(confidence, 3)
    }

    if additional:
        metadata.update(additional)

    return metadata


def calculate_confidence_from_data_ratio(
    actual: int,
    required: int,
    warning_threshold: float = 0.75,
    degraded_threshold: float = 0.50
) -> float:
    """根据数据充足率计算置信度

    简化版的置信度计算函数，用于快速计算。

    Args:
        actual: 实际数据量
        required: 最小要求数据量
        warning_threshold: 警告阈值（默认0.75）
        degraded_threshold: 降级阈值（默认0.50）

    Returns:
        置信度（0.0 - 1.0）

    Example:
        >>> calculate_confidence_from_data_ratio(20, 20)  # 100%
        1.0
        >>> calculate_confidence_from_data_ratio(18, 20)  # 90%
        0.875
        >>> calculate_confidence_from_data_ratio(10, 20)  # 50%
        0.5
        >>> calculate_confidence_from_data_ratio(5, 20)   # 25%
        0.0
    """
    ratio = actual / max(1, required)

    if ratio >= 1.0:
        return 1.0
    elif ratio >= warning_threshold:
        # 线性插值: 75% → 0.75, 100% → 1.0
        return 0.75 + 0.25 * ((ratio - warning_threshold) / (1.0 - warning_threshold))
    elif ratio >= degraded_threshold:
        # 线性插值: 50% → 0.5, 75% → 0.75
        return 0.5 + 0.25 * ((ratio - degraded_threshold) / (warning_threshold - degraded_threshold))
    else:
        # < 50%: 禁用
        return 0.0
