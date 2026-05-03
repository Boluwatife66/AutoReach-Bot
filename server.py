"""
server.py — AutoReach Keep-Alive + API Server
=============================================
- GET /          → "Bot is alive" (for UptimeRobot / Render health checks)
- GET /api/stats → JSON stats for the dashboard
- Runs on PORT from env (Render sets this automatically)
"""

import os
import sqlite3

from flask import Flask, jsonify
from dotenv import load_dotenv

load_dotenv()

app   = Flask(__name__)
PORT  = int(os.getenv("PORT", 8080))
DB_PATH = "database.db"


def _query_stats() -> dict:
    """Read stats from SQLite. Returns zeros if DB doesn't exist yet."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        from datetime import date
        today   = date.today().isoformat()
        total   = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        new_t   = conn.execute(
            "SELECT COUNT(*) AS c FROM users WHERE date_joined = ?", (today,)
        ).fetchone()["c"]
        refs    = conn.execute(
            "SELECT COALESCE(SUM(referrals_count),0) AS s FROM users"
        ).fetchone()["s"]
        conn.close()
        return {"total_users": total, "new_today": new_t, "total_referrals": refs}
    except Exception:
        return {"total_users": 0, "new_today": 0, "total_referrals": 0}


@app.route("/")
def index():
    """Health-check endpoint — keep Render / UptimeRobot happy."""
    return "Bot is alive ✅", 200


@app.route("/api/stats")
def api_stats():
    """
    Returns bot statistics as JSON.
    Used by the AutoReach Dashboard (dashboard/index.html).
    """
    stats = _query_stats()
    # Add CORS header so the dashboard HTML file can call this from any origin
    response = jsonify(stats)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


if __name__ == "__main__":
    # This is called directly when imported by bot.py in a thread,
    # OR you can run `python server.py` standalone for testing.
    app.run(host="0.0.0.0", port=PORT)
