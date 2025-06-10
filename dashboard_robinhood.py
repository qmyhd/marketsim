# Enhanced Trading Game Dashboard - Robinhood Style
from flask import Flask, render_template, url_for, redirect, jsonify
import sqlite3
import requests
from datetime import datetime, date
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ──────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
FINNHUB_API_KEY_SECOND = os.getenv("FINNHUB_API_KEY_SECOND")
FINNHUB_API_KEY_2 = os.getenv("FINNHUB_API_KEY_2")  # Alternative naming
DB_NAME = "trading_game.db"
APP_NAME = "Trading Dashboard"

app = Flask(__name__, template_folder="templates")

# Module-level price cache with timestamps (shared with bot)
price_cache = {}
# Cache time-to-live in seconds (override with PRICE_CACHE_TTL env var)
CACHE_DURATION = int(os.getenv("PRICE_CACHE_TTL", "14400"))
CACHE_TTL = CACHE_DURATION  # keep in sync with bot
rate_limit_until = 0  # timestamp until we should avoid API calls
last_request_time = 0  # throttle API requests
# Minimum seconds between API calls (shared with bot)
MIN_REQUEST_INTERVAL = float(os.getenv("MIN_REQUEST_INTERVAL", 2))
company_name_cache = {}
COMPANY_CACHE_TTL = int(os.getenv("COMPANY_CACHE_TTL", 86400))

# Cached leaderboard data to minimize API usage
dashboard_data = {"leaderboard": None, "summary": None, "timestamp": 0}
DASHBOARD_CACHE_DURATION = int(os.getenv("DASHBOARD_CACHE_DURATION", 300))

# ──────────────────────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────────────────────
def preload_price_cache():
    """Load cached prices from the database into memory."""
    global price_cache
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT symbol, price, last_updated FROM last_price")
        rows = cursor.fetchall()
        
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
    except sqlite3.OperationalError:
        # Table doesn't exist yet, that's okay
        print("last_price table doesn't exist yet, skipping price cache preload")
    finally:
        conn.close()

def get_last_price_from_db(symbol: str) -> float | None:
    """Get last known price for symbol from database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT price FROM last_price WHERE symbol = ?", (symbol.upper(),))
        result = cursor.fetchone()
        if result:
            return result[0]
    except sqlite3.OperationalError:
        # Table doesn't exist yet
        pass
    finally:
        conn.close()
    return None

def save_price_to_db(symbol: str, price: float) -> None:
    """Persist latest price to the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO last_price (symbol, price, last_updated) VALUES (?, ?, CURRENT_TIMESTAMP)",
        (symbol.upper(), price),
    )
    conn.commit()
    conn.close()

def get_price_yahoo(symbol: str) -> float | None:
    """Fetch price from Yahoo Finance as a fallback."""
    url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbol}"
    global last_request_time
    try:
        resp = requests.get(url, timeout=5)
        last_request_time = time.time()
        if resp.status_code == 200:
            data = resp.json()
            result = data.get("quoteResponse", {}).get("result", [])
            if result:
                price = result[0].get("regularMarketPrice")
                if price and price > 0:
                    return price
    except Exception as exc:
        print(f"Yahoo Finance error for {symbol}: {exc}")
    return None

def get_price(symbol: str) -> float | None:
    """Get stock price with caching and rate limit handling."""
    global rate_limit_until, last_request_time
    cache_key = symbol.upper()
    current_time = time.time()
    
    # Check if we have a cached price that's still fresh
    if cache_key in price_cache:
        cached_price, cached_time = price_cache[cache_key]
        if current_time - cached_time < CACHE_DURATION:
            return cached_price
    
    # Throttle requests to avoid excessive API usage
    if current_time - last_request_time < MIN_REQUEST_INTERVAL:
        if cache_key in price_cache:
            cached_price, _ = price_cache[cache_key]
            return cached_price
        db_price = get_last_price_from_db(symbol)
        if db_price:
            return db_price
        return None

    # Check if we're in a rate limit period
    if current_time < rate_limit_until:
        # Return cached price if available during rate limit
        if cache_key in price_cache:
            cached_price, _ = price_cache[cache_key]
            print(f"Rate limited, using cached price for {symbol}: ${cached_price:.2f}")
            return cached_price
        return None
    
    # Try primary API key first
    api_key = FINNHUB_API_KEY
    url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={api_key}"
    
    try:
        response = requests.get(url, timeout=5)
        last_request_time = time.time()
        
        if response.status_code == 429:
            # Rate limited - set rate limit period and try secondary key
            rate_limit_until = current_time + 60
            print(f"Rate limited on primary key, trying secondary key for {symbol}")
            
            if FINNHUB_API_KEY_SECOND:
                url_secondary = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_API_KEY_SECOND}"
                response_secondary = requests.get(url_secondary, timeout=5)
                last_request_time = time.time()

                if response_secondary.status_code == 200:
                    data = response_secondary.json()
                    price = data.get("c")
                    if price and price > 0:
                        # Cache the result
                        price_cache[cache_key] = (price, current_time)
                        save_price_to_db(symbol, price)
                        return price
                elif response_secondary.status_code == 429:
                    print(f"Secondary key also rate limited for {symbol}")
            
            # Try alternative key if available
            if FINNHUB_API_KEY_2:
                url_alt = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_API_KEY_2}"
                response_alt = requests.get(url_alt, timeout=5)
                last_request_time = time.time()

                if response_alt.status_code == 200:
                    data = response_alt.json()
                    price = data.get("c")
                    if price and price > 0:
                        # Cache the result
                        price_cache[cache_key] = (price, current_time)
                        save_price_to_db(symbol, price)
                        return price
            
            # If both keys are rate limited, return cached price if available
            if cache_key in price_cache:
                cached_price, _ = price_cache[cache_key]
                print(f"Both keys rate limited, using cached price for {symbol}: ${cached_price:.2f}")
                return cached_price
            return None
        
        elif response.status_code == 200:
            data = response.json()
            price = data.get("c")
            if price and price > 0:
                # Cache the result
                price_cache[cache_key] = (price, current_time)
                save_price_to_db(symbol, price)
                return price
        
        # API call failed, attempt Yahoo Finance fallback
        yahoo_price = get_price_yahoo(symbol)
        if yahoo_price:
            price_cache[cache_key] = (yahoo_price, current_time)
            save_price_to_db(symbol, yahoo_price)
            return yahoo_price

        # Use cached price if available
        if cache_key in price_cache:
            cached_price, _ = price_cache[cache_key]
            print(f"API call failed, using cached price for {symbol}: ${cached_price:.2f}")
            return cached_price
        return None
        
    except Exception as e:
        print(f"Error fetching price for {symbol}: {e}")

        yahoo_price = get_price_yahoo(symbol)
        if yahoo_price:
            price_cache[cache_key] = (yahoo_price, current_time)
            save_price_to_db(symbol, yahoo_price)
            return yahoo_price

        if cache_key in price_cache:
            cached_price, _ = price_cache[cache_key]
            return cached_price

        db_price = get_last_price_from_db(symbol)
        if db_price:
            print(f"Using database fallback price for {symbol}: ${db_price:.2f}")
            return db_price

        return None

def get_company_name(symbol: str) -> str | None:
    """Return company name with caching."""
    key = symbol.upper()
    current_time = time.time()

    if key in company_name_cache:
        name, ts = company_name_cache[key]
        if current_time - ts < COMPANY_CACHE_TTL:
            return name

    url = f"https://finnhub.io/api/v1/stock/profile2?symbol={key}&token={FINNHUB_API_KEY}"
    global last_request_time
    try:
        response = requests.get(url, timeout=5)
        last_request_time = time.time()
        if response.status_code == 200:
            data = response.json()
            name = data.get("name", key)
            company_name_cache[key] = (name, current_time)
            return name
    except Exception as e:
        print(f"Error fetching company name for {symbol}: {e}")

    if key in company_name_cache:
        return company_name_cache[key][0]
    return None

def fetch_leaderboard():
    """Return sorted leaderboard list and summary statistics."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Get all users
    cursor.execute("SELECT user_id, cash, initial_value, username FROM users")
    users = cursor.fetchall()
    
    leaderboard = []
    total_aum = 0
    total_roi = 0
    valid_users = 0
    
    for user_id, cash, initial_value, username in users:
        name = username if username else f"User-{user_id[-4:]}"
        # Get holdings
        cursor.execute("SELECT symbol, shares, avg_price FROM holdings WHERE user_id = ?", (user_id,))
        holdings = cursor.fetchall()
        
        # Calculate portfolio value
        holdings_value = 0
        total_holdings = len(holdings)
        for symbol, shares, avg_price in holdings:
            price = get_price(symbol)
            if price:
                holdings_value += price * shares
            else:
                # Fallback to database for last known price
                db_price = get_last_price_from_db(symbol)
                if db_price:
                    print(f"Using database fallback for {symbol} in leaderboard: ${db_price:.2f}")
                    holdings_value += db_price * shares
        
        total_value = cash + holdings_value
        roi = ((total_value - initial_value) / initial_value) * 100 if initial_value else 0
        pnl = total_value - initial_value
        
        leaderboard.append({
            "user_id": user_id,
            "name": name,
            "cash": cash,
            "holdings_value": holdings_value,
            "total_value": total_value,
            "roi": roi,
            "pnl": pnl,
            "total_holdings": total_holdings
        })
        
        total_aum += total_value
        if initial_value > 0:
            total_roi += roi
            valid_users += 1
    
    # Sort by total value descending
    leaderboard.sort(key=lambda x: x["total_value"], reverse=True)
    
    # Calculate summary stats
    avg_roi = total_roi / valid_users if valid_users > 0 else 0
    best_performer = leaderboard[0]["name"] if leaderboard else "N/A"
    
    summary = {
        "total_users": len(users),
        "total_aum": total_aum,
        "avg_roi": avg_roi,
        "best_performer": best_performer
    }
    
    conn.close()
    return leaderboard, summary

def fetch_user_portfolio(user_id: str):
    """Return detailed portfolio data for a specific user."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Get user data
    cursor.execute("SELECT username, cash, initial_value FROM users WHERE user_id = ?", (user_id,))
    user_row = cursor.fetchone()
    
    if not user_row:
        conn.close()
        return None
    
    username, cash, initial_value = user_row
    name = username if username else f"User-{user_id[-4:]}"
    
    # Get holdings
    cursor.execute("SELECT symbol, shares, avg_price FROM holdings WHERE user_id = ?", (user_id,))
    holdings_rows = cursor.fetchall()
    
    holdings = []
    holdings_value = 0
    for symbol, shares, avg_price in holdings_rows:
        price = get_price(symbol)
        if not price:
            # Try database fallback for last known price
            db_price = get_last_price_from_db(symbol)
            if db_price:
                print(f"Using database fallback for {symbol} in user portfolio: ${db_price:.2f}")
                price = db_price
            else:
                # Skip positions where we can't get any price to avoid incorrect P&L
                print(f"Warning: Could not fetch price for {symbol}, skipping from portfolio calculation")
                continue
            
        value = price * shares
        change = ((price - avg_price) / avg_price) * 100 if avg_price else 0
        unrealized_pnl = (price - avg_price) * shares
        holdings_value += value
        
        # Get company name
        company_name = get_company_name(symbol)
        
        holdings.append({
            "symbol": symbol,
            "company_name": company_name or symbol,
            "shares": shares,
            "avg_price": avg_price,
            "price": price,
            "value": value,
            "change": change,
            "unrealized_pnl": unrealized_pnl,
            "portfolio_percent": 0  # Will calculate after we know total
        })
    
    # Calculate total value and portfolio percentages
    total_value = cash + holdings_value
    for holding in holdings:
        holding["portfolio_percent"] = (holding["value"] / total_value) * 100 if total_value > 0 else 0
    
    # Sort holdings by value descending
    holdings.sort(key=lambda h: h["value"], reverse=True)
    
    # Get historical data
    cursor.execute("SELECT date, portfolio_value FROM history WHERE user_id = ? ORDER BY date", (user_id,))
    history_rows = cursor.fetchall()
    
    history_dates = [row[0] for row in history_rows]
    history_values = [row[1] for row in history_rows]
    
    # Prepare pie chart data (include cash as a slice if > 0)
    pie_labels = [h["symbol"] for h in holdings]
    pie_values = [h["value"] for h in holdings]
    
    if cash > 0:
        pie_labels.append("Cash")
        pie_values.append(cash)
    
    roi = ((total_value - initial_value) / initial_value) * 100 if initial_value else 0
    
    conn.close()
    
    return {
        "name": name,
        "cash": cash,
        "holdings_value": holdings_value,
        "total_value": total_value,
        "roi": roi,
        "holdings": holdings,
        "pie_labels": pie_labels,
        "pie_values": pie_values,
        "history_dates": history_dates,
        "history_values": history_values
    }

def refresh_dashboard_data() -> None:
    """Refresh leaderboard cache."""
    global dashboard_data
    leaderboard, summary = fetch_leaderboard()
    dashboard_data = {
        "leaderboard": leaderboard,
        "summary": summary,
        "timestamp": time.time(),
    }

# ──────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────
@app.route("/health")
def health():
    return "OK", 200

@app.route("/")
def index():
    current_time = time.time()
    if (
        dashboard_data["leaderboard"] is None
        or current_time - dashboard_data["timestamp"] > DASHBOARD_CACHE_DURATION
    ):
        refresh_dashboard_data()
    return render_template(
        "index.html",
        leaderboard=dashboard_data["leaderboard"],
        summary=dashboard_data["summary"],
        app_name=APP_NAME,
    )

@app.route("/user/<user_id>")
def user_detail(user_id):
    user_data = fetch_user_portfolio(user_id)
    if not user_data:
        return redirect(url_for("index"))

    return render_template(
        "user.html",
        user=user_data,
        app_name=APP_NAME
    )

@app.route("/api/refresh")
def api_refresh():
    """API endpoint to refresh data without full page reload."""
    refresh_dashboard_data()
    return jsonify({"leaderboard": dashboard_data["leaderboard"], "summary": dashboard_data["summary"]})

# ──────────────────────────────────────────────────────────────
# Run
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"🚀 Starting {APP_NAME}")
    
    # Preload price cache from database
    print("📈 Preloading price cache from database...")
    preload_price_cache()
    refresh_dashboard_data()
    
    port = int(os.getenv("PORT", 8080))  # Use Fly.io's PORT or default to 8080
    print(f"📊 Dashboard will be available at: http://localhost:{port}")
    print("🎨 Now featuring Robinhood-style design!")
    app.run(debug=False, host="0.0.0.0", port=port)
