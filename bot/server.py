"""
=============================================================
  ISSSSMAIL SCALPER BOT — HTTP API Server
  خادم API البوت للتواصل مع الداشبورد
=============================================================

Lightweight HTTP server (stdlib only — no Flask needed).
Listens on http://127.0.0.1:8765

Endpoints:
  GET  /status          → full bot status JSON
  POST /start           → start the bot
  POST /stop            → stop the bot
  POST /settings        → update TP / SL / daily goal
  GET  /trades          → trade log JSON
"""

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs

from bot.engine import ScalperEngine

logger   = logging.getLogger("issssmail.server")
_engine  = ScalperEngine()

HOST = "127.0.0.1"
PORT = 8765


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle each HTTP request in a separate thread so status polling never blocks."""
    daemon_threads = True
    allow_reuse_address = True


# ──────────────────────────────────────────────────────────
# Request handler
# ──────────────────────────────────────────────────────────
class BotHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):   # silence default access log
        pass

    def _send_json(self, data: dict, code: int = 200):
        try:
            body = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(body)
        except (ConnectionAbortedError, BrokenPipeError, ConnectionResetError, OSError):
            pass  # client disconnected — ignore silently

    def handle_error(self, request, client_address):
        pass  # suppress error log spam from client disconnects

    def do_OPTIONS(self):
        self._send_json({})

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/status":
            self._send_json(_engine.get_status())
        elif path == "/trades":
            status = _engine.get_status()
            self._send_json({"trades": status.get("trades", [])})
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(body) if body.strip() else {}
        except json.JSONDecodeError:
            payload = {}

        if path == "/start":
            result = _engine.start()
            self._send_json({"result": result})

        elif path == "/stop":
            result = _engine.stop()
            self._send_json({"result": result})

        elif path == "/settings":
            if "daily_goal" in payload:
                try:
                    _engine.set_daily_goal(float(payload["daily_goal"]))
                except (ValueError, TypeError):
                    pass
            if "tp_usd" in payload:
                try:
                    _engine.set_tp(float(payload["tp_usd"]))
                except (ValueError, TypeError):
                    pass
            if "sl_usd" in payload:
                try:
                    _engine.set_sl(float(payload["sl_usd"]))
                except (ValueError, TypeError):
                    pass
            self._send_json({"result": "settings_updated", "status": _engine.get_status()["config"]})

        elif path == "/reset":
            result = _engine.reset_daily()
            self._send_json({"result": result, "status": _engine.get_status()})

        else:
            self._send_json({"error": "Unknown endpoint"}, 404)


# ──────────────────────────────────────────────────────────
# Server start
# ──────────────────────────────────────────────────────────
def run_server():
    server = ThreadedHTTPServer((HOST, PORT), BotHandler)
    logger.info("API server listening on http://%s:%d (Threaded)", HOST, PORT)
    server.serve_forever()


def start_server_thread():
    t = threading.Thread(target=run_server, daemon=True, name="APIServer")
    t.start()
    return t


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s — %(message)s")
    logger.info("Starting ISSSSMAIL Scalper Bot API Server…")
    run_server()
