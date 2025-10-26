# coding: utf-8
"""
full_run: 完整批量扫描工具
- 从候选池（base + overlay）获取交易对
- 逐个分析并生成交易信号
- 可选发送到 Telegram
"""
from __future__ import annotations
import os
import sys
import argparse
import json
import time

# 统一输出风格
os.environ.setdefault("ATS_FMT_SHOW_ZERO", "1")
os.environ.setdefault("ATS_FMT_FULL", "1")
os.environ.setdefault("ATS_FMT_EXPLAIN", "1")
os.environ.setdefault("ATS_FMT_DECIMALS_AUTO", "1")

from ats_core.cfg import CFG
from ats_core.pools.base_builder import build_base_universe
from ats_core.pools.overlay_builder import build as build_overlay
from ats_core.pipeline.analyze_symbol import analyze_symbol
from ats_core.outputs.telegram_fmt import render_trade, render_watch
from ats_core.logging import log, warn

try:
    from ats_core.outputs.publisher import telegram_send
except Exception:
    telegram_send = None

# 数据库支持（可选）
try:
    from ats_core.database import save_signal, save_candidate_pool
    DB_ENABLED = True
except Exception as e:
    DB_ENABLED = False
    save_signal = None
    save_candidate_pool = None
    warn(f"⚠️  Database not available: {e}")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="完整批量扫描并分析交易信号")
    ap.add_argument("--limit", type=int, default=None,
                    help="限制处理的交易对数量")
    ap.add_argument("--send", action="store_true",
                    help="发送Prime信号到 Telegram（默认只打印）")
    ap.add_argument("--save-json", dest="save_json", action="store_true",
                    help="保存分析结果为 JSON 文件")
    ap.add_argument("--no-db", dest="no_db", action="store_true",
                    help="不保存到数据库")

    args = ap.parse_args(argv)
    do_send = args.send and (telegram_send is not None)

    # 构建候选池
    log("正在构建候选池...")
    try:
        base = build_base_universe()
        log(f"基础候选池: {len(base)} 个交易对")
    except Exception as e:
        warn(f"构建基础池失败: {e}")
        base = []

    try:
        overlay = build_overlay()
        log(f"叠加候选池: {len(overlay)} 个交易对")
    except Exception as e:
        warn(f"构建叠加池失败: {e}")
        overlay = []

    # 合并并去重（overlay 优先）
    syms = overlay + [s for s in base if s not in overlay]

    # 保存候选池到数据库
    if DB_ENABLED and save_candidate_pool and not args.no_db:
        try:
            if base:
                save_candidate_pool(base, pool_type='base', run_mode='manual')
            if overlay:
                save_candidate_pool(overlay, pool_type='overlay', run_mode='manual')
            if syms:
                save_candidate_pool(syms, pool_type='merged', run_mode='manual')
        except Exception as e:
            warn(f"保存候选池失败: {e}")

    if args.limit and args.limit > 0:
        syms = syms[:args.limit]

    if not syms:
        warn("候选池为空，无法执行扫描")
        return 2

    log(f"开始扫描 {len(syms)} 个交易对...")

    results = []
    fail = 0
    sent = 0
    prime_cnt = 0

    for idx, sym in enumerate(syms, 1):
        try:
            log(f"[{idx}/{len(syms)}] 分析 {sym}...")

            r = analyze_symbol(sym)
            r["symbol"] = sym

            # 保存所有信号到数据库（不管质量如何）
            if DB_ENABLED and save_signal and not args.no_db:
                try:
                    save_signal(r)
                except Exception as e:
                    warn(f"[DB SAVE FAIL] {sym} -> {e}")

            pub = r.get("publish") or {}
            is_prime = pub.get("prime", False)

            # 只处理prime信号（高质量信号）
            if not is_prime:
                log(f"[SKIP] {sym} - 不是Prime信号 (P={r.get('probability', 0):.3f})")
                continue

            # 渲染为正式信号
            txt = render_trade(r)
            prime_cnt += 1

            print(f"\n{'='*60}")
            print(f"  {sym} [PRIME]")
            print(f"{'='*60}")
            print(txt)
            print()

            # 保存结果到JSON（可选）
            if args.save_json:
                results.append(r)

            # 发送到 Telegram（只发送prime信号）
            if do_send:
                try:
                    telegram_send(txt)
                    sent += 1
                    log(f"[SENT] {sym}")
                except Exception as e:
                    fail += 1
                    warn(f"[SEND FAIL] {sym} -> {e}")

            # 延迟，避免 API 限流
            delay_ms = CFG.get("limits", "per_symbol_delay_ms", default=600)
            if idx < len(syms):  # 最后一个不需要延迟
                time.sleep(delay_ms / 1000.0)

        except Exception as e:
            fail += 1
            warn(f"[ANALYZE FAIL] {sym} -> {e}")

    # 保存 JSON 结果
    if args.save_json and results:
        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data", "reports"
        )
        os.makedirs(output_dir, exist_ok=True)

        ts = time.strftime("%Y%m%dT%H%MZ", time.gmtime())
        json_path = os.path.join(output_dir, f"full_run_{ts}.json")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        log(f"结果已保存: {json_path}")

    # 打印摘要
    print("\n" + "="*60)
    print("扫描摘要".center(60))
    print("="*60)
    print(f"候选总数: {len(syms)}")
    print(f"分析成功: {len(syms) - fail}")
    print(f"Prime信号: {prime_cnt}")
    print(f"已发送: {sent}")
    print(f"失败: {fail}")
    print("="*60)

    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
