import sys
from ats_core.pipeline.analyze_symbol import analyze_symbol
from ats_core.outputs.telegram_fmt import render_prime, render_watch
from ats_core.outputs.publisher import telegram_send

def main():
    if len(sys.argv)<2:
        print("Usage: python -m tools.oneoff SYMBOL [--send]")
        sys.exit(1)
    sym=sys.argv[1].upper()
    send = ("--send" in sys.argv[2:])
    r = analyze_symbol(sym, ctx_market=None)
    html = render_prime(r) if r["publish"]["prime"] else render_watch(r)
    print(html)
    if send: telegram_send(html)

if __name__=="__main__":
    main()