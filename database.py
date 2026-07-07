"""
database.py
Handles all SQLite database operations for the Expense Tracker.
"""
import sqlite3
import os
from datetime import date

DB_NAME = "data/expenses.db"

def get_connection():
    """Create and return a SQLite connection."""
    os.makedirs(os.path.dirname(DB_NAME), exist_ok=True)
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    return conn

def init_db():
    """Create all required tables if they don't already exist."""
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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS savings_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            target_amount REAL NOT NULL,
            target_date TEXT,
            created_date TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS goal_contributions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            contribution_date TEXT NOT NULL,
            note TEXT,
            FOREIGN KEY (goal_id) REFERENCES savings_goals (id)
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

def get_daily_totals():
    """Return list of (date, total_amount) for every day that has at least one expense."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT date, SUM(amount) FROM expenses GROUP BY date ORDER BY date")
    rows = cursor.fetchall()
    conn.close()
    return rows

# ---------------------------------------------------------------------------
# Savings Goals
# ---------------------------------------------------------------------------

def add_goal(name: str, target_amount: float, target_date: str):
    """Create a new savings goal."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO savings_goals (name, target_amount, target_date, created_date) VALUES (?, ?, ?, ?)",
        (name, target_amount, target_date, str(date.today()))
    )
    conn.commit()
    conn.close()

def get_all_goals():
    """Return all savings goals as a list of tuples: (id, name, target_amount, target_date, created_date)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, target_amount, target_date, created_date FROM savings_goals ORDER BY created_date DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_goal(goal_id: int):
    """Delete a goal and all of its contributions."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM goal_contributions WHERE goal_id = ?", (goal_id,))
    cursor.execute("DELETE FROM savings_goals WHERE id = ?", (goal_id,))
    conn.commit()
    conn.close()

def add_contribution(goal_id: int, amount: float, contribution_date: str, note: str = ""):
    """Log a contribution towards a savings goal."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO goal_contributions (goal_id, amount, contribution_date, note) VALUES (?, ?, ?, ?)",
        (goal_id, amount, contribution_date, note)
    )
    conn.commit()
    conn.close()

def get_contributions(goal_id: int):
    """Return all contributions for a given goal, most recent first."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, amount, contribution_date, note FROM goal_contributions WHERE goal_id = ? ORDER BY contribution_date DESC",
        (goal_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_contribution(contribution_id: int):
    """Delete a single contribution entry."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM goal_contributions WHERE id = ?", (contribution_id,))
    conn.commit()
    conn.close()

def get_goal_saved_total(goal_id: int) -> float:
    """Return the total amount saved so far for a given goal."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(amount) FROM goal_contributions WHERE goal_id = ?", (goal_id,))
    result = cursor.fetchone()[0]
    conn.close()
    return result if result else 0.0