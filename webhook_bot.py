import os
import asyncio
from datetime import date
import aiosqlite
import aiohttp
import discord
from dotenv import load_dotenv

from botsim_enhanced import (
    get_price,
    preload_price_cache,
    price_cache,
    persist_price_cache,
    DB_NAME,
)

load_dotenv()

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

async def send_message(content: str, file: discord.File | None = None) -> None:
    if WEBHOOK_URL:
        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(WEBHOOK_URL, session=session)
            await webhook.send(content, file=file)
    else:
        print(content)


async def daily_update() -> None:
    await preload_price_cache()
    messages = []
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id, cash, last_value, initial_value FROM users") as cursor:
            users = await cursor.fetchall()

        for user_id, cash, last_value, initial_value in users:
            async with db.execute("SELECT symbol, shares FROM holdings WHERE user_id = ?", (user_id,)) as cursor:
                holdings = await cursor.fetchall()

            total_value = cash
            for symbol, shares in holdings:
                price = await get_price(symbol)
                if price:
                    total_value += shares * price

            await db.execute("UPDATE users SET last_value = ? WHERE user_id = ?", (total_value, user_id))
            today = date.today().isoformat()
            await db.execute(
                "INSERT OR REPLACE INTO history (user_id, date, portfolio_value) VALUES (?, ?, ?)",
                (user_id, today, total_value),
            )

            total_gain = ((total_value - initial_value) / initial_value) * 100
            day_gain = ((total_value - last_value) / last_value) * 100 if last_value else 0
            messages.append(
                f"<@{user_id}> Portfolio ${total_value:,.2f} | ROI {total_gain:+.2f}% | Day {day_gain:+.2f}%"
            )
        await db.commit()

    if messages:
        await send_message("\n".join(messages))

COMMANDS = {"daily_update": daily_update}

async def main() -> None:
    command = os.getenv("BOT_COMMAND", "daily_update")
    handler = COMMANDS.get(command)
    if not handler:
        print(f"Unknown command: {command}")
        return
    try:
        await handler()
    finally:
        await persist_price_cache()

if __name__ == "__main__":
    asyncio.run(main())
