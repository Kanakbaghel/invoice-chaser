// ---------------- State ----------------
let bundle = null;
let uploadToken = null;
let activeTiers = new Set(["gentle", "polite_followup", "firm", "urgent"]);
let targetDateManuallySet = false;
let tierChart = null;
let forecastChart = null;
let tierThresholdChart = null;
let riskThresholdChart = null;
let priorityWeightChart = null;

const TIER_LABELS = { gentle: "Gentle", polite_followup: "Follow-up", firm: "Firm", urgent: "Urgent" };

const PAGE_PATHS = {
  "/": "home",
  "/invoices": "invoices",
  "/customer-risk": "customer-risk",
  "/ask-the-agent": "ask-the-agent",
  "/forecast": "forecast",
  "/reminders": "reminders",
};

// ---------------- Init ----------------
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  buildTierChips();
  attachListeners();
  attachAgentChat();
  attachNavigation();
  attachSidebar();
  showPage(currentPageFromPath(), {
    hash: window.location.hash.replace("#", ""),
    preserveScroll: true,
  });
  renderMethodologyCharts();
  loadSample();
});

function currentPageFromPath() {
  const path = (window.location.pathname || "/").replace(/\/+$/, "") || "/";
  return PAGE_PATHS[path] || "home";
}

function showPage(pageId, options = {}) {
  document.documentElement.setAttribute("data-page", pageId);
  document.documentElement.classList.remove("sidebar-open");
  updateSidebarActive(pageId);

  requestAnimationFrame(() => {
    if (pageId === "home" && bundle) {
      renderDashboard(bundle);
    } else if (pageId === "invoices") {
      renderMethodologyCharts();
      if (bundle) applyFilters();
    } else if (pageId === "forecast" && bundle) {
      renderForecastChart();
      updateForecastResult();
    } else if (pageId === "customer-risk" && bundle) {
      renderConcentration(bundle.concentration);
      renderRiskSummary(bundle.concentration);
    }

    if (options.hash) {
      const target = document.getElementById(options.hash);
      if (target) {
        target.scrollIntoView({ behavior: options.preserveScroll ? "auto" : "smooth" });
        return;
      }
    }

    if (!options.preserveScroll) {
      window.scrollTo(0, 0);
    }
  });
}

function updateSidebarActive(pageId) {
  document.querySelectorAll(".sidebar-nav a[data-nav]").forEach((link) => {
    const active = link.dataset.nav === pageId;
    link.classList.toggle("is-active", active);
    if (active) {
      link.setAttribute("aria-current", "page");
    } else {
      link.removeAttribute("aria-current");
    }
  });
}

function attachSidebar() {
  const toggle = document.getElementById("sidebar-toggle");
  const collapse = document.getElementById("sidebar-collapse");
  const backdrop = document.getElementById("sidebar-backdrop");
  const root = document.documentElement;

  if (toggle) {
    toggle.addEventListener("click", () => {
      root.classList.toggle("sidebar-open");
    });
  }

  if (collapse) {
    collapse.addEventListener("click", () => {
      if (window.matchMedia("(max-width: 860px)").matches) {
        root.classList.remove("sidebar-open");
        return;
      }
      const next = !root.classList.contains("sidebar-collapsed");
      root.classList.toggle("sidebar-collapsed", next);
      safeStorageSet("ic-sidebar", next ? "collapsed" : "expanded");
    });
  }

  if (backdrop) {
    backdrop.addEventListener("click", () => {
      root.classList.remove("sidebar-open");
    });
  }
}

function attachNavigation() {
  document.querySelectorAll("a[data-nav]").forEach((link) => {
    link.addEventListener("click", (event) => {
      if (event.defaultPrevented) return;
      if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
        return;
      }

      const href = link.getAttribute("href");
      if (!href || href.startsWith("http")) return;

      event.preventDefault();

      const url = new URL(href, window.location.origin);
      const path = url.pathname.replace(/\/+$/, "") || "/";
      const pageId = PAGE_PATHS[path] || "home";
      const hash = url.hash.replace("#", "");
      const next = `${path}${hash ? `#${hash}` : ""}`;
      const current = `${(window.location.pathname.replace(/\/+$/, "") || "/")}${window.location.hash}`;

      if (current !== next) {
        history.pushState({ page: pageId }, "", next);
      }

      showPage(pageId, { hash });
    });
  });

  window.addEventListener("popstate", () => {
    showPage(currentPageFromPath(), {
      hash: window.location.hash.replace("#", ""),
    });
  });
}

// ---------------- Agent chat (real Strands/Bedrock agent) ----------------
function attachAgentChat() {
  const btn = document.getElementById("agent-ask-btn");
  const input = document.getElementById("agent-question");
  const responseBox = document.getElementById("agent-chat-response");
  const log = document.getElementById("agent-chat-log");

  if (!btn || !input) return;

  const clearEmpty = () => {
    if (!log) return;
    const empty = log.querySelector(".chat-empty");
    if (empty) empty.remove();
  };

  const appendBubble = (role, text, extraClass) => {
    if (!log) return null;
    clearEmpty();
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble ${role}${extraClass ? ` ${extraClass}` : ""}`;
    bubble.textContent = text;
    log.appendChild(bubble);
    log.scrollTop = log.scrollHeight;
    return bubble;
  };

  const ask = async (preset) => {
    const question = (preset || input.value).trim();
    if (!question) return;

    input.value = "";
    appendBubble("user", question);
    const pending = appendBubble("agent", "Thinking…", "is-loading");
    if (responseBox) {
      responseBox.textContent = "Thinking…";
    }
    btn.disabled = true;

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });

      const data = await res.json();
      const text = data.answer || data.error || "No response from the agent.";
      const isError = !data.answer;
      if (pending) {
        pending.textContent = text;
        pending.classList.remove("is-loading");
        pending.classList.toggle("is-error", isError);
      }
      if (responseBox) responseBox.textContent = text;
    } catch (err) {
      const text = "Couldn't reach the agent. Try again in a moment.";
      if (pending) {
        pending.textContent = text;
        pending.classList.remove("is-loading");
        pending.classList.add("is-error");
      }
      if (responseBox) responseBox.textContent = text;
    } finally {
      btn.disabled = false;
      if (log) log.scrollTop = log.scrollHeight;
    }
  };

  btn.onclick = () => ask();
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") ask();
  });

  document.querySelectorAll("#suggested-questions [data-question]").forEach((chip) => {
    chip.addEventListener("click", () => ask(chip.getAttribute("data-question")));
  });
}

// ---------------- Theme (dark / light) ----------------
function initTheme() {
  const toggle = document.getElementById("theme-toggle");
  if (!toggle) return;

  const root = document.documentElement;

  const getPreferredTheme = () => {
    const saved = safeStorageGet("ic-theme");
    if (saved === "light" || saved === "dark") return saved;
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  };

  const applyTheme = (theme) => {
    root.setAttribute("data-theme", theme);
    toggle.setAttribute("aria-pressed", theme === "light" ? "true" : "false");
    toggle.setAttribute("aria-label", theme === "light" ? "Switch to dark mode" : "Switch to light mode");
    updateChartThemeColors();
  };

  // The inline <script> in <head> already set the initial attribute to avoid
  // a flash of the wrong theme — just sync state and wire the click handler.
  applyTheme(getPreferredTheme());

  toggle.addEventListener("click", () => {
    const next = root.getAttribute("data-theme") === "light" ? "dark" : "light";
    applyTheme(next);
    safeStorageSet("ic-theme", next);
  });

  // Follow the OS theme if the user hasn't explicitly chosen one yet.
  if (window.matchMedia) {
    window.matchMedia("(prefers-color-scheme: light)").addEventListener("change", (e) => {
      if (safeStorageGet("ic-theme")) return; // user has an explicit preference
      applyTheme(e.matches ? "light" : "dark");
    });
  }
}

function safeStorageGet(key) {
  try { return localStorage.getItem(key); } catch (e) { return null; }
}

function safeStorageSet(key, value) {
  try { localStorage.setItem(key, value); } catch (e) { /* ignore (private mode, etc.) */ }
}

// Re-draw charts so their gridlines/labels pick up the new theme colors.
function updateChartThemeColors() {
  renderMethodologyCharts();
  if (!bundle) return;
  applyFilters();
  renderForecastChart();
}

function getChartColors() {
  const styles = getComputedStyle(document.documentElement);
  const read = (name, fallback) => styles.getPropertyValue(name).trim() || fallback;
  return {
    text: read("--text-secondary", "#b6bbc8"),
    grid: read("--border", "rgba(255,255,255,0.08)"),
    gentle: read("--chart-gentle", "#86b38d"),
    followup: read("--chart-followup", "#d4a24e"),
    firm: read("--chart-firm", "#d4925a"),
    urgent: read("--chart-urgent", "#d97b7b"),
    best: read("--chart-best", "#d4a24e"),
    worst: read("--chart-worst", "#d97b7b"),
    amount: read("--chart-amount", "#8fa0bd"),
    risk: read("--chart-risk", "#c4b08a"),
  };
}

function buildTierChips() {
  const container = document.getElementById("tier-chips");
  if (!container) return;
  Object.keys(TIER_LABELS).forEach((tier) => {
    const chip = document.createElement("button");
    chip.className = `chip active ${tier}`;
    chip.textContent = TIER_LABELS[tier];
    chip.dataset.tier = tier;
    chip.onclick = () => {
      if (activeTiers.has(tier)) {
        activeTiers.delete(tier);
        chip.classList.remove("active");
      } else {
        activeTiers.add(tier);
        chip.classList.add("active");
      }
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
    const horizon = parseInt(e.target.value, 10);
    document.getElementById("horizon-value").textContent = `${horizon} days`;

    if (bundle && !targetDateManuallySet) {
      const asOf = new Date(bundle.as_of);
      const synced = new Date(asOf);
      synced.setDate(synced.getDate() + horizon);
      document.getElementById("target-date").value = synced.toISOString().slice(0, 10);
    }

    renderForecastChart();
    updateForecastResult();
    if (bundle) renderStats(bundle.summary);
  };

  document.getElementById("target-date").onchange = () => {
    targetDateManuallySet = true;
    updateForecastResult();
  };

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

// ---------------- Status banner (loading / error) ----------------
function showBanner(kind, message, retryFn) {
  const container = document.getElementById("status-banner-container");
  if (!container) return;

  const banner = document.createElement("div");
  banner.className = `status-banner ${kind}`;

  const icon = document.createElement("span");
  icon.className = "banner-icon";
  icon.textContent = kind === "error" ? "!" : "…";
  banner.appendChild(icon);

  const text = document.createElement("div");
  text.textContent = message;
  banner.appendChild(text);

  if (retryFn) {
    const btn = document.createElement("button");
    btn.className = "retry-btn";
    btn.type = "button";
    btn.textContent = "Retry";
    btn.onclick = retryFn;
    banner.appendChild(btn);
  }

  container.innerHTML = "";
  container.appendChild(banner);
}

function clearBanner() {
  const container = document.getElementById("status-banner-container");
  if (container) container.innerHTML = "";
}

function setStatsLoading(isLoading) {
  ["stat-open", "stat-overdue", "stat-outstanding", "stat-overdue-amount", "stat-forecast", "stat-atrisk"].forEach((id) => {
    const el = document.getElementById(id);
    if (!el) return;

    el.classList.toggle("is-loading", isLoading);

    if (isLoading) {
      el.textContent = "0000";
    }
  });
}

// ---------------- Data loading ----------------
async function loadSample() {
  const snapshot = document.getElementById("snapshot-date").value || "2013-03-01";

  setStatsLoading(true);
  showBanner("loading", "Analyzing invoices…");

  try {
    const res = await fetch(`/api/sample?snapshot=${snapshot}`);

    if (!res.ok) {
      throw new Error(`Server responded with ${res.status}`);
    }

    const data = await res.json();

    if (data.error) {
      throw new Error(data.error);
    }

    clearBanner();
    setBundle(data);
  } catch (err) {
    setStatsLoading(false);

    showBanner(
      "error",
      `Couldn't load the sample ledger. ${err.message || "The server didn't respond."}`,
      loadSample
    );
  }
}

async function handleFileSelect(e) {
  const file = e.target.files[0];
  if (!file) return;

  document.getElementById("file-drop-label").textContent = file.name;

  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch("/api/upload/columns", {
    method: "POST",
    body: formData,
  });

  const data = await res.json();

  if (data.error) {
    alert(data.error);
    return;
  }

  uploadToken = data.token;

  ["map-customer", "map-amount", "map-id", "map-due"].forEach((id) => {
    const sel = document.getElementById(id);
    sel.innerHTML = data.columns
      .map((c) => `<option value="${c}">${c}</option>`)
      .join("");
  });

  const paidSel = document.getElementById("map-paid");

  paidSel.innerHTML =
    `<option value="">(none — assume all unpaid)</option>` +
    data.columns
      .map((c) => `<option value="${c}">${c}</option>`)
      .join("");

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

  setStatsLoading(true);
  showBanner("loading", "Analyzing your invoices…");

  try {
    const res = await fetch("/api/upload/compute", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      throw new Error(`Server responded with ${res.status}`);
    }

    const data = await res.json();

    if (data.error) {
      throw new Error(data.error);
    }

    clearBanner();
    setBundle(data);
  } catch (err) {
    setStatsLoading(false);

    showBanner(
      "error",
      `Couldn't analyze that file. ${err.message || "The server didn't respond."}`,
      computeUpload
    );
  }
}

// ---------------- Rendering ----------------
function setBundle(data) {
  bundle = data;

  renderStats(data.summary);
  renderDashboard(data);
  renderHeroMock(data);
  applyFilters();
  renderActionPlan(data.action_plan);
  renderConcentration(data.concentration);
  renderRiskSummary(data.concentration);
  populateInvoiceSelect(data.overdue);

  const asOf = new Date(data.as_of);
  const horizon = parseInt(document.getElementById("horizon-slider").value, 10);

  const targetDefault = new Date(asOf);
  targetDefault.setDate(targetDefault.getDate() + horizon);

  document.getElementById("target-date").value =
    targetDefault.toISOString().slice(0, 10);

  targetDateManuallySet = false;

  renderForecastChart();
  updateForecastResult();

  const summaryEl = document.getElementById("agent-summary");

  if (summaryEl && data.impact) {
    summaryEl.textContent = data.impact.summary_text;
  }

  document.getElementById("reminder-output").textContent =
    "Select an invoice above to draft a reminder.";

  const planOutput = document.getElementById("payment-plan-output");
  if (planOutput) {
    planOutput.textContent =
      "Select a firm or urgent invoice to generate a payment-plan offer.";
  }

  const explainer = document.getElementById("decision-explainer");
  if (explainer) explainer.style.display = "none";
}

// The hero section has a small "Invoice Chaser Agent — LIVE" preview box.
// It ships with static placeholder numbers in the HTML; this wires it to
// the real bundle so it never shows stale figures or an "attention
// required" alert when nothing actually needs attention.
function renderHeroMock(data) {
  const heroBox = document.querySelector(".hero-dashboard");
  if (!heroBox) return;

  const s = data.summary || {};
  const totalOutstanding = Number(s.total_outstanding) || 0;
  const overdueAmount = Number(s.overdue_amount) || 0;

  const amountEl = heroBox.querySelector(".mini-amount");
  if (amountEl) amountEl.textContent = `₹${totalOutstanding.toFixed(2)}`;

  const statEls = heroBox.querySelectorAll(".mini-stats strong");
  if (statEls.length >= 3) {
    statEls[0].textContent = s.open_invoices ?? 0;
    statEls[1].textContent = s.overdue_invoices ?? 0;
    statEls[2].textContent = `₹${overdueAmount.toFixed(2)}`;
  }

  const progressEl = heroBox.querySelector(".mini-progress span");
  if (progressEl) {
    const pct = totalOutstanding > 0 ? Math.min(100, (overdueAmount / totalOutstanding) * 100) : 0;
    progressEl.style.width = `${pct.toFixed(0)}%`;
  }

  const alertBox = heroBox.querySelector(".mini-alert");
  if (alertBox) {
    const worst = (data.overdue && data.overdue[0]) || null;
    const needsAttention = worst && (worst.tier === "firm" || worst.tier === "urgent");

    if (needsAttention) {
      alertBox.style.display = "flex";
      const pEl = alertBox.querySelector("p");
      if (pEl) {
        pEl.textContent = `Invoice ${worst.invoice_number} is ${worst.days_overdue} days overdue.`;
      }
    } else {
      alertBox.style.display = "none";
    }
  }
}

function getExpectedCash(data) {
  const forecast = data && data.forecast;
  if (!forecast || !forecast.dates || !forecast.dates.length) return 0;

  const horizonEl = document.getElementById("horizon-slider");
  const horizon = parseInt(horizonEl && horizonEl.value ? horizonEl.value : "60", 10);
  const asOf = new Date(data.as_of);
  const cutoff = new Date(asOf);
  cutoff.setDate(cutoff.getDate() + horizon);

  let value = 0;
  forecast.dates.forEach((date, index) => {
    if (new Date(date) <= cutoff) {
      value = Number(forecast.best[index]) || 0;
    }
  });
  return value;
}

function countAtRiskCustomers(data) {
  const list = (data && data.concentration) || [];
  const notable = list.filter((item) => (item.concentration_flag || "Low") !== "Low");
  if (notable.length) return notable.length;

  return Object.values((data && data.risk) || {}).filter(
    (item) => item.risk_level === "High" || item.risk_level === "Medium"
  ).length;
}

function formatAsOf(dateValue) {
  if (!dateValue) return "";
  const date = new Date(dateValue);
  if (Number.isNaN(date.getTime())) return String(dateValue);
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function renderDashboard(data) {
  if (!data) return;

  const asOfText = data.as_of ? `As of ${formatAsOf(data.as_of)}` : "";
  const topbar = document.getElementById("topbar-as-of");
  const dashAsOf = document.getElementById("dash-as-of");
  if (topbar) topbar.textContent = asOfText || "Current ledger";
  if (dashAsOf) dashAsOf.textContent = asOfText;

  renderDashboardOverdue((data.overdue || []).slice(0, 5));
}

function renderDashboardOverdue(rows) {
  const tbody = document.getElementById("dash-overdue-body");
  const empty = document.getElementById("dash-overdue-empty");
  if (!tbody) return;

  tbody.innerHTML = "";
  if (empty) empty.style.display = rows.length ? "none" : "block";

  rows.forEach((row) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.customer}</td>
      <td>${row.invoice_number}</td>
      <td>₹${row.amount.toFixed(2)}</td>
      <td>${row.due_date}</td>
      <td>${row.days_overdue}</td>
      <td><span class="tier-badge ${row.tier}">${TIER_LABELS[row.tier] || row.tier}</span></td>
    `;
    tbody.appendChild(tr);
  });
}

function renderRiskSummary(list) {
  const totalEl = document.getElementById("risk-stat-total");
  const elevatedEl = document.getElementById("risk-stat-elevated");
  const largestEl = document.getElementById("risk-stat-largest");
  const largestName = document.getElementById("risk-stat-largest-name");
  if (!totalEl) return;

  const rows = list || [];
  const elevated = rows.filter((item) => (item.concentration_flag || "Low") !== "Low");
  const largest = [...rows].sort(
    (a, b) => (Number(b.pct_of_total_ar) || 0) - (Number(a.pct_of_total_ar) || 0)
  )[0];

  totalEl.textContent = rows.length;
  if (elevatedEl) elevatedEl.textContent = elevated.length;
  if (largestEl) {
    largestEl.textContent = largest ? `${Number(largest.pct_of_total_ar).toFixed(1)}%` : "—";
  }
  if (largestName) {
    largestName.textContent = largest ? largest.customer : "Of total outstanding";
  }
}

function renderStats(s) {
  const totalOutstanding = Number(s.total_outstanding) || 0;
  const overdueAmount = Number(s.overdue_amount) || 0;
  const expectedCash = bundle ? getExpectedCash(bundle) : 0;
  const atRisk = bundle ? countAtRiskCustomers(bundle) : 0;

  const statElements = {
    "stat-open": s.open_invoices ?? 0,
    "stat-overdue": s.overdue_invoices ?? 0,
    "stat-outstanding": `₹${totalOutstanding.toFixed(2)}`,
    "stat-overdue-amount": `₹${overdueAmount.toFixed(2)}`,
    "stat-forecast": `₹${expectedCash.toFixed(2)}`,
    "stat-atrisk": atRisk,
  };

  Object.entries(statElements).forEach(([id, value]) => {
    const el = document.getElementById(id);

    if (!el) return;

    // REQUIRED FIX:
    // Remove the loading/skeleton state once the real value is available.
    el.classList.remove("is-loading");

    // Display the actual value.
    el.textContent = value;
  });
}

function applyFilters() {
  if (!bundle) return;

  const searchEl = document.getElementById("search-input");
  const minEl = document.getElementById("amount-min");
  const maxEl = document.getElementById("amount-max");
  if (!searchEl || !minEl) return;

  const search = searchEl.value.toLowerCase();
  const min = parseFloat(minEl.value) || 0;

  const maxRaw = maxEl ? maxEl.value : "";
  const max = maxRaw ? parseFloat(maxRaw) : Infinity;

  const filtered = bundle.overdue.filter((row) =>
    row.customer.toLowerCase().includes(search) &&
    activeTiers.has(row.tier) &&
    row.amount >= min &&
    row.amount <= max
  );

  renderTable(filtered);
  renderTierChart(filtered);
}

function renderTable(rows) {
  const tbody = document.getElementById("invoice-table-body");
  if (!tbody) return;

  tbody.innerHTML = "";

  const empty = document.getElementById("table-empty");
  if (empty) empty.style.display = rows.length ? "none" : "block";

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
  const totals = {
    gentle: 0,
    polite_followup: 0,
    firm: 0,
    urgent: 0,
  };

  rows.forEach((r) => {
    totals[r.tier] += r.amount;
  });

  const ctx = document.getElementById("tier-chart");
  if (!ctx) return;

  const dataValues = Object.keys(TIER_LABELS).map((t) => totals[t]);

  const chartColors = getChartColors();
  const colors = [
    chartColors.gentle,
    chartColors.followup,
    chartColors.firm,
    chartColors.urgent,
  ];

  if (tierChart) {
    tierChart.destroy();
  }

  tierChart = new Chart(ctx, {
    type: "bar",

    data: {
      labels: Object.values(TIER_LABELS),

      datasets: [
        {
          data: dataValues,
          backgroundColor: colors,
          borderRadius: 4,
        },
      ],
    },

    options: {
      plugins: {
        legend: {
          display: false,
        },

        title: {
          display: true,
          text: "By urgency (₹)",
          color: chartColors.text,
        },
      },

      scales: {
        x: {
          ticks: {
            color: chartColors.text,
          },
          grid: {
            color: chartColors.grid,
          },
        },

        y: {
          beginAtZero: true,
          ticks: {
            color: chartColors.text,
          },
          grid: {
            color: chartColors.grid,
          },
        },
      },
    },
  });
}

function renderActionPlan(list) {
  const container = document.getElementById("action-plan-list");
  if (!container) return;

  container.innerHTML = "";

  if (!list.length) {
    container.innerHTML =
      `<div class="empty-state">No overdue invoices — nothing to chase!</div>`;
    return;
  }

  list.slice(0, 5).forEach((item, i) => {
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

function renderConcentration(list) {
  const container = document.getElementById("concentration-list");
  if (!container) return;

  container.innerHTML = "";

  if (!list || !list.length) {
    container.innerHTML =
      `<div class="empty-state">No concentration data available.</div>`;
    return;
  }

  const palette = getChartColors();
  const FLAG_COLORS = { High: palette.urgent, Medium: palette.followup, Low: palette.gentle };

  const sorted = [...list].sort(
    (a, b) => (Number(b.pct_of_total_ar) || 0) - (Number(a.pct_of_total_ar) || 0)
  );

  const notable = sorted.filter((item) => (item.concentration_flag || "Low") !== "Low");
  const low = sorted.filter((item) => (item.concentration_flag || "Low") === "Low");

  if (!notable.length) {
    container.innerHTML =
      `<div class="empty-state">No customer holds a concerning share of your outstanding AR right now.</div>`;
  }

  notable.forEach((item) => {
    const row = document.createElement("div");
    row.className = "concentration-row";

    const pct = Number(item.pct_of_total_ar) || 0;
    const flag = item.concentration_flag || "Low";
    const barColor = FLAG_COLORS[flag] || FLAG_COLORS.Low;

    row.innerHTML = `
      <div class="concentration-customer">
        <strong>${item.customer}</strong>
        <span>₹${Number(item.outstanding_amount).toFixed(2)}</span>
      </div>
      <div class="concentration-bar-wrapper">
        <div class="concentration-bar">
          <span style="width:${Math.min(pct, 100)}%; color:${barColor}"></span>
        </div>
        <span>${pct.toFixed(1)}%</span>
      </div>
      <span class="concentration-badge ${flag.toLowerCase()}">${flag}</span>
    `;

    container.appendChild(row);
  });

  if (low.length) {
    const collapsedRow = document.createElement("div");
    collapsedRow.className = "concentration-collapsed-row";
    collapsedRow.innerHTML = `
      <span class="label">${low.length} other customer${low.length === 1 ? "" : "s"}, each under 10% of total AR</span>
      <button type="button" class="toggle">view all</button>
    `;

    const grid = document.createElement("div");
    grid.className = "concentration-low-grid";
    grid.innerHTML = low
      .map(
        (item) => `
          <div class="concentration-low-item">
            <strong>${item.customer}</strong>
            <span>${(Number(item.pct_of_total_ar) || 0).toFixed(1)}%</span>
          </div>
        `
      )
      .join("");

    collapsedRow.addEventListener("click", () => {
      const isOpen = grid.classList.toggle("open");
      collapsedRow.querySelector(".toggle").textContent = isOpen ? "hide" : "view all";
    });

    container.appendChild(collapsedRow);
    container.appendChild(grid);
  }
}

function renderForecastChart() {
  if (!bundle) return;

  const horizon = parseInt(
    document.getElementById("horizon-slider").value,
    10
  );

  const asOf = new Date(bundle.as_of);

  const cutoff = new Date(asOf);
  cutoff.setDate(cutoff.getDate() + horizon);

  const dates = [];
  const best = [];
  const worst = [];

  bundle.forecast.dates.forEach((d, i) => {
    if (new Date(d) <= cutoff) {
      dates.push(d);
      best.push(bundle.forecast.best[i]);
      worst.push(bundle.forecast.worst[i]);
    }
  });

  const ctx = document.getElementById("forecast-chart");

  const chartColors = getChartColors();

  if (forecastChart) {
    forecastChart.destroy();
  }

  forecastChart = new Chart(ctx, {
    type: "line",

    data: {
      labels: dates,

      datasets: [
        {
          label: "Best case",
          data: best,
          borderColor: chartColors.best,
          backgroundColor: "rgba(212,162,78,0.14)",
          tension: 0.2,
          fill: true,
        },

        {
          label: "Worst case",
          data: worst,
          borderColor: chartColors.worst,
          backgroundColor: "rgba(217,123,123,0.12)",
          tension: 0.2,
          fill: true,
        },
      ],
    },

    options: {
      plugins: {
        legend: {
          position: "bottom",

          labels: {
            color: chartColors.text,
          },
        },
      },

      scales: {
        x: {
          ticks: {
            color: chartColors.text,
          },

          grid: {
            color: chartColors.grid,
          },
        },

        y: {
          ticks: {
            color: chartColors.text,
          },

          grid: {
            color: chartColors.grid,
          },
        },
      },
    },
  });
}

function updateForecastResult() {
  if (!bundle || !bundle.forecast.dates.length) {
    document.getElementById("forecast-result").textContent =
      "Not enough data to forecast yet.";
    return;
  }

  const targetDate = new Date(
    document.getElementById("target-date").value
  );

  const targetAmount =
    parseFloat(document.getElementById("target-amount").value) || 0;

  let bestVal = 0;
  let worstVal = 0;

  bundle.forecast.dates.forEach((d, i) => {
    if (new Date(d) <= targetDate) {
      bestVal = bundle.forecast.best[i];
      worstVal = bundle.forecast.worst[i];
    }
  });

  let msg =
    `Best case by then: ₹${bestVal.toFixed(2)} · Worst case: ₹${worstVal.toFixed(2)}`;

  if (targetAmount > 0) {
    if (worstVal >= targetAmount) {
      msg += " — Even worst case, you're covered. ✅";
    } else if (bestVal >= targetAmount) {
      msg +=
        " — Covered if clients pay roughly on time, not guaranteed. ⚠️";
    } else {
      msg += " — You may fall short of this amount by then. 🔴";
    }
  }

  document.getElementById("forecast-result").textContent = msg;
}

function populateInvoiceSelect(rows) {
  const sel = document.getElementById("invoice-select");

  sel.innerHTML =
    `<option value="">— choose an invoice —</option>` +
    rows
      .map(
        (r) =>
          `<option value="${r.invoice_number}">${r.invoice_number} — ${r.customer} (₹${r.amount.toFixed(2)})</option>`
      )
      .join("");
}

async function refreshReminder() {
  const invoiceNumber =
    document.getElementById("invoice-select").value;

  if (!invoiceNumber || !bundle) return;

  const row = bundle.overdue.find(
    (r) => r.invoice_number === invoiceNumber
  );

  if (!row) return;

  const res = await fetch("/api/reminder", {
    method: "POST",

    headers: {
      "Content-Type": "application/json",
    },

    body: JSON.stringify(row),
  });

  const data = await res.json();

  document.getElementById("reminder-output").textContent =
    data.message;
}

async function onInvoiceSelect() {
  const invoiceNumber =
    document.getElementById("invoice-select").value;

  if (!invoiceNumber) return;

  const row = bundle.overdue.find(
    (r) => r.invoice_number === invoiceNumber
  );

  if (!row) return;

  await refreshReminder();

  const riskContainer =
    document.getElementById("risk-badge-container");

  const risk = bundle.risk[row.customer];

  if (risk) {
    riskContainer.innerHTML = `
      <div class="risk-badge">
        <span class="risk-dot ${risk.risk_level}"></span>
        ${risk.risk_level} risk — ${risk.summary}
      </div>
    `;
  } else {
    riskContainer.innerHTML = "";
  }

  // ---- Decision Explainer: show the "why" behind tone, risk, and rank ----
  document.getElementById("decision-explainer").style.display =
    "block";

  document.getElementById("explain-tier").textContent =
    row.why;

  const riskRow =
    document.getElementById("explain-risk-row");

  if (risk) {
    document.getElementById("explain-risk").textContent =
      risk.why;

    riskRow.style.display = "flex";
  } else {
    riskRow.style.display = "none";
  }

  const priorityRow =
    document.getElementById("explain-priority-row");

  const planItem = bundle.action_plan.find(
    (p) => p.invoice_number === invoiceNumber
  );

  if (planItem) {
    document.getElementById("explain-priority").textContent =
      planItem.why;

    priorityRow.style.display = "flex";
  } else {
    priorityRow.style.display = "none";
  }

  const planSection =
    document.getElementById("payment-plan-section");

  if (planSection) planSection.style.display = "block";

  if (row.tier === "firm" || row.tier === "urgent") {
    fetchPaymentPlan();
  } else {
    const planOutput = document.getElementById("payment-plan-output");
    if (planOutput) {
      planOutput.textContent =
        "Payment plans are suggested for firm or urgent invoices.";
    }
  }
}

// ---------------- Methodology charts ----------------
// These visualize the actual constants the backend uses (data_loader.py's
// reminder_tier(), client_risk.py's _risk_level(), weekly_brief.py's score
// weights) — not sample-data-dependent, so they render once on load and
// again whenever the theme changes.
function renderMethodologyCharts() {
  if (typeof Chart === "undefined") return;

  const chartColors = getChartColors();

  const commonScales = {
    x: {
      ticks: {
        color: chartColors.text,
      },

      grid: {
        color: chartColors.grid,
      },
    },

    y: {
      ticks: {
        color: chartColors.text,
      },

      grid: {
        display: false,
      },
    },
  };

  const tierCtx =
    document.getElementById("chart-tier-thresholds");

  if (tierCtx) {
    if (tierThresholdChart) {
      tierThresholdChart.destroy();
    }

    tierThresholdChart = new Chart(tierCtx, {
      type: "bar",

      data: {
        labels: [
          "Gentle",
          "Follow-up",
          "Firm",
          "Urgent",
        ],

        datasets: [
          {
            data: [
              [0, 5],
              [6, 13],
              [14, 25],
              [26, 40],
            ],

            backgroundColor: [
              chartColors.gentle,
              chartColors.followup,
              chartColors.firm,
              chartColors.urgent,
            ],

            borderRadius: 4,
          },
        ],
      },

      options: {
        indexAxis: "y",

        plugins: {
          legend: {
            display: false,
          },
        },

        scales: {
          x: {
            ...commonScales.x,

            title: {
              display: true,
              text: "Days overdue",
              color: chartColors.text,
            },
          },

          y: commonScales.y,
        },
      },
    });
  }

  const riskCtx =
    document.getElementById("chart-risk-thresholds");

  if (riskCtx) {
    if (riskThresholdChart) {
      riskThresholdChart.destroy();
    }

    riskThresholdChart = new Chart(riskCtx, {
      type: "bar",

      data: {
        labels: [
          "Low",
          "Medium",
          "High",
        ],

        datasets: [
          {
            data: [
              [0, 2],
              [2, 10],
              [10, 20],
            ],

            backgroundColor: [
              chartColors.gentle,
              chartColors.followup,
              chartColors.urgent,
            ],

            borderRadius: 4,
          },
        ],
      },

      options: {
        indexAxis: "y",

        plugins: {
          legend: {
            display: false,
          },
        },

        scales: {
          x: {
            ...commonScales.x,

            title: {
              display: true,
              text: "Avg. days late (High is 10+)",
              color: chartColors.text,
            },
          },

          y: commonScales.y,
        },
      },
    });
  }

  const priorityCtx =
    document.getElementById("chart-priority-weights");

  if (priorityCtx) {
    if (priorityWeightChart) {
      priorityWeightChart.destroy();
    }

    priorityWeightChart = new Chart(priorityCtx, {
      type: "bar",

      data: {
        labels: [
          "Max points (of 10)",
        ],

        datasets: [
          {
            label: "Amount",
            data: [3],
            backgroundColor: chartColors.amount,
          },

          {
            label: "Urgency",
            data: [4],
            backgroundColor: chartColors.urgent,
          },

          {
            label: "Client risk",
            data: [3],
            backgroundColor: chartColors.risk,
          },
        ],
      },

      options: {
        indexAxis: "y",

        scales: {
          x: {
            ...commonScales.x,
            stacked: true,
            max: 10,
          },

          y: {
            ...commonScales.y,
            stacked: true,
          },
        },

        plugins: {
          legend: {
            position: "bottom",

            labels: {
              color: chartColors.text,
            },
          },
        },
      },
    });
  }
}

async function fetchPaymentPlan() {
  const invoiceNumber =
    document.getElementById("invoice-select").value;

  const row = bundle.overdue.find(
    (r) => r.invoice_number === invoiceNumber
  );

  if (!row) return;

  const installments = parseInt(
    document.getElementById("installments-slider").value,
    10
  );

  const res = await fetch("/api/payment-plan", {
    method: "POST",

    headers: {
      "Content-Type": "application/json",
    },

    body: JSON.stringify({
      ...row,
      num_installments: installments,
    }),
  });

  const data = await res.json();

  document.getElementById("payment-plan-output").textContent =
    data.message;
}
