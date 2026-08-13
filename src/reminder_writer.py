"""
reminder_writer.py
--------------------
Turns an overdue invoice + its reminder tier into a ready-to-send message.
This is deterministic (rule-based) so it works even before the LLM/agent
layer is wired up — the agent will call this as a *tool* and can polish
the tone further using the model if we want.
"""

TEMPLATES = {
    "gentle": (
        "Subject: Friendly reminder — Invoice {invoice_number}\n\n"
        "Hi {customer},\n\n"
        "Just a quick note — invoice {invoice_number} for {amount} was due on {due_date} "
        "and it looks like it hasn't been settled yet. No rush, just flagging it in case "
        "it slipped through. Let me know if you need another copy of the invoice.\n\n"
        "Thanks!"
    ),
    "polite_followup": (
        "Subject: Following up — Invoice {invoice_number} ({days_overdue} days overdue)\n\n"
        "Hi {customer},\n\n"
        "Following up on invoice {invoice_number} for {amount}, which was due on {due_date} "
        "and is now {days_overdue} days overdue. Could you let me know the expected payment date? "
        "Happy to answer any questions about the invoice.\n\n"
        "Thanks for your help."
    ),
    "firm": (
        "Subject: Action needed — Invoice {invoice_number} significantly overdue\n\n"
        "Hi {customer},\n\n"
        "Invoice {invoice_number} for {amount} is now {days_overdue} days past its due date "
        "of {due_date}. This is the third follow-up on this invoice. Please arrange payment "
        "at your earliest convenience, or let me know immediately if there's an issue "
        "preventing payment so we can resolve it.\n\n"
        "Please treat this as a priority."
    ),
    "urgent": (
        "Subject: URGENT — Invoice {invoice_number} — {days_overdue} days overdue\n\n"
        "Hi {customer},\n\n"
        "Invoice {invoice_number} for {amount} remains unpaid, {days_overdue} days past the "
        "due date of {due_date}. Despite previous reminders, we have not received payment or "
        "a response. Please settle this invoice immediately or contact us to discuss a payment "
        "plan. Continued non-payment may require us to escalate this further.\n\n"
        "We'd much rather resolve this directly — please reach out as soon as possible."
    ),
}


def draft_reminder(customer: str, invoice_number: str, amount: float,
                    due_date: str, days_overdue: int, tier: str) -> str:
    """Build a reminder message for one invoice based on its tier."""
    if tier not in TEMPLATES:
        return f"No reminder needed — invoice {invoice_number} is not overdue."

    return TEMPLATES[tier].format(
        customer=customer,
        invoice_number=invoice_number,
        amount=f"₹{amount:,.2f}",
        due_date=due_date,
        days_overdue=days_overdue,
    )
