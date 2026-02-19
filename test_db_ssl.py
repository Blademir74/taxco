import os
import sys

# Add dashboard to path so we can import queries
sys.path.insert(0, os.path.abspath("dashboard"))

# Mock streamlit for queries.py import (if strictly needed, but let's see)
# queries.py imports streamlit? 
# I will just try importing. If it fails, I will mock it.

try:
    from queries import get_engine
    from sqlalchemy import text
except ImportError as e:
    print(f"Import Error: {e}")
    # Create a mock streamlit module
    from unittest.mock import MagicMock
    sys.modules["streamlit"] = MagicMock()
    from queries import get_engine
    from sqlalchemy import text

print("--- Testing Database Connection Logic in queries.py ---")

# Test Case 1: No DATABASE_URL (Fallback to localhost + SSL)
if "DATABASE_URL" in os.environ:
    del os.environ["DATABASE_URL"]

try:
    engine = get_engine()
    url = str(engine.url)
    print(f"\nTest 1 (No Env): URL = {url}")
    # SQLAlchemy URL object might store query params in .query
    query_str = str(engine.url.query)
    if "sslmode=require" in url or "sslmode=require" in query_str or ('sslmode', 'require') in engine.url.query.items():
        print("PASS: SSL Mode enforced in fallback.")
    else:
        print("FAIL: SSL Mode MISSING in fallback.")
except Exception as e:
    print(f"Test 1 Error: {e}")

# Test Case 2: DATABASE_URL provided without SSL
os.environ["DATABASE_URL"] = "postgresql://user:pass@host:5432/db"
try:
    engine = get_engine()
    url = str(engine.url)
    print(f"\nTest 2 (Env without SSL): URL = {url}")
    query_str = str(engine.url.query)
    if "sslmode=require" in url or "sslmode=require" in query_str or ('sslmode', 'require') in engine.url.query.items():
         print("PASS: SSL Mode appended.")
    else:
         print("FAIL: SSL Mode NOT appended.")
except Exception as e:
    print(f"Test 2 Error: {e}")

# Test Case 3: DATABASE_URL provided WITH SSL
os.environ["DATABASE_URL"] = "postgresql://user:pass@host:5432/db?sslmode=require"
try:
    engine = get_engine()
    url = str(engine.url)
    print(f"\nTest 3 (Env with SSL): URL = {url}")
    if url.count("sslmode=require") == 1:
         print("PASS: SSL Mode preserved (not duplicated).")
    else:
         print(f"FAIL: SSL Mode count is {url.count('sslmode=require')}")
except Exception as e:
    print(f"Test 3 Error: {e}")
