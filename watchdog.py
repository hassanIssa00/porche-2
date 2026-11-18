"""
=============================================================
  ISSSSMAIL 24/7 WATCHDOG — الحارس الدائم للبوت 24/7
  يراقب البوت كل 10 ثوانٍ:
    1. يتحقق من عمل السيرفر والتطبيق
    2. يتحقق من اتصال ميتاتريدر (MT5)
    3. يكشف أي تجمد أو توقف (Deadlock Detection)
    4. يعيد تشغيل البوت فوراً وتلقائياً دون توقف
=============================================================
"""

import time
import subprocess
import urllib.request
import urllib.error
import json
import os
import sys

URL_STATUS = "http://127.0.0.1:8765/status"
URL_START  = "http://127.0.0.1:8765/start"
PROJECT_DIR = r"c:\Users\hassa\Desktop\all project\issssmail"

_last_loop_count = -1
_loop_stuck_count = 0
_disconnect_count = 0

def get_status() -> tuple[bool, dict]:
    try:
        req = urllib.request.Request(URL_STATUS, headers={"User-Agent": "Watchdog-24-7"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                return True, data
    except Exception as e:
        return False, {"error": str(e)}
    return False, {}

def kill_stale_bot():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Watchdog] Killing any stale bot processes...", flush=True)
    try:
        subprocess.run(["powershell", "-Command", "Get-Process python* -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -eq '' -and $_.Id -notin @(14108, 32532, 17048, 32352) } | Stop-Process -Force -ErrorAction SilentlyContinue"], timeout=10)
        time.sleep(2)
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Watchdog] Kill error: {e}", flush=True)

def launch_bot():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Watchdog] 🚀 Launching main.py...", flush=True)
    try:
        subprocess.Popen([sys.executable, "main.py"], cwd=PROJECT_DIR, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        time.sleep(4)
        # Send /start command
        post_req = urllib.request.Request(URL_START, data=b"{}", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(post_req, timeout=5) as r:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Watchdog] Sent /start → {r.status} ✓", flush=True)
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Watchdog] Launch error: {e}", flush=True)

def check_and_recover():
    global _last_loop_count, _loop_stuck_count, _disconnect_count

    is_up, status_data = get_status()

    # 1. Server is down
    if not is_up:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Watchdog] ⚠️ Server unreachable ({status_data.get('error')}). Restarting bot...", flush=True)
        kill_stale_bot()
        launch_bot()
        return

    bot_status = status_data.get("bot_status", "UNKNOWN")
    connected = status_data.get("connected", False)
    loop_count = status_data.get("loop_count", 0)

    # 2. Bot is not running
    if bot_status != "RUNNING":
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Watchdog] Bot status is '{bot_status}'. Sending /start...", flush=True)
        try:
            post_req = urllib.request.Request(URL_START, data=b"{}", headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(post_req, timeout=5) as r:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Watchdog] Started bot ✓", flush=True)
        except Exception as e:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Watchdog] Failed to /start: {e}", flush=True)

    # 3. MT5 Disconnected
    if not connected:
        _disconnect_count += 1
        if _disconnect_count >= 3:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Watchdog] MT5 disconnected for 30s. Restarting bot...", flush=True)
            _disconnect_count = 0
            kill_stale_bot()
            launch_bot()
    else:
        _disconnect_count = 0

    # 4. Deadlock / Freeze detection (loop_count not increasing)
    if bot_status == "RUNNING":
        if loop_count == _last_loop_count:
            _loop_stuck_count += 1
            if _loop_stuck_count >= 4: # 40 seconds without a single loop tick
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Watchdog] 🚨 Deadlock detected! Loop stuck at #{loop_count} for 40s. Restarting...", flush=True)
                _loop_stuck_count = 0
                kill_stale_bot()
                launch_bot()
        else:
            _loop_stuck_count = 0
            _last_loop_count = loop_count

def main():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Watchdog] 24/7 Resilient Watchdog Active. Checking every 10s...", flush=True)
    while True:
        try:
            check_and_recover()
        except Exception as e:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Watchdog] Error: {e}", flush=True)
        time.sleep(10)

if __name__ == '__main__':
    main()
