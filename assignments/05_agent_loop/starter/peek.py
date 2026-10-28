"""
peek.py: look at the ground truth in KernMart's database. GIVEN: do not edit.

    python peek.py KM-48213       one order + its tracking events
    python peek.py                all orders
Use it to VALIDATE what your agent says: the database is the truth, the reply is a claim.
"""
import sys

from setup_db import DB_PATH, connect, reset_db

import os
if not os.path.exists(DB_PATH):
    reset_db()
con = connect()
if len(sys.argv) > 1:
    oid = sys.argv[1].upper()
    row = con.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    if row is None:
        sys.exit(f"{oid}: no such order")
    print({k: row[k] for k in row.keys()})
    for e in con.execute("SELECT ts, text FROM shipment_events WHERE order_id=? ORDER BY id", (oid,)):
        print("  ", e["ts"], e["text"])
else:
    for r in con.execute("SELECT id, customer_id, item, total_cents, status, promised_on, delivered_on FROM orders"):
        print(tuple(r))
