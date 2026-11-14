"""
=============================================================
  ISSSSMAIL SCALPER BOT v3.0 — Analysis Engine
  محرك التحليل الفني المتقدم — استراتيجية بولباك الاتجاه
=============================================================

Professional Trend-Pullback Confluence System:
  1. Macro Trend: M15 EMA 20 vs EMA 50
  2. Micro Trend: M5 EMA 20 vs EMA 50
  3. Pullback Check: Price near EMA 20 (not overextended)
  4. Candle Reversal: Bullish/Bearish confirmation candle
  5. RSI Momentum: Healthy zone (no buying into overbought)
  6. MACD Confirmation: Momentum expanding in trend direction
"""

import math
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
    """Exponential Moving Average."""
    if len(closes) < period:
        return []
    k = 2.0 / (period + 1)
    seed = sum(closes[:period]) / period
    result = [seed]
    for price in closes[period:]:
        result.append(price * k + result[-1] * (1 - k))
    return result


def _rsi(closes: list[float], period: int = 14) -> Optional[float]:
    """Relative Strength Index."""
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
    """MACD line, signal line, histogram."""
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
    """Average True Range (volatility)."""
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
    """Average Directional Index (trend strength)."""
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
# MAIN ANALYSIS LOGIC
# ══════════════════════════════════════════════════════════

def analyze(
    candles: list[dict],
    htf_candles: Optional[list[dict]] = None,
) -> dict:
    """
    Perform professional trend-pullback confluence analysis.
    Returns signal (BUY / SELL / WAIT) with score and indicators.
    """
    if len(candles) < config.CANDLES_NEEDED:
        return _wait(f"Need {config.CANDLES_NEEDED} candles, got {len(candles)}")

    closes = [float(c["close"]) for c in candles]
    highs  = [float(c["high"])  for c in candles]
    lows   = [float(c["low"])   for c in candles]
    opens  = [float(c["open"])  for c in candles]

    # Calculate indicators on M5
    fast_ema_list = _ema(closes, config.TREND_FAST_EMA)
    slow_ema_list = _ema(closes, config.TREND_SLOW_EMA)
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

    # Macro trend from M15
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

    # Confluence Scoring (0 to 6 points)
    b_score, s_score = 0, 0
    b_reasons, s_reasons = [], []

    # 1. M5 EMA trend
    if fast_ema > slow_ema:
        b_score += 1
        b_reasons.append("M5 EMA20>EMA50 ↑")
    elif fast_ema < slow_ema:
        s_score += 1
        s_reasons.append("M5 EMA20<EMA50 ↓")

    # 2. M15 Higher Timeframe alignment
    if htf_signal == SIGNAL_BUY:
        b_score += 1
        b_reasons.append("M15 Trend: BULLISH ✓")
    elif htf_signal == SIGNAL_SELL:
        s_score += 1
        s_reasons.append("M15 Trend: BEARISH ✓")

    # 3. Pullback / Value Check (price not overextended from EMA20)
    # Distance from EMA20 should be <= 1.5 ATR
    if atr_val and atr_val > 0:
        dist = abs(last_close - fast_ema)
        if dist <= 1.5 * atr_val:
            b_score += 1
            s_score += 1
            b_reasons.append("Healthy pullback (not overextended)")
            s_reasons.append("Healthy pullback (not overextended)")
        else:
            b_reasons.append("Price extended from EMA20")
            s_reasons.append("Price extended from EMA20")

    # 4. Candlestick Confirmation
    if last_close > last_open and last_close >= fast_ema:
        b_score += 1
        b_reasons.append("Bullish candle close above EMA20")
    elif last_close < last_open and last_close <= fast_ema:
        s_score += 1
        s_reasons.append("Bearish candle close below EMA20")

    # 5. RSI Momentum in healthy zone
    if rsi_val is not None:
        if 45.0 <= rsi_val <= 68.0:
            b_score += 1
            b_reasons.append(f"RSI={rsi_val} (bullish zone)")
        if 32.0 <= rsi_val <= 55.0:
            s_score += 1
            s_reasons.append(f"RSI={rsi_val} (bearish zone)")

    # 6. MACD Histogram confirmation
    if macd_hist is not None:
        if macd_hist > 0:
            b_score += 1
            b_reasons.append(f"MACD+{macd_hist:.4f}")
        elif macd_hist < 0:
            s_score += 1
            s_reasons.append(f"MACD{macd_hist:.4f}")

    # ── HARD FILTER 1: Macro HTF Trend Alignment ────────────
    # In Bitcoin, NEVER enter counter-trend against M15!
    if htf_signal == SIGNAL_SELL:
        b_score = 0
        b_reasons = ["Blocked by M15 Macro Downtrend"]
    elif htf_signal == SIGNAL_BUY:
        s_score = 0
        s_reasons = ["Blocked by M15 Macro Uptrend"]

    trend_str = "UP" if fast_ema > slow_ema else ("DOWN" if fast_ema < slow_ema else "FLAT")

    # ── HARD FILTER 2: Chop / Consolidation Guard (ADX) ────
    # If ADX is weak, the market is in a choppy flat range — DO NOT TRADE
    min_adx = getattr(config, "ADX_MIN", 18.0)
    if adx_val is not None and adx_val < min_adx:
        return {
            "signal":       SIGNAL_WAIT,
            "score":        max(b_score, s_score),
            "max_score":    6,
            "reason":       f"WAIT — فلتر التذبذب: السوق متذبذب بدون اتجاه واضح (ADX={adx_val:.1f} < {min_adx})",
            "fast_ema":     round(fast_ema, 5),
            "slow_ema":     round(slow_ema, 5),
            "rsi":          rsi_val,
            "macd":         macd_hist,
            "adx":          adx_val,
            "atr":          atr_val,
            "trend":        trend_str,
            "htf_signal":   htf_signal,
            "candles_used": len(candles),
        }

    threshold = config.MIN_SIGNAL_SCORE

    if b_score >= threshold and b_score > s_score:
        signal = SIGNAL_BUY
        score = b_score
        reason = f"BUY {b_score}/6 | " + " | ".join(b_reasons)
    elif s_score >= threshold and s_score > b_score:
        signal = SIGNAL_SELL
        score = s_score
        reason = f"SELL {s_score}/6 | " + " | ".join(s_reasons)
    else:
        signal = SIGNAL_WAIT
        score = max(b_score, s_score)
        reason = f"WAIT — BUY:{b_score}/6 SELL:{s_score}/6 (need ≥{threshold}/6)"

    return {
        "signal":       signal,
        "score":        score,
        "max_score":    6,
        "reason":       reason,
        "fast_ema":     round(fast_ema, 5),
        "slow_ema":     round(slow_ema, 5),
        "rsi":          rsi_val,
        "macd":         macd_hist,
        "adx":          adx_val,
        "atr":          atr_val,
        "trend":        trend_str,
        "htf_signal":   htf_signal,
        "candles_used": len(candles),
    }


def _wait(reason: str) -> dict:
    return {
        "signal":       SIGNAL_WAIT,
        "score":        0,
        "max_score":    6,
        "reason":       reason,
        "fast_ema":     None,
        "slow_ema":     None,
        "rsi":          None,
        "macd":         None,
        "adx":          None,
        "atr":          None,
        "trend":        "FLAT",
        "htf_signal":   SIGNAL_WAIT,
        "candles_used": 0,
    }
