// Tests des fonctions pures de l'extension :  node --test tests/
const test = require("node:test");
const assert = require("node:assert/strict");
const lib = require("../chrome-extension/lib.js");
const { CONFIG } = require("../chrome-extension/config.js");

const items = [
  { text: "great video", author: "@a", sentiment: 1, confidence: 0.9 },
  { text: "so bad", author: "@b", sentiment: -1, confidence: 0.8 },
  { text: "what mic?", author: "@c", sentiment: 0, confidence: 0.7 },
  { text: "love it, great", author: "@d", sentiment: 1, confidence: 0.6, isReply: true },
  { text: "!!!", author: "@e", sentiment: 0, confidence: 0, skipped: true },
];

test("chunk découpe en lots et garde l'ordre", () => {
  assert.deepEqual(lib.chunk([1, 2, 3, 4, 5], 2), [[1, 2], [3, 4], [5]]);
  assert.deepEqual(lib.chunk([], 3), []);
  assert.equal(lib.chunk(Array.from({ length: 250 }, (_, i) => i), CONFIG.BATCH_SIZE).length, 3);
  assert.throws(() => lib.chunk([1], 0));
});

test("videoIdFromUrl reconnaît les formats YouTube", () => {
  assert.equal(lib.videoIdFromUrl("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42"), "dQw4w9WgXcQ");
  assert.equal(lib.videoIdFromUrl("https://youtu.be/abc123"), "abc123");
  assert.equal(lib.videoIdFromUrl("https://www.youtube.com/shorts/xyz_9"), "xyz_9");
  assert.equal(lib.videoIdFromUrl("https://www.youtube.com/feed/trending"), null);
  assert.equal(lib.videoIdFromUrl("https://example.com/watch?v=abc"), null);
  assert.equal(lib.videoIdFromUrl("pas une url"), null);
});

test("normalizeApiUrl nettoie l'URL saisie", () => {
  assert.equal(lib.normalizeApiUrl(" https://x-7860.app.github.dev/ "), "https://x-7860.app.github.dev");
  assert.equal(lib.normalizeApiUrl("x-7860.app.github.dev"), "https://x-7860.app.github.dev");
  assert.equal(lib.normalizeApiUrl("localhost:7860"), "http://localhost:7860");
  assert.equal(lib.normalizeApiUrl(""), "");
});

test("computeStats exclut les commentaires ignorés des pourcentages", () => {
  const s = lib.computeStats(items);
  assert.equal(s.total, 5);
  assert.equal(s.analyzed, 4);
  assert.equal(s.skipped, 1);
  assert.equal(s.pos, 2);
  assert.equal(s.posPct, 50);
  assert.equal(s.posPct + s.neuPct + s.negPct, 100);
  assert.equal(s.score, 0.25);
  assert.equal(lib.computeStats([]).score, 0);
});

test("filterItems filtre, cherche et trie", () => {
  assert.equal(lib.filterItems(items, { filter: "1" }).length, 2);
  assert.equal(lib.filterItems(items, { filter: "0" }).length, 1); // l'ignoré n'est pas « neutre »
  assert.equal(lib.filterItems(items, { search: "GREAT" }).length, 2);
  assert.equal(lib.filterItems(items, { search: "@b" }).length, 1);
  assert.deepEqual(lib.filterItems(items, { filter: "1", sort: "conf-asc" }).map((i) => i.confidence), [0.6, 0.9]);
  assert.equal(lib.filterItems(items).length, 5);
});

test("toCsv échappe guillemets, virgules et retours à la ligne", () => {
  const csv = lib.toCsv([{ text: 'il a dit "wow", puis\nrien', author: "@x", sentiment: 1, confidence: 0.5 }]);
  assert.ok(csv.startsWith("﻿"));
  assert.ok(csv.includes('"il a dit ""wow"", puis\nrien"'));
});

test("summaryText résume les résultats", () => {
  const txt = lib.summaryText({ title: "Vidéo", url: "https://youtu.be/x", stats: lib.computeStats(items) }, items.slice(0, 2));
  assert.match(txt, /4 commentaires analysés \(1 ignorés\)/);
  assert.match(txt, /\[Positif 90 %\] @a : great video/);
});

test("apiErrorMessage donne un message lisible", () => {
  assert.match(lib.apiErrorMessage(503, { detail: "x" }), /modèle n'est pas chargé/);
  assert.match(lib.apiErrorMessage(422, { error: "Données invalides", details: [{ message: "vide" }] }), /422.*Données invalides.*vide/);
});

test("verdict traduit le score en mots", () => {
  assert.equal(lib.verdict(0.7, 10).label, "Très positif");
  assert.equal(lib.verdict(0.2, 10).tone, "pos");
  assert.equal(lib.verdict(0, 10).label, "Avis partagés");
  assert.equal(lib.verdict(-0.3, 10).tone, "neg");
  assert.equal(lib.verdict(-0.9, 10).label, "Très négatif");
  assert.equal(lib.verdict(0, 0).label, "Pas assez de commentaires");
});

test("topComments renvoie les plus marqués, sans les ignorés", () => {
  assert.deepEqual(lib.topComments(items, 1, 2).map((i) => i.author), ["@a", "@d"]);
  assert.equal(lib.topComments(items, -1)[0].author, "@b");
  assert.equal(lib.topComments([], 1).length, 0);
});
