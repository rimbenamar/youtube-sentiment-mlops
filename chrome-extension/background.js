/**
 * Service worker : exécute l'analyse en arrière-plan.
 *
 * Le popup se ferme dès qu'on clique ailleurs ; si l'analyse tournait dans le popup, elle serait perdue.
 * Ici elle continue, la progression est écrite dans chrome.storage.session (clé job:<tabId>)
 * et le résultat final dans chrome.storage.local (clé results, une entrée par vidéo).
 */
importScripts("config.js", "lib.js");

const jobKey = (tabId) => `job:${tabId}`;

async function getSettings() {
  const { settings } = await chrome.storage.local.get("settings");
  return { ...CONFIG.DEFAULT_SETTINGS, ...(settings || {}) };
}

async function setJob(tabId, job) {
  await chrome.storage.session.set({ [jobKey(tabId)]: { ...job, updatedAt: Date.now() } });
}

async function fetchJson(url, options = {}, timeout = CONFIG.REQUEST_TIMEOUT_MS) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeout);
  try {
    const res = await fetch(url, { ...options, signal: ctrl.signal });
    const type = res.headers.get("content-type") || "";
    if (!type.includes("application/json")) {
      throw new Error(`Réponse inattendue (HTTP ${res.status}). Si l'API est sur Codespaces, vérifiez que le port 7860 est « Public ».`);
    }
    const body = await res.json();
    if (!res.ok) throw new Error(apiErrorMessage(res.status, body));
    return body;
  } catch (e) {
    if (e.name === "AbortError") throw new Error("Délai dépassé : l'API ne répond pas (Codespace arrêté ?).");
    if (e instanceof TypeError) throw new Error(`Impossible de joindre l'API (${url.replace(/\/predict_batch$/, "")}). Vérifiez l'URL et que le serveur est lancé.`);
    throw e;
  } finally {
    clearTimeout(timer);
  }
}

async function ensureContentScript(tabId) {
  try {
    await chrome.tabs.sendMessage(tabId, { action: "ping" });
  } catch {
    // Onglet ouvert avant l'installation de l'extension : on injecte le script maintenant.
    await chrome.scripting.executeScript({ target: { tabId }, files: ["content.js"] });
  }
}

async function predictAll(apiUrl, texts, onProgress) {
  const batches = chunk(texts, CONFIG.BATCH_SIZE);
  const results = new Array(batches.length);
  let next = 0, done = 0, apiMs = 0, modelVersion = null;
  async function worker() {
    while (next < batches.length) {
      const i = next++;
      const body = await fetchJson(`${apiUrl}/predict_batch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ comments: batches[i] }),
      });
      if (!Array.isArray(body.predictions) || body.predictions.length !== batches[i].length) {
        throw new Error("Réponse de l'API incohérente (nombre de prédictions).");
      }
      results[i] = body.predictions;
      apiMs += body.processing_time_ms || 0;
      modelVersion = body.model_version || modelVersion;
      await onProgress(++done, batches.length);
    }
  }
  await Promise.all(Array.from({ length: Math.min(CONFIG.MAX_PARALLEL, batches.length) }, worker));
  return { predictions: results.flat(), apiMs, modelVersion, batches: batches.length };
}

async function saveResult(result) {
  const { results = {} } = await chrome.storage.local.get("results");
  results[result.videoId] = result;
  // On ne garde que les analyses les plus récentes
  const keys = Object.keys(results).sort((a, b) => (results[b].date > results[a].date ? 1 : -1));
  for (const k of keys.slice(CONFIG.MAX_STORED_RESULTS)) delete results[k];
  await chrome.storage.local.set({ results });
}

const running = new Set();

async function analyze(tabId) {
  if (running.has(tabId)) return;
  running.add(tabId);
  const t0 = Date.now();
  try {
    const tab = await chrome.tabs.get(tabId);
    const videoId = videoIdFromUrl(tab.url);
    if (!videoId || !/\/watch/.test(tab.url)) throw new Error("Ouvrez une vidéo YouTube (youtube.com/watch?v=…).");
    const settings = await getSettings();
    const apiUrl = normalizeApiUrl(settings.apiUrl || DEFAULT_API_URL);

    await setJob(tabId, { status: "extracting", videoId, message: settings.autoScroll ? "Chargement des commentaires…" : "Lecture des commentaires visibles…" });
    await ensureContentScript(tabId);
    const ext = await chrome.tabs.sendMessage(tabId, {
      action: "extract",
      options: { max: settings.maxComments, autoScroll: settings.autoScroll, includeReplies: settings.includeReplies },
    });
    if (!ext?.ok) throw new Error(ext?.error || "Extraction impossible.");
    if (!ext.comments.length) throw new Error("Aucun commentaire trouvé. Faites défiler jusqu'aux commentaires puis réessayez.");

    const total = ext.comments.length;
    await setJob(tabId, { status: "analyzing", videoId, done: 0, total: Math.ceil(total / CONFIG.BATCH_SIZE), message: `Analyse de ${total} commentaires…` });
    const { predictions, apiMs, modelVersion, batches } = await predictAll(apiUrl, ext.comments.map((c) => c.text), (done, n) =>
      setJob(tabId, { status: "analyzing", videoId, done, total: n, message: `Analyse… lot ${done}/${n}` }));

    const items = ext.comments.map((c, i) => ({ ...predictions[i], ...c }));
    const result = {
      videoId, title: ext.title, url: ext.url, date: new Date().toISOString(),
      items, stats: computeStats(items), apiMs, totalMs: Date.now() - t0, modelVersion, batches, apiUrl,
    };
    await saveResult(result);
    await setJob(tabId, { status: "done", videoId });
  } catch (e) {
    const tab = await chrome.tabs.get(tabId).catch(() => null);
    await setJob(tabId, { status: "error", videoId: tab ? videoIdFromUrl(tab.url) : null, error: e.message || String(e) });
  } finally {
    running.delete(tabId);
  }
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.type === "analyze" && Number.isInteger(msg.tabId)) {
    analyze(msg.tabId); // ne pas attendre : le popup suit la progression via chrome.storage
    sendResponse({ started: true });
  }
  return false;
});

// Nettoyage de l'état d'un onglet fermé
chrome.tabs.onRemoved.addListener((tabId) => chrome.storage.session.remove(jobKey(tabId)));
