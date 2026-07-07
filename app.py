"""
app.py
Personal Expense Tracker - Streamlit app (Step 4: NLP Entry + Budget Alerts + Charts)
"""

import re
import json
import os
import calendar
import statistics
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta
import database as db
from fpdf import FPDF
from io import BytesIO

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
# Custom CSS
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
# Category -> icon mapping
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
# Rule-based Natural Language Expense Parser (no AI API needed)
# ---------------------------------------------------------------------------
CATEGORY_KEYWORDS = {
    "Food": ["lunch", "dinner", "breakfast", "food", "restaurant", "coffee", "snack", "pizza", "groceries", "grocery"],
    "Transport": ["uber", "ola", "taxi", "bus", "train", "petrol", "fuel", "auto", "cab", "metro"],
    "Rent": ["rent", "landlord"],
    "Shopping": ["shopping", "clothes", "shoes", "amazon", "flipkart", "mall"],
    "Entertainment": ["movie", "netflix", "concert", "game", "spotify", "cinema"],
    "Bills": ["electricity", "bill", "recharge", "wifi", "internet", "water bill"],
    "Education": ["book", "course", "tuition", "fees", "exam"],
}

def generate_pdf_report(df, total_spent, this_month, monthly_budget):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Personal Expense Report", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 8, f"Generated on: {date.today().strftime('%d %b %Y')}", ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Summary", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"Total Spent: Rs. {total_spent:,.2f}", ln=True)
    pdf.cell(0, 7, f"This Month: Rs. {this_month:,.2f}", ln=True)
    if monthly_budget > 0:
        pdf.cell(0, 7, f"Monthly Budget: Rs. {monthly_budget:,.2f}", ln=True)
    pdf.ln(5)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Transactions", ln=True)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(30, 7, "Date", border=1)
    pdf.cell(35, 7, "Category", border=1)
    pdf.cell(75, 7, "Description", border=1)
    pdf.cell(30, 7, "Amount", border=1, ln=True)

    pdf.set_font("Helvetica", "", 9)
    for _, row in df.iterrows():
        pdf.cell(30, 7, row["Date"].strftime("%d %b %Y"), border=1)
        pdf.cell(35, 7, str(row["Category"]), border=1)
        pdf.cell(75, 7, str(row["Description"])[:40], border=1)
        pdf.cell(30, 7, f"Rs. {row['Amount']:,.2f}", border=1, ln=True)

    return bytes(pdf.output())

def parse_expense_text(text: str):
    """
    Parses a natural language expense string like:
    'spent 250 on lunch yesterday'
    Returns (amount, category, description, expense_date).
    """
    text_lower = text.lower()

    amount_match = re.search(r'(\d+(\.\d+)?)', text)
    amount = float(amount_match.group(1)) if amount_match else None

    expense_date = date.today()
    if "yesterday" in text_lower:
        expense_date = date.today() - timedelta(days=1)
    elif "today" in