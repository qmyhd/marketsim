"""
Market Sim Statistics and Portfolio Commands Module
===================================================

This module implements portfolio analysis and statistics commands for the Market Sim bot.
It provides comprehensive portfolio tracking, leaderboards, performance charts, and
market statistics with real-time data integration.

Commands Provided:
- !portfolio: Complete portfolio view with P&L analysis
- !leaderboard: Top traders ranked by ROI performance
- !chart: Historical performance chart generation
- !stats: Overall market statistics and metrics

Features:
- Real-time portfolio valuation using current market prices
- ROI calculations based on initial investment values
- Interactive charts using matplotlib with Discord integration
- Comprehensive P&L analysis for individual positions
- Leaderboard rankings with performance metrics
- Historical data visualization and trend analysis

Technical Implementation:
- Async database operations for performance
- Real-time price fetching and validation
- Chart generation with matplotlib and Discord file uploads
- Error handling for invalid users or missing data
- Memory-efficient data processing for large portfolios
"""

from discord.ext import commands
import discord
import matplotlib.pyplot as plt
import io
from typing import List, Tuple, Optional, Any
from datetime import datetime

from database import (
    get_holdings,
    get_cash,
    get_user,
    get_all_users,
    get_history,
)
from prices import get_price, get_company_name


class StatsCog(commands.Cog):
    """
    Discord cog containing portfolio analysis and statistics commands.
    
    This cog provides comprehensive portfolio tracking, performance analysis,
    leaderboards, and market statistics for all users in the trading game.
    """

    def __init__(self, bot: commands.Bot) -> None:
        """
        Initialize the statistics cog.
        
        Args:
            bot: The Discord bot instance
        """
        self.bot = bot

    @commands.command(name="portfolio")
    async def portfolio(self, ctx: commands.Context) -> None:
        """Display the user's portfolio with ROI information."""
        user_id = str(ctx.author.id)
        rows = await get_holdings(user_id)
        if not rows:
            await ctx.send(f"{ctx.author.mention} you have no holdings.")
            return

        cash = await get_cash(user_id) or 0
        header = f"📊 **{ctx.author.display_name}'s Portfolio**\n"
        total_value = cash
        holdings_lines = []

        for symbol, shares, avg_price in rows:
            company_name = await get_company_name(symbol)
            price = await get_price(symbol)
            if not price:
                continue

            position_value = shares * price
            unrealized = (price - avg_price) * shares
            pnl_symbol = "📈" if unrealized >= 0 else "📉"
            total_value += position_value

            holdings_lines.append(
                f"`{symbol}` ({company_name[:20]}{'...' if len(company_name) > 20 else ''})\n"
                f"  {shares}@${avg_price:.2f}→${price:.2f} ${position_value:,.0f} {pnl_symbol}${abs(unrealized):,.0f}"
            )

        holdings_value = total_value - cash
        user = await get_user(user_id)
        initial_value = user[2] if user else 1000000
        roi = ((total_value - initial_value) / initial_value) * 100 if total_value > 0 else 0

        summary = (
            f"💰 Cash: ${cash:,.0f} | 💼 Holdings: ${holdings_value:,.0f}\n"
            f"💎 Total Value: ${total_value:,.0f} | 📈 ROI: {roi:+.2f}%"
        )

        message = header + "\n".join(holdings_lines) + f"\n\n{summary}"
        await ctx.send(message)

    @commands.command(name="leaderboard")
    async def leaderboard(self, ctx: commands.Context) -> None:
        """Show the top traders ranked by ROI."""
        users = await get_all_users()
        if not users:
            await ctx.send("No users found.")
            return

        # Calculate current portfolio values
        user_data = []
        for user_id, cash, initial_value, _ in users:
            holdings = await get_holdings(user_id)
            total_value = cash

            for symbol, shares, _ in holdings:
                price = await get_price(symbol)
                if price:
                    total_value += shares * price

            roi = ((total_value - initial_value) / initial_value) * 100 if initial_value > 0 else 0
            user_data.append((user_id, total_value, roi))

        # Sort by ROI (descending)
        user_data.sort(key=lambda x: x[2], reverse=True)

        lines = ["🏆 **Market Sim Leaderboard**\n"]
        for i, (user_id, total_value, roi) in enumerate(user_data[:10], 1):
            try:
                user = await self.bot.fetch_user(int(user_id))
                emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                lines.append(
                    f"{emoji} **{user.display_name}**: ${total_value:,.0f} ({roi:+.2f}%)"
                )
            except Exception:
                continue

        await ctx.send("\n".join(lines))

    @commands.command(name="chart")
    async def chart(self, ctx: commands.Context) -> None:
        """Generate a portfolio performance chart."""
        user_id = str(ctx.author.id)
        history = await get_history(user_id)
        
        if not history:
            await ctx.send(f"{ctx.author.mention} no portfolio history found.")
            return

        # Extract dates and values
        dates = [date for date, _ in history]
        values = [value for _, value in history]

        if len(values) < 2:
            await ctx.send(f"{ctx.author.mention} need at least 2 days of history for a chart.")
            return

        # Create the chart
        plt.figure(figsize=(10, 6))
        plt.plot(dates, values, linewidth=2, color='#00ff88')
        plt.title(f"{ctx.author.display_name}'s Portfolio Performance", fontsize=14, fontweight='bold')
        plt.xlabel('Date')
        plt.ylabel('Portfolio Value ($)')
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()

        # Format y-axis to show currency
        plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))

        # Save to bytes
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        plt.close()

        # Send as file
        file = discord.File(buffer, filename=f"{ctx.author.display_name}_portfolio.png")
        await ctx.send(file=file)

    @commands.command(name="stats")
    async def stats(self, ctx: commands.Context) -> None:
        """Show overall market statistics."""
        users = await get_all_users()
        if not users:
            await ctx.send("No market data available.")
            return

        total_users = len(users)
        total_aum = 0
        total_initial = 0

        for user_id, cash, initial_value, _ in users:
            holdings = await get_holdings(user_id)
            current_value = cash
            
            for symbol, shares, _ in holdings:
                price = await get_price(symbol)
                if price:
                    current_value += shares * price

            total_aum += current_value
            total_initial += initial_value

        avg_roi = ((total_aum - total_initial) / total_initial) * 100 if total_initial > 0 else 0

        stats_message = (
            "📊 **Market Statistics**\n"
            f"👥 Active Traders: {total_users}\n"
            f"💰 Assets Under Management: ${total_aum:,.0f}\n"
            f"📈 Average ROI: {avg_roi:+.2f}%"
        )

        await ctx.send(stats_message)


async def setup(bot: commands.Bot) -> None:
    """Cog loader for StatsCog."""
    await bot.add_cog(StatsCog(bot))
