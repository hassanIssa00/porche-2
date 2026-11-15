"""
=============================================================
  ISSSSMAIL SCALPER BOT v5.5 — High-Quality M1 Analysis
  محرك التحليل الفني — سكالبينج منضبط عالي الدقة على فريم M1
=============================================================

Rules for Profitable Scalping:
  1. Direction: Clean EMA 7 / EMA 20 divergence (no tangled lines).
  2. Candle Confirmation: Green candle for BUY, Red candle for SELL.
  3. RSI Momentum: Active zone, avoiding tops (>72) and bottoms (<28).
  4. Both BUY and SELL supported with zero directional bias.
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
# MAIN M1 SCALPING ANALYSIS
# ══════════════════════════════════════════════════════════

def analyze(
    candles: list[dict],
    htf_candles: Optional[list[dict]] = None,
) -> dict:
    """
    High-Quality M1 Scalping Analysis.
    3-point confluence with strict candle & EMA divergence checks.
    """
    if len(candles) < config.CANDLES_NEEDED:
        return _wait(f"Need {config.CANDLES_NEEDED} candles, got {len(candles)}")

    closes = [float(c["close"]) for c in candles]
    highs  = [float(c["high"])  for c in candles]
    lows   = [float(c["low"])   for c in candles]
    opens  = [float(c["open"])  for c in candles]

    # Indicators on M1
    fast_ema_list = _ema(closes, config.TREND_FAST_EMA)   # EMA 7
    slow_ema_list = _ema(closes, config.TREND_SLOW_EMA)   # EMA 20
    if not fast_ema_list or not slow_ema_list:
        return _wait("EMA calculation failed")

    fast_ema = fast_ema_list[-1]
    slow_ema = slow_ema_list[-1]

    rsi_val  = _rsi(closes, config.RSI_PERIOD)
    atr_val  = _atr(highs, lows, closes, config.ATR_PERIOD)
    adx_val  = _adx(highs, lows, closes, config.ADX_PERIOD)
    _, _, macd_hist = _macd(closes, config.MACD_FAST, config.MACD_SLOW, config.MACD_SIGNAL)

    last_close = closes[-1]
    last_open  = opens[-1]
    ema_diff   = fast_ema - slow_ema
    min_diff   = getattr(config, "MIN_EMA_DIFF", 4.0)

    # ══════════════════════════════════════════════════════
    # 3-POINT CONFLUENCE SCORING
    # ══════════════════════════════════════════════════════
    b_score, s_score = 0, 0
    b_reasons, s_reasons = [], []

    # 1. EMA Divergence (avoid flat chop)
    if ema_diff >= min_diff:
        b_score += 1
        b_reasons.append(f"M1 EMA7({fast_ema:.1f}) > EMA20(+${ema_diff:.1f}) ↑")
    elif ema_diff <= -min_diff:
        s_score += 1
        s_reasons.append(f"M1 EMA7({fast_ema:.1f}) < EMA20(-${abs(ema_diff):.1f}) ↓")
    else:
        b_reasons.append(f"EMA متقاربة (${abs(ema_diff):.1f} < ${min_diff:.1f})")
        s_reasons.append(f"EMA متقاربة (${abs(ema_diff):.1f} < ${min_diff:.1f})")

    # 2. Candle Confirmation (green candle closing above EMA7 for BUY, red closing below EMA7 for SELL)
    if last_close > last_open and last_close >= fast_ema:
        b_score += 1
        b_reasons.append("Bullish Green Candle close above EMA7 ↑")
    elif last_close < last_open and last_close <= fast_ema:
        s_score += 1
        s_reasons.append("Bearish Red Candle close below EMA7 ↓")
    else:
        b_reasons.append("شمعة محايدة أو غير متوافقة")
        s_reasons.append("شمعة محايدة أو غير متوافقة")

    # 3. RSI Active Momentum Zone
    if rsi_val is not None:
        if 48.0 <= rsi_val <= 72.0:
            b_score += 1
            b_reasons.append(f"RSI={rsi_val} (bullish zone)")
        elif 28.0 <= rsi_val <= 52.0:
            s_score += 1
            s_reasons.append(f"RSI={rsi_val} (bearish zone)")
        else:
            b_reasons.append(f"RSI={rsi_val} (منطقة ذروة)")
            s_reasons.append(f"RSI={rsi_val} (منطقة ذروة)")

    # 4. MACD Direction (Bonus info)
    if macd_hist is not None:
        if macd_hist > 0:
            b_reasons.append(f"MACD +{macd_hist:.2f}")
        elif macd_hist < 0:
            s_reasons.append(f"MACD {macd_hist:.2f}")

    threshold = config.MIN_SIGNAL_SCORE  # = 3

    trend_str = "UP" if ema_diff > 0 else ("DOWN" if ema_diff < 0 else "FLAT")

    if b_score >= threshold and b_score > s_score:
        signal = SIGNAL_BUY
        score  = b_score
        reason = f"BUY {b_score}/3 🚀 | " + " | ".join(b_reasons)
    elif s_score >= threshold and s_score > b_score:
        signal = SIGNAL_SELL
        score  = s_score
        reason = f"SELL {s_score}/3 🔻 | " + " | ".join(s_reasons)
    else:
        signal = SIGNAL_WAIT
        score  = max(b_score, s_score)
        detail = " | ".join(b_reasons) if b_score > s_score else " | ".join(s_reasons)
        reason = f"WAIT ({max(b_score, s_score)}/3) | {detail}"

    return {
        "signal":       signal,
        "score":        score,
        "max_score":    3,
        "reason":       reason,
        "fast_ema":     round(fast_ema, 2),
        "slow_ema":     round(slow_ema, 2),
        "rsi":          rsi_val,
        "macd":         macd_hist,
        "adx":          adx_val,
        "atr":          atr_val,
        "trend":        trend_str,
        "htf_signal":   "M1",
        "dynamic_tp":   atr_val,
        "candles_used": len(candles),
    }


def _wait(reason: str) -> dict:
    return {
        "signal": SIGNAL_WAIT, "score": 0, "max_score": 3,
        "reason": reason, "fast_ema": None, "slow_ema": None,
        "rsi": None, "macd": None, "adx": None, "atr": None,
        "trend": "FLAT", "htf_signal": "M1",
        "dynamic_tp": None, "candles_used": 0,
    }
