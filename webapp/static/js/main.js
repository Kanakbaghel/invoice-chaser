// ---------------- State ----------------
let bundle = null;
let uploadToken = null;
let activeTiers = new Set(["gentle", "polite_followup", "firm", "urgent"]);
let tierChart = null;
let forecastChart = null;

const TIER_LABELS = { gentle: "Gentle", polite_followup: "Follow-up", firm: "Firm", urgent: "Urgent" };

// ---------------- Init ----------------
document.addEventListener("DOMContentLoaded", () => {
  buildTierChips();
  attachListeners();
  loadSample();
});

function buildTierChips() {
  const container = document.getElementById("tier-chips");
  Object.keys(TIER_LABELS).forEach((tier) => {
    const chip = document.createElement("button");
    chip.className = `chip active ${tier}`;
    chip.textContent = TIER_LABELS[tier];
    chip.dataset.tier = tier;
    chip.onclick = () => {
      if (activeTiers.has(tier)) { activeTiers.delete(tier); chip.classList.remove("active"); }
      else { activeTiers.add(tier); chip.classList.add("active"); }
      applyFilters();
    };
    container.appendChild(chip);
  });
}

function attachListeners() {
  document.getElementById("btn-sample").onclick = () => switchSource("sample");
  document.getElementById("btn-upload").onclick = () => switchSource("upload");
  document.getElementById("snapshot-date").onchange = loadSample;
  document.getElementById("file-drop").onclick = () => document.getElementById("file-input").click();
  document.getElementById("file-input").onchange = handleFileSelect;
  document.getElementById("compute-upload-btn").onclick = computeUpload;

  document.getElementById("search-input").oninput = applyFilters;
  document.getElementById("amount-min").oninput = applyFilters;
  document.getElementById("amount-max").oninput = applyFilters;

  document.getElementById("horizon-slider").oninput = (e) => {
    document.getElementById("horizon-value").textContent = `${e.target.value} days`;
    renderForecastChart();
    updateForecastResult();
  };
  document.getElementById("target-date").onchange = updateForecastResult;
  document.getElementById("target-amount").oninput = updateForecastResult;

  document.getElementById("invoice-select").onchange = onInvoiceSelect;
  document.getElementById("installments-slider").oninput = (e) => {
    document.getElementById("installments-value").textContent = e.target.value;
    fetchPaymentPlan();
  };
}

function switchSource(mode) {
  document.getElementById("btn-sample").classList.toggle("active", mode === "sample");
  document.getElementById("btn-upload").classList.toggle("active", mode === "upload");
  document.getElementById("sample-controls").style.display = mode === "sample" ? "block" : "none";
  document.getElementById("upload-controls").style.display = mode === "upload" ? "block" : "none";
  if (mode === "sample") loadSample();
}

// ---------------- Data loading ----------------
async function loadSample() {
  const snapshot = document.getElementById("snapshot-date").value || "2013-03-01";
  const res = await fetch(`/api/sample?snapshot=${snapshot}`);
  const data = await res.json();
  setBundle(data);
}

async function handleFileSelect(e) {
  const file = e.target.files[0];
  if (!file) return;
  document.getElementById("file-drop-label").textContent = file.name;

  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch("/api/upload/columns", { method: "POST", body: formData });
  const data = await res.json();
  if (data.error) { alert(data.error); return; }

  uploadToken = data.token;
  ["map-customer", "map-amount", "map-id", "map-due"].forEach((id) => {
    const sel = document.getElementById(id);
    sel.innerHTML = data.columns.map((c) => `<option value="${c}">${c}</option>`).join("");
  });
  const paidSel = document.getElementById("map-paid");
  paidSel.innerHTML = `<option value="">(none — assume all unpaid)</option>` +
    data.columns.map((c) => `<option value="${c}">${c}</option>`).join("");

  document.getElementById("mapping-container").style.display = "block";
}

async function computeUpload() {
  const payload = {
    token: uploadToken,
    customer_col: document.getElementById("map-customer").value,
    amount_col: document.getElementById("map-amount").value,
    id_col: document.getElementById("map-id").value,
    due_col: document.getElementById("map-due").value,
    paid_col: document.getElementById("map-paid").value || null,
  };
  const res = await fetch("/api/upload/compute", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (data.error) { alert(data.error); return; }
  setBundle(data);
}

// ---------------- Rendering ----------------
function setBundle(data) {
  bundle = data;
  renderStats(data.summary);
  applyFilters();
  renderActionPlan(data.action_plan);
  populateInvoiceSelect(data.overdue);

  const asOf = new Date(data.as_of);
  const targetDefault = new Date(asOf); targetDefault.setDate(targetDefault.getDate() + 30);
  document.getElementById("target-date").value = targetDefault.toISOString().slice(0, 10);

  renderForecastChart();
  updateForecastResult();

  document.getElementById("reminder-output").textContent = "Select an invoice above to draft a reminder.";
  document.getElementById("payment-plan-section").style.display = "none";
}

function renderStats(s) {
  document.getElementById("stat-open").textContent = s.open_invoices;
  document.getElementById("stat-overdue").textContent = s.overdue_invoices;
  document.getElementById("stat-outstanding").textContent = `₹${s.total_outstanding.toFixed(2)}`;
  document.getElementById("stat-overdue-amount").textContent = `₹${s.overdue_amount.toFixed(2)}`;
}

function applyFilters() {
  if (!bundle) return;
  const search = document.getElementById("search-input").value.toLowerCase();
  const min = parseFloat(document.getElementById("amount-min").value) || 0;
  const maxRaw = document.getElementById("amount-max").value;
  const max = maxRaw ? parseFloat(maxRaw) : Infinity;

  const filtered = bundle.overdue.filter((row) =>
    row.customer.toLowerCase().includes(search) &&
    activeTiers.has(row.tier) &&
    row.amount >= min && row.amount <= max
  );

  renderTable(filtered);
  renderTierChart(filtered);
}

function renderTable(rows) {
  const tbody = document.getElementById("invoice-table-body");
  tbody.innerHTML = "";
  document.getElementById("table-empty").style.display = rows.length ? "none" : "block";

  rows.forEach((row) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.customer}</td>
      <td>${row.invoice_number}</td>
      <td>₹${row.amount.toFixed(2)}</td>
      <td>${row.due_date}</td>
      <td>${row.days_overdue}</td>
      <td><span class="tier-badge ${row.tier}">${TIER_LABELS[row.tier]}</span></td>
    `;
    tbody.appendChild(tr);
  });
}

function renderTierChart(rows) {
  const totals = { gentle: 0, polite_followup: 0, firm: 0, urgent: 0 };
  rows.forEach((r) => { totals[r.tier] += r.amount; });

  const ctx = document.getElementById("tier-chart");
  const dataValues = Object.keys(TIER_LABELS).map((t) => totals[t]);
  const colors = ["#2F6F68", "#C89A3E", "#B3382C", "#7a1f16"];

  if (tierChart) tierChart.destroy();
  tierChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: Object.values(TIER_LABELS),
      datasets: [{ data: dataValues, backgroundColor: colors, borderRadius: 4 }],
    },
    options: {
      plugins: { legend: { display: false }, title: { display: true, text: "By urgency (₹)" } },
      scales: { y: { beginAtZero: true } },
    },
  });
}

function renderActionPlan(list) {
  const container = document.getElementById("action-plan-list");
  container.innerHTML = "";
  if (!list.length) {
    container.innerHTML = `<div class="empty-state">No overdue invoices — nothing to chase!</div>`;
    return;
  }
  list.slice(0, 10).forEach((item, i) => {
    const row = document.createElement("div");
    row.className = "action-row";
    row.innerHTML = `
      <span class="priority">#${i + 1}</span>
      <span>${item.customer} — ₹${item.amount.toFixed(2)} (${item.days_overdue}d late)</span>
      <span><strong>${item.recommended_action}</strong></span>
    `;
    container.appendChild(row);
  });
}

function renderForecastChart() {
  if (!bundle) return;
  const horizon = parseInt(document.getElementById("horizon-slider").value, 10);
  const asOf = new Date(bundle.as_of);
  const cutoff = new Date(asOf); cutoff.setDate(cutoff.getDate() + horizon);

  const dates = [], best = [], worst = [];
  bundle.forecast.dates.forEach((d, i) => {
    if (new Date(d) <= cutoff) {
      dates.push(d); best.push(bundle.forecast.best[i]); worst.push(bundle.forecast.worst[i]);
    }
  });

  const ctx = document.getElementById("forecast-chart");
  if (forecastChart) forecastChart.destroy();
  forecastChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: dates,
      datasets: [
        { label: "Best case", data: best, borderColor: "#2F6F68", backgroundColor: "rgba(47,111,104,0.1)", tension: 0.2, fill: true },
        { label: "Worst case", data: worst, borderColor: "#B3382C", backgroundColor: "rgba(179,56,44,0.08)", tension: 0.2, fill: true },
      ],
    },
    options: { plugins: { legend: { position: "bottom" } } },
  });
}

function updateForecastResult() {
  if (!bundle || !bundle.forecast.dates.length) {
    document.getElementById("forecast-result").textContent = "Not enough data to forecast yet.";
    return;
  }
  const targetDate = new Date(document.getElementById("target-date").value);
  const targetAmount = parseFloat(document.getElementById("target-amount").value) || 0;

  let bestVal = 0, worstVal = 0;
  bundle.forecast.dates.forEach((d, i) => {
    if (new Date(d) <= targetDate) { bestVal = bundle.forecast.best[i]; worstVal = bundle.forecast.worst[i]; }
  });

  let msg = `Best case by then: ₹${bestVal.toFixed(2)} · Worst case: ₹${worstVal.toFixed(2)}`;
  if (targetAmount > 0) {
    if (worstVal >= targetAmount) msg += " — Even worst case, you're covered. ✅";
    else if (bestVal >= targetAmount) msg += " — Covered if clients pay roughly on time, not guaranteed. ⚠️";
    else msg += " — You may fall short of this amount by then. 🔴";
  }
  document.getElementById("forecast-result").textContent = msg;
}

function populateInvoiceSelect(rows) {
  const sel = document.getElementById("invoice-select");
  sel.innerHTML = `<option value="">— choose an invoice —</option>` +
    rows.map((r) => `<option value="${r.invoice_number}">${r.invoice_number} — ${r.customer} (₹${r.amount.toFixed(2)})</option>`).join("");
}

async function onInvoiceSelect() {
  const invoiceNumber = document.getElementById("invoice-select").value;
  if (!invoiceNumber) return;
  const row = bundle.overdue.find((r) => r.invoice_number === invoiceNumber);
  if (!row) return;

  const res = await fetch("/api/reminder", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(row),
  });
  const data = await res.json();
  document.getElementById("reminder-output").textContent = data.message;

  const riskContainer = document.getElementById("risk-badge-container");
  const risk = bundle.risk[row.customer];
  if (risk) {
    riskContainer.innerHTML = `<div class="risk-badge"><span class="risk-dot ${risk.risk_level}"></span> ${risk.risk_level} risk — ${risk.summary}</div>`;
  } else {
    riskContainer.innerHTML = "";
  }

  const planSection = document.getElementById("payment-plan-section");
  if (row.tier === "firm" || row.tier === "urgent") {
    planSection.style.display = "block";
    fetchPaymentPlan();
  } else {
    planSection.style.display = "none";
  }
}

async function fetchPaymentPlan() {
  const invoiceNumber = document.getElementById("invoice-select").value;
  const row = bundle.overdue.find((r) => r.invoice_number === invoiceNumber);
  if (!row) return;
  const installments = parseInt(document.getElementById("installments-slider").value, 10);

  const res = await fetch("/api/payment-plan", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...row, num_installments: installments }),
  });
  const data = await res.json();
  document.getElementById("payment-plan-output").textContent = data.message;
}
