const STAGES = [
  "CLAIM",
  "COLLECT",
  "NORMALIZE",
  "SUPPORT",
  "CHALLENGE",
  "QUALITY",
  "ADJUDICATE",
  "RECEIPT",
];

const stagesEl = document.getElementById("stages");
const form = document.getElementById("verify-form");
const cta = document.getElementById("cta");
const errorEl = document.getElementById("error");

function renderStages(current, completed, failed) {
  stagesEl.innerHTML = "";
  for (const name of STAGES) {
    const li = document.createElement("li");
    li.textContent = name;
    if (failed && !completed.includes(name) && name === current) li.classList.add("fail");
    else if (completed.includes(name)) li.classList.add("done");
    else if (name === current) li.classList.add("active");
    stagesEl.appendChild(li);
  }
}

function clearList(id) {
  document.getElementById(id).innerHTML = "";
}

function addItems(listId, items) {
  const list = document.getElementById(listId);
  list.innerHTML = "";
  if (!items || items.length === 0) {
    const empty = document.createElement("li");
    empty.textContent = "No filings.";
    list.appendChild(empty);
    return;
  }
  for (const item of items) {
    const li = document.createElement("li");
    const title = document.createElement("strong");
    title.textContent = item.title;
    const body = document.createElement("span");
    body.textContent = item.body;
    li.append(title, body);
    list.appendChild(li);
  }
}

function shortenAddress(address) {
  const value = String(address || "").trim();
  if (value.length <= 14) return value;
  return `${value.slice(0, 6)}…${value.slice(-4)}`;
}

function tokenDisplay(token) {
  if (!token) return "";
  const symbol = String(token.symbol || "").trim();
  if (symbol) return symbol;
  const address = token.address || "";
  return address ? shortenAddress(address) : "";
}

function setClaimMeta({ chain, token, timeframe, synthetic }) {
  const meta = document.getElementById("claim-meta");
  meta.replaceChildren();

  const parts = [];
  if (chain) parts.push({ text: String(chain), emphasize: false });
  const label = tokenDisplay(token);
  if (label) parts.push({ text: label, emphasize: true });
  if (timeframe) parts.push({ text: String(timeframe), emphasize: false });
  parts.push({
    text: synthetic ? "synthetic docket" : "live Nansen observations",
    emphasize: false,
  });

  parts.forEach((part, index) => {
    if (index > 0) meta.append(" · ");
    if (part.emphasize) {
      const span = document.createElement("span");
      span.className = "token-emphasis";
      span.textContent = part.text;
      meta.append(span);
    } else {
      meta.append(part.text);
    }
  });
}

function displayValue(value) {
  return value == null || value === "" ? "—" : String(value);
}

function appendRow(dl, key, value, className) {
  const dt = document.createElement("dt");
  dt.textContent = key;
  const dd = document.createElement("dd");
  dd.textContent = displayValue(value);
  if (className) dd.className = className;
  dl.append(dt, dd);
}

function appendGroup(parent, title) {
  const section = document.createElement("section");
  section.className = "receipt-group";
  const heading = document.createElement("h3");
  heading.textContent = title;
  const dl = document.createElement("dl");
  dl.className = "receipt-rows";
  section.append(heading, dl);
  parent.append(section);
  return { section, dl };
}

function isExchangeCountWarning(warning) {
  const text = String(warning);
  return (
    text === "TGM_EXCHANGE_WALLET_COUNT_ALWAYS_ZERO" ||
    text === "TGM_PROVIDER:exchange_wallet_count is always 0 (not tracked), even when exchange net flow is non-zero." ||
    (text.startsWith("TGM_PROVIDER:") && /exchange_wallet_count/i.test(text))
  );
}

function isFreshCountWarning(warning) {
  const text = String(warning);
  return (
    text === "TGM_FRESH_WALLET_COUNT_ALWAYS_ZERO" ||
    text === "TGM_PROVIDER:fresh_wallets_wallet_count is always 0 (not tracked), even when fresh-wallet net flow is non-zero." ||
    (text.startsWith("TGM_PROVIDER:") && /fresh_wallets_wallet_count/i.test(text))
  );
}

function setWarnings(rawWarnings) {
  const root = document.getElementById("warnings");
  root.replaceChildren();
  const warnings = (rawWarnings || []).map((item) => String(item)).filter(Boolean);
  if (warnings.length === 0) return;

  const notes = [];
  if (warnings.some(isExchangeCountWarning)) {
    notes.push("Exchange wallet counts are unavailable for this observation.");
  }
  if (warnings.some(isFreshCountWarning)) {
    notes.push("Fresh-wallet counts are unavailable for this observation.");
  }
  for (const warning of warnings) {
    if (isExchangeCountWarning(warning) || isFreshCountWarning(warning)) continue;
    notes.push(warning);
  }

  const heading = document.createElement("h3");
  heading.textContent = "Data notes";
  const list = document.createElement("ul");
  list.className = "data-notes";
  for (const note of notes) {
    const li = document.createElement("li");
    li.textContent = note;
    list.append(li);
  }

  const details = document.createElement("details");
  const summary = document.createElement("summary");
  summary.textContent = "Technical details";
  const tech = document.createElement("ul");
  for (const warning of warnings) {
    const li = document.createElement("li");
    li.textContent = warning;
    tech.append(li);
  }
  details.append(summary, tech);
  root.append(heading, list, details);
}

function setReceipt(receipt) {
  const root = document.getElementById("receipt-fields");
  root.replaceChildren();
  if (!receipt) return;

  const decision = appendGroup(root, "Decision");
  appendRow(decision.dl, "Claim", receipt.claim_display, "receipt-claim");

  const verdictBlock = document.createElement("div");
  verdictBlock.className = "receipt-verdict";
  const verdictLabel = document.createElement("p");
  verdictLabel.className = "receipt-kicker";
  verdictLabel.textContent = "Verdict";
  const verdictValue = document.createElement("p");
  verdictValue.className = "receipt-verdict-stamp";
  verdictValue.textContent = displayValue(receipt.verdict);
  verdictBlock.append(verdictLabel, verdictValue);
  decision.section.append(verdictBlock);

  const ledger = document.createElement("dl");
  ledger.className = "receipt-ledger";
  const meterRows = [
    ["Support", receipt.support_strength, "receipt-ledger-support"],
    ["Challenge", receipt.challenge_strength, "receipt-ledger-challenge"],
    ["Quality", receipt.data_quality, "receipt-ledger-quality"],
  ];
  for (const [key, value, className] of meterRows) {
    const wrap = document.createElement("div");
    wrap.className = className;
    const dt = document.createElement("dt");
    dt.textContent = key;
    const dd = document.createElement("dd");
    dd.textContent = displayValue(value);
    wrap.append(dt, dd);
    ledger.append(wrap);
  }
  decision.section.append(ledger);

  const evidence = appendGroup(root, "Evidence");
  appendRow(evidence.dl, "Observed at", receipt.observed_at);
  appendRow(evidence.dl, "Observations", receipt.observation_count);
  appendRow(evidence.dl, "Support observations", receipt.support_observation_count);
  appendRow(evidence.dl, "Challenge observations", receipt.challenge_observation_count);

  const provenance = appendGroup(root, "Provenance");
  appendRow(provenance.dl, "Chain", receipt.chain, "receipt-secondary");
  appendRow(provenance.dl, "Token", receipt.token_symbol || receipt.token_address, "token-emphasis");
  if (receipt.tgm_timeframe) {
    appendRow(provenance.dl, "Timeframe", receipt.tgm_timeframe, "receipt-secondary");
  }
  appendRow(provenance.dl, "Fingerprint", receipt.evidence_fingerprint, "receipt-mono-muted");
  appendRow(provenance.dl, "Receipt ID", receipt.receipt_id, "receipt-mono-muted");
  appendRow(provenance.dl, "Attribution", receipt.attribution);
}

function apiBase() {
  // Judge-facing UI: same-origin by default. Dev override via window.SINGULANT_PROOF_API_BASE only.
  const configured = (window.SINGULANT_PROOF_API_BASE || "").trim().replace(/\/$/, "");
  if (configured) return configured;
  if (window.location.protocol === "file:") return "http://127.0.0.1:8000";
  return "";
}

function showError(message) {
  errorEl.hidden = false;
  errorEl.textContent = message;
}

function hideError() {
  errorEl.hidden = true;
  errorEl.textContent = "";
}

function resetDocket() {
  clearList("support-case");
  clearList("challenge-case");
  document.getElementById("support-score").textContent = "—";
  document.getElementById("challenge-score").textContent = "—";
  document.getElementById("m-support").textContent = "—";
  document.getElementById("m-challenge").textContent = "—";
  document.getElementById("m-quality").textContent = "—";
  document.getElementById("receipt-fields").innerHTML = "";
  document.getElementById("warnings").innerHTML = "";
  document.getElementById("claim-meta").textContent = "Awaiting docket.";
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideError();
  cta.disabled = true;
  resetDocket();
  renderStages("CLAIM", [], false);
  document.getElementById("verdict").textContent = "Examining…";

  const payload = {
    chain: document.getElementById("chain").value.trim(),
    token_address: document.getElementById("token").value.trim(),
    claim: "SMART_MONEY_IS_ACCUMULATING_THIS_TOKEN",
    timeframe: document.getElementById("timeframe").value,
    demo: false,
  };

  try {
    renderStages("COLLECT", ["CLAIM"], false);
    const response = await fetch(`${apiBase()}/v1/proof/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      renderStages("COLLECT", ["CLAIM"], true);
      const detail = body.detail || response.statusText;
      showError(typeof detail === "string" ? detail : JSON.stringify(detail));
      document.getElementById("verdict").textContent = "DOCKET REJECTED";
      return;
    }

    const completed = body.stages_completed || STAGES;
    renderStages("RECEIPT", completed, false);
    setClaimMeta({
      chain: body.chain,
      token: body.token,
      timeframe: body.timeframe || payload.timeframe,
      synthetic: body.synthetic,
    });
    addItems("support-case", body.support_case);
    addItems("challenge-case", body.challenge_case);
    document.getElementById("support-score").textContent = body.support_strength;
    document.getElementById("challenge-score").textContent = body.challenge_strength;
    document.getElementById("m-support").textContent = body.support_strength;
    document.getElementById("m-challenge").textContent = body.challenge_strength;
    document.getElementById("m-quality").textContent = body.data_quality;
    document.getElementById("verdict").textContent = body.verdict;
    setReceipt(body.evidence_receipt);
    setWarnings(body.warnings);
  } catch (err) {
    renderStages("COLLECT", ["CLAIM"], true);
    showError(err.message || "Network error talking to the local API.");
    document.getElementById("verdict").textContent = "UNREACHABLE";
  } finally {
    cta.disabled = false;
  }
});
