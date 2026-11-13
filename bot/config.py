"""
=============================================================
  ISSSSMAIL SCALPER BOT v2.0 — Configuration
  إعدادات بوت التداول السكالبر للذهب والبيتكوين
=============================================================

All bot parameters live here. Edit once, affects everything.
جميع الإعدادات هنا — تعديل واحد يؤثر على كل شيء.
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

# Take Profit: USD target per trade
# XAUUSDm ATR (M5) ≈ $4 → TP of $2 is realistic (0.5 × ATR)
# Note: actual TP in POINTS is calculated dynamically from ATR in engine.py
TAKE_PROFIT_USD: float = 2.00     # Realistic target given spread=$0.24 & ATR=$4

# Stop Loss: USD floor per trade
# Engine calculates ATR-based SL (1.0 × ATR) which may be larger than this
STOP_LOSS_USD: float = 2.00       # Floor — real SL based on ATR in engine

# Fallback SL/TP in POINTS if all else fails
SL_POINTS: int  = 500             # Safe fallback
TP_POINTS: int  = 500


# ──────────────────────────────────────────────────────────
# Daily goal — shows progress bar in dashboard
# الهدف اليومي — يُظهر شريط التقدم في الداشبورد
# ──────────────────────────────────────────────────────────
DAILY_GOAL_USD: float = 10.0      # USD per day


# ──────────────────────────────────────────────────────────
# Maximum concurrent open positions (all symbols combined)
# الحد الأقصى للصفقات المفتوحة في نفس الوقت
# ──────────────────────────────────────────────────────────
MAX_OPEN_POSITIONS: int = 2       # 1 per symbol max


# ──────────────────────────────────────────────────────────
# Primary trend analysis settings (M5 timeframe)
# إعدادات تحليل الاتجاه الأساسية (إطار زمني M5)
# ──────────────────────────────────────────────────────────
TREND_TF: str         = "M5"      # Primary timeframe
TREND_FAST_EMA: int   = 9         # Fast EMA period
TREND_SLOW_EMA: int   = 21        # Slow EMA period
RSI_PERIOD: int       = 14        # RSI period
RSI_OVERBOUGHT: float = 65.0      # RSI sell threshold
RSI_OVERSOLD:  float  = 35.0      # RSI buy threshold
CANDLES_NEEDED: int   = 60        # Minimum candles (need more for MACD/BB)


# ──────────────────────────────────────────────────────────
# Higher Timeframe (HTF) confirmation — M15
# تأكيد الاتجاه من الإطار الزمني الأعلى M15
# ──────────────────────────────────────────────────────────
HTF_TF: str         = "M15"       # Higher timeframe for trend filter
HTF_FAST_EMA: int   = 9           # HTF fast EMA
HTF_SLOW_EMA: int   = 21          # HTF slow EMA
HTF_CANDLES: int    = 30          # Candles to fetch for HTF


# ──────────────────────────────────────────────────────────
# Confluence scoring system
# نظام درجات التقاطع — الصفقة تفتح لو الدرجة ≥ الحد الأدنى
# ──────────────────────────────────────────────────────────
# Score components (each = +1 point):
#   1. EMA9 > EMA21 (BUY) or EMA9 < EMA21 (SELL)
#   2. MACD histogram positive (BUY) or negative (SELL)
#   3. RSI in healthy range (not extreme) [35–65]
#   4. Price above BB midline (BUY) or below (SELL)
#   5. ADX > 20 (trending market)
#   6. M15 EMA alignment matches M5 signal
MIN_SIGNAL_SCORE: int = 5         # Need 5/7 — strict filter (avoid bad trades)


# ──────────────────────────────────────────────────────────
# Indicator parameters (pure Python, no external libs)
# إعدادات المؤشرات — محسوبة بـ Python خالص بدون مكتبات خارجية
# ──────────────────────────────────────────────────────────
MACD_FAST: int     = 12           # MACD fast EMA period
MACD_SLOW: int     = 26           # MACD slow EMA period
MACD_SIGNAL: int   = 9            # MACD signal line period
BB_PERIOD: int     = 20           # Bollinger Bands period
BB_STD: float      = 2.0          # Bollinger Bands standard deviation multiplier
ATR_PERIOD: int    = 14           # ATR period (Average True Range)
ADX_PERIOD: int    = 14           # ADX period (trend strength)
ADX_MIN: float     = 25.0         # Minimum ADX for trending market (25 = real trend)


# ──────────────────────────────────────────────────────────
# Trailing stop (moves SL to protect profits)
# وقف الخسارة المتحرك — يحمي الأرباح تلقائيًا
# ──────────────────────────────────────────────────────────
TRAIL_ENABLED: bool          = True
TRAIL_BREAKEVEN_AT_PCT: float = 0.3   # Move SL to breakeven when profit >= 30% of TP
TRAIL_START_AT_PCT: float     = 0.6   # Start trailing when profit >= 60% of TP
TRAIL_ATR_MULTIPLIER: float   = 0.5   # Trail distance = 0.5 × ATR


# ──────────────────────────────────────────────────────────
# Session filter (UTC hours) — when to trade each symbol
# فلتر جلسات التداول (بتوقيت UTC)
# ──────────────────────────────────────────────────────────
# Gold is best during London + NY overlap: 08:00–17:00 UTC
# Bitcoin trades 24/7 but is most active 14:00–22:00 UTC
SESSION_FILTER_ENABLED: bool = True
GOLD_SESSIONS: list = [(7, 20)]   # UTC hour ranges for Gold trading
BTC_SESSIONS:  list = [(0, 24)]   # Bitcoin: all hours


# ──────────────────────────────────────────────────────────
# Risk management — consecutive losses protection
# إدارة المخاطر — حماية من الخسائر المتتالية
# ──────────────────────────────────────────────────────────
MAX_CONSECUTIVE_LOSSES: int    = 3   # Pause after this many losses in a row
PAUSE_CANDLES_AFTER_STREAK: int = 2  # Skip this many scans after loss streak


# ──────────────────────────────────────────────────────────
# Bot timing
# توقيت البوت
# ──────────────────────────────────────────────────────────
SCAN_INTERVAL_SEC: int = 10       # How often bot checks market (seconds)
MAGIC_NUMBER:      int = 998877   # Magic number to identify bot's trades


# ──────────────────────────────────────────────────────────
# Risk guard — maximum daily loss
# حارس المخاطر — أقصى خسارة يومية
# ──────────────────────────────────────────────────────────
MAX_DAILY_LOSS_USD: float = 20.0  # Stop trading if daily loss exceeds this
