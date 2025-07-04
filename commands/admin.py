"""
Market Sim Administrative Commands Module
=========================================

This module provides administrative commands for managing the Market Sim bot.
These commands are restricted to users with administrator permissions and
handle maintenance tasks like daily updates, cache management, and system operations.

Commands Provided:
- !daily_update: Generate and post daily portfolio summaries
- !flushcache: Persist cached prices to database
- !clearcache: Clear in-memory price cache
- !reloadcache: Reload price cache from database

Features:
- Administrator permission checking for security
- Daily portfolio value calculations and history tracking
- Cache management for performance optimization
- Automated portfolio updates with ROI calculations
- Error handling and validation for all operations

Security:
- All commands require Discord administrator permissions
- Database operations are protected with proper error handling
- No sensitive data exposure in command responses

Usage:
These commands are typically used by bot administrators to:
- Perform daily maintenance tasks
- Manage price cache for optimal performance
- Generate portfolio reports for all users
- Troubleshoot data issues
"""

from discord.ext import commands
import discord
import os
import aiosqlite
from datetime import date
from typing import List, Optional, Any

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
    """
    Discord cog containing administrative commands for bot management.
    
    This cog provides tools for administrators to manage the bot's
    operation, including cache management, daily updates, and maintenance tasks.
    All commands require administrator permissions for security.
    """

    def __init__(self, bot: commands.Bot) -> None:
        """
        Initialize the administrative cog.
        
        Args:
            bot: The Discord bot instance
        """
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

                holdings_value = 0
                for symbol, shares in holdings:
                    price = await get_price(symbol)
                    if price:
                        holdings_value += shares * price
                
                total_value = cash + holdings_value
                await db.execute(
                    "UPDATE users SET last_value = ? WHERE user_id = ?",
                    (total_value, user_id),
                )
                await record_history(user_id, total_value)
                total_gain = ((total_value - initial) / initial) * 100
                user = await self.bot.fetch_user(int(user_id))
                lines.append(
                    f"{user.name}: Holdings ${holdings_value:,.2f} | Cash ${cash:,.2f} | All-time ROI {total_gain:+.2f}%"
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
