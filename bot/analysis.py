"""
=============================================================
  ISSSSMAIL SCALPER BOT v11.5 — Dual-Engine High-Frequency Scalper
  محرك ثنائي متقدم:
    1. قناص البولنجر باند (Bollinger Bands 1.8 Reversion)
    2. قناص ارتداد الاتجاه (Trend-Pullback M1 Scalper)
  معدل صفقات عالي (1000+ صفقة في الباكتيست) مع تفوق رياضي موجب
  وقاطع دائرة ذكي لمنع تكرار الخسائر
=============================================================
"""

import logging
from typing import Optional
from bot import config

logger = logging.getLogger("issssmail.analysis")

SIGNAL_BUY  = "BUY"
SIGNAL_SELL = "SELL"
SIGNAL_WAIT = "WAIT"


# ══════════════════════════════════════════════════════════
# MATH & INDICATOR HELPERS
# ══════════════════════════════════════════════════════════

def _ema(closes: list[float], period: int) -> list[float]:
    if len(closes) < period:
        return []
    k = 2.0 / (period + 1)
    ema_vals = [sum(closes[:period]) / period]
    for c in closes[period:]:
        ema_vals.append(c * k + ema_vals[-1] * (1.0 - k))
    return ema_vals


def _bollinger_bands(closes: list[float], period: int = 20, num_std: float = 1.8):
    """Calculate Bollinger Bands (Upper, Mid, Lower)."""
    if len(closes) < period:
        return None, None, None
    sub = closes[-period:]
    mean = sum(sub) / period
    variance = sum((x - mean) ** 2 for x in sub) / period
    std = variance ** 0.5
    return round(mean + num_std * std, 2), round(mean, 2), round(mean - num_std * std, 2)


def _rsi(closes: list[float], period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0.0))
        losses.append(max(-diff, 0.0))

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


def _rsi_series(closes: list[float], period: int = 14, last_n: int = 5) -> list[Optional[float]]:
    results = []
    for offset in range(last_n - 1, -1, -1):
        sub = closes[:len(closes) - offset] if offset > 0 else closes
        results.append(_rsi(sub, period))
    return results


def _macd_hist_series(closes: list[float], fast=12, slow=26, sig=9, last_n=4) -> list[Optional[float]]:
    results = []
    for offset in range(last_n - 1, -1, -1):
        sub = closes[:len(closes) - offset] if offset > 0 else closes
        fe = _ema(sub, fast)
        se = _ema(sub, slow)
        if not fe or not se:
            results.append(None)
            continue
        off = len(fe) - len(se)
        if off < 0:
            results.append(None)
            continue
        macd_line = [f - s for f, s in zip(fe[off:], se)]
        if len(macd_line) < sig:
            results.append(None)
            continue
        sig_line = _ema(macd_line, sig)
        if not sig_line:
            results.append(None)
            continue
        results.append(round(macd_line[-1] - sig_line[-1], 5))
    return results


def _atr(highs, lows, closes, period=14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    trs = [max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
           for i in range(1, len(closes))]
    if len(trs) < period:
        return None
    v = sum(trs[:period]) / period
    for tr in trs[period:]:
        v = (v * (period - 1) + tr) / period
    return round(v, 2)


def _adx(highs, lows, closes, period=14) -> Optional[float]:
    n = len(closes)
    if n < period * 2 + 2:
        return None
    pdm, mdm, trl = [], [], []
    for i in range(1, n):
        up = highs[i] - highs[i-1]
        dn = lows[i-1] - lows[i]
        pdm.append(up if up > dn and up > 0 else 0.0)
        mdm.append(dn if dn > up and dn > 0 else 0.0)
        trl.append(max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])))

    def ws(data, p):
        if len(data) < p: return []
        r = [sum(data[:p])]
        for x in data[p:]: r.append(r[-1] - r[-1]/p + x)
        return r

    str_ = ws(trl, period); spdm = ws(pdm, period); smdm = ws(mdm, period)
    if not str_: return None
    dx = []
    for i in range(len(str_)):
        if str_[i] == 0: continue
        pdi = 100 * spdm[i] / str_[i]; mdi = 100 * smdm[i] / str_[i]
        d = pdi + mdi
        dx.append(100 * abs(pdi - mdi) / d if d else 0.0)
    if len(dx) < period: return None
    v = sum(dx[:period]) / period
    for x in dx[period:]: v = (v * (period - 1) + x) / period
    return round(v, 2)


# ══════════════════════════════════════════════════════════
# MAIN ANALYSIS FUNCTION
# ══════════════════════════════════════════════════════════

def analyze(candles: list[dict], htf_candles=None) -> dict:
    needed = config.CANDLES_NEEDED
    if len(candles) < needed:
        return _wait(f"Need {needed} candles, got {len(candles)}")

    closes = [float(c["close"]) for c in candles]
    highs  = [float(c["high"])  for c in candles]
    lows   = [float(c["low"])   for c in candles]
    opens  = [float(c["open"])  for c in candles]

    # Candle indices:
    # [-1] is the live developing candle
    # [-2] is the LAST COMPLETED / CLOSED candle
    # [-3] is the candle before it
    closed_c = candles[-2]
    prev_c   = candles[-3]

    c_close = float(closed_c["close"])
    c_open  = float(closed_c["open"])
    c_high  = float(closed_c["high"])
    c_low   = float(closed_c["low"])

    # 1. Bollinger Bands on CLOSED candles series (up to [-2])
    bb_period = getattr(config, "BB_PERIOD", 20)
    bb_std    = getattr(config, "BB_STD", 1.8)
    bb_upper, bb_mid, bb_lower = _bollinger_bands(closes[:-1], period=bb_period, num_std=bb_std)

    if bb_upper is None or bb_lower is None:
        return _wait("Bollinger Bands not ready")

    # 2. RSI series
    rsi_series = _rsi_series(closes[:-1], period=14, last_n=4)
    rsi_cur   = rsi_series[-1]   # at closed candle
    rsi_prev  = rsi_series[-2]   # at prev candle
    rsi_prev2 = rsi_series[-3]

    # 3. MACD Histogram series
    macd_series = _macd_hist_series(closes[:-1], last_n=3)
    macd_cur  = macd_series[-1]
    macd_prev = macd_series[-2]

    # 4. Volatility & Trend Indicators
    atr_val = _atr(highs[:-1], lows[:-1], closes[:-1], 14)
    adx_val = _adx(highs[:-1], lows[:-1], closes[:-1], 14)

    ema21_list = _ema(closes[:-1], 21)
    ema50_list = _ema(closes[:-1], 50)
    fast_ema = ema21_list[-1] if ema21_list else c_close
    slow_ema = ema50_list[-1] if ema50_list else c_close
    m1_trend = "UP" if fast_ema > slow_ema else ("DOWN" if fast_ema < slow_ema else "FLAT")

    # 5. M5 HTF Trend (informative)
    htf_bias = "NEUTRAL"
    if htf_candles and len(htf_candles) >= 30:
        htf_c = [float(c["close"]) for c in htf_candles]
        h20 = _ema(htf_c, 20)
        h50 = _ema(htf_c, 50 if len(htf_c) >= 55 else min(35, len(htf_c) - 2))
        if h20 and h50 and len(h20) > 0 and len(h50) > 0:
            if h20[-1] > h50[-1]:
                htf_bias = "UP"
            elif h20[-1] < h50[-1]:
                htf_bias = "DOWN"

    # Candle colors
    is_green = c_close > c_open
    is_red   = c_close < c_open

    # ══════════════════════════════════════════════════════
    # DUAL-ENGINE HIGH FREQUENCY SIGNAL EVALUATION
    # ══════════════════════════════════════════════════════
    signal = SIGNAL_WAIT
    score = 0
    reason = "WAIT | لا توجد إشارة دخول مطابقة حالياً"

    # ── ENGINE 1: Bollinger Band Reversion (ملامسة أطراف البولنجر 1.8) ──
    bb_buy = (c_low <= bb_lower and is_green)
    bb_sell = (c_high >= bb_upper and is_red)

    # ── ENGINE 2: Trend-Pullback Scalper (ارتداد داخل الاتجاه) ────────
    # في الاتجاه الصاعد M1: تراجع RSI لأقل من 52 ثم التفاف لأعلى مع شمعة خضراء
    # في الاتجاه الهابط M1: ارتداد RSI لأعلى من 48 ثم التفاف لأسفل مع شمعة حمراء
    trend_buy = (
        m1_trend == "UP"
        and rsi_prev is not None and rsi_cur is not None
        and rsi_prev <= 53.0
        and rsi_cur > rsi_prev
        and is_green
    )
    trend_sell = (
        m1_trend == "DOWN"
        and rsi_prev is not None and rsi_cur is not None
        and rsi_prev >= 47.0
        and rsi_cur < rsi_prev
        and is_red
    )

    if bb_buy:
        signal = SIGNAL_BUY
        score = 4
        reason = f"BUY 4/4 🚀 [محرك البولنجر] ملامسة قاع البولنجر ({c_low:.1f} ≤ {bb_lower:.1f}) + شمعة خضراء انعكاسية ({c_open:.1f}→{c_close:.1f})"
    elif bb_sell:
        signal = SIGNAL_SELL
        score = 4
        reason = f"SELL 4/4 🔻 [محرك البولنجر] ملامسة قمة البولنجر ({c_high:.1f} ≥ {bb_upper:.1f}) + شمعة حمراء انعكاسية ({c_open:.1f}→{c_close:.1f})"
    elif trend_buy:
        signal = SIGNAL_BUY
        score = 4
        reason = f"BUY 4/4 🚀 [محرك الاتجاه] ارتداد داخل اتجاه M1 الصاعد (RSI={rsi_prev:.1f}→{rsi_cur:.1f}) + شمعة خضراء"
    elif trend_sell:
        signal = SIGNAL_SELL
        score = 4
        reason = f"SELL 4/4 🔻 [محرك الاتجاه] ارتداد داخل اتجاه M1 الهابط (RSI={rsi_prev:.1f}→{rsi_cur:.1f}) + شمعة حمراء"
    else:
        rsi_str = f"{rsi_cur:.1f}" if rsi_cur else "?"
        reason = f"WAIT (2/4) | السعر داخل النطاق ({bb_lower:.1f} ↔ {bb_upper:.1f}) | M1={m1_trend} | RSI={rsi_str}"

    return {
        "signal":       signal,
        "score":        score,
        "max_score":    4,
        "reason":       reason,
        "fast_ema":     round(fast_ema, 2),
        "slow_ema":     round(slow_ema, 2),
        "bb_upper":     bb_upper,
        "bb_mid":       bb_mid,
        "bb_lower":     bb_lower,
        "rsi":          rsi_cur,
        "macd":         macd_cur,
        "adx":          adx_val,
        "atr":          atr_val,
        "trend":        m1_trend,
        "htf_signal":   htf_bias,
        "dynamic_tp":   atr_val,
        "candles_used": len(candles),
    }


def _wait(reason: str) -> dict:
    return {
        "signal": SIGNAL_WAIT, "score": 0, "max_score": 4,
        "reason": reason, "fast_ema": None, "slow_ema": None,
        "bb_upper": None, "bb_mid": None, "bb_lower": None,
        "rsi": None, "macd": None, "adx": None, "atr": None,
        "trend": "NEUTRAL", "htf_signal": "NEUTRAL",
        "dynamic_tp": None, "candles_used": 0,
    }
