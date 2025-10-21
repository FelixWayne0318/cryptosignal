import time, random
from ats_core.logging import warn
from ats_core.cfg import CFG

def sleep_retry(i):
    base = CFG.get("limits","backoff_first_sec", default=2.5)
    mx   = CFG.get("limits","backoff_max_sec", default=30.0)
    t = min(mx, base * (2 ** i)) * (0.8 + 0.4*random.random())
    warn("backoff %.2fs (attempt %d)", t, i+1)
    time.sleep(t)