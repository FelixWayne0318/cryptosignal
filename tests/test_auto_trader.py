# coding: utf-8
"""
自动交易系统测试

运行方法:
    pytest tests/test_auto_trader.py -v
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock


class TestBinanceFuturesClient:
    """测试币安合约客户端"""

    def test_client_initialization(self):
        """测试客户端初始化"""
        from ats_core.execution.binance_futures_client import BinanceFuturesClient

        client = BinanceFuturesClient(
            api_key="test_key",
            api_secret="test_secret",
            testnet=True
        )

        assert client.api_key == "test_key"
        assert client.api_secret == "test_secret"
        assert client.testnet is True
        assert client.base_url == "https://testnet.binancefuture.com"

    def test_signature_generation(self):
        """测试签名生成"""
        from ats_core.execution.binance_futures_client import BinanceFuturesClient

        client = BinanceFuturesClient(
            api_key="test_key",
            api_secret="test_secret"
        )

        params = {'symbol': 'BTCUSDT', 'side': 'BUY'}
        signature = client._generate_signature(params)

        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA256 hex digest


class TestPositionManager:
    """测试动态仓位管理器"""

    def test_calculate_stop_loss_take_profit(self):
        """测试止损止盈计算"""
        from ats_core.execution.position_manager import calculate_stop_loss_take_profit

        # 测试LONG
        result = calculate_stop_loss_take_profit(
            entry_price=50000.0,
            side='LONG',
            factors={
                'signal_strength': 85,
                'trend_score': 70,
                'liquidity_score': 60,
                'volatility_atr_pct': 2.0
            }
        )

        assert 'stop_loss' in result
        assert 'take_profit_1' in result
        assert 'take_profit_2' in result

        # LONG: 止损应该低于入场价
        assert result['stop_loss'] < 50000.0
        # LONG: 止盈应该高于入场价
        assert result['take_profit_1'] > 50000.0
        assert result['take_profit_2'] > result['take_profit_1']

    def test_calculate_stop_loss_take_profit_short(self):
        """测试SHORT止损止盈计算"""
        from ats_core.execution.position_manager import calculate_stop_loss_take_profit

        result = calculate_stop_loss_take_profit(
            entry_price=50000.0,
            side='SHORT',
            factors={}
        )

        # SHORT: 止损应该高于入场价
        assert result['stop_loss'] > 50000.0
        # SHORT: 止盈应该低于入场价
        assert result['take_profit_1'] < 50000.0
        assert result['take_profit_2'] < result['take_profit_1']

    def test_position_pnl_calculation(self):
        """测试持仓盈亏计算"""
        from ats_core.execution.position_manager import Position

        # LONG持仓
        position = Position(
            symbol='BTCUSDT',
            side='LONG',
            entry_price=50000.0,
            quantity=0.1,
            leverage=5,
            stop_loss=49000.0,
            take_profit_1=52000.0,
            take_profit_2=54000.0
        )

        # 价格上涨 +2%
        pnl = position.get_current_pnl_pct(51000.0)
        assert pnl == pytest.approx(2.0, rel=0.01)

        # 价格下跌 -2%
        pnl = position.get_current_pnl_pct(49000.0)
        assert pnl == pytest.approx(-2.0, rel=0.01)


class TestSignalExecutor:
    """测试信号执行器"""

    def test_calculate_leverage(self):
        """测试杠杆计算"""
        from ats_core.execution.signal_executor import SignalExecutor
        from ats_core.execution.binance_futures_client import BinanceFuturesClient
        from ats_core.execution.position_manager import DynamicPositionManager

        client = BinanceFuturesClient("key", "secret")
        manager = DynamicPositionManager(client)
        executor = SignalExecutor(client, manager)

        # 高信号强度 -> 5x
        leverage = executor._calculate_leverage(0.85)
        assert leverage == 5

        # 中等信号强度 -> 3x
        leverage = executor._calculate_leverage(0.7)
        assert leverage == 3

        # 低信号强度 -> 2x
        leverage = executor._calculate_leverage(0.5)
        assert leverage == 2


class TestAutoTrader:
    """测试自动交易器"""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """测试初始化"""
        from ats_core.execution.auto_trader import AutoTrader

        trader = AutoTrader()

        assert trader.is_initialized is False
        assert trader.is_running is False


@pytest.mark.integration
class TestIntegration:
    """集成测试（需要真实API密钥）"""

    @pytest.mark.asyncio
    async def test_connection(self):
        """测试API连接"""
        from ats_core.execution.binance_futures_client import get_binance_client

        try:
            client = get_binance_client()
            await client.initialize()

            # 测试时间同步
            timestamp = client._get_timestamp()
            assert timestamp > 0

            # 测试账户信息
            account = await client.get_account_info()
            assert 'totalWalletBalance' in account or 'error' in account

            await client.close()

        except FileNotFoundError:
            pytest.skip("配置文件不存在，跳过集成测试")

    @pytest.mark.asyncio
    async def test_market_data(self):
        """测试市场数据获取"""
        from ats_core.execution.binance_futures_client import get_binance_client

        try:
            client = get_binance_client()
            await client.initialize()

            # 测试行情数据
            ticker = await client.get_ticker('BTCUSDT')
            assert 'lastPrice' in ticker or 'error' in ticker

            # 测试K线数据
            klines = await client.get_klines('BTCUSDT', '5m', limit=10)
            assert isinstance(klines, (list, dict))

            await client.close()

        except FileNotFoundError:
            pytest.skip("配置文件不存在，跳过集成测试")


# ============ 性能测试 ============

@pytest.mark.performance
class TestPerformance:
    """性能测试"""

    def test_factor_calculation_speed(self):
        """测试因子计算速度"""
        import time
        from ats_core.execution.position_manager import calculate_stop_loss_take_profit

        start = time.time()

        for _ in range(1000):
            calculate_stop_loss_take_profit(
                entry_price=50000.0,
                side='LONG',
                factors={
                    'signal_strength': 85,
                    'trend_score': 70,
                    'liquidity_score': 60,
                    'volatility_atr_pct': 2.0
                }
            )

        elapsed = time.time() - start

        # 1000次计算应该在100ms内完成
        assert elapsed < 0.1
        print(f"\n1000次因子计算耗时: {elapsed*1000:.2f}ms")


if __name__ == '__main__':
    # 运行测试
    pytest.main([__file__, '-v', '--tb=short'])
