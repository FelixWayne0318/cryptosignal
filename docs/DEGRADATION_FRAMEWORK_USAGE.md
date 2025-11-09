# 统一降级策略框架使用指南

**版本**: v3.1
**创建日期**: 2025-11-09
**状态**: ✅ 可用

---

## 📖 概述

本文档介绍如何使用v3.1版本的统一降级策略框架，包括：
1. **三级降级策略**: 自动根据数据量计算置信度
2. **降级监控**: 全局记录和统计降级事件
3. **标准化元数据**: 统一的降级诊断信息

---

## 🎯 核心概念

### 三级降级策略

| 级别 | 数据充足率 | 置信度 | 行为 | 适用场景 |
|------|-----------|--------|------|---------|
| **NORMAL** (正常) | ≥ 100% | 1.0 | 正常计算 | 数据充足 |
| **WARNING** (警告) | 75%-100% | 0.75-1.0 | 计算 + 置信度加权 | 数据略少 |
| **DEGRADED** (降级) | 50%-75% | 0.5-0.75 | 计算 + 强降权 | 数据不足 |
| **DISABLED** (禁用) | < 50% | 0.0 | 返回0分 | 数据极少 |

### 置信度计算

```
confidence = f(actual_data / min_required)

- 100%+  → 1.0   (正常)
- 75-100% → 0.75-1.0 (线性插值)
- 50-75%  → 0.5-0.75 (线性插值)
- <50%    → 0.0   (禁用)

adjusted_score = raw_score × confidence
```

---

## 🚀 快速开始

### 方法1: 使用DegradationManager（推荐）

适用于需要完整降级管理的因子。

```python
from ats_core.utils.degradation import DegradationManager
from ats_core.monitoring import record_degradation

def score_my_factor(data, params=None):
    """示例因子评分函数"""

    # 1. 创建降级管理器
    manager = DegradationManager(
        factor_name="MY_FACTOR",
        min_data_required=20  # 最小数据要求
    )

    # 2. 评估数据质量
    result = manager.evaluate(
        actual_data_points=len(data),
        raw_score=0.0  # 数据不足时的默认分数
    )

    # 3. 如果降级，直接返回
    if result.level.value != "normal":
        # 记录降级事件（用于监控）
        record_degradation(
            factor_name="MY_FACTOR",
            level=result.level.value,
            confidence=result.confidence,
            actual_data=len(data),
            required_data=20,
            reason=result.degradation_reason
        )

        # 返回 (score, metadata)
        return 0, result.to_dict()

    # 4. 数据充足，正常计算
    # ... 计算逻辑 ...
    raw_score = calculate_score(data)

    # 5. 应用置信度加权（即使在NORMAL级别也可以）
    result = manager.evaluate(
        actual_data_points=len(data),
        raw_score=raw_score
    )

    # 6. 返回调整后的分数
    return int(result.adjusted_score), result.to_dict()
```

### 方法2: 使用便捷函数（简化版）

适用于简单的数据检查场景。

```python
from ats_core.utils.degradation import (
    calculate_confidence_from_data_ratio,
    create_degradation_metadata
)

def score_simple_factor(data, min_required=20):
    """简化版因子评分函数"""

    # 1. 检查数据充足性
    if len(data) < min_required * 0.5:  # <50%: 禁用
        return 0, create_degradation_metadata(
            reason="insufficient_data",
            min_required=min_required,
            actual=len(data),
            confidence=0.0
        )

    # 2. 计算置信度
    confidence = calculate_confidence_from_data_ratio(
        actual=len(data),
        required=min_required
    )

    # 3. 正常计算
    raw_score = calculate_score(data)

    # 4. 应用置信度加权
    adjusted_score = raw_score * confidence

    # 5. 返回结果
    return int(adjusted_score), {
        "confidence": confidence,
        "raw_score": raw_score,
        "adjusted_score": adjusted_score,
        "degradation_reason": "partial_insufficient_data" if confidence < 1.0 else "none"
    }
```

---

## 📚 完整示例：重构M因子

以下是如何将现有的M因子重构为使用新框架：

### 重构前（v3.0）

```python
def score_momentum(h, l, c, params=None):
    # 数据检查
    if len(c) < min_data_points:
        return 0, {
            "slope_now": 0.0,
            "accel": 0.0,
            "slope_score": 0,
            "accel_score": 0,
            "degradation_reason": "insufficient_data",
            "min_data_required": min_data_points
        }

    # 正常计算
    # ... 计算逻辑 ...

    return M, meta
```

### 重构后（v3.1 - 可选升级）

```python
from ats_core.utils.degradation import DegradationManager
from ats_core.monitoring import record_degradation

def score_momentum(h, l, c, params=None):
    # 读取配置
    try:
        config = get_factor_config()
        min_data_points = config.get_data_quality_threshold("M", "min_data_points")
    except:
        min_data_points = 20

    # 创建降级管理器
    manager = DegradationManager(
        factor_name="M",
        min_data_required=min_data_points
    )

    # 评估数据质量
    degradation_result = manager.evaluate(
        actual_data_points=len(c),
        raw_score=0.0  # 默认分数
    )

    # 如果禁用，直接返回
    if degradation_result.level.value == "disabled":
        record_degradation(
            factor_name="M",
            level="disabled",
            confidence=0.0,
            actual_data=len(c),
            required_data=min_data_points,
            reason="insufficient_data"
        )

        return 0, {
            "slope_now": 0.0,
            "accel": 0.0,
            "slope_score": 0,
            "accel_score": 0,
            **degradation_result.to_dict()  # 包含降级信息
        }

    # 正常计算（即使在WARNING/DEGRADED级别）
    # ... 计算逻辑 ...
    slope_score = ...
    accel_score = ...
    M_raw = slope_weight * slope_score + accel_weight * accel_score

    # 应用StandardizationChain
    M_pub, diagnostics = standardization_chain.standardize(M_raw)

    # 应用置信度加权
    final_result = manager.evaluate(
        actual_data_points=len(c),
        raw_score=M_pub
    )

    # 记录降级事件（如果有）
    if final_result.level.value != "normal":
        record_degradation(
            factor_name="M",
            level=final_result.level.value,
            confidence=final_result.confidence,
            actual_data=len(c),
            required_data=min_data_points,
            reason=final_result.degradation_reason
        )

    # 返回调整后的分数
    return int(final_result.adjusted_score), {
        "slope_now": slope_now,
        "accel": accel,
        "slope_score": slope_score,
        "accel_score": accel_score,
        **final_result.to_dict()  # 包含置信度和降级信息
    }
```

**注**: 对于已经实现P0修复的因子，升级到v3.1框架是**可选**的。当前的降级处理已经足够，升级主要带来：
- 自动置信度加权（WARNING/DEGRADED级别）
- 全局降级监控
- 更详细的诊断信息

---

## 📊 降级监控使用

### 记录降级事件

```python
from ats_core.monitoring import record_degradation

# 在因子降级时记录
record_degradation(
    factor_name="M",
    level="degraded",  # normal/warning/degraded/disabled
    confidence=0.6,
    actual_data=12,
    required_data=20,
    reason="insufficient_data",
    symbol="BTCUSDT"  # 可选
)
```

### 查询降级统计

```python
from ats_core.monitoring import get_degradation_stats

# 获取M因子最近24小时的降级统计
stats = get_degradation_stats(factor_name="M", last_n_hours=24)

print(f"总降级次数: {stats['total_events']}")
print(f"平均置信度: {stats['avg_confidence']}")
print(f"按级别分组: {stats['by_level']}")
# 输出示例:
# 总降级次数: 15
# 平均置信度: 0.673
# 按级别分组: {'warning': 8, 'degraded': 5, 'disabled': 2}
```

### 导出降级报告

```python
from ats_core.monitoring import get_global_monitor

monitor = get_global_monitor()

# 导出JSON格式
monitor.export_to_json(
    file_path="/tmp/degradation_report.json",
    last_n_hours=24
)

# 导出CSV格式
monitor.export_to_csv(
    file_path="/tmp/degradation_report.csv",
    factor_name="M",
    last_n_hours=24
)
```

### 获取实时告警

```python
from ats_core.monitoring import get_global_monitor

monitor = get_global_monitor()

# 获取最近1小时的告警摘要
alert = monitor.get_alert_summary(threshold_hours=1)

print(alert["summary"])
# 输出示例:
# "🚨 严重: 2个因子完全禁用 | ⚠️ 警告: 3个因子降级"

# 检查严重降级的因子
for factor_info in alert["critical_factors"]:
    print(f"⚠️ {factor_info['factor']}: 禁用{factor_info['disabled_count']}次")
```

---

## 🔧 高级用法

### 自定义降级阈值

```python
from ats_core.utils.degradation import DegradationManager

# 为波动性大的因子使用更严格的阈值
manager = DegradationManager(
    factor_name="VOLATILE_FACTOR",
    min_data_required=30,
    warning_threshold=0.80,   # 80%才算正常（默认75%）
    degraded_threshold=0.60,  # 60%以下才降级（默认50%）
    disabled_threshold=0.60   # 60%以下禁用（默认50%）
)
```

### 自定义元数据

```python
result = manager.evaluate(
    actual_data_points=len(data),
    raw_score=score,
    additional_metadata={
        "algo_version": "v3.1",
        "market_regime": "volatile",
        "data_source": "binance"
    }
)

# result.metadata 将包含额外字段
```

### 批量评估多个因子

```python
from ats_core.utils.degradation import DegradationManager

factors = {
    "M": {"min_data": 20, "actual": 18, "score": 75},
    "V+": {"min_data": 25, "actual": 20, "score": 60},
    "C+": {"min_data": 7, "actual": 10, "score": 80}
}

results = {}
for name, config in factors.items():
    manager = DegradationManager(
        factor_name=name,
        min_data_required=config["min_data"]
    )

    result = manager.evaluate(
        actual_data_points=config["actual"],
        raw_score=config["score"]
    )

    results[name] = {
        "score": result.adjusted_score,
        "confidence": result.confidence,
        "level": result.level.value
    }

print(results)
# 输出:
# {
#     "M": {"score": 67.5, "confidence": 0.9, "level": "warning"},
#     "V+": {"score": 48.0, "confidence": 0.8, "level": "warning"},
#     "C+": {"score": 80.0, "confidence": 1.0, "level": "normal"}
# }
```

---

## ⚠️ 注意事项

### 1. 向后兼容性

新框架**完全向后兼容**。您可以：
- ✅ 继续使用P0修复的旧降级处理（已经足够）
- ✅ 选择性升级部分因子到v3.1框架
- ✅ 逐步迁移所有因子

### 2. 性能考虑

- `DegradationManager.evaluate()` 非常轻量（~0.1ms）
- 降级事件记录是异步的，不影响主流程
- 监控器自动清理旧事件（最多保留10000个）

### 3. 线程安全

- `DegradationMonitor` 使用Lock保护共享数据
- 可以在多线程环境中安全使用

### 4. 什么时候应该升级？

**建议升级**（使用v3.1框架）的场景：
- ✅ 新因子开发
- ✅ 需要细粒度置信度加权（WARNING级别不完全禁用）
- ✅ 需要降级监控和统计
- ✅ 需要A/B测试不同降级策略

**可以保持现状**（P0修复已足够）的场景：
- ✅ 现有因子运行稳定
- ✅ 只需要简单的数据检查（有/无）
- ✅ 不需要置信度加权

---

## 📋 元数据字段对比

### v3.0（P0修复后）

```python
{
    "degradation_reason": "insufficient_data",
    "min_data_required": 20,
    "actual_data_points": 5
}
```

### v3.1（新框架）

```python
{
    "degradation_level": "disabled",      # 新增：降级级别
    "confidence": 0.0,                    # 新增：置信度
    "raw_score": 0.0,                     # 新增：原始分数
    "adjusted_score": 0.0,                # 新增：调整后分数
    "degradation_reason": "insufficient_data",
    "min_data_required": 20,
    "actual_data_points": 5,
    "data_ratio": 0.25,                   # 新增：数据充足率
    "factor_name": "M"                    # 新增：因子名称
}
```

---

## 🧪 单元测试示例

```python
import unittest
from ats_core.utils.degradation import DegradationManager, DegradationLevel

class TestDegradationFramework(unittest.TestCase):

    def test_normal_level(self):
        """测试正常级别（100%数据）"""
        manager = DegradationManager("TEST", min_data_required=20)
        result = manager.evaluate(actual_data_points=20, raw_score=100)

        self.assertEqual(result.level, DegradationLevel.NORMAL)
        self.assertEqual(result.confidence, 1.0)
        self.assertEqual(result.adjusted_score, 100.0)

    def test_warning_level(self):
        """测试警告级别（75%-100%数据）"""
        manager = DegradationManager("TEST", min_data_required=20)
        result = manager.evaluate(actual_data_points=18, raw_score=100)  # 90%

        self.assertEqual(result.level, DegradationLevel.WARNING)
        self.assertGreater(result.confidence, 0.75)
        self.assertLess(result.confidence, 1.0)
        self.assertLess(result.adjusted_score, 100.0)

    def test_degraded_level(self):
        """测试降级级别（50%-75%数据）"""
        manager = DegradationManager("TEST", min_data_required=20)
        result = manager.evaluate(actual_data_points=12, raw_score=100)  # 60%

        self.assertEqual(result.level, DegradationLevel.DEGRADED)
        self.assertGreaterEqual(result.confidence, 0.5)
        self.assertLess(result.confidence, 0.75)

    def test_disabled_level(self):
        """测试禁用级别（<50%数据）"""
        manager = DegradationManager("TEST", min_data_required=20)
        result = manager.evaluate(actual_data_points=5, raw_score=100)  # 25%

        self.assertEqual(result.level, DegradationLevel.DISABLED)
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.adjusted_score, 0.0)

if __name__ == '__main__':
    unittest.main()
```

---

## 📖 相关文档

- `docs/DEGRADATION_STRATEGY_ANALYSIS.md` - 降级策略现状分析
- `docs/DEGRADATION_P0_FIXES_SUMMARY.md` - P0修复总结
- `ats_core/utils/degradation.py` - 降级框架源代码
- `ats_core/monitoring/degradation_monitor.py` - 监控系统源代码

---

## 🎉 总结

v3.1降级框架提供了：
1. ✅ **统一接口**: 所有因子使用相同的降级逻辑
2. ✅ **自动置信度**: 根据数据量自动计算置信度
3. ✅ **全局监控**: 记录和分析降级事件
4. ✅ **向后兼容**: 可选升级，不影响现有代码
5. ✅ **易于使用**: 便捷函数和管理器类

**下一步**:
- 在新因子开发时使用新框架
- 根据需要选择性升级现有因子
- 使用监控系统分析降级模式
- 根据生产数据调优降级阈值

---

**生成时间**: 2025-11-09
**作者**: Claude Code Agent
**版本**: v3.1
