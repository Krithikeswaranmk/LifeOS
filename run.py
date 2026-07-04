#!/usr/bin/env python3
"""LifeOS v2 Dashboard — python run.py"""
import os
import sys
import threading
from pathlib import Path
import uvicorn
sys.path.insert(0, str(Path(__file__).parent))

port = int(os.getenv("PORT", "8000"))
run_monitor = os.getenv("RUN_MONITOR", "false").strip().lower() in ("1", "true", "yes", "on")


def _start_monitor_thread() -> None:
	# Render free plan does not support worker services, so optionally co-run monitor.
	import monitor

	thread = threading.Thread(target=monitor.main, daemon=True, name="lifeos-monitor")
	thread.start()

print("""
╔══════════════════════════════════════════════════════════╗
║        LifeOS v2 — Dashboard Server                     ║
╠══════════════════════════════════════════════════════════╣
║  Open:  http://localhost:{port:<30}║
║  Monitor mode: {monitor_mode:<40}║
╚══════════════════════════════════════════════════════════╝
""".format(port=port, monitor_mode=("embedded" if run_monitor else "separate process")))

if run_monitor:
	_start_monitor_thread()

uvicorn.run("api.server:app", host="0.0.0.0", port=port, log_level="warning")
