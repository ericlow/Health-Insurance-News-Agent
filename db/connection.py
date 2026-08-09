import psycopg2
from psycopg2 import pool, OperationalError, extensions
from config import DATABASE_URL

_pool = None

def _make_pool():
    return pool.SimpleConnectionPool(1, 5, DATABASE_URL)

def get_connection():
    global _pool
    if _pool is None:
        _pool = _make_pool()
    conn = _pool.getconn()
    try:
        if conn.status != extensions.STATUS_READY:
            conn.rollback()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
    except OperationalError:
        try:
            conn.close()
        except Exception:
            pass
        # ponytail: resets entire pool; fine since Lambda has one connection at a time
        _pool = _make_pool()
        conn = _pool.getconn()
    return conn

def release_connection(conn):
    if _pool:
        _pool.putconn(conn)
