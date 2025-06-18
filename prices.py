"""
Market Sim Price Retrieval and Caching System
=============================================

This module handles real-time stock price fetching from multiple API providers
with intelligent caching, rate limiting, and fallback mechanisms. Optimized for
Fly.io free tier with memory-conscious LRU cache management.

Features:
- Multi-provider API support (Finnhub, Polygon, Alpaca, Yahoo Finance)
- Intelligent fallback system when primary APIs fail
- Memory-optimized caching with configurable limits
- Rate limiting and exponential backoff
- Persistent cache storage in database
- Company name resolution and caching

API Providers (in order of preference):
1. Finnhub - Primary real-time data provider
2. Polygon - Secondary provider with backup keys
3. Alpaca - Alternative financial data source
4. Yahoo Finance - Free fallback option

Cache Management:
- Price cache: Limited to 1,000 entries by default
- Company name cache: Limited to 500 entries by default  
- LRU eviction when memory limits are reached
- TTL-based expiration (24 hours default)
- Persistent storage in SQLite database

Environment Variables:
- FINNHUB_API_KEY: Primary API key for real-time data
- FINNHUB_API_KEY_SECOND, FINNHUB_API_KEY_2: Backup keys
- POLYGON_API_KEY: Alternative data provider
- ALPACA_API_KEY, ALPACA_SECRET_KEY: Alpaca API credentials
- PRICE_CACHE_TTL: Cache expiration time in seconds (default: 86400)
- MAX_PRICE_CACHE_SIZE: Maximum cached prices (default: 1000)
- MIN_REQUEST_INTERVAL: Minimum seconds between API calls (default: 2)
"""

import os
import time
import aiohttp
import aiosqlite
from datetime import datetime
from typing import Optional, Dict, Tuple, Any

from database import DB_NAME, get_last_price_from_db, update_last_price

# Load API keys
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
POLYGON_API_KEY = os.getenv("Polygon_API_KEY")
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
ALPACA_ENDPOINT = os.getenv("ALPACA_ENDPOINT", "https://paper-api.alpaca.markets/v2")

# Caches with memory optimization for Fly.io free tier
price_cache: dict[str, tuple[float, float]] = {}
CACHE_TTL = int(os.getenv("PRICE_CACHE_TTL", "86400"))
MIN_REQUEST_INTERVAL = float(os.getenv("MIN_REQUEST_INTERVAL", "2"))
# Limit cache size to save memory (free tier has only 256MB RAM)
MAX_CACHE_SIZE = int(os.getenv("MAX_PRICE_CACHE_SIZE", "1000"))
last_request_time = 0.0
backoff_until = 0.0
rate_limit_until = 0.0

company_name_cache: dict[str, tuple[str, float]] = {}
COMPANY_CACHE_TTL = int(os.getenv("COMPANY_CACHE_TTL", "86400"))
MAX_COMPANY_CACHE_SIZE = int(os.getenv("MAX_COMPANY_CACHE_SIZE", "500"))

async def persist_price_cache() -> None:
    """Store cached prices in the database."""
    async with aiosqlite.connect(DB_NAME) as db:
        for symbol, (price, _) in price_cache.items():
            await update_last_price(db, symbol, price)
        await db.commit()

def _cleanup_old_cache_entries() -> None:
    """Remove old entries from caches to save memory (LRU-style cleanup)."""
    current_time = time.time()
    
    # Clean price cache
    if len(price_cache) > MAX_CACHE_SIZE:
        # Remove oldest 20% of entries when cache is full
        items_to_remove = len(price_cache) - int(MAX_CACHE_SIZE * 0.8)
        sorted_items = sorted(price_cache.items(), key=lambda x: x[1][1])  # Sort by timestamp
        for symbol, _ in sorted_items[:items_to_remove]:
            del price_cache[symbol]
    
    # Clean company name cache  
    if len(company_name_cache) > MAX_COMPANY_CACHE_SIZE:
        items_to_remove = len(company_name_cache) - int(MAX_COMPANY_CACHE_SIZE * 0.8)
        sorted_items = sorted(company_name_cache.items(), key=lambda x: x[1][1])
        for symbol, _ in sorted_items[:items_to_remove]:
            del company_name_cache[symbol]

async def get_price_finnhub(symbol: str) -> float | None:
    """Fetch the latest price from Finnhub."""
    url = f"https://finnhub.io/api/v1/quote?symbol={symbol.upper()}&token={FINNHUB_API_KEY}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200 and 'application/json' in resp.headers.get('content-type', '').lower():
                    data = await resp.json()
                    price = data.get("c")
                    if price and price > 0:
                        return price
                elif resp.status == 429:
                    retry_after = resp.headers.get("Retry-After") or resp.headers.get("X-RateLimit-Reset")
                    wait = float(retry_after) if retry_after else 60
                    raise aiohttp.ClientResponseError(
                        request_info=resp.request_info,
                        history=resp.history,
                        status=429,
                        message="Rate limited",
                        headers={"retry-after": str(wait)},
                    )
    except aiohttp.ClientResponseError as e:
        if e.status == 429:
            raise
    except Exception:
        pass
    return None

async def get_price_yfinance(symbol: str) -> float | None:
    """Fetch the latest price from Yahoo Finance."""
    url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbol}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200 and 'application/json' in resp.headers.get('content-type', '').lower():
                    data = await resp.json()
                    result = data.get("quoteResponse", {}).get("result", [])
                    if result:
                        price = result[0].get("regularMarketPrice")
                        if price and price > 0:
                            return price
    except Exception:
        pass
    return None

async def get_price_polygon(symbol: str) -> float | None:
    """Fetch the latest price from Polygon."""
    if not POLYGON_API_KEY:
        return None
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev?apikey={POLYGON_API_KEY}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200 and 'application/json' in resp.headers.get('content-type', '').lower():
                    data = await resp.json()
                    results = data.get("results", [])
                    if results:
                        price = results[0].get("c")
                        if price and price > 0:
                            return price
    except Exception:
        pass
    return None

async def get_price_alpaca(symbol: str) -> float | None:
    """Fetch the latest price from Alpaca."""
    if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
        return None
    url = f"{ALPACA_ENDPOINT}/stocks/{symbol}/quotes/latest"
    headers = {
        "APCA-API-KEY-ID": ALPACA_API_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200 and 'application/json' in resp.headers.get('content-type', '').lower():
                    data = await resp.json()
                    quote = data.get("quote", {})
                    bid = quote.get("bp", 0)
                    ask = quote.get("ap", 0)
                    if bid > 0 and ask > 0:
                        return (bid + ask) / 2
    except Exception:
        pass
    return None

async def get_price(symbol: str) -> float | None:
    """Return the best available price using API fallbacks and cache."""
    global last_request_time, backoff_until, rate_limit_until
    symbol = symbol.upper()
    now = time.time()
    
    # Check cache first
    if symbol in price_cache:
        price, ts = price_cache[symbol]
        if now - ts < CACHE_TTL:
            return price
    
    # Rate limiting check
    if now - last_request_time < MIN_REQUEST_INTERVAL:
        cached = price_cache.get(symbol)
        if cached:
            return cached[0]
        return await get_last_price_from_db(symbol)
    
    # Memory optimization: cleanup cache if needed
    _cleanup_old_cache_entries()
    
    finnhub_ok = now >= max(backoff_until, rate_limit_until)
    last_request_time = time.time()
    providers = []
    if finnhub_ok and FINNHUB_API_KEY:
        providers.append(get_price_finnhub)
    providers.append(get_price_yfinance)
    providers.append(get_price_polygon)
    providers.append(get_price_alpaca)
    
    for provider in providers:
        try:
            price = await provider(symbol)
            if price and price > 0:
                price_cache[symbol] = (price, time.time())
                async with aiosqlite.connect(DB_NAME) as db:
                    await update_last_price(db, symbol, price)
                    await db.commit()
                return price
        except aiohttp.ClientResponseError as e:
            if e.status == 429 and provider is get_price_finnhub:
                retry_after = e.headers.get("retry-after") if e.headers else None
                wait = float(retry_after) if retry_after else 60
                backoff_until = rate_limit_until = time.time() + wait
        except Exception:
            pass
    
    # Fallback to cache or database
    cached = price_cache.get(symbol)
    if cached:
        return cached[0]
    return await get_last_price_from_db(symbol)

async def get_company_name(symbol: str) -> str:
    """Return the company name for a stock symbol."""
    symbol = symbol.upper()
    now = time.time()
    
    # Check cache first
    if symbol in company_name_cache:
        name, ts = company_name_cache[symbol]
        if now - ts < COMPANY_CACHE_TTL:
            return name
    
    # Rate limiting check
    if now < max(backoff_until, rate_limit_until):
        cached = company_name_cache.get(symbol)
        return cached[0] if cached else symbol
    
    # Memory optimization: cleanup cache if needed
    _cleanup_old_cache_entries()
    
    url = f"https://finnhub.io/api/v1/stock/profile2?symbol={symbol}&token={FINNHUB_API_KEY}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200 and 'application/json' in resp.headers.get('content-type', '').lower():
                    data = await resp.json()
                    name = data.get("name", symbol)
                    company_name_cache[symbol] = (name, now)
                    return name
    except Exception:
        pass
    
    cached = company_name_cache.get(symbol)
    return cached[0] if cached else symbol

async def preload_price_cache() -> None:
    """Load cached prices from the database into memory."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT symbol, price, last_updated FROM last_price") as cur:
            rows = await cur.fetchall()
        for symbol, price, last_updated in rows:
            try:
                dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                ts = dt.timestamp()
                price_cache[symbol.upper()] = (price, ts)
            except Exception:
                continue

async def clear_price_cache() -> None:
    """Remove all items from the in-memory price cache."""
    price_cache.clear()

