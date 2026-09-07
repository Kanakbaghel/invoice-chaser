/**
 * Focused unit tests for independent invoice filter composition.
 * Run: node webapp/static/js/invoiceFilters.test.js
 */
const assert = require("assert");
const {
  parseOptionalAmount,
  filterOverdueInvoices,
} = require("./invoiceFilters.js");

const SAMPLE = [
  {
    customer: "5924-UOPGH",
    invoice_number: "2538593943",
    amount: 72.36,
    tier: "polite_followup",
    days_overdue: 11,
  },
  {
    customer: "1604-LIFKX",
    invoice_number: "3037486776",
    amount: 79.37,
    tier: "gentle",
    days_overdue: 1,
  },
  {
    customer: "9181-HEKGV",
    invoice_number: "5364802553",
    amount: 87.0,
    tier: "urgent",
    days_overdue: 31,
  },
  {
    customer: "ACME Corp",
    invoice_number: "1001",
    amount: 250.0,
    tier: "firm",
    days_overdue: 20,
  },
];

function ids(rows) {
  return rows.map((r) => r.invoice_number).sort();
}

// Test 1: Search Client only (no urgency)
{
  const result = filterOverdueInvoices(SAMPLE, {
    search: "LIFKX",
    activeTiers: new Set(),
  });
  assert.deepStrictEqual(ids(result), ["3037486776"]);
}

// Test 2: Min Amount only (no urgency)
{
  const result = filterOverdueInvoices(SAMPLE, {
    minAmount: 80,
    activeTiers: new Set(),
  });
  assert.deepStrictEqual(ids(result), ["1001", "5364802553"]);
}

// Test 3: Max Amount only (no urgency)
{
  const result = filterOverdueInvoices(SAMPLE, {
    maxAmount: 75,
    activeTiers: new Set(),
  });
  assert.deepStrictEqual(ids(result), ["2538593943"]);
}

// Test 4: Min + Max Amount
{
  const result = filterOverdueInvoices(SAMPLE, {
    minAmount: 70,
    maxAmount: 85,
    activeTiers: new Set(),
  });
  assert.deepStrictEqual(ids(result), ["2538593943", "3037486776"]);
}

// Test 5: Search Client + Amount
{
  const result = filterOverdueInvoices(SAMPLE, {
    search: "9181",
    minAmount: 80,
    maxAmount: 100,
    activeTiers: new Set(),
  });
  assert.deepStrictEqual(ids(result), ["5364802553"]);
}

// Test 6: Urgency only
{
  const result = filterOverdueInvoices(SAMPLE, {
    activeTiers: new Set(["gentle"]),
  });
  assert.deepStrictEqual(ids(result), ["3037486776"]);
}

// Test 7: Search + Amount + Urgency
{
  const result = filterOverdueInvoices(SAMPLE, {
    search: "HEKGV",
    minAmount: 50,
    maxAmount: 100,
    activeTiers: new Set(["urgent"]),
  });
  assert.deepStrictEqual(ids(result), ["5364802553"]);
}

// Test 8: No filters → all invoices
{
  const result = filterOverdueInvoices(SAMPLE, {});
  assert.deepStrictEqual(ids(result), ["1001", "2538593943", "3037486776", "5364802553"]);
}

// Test 9: Invalid/empty amount fields must not break filtering
{
  assert.strictEqual(parseOptionalAmount(""), null);
  assert.strictEqual(parseOptionalAmount("   "), null);
  assert.strictEqual(parseOptionalAmount("abc"), null);
  assert.strictEqual(parseOptionalAmount("12.5"), 12.5);
  assert.strictEqual(parseOptionalAmount("0"), 0);

  const result = filterOverdueInvoices(SAMPLE, {
    search: "ACME",
    minAmount: parseOptionalAmount(""),
    maxAmount: parseOptionalAmount("nope"),
    activeTiers: new Set(),
  });
  assert.deepStrictEqual(ids(result), ["1001"]);
}

// Empty urgency set is treated as "no urgency filter"
{
  const withEmpty = filterOverdueInvoices(SAMPLE, {
    search: "UOPGH",
    activeTiers: new Set(),
  });
  const withNull = filterOverdueInvoices(SAMPLE, {
    search: "UOPGH",
    activeTiers: null,
  });
  assert.deepStrictEqual(ids(withEmpty), ["2538593943"]);
  assert.deepStrictEqual(ids(withNull), ["2538593943"]);
}

console.log("invoiceFilters.test.js: all checks passed");
