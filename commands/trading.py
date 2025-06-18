"""
Market Sim Trading Commands Module
=================================

This module implements all trading-related Discord commands for the Market Sim bot.
It provides core functionality for users to join the game, check balances, and
execute buy/sell transactions with real-time stock price validation.

Commands Provided:
- !join: Create new user account with starting capital
- !balance: Check current cash balance
- !buy <symbol> <quantity>: Purchase stocks by share count
- !sell <symbol> <quantity>: Sell stocks from holdings
- !USD <symbol> <amount>: Purchase stocks using dollar amount

Features:
- Real-time price validation for all transactions
- Automatic cost basis calculation with weighted averages
- Input validation and error handling
- Discord user integration with proper mentions
- Company name resolution for better user experience

Architecture:
- Implements discord.py Cog pattern for modular commands
- Async/await for non-blocking database operations
- Type hints for better code maintainability
- Comprehensive error handling and user feedback
"""

from discord.ext import commands
import discord
from typing import Optional

from database import (
    create_user,
    get_user,
    get_cash,
    update_cash,
    get_holding,
    get_holdings,
    update_holding,
    insert_holding,
    delete_holding,
)
from prices import get_price, get_company_name


class TradingCog(commands.Cog):
    """
    Discord cog containing all trading-related commands.
    
    This cog handles user account creation, balance checking, and
    stock trading operations (buy/sell) with real-time price data.
    """

    def __init__(self, bot: commands.Bot) -> None:
        """
        Initialize the trading cog.
        
        Args:
            bot: The Discord bot instance        """
        self.bot = bot

    @commands.command(name="join")
    async def join(self, ctx: commands.Context) -> None:
        """
        Create a new user profile with starting cash to begin trading.
        
        This command initializes a new user account with the default starting
        capital (typically $1,000,000). Each Discord user can only join once.
        
        Usage:
            !join
            
        Features:
            - Creates user account with configurable starting capital
            - Prevents duplicate accounts for the same Discord user
            - Sets initial portfolio value for ROI calculations
            - Provides confirmation message with starting balance
            
        Args:
            ctx: Discord command context containing user and channel info
            
        Example:
            User: !join
            Bot: Welcome! You've joined with $1,000,000.00 starting cash.
        """
        user_id = str(ctx.author.id)
        username = ctx.author.display_name
        if await get_user(user_id):
            await ctx.send(f"{ctx.author.mention} you already joined!")
        else:
            await create_user(user_id, username)
            await ctx.send(
                f"{ctx.author.mention} welcome! You've been given $1,000,000 virtual cash."
            )

    @commands.command(name="balance")
    async def balance(self, ctx: commands.Context) -> None:
        """Show the user's cash balance."""
        user_id = str(ctx.author.id)
        cash = await get_cash(user_id)
        if cash is not None:
            await ctx.send(f"{ctx.author.mention} your current balance is ${cash:,.2f}")
        else:
            await ctx.send(
                f"{ctx.author.mention} you haven't joined yet. Use `!join` to get started."
            )

    @commands.command(name="buy")
    async def buy(self, ctx: commands.Context, symbol: str, quantity: int) -> None:
        """Buy shares of a stock."""
        user_id = str(ctx.author.id)
        if quantity <= 0:
            await ctx.send("Quantity must be greater than 0.")
            return
        symbol = symbol.upper()
        company_name = await get_company_name(symbol)
        price = await get_price(symbol)
        if not price:
            await ctx.send(f"Could not fetch live price for `{symbol}` ({company_name}).")
            return
        cost = price * quantity
        cash = await get_cash(user_id)
        if cash is None:
            await ctx.send("You need to `!join` before trading.")
            return
        if cash < cost:
            await ctx.send(
                f"❌ **Insufficient funds!** You need ${cost:,.2f} but only have ${cash:,.2f}"
            )
            return
        holding = await get_holding(user_id, symbol)
        if holding:
            shares, avg = holding
            total = shares + quantity
            new_avg = ((shares * avg) + (quantity * price)) / total
            await update_holding(user_id, symbol, total, new_avg)
        else:
            await insert_holding(user_id, symbol, quantity, price)
        await update_cash(user_id, cash - cost)
        await ctx.send(
            f"✅ {ctx.author.mention} bought **{quantity} shares** of `{symbol}` ({company_name}) at ${price:,.2f} each\n"
            f"💰 Total cost: ${cost:,.2f}"
        )

    @commands.command(name="sell")
    async def sell(self, ctx: commands.Context, symbol: str, quantity: int) -> None:
        """Sell shares of a stock."""
        user_id = str(ctx.author.id)
        if quantity <= 0:
            await ctx.send("Quantity must be greater than 0.")
            return
        symbol = symbol.upper()
        company_name = await get_company_name(symbol)
        price = await get_price(symbol)
        if not price:
            await ctx.send(f"Could not fetch live price for `{symbol}` ({company_name}).")
            return
        holding = await get_holding(user_id, symbol)
        if not holding:
            await ctx.send(f"❌ You don't own any shares of `{symbol}` ({company_name}).")
            return
        shares_owned, avg_price = holding
        if shares_owned < quantity:
            await ctx.send(
                f"❌ You only have **{shares_owned}** shares of `{symbol}` ({company_name}) but tried to sell **{quantity}**."
            )
            return
        proceeds = price * quantity
        if shares_owned == quantity:
            await delete_holding(user_id, symbol)
        else:
            await update_holding(user_id, symbol, shares_owned - quantity, avg_price)
        cash = await get_cash(user_id) or 0
        await update_cash(user_id, cash + proceeds)
        await ctx.send(
            f"✅ {ctx.author.mention} sold **{quantity} shares** of `{symbol}` ({company_name}) at ${price:,.2f} each\n"
            f"💰 Proceeds: ${proceeds:,.2f}"
        )

    @commands.command(name="USD")
    async def buy_usd(self, ctx: commands.Context, symbol: str, amount: float) -> None:
        """Buy shares using a dollar amount instead of quantity."""
        user_id = str(ctx.author.id)
        if amount <= 0:
            await ctx.send("Amount must be greater than 0.")
            return
        symbol = symbol.upper()
        company_name = await get_company_name(symbol)
        price = await get_price(symbol)
        if not price:
            await ctx.send(f"Could not fetch live price for `{symbol}` ({company_name}).")
            return
        shares_possible = int(amount // price)
        if shares_possible <= 0:
            await ctx.send("Amount too small to buy even one share.")
            return
        actual_cost = shares_possible * price
        cash = await get_cash(user_id)
        if cash is None:
            await ctx.send("You need to `!join` before trading.")
            return
        if cash < actual_cost:
            await ctx.send(
                f"❌ **Insufficient funds!** You need ${actual_cost:,.2f} but only have ${cash:,.2f}"
            )
            return
        holding = await get_holding(user_id, symbol)
        if holding:
            shares, avg = holding
            total = shares + shares_possible
            new_avg = ((shares * avg) + (shares_possible * price)) / total
            await update_holding(user_id, symbol, total, new_avg)
        else:
            await insert_holding(user_id, symbol, shares_possible, price)
        await update_cash(user_id, cash - actual_cost)
        await ctx.send(
            f"✅ {ctx.author.mention} bought **{shares_possible} shares** of `{symbol}` ({company_name}) with ${actual_cost:,.2f}"
        )


async def setup(bot: commands.Bot) -> None:
    """Cog loader for dynamic imports."""
    await bot.add_cog(TradingCog(bot))
