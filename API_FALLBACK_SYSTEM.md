# API Fallback System Documentation

## Overview
The trading bot implements a robust multi-provider price fetching system with comprehensive error handling, rate limiting, and fallback mechanisms.

## Provider Priority Order
1. **Finnhub Primary** - Main data source (with backoff protection)
2. **Yahoo Finance** - First fallback
3. **Polygon** - Second fallback  
4. **Alpaca** - Third fallback
5. **Cached Prices** - Memory cache (any age)
6. **Database Prices** - Last known prices from database

## Error Handling Improvements

### 1. JSON Parsing Protection
**Issue Fixed**: Previously parsed JSON on any 200 status without checking content-type
**Solution**: 
- Check `Content-Type` header before JSON parsing
- Catch `aiohttp.ContentTypeError` and `ValueError`
- Log non-JSON response text for debugging

```python
if 'application/json' in content_type:
    try:
        data = await resp.json()
        # Process data
    except (aiohttp.ContentTypeError, ValueError) as json_err:
        print(f"❌ Provider: JSON parsing error: {json_err}")
        text_response = await resp.text()
        print(f"❌ Provider: Response text: {text_response[:200]}")
        return None
```

### 2. Accurate Backoff Timing
**Issue Fixed**: Backoff timing used request start time instead of completion time
**Solution**:
- Use `time.time()` at actual completion for backoff calculations
- Separate tracking for Finnhub failures vs general provider failures
- More precise rate limiting

```python
# Before (inaccurate)
backoff_until = current_time + 60  # Used start time

# After (accurate) 
backoff_completion_time = time.time()  # Use completion time
backoff_until = backoff_completion_time + 60
```

### 3. Enhanced Rate Limit Handling
- Specific handling for 429 status codes
- Raises `ClientResponseError` to trigger backoff logic
- Distinguishes between rate limits and other HTTP errors

### 4. Improved Company Name Fetching
- Respects backoff periods to avoid additional API calls
- Proper JSON parsing with error handling
- Enhanced caching with fallback to symbol if name unavailable

## Caching Strategy

### Price Cache
- **TTL**: 24 hours (configurable via `PRICE_CACHE_TTL`)
- **Structure**: `{symbol: (price, timestamp)}`
- **Persistence**: Automatically saved to database
- **Fallback**: Uses any cached price if all providers fail

### Company Name Cache  
- **TTL**: 24 hours (configurable via `COMPANY_CACHE_TTL`)
- **Structure**: `{symbol: (name, timestamp)}`
- **Fallback**: Returns symbol if name unavailable

## Configuration Variables

### Environment Variables
```bash
# Cache settings
PRICE_CACHE_TTL=86400          # Price cache TTL (24 hours)
COMPANY_CACHE_TTL=86400        # Company name cache TTL (24 hours)
MIN_REQUEST_INTERVAL=2         # Minimum seconds between API requests

# API Keys
FINNHUB_API_KEY=your_key       # Primary Finnhub key
FINNHUB_API_KEY_SECOND=key2    # Secondary Finnhub key (unused currently)
Polygon_API_KEY=your_key       # Polygon.io key
ALPACA_API_KEY=your_key        # Alpaca API key
ALPACA_SECRET_KEY=your_secret  # Alpaca secret key
ALPACA_ENDPOINT=endpoint_url   # Alpaca endpoint (paper/live)
```

## API Provider Details

### Finnhub
- **Endpoint**: `https://finnhub.io/api/v1/quote?symbol={symbol}&token={api_key}`
- **Rate Limits**: Handles 429 responses with backoff
- **Data Field**: `c` (current price)

### Yahoo Finance  
- **Endpoint**: `https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbol}`
- **Rate Limits**: No authentication required
- **Data Field**: `quoteResponse.result[0].regularMarketPrice`

### Polygon
- **Endpoint**: `https://api.polygon.io/v2/aggs/ticker/{symbol}/prev?apikey={api_key}`
- **Rate Limits**: API key based
- **Data Field**: `results[0].c` (close price)

### Alpaca
- **Endpoint**: `{endpoint}/stocks/{symbol}/quotes/latest`
- **Authentication**: API key + secret in headers
- **Data Field**: Mid-price calculated from bid/ask (`(bp + ap) / 2`)

## Error Recovery Flow

```
Request Price for AAPL
├── Check Cache (< 24h) → Return if found
├── Check Rate Limiting → Skip to fallbacks if limited
├── Try Finnhub → 429 Rate Limited
│   ├── Set backoff_until = now + 60s
│   └── Continue to next provider
├── Try Yahoo Finance → Success! 
│   ├── Cache price with timestamp
│   ├── Save to database
│   └── Return price
└── If all fail:
    ├── Try stale cache (any age)
    ├── Try database lookup
    └── Return None if nothing available
```

## Database Schema

### last_price table
```sql
CREATE TABLE last_price (
    symbol TEXT PRIMARY KEY,
    price REAL,
    last_updated TEXT  -- SQLite CURRENT_TIMESTAMP
);
```

## Monitoring and Logging

All price fetching attempts are logged with emojis for easy monitoring:
- ✅ Success
- ❌ Error/Failure  
- ⚠️ Warning (rate limits, non-JSON responses)
- 🔄 Attempt/Retry
- 📦 Cache usage
- 🗄️ Database fallback
- ⏰ Backoff period

## Performance Considerations

1. **Request Throttling**: Minimum 2-second interval between requests
2. **Connection Reuse**: Uses `aiohttp.ClientSession` for efficient connection pooling
3. **Timeout Protection**: 10-second timeout on all HTTP requests
4. **Memory Efficiency**: Bounded cache with TTL cleanup
5. **Database Optimization**: Batch cache persistence with transaction commits

## Future Improvements

1. **Exponential Backoff**: Currently uses fixed 60-second backoff
2. **Circuit Breaker**: Could implement circuit breaker pattern for failed providers
3. **Metrics Collection**: Add performance metrics and success rates per provider
4. **Dynamic Provider Selection**: Prioritize providers based on recent success rates
