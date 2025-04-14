import discord
from discord.ext import commands
import aiosqlite
import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import matplotlib.pyplot as plt
import io
from datetime import datetime
import os
scheduler = AsyncIOScheduler()
print("Starting bot script...")  # Add this to the top of the file

TOKEN = os.getenv("TOKEN")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

DB_NAME = "trading_game.db"
async def get_price(symbol):
    url = f"https://finnhub.io/api/v1/quote?symbol={symbol.upper()}&token={FINNHUB_API_KEY}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            return data.get("c")  # current price
        
async def daily_update():
    channel = bot.get_channel(1361409115796017352)  # Replace with actual channel ID
    if not channel:
        return

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id, cash, last_value FROM users") as cursor:
            users = await cursor.fetchall()

        for user_id, cash, last_value in users:
            async with db.execute("SELECT symbol, shares FROM holdings WHERE user_id = ?", (user_id,)) as cursor:
                holdings = await cursor.fetchall()

            total_value = cash
            for symbol, shares in holdings:
                price = await get_price(symbol)
                if price:
                    total_value += shares * price

            # Update last_value
            await db.execute("UPDATE users SET last_value = ? WHERE user_id = ?", (total_value, user_id))
            today = date.today().isoformat()
            await db.execute(
                "INSERT OR REPLACE INTO history (user_id, date, portfolio_value) VALUES (?, ?, ?)",
                (user_id, today, total_value)
)
            user = await bot.fetch_user(int(user_id))
            total_gain = ((total_value - 100000) / 100000) * 100
            day_gain = ((total_value - last_value) / last_value) * 100 if last_value else 0

            await channel.send(
                f"📈 {user.name}'s Portfolio Update:\n"
                f"Total Value: ${total_value:,.2f}\n"
                f"All-time ROI: {total_gain:+.2f}%\n"
                f"Daily Change: {day_gain:+.2f}%"
            )

        await db.commit()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                cash REAL DEFAULT 100000,
                initial_value REAL DEFAULT 100000,
                last_value REAL DEFAULT 100000
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS holdings (
                user_id TEXT,
                symbol TEXT,
                shares INTEGER,
                avg_price REAL,
                PRIMARY KEY (user_id, symbol)
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS history (
                user_id TEXT,
                date TEXT,
                portfolio_value REAL,
                PRIMARY KEY (user_id, date)
            )
        ''')
        await db.commit()

    if not scheduler.running:
        scheduler.start()
        scheduler.add_job(daily_update, "cron", hour=18, minute=0)  # or test with minute="*" for now

@bot.command(name="join")
async def join(ctx):
    user_id = str(ctx.author.id)

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()

        if user:
            await ctx.send(f"{ctx.author.mention} you already joined!")
        else:
            await db.execute("INSERT INTO users (user_id, cash) VALUES (?, ?)", (user_id, 100000))
            await db.commit()
            await ctx.send(f"{ctx.author.mention} welcome! You've been given $100,000 virtual cash.")
            
@bot.command(name="balance")
async def balance(ctx):
    user_id = str(ctx.author.id)

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT cash FROM users WHERE user_id = ?", (user_id,)) as cursor:
            result = await cursor.fetchone()

        if result:
            cash = result[0]
            await ctx.send(f"{ctx.author.mention} your current balance is ${cash:,.2f}")
        else:
            await ctx.send(f"{ctx.author.mention} you haven’t joined yet. Use `!join` to get started.")
            

@bot.command(name="sell")
async def sell(ctx, symbol: str, quantity: int):
    user_id = str(ctx.author.id)
    quantity = int(quantity)

    if quantity <= 0:
        await ctx.send("Quantity must be greater than 0.")
        return

    symbol = symbol.upper()
    price = await get_price(symbol)
    if price is None or price == 0:
        await ctx.send(f"Could not fetch live price for `{symbol}`.")
        return

    async with aiosqlite.connect(DB_NAME) as db:
        # Check holding
        async with db.execute("SELECT shares, avg_price FROM holdings WHERE user_id = ? AND symbol = ?", (user_id, symbol)) as cursor:
            holding = await cursor.fetchone()

        if not holding or holding[0] < quantity:
            await ctx.send(f"You don't have enough shares of `{symbol}` to sell.")
            return

        shares_owned, avg_price = holding
        proceeds = price * quantity

        # Update holdings
        if shares_owned == quantity:
            await db.execute("DELETE FROM holdings WHERE user_id = ? AND symbol = ?", (user_id, symbol))
        else:
            await db.execute("UPDATE holdings SET shares = ? WHERE user_id = ? AND symbol = ?", (shares_owned - quantity, user_id, symbol))

        # Add cash
        async with db.execute("SELECT cash FROM users WHERE user_id = ?", (user_id,)) as cursor:
            result = await cursor.fetchone()
        current_cash = result[0]
        new_cash = current_cash + proceeds

        await db.execute("UPDATE users SET cash = ? WHERE user_id = ?", (new_cash, user_id))
        await db.commit()

        await ctx.send(f"{ctx.author.mention} sold {quantity} shares of `{symbol}` at ${price:,.2f} each. Total: ${proceeds:,.2f}")

@bot.command(name="portfolio")
async def portfolio(ctx):
    user_id = str(ctx.author.id)

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT symbol, shares, avg_price FROM holdings WHERE user_id = ?", (user_id,)) as cursor:
            rows = await cursor.fetchall()

        if not rows:
            await ctx.send(f"{ctx.author.mention} you have no holdings.")
            return

        message_lines = [f"📊 **{ctx.author.display_name}'s Portfolio**"]
        total_value = 0

        for symbol, shares, avg_price in rows:
            price = await get_price(symbol)
            if not price:
                continue

            position_value = shares * price
            unrealized = (price - avg_price) * shares
            total_value += position_value

            message_lines.append(
                f"• `{symbol}` — {shares} shares @ ${avg_price:.2f} → ${price:.2f} | "
                f"Value: ${position_value:,.2f} | Unrealized: {'+' if unrealized >= 0 else '-'}${abs(unrealized):,.2f}"
            )

        message_lines.append(f"\n💼 **Total Holdings Value:** ${total_value:,.2f}")
        await ctx.send("\n".join(message_lines))
@bot.command(name="buy")
async def buy(ctx, symbol: str, quantity: int):
    user_id = str(ctx.author.id)
    quantity = int(quantity)

    if quantity <= 0:
        await ctx.send("Quantity must be greater than 0.")
        return

    price = await get_price(symbol)
    if price is None or price == 0:
        await ctx.send(f"Could not fetch live price for `{symbol.upper()}`.")
        return

    cost = price * quantity

    async with aiosqlite.connect(DB_NAME) as db:
        # Check user balance
        async with db.execute("SELECT cash FROM users WHERE user_id = ?", (user_id,)) as cursor:
            result = await cursor.fetchone()

        if not result:
            await ctx.send("You need to `!join` before trading.")
            return

        balance = result[0]
        if balance < cost:
            await ctx.send(f"Insufficient funds. You need ${cost:,.2f} but have ${balance:,.2f}")
            return

        # Deduct cash
        new_balance = balance - cost
        await db.execute("UPDATE users SET cash = ? WHERE user_id = ?", (new_balance, user_id))

        # Update holdings
        async with db.execute("SELECT shares, avg_price FROM holdings WHERE user_id = ? AND symbol = ?", (user_id, symbol.upper())) as cursor:
            holding = await cursor.fetchone()

        if holding:
            old_shares, old_avg_price = holding
            total_shares = old_shares + quantity
            new_avg_price = ((old_shares * old_avg_price) + (quantity * price)) / total_shares
            await db.execute(
                "UPDATE holdings SET shares = ?, avg_price = ? WHERE user_id = ? AND symbol = ?",
                (total_shares, new_avg_price, user_id, symbol.upper())
            )
        else:
            await db.execute(
                "INSERT INTO holdings (user_id, symbol, shares, avg_price) VALUES (?, ?, ?, ?)",
                (user_id, symbol.upper(), quantity, price)
            )

        await db.commit()
        await ctx.send(f"{ctx.author.mention} bought {quantity} shares of `{symbol.upper()}` at ${price:,.2f} each. Total: ${cost:,.2f}")
        
@bot.command(name="leaderboard")
async def leaderboard(ctx):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id, cash, initial_value FROM users") as cursor:
            user_data = await cursor.fetchall()

        leaderboard_entries = []

        for user_id, cash, initial in user_data:
            async with db.execute("SELECT symbol, shares FROM holdings WHERE user_id = ?", (user_id,)) as cursor:
                holdings = await cursor.fetchall()

            total_value = cash
            for symbol, shares in holdings:
                price = await get_price(symbol)
                if price:
                    total_value += shares * price

            roi = ((total_value - initial) / initial) * 100
            leaderboard_entries.append((user_id, total_value, roi))

        # Sort by ROI descending
        leaderboard_entries.sort(key=lambda x: x[2], reverse=True)

        if not leaderboard_entries:
            await ctx.send("No data for leaderboard yet.")
            return

        message = ["🏆 **Leaderboard - Top Traders by ROI** 🏆"]
        for i, (user_id, value, roi) in enumerate(leaderboard_entries[:10], start=1):
            user = await bot.fetch_user(int(user_id))
            message.append(
                f"{i}. **{user.name}** - ${value:,.2f} | ROI: {roi:+.2f}%"
            )

        await ctx.send("\n".join(message))
        
        
        
@bot.command(name="chart")
async def chart(ctx):
    user_id = str(ctx.author.id)

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT date, portfolio_value FROM history WHERE user_id = ? ORDER BY date", (user_id,)) as cursor:
            rows = await cursor.fetchall()

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

    await ctx.send(file=discord.File(buf, filename="portfolio_chart.png"))

if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"Error: {e}")