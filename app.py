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
    elif "today" in text_lower:
        expense_date = date.today()

    category = "Other"
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            category = cat
            break

    description = text.strip().capitalize()

    return amount, category, description, expense_date

# ---------------------------------------------------------------------------
# Voice-to-Expense: browser Web Speech API (free, no external API/key)
# ---------------------------------------------------------------------------
def voice_input_component():
    components.html(
        """
        <div style="text-align:center; padding:6px 0;">
          <button id="voiceBtn" style="
              background-color:#4338ca; color:white; border:none;
              border-radius:10px; padding:10px 18px; font-weight:600;
              font-size:0.95rem; cursor:pointer; width:100%;">
            🎤 Tap to Speak
          </button>
          <p id="voiceStatus" style="color:#6b7280; font-size:0.82rem; margin-top:6px;"></p>
          <button id="useBtn" style="
              display:none; background-color:#16a34a; color:white; border:none;
              border-radius:10px; padding:8px 16px; font-weight:600;
              font-size:0.9rem; cursor:pointer; width:100%; margin-top:6px;">
            ✅ Use this
          </button>
        </div>
        <script>
        const btn = document.getElementById('voiceBtn');
        const useBtn = document.getElementById('useBtn');
        const status = document.getElementById('voiceStatus');
        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        let lastTranscript = "";

        if (!SR) {
          status.innerText = "Speech recognition needs Chrome or Edge.";
          btn.disabled = true;
        } else {
          const recognition = new SR();
          recognition.continuous = false;
          recognition.interimResults = false;
          recognition.lang = 'en-IN';

          btn.onclick = () => {
            useBtn.style.display = "none";
            status.innerText = "Listening...";
            recognition.start();
          };

          recognition.onresult = (event) => {
            lastTranscript = event.results[0][0].transcript;
            status.innerText = 'Heard: "' + lastTranscript + '" — tap Use this to confirm.';
            useBtn.style.display = "block";
          };

          recognition.onerror = (event) => {
            status.innerText = "Error: " + event.error + ". Tap to try again.";
            useBtn.style.display = "none";
          };

          recognition.onend = () => {
            if (status.innerText === "Listening...") {
              status.innerText = "Didn't catch that. Tap to try again.";
            }
          };

          // This runs inside a fresh click event, so top-navigation is allowed.
          useBtn.onclick = () => {
            const url = new URL(window.parent.location.href);
            url.searchParams.set('voice_transcript', lastTranscript);
            window.parent.location.href = url.toString();
          };
        }
        </script>
        """,
        height=140,
    )

# ---------------------------------------------------------------------------
# Budget persistence (simple local JSON file)
# ---------------------------------------------------------------------------
BUDGET_FILE = "data/budget.json"

def load_budget() -> float:
    if os.path.exists(BUDGET_FILE):
        with open(BUDGET_FILE, "r") as f:
            return json.load(f).get("monthly_budget", 0.0)
    return 0.0

def save_budget(amount: float):
    os.makedirs("data", exist_ok=True)
    with open(BUDGET_FILE, "w") as f:
        json.dump({"monthly_budget": amount}, f)

# ---------------------------------------------------------------------------
# Init DB
# ---------------------------------------------------------------------------
db.init_db()

# ---------------------------------------------------------------------------
# Sidebar - Add Expense Form
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🗣️ Quick Add (Natural Language)")
    st.caption('Try: "spent 250 on lunch today"')

    nl_text = st.text_input("Describe your expense", placeholder="e.g. spent 200 on uber yesterday", key="nl_input")
    if st.button("✨ Parse & Add", width='stretch'):
        if nl_text.strip() == "":
            st.warning("Type something first.")
        else:
            amount, category, description, expense_date = parse_expense_text(nl_text)
            if amount is None:
                st.error("Couldn't find an amount. Try including a number, e.g. 'spent 200 on lunch'.")
            else:
                db.add_expense(str(expense_date), category, description, amount)
                st.success(f"Added {icon_for(category)} ₹{amount:.2f} — {category} ({expense_date})")
                st.rerun()

    st.divider()

    st.markdown("### 🎤 Voice Entry")
    st.caption('Tap and say something like: "spent 250 on lunch today"')

    voice_input_component()

    if "voice_transcript" in st.query_params:
        transcript = st.query_params["voice_transcript"]
        st.info(f'🎙️ Heard: "{transcript}"')

        v_amount, v_category, v_description, v_date = parse_expense_text(transcript)
        category_options = list(CATEGORY_ICONS.keys())
        default_index = category_options.index(v_category) if v_category in category_options else 0

        with st.form("voice_confirm_form", clear_on_submit=True):
            st.caption("Double-check the details below before adding.")
            vc_date = st.date_input("Date", value=v_date, key="voice_date")
            vc_category = st.selectbox("Category", category_options, index=default_index, key="voice_cat")
            vc_amount = st.number_input(
                "Amount (₹)", min_value=0.0, step=10.0, format="%.2f",
                value=v_amount if v_amount is not None else 0.0, key="voice_amt"
            )
            vc_description = st.text_input("Description", value=v_description, key="voice_desc")

            col_confirm, col_discard = st.columns(2)
            with col_confirm:
                voice_confirmed = st.form_submit_button("✅ Add", width='stretch')
            with col_discard:
                voice_discarded = st.form_submit_button("❌ Discard", width='stretch')

            if voice_confirmed:
                if vc_amount <= 0:
                    st.warning("Enter an amount greater than 0.")
                else:
                    db.add_expense(str(vc_date), vc_category, vc_description, vc_amount)
                    st.success(f"Added {icon_for(vc_category)} ₹{vc_amount:.2f} — {vc_category}")
                    st.query_params.clear()
                    st.rerun()

            if voice_discarded:
                st.query_params.clear()
                st.rerun()

    st.divider()

    st.markdown("### ➕ Add Expense (Manual)")
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

    st.markdown("### 🎯 Monthly Budget")
    current_budget = load_budget()
    new_budget = st.number_input(
        "Set your monthly budget (₹)",
        min_value=0.0,
        step=500.0,
        value=current_budget,
        format="%.2f"
    )
    if st.button("💾 Save Budget", width='stretch'):
        save_budget(new_budget)
        st.success(f"Budget set to ₹{new_budget:,.2f}")
        st.rerun()

    st.divider()
    st.caption("💡 Tip: add a few expenses across different categories to see the dashboard come alive.")

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
st.markdown('<div class="main-title">💰 Personal Expense Tracker</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Track where your money goes, one entry at a time.</div>', unsafe_allow_html=True)

rows = db.get_all_expenses()
monthly_budget = load_budget()
has_expenses = bool(rows)

if has_expenses:
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

    if monthly_budget > 0:
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<div class="section-header">🎯 Budget Tracker</div>', unsafe_allow_html=True)

        percent_used = min(this_month / monthly_budget, 1.0)
        st.progress(percent_used, text=f"₹{this_month:,.0f} of ₹{monthly_budget:,.0f} used ({percent_used*100:.0f}%)")

        if this_month >= monthly_budget:
            st.error(f"🚨 You've exceeded your monthly budget of ₹{monthly_budget:,.0f}!")
        elif this_month >= 0.8 * monthly_budget:
            st.warning(f"⚠️ You've used {percent_used*100:.0f}% of your monthly budget. Slow down!")
        else:
            st.success(f"✅ You're within budget — {percent_used*100:.0f}% used.")

    st.markdown("<hr>", unsafe_allow_html=True)
else:
    st.markdown("<br>", unsafe_allow_html=True)
    st.info("👋 No expenses yet — add your first one using the form in the sidebar! (Your Savings Goals below don't need any expenses to get started.)")
    st.markdown("<hr>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["📋 All Expenses", "📊 Charts", "🗓️ Monthly Overview", "🎯 Savings Goals", "🗑️ Manage", "📤 Export"]
)

with tab1:
    if not has_expenses:
        st.info("No expenses yet.")
    else:
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
    if not has_expenses:
        st.info("No expenses yet.")
    else:
        st.markdown('<div class="section-header">Spending Breakdown</div>', unsafe_allow_html=True)

        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            category_totals = df.groupby("Category")["Amount"].sum().reset_index()
            fig_pie = px.pie(
                category_totals,
                names="Category",
                values="Amount",
                title="By Category",
                hole=0.4
            )
            st.plotly_chart(fig_pie, width='stretch')

        with chart_col2:
            daily_totals = df.groupby(df["Date"].dt.date)["Amount"].sum().reset_index()
            daily_totals.columns = ["Date", "Amount"]
            fig_line = px.line(
                daily_totals,
                x="Date",
                y="Amount",
                title="Spending Over Time",
                markers=True
            )
            st.plotly_chart(fig_line, width='stretch')

with tab3:
    st.markdown('<div class="section-header">Monthly Overview</div>', unsafe_allow_html=True)
    st.caption("A calendar view of daily spending, with unusually high days flagged.")

    if not has_expenses:
        st.info("No expenses yet.")
    else:
        month_periods = sorted(df["Date"].dt.to_period("M").unique(), reverse=True)
        month_options = {p.strftime("%B %Y"): p for p in month_periods}
        selected_label = st.selectbox("Select month", list(month_options.keys()), key="overview_month")
        selected_period = month_options[selected_label]

        year, month = selected_period.year, selected_period.month

        # Daily totals for the selected month
        month_df = df[df["Date"].dt.to_period("M") == selected_period]
        daily_series = month_df.groupby(month_df["Date"].dt.date)["Amount"].sum()

        # Anomaly detection using all-time daily spending (so it's meaningful even
        # for months with only a few entries)
        all_daily = db.get_daily_totals()  # list of (date_str, total)
        all_amounts = [amt for _, amt in all_daily]

        if len(all_amounts) >= 3:
            mean_amt = statistics.mean(all_amounts)
            std_amt = statistics.pstdev(all_amounts)
            threshold = mean_amt + 1.5 * std_amt if std_amt > 0 else mean_amt * 2
        elif all_amounts:
            mean_amt = statistics.mean(all_amounts)
            threshold = mean_amt * 2
        else:
            mean_amt = 0
            threshold = 0

        anomalies = {
            d: amt for d, amt in daily_series.items()
            if threshold > 0 and amt > threshold
        }

        # Build the calendar grid (weeks x 7 days), Monday-first
        cal = calendar.Calendar(firstweekday=0)
        weeks = cal.monthdayscalendar(year, month)

        z, text, customdata = [], [], []
        for week in weeks:
            z_row, text_row, custom_row = [], [], []
            for day in week:
                if day == 0:
                    z_row.append(None)
                    text_row.append("")
                    custom_row.append(False)
                else:
                    d = date(year, month, day)
                    amt = float(daily_series.get(d, 0.0))
                    is_anomaly = d in anomalies
                    z_row.append(amt if amt > 0 else 0)
                    marker = " ⚠️" if is_anomaly else ""
                    text_row.append(f"{day}<br>₹{amt:,.0f}{marker}" if amt > 0 else f"{day}")
                    custom_row.append(is_anomaly)
            z.append(z_row)
            text.append(text_row)
            customdata.append(custom_row)

        fig_cal = go.Figure(data=go.Heatmap(
            z=z,
            text=text,
            texttemplate="%{text}",
            textfont={"size": 12},
            colorscale="YlOrRd",
            xgap=4,
            ygap=4,
            hoverinfo="skip",
            showscale=True,
            colorbar=dict(title="₹"),
        ))
        fig_cal.update_xaxes(
            tickmode="array",
            tickvals=list(range(7)),
            ticktext=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            side="top",
        )
        fig_cal.update_yaxes(autorange="reversed", showticklabels=False)
        fig_cal.update_layout(
            height=110 * len(weeks) + 60,
            margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(fig_cal, width='stretch')

        if anomalies:
            st.markdown("**⚠️ Unusually high spending days this month:**")
            for d, amt in sorted(anomalies.items()):
                st.write(f"- {d.strftime('%d %b')}: ₹{amt:,.0f} (your typical day is around ₹{mean_amt:,.0f})")
        else:
            st.caption("No unusual spending days detected this month.")

with tab4:
    st.markdown('<div class="section-header">🎯 Savings Goals</div>', unsafe_allow_html=True)
    st.caption("Set savings targets and log contributions toward them.")

    with st.expander("➕ Add a new goal"):
        with st.form("add_goal_form", clear_on_submit=True):
            goal_name = st.text_input("Goal name", placeholder="e.g. New Laptop")
            goal_target = st.number_input("Target amount (₹)", min_value=0.0, step=500.0, format="%.2f")
            goal_date = st.date_input("Target date", value=date.today() + timedelta(days=90))
            goal_submitted = st.form_submit_button("Create Goal", width='stretch')

            if goal_submitted:
                if not goal_name.strip():
                    st.warning("Give your goal a name.")
                elif goal_target <= 0:
                    st.warning("Target amount must be greater than 0.")
                else:
                    db.add_goal(goal_name.strip(), goal_target, str(goal_date))
                    st.success(f"Goal '{goal_name}' created!")
                    st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)

    goals = db.get_all_goals()

    if not goals:
        st.info("No savings goals yet — create one above to get started.")
    else:
        for goal_id, name, target_amount, target_date, created_date in goals:
            saved = db.get_goal_saved_total(goal_id)
            progress = min(saved / target_amount, 1.0) if target_amount > 0 else 0.0

            st.markdown(f"#### {name}")
            st.progress(progress, text=f"₹{saved:,.0f} of ₹{target_amount:,.0f} saved ({progress*100:.0f}%)")

            info_col, action_col = st.columns([3, 1])
            with info_col:
                if target_date:
                    try:
                        t_date = pd.to_datetime(target_date).date()
                        days_left = (t_date - date.today()).days
                        if progress >= 1.0:
                            pass
                        elif days_left >= 0:
                            st.caption(f"Target date: {t_date.strftime('%d %b %Y')} ({days_left} days left)")
                        else:
                            st.caption(f"Target date: {t_date.strftime('%d %b %Y')} (passed {abs(days_left)} days ago)")
                    except Exception:
                        pass
                if progress >= 1.0:
                    st.success("🎉 Goal reached!")
            with action_col:
                if st.button("🗑️ Delete goal", key=f"del_goal_{goal_id}", width='stretch'):
                    db.delete_goal(goal_id)
                    st.success(f"Deleted '{name}'")
                    st.rerun()

            with st.expander(f"💰 Add contribution / view history"):
                with st.form(f"contrib_form_{goal_id}", clear_on_submit=True):
                    c_amount = st.number_input(
                        "Amount (₹)", min_value=0.0, step=100.0, format="%.2f", key=f"c_amt_{goal_id}"
                    )
                    c_date = st.date_input("Date", value=date.today(), key=f"c_date_{goal_id}")
                    c_note = st.text_input("Note (optional)", key=f"c_note_{goal_id}")
                    c_submit = st.form_submit_button("Add Contribution")

                    if c_submit:
                        if c_amount <= 0:
                            st.warning("Enter an amount greater than 0.")
                        else:
                            db.add_contribution(goal_id, c_amount, str(c_date), c_note)
                            st.success(f"Added ₹{c_amount:,.0f} to '{name}'")
                            st.rerun()

                contributions = db.get_contributions(goal_id)
                if contributions:
                    st.markdown("**History:**")
                    for contrib_id, c_amt, c_dt, c_note in contributions:
                        hist_col1, hist_col2 = st.columns([5, 1])
                        with hist_col1:
                            note_str = f" — {c_note}" if c_note else ""
                            st.write(f"₹{c_amt:,.0f} on {c_dt}{note_str}")
                        with hist_col2:
                            if st.button("🗑️", key=f"del_contrib_{contrib_id}"):
                                db.delete_contribution(contrib_id)
                                st.rerun()
                else:
                    st.caption("No contributions logged yet.")

            st.markdown("<hr>", unsafe_allow_html=True)

with tab5:
    st.markdown('<div class="section-header">Delete a Transaction</div>', unsafe_allow_html=True)
    st.caption("Select an ID from the table above and remove it here.")

    delete_id = st.number_input("Expense ID", min_value=0, step=1)
    if st.button("🗑️ Delete Expense"):
        db.delete_expense(delete_id)
        st.success(f"Deleted expense #{delete_id}")
        st.rerun()

with tab6:
    st.markdown('<div class="section-header">Export Your Data</div>', unsafe_allow_html=True)
    st.caption("Download your expense history as a CSV or a formatted PDF report.")

    if not has_expenses:
        st.info("No expenses yet.")
    else:
        export_col1, export_col2 = st.columns(2)

        with export_col1:
            csv_data = df.drop(columns=["ID"]).to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Download CSV",
                data=csv_data,
                file_name=f"expenses_{date.today()}.csv",
                mime="text/csv"
            )

        with export_col2:
            pdf_bytes = generate_pdf_report(df, total_spent, this_month, monthly_budget)
            st.download_button(
                label="⬇️ Download PDF Report",
                data=pdf_bytes,
                file_name=f"expense_report_{date.today()}.pdf",
                mime="application/pdf"
            )