const state = {
  bootstrap: null,
  bigBangs: [],
  workspace: null,
  selectedBigBangId: null,
  selectedMultiverseId: null,
  selectedTickId: null,
  loading: false,
};

const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const text = await response.text();
  let body = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  if (!response.ok) {
    const detail = body && body.detail ? body.detail : response.statusText;
    throw new Error(Array.isArray(detail) ? detail.map((item) => item.msg).join(", ") : detail);
  }
  return body;
}

function toast(message) {
  const node = $("toast");
  node.textContent = message;
  node.classList.add("visible");
  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => node.classList.remove("visible"), 3600);
}

function fmtDate(value) {
  if (!value) return "not recorded";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString();
}

function compactId(value) {
  return value ? String(value).slice(0, 8) : "none";
}

function firstWords(value, count = 16) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (!text) return "No summary yet";
  const words = text.split(" ");
  return words.length > count ? `${words.slice(0, count).join(" ")}...` : text;
}

function setBusy(isBusy) {
  state.loading = isBusy;
  for (const id of ["createScenarioButton", "startButton", "pauseButton", "resumeButton", "simulateButton", "runButton", "reportButton"]) {
    $(id).disabled = isBusy;
  }
}

async function init() {
  bindEvents();
  await loadBootstrap();
  await loadBigBangs();
}

function bindEvents() {
  $("refreshButton").addEventListener("click", refreshAll);
  $("createScenarioButton").addEventListener("click", createFromScenario);
  $("createForm").addEventListener("submit", createFromForm);
  $("startButton").addEventListener("click", () => updateBigBangStatus("start"));
  $("pauseButton").addEventListener("click", () => updateBigBangStatus("pause"));
  $("resumeButton").addEventListener("click", () => updateBigBangStatus("resume"));
  $("simulateButton").addEventListener("click", simulateNextTick);
  $("runButton").addEventListener("click", runUntilComplete);
  $("reportButton").addEventListener("click", generateReport);
}

async function loadBootstrap() {
  state.bootstrap = await api("/api/frontend/bootstrap");
  $("providerLine").textContent = `${state.bootstrap.settings.default_llm_provider} / ${state.bootstrap.settings.default_model}`;
  $("tickDuration").value = state.bootstrap.defaults.simulation_config.tick_duration;
  $("maxTicks").value = state.bootstrap.defaults.simulation_config.max_ticks;
  renderScenarioOptions();
}

function renderScenarioOptions() {
  const select = $("scenarioSelect");
  select.innerHTML = "";
  for (const scenario of state.bootstrap.scenario_bank.scenarios) {
    const option = document.createElement("option");
    option.value = scenario.id;
    option.textContent = scenario.title;
    select.appendChild(option);
  }
}

async function loadBigBangs() {
  try {
    state.bigBangs = await api("/api/big-bangs");
  } catch (error) {
    state.bigBangs = [];
    renderBigBangs(error.message);
    renderEmptyWorkspace("Database unavailable", "Start PostgreSQL and refresh to load Big Bangs.");
    return;
  }
  renderBigBangs();
  if (!state.selectedBigBangId && state.bigBangs.length) {
    state.selectedBigBangId = state.bigBangs[0].id;
  }
  if (state.selectedBigBangId) {
    await loadWorkspace(state.selectedBigBangId);
  } else {
    renderEmptyWorkspace("No Big Bang selected", "Create one from the scenario bank or a prose scenario.");
  }
}

async function refreshAll() {
  await loadBigBangs();
  toast("Refreshed");
}

function renderBigBangs(error) {
  const list = $("bigBangList");
  list.innerHTML = "";
  if (error) {
    list.append(empty(`Database unavailable: ${error}`));
    return;
  }
  if (!state.bigBangs.length) {
    list.append(empty("No Big Bangs yet."));
    return;
  }
  for (const item of state.bigBangs) {
    const button = document.createElement("button");
    button.className = `big-bang-item ${item.id === state.selectedBigBangId ? "active" : ""}`;
    button.innerHTML = `
      <span class="item-title">${escapeHtml(item.name)}</span>
      <span class="item-meta">${escapeHtml(item.status)} / v${item.current_config_version} / ${compactId(item.id)}</span>
    `;
    button.addEventListener("click", async () => {
      state.selectedBigBangId = item.id;
      state.selectedMultiverseId = null;
      state.selectedTickId = null;
      renderBigBangs();
      await loadWorkspace(item.id);
    });
    list.appendChild(button);
  }
}

async function loadWorkspace(bigBangId) {
  try {
    state.workspace = await api(`/api/frontend/workspace/${bigBangId}`);
    if (!state.selectedMultiverseId && state.workspace.multiverses.length) {
      state.selectedMultiverseId = state.workspace.multiverses[0].id;
    }
    renderWorkspace();
  } catch (error) {
    renderEmptyWorkspace("Workspace unavailable", error.message);
  }
}

function renderEmptyWorkspace(title, detail) {
  $("workspaceTitle").textContent = title;
  $("canvasTitle").textContent = detail;
  $("summaryChips").innerHTML = "";
  $("timelineCanvas").innerHTML = "";
  $("timelineCanvas").append(empty(detail));
  $("activityList").innerHTML = "";
  $("tickList").innerHTML = "";
  $("signalList").innerHTML = "";
  renderInspector("idle", { message: detail });
}

function renderWorkspace() {
  const workspace = state.workspace;
  $("workspaceTitle").textContent = workspace.big_bang.name;
  $("canvasTitle").textContent = `${workspace.multiverses.length} timeline${workspace.multiverses.length === 1 ? "" : "s"}`;
  renderChips([
    `${workspace.big_bang.status}`,
    `${workspace.actors.length} actors`,
    `${workspace.latest_ticks.length} recent ticks`,
    `${workspace.jobs.length} jobs`,
  ]);
  renderTimeline();
  renderActivity();
  renderTicks();
  renderSignals();
  renderInspector("big_bang", workspace.big_bang);
}

function renderChips(values) {
  $("summaryChips").innerHTML = values.map((value) => `<span class="chip">${escapeHtml(value)}</span>`).join("");
}

function renderTimeline() {
  const canvas = $("timelineCanvas");
  canvas.innerHTML = "";
  if (!state.workspace.multiverses.length) {
    canvas.append(empty("No multiverses have been initialized."));
    return;
  }

  const positions = new Map();
  const byId = new Map(state.workspace.multiverses.map((item) => [item.id, item]));
  const depthBuckets = new Map();
  for (const item of state.workspace.multiverses) {
    const bucket = depthBuckets.get(item.depth) || [];
    bucket.push(item);
    depthBuckets.set(item.depth, bucket);
  }
  for (const [depth, items] of depthBuckets.entries()) {
    items.sort((a, b) => a.ui_label.localeCompare(b.ui_label));
    items.forEach((item, index) => {
      positions.set(item.id, { x: 34 + depth * 230, y: 28 + index * 132 });
    });
  }

  const maxDepth = Math.max(...state.workspace.multiverses.map((item) => item.depth));
  const maxBucket = Math.max(...Array.from(depthBuckets.values()).map((items) => items.length));
  const inner = document.createElement("div");
  inner.className = "timeline-inner";
  inner.style.width = `${Math.max(780, 260 + maxDepth * 230)}px`;
  inner.style.height = `${Math.max(330, 160 + maxBucket * 132)}px`;

  for (const edge of state.workspace.lineage_edges) {
    const parent = positions.get(edge.parent_multiverse_id);
    const child = positions.get(edge.child_multiverse_id);
    if (!parent || !child) continue;
    const x1 = parent.x + 156;
    const y1 = parent.y + 42;
    const x2 = child.x;
    const y2 = child.y + 42;
    const length = Math.hypot(x2 - x1, y2 - y1);
    const angle = Math.atan2(y2 - y1, x2 - x1) * 180 / Math.PI;
    const line = document.createElement("div");
    line.className = "edge";
    line.style.left = `${x1}px`;
    line.style.top = `${y1}px`;
    line.style.width = `${length}px`;
    line.style.transform = `rotate(${angle}deg)`;
    inner.appendChild(line);
  }

  for (const item of state.workspace.multiverses) {
    const pos = positions.get(item.id);
    const ticks = state.workspace.ticks_by_multiverse[item.id] || [];
    const node = document.createElement("button");
    node.className = `node ${item.id === state.selectedMultiverseId ? "active" : ""}`;
    node.style.left = `${pos.x}px`;
    node.style.top = `${pos.y}px`;
    node.innerHTML = `
      <div class="node-label">${escapeHtml(item.ui_label)}</div>
      <div class="node-status">${escapeHtml(item.status)} / depth ${item.depth}</div>
      <div class="node-summary">${ticks.length} ticks / ${escapeHtml(firstWords(item.branch_reason, 7))}</div>
    `;
    node.addEventListener("click", async () => {
      state.selectedMultiverseId = item.id;
      state.selectedTickId = null;
      renderTimeline();
      renderTicks();
      await inspect("multiverse", item.id);
    });
    inner.appendChild(node);
    byId.set(item.id, item);
  }
  canvas.appendChild(inner);
}

function renderActivity() {
  const list = $("activityList");
  list.innerHTML = "";
  const activity = state.workspace.activity || [];
  if (!activity.length) {
    list.append(empty("No activity yet."));
    return;
  }
  for (const item of activity) {
    const node = document.createElement("button");
    node.className = "activity-item";
    node.innerHTML = `
      <span class="item-title">${escapeHtml(item.label)}</span>
      <span class="item-meta">${escapeHtml(item.kind)} / ${escapeHtml(item.status)} / ${fmtDate(item.created_at)}</span>
    `;
    node.addEventListener("click", () => inspect(activityToType(item.kind), item.id));
    list.appendChild(node);
  }
}

function renderTicks() {
  const list = $("tickList");
  list.innerHTML = "";
  if (!state.selectedMultiverseId) {
    list.append(empty("Select a multiverse."));
    return;
  }
  const ticks = state.workspace.ticks_by_multiverse[state.selectedMultiverseId] || [];
  if (!ticks.length) {
    list.append(empty("No ticks for this timeline."));
    return;
  }
  for (const tick of ticks) {
    const node = document.createElement("button");
    node.className = `tick-item ${tick.id === state.selectedTickId ? "active" : ""}`;
    node.innerHTML = `
      <span class="item-title">${escapeHtml(tick.ui_label)}</span>
      <span class="item-meta">${escapeHtml(tick.status)} / index ${tick.tick_index} / ${escapeHtml(firstWords(tick.summary, 8))}</span>
    `;
    node.addEventListener("click", async () => {
      state.selectedTickId = tick.id;
      renderTicks();
      await inspect("tick", tick.id);
    });
    list.appendChild(node);
  }
}

function renderSignals() {
  const list = $("signalList");
  list.innerHTML = "";
  const graphLayers = state.workspace.graphs.layers.map((layer) => ({
    title: layer.layer,
    meta: `${layer.count} snapshots / latest tick ${layer.latest_tick_index}`,
  }));
  const emotions = state.workspace.emotion_observability.emotions_seen.map((emotion) => ({
    title: emotion,
    meta: "emotion observed",
  }));
  const sociology = state.workspace.sociology.models_seen.map((model) => ({
    title: model,
    meta: "sociology model",
  }));
  const rows = [...graphLayers, ...emotions, ...sociology];
  if (!rows.length) {
    list.append(empty("No graph, emotion, or sociology signals yet."));
    return;
  }
  for (const row of rows) {
    const node = document.createElement("div");
    node.className = "signal-item";
    node.innerHTML = `
      <span class="item-title">${escapeHtml(row.title)}</span>
      <span class="item-meta">${escapeHtml(row.meta)}</span>
    `;
    list.appendChild(node);
  }
}

async function inspect(type, id) {
  try {
    const payload = await api(`/api/frontend/inspect/${type}/${id}`);
    renderInspector(payload.type, payload);
  } catch (error) {
    renderInspector("error", { message: error.message });
  }
}

function renderInspector(type, payload) {
  $("inspectorType").textContent = type;
  const content = $("inspectorContent");
  content.innerHTML = "";
  if (!payload) {
    content.append(empty("Nothing selected."));
    return;
  }
  const item = payload.item || payload;
  const header = document.createElement("div");
  header.innerHTML = `
    <div class="kv"><b>Name</b><span>${escapeHtml(item.name || item.ui_label || item.label || item.report_type || item.job_type || item.message || "Selected item")}</span></div>
    <div class="kv"><b>Status</b><span>${escapeHtml(item.status || item.decision || "n/a")}</span></div>
    <div class="kv"><b>ID</b><span>${escapeHtml(item.id || "n/a")}</span></div>
    <div class="kv"><b>Created</b><span>${escapeHtml(fmtDate(item.created_at))}</span></div>
  `;
  content.appendChild(header);
  const pre = document.createElement("pre");
  pre.textContent = JSON.stringify(payload, null, 2);
  content.appendChild(pre);
}

async function createFromScenario() {
  const scenarioId = $("scenarioSelect").value;
  if (!scenarioId) return;
  await withBusy(async () => {
    const result = await api(`/api/scenario-bank/${scenarioId}/big-bang`, { method: "POST", body: "{}" });
    state.selectedBigBangId = result.big_bang_id;
    toast("Created Big Bang from scenario");
    await loadBigBangs();
  });
}

async function createFromForm(event) {
  event.preventDefault();
  const payload = {
    name: $("newName").value.trim(),
    scenario_text: $("newScenario").value.trim(),
    simulation_config: {
      tick_duration: $("tickDuration").value.trim() || state.bootstrap.defaults.simulation_config.tick_duration,
      max_ticks: Number($("maxTicks").value || state.bootstrap.defaults.simulation_config.max_ticks),
    },
    use_initializer_agent: $("useInitializer").checked,
  };
  await withBusy(async () => {
    const created = await api("/api/big-bangs", { method: "POST", body: JSON.stringify(payload) });
    state.selectedBigBangId = created.id;
    toast("Created Big Bang");
    $("createForm").reset();
    $("tickDuration").value = state.bootstrap.defaults.simulation_config.tick_duration;
    $("maxTicks").value = state.bootstrap.defaults.simulation_config.max_ticks;
    $("useInitializer").checked = true;
    await loadBigBangs();
  });
}

async function updateBigBangStatus(action) {
  if (!state.selectedBigBangId) return toast("Select a Big Bang first");
  await withBusy(async () => {
    await api(`/api/big-bangs/${state.selectedBigBangId}/${action}`, { method: "POST", body: "{}" });
    toast(`${action} complete`);
    await loadWorkspace(state.selectedBigBangId);
  });
}

async function simulateNextTick() {
  if (!state.selectedMultiverseId) return toast("Select a multiverse first");
  await withBusy(async () => {
    const tick = await api(`/api/multiverses/${state.selectedMultiverseId}/simulate-next-tick`, {
      method: "POST",
      body: JSON.stringify({ force: false }),
    });
    state.selectedTickId = tick.id;
    toast(`Simulated ${tick.ui_label}`);
    await loadWorkspace(state.selectedBigBangId);
    await inspect("tick", tick.id);
  });
}

async function runUntilComplete() {
  if (!state.selectedBigBangId) return toast("Select a Big Bang first");
  await withBusy(async () => {
    await api(`/api/big-bangs/${state.selectedBigBangId}/run-until-complete`, {
      method: "POST",
      body: JSON.stringify({ max_total_ticks: 24 }),
    });
    toast("Run complete");
    await loadWorkspace(state.selectedBigBangId);
  });
}

async function generateReport() {
  if (!state.selectedBigBangId) return toast("Select a Big Bang first");
  await withBusy(async () => {
    await api(`/api/big-bangs/${state.selectedBigBangId}/reports/final`, {
      method: "POST",
      body: JSON.stringify({ regenerate: false }),
    });
    toast("Report generated");
    await loadWorkspace(state.selectedBigBangId);
  });
}

async function withBusy(fn) {
  setBusy(true);
  try {
    await fn();
  } catch (error) {
    toast(error.message);
  } finally {
    setBusy(false);
  }
}

function activityToType(kind) {
  return kind;
}

function empty(message) {
  const node = document.createElement("div");
  node.className = "empty";
  node.textContent = message;
  return node;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

init().catch((error) => {
  renderEmptyWorkspace("Workbench failed to load", error.message);
  toast(error.message);
});
