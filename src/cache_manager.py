import sqlite3
import json
import zlib
import os
import time
from datetime import datetime, timedelta
import streamlit as st
import hashlib

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'eduplan_cache.db')

def init_db():
    """Initialize the SQLite database for caching and metrics."""
    # Ensure directory exists
    os.makedirs(os.path.dirname(DB_PATH) or '.', exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Cache table: stores compressed JSON responses
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cache (
        cache_key TEXT PRIMARY KEY,
        endpoint TEXT,
        data_blob BLOB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP,
        access_count INTEGER DEFAULT 0
    )
    ''')
    
    # Metrics table: tracks hit/miss and latency for analytics
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        endpoint TEXT,
        cache_type TEXT,
        hit BOOLEAN,
        latency_ms REAL
    )
    ''')
    
    # Index for faster cache lookup and cleanup
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache(expires_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp)')
    
    conn.commit()
    conn.close()

# Initialize upon import
init_db()

def _compress(data_dict: dict) -> bytes:
    """Serialize and compress a dictionary."""
    json_str = json.dumps(data_dict)
    return zlib.compress(json_str.encode('utf-8'))

def _decompress(compressed_data: bytes) -> dict:
    """Decompress and deserialize a dictionary."""
    json_str = zlib.decompress(compressed_data).decode('utf-8')
    return json.loads(json_str)

def get_sqlite_cache(cache_key: str):
    """Retrieve an item from the SQLite cache if it exists and is not expired."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT data_blob, expires_at FROM cache WHERE cache_key = ?
    ''', (cache_key,))
    
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
        
    data_blob, expires_at_str = row
    
    # Check expiration
    if expires_at_str:
        expires_at = datetime.fromisoformat(expires_at_str)
        if datetime.now() > expires_at:
            # Expired, delete it and return None
            cursor.execute('DELETE FROM cache WHERE cache_key = ?', (cache_key,))
            conn.commit()
            conn.close()
            return None
            
    # Update access count
    cursor.execute('''
        UPDATE cache SET access_count = access_count + 1 WHERE cache_key = ?
    ''', (cache_key,))
    conn.commit()
    conn.close()
    
    return _decompress(data_blob)

def set_sqlite_cache(cache_key: str, endpoint: str, data_dict: dict, ttl_days: int = 30):
    """Store an item in the SQLite cache with compression."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    expires_at = datetime.now() + timedelta(days=ttl_days)
    compressed_data = _compress(data_dict)
    
    cursor.execute('''
        INSERT OR REPLACE INTO cache (cache_key, endpoint, data_blob, expires_at, access_count)
        VALUES (?, ?, ?, ?, ?)
    ''', (cache_key, endpoint, compressed_data, expires_at.isoformat(), 0))
    
    conn.commit()
    conn.close()

def log_metric(endpoint: str, cache_type: str, hit: bool, latency_ms: float):
    """Log performance metrics."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO metrics (endpoint, cache_type, hit, latency_ms)
        VALUES (?, ?, ?, ?)
    ''', (endpoint, cache_type, hit, latency_ms))
    
    conn.commit()
    conn.close()

def cleanup_expired_cache():
    """Remove expired cache entries to prevent memory bloat."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    now = datetime.now().isoformat()
    cursor.execute('DELETE FROM cache WHERE expires_at < ?', (now,))
    deleted = cursor.rowcount
    
    conn.commit()
    conn.close()
    return deleted

def clear_all_cache():
    """Completely wipe both SQLite cache and st.cache_data."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM cache')
    conn.commit()
    conn.close()
    st.cache_data.clear()

def get_analytics():
    """Fetch aggregated cache analytics for the UI."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Total requests
    cursor.execute('SELECT COUNT(*) FROM metrics')
    total_requests = cursor.fetchone()[0]
    
    # Overall Hit Rate
    cursor.execute('SELECT COUNT(*) FROM metrics WHERE hit = 1')
    total_hits = cursor.fetchone()[0]
    hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0
    
    # Avg latency (cache vs live) - Lesson Plans
    cursor.execute('SELECT AVG(latency_ms) FROM metrics WHERE endpoint = "lesson_plan" AND hit = 1')
    avg_latency_cached = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT AVG(latency_ms) FROM metrics WHERE endpoint = "lesson_plan" AND hit = 0')
    avg_latency_live = cursor.fetchone()[0] or 0
    
    # SQLite cache size breakdown
    cursor.execute('SELECT COUNT(*), SUM(LENGTH(data_blob)) FROM cache')
    cache_row = cursor.fetchone()
    cache_items = cache_row[0] or 0
    cache_bytes = cache_row[1] or 0
    
    conn.close()
    
    return {
        "total_requests": total_requests,
        "hit_rate_pct": hit_rate,
        "avg_latency_cached_ms": avg_latency_cached,
        "avg_latency_live_ms": avg_latency_live,
        "sqlite_items": cache_items,
        "sqlite_size_mb": cache_bytes / (1024 * 1024)
    }

# -------------------------------------------------------------------------
# Dynamic Routing Logic
# -------------------------------------------------------------------------

def generate_cache_key(endpoint: str, **kwargs) -> str:
    """Generate a deterministic hash key from kwargs. Include model names."""
    # We sort keys to ensure stable hashing
    key_str = f"{endpoint}:" + ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
    return hashlib.md5(key_str.encode('utf-8')).hexdigest()

# For Streamlit native caching (ephemeral, small payloads like topics)
@st.cache_data(ttl=timedelta(hours=24))
def _st_cached_execute(endpoint: str, kwargs_hash: str, func, _func_kwargs: dict):
    # kwargs_hash parameter exists purely to segment the st.cache_data key correctly
    return func(**_func_kwargs)


def intelligent_cache(endpoint: str, cache_type: str = "sqlite", ttl_days: int = 30):
    """
    Decorator for intelligent dual-layer caching.
    :param endpoint: Identifier for logging (e.g., 'lesson_plan', 'topic_suggestions')
    :param cache_type: 'st' (Streamlit in-memory) or 'sqlite' (Persistent storage)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # 1. Generate unique deterministic cache key from parameters
            cache_key = generate_cache_key(endpoint, **kwargs)
            
            # 2. Check Cache
            cached_result = None
            if cache_type == "sqlite":
                cached_result = get_sqlite_cache(cache_key)
            else:
                pass # Streamlit checking goes below
                
            if cached_result is not None:
                latency = (time.time() - start_time) * 1000
                log_metric(endpoint, cache_type, hit=True, latency_ms=latency)
                
                # Tag it so the UI knows
                if isinstance(cached_result, dict):
                    cached_result["_served_from_cache"] = True
                    cached_result["_cache_latency_ms"] = latency
                    
                return cached_result
                
            # 3. Cache Miss - Execute actual function
            if cache_type == "st":
                # We defer to the st.cache_data wrapped helper function
                # Note: `st.cache_data` doesn't measure original execution latency out of the box easily,
                # but we can wrap it
                try:
                    result = _st_cached_execute(endpoint, cache_key, func, kwargs)
                    latency = (time.time() - start_time) * 1000
                    log_metric(endpoint, cache_type, hit=False, latency_ms=latency)
                    return result
                except Exception as e:
                    # In case st.cache_data throws unhashable errors, fallback to live
                    pass

            # Execute for SQLite or fallback
            result = func(*args, **kwargs)
            latency = (time.time() - start_time) * 1000
            
            # Log miss
            log_metric(endpoint, cache_type, hit=False, latency_ms=latency)
            
            # Save to cache if successful
            # Assuming our functions return dicts with a 'success' boolean
            is_success = isinstance(result, dict) and result.get("success", False)
            if is_success and cache_type == "sqlite":
                set_sqlite_cache(cache_key, endpoint, result, ttl_days=ttl_days)
                
            return result
            
        return wrapper
    return decorator
