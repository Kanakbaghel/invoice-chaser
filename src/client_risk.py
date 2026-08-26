"""
client_risk.py
----------------
Looks at a client's PAST settled invoices (from the historical dataset) to
score how risky they are to work with going forward — someone who always
pays 40 days late is a different kind of client than someone who's paid
on time nine times and is late once.

This only works when there's settlement history to learn from. For a
brand-new client with no history, we simply say "not enough data yet."
"""

import pandas as pd


def compute_client_risk(df: pd.DataFrame, as_of_date: str) -> pd.DataFrame:
    """
    For each customer, look at invoices that were ALREADY SETTLED before
    as_of_date (their track record so far) and summarize how late they
    tend to pay.

    Returns one row per customer with: num_invoices, avg_days_late,
    median_days_late, p90_days_late, pct_disputed, risk_level.
    """
    as_of = pd.Timestamp(as_of_date)
    history = df[df["SettledDate"] <= as_of].copy()

    if history.empty:
        return pd.DataFrame(columns=[
            "customerID", "num_invoices", "avg_days_late", "median_days_late",
            "p90_days_late", "pct_disputed", "risk_level"
        ])

    grouped = history.groupby("customerID").agg(
        num_invoices=("invoiceNumber", "count"),
        avg_days_late=("DaysLate", "mean"),
        median_days_late=("DaysLate", "median"),
        p90_days_late=("DaysLate", lambda s: s.quantile(0.9)),
        pct_disputed=("Disputed", lambda s: (s == "Yes").mean() * 100),
    ).reset_index()

    grouped["avg_days_late"] = grouped["avg_days_late"].round(1)
    grouped["median_days_late"] = grouped["median_days_late"].round(1)
    grouped["p90_days_late"] = grouped["p90_days_late"].round(1)
    grouped["pct_disputed"] = grouped["pct_disputed"].round(0)
    grouped["risk_level"] = grouped["avg_days_late"].apply(_risk_level)

    return grouped.sort_values("avg_days_late", ascending=False)


def _risk_level(avg_days_late: float) -> str:
    if avg_days_late <= 2:
        return "Low"
    elif avg_days_late <= 10:
        return "Medium"
    else:
        return "High"


def client_risk_summary(risk_row: pd.Series) -> str:
    """One-line human-readable summary for a single client's risk profile."""
    if risk_row["risk_level"] == "Low":
        return (
            f"Reliable payer — {risk_row['num_invoices']} past invoices, "
            f"averages {risk_row['avg_days_late']:.0f} days late."
        )
    elif risk_row["risk_level"] == "Medium":
        return (
            f"Occasionally slow — {risk_row['num_invoices']} past invoices, "
            f"averages {risk_row['avg_days_late']:.0f} days late. Worth a heads-up reminder before due date."
        )
    else:
        return (
            f"Chronically late — {risk_row['num_invoices']} past invoices, "
            f"averages {risk_row['avg_days_late']:.0f} days late. Consider requiring a deposit upfront next time."
        )

def compute_concentration_risk(open_df: pd.DataFrame) -> pd.DataFrame:
    """
    For each customer, what % of TOTAL outstanding AR do they represent?
    High concentration = if this one client goes bad, it hurts a lot.
    """
    total_outstanding = open_df["InvoiceAmount"].sum()
    by_customer = open_df.groupby("customerID")["InvoiceAmount"].sum().reset_index()
    by_customer["pct_of_total_ar"] = (by_customer["InvoiceAmount"] / total_outstanding * 100).round(1)
    by_customer["concentration_flag"] = by_customer["pct_of_total_ar"].apply(
        lambda pct: "High" if pct >= 25 else ("Medium" if pct >= 10 else "Low")
    )
    return by_customer.sort_values("pct_of_total_ar", ascending=False)
