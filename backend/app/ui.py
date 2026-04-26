from __future__ import annotations

from html import escape
from pathlib import Path

from fastapi.responses import HTMLResponse


def _default_project_path() -> str:
    repo_root = Path(__file__).resolve().parents[2]
    if repo_root.exists():
        return str(repo_root)
    return "/home/udot/PROJECTS/local-coding-agent"


def render_ui() -> HTMLResponse:
    default_project_path = escape(_default_project_path())
    html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Local Coding Agent</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #111317;
      --panel: #1a1f27;
      --panel-alt: #141922;
      --border: #2a3340;
      --text: #e6edf3;
      --muted: #99a7b8;
      --accent: #64c6ff;
      --accent-strong: #2d8cff;
      --warn: #ffb454;
      --danger: #ff7b72;
      --success: #7ee787;
      --shadow: 0 20px 40px rgba(0, 0, 0, 0.22);
      --radius: 18px;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(45, 140, 255, 0.15), transparent 28rem),
        radial-gradient(circle at top right, rgba(100, 198, 255, 0.1), transparent 24rem),
        linear-gradient(180deg, #0d1014 0%, var(--bg) 100%);
      color: var(--text);
      min-height: 100vh;
    }

    .page {
      max-width: 1400px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }

    .hero {
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 18px;
      margin-bottom: 18px;
    }

    .card {
      background: linear-gradient(180deg, rgba(255, 255, 255, 0.02), rgba(255, 255, 255, 0)), var(--panel);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 18px;
    }

    h1, h2, h3 {
      margin: 0 0 12px;
      line-height: 1.15;
    }

    h1 {
      font-size: clamp(2rem, 4vw, 3.2rem);
      letter-spacing: -0.04em;
    }

    h2 {
      font-size: 1.05rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
    }

    p, li, label, small {
      color: var(--muted);
    }

    .hero p {
      max-width: 60rem;
    }

    .safety-list {
      margin: 0;
      padding-left: 18px;
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(12, minmax(0, 1fr));
      gap: 18px;
    }

    .span-4 { grid-column: span 4; }
    .span-5 { grid-column: span 5; }
    .span-6 { grid-column: span 6; }
    .span-7 { grid-column: span 7; }
    .span-8 { grid-column: span 8; }
    .span-12 { grid-column: span 12; }

    .field {
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-bottom: 12px;
    }

    .row {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      align-items: center;
    }

    input, textarea, button {
      font: inherit;
    }

    input[type="text"],
    textarea {
      width: 100%;
      border: 1px solid var(--border);
      border-radius: 12px;
      background: var(--panel-alt);
      color: var(--text);
      padding: 12px 14px;
      outline: none;
    }

    input[type="text"]:focus,
    textarea:focus {
      border-color: var(--accent-strong);
      box-shadow: 0 0 0 3px rgba(45, 140, 255, 0.18);
    }

    textarea {
      min-height: 120px;
      resize: vertical;
    }

    button {
      border: 0;
      border-radius: 999px;
      padding: 10px 16px;
      background: linear-gradient(135deg, var(--accent-strong), var(--accent));
      color: #051018;
      font-weight: 700;
      cursor: pointer;
    }

    button.secondary {
      background: #253042;
      color: var(--text);
    }

    button.warn {
      background: #4a3420;
      color: #ffd8a8;
    }

    button:disabled {
      cursor: not-allowed;
      opacity: 0.7;
    }

    .checkbox {
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 10px 0 14px;
    }

    .output {
      margin-top: 14px;
      padding-top: 14px;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
    }

    .pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 10px;
      border-radius: 999px;
      background: #18212f;
      color: var(--text);
      font-size: 0.92rem;
      margin-right: 8px;
      margin-bottom: 8px;
    }

    .status-ok { color: var(--success); }
    .status-bad { color: var(--danger); }
    .status-warn { color: var(--warn); }

    pre {
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .mono-box {
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.92rem;
      line-height: 1.5;
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 14px;
      background: #0d1117;
      color: #d0d7de;
      padding: 14px;
      min-height: 120px;
      overflow: auto;
    }

    .proposal-list {
      display: grid;
      gap: 12px;
    }

    .proposal-item {
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 14px;
      padding: 14px;
      background: rgba(255, 255, 255, 0.02);
    }

    .proposal-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: flex-start;
      flex-wrap: wrap;
      margin-bottom: 10px;
    }

    .proposal-head strong {
      display: block;
      margin-bottom: 6px;
      word-break: break-all;
    }

    .meta-list {
      display: grid;
      gap: 8px;
      margin: 0;
    }

    .meta-list div {
      display: grid;
      grid-template-columns: 140px 1fr;
      gap: 8px;
      align-items: start;
    }

    .meta-list dt {
      color: var(--muted);
      font-weight: 600;
    }

    .meta-list dd {
      margin: 0;
    }

    .message {
      padding: 12px 14px;
      border-radius: 12px;
      margin-bottom: 12px;
      border: 1px solid rgba(255, 255, 255, 0.06);
      background: rgba(255, 255, 255, 0.03);
    }

    .message.error {
      border-color: rgba(255, 123, 114, 0.32);
      background: rgba(255, 123, 114, 0.08);
    }

    .message.success {
      border-color: rgba(126, 231, 135, 0.32);
      background: rgba(126, 231, 135, 0.08);
    }

    .muted {
      color: var(--muted);
    }

    @media (max-width: 1080px) {
      .hero,
      .grid {
        grid-template-columns: 1fr;
      }

      .span-4,
      .span-5,
      .span-6,
      .span-7,
      .span-8,
      .span-12 {
        grid-column: span 1;
      }
    }
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <div class="card">
        <h1>Local Coding Agent</h1>
        <p>A lightweight browser UI for the local backend. Ask repository questions, plan changes, inspect saved proposals, apply reviewed diffs, and run fixed-scope validation checks without a separate frontend app.</p>
      </div>
      <div class="card">
        <h2>Safety Notes</h2>
        <ul class="safety-list">
          <li>This tool can modify local files only when Apply is clicked.</li>
          <li>Review generated diffs before applying.</li>
          <li>Proposals with warnings should not be applied.</li>
        </ul>
      </div>
    </section>

    <section class="grid">
      <div class="card span-4">
        <h2>Backend Status</h2>
        <div id="backendStatus" class="message">Loading backend status...</div>
      </div>

      <div class="card span-8">
        <h2>Project Path</h2>
        <div class="field">
          <label for="projectPath">Project path used by ask and plan-change requests</label>
          <input id="projectPath" type="text" value="__DEFAULT_PROJECT_PATH__">
        </div>
      </div>

      <div class="card span-6">
        <h2>Ask Repository Question</h2>
        <div class="field">
          <label for="askQuestion">Question</label>
          <textarea id="askQuestion" placeholder="How is proposal apply wired into the backend?"></textarea>
        </div>
        <div class="field">
          <label for="askFiles">Files (comma-separated)</label>
          <input id="askFiles" type="text" value="backend/app/main.py, backend/app/repo/proposal_apply.py">
        </div>
        <div class="row">
          <button id="askButton">Ask</button>
        </div>
        <div class="output">
          <div id="askResult" class="message muted">Ask results will appear here.</div>
          <div class="meta-list">
            <div><dt>Context files</dt><dd id="askContextFiles" class="muted">None yet.</dd></div>
          </div>
        </div>
      </div>

      <div class="card span-6">
        <h2>Plan a Code Change</h2>
        <div class="field">
          <label for="planTask">Task</label>
          <textarea id="planTask" placeholder="Add a small endpoint after health that returns version metadata."></textarea>
        </div>
        <div class="field">
          <label for="planFiles">Files (comma-separated)</label>
          <input id="planFiles" type="text" value="backend/app/main.py">
        </div>
        <label class="checkbox">
          <input id="saveProposal" type="checkbox" checked>
          <span>Save proposal</span>
        </label>
        <div class="field">
          <label for="proposalName">Proposal name</label>
          <input id="proposalName" type="text" value="ui-created-proposal">
        </div>
        <div class="row">
          <button id="planButton">Plan Change</button>
        </div>
        <div class="output">
          <div id="planSummary" class="message muted">Plan-change results will appear here.</div>
          <dl class="meta-list">
            <div><dt>Target file</dt><dd id="planTargetFile" class="muted">None yet.</dd></div>
            <div><dt>Operation</dt><dd id="planOperation" class="muted">None yet.</dd></div>
            <div><dt>Anchor</dt><dd id="planAnchor" class="muted">None yet.</dd></div>
            <div><dt>Warnings</dt><dd id="planWarnings" class="muted">None.</dd></div>
            <div><dt>Safety notes</dt><dd id="planSafetyNotes" class="muted">None.</dd></div>
          </dl>
        </div>
      </div>

      <div class="card span-7">
        <h2>Generated Diff</h2>
        <div id="selectedProposalInfo" class="message muted">No proposal selected.</div>
        <pre id="generatedDiff" class="mono-box">No generated diff yet.</pre>
      </div>

      <div class="card span-5">
        <h2>Apply Proposal</h2>
        <div id="applyResult" class="message muted">Apply results will appear here.</div>
        <div class="meta-list">
          <div><dt>Selected proposal</dt><dd id="selectedProposalId" class="muted">None</dd></div>
        </div>
      </div>

      <div class="card span-7">
        <h2>Saved Proposals</h2>
        <div class="row">
          <button id="refreshProposalsButton">Refresh Proposals</button>
        </div>
        <div id="proposalList" class="proposal-list output">
          <div class="message muted">No proposals loaded yet.</div>
        </div>
      </div>

      <div class="card span-5">
        <h2>Validation Result</h2>
        <div class="row">
          <button id="basicValidationButton">Run Basic Validation</button>
        </div>
        <div id="validationResult" class="output">
          <div class="message muted">Validation results will appear here.</div>
        </div>
      </div>
    </section>
  </div>

  <script>
    const state = {
      selectedProposalId: null,
    };

    function byId(id) {
      return document.getElementById(id);
    }

    function parseCsv(value) {
      return value
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);
    }

    function escapeHtml(value) {
      return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
    }

    function formatList(items) {
      if (!items || !items.length) {
        return "None.";
      }
      return items.join(", ");
    }

    async function apiRequest(url, options = {}) {
      const response = await fetch(url, {
        headers: {
          "Content-Type": "application/json",
          ...(options.headers || {}),
        },
        ...options,
      });

      let data = null;
      try {
        data = await response.json();
      } catch (_error) {
        data = null;
      }

      if (!response.ok) {
        const detail = data && typeof data.detail === "string" ? data.detail : response.statusText;
        throw new Error(detail || "Request failed.");
      }

      return data;
    }

    function setMessage(elementId, message, kind = "") {
      const el = byId(elementId);
      el.className = "message" + (kind ? ` ${kind}` : "");
      el.textContent = message;
    }

    function renderValidation(data, label) {
      const checks = (data.checks || []).map((check) => {
        const status = check.ok ? "status-ok" : "status-bad";
        return `
          <div class="proposal-item">
            <div class="proposal-head">
              <div>
                <strong>${escapeHtml(check.name)}</strong>
                <div class="muted">${escapeHtml(check.url)}</div>
              </div>
              <div class="${status}">${check.ok ? "OK" : "FAILED"}</div>
            </div>
            <div class="meta-list">
              <div><dt>Status code</dt><dd>${escapeHtml(check.status_code ?? "n/a")}</dd></div>
              <div><dt>Preview</dt><dd><pre class="mono-box">${escapeHtml(check.response_preview ?? "")}</pre></dd></div>
              <div><dt>Error</dt><dd>${escapeHtml(check.error ?? "None")}</dd></div>
            </div>
          </div>
        `;
      }).join("");

      byId("validationResult").innerHTML = `
        <div class="message ${data.ok ? "success" : "error"}">
          ${escapeHtml(label)}: ${data.ok ? "ok=true" : "ok=false"}
        </div>
        ${checks || '<div class="message muted">No checks returned.</div>'}
      `;
    }

    async function loadBackendStatus() {
      try {
        const [health, settings] = await Promise.all([
          apiRequest("/health", { headers: {} }),
          apiRequest("/settings", { headers: {} }),
        ]);
        byId("backendStatus").className = "message success";
        byId("backendStatus").innerHTML = `
          <div class="pill">status <span class="status-ok">${escapeHtml(health.status)}</span></div>
          <div class="pill">env ${escapeHtml(settings.app_env)}</div>
          <div class="pill">model ${escapeHtml(settings.ollama_model)}</div>
        `;
      } catch (error) {
        setMessage("backendStatus", String(error.message || error), "error");
      }
    }

    async function handleAsk() {
      const payload = {
        project_path: byId("projectPath").value.trim(),
        question: byId("askQuestion").value.trim(),
        files: parseCsv(byId("askFiles").value),
      };

      setMessage("askResult", "Running repository question...", "");
      try {
        const data = await apiRequest("/repo/ask", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        setMessage("askResult", data.response || "No response text returned.", "success");
        byId("askContextFiles").textContent = formatList(data.context_files);
      } catch (error) {
        setMessage("askResult", String(error.message || error), "error");
        byId("askContextFiles").textContent = "None.";
      }
    }

    async function handlePlanChange() {
      const payload = {
        project_path: byId("projectPath").value.trim(),
        task: byId("planTask").value.trim(),
        files: parseCsv(byId("planFiles").value),
        save_proposal: byId("saveProposal").checked,
        proposal_name: byId("proposalName").value.trim() || null,
      };

      setMessage("planSummary", "Planning change...", "");
      try {
        const data = await apiRequest("/repo/plan-change", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        setMessage("planSummary", data.explanation || "No explanation returned.", "success");
        byId("planTargetFile").textContent = data.target_file || "None";
        byId("planOperation").textContent = data.operation || "None";
        byId("planAnchor").textContent = data.anchor || "None";
        byId("planWarnings").textContent = formatList(data.warnings);
        byId("planSafetyNotes").textContent = formatList(data.safety_notes);
        byId("generatedDiff").textContent = data.generated_diff || "No generated diff returned.";
        byId("selectedProposalInfo").textContent = data.proposal_id
          ? `Latest saved proposal: ${data.proposal_id}`
          : "Planner returned a diff without saving a proposal.";
        if (data.proposal_id) {
          state.selectedProposalId = data.proposal_id;
          byId("selectedProposalId").textContent = data.proposal_id;
          await loadProposalDetail(data.proposal_id);
          await loadProposals();
        }
      } catch (error) {
        setMessage("planSummary", String(error.message || error), "error");
      }
    }

    async function loadProposals() {
      const container = byId("proposalList");
      container.innerHTML = '<div class="message">Loading proposals...</div>';
      try {
        const data = await apiRequest("/repo/proposals", { headers: {} });
        const proposals = data.proposals || [];
        if (!proposals.length) {
          container.innerHTML = '<div class="message muted">No saved proposals found.</div>';
          return;
        }

        container.innerHTML = proposals.map((proposal) => `
          <div class="proposal-item">
            <div class="proposal-head">
              <div>
                <strong>${escapeHtml(proposal.proposal_id)}</strong>
                <div class="muted">${escapeHtml(proposal.task || "")}</div>
              </div>
              <div class="${proposal.warnings_count ? "status-warn" : "status-ok"}">
                warnings: ${escapeHtml(proposal.warnings_count ?? 0)}
              </div>
            </div>
            <div class="meta-list">
              <div><dt>Target file</dt><dd>${escapeHtml(proposal.target_file || "None")}</dd></div>
            </div>
            <div class="row" style="margin-top: 12px;">
              <button class="secondary" data-action="view" data-id="${escapeHtml(proposal.proposal_id)}">View</button>
              <button class="warn" data-action="apply" data-id="${escapeHtml(proposal.proposal_id)}">Apply</button>
              <button class="secondary" data-action="validate" data-id="${escapeHtml(proposal.proposal_id)}">Validate</button>
            </div>
          </div>
        `).join("");
      } catch (error) {
        container.innerHTML = `<div class="message error">${escapeHtml(String(error.message || error))}</div>`;
      }
    }

    async function loadProposalDetail(proposalId) {
      try {
        const data = await apiRequest(`/repo/proposals/${encodeURIComponent(proposalId)}`, { headers: {} });
        state.selectedProposalId = proposalId;
        byId("selectedProposalId").textContent = proposalId;
        byId("selectedProposalInfo").innerHTML = `
          <div><strong>${escapeHtml(proposalId)}</strong></div>
          <div class="muted">warnings: ${escapeHtml((data.warnings || []).length)}</div>
          <div class="muted">safety notes: ${escapeHtml((data.safety_notes || []).join(" | ") || "None")}</div>
        `;
        byId("generatedDiff").textContent = data.generated_diff || "No generated diff saved for this proposal.";
      } catch (error) {
        setMessage("applyResult", String(error.message || error), "error");
      }
    }

    async function applyProposal(proposalId) {
      if (!window.confirm(`Apply proposal ${proposalId}? This may modify local files.`)) {
        return;
      }

      setMessage("applyResult", `Applying ${proposalId}...`, "");
      try {
        const data = await apiRequest(`/repo/proposals/${encodeURIComponent(proposalId)}/apply`, {
          method: "POST",
          body: JSON.stringify({
            confirm_apply: true,
            allow_warnings: false,
            create_backup: true,
          }),
        });
        setMessage(
          "applyResult",
          `${proposalId}: ${data.message} backup=${data.backup_path || "none"}`,
          data.applied ? "success" : "error",
        );
        state.selectedProposalId = proposalId;
        byId("selectedProposalId").textContent = proposalId;
      } catch (error) {
        setMessage("applyResult", `${proposalId}: ${String(error.message || error)}`, "error");
      }
    }

    async function validateProposal(proposalId) {
      try {
        const data = await apiRequest(`/repo/proposals/${encodeURIComponent(proposalId)}/validate`, {
          method: "POST",
          body: JSON.stringify({
            include_version: true,
            include_settings: true,
            include_models: false,
          }),
        });
        renderValidation(data, `Proposal validation for ${proposalId}`);
      } catch (error) {
        byId("validationResult").innerHTML = `<div class="message error">${escapeHtml(String(error.message || error))}</div>`;
      }
    }

    async function runBasicValidation() {
      try {
        const data = await apiRequest("/repo/validation/basic", { headers: {} });
        renderValidation(data, "Basic validation");
      } catch (error) {
        byId("validationResult").innerHTML = `<div class="message error">${escapeHtml(String(error.message || error))}</div>`;
      }
    }

    byId("askButton").addEventListener("click", handleAsk);
    byId("planButton").addEventListener("click", handlePlanChange);
    byId("refreshProposalsButton").addEventListener("click", loadProposals);
    byId("basicValidationButton").addEventListener("click", runBasicValidation);

    byId("proposalList").addEventListener("click", async (event) => {
      const button = event.target.closest("button[data-action]");
      if (!button) {
        return;
      }
      const proposalId = button.getAttribute("data-id");
      const action = button.getAttribute("data-action");
      if (!proposalId || !action) {
        return;
      }
      if (action === "view") {
        await loadProposalDetail(proposalId);
      } else if (action === "apply") {
        await applyProposal(proposalId);
      } else if (action === "validate") {
        await validateProposal(proposalId);
      }
    });

    loadBackendStatus();
    loadProposals();
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html.replace("__DEFAULT_PROJECT_PATH__", default_project_path))
