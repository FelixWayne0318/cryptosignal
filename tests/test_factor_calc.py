#!/usr/bin/env python3
# coding: utf-8
"""
快速测试：检查因子计算是否正常工作
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ats_core.sources.binance import get_klines

print("=" * 70)
print("测试因子计算 - BTCUSDT")
print("=" * 70)

# 1. 获取K线数据
print("\n【1. 获取K线数据】")
try:
    k1 = get_klines('BTCUSDT', '1h', 300)
    k4 = get_klines('BTCUSDT', '4h', 200)
    print(f"✅ 1h K线: {len(k1)}根")
    print(f"✅ 4h K线: {len(k4)}根")

    # 提取HLCV
    h = [float(x[2]) for x in k1]
    l = [float(x[3]) for x in k1]
    c = [float(x[4]) for x in k1]
    c4 = [float(x[4]) for x in k4]

    print(f"最新收盘价: {c[-1]:.2f}")
except Exception as e:
    print(f"❌ 获取K线失败: {e}")
    sys.exit(1)

# 2. 测试T因子
print("\n【2. 测试T因子（趋势）】")
try:
    from ats_core.features.trend import score_trend
    T, Tm = score_trend(h, l, c, c4, {})
    print(f"✅ T因子: {T:+.1f}")
    print(f"   Tm: {Tm}")
except Exception as e:
    print(f"❌ T因子计算失败: {e}")
    import traceback
    traceback.print_exc()

# 3. 测试M因子
print("\n【3. 测试M因子（动量）】")
try:
    from ats_core.features.momentum import score_momentum
    M, meta = score_momentum(h, l, c, {})
    print(f"✅ M因子: {M:+.1f}")
except Exception as e:
    print(f"❌ M因子计算失败: {e}")
    import traceback
    traceback.print_exc()

# 4. 测试V因子
print("\n【4. 测试V因子（量能）】")
try:
    q = [float(x[5]) for x in k1]  # 成交量
    from ats_core.features.volume import score_volume
    V, meta = score_volume(q, closes=c)
    print(f"✅ V因子: {V:+.1f}")
except Exception as e:
    print(f"❌ V因子计算失败: {e}")
    import traceback
    traceback.print_exc()

# 5. 测试C因子
print("\n【5. 测试C因子（CVD）】")
try:
    from ats_core.factors_v2.cvd_enhanced import calculate_cvd_enhanced
    C, meta = calculate_cvd_enhanced(k1, {})
    print(f"✅ C因子: {C:+.1f}")
except Exception as e:
    print(f"❌ C因子计算失败: {e}")
    import traceback
    traceback.print_exc()

# 6. 测试S因子
print("\n【6. 测试S因子（结构）】")
try:
    from ats_core.features.structure_sq import score_structure
    atr_now = sum(abs(h[i] - l[i]) for i in range(-14, 0)) / 14
    ema30_last = sum(c[-30:]) / 30
    S, meta = score_structure(h, l, c, ema30_last, atr_now, {})
    print(f"✅ S因子: {S:+.1f}")
except Exception as e:
    print(f"❌ S因子计算失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("测试完成")
print("=" * 70)
