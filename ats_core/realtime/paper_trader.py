# coding: utf-8
"""
PaperTrader - Real-Time Paper Trading控制器

职责：
- 协调DataFeed、PaperBroker、StateManager
- 每个1m bar完成时检查信号
- 提交订单并监控执行
- 定期保存状态和生成报告

架构：
    DataFeed (WebSocket) → Kline完成 → 信号分析 → PaperBroker → StateManager

Version: v1.0.0
Standard: SYSTEM_ENHANCEMENT_STANDARD.md v3.3.0
"""

from __future__ import annotations

import asyncio
import logging
import signal
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from ats_core.broker.base import (
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
)
from ats_core.broker.paper_broker import PaperBroker
from ats_core.realtime.data_feed import DataFeed
from ats_core.realtime.state_manager import StateManager
from ats_core.cfg import CFG
from ats_core.pipeline.analyze_symbol import analyze_symbol_with_preloaded_klines

logger = logging.getLogger(__name__)


class PaperTrader:
    """
    Real-Time Paper Trading控制器

    配置从config/params.json的paper_trading读取
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化PaperTrader

        Args:
            config: Paper Trading配置（默认从CFG读取）
        """
        # 加载配置
        if config is None:
            config = CFG.params.get("paper_trading", {})

        self.config = config
        self.enabled = config.get("enabled", True)
        self.symbols = config.get("symbols", ["BNBUSDT"])
        self.interval = config.get("interval", "1h")
        self.initial_equity = config.get("initial_equity", 100000)

        # 风险配置
        risk_config = config.get("risk", {})
        self.per_trade_risk_pct = risk_config.get("per_trade_risk_pct", 0.01)
        self.max_concurrent_positions = risk_config.get("max_concurrent_positions", 3)
        self.max_daily_trades = risk_config.get("max_daily_trades", 10)
        self.max_drawdown_percent = risk_config.get("max_drawdown_percent", 5.0)

        # 初始化组件
        self.broker = PaperBroker(
            config.get("execution", {}),
            initial_equity=self.initial_equity
        )

        self.data_feed = DataFeed(
            config.get("data_feed", {}),
            symbols=self.symbols
        )

        self.state_manager = StateManager(
            config.get("reporting", {})
        )

        # 设置回调
        self.data_feed.set_callbacks(
            on_kline=self._on_kline_complete,
            on_price=self._on_price_update
        )

        # 运行状态
        self._running = False
        self._daily_trades = 0
        self._last_daily_reset = 0

        # 信号冷却（防止同一symbol短时间内重复信号）
        self._signal_cooldowns: Dict[str, int] = {}
        self._cooldown_minutes = 60  # 1小时冷却

        logger.info(
            f"PaperTrader初始化: "
            f"symbols={self.symbols}, "
            f"initial_equity={self.initial_equity}, "
            f"max_positions={self.max_concurrent_positions}"
        )

    async def start(self) -> None:
        """启动Paper Trading"""
        if not self.enabled:
            logger.warning("Paper Trading未启用")
            return

        self._running = True
        logger.info("=" * 60)
        logger.info("🚀 Paper Trading启动")
        logger.info("=" * 60)

        # 尝试恢复状态
        saved_state = self.state_manager.load_state()
        if saved_state:
            self.broker.load_state(saved_state)
            logger.info("已恢复上次状态")

        # 预加载历史数据
        logger.info("预加载历史K线数据...")
        await self.data_feed.preload_history(interval="1m")

        buffer_status = self.data_feed.get_buffer_status()
        for symbol, count in buffer_status.items():
            logger.info(f"  {symbol}: {count}条K线")

        # 设置信号处理
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

        # 启动数据流
        logger.info("连接实时数据源...")
        try:
            await self.data_feed.start()
        except Exception as e:
            logger.error(f"数据源异常: {e}")
            await self.stop()

    async def stop(self) -> None:
        """停止Paper Trading"""
        if not self._running:
            return

        self._running = False
        logger.info("正在停止Paper Trading...")

        # 停止数据流
        await self.data_feed.stop()

        # 保存最终状态
        self.state_manager.save_state(self.broker.save_state(), force=True)

        # 打印最终报告
        self._print_final_report()

        logger.info("Paper Trading已停止")

    def _on_price_update(self, symbol: str, price: float, timestamp: int) -> None:
        """
        价格更新回调

        传递给Broker检查订单成交和SL/TP
        """
        # 更新Broker
        self.broker.on_price_update(symbol, price, timestamp)
        self.broker.on_time(timestamp)

        # 定期保存状态
        self.state_manager.save_state(self.broker.save_state())

        # 定期打印状态
        if self.state_manager.should_log_status():
            self._log_status()

    def _on_kline_complete(self, symbol: str, kline: Dict[str, Any]) -> None:
        """
        K线完成回调

        每个1m bar完成时检查是否需要重新评估信号
        对于1h interval，每60个1m bar评估一次
        """
        # 检查是否是整点（对于1h interval）
        if self.interval == "1h":
            # 每60分钟评估一次
            close_time = kline["close_time"]
            minutes = (close_time // 60000) % 60
            if minutes != 0:
                return

        # 重置每日交易计数
        self._check_daily_reset()

        # 检查交易限制
        if self._daily_trades >= self.max_daily_trades:
            logger.debug(f"已达每日交易上限: {self._daily_trades}")
            return

        # 检查最大持仓数
        account = self.broker.get_account_state()
        if len(account.open_positions) >= self.max_concurrent_positions:
            logger.debug(f"已达最大持仓数: {len(account.open_positions)}")
            return

        # 检查最大回撤
        drawdown_pct = (self.initial_equity - account.equity) / self.initial_equity * 100
        if drawdown_pct >= self.max_drawdown_percent:
            logger.warning(f"已达最大回撤: {drawdown_pct:.2f}%")
            return

        # 检查信号冷却
        current_ts = int(time.time() * 1000)
        cooldown_ts = self._signal_cooldowns.get(symbol, 0)
        if current_ts < cooldown_ts:
            logger.debug(f"{symbol} 在信号冷却期内")
            return

        # 分析信号
        try:
            self._analyze_and_trade(symbol, current_ts)
        except Exception as e:
            logger.error(f"信号分析异常: {symbol} - {e}")

    def _analyze_and_trade(self, symbol: str, timestamp: int) -> None:
        """
        分析信号并执行交易

        Args:
            symbol: 交易对
            timestamp: 当前时间戳
        """
        # 获取K线数据
        klines = self.data_feed.get_klines(symbol, limit=300)
        if len(klines) < 24:
            logger.warning(f"{symbol} K线数据不足: {len(klines)}")
            return

        # 转换为1h K线（聚合1m → 1h）
        hourly_klines = self._aggregate_to_hourly(klines)
        if len(hourly_klines) < 24:
            logger.warning(f"{symbol} 1h K线不足: {len(hourly_klines)}")
            return

        # 调用四步系统分析
        logger.info(f"🔍 分析信号: {symbol}")
        analysis_result = analyze_symbol_with_preloaded_klines(
            symbol=symbol,
            preloaded_klines=hourly_klines,
            params=CFG.params
        )

        # 检查是否有有效信号
        four_step = analysis_result.get("four_step_decision", {})
        if not four_step or four_step.get("decision") != "ACCEPT":
            reject_reason = four_step.get("reject_reason", "无信号")
            logger.debug(f"{symbol} 无信号: {reject_reason}")
            return

        # 提取交易参数
        action = four_step.get("action")  # "LONG" or "SHORT"
        entry_price = four_step.get("entry_price", 0)
        stop_loss = four_step.get("stop_loss", 0)
        take_profit = four_step.get("take_profit", 0)

        if not entry_price or not stop_loss or not take_profit:
            logger.warning(f"{symbol} 信号价格无效")
            return

        # 计算仓位大小
        account = self.broker.get_account_state()
        risk_amount = account.equity * self.per_trade_risk_pct

        if action == "LONG":
            risk_per_unit = entry_price - stop_loss
        else:
            risk_per_unit = stop_loss - entry_price

        if risk_per_unit <= 0:
            logger.warning(f"{symbol} 风险计算无效: {risk_per_unit}")
            return

        quantity = risk_amount / risk_per_unit

        # 创建订单
        order_id = str(uuid.uuid4())[:8]
        expire_at = timestamp + (self.broker.max_entry_minutes * 60 * 1000)

        order = Order(
            id=order_id,
            symbol=symbol,
            side=OrderSide.BUY if action == "LONG" else OrderSide.SELL,
            type=OrderType.LIMIT,
            price=entry_price,
            quantity=quantity,
            created_at=timestamp,
            expire_at=expire_at,
            tag="ENTRY",
            metadata={
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "step1_result": four_step.get("step1_direction", {}),
                "step2_result": four_step.get("step2_timing", {}),
                "step3_result": four_step.get("step3_risk", {}),
                "step4_result": four_step.get("step4_quality", {}),
                "factor_scores": analysis_result.get("scores", {}),
            }
        )

        # 提交订单
        self.broker.submit_order(order)

        # 设置信号冷却
        cooldown_ms = self._cooldown_minutes * 60 * 1000
        self._signal_cooldowns[symbol] = timestamp + cooldown_ms

        # 增加交易计数
        self._daily_trades += 1

        # 记录日志
        self.state_manager.log_position_open(
            position_id=order_id,
            symbol=symbol,
            direction=action,
            entry_price=entry_price,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
            metadata={"order_id": order_id}
        )

        logger.info(
            f"📤 订单提交: {symbol} {action} "
            f"{quantity:.4f}@{entry_price:.2f} "
            f"SL={stop_loss:.2f} TP={take_profit:.2f}"
        )

    def _aggregate_to_hourly(self, klines_1m: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        将1m K线聚合为1h K线

        Args:
            klines_1m: 1分钟K线数据

        Returns:
            1小时K线数据
        """
        if not klines_1m:
            return []

        hourly = []
        current_hour = None
        current_bar = None

        for kline in klines_1m:
            # 计算所属小时
            hour_ts = (kline["open_time"] // 3600000) * 3600000

            if current_hour != hour_ts:
                # 保存上一个小时的bar
                if current_bar:
                    hourly.append(current_bar)

                # 开始新的小时bar
                current_hour = hour_ts
                current_bar = {
                    "open_time": hour_ts,
                    "open": kline["open"],
                    "high": kline["high"],
                    "low": kline["low"],
                    "close": kline["close"],
                    "volume": kline["volume"],
                    "close_time": hour_ts + 3600000 - 1,
                    "quote_volume": kline.get("quote_volume", 0),
                    "trades": kline.get("trades", 0),
                }
            else:
                # 更新当前小时bar
                current_bar["high"] = max(current_bar["high"], kline["high"])
                current_bar["low"] = min(current_bar["low"], kline["low"])
                current_bar["close"] = kline["close"]
                current_bar["volume"] += kline["volume"]
                current_bar["quote_volume"] += kline.get("quote_volume", 0)
                current_bar["trades"] += kline.get("trades", 0)

        # 添加最后一个bar
        if current_bar:
            hourly.append(current_bar)

        return hourly

    def _check_daily_reset(self) -> None:
        """检查是否需要重置每日交易计数"""
        current_day = int(time.time() // 86400)
        if current_day > self._last_daily_reset:
            self._daily_trades = 0
            self._last_daily_reset = current_day
            logger.info("每日交易计数已重置")

    def _log_status(self) -> None:
        """打印当前状态"""
        account = self.broker.get_account_state()
        summary = self.state_manager.get_summary()

        logger.info("=" * 50)
        logger.info("📊 Paper Trading状态报告")
        logger.info("=" * 50)
        logger.info(f"权益: ${account.equity:.2f}")
        logger.info(f"余额: ${account.balance:.2f}")
        logger.info(f"未实现盈亏: ${account.unrealized_pnl:.2f}")
        logger.info(f"已实现盈亏: ${account.realized_pnl:.2f}")
        logger.info(f"手续费: ${account.fees_paid:.2f}")
        logger.info(f"开仓持仓: {len(account.open_positions)}")
        logger.info(f"待成交订单: {len(account.open_orders)}")
        logger.info(f"总交易次数: {summary['total_trades']}")
        logger.info(f"胜率: {summary['win_rate']*100:.1f}%")
        logger.info("=" * 50)

    def _print_final_report(self) -> None:
        """打印最终报告"""
        account = self.broker.get_account_state()
        summary = self.state_manager.get_summary()

        total_return = (account.equity - self.initial_equity) / self.initial_equity * 100

        logger.info("")
        logger.info("=" * 60)
        logger.info("📈 Paper Trading最终报告")
        logger.info("=" * 60)
        logger.info(f"初始权益: ${self.initial_equity:.2f}")
        logger.info(f"最终权益: ${account.equity:.2f}")
        logger.info(f"总收益率: {total_return:+.2f}%")
        logger.info(f"已实现盈亏: ${account.realized_pnl:.2f}")
        logger.info(f"总手续费: ${account.fees_paid:.2f}")
        logger.info("-" * 60)
        logger.info(f"总交易次数: {summary['total_trades']}")
        logger.info(f"盈利次数: {summary['wins']}")
        logger.info(f"亏损次数: {summary['losses']}")
        logger.info(f"胜率: {summary['win_rate']*100:.1f}%")
        logger.info("-" * 60)
        logger.info(f"状态文件: {summary['state_file']}")
        logger.info(f"交易日志: {summary['trade_log_file']}")
        logger.info("=" * 60)


async def run_paper_trader(config: Optional[Dict[str, Any]] = None) -> None:
    """
    运行Paper Trader的便捷函数

    Args:
        config: 配置（可选）
    """
    trader = PaperTrader(config)
    await trader.start()
