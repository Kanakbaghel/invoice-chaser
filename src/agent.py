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
from strands.models import BedrockModel
from pathlib import Path
from data_loader import load_invoices, get_open_invoices, reminder_tier, cash_flow_projection
from reminder_writer import draft_reminder
from client_risk import compute_client_risk, client_risk_summary
from payment_plan import draft_payment_plan_offer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = str(PROJECT_ROOT / "data" / "accounts_receivable.csv")

# Amazon Nova Micro — fast, cheap, and doesn't require the extra
# Anthropic use-case approval step that new AWS accounts sometimes
# have to wait on. Swap back to a Claude model_id later if you want.
bedrock_model = BedrockModel(
    model_id="us.amazon.nova-micro-v1:0",
    region_name="us-east-1",
)
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


@tool
def check_client_risk(customer_id: str) -> str:
    """Check a client's payment history to see if they're a reliable payer or a risk."""
    df = load_invoices(DATA_PATH)
    risk_df = compute_client_risk(df, SNAPSHOT_DATE)
    match = risk_df[risk_df["customerID"] == customer_id]

    if match.empty:
        return f"No payment history found for {customer_id} — either a new client or no settled invoices yet."

    return client_risk_summary(match.iloc[0])


@tool
def offer_payment_plan(invoice_number: str, num_installments: int = 3) -> str:
    """Draft an installment payment plan offer for a severely overdue invoice, instead of a blunt demand."""
    df = load_invoices(DATA_PATH)
    open_df = get_open_invoices(df, SNAPSHOT_DATE)
    match = open_df[open_df["invoiceNumber"].astype(str) == str(invoice_number)]

    if match.empty:
        return f"Invoice {invoice_number} not found among open invoices."

    row = match.iloc[0]
    return draft_payment_plan_offer(
        customer=row["customerID"],
        invoice_number=str(row["invoiceNumber"]),
        amount=row["InvoiceAmount"],
        days_overdue=int(row["DaysOverdue"]),
        num_installments=num_installments,
    )


# The agent itself — wire the tools together with a system prompt.
invoice_agent = Agent(
    model=bedrock_model,
    tools=[
        check_overdue_invoices, get_cash_flow_summary, draft_reminder_for_invoice,
        check_client_risk, offer_payment_plan,
    ],
    system_prompt=(
        "You are Invoice Chaser, an assistant that helps freelancers and small "
        "business owners stay on top of unpaid invoices. When asked about overdue "
        "invoices, use your tools to check real data before answering. When asked "
        "to follow up on a client, draft a reminder using the appropriate tone for "
        "how overdue the invoice is — check the client's payment history first if "
        "relevant, since a chronically late payer and an occasionally-late one need "
        "different approaches. For invoices that are severely overdue, consider "
        "suggesting a payment plan instead of an aggressive reminder. Be concise "
        "and business-appropriate."
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