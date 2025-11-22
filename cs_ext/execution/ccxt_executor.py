# cs_ext/execution/ccxt_executor.py
"""
基于 CCXT 的订单执行器

这是 Hummingbot 执行器的轻量替代方案，直接使用 CCXT 下单。
适合：
- 快速测试
- 简单策略
- 不需要 Hummingbot 复杂功能的场景

⚠️ 警告：此模块涉及真实资金交易，使用前请：
1. 先在测试网验证
2. 设置合理的风控参数
3. 小资金测试
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime

from cs_ext.api.ccxt_wrapper import CcxtExchange


@dataclass
class OrderResult:
    """订单执行结果"""
    signal_id: str
    order_id: Optional[str] = None
    status: str = "pending"  # pending, filled, failed, cancelled
    filled_price: Optional[float] = None
    filled_amount: Optional[float] = None
    error_message: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class ExecutionSignal:
    """交易信号"""
    exchange: str           # "binance" / "binanceusdm" / "okx"
    symbol: str             # "BTC/USDT"
    side: str               # "buy" / "sell"
    quantity: float
    signal_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    order_type: str = "market"
    price: Optional[float] = None
    leverage: Optional[int] = None
    reduce_only: bool = False
    params: Dict[str, Any] = field(default_factory=dict)


class CcxtExecutor:
    """
    基于 CCXT 的订单执行器

    Features:
    - 信号队列管理
    - 异步执行
    - 订单追踪
    - 简单风控检查
    """

    def __init__(
        self,
        exchange: CcxtExchange,
        poll_interval: float = 0.5,
        max_order_value: float = 1000.0,  # 单笔最大金额限制
        dry_run: bool = True,  # 默认模拟模式
    ):
        self._exchange = exchange
        self._poll_interval = poll_interval
        self._max_order_value = max_order_value
        self._dry_run = dry_run

        self._signals: List[ExecutionSignal] = []
        self._results: Dict[str, OrderResult] = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    @property
    def dry_run(self) -> bool:
        return self._dry_run

    def set_dry_run(self, value: bool):
        """切换模拟/实盘模式"""
        self._dry_run = value
        mode = "模拟" if value else "实盘"
        print(f"[CcxtExecutor] 切换到{mode}模式")

    def submit_signal(self, signal: ExecutionSignal) -> str:
        """提交交易信号，返回 signal_id"""
        with self._lock:
            self._signals.append(signal)
            self._results[signal.signal_id] = OrderResult(
                signal_id=signal.signal_id,
                status="pending"
            )
        print(f"[CcxtExecutor] 信号已提交: {signal.signal_id} {signal.side} {signal.symbol}")
        return signal.signal_id

    def get_result(self, signal_id: str) -> Optional[OrderResult]:
        """获取订单执行结果"""
        return self._results.get(signal_id)

    def _pop_signal(self) -> Optional[ExecutionSignal]:
        with self._lock:
            if not self._signals:
                return None
            return self._signals.pop(0)

    def _risk_check(self, signal: ExecutionSignal) -> tuple[bool, str]:
        """
        简单风控检查

        Returns:
            (通过, 原因)
        """
        # 检查数量
        if signal.quantity <= 0:
            return False, "数量必须大于0"

        # 检查订单金额
        try:
            ticker = self._exchange.fetch_ticker(signal.symbol)
            price = ticker.get("last", 0)
            order_value = signal.quantity * price

            if order_value > self._max_order_value:
                return False, f"订单金额 {order_value:.2f} 超过限制 {self._max_order_value}"
        except Exception as e:
            return False, f"获取价格失败: {e}"

        return True, "OK"

    def _execute_signal(self, signal: ExecutionSignal):
        """执行单个信号"""
        result = self._results[signal.signal_id]

        # 风控检查
        passed, reason = self._risk_check(signal)
        if not passed:
            result.status = "failed"
            result.error_message = f"风控拒绝: {reason}"
            print(f"[CcxtExecutor] ❌ 风控拒绝 {signal.signal_id}: {reason}")
            return

        # 模拟模式
        if self._dry_run:
            try:
                ticker = self._exchange.fetch_ticker(signal.symbol)
                price = ticker.get("last", 0)

                result.status = "filled"
                result.filled_price = price
                result.filled_amount = signal.quantity
                result.order_id = f"DRY_{signal.signal_id}"

                print(f"[CcxtExecutor] 🔵 模拟成交 {signal.signal_id}: "
                      f"{signal.side} {signal.quantity} {signal.symbol} @ {price}")
            except Exception as e:
                result.status = "failed"
                result.error_message = str(e)
                print(f"[CcxtExecutor] ❌ 模拟失败 {signal.signal_id}: {e}")
            return

        # 实盘下单
        try:
            params = signal.params.copy()
            if signal.reduce_only:
                params["reduceOnly"] = True

            order = self._exchange.create_order(
                symbol=signal.symbol,
                side=signal.side,
                order_type=signal.order_type,
                amount=signal.quantity,
                price=signal.price,
                params=params
            )

            result.order_id = order.get("id")
            result.status = "filled" if order.get("status") == "closed" else "submitted"
            result.filled_price = order.get("average") or order.get("price")
            result.filled_amount = order.get("filled", signal.quantity)

            print(f"[CcxtExecutor] ✅ 订单成功 {signal.signal_id}: "
                  f"order_id={result.order_id} status={result.status}")

        except Exception as e:
            result.status = "failed"
            result.error_message = str(e)
            print(f"[CcxtExecutor] ❌ 下单失败 {signal.signal_id}: {e}")

    def _run_loop(self):
        print(f"[CcxtExecutor] 执行线程启动 (dry_run={self._dry_run})")
        while self._running:
            signal = self._pop_signal()
            if signal:
                try:
                    self._execute_signal(signal)
                except Exception as e:
                    print(f"[CcxtExecutor] 执行异常: {e}")
            else:
                time.sleep(self._poll_interval)
        print("[CcxtExecutor] 执行线程退出")

    def start(self):
        """启动执行线程"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """停止执行线程"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None


# ========== 便捷函数 ==========

def create_executor_from_config(
    exchange_id: str,
    api_key: str = None,
    secret: str = None,
    password: str = None,
    testnet: bool = False,
    dry_run: bool = True,
    max_order_value: float = 1000.0,
) -> CcxtExecutor:
    """
    从配置创建执行器

    Usage:
        executor = create_executor_from_config(
            exchange_id="binanceusdm",
            api_key="xxx",
            secret="xxx",
            testnet=True,
            dry_run=True
        )
        executor.start()

        signal = ExecutionSignal(
            exchange="binanceusdm",
            symbol="BTC/USDT",
            side="buy",
            quantity=0.001
        )
        executor.submit_signal(signal)
    """
    exchange = CcxtExchange(
        exchange_id=exchange_id,
        api_key=api_key,
        secret=secret,
        password=password,
        testnet=testnet
    )

    return CcxtExecutor(
        exchange=exchange,
        dry_run=dry_run,
        max_order_value=max_order_value
    )
