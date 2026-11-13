"""
=============================================================
  ISSSSMAIL SCALPER BOT — Analysis Engine
  محرك التحليل الفني: EMA + RSI + Trend Detection
=============================================================

Reads candles from MT5 via direct import of mt5_utils,
calculates indicators, and returns a clear BUY/SELL/WAIT signal.
"""

import sys
import os
import math
import logging
from typing import Optional

# ── add MCP server dir to path so we can import mt5_utils ──
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from bot import config

logger = logging.getLogger("issssmail.analysis")


# ──────────────────────────────────────────────────────────
# Public signal constants
# ──────────────────────────────────────────────────────────
SIGNAL_BUY  = "BUY"
SIGNAL_SELL = "SELL"
SIGNAL_WAIT = "WAIT"


# ──────────────────────────────────────────────────────────
# EMA calculation (pure Python — no external libraries)
# حساب المتوسط المتحرك الأسي
# ──────────────────────────────────────────────────────────
def _ema(closes: list[float], period: int) -> list[float]:
    """Calculate EMA for a list of closing prices."""
    if len(closes) < period:
        return []
    k = 2.0 / (period + 1)
    result: list[float] = []
    # seed with simple average of first 'period' values
    seed = sum(closes[:period]) / period
    result.append(seed)
    for price in closes[period:]:
        result.append(price * k + result[-1] * (1 - k))
    return result


def _rsi(closes: list[float], period: int) -> Optional[float]:
    """Calculate the latest RSI value."""
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))

    if len(gains) < period:
        return None

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1 + rs)), 2)


# ──────────────────────────────────────────────────────────
# Main analysis function
# الدالة الرئيسية للتحليل
# ──────────────────────────────────────────────────────────
def analyze(candles: list[dict]) -> dict:
    """
    Analyze candle data and return a trading signal.

    Args:
        candles: list of OHLCV dicts from mt5_get_candles
                 each dict has keys: open, high, low, close, tick_volume

    Returns:
        {
            "signal":    "BUY" | "SELL" | "WAIT",
            "reason":    str,           # human-readable explanation
            "fast_ema":  float,
            "slow_ema":  float,
            "rsi":       float,
            "trend":     "UP" | "DOWN" | "FLAT",
            "candles_used": int
        }
    """
    closes = [float(c["close"]) for c in candles if math.isfinite(float(c["close"]))]

    if len(closes) < config.CANDLES_NEEDED:
        return _wait(f"Not enough candles ({len(closes)}/{config.CANDLES_NEEDED})")

    fast_ema_list = _ema(closes, config.TREND_FAST_EMA)
    slow_ema_list = _ema(closes, config.TREND_SLOW_EMA)
    rsi_val       = _rsi(closes, config.RSI_PERIOD)

    if not fast_ema_list or not slow_ema_list:
        return _wait("EMA calculation failed — not enough data")

    fast_ema = fast_ema_list[-1]
    slow_ema = slow_ema_list[-1]

    # ── Trend detection via EMA crossover ──────────────────
    ema_diff_pct = abs(fast_ema - slow_ema) / slow_ema * 100.0

    if fast_ema > slow_ema:
        trend = "UP"
    elif fast_ema < slow_ema:
        trend = "DOWN"
    else:
        trend = "FLAT"

    # ── RSI guard ──────────────────────────────────────────
    if rsi_val is None:
        rsi_ok_buy  = True   # no RSI data → allow
        rsi_ok_sell = True
    else:
        rsi_ok_buy  = rsi_val < config.RSI_OVERBOUGHT   # don't buy if overbought
        rsi_ok_sell = rsi_val > config.RSI_OVERSOLD      # don't sell if oversold

    # ── Signal logic ───────────────────────────────────────
    if trend == "UP" and rsi_ok_buy:
        signal = SIGNAL_BUY
        reason = (
            f"Uptrend confirmed: EMA{config.TREND_FAST_EMA}={fast_ema:.4f} > "
            f"EMA{config.TREND_SLOW_EMA}={slow_ema:.4f} | "
            f"RSI={rsi_val}"
        )
    elif trend == "DOWN" and rsi_ok_sell:
        signal = SIGNAL_SELL
        reason = (
            f"Downtrend confirmed: EMA{config.TREND_FAST_EMA}={fast_ema:.4f} < "
            f"EMA{config.TREND_SLOW_EMA}={slow_ema:.4f} | "
            f"RSI={rsi_val}"
        )
    else:
        signal = SIGNAL_WAIT
        reason = (
            f"Trend={trend} | RSI={rsi_val} | "
            f"EMA diff={ema_diff_pct:.3f}% — waiting for alignment"
        )

    return {
        "signal":       signal,
        "reason":       reason,
        "fast_ema":     round(fast_ema, 5),
        "slow_ema":     round(slow_ema, 5),
        "rsi":          rsi_val,
        "trend":        trend,
        "candles_used": len(closes),
    }


def _wait(reason: str) -> dict:
    return {
        "signal":       SIGNAL_WAIT,
        "reason":       reason,
        "fast_ema":     None,
        "slow_ema":     None,
        "rsi":          None,
        "trend":        "FLAT",
        "candles_used": 0,
    }
