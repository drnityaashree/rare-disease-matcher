const state = {
  apiKey: "SUPER_SECURE_RARE_DISEASE_NETWORK_KEY_2026",
  role: "admin",
  recentQueries: [],
  symptoms: [],
  selectedSymptoms: [],
};

const headers = () => ({
  "Content-Type": "application/json",
  "X-API-Key": state.apiKey,
  "X-Role": state.role,
});

const $ = (id) => document.getElementById(id);

function item(title, detail) {
  return `<div class="list-item"><strong>${title}</strong><p class="muted">${detail || ""}</p></div>`;
}

function normalizeName(value) {
  return value.trim().replace(/\s+/g, " ");
}

function escapeHtml(value) {
  return String(value || "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));
}

function showView(viewId) {
  document.querySelectorAll(".view").forEach((view) => view.classList.remove("active-view"));
  document.querySelectorAll(".nav-button").forEach((button) => button.classList.remove("active"));
  $(viewId).classList.add("active-view");
  document.querySelector(`[data-view="${viewId}"]`).classList.add("active");
}

async function loadSummary() {
  const response = await fetch("/network-summary");
  const data = await response.json();
  $("activeNodes").textContent = data.active_nodes;
  $("totalRecords").textContent = data.total_records;
  $("auditCount").textContent = data.total_audit_logs;
  $("networkStatus").textContent = data.active_nodes > 0 ? "Online" : "Offline";
  $("nodeList").innerHTML = data.nodes.length
    ? data.nodes.map((node) => item(
      `${node.hospital_name || node.node_id} (${node.status || "unknown"})`,
      `${node.node_id} | ${node.url} | ${node.records || 0} records | ${node.symptoms || 0} symptoms | last heartbeat ${node.last_seen || "now"}`
    )).join("")
    : item("No active nodes", "Start a hospital node on port 8001.");
}

async function loadSymptoms() {
  try {
    const response = await fetch("/symptoms");
    const data = await response.json();
    state.symptoms = data.symptoms || [];
    $("symptomSuggestions").innerHTML = data.symptoms.map((symptom) => `<option value="${symptom.name}"></option>`).join("");
    renderSymptomOptions();
  } catch {
    state.symptoms = [];
    $("symptomSuggestions").innerHTML = "";
    renderSymptomOptions();
  }
}

function addSelectedSymptom(rawName, severityValue) {
  const name = normalizeName(rawName);
  if (!name) return;
  const existing = state.selectedSymptoms.find((item) => item.name.toLowerCase() === name.toLowerCase());
  if (existing) {
    existing.severity = Number(severityValue || existing.severity || 3);
  } else {
    state.selectedSymptoms.push({name, severity: Number(severityValue || 3)});
  }
  renderSelectedSymptoms();
}

function removeSelectedSymptom(name) {
  state.selectedSymptoms = state.selectedSymptoms.filter((item) => item.name.toLowerCase() !== name.toLowerCase());
  renderSelectedSymptoms();
}

function renderSelectedSymptoms() {
  $("selectedSymptomChips").innerHTML = state.selectedSymptoms.length
    ? state.selectedSymptoms.map((symptom) => `
      <span class="chip">
        ${escapeHtml(symptom.name)} <small>severity ${symptom.severity}</small>
        <button type="button" data-remove-symptom="${escapeHtml(symptom.name)}">x</button>
      </span>
    `).join("")
    : `<span class="muted">No selected symptom chips yet.</span>`;

  document.querySelectorAll("[data-remove-symptom]").forEach((button) => {
    button.addEventListener("click", () => removeSelectedSymptom(button.dataset.removeSymptom));
  });
}

function renderSymptomOptions() {
  const query = ($("symptomSearchInput")?.value || "").toLowerCase().trim();
  const symptoms = state.symptoms
    .filter((symptom) => !query || symptom.name.toLowerCase().includes(query))
    .slice(0, 12);
  $("symptomOptionList").innerHTML = symptoms.length
    ? symptoms.map((symptom) => {
      const checked = state.selectedSymptoms.some((item) => item.name.toLowerCase() === symptom.name.toLowerCase());
      return `
        <label class="symptom-option">
          <input type="checkbox" data-symptom-option="${escapeHtml(symptom.name)}" ${checked ? "checked" : ""}>
          <span>${escapeHtml(symptom.name)}</span>
          <small>${(symptom.sources || []).join(", ")}</small>
        </label>
      `;
    }).join("")
    : `<span class="muted">No matching symptoms from active nodes.</span>`;

  document.querySelectorAll("[data-symptom-option]").forEach((checkbox) => {
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) {
        addSelectedSymptom(checkbox.dataset.symptomOption, $("symptomSeverityInput").value);
      } else {
        removeSelectedSymptom(checkbox.dataset.symptomOption);
      }
    });
  });
}

async function loadAnalytics() {
  const response = await fetch("/network-analytics");
  const data = await response.json();

  $("hotspotList").innerHTML = data.hotspots.length
    ? data.hotspots.map((hotspot) => item(hotspot.disease_name, `${hotspot.case_count} cases | ${hotspot.hospitals.join(", ")} | ${hotspot.top_symptoms.join(", ")}`)).join("")
    : item("No hotspots detected", "More cases are needed for repeated pattern alerts.");

  $("riskList").innerHTML = data.risk_alerts.length
    ? data.risk_alerts.map((alert) => item(alert.disease_name, `${alert.risk_alert}: ${alert.critical_symptoms.join(", ")}`)).join("")
    : item("No critical alerts", "No record has multiple severity-5 symptoms.");

  $("rarePatternList").innerHTML = data.rare_patterns.length
    ? data.rare_patterns.map((pattern) => item(pattern.disease_name, pattern.rare_symptoms.join(", "))).join("")
    : item("No rare patterns", "No unusual symptom combinations found.");

  $("duplicateList").innerHTML = data.duplicates.length
    ? data.duplicates.map((dup) => item(`${dup.record_a} / ${dup.record_b}`, `${dup.similarity} similarity | ${dup.shared_symptoms.join(", ")}`)).join("")
    : item("No duplicates", "No highly similar repeated cases detected.");

  $("timelineList").innerHTML = data.timeline.length
    ? data.timeline.map((row) => item(`${row.date} - ${row.diagnosis}`, row.symptoms.map((s) => `${s.name} (${s.severity})`).join(", "))).join("")
    : item("No timeline data", "Start nodes and seed records first.");
}

async function runSearch() {
  const manualSymptoms = $("symptomInput").value.split(",").map((value) => normalizeName(value)).filter(Boolean);
  const severityValue = Number($("severityInput").value);
  const severity = {};
  manualSymptoms.forEach((symptom) => {
    severity[symptom.toLowerCase()] = severityValue;
  });
  state.selectedSymptoms.forEach((symptom) => {
    severity[symptom.name.toLowerCase()] = symptom.severity;
  });
  const symptoms = [...manualSymptoms, ...state.selectedSymptoms.map((symptom) => symptom.name)]
    .filter((symptom, index, values) => values.findIndex((value) => value.toLowerCase() === symptom.toLowerCase()) === index);

  const body = {
    symptoms,
    severity,
    notes: $("notesInput").value,
    top_k: 5,
  };

  const response = await fetch("/find-matches", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body),
  });
  const data = await response.json();
  state.recentQueries.unshift({symptoms: symptoms.join(", "), count: data.total_matches_found || 0, time: new Date().toLocaleTimeString()});
  renderRecentQueries();
  renderResults(data.results || []);
  await loadSummary();
  await loadAnalytics();
}

function renderResults(results) {
  $("resultsList").innerHTML = results.length
    ? results.map((result) => `
      <article class="result-card">
        <div class="score-row">
          <strong>${result.disease_name}</strong>
          <span class="badge ${result.risk_alert}">${result.risk_alert}</span>
        </div>
        <span>${result.hospital_name}${result.node_id ? ` | ${result.node_id}` : ""}</span>
        <span>Similarity: ${result.similarity_score} | Confidence: ${result.confidence_score}</span>
        <div class="mini-bars">
          ${Object.entries(result.confidence_breakdown || {}).map(([label, value]) => `
            <span title="${label}: ${value}"><i style="width:${Math.max(4, Math.round(Number(value) * 100))}%"></i></span>
          `).join("")}
        </div>
        <p>${result.explanation}</p>
        <small class="muted">Record ${result.record_id} | ${result.disease_classification || "unknown"} | Matched: ${result.matched_symptoms.join(", ") || "clinical notes"}</small>
      </article>
    `).join("")
    : item("No matches found", "Try adding more symptoms or notes.");
}

function renderRecentQueries() {
  $("recentQueries").innerHTML = state.recentQueries.length
    ? state.recentQueries.slice(0, 5).map((query) => item(query.symptoms, `${query.count} matches | ${query.time}`)).join("")
    : item("No queries yet", "Run a distributed symptom search.");
}

async function loadAuditLogs() {
  try {
    const response = await fetch("/audit-logs", {headers: headers()});
    const data = await response.json();
    $("auditTable").innerHTML = data.logs.map((log) => `
      <tr>
        <td>${log.timestamp}</td>
        <td>${log.matched_record_id}</td>
        <td>${log.hospital_name || log.responding_hospital_id}</td>
        <td>${log.similarity_score}</td>
      </tr>
    `).join("");
  } catch {
    $("auditTable").innerHTML = `<tr><td colspan="4">Start hospital node to view audit logs.</td></tr>`;
  }
}

function parseSeverityMap(value) {
  return value.split(",").map((chunk) => chunk.trim()).filter(Boolean).reduce((acc, chunk) => {
    const [name, rawSeverity] = chunk.split(":").map((part) => part.trim());
    if (name) {
      acc[name] = Math.max(1, Math.min(Number(rawSeverity || 3), 5));
    }
    return acc;
  }, {});
}

async function saveAdminEntry() {
  $("adminStatus").textContent = "Saving...";
  const diseaseName = $("adminDiseaseInput").value.trim();
  const symptomName = $("adminSymptomInput").value.trim();
  const recordSymptoms = parseSeverityMap($("adminRecordSymptomsInput").value);

  try {
    if (diseaseName) {
      await fetch("/admin/diseases", {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({disease_name: diseaseName, icd10_code: $("adminIcdInput").value.trim() || null}),
      });
    }
    if (symptomName) {
      await fetch("/admin/symptoms", {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({symptom_name: symptomName, snomed_code: $("adminSnomedInput").value.trim() || null}),
      });
    }
    if (diseaseName && Object.keys(recordSymptoms).length) {
      const response = await fetch("/admin/clinical-records", {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({
          disease_name: diseaseName,
          symptoms: recordSymptoms,
          notes: $("adminNotesInput").value,
          age_at_encounter: $("adminAgeInput").value ? Number($("adminAgeInput").value) : null,
          hospital_name: $("adminHospitalInput").value.trim() || "Manual Clinical Registry",
        }),
      });
      const data = await response.json();
      $("adminStatus").textContent = `Saved record ${data.record_id || ""}`.trim();
    } else {
      $("adminStatus").textContent = "Saved disease/symptom metadata.";
    }
    await refreshAll();
  } catch {
    $("adminStatus").textContent = "Could not save. Start hospital node and use an admin role.";
  }
}

async function refreshAll() {
  await loadSummary();
  await loadSymptoms();
  await loadAnalytics();
  await loadAuditLogs();
  renderRecentQueries();
}

$("loginButton").addEventListener("click", async () => {
  state.role = $("roleSelect").value;
  state.apiKey = $("apiKeyInput").value;
  $("roleBadge").textContent = state.role;
  $("loginScreen").classList.add("hidden");
  $("appShell").classList.remove("hidden");
  await refreshAll();
});

document.querySelectorAll(".nav-button").forEach((button) => {
  button.addEventListener("click", () => showView(button.dataset.view));
});

$("refreshButton").addEventListener("click", refreshAll);
$("searchButton").addEventListener("click", runSearch);
$("adminSaveButton").addEventListener("click", saveAdminEntry);
$("symptomSearchInput").addEventListener("input", renderSymptomOptions);
$("addSymptomButton").addEventListener("click", () => {
  addSelectedSymptom($("customSymptomInput").value || $("symptomSearchInput").value, $("symptomSeverityInput").value);
  $("customSymptomInput").value = "";
  $("symptomSearchInput").value = "";
  renderSymptomOptions();
});
renderSelectedSymptoms();
