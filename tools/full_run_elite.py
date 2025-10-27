# coding: utf-8
"""
full_run_elite: Gold方案完整集成版
- 使用Elite Universe Builder构建候选池
- 元数据传递到analyze_symbol
- 贝叶斯先验调整概率
- 安全并发控制（防风控）
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
from ats_core.pools.elite_builder import build_elite_universe
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
    ap = argparse.ArgumentParser(description="Elite版批量扫描（Gold方案）")
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

    # ★ Gold方案核心：使用Elite Universe Builder
    log("=" * 60)
    log("🏆 Elite Universe Builder - 世界顶级候选池构建")
    log("=" * 60)

    try:
        symbols, metadata = build_elite_universe()
        log(f"\n✅ Elite候选池构建完成：{len(symbols)} 个交易对")
    except Exception as e:
        warn(f"❌ Elite候选池构建失败: {e}")
        import traceback
        traceback.print_exc()
        return 2

    # 保存候选池到数据库
    if DB_ENABLED and save_candidate_pool and not args.no_db:
        try:
            if symbols:
                save_candidate_pool(symbols, pool_type='elite', run_mode='manual')
        except Exception as e:
            warn(f"⚠️  保存候选池失败: {e}")

    # 限制数量
    if args.limit and args.limit > 0:
        symbols = symbols[:args.limit]
        log(f"   限制处理数量: {len(symbols)} 个")

    if not symbols:
        warn("候选池为空，无法执行扫描")
        return 2

    log(f"\n开始分析 {len(symbols)} 个交易对...")
    log("=" * 60)

    results = []
    fail = 0
    sent = 0
    prime_cnt = 0

    for idx, sym in enumerate(symbols, 1):
        try:
            log(f"\n[{idx}/{len(symbols)}] 分析 {sym}...")

            # ★ Gold方案核心：传递元数据到analyze_symbol
            elite_meta = metadata.get(sym, {})

            # 显示先验信息
            if elite_meta:
                log(f"   候选池先验: {elite_meta['trend_dir']} "
                    f"(做多{elite_meta['long_score']:.0f}/做空{elite_meta['short_score']:.0f})")

            # 调用analyze_symbol，传入元数据
            r = analyze_symbol(sym, elite_meta=elite_meta)
            r["symbol"] = sym

            # 保存所有信号到数据库
            if DB_ENABLED and save_signal and not args.no_db:
                try:
                    save_signal(r)
                except Exception as e:
                    warn(f"[DB SAVE FAIL] {sym} -> {e}")

            pub = r.get("publish") or {}
            is_prime = pub.get("prime", False)

            # 只处理prime信号
            if not is_prime:
                prob = r.get('probability', 0)
                log(f"   ⏭️  跳过（非Prime，P={prob:.1%}）")
                continue

            # 渲染为正式信号
            txt = render_trade(r)
            prime_cnt += 1

            print(f"\n{'='*60}")
            print(f"  {sym} [PRIME]")

            # 显示贝叶斯提升信息
            bayesian_boost = r.get("bayesian_boost")
            if bayesian_boost:
                print(f"  🎯 候选池先验提升: +{bayesian_boost*100:.1f}%")

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
            if idx < len(symbols):  # 最后一个不需要延迟
                time.sleep(delay_ms / 1000.0)

        except Exception as e:
            fail += 1
            warn(f"[ANALYZE FAIL] {sym} -> {e}")
            import traceback
            traceback.print_exc()

    # 保存 JSON 结果
    if args.save_json and results:
        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data", "reports"
        )
        os.makedirs(output_dir, exist_ok=True)

        ts = time.strftime("%Y%m%dT%H%MZ", time.gmtime())
        json_path = os.path.join(output_dir, f"elite_run_{ts}.json")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        log(f"\n结果已保存: {json_path}")

    # 打印摘要
    print("\n" + "="*60)
    print("扫描摘要（Elite版）".center(60))
    print("="*60)
    print(f"候选总数: {len(symbols)}")
    print(f"分析成功: {len(symbols) - fail}")
    print(f"Prime信号: {prime_cnt}")
    print(f"已发送: {sent}")
    print(f"失败: {fail}")
    print("="*60)

    # 显示贝叶斯提升统计
    boosted_count = sum(1 for r in results if r.get("bayesian_boost"))
    if boosted_count > 0:
        print(f"\n🎯 贝叶斯先验提升: {boosted_count}/{len(results)} 个信号")
        avg_boost = sum(r.get("bayesian_boost", 0) for r in results) / len(results)
        print(f"   平均提升: +{avg_boost*100:.1f}%")

    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
