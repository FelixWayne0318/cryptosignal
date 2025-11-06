#!/usr/bin/env python3
"""
快速测试脚本：分析单个币种并输出详细格式
用于验证 Problem 3 修复效果
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ats_core.pipeline.analyze_symbol import analyze_symbol_v6
from ats_core.outputs.telegram_fmt import render_signal_detailed
from ats_core.data.unified_data_manager import get_klines
import json

def test_symbol(symbol: str):
    """测试单个币种的分析结果"""
    print(f"\n{'='*60}")
    print(f"分析币种: {symbol}")
    print(f"{'='*60}\n")

    # 1. 获取K线数据
    print("📊 获取K线数据...")
    klines_1h = get_klines(symbol, "1h", limit=300)
    klines_4h = get_klines(symbol, "4h", limit=200)
    klines_15m = get_klines(symbol, "15m", limit=200)
    klines_1d = get_klines(symbol, "1d", limit=100)

    if not klines_1h or len(klines_1h) < 100:
        print(f"❌ {symbol} K线数据不足")
        return

    print(f"✓ 1h: {len(klines_1h)}根, 4h: {len(klines_4h)}根, 15m: {len(klines_15m)}根, 1d: {len(klines_1d)}根")

    # 2. 运行分析
    print("\n🔍 运行分析...")
    result = analyze_symbol_v6(
        symbol=symbol,
        klines_1h=klines_1h,
        klines_4h=klines_4h,
        klines_15m=klines_15m,
        klines_1d=klines_1d,
        verbose=True
    )

    if not result:
        print(f"❌ {symbol} 分析失败")
        return

    # 3. 显示关键数据
    print("\n" + "="*60)
    print("核心数据")
    print("="*60)

    # 显示评分
    confidence = result.get("confidence", 0)
    prime_strength = result.get("prime_strength", 0)
    P_chosen = result.get("P_chosen", 0)
    print(f"\n📈 评分:")
    print(f"   置信度: {confidence}")
    print(f"   Prime强度: {prime_strength}")
    print(f"   概率: {P_chosen:.3f}")

    # 显示因子
    scores = result.get("scores", {})
    print(f"\n🔢 A-层核心因子:")
    print(f"   T={scores.get('T',0):.1f}, M={scores.get('M',0):.1f}, C={scores.get('C',0):.1f}")
    print(f"   V={scores.get('V',0):.1f}, O={scores.get('O',0):.1f}, B={scores.get('B',0):.1f}")

    # 显示调制器
    print(f"\n⚙️ B-层调制器:")
    print(f"   L={result.get('L',0):.1f}, S={result.get('S',0):.1f}")
    print(f"   F={result.get('F',0):.1f}, I={result.get('I',0):.1f}")

    # 显示四门
    gates = result.get("gates", {})
    print(f"\n🚪 四门调节:")
    print(f"   DataQual={gates.get('data_qual',0):.3f}")
    print(f"   EV={gates.get('ev_gate',0):.3f}")
    print(f"   Execution={gates.get('execution',0):.3f}")
    print(f"   Probability={gates.get('probability',0):.3f}")

    # ⭐ 重点：显示 fi_thresholds（问题3修复的核心）
    fi_thresholds = result.get("fi_thresholds", {})
    if fi_thresholds:
        print(f"\n{'='*60}")
        print("🎯 FI Thresholds（问题3修复核心）")
        print(f"{'='*60}")
        print(f"   p_min_base: {fi_thresholds.get('p_min_base', 0):.4f}")
        print(f"   p_min_adjusted: {fi_thresholds.get('p_min_adjusted', 0):.4f}")
        print(f"   F_normalized: {fi_thresholds.get('F_normalized', 0):.4f}")
        print(f"   I_normalized: {fi_thresholds.get('I_normalized', 0):.4f}")
        print(f"   g_F: {fi_thresholds.get('g_F', 0):.4f}")
        print(f"   g_I: {fi_thresholds.get('g_I', 0):.4f}")
        print(f"   adj_F (F的p_min调整): {fi_thresholds.get('adj_F', 0):+.4f}")
        print(f"   adj_I (I的p_min调整): {fi_thresholds.get('adj_I', 0):+.4f}")
        print(f"   safety_adjustment: {fi_thresholds.get('safety_adjustment', 0):+.4f}")

        # 显示完整公式
        p_min_base = fi_thresholds.get('p_min_base', 0)
        adj_F = fi_thresholds.get('adj_F', 0)
        adj_I = fi_thresholds.get('adj_I', 0)
        safety_adj = fi_thresholds.get('safety_adjustment', 0)
        p_min_final = fi_thresholds.get('p_min_adjusted', 0)

        print(f"\n   📐 完整公式:")
        print(f"   p_min = {p_min_base:.4f} + F{adj_F:+.4f} + I{adj_I:+.4f} + 安全{safety_adj:+.4f}")
        print(f"         = {p_min_final:.4f}")

        # 验证 I 因子是否生效
        if abs(adj_I) > 0.0001:
            print(f"\n   ✅ I因子已生效（贡献: {adj_I:+.4f}）")
        else:
            print(f"\n   ⚠️ I因子未生效或贡献为0")
    else:
        print(f"\n⚠️ 没有找到 fi_thresholds 数据（可能使用了旧版本）")

    # 4. 显示 Telegram 详细格式（包含新的 p_min 调整显示）
    print(f"\n{'='*60}")
    print("📱 Telegram 详细格式输出")
    print(f"{'='*60}\n")

    telegram_output = render_signal_detailed(result, is_watch=False)
    print(telegram_output)

    # 5. 显示拒绝原因（如果有）
    rejection_reason = result.get("rejection_reason", [])
    if rejection_reason:
        print(f"\n{'='*60}")
        print("❌ 拒绝原因")
        print(f"{'='*60}")
        for reason in rejection_reason:
            print(f"   {reason}")
    else:
        print(f"\n✅ 通过所有门槛")

    print(f"\n{'='*60}\n")

if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else "KNCUSDT"
    test_symbol(symbol)
