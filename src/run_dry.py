"""
run_dry.py
-----------
Runs the full Invoice Chaser logic end-to-end WITHOUT needing AWS/Bedrock —
this is the rule-based "brain" of the agent. Once AWS is set up, agent.py
wraps this same logic with an LLM layer so it can also answer free-form
questions. For now, this script alone proves the core automation works.

Run with: python run_dry.py
"""

from data_loader import load_invoices, get_open_invoices, reminder_tier, cash_flow_projection, DEFAULT_DATA_PATH
from reminder_writer import draft_reminder

SNAPSHOT_DATE = "2013-03-01"  # simulated "today"


def main():
    df = load_invoices(str(DEFAULT_DATA_PATH))
    open_df = get_open_invoices(df, SNAPSHOT_DATE)

    summary = cash_flow_projection(open_df)
    print("=" * 60)
    print(f"INVOICE CHASER — snapshot as of {SNAPSHOT_DATE}")
    print("=" * 60)
    print(f"Open invoices:      {summary['num_open_invoices']}")
    print(f"Overdue invoices:   {summary['num_overdue_invoices']}")
    print(f"Total outstanding:  ₹{summary['total_outstanding']:.2f}")
    print(f"Overdue amount:     ₹{summary['overdue_amount']:.2f}")
    print(f"Not yet due:        ₹{summary['not_yet_due_amount']:.2f}")
    print()

    overdue = open_df[open_df["IsOverdue"]].sort_values("DaysOverdue", ascending=False)

    if overdue.empty:
        print("No overdue invoices — nothing to chase today!")
        return

    print(f"Drafting reminders for {len(overdue)} overdue invoices:\n")

    for _, row in overdue.iterrows():
        tier = reminder_tier(int(row["DaysOverdue"]))
        message = draft_reminder(
            customer=row["customerID"],
            invoice_number=str(row["invoiceNumber"]),
            amount=row["InvoiceAmount"],
            due_date=row["DueDate"].strftime("%d %b %Y"),
            days_overdue=int(row["DaysOverdue"]),
            tier=tier,
        )
        print("-" * 60)
        print(f"[{tier.upper()}] Invoice {row['invoiceNumber']} — {row['customerID']}")
        print("-" * 60)
        print(message)
        print()


if __name__ == "__main__":
    main()
