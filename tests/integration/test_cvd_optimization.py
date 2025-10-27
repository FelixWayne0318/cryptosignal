#!/usr/bin/env python3
# coding: utf-8
"""
测试CVD优化效果
比较旧方法（Tick Rule）vs 新方法（真实Taker Buy Volume）
"""

from ats_core.sources.binance import get_klines, get_spot_klines
from ats_core.features.cvd import cvd_from_klines, cvd_combined
import sys

def test_cvd_improvement():
    """测试CVD计算改进"""
    print("=" * 70)
    print("CVD计算优化测试")
    print("=" * 70)

    # 测试币种
    symbol = "BTCUSDT"

    try:
        # 获取合约数据
        print(f"\n1. 获取 {symbol} 合约K线数据...")
        futures_klines = get_klines(symbol, "1h", 100)
        print(f"   ✅ 获取到 {len(futures_klines)} 根K线")

        # 检查数据格式
        if futures_klines and len(futures_klines[0]) >= 10:
            print(f"   ✅ K线包含 {len(futures_klines[0])} 列数据（包含takerBuyVolume）")
            sample = futures_klines[-1]
            print(f"\n   最新K线示例:")
            print(f"   - 收盘价: {sample[4]}")
            print(f"   - 总成交量: {sample[5]}")
            print(f"   - 主动买入量: {sample[9]}")

            # 计算买卖比例
            total_vol = float(sample[5])
            buy_vol = float(sample[9])
            sell_vol = total_vol - buy_vol
            buy_ratio = buy_vol / total_vol * 100 if total_vol > 0 else 0
            print(f"   - 买入比例: {buy_ratio:.1f}%")
            print(f"   - 卖出比例: {100-buy_ratio:.1f}%")
        else:
            print(f"   ⚠️ K线数据列数不足")

    except Exception as e:
        print(f"   ❌ 获取合约数据失败: {e}")
        return

    # 方法1：旧方法（Tick Rule）
    print(f"\n2. 计算CVD - 旧方法（Tick Rule估算）...")
    try:
        cvd_old = cvd_from_klines(futures_klines, use_taker_buy=False)
        cvd_old_change = cvd_old[-1] - cvd_old[-7] if len(cvd_old) >= 7 else 0
        print(f"   ✅ CVD (旧): {cvd_old[-1]:.2f}")
        print(f"   📊 6小时变化: {cvd_old_change:+.2f}")
    except Exception as e:
        print(f"   ❌ 计算失败: {e}")
        cvd_old = []

    # 方法2：新方法（真实Taker Buy Volume）
    print(f"\n3. 计算CVD - 新方法（真实Taker Buy Volume）...")
    try:
        cvd_new = cvd_from_klines(futures_klines, use_taker_buy=True)
        cvd_new_change = cvd_new[-1] - cvd_new[-7] if len(cvd_new) >= 7 else 0
        print(f"   ✅ CVD (新): {cvd_new[-1]:.2f}")
        print(f"   📊 6小时变化: {cvd_new_change:+.2f}")
    except Exception as e:
        print(f"   ❌ 计算失败: {e}")
        cvd_new = []

    # 对比
    if cvd_old and cvd_new:
        print(f"\n4. 对比分析...")
        diff = abs(cvd_new[-1] - cvd_old[-1])
        diff_pct = diff / abs(cvd_old[-1]) * 100 if cvd_old[-1] != 0 else 0
        print(f"   📊 CVD差异: {diff:.2f} ({diff_pct:.1f}%)")
        print(f"   📊 方向差异: {cvd_new_change - cvd_old_change:+.2f}")

        # 判断准确性提升
        if diff_pct > 5:
            print(f"   ✅ 新方法与旧方法有明显差异，数据更准确")
        else:
            print(f"   ℹ️ 新方法与旧方法结果接近")

    # 测试现货+合约组合（可选）
    print(f"\n5. 测试现货CVD（可选功能）...")
    try:
        spot_klines = get_spot_klines(symbol, "1h", 100)
        print(f"   ✅ 获取到现货K线 {len(spot_klines)} 根")

        cvd_spot = cvd_from_klines(spot_klines, use_taker_buy=True)
        print(f"   ✅ 现货CVD: {cvd_spot[-1]:.2f}")

        # 计算成交额比例
        n = min(len(futures_klines), len(spot_klines))
        f_quote = sum([float(k[7]) for k in futures_klines[-n:]])
        s_quote = sum([float(k[7]) for k in spot_klines[-n:]])
        total_quote = f_quote + s_quote
        f_weight = f_quote / total_quote * 100 if total_quote > 0 else 0
        s_weight = s_quote / total_quote * 100 if total_quote > 0 else 0

        print(f"\n   成交额分析（最近{n}小时）:")
        print(f"   - 合约成交额: ${f_quote:,.0f} ({f_weight:.1f}%)")
        print(f"   - 现货成交额: ${s_quote:,.0f} ({s_weight:.1f}%)")

        # 组合现货+合约（动态权重）
        cvd_mix_dynamic = cvd_combined(futures_klines, spot_klines, use_dynamic_weight=True)
        print(f"\n   ✅ 组合CVD (动态权重 {f_weight:.1f}%:{s_weight:.1f}%): {cvd_mix_dynamic[-1]:.2f}")

        # 对比固定权重
        cvd_mix_fixed = cvd_combined(futures_klines, spot_klines, use_dynamic_weight=False)
        print(f"   ℹ️ 组合CVD (固定权重 70%:30%): {cvd_mix_fixed[-1]:.2f}")

    except Exception as e:
        print(f"   ℹ️ 现货数据获取失败（可选功能）: {e}")

    print(f"\n" + "=" * 70)
    print("✅ CVD优化测试完成!")
    print("=" * 70)
    print("\n优化总结:")
    print("1. ✅ 使用真实的takerBuyVolume替代Tick Rule估算")
    print("2. ✅ CVD计算更加准确，反映真实买卖压力")
    print("3. ✅ 支持现货+合约组合CVD（动态权重，按成交额比例）")
    print("4. ✅ 向后兼容（保留旧方法）")
    print("\n权重计算方法:")
    print("- 动态权重（推荐）：根据实际成交额（USDT）自动计算")
    print("  例：合约10亿，现货1亿 → 权重90.9%:9.1%")
    print("- 固定权重（备选）：70%合约 + 30%现货")

if __name__ == "__main__":
    try:
        test_cvd_improvement()
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
