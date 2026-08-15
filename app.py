"""
app.py
-------
Web dashboard for Invoice Chaser. Lets people explore the sample dataset
OR upload their own invoice data and get the same overdue detection,
cash-flow projection, and reminder drafting — no AWS needed for this part.

Run locally with: streamlit run app.py
Deploy free on Streamlit Community Cloud by pointing it at this file.
"""

import sys
import os
from datetime import date, datetime

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from data_loader import load_invoices, get_open_invoices, reminder_tier, cash_flow_projection, DEFAULT_DATA_PATH
from reminder_writer import draft_reminder
from client_risk import compute_client_risk, client_risk_summary
from payment_plan import draft_payment_plan_offer
from forecast import project_cash_flow, projected_cash_by
from weekly_brief import build_action_plan


st.set_page_config(page_title="Invoice Chaser", page_icon="🧾", layout="wide")

st.markdown(
    """
    <style>
    .big-title { font-size: 2.4rem; font-weight: 700; margin-bottom: 0; }
    .subtitle { color: #6b7280; font-size: 1.05rem; margin-top: 0.2rem; }
    div[data-testid="stMetric"] {
        background-color: #f8f9fb;
        border: 1px solid #eaecef;
        border-radius: 10px;
        padding: 12px 16px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<p class="big-title">🧾 Invoice Chaser</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="subtitle">An agent that chases down unpaid invoices — for freelancers and small businesses. '
    'Built for the AWS Agents for Humans Hackathon with the Strands Agents SDK.</p>',
    unsafe_allow_html=True,
)
st.markdown("---")


# ---------- Data source selection ----------
st.sidebar.header("📂 Data source")
source = st.sidebar.radio(
    "Choose what to analyze",
    ["Sample dataset (IBM public data)", "Upload your own invoices"],
)

df = None
mode = None  # "sample" or "upload"

if source.startswith("Sample"):
    mode = "sample"
    st.sidebar.markdown("---")
    snapshot = st.sidebar.date_input(
        "Snapshot date (simulated 'today')",
        value=date(2013, 3, 1),
        help="This dataset is historical, so this date lets you explore what was outstanding at different points in time.",
    )
    try:
        df = load_invoices(str(DEFAULT_DATA_PATH))
    except FileNotFoundError:
        st.error(f"Couldn't find the sample data file at `{DEFAULT_DATA_PATH}`.")
        st.stop()

else:
    mode = "upload"
    st.sidebar.markdown("---")
    uploaded_file = st.sidebar.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx", "xls"])
    st.sidebar.caption("Your file needs at least: a client/customer name, an invoice amount, and a due date. A 'paid' status column is optional.")

    if uploaded_file is None:
        st.info("👈 Upload a CSV or Excel file in the sidebar to analyze your own invoices, or switch to the sample dataset.")
        st.stop()

    try:
        if uploaded_file.name.lower().endswith(".csv"):
            raw_df = pd.read_csv(uploaded_file)
        else:
            raw_df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Couldn't read that file: {e}")
        st.stop()


# ---------- Sample dataset flow ----------
if mode == "sample":
    open_df = get_open_invoices(df, str(snapshot))
    summary = cash_flow_projection(open_df)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Open invoices", summary["num_open_invoices"])
    col2.metric("Overdue invoices", summary["num_overdue_invoices"])
    col3.metric("Total outstanding", f"₹{summary['total_outstanding']:.2f}")
    col4.metric("Overdue amount", f"₹{summary['overdue_amount']:.2f}")

    st.markdown("---")
    overdue = open_df[open_df["IsOverdue"]].sort_values("DaysOverdue", ascending=False).copy()

    if overdue.empty:
        st.success("No overdue invoices as of this date — nothing to chase!")
        st.stop()

    overdue["Tier"] = overdue["DaysOverdue"].apply(lambda d: reminder_tier(int(d)))
    id_col, amount_col, due_col, days_col, customer_col = (
        "invoiceNumber", "InvoiceAmount", "DueDate", "DaysOverdue", "customerID"
    )
    working = overdue
    as_of_ts = pd.Timestamp(str(snapshot))
    risk_df = compute_client_risk(df, str(snapshot))
    has_risk_data = True

# ---------- Upload flow: column mapping ----------
else:
    st.subheader("1. Map your columns")
    st.caption("Tell us which column in your file is which — we won't rename or store your data anywhere.")

    with st.expander("Preview of your uploaded data", expanded=False):
        st.dataframe(raw_df.head(10), use_container_width=True)

    cols = list(raw_df.columns)
    c1, c2 = st.columns(2)
    with c1:
        customer_map = st.selectbox("Client / customer name column", cols)
        amount_map = st.selectbox("Invoice amount column", cols)
        invoice_id_map = st.selectbox("Invoice number / ID column", cols)
    with c2:
        due_date_map = st.selectbox("Due date column", cols)
        paid_map = st.selectbox("Paid / settled status column (optional)", ["(none — assume all unpaid)"] + cols)

    work = pd.DataFrame({
        "customerID": raw_df[customer_map],
        "invoiceNumber": raw_df[invoice_id_map].astype(str),
        "InvoiceAmount": pd.to_numeric(raw_df[amount_map], errors="coerce"),
        "DueDate": pd.to_datetime(raw_df[due_date_map], errors="coerce"),
    })

    if paid_map != "(none — assume all unpaid)":
        paid_series = raw_df[paid_map].astype(str).str.strip().str.lower()
        is_paid = paid_series.isin(["yes", "true", "1", "paid", "y"])
        work = work[~is_paid]

    work = work.dropna(subset=["DueDate", "InvoiceAmount"])

    today = pd.Timestamp(date.today())
    work["DaysOverdue"] = (today - work["DueDate"]).dt.days
    work["IsOverdue"] = work["DaysOverdue"] > 0

    st.markdown("---")
    st.subheader("2. Results")

    total_outstanding = round(work["InvoiceAmount"].sum(), 2)
    overdue_amount = round(work.loc[work["IsOverdue"], "InvoiceAmount"].sum(), 2)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Open invoices", len(work))
    col2.metric("Overdue invoices", int(work["IsOverdue"].sum()))
    col3.metric("Total outstanding", f"₹{total_outstanding:.2f}")
    col4.metric("Overdue amount", f"₹{overdue_amount:.2f}")

    st.markdown("---")
    overdue = work[work["IsOverdue"]].sort_values("DaysOverdue", ascending=False).copy()

    if overdue.empty:
        st.success("No overdue invoices found in your data — nothing to chase!")
        st.stop()

    overdue["Tier"] = overdue["DaysOverdue"].apply(lambda d: reminder_tier(int(d)))
    id_col, amount_col, due_col, days_col, customer_col = (
        "invoiceNumber", "InvoiceAmount", "DueDate", "DaysOverdue", "customerID"
    )
    working = overdue
    as_of_ts = today
    risk_df = None
    has_risk_data = False


# ---------- Shared: filters ----------
st.subheader("🔍 Filter")
f1, f2, f3 = st.columns([2, 2, 2])
with f1:
    search = st.text_input("Search by client name", "")
with f2:
    tier_filter = st.multiselect(
        "Urgency", options=["gentle", "polite_followup", "firm", "urgent"],
        default=["gentle", "polite_followup", "firm", "urgent"],
    )
with f3:
    max_amt = float(working["InvoiceAmount"].max())
    amount_range = st.slider("Amount range (₹)", 0.0, max_amt, (0.0, max_amt))

if search:
    working = working[working[customer_col].astype(str).str.contains(search, case=False, na=False)]
working = working[working["Tier"].isin(tier_filter)]
working = working[
    (working[amount_col] >= amount_range[0]) & (working[amount_col] <= amount_range[1])
]

if working.empty:
    st.warning("No invoices match these filters.")
    st.stop()

st.markdown("---")

# ---------- Table + chart ----------
tier_order = ["gentle", "polite_followup", "firm", "urgent"]
tier_totals = working.groupby("Tier")["InvoiceAmount"].sum()
tier_totals = tier_totals.reindex([t for t in tier_order if t in tier_totals.index])

left, right = st.columns([2, 1])

with left:
    st.subheader(f"{len(working)} overdue invoices")
    show_df = working.rename(columns={
        customer_col: "Client", id_col: "Invoice #", amount_col: "Amount",
        due_col: "Due Date", days_col: "Days Overdue",
    })[["Client", "Invoice #", "Amount", "Due Date", "Days Overdue", "Tier"]]
    st.dataframe(show_df, use_container_width=True, hide_index=True)

with right:
    st.subheader("By urgency")
    st.bar_chart(tier_totals)

st.markdown("---")

# ---------- This week's action plan ----------
st.subheader("📅 This week's action plan")
st.caption("Not every overdue invoice deserves the same urgency — this ranks them by money at stake, how overdue they are, and (when known) the client's payment history.")

action_plan = build_action_plan(working, risk_df)
plan_display = action_plan.rename(columns={
    customer_col: "Client", id_col: "Invoice #", amount_col: "Amount", days_col: "Days Overdue",
})[["Client", "Invoice #", "Amount", "Days Overdue", "Tier", "PriorityScore", "RecommendedAction"]]
st.dataframe(plan_display, use_container_width=True, hide_index=True)

st.markdown("---")

# ---------- Cash flow forecast ----------
st.subheader("📈 Cash flow forecast")
st.caption("Best case: everyone pays on their due date. Worst case: each client pays based on their own track record (or a default buffer if unknown).")

cumulative = project_cash_flow(working, as_of_ts, risk_df)

if cumulative.empty:
    st.info("Not enough data to build a forecast yet.")
else:
    horizon = st.slider("Forecast horizon (days)", 7, 120, 60)
    window_end = as_of_ts + pd.Timedelta(days=horizon)
    chart_data = cumulative[cumulative.index <= window_end]
    st.line_chart(chart_data)

    fc1, fc2 = st.columns(2)
    with fc1:
        target_date = st.date_input("Check cash available by", value=(as_of_ts + pd.Timedelta(days=30)).date())
    with fc2:
        target_amount = st.number_input("Amount you need (₹)", min_value=0.0, value=0.0, step=100.0)

    projected = projected_cash_by(cumulative, pd.Timestamp(target_date))
    pc1, pc2 = st.columns(2)
    pc1.metric("Best case by then", f"₹{projected['Best case']:.2f}")
    pc2.metric("Worst case by then", f"₹{projected['Worst case']:.2f}")

    if target_amount > 0:
        if projected["Worst case"] >= target_amount:
            st.success("Even in the worst case, you're projected to have this covered.")
        elif projected["Best case"] >= target_amount:
            st.warning("You'll likely be covered if clients pay roughly on time — but it's not guaranteed.")
        else:
            st.error("Based on current invoices, you may fall short of this amount by then.")

st.markdown("---")
st.subheader("Draft a reminder")

invoice_options = working[id_col].astype(str).tolist()
selected = st.selectbox("Pick an overdue invoice", invoice_options)

row = working[working[id_col].astype(str) == selected].iloc[0]
tier = reminder_tier(int(row[days_col]))
message = draft_reminder(
    customer=row[customer_col],
    invoice_number=str(row[id_col]),
    amount=row[amount_col],
    due_date=row[due_col].strftime("%d %b %Y") if isinstance(row[due_col], (pd.Timestamp, datetime)) else str(row[due_col]),
    days_overdue=int(row[days_col]),
    tier=tier,
)

st.text_area("Reminder draft — copy and send as-is, or edit first", message, height=220)

# ---------- Client risk (only when we have settlement history) ----------
if has_risk_data:
    st.markdown("---")
    st.subheader("📊 Client payment risk")
    st.caption("Based on this client's past settled invoices — how reliably do they pay?")

    client_match = risk_df[risk_df["customerID"] == row[customer_col]]

    if client_match.empty:
        st.info(f"No payment history found yet for **{row[customer_col]}** — not enough data to score them.")
    else:
        r = client_match.iloc[0]
        badge = {"Low": "🟢", "Medium": "🟡", "High": "🔴"}[r["risk_level"]]
        st.markdown(f"**{badge} {r['risk_level']} risk** — {client_risk_summary(r)}")

    with st.expander("See risk profile for all clients"):
        st.dataframe(
            risk_df.rename(columns={
                "customerID": "Client", "num_invoices": "Past Invoices",
                "avg_days_late": "Avg Days Late", "pct_disputed": "% Disputed", "risk_level": "Risk",
            }),
            use_container_width=True, hide_index=True,
        )

# ---------- Payment plan suggestion for severely overdue invoices ----------
if tier in ("firm", "urgent"):
    st.markdown("---")
    st.subheader("💳 Consider a payment plan instead")
    st.caption("This invoice is significantly overdue — a blunt demand may not land well. Here's a softer alternative.")

    num_installments = st.slider("Number of installments", min_value=2, max_value=4, value=3)
    plan_message = draft_payment_plan_offer(
        customer=row[customer_col],
        invoice_number=str(row[id_col]),
        amount=row[amount_col],
        days_overdue=int(row[days_col]),
        num_installments=num_installments,
    )
    st.text_area("Payment plan offer", plan_message, height=260)