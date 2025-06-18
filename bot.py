"""
Market Sim Discord Bot - Main Entry Point
==========================================

This module initializes and runs the Discord trading bot for the Market Sim application.
It handles bot startup, cog loading, database initialization, and graceful shutdown.

The bot provides trading simulation commands through modular cogs:
- Trading commands: join, balance, buy, sell, USD
- Statistics commands: portfolio, leaderboard, chart, stats  
- Admin commands: daily_update, cache management

Architecture:
- Async/await pattern for non-blocking operations
- Modular cog system for command organization
- Automatic database initialization
- Price cache preloading for performance
- Graceful shutdown with cache persistence

Usage:
    python bot.py           # Direct execution
    python start_bot.py     # Recommended launcher with validation
"""

import asyncio
import os
import atexit
from dotenv import load_dotenv
import discord
from discord.ext import commands

from database import DB_NAME, init_db
from prices import preload_price_cache, persist_price_cache

# Load environment variables from .env file
load_dotenv()
TOKEN = os.getenv("TOKEN")

# Configure Discord bot with required intents
intents = discord.Intents.default()
intents.message_content = True  # Required for reading command messages
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready() -> None:
    """
    Initialize the bot when it successfully connects to Discord.
    
    This event handler:
    1. Initializes the SQLite database schema
    2. Preloads the price cache from database for performance
    3. Loads all command cogs (trading, stats, admin)
    4. Logs successful startup with database path
    
    Raises:
        Exception: If database initialization or cog loading fails
    """
    await init_db()
    await preload_price_cache()
    
    # Load command modules using async extension loading
    await bot.load_extension("commands.trading")
    await bot.load_extension("commands.stats") 
    await bot.load_extension("commands.admin")
    
    print(f"🤖 Market Sim Bot ready! Logged in as {bot.user}")
    print(f"📊 Database: {DB_NAME}")
    print(f"🎯 Command prefix: {bot.command_prefix}")
    print(f"📈 Ready to simulate trading in {len(bot.guilds)} server(s)")


async def shutdown() -> None:
    """
    Gracefully shutdown the bot and persist cached data.
    
    This function ensures that:
    - All cached prices are saved to the database
    - Resources are properly cleaned up
    - No data is lost during shutdown
    """
    print("🔄 Shutting down bot, persisting cache...")
    await persist_price_cache()
    print("✅ Cache persisted successfully")


# Register shutdown handler for graceful termination
atexit.register(lambda: asyncio.run(persist_price_cache()))


def main() -> None:
    """
    Entry point for launching the Discord bot.
    
    This function:
    1. Validates that the Discord token is available
    2. Starts the bot with proper error handling
    3. Provides clear error messages for common issues
    
    Raises:
        ValueError: If TOKEN environment variable is not set
        discord.LoginFailure: If the Discord token is invalid
    """
    if not TOKEN:
        raise ValueError(
            "❌ Discord TOKEN not found in environment variables.\n"
            "Please check your .env file and ensure TOKEN is set."
        )
    
    try:
        print("🚀 Starting Market Sim Discord Bot...")
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("❌ Failed to login to Discord. Please check your TOKEN in .env")
        raise
    except Exception as e:
        print(f"❌ Bot startup failed: {e}")
        raise

if __name__ == "__main__":
    main()
