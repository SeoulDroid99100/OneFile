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

# Standard Library
from contextlib import contextmanager  # Not actually used, but no harm.

# Third-Party
from pyrogram import Client, filters, idle  # Correct Pyrogram imports
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton  # Correct type imports
from pyrogram.handlers import MessageHandler, CallbackQueryHandler  # Correct handler imports
from pyrogram.enums import ParseMode  # Correct enum import

# ---------------------------
# 2. Configuration Management
# ---------------------------
@dataclass(frozen=True)  # Excellent use of dataclass for config! frozen=True is good.
class Config:
    API_ID: int = 28213805
    API_HASH: str = "8f80142dfef1a696bee7f6ab4f6ece34"
    BOT_TOKEN: str = "7227094800:AAHoegjcwXUFOgeJbLnxnwbKKeRjHT4Ba5A"
    POSTGRES_URI: str = "postgres://avnadmin:AVNS_DLTo9WK_5HYei9Xu9SY@pg-3efabe4d-anup-84fe.g.aivencloud.com:14318/defaultdb?sslmode=require"
    POOL_SIZE: int = 15
    ADMINS: List[int] = field(default_factory=lambda: [6656275515])  # Use default_factory is PERFECT for mutable defaults.

# ---------------------------
# 3. State Management
# ---------------------------
class AppState:
    db_pool: Optional[asyncpg.pool.Pool] = None  # Correct typing and initialization
    active_sessions: dict[int, datetime] = {}  # Good for tracking sessions
    feature_flags: dict[str, bool] = {"maintenance_mode": False}  # Feature flags are a good pattern

# ---------------------------
# 4. Utility Classes
# ---------------------------
class DatabaseManager:  # Excellent for abstracting DB operations
    @staticmethod
    async def fetch(query: str, *args) -> list[asyncpg.Record]:
        async with AppState.db_pool.acquire() as conn:  # Correctly uses the pool
            return await conn.fetch(query, *args)  # Correct async fetch

    @staticmethod
    async def execute(query: str, *args) -> str:
        async with AppState.db_pool.acquire() as conn:  # Correctly uses the pool
            return await conn.execute(query, *args) # Correct async execute

class DateTimeUtils:  # Good utility class
    @staticmethod
    def iso_format() -> str:
        return datetime.utcnow().isoformat()  #  Correct and efficient

# ---------------------------
# 5. Custom Filters
# ---------------------------
class CustomFilters:
    #  Correctly creates a custom filter.  Using a class is good for organization.
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
               return await next_handler(client, update, conn)  # Pass conn to handler.  EXCELLENT!
            except Exception as e:
                logging.error(f"Database error in handler: {e}") # Log the error

    @staticmethod
    async def error_handler(client: Client, update, next_handler):
        try:
            return await next_handler(client, update)
        except Exception as e:
            logging.exception(f"Error in handler: {e}") # Use exception to log traceback - VERY IMPORTANT
            if isinstance(update, Message):
                await update.reply_text(f"An error occurred: {e}") # Reply with the error

# ---------------------------
# 7. UI Components
# ---------------------------
class KeyboardBuilder: # Good practice to separate UI
    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([[InlineKeyboardButton("📊 Stats", callback_data="stats")]])

class TemplateManager:  #Consider moving to separate file if it gets large
    WELCOME_MSG = "Welcome {name}! Your account was created on {date}" # Could be useful

# ---------------------------
# 8. Handler Functions
# ---------------------------

# --- 8.A. Start Handler ---
async def handle_start(client: Client, message: Message, conn):  # Correct signature with DB connection
    user = message.from_user
    await DatabaseManager.execute(
        """INSERT INTO users (id, username, created_at)
        VALUES ($1, $2, $3) ON CONFLICT (id) DO UPDATE
        SET username = EXCLUDED.username""",
        user.id, user.username, DateTimeUtils.iso_format()  # Correct use of parameters to prevent SQL injection!
    )

    welcome_text = (
        f"[🌚](https://envs.sh/taC.jpg) ˹ᴅᴇɪꜰɪᴇᴅ ʙᴇɪɴɢ˼ **{user.first_name}** . . .\n\n"
        f"**ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ** 〄 **ʟᴜɴᴅᴍᴀᴛᴇ ᴜx** 〄 – **ᴛʜᴇ ᴜʟᴛɪᴍᴀᴛᴇ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ ʙᴏᴛ ғᴏʀ ᴛᴇʟᴇɢʀᴀᴍ ɢʀᴏᴜᴘs.**\n"
        f"**ᴇxᴘʟᴏʀᴇ ᴍʏ ғᴇᴀᴛᴜʀᴇs ᴡɪᴛʜ** /help **ᴀɴᴅ ᴇɴʜᴀɴᴄᴇ ʏᴏᴜʀ ᴇxᴘᴇʀɪᴇɴᴄᴇ.**"
    )
    await message.reply_text(welcome_text, disable_web_page_preview=False)  # Correct usage

# --- 8.B. Stats Handler ---
async def handle_stats(client: Client, callback_query, conn):  # Correct signature
    count = await DatabaseManager.fetch("SELECT COUNT(*) FROM users")  # Get user count
    await callback_query.answer(f"Total users: {count[0]['count']}")  # Correctly answer the callback query

# --- 8.C. Handler Wrapper (for middleware) ---
async def message_handler_wrapper(handler_func):
    async def wrapper(client: Client, update, *args):
        return await handler_func(client, update, *args) # Pass the arguments to the handler function
    return wrapper

# ---------------------------
# 9. Client Initialization
# ---------------------------
app = Client(
    name="pg_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    parse_mode=ParseMode.MARKDOWN  # Correctly setting parse mode
)

# ---------------------------
# 10. Lifecycle Management
# ---------------------------
#ERROR HERE: app.on_startup doesn't exist
#@app.on_startup()
#async def startup_event(client: Client):
async def startup_event(): # Remove the decorator, no need for client argument
    logging.info("Starting up...")
    AppState.db_pool = await asyncpg.create_pool(  # Correctly create the pool
        dsn=Config.POSTGRES_URI,
        min_size=5,  # Good practice
        max_size=Config.POOL_SIZE  # Good practice
    )
    async with AppState.db_pool.acquire() as conn:
      await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                username TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
      """)  # Correctly creates the table if it doesn't exist
    logging.info("Database pool initialized and tables checked/created.")

# ---------------------------
# 11. Handler Registration
# ---------------------------
# Correctly adding handlers.  Middleware usage is excellent.
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
        level=logging.INFO,  # Good practice
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"  # Good log format
    )

    # Start Application
    #app.run() # Incorrect
    app.run(startup_event()) # Pass the async function
