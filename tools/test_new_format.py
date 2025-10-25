# coding: utf-8
"""
测试新的 Telegram 消息格式
- 显示概率而不是 Conviction
- TTL 显示为 "有效期8h"
- 六维描述根据方向调整

使用：
  python3 test_new_format.py BTCUSDT ETHUSDT  # 只显示格式
  python3 test_new_format.py --send BTCUSDT   # 强制发送到 Telegram（测试用）
"""
import sys
import argparse
sys.path.insert(0, "/home/user/cryptosignal")

from ats_core.pipeline.analyze_symbol import analyze_symbol
from ats_core.outputs.telegram_fmt import render_trade, render_watch

try:
    from ats_core.outputs.publisher import telegram_send
except Exception:
    telegram_send = None

def test_format(symbols=None, do_send=False):
    if symbols is None:
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    sent_count = 0
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

            # 强制发送（测试用）
            if do_send:
                if telegram_send is None:
                    print(f"\n⚠️ 无法发送：telegram_send 不可用")
                else:
                    try:
                        telegram_send(txt)
                        sent_count += 1
                        print(f"\n✅ 已发送到 Telegram")
                    except Exception as e:
                        print(f"\n❌ 发送失败: {e}")

        except Exception as e:
            print(f"❌ 分析失败: {e}")
            import traceback
            traceback.print_exc()

    if do_send:
        print(f"\n{'='*70}")
        print(f"发送摘要: {sent_count}/{len(symbols)} 条消息已发送")
        print(f"{'='*70}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="测试 Telegram 消息格式")
    parser.add_argument("--send", action="store_true", help="强制发送到 Telegram（忽略发布条件）")
    parser.add_argument("symbols", nargs="*", help="要测试的交易对符号")

    args = parser.parse_args()
    syms = args.symbols if args.symbols else None
    test_format(syms, do_send=args.send)
