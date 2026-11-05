/**
 * Fonctions pures partagées par le service worker et le popup (et testées avec `node --test`).
 * Aucune dépendance au navigateur ici.
 */
var SENTIMENTS = [
  { key: "1", value: 1, label: "Positif", cls: "pos" },
  { key: "0", value: 0, label: "Neutre", cls: "neu" },
  { key: "-1", value: -1, label: "Négatif", cls: "neg" },
];
var LABEL_BY_KEY = { "1": "Positif", "0": "Neutre", "-1": "Négatif" };
var CLASS_BY_KEY = { "1": "pos", "0": "neu", "-1": "neg" };

/** Découpe un tableau en lots de `size` éléments. */
function chunk(items, size) {
  if (!Number.isInteger(size) || size < 1) throw new Error("taille de lot invalide");
  const out = [];
  for (let i = 0; i < items.length; i += size) out.push(items.slice(i, i + size));
  return out;
}

/** Identifiant de vidéo YouTube depuis une URL (/watch?v=…, /shorts/…, youtu.be/…), sinon null. */
function videoIdFromUrl(url) {
  try {
    const u = new URL(url);
    if (u.hostname === "youtu.be") return u.pathname.slice(1) || null;
    if (!/(^|\.)youtube\.com$/.test(u.hostname)) return null;
    if (u.pathname === "/watch") return u.searchParams.get("v");
    const m = u.pathname.match(/^\/shorts\/([\w-]+)/);
    return m ? m[1] : null;
  } catch {
    return null;
  }
}

/** Normalise l'URL d'API saisie par l'utilisateur (espaces, slash final, schéma manquant). */
function normalizeApiUrl(url) {
  let u = String(url || "").trim().replace(/\/+$/, "");
  if (u && !/^https?:\/\//i.test(u)) u = (/^(localhost|127\.0\.0\.1)/.test(u) ? "http://" : "https://") + u;
  return u;
}

/** Statistiques globales ; les commentaires `skipped` sont exclus des pourcentages. */
function computeStats(items) {
  const analyzed = items.filter((it) => !it.skipped);
  const n = analyzed.length;
  const c = { "1": 0, "0": 0, "-1": 0 };
  let conf = 0;
  for (const it of analyzed) {
    c[String(it.sentiment)]++;
    conf += it.confidence;
  }
  const pct = (k) => (n ? (100 * c[k]) / n : 0);
  return {
    total: items.length,
    analyzed: n,
    skipped: items.length - n,
    pos: c["1"], neu: c["0"], neg: c["-1"],
    posPct: pct("1"), neuPct: pct("0"), negPct: pct("-1"),
    avgConf: n ? conf / n : 0,
    score: n ? (c["1"] - c["-1"]) / n : 0,
  };
}

/** Filtre / recherche / tri de la liste affichée. */
function filterItems(items, { filter = "all", search = "", sort = "order" } = {}) {
  const q = search.trim().toLowerCase();
  let out = items.filter((it) => {
    if (filter !== "all" && (it.skipped || String(it.sentiment) !== filter)) return false;
    return !q || it.text.toLowerCase().includes(q) || (it.author || "").toLowerCase().includes(q);
  });
  if (sort === "conf-desc") out = [...out].sort((a, b) => b.confidence - a.confidence);
  if (sort === "conf-asc") out = [...out].sort((a, b) => a.confidence - b.confidence);
  return out;
}

function labelOf(it) {
  return it.skipped ? "Ignoré" : LABEL_BY_KEY[String(it.sentiment)];
}

function csvEscape(v) {
  const s = String(v ?? "");
  return /[",\n\r;]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

/** Export CSV (UTF-8 avec BOM pour Excel). */
function toCsv(items) {
  const rows = [["auteur", "commentaire", "sentiment", "label", "confiance", "reponse", "ignore"].join(",")];
  for (const it of items) {
    rows.push([csvEscape(it.author), csvEscape(it.text), it.sentiment, csvEscape(labelOf(it)),
      it.confidence, it.isReply ? 1 : 0, it.skipped ? 1 : 0].join(","));
  }
  return "﻿" + rows.join("\n");
}

/** Texte copié dans le presse-papiers. */
function summaryText(result, items) {
  const s = result.stats;
  const lines = [
    `Analyse de sentiment — ${result.title || "vidéo YouTube"}`,
    result.url || "",
    `${s.analyzed} commentaires analysés${s.skipped ? ` (${s.skipped} ignorés)` : ""}`,
    `Positif ${s.posPct.toFixed(1)} % (${s.pos}) · Neutre ${s.neuPct.toFixed(1)} % (${s.neu}) · Négatif ${s.negPct.toFixed(1)} % (${s.neg})`,
    `Score global ${s.score >= 0 ? "+" : ""}${s.score.toFixed(2)} · Confiance moyenne ${(s.avgConf * 100).toFixed(1)} %`,
    "",
  ];
  for (const it of items) {
    const conf = it.skipped ? "" : ` ${(it.confidence * 100).toFixed(0)} %`;
    lines.push(`[${labelOf(it)}${conf}] ${it.author ? it.author + " : " : ""}${it.text.replace(/\s+/g, " ")}`);
  }
  return lines.join("\n");
}

/** Verdict en mots à partir du score (-1 à +1). */
function verdict(score, analyzed) {
  if (!analyzed) return { label: "Pas assez de commentaires", tone: "neu" };
  if (score >= 0.5) return { label: "Très positif", tone: "pos" };
  if (score >= 0.15) return { label: "Plutôt positif", tone: "pos" };
  if (score > -0.15) return { label: "Avis partagés", tone: "neu" };
  if (score > -0.5) return { label: "Plutôt négatif", tone: "neg" };
  return { label: "Très négatif", tone: "neg" };
}

/** Commentaires les plus marqués d'un sentiment (confiance la plus haute). */
function topComments(items, sentiment, n = 1) {
  return items
    .filter((it) => !it.skipped && it.sentiment === sentiment)
    .sort((a, b) => b.confidence - a.confidence)
    .slice(0, n);
}

/** Message d'erreur lisible à partir d'une réponse d'API. */
function apiErrorMessage(status, body) {
  const detail = body && (body.detail || body.error);
  const extra = body && Array.isArray(body.details) && body.details.length
    ? " (" + body.details.map((d) => d.message).join(", ") + ")" : "";
  if (status === 503) return "Le modèle n'est pas chargé sur le serveur (fichiers .joblib manquants ?).";
  return `Erreur API ${status} : ${typeof detail === "string" ? detail : JSON.stringify(detail)}${extra}`;
}

if (typeof module !== "undefined") {
  module.exports = { SENTIMENTS, verdict, topComments, chunk, videoIdFromUrl, normalizeApiUrl, computeStats, filterItems, labelOf, toCsv, summaryText, apiErrorMessage };
}
