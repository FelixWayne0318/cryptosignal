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

Version: v8.0.2
Standard: SYSTEM_ENHANCEMENT_STANDARD.md v3.3.0

Changelog v8.0.2:
    - 四步决策系统完整集成
    - CVD/OBI快速触发 + 四步验证双重模式
    - K线缓存支持
    - format_converter统一数据格式

Changelog v8.0.1:
    - 集成Telegram通知（使用render_signal_v72模板）
    - 添加mid_price到RealtimeFactors
    - 所有阈值从配置文件读取（零硬编码）
    - 修复executor.submit → submit_signal
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

# Telegram通知支持
try:
    from ats_core.outputs.telegram_fmt import render_signal_v72
    TELEGRAM_FMT_AVAILABLE = True
except ImportError:
    TELEGRAM_FMT_AVAILABLE = False

# 四步决策系统集成
try:
    from ats_core.decision.four_step_system import run_four_step_decision
    from ats_core.pipeline.analyze_symbol import analyze_symbol_with_preloaded_klines
    from ats_core.data.realtime_kline_cache import RealtimeKlineCache
    from ats_core.utils.format_converter import (
        normalize_symbol,
        four_step_to_decision_output,
        decision_to_telegram_dict,
    )
    FOUR_STEP_AVAILABLE = True
except ImportError as e:
    FOUR_STEP_AVAILABLE = False
    logger.warning(f"四步决策系统导入失败: {e}")

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
        self.exchange_id = exec_cfg.get("exchange_id", "binanceusdm")
        self.default_order_quantity = exec_cfg.get("default_order_quantity", 0.001)
        self.max_order_value = exec_cfg.get("max_order_value_usdt", 1000.0)

        storage_cfg = self.config.get("storage_layer", {})
        self.storage_enabled = storage_cfg.get("enabled", True)
        self.storage_path = storage_cfg.get("storage_path", "data/v8_storage")

        # 信号阈值配置（零硬编码）
        signal_thresholds = pipeline_cfg.get("signal_thresholds", {})
        self.cvd_z_threshold = signal_thresholds.get("cvd_z_threshold", 0.5)
        self.obi_threshold = signal_thresholds.get("obi_threshold", 0.1)
        self.base_confidence = signal_thresholds.get("base_confidence", 0.5)

        # Telegram配置
        telegram_cfg = pipeline_cfg.get("telegram_notification", {})
        self.telegram_enabled = telegram_cfg.get("enabled", True)
        self.use_v72_template = telegram_cfg.get("use_v72_template", True)

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

        # 5. Telegram配置（延迟初始化）
        self._telegram_bot_token = None
        self._telegram_chat_id = None
        self._telegram_initialized = False

        # 6. K线缓存（用于四步决策系统）
        self.kline_cache = None
        self._kline_cache_initialized = False

        # 7. 四步决策系统配置
        four_step_cfg = self.config.get("decision_pipeline", {}).get("four_step_integration", {})
        self.use_four_step = four_step_cfg.get("enabled", False) and FOUR_STEP_AVAILABLE
        self.four_step_fallback = four_step_cfg.get("fallback_to_simple", True)

        if self.use_four_step:
            logger.info("四步决策系统集成已启用")
        else:
            logger.info("使用简化CVD/OBI判断模式")

    def _init_telegram(self) -> None:
        """初始化Telegram配置"""
        if self._telegram_initialized:
            return

        if not self.telegram_enabled:
            self._telegram_initialized = True
            return

        try:
            import os
            import json
            from pathlib import Path

            # 优先从config/telegram.json加载
            project_root = Path(__file__).parent.parent.parent
            config_file = project_root / 'config' / 'telegram.json'

            if config_file.exists():
                with open(config_file) as f:
                    cfg = json.load(f)
                    if cfg.get('enabled', True):
                        self._telegram_bot_token = cfg.get('bot_token', '').strip()
                        self._telegram_chat_id = cfg.get('chat_id', '').strip()
                        logger.info("从config/telegram.json加载Telegram配置")

            # 环境变量覆盖
            if not self._telegram_bot_token:
                self._telegram_bot_token = (
                    os.getenv('TELEGRAM_BOT_TOKEN') or
                    os.getenv('ATS_TELEGRAM_BOT_TOKEN') or ''
                ).strip()
            if not self._telegram_chat_id:
                self._telegram_chat_id = (
                    os.getenv('TELEGRAM_CHAT_ID') or
                    os.getenv('ATS_TELEGRAM_CHAT_ID') or ''
                ).strip()

            if self._telegram_bot_token and self._telegram_chat_id:
                logger.info("Telegram配置加载成功")
            else:
                logger.warning("Telegram配置不完整，通知功能将被禁用")
                self.telegram_enabled = False

        except Exception as e:
            logger.error(f"加载Telegram配置失败: {e}")
            self.telegram_enabled = False

        self._telegram_initialized = True

    def _send_telegram(self, message: str) -> None:
        """发送Telegram消息"""
        if not self.telegram_enabled:
            return

        # 确保已初始化
        self._init_telegram()

        if not self._telegram_bot_token or not self._telegram_chat_id:
            return

        try:
            import requests

            url = f"https://api.telegram.org/bot{self._telegram_bot_token}/sendMessage"
            payload = {
                "chat_id": self._telegram_chat_id,
                "text": message,
                "parse_mode": "HTML",
            }
            resp = requests.post(url, json=payload, timeout=10)

            if resp.status_code == 200:
                logger.debug("Telegram消息发送成功")
            else:
                logger.warning(f"Telegram发送失败: {resp.status_code} - {resp.text}")

        except Exception as e:
            logger.error(f"发送Telegram消息异常: {e}")

    def _format_signal_for_telegram(self, signal: V8Signal) -> Dict[str, Any]:
        """
        将V8Signal格式化为Telegram模板所需的字典格式

        Args:
            signal: V8信号

        Returns:
            兼容render_signal_v72的字典
        """
        # 计算大致的入场/止损/止盈价格（基于CVD和OBI方向）
        # 注意：这是基于实时因子的估算，完整版需要集成四步决策系统
        current_price = signal.factors.mid_price if signal.factors.mid_price > 0 else 0

        # 基于spread计算粗略的止损/止盈
        spread_pct = signal.factors.spread_bps / 10000  # 转为百分比
        base_risk_pct = max(0.005, spread_pct * 3)  # 至少0.5%风险

        if signal.direction == "long":
            entry = current_price
            stop_loss = entry * (1 - base_risk_pct)
            take_profit = entry * (1 + base_risk_pct * 2)  # RR = 2:1
        else:
            entry = current_price
            stop_loss = entry * (1 + base_risk_pct)
            take_profit = entry * (1 - base_risk_pct * 2)

        # 构建兼容telegram_fmt的信号字典
        return {
            "symbol": signal.symbol.replace("-PERP", "").replace("-USDT", "USDT"),
            "price": current_price,
            "side": signal.direction,
            "prime": signal.strength,
            "probability": signal.confidence,

            # 交易建议（V8实时版本的估算值）
            "entry_price": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_pct": base_risk_pct * 100,
            "reward_pct": base_risk_pct * 200,
            "risk_reward_ratio": 2.0,

            # V8特有因子
            "v8_factors": {
                "cvd_z": signal.factors.cvd_z,
                "obi": signal.factors.obi,
                "trade_intensity": signal.factors.trade_intensity,
                "spread_bps": signal.factors.spread_bps,
            },

            # 来源标记
            "source": "v8_realtime",
            "version": "v8.0.1",

            # 默认TTL
            "ttl_h": 4,
        }

    def _notify_signal(self, signal: V8Signal) -> None:
        """
        发送信号通知到Telegram

        Args:
            signal: V8信号
        """
        if not self.telegram_enabled:
            return

        if not TELEGRAM_FMT_AVAILABLE:
            logger.warning("telegram_fmt模块不可用，跳过Telegram通知")
            return

        try:
            # 格式化信号
            signal_dict = self._format_signal_for_telegram(signal)

            # 使用v72模板渲染
            if self.use_v72_template:
                message = render_signal_v72(signal_dict)
            else:
                # 简单格式
                message = (
                    f"🎯 V8 Signal: {signal.symbol}\n"
                    f"方向: {'🟢 LONG' if signal.direction == 'long' else '🔴 SHORT'}\n"
                    f"强度: {signal.strength:.1f}\n"
                    f"置信度: {signal.confidence:.2f}\n"
                    f"CVD Z: {signal.factors.cvd_z:.2f}\n"
                    f"OBI: {signal.factors.obi:.3f}"
                )

            # 发送
            self._send_telegram(message)

        except Exception as e:
            logger.error(f"发送Telegram通知失败: {e}")

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

        # 发送Telegram通知
        if self.telegram_enabled:
            self._notify_signal(signal)

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
        # ===== V8 + 四步决策系统融合 =====
        # v8.0.2: 实现CVD/OBI快速触发 + 四步决策验证
        # ================================

        # 1. 快速预筛选：基于CVD和OBI
        cvd_z = factors.cvd_z
        obi = factors.obi

        if cvd_z > self.cvd_z_threshold and obi > self.obi_threshold:
            direction = "long"
            strength = min(100, (cvd_z * 20 + obi * 100))
        elif cvd_z < -self.cvd_z_threshold and obi < -self.obi_threshold:
            direction = "short"
            strength = min(100, (abs(cvd_z) * 20 + abs(obi) * 100))
        else:
            return None

        # 2. 尝试四步决策系统验证
        if self.use_four_step and FOUR_STEP_AVAILABLE:
            four_step_result = self._run_four_step_validation(factors, direction)
            if four_step_result:
                # 四步系统通过，使用其结果
                return four_step_result
            elif not self.four_step_fallback:
                # 四步系统拒绝且不允许fallback
                logger.debug(f"{factors.symbol} 四步决策拒绝，无fallback")
                return None
            # 四步系统失败但允许fallback，继续使用简化判断

        # 3. 简化判断（CVD/OBI模式）
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
                "source": "v8_realtime_simple",
                "cvd_z": cvd_z,
                "obi": obi,
            }
        )

    def _run_four_step_validation(
        self, factors: RealtimeFactors, direction: str
    ) -> Optional[V8Signal]:
        """
        运行四步决策系统验证

        Args:
            factors: 实时因子
            direction: 预判方向

        Returns:
            V8Signal或None（如果验证失败）
        """
        try:
            symbol = normalize_symbol(factors.symbol)

            # 检查K线缓存
            if not self.kline_cache or symbol not in self.kline_cache.cache:
                logger.debug(f"{symbol} 无K线缓存，跳过四步验证")
                return None

            # 获取缓存的K线
            k1h = list(self.kline_cache.cache[symbol].get('1h', []))
            if len(k1h) < 50:
                logger.debug(f"{symbol} K线数据不足 ({len(k1h)}<50)")
                return None

            # 调用完整分析（包含四步决策）
            result = analyze_symbol_with_preloaded_klines(
                symbol=symbol,
                k1h=k1h,
                k4h=[],  # 可选
                oi_data=None,
                orderbook={
                    'bids': [[factors.mid_price * 0.999, factors.bid_depth]],
                    'asks': [[factors.mid_price * 1.001, factors.ask_depth]],
                } if factors.mid_price > 0 else None,
            )

            # 检查四步决策结果
            four_step = result.get("four_step_decision", {})
            if not four_step or four_step.get("decision") != "ACCEPT":
                reject_reason = four_step.get("reject_reason", "unknown")
                logger.debug(f"{symbol} 四步决策拒绝: {reject_reason}")
                return None

            # 四步系统通过，构建V8Signal
            decision = four_step_to_decision_output(four_step, factors.timestamp)

            return V8Signal(
                symbol=factors.symbol,
                timestamp=factors.timestamp,
                direction=decision.action.lower() if decision.action else direction,
                strength=decision.step1_result.get("final_strength", 50),
                confidence=decision.confidence,
                factors=factors,
                meta={
                    "source": "v8_four_step",
                    "entry_price": decision.entry_price,
                    "stop_loss": decision.stop_loss,
                    "take_profit": decision.take_profit,
                    "risk_reward_ratio": decision.risk_reward_ratio,
                    "cvd_z": factors.cvd_z,
                    "obi": factors.obi,
                }
            )

        except Exception as e:
            logger.error(f"四步决策验证异常: {e}")
            return None

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
        confidence = self.base_confidence  # 从配置读取基础信心度

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
                    self.exchange_id,  # 从配置读取交易所ID
                    api_key=api_key,
                    secret=api_secret,
                )
                self.executor = CcxtExecutor(
                    exchange=exchange,
                    dry_run=self.dry_run,
                    max_order_value=self.max_order_value,  # 从配置读取
                )

            # 转换为执行信号
            from cs_ext.execution.ccxt_executor import ExecutionSignal
            exec_signal = ExecutionSignal(
                exchange=self.exchange_id,
                symbol=signal.symbol.replace("-PERP", "").replace("-USDT", "/USDT"),
                side="buy" if signal.direction == "long" else "sell",
                order_type="market",
                quantity=self.default_order_quantity,  # 从配置读取订单数量
                signal_id=f"v8_{int(signal.timestamp)}",
            )

            self.executor.submit_signal(exec_signal)  # 修复：submit → submit_signal
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

            # 启动流 - 使用异步方法避免事件循环嵌套问题
            await self.stream._run_async()

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
