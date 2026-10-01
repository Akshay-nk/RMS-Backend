import sqlite3
import os
import re
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "restaurant.db")
SQL_SEED_PATH = os.path.join(os.path.dirname(__file__), "seed_data.sql")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

@contextmanager
def get_db():
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS Menu (
    item_id TEXT PRIMARY KEY,
    item_name TEXT,
    item_type TEXT,
    item_category TEXT,
    item_price REAL,
    item_description TEXT
);

CREATE TABLE IF NOT EXISTS Accounts (
    account_id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT,
    register_date TEXT,
    phone_number TEXT,
    password TEXT
);

CREATE TABLE IF NOT EXISTS Staffs (
    staff_id INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_name TEXT,
    role TEXT,
    account_id INTEGER,
    FOREIGN KEY (account_id) REFERENCES Accounts(account_id)
);

CREATE TABLE IF NOT EXISTS Memberships (
    member_id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_name TEXT,
    points INTEGER DEFAULT 0,
    account_id INTEGER,
    FOREIGN KEY (account_id) REFERENCES Accounts(account_id)
);

CREATE TABLE IF NOT EXISTS Restaurant_Tables (
    table_id INTEGER PRIMARY KEY,
    capacity INTEGER,
    is_available INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS Table_Availability (
    availability_id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_id INTEGER,
    reservation_date TEXT,
    reservation_time TEXT,
    status TEXT,
    FOREIGN KEY (table_id) REFERENCES Restaurant_Tables(table_id)
);

CREATE TABLE IF NOT EXISTS Reservations (
    reservation_id INTEGER PRIMARY KEY,
    customer_name TEXT,
    table_id INTEGER,
    reservation_time TEXT,
    reservation_date TEXT,
    head_count INTEGER,
    special_request TEXT,
    FOREIGN KEY (table_id) REFERENCES Restaurant_Tables(table_id)
);

CREATE TABLE IF NOT EXISTS card_payments (
    card_id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_holder_name TEXT NOT NULL,
    card_number TEXT NOT NULL,
    expiry_date TEXT NOT NULL,
    security_code TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Bills (
    bill_id INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_id INTEGER,
    member_id INTEGER,
    reservation_id INTEGER,
    table_id INTEGER,
    card_id INTEGER,
    payment_method TEXT,
    bill_time TEXT,
    payment_time TEXT,
    FOREIGN KEY (staff_id) REFERENCES Staffs(staff_id),
    FOREIGN KEY (member_id) REFERENCES Memberships(member_id),
    FOREIGN KEY (reservation_id) REFERENCES Reservations(reservation_id),
    FOREIGN KEY (table_id) REFERENCES Restaurant_Tables(table_id),
    FOREIGN KEY (card_id) REFERENCES card_payments(card_id)
);

CREATE TABLE IF NOT EXISTS Bill_Items (
    bill_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id INTEGER,
    item_id TEXT,
    quantity INTEGER,
    FOREIGN KEY (bill_id) REFERENCES Bills(bill_id),
    FOREIGN KEY (item_id) REFERENCES Menu(item_id)
);

CREATE TABLE IF NOT EXISTS Kitchen (
    kitchen_id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_id INTEGER,
    item_id TEXT,
    quantity INTEGER,
    time_submitted TEXT,
    time_ended TEXT,
    FOREIGN KEY (table_id) REFERENCES Restaurant_Tables(table_id),
    FOREIGN KEY (item_id) REFERENCES Menu(item_id)
);
"""

def seed_database():
    with get_db() as conn:
        conn.executescript(CREATE_TABLES_SQL)
        
        # Check if already seeded
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Menu")
        if cursor.fetchone()[0] > 0:
            return  # Already seeded

        if not os.path.exists(SQL_SEED_PATH):
            print(f"Seed SQL file not found at {SQL_SEED_PATH}")
            return

        with open(SQL_SEED_PATH, "r", encoding="utf-8", errors="ignore") as f:
            sql_content = f.read()

        # Extract all INSERT statements
        lines = []
        for line in sql_content.splitlines():
            stripped = line.strip()
            if stripped.startswith("--") or stripped.startswith("/*"):
                continue
            lines.append(line)
        cleaned_sql = "\n".join(lines)

        statements = re.findall(r"INSERT\s+INTO\s+[^;]+;", cleaned_sql, re.IGNORECASE | re.DOTALL)
        for stmt in statements:
            try:
                conn.execute(stmt)
            except Exception as e:
                print(f"Warning inserting seed: {e}\nStatement: {stmt[:100]}...")

        conn.commit()
        print("Database seeded successfully from seed_data.sql.")

if __name__ == "__main__":
    seed_database()
    with get_db() as conn:
        for tbl in ["Menu", "Restaurant_Tables", "Accounts", "Staffs", "Memberships", "Reservations", "Bills", "Bill_Items", "Kitchen"]:
            count = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            print(f"Table '{tbl}': {count} records")
