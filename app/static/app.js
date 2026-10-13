const api = async (path, options = {}) => {
  const res = await fetch(path, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (res.status === 401) {
    showLogin();
    throw new Error("Not authenticated");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
};

function toast(message, kind = "info") {
  const container = document.getElementById("toast-container");
  const el = document.createElement("div");
  el.className = `toast ${kind}`;
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => el.remove(), 5000);
}

function showLogin() {
  document.getElementById("login-view").classList.remove("hidden");
  document.getElementById("app-view").classList.add("hidden");
}

function showApp() {
  document.getElementById("login-view").classList.add("hidden");
  document.getElementById("app-view").classList.remove("hidden");
  loadJobs();
  loadRuns();
  pollNotifications();
}

// ---------- Auth ----------

document.getElementById("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const username = document.getElementById("login-username").value;
  const password = document.getElementById("login-password").value;
  const errorEl = document.getElementById("login-error");
  errorEl.classList.add("hidden");
  try {
    await api("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) });
    showApp();
  } catch (err) {
    errorEl.textContent = "Invalid username or password.";
    errorEl.classList.remove("hidden");
  }
});

document.getElementById("logout-btn").addEventListener("click", async () => {
  await api("/auth/logout", { method: "POST" });
  showLogin();
});

async function checkAuth() {
  try {
    const me = await api("/auth/me");
    if (me.user) {
      showApp();
    } else {
      showLogin();
    }
  } catch {
    showLogin();
  }
}

// ---------- Tabs ----------

document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.add("hidden"));
    document.getElementById(`${btn.dataset.tab}-tab`).classList.remove("hidden");
    if (btn.dataset.tab === "history") loadRuns();
  });
});

// ---------- Jobs ----------

let jobsCache = [];
let runningPollers = new Set();

function statusBadge(status) {
  return `<span class="status-badge status-${status}">${status}</span>`;
}

async function loadJobs() {
  jobsCache = await api("/api/jobs");
  const tbody = document.getElementById("jobs-tbody");
  tbody.innerHTML = "";

  const jobFilterSelect = document.getElementById("filter-job");
  jobFilterSelect.innerHTML = '<option value="">All jobs</option>';
  jobsCache.forEach((j) => {
    const opt = document.createElement("option");
    opt.value = j.id;
    opt.textContent = j.name;
    jobFilterSelect.appendChild(opt);
  });

  for (const job of jobsCache) {
    const lastRun = await getLastRun(job.id);
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(job.name)}</td>
      <td>${job.backup_type}</td>
      <td>${describeEndpoint(job.source_type, job.source_config)}</td>
      <td>${describeEndpoint(job.destination_type, job.destination_config)}</td>
      <td>${lastRun ? new Date(lastRun.started_at).toLocaleString() : "—"}</td>
      <td>${statusBadge(lastRun ? lastRun.status : "idle")}</td>
      <td class="row-actions">
        <button data-action="run" title="Run Now">▶</button>
        <button data-action="edit" title="Edit">✎</button>
        <button data-action="delete" title="Delete">🗑</button>
      </td>
    `;
    tr.querySelector('[data-action="run"]').addEventListener("click", (e) => { e.stopPropagation(); runJob(job.id); });
    tr.querySelector('[data-action="edit"]').addEventListener("click", (e) => { e.stopPropagation(); openJobModal(job); });
    tr.querySelector('[data-action="delete"]').addEventListener("click", (e) => { e.stopPropagation(); deleteJob(job.id); });
    tbody.appendChild(tr);
  }
}

async function getLastRun(jobId) {
  const runs = await api(`/api/runs?job_id=${jobId}`);
  return runs[0] || null;
}

function describeEndpoint(type, config) {
  if (type === "local") return `local:${config.path || ""}`;
  if (type === "nfs") return `nfs://${config.host || ""}${config.export_path || ""}`;
  if (type === "smb") return `smb://${config.host || ""}/${config.share || ""}`;
  if (type === "s3") return `s3://${config.bucket || ""}/${config.prefix || ""}`;
  return type;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

async function runJob(jobId) {
  try {
    const run = await api(`/api/jobs/${jobId}/run`, { method: "POST" });
    toast("Job started", "info");
    pollRun(run.id);
  } catch (err) {
    toast(err.message, "error");
  }
}

function pollRun(runId) {
  if (runningPollers.has(runId)) return;
  runningPollers.add(runId);
  const interval = setInterval(async () => {
    const run = await api(`/api/runs/${runId}`);
    if (run.status !== "running") {
      clearInterval(interval);
      runningPollers.delete(runId);
      toast(`Run #${run.id} ${run.status}`, run.status === "success" ? "success" : "error");
      loadJobs();
      loadRuns();
    }
  }, 2000);
}

async function deleteJob(jobId) {
  if (!confirm("Delete this job? This cannot be undone.")) return;
  await api(`/api/jobs/${jobId}`, { method: "DELETE" });
  toast("Job deleted", "info");
  loadJobs();
}

// ---------- Job modal ----------

const configFieldDefs = {
  local: [{ key: "path", label: "Path", type: "text" }],
  nfs: [
    { key: "host", label: "Host", type: "text" },
    { key: "export_path", label: "Export Path", type: "text" },
    { key: "mount_options", label: "Mount Options", type: "text" },
    { key: "path", label: "Subpath (optional)", type: "text" },
  ],
  smb: [
    { key: "host", label: "Host", type: "text" },
    { key: "share", label: "Share Name", type: "text" },
    { key: "username", label: "Username", type: "text" },
    { key: "password", label: "Password", type: "password" },
    { key: "domain", label: "Domain (optional)", type: "text" },
    { key: "mount_options", label: "Mount Options", type: "text" },
    { key: "path", label: "Subpath (optional)", type: "text" },
  ],
  s3: [
    { key: "bucket", label: "Bucket", type: "text" },
    { key: "prefix", label: "Prefix/Path", type: "text" },
    { key: "region", label: "Region", type: "text" },
    { key: "access_key", label: "Access Key (optional override)", type: "text" },
    { key: "secret_key", label: "Secret Key (optional override)", type: "password" },
  ],
};

function renderConfigFields(containerId, type, values = {}) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";
  (configFieldDefs[type] || []).forEach((field) => {
    const label = document.createElement("label");
    label.textContent = field.label;
    const input = document.createElement("input");
    input.type = field.type;
    input.dataset.key = field.key;
    input.value = values[field.key] || "";
    label.appendChild(input);
    container.appendChild(label);
  });
}

function collectConfig(containerId) {
  const container = document.getElementById(containerId);
  const config = {};
  container.querySelectorAll("input").forEach((input) => {
    if (input.value) config[input.dataset.key] = input.value;
  });
  return config;
}

document.getElementById("job-source-type").addEventListener("change", (e) => {
  renderConfigFields("source-config", e.target.value);
});
document.getElementById("job-destination-type").addEventListener("change", (e) => {
  renderConfigFields("destination-config", e.target.value);
});

document.getElementById("job-backup-type").addEventListener("change", (e) => {
  updateTypeFields(e.target.value);
});

function updateTypeFields(backupType) {
  document.getElementById("sql-fields").classList.toggle("hidden", backupType !== "sql");
  document.getElementById("s3job-fields").classList.toggle("hidden", backupType !== "s3");
  document.getElementById("filecopy-fields").classList.toggle("hidden", backupType !== "filecopy");
}

function openJobModal(job = null) {
  const modal = document.getElementById("job-modal");
  document.getElementById("job-modal-title").textContent = job ? "Edit Job" : "Create Job";
  document.getElementById("job-id").value = job ? job.id : "";
  document.getElementById("job-name").value = job ? job.name : "";
  document.getElementById("job-description").value = job ? job.description || "" : "";
  document.getElementById("job-backup-type").value = job ? job.backup_type : "sql";
  document.getElementById("job-source-type").value = job ? job.source_type : "local";
  document.getElementById("job-destination-type").value = job ? job.destination_type : "local";
  document.getElementById("job-notify-success").checked = job ? job.notify_on_success : false;
  document.getElementById("job-enabled").checked = job ? job.enabled : true;

  renderConfigFields("source-config", job ? job.source_type : "local", job ? job.source_config : {});
  renderConfigFields("destination-config", job ? job.destination_type : "local", job ? job.destination_config : {});
  updateTypeFields(job ? job.backup_type : "sql");

  const bc = job ? job.backup_config : {};
  document.getElementById("sql-engine").value = bc.engine || "postgresql";
  document.getElementById("sql-host").value = bc.host || "";
  document.getElementById("sql-port").value = bc.port || "";
  document.getElementById("sql-database").value = bc.database || "";
  document.getElementById("sql-username").value = bc.username || "";
  document.getElementById("sql-password").value = bc.password || "";
  document.getElementById("sql-output-format").value = bc.output_format || "sql";
  document.getElementById("s3job-mode").value = bc.mode || "copy";
  document.getElementById("s3job-direction").value = bc.direction || "upload";
  document.getElementById("filecopy-mode").value = bc.mode || "rsync";
  document.getElementById("filecopy-delete").checked = bc.delete || false;

  modal.classList.remove("hidden");
}

document.getElementById("create-job-btn").addEventListener("click", () => openJobModal());
document.getElementById("job-cancel-btn").addEventListener("click", () => {
  document.getElementById("job-modal").classList.add("hidden");
});

function buildBackupConfig(backupType) {
  if (backupType === "sql") {
    return {
      engine: document.getElementById("sql-engine").value,
      host: document.getElementById("sql-host").value,
      port: Number(document.getElementById("sql-port").value) || undefined,
      database: document.getElementById("sql-database").value,
      username: document.getElementById("sql-username").value,
      password: document.getElementById("sql-password").value,
      output_format: document.getElementById("sql-output-format").value,
    };
  }
  if (backupType === "s3") {
    return {
      mode: document.getElementById("s3job-mode").value,
      direction: document.getElementById("s3job-direction").value,
    };
  }
  if (backupType === "filecopy") {
    return {
      mode: document.getElementById("filecopy-mode").value,
      delete: document.getElementById("filecopy-delete").checked,
    };
  }
  return {};
}

document.getElementById("job-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = document.getElementById("job-id").value;
  const backupType = document.getElementById("job-backup-type").value;
  const payload = {
    name: document.getElementById("job-name").value,
    description: document.getElementById("job-description").value,
    source_type: document.getElementById("job-source-type").value,
    source_config: collectConfig("source-config"),
    destination_type: document.getElementById("job-destination-type").value,
    destination_config: collectConfig("destination-config"),
    backup_type: backupType,
    backup_config: buildBackupConfig(backupType),
    notify_on_success: document.getElementById("job-notify-success").checked,
    enabled: document.getElementById("job-enabled").checked,
  };

  try {
    if (id) {
      await api(`/api/jobs/${id}`, { method: "PUT", body: JSON.stringify(payload) });
      toast("Job updated", "success");
    } else {
      await api("/api/jobs", { method: "POST", body: JSON.stringify(payload) });
      toast("Job created", "success");
    }
    document.getElementById("job-modal").classList.add("hidden");
    loadJobs();
  } catch (err) {
    toast(err.message, "error");
  }
});

// ---------- History & Logs ----------

async function loadRuns() {
  const jobId = document.getElementById("filter-job").value;
  const statusFilter = document.getElementById("filter-status").value;
  const params = new URLSearchParams();
  if (jobId) params.set("job_id", jobId);
  if (statusFilter) params.set("status_filter", statusFilter);

  const runs = await api(`/api/runs?${params.toString()}`);
  const jobsById = Object.fromEntries(jobsCache.map((j) => [j.id, j.name]));
  const tbody = document.getElementById("runs-tbody");
  tbody.innerHTML = "";

  runs.forEach((run) => {
    const tr = document.createElement("tr");
    const duration = run.duration_seconds ? `${run.duration_seconds.toFixed(1)}s` : "—";
    tr.innerHTML = `
      <td>${escapeHtml(jobsById[run.job_id] || `#${run.job_id}`)}</td>
      <td>${new Date(run.started_at).toLocaleString()}</td>
      <td>${run.ended_at ? new Date(run.ended_at).toLocaleString() : "—"}</td>
      <td>${duration}</td>
      <td>${statusBadge(run.status)}</td>
    `;
    tr.addEventListener("click", () => openLogModal(run.id));
    tbody.appendChild(tr);
  });
}

document.getElementById("filter-job").addEventListener("change", loadRuns);
document.getElementById("filter-status").addEventListener("change", loadRuns);

async function openLogModal(runId) {
  const run = await api(`/api/runs/${runId}`);
  document.getElementById("log-content").textContent = run.log_output || "(no output)";
  document.getElementById("log-modal").classList.remove("hidden");
}

document.getElementById("log-close-btn").addEventListener("click", () => {
  document.getElementById("log-modal").classList.add("hidden");
});

// ---------- Notifications ----------

let seenNotificationIds = new Set();

async function pollNotifications() {
  try {
    const notifications = await api("/api/notifications?unread_only=true");
    document.getElementById("notif-count").textContent = notifications.length;
    document.getElementById("notif-count").classList.toggle("hidden", notifications.length === 0);
    notifications.forEach((n) => {
      if (!seenNotificationIds.has(n.id)) {
        seenNotificationIds.add(n.id);
      }
    });
  } catch {
    // ignore transient polling errors
  }
  setTimeout(pollNotifications, 5000);
}

document.getElementById("notif-btn").addEventListener("click", async () => {
  const notifications = await api("/api/notifications");
  const lines = notifications.slice(0, 10).map((n) => `[${n.level}] ${n.message}`).join("\n");
  alert(lines || "No notifications yet.");
  for (const n of notifications.filter((n) => !n.read)) {
    await api(`/api/notifications/${n.id}/read`, { method: "POST" });
  }
  pollNotifications();
});

checkAuth();
