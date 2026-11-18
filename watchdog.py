"""
=============================================================
  ISSSSMAIL 24/7 WATCHDOG — الحارس الدائم للبوت 24/7
  يراقب البوت كل 15 ثانية ويعيد تشغيله فوراً وبشكل تلقائي إذا توقف
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

def check_server() -> tuple[bool, str]:
    try:
        req = urllib.request.Request(URL_STATUS, headers={"User-Agent": "Watchdog"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                return True, data.get("bot_status", "UNKNOWN")
    except Exception as e:
        return False, str(e)
    return False, "UNKNOWN"

def ensure_bot_running():
    is_up, bot_status = check_server()
    if not is_up:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Watchdog] ⚠️ Bot server not responding ({bot_status}). Starting main.py...")
        try:
            # Spawn main.py in background
            subprocess.Popen([sys.executable, "main.py"], cwd=PROJECT_DIR, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            time.sleep(5)
        except Exception as e:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Watchdog] Error launching main.py: {e}")
            return

    # Check if started, and make sure trading loop is active
    is_up, bot_status = check_server()
    if is_up and bot_status != "RUNNING":
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Watchdog] Bot status is '{bot_status}'. Sending /start command...")
        try:
            post_req = urllib.request.Request(URL_START, data=b"{}", headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(post_req, timeout=5) as r:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Watchdog] /start response: {r.status}")
        except Exception as e:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Watchdog] /start request failed: {e}")

def main():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Watchdog] Started 24/7 Watchdog daemon for ISSSSMAIL Scalper Bot.", flush=True)
    while True:
        try:
            ensure_bot_running()
        except Exception as e:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Watchdog] Loop error: {e}")
        time.sleep(15)

if __name__ == '__main__':
    main()
