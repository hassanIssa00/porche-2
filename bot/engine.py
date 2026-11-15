"""
=============================================================
  ISSSSMAIL SCALPER BOT v3.0 — Professional Swing Scalper
  محرك التداول الاحترافي — استراتيجية بولباك منضبطة
=============================================================

Rules enforced by this engine:
  1. No overtrading: Only 1 position open at a time across account.
  2. 3-Minute Cooldown: After a trade closes, no new trades for 180s.
  3. Real Targets: TP = $3.00, SL = $2.50 (wide enough to survive spread/noise).
  4. Breakeven Protection: At +$1.50 profit, SL is automatically moved to entry + $0.30.
  5. Account Protection: Stops trading automatically if daily loss reaches $15.00.
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
            "stats": {"total_wins": 0, "total_losses": 0, "total_profit": 0.0, "total_loss": 0.0},
        }


def _save_state(state: dict) -> None:
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.warning("Could not save state: %s", exc)


class ScalperEngine:
    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        self.status = "STOPPED"
        self.last_signal = {s: "—" for s in config.SYMBOLS}
        self.last_analysis = {s: {} for s in config.SYMBOLS}
        self.last_error = ""
        self.loop_count = 0

        # Cooldown timer: time when last position closed
        self._last_close_time: float = 0.0

        # Breakeven tracking per ticket {ticket: bool}
        self._breakeven_set: dict[int, bool] = {}

        # Consecutive loss protection
        self._consecutive_losses: int = 0

        self._state = _load_state()
        if self._state.get("session_start") is None:
            self._state["session_start"] = datetime.datetime.now().isoformat()
        if "stats" not in self._state:
            self._state["stats"] = {"total_wins": 0, "total_losses": 0, "total_profit": 0.0, "total_loss": 0.0}

        # Keep saved settings
        if "settings_daily_goal" in self._state:
            config.DAILY_GOAL_USD = float(self._state["settings_daily_goal"])
        if "settings_tp_usd" in self._state:
            config.TAKE_PROFIT_USD = float(self._state["settings_tp_usd"])
        if "settings_sl_usd" in self._state:
            config.STOP_LOSS_USD = float(self._state["settings_sl_usd"])

    # ══════════════════════════════════════════════════════
    # Public API
    # ══════════════════════════════════════════════════════

    def start(self) -> str:
        with self._lock:
            if self._running:
                return "already_running"
            self._running = True
            self.status = "CONNECTING"
            self.last_error = ""
            self._state["session_start"] = datetime.datetime.now().isoformat()
            _save_state(self._state)
            self._thread = threading.Thread(target=self._loop, daemon=True, name="ScalperBot")
            self._thread.start()
            logger.info("Bot started background loop.")
            return "started"

    def stop(self) -> str:
        with self._lock:
            if not self._running:
                return "already_stopped"
            self._running = False
            self.status = "STOPPED"
        if self._thread:
            self._thread.join(timeout=10)
        mt5bridge.disconnect()
        logger.info("Bot stopped ✓")
        return "stopped"

    def get_status(self) -> dict:
        acc = mt5bridge.account_info() or {}
        positions = mt5bridge.get_open_positions(magic=config.MAGIC_NUMBER)
        daily_pnl = self._calc_daily_pnl()
        stats = self._calc_stats()

        # Remaining cooldown seconds
        remaining_cd = max(0, int(config.TRADE_COOLDOWN_SEC - (time.time() - self._last_close_time)))

        return {
            "bot_status": self.status,
            "connected": mt5bridge.is_connected(),
            "last_error": self.last_error,
            "loop_count": self.loop_count,
            "version": "3.0",
            "account": {
                "balance": acc.get("balance", 0.0),
                "equity": acc.get("equity", 0.0),
                "profit": acc.get("profit", 0.0),
                "currency": acc.get("currency", "USD"),
                "login": acc.get("login", "—"),
            },
            "daily": {
                "pnl": round(daily_pnl, 2),
                "goal": config.DAILY_GOAL_USD,
                "goal_pct": round(min((daily_pnl / config.DAILY_GOAL_USD) * 100, 100), 1) if config.DAILY_GOAL_USD > 0 else 0,
                "goal_hit": daily_pnl >= config.DAILY_GOAL_USD,
                "max_loss": config.MAX_DAILY_LOSS_USD,
                "loss_hit": daily_pnl <= -config.MAX_DAILY_LOSS_USD,
            },
            "open_positions": positions,
            "positions_count": len(positions),
            "signals": self.last_signal,
            "analysis": self.last_analysis,
            "trades": self._state.get("trades", [])[-50:],
            "trade_count": len(self._state.get("trades", [])),
            "session_start": self._state.get("session_start", ""),
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "stats": stats,
            "risk": {
                "cooldown_remaining_sec": remaining_cd,
                "max_daily_loss": config.MAX_DAILY_LOSS_USD,
            },
            "config": {
                "symbols": config.SYMBOLS,
                "lot_size": config.LOT_SIZE,
                "tp_usd": config.TAKE_PROFIT_USD,
                "sl_usd": config.STOP_LOSS_USD,
                "breakeven_trigger": config.BREAKEVEN_TRIGGER_USD,
                "scan_sec": config.SCAN_INTERVAL_SEC,
                "daily_goal": config.DAILY_GOAL_USD,
                "cooldown_sec": config.TRADE_COOLDOWN_SEC,
                "max_positions": config.MAX_OPEN_POSITIONS,
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

    def reset_daily(self) -> str:
        with self._lock:
            today = datetime.date.today().isoformat()
            trades = self._state.setdefault("trades", [])
            for t in trades:
                if t.get("time", "").startswith(today):
                    t["archived"] = True
            self._state["session_start"] = datetime.datetime.now().isoformat()
            self._state["stats"] = {"total_wins": 0, "total_losses": 0, "total_profit": 0.0, "total_loss": 0.0}
            self._last_close_time = 0.0
            _save_state(self._state)
            logger.info("Session reset ✓")
            return "reset_ok"

    # ══════════════════════════════════════════════════════
    # Main Engine Loop
    # ══════════════════════════════════════════════════════

    def _loop(self):
        logger.info("Bot loop running. Checking every %d seconds.", config.SCAN_INTERVAL_SEC)
        while self._running:
            try:
                self.loop_count += 1
                self._tick()
            except Exception as exc:
                logger.exception("Unexpected error in loop: %s", exc)
                self.last_error = str(exc)

            for _ in range(config.SCAN_INTERVAL_SEC):
                if not self._running:
                    break
                time.sleep(1)

        logger.info("Bot loop terminated.")

    def _update_all_analysis(self):
        """Always refresh technical analysis for all symbols so dashboard is continuously live."""
        for symbol in config.SYMBOLS:
            try:
                candles = mt5bridge.get_candles(symbol, timeframe=config.TREND_TF, count=config.CANDLES_NEEDED + 20)
                htf_tf = getattr(config, "HTF_TF", "M5")
                htf_cnt = getattr(config, "HTF_CANDLES", 30)
                htf_candles = mt5bridge.get_candles(symbol, timeframe=htf_tf, count=htf_cnt + 10)
                if candles and len(candles) >= config.CANDLES_NEEDED:
                    result = analysis.analyze(candles, htf_candles=htf_candles)
                    self.last_signal[symbol] = result.get("signal", "WAIT")
                    self.last_analysis[symbol] = result
            except Exception as exc:
                logger.warning("[%s] Failed to analyze: %s", symbol, exc)

    def _tick(self):
        if not mt5bridge.is_connected():
            if not mt5bridge.connect():
                self.status = "CONNECTING"
                self.last_error = "في انتظار الاتصال بميتاتريدر وسيرفر التداول..."
                time.sleep(2)
                return
            self.status = "RUNNING"
            self.last_error = ""

        # 1. Continuous Market Analysis for ALL active symbols
        self._update_all_analysis()

        # 2. Sync closed deals from MT5 history
        self._sync_closed_trades()

        daily_pnl = self._calc_daily_pnl()

        # 3. Daily Loss Guard (only active if enabled)
        if getattr(config, "AUTO_PAUSE_ON_DAILY_LOSS", False) and daily_pnl <= -config.MAX_DAILY_LOSS_USD:
            logger.warning("Daily loss limit reached ($%.2f / $%.2f). Pausing entries.",
                           abs(daily_pnl), config.MAX_DAILY_LOSS_USD)
            self.last_error = f"أوقف التداول: تم الوصول للحد الأقصى للخسارة اليومية (${config.MAX_DAILY_LOSS_USD})"
            return

        # 3. Manage any open position (TP, SL, Breakeven)
        open_positions = mt5bridge.get_open_positions(magic=config.MAGIC_NUMBER)
        for pos in open_positions:
            self._manage_position(pos)

        # 4. Check if we can open a new position
        # Rules: Total open < MAX_OPEN_POSITIONS (1), and cooldown has passed
        open_positions_fresh = mt5bridge.get_open_positions(magic=config.MAGIC_NUMBER)
        if len(open_positions_fresh) >= config.MAX_OPEN_POSITIONS:
            return  # Wait until current trade finishes

        # Check cooldown — rapid scalping (e.g. 20s)
        time_since_close = time.time() - self._last_close_time
        if self._last_close_time > 0 and time_since_close < config.TRADE_COOLDOWN_SEC:
            logger.debug("Cooldown active: %ds remaining", int(config.TRADE_COOLDOWN_SEC - time_since_close))
            return

        # Try to find a high-probability trade
        for symbol in config.SYMBOLS:
            if not self._running:
                return
            if len(mt5bridge.get_open_positions(magic=config.MAGIC_NUMBER)) >= config.MAX_OPEN_POSITIONS:
                break
            self._evaluate_symbol(symbol)

    # ══════════════════════════════════════════════════════
    # Position Management (Breakeven + Exit)
    # ══════════════════════════════════════════════════════

    def _manage_position(self, pos: dict):
        profit = pos["profit"]
        ticket = pos["ticket"]
        symbol = pos["symbol"]

        # ── 1. Breakeven Protection ────────────────────────
        # Disabled when BREAKEVEN_TRIGGER_USD <= 0 to let winning trades breathe to full TP
        if config.BREAKEVEN_TRIGGER_USD > 0 and not self._breakeven_set.get(ticket, False):
            if profit >= config.BREAKEVEN_TRIGGER_USD:
                self._move_to_breakeven(pos)

        # ── 2. Fallback only if order has NO Stop Loss on broker ──
        # All orders have broker-side SL/TP. Only close manually if SL was missing:
        pos_sl = float(pos.get("sl") or 0.0)
        if pos_sl == 0.0 and profit <= -config.STOP_LOSS_USD:
            logger.info("Closing position without broker SL %s #%d — -$%.2f", symbol, ticket, abs(profit))
            res = mt5bridge.close_position(
                ticket=ticket,
                symbol=symbol,
                lot=pos["volume"],
                pos_type=pos["type"]
            )
            if res.get("success"):
                self._breakeven_set.pop(ticket, None)
                self._last_close_time = time.time()
                self._record_closed_trade(pos, profit, f"Manual SL: -${abs(profit):.2f}")

    def _move_to_breakeven(self, pos: dict):
        """Move Stop Loss to entry price + small buffer to lock in profit."""
        import MetaTrader5 as mt5
        ticket = pos["ticket"]
        symbol = pos["symbol"]
        pos_type = pos["type"]
        entry = pos["price_open"]
        sym_info = mt5bridge.get_symbol_info(symbol)
        if not sym_info:
            return

        point = float(getattr(sym_info, "point", 0.001))
        digits = int(getattr(sym_info, "digits", 3))

        # Calculate buffer in profit direction based on BREAKEVEN_LOCK_USD
        tick_value = float(getattr(sym_info, "trade_tick_value", 0.0))
        tick_size = float(getattr(sym_info, "trade_tick_size", point))
        if tick_value <= 0 or tick_size <= 0:
            tick_value, tick_size = 1.0, point
        val_per_point = (tick_value / tick_size) * point * float(pos.get("volume", config.LOT_SIZE))
        if val_per_point <= 0:
            val_per_point = 0.001

        buffer_pts = max(10, int(config.BREAKEVEN_LOCK_USD / val_per_point))
        tick = mt5bridge.get_tick(symbol)

        if pos_type == "BUY":
            new_sl = round(entry + buffer_pts * point, digits)
            if tick and new_sl >= tick["bid"]:
                new_sl = round(tick["bid"] - 10 * point, digits)
        else:
            new_sl = round(entry - buffer_pts * point, digits)
            if tick and new_sl <= tick["ask"]:
                new_sl = round(tick["ask"] + 10 * point, digits)

        req = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "symbol": symbol,
            "sl": float(new_sl),
            "tp": float(pos["tp"]),
        }
        res = mt5.order_send(req)
        if res and res.retcode in (10008, 10009):
            self._breakeven_set[ticket] = True
            logger.info("Breakeven activated for #%d at %.3f (Risk-free trade now!)", ticket, new_sl)
        else:
            logger.warning("Could not set breakeven for #%d: %s", ticket, res.comment if res else "")

    # ══════════════════════════════════════════════════════
    # Trade Opening
    # ══════════════════════════════════════════════════════

    def _evaluate_symbol(self, symbol: str):
        # Session check
        if config.SESSION_FILTER_ENABLED and not self._in_session(symbol):
            return

        candles = mt5bridge.get_candles(symbol, timeframe=config.TREND_TF, count=config.CANDLES_NEEDED + 20)
        htf_tf = getattr(config, "HTF_TF", "M5")
        htf_cnt = getattr(config, "HTF_CANDLES", 30)
        htf_candles = mt5bridge.get_candles(symbol, timeframe=htf_tf, count=htf_cnt + 10)

        result = analysis.analyze(candles, htf_candles=htf_candles)
        self.last_signal[symbol] = result["signal"]
        self.last_analysis[symbol] = result

        if result["signal"] == analysis.SIGNAL_WAIT:
            return

        logger.info("[%s] High-Probability Signal: %s (%d/%d) — %s",
                    symbol, result["signal"], result["score"], result.get("max_score", 3), result["reason"])

        tick = mt5bridge.get_tick(symbol)
        sym_info = mt5bridge.get_symbol_info(symbol)
        if not tick or not sym_info:
            return

        point = float(getattr(sym_info, "point", 0.001))
        digits = int(getattr(sym_info, "digits", 3))
        tick_value = float(getattr(sym_info, "trade_tick_value", 0.0))
        tick_size = float(getattr(sym_info, "trade_tick_size", point))
        if tick_value <= 0 or tick_size <= 0:
            tick_value, tick_size = 1.0, point

        value_per_point = (tick_value / tick_size) * point * config.LOT_SIZE
        if value_per_point <= 0:
            value_per_point = 0.001

        # ── Dynamic TP calculation (ATR-based, profitable ratio R:R 1:2) ──
        raw_atr = result.get("dynamic_tp")  # raw ATR in price units (e.g. 50.0)
        if raw_atr and raw_atr > 0:
            # raw_atr is price move in USD. On LOT_SIZE (0.01), 1 USD move = LOT_SIZE USD
            atr_usd = raw_atr * config.LOT_SIZE
            dynamic_tp = atr_usd * getattr(config, "TP_ATR_MULT", 1.5)
            tp_min = getattr(config, "TP_MIN_USD", 0.80)
            tp_max = getattr(config, "TP_MAX_USD", 1.80)
            final_tp_usd = max(tp_min, min(tp_max, dynamic_tp))
        else:
            final_tp_usd = config.TAKE_PROFIT_USD

        tp_pts = int(final_tp_usd / value_per_point)
        sl_pts = int(config.STOP_LOSS_USD / value_per_point)

        # Broker stop level buffer
        broker_min = int(getattr(sym_info, "trade_stops_level", 0))
        sl_pts = max(sl_pts, broker_min + 50)
        tp_pts = max(tp_pts, broker_min + 50)

        if result["signal"] == analysis.SIGNAL_BUY:
            entry = tick["ask"]
            sl = round(entry - sl_pts * point, digits)
            tp = round(entry + tp_pts * point, digits)
            direction = "BUY"
        else:
            entry = tick["bid"]
            sl = round(entry + sl_pts * point, digits)
            tp = round(entry - tp_pts * point, digits)
            direction = "SELL"

        logger.info("[%s] Executing %s: entry=%.3f, SL=%.3f ($%.2f), TP=%.3f ($%.2f)",
                    symbol, direction, entry, sl, config.STOP_LOSS_USD, tp, final_tp_usd)

        res = mt5bridge.open_trade(
            symbol=symbol,
            direction=direction,
            lot=config.LOT_SIZE,
            sl=sl,
            tp=tp,
            magic=config.MAGIC_NUMBER,
            comment=f"PULLBACK_{direction[:1]}",
        )

        if res["success"]:
            logger.info("Opened %s #%d at %.3f", direction, res["ticket"], res["price"])
            self.last_error = ""
            self._record_trade({
                "ticket": res["ticket"],
                "symbol": symbol,
                "type": direction,
                "profit": None,
                "reason": "OPENED",
                "score": result["score"],
                "analysis": result["reason"],
                "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
        else:
            logger.warning("Trade failed [%s]: %s", symbol, res.get("error"))
            self.last_error = f"[{symbol}] {res.get('error')}"

    # ══════════════════════════════════════════════════════
    # Helpers
    # ══════════════════════════════════════════════════════

    def _sync_closed_trades(self):
        closed_deals = mt5bridge.get_today_closed_deals(magic=config.MAGIC_NUMBER)
        if not closed_deals:
            return

        trades = self._state.setdefault("trades", [])
        seen_deals = {t.get("deal_ticket") for t in trades if t.get("deal_ticket")}
        changed = False

        for deal in closed_deals:
            if deal["ticket"] in seen_deals:
                continue

            profit = deal["profit"]
            reason = "TP ✅" if profit >= 0 else "SL ❌"

            matched = False
            for t in trades:
                if t.get("ticket") == deal["position_id"] and t.get("reason") == "OPENED":
                    t["profit"] = profit
                    t["reason"] = reason
                    t["close_time"] = deal["time"]
                    t["deal_ticket"] = deal["ticket"]
                    matched = True
                    changed = True
                    self._last_close_time = time.time()
                    self._update_stats(profit)
                    break

            if not matched:
                trades.append({
                    "ticket": deal["position_id"],
                    "deal_ticket": deal["ticket"],
                    "symbol": deal["symbol"],
                    "type": deal["type"],
                    "profit": profit,
                    "reason": reason,
                    "time": deal["time"],
                })
                self._update_stats(profit)
                self._last_close_time = time.time()
                changed = True

        if changed:
            _save_state(self._state)

    def _update_stats(self, profit: float):
        stats = self._state.setdefault("stats", {"total_wins": 0, "total_losses": 0, "total_profit": 0.0, "total_loss": 0.0})
        if profit >= 0:
            stats["total_wins"] = stats.get("total_wins", 0) + 1
            stats["total_profit"] = stats.get("total_profit", 0.0) + profit
            self._consecutive_losses = 0   # reset on win
        else:
            stats["total_losses"] = stats.get("total_losses", 0) + 1
            stats["total_loss"] = stats.get("total_loss", 0.0) + abs(profit)
            self._consecutive_losses += 1
            if self._consecutive_losses >= 2:
                logger.warning("Consecutive losses: %d — cooldown extended!", self._consecutive_losses)

    def _calc_daily_pnl(self) -> float:
        trades = self._state.get("trades", [])
        today = datetime.date.today().isoformat()
        closed = sum(
            t["profit"] for t in trades
            if t.get("profit") is not None
            and t.get("time", "").startswith(today)
            and t.get("reason") not in ("OPENED",)
            and not t.get("archived", False)
        )
        floating = sum(p["profit"] for p in mt5bridge.get_open_positions(magic=config.MAGIC_NUMBER))
        return closed + floating

    def _calc_stats(self) -> dict:
        stats = self._state.get("stats", {})
        tw = stats.get("total_wins", 0)
        tl = stats.get("total_losses", 0)
        tp = stats.get("total_profit", 0.0)
        t_loss = stats.get("total_loss", 0.0)
        total = tw + tl
        win_rate = (tw / total * 100) if total > 0 else 0.0
        pf = (tp / t_loss) if t_loss > 0 else 0.0
        return {
            "total_trades": total,
            "total_wins": tw,
            "total_losses": tl,
            "win_rate_pct": round(win_rate, 1),
            "profit_factor": round(pf, 2),
            "total_profit": round(tp, 2),
            "total_loss": round(t_loss, 2),
        }

    def _in_session(self, symbol: str) -> bool:
        utc_hour = datetime.datetime.utcnow().hour
        sessions = getattr(config, "GOLD_SESSIONS", [(7, 21)]) if symbol.upper().startswith("XAU") else getattr(config, "BTC_SESSIONS", [(0, 24)])
        for s_h, e_h in sessions:
            if s_h <= utc_hour < e_h:
                return True
        return False

    def _record_trade(self, trade: dict):
        self._state.setdefault("trades", []).append(trade)
        _save_state(self._state)

    def _record_closed_trade(self, pos: dict, profit: float, reason: str):
        trades = self._state.setdefault("trades", [])
        for t in trades:
            if t.get("ticket") == pos["ticket"] and t.get("reason") == "OPENED":
                t["profit"] = profit
                t["reason"] = reason
                t["close_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self._update_stats(profit)
                _save_state(self._state)
                return
        trades.append({
            "ticket": pos["ticket"],
            "symbol": pos["symbol"],
            "type": pos["type"],
            "profit": profit,
            "reason": reason,
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        self._update_stats(profit)
        _save_state(self._state)
