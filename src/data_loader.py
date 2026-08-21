"""
data_loader.py
----------------
Loads the IBM Accounts Receivable dataset and turns it into a realistic
"live" invoice ledger that our agent can act on.

Why we need a snapshot date:
The public dataset is a HISTORICAL record — every invoice already has a
SettledDate (it's used elsewhere for late-payment prediction research).
For our agent demo we need invoices that are still OPEN (unpaid) as of
"today", so we pick a snapshot date and treat any invoice that was settled
AFTER that date as "still outstanding" at that point in time. This is a
standard technique for turning a historical ledger into a realistic
point-in-time snapshot for a demo/testing environment.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

# Resolve paths relative to this script's location, not the current working
# directory — this way it works whether you run it from src/ or the project root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "accounts_receivable.csv"


REQUIRED_COLUMNS = [
    "countryCode", "customerID", "PaperlessDate", "invoiceNumber",
    "InvoiceDate", "DueDate", "InvoiceAmount", "Disputed",
    "SettledDate", "PaperlessBill", "DaysToSettle", "DaysLate",
]


def load_invoices(path: str) -> pd.DataFrame:
    """Load the invoice file (CSV or Excel) and parse date columns."""
    if path.lower().endswith(".csv"):
        df = pd.read_csv(path)
    else:
        df = pd.read_excel(path)

    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Dataset is missing expected columns: {missing}")

    for col in ["PaperlessDate", "InvoiceDate", "DueDate", "SettledDate"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    return df


def get_open_invoices(df: pd.DataFrame, as_of_date: str) -> pd.DataFrame:
    """
    Return the invoices that were still unpaid as of `as_of_date`
    (format: 'YYYY-MM-DD'). This simulates 'today' for the demo.
    """
    as_of = pd.Timestamp(as_of_date)

    open_df = df[(df["InvoiceDate"] <= as_of) & (df["SettledDate"] > as_of)].copy()

    open_df["DaysOverdue"] = (as_of - open_df["DueDate"]).dt.days
    open_df["IsOverdue"] = open_df["DaysOverdue"] > 0

    return open_df[[
        "customerID", "invoiceNumber", "InvoiceDate", "DueDate",
        "InvoiceAmount", "Disputed", "DaysOverdue", "IsOverdue",
    ]].sort_values("DaysOverdue", ascending=False)


def reminder_tier(days_overdue: int) -> str:
    if days_overdue <= 0:
        return "not_due"
    elif days_overdue <= 5:
        return "gentle"
    elif days_overdue <= 13:
        return "polite_followup"
    elif days_overdue <= 25:
        return "firm"
    else:
        return "urgent"


def cash_flow_projection(open_df: pd.DataFrame) -> dict:
    """Simple projection: how much money is currently tied up, and how much
    of it is at risk (overdue vs not yet due)."""
    total_outstanding = round(open_df["InvoiceAmount"].sum(), 2)
    overdue_amount = round(open_df.loc[open_df["IsOverdue"], "InvoiceAmount"].sum(), 2)
    not_due_amount = round(total_outstanding - overdue_amount, 2)

    return {
        "total_outstanding": total_outstanding,
        "overdue_amount": overdue_amount,
        "not_yet_due_amount": not_due_amount,
        "num_open_invoices": int(len(open_df)),
        "num_overdue_invoices": int(open_df["IsOverdue"].sum()),
    }


if __name__ == "__main__":
    # Quick manual test — run this file directly to sanity check your data.
    df = load_invoices(str(DEFAULT_DATA_PATH))
    print(f"Loaded {len(df)} total historical invoices.")

    snapshot_date = "2013-03-01"  # pick any date inside the dataset's range
    open_invoices = get_open_invoices(df, snapshot_date)
    print(f"\nAs of {snapshot_date}: {len(open_invoices)} invoices were open.")
    print(open_invoices.head(10))

    print("\nCash flow snapshot:")
    print(cash_flow_projection(open_invoices))
