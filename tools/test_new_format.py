# coding: utf-8
"""
测试新的 Telegram 消息格式
- 显示概率而不是 Conviction
- TTL 显示为 "有效期8h"
- 六维描述根据方向调整
"""
import sys
sys.path.insert(0, "/home/user/cryptosignal")

from ats_core.pipeline.analyze_symbol import analyze_symbol
from ats_core.outputs.telegram_fmt import render_trade, render_watch

def test_format(symbols=None):
    if symbols is None:
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    for sym in symbols:
        print(f"\n{'='*70}")
        print(f"测试 {sym}")
        print('='*70)

        try:
            r = analyze_symbol(sym)

            # 显示关键信息
            print(f"\n【分析结果】")
            print(f"方向: {r['side']}")
            print(f"概率 P: {r['probability']:.3f} (P_long={r['P_long']:.3f}, P_short={r['P_short']:.3f})")
            print(f"发布: prime={r['publish']['prime']}, watch={r['publish']['watch']}")
            print(f"分数: {r['scores']}")

            # 选择渲染方式
            is_prime = r['publish']['prime']
            if is_prime:
                txt = render_trade(r)
            else:
                txt = render_watch(r)

            print(f"\n【Telegram 消息】")
            print(txt)

        except Exception as e:
            print(f"❌ 分析失败: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    syms = sys.argv[1:] if len(sys.argv) > 1 else None
    test_format(syms)
