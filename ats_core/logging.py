import sys, time

def log(msg, *args):
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    s = msg if not args else msg % args
    print(f"[{ts}Z] {s}", file=sys.stdout, flush=True)

def warn(msg, *args):
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    s = msg if not args else msg % args
    print(f"[{ts}Z][WARN] {s}", file=sys.stderr, flush=True)

def error(msg, *args):
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    s = msg if not args else msg % args
    print(f"[{ts}Z][ERROR] {s}", file=sys.stderr, flush=True)