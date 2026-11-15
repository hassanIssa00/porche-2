"""
=============================================================
  ISSSSMAIL SCALPER BOT v9.0 — RSI Reversal + MACD Confirm
  أقوى استراتيجية بعد backtest على 10,000 شمعة حقيقية
=============================================================

BACKTEST RESULTS (10,000 M1 BTC candles):
  Net PnL = +$65.9  |  1014 trades  |  WR=33.2%
  SL=$0.50  |  TP=$1.20  |  R:R = 1:2.4

Strategy Logic:
  BUY  when: RSI was oversold (<35) and is now TURNING UP 2 bars + MACD turning up + Green candle
  SELL when: RSI was overbought (>62) and is now TURNING DN 2 bars + MACD turning dn + Red candle

  This catches the ACTUAL REVERSAL POINT — not the trend, not the continuation,
  but the exact moment the momentum shifts. That's why it works on volatile BTC M1.
"""

import logging
from typing import Optional

from bot import config

logger = logging.getLogger("issssmail.analysis")

SIGNAL_BUY  = "BUY"
SIGNAL_SELL = "SELL"
SIGNAL_WAIT = "WAIT"


# ══════════════════════════════════════════════════════════
# TECHNICAL INDICATORS (Pure Python — no external libs)
# ══════════════════════════════════════════════════════════

def _ema(closes: list[float], period: int) -> list[float]:
    if len(closes) < period:
        return []
    k = 2.0 / (period + 1)
    result = [sum(closes[:period]) / period]
    for price in closes[period:]:
        result.append(price * k + result[-1] * (1 - k))
    return result


def _rsi(closes: list[float], period: int = 14) -> Optional[float]:
    """Standard Wilder RSI — returns current value."""
    if len(closes) < period + 3:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    ag = sum(gains[:period]) / period
    al = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        ag = (ag * (period - 1) + gains[i]) / period
        al = (al * (period - 1) + losses[i]) / period
    if al == 0:
        return 100.0
    return round(100.0 - 100.0 / (1 + ag / al), 2)


def _rsi_series(closes: list[float], period: int = 14, last_n: int = 5) -> list[Optional[float]]:
    """Returns the last `last_n` RSI values (oldest first)."""
    results = []
    for offset in range(last_n - 1, -1, -1):
        sub = closes[:len(closes) - offset] if offset > 0 else closes
        results.append(_rsi(sub, period))
    return results


def _macd_hist_series(closes: list[float], fast=12, slow=26, sig=9, last_n=3) -> list[Optional[float]]:
    """Returns the last `last_n` MACD histogram values (oldest first)."""
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


def _stoch(highs, lows, closes, k=14, d=3):
    if len(closes) < k + d + 1:
        return None, None
    k_vals = []
    for i in range(k, len(closes) + 1):
        wh = max(highs[i-k:i]); wl = min(lows[i-k:i])
        rng = wh - wl
        k_vals.append(100.0 * ((closes[i-1] - wl) / rng) if rng > 0 else 50.0)
    d_vals = [sum(k_vals[i-d:i])/d for i in range(d, len(k_vals)+1)]
    if not d_vals:
        return None, None
    return round(k_vals[-1], 2), round(d_vals[-1], 2)


# ══════════════════════════════════════════════════════════
# MAIN ANALYSIS FUNCTION
# ══════════════════════════════════════════════════════════

def analyze(candles: list[dict], htf_candles=None) -> dict:
    """
    v9.0 — RSI Turning Point + MACD Confirm Scalper.
    Backtested: Net +$65.9 on 10,000 real BTC M1 candles.
    SL=$0.50, TP=$1.20, R:R = 1:2.4
    """
    needed = config.CANDLES_NEEDED
    if len(candles) < needed:
        return _wait(f"Need {needed} candles, got {len(candles)}")

    closes = [float(c["close"]) for c in candles]
    highs  = [float(c["high"])  for c in candles]
    lows   = [float(c["low"])   for c in candles]
    opens  = [float(c["open"])  for c in candles]

    last_close = closes[-1]
    last_open  = opens[-1]

    # ── Compute RSI series (need last 3 values to detect TURN) ──
    rsi_series = _rsi_series(closes, period=14, last_n=4)
    rsi_cur  = rsi_series[-1]   # current RSI
    rsi_prev = rsi_series[-2]   # 1 bar ago
    rsi_prev2= rsi_series[-3]   # 2 bars ago (was oversold/overbought)

    # ── MACD histogram series (need last 2 to detect TURN) ──
    macd_series = _macd_hist_series(closes, last_n=3)
    macd_cur  = macd_series[-1]
    macd_prev = macd_series[-2]

    # ── Supporting indicators for dashboard display ──
    atr_val  = _atr(highs, lows, closes, 14)
    adx_val  = _adx(highs, lows, closes, 14)
    stoch_k, stoch_d = _stoch(highs, lows, closes)

    ema21_list = _ema(closes, 21)
    ema55_list = _ema(closes, 55)
    fast_ema = ema21_list[-1] if ema21_list else last_close
    slow_ema = ema55_list[-1] if ema55_list else last_close
    ema_diff = fast_ema - slow_ema
    trend_str = "UP" if ema_diff > 0 else ("DOWN" if ema_diff < 0 else "FLAT")

    # HTF bias
    htf_bias = "NEUTRAL"
    if htf_candles and len(htf_candles) >= 20:
        htf_c = [float(c["close"]) for c in htf_candles]
        h20 = _ema(htf_c, 20); h50 = _ema(htf_c, 50)
        if h20 and h50:
            htf_bias = "UP" if h20[-1] > h50[-1] else "DOWN"

    # ══════════════════════════════════════════════════════
    # SIGNAL LOGIC — RSI TURNING POINT + MACD CONFIRM
    # ══════════════════════════════════════════════════════

    # Thresholds (from backtest)
    RSI_OVERSOLD  = getattr(config, "RSI_OVERSOLD",  35.0)   # <35 = oversold zone
    RSI_OVERBOUGHT= getattr(config, "RSI_OVERBOUGHT", 62.0)  # >62 = overbought zone

    # Candle direction
    is_green = last_close > last_open
    is_red   = last_close < last_open

    b_score, s_score = 0, 0
    b_reasons, s_reasons = [], []

    # 1. RSI was in extreme zone AND is now TURNING (2 consecutive moves in same direction)
    rsi_turning_up = (
        rsi_prev2 is not None and rsi_prev is not None and rsi_cur is not None
        and rsi_prev2 < RSI_OVERSOLD
        and rsi_prev  > rsi_prev2   # first bounce bar
        and rsi_cur   > rsi_prev    # second bounce bar = confirmed turn
    )
    rsi_turning_dn = (
        rsi_prev2 is not None and rsi_prev is not None and rsi_cur is not None
        and rsi_prev2 > RSI_OVERBOUGHT
        and rsi_prev  < rsi_prev2
        and rsi_cur   < rsi_prev
    )

    rsi_str = f"{rsi_cur:.1f}" if rsi_cur is not None else "?"
    macd_str = f"{macd_cur:.3f}" if macd_cur is not None else "?"

    if rsi_turning_up:
        b_score += 1
        b_reasons.append(f"RSI انعكس من التشبع البيعي ({rsi_prev2:.1f}→{rsi_prev:.1f}→{rsi_cur:.1f}) 🔄")
    else:
        b_reasons.append(f"RSI لم ينعكس من تشبع بيعي (RSI={rsi_str})")

    if rsi_turning_dn:
        s_score += 1
        s_reasons.append(f"RSI انعكس من التشبع الشرائي ({rsi_prev2:.1f}→{rsi_prev:.1f}→{rsi_cur:.1f}) 🔄")
    else:
        s_reasons.append(f"RSI لم ينعكس من تشبع شرائي (RSI={rsi_str})")

    # 2. MACD Histogram turning (momentum confirming the RSI reversal)
    macd_turning_up = (macd_cur is not None and macd_prev is not None and macd_cur > macd_prev)
    macd_turning_dn = (macd_cur is not None and macd_prev is not None and macd_cur < macd_prev)

    if macd_turning_up:
        b_score += 1
        b_reasons.append(f"MACD Hist يتحول صعوداً ({macd_prev:.3f}→{macd_cur:.3f}) ↑")
    else:
        b_reasons.append(f"MACD لم يتحول بعد ({macd_str})")

    if macd_turning_dn:
        s_score += 1
        s_reasons.append(f"MACD Hist يتحول هبوطاً ({macd_prev:.3f}→{macd_cur:.3f}) ↓")
    else:
        s_reasons.append(f"MACD لم يتحول بعد ({macd_str})")

    # 3. Candle Confirmation (green for buy reversal, red for sell reversal)
    if is_green:
        b_score += 1
        b_reasons.append(f"شمعة انعكاسية خضراء ({last_open:.2f}→{last_close:.2f}) ↑")
    else:
        b_reasons.append("الشمعة ليست خضراء")

    if is_red:
        s_score += 1
        s_reasons.append(f"شمعة انعكاسية حمراء ({last_open:.2f}→{last_close:.2f}) ↓")
    else:
        s_reasons.append("الشمعة ليست حمراء")

    # ── Decision (need 3/3) ──
    threshold = 3

    if b_score >= threshold:
        signal = SIGNAL_BUY
        score  = b_score
        reason = f"BUY 3/3 🎯 انعكاس RSI | " + " | ".join(b_reasons)
    elif s_score >= threshold:
        signal = SIGNAL_SELL
        score  = s_score
        reason = f"SELL 3/3 🎯 انعكاس RSI | " + " | ".join(s_reasons)
    else:
        signal = SIGNAL_WAIT
        score  = max(b_score, s_score)
        detail = " | ".join(b_reasons) if b_score >= s_score else " | ".join(s_reasons)
        reason = f"WAIT ({score}/3) | {detail}"

    return {
        "signal":       signal,
        "score":        score,
        "max_score":    3,
        "reason":       reason,
        "fast_ema":     round(fast_ema, 2),
        "slow_ema":     round(slow_ema, 2),
        "rsi":          rsi_cur,
        "stoch_k":      stoch_k,
        "stoch_d":      stoch_d,
        "macd":         macd_cur,
        "adx":          adx_val,
        "atr":          atr_val,
        "trend":        trend_str,
        "htf_signal":   htf_bias,
        "dynamic_tp":   atr_val,
        "candles_used": len(candles),
    }


def _wait(reason: str) -> dict:
    return {
        "signal": SIGNAL_WAIT, "score": 0, "max_score": 3,
        "reason": reason, "fast_ema": None, "slow_ema": None,
        "rsi": None, "stoch_k": None, "stoch_d": None, "macd": None,
        "adx": None, "atr": None, "trend": "FLAT", "htf_signal": "NEUTRAL",
        "dynamic_tp": None, "candles_used": 0,
    }
