# coding: utf-8
"""
诊断 F（资金领先性）的计算过程
"""
import sys
sys.path.insert(0, "/home/user/cryptosignal")

from ats_core.pipeline.analyze_symbol import analyze_symbol
import json

def diagnose_F(symbol="ETHUSDT"):
    print(f"\n{'='*80}")
    print(f"诊断 {symbol} 的 F（资金领先性）计算")
    print('='*80)

    try:
        r = analyze_symbol(symbol)

        # 基本信息
        print(f"\n【基本信息】")
        print(f"方向: {r['side']}")
        print(f"概率: P={r['probability']:.3f} (P_long={r['P_long']:.3f}, P_short={r['P_short']:.3f})")

        # 七维分数
        scores = r.get('scores', {})
        print(f"\n【七维分数】")
        for dim in ['T', 'A', 'S', 'V', 'O', 'E', 'F']:
            print(f"{dim} = {scores.get(dim, 'N/A')}")

        # F 的元数据
        meta = r.get('scores_meta', {})
        F_meta = meta.get('F', {})

        print(f"\n【F 元数据（详细计算过程）】")
        print(json.dumps(F_meta, indent=2, ensure_ascii=False))

        # O 的元数据
        O_meta = meta.get('O', {})
        print(f"\n【O 元数据】")
        print(f"  oi24h_pct: {O_meta.get('oi24h_pct')}")
        print(f"  oi_score: {O_meta.get('oi_score')}")
        print(f"  align_score: {O_meta.get('align_score')}")

        # V 的元数据
        V_meta = meta.get('V', {})
        print(f"\n【V 元数据】")
        print(f"  v5v20: {V_meta.get('v5v20')}")
        print(f"  vlevel_score: {V_meta.get('vlevel_score')}")
        print(f"  vroc_score: {V_meta.get('vroc_score')}")

        # A 的元数据
        A_meta = meta.get('A', {})
        print(f"\n【A 元数据】")
        print(f"  cvd6: {A_meta.get('cvd6')}")
        print(f"  cvd_score: {A_meta.get('cvd_score')}")
        print(f"  slope_score: {A_meta.get('slope_score')}")

        # 分析
        print(f"\n{'='*80}")
        print("【问题分析】")
        print('='*80)

        fund_mom = F_meta.get('fund_momentum', 0)
        price_mom = F_meta.get('price_momentum', 0)
        leading = F_meta.get('leading_raw', 0)

        print(f"\n资金动量: {fund_mom:.1f}")
        print(f"价格动量: {price_mom:.1f}")
        print(f"领先性: {leading:.1f} (资金 - 价格)")
        print(f"F 分数: {scores.get('F')}")

        if scores.get('F', 50) < 20:
            print(f"\n⚠️  F < 20，说明价格远远领先资金（追高风险）")
            print(f"    价格动量 ({price_mom:.1f}) >> 资金动量 ({fund_mom:.1f})")
            print(f"    差距: {leading:.1f}")

            if fund_mom < 40:
                print(f"\n    资金动量过低的原因：")
                oi_score = F_meta.get('oi_score', 50)
                vol_score = F_meta.get('vol_score', 50)
                cvd_score = F_meta.get('cvd_score', 50)
                print(f"      - OI 分数: {oi_score}")
                print(f"      - 量能分数: {vol_score}")
                print(f"      - CVD 分数: {cvd_score}")

            if price_mom > 70:
                print(f"\n    价格动量过高的原因：")
                trend_score = F_meta.get('trend_score', 50)
                slope_score = F_meta.get('slope_score', 50)
                print(f"      - 趋势分数: {trend_score}")
                print(f"      - 斜率分数: {slope_score}")

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else "ETHUSDT"
    diagnose_F(symbol)
