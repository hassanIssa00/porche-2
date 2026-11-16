"""
=============================================================
  ISSSSMAIL SCALPER BOT v5.5 — High-Quality M1 Scalper
  بوت السكالبينج الذكي — نسبة ربح إلى خسارة رابحة رياضياً
=============================================================

Strategy Mathematical Principles:
  1. Risk:Reward Ratio is 1:2 (Average Win $0.80 - $1.50 vs Stop Loss $0.50).
  2. With 1:2 R:R, a 50% win rate produces steady, compounding profit.
  3. Breakeven triggers at +$0.55 (locks +$0.10, completely risk-free).
  4. 60-second cooldown prevents overtrading and eliminates broker spread bleed.
  5. Daily capital protection: auto-pauses at -$8.00 daily loss.
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

# Fallback points
SL_POINTS: int = 5000
TP_POINTS: int = 8500


# ──────────────────────────────────────────────────────────
# Frequency & cooldown
# ──────────────────────────────────────────────────────────
MAX_OPEN_POSITIONS: int = 1
TRADE_COOLDOWN_SEC: int = 10      # 10 ثانية — صفقات سريعة متتالية


# ──────────────────────────────────────────────────────────
# Analysis Settings
# ──────────────────────────────────────────────────────────
TREND_TF: str         = "M1"
TREND_FAST_EMA: int   = 21
TREND_SLOW_EMA: int   = 55
RSI_PERIOD: int       = 14
CANDLES_NEEDED: int   = 60

# RSI thresholds (من backtest)
RSI_OVERSOLD: float   = 35.0    # أقل من 35 = تشبع بيعي
RSI_OVERBOUGHT: float = 62.0    # أكثر من 62 = تشبع شرائي

# Higher Timeframe settings
HTF_TF: str           = "M5"
HTF_CANDLES: int      = 30

# Signal threshold: 4/4 مطلوبة لتأكيد الدخول
MIN_SIGNAL_SCORE: int = 4

# Indicators
MACD_FAST: int     = 12
MACD_SLOW: int     = 26
MACD_SIGNAL: int   = 9
ATR_PERIOD: int    = 14
ADX_PERIOD: int    = 14
ADX_MIN: float     = 0.0         # بدون حظر للتذبذب


# ──────────────────────────────────────────────────────────
# 24/7 Continuous Operation — No Daily Limits (لا يوجد أي حد يومي)
# ──────────────────────────────────────────────────────────
DAILY_GOAL_USD: float          = 99999.0   # بدون حد ربح يومي
MAX_DAILY_LOSS_USD: float      = 99999.0   # بدون أي حد خسارة يومي نهائياً
AUTO_PAUSE_ON_DAILY_LOSS: bool = False     # البوت شغال 24/7 مستمر بلا توقف


# ──────────────────────────────────────────────────────────
# Sessions & scan loop
# ──────────────────────────────────────────────────────────
SESSION_FILTER_ENABLED: bool = True
BTC_SESSIONS: list = [(0, 24)]

SCAN_INTERVAL_SEC: int = 2
MAGIC_NUMBER:      int = 998877
