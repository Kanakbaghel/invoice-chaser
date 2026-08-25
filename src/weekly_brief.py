"""
weekly_brief.py
------------------
Instead of treating every overdue invoice the same, this builds a
PRIORITIZED action list — which client to contact first, and what kind
of action makes sense (reminder vs. payment plan vs. just wait).

Priority combines: how much money is at stake, how overdue it is, and
(if available) how risky the client's payment history is.
"""

import pandas as pd


TIER_WEIGHTS = {"gentle": 1, "polite_followup": 2, "firm": 3, "urgent": 4}
RISK_WEIGHTS = {"Low": 1, "Medium": 2, "High": 3}


def build_action_plan(overdue_df: pd.DataFrame, client_risk_df: pd.DataFrame = None) -> pd.DataFrame:
    """
    Returns overdue_df with a `PriorityScore` and `RecommendedAction` column,
    sorted so the most important invoice to act on today is first.
    """
    if overdue_df.empty:
        return overdue_df

    df = overdue_df.copy()

    max_amount = df["InvoiceAmount"].max() or 1
    amount_score = (df["InvoiceAmount"] / max_amount) * 3  # scale 0-3

    tier_score = df["Tier"].map(TIER_WEIGHTS).fillna(1)

    risk_score = pd.Series(1, index=df.index)  # default: unknown risk
    if client_risk_df is not None and not client_risk_df.empty:
        risk_map = client_risk_df.set_index("customerID")["risk_level"].map(RISK_WEIGHTS)
        risk_score = df["customerID"].map(risk_map).fillna(1)

    df["PriorityScore"] = (amount_score + tier_score + risk_score).round(1)

    def recommend(row):
        # Eve's analysis found disputed invoices run ~4.4x later on average
        # than non-disputed ones — escalating tone on a genuine dispute can
        # backfire, so route these to dispute resolution instead of a
        # firmer reminder or a payment plan offer.
        if row.get("Disputed") == "Yes":
            return "Resolve dispute first"
        elif row["Tier"] in ("firm", "urgent"):
            return "Offer payment plan"
        elif row["Tier"] == "polite_followup":
            return "Send follow-up reminder"
        else:
            return "Send friendly nudge"

    df["RecommendedAction"] = df.apply(recommend, axis=1)

    return df.sort_values("PriorityScore", ascending=False)
