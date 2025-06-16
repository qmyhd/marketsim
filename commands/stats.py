from discord.ext import commands
import discord
import matplotlib.pyplot as plt
import io

from database import (
    get_holdings,
    get_cash,
    get_user,
    get_all_users,
    get_history,
)
from prices import get_price, get_company_name

class StatsCog(commands.Cog):
    """Portfolio and stats commands."""

    def __init__(self, bot: commands.Bot):
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
                f"  {shares}@${avg_price:.2f}→${price:.2f} {position_value:,.0f} {pnl_symbol}${abs(unrealized):,.0f}"
            )
        holdings_value = total_value - cash
        user = await get_user(user_id)
        initial_value = user[2] if user else 1000000
        roi = ((total_value - initial_value) / initial_value) * 100 if total_value > 0 else 0
        summary = (
            f"💰 Cash: ${cash:,.0f} | 💼 Holdings: ${holdings_value:,.0f}\n"
            f"📈 Total: ${total_value:,.0f} | ROI: {roi:+.1f}%"
        )
        chunk_size = 5
        for i in range(0, len(holdings_lines), chunk_size):
            chunk = holdings_lines[i : i + chunk_size]
            message = header + "\n".join(chunk) if i == 0 else "\n".join(chunk)
            if i + chunk_size >= len(holdings_lines):
                message += "\n\n" + summary
            await ctx.send(message)

    @commands.command(name="leaderboard")
    async def leaderboard(self, ctx: commands.Context) -> None:
        """Show the top users ranked by ROI."""
        user_data = await get_all_users()
        entries = []
        for user_id, cash, initial, _last in user_data:
            holdings = await get_holdings(user_id)
            total_value = cash
            for symbol, shares, _ in holdings:
                price = await get_price(symbol)
                if price:
                    total_value += shares * price
            roi = ((total_value - initial) / initial) * 100
            entries.append((user_id, total_value, roi))
        entries.sort(key=lambda x: x[2], reverse=True)
        if not entries:
            await ctx.send("No data for leaderboard yet.")
            return
        message = ["🏆 **Leaderboard - Top Traders by ROI** 🏆"]
        for i, (uid, value, roi) in enumerate(entries[:10], start=1):
            user = await self.bot.fetch_user(int(uid))
            message.append(f"{i}. **{user.name}** - ${value:,.2f} | ROI: {roi:+.2f}%")
        await ctx.send("\n".join(message))

    @commands.command(name="chart")
    async def chart(self, ctx: commands.Context) -> None:
        """Send a chart of the user's portfolio value over time."""
        rows = await get_history(str(ctx.author.id))
        if not rows or len(rows) < 2:
            await ctx.send("Not enough data to generate a chart yet.")
            return
        dates, values = zip(*rows)
        plt.figure(figsize=(10, 4))
        plt.plot(dates, values, marker="o")
        plt.xticks(rotation=45)
        plt.title(f"{ctx.author.display_name}'s Portfolio Value Over Time")
        plt.xlabel("Date")
        plt.ylabel("Value ($)")
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        plt.close()
        await ctx.send(file=discord.File(buf, "chart.png"))


async def setup(bot: commands.Bot) -> None:
    """Cog loader for StatsCog."""
    await bot.add_cog(StatsCog(bot))
