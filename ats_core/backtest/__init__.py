# coding: utf-8
"""
Backtest Framework v1.0 - Module Initialization
回测框架 - 模块初始化

Public API:
- HistoricalDataLoader: 历史数据加载器
- BacktestEngine: 回测引擎
- BacktestMetrics: 性能评估器
- BacktestResult: 回测结果数据类
- SimulatedSignal: 模拟信号数据类
- MetricsReport: 指标报告数据类
- SignalMetrics: 信号级指标数据类
- StepMetrics: 步骤级指标数据类
- PortfolioMetrics: 组合级指标数据类
- DistributionMetrics: 分布分析指标数据类

Usage:
    from ats_core.backtest import (
        HistoricalDataLoader,
        BacktestEngine,
        BacktestMetrics
    )

    # 初始化组件
    data_loader = HistoricalDataLoader(config["backtest"]["data_loader"])
    engine = BacktestEngine(config["backtest"]["engine"], data_loader)
    metrics = BacktestMetrics(config["backtest"]["metrics"])

    # 执行回测
    result = engine.run(["ETHUSDT"], start_time, end_time)

    # 计算指标
    report = metrics.calculate_all_metrics(result)

    # 生成报告
    json_report = metrics.generate_report(report, "json")

Standard: SYSTEM_ENHANCEMENT_STANDARD.md v3.3.0
Design: docs/BACKTEST_FRAMEWORK_v1.0_DESIGN.md
"""

from ats_core.backtest.data_loader import HistoricalDataLoader
from ats_core.backtest.engine import (
    BacktestEngine,
    BacktestResult,
    SimulatedSignal
)
from ats_core.backtest.metrics import (
    BacktestMetrics,
    MetricsReport,
    SignalMetrics,
    StepMetrics,
    PortfolioMetrics,
    DistributionMetrics
)
from ats_core.backtest.v8_data_loader import (
    V8BacktestDataLoader,
    create_v8_data_loader
)

__version__ = "1.1.0"

__all__ = [
    # Core Classes
    "HistoricalDataLoader",
    "BacktestEngine",
    "BacktestMetrics",

    # V8 Classes
    "V8BacktestDataLoader",
    "create_v8_data_loader",

    # Data Classes
    "BacktestResult",
    "SimulatedSignal",
    "MetricsReport",
    "SignalMetrics",
    "StepMetrics",
    "PortfolioMetrics",
    "DistributionMetrics",
]
