# coding: utf-8
"""
诊断7维度分数（统一±100系统）
检查：T/M/C/S/V/O/E
"""
import sys
sys.path.insert(0, "/home/user/cryptosignal")

from ats_core.pipeline.analyze_symbol import analyze_symbol
import json

def diagnose_zeros(symbols=None):
    if symbols is None:
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ORDERUSDT"]

    print(f"\n{'='*80}")
    print("诊断7维度分数（统一±100系统）")
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

            print(f"\n【7维分数（±100系统）】")
            print(f"T={scores.get('T'):+4d}  M={scores.get('M'):+4d}  C={scores.get('C'):+4d}")
            print(f"S={scores.get('S'):+4d}  V={scores.get('V'):+4d}  O={scores.get('O'):+4d}  E={scores.get('E'):+4d}")

            # Scorecard结果
            weighted = r.get('weighted_score', 0)
            confidence = r.get('confidence', 0)
            print(f"\n【Scorecard】")
            print(f"加权分数: {weighted:+4d}/100")
            print(f"置信度:   {confidence:4d}/100")

            # 持仓 O 的元数据
            print(f"\n【持仓 O 元数据】")
            o_meta = meta.get('O', {})
            if isinstance(o_meta, dict):
                print(json.dumps(o_meta, indent=2, ensure_ascii=False))
            else:
                print(f"  {o_meta}")

            # 动量 M 的元数据
            print(f"\n【动量 M 元数据】")
            m_meta = meta.get('M', {})
            if isinstance(m_meta, dict):
                print(json.dumps(m_meta, indent=2, ensure_ascii=False))
            else:
                print(f"  {m_meta}")

            # CVD资金流 C 的元数据
            print(f"\n【CVD资金流 C 元数据】")
            c_meta = meta.get('C', {})
            if isinstance(c_meta, dict):
                print(json.dumps(c_meta, indent=2, ensure_ascii=False))
            else:
                print(f"  {c_meta}")

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
