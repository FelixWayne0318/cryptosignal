import os, time, json
from ats_core.cfg import CFG
from ats_core.pools.base_builder import build_base_universe
from ats_core.pools.overlay_builder import update_overlay_universe
from ats_core.pipeline.analyze_symbol import analyze_symbol
from ats_core.outputs.telegram_fmt import render_prime, render_watch
from ats_core.outputs.publisher import telegram_send
from ats_core.logging import log, warn

DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "data", "reports")
os.makedirs(DATA, exist_ok=True)

def batch_run():
    base = build_base_universe()
    overlay = update_overlay_universe(base)
    syms = overlay + [s for s in base if s not in overlay]
    for sym in syms:
        try:
            r = analyze_symbol(sym, ctx_market=None)
            html = render_prime(r) if r["publish"]["prime"] else render_watch(r)
            telegram_send(html)
            # save report
            ts=time.strftime("%Y%m%dT%H%MZ", time.gmtime())
            with open(os.path.join(DATA, f"scan_{sym}_{ts}.md"),"w",encoding="utf-8") as f:
                f.write(html)
        except Exception as e:
            warn("batch %s error: %s", sym, e)
        time.sleep(CFG.get("limits","per_symbol_delay_ms", default=600)/1000.0)