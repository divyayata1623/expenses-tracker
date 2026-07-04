import sqlite3
import os
from datetime import date, timedelta
import random

os.makedirs("sample_data", exist_ok=True)

conn = sqlite3.connect("sample_data/expenses_sample.db")
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT,
        amount REAL NOT NULL
    )
""")

categories = {
    "Food": ["Lunch at cafe", "Groceries", "Coffee", "Dinner with friends"],
    "Transport": ["Auto fare", "Bus ticket", "Fuel", "Cab ride"],
    "Entertainment": ["Movie ticket", "Netflix subscription", "Concert"],
    "Bills": ["Electricity bill", "Mobile recharge", "Internet bill"],
    "Shopping": ["Clothes", "Stationery", "Gift"],
}

start_date = date(2026, 6, 1)
sample_rows = []
for i in range(40):
    day = start_date + timedelta(days=random.randint(0, 30))
    category = random.choice(list(categories.keys()))
    description = random.choice(categories[category])
    amount = round(random.uniform(50, 2000), 2)
    sample_rows.append((day.isoformat(), category, description, amount))

cursor.executemany(
    "INSERT INTO expenses (date, category, description, amount) VALUES (?, ?, ?, ?)",
    sample_rows
)

conn.commit()
conn.close()

print("Sample database created at sample_data/expenses_sample.db with 40 dummy entries.")