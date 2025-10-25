# coding: utf-8
"""
诊断持仓 (O) 评分为 0 的问题
"""
import sys
sys.path.insert(0, "/home/user/cryptosignal")

from ats_core.sources.oi import fetch_oi_hourly
from ats_core.sources.binance import get_klines
from ats_core.features.open_interest import score_open_interest

def diagnose_oi(symbol="TRXUSDT"):
    print(f"\n{'='*60}")
    print(f"诊断 {symbol} 持仓数据")
    print('='*60)

    # 1. 获取 OI 数据
    print("\n1. 获取 OI 数据...")
    oi = fetch_oi_hourly(symbol, limit=200)
    print(f"   OI 数据点数: {len(oi)}")
    if oi:
        print(f"   最近 5 个值: {oi[-5:]}")
        print(f"   最新值: {oi[-1]}")
    else:
        print("   ⚠️ 未获取到 OI 数据！")
        return

    # 2. 获取价格数据
    print("\n2. 获取价格数据...")
    k1 = get_klines(symbol, "1h", 300)
    closes = [float(r[4]) for r in k1]
    print(f"   价格数据点数: {len(closes)}")
    print(f"   最新收盘价: {closes[-1]}")

    # 3. 计算 cvd6_fallback（用于兜底）
    cvd6 = 0.02  # 示例值

    # 4. 测试多头侧评分
    print("\n3. 测试多头侧评分...")
    params = {
        "long_oi24_lo": 1.0,
        "long_oi24_hi": 8.0,
        "upup12_lo": 6,
        "upup12_hi": 12,
        "w_change": 0.7,
        "w_align": 0.3,
        "crowding_p95_penalty": 10
    }

    O_long, meta_long = score_open_interest(symbol, closes, True, params, cvd6)
    print(f"   多头侧 O 分数: {O_long}")
    print(f"   元数据: {meta_long}")

    # 5. 测试空头侧评分
    print("\n4. 测试空头侧评分...")
    params["short_oi24_lo"] = 2.0
    params["short_oi24_hi"] = 10.0
    params["dnup12_lo"] = 6
    params["dnup12_hi"] = 12

    O_short, meta_short = score_open_interest(symbol, closes, False, params, cvd6)
    print(f"   空头侧 O 分数: {O_short}")
    print(f"   元数据: {meta_short}")

    print("\n" + "="*60)
    print("诊断完成")
    print("="*60 + "\n")

if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else "TRXUSDT"
    diagnose_oi(symbol)
