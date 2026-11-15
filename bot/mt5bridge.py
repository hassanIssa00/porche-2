"""
=============================================================
  ISSSSMAIL SCALPER BOT — MT5 Bridge
  جسر الاتصال بـ MetaTrader 5
=============================================================

Wraps the MetaTrader5 Python API directly (same as the MCP server
does internally). No HTTP calls — fast in-process connection.
"""

import sys
import os
import math
import logging
from datetime import datetime
from typing import Optional, Any

# ── Add MCP utilities to path ──────────────────────────────
MCP_DIR = r"C:\Users\hassa\Desktop\all project\mcp forex"
if MCP_DIR not in sys.path:
    sys.path.insert(0, MCP_DIR)

try:
    import mt5_utils
    _HAS_UTILS = True
except ImportError:
    _HAS_UTILS = False

try:
    import MetaTrader5 as mt5
    _HAS_MT5 = True
except ImportError:
    mt5 = None           # type: ignore
    _HAS_MT5 = False

logger = logging.getLogger("issssmail.mt5bridge")


# ──────────────────────────────────────────────────────────
# Connection helpers
# ──────────────────────────────────────────────────────────
def is_terminal_process_running() -> bool:
    """Check if MetaTrader 5 executable (terminal64.exe) is running."""
    try:
        import psutil
        for p in psutil.process_iter(['name']):
            name = p.info.get('name')
            if name and 'terminal64' in name.lower():
                return True
    except Exception:
        pass
    return False


def connect() -> bool:
    """Initialize and connect to MT5 terminal. Returns True on success."""
    if not _HAS_MT5:
        logger.error("MetaTrader5 package not installed.")
        return False
    # Never launch MT5 in hidden background mode if user hasn't opened it!
    if not is_terminal_process_running():
        logger.warning("MT5 process (terminal64.exe) is not running on desktop. Waiting for user to open MT5.")
        return False
    if mt5.initialize():
        ti = mt5.terminal_info()
        if ti and ti.connected:
            logger.info("MT5 connected ✓")
            return True
    logger.error("MT5 init failed: %s", mt5.last_error())
    return False


def disconnect() -> None:
    if _HAS_MT5:
        mt5.shutdown()


def is_connected() -> bool:
    if not _HAS_MT5:
        return False
    try:
        ti = mt5.terminal_info()
        return ti is not None and bool(ti.connected)
    except Exception:
        return False


# ──────────────────────────────────────────────────────────
# Account info
# ──────────────────────────────────────────────────────────
def account_info() -> Optional[dict]:
    """Return account dict or None."""
    if not _HAS_MT5:
        return None
    acc = mt5.account_info()
    if acc is None:
        return None
    if _HAS_UTILS:
        return mt5_utils.format_account_info(acc)
    return {
        "login":       acc.login,
        "balance":     round(acc.balance, 2),
        "equity":      round(acc.equity, 2),
        "profit":      round(acc.profit, 2),
        "margin_free": round(acc.margin_free, 2),
        "leverage":    acc.leverage,
        "currency":    acc.currency,
    }


# ──────────────────────────────────────────────────────────
# Candles
# ──────────────────────────────────────────────────────────
def get_candles(symbol: str, timeframe: str = "M5", count: int = 100) -> list[dict]:
    """Return list of OHLCV candle dicts for the given symbol/timeframe."""
    if not _HAS_MT5:
        return []

    tf_map = {
        "M1": 1, "M5": 5, "M15": 15, "M30": 30,
        "H1": 16385, "H4": 16388, "D1": 16408,
    }
    tf = tf_map.get(timeframe.upper(), 5)

    # Resolve broker-specific symbol name (e.g. XAUUSDm, BTCUSD.r, etc.)
    resolved = _resolve_symbol(symbol)
    if not resolved:
        logger.warning("Could not resolve symbol: %s", symbol)
        return []

    logger.debug("get_candles: %s → %s  TF=%s  count=%d", symbol, resolved, timeframe, count)
    rates = mt5.copy_rates_from_pos(resolved, tf, 0, count)
    if rates is None:
        logger.warning("copy_rates_from_pos returned None for %s — MT5 error: %s", resolved, mt5.last_error())
        return []

    result = []
    for r in rates:
        try:
            result.append({
                "time":   r["time"],
                "open":   float(r["open"]),
                "high":   float(r["high"]),
                "low":    float(r["low"]),
                "close":  float(r["close"]),
                "volume": int(r["tick_volume"]),
            })
        except Exception:
            continue
    return result


def _resolve_symbol(symbol: str) -> Optional[str]:
    """Try to select the symbol in MT5; handle broker suffixes. Returns resolved name or None."""
    if not _HAS_MT5:
        return None
    # Try exact name first
    if mt5.symbol_select(symbol, True):
        info = mt5.symbol_info(symbol)
        if info is not None:
            return symbol
    # Search all symbols for prefix match (handles broker suffixes: XAUUSDm, BTCUSDr, etc.)
    syms = mt5.symbols_get()
    if syms:
        up = symbol.upper()
        # Exact case-insensitive match first
        exact = [s.name for s in syms if s.name.upper() == up]
        if exact:
            mt5.symbol_select(exact[0], True)
            return exact[0]
        # Prefix match (e.g. XAUUSD → XAUUSDm)
        matches = [s.name for s in syms if s.name.upper().startswith(up)]
        if matches:
            mt5.symbol_select(matches[0], True)
            return matches[0]
    logger.warning("Symbol '%s' not found in MT5 symbols list.", symbol)
    return None


# ──────────────────────────────────────────────────────────
# Price
# ──────────────────────────────────────────────────────────
def get_tick(symbol: str) -> Optional[dict]:
    """Return current bid/ask or None."""
    if not _HAS_MT5:
        return None
    sym = _resolve_symbol(symbol)
    if not sym:
        return None
    tick = mt5.symbol_info_tick(sym)
    if tick is None:
        return None
    return {"bid": tick.bid, "ask": tick.ask, "symbol": sym}


def get_symbol_info(symbol: str) -> Optional[Any]:
    """Return raw MT5 symbol_info object."""
    if not _HAS_MT5:
        return None
    sym = _resolve_symbol(symbol)
    if not sym:
        return None
    return mt5.symbol_info(sym)


# ──────────────────────────────────────────────────────────
# Closed deals history (from MT5)
# ──────────────────────────────────────────────────────────
def get_today_closed_deals(magic: Optional[int] = None) -> list[dict]:
    """
    Return all closed deals from today's MT5 history.
    Only ENTRY_OUT deals (position close) are included.
    """
    if not _HAS_MT5:
        return []
    import datetime as _dt
    today_start = _dt.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow    = today_start + _dt.timedelta(days=1)
    deals = mt5.history_deals_get(today_start, tomorrow)
    if deals is None:
        return []
    result = []
    for d in deals:
        # entry==1 means ENTRY_OUT (closing deal)
        if getattr(d, "entry", -1) != 1:
            continue
        if magic is not None and getattr(d, "magic", -1) != magic:
            continue
        result.append({
            "ticket":      d.ticket,
            "position_id": d.position_id,
            "symbol":      d.symbol,
            "type":        "BUY" if d.type == 0 else "SELL",
            "volume":      round(d.volume, 4),
            "price":       d.price,
            "profit":      round(d.profit + d.swap + d.commission, 2),
            "time":        _dt.datetime.fromtimestamp(d.time).strftime("%Y-%m-%d %H:%M:%S"),
        })
    return result


# ──────────────────────────────────────────────────────────
# Positions
# ──────────────────────────────────────────────────────────
def get_open_positions(magic: Optional[int] = None) -> list[dict]:
    """Return list of open position dicts (filtered by magic if given)."""
    if not _HAS_MT5:
        return []
    positions = mt5.positions_get()
    if positions is None:
        return []
    result = []
    for p in positions:
        if magic is not None and p.magic != magic:
            continue
        result.append({
            "ticket":      p.ticket,
            "symbol":      p.symbol,
            "type":        "BUY" if p.type == 0 else "SELL",
            "volume":      p.volume,
            "price_open":  p.price_open,
            "price_current": p.price_current,
            "profit":      round(p.profit, 2),
            "sl":          p.sl,
            "tp":          p.tp,
            "magic":       p.magic,
            "comment":     p.comment,
        })
    return result


# ──────────────────────────────────────────────────────────
# Trade execution
# ──────────────────────────────────────────────────────────
def _filling_mode(sym_info: Any) -> int:
    """Auto-detect correct filling mode for broker."""
    if _HAS_UTILS:
        try:
            return mt5_utils.get_symbol_filling_mode(sym_info)
        except ValueError:
            pass
    return getattr(mt5, "ORDER_FILLING_IOC", 1)


def open_trade(symbol: str, direction: str, lot: float,
               sl: float, tp: float, magic: int, comment: str = "ISSBOT") -> dict:
    """
    Open a market BUY or SELL.
    Returns dict with keys: success, ticket, price, error
    """
    if not _HAS_MT5:
        return {"success": False, "error": "MT5 not available"}

    sym = _resolve_symbol(symbol)
    sym_info = mt5.symbol_info(sym)
    if sym_info is None:
        return {"success": False, "error": f"Symbol info unavailable for {sym}"}

    tick = mt5.symbol_info_tick(sym)
    if tick is None:
        return {"success": False, "error": "No tick data"}

    digits = int(getattr(sym_info, "digits", 2))
    point = float(getattr(sym_info, "point", 0.01))

    if direction == "BUY":
        order_type = mt5.ORDER_TYPE_BUY
        price = tick.ask
        # Ensure SL is strictly below current ask and TP strictly above
        if sl > 0 and sl >= price:
            sl = round(price - 50.0, digits)
        if tp > 0 and tp <= price:
            tp = round(price + 80.0, digits)
    else:
        order_type = mt5.ORDER_TYPE_SELL
        price = tick.bid
        # Ensure SL is strictly above current bid and TP strictly below
        if sl > 0 and sl <= price:
            sl = round(price + 50.0, digits)
        if tp > 0 and tp >= price:
            tp = round(price - 80.0, digits)

    filling = _filling_mode(sym_info)

    request = {
        "action":      mt5.TRADE_ACTION_DEAL,
        "symbol":      sym,
        "volume":      float(lot),
        "type":        order_type,
        "price":       float(price),
        "sl":          float(sl),
        "tp":          float(tp),
        "deviation":   20,
        "magic":       int(magic),
        "comment":     comment,
        "type_time":   mt5.ORDER_TIME_GTC,
        "type_filling": filling,
    }

    result = mt5.order_send(request)
    if result is None:
        return {"success": False, "error": str(mt5.last_error())}

    ok = result.retcode in (10008, 10009)
    return {
        "success": ok,
        "ticket":  result.order,
        "price":   result.price,
        "retcode": result.retcode,
        "error":   result.comment if not ok else "",
    }


def close_position(ticket: int, symbol: str, lot: float, pos_type: str) -> dict:
    """
    Close an open position by ticket.
    pos_type: 'BUY' or 'SELL'
    """
    if not _HAS_MT5:
        return {"success": False, "error": "MT5 not available"}

    sym = _resolve_symbol(symbol)
    sym_info = mt5.symbol_info(sym)
    tick = mt5.symbol_info_tick(sym)
    if tick is None or sym_info is None:
        return {"success": False, "error": "No tick / symbol info"}

    # To close a BUY we SELL, and vice versa
    if pos_type == "BUY":
        order_type = mt5.ORDER_TYPE_SELL
        price = tick.bid
    else:
        order_type = mt5.ORDER_TYPE_BUY
        price = tick.ask

    filling = _filling_mode(sym_info)

    request = {
        "action":      mt5.TRADE_ACTION_DEAL,
        "symbol":      sym,
        "volume":      float(lot),
        "type":        order_type,
        "position":    int(ticket),
        "price":       float(price),
        "deviation":   20,
        "magic":       0,
        "comment":     "ISSBOT close",
        "type_time":   mt5.ORDER_TIME_GTC,
        "type_filling": filling,
    }

    result = mt5.order_send(request)
    if result is None:
        return {"success": False, "error": str(mt5.last_error())}

    ok = result.retcode in (10008, 10009)
    return {"success": ok, "retcode": result.retcode, "error": result.comment if not ok else ""}
