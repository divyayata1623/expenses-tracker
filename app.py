"""
app.py
Personal Expense Tracker - Streamlit app (Step 2.5: Improved UI/UX)
"""

import streamlit as st
import pandas as pd
from datetime import date
import database as db

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Expense Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------------------------
# Custom CSS — gives the app a cleaner, more "designed" look
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    html, body, [class*="css"] {
        font-family: 'Segoe UI', 'Inter', sans-serif;
    }
    .main-title {
        font-size: 2.3rem;
        font-weight: 800;
        margin-bottom: 0rem;
        color: #1a1a1a;
    }
    .subtitle {
        color: #6b7280;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #eee;
        border-radius: 14px;
        padding: 18px 20px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.04);
    }
    div[data-testid="stMetricLabel"] {
        font-weight: 600;
        color: #6b7280;
    }
    div[data-testid="stMetricValue"] {
        font-weight: 800;
        color: #111827;
    }
    section[data-testid="stSidebar"] {
        background-color: #fafafa;
        border-right: 1px solid #eee;
    }
    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
        padding: 0.5rem 1rem;
    }
    .category-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 600;
        background-color: #eef2ff;
        color: #4338ca;
    }
    .section-header {
        font-size: 1.3rem;
        font-weight: 700;
        margin-top: 0.5rem;
        margin-bottom: 0.8rem;
        color: #111827;
    }
    hr {
        margin: 1.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Category → icon mapping
# ---------------------------------------------------------------------------
CATEGORY_ICONS = {
    "Food": "🍔",
    "Transport": "🚌",
    "Rent": "🏠",
    "Shopping": "🛍️",
    "Entertainment": "🎬",
    "Bills": "🧾",
    "Education": "📚",
    "Other": "📌",
}

def icon_for(category: str) -> str:
    return CATEGORY_ICONS.get(category, "📌")

# ---------------------------------------------------------------------------
# Init DB
# ---------------------------------------------------------------------------
db.init_db()

# ---------------------------------------------------------------------------
# Sidebar — Add Expense Form
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ➕ Add Expense")
    st.caption("Log a new transaction")

    with st.form("add_expense_form", clear_on_submit=True):
        expense_date = st.date_input("Date", value=date.today())
        category = st.selectbox("Category", list(CATEGORY_ICONS.keys()))
        amount = st.number_input("Amount (₹)", min_value=0.0, step=10.0, format="%.2f")
        description = st.text_input("Description", placeholder="e.g. Lunch with friends")

        submitted = st.form_submit_button("Add Expense", width='stretch')

        if submitted:
            if amount <= 0:
                st.warning("Enter an amount greater than 0.")
            else:
                db.add_expense(str(expense_date), category, description, amount)
                st.success(f"Added {icon_for(category)} ₹{amount:.2f} — {category}")
                st.rerun()

    st.divider()
    st.caption("💡 Tip: add a few expenses across different categories to see the dashboard come alive.")

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
st.markdown('<div class="main-title">💰 Personal Expense Tracker</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Track where your money goes, one entry at a time.</div>', unsafe_allow_html=True)

rows = db.get_all_expenses()

if rows:
    df = pd.DataFrame(rows, columns=["ID", "Date", "Category", "Description", "Amount"])
    df["Date"] = pd.to_datetime(df["Date"])

    total_spent = df["Amount"].sum()
    num_transactions = len(df)
    top_category = df.groupby("Category")["Amount"].sum().idxmax()
    this_month = df[df["Date"].dt.month == date.today().month]["Amount"].sum()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💵 Total Spent", f"₹{total_spent:,.0f}")
    col2.metric("📅 This Month", f"₹{this_month:,.0f}")
    col3.metric("🧾 Transactions", f"{num_transactions}")
    col4.metric("🏆 Top Category", f"{icon_for(top_category)} {top_category}")

    st.markdown("<hr>", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📋 All Expenses", "🗑️ Manage"])

    with tab1:
        st.markdown('<div class="section-header">Recent Transactions</div>', unsafe_allow_html=True)

        display_df = df.copy()
        display_df["Date"] = display_df["Date"].dt.strftime("%d %b %Y")
        display_df["Category"] = display_df["Category"].apply(lambda c: f"{icon_for(c)} {c}")
        display_df["Amount"] = display_df["Amount"].apply(lambda a: f"₹{a:,.2f}")

        st.dataframe(
            display_df,
            width='stretch',
            hide_index=True,
            column_config={
                "ID": st.column_config.NumberColumn("ID", width="small"),
                "Amount": st.column_config.TextColumn("Amount", width="small"),
            }
        )

    with tab2:
        st.markdown('<div class="section-header">Delete a Transaction</div>', unsafe_allow_html=True)
        st.caption("Select an ID from the table above and remove it here.")

        delete_id = st.number_input("Expense ID", min_value=0, step=1)
        if st.button("🗑️ Delete Expense"):
            db.delete_expense(delete_id)
            st.success(f"Deleted expense #{delete_id}")
            st.rerun()

else:
    st.markdown("<br>", unsafe_allow_html=True)
    st.info("👋 No expenses yet — add your first one using the form in the sidebar!")
