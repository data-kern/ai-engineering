"""
KernMart's business database. GIVEN: do not edit.

Fictional retailer, synthetic data. In production this would be your order system behind an API.
The agent never touches this file or the database directly: it only gets the tools you build in agent.py.

Run `python setup_db.py` any time to reset the data to the exact same starting point.
"""
import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "data", "kernmart.db")

SCHEMA = """
CREATE TABLE customers(id TEXT PRIMARY KEY, name TEXT, email TEXT, tier TEXT);
CREATE TABLE orders(id TEXT PRIMARY KEY, customer_id TEXT, item TEXT, total_cents INTEGER, status TEXT,
                    ordered_on TEXT, promised_on TEXT, delivered_on TEXT, payment_method TEXT,
                    carrier TEXT, tracking_no TEXT);
CREATE TABLE shipment_events(id INTEGER PRIMARY KEY AUTOINCREMENT, order_id TEXT, ts TEXT, text TEXT);
"""


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row          # rows behave like dicts: row["item"]
    return con


def reset_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    con = connect()
    con.executescript(SCHEMA)
    con.executemany("INSERT INTO customers VALUES (?,?,?,?)", [
        ("C-1001", "Priya Nair", "priya.nair@example.com", "gold"),
        ("C-1002", "Tom de Vries", "tom.devries@example.com", "standard"),
        ("C-1003", "Sanne Bakker", "sanne.bakker@example.com", "standard"),
    ])
    con.executemany("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?)", [
        ("KM-48213", "C-1001", "Wireless Headphones", 8900, "delivered", "2026-10-04", "2026-10-10", "2026-10-16", "iDEAL", "PostNL", "3SKM48213"),
        ("KM-48100", "C-1001", "USB-C Cable (2 m)", 1299, "delivered", "2026-10-08", "2026-10-12", "2026-10-12", "iDEAL", "PostNL", "3SKM48100"),
        ("KM-48500", "C-1001", "Smart Speaker", 5900, "delivered", "2026-10-12", "2026-10-17", "2026-10-17", "Visa (ending 4242)", "DHL", "JVGL48500"),
        ("KM-50111", "C-1003", "Desk Lamp", 3450, "in_transit", "2026-10-17", "2026-10-22", None, "iDEAL", "PostNL", "3SKM50111"),
        ("KM-49007", "C-1002", "Espresso Machine", 14900, "delivered", "2026-10-09", "2026-10-15", "2026-10-15", "iDEAL", "DHL", "JVGL49007"),
    ])
    con.executemany("INSERT INTO shipment_events(order_id, ts, text) VALUES (?,?,?)", [
        ("KM-48213", "2026-10-04", "Label created"),
        ("KM-48213", "2026-10-08", "Left sorting centre"),
        ("KM-48213", "2026-10-12", "Delayed: sorting-centre congestion"),
        ("KM-48213", "2026-10-16", "Delivered to front door"),
        ("KM-50111", "2026-10-17", "Label created"),
        ("KM-50111", "2026-10-19", "Arrived at sorting centre Utrecht"),
        ("KM-50111", "2026-10-20", "Departed depot Zwolle, on the way to you. Expected 2026-10-22"),
        ("KM-49007", "2026-10-09", "Label created"),
        ("KM-49007", "2026-10-13", "Left sorting centre"),
        ("KM-49007", "2026-10-15", "Delivered, left with neighbour (no signature)."),
    ])
    con.commit()
    con.close()


if __name__ == "__main__":
    reset_db()
    con = connect()
    for table in ("customers", "orders", "shipment_events"):
        print(f"{table:<16} {con.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]} rows")
    con.close()
    print(f"Database ready: {DB_PATH}")
