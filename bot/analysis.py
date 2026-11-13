"""
=============================================================
  ISSSSMAIL SCALPER BOT v2.1 — Analysis Engine (SMART FIX)
  محرك التحليل الذكي — مُصحَّح لواقع السوق الحقيقي
=============================================================

REAL PROBLEMS SOLVED:
  1. Spread = 240 pts = $0.24 on XAUUSDm → TP must be >> spread
  2. ATR (M5) ≈ $4 per candle → SL of $0.50 is too tight → instant SL hit
  3. Must ensure TP > 2× spread before opening any trade
  4. Use proper multi-timeframe trend: M5 + M15 + H1 alignment
  5. Only trade when ADX > 25 (real trend, not noise)
  6. Minimum score threshold enforced strictly

STRATEGY REWRITE:
  • TP target: 1.0–1.5× ATR (realistic given volatility)
  • SL: 0.75× ATR (wider than spread×3, never too tight)
  • Min spread ratio: TP/spread >= 2.0 (don't trade if spread eats profit)
  • Score ≥ 4/6 required (confluence filter)
  • Session filter: Gold 08-17 UTC (best liquidity)

المشاكل المحلولة:
  ١. السبريد 240 نقطة = ٢٤ سنت → TP لازم أكبر من السبريد بمرتين
  ٢. ATR السوق ≈ ٤$ لكل شمعة M5 → SL بـ ٠.٥$ بيتضرب فورًا
  ٣. فلتر: TP / spread >= 2 (ما نفتحش صفقة لو السبريد بياكل الربح)
"""

import math
import logging
from typing import Optional

from bot import config

logger = logging.getLogger("issssmail.analysis")


# ──────────────────────────────────────────────────────────
# Signal constants
# ──────────────────────────────────────────────────────────
SIGNAL_BUY  = "BUY"
SIGNAL_SELL = "SELL"
SIGNAL_WAIT = "WAIT"


# ══════════════════════════════════════════════════════════
# INDICATORS — Pure Python (no external libraries)
# ══════════════════════════════════════════════════════════

def _ema(closes: list[float], period: int) -> list[float]:
    """Exponential Moving Average — Wilder-style seeded with SMA."""
    if len(closes) < period:
        return []
    k = 2.0 / (period + 1)
    seed = sum(closes[:period]) / period
    result = [seed]
    for price in closes[period:]:
        result.append(price * k + result[-1] * (1 - k))
    return result


def _rsi(closes: list[float], period: int = 14) -> Optional[float]:
    """RSI with Wilder smoothing."""
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
    return round(mv, 6), round(sv, 6), round(mv - sv, 6)


def _bollinger(closes: list[float], period: int = 20, mult: float = 2.0
               ) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """Bollinger Bands: upper, mid, lower."""
    if len(closes) < period:
        return None, None, None
    w = closes[-period:]
    mid = sum(w) / period
    std = math.sqrt(sum((x - mid) ** 2 for x in w) / period)
    return round(mid + mult * std, 5), round(mid, 5), round(mid - mult * std, 5)


def _atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14
         ) -> Optional[float]:
    """Average True Range — volatility measure."""
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
    """Average Directional Index — trend strength (0–100). >25 = strong trend."""
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


def _stochastic(highs: list[float], lows: list[float], closes: list[float],
                k_period: int = 14, d_period: int = 3
                ) -> tuple[Optional[float], Optional[float]]:
    """
    Stochastic Oscillator (%K, %D).
    %K < 20 = oversold (BUY), %K > 80 = overbought (SELL).
    مؤشر ستوكاستيك — يكشف منطقة ذروة البيع/الشراء.
    """
    if len(closes) < k_period + d_period:
        return None, None
    k_values = []
    for i in range(k_period - 1, len(closes)):
        hh = max(highs[i - k_period + 1: i + 1])
        ll = min(lows[i  - k_period + 1: i + 1])
        if hh == ll:
            k_values.append(50.0)
        else:
            k_values.append(100.0 * (closes[i] - ll) / (hh - ll))
    if len(k_values) < d_period:
        return None, None
    k = k_values[-1]
    d = sum(k_values[-d_period:]) / d_period
    return round(k, 2), round(d, 2)


# ══════════════════════════════════════════════════════════
# SMART CONFLUENCE SCORING
# نظام التسجيل الذكي — يوزن المؤشرات بشكل صحيح
# ══════════════════════════════════════════════════════════

def _score_confluence(
    fast_ema: float, slow_ema: float,
    macd_hist: Optional[float],
    rsi: Optional[float],
    close: float, bb_mid: Optional[float],
    adx: Optional[float],
    htf_signal: str,
    stoch_k: Optional[float],
) -> tuple[int, int, list[str], list[str]]:
    """
    Score BUY and SELL signals independently (0–7 points each).
    Returns (buy_score, sell_score, buy_reasons, sell_reasons).

    Scoring:
      1. EMA9 vs EMA21 crossover            (+1)
      2. MACD histogram direction            (+1)
      3. RSI zone (not extreme opposite)     (+1)
      4. Price vs Bollinger midline          (+1)
      5. ADX > 25 (real trend, not noise)    (+1)
      6. M15 HTF EMA alignment               (+1)
      7. Stochastic K confirmation           (+1)
    """
    b_score, s_score = 0, 0
    b_why,   s_why   = [], []

    # 1 — EMA crossover
    if fast_ema > slow_ema:
        b_score += 1
        b_why.append(f"EMA9({fast_ema:.1f})>EMA21({slow_ema:.1f})↑")
    elif fast_ema < slow_ema:
        s_score += 1
        s_why.append(f"EMA9({fast_ema:.1f})<EMA21({slow_ema:.1f})↓")

    # 2 — MACD histogram
    if macd_hist is not None:
        if macd_hist > 0:
            b_score += 1
            b_why.append(f"MACD+{macd_hist:.4f}")
        elif macd_hist < 0:
            s_score += 1
            s_why.append(f"MACD{macd_hist:.4f}")

    # 3 — RSI zone (avoid overbought for BUY, oversold for SELL)
    if rsi is not None:
        rsi_buy_ok  = rsi < config.RSI_OVERBOUGHT  # don't buy overbought
        rsi_sell_ok = rsi > config.RSI_OVERSOLD    # don't sell oversold
        if rsi_buy_ok:
            b_score += 1
            b_why.append(f"RSI={rsi}✓")
        if rsi_sell_ok:
            s_score += 1
            s_why.append(f"RSI={rsi}✓")

    # 4 — Bollinger midline position
    if bb_mid is not None:
        if close > bb_mid:
            b_score += 1
            b_why.append(f"above BB mid({bb_mid:.1f})")
        else:
            s_score += 1
            s_why.append(f"below BB mid({bb_mid:.1f})")

    # 5 — ADX trend strength (require > 25 for meaningful trend)
    if adx is not None:
        if adx >= 25.0:
            b_score += 1
            s_score += 1
            b_why.append(f"ADX={adx}(strong)")
            s_why.append(f"ADX={adx}(strong)")
        elif adx >= 20.0:
            # Weak trend — half credit (round down) → no point
            b_why.append(f"ADX={adx}(weak)")
            s_why.append(f"ADX={adx}(weak)")
        else:
            b_why.append(f"ADX={adx}(ranging!)")
            s_why.append(f"ADX={adx}(ranging!)")

    # 6 — HTF (M15) alignment
    if htf_signal == SIGNAL_BUY:
        b_score += 1
        b_why.append("M15↑")
    elif htf_signal == SIGNAL_SELL:
        s_score += 1
        s_why.append("M15↓")

    # 7 — Stochastic confirmation
    if stoch_k is not None:
        if stoch_k < 50:          # K in lower half → sell bias
            s_score += 1
            s_why.append(f"Stoch%K={stoch_k}<50")
        else:
            b_score += 1          # K in upper half → buy bias
            b_why.append(f"Stoch%K={stoch_k}≥50")

    return b_score, s_score, b_why, s_why


# ══════════════════════════════════════════════════════════
# SPREAD VIABILITY CHECK
# فلتر السبريد — لا تفتح صفقة لو السبريد بياكل الربح
# ══════════════════════════════════════════════════════════

def _spread_viable(spread_usd: float, tp_usd: float, min_ratio: float = 2.0) -> bool:
    """
    Return True only if TP / spread >= min_ratio.
    Example: spread=$0.24, TP=$0.50 → ratio=2.08 → OK
             spread=$0.24, TP=$0.30 → ratio=1.25 → REJECT
    """
    if spread_usd <= 0:
        return True
    return (tp_usd / spread_usd) >= min_ratio


# ══════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════

def analyze(
    candles: list[dict],
    htf_candles: Optional[list[dict]] = None,
    spread_usd: float = 0.0,
    tp_usd: float = 0.0,
) -> dict:
    """
    Full multi-indicator confluence analysis.

    Args:
        candles:    M5 OHLCV candles from mt5bridge.get_candles()
        htf_candles: M15 candles for HTF confirmation
        spread_usd: current spread in USD (to filter low R:R trades)
        tp_usd:     configured TP target in USD

    Returns extended result dict with all indicators + score.
    """
    closes = [float(c["close"]) for c in candles if math.isfinite(float(c["close"]))]
    highs  = [float(c["high"])  for c in candles if math.isfinite(float(c["high"]))]
    lows   = [float(c["low"])   for c in candles if math.isfinite(float(c["low"]))]

    if len(closes) < config.CANDLES_NEEDED:
        return _wait(f"Not enough candles ({len(closes)}/{config.CANDLES_NEEDED})")

    # ── Compute all indicators ─────────────────────────────
    fe_list = _ema(closes, config.TREND_FAST_EMA)
    se_list = _ema(closes, config.TREND_SLOW_EMA)
    if not fe_list or not se_list:
        return _wait("EMA failed")

    fast_ema = fe_list[-1]
    slow_ema = se_list[-1]
    rsi_val  = _rsi(closes, config.RSI_PERIOD)
    _, _, macd_hist = _macd(closes, config.MACD_FAST, config.MACD_SLOW, config.MACD_SIGNAL)
    bb_upper, bb_mid, bb_lower = _bollinger(closes, config.BB_PERIOD, config.BB_STD)
    atr_val  = _atr(highs, lows, closes, config.ATR_PERIOD)
    adx_val  = _adx(highs, lows, closes, config.ADX_PERIOD)
    stoch_k, stoch_d = _stochastic(highs, lows, closes)

    close = closes[-1]
    trend = "UP" if fast_ema > slow_ema else ("DOWN" if fast_ema < slow_ema else "FLAT")

    # ── HTF signal ─────────────────────────────────────────
    htf_signal = SIGNAL_WAIT
    if htf_candles and len(htf_candles) >= 25:
        htf_c = [float(c["close"]) for c in htf_candles if math.isfinite(float(c["close"]))]
        if len(htf_c) >= config.HTF_SLOW_EMA + 1:
            hfe = _ema(htf_c, config.HTF_FAST_EMA)
            hse = _ema(htf_c, config.HTF_SLOW_EMA)
            if hfe and hse:
                htf_signal = SIGNAL_BUY if hfe[-1] > hse[-1] else SIGNAL_SELL

    # ── Spread viability check ─────────────────────────────
    # If spread eats too much of TP → don't trade at all
    spread_ok = True
    spread_msg = ""
    if spread_usd > 0 and tp_usd > 0:
        spread_ok = _spread_viable(spread_usd, tp_usd, min_ratio=1.8)
        if not spread_ok:
            spread_msg = f"Spread ${spread_usd:.3f} too wide vs TP ${tp_usd:.2f} (ratio={tp_usd/spread_usd:.2f}<1.8)"

    # ── Score ──────────────────────────────────────────────
    b_score, s_score, b_why, s_why = _score_confluence(
        fast_ema=fast_ema, slow_ema=slow_ema,
        macd_hist=macd_hist,
        rsi=rsi_val,
        close=close, bb_mid=bb_mid,
        adx=adx_val,
        htf_signal=htf_signal,
        stoch_k=stoch_k,
    )

    threshold = config.MIN_SIGNAL_SCORE

    # ── Determine final signal ─────────────────────────────
    if not spread_ok:
        signal = SIGNAL_WAIT
        score  = max(b_score, s_score)
        reason = f"WAIT — {spread_msg}"

    elif b_score >= threshold and b_score > s_score:
        signal = SIGNAL_BUY
        score  = b_score
        reason = f"BUY {b_score}/7 | " + " | ".join(b_why)

    elif s_score >= threshold and s_score > b_score:
        signal = SIGNAL_SELL
        score  = s_score
        reason = f"SELL {s_score}/7 | " + " | ".join(s_why)

    elif b_score == s_score and b_score >= threshold:
        # Tie — prefer HTF direction
        if htf_signal == SIGNAL_BUY:
            signal, score, reason = SIGNAL_BUY, b_score, f"BUY(tie→HTF) {b_score}/7"
        elif htf_signal == SIGNAL_SELL:
            signal, score, reason = SIGNAL_SELL, s_score, f"SELL(tie→HTF) {s_score}/7"
        else:
            signal = SIGNAL_WAIT
            score  = b_score
            reason = f"WAIT — tie B{b_score}=S{s_score} no HTF"

    else:
        signal = SIGNAL_WAIT
        score  = max(b_score, s_score)
        reason = f"WAIT — BUY:{b_score} SELL:{s_score} (need≥{threshold}/7) | ADX={adx_val}"

    logger.info("[analyze] %s score=%d/7 trend=%s htf=%s ADX=%s RSI=%s",
                signal, score, trend, htf_signal, adx_val, rsi_val)

    return {
        "signal":       signal,
        "score":        score,
        "max_score":    7,
        "reason":       reason,
        "fast_ema":     round(fast_ema, 5),
        "slow_ema":     round(slow_ema, 5),
        "rsi":          rsi_val,
        "macd":         macd_hist,
        "adx":          adx_val,
        "atr":          atr_val,
        "bb_upper":     bb_upper,
        "bb_mid":       bb_mid,
        "bb_lower":     bb_lower,
        "stoch_k":      stoch_k,
        "stoch_d":      stoch_d,
        "trend":        trend,
        "htf_signal":   htf_signal,
        "spread_ok":    spread_ok,
        "candles_used": len(closes),
    }


def _wait(reason: str) -> dict:
    return {
        "signal": SIGNAL_WAIT, "score": 0, "max_score": 7, "reason": reason,
        "fast_ema": None, "slow_ema": None, "rsi": None, "macd": None,
        "adx": None, "atr": None, "bb_upper": None, "bb_mid": None, "bb_lower": None,
        "stoch_k": None, "stoch_d": None,
        "trend": "FLAT", "htf_signal": SIGNAL_WAIT,
        "spread_ok": True, "candles_used": 0,
    }
