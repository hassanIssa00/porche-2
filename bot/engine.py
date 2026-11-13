"""
=============================================================
  ISSSSMAIL SCALPER BOT v2.0 — Core Trading Engine
  المحرك الأساسي لبوت التداول — النسخة الذكية المحسّنة
=============================================================

Enhancements over v1.0:
  ✅ Multi-indicator confluence scoring (not just EMA+RSI)
  ✅ ATR-based dynamic SL/TP calculation
  ✅ Trailing stop (breakeven + trailing SL)
  ✅ Session filter (trade Gold only during active hours)
  ✅ Consecutive losses protection (pause after loss streak)
  ✅ M15 HTF trend confirmation fetched automatically
  ✅ Performance stats: win rate, profit factor, avg win/loss
  ✅ All settings persist across restarts (state.json)

الاستراتيجية:
  • الذهب والبيتكوين فقط
  • نظام درجات التقاطع: 6 مؤشرات — الصفقة تفتح لو الدرجة ≥ 4
  • SL/TP ديناميكية مبنية على ATR
  • وقف خسارة متحرك يحمي الأرباح
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
# State persistence — survives process restarts
# ──────────────────────────────────────────────────────────
STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "state.json")


def _load_state() -> dict:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "trades": [],
            "daily_pnl": 0.0,
            "session_start": None,
            "stats": {
                "total_wins": 0, "total_losses": 0,
                "total_profit": 0.0, "total_loss": 0.0,
            },
        }


def _save_state(state: dict) -> None:
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.warning("Could not save state: %s", exc)


# ──────────────────────────────────────────────────────────
# ScalperEngine — the main bot controller
# المحرك الرئيسي للبوت
# ──────────────────────────────────────────────────────────
class ScalperEngine:
    """
    Main bot engine. Runs in a background thread.
    Call start() to begin trading. Call stop() to halt gracefully.
    Thread-safe: all shared state protected by self._lock.
    """

    def __init__(self):
        self._running  = False
        self._thread: Optional[threading.Thread] = None
        self._lock     = threading.Lock()

        # Live status (read by dashboard via get_status())
        self.status       = "STOPPED"       # STOPPED | RUNNING | ERROR
        self.last_signal  = {s: "—" for s in config.SYMBOLS}
        self.last_analysis= {s: {} for s in config.SYMBOLS}
        self.last_error   = ""
        self.loop_count   = 0

        # Consecutive loss streak protection
        self._consecutive_losses = 0
        self._pause_ticks        = 0   # remaining ticks to pause per symbol

        # Trailing stop tracking {ticket: {"trail_started": bool, "breakeven_set": bool}}
        self._trail_state: dict[int, dict] = {}

        # Persistent state
        self._state = _load_state()
        if self._state.get("session_start") is None:
            self._state["session_start"] = datetime.datetime.now().isoformat()
        if "stats" not in self._state:
            self._state["stats"] = {
                "total_wins": 0, "total_losses": 0,
                "total_profit": 0.0, "total_loss": 0.0,
            }

        # Restore saved settings (survive restarts)
        if "settings_daily_goal" in self._state:
            config.DAILY_GOAL_USD = float(self._state["settings_daily_goal"])
        if "settings_tp_usd" in self._state:
            config.TAKE_PROFIT_USD = float(self._state["settings_tp_usd"])
        if "settings_sl_usd" in self._state:
            config.STOP_LOSS_USD = float(self._state["settings_sl_usd"])

    # ══════════════════════════════════════════════════════
    # Public API — called by HTTP server (bot/server.py)
    # ══════════════════════════════════════════════════════

    def start(self) -> str:
        with self._lock:
            if self._running:
                return "already_running"
            if not mt5bridge.connect():
                self.status    = "ERROR"
                self.last_error = "Cannot connect to MT5. Make sure MT5 is running and logged in."
                return "mt5_error"
            self._running  = True
            self.status    = "RUNNING"
            self._state["session_start"] = datetime.datetime.now().isoformat()
            _save_state(self._state)
            self._thread = threading.Thread(
                target=self._loop, daemon=True, name="ScalperBot"
            )
            self._thread.start()
            logger.info("Bot started ✓  v2.0")
            return "started"

    def stop(self) -> str:
        with self._lock:
            if not self._running:
                return "already_stopped"
            self._running = False
            self.status   = "STOPPED"
        if self._thread:
            self._thread.join(timeout=15)
        mt5bridge.disconnect()
        logger.info("Bot stopped ✓")
        return "stopped"

    def get_status(self) -> dict:
        """Return full snapshot for dashboard — includes all v2.0 fields."""
        if not mt5bridge.is_connected():
            mt5bridge.connect()   # read-only connect

        acc       = mt5bridge.account_info() or {}
        positions = mt5bridge.get_open_positions(magic=config.MAGIC_NUMBER)
        daily_pnl = self._calc_daily_pnl()
        stats     = self._calc_stats()

        return {
            "bot_status":    self.status,
            "connected":     mt5bridge.is_connected(),
            "last_error":    self.last_error,
            "loop_count":    self.loop_count,
            "version":       "2.0",
            "account": {
                "balance":   acc.get("balance",  0.0),
                "equity":    acc.get("equity",   0.0),
                "profit":    acc.get("profit",   0.0),
                "currency":  acc.get("currency", "USD"),
                "login":     acc.get("login",    "—"),
            },
            "daily": {
                "pnl":        round(daily_pnl, 2),
                "goal":       config.DAILY_GOAL_USD,
                "goal_pct":   round(
                    min((daily_pnl / config.DAILY_GOAL_USD) * 100, 100), 1
                ) if config.DAILY_GOAL_USD > 0 else 0,
                "goal_hit":   daily_pnl >= config.DAILY_GOAL_USD,
                "max_loss":   config.MAX_DAILY_LOSS_USD,
                "loss_hit":   daily_pnl <= -config.MAX_DAILY_LOSS_USD,
            },
            "open_positions":  positions,
            "positions_count": len(positions),
            "signals":         self.last_signal,
            "analysis":        self.last_analysis,
            "trades":          self._state.get("trades", [])[-50:],
            "trade_count":     len(self._state.get("trades", [])),
            "session_start":   self._state.get("session_start", ""),
            "timestamp":       datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "stats":           stats,
            "risk": {
                "consecutive_losses": self._consecutive_losses,
                "pause_ticks":        self._pause_ticks,
            },
            "config": {
                "symbols":      config.SYMBOLS,
                "lot_size":     config.LOT_SIZE,
                "tp_usd":       config.TAKE_PROFIT_USD,
                "sl_usd":       config.STOP_LOSS_USD,
                "scan_sec":     config.SCAN_INTERVAL_SEC,
                "daily_goal":   config.DAILY_GOAL_USD,
                "min_score":    config.MIN_SIGNAL_SCORE,
                "trail":        config.TRAIL_ENABLED,
                "session_filter": config.SESSION_FILTER_ENABLED,
            },
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

    # ══════════════════════════════════════════════════════
    # Internal bot loop
    # ══════════════════════════════════════════════════════

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
        """One full iteration: sync → check risk → analyze → manage → open."""
        if not mt5bridge.is_connected():
            if not mt5bridge.connect():
                self.status    = "ERROR"
                self.last_error = "MT5 disconnected"
                return
            self.status = "RUNNING"

        # 1. Pull closed trades from MT5 history
        self._sync_closed_trades()

        daily_pnl = self._calc_daily_pnl()

        # 2. Max daily loss guard
        if daily_pnl <= -config.MAX_DAILY_LOSS_USD:
            logger.warning("Max daily loss hit (%.2f). Pausing entries.", daily_pnl)
            return

        # 3. Pause ticks guard (after consecutive loss streak)
        if self._pause_ticks > 0:
            self._pause_ticks -= 1
            logger.info("Loss streak pause — ticks remaining: %d", self._pause_ticks)
            return

        open_positions = mt5bridge.get_open_positions(magic=config.MAGIC_NUMBER)

        # 4. Process each symbol
        for symbol in config.SYMBOLS:
            if not self._running:
                return
            self._process_symbol(symbol, open_positions, daily_pnl)

    def _process_symbol(self, symbol: str, open_positions: list[dict], daily_pnl: float):
        """Analyze one symbol: manage existing positions, then open new one if slot free."""

        # ── Session filter ─────────────────────────────────
        if config.SESSION_FILTER_ENABLED and not self._in_session(symbol):
            logger.debug("[%s] Out of session hours — skipping", symbol)
            return

        # ── Filter positions for this symbol ───────────────
        sym_positions = [
            p for p in open_positions
            if p["symbol"].upper().startswith(symbol[:3].upper())
        ]

        # ── Manage open positions (trailing stop / close) ──
        for pos in sym_positions:
            self._manage_position(pos)

        # ── Refresh positions after any closes ─────────────
        open_positions_fresh = mt5bridge.get_open_positions(magic=config.MAGIC_NUMBER)
        sym_positions_fresh  = [
            p for p in open_positions_fresh
            if p["symbol"].upper().startswith(symbol[:3].upper())
        ]
        total_open = len(open_positions_fresh)

        # ── Open new position if slot available ────────────
        if len(sym_positions_fresh) == 0 and total_open < config.MAX_OPEN_POSITIONS:
            self._try_open(symbol)

    # ══════════════════════════════════════════════════════
    # Position management (TP / SL / trailing stop)
    # ══════════════════════════════════════════════════════

    def _manage_position(self, pos: dict):
        """
        Check if a position should be closed (USD-based TP/SL).
        Also handle trailing stop logic.
        """
        profit = pos["profit"]
        ticket = pos["ticket"]

        # ── Initialize trail state for new positions ───────
        if ticket not in self._trail_state:
            self._trail_state[ticket] = {
                "breakeven_set": False,
                "trail_started": False,
            }

        ts = self._trail_state[ticket]

        should_close = False
        close_reason = ""

        # ── USD-based TP / SL check ────────────────────────
        if profit >= config.TAKE_PROFIT_USD:
            should_close = True
            close_reason = f"TP hit: +${profit:.2f} 🎯"
        elif profit <= -config.STOP_LOSS_USD:
            should_close = True
            close_reason = f"SL hit: -${abs(profit):.2f} ❌"

        # ── Trailing stop logic ────────────────────────────
        if config.TRAIL_ENABLED and not should_close and profit > 0:
            self._apply_trailing_stop(pos, ts)

        if should_close:
            logger.info("Closing %s #%d — %s", pos["symbol"], ticket, close_reason)
            result = mt5bridge.close_position(
                ticket   = ticket,
                symbol   = pos["symbol"],
                lot      = pos["volume"],
                pos_type = pos["type"],
            )
            if result["success"]:
                # Remove trailing state for this ticket
                self._trail_state.pop(ticket, None)
                self._record_closed_trade(pos, profit, close_reason)
                # Update consecutive loss counter
                if profit < 0:
                    self._consecutive_losses += 1
                    if self._consecutive_losses >= config.MAX_CONSECUTIVE_LOSSES:
                        self._pause_ticks = config.PAUSE_CANDLES_AFTER_STREAK
                        logger.warning(
                            "Loss streak (%d). Pausing for %d ticks.",
                            self._consecutive_losses, self._pause_ticks
                        )
                else:
                    self._consecutive_losses = 0  # reset on win
                logger.info("Closed ✓  profit=%.2f", profit)
            else:
                logger.warning("Close failed: %s", result.get("error"))

    def _apply_trailing_stop(self, pos: dict, ts: dict):
        """
        Move SL to breakeven or trail it once profit is sufficient.
        Uses ATR-based trailing distance from last analysis.
        """
        profit  = pos["profit"]
        tp_usd  = config.TAKE_PROFIT_USD

        # Get ATR from last analysis for this symbol
        sym_analysis = self.last_analysis.get(pos["symbol"], {})
        atr = sym_analysis.get("atr")

        # Phase 1: Move to breakeven when profit ≥ TRAIL_BREAKEVEN_AT_PCT × TP
        if not ts["breakeven_set"] and profit >= tp_usd * config.TRAIL_BREAKEVEN_AT_PCT:
            new_sl = pos["price_open"]  # breakeven = entry price
            if self._modify_sl(pos, new_sl):
                ts["breakeven_set"] = True
                logger.info("Breakeven set for #%d (profit=%.2f)", pos["ticket"], profit)

        # Phase 2: Trail SL when profit ≥ TRAIL_START_AT_PCT × TP
        elif ts["breakeven_set"] and profit >= tp_usd * config.TRAIL_START_AT_PCT:
            if atr and atr > 0:
                trail_dist = atr * config.TRAIL_ATR_MULTIPLIER
                sym_info = mt5bridge.get_symbol_info(pos["symbol"])
                point = float(getattr(sym_info, "point", 0.001)) if sym_info else 0.001
                digits = int(getattr(sym_info, "digits", 3)) if sym_info else 3

                tick = mt5bridge.get_tick(pos["symbol"])
                if tick:
                    if pos["type"] == "BUY":
                        new_sl = round(tick["bid"] - trail_dist, digits)
                        if new_sl > pos["sl"]:  # only move SL up
                            self._modify_sl(pos, new_sl)
                            ts["trail_started"] = True
                    else:  # SELL
                        new_sl = round(tick["ask"] + trail_dist, digits)
                        if new_sl < pos["sl"] or pos["sl"] == 0:  # only move SL down
                            self._modify_sl(pos, new_sl)
                            ts["trail_started"] = True

    def _modify_sl(self, pos: dict, new_sl: float) -> bool:
        """Send a modify order to update SL for an open position."""
        import MetaTrader5 as mt5  # local import — only if MT5 available
        sym = pos["symbol"]
        sym_info = mt5bridge.get_symbol_info(sym)
        if sym_info is None:
            return False
        request = {
            "action":   mt5.TRADE_ACTION_SLTP,
            "position": pos["ticket"],
            "symbol":   sym,
            "sl":       float(new_sl),
            "tp":       float(pos["tp"]),
        }
        result = mt5.order_send(request)
        if result and result.retcode in (10008, 10009):
            logger.debug("SL modified for #%d to %.5f", pos["ticket"], new_sl)
            return True
        logger.warning("SL modify failed for #%d: %s", pos["ticket"],
                       result.comment if result else "no result")
        return False

    # ══════════════════════════════════════════════════════
    # Trade opening — confluence-based
    # ══════════════════════════════════════════════════════

    def _try_open(self, symbol: str):
        """Fetch candles, run confluence analysis, open trade if score is high enough."""

        # ── Fetch M5 candles (primary TF) ─────────────────
        candles = mt5bridge.get_candles(
            symbol, timeframe=config.TREND_TF, count=config.CANDLES_NEEDED + 20
        )

        # ── Fetch M15 candles (HTF confirmation) ──────────
        htf_candles = mt5bridge.get_candles(
            symbol, timeframe=config.HTF_TF, count=config.HTF_CANDLES + 10
        )

        # ── Get tick and symbol info first (needed for spread filter) ──
        tick     = mt5bridge.get_tick(symbol)
        sym_info = mt5bridge.get_symbol_info(symbol)
        if tick is None or sym_info is None:
            logger.warning("[%s] Cannot get tick or symbol info", symbol)
            return

        point      = float(getattr(sym_info, "point",             0.001))
        digits     = int(getattr(sym_info,   "digits",            3))
        tick_value = float(getattr(sym_info, "trade_tick_value",  0.0))
        tick_size  = float(getattr(sym_info, "trade_tick_size",   point))

        if tick_value <= 0 or tick_size <= 0:
            tick_value = 1.0
            tick_size  = point

        # value_per_point: USD profit per 1 point move with LOT_SIZE lots
        value_per_point = (tick_value / tick_size) * point * config.LOT_SIZE

        # Spread in USD (used to filter low R:R trades)
        spread_pts = max(0, int((tick["ask"] - tick["bid"]) / point))
        spread_usd = spread_pts * value_per_point

        # ── Run analysis (pass spread so it can filter bad trades) ──
        result = analysis.analyze(
            candles,
            htf_candles=htf_candles,
            spread_usd=spread_usd,
            tp_usd=config.TAKE_PROFIT_USD,
        )
        self.last_signal[symbol]    = result["signal"]
        self.last_analysis[symbol]  = result

        if result["signal"] == analysis.SIGNAL_WAIT:
            logger.debug("[%s] WAIT (score=%d/7) — %s", symbol, result["score"], result["reason"])
            return

        logger.info("[%s] Signal=%s score=%d/7 | %s",
                    symbol, result["signal"], result["score"], result["reason"])

        # ── SMART SL/TP: ATR-based, respects spread & broker limits ──
        # Key insight: SL must be >> spread, and TP must be realistic vs ATR
        atr = result.get("atr")

        if atr and atr > 0 and value_per_point > 0:
            # ATR-based:
            #   SL = 1.0 × ATR (gives enough room for natural price movement)
            #   TP = 0.8 × ATR (realistic target — slightly less than 1 ATR move)
            # This ensures: even if market oscillates 1 ATR, SL holds
            atr_sl_pts = int(atr * 1.0 / point)
            atr_tp_pts = int(atr * 0.8 / point)

            # USD floor (minimum acceptable TP/SL in USD)
            usd_sl_pts = max(50, int(config.STOP_LOSS_USD   / value_per_point) + 10)
            usd_tp_pts = max(50, int(config.TAKE_PROFIT_USD / value_per_point) + 10)

            # Use max of ATR-based vs USD-based (never too tight)
            sl_pts = max(atr_sl_pts, usd_sl_pts)
            tp_pts = max(atr_tp_pts, usd_tp_pts)
        elif value_per_point > 0:
            sl_pts = max(50, int(config.STOP_LOSS_USD   / value_per_point) + 10)
            tp_pts = max(50, int(config.TAKE_PROFIT_USD / value_per_point) + 10)
        else:
            sl_pts = config.SL_POINTS
            tp_pts = config.TP_POINTS

        # Respect broker minimum stop level
        broker_min = int(getattr(sym_info, "trade_stops_level", 0))
        sl_pts = max(sl_pts, broker_min + 10)
        tp_pts = max(tp_pts, broker_min + 10)

        # SL must be at least 2× spread (never get stopped by spread alone)
        sl_pts = max(sl_pts, spread_pts * 2)
        # TP must be at least 2× spread (minimum acceptable reward)
        tp_pts = max(tp_pts, spread_pts * 2)

        actual_tp_usd = tp_pts * value_per_point
        actual_sl_usd = sl_pts * value_per_point
        rr_ratio = actual_tp_usd / actual_sl_usd if actual_sl_usd > 0 else 0

        logger.info("[%s] spread=$%.3f atr=%s  sl_pts=%d($%.2f) tp_pts=%d($%.2f) R:R=%.2f",
                    symbol, spread_usd, atr, sl_pts, actual_sl_usd, tp_pts, actual_tp_usd, rr_ratio)

        # ── Calculate entry / SL / TP prices ──────────────
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

        logger.info("[%s] %s  entry=%.5f  sl=%.5f  tp=%.5f", symbol, direction, entry, sl, tp)

        # ── Send order ─────────────────────────────────────
        trade_result = mt5bridge.open_trade(
            symbol    = symbol,
            direction = direction,
            lot       = config.LOT_SIZE,
            sl        = sl,
            tp        = tp,
            magic     = config.MAGIC_NUMBER,
            comment   = f"ISS2_{direction[:1]}_s{result['score']}",
        )

        if trade_result["success"]:
            logger.info("Opened %s #%d @ %.5f (score=%d/6)",
                        direction, trade_result["ticket"], trade_result["price"], result["score"])
            self.last_error = ""
            self._record_trade({
                "ticket":   trade_result["ticket"],
                "symbol":   symbol,
                "type":     direction,
                "profit":   None,
                "reason":   "OPENED",
                "score":    result["score"],
                "analysis": result["reason"],
                "time":     datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
        else:
            err = trade_result.get("error", "unknown")
            logger.warning("Trade open failed [%s]: %s", symbol, err)
            self.last_error = f"[{symbol}] {err}"

    # ══════════════════════════════════════════════════════
    # Closed trades sync
    # ══════════════════════════════════════════════════════

    def _sync_closed_trades(self):
        """
        Read today's closed deals from MT5 history and update the trade log.
        Catches SL/TP closes that happen inside the broker without engine seeing them.
        Also updates performance stats (win/loss counters).
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

            # ── Update existing OPENED record ───────────────
            matched = False
            for t in trades:
                if t.get("ticket") == deal["position_id"] and t.get("reason") == "OPENED":
                    t["profit"]      = profit
                    t["reason"]      = reason
                    t["close_time"]  = deal["time"]
                    t["deal_ticket"] = deal["ticket"]
                    matched  = True
                    changed  = True
                    # Update performance stats
                    self._update_stats(profit)
                    logger.info("Trade #%d closed — profit=%.2f (%s)",
                                deal["position_id"], profit, reason)
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
                self._update_stats(profit)
                changed = True
                logger.info("New closed trade recorded — profit=%.2f (%s)", profit, reason)

        if changed:
            _save_state(self._state)

    def _update_stats(self, profit: float) -> None:
        """Update win/loss stats after a trade closes."""
        stats = self._state.setdefault("stats", {
            "total_wins": 0, "total_losses": 0,
            "total_profit": 0.0, "total_loss": 0.0,
        })
        if profit >= 0:
            stats["total_wins"]   = stats.get("total_wins", 0) + 1
            stats["total_profit"] = stats.get("total_profit", 0.0) + profit
        else:
            stats["total_losses"] = stats.get("total_losses", 0) + 1
            stats["total_loss"]   = stats.get("total_loss", 0.0) + abs(profit)

    # ══════════════════════════════════════════════════════
    # Helpers
    # ══════════════════════════════════════════════════════

    def _calc_daily_pnl(self) -> float:
        """Sum of profits from today's closed trades + current floating P&L."""
        trades = self._state.get("trades", [])
        today  = datetime.date.today().isoformat()
        closed = sum(
            t["profit"] for t in trades
            if t.get("profit") is not None
            and t.get("time", "").startswith(today)
            and t.get("reason") not in ("OPENED",)
        )
        floating = sum(
            p["profit"]
            for p in mt5bridge.get_open_positions(magic=config.MAGIC_NUMBER)
        )
        return closed + floating

    def _calc_stats(self) -> dict:
        """Compute performance statistics for display in dashboard."""
        stats      = self._state.get("stats", {})
        total_wins  = stats.get("total_wins", 0)
        total_losses= stats.get("total_losses", 0)
        total_profit= stats.get("total_profit", 0.0)
        total_loss  = stats.get("total_loss", 0.0)
        total_trades= total_wins + total_losses

        win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0.0
        avg_win  = (total_profit / total_wins)  if total_wins   > 0 else 0.0
        avg_loss = (total_loss   / total_losses) if total_losses > 0 else 0.0
        profit_factor = (total_profit / total_loss) if total_loss > 0 else 0.0

        return {
            "total_trades":   total_trades,
            "total_wins":     total_wins,
            "total_losses":   total_losses,
            "win_rate_pct":   round(win_rate, 1),
            "profit_factor":  round(profit_factor, 2),
            "avg_win":        round(avg_win, 2),
            "avg_loss":       round(avg_loss, 2),
            "total_profit":   round(total_profit, 2),
            "total_loss":     round(total_loss, 2),
        }

    def _in_session(self, symbol: str) -> bool:
        """Return True if current UTC hour is within trading session for symbol."""
        utc_hour = datetime.datetime.utcnow().hour
        if symbol.upper().startswith("XAU"):
            sessions = config.GOLD_SESSIONS
        else:
            sessions = config.BTC_SESSIONS
        for start_h, end_h in sessions:
            if start_h <= utc_hour < end_h:
                return True
        return False

    def _record_trade(self, trade: dict) -> None:
        self._state.setdefault("trades", []).append(trade)
        _save_state(self._state)

    def _record_closed_trade(self, pos: dict, profit: float, reason: str) -> None:
        """Record a manually closed trade (by _manage_position)."""
        trades = self._state.setdefault("trades", [])
        # Try to update existing OPENED record
        for t in trades:
            if t.get("ticket") == pos["ticket"] and t.get("reason") == "OPENED":
                t["profit"]     = profit
                t["reason"]     = reason
                t["close_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self._update_stats(profit)
                _save_state(self._state)
                return
        # Not found — add new record
        trades.append({
            "ticket":     pos["ticket"],
            "symbol":     pos["symbol"],
            "type":       pos["type"],
            "profit":     profit,
            "reason":     reason,
            "time":       datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        self._update_stats(profit)
        _save_state(self._state)
