"""
=============================================================
  ISSSSMAIL SCALPER BOT v4.2 — Smart Confluence Scalper
  محرك التحليل الذكي — كل الإشارات لازم تتفق
=============================================================

Strategy: 4/4 Confluence Required
  1. M5 trend direction (EMA 20 vs EMA 50) — الاتجاه العام
  2. M1 EMA cross (EMA 9 vs EMA 21) — نفس اتجاه M5
  3. RSI momentum — فوق 50 لـ BUY، تحت 50 لـ SELL
  4. MACD histogram — موجب لـ BUY، سالب لـ SELL

  كل الـ 4 لازم يتفقوا — مفيش صفقات نص نص
"""

import logging
from typing import Optional

from bot import config

logger = logging.getLogger("issssmail.analysis")

SIGNAL_BUY  = "BUY"
SIGNAL_SELL = "SELL"
SIGNAL_WAIT = "WAIT"


# ══════════════════════════════════════════════════════════
# TECHNICAL INDICATORS
# ══════════════════════════════════════════════════════════

def _ema(closes: list[float], period: int) -> list[float]:
    if len(closes) < period:
        return []
    k = 2.0 / (period + 1)
    seed = sum(closes[:period]) / period
    result = [seed]
    for price in closes[period:]:
        result.append(price * k + result[-1] * (1 - k))
    return result


def _rsi(closes: list[float], period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    if len(gains) < period:
        return None
    ag = sum(gains[:period]) / period
    al = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        ag = (ag * (period - 1) + gains[i]) / period
        al = (al * (period - 1) + losses[i]) / period
    if al == 0:
        return 100.0
    return round(100.0 - 100.0 / (1 + ag / al), 2)


def _macd(closes: list[float], fast: int = 12, slow: int = 26, sig: int = 9
          ) -> tuple[Optional[float], Optional[float], Optional[float]]:
    if len(closes) < slow + sig:
        return None, None, None
    fe = _ema(closes, fast)
    se = _ema(closes, slow)
    offset = len(fe) - len(se)
    if offset < 0:
        return None, None, None
    macd_line = [f - s for f, s in zip(fe[offset:], se)]
    if len(macd_line) < sig:
        return None, None, None
    se2 = _ema(macd_line, sig)
    if not se2:
        return None, None, None
    off2 = len(macd_line) - len(se2)
    ml = macd_line[off2:]
    mv = ml[-1]
    sv = se2[-1]
    return round(mv, 5), round(sv, 5), round(mv - sv, 5)


def _atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14
         ) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    trs = [
        max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        for i in range(1, len(closes))
    ]
    if len(trs) < period:
        return None
    atr_v = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr_v = (atr_v * (period - 1) + tr) / period
    return round(atr_v, 5)


def _adx(highs: list[float], lows: list[float], closes: list[float], period: int = 14
         ) -> Optional[float]:
    n = len(closes)
    if n < period * 2 + 2:
        return None
    pdm, mdm, trl = [], [], []
    for i in range(1, n):
        up = highs[i] - highs[i-1]
        dn = lows[i-1] - lows[i]
        pdm.append(up if up > dn and up > 0 else 0.0)
        mdm.append(dn if dn > up and dn > 0 else 0.0)
        tr = max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
        trl.append(tr)

    def _ws(data, p):
        if len(data) < p:
            return []
        r = [sum(data[:p])]
        for x in data[p:]:
            r.append(r[-1] - r[-1]/p + x)
        return r

    str_ = _ws(trl, period)
    spdm = _ws(pdm, period)
    smdm = _ws(mdm, period)
    if not str_:
        return None

    dx_list = []
    for i in range(len(str_)):
        if str_[i] == 0:
            continue
        pdi = 100 * spdm[i] / str_[i]
        mdi = 100 * smdm[i] / str_[i]
        d = pdi + mdi
        dx_list.append(100 * abs(pdi - mdi) / d if d else 0.0)

    if len(dx_list) < period:
        return None
    adx_v = sum(dx_list[:period]) / period
    for dx in dx_list[period:]:
        adx_v = (adx_v * (period - 1) + dx) / period
    return round(adx_v, 2)


# ══════════════════════════════════════════════════════════
# MAIN ANALYSIS — Smart Confluence v4.2
# ══════════════════════════════════════════════════════════

def analyze(
    candles: list[dict],
    htf_candles: Optional[list[dict]] = None,
) -> dict:
    """
    Smart confluence: ALL 4 conditions must agree.
    No more half-signals. Quality over quantity.
    """
    if len(candles) < config.CANDLES_NEEDED:
        return _wait(f"Need {config.CANDLES_NEEDED} candles, got {len(candles)}")

    closes = [float(c["close"]) for c in candles]
    highs  = [float(c["high"])  for c in candles]
    lows   = [float(c["low"])   for c in candles]

    # ── M1 Indicators ─────────────────────────────────────
    fast_ema_list = _ema(closes, config.TREND_FAST_EMA)   # EMA 9
    slow_ema_list = _ema(closes, config.TREND_SLOW_EMA)   # EMA 21
    if not fast_ema_list or not slow_ema_list:
        return _wait("EMA calculation failed")

    fast_ema = fast_ema_list[-1]
    slow_ema = slow_ema_list[-1]

    rsi_val  = _rsi(closes, config.RSI_PERIOD)
    atr_val  = _atr(highs, lows, closes, config.ATR_PERIOD)
    adx_val  = _adx(highs, lows, closes, config.ADX_PERIOD)
    _, _, macd_hist = _macd(closes, config.MACD_FAST, config.MACD_SLOW, config.MACD_SIGNAL)

    # ── M5 Trend Direction (HTF) ───────────────────────────
    htf_signal = SIGNAL_WAIT
    if htf_candles and len(htf_candles) >= config.HTF_CANDLES:
        htf_closes = [float(c["close"]) for c in htf_candles]
        h_fast = _ema(htf_closes, config.HTF_FAST_EMA)
        h_slow = _ema(htf_closes, config.HTF_SLOW_EMA)
        if h_fast and h_slow:
            if h_fast[-1] > h_slow[-1]:
                htf_signal = SIGNAL_BUY
            elif h_fast[-1] < h_slow[-1]:
                htf_signal = SIGNAL_SELL

    # ── Chop Filter ────────────────────────────────────────
    min_adx = getattr(config, "ADX_MIN", 20.0)
    if adx_val is not None and adx_val < min_adx:
        return _wait_detail(
            f"WAIT — سوق متذبذب (ADX={adx_val:.1f} < {min_adx})",
            fast_ema, slow_ema, rsi_val, macd_hist, adx_val, atr_val, htf_signal, len(candles)
        )

    # ══════════════════════════════════════════════════════
    # SMART SCORING: كل شرط مستقل — 4 شروط / 4 نقاط
    # الفرق: RSI فوق 50 = UP فقط، تحت 50 = DOWN فقط
    # ══════════════════════════════════════════════════════

    b_score, s_score = 0, 0
    b_reasons, s_reasons = [], []

    # ── شرط 1: M5 الاتجاه العام ──────────────────────────
    if htf_signal == SIGNAL_BUY:
        b_score += 1
        b_reasons.append("M5 ↑ (BUY)")
    elif htf_signal == SIGNAL_SELL:
        s_score += 1
        s_reasons.append("M5 ↓ (SELL)")
    else:
        # M5 مش واضح — استنى
        return _wait_detail(
            "WAIT — M5 بدون اتجاه واضح",
            fast_ema, slow_ema, rsi_val, macd_hist, adx_val, atr_val, htf_signal, len(candles)
        )

    # ── شرط 2: M1 EMA اتجاه (لازم يوافق M5) ─────────────
    if fast_ema > slow_ema:
        b_score += 1
        b_reasons.append(f"M1 EMA9({fast_ema:.0f}) > EMA21({slow_ema:.0f}) ↑")
    elif fast_ema < slow_ema:
        s_score += 1
        s_reasons.append(f"M1 EMA9({fast_ema:.0f}) < EMA21({slow_ema:.0f}) ↓")
    else:
        # EMA متساوية — مفيش اتجاه
        pass

    # ── شرط 3: RSI — فوق 55 صعود، تحت 45 هبوط ──────────
    if rsi_val is not None:
        if rsi_val > 55:
            b_score += 1
            b_reasons.append(f"RSI={rsi_val} > 55 (bullish)")
        elif rsi_val < 45:
            s_score += 1
            s_reasons.append(f"RSI={rsi_val} < 45 (bearish)")
        else:
            b_reasons.append(f"RSI={rsi_val} (محايد 45-55)")
            s_reasons.append(f"RSI={rsi_val} (محايد 45-55)")

    # ── شرط 4: MACD Histogram — موجب لـ BUY، سالب لـ SELL ─
    if macd_hist is not None:
        if macd_hist > 0:
            b_score += 1
            b_reasons.append(f"MACD +{macd_hist:.2f} (bullish)")
        elif macd_hist < 0:
            s_score += 1
            s_reasons.append(f"MACD {macd_hist:.2f} (bearish)")
        else:
            b_reasons.append("MACD = 0 (no momentum)")
            s_reasons.append("MACD = 0 (no momentum)")

    # ══════════════════════════════════════════════════════
    # HARD RULE: M5 و M1 لازم يتفقوا
    # استثناء: لو الفرق بين EMA9 و EMA21 كبير جداً = تعارض حقيقي
    # لو الفرق صغير (< 100 نقطة) = السوق بيتحول = نسمح بالدخول
    # ══════════════════════════════════════════════════════
    ema_gap = abs(fast_ema - slow_ema)
    strong_conflict = ema_gap > 100  # فرق أكبر من 100$ = تعارض حقيقي

    m1_up   = fast_ema > slow_ema
    m1_down = fast_ema < slow_ema

    if htf_signal == SIGNAL_SELL and m1_up and strong_conflict:
        return _wait_detail(
            f"WAIT — تعارض قوي: M5 هبوط vs M1 صعود (فرق EMA={ema_gap:.0f}$) — انتظر",
            fast_ema, slow_ema, rsi_val, macd_hist, adx_val, atr_val, htf_signal, len(candles)
        )

    if htf_signal == SIGNAL_BUY and m1_down and strong_conflict:
        return _wait_detail(
            f"WAIT — تعارض قوي: M5 صعود vs M1 هبوط (فرق EMA={ema_gap:.0f}$) — انتظر",
            fast_ema, slow_ema, rsi_val, macd_hist, adx_val, atr_val, htf_signal, len(candles)
        )

    # ══════════════════════════════════════════════════════
    # القرار النهائي — 4/4 مطلوب (كل الشروط)
    # ══════════════════════════════════════════════════════
    threshold = config.MIN_SIGNAL_SCORE  # = 4

    trend_str = "UP" if fast_ema > slow_ema else ("DOWN" if fast_ema < slow_ema else "FLAT")

    if b_score >= threshold:
        signal = SIGNAL_BUY
        score  = b_score
        reason = f"BUY {b_score}/4 ✅ | " + " | ".join(b_reasons)
    elif s_score >= threshold:
        signal = SIGNAL_SELL
        score  = s_score
        reason = f"SELL {s_score}/4 ✅ | " + " | ".join(s_reasons)
    else:
        signal = SIGNAL_WAIT
        score  = max(b_score, s_score)
        dir_b  = " | ".join(b_reasons) if b_score > s_score else " | ".join(s_reasons)
        reason = f"WAIT — {max(b_score,s_score)}/4 (محتاج {threshold}/4) | {dir_b}"

    return {
        "signal":       signal,
        "score":        score,
        "max_score":    4,
        "reason":       reason,
        "fast_ema":     round(fast_ema, 2),
        "slow_ema":     round(slow_ema, 2),
        "rsi":          rsi_val,
        "macd":         macd_hist,
        "adx":          adx_val,
        "atr":          atr_val,
        "trend":        trend_str,
        "htf_signal":   htf_signal,
        "dynamic_tp":   atr_val,
        "candles_used": len(candles),
    }


# ══════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════

def _wait(reason: str) -> dict:
    return {
        "signal": SIGNAL_WAIT, "score": 0, "max_score": 4,
        "reason": reason, "fast_ema": None, "slow_ema": None,
        "rsi": None, "macd": None, "adx": None, "atr": None,
        "trend": "FLAT", "htf_signal": SIGNAL_WAIT,
        "dynamic_tp": None, "candles_used": 0,
    }


def _wait_detail(reason, fe, se, rsi, macd, adx, atr, htf, used) -> dict:
    trend = "UP" if (fe and se and fe > se) else ("DOWN" if (fe and se and fe < se) else "FLAT")
    return {
        "signal": SIGNAL_WAIT, "score": 0, "max_score": 4,
        "reason": reason,
        "fast_ema": round(fe, 2) if fe else None,
        "slow_ema": round(se, 2) if se else None,
        "rsi": rsi, "macd": macd, "adx": adx, "atr": atr,
        "trend": trend, "htf_signal": htf,
        "dynamic_tp": atr, "candles_used": used,
    }
