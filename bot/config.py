"""
=============================================================
  ISSSSMAIL SCALPER BOT — Configuration
  إعدادات بوت التداول السكالبر للذهب والبيتكوين
=============================================================

All bot parameters live here. Edit once, affects everything.
"""

from typing import Optional


# ──────────────────────────────────────────────────────────
# MT5 MCP Server path (the one already on your machine)
# مسار خادم MCP الموجود على جهازك
# ──────────────────────────────────────────────────────────
MCP_SERVER_DIR: str = r"C:\Users\hassa\Desktop\all project\mcp forex"


# ──────────────────────────────────────────────────────────
# Symbols to trade (Gold + Bitcoin only)
# الرموز المسموح بتداولها فقط
# ──────────────────────────────────────────────────────────
SYMBOLS: list[str] = ["XAUUSDm", "BTCUSDm"]   # Gold + Bitcoin (Exness broker suffix)


# ──────────────────────────────────────────────────────────
# Trade sizing & profit/loss targets per trade
# حجم الصفقة وأهداف الربح والخسارة لكل صفقة
# ──────────────────────────────────────────────────────────
LOT_SIZE: float = 0.01            # Minimum lot — keep risk tiny (أصغر لوت)

# Take Profit: how many USD profit per trade before closing
# هدف الربح بالدولار لكل صفقة
TAKE_PROFIT_USD: float = 0.50     # e.g. 0.20 | 0.30 | 0.50 | 0.70 | 0.80

# Stop Loss: close if loss reaches this amount (USD)
# وقف الخسارة بالدولار — يغلق الصفقة ويفتح غيرها
STOP_LOSS_USD: float = 0.50       # e.g. 0.50

# Fallback SL/TP in POINTS if USD calc not available
SL_POINTS: int  = 150             # ~15 pips backup
TP_POINTS: int  = 150             # ~15 pips backup


# ──────────────────────────────────────────────────────────
# Daily goal — bot pauses (not stops) when reached
# الهدف اليومي — البوت يستمر لكن يظهر "هدف محقق"
# ──────────────────────────────────────────────────────────
DAILY_GOAL_USD: float = 10.0      # USD per day


# ──────────────────────────────────────────────────────────
# Maximum concurrent open positions (all symbols combined)
# الحد الأقصى للصفقات المفتوحة في نفس الوقت
# ──────────────────────────────────────────────────────────
MAX_OPEN_POSITIONS: int = 2       # 1 per symbol max


# ──────────────────────────────────────────────────────────
# Trend analysis settings
# إعدادات تحليل الاتجاه
# ──────────────────────────────────────────────────────────
TREND_TF: str         = "M5"      # Timeframe for trend detection
TREND_FAST_EMA: int   = 9         # Fast EMA period
TREND_SLOW_EMA: int   = 21        # Slow EMA period
RSI_PERIOD: int       = 14        # RSI period
RSI_OVERBOUGHT: float = 65.0      # RSI sell threshold
RSI_OVERSOLD:  float  = 35.0      # RSI buy threshold
CANDLES_NEEDED: int   = 50        # Minimum candles for analysis


# ──────────────────────────────────────────────────────────
# Bot timing
# توقيت البوت
# ──────────────────────────────────────────────────────────
SCAN_INTERVAL_SEC: int = 10       # How often bot checks market (seconds)
MAGIC_NUMBER:      int = 998877   # Magic number to identify bot's trades


# ──────────────────────────────────────────────────────────
# Risk guard
# حارس المخاطر
# ──────────────────────────────────────────────────────────
MAX_DAILY_LOSS_USD: float = 20.0  # Stop trading if daily loss exceeds this
