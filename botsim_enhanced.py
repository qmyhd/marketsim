"""Compatibility wrapper for legacy imports."""
from prices import (
    get_price,
    preload_price_cache,
    price_cache,
    persist_price_cache,
    get_company_name,
)
from database import DB_NAME
from bot import main

__all__ = [
    "get_price",
    "preload_price_cache",
    "price_cache",
    "persist_price_cache",
    "get_company_name",
    "DB_NAME",
    "main",
]

if __name__ == "__main__":
    main()
