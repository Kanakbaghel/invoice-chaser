"""
impact_calculator.py
-----------------------
Estimates how much time and cash-flow improvement a business owner gets
from using Invoice Chaser instead of manually tracking and chasing
invoices. These are clearly-labeled ESTIMATES based on stated assumptions
— not measured causal effects (we don't have before/after data for that).
"""

DEFAULT_MINUTES_PER_MANUAL_FOLLOWUP = 15  # time to find, draft, and send one manual reminder
DEFAULT_LATE_REDUCTION_PCT = 20  # assumed % reduction in lateness from consistent, well-timed reminders


def estimate_impact(overdue_df, minutes_per_manual_followup: int = DEFAULT_MINUTES_PER_MANUAL_FOLLOWUP,
                     assumed_late_reduction_pct: float = DEFAULT_LATE_REDUCTION_PCT) -> dict:
    """
    overdue_df must have an InvoiceAmount column (one row per overdue invoice).
    Returns hours saved and an estimated cash-acceleration figure, plus the
    assumptions used so this is never presented as a precise measurement.
    """
    n = len(overdue_df)
    total_overdue_amount = round(float(overdue_df["InvoiceAmount"].sum()), 2) if n else 0.0
    hours_saved = round(n * minutes_per_manual_followup / 60, 1)
    estimated_cash_accelerated = round(total_overdue_amount * (assumed_late_reduction_pct / 100), 2)

    return {
        "invoices_handled": n,
        "estimated_hours_saved": hours_saved,
        "total_overdue_amount": total_overdue_amount,
        "estimated_cash_accelerated": estimated_cash_accelerated,
        "assumptions": {
            "minutes_per_manual_followup": minutes_per_manual_followup,
            "assumed_late_reduction_pct": assumed_late_reduction_pct,
        },
    }


def impact_summary_text(impact: dict) -> str:
    """One or two friendly sentences summarizing the estimate for display."""
    if impact["invoices_handled"] == 0:
        return "No overdue invoices right now — nothing to estimate."

    return (
        f"Chasing these {impact['invoices_handled']} invoices manually would take roughly "
        f"{impact['estimated_hours_saved']:.1f} hours. Consistent follow-up could also bring in "
        f"about ₹{impact['estimated_cash_accelerated']:,.2f} sooner than it would otherwise arrive "
        f"(estimate, not a guarantee)."
    )
