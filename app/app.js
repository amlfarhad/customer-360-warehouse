(() => {
  "use strict";

  const state = {
    data: null,
    view: "overview",
    accountId: null,
    queueLimit: 30,
    filters: {
      search: "",
      risk: "all",
      segment: "all",
      lifecycle: "all",
      sort: "risk",
    },
    actions: {},
    toastTimer: null,
  };

  const byId = (id) => document.getElementById(id);

  const escapeHTML = (value) =>
    String(value === null || value === undefined ? "" : value).replace(/[&<>"']/g, (character) => {
      const entities = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;",
      };
      return entities[character];
    });

  const formatNumber = (value, maximumFractionDigits = 0) => {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
    const digits = Number.isFinite(Number(maximumFractionDigits)) ? Math.max(0, Math.min(20, Number(maximumFractionDigits))) : 0;
    return new Intl.NumberFormat("en-US", { maximumFractionDigits: digits }).format(Number(value));
  };

  const formatCurrency = (value, maximumFractionDigits = 0) => {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
    const digits = Number.isFinite(Number(maximumFractionDigits)) ? Math.max(0, Math.min(20, Number(maximumFractionDigits))) : 0;
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: digits,
    }).format(Number(value));
  };

  const formatPercent = (value, maximumFractionDigits = 0) => {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
    const digits = Number.isFinite(Number(maximumFractionDigits)) ? Math.max(0, Math.min(20, Number(maximumFractionDigits))) : 0;
    return new Intl.NumberFormat("en-US", {
      style: "percent",
      maximumFractionDigits: digits,
    }).format(Number(value));
  };

  const formatDate = (value) => {
    if (!value) return "—";
    const source = String(value);
    if (/^\d{4}-\d{2}$/.test(source)) {
      return new Intl.DateTimeFormat("en-US", { month: "short", year: "numeric" }).format(
        new Date(source + "-01T00:00:00Z"),
      );
    }
    const date = new Date(source);
    if (Number.isNaN(date.getTime())) return escapeHTML(source);
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    }).format(date);
  };

  const titleCase = (value) =>
    String(value || "—")
      .replace(/_/g, " ")
      .replace(/\b\w/g, (character) => character.toUpperCase());

  const riskLabel = (value) => {
    if (value === "already_churned") return "Already churned";
    return titleCase(value);
  };

  const riskClass = (value) => "risk-" + String(value || "low").toLowerCase();

  const statusClass = (value) => "status-" + String(value || "warn").toLowerCase();

  const signalClass = (value) => "signal-" + String(value || "heuristic").toLowerCase();

  const actionOptions = [
    "Review failed billing",
    "Follow up on support load",
    "Run an adoption check-in",
    "Confirm churn recovery plan",
    "Monitor next refresh",
  ];

  const defaultAction = (account) => {
    if (Number(account.failed_invoice_amount || 0) > 0) return "Review failed billing";
    if (String(account.lifecycle_stage) === "churned") return "Confirm churn recovery plan";
    if (Number(account.high_priority_tickets || 0) > 0) return "Follow up on support load";
    const median = segmentMedian(account.segment);
    if (Number(account.avg_daily_features || 0) < median) return "Run an adoption check-in";
    return "Monitor next refresh";
  };

  const segmentMedian = (segment) => {
    if (!state.data || !Array.isArray(state.data.queue)) return 0;
    const values = state.data.queue
      .filter((row) => row.segment === segment)
      .map((row) => Number(row.avg_daily_features || 0))
      .sort((left, right) => left - right);
    if (!values.length) return 0;
    const middle = Math.floor(values.length / 2);
    return values.length % 2 ? values[middle] : (values[middle - 1] + values[middle]) / 2;
  };

  const qualitySummary = () => {
    const summary = state.data.quality.summary;
    return (
      summary.status +
      " · " +
      formatNumber(summary.failed) +
      " failed · " +
      formatNumber(summary.warnings) +
      " warnings"
    );
  };

  const metricCard = (label, value, note, className = "") =>
    '<article class="metric-card ' +
    className +
    '"><div class="metric-label"><span>' +
    escapeHTML(label) +
    '</span></div><strong class="metric-value">' +
    value +
    '</strong><span class="metric-note">' +
    escapeHTML(note) +
    "</span></article>";

  const qualityStrip = () => {
    const summary = state.data.quality.summary;
    const className = summary.status === "pass" ? "quality-strip--pass" : "quality-strip--fail";
    return (
      '<div class="quality-strip ' +
      className +
      '" role="status"><div class="quality-strip-copy"><strong>Data quality: ' +
      escapeHTML(String(summary.status).toUpperCase()) +
      "</strong><span>" +
      formatNumber(summary.failed) +
      " critical issue(s) and " +
      formatNumber(summary.warnings) +
      " warning(s) remain visible in the audit.</span></div><a class=\"button button-quiet button-small\" href=\"#definitions\">Inspect audit ↗</a></div>"
    );
  };

  const renderSegmentSnapshot = () => {
    const rows = state.data.segments || [];
    if (!rows.length) return '<div class="empty-state"><div><strong>No segment data</strong><span>There are no modeled segments in this payload.</span></div></div>';
    return (
      '<div class="segment-table" role="table" aria-label="Segment snapshot"><div class="segment-row" role="row"><strong class="segment-name">Segment</strong><span>Accounts</span><span>Risk</span><span>Revenue</span></div>' +
      rows
        .map(
          (row) =>
            '<div class="segment-row" role="row"><strong class="segment-name">' +
            escapeHTML(titleCase(row.segment)) +
            "</strong><span>" +
            formatNumber(row.accounts) +
            "</span><span>" +
            formatNumber(row.average_churn_risk, 1) +
            "</span><span>" +
            formatCurrency(row.recognized_revenue) +
            "</span></div>",
        )
        .join("") +
      "</div>"
    );
  };

  const renderAdoptionPanel = () => {
    const grouped = {};
    (state.data.adoption || []).forEach((row) => {
      const key = String(row.event_name);
      if (!grouped[key] || Number(row.adoption_rate || 0) > Number(grouped[key].adoption_rate || 0)) {
        grouped[key] = row;
      }
    });
    const rows = Object.values(grouped)
      .sort((left, right) => Number(right.adoption_rate || 0) - Number(left.adoption_rate || 0))
      .slice(0, 7);
    if (!rows.length) return '<div class="empty-state"><div><strong>No adoption data</strong><span>The product event mart is empty.</span></div></div>';
    return (
      '<div class="bar-list" aria-label="Top feature adoption rates">' +
      rows
        .map(
          (row) =>
            '<div class="bar-item"><span class="bar-label">' +
            escapeHTML(titleCase(row.event_name)) +
            '<small class="cell-note">' +
            escapeHTML(titleCase(row.segment)) +
            "</small></span><span class=\"bar-track\"><span style=\"width:" +
            Math.max(3, Math.min(100, Number(row.adoption_rate || 0) * 100)) +
            '%"></span></span><span class="bar-value">' +
            formatPercent(row.adoption_rate, 0) +
            "</span></div>",
        )
        .join("") +
      "</div>"
    );
  };

  const renderRetentionPanel = () => {
    const rows = (state.data.retention || []).slice(0, 8);
    if (!rows.length) return '<div class="empty-state"><div><strong>No retention data</strong><span>The revenue retention mart is empty.</span></div></div>';
    return (
      '<table class="mini-table"><thead><tr><th>Segment / plan</th><th>GRR</th><th>Revenue</th></tr></thead><tbody>' +
      rows
        .map(
          (row) =>
            "<tr><td><strong>" +
            escapeHTML(titleCase(row.segment)) +
            '<small class="cell-note">' +
            escapeHTML(row.plan ? titleCase(row.plan) : "No plan") +
            "</small></td><td>" +
            (row.gross_revenue_retention === null || row.gross_revenue_retention === undefined
              ? "n/a"
              : formatPercent(row.gross_revenue_retention, 1)) +
            "</td><td>" +
            formatCurrency(row.recognized_revenue) +
            "</td></tr>",
        )
        .join("") +
      "</tbody></table>"
    );
  };

  const filteredQueue = () => {
    const filters = state.filters;
    const query = filters.search.trim().toLowerCase();
    const rows = (state.data.queue || []).filter((row) => {
      const searchable = [row.account_name, row.account_id, row.industry, row.region].join(" ").toLowerCase();
      return (
        (!query || searchable.includes(query)) &&
        (filters.risk === "all" || row.churn_risk_band === filters.risk) &&
        (filters.segment === "all" || row.segment === filters.segment) &&
        (filters.lifecycle === "all" || row.lifecycle_stage === filters.lifecycle)
      );
    });
    const sorters = {
      risk: (left, right) =>
        Number(right.churn_risk_score || 0) - Number(left.churn_risk_score || 0) ||
        Number(right.recognized_revenue || 0) - Number(left.recognized_revenue || 0),
      revenue: (left, right) =>
        Number(right.recognized_revenue || 0) - Number(left.recognized_revenue || 0) ||
        Number(right.churn_risk_score || 0) - Number(left.churn_risk_score || 0),
      health: (left, right) =>
        Number(left.health_score || 0) - Number(right.health_score || 0) ||
        Number(right.churn_risk_score || 0) - Number(left.churn_risk_score || 0),
      support: (left, right) =>
        Number(right.high_priority_tickets || 0) - Number(left.high_priority_tickets || 0) ||
        Number(right.churn_risk_score || 0) - Number(left.churn_risk_score || 0),
    };
    return rows.sort(sorters[filters.sort] || sorters.risk);
  };

  const queueCountText = () => {
    const total = filteredQueue().length;
    const visible = Math.min(state.queueLimit, total);
    return visible < total ? "Showing " + formatNumber(visible) + " of " + formatNumber(total) : formatNumber(total) + " shown";
  };

  const queueRowsMarkup = () => {
    const rows = filteredQueue().slice(0, state.queueLimit);
    if (!rows.length) {
      return '<tr class="empty-row"><td colspan="5"><strong>No accounts match this view.</strong><span class="cell-note">Clear a filter or search another account.</span></td></tr>';
    }
    return rows
      .map((row) => {
        const health = Math.max(0, Math.min(100, Number(row.health_score || 0)));
        const risk = Math.max(0, Math.min(100, Number(row.churn_risk_score || 0)));
        return (
          '<tr class="queue-row" data-account-id="' +
          escapeHTML(row.account_id) +
          '" tabindex="0" aria-label="Open ' +
          escapeHTML(row.account_name) +
          '"><td><span class="account-name">' +
          escapeHTML(row.account_name) +
          '</span><span class="account-meta">' +
          escapeHTML(titleCase(row.segment)) +
          " · " +
          escapeHTML(row.region) +
          '</span></td><td><span class="reason-chip">' +
          escapeHTML(row.primary_reason) +
          '</span><span class="cell-note">' +
          escapeHTML(row.lifecycle_stage) +
          "</span></td><td><span class=\"risk-badge " +
          riskClass(row.churn_risk_band) +
          '">' +
          escapeHTML(riskLabel(row.churn_risk_band)) +
          '</span><span class="cell-note">' +
          formatNumber(risk, 1) +
          "/100</span></td><td><div class=\"score-cell\"><span class=\"score-number\">" +
          formatNumber(health, 1) +
          '</span><div class="meter ' +
          (health < 40 ? "meter-danger" : health > 70 ? "meter-positive" : "") +
          '"><span style="width:' +
          health +
          '%"></span></div></div></td><td class="number">' +
          formatCurrency(row.recognized_revenue) +
          "</td></tr>"
        );
      })
      .join("");
  };

  const queueFooterMarkup = () => {
    const total = filteredQueue().length;
    const visible = Math.min(state.queueLimit, total);
    return (
      '<div class="queue-footer"><span id="queue-caption">' +
      queueCountText() +
      '</span>' +
      (visible < total
        ? '<button class="button button-text button-small" data-action="show-more-queue">Show next 30 →</button>'
        : "") +
      "</div>"
    );
  };

  const overviewMarkup = () => {
    const kpis = state.data.kpis;
    const segmentOptions = [...new Set((state.data.queue || []).map((row) => row.segment))].sort();
    const lifecycleOptions = [...new Set((state.data.queue || []).map((row) => row.lifecycle_stage))].sort();
    return (
      '<section class="page-intro"><div><p class="eyebrow">Portfolio / attention queue</p><h1>Make the next customer-health decision visible.</h1><p class="lede">Start with the accounts that need attention, then open the evidence behind the signal. This workspace separates observed source facts from heuristic flags so an operator can choose the next action with context.</p></div><div class="page-actions"><button class="button button-primary" data-action="export-queue">Export queue ↓</button><a class="button button-quiet" href="https://github.com/amlfarhad/customer-analytics-warehouse" target="_blank" rel="noreferrer">Inspect pipeline ↗</a></div></section>' +
      qualityStrip() +
      '<section class="summary-grid" aria-label="Portfolio summary">' +
      metricCard("Accounts modeled", formatNumber(kpis.accounts), "Unique rows in mart_customer_health") +
      metricCard("Attention accounts", formatNumber(kpis.attention_accounts), "High or already-churned risk band") +
      metricCard("Recognized revenue", formatCurrency(kpis.recognized_revenue), "Paid, positive invoice records") +
      metricCard("Average health", formatNumber(kpis.average_health, 1) + "/100", "Existing rule-based score") +
      "</section>" +
      '<section class="workspace-grid"><article class="panel queue-panel"><div class="panel-header"><div><p class="eyebrow">Operator queue</p><h2 class="panel-title">Who needs a look?</h2><p class="panel-subtitle">Sorted by churn risk, then recognized revenue. Open a row to inspect drivers and records.</p></div><span class="queue-count" id="queue-count">' +
      queueCountText() +
      "</span></div>" +
      '<div class="queue-toolbar"><label class="field"><span class="sr-only">Search accounts</span><input id="queue-search" type="search" placeholder="Search account, region, or industry" value="' +
      escapeHTML(state.filters.search) +
      '"></label><label class="select-field"><span class="sr-only">Risk band</span><select id="queue-risk"><option value="all">All risk bands</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option><option value="already_churned">Already churned</option></select></label><label class="select-field"><span class="sr-only">Segment</span><select id="queue-segment"><option value="all">All segments</option>' +
      segmentOptions.map((value) => '<option value="' + escapeHTML(value) + '">' + escapeHTML(titleCase(value)) + "</option>").join("") +
      '</select></label><label class="select-field"><span class="sr-only">Lifecycle</span><select id="queue-lifecycle"><option value="all">All lifecycle stages</option>' +
      lifecycleOptions.map((value) => '<option value="' + escapeHTML(value) + '">' + escapeHTML(titleCase(value)) + "</option>").join("") +
      '</select></label><label class="select-field"><span class="sr-only">Sort queue</span><select id="queue-sort"><option value="risk">Sort: risk first</option><option value="revenue">Sort: revenue first</option><option value="health">Sort: lowest health</option><option value="support">Sort: support load</option></select></label><button class="button button-quiet button-small" data-action="clear-filters">Clear filters</button></div>' +
      '<div class="table-wrap"><table class="queue-table"><caption class="sr-only">Customer health attention queue</caption><thead><tr><th>Account</th><th>Primary signal</th><th>Risk</th><th>Health</th><th>Revenue</th></tr></thead><tbody id="queue-body">' +
      queueRowsMarkup() +
      "</tbody></table></div>" +
      queueFooterMarkup() +
      "</article>" +
      '<aside class="stack"><article class="panel panel-deep"><p class="eyebrow">Use this desk</p><h2>Facts first. Action second.</h2><div class="callout"><p>Every row combines modeled scores with the records that explain them. Start a conversation, billing review, or adoption check-in only after reading the evidence.</p></div><ul class="principle-list"><li>Observed facts come from CRM, billing, product, or support source records.</li><li>Heuristic flags are explicit rules, not probabilities or customer outcomes.</li><li>Saved next actions stay in this browser until you export them.</li></ul></article><article class="panel"><div class="panel-header"><div><p class="eyebrow">Segment snapshot</p><h2 class="panel-title">Where is exposure concentrated?</h2></div></div>' +
      renderSegmentSnapshot() +
      "</article></aside></section>" +
      '<section class="section-grid"><article class="panel"><div class="panel-header"><div><p class="eyebrow">Product adoption</p><h2 class="panel-title">Which features show up in the source events?</h2><p class="panel-subtitle">Highest adoption rate by feature across the modeled segments.</p></div></div>' +
      renderAdoptionPanel() +
      '</article><article class="panel"><div class="panel-header"><div><p class="eyebrow">Revenue retention</p><h2 class="panel-title">How does retention compare?</h2><p class="panel-subtitle">Gross revenue retention by segment and plan from the existing mart.</p></div></div>' +
      renderRetentionPanel() +
      "</article></section>"
    );
  };

  const driverCard = (icon, title, headline, body, source, alert) =>
    '<article class="driver-card ' +
    (alert ? "driver-card--alert" : "driver-card--clear") +
    '"><div class="driver-topline"><span class="driver-icon" aria-hidden="true">' +
    icon +
    '</span><span class="signal-badge ' +
    (alert ? "signal-heuristic" : "signal-observed") +
    '">' +
    (alert ? "Review" : "No exception") +
    '</span></div><h3>' +
    escapeHTML(title) +
    "</h3><p><strong>" +
    escapeHTML(headline) +
    "</strong><br>" +
    escapeHTML(body) +
    '</p><span class="driver-source">' +
    escapeHTML(source) +
    "</span></article>";

  const renderDrivers = (account) => {
    const failed = Number(account.failed_invoice_amount || 0);
    const highPriority = Number(account.high_priority_tickets || 0);
    const events = Number(account.total_events || 0);
    const featureVariety = Number(account.avg_daily_features || 0);
    const median = segmentMedian(account.segment);
    const adoptionGap = featureVariety < median;
    const churned = String(account.lifecycle_stage) === "churned";
    return (
      '<div class="driver-grid">' +
      driverCard(
        "$",
        "Billing",
        failed > 0 ? formatCurrency(failed) + " failed amount" : "No failed invoice amount",
        failed > 0 ? "Inspect invoice records before a collections or renewal motion." : "No failed invoice amount is present in the current account mart.",
        "fct_subscription_revenue",
        failed > 0,
      ) +
      driverCard(
        "↗",
        "Product activity",
        formatNumber(events) + " source events",
        adoptionGap
          ? formatNumber(featureVariety, 1) + " average daily features, below the " + formatNumber(median, 1) + " segment median."
          : formatNumber(featureVariety, 1) + " average daily features, at or above the segment median.",
        "fct_product_usage_daily",
        adoptionGap,
      ) +
      driverCard(
        "!",
        "Support",
        formatNumber(highPriority) + " high-priority ticket(s)",
        highPriority > 0
          ? "High or urgent support records are visible for follow-up."
          : "No high or urgent support records are present in the current fact table.",
        "fct_support_tickets",
        highPriority > 0,
      ) +
      driverCard(
        "◇",
        "Lifecycle",
        churned ? "CRM stage: churned" : "CRM stage: " + titleCase(account.lifecycle_stage),
        churned
          ? "This is a recovery or closed-loop review, not a forward-looking prediction."
          : "Lifecycle is an observed CRM attribute used in the existing score formula.",
        "dim_accounts",
        churned,
      ) +
      "</div>"
    );
  };

  const trendBlock = (title, rows, valueKey, formatter, description) => {
    const ordered = (rows || []).slice().sort((left, right) => String(left.month).localeCompare(String(right.month)));
    if (!ordered.length) {
      return '<div class="trend-block"><div class="trend-title"><span>' + escapeHTML(title) + '</span></div><div class="empty-state"><div><strong>No trend rows</strong><span>There are no records for this source.</span></div></div></div>';
    }
    const values = ordered.map((row) => Number(row[valueKey] || 0));
    const max = Math.max(...values, 0);
    const bars = ordered
      .map((row) => {
        const value = Number(row[valueKey] || 0);
        const height = max > 0 ? Math.max(8, (value / max) * 100) : 5;
        return '<span class="trend-bar" style="--bar-height:' + height + '%" data-value="' + escapeHTML(formatter(value)) + '" title="' + escapeHTML(formatDate(row.month) + ": " + formatter(value)) + '"></span>';
      })
      .join("");
    return (
      '<div class="trend-block"><div class="trend-title"><span>' +
      escapeHTML(title) +
      '</span><span>' +
      escapeHTML(description) +
      '</span></div><div class="bar-chart" role="img" aria-label="' +
      escapeHTML(title + " trend") +
      '">' +
      bars +
      '</div><div class="trend-axis">' +
      ordered
        .map((row) => "<span>" + escapeHTML(formatDate(row.month)) + "</span>")
        .join("") +
      "</div></div>"
    );
  };

  const renderSignalPanel = (title, badge, body, items) => {
    const list = items.length
      ? "<ul>" +
        items
          .map(
            (item) =>
              "<li><strong>" +
              escapeHTML(item.label) +
              "</strong><span>" +
              escapeHTML(item.detail) +
              "</span></li>",
          )
          .join("") +
        "</ul>"
      : '<div class="model-empty"><p>No signals are recorded in this classification for this account.</p></div>';
    return (
      '<article class="signal-panel"><span class="signal-badge ' +
      signalClass(badge.type) +
      '">' +
      escapeHTML(badge.label) +
      "</span><h3>" +
      escapeHTML(title) +
      "</h3><p>" +
      escapeHTML(body) +
      "</p>" +
      list +
      "</article>"
    );
  };

  const recordTable = (title, source, rows, columns) => {
    const safeRows = Array.isArray(rows) ? rows : [];
    if (!safeRows.length) {
      return '<section class="record-section"><div class="panel-header"><div><h3 class="panel-title">' + escapeHTML(title) + '</h3><p class="panel-subtitle">' + escapeHTML(source) + '</p></div></div><div class="empty-state"><div><strong>No source records</strong><span>This account has no rows in this source table.</span></div></div></section>';
    }
    return (
      '<section class="record-section"><div class="panel-header"><div><h3 class="panel-title">' +
      escapeHTML(title) +
      '</h3><p class="panel-subtitle">' +
      escapeHTML(source) +
      " · " +
      formatNumber(safeRows.length) +
      " recent row(s)</p></div></div><div class=\"record-table-wrap\"><table class=\"record-table\"><caption class=\"sr-only\">" +
      escapeHTML(title) +
      '</caption><thead><tr>' +
      columns.map((column) => "<th>" + escapeHTML(column.label) + "</th>").join("") +
      "</tr></thead><tbody>" +
      safeRows
        .map(
          (row) =>
            "<tr>" +
            columns
              .map((column) => {
                const value = row[column.key];
                const display = column.format ? column.format(value, row) : value;
                return '<td class="' + (column.number ? "number" : "") + '">' + escapeHTML(display) + "</td>";
              })
              .join("") +
            "</tr>",
        )
        .join("") +
      "</tbody></table></div></section>"
    );
  };

  const renderDetail = (accountId) => {
    const detail = state.data.accounts[String(accountId)];
    if (!detail) {
      state.view = "overview";
      return overviewMarkup();
    }
    const account = detail.account;
    const action = state.actions[String(accountId)] || defaultAction(account);
    const observed = [
      {
        label: "CRM lifecycle",
        detail: titleCase(account.lifecycle_stage) + " · " + titleCase(account.segment) + " · " + account.region,
      },
      {
        label: "Recognized revenue",
        detail: formatCurrency(account.recognized_revenue) + " from paid, positive invoice records.",
      },
      {
        label: "Product events",
        detail: formatNumber(account.total_events) + " event rows in the product source.",
      },
      {
        label: "Support records",
        detail: formatNumber(account.support_tickets) + " tickets · " + formatNumber(account.high_priority_tickets) + " high priority.",
      },
    ];
    const heuristics = (account.attention_reasons || []).filter((reason) => reason.type === "heuristic");
    return (
      '<button class="button button-text detail-back" data-action="back-to-queue">← Back to queue</button><section class="detail-heading"><div><p class="eyebrow">Account investigation / ' +
      escapeHTML(account.account_id) +
      '</p><h1>' +
      escapeHTML(account.account_name) +
      '</h1><div class="detail-meta"><span class="risk-badge ' +
      riskClass(account.churn_risk_band) +
      '">' +
      escapeHTML(riskLabel(account.churn_risk_band)) +
      '</span><span class="lifecycle-badge">' +
      escapeHTML(titleCase(account.lifecycle_stage)) +
      "</span><span>" +
      escapeHTML(titleCase(account.industry)) +
      " · " +
      escapeHTML(account.region) +
      " · " +
      escapeHTML(account.plan || "No plan") +
      "</span></div></div><div class=\"detail-actions\"><div class=\"action-control\"><label for=\"action-select\">Recommended next action</label><select id=\"action-select\" class=\"action-select\">" +
      actionOptions
        .map((option) => '<option value="' + escapeHTML(option) + '"' + (option === action ? " selected" : "") + ">" + escapeHTML(option) + "</option>")
        .join("") +
      '</select></div><button class="button button-primary" data-action="save-action">Save action</button><button class="button button-quiet" data-action="export-account">Export brief ↓</button></div></section>' +
      '<section class="detail-metrics" aria-label="Account metrics">' +
      metricCard("Health", formatNumber(account.health_score, 1) + "/100", "Heuristic score") +
      metricCard("Churn risk", formatNumber(account.churn_risk_score, 1) + "/100", riskLabel(account.churn_risk_band)) +
      metricCard("Revenue", formatCurrency(account.recognized_revenue), "Recognized invoices") +
      metricCard("Feature variety", formatNumber(account.avg_daily_features, 1), "Average per active day") +
      metricCard("Priority tickets", formatNumber(account.high_priority_tickets), "High or urgent") +
      "</section>" +
      '<section class="detail-layout"><article class="panel"><div class="panel-header"><div><p class="eyebrow">Diagnosis</p><h2>Why this account is in view</h2><p class="panel-subtitle">Driver cards use observed source facts and make the rule-based flags explicit.</p></div></div>' +
      renderDrivers(account) +
      '</article><aside class="panel"><p class="eyebrow">Decision note</p><h2>Keep the evidence attached.</h2><div class="callout"><p>Use the selected action as an operator note. It is saved locally and included in exports; it is not written back to a CRM.</p></div><ul class="principle-list"><li>Billing rows show the amount and status used by the revenue mart.</li><li>Product rows show the event names behind feature variety.</li><li>Support rows show category, priority, and resolution time.</li></ul></aside></section>' +
      '<section class="panel" style="margin-bottom:18px"><div class="panel-header"><div><p class="eyebrow">Time trends</p><h2>What changed in the modeled records?</h2><p class="panel-subtitle">Monthly aggregates are generated from the existing fact tables. Hover bars for values.</p></div></div><div class="trend-grid">' +
      trendBlock("Product events", detail.trends.usage, "events", (value) => formatNumber(value), "events") +
      trendBlock("Recognized revenue", detail.trends.revenue, "recognized_revenue", (value) => formatCurrency(value), "USD") +
      trendBlock("Support tickets", detail.trends.support, "tickets", (value) => formatNumber(value), "tickets") +
      "</div></section>" +
      '<section class="signal-grid">' +
      renderSignalPanel("Observed facts", { label: "Observed", type: "observed" }, "Directly present in the source or modeled fact records.", observed) +
      renderSignalPanel("Heuristic flags", { label: "Heuristic", type: "heuristic" }, "Explicit rules used to help sort attention; not probabilities.", heuristics) +
      '<article class="signal-panel"><span class="signal-badge signal-heuristic">Model-derived</span><h3>No model signal</h3><p>The current repository does not contain an ML model or validated probability. Do not read the heuristic scores as predicted customer outcomes.</p><div class="model-empty"><p>Model-derived signals: none in this demo pipeline.</p></div></article>' +
      "</section>" +
      '<section class="panel records-grid"><div>' +
      recordTable("CRM account record", "dim_accounts · deduplicated in staging", detail.records.crm, [
        { label: "Account ID", key: "account_id" },
        { label: "Name", key: "account_name" },
        { label: "Industry", key: "industry" },
        { label: "Region", key: "region" },
        { label: "Lifecycle", key: "lifecycle_stage" },
      ]) +
      recordTable("Subscription context", "dim_customers", detail.records.customer, [
        { label: "Plan", key: "plan" },
        { label: "Status", key: "subscription_status" },
        { label: "Customer since", key: "customer_since", format: formatDate },
        { label: "Segment", key: "segment" },
      ]) +
      "</div><div>" +
      recordTable("Billing invoice records", "fct_subscription_revenue · recent rows", detail.records.invoices, [
        { label: "Invoice date", key: "invoice_date", format: formatDate },
        { label: "Status", key: "status" },
        { label: "Amount", key: "amount", format: formatCurrency, number: true },
        { label: "Recognized", key: "recognized_revenue", format: formatCurrency, number: true },
      ]) +
      recordTable("Support records", "fct_support_tickets · recent rows", detail.records.support, [
        { label: "Date", key: "ticket_date", format: formatDate },
        { label: "Category", key: "category" },
        { label: "Priority", key: "priority" },
        { label: "Hours", key: "resolved_hours", format: (value) => formatNumber(value, 1), number: true },
      ]) +
      "</div></section>" +
      '<section class="panel"><div class="panel-header"><div><p class="eyebrow">Source records</p><h2>Additional evidence</h2><p class="panel-subtitle">Product events and pipeline rows are retained for investigation even when they do not drive the headline score.</p></div></div>' +
      recordTable("Product event records", "stg_product_events · recent rows", detail.records.product, [
        { label: "Event at", key: "event_at", format: formatDate },
        { label: "Event", key: "event_name", format: (value) => value || "null event name" },
        { label: "User role", key: "user_role" },
      ]) +
      recordTable("Pipeline opportunities", "fct_pipeline_opportunities · recent rows", detail.records.opportunities, [
        { label: "Stage", key: "stage" },
        { label: "Amount", key: "amount", format: formatCurrency, number: true },
        { label: "Created", key: "created_at", format: formatDate },
      ]) +
      "</section>"
    );
  };

  const renderQualityRows = () => {
    const checks = state.data.quality.checks || [];
    return checks
      .map(
        (check) =>
          '<div class="quality-row"><i class="' +
          statusClass(check.status) +
          '" aria-hidden="true"></i><div><strong>' +
          escapeHTML(titleCase(check.name)) +
          "</strong><span>" +
          escapeHTML(check.detail) +
          "</span></div><em class=\"" +
          statusClass(check.status) +
          '">' +
          escapeHTML(check.status) +
          "</em></div>",
      )
      .join("");
  };

  const renderDefinitions = () => {
    const metrics = state.data.metric_dictionary || [];
    const coverage = state.data.source_coverage || [];
    const lineage = state.data.lineage || [];
    const summary = state.data.quality.summary;
    return (
      '<section class="page-intro"><div><p class="eyebrow">Trust layer / definitions</p><h1>Know what the signal means before you act.</h1><p class="lede">The source pipeline is intentionally transparent. This page keeps the metric dictionary, lineage, audit results, and demo limitations beside the workflow.</p></div><div class="page-actions"><a class="button button-primary" href="https://github.com/amlfarhad/customer-analytics-warehouse/blob/main/docs/data_model.md" target="_blank" rel="noreferrer">Read data model ↗</a></div></section>' +
      '<section class="quality-strip ' +
      (summary.status === "pass" ? "quality-strip--pass" : "quality-strip--fail") +
      '"><div class="quality-strip-copy"><strong>Quality audit: ' +
      escapeHTML(String(summary.status).toUpperCase()) +
      "</strong><span>" +
      escapeHTML(qualitySummary()) +
      "</span></div><span class=\"muted\">Refresh status is generated from src/run_quality_checks.py.</span></section>" +
      '<section class="definitions-grid"><article class="panel"><div class="panel-header"><div><p class="eyebrow">Metric dictionary</p><h2>Definitions with boundaries</h2><p class="panel-subtitle">Observed fields and heuristic scores are named separately so they are not accidentally overclaimed.</p></div></div><div class="definition-grid">' +
      metrics
        .map(
          (metric) =>
            '<article class="definition-card"><span class="signal-badge ' +
            signalClass(metric.classification) +
            '">' +
            escapeHTML(metric.classification) +
            '</span><h3>' +
            escapeHTML(metric.name) +
            "</h3><p>" +
            escapeHTML(metric.definition) +
            '</p><p class="caveat">' +
            escapeHTML(metric.caveat) +
            '</p><code class="definition-source">' +
            escapeHTML(metric.source) +
            "</code></article>",
        )
        .join("") +
      '</div></article><aside class="panel"><p class="eyebrow">Demo boundaries</p><h2>What this sample does not prove.</h2><ul class="limitations-list"><li>The data is synthetic and deterministic; it is not evidence of production use or customer outcomes.</li><li>Health and churn risk are rule-based heuristic scores, not ML predictions or validated probabilities.</li><li>Negative invoices, duplicate CRM inputs, null events, and date errors remain visible in the quality audit.</li><li>Saved actions are browser-local notes; the app does not write to a CRM, billing system, or support tool.</li></ul><a class="button button-quiet button-small" href="https://github.com/amlfarhad/customer-analytics-warehouse/blob/main/docs/quality_rules.md" target="_blank" rel="noreferrer">Read quality rules ↗</a></aside></section>' +
      '<section class="definitions-grid"><article class="panel"><div class="panel-header"><div><p class="eyebrow">Lineage</p><h2>From source record to decision signal</h2></div></div><div class="lineage-list">' +
      lineage
        .map(
          (item) =>
            '<div class="lineage-item"><strong>' +
            escapeHTML(item.signal) +
            '</strong><p><code>' +
            escapeHTML(item.source) +
            "</code>" +
            escapeHTML(item.logic) +
            "</p></div>",
        )
        .join("") +
      '</div></article><article class="panel"><div class="panel-header"><div><p class="eyebrow">Source coverage</p><h2>Refresh footprint</h2><p class="panel-subtitle">Row counts and observed coverage are read from the raw tables at export time.</p></div></div><div class="table-wrap"><table class="data-table coverage-table"><caption class="sr-only">Source coverage</caption><thead><tr><th>Source</th><th>Rows</th><th>Coverage</th></tr></thead><tbody>' +
      coverage
        .map(
          (row) =>
            "<tr><td><strong>" +
            escapeHTML(row.source) +
            '<small class="cell-note">' +
            escapeHTML(row.table) +
            "</small></td><td class=\"number\">" +
            formatNumber(row.row_count) +
            "</td><td>" +
            escapeHTML(formatDate(row.coverage_start)) +
            " → " +
            escapeHTML(formatDate(row.coverage_end)) +
            "</td></tr>",
        )
        .join("") +
      "</tbody></table></div></article></section>" +
      '<section class="definitions-grid"><article class="panel"><div class="panel-header"><div><p class="eyebrow">Data quality</p><h2>What should block confidence?</h2><p class="panel-subtitle">The audit intentionally keeps source anomalies visible instead of hiding them in the UI.</p></div></div><div class="quality-list">' +
      renderQualityRows() +
      '</div></article><article class="panel"><p class="eyebrow">Refresh contract</p><h2>Rebuild the evidence, then reload.</h2><p class="lede">The public sample is a static export. Re-run the repository demo command to regenerate source CSVs, DuckDB marts, the quality audit, and this JSON payload with the same seed.</p><code class="definition-source">python3 -m src.cli demo --workspace . --accounts 500 --seed 42</code></article></section>'
    );
  };

  const updateNav = () => {
    document.querySelectorAll("[data-nav]").forEach((link) => {
      const active = link.getAttribute("data-nav") === state.view;
      if (active) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    });
    document.title =
      state.view === "detail" && state.accountId
        ? "Account " + state.accountId + " / customer health"
        : state.view === "definitions"
          ? "Definitions & lineage / customer health"
          : "Customer health / decision workspace";
  };

  const render = () => {
    if (!state.data) return;
    const root = byId("view-root");
    if (!root) return;
    root.innerHTML =
      state.view === "detail" ? renderDetail(state.accountId) : state.view === "definitions" ? renderDefinitions() : overviewMarkup();
    updateNav();
  };

  const updateQueue = () => {
    const body = byId("queue-body");
    const count = byId("queue-count");
    const caption = byId("queue-caption");
    if (body) body.innerHTML = queueRowsMarkup();
    if (count) count.textContent = queueCountText();
    if (caption) caption.parentElement.outerHTML = queueFooterMarkup();
  };

  const setFiltersFromControls = () => {
    const search = byId("queue-search");
    const risk = byId("queue-risk");
    const segment = byId("queue-segment");
    const lifecycle = byId("queue-lifecycle");
    const sort = byId("queue-sort");
    if (search) state.filters.search = search.value;
    if (risk) state.filters.risk = risk.value;
    if (segment) state.filters.segment = segment.value;
    if (lifecycle) state.filters.lifecycle = lifecycle.value;
    if (sort) state.filters.sort = sort.value;
  };

  const clearFilters = () => {
    state.filters = { search: "", risk: "all", segment: "all", lifecycle: "all", sort: "risk" };
    state.queueLimit = 30;
    render();
  };

  const downloadFile = (filename, content, type) => {
    const blob = new Blob([content], { type: type || "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  const csvValue = (value) => {
    const text = value === null || value === undefined ? "" : String(value);
    return '"' + text.replace(/"/g, '""') + '"';
  };

  const exportQueue = () => {
    const rows = filteredQueue();
    const headers = ["account_id", "account_name", "segment", "region", "lifecycle_stage", "risk_band", "churn_risk_score", "health_score", "recognized_revenue", "primary_reason", "next_action"];
    const lines = [headers.map(csvValue).join(",")];
    rows.forEach((row) => {
      lines.push(
        [
          row.account_id,
          row.account_name,
          row.segment,
          row.region,
          row.lifecycle_stage,
          row.churn_risk_band,
          row.churn_risk_score,
          row.health_score,
          row.recognized_revenue,
          row.primary_reason,
          state.actions[String(row.account_id)] || defaultAction(row),
        ]
          .map(csvValue)
          .join(","),
      );
    });
    downloadFile("customer-health-queue.csv", lines.join("\n") + "\n", "text/csv;charset=utf-8");
    showToast(formatNumber(rows.length) + " queue row(s) exported.");
  };

  const exportAccount = () => {
    const detail = state.data.accounts[String(state.accountId)];
    if (!detail) return;
    const account = detail.account;
    const action = state.actions[String(state.accountId)] || defaultAction(account);
    const lines = [
      "CUSTOMER HEALTH ACCOUNT BRIEF",
      "",
      account.account_name + " · " + account.account_id,
      "Risk band: " + riskLabel(account.churn_risk_band) + " (" + formatNumber(account.churn_risk_score, 1) + "/100)",
      "Health score: " + formatNumber(account.health_score, 1) + "/100",
      "Segment: " + titleCase(account.segment) + " · " + account.region + " · " + titleCase(account.lifecycle_stage),
      "",
      "RECOMMENDED NEXT ACTION",
      action,
      "",
      "OBSERVED FACTS",
      ...[
        "Recognized revenue: " + formatCurrency(account.recognized_revenue),
        "Failed invoice amount: " + formatCurrency(account.failed_invoice_amount),
        "Product events: " + formatNumber(account.total_events),
        "Average daily feature variety: " + formatNumber(account.avg_daily_features, 1),
        "Support tickets: " + formatNumber(account.support_tickets) + " (" + formatNumber(account.high_priority_tickets) + " high priority)",
      ],
      "",
      "SOURCE NOTE",
      state.data.meta.source_note,
      state.data.meta.model_note,
    ];
    downloadFile("account-" + account.account_id + "-brief.txt", lines.join("\n") + "\n");
    showToast("Account brief exported.");
  };

  const saveAction = () => {
    const select = byId("action-select");
    if (!select || !state.accountId) return;
    state.actions[String(state.accountId)] = select.value;
    try {
      localStorage.setItem("customer-health-actions", JSON.stringify(state.actions));
    } catch (error) {
      showToast("Action selected for this session; browser storage is unavailable.");
      return;
    }
    showToast("Saved locally: " + select.value + ".");
  };

  const showToast = (message) => {
    const toast = byId("toast");
    if (!toast) return;
    toast.textContent = message;
    toast.hidden = false;
    window.clearTimeout(state.toastTimer);
    state.toastTimer = window.setTimeout(() => {
      toast.hidden = true;
    }, 3600);
  };

  const loadSavedActions = () => {
    try {
      const stored = localStorage.getItem("customer-health-actions");
      if (stored) state.actions = JSON.parse(stored) || {};
    } catch (error) {
      state.actions = {};
    }
  };

  const routeFromHash = () => {
    const hash = window.location.hash.replace(/^#/, "");
    if (hash === "definitions") {
      state.view = "definitions";
      state.accountId = null;
    } else if (hash.indexOf("account/") === 0) {
      state.view = "detail";
      state.accountId = hash.slice("account/".length);
    } else {
      state.view = "overview";
      state.accountId = null;
    }
    if (state.data) render();
  };

  const showLoadedWorkspace = () => {
    byId("loading-state").hidden = true;
    byId("error-state").hidden = true;
    byId("workspace").hidden = false;
  };

  const showLoadError = (message) => {
    byId("loading-state").hidden = true;
    byId("workspace").hidden = true;
    byId("error-state").hidden = false;
    byId("error-message").textContent = message;
  };

  const loadData = async () => {
    byId("loading-state").hidden = false;
    byId("error-state").hidden = true;
    byId("workspace").hidden = true;
    try {
      const response = await fetch("./data/workspace.json", { cache: "no-store" });
      if (!response.ok) throw new Error("HTTP " + response.status);
      const data = await response.json();
      if (!data || !Array.isArray(data.queue) || !data.kpis || !data.quality || !data.accounts) {
        throw new Error("The payload is missing required decision-workspace fields.");
      }
      state.data = data;
      loadSavedActions();
      routeFromHash();
      showLoadedWorkspace();
      render();
    } catch (error) {
      showLoadError(
        "The generated workspace data could not be read (" +
          (error && error.message ? error.message : "unknown error") +
          "). Re-run python3 -m src.cli demo --workspace . and reload.",
      );
    }
  };

  document.addEventListener("click", (event) => {
    const row = event.target.closest("[data-account-id]");
    if (row && row.classList.contains("queue-row")) {
      window.location.hash = "account/" + row.getAttribute("data-account-id");
      return;
    }
    const action = event.target.closest("[data-action]");
    if (!action) return;
    const name = action.getAttribute("data-action");
    if (name === "export-queue") exportQueue();
    if (name === "export-account") exportAccount();
    if (name === "save-action") saveAction();
    if (name === "clear-filters") clearFilters();
    if (name === "show-more-queue") {
      state.queueLimit += 30;
      updateQueue();
    }
    if (name === "back-to-queue") window.location.hash = "overview";
    if (name === "retry-load") loadData();
  });

  document.addEventListener("keydown", (event) => {
    const row = event.target.closest("[data-account-id]");
    if (row && row.classList.contains("queue-row") && (event.key === "Enter" || event.key === " ")) {
      event.preventDefault();
      window.location.hash = "account/" + row.getAttribute("data-account-id");
    }
  });

  document.addEventListener("input", (event) => {
    if (event.target && event.target.id === "queue-search") {
      setFiltersFromControls();
      updateQueue();
    }
  });

  document.addEventListener("change", (event) => {
    if (event.target && ["queue-risk", "queue-segment", "queue-lifecycle", "queue-sort"].includes(event.target.id)) {
      setFiltersFromControls();
      updateQueue();
    }
  });

  window.addEventListener("hashchange", routeFromHash);
  loadData();
})();
