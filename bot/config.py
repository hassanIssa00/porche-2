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

# ── SOFTWARE TP/SL (monitored every second in engine) ─────
# These are the REAL targets — engine closes position when
# floating P&L crosses these thresholds.
# يتم مراقبة الـ P&L الحي كل ثانية، الإغلاق عند أول مكسب/خسارة
TAKE_PROFIT_USD: float = 0.30     # Close immediately when profit >= $0.30
STOP_LOSS_USD:   float = 0.30     # Close immediately when loss   >= $0.30

# ── MT5 HARD SL/TP (wide — just to satisfy broker requirements) ──
# These are NOT the real targets. They are fallback safety nets.
# الـ SL/TP في MT5 واسع فقط عشان البروكر يقبل الأوردر
# البرنامج نفسه بيقفل الصفقة قبلها بكتير
MT5_SL_MULTIPLIER: float = 2.0   # MT5 SL = 2 × ATR (wide safety net)
MT5_TP_MULTIPLIER: float = 2.0   # MT5 TP = 2 × ATR (wide safety net)
SL_POINTS: int  = 800             # Fallback if ATR unavailable
TP_POINTS: int  = 800


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
MIN_SIGNAL_SCORE: int = 4         # Score threshold (4/7) for responsive trend trading


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
ADX_MIN: float     = 20.0         # Minimum ADX for trending market


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
GOLD_SESSIONS: list = [(7, 21)]   # UTC hour ranges for Gold trading
BTC_SESSIONS:  list = [(0, 24)]   # Bitcoin: all hours


# ──────────────────────────────────────────────────────────
# Risk management — continuous trading preference
# إدارة المخاطر — البوت لا يتوقف إلا بأمر المستخدم
# ──────────────────────────────────────────────────────────
MAX_CONSECUTIVE_LOSSES: int    = 5   # Just for tracking / warning
PAUSE_CANDLES_AFTER_STREAK: int = 0  # 0 = do not pause; immediately look for next trade


# ──────────────────────────────────────────────────────────
# Bot timing
# توقيت البوت
# ──────────────────────────────────────────────────────────
SCAN_INTERVAL_SEC: int = 5        # Scan market every 5 seconds
MAGIC_NUMBER:      int = 998877   # Magic number to identify bot's trades


# ──────────────────────────────────────────────────────────
# Risk guard — maximum daily loss
# حارس المخاطر — أقصى خسارة يومية
# ──────────────────────────────────────────────────────────
MAX_DAILY_LOSS_USD: float = 100.0 # Warning threshold
AUTO_PAUSE_ON_DAILY_LOSS: bool = False  # False = Never auto-pause (stops only when user clicks STOP)
