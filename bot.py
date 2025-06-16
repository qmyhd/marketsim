import asyncio
import os
import atexit
from dotenv import load_dotenv
import discord
from discord.ext import commands

from database import DB_NAME, init_db
from prices import preload_price_cache, persist_price_cache
from commands.trading import TradingCog
from commands.stats import StatsCog
from commands.admin import AdminCog

load_dotenv()
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready() -> None:
    """Initialize database and load price cache when the bot starts."""
    await init_db()
    await preload_price_cache()
    print(f"Logged in as {bot.user} using DB {DB_NAME}")

async def shutdown() -> None:
    """Persist cached prices on shutdown."""
    await persist_price_cache()

atexit.register(lambda: asyncio.run(persist_price_cache()))

bot.add_cog(TradingCog(bot))
bot.add_cog(StatsCog(bot))
bot.add_cog(AdminCog(bot))


def main() -> None:
    """Entry point for launching the Discord bot."""
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
