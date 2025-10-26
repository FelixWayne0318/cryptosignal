#!/usr/bin/env python3
# coding: utf-8
"""
manual_run: 手动运行分析（使用现有候选池，强制发送）
- 读取现有候选池（不重新构建）
- 分析前N个币种（默认10个）
- 强制发送所有分析结果（不管是否符合发布条件）
- 自动保存信号到数据库（如果启用）
"""
import os
import sys
import json
import time
import argparse

os.environ.setdefault("ATS_FMT_SHOW_ZERO", "1")
os.environ.setdefault("ATS_FMT_FULL", "1")
os.environ.setdefault("ATS_FMT_EXPLAIN", "1")
os.environ.setdefault("ATS_FMT_DECIMALS_AUTO", "1")

from ats_core.pipeline.analyze_symbol import analyze_symbol
from ats_core.outputs.telegram_fmt import render_signal
from ats_core.logging import log, warn

try:
    from ats_core.outputs.publisher import telegram_send
except Exception:
    telegram_send = None

# 数据库支持（可选）
try:
    from ats_core.database import save_signal
    DB_ENABLED = True
except Exception as e:
    DB_ENABLED = False
    warn(f"⚠️  Database not available: {e}")


def load_existing_pool():
    """读取现有候选池（不重新构建）"""
    import json
    from pathlib import Path

    base_path = Path(__file__).parent.parent / "data" / "base_pool.json"
    overlay_path = Path(__file__).parent.parent / "data" / "overlay_pool.json"

    symbols = []

    # 读取 overlay（优先级高）
    if overlay_path.exists():
        try:
            with open(overlay_path, 'r') as f:
                overlay_data = json.load(f)
                if isinstance(overlay_data, list):
                    # 候选池可能是字符串列表或对象列表
                    for item in overlay_data:
                        if isinstance(item, dict):
                            # 对象格式：{'symbol': 'BTCUSDT', 'z24': 1.0, ...}
                            symbols.append(item['symbol'])
                        else:
                            # 字符串格式：'BTCUSDT'
                            symbols.append(item)
                    log(f"✅ 读取 overlay 候选池: {len(overlay_data)} 个")
        except Exception as e:
            warn(f"读取 overlay 失败: {e}")

    # 读取 base
    if base_path.exists():
        try:
            with open(base_path, 'r') as f:
                base_data = json.load(f)
                if isinstance(base_data, list):
                    # 去重（overlay 优先）
                    for item in base_data:
                        # 提取symbol字段（兼容对象和字符串）
                        sym = item['symbol'] if isinstance(item, dict) else item
                        if sym not in symbols:
                            symbols.append(sym)
                    log(f"✅ 读取 base 候选池: {len(base_data)} 个（合并后总计 {len(symbols)} 个）")
        except Exception as e:
            warn(f"读取 base 失败: {e}")

    if not symbols:
        # 如果都不存在，尝试构建一次
        warn("⚠️  未找到现有候选池文件，尝试构建...")
        try:
            from ats_core.pools.base_builder import build_base_universe
            from ats_core.pools.overlay_builder import build as build_overlay

            overlay = build_overlay()
            base = build_base_universe()

            symbols = overlay + [s for s in base if s not in overlay]
            log(f"✅ 新构建候选池: base={len(base)}, overlay={len(overlay)}, total={len(symbols)}")
        except Exception as e:
            warn(f"构建候选池失败: {e}")
            # 使用默认候选池
            symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]
            log(f"⚠️  使用默认候选池: {symbols}")

    return symbols


def main():
    ap = argparse.ArgumentParser(description="手动分析（读取现有候选池，强制发送）")
    ap.add_argument("--top", type=int, default=10,
                    help="分析前N个币种（默认10）")
    ap.add_argument("--send", action="store_true",
                    help="发送到Telegram（默认只打印）")
    ap.add_argument("--symbols", type=str, nargs="+",
                    help="指定币种列表（不使用候选池）")
    ap.add_argument("--no-db", action="store_true",
                    help="不保存到数据库")

    args = ap.parse_args()
    do_send = args.send and (telegram_send is not None)
    do_save_db = DB_ENABLED and not args.no_db

    if not do_send:
        log("⚠️  未启用发送模式，只打印结果（使用 --send 启用发送）")

    if do_save_db:
        log("✅ 数据库记录已启用")
    elif DB_ENABLED:
        log("⚠️  数据库记录已禁用（--no-db）")
    else:
        log("⚠️  数据库不可用")

    # 获取币种列表
    if args.symbols:
        symbols = args.symbols
        log(f"使用指定币种: {symbols}")
    else:
        symbols = load_existing_pool()
        if args.top > 0 and args.top < len(symbols):
            symbols = symbols[:args.top]
            log(f"取前 {args.top} 个币种")

    if not symbols:
        warn("❌ 候选池为空")
        return 2

    log(f"开始分析 {len(symbols)} 个币种...\n")

    results = []
    sent_count = 0
    fail_count = 0
    saved_count = 0

    for idx, sym in enumerate(symbols, 1):
        try:
            log(f"[{idx}/{len(symbols)}] 分析 {sym}...")

            r = analyze_symbol(sym)
            r["symbol"] = sym

            # 获取概率和发布状态
            prob = r.get("probability", 0)
            pub = r.get("publish") or {}
            is_prime = pub.get("prime", False)
            is_watch = pub.get("watch", False)

            # 选择标签（手动模式：即使不符合条件也显示）
            if is_prime:
                tag = "[PRIME]"
                is_watch_flag = False
            elif is_watch:
                tag = "[WATCH]"
                is_watch_flag = True
            else:
                # 不符合发布条件，但手动模式仍然发送
                tag = "[MANUAL]"
                is_watch_flag = False  # 使用 PRIME 格式

            # 渲染消息
            txt = render_signal(r, is_watch=is_watch_flag)

            # 打印到控制台
            print(f"\n{'='*60}")
            print(f"  {sym} {tag} - P={prob:.1%}")
            print(f"{'='*60}")
            print(txt)
            print()

            # 保存到数据库
            signal_id = None
            if do_save_db:
                try:
                    signal_id = save_signal(r)
                    saved_count += 1
                except Exception as e:
                    warn(f"⚠️  Failed to save to database: {e}")

            results.append({
                "symbol": sym,
                "tag": tag,
                "probability": prob,
                "side": r.get("side"),
                "F_score": r.get("F_score"),
                "F_adjustment": r.get("F_adjustment"),
                "signal_id": signal_id,
            })

            # 发送到Telegram（强制发送，不管是否符合条件）
            if do_send:
                try:
                    telegram_send(txt)
                    sent_count += 1
                    log(f"✅ [SENT] {sym}")
                except Exception as e:
                    fail_count += 1
                    warn(f"❌ [SEND FAIL] {sym} -> {e}")

            # 延迟
            if idx < len(symbols):
                time.sleep(0.6)

        except Exception as e:
            fail_count += 1
            warn(f"❌ [ANALYZE FAIL] {sym} -> {e}")
            import traceback
            traceback.print_exc()

    # 打印摘要
    print("\n" + "="*60)
    print("分析摘要".center(60))
    print("="*60)
    print(f"候选总数: {len(symbols)}")
    print(f"分析成功: {len(results)}")
    print(f"已发送: {sent_count}")
    if do_save_db:
        print(f"已保存到数据库: {saved_count}")
    print(f"失败: {fail_count}")
    print("="*60)

    # 显示详细结果
    if results:
        print("\n详细结果:")
        print("-" * 80)
        for r in results:
            side_icon = "🟩" if r["side"] == "long" else "🟥"
            print(f"{side_icon} {r['symbol']:15} {r['tag']:10} P={r['probability']:>6.1%} "
                  f"F={r['F_score']:>2d} adj={r['F_adjustment']:>4.2f}")
        print("-" * 80)

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
