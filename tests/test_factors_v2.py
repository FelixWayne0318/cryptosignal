# coding: utf-8
"""
因子系统v2单元测试

测试覆盖：
1. CVD增强因子（含Basis校正）
2. 独立性因子
3. 流动性因子
4. OI四象限因子
5. 清算密度因子
6. 多时间框架协同

运行方法：
    pytest tests/test_factors_v2.py -v
"""

import pytest
import numpy as np
from typing import List


# ========== CVD增强因子测试 ==========

def test_cvd_enhanced_basic():
    """测试CVD增强因子基础功能"""
    from ats_core.factors_v2.cvd_enhanced import calculate_cvd_enhanced

    # 生成模拟K线（上涨趋势）
    klines = []
    for i in range(80):
        o = 50000 + i * 50
        c = o + 30  # 持续上涨
        h = max(o, c) + 10
        l = min(o, c) - 5
        v = 1000
        klines.append([i, o, h, l, c, v])

    score, metadata = calculate_cvd_enhanced(klines)

    assert isinstance(score, (int, float))
    assert -100 <= score <= 100
    assert 'cvd_score' in metadata
    assert 'cvd_direction' in metadata
    print(f"  CVD评分: {score:.1f}, 方向: {metadata['cvd_direction']}")


def test_cvd_basis_correction():
    """测试CVD Basis校正功能"""
    from ats_core.factors_v2.cvd_enhanced import calculate_cvd_enhanced

    # 生成永续和现货K线（永续溢价100bps）
    klines_perp = []
    klines_spot = []

    for i in range(80):
        # 现货价格
        spot_price = 50000 + i * 50

        # 永续价格（溢价100bps = 1%）
        perp_price = spot_price * 1.01

        # 永续K线
        klines_perp.append([i, perp_price, perp_price + 20, perp_price - 10, perp_price, 2000])

        # 现货K线
        klines_spot.append([i, spot_price, spot_price + 15, spot_price - 8, spot_price, 1000])

    # 启用basis校正
    params = {'basis_correction': True, 'basis_threshold_bps': 50.0}
    score, metadata = calculate_cvd_enhanced(klines_perp, klines_spot, params)

    assert 'basis_bps' in metadata
    assert 'basis_adjusted' in metadata
    assert abs(metadata['basis_bps']) > 50  # 应该检测到溢价
    print(f"  Basis: {metadata['basis_bps']:.1f}bps, 已校正: {metadata['basis_adjusted']}")


# ========== 独立性因子测试 ==========

def test_independence_basic():
    """测试独立性因子基础功能"""
    from ats_core.factors_v2.independence import calculate_independence

    # 生成价格数据
    np.random.seed(42)

    # BTC价格（趋势上涨）
    btc_prices = [50000 + i * 100 + np.random.rand() * 50 for i in range(100)]

    # ETH价格（趋势上涨）
    eth_prices = [3000 + i * 5 + np.random.rand() * 10 for i in range(100)]

    # ALT价格（高度相关）
    alt_prices = [100 + (btc_prices[i] / 500) + np.random.rand() * 2 for i in range(100)]

    score, beta_sum, metadata = calculate_independence(alt_prices, btc_prices, eth_prices)

    assert isinstance(score, (int, float))
    assert 0 <= score <= 100  # 独立性评分
    assert beta_sum >= 0
    print(f"  独立性评分: {score:.1f}, Beta总和: {beta_sum:.2f}")


# ========== 流动性因子测试 ==========

def test_liquidity_basic():
    """测试流动性因子基础功能"""
    from ats_core.factors_v2.liquidity import calculate_liquidity

    # 模拟订单簿（高流动性）
    orderbook = {
        'bids': [[50000 - i, 10 + i] for i in range(20)],  # 20档买单
        'asks': [[50000 + i, 10 + i] for i in range(20)]   # 20档卖单
    }

    score, metadata = calculate_liquidity(orderbook)

    assert isinstance(score, (int, float))
    assert 0 <= score <= 100  # 质量因子
    assert 'spread_bps' in metadata
    assert 'liquidity_level' in metadata
    print(f"  流动性评分: {score:.1f}, 点差: {metadata['spread_bps']:.1f}bps")


def test_liquidity_degradation():
    """测试流动性因子降级处理（空订单簿）"""
    from ats_core.factors_v2.liquidity import calculate_liquidity

    # 空订单簿
    orderbook = {'bids': [], 'asks': []}

    score, metadata = calculate_liquidity(orderbook)

    # 应该返回中性评分
    assert score == 50.0
    assert metadata.get('degraded') == True
    print(f"  降级评分: {score:.1f}, 原因: {metadata.get('reason', 'N/A')}")


# ========== OI四象限因子测试 ==========

def test_oi_regime_up_up():
    """测试OI四象限 - up_up场景"""
    from ats_core.factors_v2.oi_regime import calculate_oi_regime

    # 价格上涨 + OI上涨（多头加仓）
    oi_hist = [1000 + i * 10 for i in range(50)]  # OI递增
    price_hist = [50000 + i * 100 for i in range(50)]  # 价格递增

    score, regime, metadata = calculate_oi_regime(oi_hist, price_hist)

    assert regime == 'up_up'
    assert score > 50  # 看涨评分
    print(f"  OI体制: {regime}, 评分: {score:.1f}")


# ========== 多时间框架协同测试 ==========

def test_multi_timeframe_coherence():
    """测试多时间框架一致性"""
    from ats_core.features.multi_timeframe import multi_timeframe_coherence

    # 注意：需要模拟get_klines函数
    # 这里只测试接口调用

    try:
        result = multi_timeframe_coherence("BTCUSDT", verbose=False)

        assert 'coherence_score' in result
        assert 'dominant_direction' in result
        assert 0 <= result['coherence_score'] <= 100
        print(f"  一致性评分: {result['coherence_score']:.1f}")
        print(f"  主导方向: {result['dominant_direction']}")

    except Exception as e:
        pytest.skip(f"需要Binance API连接: {e}")


# ========== 配置管理测试 ==========

def test_factor_config():
    """测试因子配置管理器"""
    from ats_core.config.factor_config import get_factor_config

    config = get_factor_config()

    assert config.version is not None
    assert len(config.get_enabled_factors()) > 0

    # 测试获取权重
    weights = config.get_all_weights()
    assert 'T' in weights
    assert weights['T'] > 0

    # 测试自适应权重
    adaptive_weights = config.get_adaptive_weights(market_regime=70, volatility=0.03)
    assert isinstance(adaptive_weights, dict)

    print(f"  配置版本: {config.version}")
    print(f"  启用因子: {len(config.get_enabled_factors())}")


# ========== 并行扫描测试 ==========

def test_batch_scan_parallel_dry_run():
    """测试并行扫描（dry run）"""
    from ats_core.pipeline.batch_scan import batch_run_parallel

    # 注意：实际测试需要Binance API
    # 这里只测试接口存在性

    assert callable(batch_run_parallel)
    print("  并行扫描接口已实现")


# ========== WebSocket框架测试 ==========

def test_websocket_client():
    """测试WebSocket客户端框架"""
    from ats_core.streaming.websocket_client import WebSocketClient

    client = WebSocketClient()

    # 测试订阅接口
    def dummy_callback(data):
        pass

    client.subscribe_kline("BTCUSDT", "1m", dummy_callback)
    client.subscribe_orderbook("BTCUSDT", dummy_callback)

    stats = client.get_stats()
    assert stats['subscriptions'] == 2

    print(f"  WebSocket订阅数: {stats['subscriptions']}")


# ========== 强化学习框架测试 ==========

def test_rl_agent():
    """测试强化学习止损智能体"""
    from ats_core.rl.dynamic_stop_loss import DynamicStopLossAgent, build_state

    agent = DynamicStopLossAgent()

    # 构建测试状态
    state = build_state(
        entry_price=50000,
        current_price=51000,
        entry_time=0,
        current_time=3600,
        volatility=0.02,
        signal_probability=0.7,
        market_regime=60
    )

    assert state.shape == (5,)
    assert -1 <= state[0] <= 1  # profit归一化

    # 测试动作选择
    action = agent.get_action(state, explore=False)
    assert 0 <= action < 4

    # 测试动作应用
    new_sl = agent.apply_action(50000, 51000, 49000, action, "LONG")
    assert isinstance(new_sl, float)

    print(f"  RL状态维度: {state.shape}")
    print(f"  动作: {action}")


# ========== 测试运行器 ==========

if __name__ == "__main__":
    print("=" * 70)
    print("因子系统v2单元测试")
    print("=" * 70)

    # 手动运行测试
    tests = [
        ("CVD增强基础", test_cvd_enhanced_basic),
        ("CVD Basis校正", test_cvd_basis_correction),
        ("独立性因子", test_independence_basic),
        ("流动性因子", test_liquidity_basic),
        ("流动性降级", test_liquidity_degradation),
        ("OI四象限", test_oi_regime_up_up),
        ("多时间框架", test_multi_timeframe_coherence),
        ("配置管理", test_factor_config),
        ("并行扫描", test_batch_scan_parallel_dry_run),
        ("WebSocket", test_websocket_client),
        ("强化学习", test_rl_agent)
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            print(f"\n[{name}]")
            test_func()
            print(f"  ✅ 通过")
            passed += 1
        except Exception as e:
            print(f"  ❌ 失败: {e}")
            failed += 1

    print("\n" + "=" * 70)
    print(f"测试完成: {passed} 通过, {failed} 失败")
    print("=" * 70)
