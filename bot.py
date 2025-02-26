# -*- coding: utf-8 -*-
"""
Pyrogram Bot  (No Auto Dependency Management)
Version: 3.11
Author: Your Name
"""

# ---------------------------
# 1. Core Imports
# ---------------------------
import logging
import asyncpg
from typing import Any, Optional, Callable, List
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path  # Import Path

# Standard Library
from contextlib import contextmanager

# Third-Party
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.enums import ParseMode
import asyncio
import os

# ---------------------------
# 2. Configuration Management
# ---------------------------
@dataclass(frozen=True)
class Config:
    API_ID: int = int(os.environ["API_ID"])
    API_HASH: str = os.environ["API_HASH"]
    BOT_TOKEN: str = os.environ["BOT_TOKEN"]
    POSTGRES_URI: str = os.environ["POSTGRES_URI"]
    POOL_SIZE: int = 15
    ADMINS: List[int] = field(default_factory=lambda: [6656275515])
    SESSION_DIR: str = os.environ.get("SESSION_DIR", "/app/sessions") # Get session dir from env, default to /app/sessions

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

# ---------------------------
# 6. Middleware Framework
# ---------------------------
class Middleware:
    @staticmethod
    async def db_connector(client: Client, update, next_handler):
        async with AppState.db_pool.acquire() as conn:
            try:
               return await next_handler(client, update, conn)
            except Exception as e:
                logging.error(f"Database error in handler: {e}")

    @staticmethod
    async def error_handler(client: Client, update, next_handler):
        try:
            return await next_handler(client, update)
        except Exception as e:
            logging.exception(f"Error in handler: {e}")
            if isinstance(update, Message):
                await update.reply_text(f"An error occurred: {e}")

# ---------------------------
# 7. UI Components
# ---------------------------
class KeyboardBuilder:
    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([[InlineKeyboardButton("📊 Stats", callback_data="stats")]])

class TemplateManager:
    WELCOME_MSG = "Welcome {name}! Your account was created on {date}"

# ---------------------------
# 8. Handler Functions
# ---------------------------

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

async def handle_stats(client: Client, callback_query, conn):
    count = await DatabaseManager.fetch("SELECT COUNT(*) FROM users")
    await callback_query.answer(f"Total users: {count[0]['count']}")

async def message_handler_wrapper(handler_func):
    async def wrapper(client: Client, update, *args):
        return await handler_func(client, update, *args)
    return wrapper

# ---------------------------
# 9. Client Initialization
# ---------------------------

# Use an absolute path from the environment variable
session_dir = Path(Config.SESSION_DIR)
session_dir.mkdir(parents=True, exist_ok=True)  # Ensure directory exists

app = Client(
    name=str(session_dir / "pg_bot"),  # Use the absolute path
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    parse_mode=ParseMode.MARKDOWN,
    workdir=str(session_dir) # ADD WORKDIR here
)

# ---------------------------
# 10. Lifecycle Management
# ---------------------------
async def startup_event():
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
async def register_handlers():
  app.add_handler(MessageHandler(await message_handler_wrapper(handle_start), filters.command("start") & filters.private))
  app.add_handler(CallbackQueryHandler(await message_handler_wrapper(handle_stats), filters.regex("^stats$")))

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

    async def main():
        await startup_event()
        await register_handlers()
        try:
            await app.start()
            await idle()
        except Exception as e:
            logging.exception("An error occurred during bot startup:")

    asyncio.run(main())
