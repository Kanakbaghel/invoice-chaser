"""
forecast.py
-------------
Projects when outstanding invoice money is actually likely to arrive —
not just "how much is owed" but "when will I realistically have it."

Two scenarios, built from each client's own settlement history
(median and 90th-percentile days late) rather than a flat guessed
buffer — a methodology change based on Eve's analysis notebook:
- Best case: each client pays at their own MEDIAN days-late (typical behavior)
- Worst case: each client pays at their own 90th-PERCENTILE days-late
  (a bad-but-plausible outcome, not their single worst-ever invoice)

Clients with no history fall back to a flat default (new-client case).
"""

import pandas as pd

DEFAULT_MEDIAN_BUFFER_DAYS = 0   # no history: assume on-time for best case
DEFAULT_P90_BUFFER_DAYS = 14     # no history: assume a two-week slip for worst case


def project_cash_flow(open_df: pd.DataFrame, as_of: pd.Timestamp,
                       client_risk_df: pd.DataFrame = None) -> pd.DataFrame:
    """
    Returns a DataFrame indexed by date with cumulative expected cash
    under 'Best case' and 'Worst case' columns.
    """
    if open_df.empty:
        return pd.DataFrame(columns=["Best case", "Worst case"])

    events = []
    for _, r in open_df.iterrows():
        amt = r["InvoiceAmount"]
        due = r["DueDate"]

        best_buffer = DEFAULT_MEDIAN_BUFFER_DAYS
        worst_buffer = DEFAULT_P90_BUFFER_DAYS

        if client_risk_df is not None and not client_risk_df.empty:
            match = client_risk_df[client_risk_df["customerID"] == r["customerID"]]
            if not match.empty:
                row = match.iloc[0]
                if "median_days_late" in row and pd.notna(row["median_days_late"]):
                    best_buffer = max(float(row["median_days_late"]), 0)
                if "p90_days_late" in row and pd.notna(row["p90_days_late"]):
                    worst_buffer = max(float(row["p90_days_late"]), best_buffer)

        best_date = max(due + pd.Timedelta(days=best_buffer), as_of)
        worst_date = max(due + pd.Timedelta(days=worst_buffer), as_of)

        events.append({"date": best_date, "amount": amt, "scenario": "Best case"})
        events.append({"date": worst_date, "amount": amt, "scenario": "Worst case"})

    events_df = pd.DataFrame(events)
    grouped = events_df.groupby(["scenario", "date"])["amount"].sum().reset_index()
    pivot = grouped.pivot(index="date", columns="scenario", values="amount").fillna(0).sort_index()

    for col in ["Best case", "Worst case"]:
        if col not in pivot.columns:
            pivot[col] = 0.0

    return pivot[["Best case", "Worst case"]].cumsum()


def projected_cash_by(cumulative: pd.DataFrame, target_date: pd.Timestamp) -> dict:
    """How much cash is projected to have arrived by a given target date, per scenario."""
    if cumulative.empty:
        return {"Best case": 0.0, "Worst case": 0.0}

    upto = cumulative[cumulative.index <= target_date]
    if upto.empty:
        return {"Best case": 0.0, "Worst case": 0.0}

    last_row = upto.iloc[-1]
    return {"Best case": round(last_row["Best case"], 2), "Worst case": round(last_row["Worst case"], 2)}
