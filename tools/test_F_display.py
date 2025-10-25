# coding: utf-8
"""
测试七维显示（使用模拟数据）
"""
import sys
sys.path.insert(0, "/home/user/cryptosignal")

from ats_core.outputs.telegram_fmt import render_signal

# 模拟一个完整的七维分析结果（价格领先场景）
mock_result = {
    "symbol": "ETHUSDT",
    "price": 3250.50,
    "side": "long",
    "probability": 0.54,
    "ttl_h": 8,

    # 七维分数
    "T": 67,
    "S": 55,
    "V": 48,
    "A": 52,
    "O": 45,
    "E": 60,
    "F": 0,  # 极低分数

    # 所有维度的元数据（包含真实底层数据）
    "scores_meta": {
        "T": {
            "Tm": 1,  # 多头趋势
            "slopeATR": 0.05,
            "emaOrder": 1
        },
        "S": {
            "theta": 0.42,  # 结构角度
            "icr": 0.55,
            "retr": 0.48
        },
        "V": {
            "v5v20": 1.15,  # 量能比率
            "vroc_abs": 0.025,
            "vlevel_score": 52,
            "vroc_score": 45
        },
        "A": {
            "cvd6": 0.018,  # CVD +1.8%
            "dslope30": 0.035,
            "weak_ok": True,
            "slope_score": 58,
            "cvd_score": 48
        },
        "O": {
            "oi24h_pct": 2.3,  # OI +2.3%
            "oi1h_pct": 0.8,
            "upup12": 0.52,
            "crowding_warn": False
        },
        "E": {
            "chop": 38,  # Chop 指数 38
            "room": 1.2
        },
        "F": {
            "fund_momentum": 17.9,
            "price_momentum": 80.2,
            "leading_raw": -62.3  # 价格远远领先资金
        }
    }
}

print("="*80)
print("测试场景 1：价格领先（追高风险）")
print("="*80)
print(f"\n关键数据：")
print(f"  • 趋势: T={mock_result['T']} (Tm={mock_result['scores_meta']['T']['Tm']})")
print(f"  • 结构: S={mock_result['S']} (θ={mock_result['scores_meta']['S']['theta']:.2f})")
print(f"  • 量能: V={mock_result['V']} (v5/v20={mock_result['scores_meta']['V']['v5v20']:.2f})")
print(f"  • 加速: A={mock_result['A']} (CVD={mock_result['scores_meta']['A']['cvd6']*100:.1f}%)")
print(f"  • 持仓: O={mock_result['O']} (OI 24h={mock_result['scores_meta']['O']['oi24h_pct']:.1f}%)")
print(f"  • 环境: E={mock_result['E']} (Chop={mock_result['scores_meta']['E']['chop']:.0f})")
print(f"  • 资金: F={mock_result['F']} (leading_raw={mock_result['scores_meta']['F']['leading_raw']:.1f})")
print("\n" + "="*80)
print("Telegram 消息预览：")
print("="*80)
print()
print(render_signal(mock_result, is_watch=False))
print()

# 测试资金领先场景（完整七维数据）
mock_result_good = {
    "symbol": "BTCUSDT",
    "price": 98500.00,
    "side": "long",
    "probability": 0.72,
    "ttl_h": 8,

    # 七维分数
    "T": 55,
    "S": 65,
    "V": 72,
    "A": 68,
    "O": 75,
    "E": 60,
    "F": 78,  # 高分

    # 所有维度的元数据
    "scores_meta": {
        "T": {
            "Tm": 1,  # 多头趋势
            "slopeATR": 0.03,
            "emaOrder": 1
        },
        "S": {
            "theta": 0.48,  # 结构良好
            "icr": 0.68,
            "retr": 0.55
        },
        "V": {
            "v5v20": 1.85,  # 放量
            "vroc_abs": 0.055,
            "vlevel_score": 78,
            "vroc_score": 65
        },
        "A": {
            "cvd6": 0.042,  # CVD +4.2%
            "dslope30": 0.052,
            "weak_ok": True,
            "slope_score": 72,
            "cvd_score": 65
        },
        "O": {
            "oi24h_pct": 5.8,  # OI +5.8%
            "oi1h_pct": 1.5,
            "upup12": 0.78,
            "crowding_warn": False
        },
        "E": {
            "chop": 32,  # Chop 较低（趋势性好）
            "room": 2.5
        },
        "F": {
            "fund_momentum": 75.5,
            "price_momentum": 30.2,
            "leading_raw": 45.3  # 资金领先价格
        }
    }
}

print("\n" + "="*80)
print("测试场景 2：资金领先（蓄势待发）")
print("="*80)
print(f"\n关键数据：")
print(f"  • 趋势: T={mock_result_good['T']} (Tm={mock_result_good['scores_meta']['T']['Tm']})")
print(f"  • 结构: S={mock_result_good['S']} (θ={mock_result_good['scores_meta']['S']['theta']:.2f})")
print(f"  • 量能: V={mock_result_good['V']} (v5/v20={mock_result_good['scores_meta']['V']['v5v20']:.2f})")
print(f"  • 加速: A={mock_result_good['A']} (CVD={mock_result_good['scores_meta']['A']['cvd6']*100:.1f}%)")
print(f"  • 持仓: O={mock_result_good['O']} (OI 24h={mock_result_good['scores_meta']['O']['oi24h_pct']:.1f}%)")
print(f"  • 环境: E={mock_result_good['E']} (Chop={mock_result_good['scores_meta']['E']['chop']:.0f})")
print(f"  • 资金: F={mock_result_good['F']} (leading_raw={mock_result_good['scores_meta']['F']['leading_raw']:.1f})")
print("\n" + "="*80)
print("Telegram 消息预览：")
print("="*80)
print()
print(render_signal(mock_result_good, is_watch=False))
