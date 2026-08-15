"""
forecast.py
-------------
Projects when outstanding invoice money is actually likely to arrive —
not just "how much is owed" but "when will I realistically have it."

Two scenarios:
- Best case: everyone pays on their due date (or immediately, if already overdue)
- Worst case: each client pays based on their own historical lateness
  (a chronically-late client is assumed to stay chronically late)
"""

import pandas as pd


def project_cash_flow(open_df: pd.DataFrame, as_of: pd.Timestamp,
                       client_risk_df: pd.DataFrame = None,
                       default_buffer_days: int = 14) -> pd.DataFrame:
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

        best_date = max(due, as_of)

        buffer_days = default_buffer_days
        if client_risk_df is not None and not client_risk_df.empty:
            match = client_risk_df[client_risk_df["customerID"] == r["customerID"]]
            if not match.empty:
                buffer_days = max(int(match.iloc[0]["avg_days_late"]), 0)
        worst_date = max(due + pd.Timedelta(days=buffer_days), as_of)

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
