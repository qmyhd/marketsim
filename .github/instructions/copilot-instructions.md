---
applyTo: '**'
---
Use Python 3.11 syntax and typing. Follow PEP 8 with **double quotes** and full type hints in all Python code.

Always update `.env.example` and the README when adding, removing, or renaming environment variables or setup steps.

When modifying or adding Python files, run:
`python -m py_compile $(git ls-files '*.py')`
before commits to catch syntax or environment-related issues early.

Never run or auto-start the Discord bot (`bot.py`) or dashboard (`dashboard_robinhood.py`) during static analysis or testing—compilation is sufficient for QA.

Respect the modular structure:
- `bot.py` should only handle startup, cog loading, and global setup.
- Cogs must define an async `setup()` function and cleanly register commands.
- `database.py` manages schema creation, user defaults, and persistent config like `DEFAULT_STARTING_CASH`.

When adding new command modules:
- Place them in `commands/` and name them clearly (e.g., `trading.py`, `stats.py`).
- Ensure they don’t introduce circular imports or hard-coded environment dependencies.

For caching, TTLs, and rate-limiting logic:
- Use `CACHE_TTL`, `MIN_REQUEST_INTERVAL`, and `backoff_until` from `prices.py`.
- APIs like Finnhub must check for 429 errors and back off accordingly.

If making changes to command routing or execution logic, verify that each `@commands.command()` still runs under the expected prefix and context.

When adding new endpoints or providers, update `price_cache`, TTLs, and supported domains list.