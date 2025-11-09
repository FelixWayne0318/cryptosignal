# coding: utf-8
"""
自动交易系统主程序（世界顶尖标准）

架构:
┌─────────────┐
│ Auto Trader │  主协调器
└──────┬──────┘
       │
       ├──→ BinanceFuturesClient (WebSocket + REST)
       ├──→ SignalExecutor (信号→交易)
       └──→ DynamicPositionManager (实时管理)

特性:
1. WebSocket实时数据（200ms延迟）
2. 因子驱动动态管理
3. API友好（11 req/min）
4. 完善的错误处理和恢复
5. 关键事件通知

使用场景:
- 单次扫描: scan_and_execute()
- 定时扫描: start_periodic_scan(interval_minutes=60)
- 手动信号: execute_manual_signal(symbol)
"""

import asyncio
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta, timezone

# UTC+8时区（北京时间）
TZ_UTC8 = timezone(timedelta(hours=8))

from ats_core.execution.binance_futures_client import (
    BinanceFuturesClient,
    get_binance_client
)
from ats_core.execution.position_manager import DynamicPositionManager
from ats_core.execution.signal_executor import (
    SignalExecutor,
    execute_scan_signals
)
from ats_core.pipeline.batch_scan_optimized import OptimizedBatchScanner
from ats_core.logging import log, warn, error


class AutoTrader:
    """
    自动交易系统

    组件:
    - BinanceFuturesClient: 币安交易客户端
    - SignalExecutor: 信号执行器
    - DynamicPositionManager: 动态仓位管理器

    使用:
    ```python
    trader = AutoTrader()
    await trader.initialize()

    # 启动定时扫描
    await trader.start_periodic_scan(interval_minutes=60)

    # 或单次扫描
    await trader.scan_and_execute()
    ```
    """

    def __init__(
        self,
        config_path: str = "config/binance_credentials.json",
        use_optimized_scan: bool = True
    ):
        self.config_path = config_path
        self.use_optimized_scan = use_optimized_scan

        # 核心组件
        self.client: Optional[BinanceFuturesClient] = None
        self.position_manager: Optional[DynamicPositionManager] = None
        self.signal_executor: Optional[SignalExecutor] = None
        self.batch_scanner: Optional[OptimizedBatchScanner] = None

        # 状态
        self.is_initialized = False
        self.is_running = False

        # 统计
        self.stats = {
            'start_time': None,
            'total_scans': 0,
            'total_signals': 0,
            'total_trades': 0,
            'total_pnl_usdt': 0.0
        }

        log("🚀 AutoTrader 初始化...")
        if use_optimized_scan:
            log("   使用WebSocket优化扫描（17倍提速）✅")

    # ========== 初始化 ==========

    async def initialize(self):
        """
        初始化所有组件

        步骤:
        1. 创建币安客户端
        2. 同步服务器时间
        3. 创建仓位管理器
        4. 创建信号执行器
        5. 初始化批量扫描器（如果启用优化）
        6. 恢复现有持仓（如果有）
        """
        if self.is_initialized:
            log("⚠️  AutoTrader 已初始化")
            return

        log("=" * 60)
        log("🚀 正在初始化 AutoTrader...")
        log("=" * 60)

        # 1. 创建币安客户端
        log("1️⃣  创建币安客户端...")
        self.client = get_binance_client(self.config_path)
        await self.client.initialize()

        # 2. 创建仓位管理器
        log("2️⃣  创建动态仓位管理器...")
        self.position_manager = DynamicPositionManager(self.client)

        # 3. 创建信号执行器
        log("3️⃣  创建信号执行器...")
        self.signal_executor = SignalExecutor(
            client=self.client,
            position_manager=self.position_manager,
            auto_execute=True,
            telegram_notify=True
        )

        # 4. 初始化批量扫描器（如果启用优化）
        if self.use_optimized_scan:
            log("4️⃣  初始化WebSocket批量扫描器（约2分钟）...")
            self.batch_scanner = OptimizedBatchScanner()
            self.batch_scanner.client = self.client  # 复用客户端
            await self.batch_scanner.initialize()
            log("   ✅ WebSocket扫描已就绪（后续扫描约5秒）")

        # 5. 恢复现有持仓
        step_num = "5️⃣" if self.use_optimized_scan else "4️⃣"
        log(f"{step_num}  检查现有持仓...")
        await self._recover_positions()

        # 6. 启动仓位管理器
        step_num = "6️⃣" if self.use_optimized_scan else "5️⃣"
        log(f"{step_num}  启动动态仓位管理器...")
        asyncio.create_task(self.position_manager.start())

        self.is_initialized = True
        self.stats['start_time'] = time.time()

        log("=" * 60)
        log("✅ AutoTrader 初始化完成！")
        log("=" * 60)
        log(f"   API端点: {self.client.base_url}")
        log(f"   WebSocket: {self.client.ws_base_url}")
        log(f"   自动执行: 开启")
        log(f"   电报通知: 开启")
        log(f"   优化扫描: {'开启（17倍提速）' if self.use_optimized_scan else '关闭'}")
        log("=" * 60)

    async def _recover_positions(self):
        """
        恢复现有持仓到管理器

        场景: 系统重启后，恢复之前的持仓
        """
        try:
            positions = await self.client.get_positions()

            if not positions:
                log("   无现有持仓")
                return

            log(f"   发现 {len(positions)} 个现有持仓")

            for pos in positions:
                symbol = pos['symbol']
                position_amt = float(pos['positionAmt'])
                entry_price = float(pos['entryPrice'])
                leverage = int(pos['leverage'])

                # 确定方向
                side = 'LONG' if position_amt > 0 else 'SHORT'
                quantity = abs(position_amt)

                log(f"   恢复持仓: {symbol} {side} qty={quantity} @ ${entry_price}")

                # 注意: 这里简化处理，实际应该从数据库恢复完整的止损止盈信息
                # 这里使用默认值
                from ats_core.execution.position_manager import (
                    Position,
                    calculate_stop_loss_take_profit
                )

                # 使用默认因子计算止损止盈
                risk_params = calculate_stop_loss_take_profit(
                    entry_price=entry_price,
                    side=side,
                    factors={}  # 使用默认值
                )

                position_obj = Position(
                    symbol=symbol,
                    side=side,
                    entry_price=entry_price,
                    quantity=quantity,
                    leverage=leverage,
                    stop_loss=risk_params['stop_loss'],
                    take_profit_1=risk_params['take_profit_1'],
                    take_profit_2=risk_params['take_profit_2']
                )

                self.position_manager.add_position(position_obj)

            log(f"✅ 已恢复 {len(positions)} 个持仓到管理器")

        except Exception as e:
            error(f"恢复持仓失败: {e}")

    # ========== 扫描和执行 ==========

    async def scan_and_execute(
        self,
        symbols: Optional[List[str]] = None,
        min_score: int = 70
    ):
        """
        单次扫描并执行

        Args:
            symbols: 币种列表（如果为None，使用池管理器）
            min_score: 最低信号分数
        """
        if not self.is_initialized:
            error("❌ AutoTrader 未初始化，请先调用 initialize()")
            return

        log("\n" + "=" * 60)
        log(f"🔍 开始扫描...")
        log(f"   时间: {datetime.now(TZ_UTC8).strftime('%Y-%m-%d %H:%M:%S')}")
        log(f"   最低分数: {min_score}")
        log(f"   扫描模式: {'WebSocket优化（17倍提速）' if self.use_optimized_scan else 'REST标准'}")
        log("=" * 60)

        start_time = time.time()

        # 执行扫描（优化 vs 标准）
        if self.use_optimized_scan and self.batch_scanner:
            # 使用WebSocket优化扫描（0次API，约5秒）
            scan_results = await self.batch_scanner.scan(
                min_score=min_score,
                max_symbols=len(symbols) if symbols else None
            )

            # 处理扫描结果
            for result in scan_results['results']:
                try:
                    await self.signal_executor.process_signal(
                        result['symbol'],
                        result
                    )
                except Exception as e:
                    error(f"处理信号失败 {result.get('symbol')}: {e}")

            log(f"\n📊 扫描统计:")
            log(f"   扫描币种: {scan_results['total_symbols']}")
            log(f"   发现信号: {scan_results['signals_found']}")
            log(f"   API调用: {scan_results['api_calls']} ✅")
            log(f"   缓存命中: {scan_results['cache_stats']['hit_rate']}")

        else:
            # 使用标准REST扫描（兼容模式）
            await execute_scan_signals(
                executor=self.signal_executor,
                symbols=symbols,
                min_score=min_score
            )

        elapsed = time.time() - start_time
        self.stats['total_scans'] += 1

        log("\n" + "=" * 60)
        log(f"✅ 扫描完成")
        log(f"   耗时: {elapsed:.2f}秒")
        if self.use_optimized_scan:
            log(f"   速度: {scan_results['symbols_per_second']:.1f} 币种/秒 🚀")
        log(f"   当前持仓: {len(self.position_manager.get_all_positions())}")
        log("=" * 60)

    async def start_periodic_scan(
        self,
        interval_minutes: int = 60,
        symbols: Optional[List[str]] = None,
        min_score: int = 70
    ):
        """
        启动定时扫描

        Args:
            interval_minutes: 扫描间隔（分钟）
            symbols: 币种列表
            min_score: 最低信号分数
        """
        if not self.is_initialized:
            error("❌ AutoTrader 未初始化，请先调用 initialize()")
            return

        self.is_running = True

        log("\n" + "=" * 60)
        log("🔄 启动定时扫描")
        log("=" * 60)
        log(f"   扫描间隔: {interval_minutes} 分钟")
        log(f"   最低分数: {min_score}")
        log("=" * 60)

        while self.is_running:
            try:
                # 执行扫描
                await self.scan_and_execute(symbols, min_score)

                # 等待下次扫描
                next_scan = datetime.now(TZ_UTC8).timestamp() + interval_minutes * 60
                next_scan_time = datetime.fromtimestamp(next_scan, tz=TZ_UTC8).strftime('%Y-%m-%d %H:%M:%S')

                log(f"\n⏰ 下次扫描: {next_scan_time}")

                await asyncio.sleep(interval_minutes * 60)

            except Exception as e:
                error(f"定时扫描错误: {e}")
                await asyncio.sleep(60)  # 出错后等待1分钟重试

    async def stop(self):
        """停止自动交易系统"""
        log("\n" + "=" * 60)
        log("🛑 正在停止 AutoTrader...")
        log("=" * 60)

        self.is_running = False

        # 停止仓位管理器
        if self.position_manager:
            await self.position_manager.stop()

        # 🔧 修复：关闭批量扫描器（释放WebSocket连接）
        if self.batch_scanner:
            await self.batch_scanner.close()

        # 关闭客户端
        if self.client:
            await self.client.close()

        # 打印最终统计
        self._print_final_stats()

        log("=" * 60)
        log("✅ AutoTrader 已停止")
        log("=" * 60)

    # ========== 手动操作 ==========

    async def execute_manual_signal(self, symbol: str):
        """
        手动执行单个信号

        Args:
            symbol: 交易对

        使用场景: 手动触发特定币种的交易
        """
        if not self.is_initialized:
            error("❌ AutoTrader 未初始化")
            return

        log(f"\n📝 手动执行信号: {symbol}")

        await self.signal_executor.process_signal(symbol)

    async def close_all_positions(self):
        """
        紧急平仓所有持仓

        使用场景: 紧急情况需要退出所有仓位
        """
        if not self.is_initialized:
            error("❌ AutoTrader 未初始化")
            return

        log("\n🚨 紧急平仓所有持仓...")

        positions = self.position_manager.get_all_positions()

        log(f"   共 {len(positions)} 个持仓")

        for position in positions:
            try:
                log(f"   平仓: {position.symbol}")
                await self.client.close_position(position.symbol)
                self.position_manager.remove_position(position.symbol)

            except Exception as e:
                error(f"平仓失败 {position.symbol}: {e}")

        log("✅ 所有持仓已平仓")

    # ========== 信息查询 ==========

    async def get_account_summary(self) -> Dict:
        """获取账户摘要"""
        if not self.is_initialized:
            return {}

        account_info = await self.client.get_account_info()

        return {
            'total_wallet_balance': float(account_info.get('totalWalletBalance', 0)),
            'total_unrealized_pnl': float(account_info.get('totalUnrealizedProfit', 0)),
            'total_margin_balance': float(account_info.get('totalMarginBalance', 0)),
            'available_balance': float(account_info.get('availableBalance', 0)),
            'positions_count': len(self.position_manager.get_all_positions()),
            'max_positions': self.signal_executor.config.get('max_concurrent_positions', 5)
        }

    async def print_status(self):
        """打印当前状态"""
        log("\n" + "=" * 60)
        log("📊 AutoTrader 状态")
        log("=" * 60)

        # 账户信息
        summary = await self.get_account_summary()

        log(f"💰 账户余额: ${summary.get('total_wallet_balance', 0):.2f}")
        log(f"📈 未实现盈亏: ${summary.get('total_unrealized_pnl', 0):.2f}")
        log(f"💵 可用余额: ${summary.get('available_balance', 0):.2f}")

        # 持仓信息
        positions = self.position_manager.get_all_positions()
        log(f"\n📊 持仓: {len(positions)}/{summary.get('max_positions', 5)}")

        for pos in positions:
            current_price = self.position_manager.price_cache.get(pos.symbol, pos.entry_price)
            pnl_pct = pos.get_current_pnl_pct(current_price)

            log(f"   {pos.symbol} {pos.side}")
            log(f"      入场: ${pos.entry_price:.4f}")
            log(f"      当前: ${current_price:.4f}")
            log(f"      盈亏: {pnl_pct:+.2f}%")
            log(f"      TP1: {'✅' if pos.tp1_hit else '⏳'}")

        # 执行统计
        executor_stats = self.signal_executor.get_stats()
        manager_stats = self.position_manager.get_stats()

        log(f"\n📊 执行统计")
        log(f"   信号数: {executor_stats['signals_received']}")
        log(f"   交易数: {executor_stats['trades_executed']}")
        log(f"   失败数: {executor_stats['trades_failed']}")
        log(f"   TP1触达: {manager_stats['tp1_hits']}")
        log(f"   TP2触达: {manager_stats['tp2_hits']}")
        log(f"   止损触发: {manager_stats['stop_losses']}")

        log("=" * 60)

    def _print_final_stats(self):
        """打印最终统计"""
        if not self.stats['start_time']:
            return

        elapsed_hours = (time.time() - self.stats['start_time']) / 3600

        log("\n" + "=" * 60)
        log("📊 最终统计")
        log("=" * 60)
        log(f"   运行时长: {elapsed_hours:.2f} 小时")
        log(f"   总扫描次数: {self.stats['total_scans']}")
        log(f"   总交易次数: {self.stats['total_trades']}")

        executor_stats = self.signal_executor.get_stats() if self.signal_executor else {}
        manager_stats = self.position_manager.get_stats() if self.position_manager else {}

        log(f"\n📊 执行详情")
        log(f"   信号数: {executor_stats.get('signals_received', 0)}")
        log(f"   成功交易: {executor_stats.get('trades_executed', 0)}")
        log(f"   失败交易: {executor_stats.get('trades_failed', 0)}")
        log(f"   TP1触达: {manager_stats.get('tp1_hits', 0)}")
        log(f"   TP2触达: {manager_stats.get('tp2_hits', 0)}")
        log(f"   止损触发: {manager_stats.get('stop_losses', 0)}")
        log("=" * 60)


# ============ 便捷启动函数 ============

async def run_single_scan(min_score: int = 70):
    """
    便捷函数: 单次扫描

    使用:
    ```python
    import asyncio
    from ats_core.execution.auto_trader import run_single_scan

    asyncio.run(run_single_scan(min_score=75))
    ```
    """
    trader = AutoTrader()
    await trader.initialize()
    await trader.scan_and_execute(min_score=min_score)
    await trader.stop()


async def run_periodic_scan(interval_minutes: int = 60, min_score: int = 70):
    """
    便捷函数: 定时扫描

    使用:
    ```python
    import asyncio
    from ats_core.execution.auto_trader import run_periodic_scan

    asyncio.run(run_periodic_scan(interval_minutes=60, min_score=75))
    ```
    """
    trader = AutoTrader()
    await trader.initialize()

    try:
        await trader.start_periodic_scan(
            interval_minutes=interval_minutes,
            min_score=min_score
        )
    except KeyboardInterrupt:
        log("\n⚠️  收到中断信号")
    finally:
        await trader.stop()


# ============ 测试函数 ============

async def test_connection():
    """
    测试币安连接

    使用:
    ```python
    import asyncio
    from ats_core.execution.auto_trader import test_connection

    asyncio.run(test_connection())
    ```
    """
    log("🧪 测试币安连接...")

    trader = AutoTrader()
    await trader.initialize()

    # 测试账户信息
    log("\n1️⃣  测试账户信息...")
    summary = await trader.get_account_summary()
    log(f"   账户余额: ${summary.get('total_wallet_balance', 0):.2f}")

    # 测试价格查询
    log("\n2️⃣  测试价格查询...")
    ticker = await trader.client.get_ticker('BTCUSDT')
    log(f"   BTC价格: ${float(ticker.get('lastPrice', 0)):.2f}")

    # 测试持仓查询
    log("\n3️⃣  测试持仓查询...")
    positions = await trader.client.get_positions()
    log(f"   当前持仓: {len(positions)}")

    await trader.stop()

    log("\n✅ 连接测试完成！")


if __name__ == "__main__":
    # 测试连接
    # asyncio.run(test_connection())

    # 单次扫描
    # asyncio.run(run_single_scan(min_score=75))

    # 定时扫描（每小时）
    asyncio.run(run_periodic_scan(interval_minutes=60, min_score=75))
