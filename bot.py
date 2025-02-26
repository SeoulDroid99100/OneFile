# -*- coding: utf-8 -*-
"""
Pyrogram Bot with Auto Dependency Management
Version: 3.7
Author: Your Name
"""

# ---------------------------
# 0. Dependency Management
# ---------------------------
import sys
import subprocess

REQUIRED_PACKAGES = [
    ('pyrogram[fast]', '2.0.106'),
    ('asyncpg', '0.27.0'),
    ('python-dotenv', '1.0.0'),
    ('tgcrypto')
]

def ensure_dependencies():
    try:
        from pyrogram import __version__ as pyro_ver
        from asyncpg import __version__ as pg_ver
        from importlib.metadata import version

        installed = {
            'pyrogram[fast]': version('pyrogram'),
            'asyncpg': version('asyncpg'),
            'python-dotenv': version('python-dotenv')
        }

        missing = []
        for pkg, req_ver in REQUIRED_PACKAGES:
            if installed[pkg] < req_ver:
                missing.append(f"{pkg}>={req_ver}")

        if missing:
            raise ImportError()

    except ImportError:
        print("Installing missing dependencies...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "--disable-pip-version-check",
            "--no-warn-script-location",
            *[f"{pkg}>={ver}" for pkg, ver in REQUIRED_PACKAGES]
        ])
        print("\nDependencies installed. Please restart the application.")
        sys.exit(0)

ensure_dependencies()

# ---------------------------
# 1. Core Imports
# ---------------------------
import logging
import asyncpg
from typing import Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass

# Standard Library
from contextlib import contextmanager

# Third-Party
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.enums import ParseMode

# ---------------------------
# 2. Configuration Management
# ---------------------------
@dataclass(frozen=True)
class Config:
    API_ID: int = 28213805
    API_HASH: str = "8f80142dfef1a696bee7f6ab4f6ece34"
    BOT_TOKEN: str = "7227094800:AAHoegjcwXUFOgeJbLnxnwbKKeRjHT4Ba5A"
    POSTGRES_URI: str = "postgres://avnadmin:AVNS_DLTo9WK_5HYei9Xu9SY@pg-3efabe4d-anup-84fe.g.aivencloud.com:14318/defaultdb?sslmode=require"
    POOL_SIZE: int = 15
    ADMINS: list[int] = [6656275515]  # Add admin user IDs here

# ---------------------------
# 3. State Management
# ---------------------------
class AppState:
    db_pool: Optional[asyncpg.pool.Pool] = None
    active_sessions: dict[int, datetime] = {}
    feature_flags: dict[str, bool] = {"maintenance_mode": False}

# ---------------------------
# 4. Utility Classes
# ---------------------------
class DatabaseManager:
    @staticmethod
    async def fetch(query: str, *args) -> list[asyncpg.Record]:
        async with AppState.db_pool.acquire() as conn:
            return await conn.fetch(query, *args)

    @staticmethod
    async def execute(query: str, *args) -> str:
        async with AppState.db_pool.acquire() as conn:
            return await conn.execute(query, *args)

class DateTimeUtils:
    @staticmethod
    def iso_format() -> str:
        return datetime.utcnow().isoformat()

# ---------------------------
# 5. Custom Filters
# ---------------------------
class CustomFilters:
    admin_only = filters.create(lambda _, __, m: m.from_user and m.from_user.id in Config.ADMINS)
    # Example rate limit (not implemented, but placeholder)
    # rate_limit = filters.create(lambda _, __, ___: check_rate_limit())

# ---------------------------
# 6. Middleware Framework
# ---------------------------
class Middleware:
    @staticmethod
    async def db_connector(client: Client, update, next_handler):
        async with AppState.db_pool.acquire() as conn:
            try:
               return await next_handler(client, update, conn)  # Pass conn to handler
            except Exception as e:
                logging.error(f"Database error in handler: {e}")

    @staticmethod
    async def error_handler(client: Client, update, next_handler):
        try:
            return await next_handler(client, update)
        except Exception as e:
            logging.exception(f"Error in handler: {e}") # Use exception to log traceback
            if isinstance(update, Message):
                await update.reply_text(f"An error occurred: {e}")

# ---------------------------
# 7. UI Components
# ---------------------------
class KeyboardBuilder:
    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([[InlineKeyboardButton("📊 Stats", callback_data="stats")]])

class TemplateManager:  #Consider moving to separate file if it gets large
    WELCOME_MSG = "Welcome {name}! Your account was created on {date}"

# ---------------------------
# 8. Handler Functions
# ---------------------------

# --- 8.A. Start Handler ---
async def handle_start(client: Client, message: Message, conn):
    user = message.from_user
    await DatabaseManager.execute(
        """INSERT INTO users (id, username, created_at)
        VALUES ($1, $2, $3) ON CONFLICT (id) DO UPDATE
        SET username = EXCLUDED.username""",
        user.id, user.username, DateTimeUtils.iso_format()
    )

    welcome_text = (
        f"[🌚](https://envs.sh/taC.jpg) ˹ᴅᴇɪꜰɪᴇᴅ ʙᴇɪɴɢ˼ **{user.first_name}** . . .\n\n"
        f"**ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ** 〄 **ʟᴜɴᴅᴍᴀᴛᴇ ᴜx** 〄 – **ᴛʜᴇ ᴜʟᴛɪᴍᴀᴛᴇ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ ʙᴏᴛ ғᴏʀ ᴛᴇʟᴇɢʀᴀᴍ ɢʀᴏᴜᴘs.**\n"
        f"**ᴇxᴘʟᴏʀᴇ ᴍʏ ғᴇᴀᴛᴜʀᴇs ᴡɪᴛʜ** /help **ᴀɴᴅ ᴇɴʜᴀɴᴄᴇ ʏᴏᴜʀ ᴇxᴘᴇʀɪᴇɴᴄᴇ.**"
    )
    await message.reply_text(welcome_text, disable_web_page_preview=False)

# --- 8.B. Stats Handler ---
async def handle_stats(client: Client, callback_query, conn):
    count = await DatabaseManager.fetch("SELECT COUNT(*) FROM users")
    await callback_query.answer(f"Total users: {count[0]['count']}")

# --- 8.C. Handler Wrapper (for middleware) ---
async def message_handler_wrapper(handler_func):
    async def wrapper(client: Client, update, *args):
        return await handler_func(client, update, *args)
    return wrapper

# ---------------------------
# 9. Client Initialization
# ---------------------------
app = Client(
    name="pg_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    parse_mode=ParseMode.MARKDOWN
)

# ---------------------------
# 10. Lifecycle Management
# ---------------------------
@app.on_startup()
async def startup_event(client: Client):
    logging.info("Starting up...")
    AppState.db_pool = await asyncpg.create_pool(
        dsn=Config.POSTGRES_URI,
        min_size=5,
        max_size=Config.POOL_SIZE
    )
    async with AppState.db_pool.acquire() as conn:
      await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                username TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
      """)
    logging.info("Database pool initialized and tables checked/created.")

# ---------------------------
# 11. Handler Registration
# ---------------------------
app.add_handler(MessageHandler(message_handler_wrapper(handle_start), filters.command("start") & filters.private))
app.add_handler(CallbackQueryHandler(message_handler_wrapper(handle_stats), filters.regex("^stats$")))

# ---------------------------
# 12. Main Execution
# ---------------------------
if __name__ == "__main__":
    # Environment Validation
    required_config_vars = [Config.API_ID, Config.API_HASH, Config.BOT_TOKEN, Config.POSTGRES_URI]
    if not all(required_config_vars):
        raise EnvironmentError("Missing required configuration values (API_ID, API_HASH, BOT_TOKEN, POSTGRES_URI)")

    # Logging Configuration
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Start Application
    app.run()
