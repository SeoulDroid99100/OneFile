# -*- coding: utf-8 -*-
"""
Pyrogram Bot with Auto Dependency Management
Version: 3.1
Author: Your Name
"""

# ---------------------------
# 0. Dependency Management
# ---------------------------
import sys
import subprocess

REQUIRED_PACKAGES = [
    ('pyrogram[fast]', '2.0.0'),
    ('asyncpg', '0.27.0'),
    ('python-dotenv', '1.0.0')
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
import os
import logging
import asyncpg
from typing import Any, Optional
from datetime import datetime

# Pyrogram Components
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.handlers import MessageHandler

# Rest of your application code follows the previous structure...
# ---------------------------
# 2. Structured Imports
# ---------------------------
# Standard Library
from datetime import datetime
from contextlib import contextmanager

# Third-Party
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

# ---------------------------
# 3. Configuration Management
# ---------------------------
@dataclass(frozen=True)
class Config:
    API_ID: int = 28213805
    API_HASH: str = "8f80142dfef1a696bee7f6ab4f6ece34"
    BOT_TOKEN: str = "7227094800:AAHoegjcwXUFOgeJbLnxnwbKKeRjHT4Ba5A"
    POSTGRES_URI: str = "postgres://avnadmin:AVNS_DLTo9WK_5HYei9Xu9SY@pg-3efabe4d-anup-84fe.g.aivencloud.com:14318/defaultdb?sslmode=require"
    POOL_SIZE: int = 15

# ---------------------------
# 4. State Management
# ---------------------------
class AppState:
    db_pool: Optional[asyncpg.pool.Pool] = None
    active_sessions: dict[int, datetime] = {}
    feature_flags: dict[str, bool] = {"maintenance_mode": False}

# ---------------------------
# 5. Utility Classes
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
# 6. Custom Filters
# ---------------------------
class CustomFilters:
    admin_only = filters.create(lambda _, __, m: m.from_user.id in ADMINS)
    rate_limit = filters.create(lambda _, __, ___: check_rate_limit())

# ---------------------------
# 7. Middleware Framework
# ---------------------------
class Middleware:
    @staticmethod
    async def db_connector(_, client: Client, call: Callable, **kwargs):
        kwargs["db"] = DatabaseManager
        return await call(client, **kwargs)

    @staticmethod
    async def error_handler(_, client: Client, call: Callable, **kwargs):
        try:
            return await call(client, **kwargs)
        except asyncpg.PostgresError as e:
            logging.error(f"Database error: {str(e)}")

# ---------------------------
# 8. UI Components
# ---------------------------
class KeyboardBuilder:
    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([[("📊 Stats", "stats")]])

class TemplateManager:
    WELCOME_MSG = "Welcome {name}! Your account was created on {date}"

# ---------------------------
# 9. Client Initialization
# ---------------------------
app = Client(
    name="pg_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# ---------------------------
# 10. Handler Setup
# ---------------------------
@app.on_message(filters.command("start") & filters.private)
async def handle_start(client: Client, message: Message):
    user = message.from_user
    await DatabaseManager.execute(
        """INSERT INTO users (id, username, created_at)
        VALUES ($1, $2, $3) ON CONFLICT (id) DO UPDATE
        SET username = EXCLUDED.username""",
        user.id, user.username, DateTimeUtils.iso_format()
    )
    await message.reply(TemplateManager.WELCOME_MSG.format(
        name=user.first_name,
        date=DateTimeUtils.iso_format()
    ))

@app.on_callback_query(filters.regex("^stats$"))
async def handle_stats(client: Client, callback_query):
    count = await DatabaseManager.fetch("SELECT COUNT(*) FROM users")
    await callback_query.answer(f"Total users: {count[0]['count']}")

# ---------------------------
# 11. Error Handling
# ---------------------------
@app.on_errors()
async def global_error_handler(client: Client, error: Exception):
    logging.error(f"Unhandled exception: {str(error)}")
    await client.send_message(ADMINS[0], f"🚨 Error: {str(error)}")

# ---------------------------
# 12. Lifecycle Management
# ---------------------------
@app.on_start()
async def initialize_db(client: Client):
    AppState.db_pool = await asyncpg.create_pool(
        dsn=Config.POSTGRES_URI,
        min_size=5,
        max_size=Config.POOL_SIZE
    )
    await DatabaseManager.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id BIGINT PRIMARY KEY,
            username TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

@app.on_stop()
async def cleanup_resources(client: Client):
    if AppState.db_pool:
        await AppState.db_pool.close()
    logging.info("Resources cleaned up successfully")

# ---------------------------
# 13. Main Execution
# ---------------------------
if __name__ == "__main__":
    # Environment validation
    required = [Config.API_ID, Config.API_HASH, Config.BOT_TOKEN]
    if not all(required):
        raise EnvironmentError("Missing required configuration values")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Register middleware
    app.add_middleware(Middleware.db_connector)
    app.add_middleware(Middleware.error_handler)

    # Start application
    app.run()
