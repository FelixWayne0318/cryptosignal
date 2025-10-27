# coding: utf-8
"""
信号执行器（混合模式：电报简洁 + 自动执行）

用户最优方案:
1. 电报发送简洁信号（入场价格、参考止损止盈）
2. 系统自动执行和管理（动态调整）
3. 只在关键事件时通知（TP1、TP2、止损、最终结果）
4. 无需频繁发送电报消息

流程:
分析信号 → 发送简洁电报 → 自动开仓 → 动态管理 → 关键事件通知
"""

import asyncio
import time
from typing import Dict, Optional
from decimal import Decimal

from ats_core.execution.binance_futures_client import BinanceFuturesClient
from ats_core.execution.position_manager import (
    DynamicPositionManager,
    Position,
    calculate_stop_loss_take_profit
)
from ats_core.pipeline.analyze_symbol import analyze_symbol
from ats_core.outputs.telegram_fmt import render_trade
from ats_core.outputs.publisher import telegram_send
from ats_core.logging import log, warn, error


class SignalExecutor:
    """
    信号执行器

    特性:
    1. 接收分析信号
    2. 发送简洁电报通知（仅参考价格）
    3. 自动执行交易
    4. 委托给位置管理器进行动态管理
    5. 关键事件通知
    """

    def __init__(
        self,
        client: BinanceFuturesClient,
        position_manager: DynamicPositionManager,
        auto_execute: bool = True,
        telegram_notify: bool = True
    ):
        self.client = client
        self.position_manager = position_manager
        self.auto_execute = auto_execute
        self.telegram_notify = telegram_notify

        # 交易配置（从config读取）
        self.config = self._load_config()

        # 统计
        self.stats = {
            'signals_received': 0,
            'trades_executed': 0,
            'trades_failed': 0,
            'telegram_sent': 0
        }

        log("✅ 信号执行器初始化完成")
        log(f"   自动执行: {'开启' if auto_execute else '关闭'}")
        log(f"   电报通知: {'开启' if telegram_notify else '关闭'}")

    def _load_config(self) -> Dict:
        """加载交易配置"""
        import json
        with open('config/binance_credentials.json', 'r') as f:
            config = json.load(f)

        return config.get('trading_limits', {})

    # ========== 信号处理 ==========

    async def process_signal(self, symbol: str, analysis_result: Optional[Dict] = None):
        """
        处理交易信号

        Args:
            symbol: 交易对
            analysis_result: 分析结果（如果为None，则重新分析）

        流程:
        1. 分析信号（如果未提供）
        2. 验证信号质量
        3. 发送电报通知（简洁版）
        4. 自动执行交易
        5. 添加到动态管理器
        """
        self.stats['signals_received'] += 1

        # 1. 获取分析结果
        if analysis_result is None:
            log(f"📊 分析信号: {symbol}")
            analysis_result = analyze_symbol(symbol)

        # 2. 验证信号
        pub = analysis_result.get('publish', {})

        if not pub.get('prime'):
            log(f"⚠️  {symbol} 信号不够强，跳过")
            return

        # 3. 提取信号信息
        signal_info = self._extract_signal_info(analysis_result)

        if not signal_info:
            warn(f"⚠️  {symbol} 信号信息提取失败")
            return

        # 4. 发送电报通知（简洁版）
        if self.telegram_notify:
            await self._send_telegram_signal(signal_info)

        # 5. 自动执行交易
        if self.auto_execute:
            success = await self._execute_trade(signal_info)

            if success:
                log(f"✅ {symbol} 交易执行成功，已添加到动态管理")
            else:
                error(f"❌ {symbol} 交易执行失败")

    def _extract_signal_info(self, analysis_result: Dict) -> Optional[Dict]:
        """
        提取信号信息

        返回:
        {
            'symbol': 'BTCUSDT',
            'direction': 'LONG',
            'entry_price': 50000.0,
            'stop_loss': 49000.0,
            'take_profit_1': 52000.0,
            'take_profit_2': 54000.0,
            'quantity': 0.1,
            'leverage': 5,
            'signal_strength': 85,
            'factors': {...}
        }
        """
        try:
            symbol = analysis_result.get('symbol')
            final_score = analysis_result.get('final_score', 0)

            # 确定方向
            direction = 'LONG' if final_score > 0 else 'SHORT'

            # 获取当前价格
            metadata = analysis_result.get('metadata', {})
            entry_price = metadata.get('current_price', 0)

            if entry_price == 0:
                error(f"❌ {symbol} 价格数据缺失")
                return None

            # 提取因子
            factors = {
                'final_score': final_score,
                'signal_strength': abs(final_score),
                'trend_score': analysis_result.get('layers', {}).get('price_action', {}).get('trend', 0),
                'volume_score': analysis_result.get('layers', {}).get('money_flow', {}).get('volume_plus', 0),
                'liquidity_score': analysis_result.get('layers', {}).get('microstructure', {}).get('liquidity', 0),
                'independence': analysis_result.get('independence', 0),
                'volatility_atr_pct': metadata.get('volatility_atr_pct', 2.0)
            }

            # 计算止损止盈
            risk_params = calculate_stop_loss_take_profit(
                entry_price=entry_price,
                side=direction,
                factors=factors
            )

            # 计算仓位大小（基于风险）
            quantity = self._calculate_position_size(
                symbol=symbol,
                entry_price=entry_price,
                stop_loss=risk_params['stop_loss'],
                risk_pct=1.0  # 每笔交易风险1%
            )

            # 计算杠杆（保守）
            leverage = self._calculate_leverage(factors['signal_strength'] / 100.0)

            return {
                'symbol': symbol,
                'direction': direction,
                'entry_price': entry_price,
                'stop_loss': risk_params['stop_loss'],
                'take_profit_1': risk_params['take_profit_1'],
                'take_profit_2': risk_params['take_profit_2'],
                'stop_pct': risk_params['stop_pct'],
                'tp1_pct': risk_params['tp1_pct'],
                'tp2_pct': risk_params['tp2_pct'],
                'quantity': quantity,
                'leverage': leverage,
                'signal_strength': abs(final_score),
                'factors': factors
            }

        except Exception as e:
            error(f"提取信号信息失败: {e}")
            return None

    def _calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        risk_pct: float = 1.0
    ) -> float:
        """
        计算仓位大小（基于风险）

        公式:
        position_size = (account_balance * risk_pct) / (entry_price - stop_loss) / entry_price

        Args:
            symbol: 交易对
            entry_price: 入场价格
            stop_loss: 止损价格
            risk_pct: 风险百分比（默认1%）

        Returns:
            仓位大小（以币种数量计）
        """
        # 简化实现：使用固定金额
        # 实际应该从账户余额动态计算
        max_position_usdt = self.config.get('max_position_size_usdt', 10000)
        min_order_usdt = self.config.get('min_order_size_usdt', 10)

        # 基于风险的仓位
        risk_distance = abs(entry_price - stop_loss) / entry_price
        position_usdt = max_position_usdt * (risk_pct / 100) / risk_distance

        # 限制最大仓位
        position_usdt = min(position_usdt, max_position_usdt)
        position_usdt = max(position_usdt, min_order_usdt)

        # 转换为币种数量
        quantity = position_usdt / entry_price

        # 四舍五入到合理精度（需要根据币种调整）
        quantity = round(quantity, 3)

        log(f"📏 仓位计算: {symbol}")
        log(f"   风险距离: {risk_distance*100:.2f}%")
        log(f"   仓位金额: ${position_usdt:.2f}")
        log(f"   仓位数量: {quantity:.4f}")

        return quantity

    def _calculate_leverage(self, signal_strength: float) -> int:
        """
        计算杠杆倍数（保守）

        Args:
            signal_strength: 信号强度（0-1）

        Returns:
            杠杆倍数（1-10）

        策略:
        - 信号强度 > 0.8: 5x
        - 信号强度 > 0.6: 3x
        - 其他: 2x
        """
        max_leverage = self.config.get('max_leverage', 10)

        if signal_strength > 0.8:
            leverage = 5
        elif signal_strength > 0.6:
            leverage = 3
        else:
            leverage = 2

        return min(leverage, max_leverage)

    # ========== 电报通知 ==========

    async def _send_telegram_signal(self, signal_info: Dict):
        """
        发送简洁电报信号

        内容:
        - 币种和方向
        - 入场价格
        - 参考止损止盈
        - 信号强度
        - 提示（系统将自动执行和管理）
        """
        symbol = signal_info['symbol']
        direction = signal_info['direction']
        entry = signal_info['entry_price']
        stop = signal_info['stop_loss']
        tp1 = signal_info['take_profit_1']
        tp2 = signal_info['take_profit_2']
        strength = signal_info['signal_strength']
        leverage = signal_info['leverage']

        # 方向emoji
        emoji = '🟢' if direction == 'LONG' else '🔴'

        # 构建消息
        message = f"""
{emoji} <b>{symbol} {direction}</b>

📊 信号强度: {strength:.0f}/100
⚡ 杠杆: {leverage}x

💰 入场: ${entry:.4f}
🛑 止损: ${stop:.4f} ({signal_info['stop_pct']:.1f}%)

🎯 止盈1: ${tp1:.4f} ({signal_info['tp1_pct']:.1f}%) - 平50%
🎯 止盈2: ${tp2:.4f} ({signal_info['tp2_pct']:.1f}%) - 平50%

<i>✅ 系统将自动执行和管理
📢 关键事件时将通知</i>
"""

        try:
            telegram_send(message)
            self.stats['telegram_sent'] += 1
            log(f"📱 电报信号已发送: {symbol} {direction}")

        except Exception as e:
            error(f"电报发送失败: {e}")

    async def _send_telegram_event(self, event_type: str, symbol: str, details: Dict):
        """
        发送关键事件通知

        事件类型:
        - entry: 入场确认
        - tp1: TP1触达
        - tp2: TP2触达
        - stop_loss: 止损触发
        - final: 最终结果
        """
        emoji_map = {
            'entry': '✅',
            'tp1': '🎯',
            'tp2': '🎯',
            'stop_loss': '🛑',
            'final': '📊'
        }

        emoji = emoji_map.get(event_type, '📢')

        message = f"{emoji} <b>{symbol} - {event_type.upper()}</b>\n\n"

        if event_type == 'entry':
            message += f"入场价格: ${details['entry_price']:.4f}\n"
            message += f"数量: {details['quantity']:.4f}\n"

        elif event_type == 'tp1':
            message += f"TP1触达: ${details['price']:.4f}\n"
            message += f"已平50%，止损移至保本\n"
            message += f"当前盈利: {details['pnl_pct']:.2f}%"

        elif event_type == 'tp2':
            message += f"TP2触达: ${details['price']:.4f}\n"
            message += f"已平剩余50%\n"
            message += f"总盈利: {details['total_pnl_pct']:.2f}%"

        elif event_type == 'stop_loss':
            message += f"止损触发: ${details['price']:.4f}\n"
            message += f"总亏损: {details['total_pnl_pct']:.2f}%"

        elif event_type == 'final':
            message += f"最终盈亏: {details['total_pnl_pct']:.2f}%\n"
            message += f"持仓时长: {details['hold_time_hours']:.1f}小时"

        try:
            telegram_send(message)
            log(f"📱 事件通知已发送: {symbol} {event_type}")

        except Exception as e:
            error(f"事件通知发送失败: {e}")

    # ========== 交易执行 ==========

    async def _execute_trade(self, signal_info: Dict) -> bool:
        """
        执行交易

        步骤:
        1. 设置杠杆和保证金模式
        2. 市价开仓
        3. 创建止损止盈订单（条件单）
        4. 添加到动态管理器
        5. 发送入场通知

        Returns:
            True: 成功, False: 失败
        """
        symbol = signal_info['symbol']
        direction = signal_info['direction']
        quantity = signal_info['quantity']
        leverage = signal_info['leverage']

        try:
            # 1. 设置杠杆
            log(f"⚙️  设置杠杆: {symbol} {leverage}x")
            await self.client.set_leverage(symbol, leverage)

            # 2. 设置保证金模式（逐仓，更安全）
            try:
                await self.client.set_margin_type(symbol, 'ISOLATED')
            except Exception as e:
                # 如果已经是逐仓模式，会报错，忽略
                log(f"保证金模式设置: {e}")

            # 3. 市价开仓
            log(f"📝 开仓: {symbol} {direction} qty={quantity}")

            if direction == 'LONG':
                order_result = await self.client.market_buy(symbol, quantity)
            else:
                order_result = await self.client.market_sell(symbol, quantity)

            if 'error' in order_result:
                error(f"❌ 开仓失败: {order_result['error']}")
                self.stats['trades_failed'] += 1
                return False

            # 获取实际成交价格
            actual_entry = float(order_result.get('avgPrice', signal_info['entry_price']))

            log(f"✅ 开仓成功: {symbol} @ ${actual_entry:.4f}")

            # 4. 创建Position对象
            position = Position(
                symbol=symbol,
                side=direction,
                entry_price=actual_entry,
                quantity=quantity,
                leverage=leverage,
                stop_loss=signal_info['stop_loss'],
                take_profit_1=signal_info['take_profit_1'],
                take_profit_2=signal_info['take_profit_2'],
                initial_factors=signal_info['factors']
            )

            # 5. 添加到动态管理器
            self.position_manager.add_position(position)

            # 6. 发送入场通知
            if self.telegram_notify:
                await self._send_telegram_event('entry', symbol, {
                    'entry_price': actual_entry,
                    'quantity': quantity
                })

            self.stats['trades_executed'] += 1

            return True

        except Exception as e:
            error(f"交易执行异常: {e}")
            self.stats['trades_failed'] += 1
            return False

    # ========== 辅助方法 ==========

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self.stats.copy()


# ============ 批量扫描集成 ============

async def execute_scan_signals(
    executor: SignalExecutor,
    symbols: list = None,
    min_score: int = 70
):
    """
    扫描并执行信号（批量）

    Args:
        executor: 信号执行器
        symbols: 币种列表（如果为None，则使用池管理器）
        min_score: 最低信号分数

    流程:
    1. 批量扫描
    2. 筛选高质量信号
    3. 逐个执行（带延迟，防止并发）
    """
    from ats_core.pools.pool_manager import get_pool_manager

    # 获取币种列表
    if symbols is None:
        manager = get_pool_manager(
            elite_cache_hours=24,
            overlay_cache_hours=1,
            verbose=False
        )
        symbols, _ = manager.get_merged_universe()

    log(f"🚀 开始批量扫描并执行: {len(symbols)} 个币种")
    log(f"   最低信号分数: {min_score}")

    executed_count = 0

    for symbol in symbols:
        try:
            # 分析
            result = analyze_symbol(symbol)

            # 检查信号强度
            final_score = abs(result.get('final_score', 0))
            pub = result.get('publish', {})

            if not pub.get('prime') or final_score < min_score:
                continue

            log(f"\n{'='*60}")
            log(f"🎯 发现高质量信号: {symbol} (分数: {final_score:.0f})")
            log(f"{'='*60}")

            # 执行信号
            await executor.process_signal(symbol, result)

            executed_count += 1

            # 检查并发限制
            max_positions = executor.config.get('max_concurrent_positions', 5)
            current_positions = len(executor.position_manager.get_all_positions())

            if current_positions >= max_positions:
                log(f"⚠️  已达到最大持仓数({max_positions})，停止扫描")
                break

            # 延迟，防止过快
            await asyncio.sleep(2)

        except Exception as e:
            error(f"处理 {symbol} 失败: {e}")

    log(f"\n{'='*60}")
    log(f"📊 批量扫描完成")
    log(f"{'='*60}")
    log(f"  扫描币种: {len(symbols)}")
    log(f"  执行交易: {executed_count}")
    log(f"{'='*60}")
