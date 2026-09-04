import sqlite3
from pathlib import Path

DB_PATH = Path("airfares.db")

def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origin TEXT, dest TEXT,
            carrier_code TEXT, carrier_name TEXT,
            scrape_date TEXT, travel_date TEXT, advance_days INTEGER,
            total_fare REAL, flight_count INTEGER,
            source TEXT
        )
    """)
    conn.commit()
    conn.close()

def insert_fares(records: list[dict]):
    conn = get_conn()
    conn.executemany("""
        INSERT INTO fares (origin, dest, carrier_code, carrier_name,
                            scrape_date, travel_date, advance_days,
                            total_fare, flight_count, source)
        VALUES (:origin,:dest,:carrier_code,:carrier_name,
                :scrape_date,:travel_date,:advance_days,
                :total_fare,:flight_count,:source)
    """, records)
    conn.commit()
    conn.close()