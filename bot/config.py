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

# STOP LOSS: أقصى خسارة 0.50 دولار فقط (حماية صارمة لرأس المال)
STOP_LOSS_USD: float = 0.50

# TAKE PROFIT: أهداف ربح حقيقية من 0.80$ إلى 1.80$ (المتوسط 1.00$)
TP_MIN_USD: float    = 0.80     # الحد الأدنى للربح (أعلى بكثير من السبريد)
TP_MAX_USD: float    = 1.80     # أقصى هدف للموجة القوية
TP_ATR_MULT: float   = 1.5      # الهدف = 1.5x ATR على الدقيقة
TAKE_PROFIT_USD: float = 1.00   # الهدف الافتراضي (ضعف الستوب لوس: R:R = 1:2)

# Breakeven: بعد تحقيق 0.55$ ربح يتم تحريك الستوب لنقطة الدخول + 0.10$ أرباح
BREAKEVEN_TRIGGER_USD: float = 0.55
BREAKEVEN_LOCK_USD: float    = 0.10

# Fallback points
SL_POINTS: int = 5000
TP_POINTS: int = 10000


# ──────────────────────────────────────────────────────────
# Frequency & cooldown (حماية من النزيف وحرق السبريد)
# ──────────────────────────────────────────────────────────
MAX_OPEN_POSITIONS: int = 1
TRADE_COOLDOWN_SEC: int = 60      # 60 ثانية بعد إغلاق الصفقة لانتظار شمعة جديدة


# ──────────────────────────────────────────────────────────
# Fast M1 Analysis Settings
# ──────────────────────────────────────────────────────────
TREND_TF: str         = "M1"      # التايم فريم السريع M1
TREND_FAST_EMA: int   = 7         # EMA 7 سريع
TREND_SLOW_EMA: int   = 20        # EMA 20 خط الأساس
RSI_PERIOD: int       = 14
CANDLES_NEEDED: int   = 40

# Higher Timeframe settings
HTF_TF: str           = "M5"
HTF_CANDLES: int      = 30

# Minimum EMA separation to avoid chop ($4 on BTC)
MIN_EMA_DIFF: float   = 4.0

# Confluence score المطلوب للدخول (3 من 3)
MIN_SIGNAL_SCORE: int = 3

# Indicators
MACD_FAST: int     = 12
MACD_SLOW: int     = 26
MACD_SIGNAL: int   = 9
ATR_PERIOD: int    = 14
ADX_PERIOD: int    = 14
ADX_MIN: float     = 0.0         # بدون حظر للتذبذب


# ──────────────────────────────────────────────────────────
# Daily Capital Protection
# ──────────────────────────────────────────────────────────
DAILY_GOAL_USD: float          = 99999.0
MAX_DAILY_LOSS_USD: float      = 8.00      # حماية رأس المال: إيقاف عند خسارة 8$ في اليوم
AUTO_PAUSE_ON_DAILY_LOSS: bool = True


# ──────────────────────────────────────────────────────────
# Sessions & scan loop
# ──────────────────────────────────────────────────────────
SESSION_FILTER_ENABLED: bool = True
BTC_SESSIONS: list = [(0, 24)]

SCAN_INTERVAL_SEC: int = 2
MAGIC_NUMBER:      int = 998877
