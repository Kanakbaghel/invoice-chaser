/**
 * Pure overdue-invoice filter helpers.
 * Each criterion is optional and independently composable.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.InvoiceFilters = factory();
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  function parseOptionalAmount(raw) {
    if (raw == null) return null;
    const text = String(raw).trim();
    if (text === "") return null;
    const value = parseFloat(text);
    return Number.isFinite(value) ? value : null;
  }

  /**
   * @param {Array<{customer: string, amount: number, tier: string}>} rows
   * @param {{
   *   search?: string,
   *   minAmount?: number|null,
   *   maxAmount?: number|null,
   *   activeTiers?: Set<string>|Iterable<string>|null
   * }} filters
   */
  function filterOverdueInvoices(rows, filters = {}) {
    const search = String(filters.search || "").trim().toLowerCase();
    const minAmount =
      filters.minAmount == null || Number.isNaN(filters.minAmount)
        ? null
        : filters.minAmount;
    const maxAmount =
      filters.maxAmount == null || Number.isNaN(filters.maxAmount)
        ? null
        : filters.maxAmount;

    let activeTiers = null;
    if (filters.activeTiers) {
      activeTiers =
        filters.activeTiers instanceof Set
          ? filters.activeTiers
          : new Set(filters.activeTiers);
      if (activeTiers.size === 0) activeTiers = null;
    }

    return rows.filter((row) => {
      if (search && !String(row.customer).toLowerCase().includes(search)) {
        return false;
      }
      if (minAmount != null && row.amount < minAmount) {
        return false;
      }
      if (maxAmount != null && row.amount > maxAmount) {
        return false;
      }
      if (activeTiers && !activeTiers.has(row.tier)) {
        return false;
      }
      return true;
    });
  }

  return { parseOptionalAmount, filterOverdueInvoices };
});
