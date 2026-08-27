# 🧾 Invoice Chaser

**An AI agent that chases down unpaid invoices — so freelancers and small business owners don't have to.**

Built with [Strands Agents SDK](https://strandsagents.com) for the AWS **Agents for Humans Hackathon** — Professional Agents track.

---

## The Problem

Freelancers and small business owners lose real money to late-paying clients — not because clients refuse to pay, but because **chasing payment is awkward, easy to forget, and takes real time**. Most people either:
- Let overdue invoices slide because sending a reminder feels uncomfortable, or
- Send the same generic nudge to every client regardless of how overdue they are, risking either being too soft (ignored) or too aggressive (damaged relationship)

Meanwhile, unpaid invoices quietly wreck cash flow — the #1 reason small businesses run into trouble.

## Who It's For

Freelancers, consultants, and small business owners who invoice clients directly and don't have a dedicated accounts-receivable team to follow up on their behalf.

## Why It Matters

A few days of delay on enough invoices can be the difference between making payroll and missing it. Invoice Chaser turns "I should really follow up on that" into something that just happens — consistently, and with the right tone every time.

---

## What It Does

Invoice Chaser is an agent that works through a business's invoice ledger and takes real action, end to end:

1. **Scans open invoices** and identifies which ones are overdue, and by how many days
2. **Classifies urgency** into four tiers — gentle → polite follow-up → firm → urgent — based on how overdue each invoice is
3. **Drafts a ready-to-send reminder** in the appropriate tone for each overdue invoice, so the tone escalates naturally without ever sounding robotic or aggressive too early
4. **Projects cash flow** — how much money is currently tied up in unpaid invoices, and how much of that is genuinely at risk

This isn't a dashboard that shows you numbers — it's an agent that does the follow-up work itself.

---

## Tech Stack

- **[Strands Agents SDK](https://strandsagents.com)** — agent framework and tool orchestration
- **Amazon Bedrock** — LLM backend for the agent
- **Python** — core logic (pandas for data processing)
- **Data**: [IBM Accounts Receivable — Late Payment Histories](https://www.kaggle.com/datasets/hhenry/finance-factoring-ibm-late-payment-histories) (public dataset, used to simulate a realistic invoice ledger)

---

## How It Works

The project is split into two layers on purpose:

- **Rule-based core** (`data_loader.py`, `reminder_writer.py`) — handles data processing, overdue detection, and reminder drafting. This logic is fully deterministic and testable on its own, without any AWS dependency.
- **Agent layer** (`agent.py`) — wraps the rule-based core as Strands **tools**, so the agent can reason about *when* to use them and answer free-form questions like "how much am I owed right now?" or "draft a follow-up for invoice X."

This means the core automation is provably solid on its own — the LLM adds a natural-language interface on top of logic that already works.

```
User / scheduled trigger
        │
        ▼
   Strands Agent (Bedrock)
        │
   ┌────┼─────────────────┐
   ▼    ▼                 ▼
check_overdue   get_cash_flow   draft_reminder_for_invoice
 _invoices()     _summary()        (invoice_number)
        │              │                  │
        └──────────────┴──────────────────┘
                      │
                      ▼
            data_loader.py (pandas)
                      │
                      ▼
         accounts_receivable.csv
```

---

## Project Structure

```
invoice-chaser/
├── data/
│   └── accounts_receivable.csv     # invoice ledger (IBM public dataset)
├── src/
│   ├── data_loader.py              # loads data, detects overdue invoices, cash flow logic
│   ├── reminder_writer.py          # tone-tiered reminder message templates
│   ├── run_dry.py                  # runs the full pipeline without AWS (for testing/demo)
│   └── agent.py                    # Strands Agent — wraps the above as tools
├── requirements.txt
└── README.md
```

---

## Running It

```bash
python -m venv venv
venv\Scripts\activate            # Windows
pip install -r requirements.txt

# Test the core logic without any AWS setup:
cd src
python run_dry.py

# Run the full conversational agent (needs AWS credentials configured):
python agent.py
```

---

## Data Note

This project uses IBM's publicly available **Accounts Receivable — Late Payment Histories** dataset (Kaggle). It's a well-known, IBM-published sample dataset with realistic invoice/payment patterns; it is not a live company's private financial data. Since the dataset is historical (every invoice has a settlement date), we simulate a "snapshot" date and treat any invoice settled after that date as still open — giving the agent a realistic, point-in-time invoice ledger to work from.

---

## License

MIT — see `LICENSE`.
