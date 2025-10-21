from typing import Dict, Any

def _fmt_pct(x, digits=0):
    try:
        return f"{round(float(x)*100, digits)}%"
    except Exception:
        return "-"

def _fmt_num(x, digits=6):
    try:
        return f"{float(x):.{digits}f}"
    except Exception:
        return "-"

def _score_line(name:str, val, meta:Dict[str,Any]=None):
    # val: 0..100；根据得分给小圆点颜色
    try:
        v = int(val)
    except Exception:
        v = 0
    if   v >= 80: dot = "🟢"
    elif v >= 65: dot = "🟡"
    else:         dot = "🟠"
    extra = ""
    # 可选：带点注释（如 “斜率快 & 1h/4h 同侧”）
    if meta and meta.get("hint"):
        extra = f"（{meta['hint']}）"
    return f"• {name} {dot} {v}{extra}"

def format_signal_v15(r: Dict[str, Any], is_watch: bool) -> str:
    """
    统一的 v1.5 电报模板：
      - is_watch=True：观察（未发布）样式（与正式相同，但标题显著标注“观察”，并附“未发布原因”）
      - is_watch=False：正式信号
    期望字段（有就用、缺则降级显示）：
      r: {
        symbol, side ('long'/'short' 可选), prob_up (0..1), dims_over,
        plan: {entry_low, entry_high, sl, tp1, tp2, R, cap_hint?},
        scores: {T,S,V,A,O,E},
        env: {prior, Q, chop, room, oi24_pct?, crowding?},
        veto: {funding_extreme?}, micro_ok (bool),
        reasons? [字符串列表]
      }
    """
    sym = r.get("symbol","-")
    # 判定多空 & 概率
    p_up = float(r.get("prob_up", 0.5))
    long_side = p_up >= 0.5 if r.get("side") is None else (str(r.get("side")).lower() in ("long","多","bull","buy"))
    side_zh = "做多" if long_side else "做空"
    prob = max(p_up, 1-p_up)
    prob_pct = f"{round(prob*100)}%"

    # 颜色块（正式：多=🟩/空=🟥；观察：标题显示🟡 观察，其它同正式）
    side_block = "🟩" if long_side else "🟥"

    # 标题
    if is_watch:
        title = f"<b>🟡 观察 · {sym}</b>"
    else:
        title = f"<b>{sym}</b>"

    # 第二行（侧与概率）
    line2 = f"{side_block} {side_zh} 概率 <b>{prob_pct}</b>"

    # 交易计划（若缺失则降级为“参考区间”）
    plan = r.get("plan", {}) or {}
    entry_low  = plan.get("entry_low")
    entry_high = plan.get("entry_high")
    sl         = plan.get("sl")
    tp1        = plan.get("tp1")
    tp2        = plan.get("tp2")
    R          = plan.get("R")
    cap_hint   = plan.get("cap_hint")  # 如 “靠近前高/对手位；Donchian72 限顶”

    if entry_low is not None and entry_high is not None:
        entry_line = f"入场区：<code>{_fmt_num(entry_low)} – {_fmt_num(entry_high)}</code>"
    else:
        # 向后兼容：旧字段 ref_low/ref_high/sr_hint
        ref_low  = r.get("ref_low")
        ref_high = r.get("ref_high")
        sr_hint  = r.get("sr_hint","近端SR带 72h")
        entry_line = f"参考区间（非指令）：<code>{_fmt_num(ref_low)} – {_fmt_num(ref_high)}</code> · {sr_hint}"

    if sl is not None:
        sl_line = f"止损：<code>{_fmt_num(sl)}</code>"
    else:
        sl_line = "止损：-"

    if tp1 is not None and R is not None:
        # 显示 R 与 TP2 限顶提示
        tp_line = f"止盈：TP1=<code>{_fmt_num(tp1)}</code> · TP2=<code>{_fmt_num(tp2) if tp2 is not None else '-'}</code>（{ '≤2.5R；' if tp2 is not None else '' }R≈{_fmt_num(R, 3)}{('；' + cap_hint) if cap_hint else ''}）"
    else:
        tp_line = "止盈：-"

    # 六维证据（T/S/V/A/O/E）
    scores = r.get("scores", {}) or {}
    T = scores.get("T",0); S = scores.get("S",0); V = scores.get("V",0)
    A = scores.get("A",0); O = scores.get("O",0); E = scores.get("E",0)
    # 这里 hint 留空，若上游提供可自动带上
    six_lines = "\n".join([
        _score_line("趋势", T, scores.get("_T")),
        _score_line("结构", S, scores.get("_S")),
        _score_line("量能", V, scores.get("_V")),
        _score_line("加速", A, scores.get("_A")),
        _score_line("持仓", O, scores.get("_O")),
        _score_line("环境", E, scores.get("_E")),
    ])

    # 环境提示
    env = r.get("env", {}) or {}
    prior = env.get("prior")
    Q     = env.get("Q")
    chop  = env.get("chop")
    room  = env.get("room")
    oi24  = env.get("oi24_pct")
    crowd = env.get("crowding")
    env_parts = []
    if prior is not None: env_parts.append(f"prior={round(float(prior),2)}")
    if Q     is not None: env_parts.append(f"Q={round(float(Q),2)}")
    if chop  is not None: env_parts.append(f"CHOP={round(float(chop),1)}")
    if room  is not None: env_parts.append(f"Room={round(float(room),2)}×ATR")
    if oi24  is not None: env_parts.append(f"OI24h={round(float(oi24),2)}%{'⚠️' if crowd else ''}")
    env_line = "<b>环境</b> " + " · ".join(env_parts) if env_parts else "<b>环境</b> -"

    # 未发布原因（仅观察显示；正式不带）
    reasons = []
    if is_watch:
        # 自动归纳（可被上游 reasons 覆盖/补充）
        prob_ok = (prob >= 0.62)
        dims_ok = (int(r.get("dims_over",0)) >= 4)
        micro_ok = bool(r.get("micro_ok", False))
        if not prob_ok:  reasons.append("概率未达标")
        if not dims_ok:  reasons.append("维度不足")
        if not micro_ok: reasons.append("15m微确认未通过")
        if (r.get("veto") or {}).get("funding_extreme"):
            reasons.append("资金费率极端")
        # 合并上游 reasons
        for extra in (r.get("reasons") or []):
            if extra not in reasons:
                reasons.append(extra)

    # 汇总
    parts = [
        title,
        f"{line2}",
        f"{entry_line}    {sl_line}",
        f"{tp_line}",
        "",
        "<b>六维证据</b>",
        six_lines,
        "",
        env_line,
    ]
    if is_watch and reasons:
        parts.append("")
        parts.append("未发布原因：" + "；".join(reasons))

    return "\n".join(parts).strip()
