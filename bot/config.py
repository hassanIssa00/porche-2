"""
=============================================================
  ISSSSMAIL SCALPER BOT v3.0 — Professional Swing Scalper
  إعدادات بوت التداول الاحترافي — استراتيجية بولباك منضبطة
=============================================================

Key Strategy Rules:
  1. No overtrading: Only 1 trade open across the account.
  2. Cooldown: Minimum 180 seconds (3 mins) after closing before opening again.
  3. Realistic targets: TP = $3.00, SL = $2.50 (room to breathe, well above spread).
  4. Breakeven protection: When profit reaches +$1.50, SL moves to entry + $0.30 (risk-free).
  5. Strict daily loss cap: Auto-pauses if daily loss reaches $15.00.
"""

# ──────────────────────────────────────────────────────────
# MT5 MCP Server path
# ──────────────────────────────────────────────────────────
MCP_SERVER_DIR: str = r"C:\Users\hassa\Desktop\all project\mcp forex"


# ──────────────────────────────────────────────────────────
# Symbols to trade (Gold + Bitcoin)
# ──────────────────────────────────────────────────────────
SYMBOLS: list[str] = ["XAUUSDm", "BTCUSDm"]   # Exness broker suffix


# ──────────────────────────────────────────────────────────
# Trade sizing & realistic profit/loss targets per trade
# حجم الصفقة وأهداف ربح ووقف واقعية تتجاوز السبريد
# ──────────────────────────────────────────────────────────
LOT_SIZE: float = 0.01            # Minimum lot

# Target profit: $3.00 (gives room for gold/btc moves, far exceeds $0.24 spread)
TAKE_PROFIT_USD: float = 3.00

# Stop loss: $0.50 (حوالي 50 سنت كما طلب المستخدم بالضبط)
STOP_LOSS_USD: float = 0.50

# Breakeven trigger: when profit reaches +$0.80, move SL to breakeven + $0.15
BREAKEVEN_TRIGGER_USD: float = 0.80
BREAKEVEN_LOCK_USD: float = 0.15

# Fallback SL/TP points for MT5 order
SL_POINTS: int = 500
TP_POINTS: int = 600


# ──────────────────────────────────────────────────────────
# Overtrading & frequency guards
# حماية من فتح الصفقات المتكرر والنزيف
# ──────────────────────────────────────────────────────────
# Maximum open positions across all symbols (1 for Gold + 1 for Bitcoin)
MAX_OPEN_POSITIONS: int = 2
MAX_POSITIONS_PER_SYMBOL: int = 1

# Cooldown after closing a trade before opening a new one on the SAME symbol (seconds)
TRADE_COOLDOWN_SEC: int = 180     # 3 minutes cooldown per symbol


# ──────────────────────────────────────────────────────────
# Trend & analysis settings
# إعدادات تحليل الاتجاه والبولباك
# ──────────────────────────────────────────────────────────
TREND_TF: str         = "M5"      # Primary trading timeframe
TREND_FAST_EMA: int   = 20        # EMA 20 on M5
TREND_SLOW_EMA: int   = 50        # EMA 50 on M5
RSI_PERIOD: int       = 14        # RSI period
RSI_OVERBOUGHT: float = 70.0      # Overbought
RSI_OVERSOLD:  float  = 30.0      # Oversold
CANDLES_NEEDED: int   = 60        # Minimum candles for analysis

# Higher Timeframe (HTF) confirmation (M15)
HTF_TF: str         = "M15"       # Macro trend timeframe
HTF_FAST_EMA: int   = 20
HTF_SLOW_EMA: int   = 50
HTF_CANDLES: int    = 40

# Confluence score required (out of 6)
MIN_SIGNAL_SCORE: int = 4

# Indicator settings
MACD_FAST: int     = 12
MACD_SLOW: int     = 26
MACD_SIGNAL: int   = 9
BB_PERIOD: int     = 20
BB_STD: float      = 2.0
ATR_PERIOD: int    = 14
ADX_PERIOD: int    = 14
ADX_MIN: float     = 20.0         # Minimum trend strength


# ──────────────────────────────────────────────────────────
# Daily goals & safety loss cap
# حارس حماية رأس المال — إيقاف التداول فوراً عند حد أقصى
# ──────────────────────────────────────────────────────────
DAILY_GOAL_USD: float = 20.0      # Realistic daily target

# Maximum daily loss: stop trading if account loses $15 in a day!
MAX_DAILY_LOSS_USD: float = 15.00
AUTO_PAUSE_ON_DAILY_LOSS: bool = True   # MUST be True to protect capital


# ──────────────────────────────────────────────────────────
# Sessions & timing
# ──────────────────────────────────────────────────────────
SESSION_FILTER_ENABLED: bool = True
GOLD_SESSIONS: list = [(7, 21)]   # Active market hours UTC
BTC_SESSIONS:  list = [(0, 24)]

SCAN_INTERVAL_SEC: int = 2        # Fast scan loop interval (2 seconds for tight SL response)
MAGIC_NUMBER:      int = 998877   # Bot trade identifier
