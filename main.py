"""
=============================================================
  ISSSSMAIL SCALPER BOT — Entry Point
  نقطة تشغيل البوت
=============================================================

Run this file to start everything:
  python main.py

It starts the HTTP API server and keeps running.
The dashboard HTML file connects to this server automatically.
"""

import logging
import signal
import sys
import time

# ── Logging setup ──────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)-20s] %(levelname)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("issssmail_bot.log", encoding="utf-8"),
    ]
)

logger = logging.getLogger("issssmail.main")

# ── Import server (which creates the engine) ──────────────
from bot.server import start_server_thread, PORT, HOST

def main():
    logger.info("=" * 60)
    logger.info("  ISSSSMAIL SCALPER BOT  v1.0")
    logger.info("  Gold (XAUUSD) + Bitcoin (BTCUSD)")
    logger.info("=" * 60)

    server_thread = start_server_thread()
    logger.info("API server started → http://%s:%d", HOST, PORT)
    logger.info("Open dashboard.html in your browser or the Antigravity side pane")
    logger.info("Press Ctrl+C to stop the server")

    # ── Graceful shutdown on Ctrl-C ───────────────────────
    def _handle_signal(sig, frame):
        logger.info("Shutdown signal received. Goodbye!")
        sys.exit(0)

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    # Keep main thread alive
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
