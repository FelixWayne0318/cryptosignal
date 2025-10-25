from ats_core.features.ta_core import ema, donchian

def price_plan(h,l,c, atr_now, params, side_long):
    ema10=ema(c,10); ema30=ema(c,30)
    price=c[-1]
    ext = min(abs(price-ema30[-1])/max(1e-12,atr_now), params["entry_ext_max"])
    delta = (params["delta_base"] + params["delta_coef"]*ext) * atr_now
    if side_long:
        entry_lo = ema10[-1]-delta
        entry_hi = ema10[-1]+0.01*atr_now
        # SL
        piv = min(l[-12:])  # last pivot low proxy
        sl = max(piv - params["sl_pivot_back"]*atr_now, (entry_lo+entry_hi)/2 - params["sl_atr_back"]*atr_now)
        # R
        R = ( (entry_lo+entry_hi)/2 - sl )
        hh,_ = donchian(h,l, params["sr_band_lookback"])
        tp1 = (entry_lo+entry_hi)/2 + params["tp1_R"]*R
        # TP2 cap
        cap = max(0.0, hh[-1]*(1.0-params["sr_margin"]) - (entry_lo+entry_hi)/2)
        tp2 = (entry_lo+entry_hi)/2 + min(params["tp2_R_max"]*R, cap)
        room = (hh[-1] - (entry_lo+entry_hi)/2)/max(1e-12, atr_now)
        if room < params["room_atr_tp2_floor"]:
            tp2 = (entry_lo+entry_hi)/2 + max(params["tp1_R"]*R, params["tp2_room_floor_R"]*R)
    else:
        entry_lo = ema10[-1]-0.01*atr_now
        entry_hi = ema10[-1]+delta
        piv = max(h[-12:])
        sl = min(piv + params["sl_pivot_back"]*atr_now, (entry_lo+entry_hi)/2 + params["sl_atr_back"]*atr_now)
        R = sl - (entry_lo+entry_hi)/2
        _,ll = donchian(h,l, params["sr_band_lookback"])
        tp1 = (entry_lo+entry_hi)/2 - params["tp1_R"]*R
        cap = max(0.0, (entry_lo+entry_hi)/2 - ll[-1]*(1.0+params["sr_margin"]))
        tp2 = (entry_lo+entry_hi)/2 - min(params["tp2_R_max"]*R, cap)
        room = ((entry_lo+entry_hi)/2 - ll[-1])/max(1e-12, atr_now)
        if room < params["room_atr_tp2_floor"]:
            tp2 = (entry_lo+entry_hi)/2 - max(params["tp1_R"]*R, params["tp2_room_floor_R"]*R)
    return {"entry_lo":entry_lo,"entry_hi":entry_hi,"sl":sl,"tp1":tp1,"tp2":tp2,"room":room}