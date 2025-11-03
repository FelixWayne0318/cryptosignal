#!/usr/bin/env python3
# coding: utf-8
"""
测试增强型监控输出
"""

from ats_core.outputs.telegram_fmt import (
    render_signal_detailed,
    render_weights_summary,
    render_prime_breakdown,
    render_four_gates,
    render_modulators
)

# 构造测试数据（模拟analyze_symbol的返回结果）
test_result = {
    "symbol": "BTCUSDT",
    "price": 42530.50,
    "side": "long",
    "probability": 0.72,
    "ttl_h": 8,
    "prime_strength": 85,
    "confidence": 72,
    "weighted_score": 63,
    "expected_value": 0.023,
    "data_quality": 0.95,
    "p_min": 0.62,
    "delta_p_min": 0.12,

    # A层因子分数
    "T": 80,
    "M": 52,
    "C": 75,
    "S": 45,
    "V": 60,
    "O": 68,
    "L": 72,
    "B": 38,
    "Q": 0,
    "I": 25,

    # B层调节器
    "F": 45,
    "F_score": 45,
    "F_adjustment": 1.0,

    # 权重配置
    "weights": {
        "T": 13.9, "M": 8.3, "C": 11.1, "S": 5.6, "V": 8.3,
        "O": 11.1, "L": 11.1, "B": 8.3, "Q": 5.6, "I": 6.7, "F": 10.0
    },

    # 因子元数据
    "scores_meta": {
        "T": {
            "Tm": 1,
            "ema_up": True
        },
        "M": {
            "slope_now": 0.0025,
            "accel": 0.0012
        },
        "C": {
            "cvd6": 0.035,
            "is_consistent": True,
            "consistency": 0.85,
            "r_squared": 0.82
        },
        "S": {
            "theta": 0.45
        },
        "V": {
            "v5v20": 1.35
        },
        "O": {
            "oi24h_pct": 12.5
        },
        "L": {
            "spread_bps": 8.5,
            "obi": 0.15
        },
        "B": {
            "basis_bps": 25.0,
            "funding_rate": 0.0001
        },
        "Q": {
            "lti": 0.0
        },
        "I": {
            "beta_sum": 0.85
        },
        "F": {
            "leading_raw": 0.35
        }
    },

    # 定价信息
    "pricing": {
        "entry_lo": 42400,
        "entry_hi": 42600,
        "sl": 41800,
        "tp1": 43500,
        "tp2": 44200
    },

    # 其他
    "note": "测试信号",
    "slippage_bps": 15.0
}

def test_all_functions():
    """测试所有增强型输出函数"""

    print("=" * 70)
    print("测试1: render_weights_summary()")
    print("=" * 70)
    print(render_weights_summary(test_result))
    print()

    print("=" * 70)
    print("测试2: render_modulators()")
    print("=" * 70)
    print(render_modulators(test_result))
    print()

    print("=" * 70)
    print("测试3: render_four_gates()")
    print("=" * 70)
    print(render_four_gates(test_result))
    print()

    print("=" * 70)
    print("测试4: render_prime_breakdown()")
    print("=" * 70)
    print(render_prime_breakdown(test_result))
    print()

    print("=" * 70)
    print("测试5: render_signal_detailed() - 完整详细模式")
    print("=" * 70)
    print(render_signal_detailed(test_result, is_watch=False))
    print()

if __name__ == "__main__":
    test_all_functions()
