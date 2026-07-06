"""
app.py
Personal Expense Tracker - Streamlit app (Step 2: basic add + view functionality)
"""

import streamlit as st
import pandas as pd
from datetime import date
import database as db

# ---- Page setup ----
st.set_page_config(page_title="Personal Expense Tracker", page_icon="💰", layout="centered")
st.title("💰 Personal Expense Tracker")

# ---- Initialize database (creates table if not exists) ----
db.init_db()

# ---- Add Expense Form ----
st.subheader("Add a new expense")

with st.form("add_expense_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        expense_date = st.date_input("Date", value=date.today())
        category = st.selectbox(
            "Category",
            ["Food", "Transport", "Rent", "Shopping", "Entertainment", "Bills", "Education", "Other"]
        )
    with col2:
        amount = st.number_input("Amount (₹)", min_value=0.0, step=10.0, format="%.2f")
        description = st.text_input("Description (optional)")

    submitted = st.form_submit_button("Add Expense")

    if submitted:
        if amount <= 0:
            st.warning("Please enter an amount greater than 0.")
        else:
            db.add_expense(str(expense_date), category, description, amount)
            st.success(f"Added ₹{amount:.2f} under '{category}'")

st.divider()

# ---- View Expenses ----
st.subheader("All Expenses")

rows = db.get_all_expenses()

if rows:
    df = pd.DataFrame(rows, columns=["ID", "Date", "Category", "Description", "Amount (₹)"])
    st.dataframe(df, use_container_width=True, hide_index=True)

    total = df["Amount (₹)"].sum()
    st.metric("Total Spent", f"₹{total:,.2f}")

    # Simple delete option
    with st.expander("Delete an expense"):
        delete_id = st.number_input("Enter ID to delete", min_value=0, step=1)
        if st.button("Delete"):
            db.delete_expense(delete_id)
            st.success(f"Deleted expense with ID {delete_id}")
            st.rerun()
else:
    st.info("No expenses added yet. Use the form above to add your first one!")
