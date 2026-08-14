"""
payment_plan.py
------------------
For invoices that are badly overdue, jumping straight to "URGENT, pay now"
often backfires — the client may genuinely not have the money right now.
This suggests a reasonable installment plan instead, and drafts a message
offering it diplomatically.
"""

from datetime import date, timedelta


def suggest_installments(amount: float, num_installments: int = 3) -> list[float]:
    """Split an amount into roughly equal installments (last one absorbs rounding)."""
    base = round(amount / num_installments, 2)
    installments = [base] * (num_installments - 1)
    installments.append(round(amount - sum(installments), 2))
    return installments


def build_plan_dates(num_installments: int = 3, gap_days: int = 14, start: date = None) -> list[str]:
    """Generate installment due dates, spaced `gap_days` apart, starting today (or `start`)."""
    start = start or date.today()
    return [(start + timedelta(days=gap_days * (i + 1))).strftime("%d %b %Y") for i in range(num_installments)]


def draft_payment_plan_offer(customer: str, invoice_number: str, amount: float,
                              days_overdue: int, num_installments: int = 3) -> str:
    """Draft a message offering an installment plan instead of a blunt demand."""
    installments = suggest_installments(amount, num_installments)
    dates = build_plan_dates(num_installments)

    plan_lines = "\n".join(
        f"  {i + 1}. ₹{amt:,.2f} by {due}" for i, (amt, due) in enumerate(zip(installments, dates))
    )

    return (
        f"Subject: A more flexible option for invoice {invoice_number}\n\n"
        f"Hi {customer},\n\n"
        f"I wanted to follow up on invoice {invoice_number} for ₹{amount:,.2f}, now {days_overdue} days overdue. "
        f"I understand things come up — rather than needing the full amount at once, here's a payment plan "
        f"that might work better:\n\n"
        f"{plan_lines}\n\n"
        f"Let me know if this works for you, or if you'd like to adjust the schedule. I'd rather find something "
        f"that works than let this drag on for either of us.\n\n"
        f"Thanks for working with me on this."
    )
