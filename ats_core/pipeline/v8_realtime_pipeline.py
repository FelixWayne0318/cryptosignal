# coding: utf-8
"""
V8实时交易管道

将所有V8组件有机融合：
    Cryptofeed → RealtimeFactorCalculator → Decision → Execution → Storage

数据流：
    1. Cryptofeed WebSocket接收trades/orderbook
    2. RealtimeFactorCalculator计算实时因子
    3. DecisionEngine生成交易信号
    4. CcxtExecutor执行订单
    5. CryptostoreAdapter持久化数据

Version: v8.0.0
Standard: SYSTEM_ENHANCEMENT_STANDARD.md v3.3.0
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from ats_core.config.threshold_config import get_thresholds
from ats_core.realtime.factor_calculator import (
    RealtimeFactorCalculator,
    RealtimeFactors,
    TradeData,
    OrderbookData,
)

logger = logging.getLogger(__name__)


@dataclass
class V8Signal:
    """V8系统生成的交易信号"""
    symbol: str
    timestamp: float
    direction: str  # 'long' or 'short'
    strength: float  # 0-100
    confidence: float  # 0-1
    factors: RealtimeFactors
    meta: Dict[str, Any] = field(default_factory=dict)


class V8RealtimePipeline:
    """
    V8实时交易管道

    整合所有V8组件，提供完整的实时交易流程。

    配置从config/signal_thresholds.json的v8_integration读取。
    """

    def __init__(self, symbols: List[str], config: Optional[Dict[str, Any]] = None):
        """
        初始化V8管道

        Args:
            symbols: 交易对列表
            config: 可选配置覆盖
        """
        # 加载配置
        thresholds = get_thresholds()
        v8_config = thresholds.get_all().get("v8_integration", {})

        # 合并配置
        self.config = {**v8_config, **(config or {})}
        self.symbols = [s.upper() for s in symbols]

        # 配置参数
        pipeline_cfg = self.config.get("decision_pipeline", {})
        self.signal_interval_ms = pipeline_cfg.get("signal_evaluation_interval_ms", 5000)
        self.min_confidence = pipeline_cfg.get("min_confidence_for_signal", 0.6)
        self.use_v72_gates = pipeline_cfg.get("use_v72_gates", True)
        self.auto_execute = pipeline_cfg.get("auto_execute", False)

        exec_cfg = self.config.get("execution_layer", {})
        self.dry_run = exec_cfg.get("dry_run", True)
        self.executor_type = exec_cfg.get("executor_type", "ccxt")

        storage_cfg = self.config.get("storage_layer", {})
        self.storage_enabled = storage_cfg.get("enabled", True)
        self.storage_path = storage_cfg.get("storage_path", "data/v8_storage")

        # 初始化组件
        self._init_components()

        # 回调函数
        self._on_signal_callback: Optional[Callable[[V8Signal], None]] = None

        # 运行状态
        self._running = False
        self._last_signal_time: Dict[str, float] = {}

        logger.info(
            f"V8RealtimePipeline初始化: symbols={symbols}, "
            f"dry_run={self.dry_run}, auto_execute={self.auto_execute}"
        )

    def _init_components(self) -> None:
        """初始化各组件"""
        # 1. 实时因子计算器
        factor_cfg = self.config.get("realtime_factor", {})
        self.factor_calculator = RealtimeFactorCalculator(
            self.symbols, factor_cfg
        )
        self.factor_calculator.set_callback(self._on_factors_update)

        # 2. 执行器（延迟初始化）
        self.executor = None

        # 3. 存储适配器（延迟初始化）
        self.storage = None

        # 4. Cryptofeed流（延迟初始化）
        self.stream = None

    def set_signal_callback(self, callback: Callable[[V8Signal], None]) -> None:
        """
        设置信号生成回调

        Args:
            callback: 信号回调函数
        """
        self._on_signal_callback = callback

    def _on_factors_update(self, factors: RealtimeFactors) -> None:
        """
        因子更新回调

        Args:
            factors: 新计算的因子
        """
        # 检查信号间隔
        now = time.time()
        last_time = self._last_signal_time.get(factors.symbol, 0)
        if (now - last_time) * 1000 < self.signal_interval_ms:
            return

        # 生成信号
        signal = self._evaluate_signal(factors)
        if signal is None:
            return

        self._last_signal_time[factors.symbol] = now

        # 存储信号
        if self.storage_enabled:
            self._store_signal(signal)

        # 触发回调
        if self._on_signal_callback:
            try:
                self._on_signal_callback(signal)
            except Exception as e:
                logger.error(f"信号回调异常: {e}")

        # 自动执行
        if self.auto_execute and not self.dry_run:
            self._execute_signal(signal)

    def _evaluate_signal(self, factors: RealtimeFactors) -> Optional[V8Signal]:
        """
        根据因子评估是否生成信号

        Args:
            factors: 实时因子

        Returns:
            V8Signal或None
        """
        # 简化的信号生成逻辑
        # 实际应该调用完整的v72决策管道

        # 方向判断：基于CVD和OBI
        cvd_z = factors.cvd_z
        obi = factors.obi

        if cvd_z > 1.0 and obi > 0.2:
            direction = "long"
            strength = min(100, (cvd_z * 20 + obi * 100))
        elif cvd_z < -1.0 and obi < -0.2:
            direction = "short"
            strength = min(100, (abs(cvd_z) * 20 + abs(obi) * 100))
        else:
            return None

        # 信心度计算
        # 基于多个因子的综合评估
        confidence = self._calculate_confidence(factors, direction)

        if confidence < self.min_confidence:
            return None

        return V8Signal(
            symbol=factors.symbol,
            timestamp=factors.timestamp,
            direction=direction,
            strength=strength,
            confidence=confidence,
            factors=factors,
            meta={
                "source": "v8_realtime",
                "cvd_z": cvd_z,
                "obi": obi,
            }
        )

    def _calculate_confidence(
        self, factors: RealtimeFactors, direction: str
    ) -> float:
        """
        计算信号信心度

        Args:
            factors: 实时因子
            direction: 信号方向

        Returns:
            信心度 (0-1)
        """
        confidence = 0.5  # 基础信心度

        # CVD Z-score贡献
        cvd_contribution = min(0.2, abs(factors.cvd_z) * 0.1)
        confidence += cvd_contribution

        # OBI贡献
        obi_contribution = min(0.15, abs(factors.obi) * 0.5)
        confidence += obi_contribution

        # 深度平衡贡献
        if factors.bid_depth > 0 and factors.ask_depth > 0:
            depth_ratio = factors.bid_depth / factors.ask_depth
            if direction == "long" and depth_ratio > 1.2:
                confidence += 0.1
            elif direction == "short" and depth_ratio < 0.8:
                confidence += 0.1

        # Spread惩罚
        if factors.spread_bps > 10:
            confidence -= 0.05
        if factors.spread_bps > 20:
            confidence -= 0.1

        return max(0.0, min(1.0, confidence))

    def _store_signal(self, signal: V8Signal) -> None:
        """
        存储信号到Cryptostore

        Args:
            signal: 交易信号
        """
        try:
            # 延迟导入避免循环依赖
            if self.storage is None:
                from cs_ext.storage.cryptostore_adapter import CryptostoreAdapter
                self.storage = CryptostoreAdapter(base_path=self.storage_path)

            self.storage.store_signal(
                ts=signal.timestamp,
                symbol=signal.symbol,
                direction=signal.direction,
                strength=signal.strength,
                probability=signal.confidence,
                extra={
                    "cvd_z": signal.factors.cvd_z,
                    "obi": signal.factors.obi,
                    "source": "v8_realtime",
                }
            )
        except Exception as e:
            logger.error(f"存储信号失败: {e}")

    def _execute_signal(self, signal: V8Signal) -> None:
        """
        执行信号

        Args:
            signal: 交易信号
        """
        try:
            # 延迟导入避免循环依赖
            if self.executor is None:
                import os
                from cs_ext.execution.ccxt_executor import CcxtExecutor
                from cs_ext.api.ccxt_wrapper import CcxtExchange

                exec_cfg = self.config.get("execution_layer", {})

                # 从环境变量加载API密钥
                api_key = os.environ.get("BINANCE_API_KEY", "")
                api_secret = os.environ.get("BINANCE_API_SECRET", "")

                if not api_key or not api_secret:
                    logger.warning("未设置BINANCE_API_KEY/BINANCE_API_SECRET，执行功能受限")

                exchange = CcxtExchange(
                    "binanceusdm",  # 使用USDT永续合约
                    api_key=api_key,
                    secret=api_secret,
                )
                self.executor = CcxtExecutor(
                    exchange=exchange,
                    dry_run=self.dry_run,
                    max_order_value=exec_cfg.get("max_order_value_usdt", 1000.0),
                )

            # 转换为执行信号
            from cs_ext.execution.ccxt_executor import ExecutionSignal
            exec_signal = ExecutionSignal(
                symbol=signal.symbol.replace("-PERP", ""),
                side="buy" if signal.direction == "long" else "sell",
                order_type="market",
                quantity=0.001,  # 最小量，实际应根据仓位管理计算
                signal_id=f"v8_{int(signal.timestamp)}",
            )

            self.executor.submit(exec_signal)
            logger.info(f"信号已提交执行: {signal.symbol} {signal.direction}")

        except Exception as e:
            logger.error(f"执行信号失败: {e}")

    async def start(self) -> None:
        """
        启动V8管道

        连接Cryptofeed并开始处理数据。
        """
        if self._running:
            logger.warning("V8管道已在运行")
            return

        self._running = True
        logger.info("V8管道启动...")

        try:
            # 导入Cryptofeed组件
            from cs_ext.data.cryptofeed_stream import CryptofeedStream

            # 转换符号格式
            cf_symbols = [s.replace("USDT", "-USDT-PERP") for s in self.symbols]

            # 创建Cryptofeed流
            stream_cfg = self.config.get("cryptofeed_stream", {})
            self.stream = CryptofeedStream(
                symbols=cf_symbols,
                on_trade=self._handle_trade,
                on_orderbook=self._handle_orderbook,
                max_depth=stream_cfg.get("max_depth", 50),
            )

            # 启动流
            self.stream.run_forever()

        except ImportError as e:
            logger.error(f"无法导入Cryptofeed组件: {e}")
            raise
        except Exception as e:
            logger.error(f"V8管道启动失败: {e}")
            raise
        finally:
            self._running = False

    def _handle_trade(self, evt) -> None:
        """
        处理Cryptofeed成交事件

        Args:
            evt: TradeEvent from CryptofeedStream
        """
        try:
            trade = TradeData(
                symbol=evt.symbol,
                timestamp=evt.ts,
                price=evt.price,
                size=evt.size,
                side=evt.side,
            )
            self.factor_calculator.on_trade(trade)

            # 存储成交数据
            if self.storage_enabled:
                self._store_trade(trade)

        except Exception as e:
            logger.error(f"处理成交数据异常: {e}")

    def _handle_orderbook(self, evt) -> None:
        """
        处理Cryptofeed订单簿事件

        Args:
            evt: OrderBookEvent from CryptofeedStream
        """
        try:
            ob = OrderbookData(
                symbol=evt.symbol,
                timestamp=evt.ts,
                bids=evt.bids,
                asks=evt.asks,
            )
            self.factor_calculator.on_orderbook(ob)

        except Exception as e:
            logger.error(f"处理订单簿数据异常: {e}")

    def _store_trade(self, trade: TradeData) -> None:
        """存储成交数据"""
        try:
            if self.storage is None:
                from cs_ext.storage.cryptostore_adapter import CryptostoreAdapter
                self.storage = CryptostoreAdapter(base_path=self.storage_path)

            self.storage.store_trade(
                ts=trade.timestamp,
                symbol=trade.symbol,
                price=trade.price,
                size=trade.size,
                side=trade.side,
            )
        except Exception as e:
            logger.debug(f"存储成交数据失败: {e}")

    def stop(self) -> None:
        """停止V8管道"""
        self._running = False
        logger.info("V8管道已停止")

    def get_status(self) -> Dict[str, Any]:
        """
        获取管道状态

        Returns:
            状态信息字典
        """
        factors = self.factor_calculator.get_all_factors()

        return {
            "running": self._running,
            "symbols": self.symbols,
            "dry_run": self.dry_run,
            "auto_execute": self.auto_execute,
            "factors": {
                s: {
                    "cvd_z": f.cvd_z,
                    "obi": f.obi,
                    "trade_intensity": f.trade_intensity,
                    "spread_bps": f.spread_bps,
                }
                for s, f in factors.items()
            },
            "last_signal_time": self._last_signal_time,
        }


def run_v8_pipeline(symbols: List[str], config: Optional[Dict[str, Any]] = None) -> None:
    """
    运行V8实时交易管道

    Args:
        symbols: 交易对列表
        config: 可选配置覆盖
    """
    import asyncio

    pipeline = V8RealtimePipeline(symbols, config)

    # 设置信号回调（打印信号）
    def on_signal(signal: V8Signal):
        print(f"[V8 Signal] {signal.symbol} {signal.direction.upper()} "
              f"strength={signal.strength:.1f} confidence={signal.confidence:.2f}")

    pipeline.set_signal_callback(on_signal)

    # 运行管道
    try:
        asyncio.run(pipeline.start())
    except KeyboardInterrupt:
        pipeline.stop()
        print("V8管道已停止")
