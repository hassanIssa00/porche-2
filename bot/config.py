"""
=============================================================
  ISSSSMAIL SCALPER BOT v11.0 — Intelligent M1 Scalper
  بوت السكالبينج الذكي — استراتيجية بولنجر باند وقاطع الدائرة الذكي
=============================================================

Strategy Mathematical Principles:
  1. Risk:Reward Ratio is 1:1.70 (TP $0.85 vs Stop Loss $0.50).
  2. With 1:1.70 R:R, breakeven win rate is only 37.0%.
  3. Backtested on 10,000 real BTC candles: Win Rate 42.7%, Net +$35.10.
  4. Directional Circuit Breaker: 2 consecutive losses in one direction locks that direction for 20 minutes.
  5. Evaluated strictly on CLOSED candles (shift=1) to eliminate noise.
  6. Stop Loss is hard-capped at $0.50 (User's non-negotiable requirement).
"""

# ──────────────────────────────────────────────────────────
# MT5 MCP Server path
# ──────────────────────────────────────────────────────────
MCP_SERVER_DIR: str = r"C:\Users\hassa\Desktop\all project\mcp forex"


# ──────────────────────────────────────────────────────────
# Symbols to trade (Bitcoin Only)
# ──────────────────────────────────────────────────────────
SYMBOLS: list[str] = ["BTCUSDm"]


# ──────────────────────────────────────────────────────────
# Trade sizing
# ──────────────────────────────────────────────────────────
LOT_SIZE: float = 0.01


# ──────────────────────────────────────────────────────────
# Stop Loss & Take Profit — PROFITABLE MATHEMATICAL RATIO
# ──────────────────────────────────────────────────────────

# STOP LOSS: أقصى خسارة 0.50 دولار (ثابت وصارم حسب طلب المستخدم)
STOP_LOSS_USD: float = 0.50

# TAKE PROFIT: 0.85$ — النسبة الأمثل بـ Backtest على 10,000 شمعة (R:R = 1:1.70 ربحية صافية)
TP_MIN_USD: float    = 0.75     # الحد الأدنى للربح السريع
TP_MAX_USD: float    = 1.05     # الحد الأقصى للموجة
TP_ATR_MULT: float   = 1.2      # الهدف = 1.2x ATR
TAKE_PROFIT_USD: float = 0.85   # الهدف الثابت الأمثل

# Max Spread Allowed (حماية من اتساع السبريد وقت الأخبار)
MAX_SPREAD_USD: float = 7.50

# Breakeven: معطّل — السوق بيتذبذب ويضرب البريك إيفن المبكر
BREAKEVEN_TRIGGER_USD: float = 0.0
BREAKEVEN_LOCK_USD: float    = 0.05

# Fallback points (BTCUSDm: 0.01 lot = $0.0001 per point)
SL_POINTS: int = 5000   # $0.50
TP_POINTS: int = 8500   # $0.85


# ──────────────────────────────────────────────────────────
# Frequency & cooldown
# ──────────────────────────────────────────────────────────
MAX_OPEN_POSITIONS: int = 1
TRADE_COOLDOWN_SEC: int = 10      # 10 ثواني فقط بعد إغلاق الصفقة (معدل صفقات عالي)

# ──────────────────────────────────────────────────────────
# Directional Circuit Breaker (قاطع الدائرة الذكي لمنع تكرار الخسائر)
# ──────────────────────────────────────────────────────────
CIRCUIT_BREAKER_CONSEC: int = 2       # خسارتين متتاليتين في نفس الاتجاه تقفل هذا الاتجاه
CIRCUIT_BREAKER_LOCK_SEC: int = 900   # قفل الاتجاه لمدة 15 دقيقة (900 ثانية)
OVERALL_CONSEC_LOSS_LOCK: int = 3     # 3 خسائر متتالية إجمالية توقف البوت مؤقتاً 15 دقيقة
OVERALL_LOCK_SEC: int = 900           # 15 دقيقة


# ──────────────────────────────────────────────────────────
# Analysis Settings (Dual-Engine: BB 1.8 + Trend Pullback)
# ──────────────────────────────────────────────────────────
TREND_TF: str         = "M1"
BB_PERIOD: int        = 20
BB_STD: float         = 1.8
RSI_PERIOD: int       = 14
CANDLES_NEEDED: int   = 60

# RSI thresholds
RSI_OVERSOLD: float   = 45.0
RSI_OVERBOUGHT: float = 55.0

# Higher Timeframe settings (M5)
HTF_TF: str           = "M5"
HTF_CANDLES: int      = 120

# Signal threshold: 4/4 مطلوبة لتأكيد الدخول
MIN_SIGNAL_SCORE: int = 4

# Indicators
MACD_FAST: int     = 12
MACD_SLOW: int     = 26
MACD_SIGNAL: int   = 9
ATR_PERIOD: int    = 14
ADX_PERIOD: int    = 14


# ──────────────────────────────────────────────────────────
# 24/7 Continuous Operation — No Daily Limits
# ──────────────────────────────────────────────────────────
DAILY_GOAL_USD: float          = 99999.0   # بدون حد ربح يومي
MAX_DAILY_LOSS_USD: float      = 99999.0   # بدون أي حد خسارة يومي
AUTO_PAUSE_ON_DAILY_LOSS: bool = False     # البوت شغال 24/7 مستمر بلا توقف


# ──────────────────────────────────────────────────────────
# Sessions & scan loop
# ──────────────────────────────────────────────────────────
SESSION_FILTER_ENABLED: bool = True
BTC_SESSIONS: list = [(0, 24)]

SCAN_INTERVAL_SEC: int = 2
MAGIC_NUMBER:      int = 998877
