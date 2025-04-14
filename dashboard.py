from flask import Flask, render_template_string
import aiosqlite
import asyncio
import aiohttp

FINNHUB_API_KEY = "cvulv81r01qjg13ap430cvulv81r01qjg13ap43g"
DB_NAME = "trading_game.db"

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Trading Game Leaderboard</title>
    <style>
        body { font-family: Arial, sans-serif; background: #111; color: #eee; padding: 20px; }
        h1 { color: #0f0; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #555; padding: 8px; text-align: left; }
        th { background: #222; }
    </style>
</head>
<body>
    <h1>Leaderboard</h1>
    <table>
        <tr><th>Rank</th><th>User</th><th>Portfolio Value</th><th>ROI</th></tr>
        {% for entry in leaderboard %}
        <tr>
            <td>{{ loop.index }}</td>
            <td>{{ entry.name }}</td>
            <td>${{ "{:,.2f}".format(entry.value) }}</td>
            <td>{{ "{:+.2f}".format(entry.roi) }}%</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""

async def get_price(symbol):
    url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_API_KEY}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            return data.get("c")

async def fetch_leaderboard():
    entries = []
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id, cash, initial_value FROM users") as cursor:
            users = await cursor.fetchall()

        for user_id, cash, initial in users:
            async with db.execute("SELECT symbol, shares FROM holdings WHERE user_id = ?", (user_id,)) as cursor:
                holdings = await cursor.fetchall()

            value = cash
            for symbol, shares in holdings:
                price = await get_price(symbol)
                if price:
                    value += shares * price

            roi = ((value - initial) / initial) * 100
            entries.append({
                "id": user_id,
                "name": f"User-{user_id[-4:]}",  # anonymous for now
                "value": value,
                "roi": roi
            })

    entries.sort(key=lambda x: x["roi"], reverse=True)
    return entries

@app.route("/")
def index():
    leaderboard = asyncio.run(fetch_leaderboard())
    return render_template_string(HTML, leaderboard=leaderboard)

if __name__ == "__main__":
    app.run(debug=True)