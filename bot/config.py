"""
=============================================================
  ISSSSMAIL SCALPER BOT v5.0 — High-Frequency M1 Micro Scalper
  بوت السكالبينج فائق السرعة — صفقات سريعة وأرباح متتالية
=============================================================

Strategy Rules:
  1. High-frequency scalping on M1 (1-minute timeframe).
  2. Profit target: $0.40 to $1.50 dynamic (fast exits in profit).
  3. Max loss per trade: $0.50 (strict hard stop).
  4. Breakeven protection: at +$0.25 profit, SL moves to entry.
  5. Short cooldown: 20 seconds between trades.
  6. 24/7 continuous operation without daily limits.
  7. Trades BOTH BUY and SELL based on immediate M1 momentum.
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
# Stop Loss & Take Profit — MICRO SCALPING
# ──────────────────────────────────────────────────────────

# STOP LOSS: أقصى خسارة 0.50 دولار فقط
STOP_LOSS_USD: float = 0.50

# TAKE PROFIT: أهداف سريعة بين 0.40$ و 1.50$
TP_MIN_USD: float    = 0.40     # أقل ربح للإغلاق السريع
TP_MAX_USD: float    = 1.50     # أقصى ربح للموجة
TP_ATR_MULT: float   = 1.0      # حجم الهدف = 1x ATR على دقيقة واحدة
TAKE_PROFIT_USD: float = 0.70   # الهدف الافتراضي

# Breakeven: بمجرد ما الصفقة تكسب 0.25$ يتحرك الستوب للدخول (حماية فورية)
BREAKEVEN_TRIGGER_USD: float = 0.25
BREAKEVEN_LOCK_USD: float    = 0.05

# Fallback points
SL_POINTS: int = 5000
TP_POINTS: int = 7000


# ──────────────────────────────────────────────────────────
# Frequency & cooldown (صفقات كثيرة وسريعة)
# ──────────────────────────────────────────────────────────
MAX_OPEN_POSITIONS: int = 1
TRADE_COOLDOWN_SEC: int = 20      # 20 ثانية فقط كول داون بعد إغلاق الصفقة


# ──────────────────────────────────────────────────────────
# Fast M1 Analysis Settings
# ──────────────────────────────────────────────────────────
TREND_TF: str         = "M1"      # التايم فريم السريع M1
TREND_FAST_EMA: int   = 7         # EMA 7 فائق السرعة
TREND_SLOW_EMA: int   = 20        # EMA 20 خط الأساس
RSI_PERIOD: int       = 14
RSI_OVERBOUGHT: float = 75.0
RSI_OVERSOLD:  float  = 25.0
CANDLES_NEEDED: int   = 40

# Higher Timeframe — مرجع إضافي فقط (لا يمنع الصفقات)
HTF_TF: str         = "M5"
HTF_FAST_EMA: int   = 20
HTF_SLOW_EMA: int   = 50
HTF_CANDLES: int    = 30

# Confluence score المطلوب للدخول (3 من 3)
MIN_SIGNAL_SCORE: int = 3

# Indicators
MACD_FAST: int     = 12
MACD_SLOW: int     = 26
MACD_SIGNAL: int   = 9
ATR_PERIOD: int    = 14
ADX_PERIOD: int    = 14
ADX_MIN: float     = 0.0         # بدون حظر للتذبذب — استغلال كل الفرص


# ──────────────────────────────────────────────────────────
# 24/7 Operation — No Daily Caps
# ──────────────────────────────────────────────────────────
DAILY_GOAL_USD: float          = 99999.0
MAX_DAILY_LOSS_USD: float      = 99999.0
AUTO_PAUSE_ON_DAILY_LOSS: bool = False


# ──────────────────────────────────────────────────────────
# Sessions & scan loop
# ──────────────────────────────────────────────────────────
SESSION_FILTER_ENABLED: bool = True
BTC_SESSIONS: list = [(0, 24)]

SCAN_INTERVAL_SEC: int = 2        # فحص كل ثانيتين
MAGIC_NUMBER:      int = 998877
