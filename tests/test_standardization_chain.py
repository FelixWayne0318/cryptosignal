#!/usr/bin/env python3
# coding: utf-8
"""
验证StandardizationChain应用到11个因子
测试目标：确保所有因子正确调用StandardizationChain并返回稳健化分数

运行: python tests/test_standardization_chain.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_trend_factor():
    """测试T因子（trend.py）"""
    from ats_core.features.trend import score_trend, _trend_chain

    # 模拟数据
    h = [100 + i*0.5 for i in range(100)]
    l = [99 + i*0.5 for i in range(100)]
    c = [99.5 + i*0.5 for i in range(100)]
    c4 = c  # 兼容参数
    cfg = {}

    T, Tm = score_trend(h, l, c, c4, cfg)

    assert isinstance(T, int), "T must be int"
    assert -100 <= T <= 100, f"T={T} out of range"
    assert _trend_chain is not None, "Chain instance must exist"
    print(f"✓ T (Trend): {T:+4d} (Tm={Tm})")
    return True

def test_momentum_factor():
    """测试M因子（momentum.py）"""
    from ats_core.features.momentum import score_momentum, _momentum_chain

    h = [100 + i*0.3 for i in range(50)]
    l = [99 + i*0.3 for i in range(50)]
    c = [99.5 + i*0.3 for i in range(50)]

    M, meta = score_momentum(h, l, c)

    assert isinstance(M, int), "M must be int"
    assert -100 <= M <= 100, f"M={M} out of range"
    assert _momentum_chain is not None, "Chain instance must exist"
    print(f"✓ M (Momentum): {M:+4d}")
    return True

def test_volume_factor():
    """测试V因子（volume.py）"""
    from ats_core.features.volume import score_volume, _volume_chain

    vol = [1000 + i*10 for i in range(30)]
    closes = [100 + i*0.2 for i in range(30)]

    V, meta = score_volume(vol, closes)

    assert isinstance(V, int), "V must be int"
    assert -100 <= V <= 100, f"V={V} out of range"
    assert _volume_chain is not None, "Chain instance must exist"
    print(f"✓ V (Volume): {V:+4d}")
    return True

def test_cvd_factor():
    """测试C因子（cvd_flow.py）"""
    from ats_core.features.cvd_flow import score_cvd, _cvd_chain

    cvd_series = [i*100 for i in range(50)]

    C, meta = score_cvd(cvd_series)

    assert isinstance(C, int), "C must be int"
    assert -100 <= C <= 100, f"C={C} out of range"
    assert _cvd_chain is not None, "Chain instance must exist"
    print(f"✓ C (CVD Flow): {C:+4d}")
    return True

def test_oi_factor():
    """测试O因子（open_interest.py）"""
    from ats_core.features.open_interest import score_oi, _oi_chain

    oi_series = [1000000 + i*5000 for i in range(50)]
    close_series = [100 + i*0.1 for i in range(50)]

    O, meta = score_oi(oi_series, close_series)

    assert isinstance(O, int), "O must be int"
    assert -100 <= O <= 100, f"O={O} out of range"
    assert _oi_chain is not None, "Chain instance must exist"
    print(f"✓ O (Open Interest): {O:+4d}")
    return True

def test_liquidity_factor():
    """测试L因子（liquidity.py）"""
    from ats_core.factors_v2.liquidity import calculate_liquidity, _liquidity_chain

    # 模拟深度数据
    depth_data = {
        'bids': [[99.5, 100], [99.0, 200]],
        'asks': [[100.5, 100], [101.0, 200]]
    }
    current_price = 100.0
    volume_24h = 1000000.0

    L, meta = calculate_liquidity(depth_data, current_price, volume_24h)

    assert isinstance(L, int), "L must be int"
    assert 0 <= L <= 100, f"L={L} out of range"  # L is 0-100 not ±100
    assert _liquidity_chain is not None, "Chain instance must exist"
    print(f"✓ L (Liquidity): {L:4d}")
    return True

def test_basis_factor():
    """测试B因子（basis_funding.py）"""
    from ats_core.factors_v2.basis_funding import calculate_basis_funding, _basis_chain

    futures_price = 100.5
    spot_price = 100.0
    funding_rate = 0.0001

    B, meta = calculate_basis_funding(futures_price, spot_price, funding_rate)

    assert isinstance(B, int), "B must be int"
    assert -100 <= B <= 100, f"B={B} out of range"
    assert _basis_chain is not None, "Chain instance must exist"
    print(f"✓ B (Basis+Funding): {B:+4d}")
    return True

def test_liquidation_factor():
    """测试Q因子（liquidation.py）"""
    from ats_core.factors_v2.liquidation import calculate_liquidation, _liquidation_chain

    # 模拟清算数据
    liquidation_data = [
        {'price': 99.0, 'side': 'long', 'qty': 1000},
        {'price': 101.0, 'side': 'short', 'qty': 800}
    ]
    current_price = 100.0

    Q, meta = calculate_liquidation(liquidation_data, current_price)

    assert isinstance(Q, int), "Q must be int"
    assert -100 <= Q <= 100, f"Q={Q} out of range"
    assert _liquidation_chain is not None, "Chain instance must exist"
    print(f"✓ Q (Liquidation): {Q:+4d}")
    return True

def test_independence_factor():
    """测试I因子（independence.py）"""
    from ats_core.factors_v2.independence import calculate_independence, _independence_chain

    # 模拟价格序列
    alt_prices = [100 + i*0.3 for i in range(50)]
    btc_prices = [50000 + i*100 for i in range(50)]
    eth_prices = [3000 + i*50 for i in range(50)]

    I, beta_sum, meta = calculate_independence(alt_prices, btc_prices, eth_prices)

    assert isinstance(I, int), "I must be int"
    assert 0 <= I <= 100, f"I={I} out of range"  # I is 0-100 not ±100
    assert _independence_chain is not None, "Chain instance must exist"
    print(f"✓ I (Independence): {I:4d} (β_sum={beta_sum:.3f})")
    return True

def test_accel_factor():
    """测试S因子（accel.py）"""
    from ats_core.features.accel import score_accel, _accel_chain

    c = [100 + i*0.2 for i in range(50)]

    S, meta = score_accel(c)

    assert isinstance(S, int), "S must be int"
    assert 0 <= S <= 100, f"S={S} out of range"  # S is 0-100 not ±100
    assert _accel_chain is not None, "Chain instance must exist"
    print(f"✓ S (Accel): {S:4d}")
    return True

def test_funding_factor():
    """测试F因子（funding_rate.py）"""
    from ats_core.features.funding_rate import score_funding_rate, _funding_chain

    funding_rate = 0.0002  # 0.02%

    F, meta = score_funding_rate(funding_rate)

    assert isinstance(F, int), "F must be int"
    assert -100 <= F <= 100, f"F={F} out of range"
    assert _funding_chain is not None, "Chain instance must exist"
    print(f"✓ F (Funding Rate): {F:+4d}")
    return True

def main():
    """运行所有测试"""
    print("=" * 60)
    print("StandardizationChain 因子验证测试")
    print("=" * 60)

    tests = [
        ("T - Trend", test_trend_factor),
        ("M - Momentum", test_momentum_factor),
        ("V - Volume", test_volume_factor),
        ("C - CVD Flow", test_cvd_factor),
        ("O - Open Interest", test_oi_factor),
        ("S - Accel", test_accel_factor),
        ("F - Funding Rate", test_funding_factor),
        ("L - Liquidity", test_liquidity_factor),
        ("B - Basis+Funding", test_basis_factor),
        ("Q - Liquidation", test_liquidation_factor),
        ("I - Independence", test_independence_factor),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ {name}: FAILED - {e}")
            failed += 1

    print("=" * 60)
    print(f"测试结果: {passed}/{len(tests)} 通过")

    if failed == 0:
        print("✅ 所有因子StandardizationChain验证通过！")
        return 0
    else:
        print(f"❌ {failed}个因子测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
