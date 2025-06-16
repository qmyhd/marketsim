import discord
from discord.ext import commands
import aiosqlite
import aiohttp
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io
from datetime import datetime, date
import os
import time
import atexit
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
print("Starting bot script...")  # Add this to the top of the file

TOKEN = os.getenv("TOKEN")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
FINNHUB_API_KEY_SECOND = os.getenv("FINNHUB_API_KEY_SECOND")
FINNHUB_API_KEY_2 = os.getenv("FINNHUB_API_KEY_2")  # Alternative naming

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

DB_NAME = os.getenv("DATABASE_URL", "/data/trading_game.db")

# Module-level price cache with timestamps
price_cache: dict[str, tuple[float, float]] = {}  # {symbol: (price, timestamp)}
# Cache time-to-live in seconds (override with PRICE_CACHE_TTL env var)
# Default is 24 hours to keep API usage minimal on Fly.io
CACHE_TTL = int(os.getenv("PRICE_CACHE_TTL", "86400"))
CACHE_DURATION = CACHE_TTL
backoff_until = 0.0  # timestamp until we should avoid API calls
rate_limit_until = 0.0  # timestamp until we should avoid API calls
# Minimal interval between API requests (to reduce Fly.io usage)
MIN_REQUEST_INTERVAL = float(os.getenv("MIN_REQUEST_INTERVAL", "2"))
last_request_time = 0.0

# Company name cache to avoid repeated API calls
company_name_cache: dict[str, tuple[str, float]] = {}
# Default TTL is one day since company names rarely change
COMPANY_CACHE_TTL = int(os.getenv("COMPANY_CACHE_TTL", "86400"))

# Persist all cached prices to the database
async def persist_price_cache() -> None:
    async with aiosqlite.connect(DB_NAME) as db:
        for symbol, (price, _) in price_cache.items():
            await db.execute(
                "INSERT OR REPLACE INTO last_price (symbol, price, last_updated) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (symbol, price),
            )
        await db.commit()

async def get_price_finnhub(symbol: str, api_key: str) -> float | None:
    """Get price from Finnhub API with proper error handling."""
    url = f"https://finnhub.io/api/v1/quote?symbol={symbol.upper()}&token={api_key}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                # Check content type first to avoid JSON parsing errors
                content_type = resp.headers.get('content-type', '').lower()
                
                if resp.status == 200:
                    if 'application/json' in content_type:
                        try:
                            data = await resp.json()
                            price = data.get("c")
                            if price and price > 0:
                                print(f"✅ Finnhub: Got price for {symbol}: ${price:.2f}")
                                return price
                        except (aiohttp.ContentTypeError, ValueError) as json_err:
                            print(f"❌ Finnhub: JSON parsing error for {symbol}: {json_err}")
                            text_response = await resp.text()
                            print(f"❌ Finnhub: Response text: {text_response[:200]}")
                            return None
                    else:
                        # Non-JSON response (possibly error message)
                        text_response = await resp.text()
                        print(f"❌ Finnhub: Non-JSON response for {symbol}: {text_response[:200]}")
                        return None
                elif resp.status == 429:
                    print(f"⚠️ Finnhub: Rate limited for {symbol}")
                    # Raise specific exception to trigger backoff
                    raise aiohttp.ClientResponseError(
                        request_info=resp.request_info,
                        history=resp.history,
                        status=429,
                        message="Rate limited"
                    )
                else:
                    text_response = await resp.text()
                    print(f"❌ Finnhub: Status {resp.status} for {symbol}: {text_response[:200]}")
                    return None
    except aiohttp.ClientResponseError as e:
        if e.status == 429:
            print(f"⚠️ Finnhub: Rate limit hit for {symbol}")
            raise  # Re-raise to trigger backoff logic
        else:
            print(f"❌ Finnhub HTTP error for {symbol}: {e}")
            return None
    except Exception as e:
        print(f"❌ Finnhub error for {symbol}: {e}")
        return None

async def get_price_yfinance(symbol: str) -> float | None:
    """Get price from Yahoo Finance API with proper error handling."""
    url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbol}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    content_type = resp.headers.get('content-type', '').lower()
                    if 'application/json' in content_type:
                        try:
                            data = await resp.json()
                            result = data.get("quoteResponse", {}).get("result", [])
                            if result:
                                price = result[0].get("regularMarketPrice")
                                if price and price > 0:
                                    print(f"✅ Yahoo Finance: Got price for {symbol}: ${price:.2f}")
                                    return price
                        except (aiohttp.ContentTypeError, ValueError) as json_err:
                            print(f"❌ Yahoo Finance: JSON parsing error for {symbol}: {json_err}")
                            return None
                    else:
                        text_response = await resp.text()
                        print(f"❌ Yahoo Finance: Non-JSON response for {symbol}: {text_response[:200]}")
                        return None
                else:
                    print(f"❌ Yahoo Finance: Status {resp.status} for {symbol}")
                    return None
    except Exception as e:
        print(f"❌ Yahoo Finance error for {symbol}: {e}")
        return None

async def get_price_polygon(symbol: str) -> float | None:
    """Get price from Polygon API with proper error handling."""
    api_key = os.getenv("Polygon_API_KEY")
    if not api_key:
        return None
    
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev?apikey={api_key}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    content_type = resp.headers.get('content-type', '').lower()
                    if 'application/json' in content_type:
                        try:
                            data = await resp.json()
                            results = data.get("results", [])
                            if results:
                                price = results[0].get("c")  # Close price
                                if price and price > 0:
                                    print(f"✅ Polygon: Got price for {symbol}: ${price:.2f}")
                                    return price
                        except (aiohttp.ContentTypeError, ValueError) as json_err:
                            print(f"❌ Polygon: JSON parsing error for {symbol}: {json_err}")
                            return None
                    else:
                        text_response = await resp.text()
                        print(f"❌ Polygon: Non-JSON response for {symbol}: {text_response[:200]}")
                        return None
                else:
                    print(f"❌ Polygon: Status {resp.status} for {symbol}")
                    return None
    except Exception as e:
        print(f"❌ Polygon error for {symbol}: {e}")
        return None

async def get_price_alpaca(symbol: str) -> float | None:
    """Get price from Alpaca API with proper error handling."""
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")
    endpoint = os.getenv("ALPACA_ENDPOINT", "https://paper-api.alpaca.markets/v2")
    
    if not api_key or not secret_key:
        return None
    
    url = f"{endpoint}/stocks/{symbol}/quotes/latest"
    headers = {
        "APCA-API-KEY-ID": api_key,
        "APCA-API-SECRET-KEY": secret_key
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    content_type = resp.headers.get('content-type', '').lower()
                    if 'application/json' in content_type:
                        try:
                            data = await resp.json()
                            quote = data.get("quote", {})
                            bid = quote.get("bp", 0)
                            ask = quote.get("ap", 0)
                            if bid > 0 and ask > 0:
                                price = (bid + ask) / 2  # Mid price
                                print(f"✅ Alpaca: Got price for {symbol}: ${price:.2f}")
                                return price
                        except (aiohttp.ContentTypeError, ValueError) as json_err:
                            print(f"❌ Alpaca: JSON parsing error for {symbol}: {json_err}")
                            return None
                    else:
                        text_response = await resp.text()
                        print(f"❌ Alpaca: Non-JSON response for {symbol}: {text_response[:200]}")
                        return None
                else:
                    print(f"❌ Alpaca: Status {resp.status} for {symbol}")
                    return None
    except Exception as e:
        print(f"❌ Alpaca error for {symbol}: {e}")
        return None

async def get_price(symbol: str) -> float | None:
    """
    Get stock price with comprehensive multi-provider fallback system:
    1. Check cache first (if fresh within CACHE_TTL)
    2. Try Finnhub primary key (if not in backoff period)
    3. Try Yahoo Finance API
    4. Try Polygon API (if API key available)
    5. Try Alpaca API (if API keys available)
    6. Fallback to cached price (any age)
    7. Fallback to database price
    
    Features:
    - Rate limit handling with 60-second backoff
    - JSON parsing error protection
    - Content-type validation
    - Request throttling (MIN_REQUEST_INTERVAL)
    - Comprehensive error logging
    """
    global backoff_until, rate_limit_until, last_request_time
    cache_key = symbol.upper()
    current_time = time.time()

    # Return cached price if it's newer than CACHE_TTL
    if cache_key in price_cache:
        cached_price, cached_time = price_cache[cache_key]
        if current_time - cached_time < CACHE_TTL:
            return cached_price

    # Throttle API usage
    if current_time - last_request_time < MIN_REQUEST_INTERVAL:
        if cache_key in price_cache:
            return price_cache[cache_key][0]
        db_price = await get_last_price_from_db(symbol)
        if db_price is not None:
            return db_price
        return None
    
    # Check if we're in a backoff/rate limit period for Finnhub
    if current_time < max(backoff_until, rate_limit_until):
        print(f"⏰ In backoff period, skipping Finnhub for {symbol}")
        finnhub_available = False
    else:
        finnhub_available = True

    # Update request time at the actual time of request
    last_request_time = time.time()
    
    # Provider priority order
    providers = []
    
    # 1. Try Finnhub primary key (if not in backoff)
    if finnhub_available and FINNHUB_API_KEY:
        providers.append(("Finnhub Primary", lambda: get_price_finnhub(symbol, FINNHUB_API_KEY)))
    
    # 2. Try Yahoo Finance
    providers.append(("Yahoo Finance", lambda: get_price_yfinance(symbol)))
    
    # 3. Try Polygon
    providers.append(("Polygon", lambda: get_price_polygon(symbol)))
    
    # 4. Try Alpaca
    providers.append(("Alpaca", lambda: get_price_alpaca(symbol)))

    # Track if Finnhub specifically failed for backoff logic
    finnhub_failed = False
    
    # Try each provider in order
    for provider_name, provider_func in providers:
        try:
            print(f"🔄 Trying {provider_name} for {symbol}...")
            price = await provider_func()
            
            if price and price > 0:
                # Success! Cache the result and save to database
                completion_time = time.time()  # Use actual completion time for accurate cache timestamps
                price_cache[cache_key] = (price, completion_time)
                
                # Save to database
                try:
                    async with aiosqlite.connect(DB_NAME) as db:
                        await db.execute(
                            "INSERT OR REPLACE INTO last_price (symbol, price, last_updated) VALUES (?, ?, CURRENT_TIMESTAMP)",
                            (symbol.upper(), price)
                        )
                        await db.commit()
                except Exception as db_e:
                    print(f"⚠️ Database save error for {symbol}: {db_e}")
                
                return price
                
        except aiohttp.ClientResponseError as e:
            if e.status == 429 and provider_name == "Finnhub Primary":
                print(f"⚠️ Finnhub rate limit hit for {symbol}, setting backoff")
                finnhub_failed = True
                # Set backoff using current completion time, not start time
                backoff_completion_time = time.time()
                backoff_until = backoff_completion_time + 60
                rate_limit_until = backoff_completion_time + 60
            else:
                print(f"❌ {provider_name} HTTP error for {symbol}: {e}")
            continue
        except Exception as e:
            if provider_name == "Finnhub Primary":
                finnhub_failed = True
            print(f"❌ {provider_name} failed for {symbol}: {e}")
            continue
    
    # If Finnhub was attempted and failed (not due to backoff), set backoff
    if finnhub_available and finnhub_failed:
        backoff_completion_time = time.time()
        backoff_until = backoff_completion_time + 60
        rate_limit_until = backoff_completion_time + 60
        print(f"⚠️ Finnhub failed, setting 60s backoff for future requests")

    # All providers failed - use fallbacks
    print(f"🔄 All providers failed for {symbol}, trying fallbacks...")
    
    # Fallback 1: Use any cached price (regardless of age)
    if cache_key in price_cache:
        cached_price, cached_time = price_cache[cache_key]
        age_hours = (current_time - cached_time) / 3600
        print(f"📦 Using stale cached price for {symbol}: ${cached_price:.2f} (age: {age_hours:.1f}h)")
        return cached_price
    
    # Fallback 2: Use database price
    db_price = await get_last_price_from_db(symbol)
    if db_price is not None:
        print(f"🗄️ Using database fallback for {symbol}: ${db_price:.2f}")
        return db_price
    
    print(f"❌ No price available for {symbol} from any source")
    return None

async def get_company_name(symbol: str) -> str:
    """Get company name from Finnhub API with caching and proper error handling."""
    cache_key = symbol.upper()
    current_time = time.time()

    # Serve from cache if not expired
    if cache_key in company_name_cache:
        name, ts = company_name_cache[cache_key]
        if current_time - ts < COMPANY_CACHE_TTL:
            return name

    # Don't fetch company names if we're in backoff period
    if current_time < max(backoff_until, rate_limit_until):
        if cache_key in company_name_cache:
            return company_name_cache[cache_key][0]
        return cache_key

    url = f"https://finnhub.io/api/v1/stock/profile2?symbol={cache_key}&token={FINNHUB_API_KEY}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    content_type = resp.headers.get('content-type', '').lower()
                    if 'application/json' in content_type:
                        try:
                            data = await resp.json()
                            name = data.get("name", cache_key)
                            if name and name != cache_key:
                                company_name_cache[cache_key] = (name, current_time)
                                return name
                        except (aiohttp.ContentTypeError, ValueError):
                            print(f"⚠️ Company name: JSON parsing error for {symbol}")
                    else:
                        print(f"⚠️ Company name: Non-JSON response for {symbol}")
                elif resp.status == 429:
                    print(f"⚠️ Company name: Rate limited for {symbol}")
                else:
                    print(f"⚠️ Company name: Status {resp.status} for {symbol}")
    except Exception as exc:
        print(f"Error fetching company name for {symbol}: {exc}")

    # Fallback to cached name or the symbol itself
    if cache_key in company_name_cache:
        return company_name_cache[cache_key][0]
    return cache_key
        
async def daily_update():
    """Send daily portfolio updates to the configured Discord channel."""
    # Get Discord channel ID from environment variable
    channel_id = os.getenv("DISCORD_CHANNEL_ID")
    if not channel_id:
        print("Warning: DISCORD_CHANNEL_ID not set in environment variables")
        return
    
    channel = bot.get_channel(int(channel_id))
    if not channel:
        print(f"Warning: Could not find Discord channel with ID: {channel_id}")
        return
        
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
            
            # Update last_value
            await db.execute("UPDATE users SET last_value = ? WHERE user_id = ?", (total_value, user_id))
            today = date.today().isoformat()
            await db.execute(
                "INSERT OR REPLACE INTO history (user_id, date, portfolio_value) VALUES (?, ?, ?)",
                (user_id, today, total_value)
            )
            
            user = await bot.fetch_user(int(user_id))
            # Calculate ROI using initial_value instead of hardcoded 1000000
            total_gain = ((total_value - initial_value) / initial_value) * 100
            day_gain = ((total_value - last_value) / last_value) * 100 if last_value else 0

            await channel.send(
                f"📈 {user.name}'s Portfolio Update:\n"
                f"Total Value: ${total_value:,.2f}\n"
                f"All-time ROI: {total_gain:+.2f}%\n"
                f"Daily Change: {day_gain:+.2f}%"
            )

        await db.commit()

async def preload_price_cache():
    """Load cached prices from the database into memory."""
    global price_cache
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT symbol, price, last_updated FROM last_price") as cursor:
            rows = await cursor.fetchall()
        
        for symbol, price, last_updated in rows:
            # Convert SQLite timestamp to Unix timestamp
            try:
                # Parse the CURRENT_TIMESTAMP format from SQLite
                dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                timestamp = dt.timestamp()
                price_cache[symbol.upper()] = (price, timestamp)
                print(f"Preloaded cached price for {symbol}: ${price:.2f}")
            except Exception as e:
                print(f"Error parsing timestamp for {symbol}: {e}")

async def get_last_price_from_db(symbol: str) -> float | None:
    """Retrieve last known price from the database."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT price FROM last_price WHERE symbol = ?", (symbol.upper(),)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return row[0]
    return None

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                cash REAL DEFAULT 1000000,
                initial_value REAL DEFAULT 1000000,
                last_value REAL DEFAULT 1000000,
                username TEXT
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS holdings (
                user_id TEXT,
                symbol TEXT,
                shares INTEGER,
                avg_price REAL,
                last_price REAL,
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
        await db.execute('''
            CREATE TABLE IF NOT EXISTS last_price (
                symbol TEXT PRIMARY KEY,
                price REAL,
                last_updated TEXT
            )
        ''')
        await db.commit()

    # Preload price cache from database
    await preload_price_cache()

@bot.command(name="join")
async def join(ctx):
    user_id = str(ctx.author.id)
    username = ctx.author.display_name

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            
        if user:
            await ctx.send(f"{ctx.author.mention} you already joined!")
        else:
            await db.execute("INSERT INTO users (user_id, cash, username) VALUES (?, ?, ?)", (user_id, 1000000, username))
            await db.commit()
            await ctx.send(f"{ctx.author.mention} welcome! You've been given $1,000,000 virtual cash.")
            
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
            await ctx.send(f"{ctx.author.mention} you haven't joined yet. Use `!join` to get started.")
            

@bot.command(name="sell")
async def sell(ctx, symbol: str, quantity: int):
    user_id = str(ctx.author.id)
    quantity = int(quantity)

    if quantity <= 0:
        await ctx.send("Quantity must be greater than 0.")
        return

    symbol = symbol.upper()
    
    # Get company name for verification
    company_name = await get_company_name(symbol)
    
    price = await get_price(symbol)
    if price is None or price == 0:
        await ctx.send(f"Could not fetch live price for `{symbol}` ({company_name}).")
        return

    async with aiosqlite.connect(DB_NAME) as db:
        # Check holding
        async with db.execute("SELECT shares, avg_price FROM holdings WHERE user_id = ? AND symbol = ?", (user_id, symbol)) as cursor:
            holding = await cursor.fetchone()

        if not holding:
            await ctx.send(f"❌ You don't own any shares of `{symbol}` ({company_name}).")
            return
            
        shares_owned, avg_price = holding
        
        if shares_owned < quantity:
            await ctx.send(f"❌ You only have **{shares_owned}** shares of `{symbol}` ({company_name}) but tried to sell **{quantity}**.")
            return

        proceeds = price * quantity
        gain_loss = (price - avg_price) * quantity
        gl_symbol = "📈" if gain_loss >= 0 else "📉"

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

        await ctx.send(f"✅ {ctx.author.mention} sold **{quantity} shares** of `{symbol}` ({company_name}) at ${price:,.2f} each\n"
                      f"💰 Proceeds: ${proceeds:,.2f} {gl_symbol} P&L: ${gain_loss:+,.2f} | Cash: ${new_cash:,.2f}")

@bot.command(name="portfolio")
async def portfolio(ctx):
    user_id = str(ctx.author.id)

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT symbol, shares, avg_price FROM holdings WHERE user_id = ?", (user_id,)) as cursor:
            rows = await cursor.fetchall()

        if not rows:
            await ctx.send(f"{ctx.author.mention} you have no holdings.")
            return

        # Get cash balance
        async with db.execute("SELECT cash FROM users WHERE user_id = ?", (user_id,)) as cursor:
            result = await cursor.fetchone()
        cash = result[0] if result else 0

        header = f"📊 **{ctx.author.display_name}'s Portfolio**\n"
        total_value = cash
        holdings_lines = []

        for symbol, shares, avg_price in rows:
            # Get company name for display
            company_name = await get_company_name(symbol)
            price = await get_price(symbol)
            if not price:
                continue

            position_value = shares * price
            unrealized = (price - avg_price) * shares
            pnl_symbol = "📈" if unrealized >= 0 else "📉"
            total_value += position_value

            # Compact format with company name
            holdings_lines.append(
                f"`{symbol}` ({company_name[:20]}{'...' if len(company_name) > 20 else ''})\n"
                f"  {shares}@${avg_price:.2f}→${price:.2f} ${position_value:,.0f} {pnl_symbol}${abs(unrealized):,.0f}"
            )
        
        # Summary
        holdings_value = total_value - cash
        
        # Get user's initial value for ROI calculation
        async with db.execute("SELECT initial_value FROM users WHERE user_id = ?", (user_id,)) as cursor:
            initial_result = await cursor.fetchone()
        initial_value = initial_result[0] if initial_result else 1000000
        
        roi = ((total_value - initial_value) / initial_value) * 100 if total_value > 0 else 0
        
        summary = (f"💰 Cash: ${cash:,.0f} | 💼 Holdings: ${holdings_value:,.0f}\n"
                  f"📈 Total: ${total_value:,.0f} | ROI: {roi:+.1f}%")

        # Split holdings into chunks if needed
        chunk_size = 5  # Holdings per message (reduced due to company names)
        for i in range(0, len(holdings_lines), chunk_size):
            chunk = holdings_lines[i:i + chunk_size]
            
            if i == 0:  # First chunk gets header
                message = header + "\n".join(chunk)
            else:  # Subsequent chunks
                message = "\n".join(chunk)
            
            # Add summary to last chunk
            if i + chunk_size >= len(holdings_lines):
                message += "\n\n" + summary
            
            await ctx.send(message)

@bot.command(name="buy")
async def buy(ctx, symbol: str, quantity: int):
    """Buy shares with exact share quantity. Use !USD for dollar amount purchases."""
    user_id = str(ctx.author.id)
    quantity = int(quantity)

    if quantity <= 0:
        await ctx.send("Quantity must be greater than 0.")
        return

    symbol = symbol.upper()
    
    # Get company name for verification
    company_name = await get_company_name(symbol)
    
    price = await get_price(symbol)
    if price is None or price == 0:
        await ctx.send(f"Could not fetch live price for `{symbol}` ({company_name}).")
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
            await ctx.send(f"❌ **Insufficient funds!** You need ${cost:,.2f} but only have ${balance:,.2f}\n"
                          f"💡 Try `!USD {symbol} {balance:.0f}` to buy with available cash.")
            return

        # Proceed with purchase - deduct cash
        new_balance = balance - cost
        await db.execute("UPDATE users SET cash = ? WHERE user_id = ?", (new_balance, user_id))

        # Update holdings
        async with db.execute("SELECT shares, avg_price FROM holdings WHERE user_id = ? AND symbol = ?", (user_id, symbol)) as cursor:
            holding = await cursor.fetchone()

        if holding:
            old_shares, old_avg_price = holding
            total_shares = old_shares + quantity
            new_avg_price = ((old_shares * old_avg_price) + (quantity * price)) / total_shares
            await db.execute(
                "UPDATE holdings SET shares = ?, avg_price = ? WHERE user_id = ? AND symbol = ?",
                (total_shares, new_avg_price, user_id, symbol)
            )
        else:
            await db.execute(
                "INSERT INTO holdings (user_id, symbol, shares, avg_price) VALUES (?, ?, ?, ?)",
                (user_id, symbol, quantity, price)
            )

        await db.commit()
        await ctx.send(f"✅ {ctx.author.mention} bought **{quantity} shares** of `{symbol}` ({company_name}) at ${price:,.2f} each\n"
                      f"💰 Total cost: ${cost:,.2f} | Remaining cash: ${new_balance:,.2f}")

@bot.command(name="USD")
async def buy_usd(ctx, symbol: str, amount: float):
    """Buy stocks with a dollar amount instead of share quantity."""
    user_id = str(ctx.author.id)
    amount = float(amount)

    if amount <= 0:
        await ctx.send("Amount must be greater than 0.")
        return

    symbol = symbol.upper()
    
    # Get company name for verification
    company_name = await get_company_name(symbol)
    
    price = await get_price(symbol)
    if price is None or price == 0:
        await ctx.send(f"Could not fetch live price for `{symbol}` ({company_name}).")
        return

    # Calculate how many shares this amount can buy
    shares_possible = int(amount / price)
    actual_cost = shares_possible * price

    if shares_possible == 0:
        await ctx.send(f"❌ ${amount:,.2f} is not enough to buy even 1 share of `{symbol}` ({company_name}) at ${price:,.2f}")
        return

    async with aiosqlite.connect(DB_NAME) as db:
        # Check user balance
        async with db.execute("SELECT cash FROM users WHERE user_id = ?", (user_id,)) as cursor:
            result = await cursor.fetchone()

        if not result:
            await ctx.send("You need to `!join` before trading.")
            return

        balance = result[0]
        if balance < actual_cost:
            await ctx.send(f"❌ **Insufficient funds!** You need ${actual_cost:,.2f} but only have ${balance:,.2f}")
            return

        # Proceed with purchase
        new_balance = balance - actual_cost
        await db.execute("UPDATE users SET cash = ? WHERE user_id = ?", (new_balance, user_id))

        # Update holdings
        async with db.execute("SELECT shares, avg_price FROM holdings WHERE user_id = ? AND symbol = ?", (user_id, symbol)) as cursor:
            holding = await cursor.fetchone()

        if holding:
            old_shares, old_avg_price = holding
            total_shares = old_shares + shares_possible
            new_avg_price = ((old_shares * old_avg_price) + (shares_possible * price)) / total_shares
            await db.execute(
                "UPDATE holdings SET shares = ?, avg_price = ? WHERE user_id = ? AND symbol = ?",
                (total_shares, new_avg_price, user_id, symbol)
            )
        else:
            await db.execute(
                "INSERT INTO holdings (user_id, symbol, shares, avg_price) VALUES (?, ?, ?, ?)",
                (user_id, symbol, shares_possible, price)
            )

        await db.commit()
        await ctx.send(f"✅ {ctx.author.mention} bought **{shares_possible} shares** of `{symbol}` ({company_name}) with ${actual_cost:,.2f}\n"
                      f"💰 Price per share: ${price:,.2f} | Remaining cash: ${new_balance:,.2f}")
        
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

    await ctx.send(file=discord.File(buf, "chart.png"))

if __name__ == "__main__":
    print("This module provides command implementations for the trading bot.")

def _flush_cache_sync() -> None:
    try:
        asyncio.run(persist_price_cache())
    except Exception:
        pass

atexit.register(_flush_cache_sync)
