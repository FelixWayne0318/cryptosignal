import os, sys, json, socket, urllib.request, urllib.parse, traceback
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
ATS  = ROOT / "ats_core"
CFG  = ROOT / "config" / "params.json"
ENVF = ROOT / ".env"

def _mask(tok: str) -> str:
    if not tok: return ""
    if len(tok) <= 10: return tok[:3] + "…"
    return tok[:5] + "…" + tok[-4:]

def check_paths():
    print("==> [1] 目录/路径检查")
    ok = True
    print(" cwd:", Path.cwd())
    print(" root:", ROOT)
    if not ATS.exists():
        print("  ✗ 缺少目录 ats_core/  → 请确认在仓库根目录运行")
        ok = False
    else:
        print("  ✓ ats_core/ 存在")
    # PYTHONPATH
    pyp = os.environ.get("PYTHONPATH","")
    if str(ROOT) not in pyp.split(":"):
        print("  ⚠ 未检测到 PYTHONPATH 中包含仓库根：", ROOT)
        print("    建议：export PYTHONPATH=%s:$PYTHONPATH" % ROOT)
    else:
        print("  ✓ PYTHONPATH 包含仓库根")
    return ok

def check_inits(repair=False):
    print("==> [2] 包结构检查（__init__.py）")
    ok = True
    missing = []
    for d in ATS.rglob("*"):
        if d.is_dir() and (d/"__init__.py").is_file() is False:
            missing.append(d)
    if missing:
        print("  ✗ 缺少 __init__.py 的包目录数：", len(missing))
        if repair:
            for d in missing:
                (d/"__init__.py").write_text("", encoding="utf-8")
            print("  ✓ 已为所有包目录补齐 __init__.py")
        else:
            print("  提示：运行 'python3 -m tools.selfcheck --repair' 可自动补齐")
        ok = False if not repair else True
    else:
        print("  ✓ 包结构完整")
    return ok

def check_env():
    print("==> [3] .env / 环境变量检查")
    tok = os.environ.get("TELEGRAM_BOT_TOKEN")
    cid = os.environ.get("TELEGRAM_CHAT_ID")
    if ENVF.exists():
        # 轻量解析 .env
        for line in ENVF.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s: continue
            k,v = s.split("=",1)
            k=k.strip(); v=v.strip().strip('"').strip("'")
            if k=="TELEGRAM_BOT_TOKEN" and not tok: tok = v
            if k=="TELEGRAM_CHAT_ID" and not cid: cid = v
    print("  BOT_TOKEN:", _mask(tok))
    print("  CHAT_ID  :", cid or "")
    ok = bool(tok and cid)
    if not ok:
        print("  ⚠ 未发现完整的电报配置（可写入 .env 或导出到当前 Shell）")
    return ok

def ping_binance():
    print("==> [4] Binance 连通性")
    try:
        with urllib.request.urlopen("https://fapi.binance.com/fapi/v1/ping", timeout=8) as r:
            _ = r.read()
        with urllib.request.urlopen("https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=1h&limit=2", timeout=8) as r:
            _ = r.read()
        print("  ✓ 连通")
        return True
    except Exception as e:
        print("  ✗ 无法连接：", e)
        print("    提示：检查 DNS/出站网络；稍后重试")
        return False

def import_modules():
    print("==> [5] 模块导入/入口检查")
    ok = True
    sys.path.insert(0, str(ROOT))  # 保险
    try:
        import ats_core.features.environment as env
        import ats_core.pipeline.analyze_symbol as ana
        import ats_core.pools.base_builder as base
        import ats_core.pools.overlay_builder as over
        import ats_core.pipeline.batch_scan as batch
    except Exception as e:
        print("  ✗ 导入失败：", e)
        ok = False
    else:
        print("  ✓ 关键模块可导入")
        # funding_hard_veto 返回值检查
        try:
            res = env.funding_hard_veto("BTCUSDT", True, {"funding_limit": 12})
            if not (isinstance(res, tuple) and len(res)==2 and isinstance(res[0], bool)):
                print("  ✗ funding_hard_veto 返回值不是 (bool, meta)")
                ok=False
            else:
                print("  ✓ funding_hard_veto 返回 (bool, meta)")
        except Exception as e:
            print("  ⚠ funding_hard_veto 调用异常（可忽略网络错误）：", e)
        # environment_score 兼容签名
        try:
            e1 = env.environment_score(48.0, 0.8, {"chop14_max":52, "room_min_for_bonus":0.5})
            if not (isinstance(e1, tuple) and len(e1)==2):
                print("  ✗ environment_score(简) 返回格式异常")
                ok=False
            else:
                print("  ✓ environment_score 兼容简签名")
        except Exception as e:
            print("  ✗ environment_score(简) 调用失败：", e)
            ok=False
        # __main__ 入口不是必须，但我们提醒
        for mod, path in [("base_builder", ATS/"pools"/"base_builder.py"),
                          ("batch_scan", ATS/"pipeline"/"batch_scan.py")]:
            try:
                text = path.read_text(encoding="utf-8")
                if 'if __name__' in text:
                    print(f"  ✓ {mod} 含 __main__ 入口（可 python -m 调用）")
                else:
                    print(f"  ⚠ {mod} 无 __main__ 入口（不影响函数式调用；-m 运行需 PYTHONPATH=.）")
            except Exception:
                pass
    return ok

def run_base():
    print("==> [6] 运行 Base 构建（写 reports/base/*）")
    try:
        sys.path.insert(0, str(ROOT))
        from ats_core.pools.base_builder import build_base_universe
        build_base_universe()
        # 验证输出
        base_dir = ROOT / "reports" / "base"
        js = list(base_dir.glob("base_pool_*.json"))
        print("  输出文件：", js[-1] if js else "未找到")
        return True if js else False
    except Exception as e:
        print("  ✗ 执行失败：")
        traceback.print_exc()
        return False

def run_overlay():
    print("==> [7] 运行 Overlay 构建（写 reports/overlay/*）")
    try:
        sys.path.insert(0, str(ROOT))
        from ats_core.pools.overlay_builder import build_overlay
        build_overlay()
        over_dir = ROOT / "reports" / "overlay"
        js = list(over_dir.glob("overlay_*.json"))
        print("  输出文件：", js[-1] if js else "未找到")
        return True if js else False
    except Exception as e:
        print("  ✗ 执行失败：")
        traceback.print_exc()
        return False

def dry_oneoff(sym="BTCUSDT"):
    print(f"==> [8] 单币 dry-run：{sym}")
    try:
        sys.path.insert(0, str(ROOT))
        from ats_core.pipeline.analyze_symbol import analyze_symbol
        r = analyze_symbol(sym, ctx_market=None)  # 不触发 Telegram
        side = "多" if r.get("prob_up",0)>=r.get("prob_dn",0) else "空"
        prob = r.get("prob", None) or max(r.get("prob_up",0), 1-r.get("prob_up",0))
        print(f"  ✓ 侧：{side} 概率≈{round(prob*100,1)}%  维度≥65数量：{r.get('dims_over',0)}/6")
        return True
    except Exception:
        traceback.print_exc()
        return False

def main():
    import argparse
    ap = argparse.ArgumentParser(description="ATS 自检")
    ap.add_argument("--repair", action="store_true", help="自动补齐 __init__.py")
    ap.add_argument("--ping-telegram", action="store_true", help="发送一条测试电报消息")
    ap.add_argument("--oneoff", metavar="SYMBOL", help="对指定币种做一次 dry-run")
    args = ap.parse_args()

    ok1 = check_paths()
    ok2 = check_inits(repair=args.repair)
    ok3 = check_env()
    ok4 = ping_binance()
    ok5 = import_modules()

    # 可选：发一条 Telegram 测试
    if args.ping_telegram and ok3:
        try:
            tok = os.environ.get("TELEGRAM_BOT_TOKEN")
            cid = os.environ.get("TELEGRAM_CHAT_ID")
            if ENVF.exists():
                for line in ENVF.read_text(encoding="utf-8").splitlines():
                    s = line.strip()
                    if not s or s.startswith("#") or "=" not in s: continue
                    k,v = s.split("=",1)
                    k=k.strip(); v=v.strip().strip('"').strip("'")
                    if k=="TELEGRAM_BOT_TOKEN" and not tok: tok = v
                    if k=="TELEGRAM_CHAT_ID" and not cid: cid = v
            data = urllib.parse.urlencode({"chat_id":cid, "text":"ATS Analyzer Telegram OK (selfcheck)"}).encode()
            req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendMessage", data=data)
            urllib.request.urlopen(req, timeout=8).read()
            print("  ✓ Telegram 发送成功")
        except Exception as e:
            print("  ✗ Telegram 发送失败：", e)

    # 跑 Base & Overlay（便于定位候选池问题）
    ok6 = run_base() if ok5 and ok4 else False
    ok7 = run_overlay() if ok5 and ok4 else False

    ok8 = True
    if args.oneoff:
        ok8 = dry_oneoff(args.oneoff)
    else:
        ok8 = dry_oneoff("BTCUSDT")

    print("\n==== 总结 ====")
    for i,(name,ok) in enumerate([
        ("路径/目录", ok1),
        ("包结构", ok2),
        (".env/电报", ok3),
        ("Binance 连通", ok4),
        ("模块导入/入口", ok5),
        ("Base 构建", ok6),
        ("Overlay 构建", ok7),
        ("单币 dry-run", ok8),
    ], start=1):
        print(f" [{i}] {name}: {'✓' if ok else '✗'}")

    # 对“是不是 main 文件的问题”给出结论
    if ok5:
        print("\n结论：入口 (__main__) 不是核心问题；若此前报 ModuleNotFoundError，多因未在仓库根运行或缺少 PYTHONPATH=.")
    else:
        print("\n提示：若 import 失败，请优先检查是否在仓库根目录，且已设置 PYTHONPATH=.")

if __name__ == "__main__":
    main()
