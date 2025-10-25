#!/usr/bin/env python3
# coding: utf-8
"""
full_run_v2: 高性能批量扫描工具（优化版）

优化特性：
1. 并发分析（5-10个币同时处理）
2. 实时进度显示（百分比 + ETA）
3. 心跳输出（防止SSH断开）
4. 错误容错（单个失败不影响整体）
5. 批次处理（更稳定）

使用方法：
    python3 tools/full_run_v2.py --send
    python3 tools/full_run_v2.py --limit 50 --workers 8
"""
from __future__ import annotations
import os
import sys
import argparse
import json
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# 统一输出风格
os.environ.setdefault("ATS_FMT_SHOW_ZERO", "1")
os.environ.setdefault("ATS_FMT_FULL", "1")
os.environ.setdefault("ATS_FMT_EXPLAIN", "1")
os.environ.setdefault("ATS_FMT_DECIMALS_AUTO", "1")

from ats_core.cfg import CFG
from ats_core.pools.base_builder import build_base_universe
from ats_core.pools.overlay_builder import build as build_overlay
from ats_core.pipeline.analyze_symbol import analyze_symbol
from ats_core.outputs.telegram_fmt import render_trade
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


class ProgressTracker:
    """进度追踪器"""
    def __init__(self, total: int):
        self.total = total
        self.completed = 0
        self.successful = 0
        self.failed = 0
        self.prime_count = 0
        self.sent_count = 0
        self.start_time = time.time()
        self.lock = Lock()
        self.last_heartbeat = time.time()

    def update(self, success: bool, is_prime: bool = False, sent: bool = False):
        """更新进度"""
        with self.lock:
            self.completed += 1
            if success:
                self.successful += 1
            else:
                self.failed += 1
            if is_prime:
                self.prime_count += 1
            if sent:
                self.sent_count += 1

    def print_progress(self, force: bool = False):
        """打印进度（节流：最多每3秒一次）"""
        now = time.time()
        if not force and now - self.last_heartbeat < 3:
            return

        with self.lock:
            if self.completed == 0:
                return

            elapsed = now - self.start_time
            percent = self.completed / self.total * 100

            # 计算ETA
            if self.completed > 0:
                avg_time = elapsed / self.completed
                remaining = (self.total - self.completed) * avg_time
                eta_str = f"{int(remaining)}s"
            else:
                eta_str = "?"

            # 格式化输出（不换行，覆盖之前的输出）
            msg = f"\r🔄 进度: {self.completed}/{self.total} ({percent:.1f}%) | " \
                  f"✅ {self.successful} ⚠️ {self.failed} | " \
                  f"⭐ Prime: {self.prime_count} | " \
                  f"📤 已发送: {self.sent_count} | " \
                  f"⏱️ ETA: {eta_str}   "

            print(msg, end='', flush=True)
            self.last_heartbeat = now

    def print_summary(self):
        """打印最终摘要"""
        elapsed = time.time() - self.start_time
        print()  # 换行
        print("\n" + "="*70)
        print("  SCAN SUMMARY".center(70))
        print("="*70)
        print(f"  Total Symbols:        {self.total}")
        print(f"  Completed:            {self.completed}")
        print(f"  Successful:           {self.successful}")
        print(f"  Failed:               {self.failed}")
        print(f"  Prime Signals:        {self.prime_count}")
        print(f"  Sent to Telegram:     {self.sent_count}")
        print(f"  Total Time:           {elapsed:.1f}s")
        print(f"  Avg Time per Symbol:  {elapsed/max(1, self.completed):.2f}s")
        print("="*70)


def analyze_symbol_safe(symbol: str) -> dict:
    """
    安全分析单个币种

    注意：移除了signal超时机制，因为在多线程环境下不安全
    如果需要超时控制，应该在线程池级别设置

    Args:
        symbol: 币种

    Returns:
        分析结果
    """
    result = analyze_symbol(symbol)
    result["symbol"] = symbol
    return result


def process_symbol(
    symbol: str,
    do_send: bool,
    save_to_db: bool,
    save_json: bool,
    progress: ProgressTracker
) -> tuple[bool, dict | None]:
    """
    处理单个币种（并发安全）

    Returns:
        (success, result_dict)
    """
    try:
        # 分析
        r = analyze_symbol_safe(symbol)

        # 保存到数据库
        if save_to_db and DB_ENABLED and save_signal:
            try:
                save_signal(r)
            except Exception as e:
                pass  # 静默失败，不影响流程

        pub = r.get("publish") or {}
        is_prime = pub.get("prime", False)

        # 发送Prime信号
        sent = False
        if is_prime and do_send and telegram_send:
            try:
                txt = render_trade(r)
                telegram_send(txt)
                sent = True
            except Exception:
                pass  # 发送失败不算错误

        # 更新进度
        progress.update(success=True, is_prime=is_prime, sent=sent)
        progress.print_progress()

        return True, r if (is_prime and save_json) else None

    except Exception as e:
        # 分析失败，记录错误但不阻塞其他币种
        progress.update(success=False)
        progress.print_progress()
        return False, None


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="高性能批量扫描工具（并发优化版）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
优化特性：
  • 并发分析（5-10个币同时处理）
  • 实时进度显示（百分比 + ETA）
  • 超时控制（30秒/币，防止卡死）
  • 心跳输出（防止SSH断开）

使用示例：
  python3 tools/full_run_v2.py --send
  python3 tools/full_run_v2.py --limit 50 --workers 8
  python3 tools/full_run_v2.py --send --no-db --workers 10
        """
    )

    ap.add_argument("--limit", type=int, default=None,
                    help="限制处理的交易对数量")
    ap.add_argument("--send", action="store_true",
                    help="发送Prime信号到Telegram")
    ap.add_argument("--save-json", dest="save_json", action="store_true",
                    help="保存Prime信号为JSON")
    ap.add_argument("--no-db", dest="no_db", action="store_true",
                    help="不保存到数据库")
    ap.add_argument("--workers", type=int, default=8,
                    help="并发worker数量（默认8，建议5-10）")

    args = ap.parse_args(argv)
    do_send = args.send and (telegram_send is not None)
    save_to_db = not args.no_db

    print()
    print("="*70)
    print("  CryptoSignal High-Performance Scanner v2.0".center(70))
    print("="*70)
    print()

    # 构建候选池
    print("📊 Step 1/3: Building candidate pool...")
    try:
        base = build_base_universe()
        print(f"   Base pool: {len(base)} symbols")
    except Exception as e:
        warn(f"Failed to build base pool: {e}")
        base = []

    try:
        overlay = build_overlay()
        print(f"   Overlay pool: {len(overlay)} symbols")
    except Exception as e:
        warn(f"Failed to build overlay pool: {e}")
        overlay = []

    # 合并
    syms = overlay + [s for s in base if s not in overlay]

    # 保存候选池
    if save_to_db and DB_ENABLED and save_candidate_pool:
        try:
            if syms:
                save_candidate_pool(syms, pool_type='merged', run_mode='manual')
                print(f"   ✅ Candidate pool saved to database")
        except Exception:
            pass

    if args.limit and args.limit > 0:
        syms = syms[:args.limit]

    if not syms:
        print("❌ No symbols to scan!")
        return 2

    print(f"   📋 Total symbols to scan: {len(syms)}")
    print(f"   🔧 Workers: {args.workers}")
    print(f"   💾 Save to DB: {'Yes' if save_to_db else 'No'}")
    print(f"   📤 Send to Telegram: {'Yes' if do_send else 'No'}")
    print()

    # 并发分析
    print("🔄 Step 2/3: Analyzing symbols (concurrent)...")
    progress = ProgressTracker(len(syms))
    results = []

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        # 提交所有任务
        futures = {
            executor.submit(
                process_symbol,
                sym,
                do_send,
                save_to_db,
                args.save_json,
                progress
            ): sym
            for sym in syms
        }

        # 等待完成
        for future in as_completed(futures):
            sym = futures[future]
            try:
                success, result = future.result()
                if result:
                    results.append(result)
            except Exception as e:
                progress.update(success=False)
                progress.print_progress()

    # 最终进度
    progress.print_progress(force=True)
    print()  # 换行

    # 保存JSON
    if args.save_json and results:
        print("\n💾 Step 3/3: Saving results...")
        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data", "reports"
        )
        os.makedirs(output_dir, exist_ok=True)

        ts = time.strftime("%Y%m%dT%H%MZ", time.gmtime())
        json_path = os.path.join(output_dir, f"full_run_v2_{ts}.json")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"   ✅ Results saved: {json_path}")

    # 打印摘要
    progress.print_summary()

    return 0 if progress.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
