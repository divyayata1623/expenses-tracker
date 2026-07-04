"""
database.py
Handles all SQLite database operations for the Expense Tracker.
"""

import sqlite3
from datetime import date

DB_NAME = "data/expenses.db"


def get_connection():
    """Create and return a SQLite connection."""
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    return conn


def init_db():
    """Create the expenses table if it doesn't already exist."""
    conn = get_connection()
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
    conn.commit()
    conn.close()


def add_expense(expense_date: str, category: str, description: str, amount: float):
    """Insert a new expense record."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO expenses (date, category, description, amount) VALUES (?, ?, ?, ?)",
        (expense_date, category, description, amount)
    )
    conn.commit()
    conn.close()


def get_all_expenses():
    """Return all expenses as a list of tuples, most recent first."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, date, category, description, amount FROM expenses ORDER BY date DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows


def delete_expense(expense_id: int):
    """Delete an expense by its ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()


def get_total_by_category():
    """Return total spend grouped by category — used later for charts."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT category, SUM(amount) FROM expenses GROUP BY category")
    rows = cursor.fetchall()
    conn.close()
    return rows
