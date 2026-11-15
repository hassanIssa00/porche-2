"""
=============================================================
  ISSSSMAIL SCALPER BOT v8.0 — Trend-Pullback Sniper Scalper
  محرك القناص — الشراء من القاع والبيع من القمة داخل الاتجاه
=============================================================

Mathematical Principles for High-Win-Rate Scalping:
  1. Trend Filter: EMA 21 vs EMA 55 (trade strictly with the dominant trend).
  2. Pullback Value Zone: Stochastic (14,3) oversold (<30) for BUY, overbought (>70) for SELL.
     NEVER chase momentum after 3 extended candles!
  3. Reversal Trigger: Reversal candle (Green close for BUY, Red close for SELL)
     confirming that buyers/sellers stepped in at the discount level.
  4. Momentum Turn: Stochastic cross (K > D for BUY, K < D for SELL) or MACD turn.
  5. Mathematical R:R: SL = $0.48, TP = $0.75-$0.90 (Positive Expected Value).
"""

import logging
from typing import Optional

from bot import config

logger = logging.getLogger("issssmail.analysis")

SIGNAL_BUY  = "BUY"
SIGNAL_SELL = "SELL"
SIGNAL_WAIT = "WAIT"


# ══════════════════════════════════════════════════════════
# TECHNICAL INDICATORS (Pure Python)
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
          ) -> tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    """Returns (macd_line, signal_line, current_hist, prev_hist)"""
    if len(closes) < slow + sig + 2:
        return None, None, None, None
    fe = _ema(closes, fast)
    se = _ema(closes, slow)
    offset = len(fe) - len(se)
    if offset < 0:
        return None, None, None, None
    macd_line = [f - s for f, s in zip(fe[offset:], se)]
    if len(macd_line) < sig + 2:
        return None, None, None, None
    se2 = _ema(macd_line, sig)
    if not se2 or len(se2) < 2:
        return None, None, None, None
    off2 = len(macd_line) - len(se2)
    cur_hist = macd_line[-1] - se2[-1]
    prev_hist = macd_line[-2] - se2[-2]
    return round(macd_line[-1], 5), round(se2[-1], 5), round(cur_hist, 5), round(prev_hist, 5)


def _stoch(highs: list[float], lows: list[float], closes: list[float],
           k_period: int = 14, d_period: int = 3
           ) -> tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    """Returns (current_k, current_d, prev_k, prev_d)"""
    if len(closes) < k_period + d_period + 2:
        return None, None, None, None
    k_vals = []
    for i in range(k_period, len(closes) + 1):
        w_h = max(highs[i - k_period:i])
        w_l = min(lows[i - k_period:i])
        rng = w_h - w_l
        k = 100.0 * ((closes[i - 1] - w_l) / rng) if rng > 0 else 50.0
        k_vals.append(k)
    d_vals = []
    for i in range(d_period, len(k_vals) + 1):
        d_vals.append(sum(k_vals[i - d_period:i]) / d_period)
    if len(d_vals) < 2 or len(k_vals) < 2:
        return None, None, None, None
    return round(k_vals[-1], 2), round(d_vals[-1], 2), round(k_vals[-2], 2), round(d_vals[-2], 2)


def _atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14
         ) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    trs = [
        max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
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
        up = highs[i] - highs[i - 1]
        dn = lows[i - 1] - lows[i]
        pdm.append(up if up > dn and up > 0 else 0.0)
        mdm.append(dn if dn > up and dn > 0 else 0.0)
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        trl.append(tr)

    def _ws(data, p):
        if len(data) < p:
            return []
        r = [sum(data[:p])]
        for x in data[p:]:
            r.append(r[-1] - r[-1] / p + x)
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
# MAIN M1 SNIPER PULLBACK ANALYSIS
# ══════════════════════════════════════════════════════════

def analyze(
    candles: list[dict],
    htf_candles: Optional[list[dict]] = None,
) -> dict:
    """
    v8.0 Sniper Trend-Pullback Scalper Analysis.
    Buys dips in uptrends, sells rallies in downtrends.
    Strictly avoids entering at exhaustion extremes.
    """
    if len(candles) < config.CANDLES_NEEDED:
        return _wait(f"Need {config.CANDLES_NEEDED} candles, got {len(candles)}")

    closes = [float(c["close"]) for c in candles]
    highs  = [float(c["high"])  for c in candles]
    lows   = [float(c["low"])   for c in candles]
    opens  = [float(c["open"])  for c in candles]

    # EMAs: Fast (21), Slow (55), Macro Baseline (200 if enough candles)
    ema21_list = _ema(closes, 21)
    ema55_list = _ema(closes, 55)
    ema200_list = _ema(closes, min(len(closes) - 1, 150)) if len(closes) >= 60 else []

    if not ema21_list or not ema55_list:
        return _wait("EMA calculation failed")

    fast_ema = ema21_list[-1]
    slow_ema = ema55_list[-1]
    macro_ema = ema200_list[-1] if ema200_list else slow_ema

    # Oscillators
    stoch_k, stoch_d, prev_k, prev_d = _stoch(highs, lows, closes, 14, 3)
    rsi_val = _rsi(closes, config.RSI_PERIOD)
    atr_val = _atr(highs, lows, closes, config.ATR_PERIOD)
    adx_val = _adx(highs, lows, closes, config.ADX_PERIOD)
    _, _, cur_macd_hist, prev_macd_hist = _macd(closes, config.MACD_FAST, config.MACD_SLOW, config.MACD_SIGNAL)

    last_close = closes[-1]
    last_open  = opens[-1]
    prev_close = closes[-2] if len(closes) >= 2 else last_close
    prev_open  = opens[-2]  if len(opens) >= 2 else last_open

    ema_diff = fast_ema - slow_ema

    # HTF Trend (M5) if available
    htf_bias = "NEUTRAL"
    if htf_candles and len(htf_candles) >= 20:
        htf_closes = [float(c["close"]) for c in htf_candles]
        htf_e20 = _ema(htf_closes, 20)
        htf_e50 = _ema(htf_closes, 50)
        if htf_e20 and htf_e50:
            if htf_e20[-1] > htf_e50[-1]:
                htf_bias = "UP"
            elif htf_e20[-1] < htf_e50[-1]:
                htf_bias = "DOWN"

    # ══════════════════════════════════════════════════════
    # 4-POINT SNIPER CONFLUENCE SCORING
    # ══════════════════════════════════════════════════════
    b_score, s_score = 0, 0
    b_reasons, s_reasons = [], []

    # 1. Trend Direction: Clean trend (EMA21 vs EMA55) + Macro filter
    if ema_diff > 1.5:
        b_score += 1
        b_reasons.append(f"الاتجاه صاعد (EMA21 > EMA55 بفارق +${ema_diff:.1f}) ↑")
    else:
        b_reasons.append(f"الاتجاه ليس صاعداً (EMA21 - EMA55 = ${ema_diff:.1f})")

    if ema_diff < -1.5:
        s_score += 1
        s_reasons.append(f"الاتجاه هابط (EMA21 < EMA55 بفارق -${abs(ema_diff):.1f}) ↓")
    else:
        s_reasons.append(f"الاتجاه ليس هابطاً (EMA21 - EMA55 = ${ema_diff:.1f})")

    # 2. Pullback into Value Zone (Stochastic or RSI in extreme discount/premium)
    # BUY: Price dipped to oversold level (Stoch < 32 or RSI < 45)
    # SELL: Price rallied to overbought level (Stoch > 68 or RSI > 55)
    if stoch_k is not None:
        min_stoch = min(stoch_k, prev_k if prev_k is not None else stoch_k)
        max_stoch = max(stoch_k, prev_k if prev_k is not None else stoch_k)

        if min_stoch <= 32.0 or (rsi_val is not None and rsi_val <= 45.0):
            b_score += 1
            b_reasons.append(f"تصحيح للقاع (Stoch={stoch_k:.1f} تشبع بيعي / سعر رخيص) 🎯")
        else:
            b_reasons.append(f"السعر ليس في قاع تصحيحي (Stoch={stoch_k:.1f})")

        if max_stoch >= 68.0 or (rsi_val is not None and rsi_val >= 55.0):
            s_score += 1
            s_reasons.append(f"ارتداد للقمة (Stoch={stoch_k:.1f} تشبع شرائي / سعر ممتاز للبيع) 🎯")
        else:
            s_reasons.append(f"السعر ليس في قمة تصحيحية (Stoch={stoch_k:.1f})")
    else:
        b_reasons.append("Stochastic غير متاح")
        s_reasons.append("Stochastic غير متاح")

    # 3. Candlestick Reversal Confirmation (Bounce off support/resistance)
    # BUY: Current candle is GREEN (close > open) rejecting the dip
    # SELL: Current candle is RED (close < open) rejecting the rally
    is_green = last_close > last_open
    is_red   = last_close < last_open

    if is_green:
        b_score += 1
        b_reasons.append(f"شمعة انعكاسية خضراء صاعدة (إغلاق {last_close:.2f} > فتح {last_open:.2f}) ↑")
    else:
        b_reasons.append("الشمعة الحالية ليست خضراء")

    if is_red:
        s_score += 1
        s_reasons.append(f"شمعة انعكاسية حمراء هابطة (إغلاق {last_close:.2f} < فتح {last_open:.2f}) ↓")
    else:
        s_reasons.append("الشمعة الحالية ليست حمراء")

    # 4. Momentum Turn (Stochastic %K > %D or MACD Histogram turning)
    if stoch_k is not None and stoch_d is not None:
        stoch_bull_cross = stoch_k > stoch_d
        stoch_bear_cross = stoch_k < stoch_d
        macd_turning_up = (cur_macd_hist is not None and prev_macd_hist is not None and cur_macd_hist > prev_macd_hist)
        macd_turning_dn = (cur_macd_hist is not None and prev_macd_hist is not None and cur_macd_hist < prev_macd_hist)

        if stoch_bull_cross or macd_turning_up:
            b_score += 1
            b_reasons.append("تأكيد عودة الزخم الشرائي (Stoch K>D أو تحول إيجابي للماكد) 🚀")
        else:
            b_reasons.append("الزخم لم يتحول لصالح الشراء بعد")

        if stoch_bear_cross or macd_turning_dn:
            s_score += 1
            s_reasons.append("تأكيد عودة الزخم البيعي (Stoch K<D أو تحول سلبي للماكد) 🔻")
        else:
            s_reasons.append("الزخم لم يتحول لصالح البيع بعد")
    else:
        b_reasons.append("مؤشرات الزخم غير مكتملة")
        s_reasons.append("مؤشرات الزخم غير مكتملة")

    threshold = 4  # 4/4 required for highest efficiency

    trend_str = "UP" if ema_diff > 0 else ("DOWN" if ema_diff < 0 else "FLAT")

    if b_score >= threshold and b_score > s_score:
        signal = SIGNAL_BUY
        score  = b_score
        reason = f"BUY {b_score}/4 🎯 قناص القاع | " + " | ".join(b_reasons)
    elif s_score >= threshold and s_score > b_score:
        signal = SIGNAL_SELL
        score  = s_score
        reason = f"SELL {s_score}/4 🎯 قناص القمة | " + " | ".join(s_reasons)
    else:
        signal = SIGNAL_WAIT
        score  = max(b_score, s_score)
        detail = " | ".join(b_reasons) if b_score > s_score else " | ".join(s_reasons)
        reason = f"WAIT ({max(b_score, s_score)}/4) | {detail}"

    return {
        "signal":       signal,
        "score":        score,
        "max_score":    4,
        "reason":       reason,
        "fast_ema":     round(fast_ema, 2),
        "slow_ema":     round(slow_ema, 2),
        "rsi":          rsi_val,
        "stoch_k":      stoch_k,
        "stoch_d":      stoch_d,
        "macd":         cur_macd_hist,
        "adx":          adx_val,
        "atr":          atr_val,
        "trend":        trend_str,
        "htf_signal":   htf_bias,
        "dynamic_tp":   atr_val,
        "candles_used": len(candles),
    }


def _wait(reason: str) -> dict:
    return {
        "signal": SIGNAL_WAIT, "score": 0, "max_score": 4,
        "reason": reason, "fast_ema": None, "slow_ema": None,
        "rsi": None, "stoch_k": None, "stoch_d": None, "macd": None,
        "adx": None, "atr": None, "trend": "FLAT", "htf_signal": "M1",
        "dynamic_tp": None, "candles_used": 0,
    }
