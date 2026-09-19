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

function setReceipt(receipt) {
  const dl = document.getElementById("receipt-fields");
  dl.innerHTML = "";
  if (!receipt) return;
  const rows = [
    ["Claim", receipt.claim_display],
    ["Verdict", receipt.verdict],
    ["Support", receipt.support_strength],
    ["Challenge", receipt.challenge_strength],
    ["Quality", receipt.data_quality],
    ["Observed at", receipt.observed_at],
    ["Observations", receipt.observation_count],
    ["Support observations", receipt.support_observation_count],
    ["Challenge observations", receipt.challenge_observation_count],
    ["Chain", receipt.chain],
    ["Token", receipt.token_symbol || receipt.token_address],
    ["Fingerprint", receipt.evidence_fingerprint],
    ["Receipt id", receipt.receipt_id],
    ["Attribution", receipt.attribution],
  ];
  for (const [key, value] of rows) {
    const dt = document.createElement("dt");
    dt.textContent = key;
    const dd = document.createElement("dd");
    dd.textContent = value == null ? "—" : String(value);
    dl.append(dt, dd);
  }
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
    document.getElementById("claim-meta").textContent = [
      body.chain,
      body.token && (body.token.symbol || body.token.address),
      body.synthetic ? "synthetic docket" : "live Nansen observations",
    ]
      .filter(Boolean)
      .join(" · ");
    addItems("support-case", body.support_case);
    addItems("challenge-case", body.challenge_case);
    document.getElementById("support-score").textContent = body.support_strength;
    document.getElementById("challenge-score").textContent = body.challenge_strength;
    document.getElementById("m-support").textContent = body.support_strength;
    document.getElementById("m-challenge").textContent = body.challenge_strength;
    document.getElementById("m-quality").textContent = body.data_quality;
    document.getElementById("verdict").textContent = body.verdict;
    setReceipt(body.evidence_receipt);
    const warnings = document.getElementById("warnings");
    warnings.innerHTML = "";
    for (const warning of body.warnings || []) {
      const li = document.createElement("li");
      li.textContent = warning;
      warnings.appendChild(li);
    }
  } catch (err) {
    renderStages("COLLECT", ["CLAIM"], true);
    showError(err.message || "Network error talking to the local API.");
    document.getElementById("verdict").textContent = "UNREACHABLE";
  } finally {
    cta.disabled = false;
  }
});
