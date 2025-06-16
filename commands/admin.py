from discord.ext import commands
import discord
import os
import aiosqlite
from datetime import date

from database import (
    get_all_users,
    get_holdings,
    record_history,
)
from prices import (
    get_price,
    persist_price_cache,
    preload_price_cache,
    clear_price_cache,
)
from database import DB_NAME

class AdminCog(commands.Cog):
    """Administrative commands for managing the bot."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _portfolio_update(self) -> list[str]:
        """Compute daily portfolio values and return summary lines."""
        await preload_price_cache()
        lines: list[str] = []
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute(
                "SELECT user_id, cash, last_value, initial_value FROM users"
            ) as cursor:
                users = await cursor.fetchall()

            for user_id, cash, last_val, initial in users:
                async with db.execute(
                    "SELECT symbol, shares FROM holdings WHERE user_id = ?",
                    (user_id,),
                ) as hcur:
                    holdings = await hcur.fetchall()

                total_value = cash
                for symbol, shares in holdings:
                    price = await get_price(symbol)
                    if price:
                        total_value += shares * price
                await db.execute(
                    "UPDATE users SET last_value = ? WHERE user_id = ?",
                    (total_value, user_id),
                )
                await record_history(user_id, total_value)
                total_gain = ((total_value - initial) / initial) * 100
                day_gain = (
                    ((total_value - last_val) / last_val) * 100 if last_val else 0
                )
                user = await self.bot.fetch_user(int(user_id))
                lines.append(
                    f"{user.name}: ${total_value:,.2f} | ROI {total_gain:+.2f}% | Day {day_gain:+.2f}%"
                )
            await db.commit()
        return lines

    @commands.command(name="daily_update")
    @commands.has_permissions(administrator=True)
    async def daily_update(self, ctx: commands.Context) -> None:
        """Post a daily portfolio summary to the configured channel."""
        channel_id = os.getenv("DISCORD_CHANNEL_ID")
        channel = (
            self.bot.get_channel(int(channel_id)) if channel_id else ctx.channel
        )
        lines = await self._portfolio_update()
        if not lines:
            await ctx.send("No users found.")
            return
        await channel.send("\n".join(lines))

    @commands.command(name="flushcache")
    @commands.has_permissions(administrator=True)
    async def flush_cache(self, ctx: commands.Context) -> None:
        """Persist cached prices to the database."""
        await persist_price_cache()
        await ctx.send("Cache flushed to database.")

    @commands.command(name="clearcache")
    @commands.has_permissions(administrator=True)
    async def clear_cache(self, ctx: commands.Context) -> None:
        """Clear the in-memory price cache."""
        clear_price_cache()
        await ctx.send("Price cache cleared.")

    @commands.command(name="reloadcache")
    @commands.has_permissions(administrator=True)
    async def reload_cache(self, ctx: commands.Context) -> None:
        """Reload cached prices from the database."""
        clear_price_cache()
        await preload_price_cache()
        await ctx.send("Price cache reloaded from database.")


async def setup(bot: commands.Bot) -> None:
    """Cog loader for AdminCog."""
    await bot.add_cog(AdminCog(bot))
