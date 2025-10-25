#!/usr/bin/env python3
# coding: utf-8
"""
quick_run: 快速运行 - 使用当前候选池（不重新构建）
"""
import os
import sys
import time

# 统一输出风格
os.environ.setdefault("ATS_FMT_SHOW_ZERO", "1")
os.environ.setdefault("ATS_FMT_FULL", "1")
os.environ.setdefault("ATS_FMT_EXPLAIN", "1")
os.environ.setdefault("ATS_FMT_DECIMALS_AUTO", "1")

from ats_core.pipeline.analyze_symbol import analyze_symbol
from ats_core.outputs.telegram_fmt import render_trade, render_watch
from ats_core.logging import log, warn

# 使用当前候选池（从缓存文件推断）
CURRENT_POOL = [
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "SOLUSDT",
    "1000PEPEUSDT",
    "COAIUSDT",
    "EVAAUSDT",
    "XPLUSDT",
]


def main():
    """运行分析"""
    log(f"使用当前候选池: {len(CURRENT_POOL)} 个交易对")
    log("不重新构建候选池\n")

    results = []
    prime_cnt = 0
    watch_cnt = 0
    skip_cnt = 0
    fail_cnt = 0

    for idx, sym in enumerate(CURRENT_POOL, 1):
        try:
            log(f"[{idx}/{len(CURRENT_POOL)}] 分析 {sym}...")

            r = analyze_symbol(sym)
            r["symbol"] = sym

            pub = r.get("publish") or {}
            is_prime = pub.get("prime", False)
            is_watch = pub.get("watch", False)

            # 发布过滤
            if not is_prime and not is_watch:
                skip_cnt += 1
                log(f"[SKIP] {sym} - 不符合发布条件 (P={r.get('probability', 0):.3f})")
                continue

            # 选择渲染方式
            if is_prime:
                txt = render_trade(r)
                prime_cnt += 1
            else:
                txt = render_watch(r)
                watch_cnt += 1

            print(f"\n{'='*60}")
            print(f"  {sym} {'[PRIME]' if is_prime else '[WATCH]'}")
            print(f"{'='*60}")
            print(txt)
            print()

            results.append({
                "symbol": sym,
                "is_prime": is_prime,
                "is_watch": is_watch,
                "probability": r.get("probability", 0),
                "side": r.get("side"),
                "scores": r.get("scores", {}),
                "P_base": r.get("P_base"),
                "F_score": r.get("F_score"),
                "F_adjustment": r.get("F_adjustment"),
            })

            # 延迟，避免 API 限流
            if idx < len(CURRENT_POOL):
                time.sleep(0.6)

        except Exception as e:
            fail_cnt += 1
            warn(f"[ANALYZE FAIL] {sym} -> {e}")
            import traceback
            traceback.print_exc()

    # 打印摘要
    print("\n" + "="*60)
    print("扫描摘要".center(60))
    print("="*60)
    print(f"候选总数: {len(CURRENT_POOL)}")
    print(f"分析成功: {len(CURRENT_POOL) - fail_cnt}")
    print(f"Prime信号: {prime_cnt}")
    print(f"Watch信号: {watch_cnt}")
    print(f"跳过: {skip_cnt}")
    print(f"失败: {fail_cnt}")
    print("="*60)

    # 显示详细结果
    if results:
        print("\n详细结果:")
        print("-" * 60)
        for r in results:
            side_icon = "🟩" if r["side"] == "long" else "🟥"
            tag = "[PRIME]" if r["is_prime"] else "[WATCH]"
            print(f"{side_icon} {r['symbol']:15} {tag:8} P={r['probability']:.1%} "
                  f"F={r['F_score']:>2d} F_adj={r['F_adjustment']:.2f}")
        print("-" * 60)

    return 0 if fail_cnt == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
