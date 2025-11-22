# coding: utf-8
"""
V8 Backtest Pipeline - 完整回测管道
V8回测管道 - 集成CCXT + Cryptostore + CryptoSignal + Freqtrade

功能：
1. 使用V8BacktestDataLoader获取数据
2. 使用CryptoSignal进行信号分析
3. 支持内部引擎或Freqtrade引擎
4. 使用Cryptostore缓存结果

Standard: SYSTEM_ENHANCEMENT_STANDARD.md v3.3.0
Architecture: V8 六层架构
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from ats_core.config.threshold_config import get_thresholds
from ats_core.backtest.v8_data_loader import V8BacktestDataLoader
from ats_core.backtest.engine import BacktestEngine, BacktestResult
from ats_core.backtest.metrics import BacktestMetrics

logger = logging.getLogger(__name__)


class V8BacktestPipeline:
    """
    V8回测管道

    完整数据流:
    CCXT (数据获取) → Cryptostore (缓存) → CryptoSignal (分析) → Engine (回测) → Metrics (评估)

    配置来源: config/signal_thresholds.json -> v8_integration.backtest
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化V8回测管道

        Args:
            config: 可选的配置覆盖
        """
        # 加载配置
        thresholds = get_thresholds()
        v8_config = thresholds.get_all().get("v8_integration", {})
        backtest_config = v8_config.get("backtest", {})

        if config:
            self._merge_config(backtest_config, config)

        self.config = backtest_config

        # 引擎配置
        engine_config = self.config.get("engine", {})
        self.engine_type = engine_config.get("type", "internal")
        self.use_cryptosignal = engine_config.get("use_cryptosignal_strategy", True)
        self.default_timeframe = engine_config.get("default_timeframe", "1h")
        self.lookback_bars = engine_config.get("lookback_bars", 300)

        # 初始化组件
        self._data_loader = None
        self._engine = None
        self._metrics = None
        self._freqtrade_available = False

        self._init_components()

        logger.info(
            f"V8BacktestPipeline initialized: "
            f"engine={self.engine_type}, "
            f"cryptosignal={self.use_cryptosignal}"
        )

    def _merge_config(self, base: Dict, override: Dict) -> None:
        """递归合并配置"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def _init_components(self) -> None:
        """初始化管道组件"""
        # 初始化V8数据加载器
        self._data_loader = V8BacktestDataLoader(self.config)

        # 检查Freqtrade可用性
        if self.engine_type == "freqtrade":
            try:
                from cs_ext.backtest.freqtrade_bridge import CryptoSignalStrategy
                self._freqtrade_available = True
                logger.info("Freqtrade引擎可用")
            except ImportError as e:
                logger.warning(f"Freqtrade不可用，使用内部引擎: {e}")
                self._freqtrade_available = False
                self.engine_type = "internal"

        # 初始化内部引擎（作为默认或fallback）
        from ats_core.cfg import CFG
        params = CFG.get("params", {})
        engine_params = params.get("backtest", {}).get("engine", {})
        data_loader_params = params.get("backtest", {}).get("data_loader", {})

        # 使用传统数据加载器作为内部引擎的数据源
        from ats_core.backtest.data_loader import HistoricalDataLoader
        internal_data_loader = HistoricalDataLoader(data_loader_params)

        self._engine = BacktestEngine(engine_params, internal_data_loader)

        # 初始化指标计算器
        metrics_params = params.get("backtest", {}).get("metrics", {})
        self._metrics = BacktestMetrics(metrics_params)

    def run(
        self,
        symbols: List[str],
        start_time: datetime,
        end_time: datetime,
        timeframe: Optional[str] = None,
        use_v8_data: bool = True
    ) -> Dict[str, Any]:
        """
        执行V8回测

        Args:
            symbols: 交易对列表
            start_time: 开始时间
            end_time: 结束时间
            timeframe: K线周期 (默认从配置读取)
            use_v8_data: 是否使用V8数据加载器

        Returns:
            {
                "result": BacktestResult,
                "metrics": MetricsReport,
                "data_source": "v8" | "internal"
            }
        """
        timeframe = timeframe or self.default_timeframe

        logger.info(
            f"V8回测开始: symbols={symbols}, "
            f"time_range={start_time.isoformat()}-{end_time.isoformat()}, "
            f"timeframe={timeframe}, engine={self.engine_type}"
        )

        # 使用V8数据加载器预加载数据
        if use_v8_data:
            v8_data = self._data_loader.preload_data(
                symbols=symbols,
                start_time=start_time,
                end_time=end_time,
                timeframe=timeframe
            )

            if not v8_data:
                logger.warning("V8数据加载失败，回退到内部数据源")
                use_v8_data = False

        # 根据引擎类型执行回测
        if self.engine_type == "freqtrade" and self._freqtrade_available:
            result = self._run_freqtrade_backtest(
                symbols, start_time, end_time, timeframe
            )
        else:
            # 使用内部引擎
            # 转换datetime为毫秒时间戳
            start_ts = int(start_time.timestamp() * 1000)
            end_ts = int(end_time.timestamp() * 1000)

            result = self._engine.run(
                symbols=symbols,
                start_time=start_ts,
                end_time=end_ts,
                interval=timeframe
            )

        # 计算指标
        metrics_report = self._metrics.calculate_all_metrics(result)

        logger.info(
            f"V8回测完成: signals={result.total_signals}, "
            f"win_rate={metrics_report.signal_metrics.win_rate:.2f}%"
        )

        return {
            "result": result,
            "metrics": metrics_report,
            "data_source": "v8" if use_v8_data else "internal",
            "engine": self.engine_type
        }

    def _run_freqtrade_backtest(
        self,
        symbols: List[str],
        start_time: datetime,
        end_time: datetime,
        timeframe: str
    ) -> BacktestResult:
        """
        使用Freqtrade引擎执行回测

        Note: 这是一个占位实现，完整的Freqtrade集成需要更多配置
        """
        logger.info("使用Freqtrade引擎执行回测")

        # TODO: 完整的Freqtrade集成
        # 1. 生成Freqtrade配置文件
        # 2. 调用Freqtrade回测命令
        # 3. 解析Freqtrade结果

        # 当前回退到内部引擎
        logger.warning("Freqtrade完整集成待实现，使用内部引擎")
        # 转换datetime为毫秒时间戳
        start_ts = int(start_time.timestamp() * 1000)
        end_ts = int(end_time.timestamp() * 1000)

        return self._engine.run(
            symbols=symbols,
            start_time=start_ts,
            end_time=end_ts,
            interval=timeframe
        )

    def generate_report(
        self,
        result: Dict[str, Any],
        format: str = "json"
    ) -> str:
        """
        生成回测报告

        Args:
            result: run()的返回结果
            format: 报告格式 ("json" | "markdown")

        Returns:
            格式化的报告字符串
        """
        return self._metrics.generate_report(result["metrics"], format)

    def get_status(self) -> Dict[str, Any]:
        """获取管道状态"""
        return {
            "engine_type": self.engine_type,
            "freqtrade_available": self._freqtrade_available,
            "use_cryptosignal": self.use_cryptosignal,
            "data_loader": self._data_loader.get_status() if self._data_loader else None,
            "default_timeframe": self.default_timeframe,
            "lookback_bars": self.lookback_bars
        }


# 便捷函数
def run_v8_backtest(
    symbols: List[str],
    start_time: datetime,
    end_time: datetime,
    timeframe: str = "1h",
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    便捷函数：执行V8回测

    Args:
        symbols: 交易对列表
        start_time: 开始时间
        end_time: 结束时间
        timeframe: K线周期
        config: 可选配置覆盖

    Returns:
        回测结果字典
    """
    pipeline = V8BacktestPipeline(config)
    return pipeline.run(symbols, start_time, end_time, timeframe)
