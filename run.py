#!/usr/bin/env python3
"""LifeOS v2 Dashboard — python run.py"""
import os
import sys
from pathlib import Path
import uvicorn
sys.path.insert(0, str(Path(__file__).parent))

port = int(os.getenv("PORT", "8000"))

print("""
╔══════════════════════════════════════════════════════════╗
║        LifeOS v2 — Dashboard Server                     ║
╠══════════════════════════════════════════════════════════╣
║  Open:  http://localhost:{port:<30}║
║  Also run monitor.py in a second terminal               ║
╚══════════════════════════════════════════════════════════╝
""".format(port=port))
uvicorn.run("api.server:app", host="0.0.0.0", port=port, log_level="warning")
