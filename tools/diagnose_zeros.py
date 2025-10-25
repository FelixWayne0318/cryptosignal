# coding: utf-8
"""
诊断为什么 O 和 A 经常是 0
"""
import sys
sys.path.insert(0, "/home/user/cryptosignal")

from ats_core.pipeline.analyze_symbol import analyze_symbol
import json

def diagnose_zeros(symbols=None):
    if symbols is None:
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ORDERUSDT"]

    print(f"\n{'='*80}")
    print("诊断 O=0 和 A=0 的原因")
    print('='*80)

    for sym in symbols:
        print(f"\n{'='*80}")
        print(f"{sym}")
        print('='*80)

        try:
            r = analyze_symbol(sym)

            # 获取元数据
            scores = r.get('scores', {})
            meta = r.get('scores_meta', {})

            print(f"\n【分数】")
            print(f"T={scores.get('T')}, A={scores.get('A')}, S={scores.get('S')}")
            print(f"V={scores.get('V')}, O={scores.get('O')}, E={scores.get('E')}")

            # 持仓 O 的元数据
            print(f"\n【持仓 O 元数据】")
            o_meta = meta.get('O', {})
            if isinstance(o_meta, dict):
                print(json.dumps(o_meta, indent=2, ensure_ascii=False))
            else:
                print(f"  {o_meta}")

            # 加速 A 的元数据
            print(f"\n【加速 A 元数据】")
            a_meta = meta.get('A', {})
            if isinstance(a_meta, dict):
                print(json.dumps(a_meta, indent=2, ensure_ascii=False))
            else:
                print(f"  {a_meta}")

            # CVD 相关
            cvd_z20 = r.get('cvd_z20', 0)
            cvd_mix = r.get('cvd_mix_abs_per_h', 0)
            print(f"\n【CVD】")
            print(f"cvd_z20: {cvd_z20:.3f}")
            print(f"cvd_mix_abs_per_h: {cvd_mix:.6f}")

        except Exception as e:
            print(f"❌ 错误: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    syms = sys.argv[1:] if len(sys.argv) > 1 else None
    diagnose_zeros(syms)
