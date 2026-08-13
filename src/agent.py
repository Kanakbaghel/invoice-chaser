"""
agent.py
---------
The actual Strands Agent. This is the file that needs AWS/Bedrock access
to run — everything in data_loader.py and reminder_writer.py works without
AWS, so we could unit-test all the logic before ever touching the cloud.

Run this AFTER:
  1. AWS account is verified
  2. `aws configure` has been run with your access key
  3. `pip install -r requirements.txt` has been run inside your venv
"""

from strands import Agent, tool
from pathlib import Path
from data_loader import load_invoices, get_open_invoices, reminder_tier, cash_flow_projection
from reminder_writer import draft_reminder

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = str(PROJECT_ROOT / "data" / "accounts_receivable.csv")
SNAPSHOT_DATE = "2013-03-01"  # simulated "today" — change to explore other points in time


@tool
def check_overdue_invoices() -> str:
    """Check which invoices are currently overdue and by how much."""
    df = load_invoices(DATA_PATH)
    open_df = get_open_invoices(df, SNAPSHOT_DATE)
    overdue = open_df[open_df["IsOverdue"]]

    if overdue.empty:
        return "No overdue invoices right now. Nice!"

    lines = [f"{len(overdue)} overdue invoices found:\n"]
    for _, row in overdue.iterrows():
        lines.append(
            f"- {row['customerID']} | Invoice {row['invoiceNumber']} | "
            f"₹{row['InvoiceAmount']:.2f} | {int(row['DaysOverdue'])} days overdue"
        )
    return "\n".join(lines)


@tool
def get_cash_flow_summary() -> str:
    """Get a summary of total outstanding money and how much is at risk."""
    df = load_invoices(DATA_PATH)
    open_df = get_open_invoices(df, SNAPSHOT_DATE)
    summary = cash_flow_projection(open_df)

    return (
        f"Total outstanding: ₹{summary['total_outstanding']:.2f} across "
        f"{summary['num_open_invoices']} open invoices.\n"
        f"Overdue amount: ₹{summary['overdue_amount']:.2f} "
        f"({summary['num_overdue_invoices']} invoices).\n"
        f"Not yet due: ₹{summary['not_yet_due_amount']:.2f}."
    )


@tool
def draft_reminder_for_invoice(invoice_number: str) -> str:
    """Draft a reminder email for a specific overdue invoice number."""
    df = load_invoices(DATA_PATH)
    open_df = get_open_invoices(df, SNAPSHOT_DATE)
    match = open_df[open_df["invoiceNumber"].astype(str) == str(invoice_number)]

    if match.empty:
        return f"Invoice {invoice_number} not found among open invoices."

    row = match.iloc[0]
    tier = reminder_tier(int(row["DaysOverdue"]))

    return draft_reminder(
        customer=row["customerID"],
        invoice_number=str(row["invoiceNumber"]),
        amount=row["InvoiceAmount"],
        due_date=row["DueDate"].strftime("%d %b %Y"),
        days_overdue=int(row["DaysOverdue"]),
        tier=tier,
    )


# The agent itself — wire the tools together with a system prompt.
invoice_agent = Agent(
    tools=[check_overdue_invoices, get_cash_flow_summary, draft_reminder_for_invoice],
    system_prompt=(
        "You are Invoice Chaser, an assistant that helps freelancers and small "
        "business owners stay on top of unpaid invoices. When asked about overdue "
        "invoices, use your tools to check real data before answering. When asked "
        "to follow up on a client, draft a reminder using the appropriate tone for "
        "how overdue the invoice is. Be concise and business-appropriate."
    ),
)


if __name__ == "__main__":
    # Simple manual test loop — run `python src/agent.py` and chat with it.
    print("Invoice Chaser agent ready. Type 'exit' to quit.\n")
    while True:
        user_input = input("You: ")
        if user_input.strip().lower() == "exit":
            break
        response = invoice_agent(user_input)
        print(f"\nAgent: {response}\n")
