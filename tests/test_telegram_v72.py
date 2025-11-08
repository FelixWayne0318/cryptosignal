# coding: utf-8
"""
测试v7.2 Telegram消息格式
"""
import sys
sys.path.insert(0, '/home/user/cryptosignal')

from ats_core.outputs.telegram_fmt import render_signal_v72, render_watch_v72, render_trade_v72
import time

# 模拟v7.2信号数据
def create_mock_v72_signal():
    """创建模拟的v7.2信号数据"""
    signal_data = {
        # 基础信息
        "symbol": "BTCUSDT",
        "price": 95234.50,
        "last": 95234.50,
        "side": "long",
        "timestamp": time.time() * 1000,

        # 原始因子
        "scores": {
            "T": 70,
            "M": 60,
            "C": 65,
            "V": 55,
            "O": 58,
            "B": 15,
            "I": 55
        },

        # 原始加权分数
        "weighted_score": 64.47,

        # 执行参数
        "tp_pct": 0.03,
        "sl_pct": 0.015,
        "TP": 0.03,
        "SL": 0.015,
        "position_size": 0.05,

        # 原始概率和EV
        "probability": 0.55,
        "expected_value": 0.010,
        "EV": 0.010,

        # 有效期
        "ttl_hours": 24,

        # v7.2增强数据
        "v72_enhancements": {
            # F因子v2
            "F_v2": 94,
            "F_v2_meta": {
                "fund_momentum": 4.24,
                "price_momentum": 0.81,
                "F_raw": 3.43
            },

            # 因子分组
            "group_scores": {
                "TC": 78.5,   # 趋势+资金流
                "VOM": 63.5,  # 量能+持仓+动量
                "B": 20.0     # 基差
            },
            "confidence_v72": 64.47,

            # 统计校准
            "P_calibrated": 0.630,
            "calibration_method": "bootstrap",  # 或 "statistical"

            # EV计算
            "EV_net": 0.0128,
            "EV_breakdown": {
                "TP_contribution": 0.0189,  # P * TP
                "SL_contribution": -0.0056,  # (1-P) * SL
                "cost": -0.0006
            },

            # 四道闸门
            "gate_results": {
                "gate1": {
                    "name": "data_quality",
                    "pass": True,
                    "bars": 200
                },
                "gate2": {
                    "name": "fund_support",
                    "pass": True,
                    "F_directional": 94
                },
                "gate3": {
                    "name": "market_risk",
                    "pass": True,
                    "independence": 55,
                    "market_regime": -15
                },
                "gate4": {
                    "name": "execution_cost",
                    "pass": True,
                    "EV_net": 0.0128
                }
            },

            # 最终判定
            "is_prime_v72": True,
            "all_gates_passed": True
        }
    }

    return signal_data


def test_v72_long_signal():
    """测试v7.2做多信号"""
    print("=" * 60)
    print("测试1: v7.2做多交易信号")
    print("=" * 60)

    signal = create_mock_v72_signal()
    message = render_trade_v72(signal)

    print(message)
    print("\n✅ 做多信号渲染成功")


def test_v72_short_signal():
    """测试v7.2做空信号"""
    print("\n" + "=" * 60)
    print("测试2: v7.2做空观察信号")
    print("=" * 60)

    signal = create_mock_v72_signal()

    # 修改为做空
    signal["side"] = "short"
    signal["scores"]["T"] = -65
    signal["scores"]["M"] = -55
    signal["weighted_score"] = -60
    signal["v72_enhancements"]["group_scores"]["TC"] = -70
    signal["v72_enhancements"]["confidence_v72"] = 60

    message = render_watch_v72(signal)

    print(message)
    print("\n✅ 做空信号渲染成功")


def test_v72_failed_gates():
    """测试v7.2闸门失败情况"""
    print("\n" + "=" * 60)
    print("测试3: v7.2闸门失败信号")
    print("=" * 60)

    signal = create_mock_v72_signal()

    # 修改F因子为负值（资金落后）
    signal["v72_enhancements"]["F_v2"] = -25
    signal["v72_enhancements"]["gate_results"]["gate2"]["pass"] = False
    signal["v72_enhancements"]["gate_results"]["gate2"]["F_directional"] = -25
    signal["v72_enhancements"]["all_gates_passed"] = False
    signal["v72_enhancements"]["is_prime_v72"] = False

    message = render_trade_v72(signal)

    print(message)
    print("\n✅ 闸门失败信号渲染成功")


def test_v72_minimal_data():
    """测试v7.2最小数据情况（无v72_enhancements）"""
    print("\n" + "=" * 60)
    print("测试4: v7.2最小数据（fallback到原始数据）")
    print("=" * 60)

    # 只有基础信息，没有v72_enhancements
    signal = {
        "symbol": "ETHUSDT",
        "price": 3456.78,
        "side": "long",
        "timestamp": time.time() * 1000,
        "scores": {
            "T": 60,
            "M": 50,
            "C": 55,
            "V": 45,
            "O": 50,
            "B": 10
        },
        "weighted_score": 55,
        "probability": 0.55,
        "expected_value": 0.008,
        "tp_pct": 0.025,
        "sl_pct": 0.012,
        "position_size": 0.04,
        "ttl_hours": 12
    }

    message = render_trade_v72(signal)

    print(message)
    print("\n✅ 最小数据渲染成功（使用fallback）")


def test_comparison():
    """对比v6.6和v7.2消息格式"""
    print("\n" + "=" * 60)
    print("测试5: v6.6 vs v7.2消息对比")
    print("=" * 60)

    signal = create_mock_v72_signal()

    # 导入v6.6渲染函数
    from ats_core.outputs.telegram_fmt import render_signal as render_signal_v66

    print("\n----- v6.6格式 -----")
    message_v66 = render_signal_v66(signal, is_watch=False)
    print(message_v66[:500] + "...")  # 只显示前500字符

    print("\n----- v7.2格式 -----")
    message_v72 = render_trade_v72(signal)
    print(message_v72[:500] + "...")  # 只显示前500字符

    print(f"\n✅ 对比完成")
    print(f"v6.6长度: {len(message_v66)} 字符")
    print(f"v7.2长度: {len(message_v72)} 字符")


if __name__ == "__main__":
    print("🧪 v7.2 Telegram消息格式测试")
    print("=" * 60)

    # 运行所有测试
    test_v72_long_signal()
    test_v72_short_signal()
    test_v72_failed_gates()
    test_v72_minimal_data()
    test_comparison()

    print("\n" + "=" * 60)
    print("✅ 所有测试完成！")
    print("=" * 60)
