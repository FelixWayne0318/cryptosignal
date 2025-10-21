from ats_core.features.ta_core import chop14, donchian
from ats_core.sources.funding import funding_stats

def funding_hard_veto(symbol, bigcap, params):
    st = funding_stats(symbol)
    if st.get("samples",0) < params["min_samples"]:
        return False, {"samples": st.get("samples",0), "reason":"insufficient"}
    z = abs(st.get("z",0.0)); p = st.get("p",0.5)
    if bigcap:
        if z>=params["z_abs_big"] or p>=params["p_hi_big"] or p<=params["p_lo_big"]:
            return True, {"samples":st["samples"],"z":z,"p":p,"reason":"extreme_bigcap"}
    else:
        if z>=params["z_abs_small"] or p>=params["p_hi_small"] or p<=params["p_lo_small"]:
            return True, {"samples":st["samples"],"z":z,"p":p,"reason":"extreme_smallcap"}
    return False, {"samples":st["samples"],"z":st.get("z",0.0),"p":st.get("p",0.5),"reason":"ok"}

def environment_score(h,l,c, atr_now, params):
    ch = chop14(h,l,c)
    hh, ll = max(h[-72:]), min(l[-72:])
    room = (hh - c[-1]) / max(1e-12, atr_now)
    s = 0
    s += int(60*max(0.0, min(1.0, (params["chop14_max"]-ch)/params["chop14_max"]))))
    s += int(40*max(0.0, min(1.0, (room - params["room_atr_min"])/(1.5 - params["room_atr_min"]))))
    return min(100,max(0,s)), {"chop":ch, "room":room}