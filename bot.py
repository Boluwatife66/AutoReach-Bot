"""
AutoReach Bot — bot.py
Buttons appear at the bottom of the screen (where the keyboard is)
using ReplyKeyboardMarkup instead of inline buttons.
"""

import logging
import os
import sqlite3
import threading
from datetime import date

from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ── Load .env FIRST before reading any variables ─────────────────────────────
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID  = int(os.getenv("ADMIN_ID", "0"))

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Database ──────────────────────────────────────────────────────────────────
DB_PATH = "database.db"


def get_conn():
    """SQLite connection with row_factory so we can do row['column_name']."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id     INTEGER UNIQUE NOT NULL,
                username        TEXT,
                referral_id     INTEGER,
                referrals_count INTEGER DEFAULT 0,
                date_joined     TEXT NOT NULL
            )
        """)
        conn.commit()
    logger.info("Database ready.")


def register_user(telegram_id: int, username: str, referral_id: int | None):
    """Register new user and credit referrer if applicable."""
    today = date.today().isoformat()
    with get_conn() as conn:
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO users
                    (telegram_id, username, referral_id, referrals_count, date_joined)
                VALUES (?, ?, ?, 0, ?)
                """,
                (telegram_id, username, referral_id, today),
            )
            conn.commit()
        except sqlite3.Error as e:
            logger.error("register_user failed: %s", e)
            return

        # Credit the referrer — isolated so a bad referral_id never kills registration
        if referral_id:
            try:
                conn.execute(
                    "UPDATE users SET referrals_count = referrals_count + 1 WHERE telegram_id = ?",
                    (referral_id,),
                )
                conn.commit()
                logger.info("Referral credited: referrer=%s new_user=%s", referral_id, telegram_id)
            except sqlite3.Error as e:
                logger.warning("Could not credit referral for %s: %s", referral_id, e)


def get_user(telegram_id: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()


def get_all_user_ids() -> list[int]:
    with get_conn() as conn:
        rows = conn.execute("SELECT telegram_id FROM users").fetchall()
    return [r["telegram_id"] for r in rows]


def get_stats() -> dict:
    today = date.today().isoformat()
    with get_conn() as conn:
        total     = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        new_today = conn.execute(
            "SELECT COUNT(*) AS c FROM users WHERE date_joined = ?", (today,)
        ).fetchone()["c"]
        referrals = conn.execute(
            "SELECT COALESCE(SUM(referrals_count), 0) AS s FROM users"
        ).fetchone()["s"]
    return {"total_users": total, "new_today": new_today, "total_referrals": referrals}


# ── Reply Keyboard ────────────────────────────────────────────────────────────
def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    ReplyKeyboardMarkup places buttons where the phone keyboard normally sits.
    - resize_keyboard=True  → compact height, doesn't take over the screen
    - is_persistent=True    → keyboard stays visible after each message
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("📊 My Stats"), KeyboardButton("🔗 My Referral Link")],
            [KeyboardButton("👥 Invite Friends")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


# ── /start ────────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Register the user and show the keyboard menu."""
    user        = update.effective_user
    telegram_id = user.id
    username    = user.username or user.first_name

    # Parse optional referral: /start ref_<telegram_id>
    referral_id = None
    if context.args:
        arg = context.args[0]
        if arg.startswith("ref_"):
            try:
                ref = int(arg[4:])
                if ref != telegram_id:          # can't refer yourself
                    referral_id = ref
            except ValueError:
                pass

    already_registered = get_user(telegram_id) is not None
    register_user(telegram_id, username, referral_id)

    if already_registered:
        text = f"👋 Welcome back, *{username}*!\n\nUse the menu below 👇"
    else:
        text = (
            f"🚀 *Welcome to AutoReach, {username}!*\n\n"
            "You're now part of our growing community.\n"
            "Use the menu below to get started 👇"
        )
        if referral_id:
            text += "\n\n✅ You joined via a referral link!"

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )


# ── Menu button handler ───────────────────────────────────────────────────────
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    ReplyKeyboard buttons send plain text messages.
    We match the text to know which button was tapped.
    """
    telegram_id = update.effective_user.id
    text        = update.message.text
    user_row    = get_user(telegram_id)

    # ── 📊 My Stats ──────────────────────────────────────────────────────────
    if text == "📊 My Stats":
        if not user_row:
            await update.message.reply_text(
                "❌ Not registered yet. Send /start first.",
                reply_markup=main_menu_keyboard(),
            )
            return

        await update.message.reply_text(
            "📊 *Your Stats*\n\n"
            f"👤 Username: @{user_row['username']}\n"
            f"📅 Joined: `{user_row['date_joined']}`\n"
            f"👥 Referrals: *{user_row['referrals_count']}*",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )

    # ── 🔗 My Referral Link ───────────────────────────────────────────────────
    elif text == "🔗 My Referral Link":
        bot_info = await context.bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start=ref_{telegram_id}"
        await update.message.reply_text(
            "🔗 *Your Referral Link*\n\n"
            f"`{ref_link}`\n\n"
            "Share this link — you get credit for every friend who joins!",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )

    # ── 👥 Invite Friends ─────────────────────────────────────────────────────
    elif text == "👥 Invite Friends":
        bot_info = await context.bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start=ref_{telegram_id}"
        await update.message.reply_text(
            "👥 *Invite Friends*\n\n"
            "Send your friends this link:\n"
            f"`{ref_link}`\n\n"
            "Every person who joins adds to your referral count! 🎉",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )


# ── Admin commands ────────────────────────────────────────────────────────────
def admin_only(func):
    """Decorator: block non-admins."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("⛔ Admin only.")
            return
        return await func(update, context)
    return wrapper


@admin_only
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = get_stats()
    await update.message.reply_text(
        "📊 *Bot Stats*\n\n"
        f"👥 Total Users:      *{s['total_users']}*\n"
        f"🆕 New Today:        *{s['new_today']}*\n"
        f"🔗 Total Referrals:  *{s['total_referrals']}*",
        parse_mode="Markdown",
    )


@admin_only
async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = get_stats()
    await update.message.reply_text(
        f"👥 Total registered users: *{s['total_users']}*",
        parse_mode="Markdown",
    )


@admin_only
async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Usage: /broadcast Your message here"""
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return

    msg      = " ".join(context.args)
    user_ids = get_all_user_ids()
    sent = failed = 0

    for uid in user_ids:
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 {msg}")
            sent += 1
        except Exception as e:
            logger.warning("Broadcast failed for %s: %s", uid, e)
            failed += 1

    await update.message.reply_text(
        f"✅ Broadcast done.\n✔ Sent: {sent}  ✗ Failed: {failed}"
    )


# ── Keep-alive server ─────────────────────────────────────────────────────────
def run_server():
    """Run Flask in a background daemon thread."""
    import server  # triggers server.app.run()


# ── Entry point ───────────────────────────────────────────────────────────────

   def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN not set in .env")

    init_db()

    import server
    server.start()
    logger.info("Keep-alive server started.")

    import asyncio
    from telegram.ext import Application

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",     start))
    app.add_handler(CommandHandler("stats",     admin_stats))
    app.add_handler(CommandHandler("users",     admin_users))
    app.add_handler(CommandHandler("broadcast", admin_broadcast))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))

    logger.info("AutoReach Bot is running...")

    async def run():
        await app.initialize()
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await app.updater.idle()
        await app.stop()
        await app.shutdown()

    asyncio.run(run())


if name == "main":
    main()
