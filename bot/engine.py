"""
=============================================================
  ISSSSMAIL SCALPER BOT — Core Trading Engine
  المحرك الأساسي لبوت التداول السكالبر
=============================================================

Strategy:
  • Trade XAUUSD (Gold) and BTCUSD (Bitcoin) only
  • Detect trend using EMA9 / EMA21 crossover + RSI filter
  • Open trades IN the trend direction
  • Small TP target ($0.20–$0.80 per trade) → many small wins
  • Close on loss ($0.50 SL) → open next trade immediately
  • Never stop unless user presses STOP button
  • Daily goal tracking: shows progress, doesn't auto-pause

الاستراتيجية:
  • الذهب والبيتكوين فقط
  • تحليل الاتجاه: EMA تقاطع + RSI
  • صفقات في اتجاه السوق بمكسب قليل وكمية كبيرة
  • وقف خسارة صغير → يغلق ويفتح صفقة جديدة فورًا
  • لا يتوقف إلا بضغطة زرار من المستخدم
"""

import time
import threading
import logging
import json
import os
import math
import datetime
from typing import Optional

from bot import config, analysis, mt5bridge

logger = logging.getLogger("issssmail.engine")


# ──────────────────────────────────────────────────────────
# State file — survives process restart
# ملف الحالة يحفظ سجل الصفقات بين إعادات التشغيل
# ──────────────────────────────────────────────────────────
STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "state.json")


def _load_state() -> dict:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"trades": [], "daily_pnl": 0.0, "session_start": None}


def _save_state(state: dict) -> None:
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.warning("Could not save state: %s", exc)


# ──────────────────────────────────────────────────────────
# ScalperEngine class
# ──────────────────────────────────────────────────────────
class ScalperEngine:
    """
    Main bot engine. Runs in a background thread.
    Call start() to begin, stop() to halt gracefully.
    """

    def __init__(self):
        self._running   = False
        self._thread: Optional[threading.Thread] = None
        self._lock      = threading.Lock()

        # Live status (read by dashboard via get_status())
        self.status      = "STOPPED"       # STOPPED | RUNNING | ERROR
        self.last_signal = {s: "—" for s in config.SYMBOLS}
        self.last_analysis = {s: {} for s in config.SYMBOLS}
        self.last_error  = ""
        self.loop_count  = 0

        # Persistent state
        self._state = _load_state()
        if self._state.get("session_start") is None:
            self._state["session_start"] = datetime.datetime.now().isoformat()

        # Restore saved settings (survive restarts)
        if "settings_daily_goal" in self._state:
            config.DAILY_GOAL_USD = float(self._state["settings_daily_goal"])
        if "settings_tp_usd" in self._state:
            config.TAKE_PROFIT_USD = float(self._state["settings_tp_usd"])
        if "settings_sl_usd" in self._state:
            config.STOP_LOSS_USD = float(self._state["settings_sl_usd"])

    # ── Public API ─────────────────────────────────────────

    def start(self) -> str:
        with self._lock:
            if self._running:
                return "already_running"
            if not mt5bridge.connect():
                self.status = "ERROR"
                self.last_error = "Cannot connect to MT5. Make sure MT5 is running and logged in."
                return "mt5_error"
            self._running = True
            self.status   = "RUNNING"
            self._state["session_start"] = datetime.datetime.now().isoformat()
            _save_state(self._state)
            self._thread = threading.Thread(target=self._loop, daemon=True, name="ScalperBot")
            self._thread.start()
            logger.info("Bot started ✓")
            return "started"

    def stop(self) -> str:
        with self._lock:
            if not self._running:
                return "already_stopped"
            self._running = False
            self.status   = "STOPPED"
        # Wait for thread to finish current cycle
        if self._thread:
            self._thread.join(timeout=15)
        mt5bridge.disconnect()
        logger.info("Bot stopped ✓")
        return "stopped"

    def get_status(self) -> dict:
        """Return full snapshot for dashboard."""
        # Always try to read from MT5 even when bot is stopped
        if not mt5bridge.is_connected():
            mt5bridge.connect()   # read-only connect — no trading started

        acc = mt5bridge.account_info() or {}
        positions = mt5bridge.get_open_positions(magic=config.MAGIC_NUMBER)
        daily_pnl = self._calc_daily_pnl()

        return {
            "bot_status":    self.status,
            "connected":     mt5bridge.is_connected(),
            "last_error":    self.last_error,
            "loop_count":    self.loop_count,
            "account": {
                "balance":   acc.get("balance", 0.0),
                "equity":    acc.get("equity", 0.0),
                "profit":    acc.get("profit", 0.0),
                "currency":  acc.get("currency", "USD"),
                "login":     acc.get("login", "—"),
            },
            "daily": {
                "pnl":        round(daily_pnl, 2),
                "goal":       config.DAILY_GOAL_USD,
                "goal_pct":   round(min((daily_pnl / config.DAILY_GOAL_USD) * 100, 100), 1) if config.DAILY_GOAL_USD > 0 else 0,
                "goal_hit":   daily_pnl >= config.DAILY_GOAL_USD,
                "max_loss":   config.MAX_DAILY_LOSS_USD,
                "loss_hit":   daily_pnl <= -config.MAX_DAILY_LOSS_USD,
            },
            "open_positions": positions,
            "positions_count": len(positions),
            "signals":        self.last_signal,
            "analysis":       self.last_analysis,
            "trades":         self._state.get("trades", [])[-50:],   # last 50
            "trade_count":    len(self._state.get("trades", [])),
            "session_start":  self._state.get("session_start", ""),
            "timestamp":      datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "config": {
                "symbols":    config.SYMBOLS,
                "lot_size":   config.LOT_SIZE,
                "tp_usd":     config.TAKE_PROFIT_USD,
                "sl_usd":     config.STOP_LOSS_USD,
                "scan_sec":   config.SCAN_INTERVAL_SEC,
                "daily_goal": config.DAILY_GOAL_USD,
            }
        }

    def set_daily_goal(self, usd: float) -> None:
        config.DAILY_GOAL_USD = usd
        self._state["settings_daily_goal"] = usd
        _save_state(self._state)

    def set_tp(self, usd: float) -> None:
        config.TAKE_PROFIT_USD = usd
        self._state["settings_tp_usd"] = usd
        _save_state(self._state)

    def set_sl(self, usd: float) -> None:
        config.STOP_LOSS_USD = usd
        self._state["settings_sl_usd"] = usd
        _save_state(self._state)

    # ── Internal loop ──────────────────────────────────────

    def _loop(self):
        """Main bot loop — runs until self._running is False."""
        logger.info("Bot loop started. Symbols: %s", config.SYMBOLS)
        while self._running:
            try:
                self.loop_count += 1
                self._tick()
            except Exception as exc:
                logger.exception("Unexpected error in bot loop: %s", exc)
                self.last_error = str(exc)
            # Sleep between scans — check _running every second
            for _ in range(config.SCAN_INTERVAL_SEC):
                if not self._running:
                    break
                time.sleep(1)
        logger.info("Bot loop exited.")

    def _tick(self):
        """One iteration: analyze → sync closed trades → manage open → open new if needed."""
        if not mt5bridge.is_connected():
            if not mt5bridge.connect():
                self.status     = "ERROR"
                self.last_error = "MT5 disconnected"
                return
            else:
                self.status = "RUNNING"

        # ── Sync closed trades from MT5 history first ──────
        self._sync_closed_trades()

        daily_pnl = self._calc_daily_pnl()

        # ── Risk guard: stop trading if max loss hit ───────
        if daily_pnl <= -config.MAX_DAILY_LOSS_USD:
            logger.warning("Max daily loss hit (%.2f). Pausing entries.", daily_pnl)
            return

        open_positions = mt5bridge.get_open_positions(magic=config.MAGIC_NUMBER)

        for symbol in config.SYMBOLS:
            if not self._running:
                return
            self._process_symbol(symbol, open_positions, daily_pnl)

    def _process_symbol(self, symbol: str, open_positions: list[dict], daily_pnl: float):
        """Analyze one symbol and act."""

        # ── 1. Manage existing positions for this symbol ───
        sym_positions = [p for p in open_positions if p["symbol"].startswith(symbol[:3])]

        for pos in sym_positions:
            self._manage_position(pos)

        # ── 2. Refresh open positions after any closes ─────
        open_positions = mt5bridge.get_open_positions(magic=config.MAGIC_NUMBER)
        sym_positions  = [p for p in open_positions if p["symbol"].startswith(symbol[:3])]
        total_open     = len(mt5bridge.get_open_positions(magic=config.MAGIC_NUMBER))

        # ── 3. Try to open new position if slot available ──
        if len(sym_positions) == 0 and total_open < config.MAX_OPEN_POSITIONS:
            self._try_open(symbol)

    def _manage_position(self, pos: dict):
        """Check if a position should be closed (USD-based TP/SL)."""
        profit = pos["profit"]

        should_close = False
        reason = ""

        if profit >= config.TAKE_PROFIT_USD:
            should_close = True
            reason = f"TP hit: +${profit:.2f}"
        elif profit <= -config.STOP_LOSS_USD:
            should_close = True
            reason = f"SL hit: -${abs(profit):.2f}"

        if should_close:
            logger.info("Closing %s #%d — %s", pos["symbol"], pos["ticket"], reason)
            result = mt5bridge.close_position(
                ticket   = pos["ticket"],
                symbol   = pos["symbol"],
                lot      = pos["volume"],
                pos_type = pos["type"],
            )
            if result["success"]:
                self._record_trade({
                    "ticket":   pos["ticket"],
                    "symbol":   pos["symbol"],
                    "type":     pos["type"],
                    "profit":   profit,
                    "reason":   reason,
                    "time":     datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
                logger.info("Closed ✓  profit=%.2f", profit)
            else:
                logger.warning("Close failed: %s", result.get("error"))

    def _try_open(self, symbol: str):
        """Analyze and open a position if signal is clear."""
        candles = mt5bridge.get_candles(symbol, timeframe=config.TREND_TF, count=config.CANDLES_NEEDED + 10)

        result = analysis.analyze(candles)
        self.last_signal[symbol]   = result["signal"]
        self.last_analysis[symbol] = result

        if result["signal"] == analysis.SIGNAL_WAIT:
            logger.debug("[%s] WAIT — %s", symbol, result["reason"])
            return

        # ── Get tick and symbol info ────────────────────────
        tick = mt5bridge.get_tick(symbol)
        if tick is None:
            return

        sym_info = mt5bridge.get_symbol_info(symbol)
        if sym_info is None:
            return

        point  = float(getattr(sym_info, "point",  0.001))
        digits = int(getattr(sym_info, "digits",   3))

        # tick_value = profit per 1 lot per 1 tick move
        tick_value = float(getattr(sym_info, "trade_tick_value", 0.0))
        tick_size  = float(getattr(sym_info, "trade_tick_size",  point))
        if tick_value <= 0 or tick_size <= 0:
            tick_value = 1.0
            tick_size  = point

        # value per 1 point move for LOT_SIZE lots
        value_per_point = (tick_value / tick_size) * point * config.LOT_SIZE

        # Convert USD target to points (minimum 50 points as floor)
        if value_per_point > 0:
            sl_pts = max(50, int(config.STOP_LOSS_USD    / value_per_point) + 10)
            tp_pts = max(50, int(config.TAKE_PROFIT_USD  / value_per_point) + 10)
        else:
            sl_pts = 500
            tp_pts = 500

        # Respect broker minimum stop level
        broker_min = int(getattr(sym_info, "trade_stops_level", 0))
        sl_pts = max(sl_pts, broker_min + 10)
        tp_pts = max(tp_pts, broker_min + 10)

        spread_pts = max(0, int((tick["ask"] - tick["bid"]) / point))
        sl_pts = max(sl_pts, spread_pts * 3)   # at least 3× spread
        tp_pts = max(tp_pts, spread_pts * 3)

        logger.info("[%s] value_per_point=%.6f  sl_pts=%d  tp_pts=%d  spread_pts=%d",
                    symbol, value_per_point, sl_pts, tp_pts, spread_pts)

        if result["signal"] == analysis.SIGNAL_BUY:
            entry     = tick["ask"]
            sl        = round(entry - sl_pts * point, digits)
            tp        = round(entry + tp_pts * point, digits)
            direction = "BUY"
        else:
            entry     = tick["bid"]
            sl        = round(entry + sl_pts * point, digits)
            tp        = round(entry - tp_pts * point, digits)
            direction = "SELL"

        logger.info("[%s] Signal=%s entry=%.5f sl=%.5f tp=%.5f", symbol, direction, entry, sl, tp)

        trade_result = mt5bridge.open_trade(
            symbol    = symbol,
            direction = direction,
            lot       = config.LOT_SIZE,
            sl        = sl,
            tp        = tp,
            magic     = config.MAGIC_NUMBER,
            comment   = f"ISSBOT_{direction[:1]}",
        )

        if trade_result["success"]:
            logger.info("Opened %s #%d @ %.5f", direction, trade_result["ticket"], trade_result["price"])
            self.last_error = ""
            self._record_trade({
                "ticket":   trade_result["ticket"],
                "symbol":   symbol,
                "type":     direction,
                "profit":   None,
                "reason":   "OPENED",
                "analysis": result["reason"],
                "time":     datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
        else:
            err = trade_result.get("error", "unknown")
            logger.warning("Trade open failed: %s", err)
            self.last_error = f"[{symbol}] {err}"

    # ── Helpers ────────────────────────────────────────────

    def _sync_closed_trades(self):
        """
        Read today's closed deals from MT5 history and update the trade log.
        Catches SL/TP closes that happen inside the broker without _manage_position seeing them.
        """
        closed_deals = mt5bridge.get_today_closed_deals(magic=config.MAGIC_NUMBER)
        if not closed_deals:
            return

        trades     = self._state.setdefault("trades", [])
        seen_deals = {t.get("deal_ticket") for t in trades if t.get("deal_ticket")}

        changed = False
        for deal in closed_deals:
            if deal["ticket"] in seen_deals:
                continue   # already recorded

            profit = deal["profit"]
            reason = "TP ✅" if profit >= 0 else "SL ❌"

            # Update existing OPENED record if position_id matches
            matched = False
            for t in trades:
                if t.get("ticket") == deal["position_id"] and t.get("reason") == "OPENED":
                    t["profit"]      = profit
                    t["reason"]      = reason
                    t["close_time"]  = deal["time"]
                    t["deal_ticket"] = deal["ticket"]
                    matched = True
                    changed = True
                    logger.info("Trade #%d closed — profit=%.2f (%s)", deal["position_id"], profit, reason)
                    break

            if not matched:
                trades.append({
                    "ticket":      deal["position_id"],
                    "deal_ticket": deal["ticket"],
                    "symbol":      deal["symbol"],
                    "type":        deal["type"],
                    "profit":      profit,
                    "reason":      reason,
                    "time":        deal["time"],
                })
                changed = True
                logger.info("New closed trade recorded — profit=%.2f (%s)", profit, reason)

        if changed:
            _save_state(self._state)

    def _calc_daily_pnl(self) -> float:
        """Sum of profits from today's closed trades + current floating P&L."""
        trades = self._state.get("trades", [])
        today  = datetime.date.today().isoformat()
        closed = sum(
            t["profit"] for t in trades
            if t.get("profit") is not None and t.get("time", "").startswith(today) and t.get("reason") != "OPENED"
        )
        floating = sum(
            p["profit"]
            for p in mt5bridge.get_open_positions(magic=config.MAGIC_NUMBER)
        )
        return closed + floating

    def _record_trade(self, trade: dict) -> None:
        self._state.setdefault("trades", []).append(trade)
        _save_state(self._state)
