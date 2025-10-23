# coding: utf-8
from __future__ import annotations

"""
full_run.py — 纯仓库内可运行的一次性全流程：
1) 读取 params.yml（可选），以及 overlay 候选
2) 按候选池选币 -> 分析 -> 渲染
3) 可选发送 Telegram

优先使用 ats_core，如果不可用则使用本地最小实现（CFG/渲染/发送/分析）。
"""

import argparse
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

# --- 第 0 层：常量与工具 ---
REPO_ROOT = Path(__file__).resolve().parents[1]  # tools/ -> repo root

def _env(name: str, default=None):
    return os.getenv(name, default)

def _bool(v) -> bool:
    return str(v).lower() in ("1", "true", "yes", "y", "on")

# --- 第 1 层：尝试导入 ats_core，如果失败就走本地实现 ---
_USING_CORE = False
try:
    from ats_core.cfg import CFG as CORE_CFG  # type: ignore
    from ats_core.outputs.telegram_fmt import render_watch as CORE_RENDER  # type: ignore
    from ats_core.outputs.publisher import telegram_send as CORE_TG_SEND  # type: ignore
    from ats_core.pools import overlay_builder as CORE_OVERLAY  # type: ignore
    from ats_core.pipeline.analyze_symbol import analyze_symbol as CORE_ANALYZE  # type: ignore
    _USING_CORE = True
except Exception:
    _USING_CORE = False

# --- 第 2 层：本地实现（仅在 _USING_CORE=False 时使用） ---
if not _USING_CORE:
    # 2.1 本地 CFG（读取 params.yml）
    try:
        import yaml  # PyYAML
    except Exception as e:
        yaml = None  # 允许没有 YAML，CFG.get 会回退 default

    class CFG:
        _data: Dict[str, Any] | None = None

        @classmethod
        def _load(cls):
            if cls._data is not None:
                return
            data: Dict[str, Any] = {}
            yml = REPO_ROOT / "params.yml"
            if yml.exists() and yaml is not None:
                try:
                    with yml.open("r", encoding="utf-8") as f:
                        data = yaml.safe_load(f) or {}
                except Exception:
                    data = {}
            cls._data = data

        @classmethod
        def get(cls, key: str, default=None):
            cls._load()
            cur: Any = cls._data or {}
            if not key:
                return cur
            for part in key.split("."):
                if isinstance(cur, dict) and part in cur:
                    cur = cur[part]
                else:
                    return default
            return cur

        @classmethod
        def all(cls) -> Dict[str, Any]:
            cls._load()
            return dict(cls._data or {})

    # 2.2 overlay 候选构建（尽量从 params.yml 拿）
    def build_overlay_candidates() -> List[str]:
        # 优先从 params.yml 的 overlay.candidates / overlay.whitelist 取
        cands = CFG.get("overlay.candidates") or CFG.get("overlay.whitelist")
        if isinstance(cands, list) and cands:
            return [str(x).upper() for x in cands]
        return []

    # 2.3 Telegram 发送（requests 直连）
    import requests

    def telegram_send(text: str,
                      chat_id: Optional[str] = None,
                      token: Optional[str] = None,
                      parse_mode: str = "HTML",
                      disable_preview: bool = True) -> Dict[str, Any]:
        token = token or _env("TELEGRAM_BOT_TOKEN") or _env("ATS_TELEGRAM_BOT_TOKEN")
        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN 未设置")
        chat_id = chat_id or _env("TELEGRAM_CHAT_ID_WATCH") or _env("TELEGRAM_CHAT_ID_PRIME") or _env("TELEGRAM_CHAT_ID")
        if not chat_id:
            raise RuntimeError("TELEGRAM_CHAT_ID/CHAT_ID_WATCH/CHAT_ID_PRIME 未设置")
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_preview,
        }
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not data.get("ok", False):
            raise RuntimeError(f"Telegram 返回异常: {data}")
        return data

    # 2.4 渲染（将分析 dict 渲染为文本；兼容多字段，尽量不丢信息）
    def render_watch(res: Dict[str, Any]) -> str:
        s = res.get("symbol", "?")
        prime = bool(res.get("prime", False))
        header = f"<b>{s}</b> {'✅' if prime else '👀'}"
        lines = [header]

        # 常见指标尝试展示（存在才显示）
        def _fmt(k, label=None, suffix=""):
            v = res.get(k)
            if v is None:
                return
            if isinstance(v, float):
                try:
                    v = f"{v:.4f}"
                except Exception:
                    v = str(v)
            lines.append(f"{label or k}: {v}{suffix}")

        _fmt("price", "price")
        _fmt("chg_pct", "change", "%")
        _fmt("score", "score")
        _fmt("trend", "trend")
        _fmt("rsi", "rsi")
        _fmt("atr", "atr")
        note = res.get("note")
        if note:
            lines.append(f"note: {note}")

        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        lines.append(f"<i>{ts}</i>")
        return "\n".join(lines)

    # 2.5 轻量分析（Binance 24h ticker 基线）
    def analyze_symbol_basic(symbol: str) -> Dict[str, Any]:
        url = f"https://fapi.binance.com/fapi/v1/ticker/24hr?symbol={symbol.upper()}"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        t = r.json()
        last = float(t["lastPrice"])
        open_ = float(t["openPrice"])
        chg_pct = (last - open_) / open_ * 100 if open_ else 0.0

        # 配置阈值（可在 params.yml 设置 overlay.prime.min_change_pct / overlay.watch.min_change_pct）
        prime_thr = CFG.get("overlay.prime.min_change_pct", 1.5) or CFG.get("overlay.prime_min_change_pct", 1.5)
        watch_thr = CFG.get("overlay.watch.min_change_pct", 0.5) or CFG.get("overlay.watch_min_change_pct", 0.5)

        # 简单评分：涨幅为正加分，跌幅扣分（可按需扩展 volume/atr/rsi 等）
        score = chg_pct

        is_prime = chg_pct >= float(prime_thr)
        # 可按需设置 is_watch 标志，但当前渲染只关心 prime
        return {
            "symbol": symbol.upper(),
            "price": last,
            "chg_pct": round(chg_pct, 3),
            "score": round(score, 3),
            "prime": bool(is_prime),
            "source": "binance.24hr",
        }

    # 2.6 对外统一接口（与 ats_core 对齐）
    def _CFG_get(key: str, default=None):
        return CFG.get(key, default)

    def _overlay_build():
        c = build_overlay_candidates()
        return c

    def _render(res: Dict[str, Any]) -> str:
        return render_watch(res)

    def _tg_send(txt: str, chat_id: Optional[str] = None):
        return telegram_send(txt, chat_id=chat_id)

    def _analyze(symbol: str) -> Dict[str, Any]:
        return analyze_symbol_basic(symbol)

else:
    # 使用 ats_core 的实现
    def _CFG_get(key: str, default=None):
        return CORE_CFG.get(key, default)

    def _overlay_build():
        try:
            c = CORE_OVERLAY.build()
            return c
        except Exception:
            return []

    def _render(res: Dict[str, Any]) -> str:
        return CORE_RENDER(res)

    def _tg_send(txt: str, chat_id: Optional[str] = None):
        return CORE_TG_SEND(txt, chat_id=chat_id)

    def _analyze(symbol: str) -> Dict[str, Any]:
        return CORE_ANALYZE(symbol)

# --- 第 3 层：通用逻辑（候选选币、路由、主流程） ---
FALLBACK_UNIVERSE = [
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","ADAUSDT","DOGEUSDT",
    "TRXUSDT","AVAXUSDT","LINKUSDT","MATICUSDT","DOTUSDT","LTCUSDT","BCHUSDT"
]

def _pick_universe(limit: int) -> List[str]:
    # 优先 overlay 候选，其次 params.yml 的 universe，最后主流兜底
    try:
        cands = _overlay_build()
        if isinstance(cands, list) and cands:
            return [s.upper() for s in cands[:limit]]
    except Exception:
        pass

    uni = _CFG_get("universe", default=[])
    if isinstance(uni, list) and uni:
        return [str(s).upper() for s in uni[:limit]]

    return FALLBACK_UNIVERSE[:limit]

def route_chat_id(is_prime: bool,
                  args_chat_prime: Optional[str],
                  args_chat_watch: Optional[str]) -> Optional[str]:
    """
    选择发送目标：
      1) CLI 覆盖：--prime-chat-id / --watch-chat-id
      2) 环境变量：TELEGRAM_CHAT_ID_PRIME / TELEGRAM_CHAT_ID_WATCH（或 ATS_* 同名变量）
      3) 回退：TELEGRAM_CHAT_ID（或 ATS_TELEGRAM_CHAT_ID）
    """
    env_prime = _env("TELEGRAM_CHAT_ID_PRIME") or _env("ATS_TELEGRAM_CHAT_ID_PRIME")
    env_watch = _env("TELEGRAM_CHAT_ID_WATCH") or _env("ATS_TELEGRAM_CHAT_ID_WATCH")
    base      = _env("TELEGRAM_CHAT_ID") or _env("ATS_TELEGRAM_CHAT_ID")

    if is_prime:
        return args_chat_prime or env_prime or base
    else:
        return args_chat_watch or env_watch or base

def maybe_tag(text: str, is_prime: bool, add_tags: bool) -> str:
    if not add_tags:
        return text
    prefix = "【正式】" if is_prime else "【观察】"
    return f"{prefix}\n{text}"

def main():
    ap = argparse.ArgumentParser(description="全流程跑一遍，支持分流路由 prime/observe（纯仓库版）")
    ap.add_argument("--limit", type=int, default=30, help="最多分析多少个标的")
    ap.add_argument("--send", action="store_true", help="真的发送到 Telegram")
    ap.add_argument("--only-prime", dest="only_prime", action="store_true", help="仅发送 prime=True 的信号")
    ap.add_argument("--only-watch", dest="only_watch", action="store_true", help="仅发送 非 prime 的信号")
    ap.add_argument("--save-json", action="store_true", help="把每个标的结果落盘 JSON 到 data/run_*/")
    ap.add_argument("--prime-chat-id", type=str, default=None, help="正式信号发送到的 Chat ID（覆盖环境变量）")
    ap.add_argument("--watch-chat-id", type=str, default=None, help="观察信号发送到的 Chat ID（覆盖环境变量）")
    ap.add_argument("--add-tags", action="store_true", help="在文本前添加【正式】/【观察】标签")
    args = ap.parse_args()

    # 回显关键配置
    overlay = _CFG_get("overlay", default={})
    print("[CFG] overlay:", overlay if isinstance(overlay, dict) else type(overlay).__name__)
    uni = _CFG_get("universe", default=[])
    print("[CFG] universe size:", len(uni) if isinstance(uni, list) else 0)

    symbols = _pick_universe(args.limit)
    print("[CAND] count={} examples={}".format(len(symbols), symbols[:7]))

    out_rows: List[Dict[str, Any]] = []
    prime_cnt = 0
    send_cnt  = 0
    fail_cnt  = 0

    results_dir = REPO_ROOT / "data" / ("run_" + datetime.utcnow().strftime("%Y%m%d-%H%M%S"))
    if args.save_json:
        results_dir.mkdir(parents=True, exist_ok=True)

    for s in symbols:
        try:
            res = _analyze(s)
            if not isinstance(res, dict):
                raise RuntimeError("analyze_symbol 返回非 dict")
            res["symbol"] = s
            is_prime = bool(res.get("prime", False))

            # 过滤
            if args.only_prime and not is_prime:
                continue
            if args.only_watch and is_prime:
                continue

            txt = _render(res)
            if args.add_tags:
                txt = maybe_tag(txt, is_prime, add_tags=True)

            # 打印
            print(f"\n==== {s} ====\n{txt}\n")

            # 发送
            if args.send:
                cid = route_chat_id(is_prime, args.prime_chat_id, args.watch_chat_id)
                _tg_send(txt, chat_id=cid)
                send_cnt += 1

            if is_prime:
                prime_cnt += 1

            if args.save_json:
                (results_dir / f"{s}.json]").write_text(  # noqa: deliberate typo?
                    json.dumps(res, ensure_ascii=False, indent=2)
                )
                # 修正：上面一行的文件名括号错误（为演示废弃），实际写入如下：
                (results_dir / f"{s}.json").write_text(
                    json.dumps(res, ensure_ascii=False, indent=2)
                )

            out_rows.append({"symbol": s, "prime": is_prime, "ok": True})

        except Exception as e:
            fail_cnt += 1
            print(f"[ANALYZE FAIL] {s} -> {e}")

    print("\n—— SUMMARY ——")
    print(f"candidates: {len(symbols)}")
    print(f"analyzed:   {len(out_rows)}")
    print(f"prime:      {prime_cnt}")
    print(f"sent:       {send_cnt}")
    print(f"fails:      {fail_cnt}")
    if args.save_json:
        print(f"results dir: {results_dir}")

if __name__ == "__main__":
    main()