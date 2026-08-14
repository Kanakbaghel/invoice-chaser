"""
app.py
-------
Web dashboard for Invoice Chaser. Wraps the same rule-based logic used by
run_dry.py in a shareable, password-protected website — no AWS needed for
this part. Once Bedrock access is available, a "Chat with agent" tab can
call the Strands agent from src/agent.py for free-form questions.

Run locally with: streamlit run app.py
Deploy on Streamlit Community Cloud (free) by pointing it at this file.
"""

import sys
import os
from datetime import date

import streamlit as st

# Make src/ importable regardless of where this app is run from.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from data_loader import load_invoices, get_open_invoices, reminder_tier, cash_flow_projection, DEFAULT_DATA_PATH
from reminder_writer import draft_reminder


st.set_page_config(page_title="Invoice Chaser", page_icon="🧾", layout="wide")


# ---------- Simple password gate ----------
def check_password() -> bool:
    """Returns True once the correct password has been entered."""

    def password_entered():
        correct = st.secrets.get("APP_PASSWORD", "letmein")
        if st.session_state.get("password_input") == correct:
            st.session_state["password_correct"] = True
            del st.session_state["password_input"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct"):
        return True

    st.text_input(
        "Password", type="password", on_change=password_entered, key="password_input"
    )
    if "password_correct" in st.session_state:
        st.error("Incorrect password.")
    return False


if not check_password():
    st.title("🧾 Invoice Chaser")
    st.caption("This dashboard is password-protected.")
    st.stop()


# ---------- Main app ----------
st.title("🧾 Invoice Chaser")
st.caption("An agent that chases down unpaid invoices — built for the AWS Agents for Humans Hackathon.")

with st.sidebar:
    st.header("Settings")
    snapshot = st.date_input(
        "Snapshot date (simulated 'today')",
        value=date(2013, 3, 1),
        help="The dataset is historical, so this date lets you explore what was outstanding at different points in time.",
    )
    st.markdown("---")
    st.caption("Data source: IBM public Accounts Receivable dataset (Kaggle).")

try:
    df = load_invoices(str(DEFAULT_DATA_PATH))
except FileNotFoundError:
    st.error(f"Couldn't find the invoice data file at `{DEFAULT_DATA_PATH}`. Make sure it's included in the deployment.")
    st.stop()

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
else:
    overdue["Tier"] = overdue["DaysOverdue"].apply(lambda d: reminder_tier(int(d)))

    st.subheader(f"{len(overdue)} overdue invoices")
    st.dataframe(
        overdue[["customerID", "invoiceNumber", "InvoiceAmount", "DueDate", "DaysOverdue", "Tier"]],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("---")
    st.subheader("Draft a reminder")

    invoice_options = overdue["invoiceNumber"].astype(str).tolist()
    selected = st.selectbox("Pick an overdue invoice", invoice_options)

    row = overdue[overdue["invoiceNumber"].astype(str) == selected].iloc[0]
    tier = reminder_tier(int(row["DaysOverdue"]))
    message = draft_reminder(
        customer=row["customerID"],
        invoice_number=str(row["invoiceNumber"]),
        amount=row["InvoiceAmount"],
        due_date=row["DueDate"].strftime("%d %b %Y"),
        days_overdue=int(row["DaysOverdue"]),
        tier=tier,
    )

    st.text_area("Reminder draft", message, height=220)