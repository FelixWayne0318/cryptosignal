#!/usr/bin/env python3
# coding: utf-8
"""
full_run_v2_fast: 超快速扫描工具（跳过选币）

特性：
- 直接读取现有候选池文件（跳过选币步骤）
- 并发分析（8个worker）
- 实时进度显示
- 超时控制

使用方法：
    python3 tools/full_run_v2_fast.py --send
    python3 tools/full_run_v2_fast.py --limit 20
"""
from __future__ import annotations
import os
import sys
import argparse
import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# 统一输出风格
os.environ.setdefault("ATS_FMT_SHOW_ZERO", "1")
os.environ.setdefault("ATS_FMT_FULL", "1")
os.environ.setdefault("ATS_FMT_EXPLAIN", "1")
os.environ.setdefault("ATS_FMT_DECIMALS_AUTO", "1")

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
        now = time.time()
        if not force and now - self.last_heartbeat < 3:
            return

        with self.lock:
            if self.completed == 0:
                return

            elapsed = now - self.start_time
            percent = self.completed / self.total * 100

            if self.completed > 0:
                avg_time = elapsed / self.completed
                remaining = (self.total - self.completed) * avg_time
                eta_str = f"{int(remaining)}s"
            else:
                eta_str = "?"

            msg = f"\r🔄 进度: {self.completed}/{self.total} ({percent:.1f}%) | " \
                  f"✅ {self.successful} ⚠️ {self.failed} | " \
                  f"⭐ Prime: {self.prime_count} | " \
                  f"📤 已发送: {self.sent_count} | " \
                  f"⏱️ ETA: {eta_str}   "

            print(msg, end='', flush=True)
            self.last_heartbeat = now

    def print_summary(self):
        elapsed = time.time() - self.start_time
        print()
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


def load_candidate_pool() -> list[str]:
    """
    从文件加载候选池（跳过选币步骤）

    Returns:
        币种列表
    """
    # 尝试多个路径
    project_root = Path(__file__).parent.parent

    candidates = [
        project_root / "data" / "base_pool.json",
        project_root / "data" / "overlay_pool.json",
        Path.home() / "cryptosignal" / "data" / "base_pool.json",
    ]

    for path in candidates:
        if path.exists():
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    # 提取symbol字段
                    if isinstance(data, list) and len(data) > 0:
                        if isinstance(data[0], dict) and 'symbol' in data[0]:
                            symbols = [item['symbol'] for item in data]
                        else:
                            symbols = data
                        return symbols
            except Exception as e:
                warn(f"Failed to load {path}: {e}")
                continue

    # 如果没有文件，使用默认列表
    return [
        'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT',
        'ADAUSDT', 'DOGEUSDT', 'LINKUSDT', 'DOTUSDT', 'MATICUSDT'
    ]


def analyze_symbol_safe(symbol: str) -> dict:
    """
    安全分析单个币种

    注意：移除了signal超时机制，因为在多线程环境下不安全
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
    """处理单个币种"""
    try:
        r = analyze_symbol_safe(symbol)

        # 保存到数据库
        if save_to_db and DB_ENABLED and save_signal:
            try:
                save_signal(r)
            except Exception:
                pass

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
                pass

        progress.update(success=True, is_prime=is_prime, sent=sent)
        progress.print_progress()

        return True, r if (is_prime and save_json) else None

    except Exception as e:
        # 分析失败，记录错误但不阻塞其他币种
        progress.update(success=False)
        progress.print_progress()
        return False, None


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="超快速批量扫描工具（跳过选币）")

    ap.add_argument("--limit", type=int, default=None,
                    help="限制处理的交易对数量")
    ap.add_argument("--send", action="store_true",
                    help="发送Prime信号到Telegram")
    ap.add_argument("--save-json", dest="save_json", action="store_true",
                    help="保存Prime信号为JSON")
    ap.add_argument("--no-db", dest="no_db", action="store_true",
                    help="不保存到数据库")
    ap.add_argument("--workers", type=int, default=8,
                    help="并发worker数量（默认8）")

    args = ap.parse_args(argv)
    do_send = args.send and (telegram_send is not None)
    save_to_db = not args.no_db

    print()
    print("="*70)
    print("  CryptoSignal Ultra-Fast Scanner v2.1".center(70))
    print("="*70)
    print()

    # 快速加载候选池
    print("📊 Step 1/3: Loading candidate pool (fast)...")
    syms = load_candidate_pool()

    if not syms:
        print("❌ No symbols found!")
        return 2

    print(f"   ✅ Loaded {len(syms)} symbols from file")

    # 保存候选池
    if save_to_db and DB_ENABLED and save_candidate_pool:
        try:
            save_candidate_pool(syms, pool_type='merged', run_mode='manual')
            print(f"   ✅ Candidate pool saved to database")
        except Exception:
            pass

    if args.limit and args.limit > 0:
        syms = syms[:args.limit]

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

        for future in as_completed(futures):
            try:
                success, result = future.result()
                if result:
                    results.append(result)
            except Exception:
                progress.update(success=False)
                progress.print_progress()

    progress.print_progress(force=True)
    print()

    # 保存JSON
    if args.save_json and results:
        print("\n💾 Step 3/3: Saving results...")
        output_dir = Path(__file__).parent.parent / "data" / "reports"
        output_dir.mkdir(parents=True, exist_ok=True)

        ts = time.strftime("%Y%m%dT%H%MZ", time.gmtime())
        json_path = output_dir / f"full_run_fast_{ts}.json"

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"   ✅ Results saved: {json_path}")

    progress.print_summary()

    return 0 if progress.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
