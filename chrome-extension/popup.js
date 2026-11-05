/**
 * Popup Écho : accueil / progression / erreur / résultats (onglets Aperçu et Commentaires).
 * L'analyse tourne dans le service worker (background.js) ; le popup suit sa progression
 * via chrome.storage et peut être fermé puis rouvert sans rien perdre.
 */
const $ = (id) => document.getElementById(id);
const FACE = { "1": "face-pos", "0": "face-neu", "-1": "face-neg" };
const SORTS = [
  { key: "order", title: "Tri : ordre de la page" },
  { key: "conf-desc", title: "Tri : confiance décroissante" },
  { key: "conf-asc", title: "Tri : confiance croissante" },
];

const state = {
  settings: { ...CONFIG.DEFAULT_SETTINGS },
  tab: null,
  videoId: null,
  result: null,
  tabView: "overview",
  view: { filter: "all", search: "", sort: "order" },
};

const svgUse = (id, cls = "") => `<svg viewBox="0 0 24 24" class="${cls}"><use href="#${id}"/></svg>`;
const fmtPct = (x) => `${Math.round(x)} %`;

/* ---------------- Réglages & thème ---------------- */
async function loadSettings() {
  const { settings } = await chrome.storage.local.get("settings");
  state.settings = { ...CONFIG.DEFAULT_SETTINGS, ...(settings || {}) };
  $("apiUrl").value = state.settings.apiUrl;
  $("maxComments").value = state.settings.maxComments;
  $("maxLabel").textContent = state.settings.maxComments;
  $("autoScroll").checked = state.settings.autoScroll;
  $("includeReplies").checked = state.settings.includeReplies;
  const dark = state.settings.theme ? state.settings.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  applyTheme(dark);
}

async function saveSettings() {
  const max = Math.min(1000, Math.max(10, parseInt($("maxComments").value, 10) || 100));
  state.settings = {
    ...state.settings,
    apiUrl: normalizeApiUrl($("apiUrl").value) || DEFAULT_API_URL,
    maxComments: max,
    autoScroll: $("autoScroll").checked,
    includeReplies: $("includeReplies").checked,
  };
  $("apiUrl").value = state.settings.apiUrl;
  await chrome.storage.local.set({ settings: state.settings });
}

function applyTheme(dark) {
  document.body.classList.toggle("dark", dark);
  $("iconMoon").hidden = dark;
  $("iconSun").hidden = !dark;
}

async function toggleTheme() {
  const dark = !document.body.classList.contains("dark");
  applyTheme(dark);
  state.settings.theme = dark ? "dark" : "light";
  await chrome.storage.local.set({ settings: state.settings });
}

function toast(msg) {
  const t = $("feedback");
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(toast.t);
  toast.t = setTimeout(() => (t.hidden = true), 2200);
}

/* ---------------- API ---------------- */
async function checkHealth(verbose = false) {
  const el = $("apiStatus");
  el.className = "api";
  $("apiStatusText").textContent = "…";
  const base = normalizeApiUrl(state.settings.apiUrl);
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 8000);
  try {
    const res = await fetch(`${base}/health`, { signal: ctrl.signal });
    if (!(res.headers.get("content-type") || "").includes("json")) throw new Error("port privé ?");
    const h = await res.json();
    const ok = res.ok && h.model_loaded;
    el.classList.add(ok ? "ok" : "ko");
    $("apiStatusText").textContent = ok ? "en ligne" : "sans modèle";
    el.title = ok ? `${base}\nModèle ${h.model_name} · version ${h.model_version}` : (h.error || "Modèle non chargé");
    if (verbose) toast(ok ? `Connexion réussie · modèle ${h.model_version}` : "API joignable, mais modèle absent");
    return ok;
  } catch {
    el.classList.add("ko");
    $("apiStatusText").textContent = "hors ligne";
    el.title = base;
    if (verbose) showError(`Impossible de joindre ${base}.\nVérifiez l'adresse, que le serveur tourne et (Codespaces) que le port 7860 est « Public ».`);
    return false;
  } finally {
    clearTimeout(timer);
  }
}

/* ---------------- États ---------------- */
function show(view) {
  for (const id of ["idle", "progress", "errorBox"]) $(id).hidden = view !== id;
  const results = view === "results";
  $("tabs").hidden = !results;
  $("overview").hidden = !(results && state.tabView === "overview");
  $("comments").hidden = !(results && state.tabView === "comments");
}

function showError(msg) {
  $("errorText").textContent = msg;
  show("errorBox");
}

function showProgress(job) {
  show("progress");
  $("progressText").textContent = job.message || "Analyse en cours…";
  const ring = $("ringFg");
  if (job.status === "analyzing" && job.total) {
    $("progress").classList.remove("spin");
    const p = job.done / job.total;
    ring.style.strokeDashoffset = String(201 * (1 - Math.max(0.06, p)));
    $("progressCount").textContent = `${Math.round(p * 100)}%`;
  } else {
    $("progress").classList.add("spin");
    ring.style.strokeDashoffset = "150";
    $("progressCount").textContent = "";
  }
}

function switchTab(name) {
  state.tabView = name;
  document.querySelectorAll("#tabs button").forEach((b) => {
    const on = b.dataset.tab === name;
    b.classList.toggle("on", on);
    b.setAttribute("aria-selected", String(on));
  });
  show("results");
}

/* ---------------- Aperçu ---------------- */
function point(angleDeg, r) {
  const a = (angleDeg * Math.PI) / 180;
  return [110 + r * Math.cos(a), 108 - r * Math.sin(a)];
}

function arc(from, to, r) {
  const [x1, y1] = point(from, r);
  const [x2, y2] = point(to, r);
  return `M${x1.toFixed(1)} ${y1.toFixed(1)} A${r} ${r} 0 0 1 ${x2.toFixed(1)} ${y2.toFixed(1)}`;
}

function renderGauge(score) {
  const R = 86;
  const deg = Math.max(-1, Math.min(1, score)) * 90; // -1 -> à gauche, +1 -> à droite
  $("gauge").innerHTML = `
    <path d="${arc(180, 124, R)}" stroke="var(--neg)" stroke-width="14"/>
    <path d="${arc(118, 62, R)}" stroke="var(--neu)" stroke-width="14"/>
    <path d="${arc(56, 0, R)}" stroke="var(--pos)" stroke-width="14"/>
    <g class="needle" style="transform: rotate(${deg}deg)">
      <path d="M110 108 L110 38" stroke="var(--ink)" stroke-width="3.5"/>
    </g>
    <circle cx="110" cy="108" r="8" fill="var(--ink)" stroke="none"/>
    <circle cx="110" cy="108" r="3" fill="var(--card)" stroke="none"/>
    <text x="22" y="126" class="lbl" text-anchor="middle">négatif</text>
    <text x="110" y="10" class="lbl" text-anchor="middle">partagé</text>
    <text x="198" y="126" class="lbl" text-anchor="middle">positif</text>`;
}

function renderOverview() {
  const r = state.result;
  const s = r.stats;
  renderGauge(s.score);
  const v = verdict(s.score, s.analyzed);
  $("verdict").textContent = v.label;
  $("verdict").className = `verdict ${v.tone}`;
  $("analyzedLine").textContent = `Score ${s.score >= 0 ? "+" : "−"}${Math.abs(s.score).toFixed(2)} · ${s.analyzed} commentaire${s.analyzed > 1 ? "s" : ""} analysé${s.analyzed > 1 ? "s" : ""}` +
    (s.skipped ? ` · ${s.skipped} ignoré${s.skipped > 1 ? "s" : ""}` : "");

  const rows = $("rows");
  rows.innerHTML = "";
  for (const [key, cls, name, n, p] of [["1", "pos", "Positif", s.pos, s.posPct], ["0", "neu", "Neutre", s.neu, s.neuPct], ["-1", "neg", "Négatif", s.neg, s.negPct]]) {
    const li = document.createElement("li");
    li.className = `row ${cls}`;
    li.innerHTML = `${svgUse(FACE[key])}<span class="row-name">${name}</span>
      <span class="track"><span style="width:${p}%"></span></span>
      <span class="row-pct">${fmtPct(p)}<small>${n}</small></span>`;
    rows.appendChild(li);
  }

  // Commentaires les plus marqués
  const box = $("standouts");
  box.innerHTML = "";
  for (const [sent, cls, title] of [[1, "pos", "Le plus enthousiaste"], [-1, "neg", "Le plus critique"]]) {
    const [it] = topComments(r.items, sent);
    if (!it) continue;
    const q = document.createElement("figure");
    q.className = `quote ${cls}`;
    const head = document.createElement("div");
    head.className = "quote-head";
    head.textContent = `${title} · ${Math.round(it.confidence * 100)} %`;
    const p = document.createElement("p");
    p.textContent = `« ${it.text} »`;
    q.append(head, p);
    if (it.author) {
      const f = document.createElement("footer");
      f.textContent = it.author;
      q.appendChild(f);
    }
    box.appendChild(q);
  }

  const parts = [`API ${Math.round(r.apiMs)} ms`, `${(r.totalMs / 1000).toFixed(1)} s au total`, `confiance ${Math.round(s.avgConf * 100)} %`];
  if (r.modelVersion) parts.push(`modèle ${r.modelVersion}`);
  $("meta").textContent = parts.join(" · ");
}

/* ---------------- Commentaires ---------------- */
function renderCounts() {
  const s = state.result.stats;
  $("cAll").textContent = s.total;
  $("cPos").textContent = s.pos;
  $("cNeu").textContent = s.neu;
  $("cNeg").textContent = s.neg;
  $("tabCount").textContent = s.total;
}

function renderList() {
  const items = filterItems(state.result.items, state.view);
  const total = state.result.items.length;
  $("listCount").textContent = items.length === total ? `${total} commentaires` : `${items.length} sur ${total} commentaires`;
  const list = $("list");
  list.innerHTML = "";
  const frag = document.createDocumentFragment();
  for (const it of items) {
    const key = String(it.sentiment);
    const cls = it.skipped ? "skip" : CLASS_BY_KEY[key];
    const li = document.createElement("li");
    li.className = `card ${cls}`;
    li.title = it.skipped ? "Texte vide après nettoyage : exclu des statistiques"
      : Object.entries(it.probabilities || {}).map(([l, v]) => `${l} ${(v * 100).toFixed(0)} %`).join(" · ");

    const face = document.createElement("span");
    face.className = "face";
    face.innerHTML = svgUse(it.skipped ? "face-skip" : FACE[key]);
    face.setAttribute("aria-label", labelOf(it));

    const body = document.createElement("div");
    body.className = "card-body";
    const top = document.createElement("div");
    top.className = "card-top";
    const who = document.createElement("span");
    who.className = "who";
    who.textContent = it.author || "Anonyme";
    if (it.isReply) {
      const tag = document.createElement("span");
      tag.className = "tag";
      tag.textContent = "réponse";
      who.appendChild(tag);
    }
    const conf = document.createElement("span");
    conf.className = "conf";
    conf.textContent = it.skipped ? "ignoré" : `${labelOf(it)} · ${Math.round(it.confidence * 100)} %`;
    top.append(who, conf);
    const text = document.createElement("p");
    text.textContent = it.text;
    text.addEventListener("click", () => text.classList.toggle("open"));
    body.append(top, text);

    li.append(face, body);
    frag.appendChild(li);
  }
  list.appendChild(frag);
  $("emptyList").hidden = items.length > 0;
}

function renderResult() {
  renderOverview();
  renderCounts();
  renderList();
  show("results");
}

/* ---------------- Synchronisation avec le service worker ---------------- */
async function refresh() {
  if (!state.tab) return;
  const key = `job:${state.tab.id}`;
  const [{ [key]: job }, { results = {} }] = await Promise.all([
    chrome.storage.session.get(key),
    chrome.storage.local.get("results"),
  ]);
  const sameVideo = job && job.videoId === state.videoId;
  if (sameVideo && (job.status === "extracting" || job.status === "analyzing")) return showProgress(job);
  if (sameVideo && job.status === "error") return showError(job.error);
  const result = state.videoId && results[state.videoId];
  if (result) {
    state.result = result;
    return renderResult();
  }
  show("idle");
}

async function startAnalysis() {
  if (!state.videoId) return showError("Ouvrez une vidéo YouTube (youtube.com/watch?v=…) puis réessayez.");
  await saveSettings();
  showProgress({ status: "extracting", message: state.settings.autoScroll ? "Chargement des commentaires…" : "Lecture des commentaires visibles…" });
  await chrome.runtime.sendMessage({ type: "analyze", tabId: state.tab.id });
}

/* ---------------- Export ---------------- */
function download(name, content, type) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function closeMenu() {
  $("exportMenu").hidden = true;
  $("exportBtn").setAttribute("aria-expanded", "false");
}

const exportItems = () => filterItems(state.result.items, state.view);
const fileBase = () => `echo_${state.result.videoId}`;

/* ---------------- Initialisation ---------------- */
document.addEventListener("DOMContentLoaded", async () => {
  await loadSettings();
  // popup.html?tabId=N cible un onglet précis (tests automatisés, popup ouvert dans un onglet)
  const forcedTab = parseInt(new URLSearchParams(location.search).get("tabId"), 10);
  if (Number.isInteger(forcedTab)) state.tab = await chrome.tabs.get(forcedTab).catch(() => null);
  else [state.tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  state.videoId = state.tab?.url && /\/watch/.test(state.tab.url) ? videoIdFromUrl(state.tab.url) : null;

  if (state.videoId) {
    $("videoTitle").textContent = (state.tab.title || "").replace(/^\(\d+\)\s*/, "").replace(/ - YouTube$/, "");
    $("videoMeta").textContent = "Vidéo YouTube";
    $("thumb").style.backgroundImage = `url("https://i.ytimg.com/vi/${encodeURIComponent(state.videoId)}/mqdefault.jpg")`;
  } else {
    $("analyzeBtn").disabled = true;
  }

  $("analyzeBtn").addEventListener("click", startAnalysis);
  $("reanalyzeBtn").addEventListener("click", startAnalysis);
  $("retryBtn").addEventListener("click", startAnalysis);
  $("themeBtn").addEventListener("click", toggleTheme);
  $("settingsBtn").addEventListener("click", () => {
    const open = $("settings").hidden;
    $("settings").hidden = !open;
    $("settingsBtn").setAttribute("aria-expanded", String(open));
  });
  $("maxComments").addEventListener("input", (e) => ($("maxLabel").textContent = e.target.value));
  $("saveSettingsBtn").addEventListener("click", async () => {
    await saveSettings();
    $("settings").hidden = true;
    $("settingsBtn").setAttribute("aria-expanded", "false");
    toast("Réglages enregistrés");
    checkHealth();
  });
  $("testApiBtn").addEventListener("click", async () => {
    await saveSettings();
    if (await checkHealth(true) && !$("errorBox").hidden) refresh();
  });

  $("tabs").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (b) switchTab(b.dataset.tab);
  });
  $("filters").addEventListener("click", (e) => {
    const chip = e.target.closest(".chip");
    if (!chip) return;
    document.querySelectorAll("#filters .chip").forEach((c) => c.classList.toggle("on", c === chip));
    state.view.filter = chip.dataset.filter;
    renderList();
  });
  $("searchBtn").addEventListener("click", () => {
    const input = $("search");
    input.hidden = !input.hidden;
    $("searchBtn").classList.toggle("on", !input.hidden);
    if (!input.hidden) input.focus();
    else if (state.view.search) { input.value = ""; state.view.search = ""; renderList(); }
  });
  $("search").addEventListener("input", (e) => { state.view.search = e.target.value; renderList(); });
  $("sortBtn").addEventListener("click", () => {
    const i = (SORTS.findIndex((s) => s.key === state.view.sort) + 1) % SORTS.length;
    state.view.sort = SORTS[i].key;
    $("sortBtn").title = SORTS[i].title;
    $("sortBtn").classList.toggle("on", i !== 0);
    toast(SORTS[i].title);
    renderList();
  });
  $("exportBtn").addEventListener("click", (e) => {
    e.stopPropagation();
    const open = $("exportMenu").hidden;
    $("exportMenu").hidden = !open;
    $("exportBtn").setAttribute("aria-expanded", String(open));
  });
  document.addEventListener("click", (e) => { if (!e.target.closest(".menu-wrap")) closeMenu(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeMenu(); });
  $("copyBtn").addEventListener("click", async () => {
    closeMenu();
    try {
      await navigator.clipboard.writeText(summaryText(state.result, exportItems()));
      toast(state.view.filter === "all" && !state.view.search ? "Résultats copiés" : "Sélection copiée");
    } catch {
      toast("Copie impossible");
    }
  });
  $("csvBtn").addEventListener("click", () => { closeMenu(); download(`${fileBase()}.csv`, toCsv(exportItems()), "text/csv;charset=utf-8"); toast("CSV téléchargé"); });
  $("jsonBtn").addEventListener("click", () => {
    closeMenu();
    const { items, ...rest } = state.result;
    download(`${fileBase()}.json`, JSON.stringify({ ...rest, filter: state.view, items: exportItems() }, null, 2), "application/json");
    toast("JSON téléchargé");
  });

  chrome.storage.onChanged.addListener((changes, area) => {
    if ((area === "session" && state.tab && changes[`job:${state.tab.id}`]) || (area === "local" && changes.results)) refresh();
  });

  await refresh();
  checkHealth();
});
