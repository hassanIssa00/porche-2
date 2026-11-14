"""
=============================================================
  ISSSSMAIL SCALPER BOT v4.0 — High-Frequency Micro Scalper
  استراتيجية سكالبينج سريع — أرباح صغيرة + صفقات كثيرة
=============================================================

Strategy Rules:
  1. Many small trades — TP $0.40 to $2.00 (dynamic per ATR)
  2. Max loss per trade: $0.50 (hard limit)
  3. M1 for fast entries, M5 for trend direction
  4. No overtrading: 1 trade at a time, 60s cooldown
  5. Daily loss cap: $5.00 auto-pause
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
# Stop Loss & Take Profit — SCALPING MODE
# خسارة أقصى 0.50$ — ربح ديناميكي 0.40 لـ 2.00$
# ──────────────────────────────────────────────────────────

# STOP LOSS: أقصى خسارة 0.50 دولار للصفقة
STOP_LOSS_USD: float    = 0.50

# TAKE PROFIT: ديناميكي بناءً على ATR — الحد الأدنى والأقصى
TP_MIN_USD: float       = 0.40     # أقل ربح مقبول
TP_MAX_USD: float       = 2.00     # أقصى هدف ربح
TP_ATR_MULT: float      = 1.5      # الهدف = 1.5x ATR (ديناميكي)

# للتوافق مع باقي الكود
TAKE_PROFIT_USD: float  = 1.00     # القيمة الافتراضية (يتم تجاوزها ديناميكياً)

# Breakeven: لما الربح يوصل 0.30$ — حرك الـ SL لنقطة الدخول (صفر خسارة)
BREAKEVEN_TRIGGER_USD: float = 0.30
BREAKEVEN_LOCK_USD: float    = 0.05

# Fallback points (للحساب الداخلي فقط)
SL_POINTS: int = 5000
TP_POINTS: int = 10000


# ──────────────────────────────────────────────────────────
# Frequency & cooldown
# ──────────────────────────────────────────────────────────
MAX_OPEN_POSITIONS: int = 1
TRADE_COOLDOWN_SEC: int = 120     # دقيقتين كول داون بين الصفقات


# ──────────────────────────────────────────────────────────
# Analysis — M1 for signals, M5 for trend
# ──────────────────────────────────────────────────────────
TREND_TF: str         = "M1"      # التايم فريم الأساسي للدخول
TREND_FAST_EMA: int   = 9         # EMA 9 على M1
TREND_SLOW_EMA: int   = 21        # EMA 21 على M1
RSI_PERIOD: int       = 14
RSI_OVERBOUGHT: float = 70.0
RSI_OVERSOLD:  float  = 30.0
CANDLES_NEEDED: int   = 50

# Higher Timeframe — M5 للاتجاه العام
HTF_TF: str         = "M5"
HTF_FAST_EMA: int   = 20
HTF_SLOW_EMA: int   = 50
HTF_CANDLES: int    = 40

# Confluence score — 4/4 مطلوب (كل الشروط لازم تتفق)
MIN_SIGNAL_SCORE: int = 4

# Indicators
MACD_FAST: int     = 12
MACD_SLOW: int     = 26
MACD_SIGNAL: int   = 9
BB_PERIOD: int     = 20
BB_STD: float      = 2.0
ATR_PERIOD: int    = 14
ADX_PERIOD: int    = 14
ADX_MIN: float     = 20.0        # لازم يكون في اتجاه (مش تذبذب)


# ──────────────────────────────────────────────────────────
# Daily goals & safety
# ──────────────────────────────────────────────────────────
DAILY_GOAL_USD: float       = 99999.0   # مش بيوقف
MAX_DAILY_LOSS_USD: float   = 99999.0   # مش بيوقف
AUTO_PAUSE_ON_DAILY_LOSS: bool = False  # البوت شغال 24/7 بلا حدود


# ──────────────────────────────────────────────────────────
# Sessions & timing
# ──────────────────────────────────────────────────────────
SESSION_FILTER_ENABLED: bool = True
BTC_SESSIONS:  list = [(0, 24)]

SCAN_INTERVAL_SEC: int = 2
MAGIC_NUMBER:      int = 998877
