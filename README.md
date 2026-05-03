# ⚡ AutoReach System

A production-ready Telegram automation bot with a Flask keep-alive server and an analytics dashboard. Deployable on Render's free tier.

---

## 📁 Project Structure

```
autoreach-bot/
├── bot.py           ← Telegram bot (all handlers + DB logic)
├── server.py        ← Flask keep-alive server + /api/stats
├── database.db      ← SQLite database (auto-created on first run)
├── requirements.txt
├── .env.example     ← Copy to .env and fill in your values
├── README.md
└── dashboard/
    ├── index.html   ← Analytics dashboard
    ├── style.css
    └── script.js
```

---

## 🔐 Environment Variables

| Variable   | Description                                 |
|------------|---------------------------------------------|
| `BOT_TOKEN` | Your Telegram bot token from @BotFather    |
| `ADMIN_ID`  | Your Telegram user ID (use @userinfobot)   |
| `PORT`      | Web server port (Render sets this for you) |

Create a `.env` file:
```
BOT_TOKEN=your_token_here
ADMIN_ID=123456789
PORT=8080
```

---

## 🤖 Bot Commands

### User commands
| Command | Description |
|---------|-------------|
| `/start` | Register + show main menu |
| `/start ref_<id>` | Register via referral link |

### Inline buttons
- 📊 **My Stats** — shows join date and referral count
- 🔗 **My Referral Link** — generates personal invite link
- 👥 **Invite Friends** — same link with instructions

### Admin commands (ADMIN_ID only)
| Command | Description |
|---------|-------------|
| `/stats` | Total users, new today, total referrals |
| `/users` | Quick user count |
| `/broadcast <msg>` | Send message to all users |

---

## 🌐 How server.py Works

`server.py` is a tiny Flask app that runs **in a background thread** alongside the Telegram bot:

```
bot.py starts
  └─► threading.Thread(target=run_server).start()
        └─► server.py Flask app listens on PORT
              ├─► GET /          → "Bot is alive ✅"  (health check)
              └─► GET /api/stats → JSON stats for dashboard
```

Both read the **same `database.db`** file, so stats are always live.

---

## 🔁 Keep-Alive Strategy (Free Tier)

Render's free tier spins down after 15 minutes of inactivity. Two ways to prevent this:

### Option A — UptimeRobot (Recommended, free)
1. Sign up at https://uptimerobot.com
2. Add a new **HTTP(s)** monitor
3. URL: `https://your-app.onrender.com/`
4. Interval: **5 minutes**

This pings your `/` endpoint every 5 min, keeping Render awake.

### Option B — Internal ping loop (add to bot.py if needed)
```python
import asyncio, aiohttp

async def self_ping():
    url = os.getenv("RENDER_EXTERNAL_URL", "")
    if not url:
        return
    async with aiohttp.ClientSession() as s:
        while True:
            try:
                await s.get(url)
            except Exception:
                pass
            await asyncio.sleep(240)  # ping every 4 min
```
Add `asyncio.create_task(self_ping())` inside `main()` after building the app.

---

## 🚀 Deployment Guide (Render)

### Step 1 — Push to GitHub
```bash
git init
git add .
git commit -m "Initial AutoReach commit"
git remote add origin https://github.com/YOUR_USERNAME/autoreach-bot.git
git push -u origin main
```

> ⚠️ Add `.env` to `.gitignore` — never commit real tokens!

### Step 2 — Create Render Web Service
1. Go to https://render.com → **New → Web Service**
2. Connect your GitHub repo
3. Configure:
   - **Name:** `autoreach-bot`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`

### Step 3 — Add Environment Variables
In Render dashboard → **Environment**:
```
BOT_TOKEN   = your_token
ADMIN_ID    = your_id
```
(`PORT` is set automatically by Render)

### Step 4 — Deploy
Click **Create Web Service**. Render will build and deploy automatically.

### Step 5 — Set up UptimeRobot
Add your Render URL to UptimeRobot as described above.

---

## 📊 Dashboard Setup

The dashboard (`dashboard/index.html`) is a static HTML file that calls your bot's `/api/stats` endpoint.

**To use it:**

1. Open `dashboard/script.js`
2. Change the `API_BASE` constant:
   ```js
   const API_BASE = "https://your-bot.onrender.com";
   ```
3. Open `dashboard/index.html` in any browser.

**Or** host the dashboard folder as a static site on Render / Netlify / GitHub Pages.

---

## 🐛 Bug Fixes Applied (vs PepeRush Bot)

| Issue | Fix |
|-------|-----|
| `sqlite3.Row` index access (`row[0]`) breaking on schema changes | Changed to `row["column_name"]` everywhere |
| Referral credit failing silently and crashing registration | Wrapped in isolated `try/except` so registration always completes |
| `dotenv` loaded after `BOT_TOKEN` read | Moved `load_dotenv()` to very top of file |
| Flask server blocking the bot event loop | Launched via `threading.Thread(daemon=True)` |
| No CORS header on `/api/stats` | Added `Access-Control-Allow-Origin: *` for dashboard access |

---

## 📦 Dependencies

```
python-telegram-bot==21.3
Flask==3.0.3
python-dotenv==1.0.1
```

---

*Built with ❤️ — AutoReach System*
