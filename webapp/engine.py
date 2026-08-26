"""
engine.py
----------
Bundles data_loader / reminder_writer / client_risk / payment_plan /
forecast / weekly_brief into a single JSON-ready dict, so the Flask API
has one function to call regardless of whether the data came from the
sample dataset or an uploaded file.
"""

import sys
import os
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from data_loader import reminder_tier, cash_flow_projection
from client_risk import client_risk_summary, compute_concentration_risk
from forecast import project_cash_flow
from weekly_brief import build_action_plan
from decision_explainer import explain_tier, explain_risk, explain_priority
from impact_calculator import estimate_impact, impact_summary_text


def bundle_from_open_df(open_df: pd.DataFrame, as_of_ts: pd.Timestamp, risk_df: pd.DataFrame = None) -> dict:
    """
    open_df must have columns: customerID, invoiceNumber, InvoiceAmount,
    DueDate, DaysOverdue, IsOverdue — this is the shared contract between
    the sample dataset path and the uploaded-file path.
    """
    summary = cash_flow_projection(open_df)

    overdue = open_df[open_df["IsOverdue"]].sort_values("DaysOverdue", ascending=False).copy()
    overdue["Tier"] = overdue["DaysOverdue"].apply(lambda d: reminder_tier(int(d)))

    overdue_records = [
        {
            "customer": row["customerID"],
            "invoice_number": str(row["invoiceNumber"]),
            "amount": round(float(row["InvoiceAmount"]), 2),
            "due_date": row["DueDate"].strftime("%d %b %Y"),
            "days_overdue": int(row["DaysOverdue"]),
            "tier": row["Tier"],
            "disputed": bool(row.get("Disputed") == "Yes"),
            "why": explain_tier(int(row["DaysOverdue"]), row["Tier"]),
        }
        for _, row in overdue.iterrows()
    ]

    risk_map = {}
    if risk_df is not None and not risk_df.empty:
        for _, r in risk_df.iterrows():
            risk_map[r["customerID"]] = {
                "risk_level": r["risk_level"],
                "avg_days_late": float(r["avg_days_late"]),
                "num_invoices": int(r["num_invoices"]),
                "pct_disputed": float(r["pct_disputed"]),
                "summary": client_risk_summary(r),
                "why": explain_risk(float(r["avg_days_late"]), r["risk_level"], int(r["num_invoices"])),
            }

        concentration_df = compute_concentration_risk(open_df) if not open_df.empty else pd.DataFrame()
    concentration_records = [
        {
            "customer": row["customerID"],
            "outstanding_amount": round(float(row["InvoiceAmount"]), 2),
            "pct_of_total_ar": float(row["pct_of_total_ar"]),
            "concentration_flag": row["concentration_flag"],
        }
        for _, row in concentration_df.iterrows()
    ] if not concentration_df.empty else []

    action_plan_df = build_action_plan(overdue, risk_df) if not overdue.empty else overdue
    max_amount = float(overdue["InvoiceAmount"].max()) if not overdue.empty else 0.0
    action_plan_records = [
        {
            "customer": row["customerID"],
            "invoice_number": str(row["invoiceNumber"]),
            "amount": round(float(row["InvoiceAmount"]), 2),
            "days_overdue": int(row["DaysOverdue"]),
            "tier": row["Tier"],
            "priority_score": float(row["PriorityScore"]),
            "recommended_action": row["RecommendedAction"],
            "why": explain_priority(
                i + 1, float(row["InvoiceAmount"]), max_amount, row["Tier"],
                risk_map.get(row["customerID"], {}).get("risk_level"),
            ),
        }
        for i, (_, row) in enumerate(action_plan_df.iterrows())
    ] if not action_plan_df.empty else []

    impact = estimate_impact(overdue)
    impact["summary_text"] = impact_summary_text(impact)

    cum = project_cash_flow(open_df, as_of_ts, risk_df)
    forecast = {
        "dates": [d.strftime("%Y-%m-%d") for d in cum.index],
        "best": [round(float(v), 2) for v in cum["Best case"]],
        "worst": [round(float(v), 2) for v in cum["Worst case"]],
    } if not cum.empty else {"dates": [], "best": [], "worst": []}

       return {
        "summary": {
            "open_invoices": summary["num_open_invoices"],
            "overdue_invoices": summary["num_overdue_invoices"],
            "total_outstanding": summary["total_outstanding"],
            "overdue_amount": summary["overdue_amount"],
        },
        "overdue": overdue_records,
        "risk": risk_map,
        "concentration": concentration_records,
        "action_plan": action_plan_records,
        "forecast": forecast,
        "impact": impact,
        "as_of": as_of_ts.strftime("%Y-%m-%d"),
    }
        
