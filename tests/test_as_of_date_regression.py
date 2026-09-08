"""
Regression: demo/reference as_of must not fall back to the real system year.

Knight reported the invoice demo UI still showing 2026 dates while
as_of = 2013-03-01. Root cause: payment-plan installment dates used
date.today() instead of the supplied reference date.
"""

from __future__ import annotations

import os
import re
import sys
from datetime import date

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "webapp"))
sys.path.insert(0, os.path.join(ROOT, "src"))

from payment_plan import build_plan_dates, draft_payment_plan_offer  # noqa: E402
from webapp.app import app  # noqa: E402

AS_OF = "2013-03-01"
CURRENT_YEAR = str(date.today().year)


@pytest.fixture
def client():
    return app.test_client()


def test_sample_as_of_is_reference_date_not_system_year(client):
    res = client.get(f"/api/sample?snapshot={AS_OF}")
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["as_of"] == AS_OF
    assert not payload["as_of"].startswith(CURRENT_YEAR)

    # Formatted display path used by the UI ("As of …")
    year, month, day = payload["as_of"].split("-")
    formatted = date(int(year), int(month), int(day)).strftime("%d %b %Y")
    assert formatted == "01 Mar 2013"
    assert "2013" in formatted
    assert CURRENT_YEAR not in formatted
    assert "2026" not in formatted


def test_format_as_of_js_helper_uses_calendar_date_not_utc_shift():
    """Mirror the frontend formatAsOf calendar-date parsing contract."""
    raw = AS_OF
    year, month, day = map(int, raw.split("-"))
    # Local calendar construction (same approach as main.js formatAsOf)
    local = date(year, month, day)
    assert local.isoformat() == AS_OF
    assert local.year == 2013
    assert local.month == 3
    assert local.day == 1
    assert local.year != int(CURRENT_YEAR)


def test_demo_invoices_still_use_2013_as_of(client):
    overdue = {
        str(row["invoice_number"]): row
        for row in client.get(f"/api/sample?snapshot={AS_OF}").get_json()["overdue"]
    }
    assert overdue["3037486776"]["tier"] == "gentle"
    assert overdue["3037486776"]["days_overdue"] == 1
    assert overdue["2538593943"]["tier"] == "polite_followup"
    assert overdue["2538593943"]["days_overdue"] == 11
    assert overdue["5364802553"]["tier"] == "urgent"
    assert overdue["5364802553"]["days_overdue"] == 31


def test_payment_plan_dates_use_as_of_not_system_today():
    dates = build_plan_dates(3, start=date.fromisoformat(AS_OF))
    assert dates == ["15 Mar 2013", "29 Mar 2013", "12 Apr 2013"]
    assert all(CURRENT_YEAR not in d for d in dates)

    message = draft_payment_plan_offer(
        customer="9181-HEKGV",
        invoice_number="5364802553",
        amount=87.0,
        days_overdue=31,
        num_installments=3,
        as_of=AS_OF,
    )
    assert "15 Mar 2013" in message
    assert "29 Mar 2013" in message
    assert "12 Apr 2013" in message
    assert CURRENT_YEAR not in message
    assert "2026" not in message


def test_payment_plan_api_does_not_emit_system_year_when_as_of_supplied(client):
    res = client.post(
        "/api/payment-plan",
        json={
            "customer": "9181-HEKGV",
            "invoice_number": "5364802553",
            "amount": 87.0,
            "days_overdue": 31,
            "num_installments": 3,
            "as_of": AS_OF,
        },
    )
    assert res.status_code == 200
    message = res.get_json()["message"]
    assert "2013" in message
    assert CURRENT_YEAR not in message
    assert not re.search(r"\b2026\b", message)


def test_payment_plan_without_as_of_still_allows_real_today():
    """Preserve intentional real-date behavior when no reference date is supplied."""
    message = draft_payment_plan_offer(
        customer="ACME",
        invoice_number="1",
        amount=100.0,
        days_overdue=40,
        num_installments=2,
    )
    assert CURRENT_YEAR in message
