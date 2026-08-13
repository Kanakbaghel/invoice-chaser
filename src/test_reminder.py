from reminder_writer import draft_reminder

# Using one of your actual overdue invoices as a test case
message = draft_reminder(
    customer="9181-HEKGV",
    invoice_number="5364802553",
    amount=87.00,
    due_date="29 Jan 2013",
    days_overdue=31,
    tier="firm",
)
print(message)
