#!/usr/bin/env python3
"""LifeOS v2 Dashboard — python run.py"""
import sys
from pathlib import Path
import uvicorn
sys.path.insert(0, str(Path(__file__).parent))

print("""
╔══════════════════════════════════════════════════════════╗
║        LifeOS v2 — Dashboard Server                     ║
╠══════════════════════════════════════════════════════════╣
║  Open:  http://localhost:8000                           ║
║  Also run monitor.py in a second terminal               ║
╚══════════════════════════════════════════════════════════╝
""")
uvicorn.run("api.server:app", host="0.0.0.0", port=8000, log_level="warning")
