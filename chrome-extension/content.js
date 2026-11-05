/**
 * Content script : s'exécute dans la page YouTube et extrait les commentaires.
 *
 * YouTube charge les commentaires dynamiquement (au scroll), donc :
 *  1. on fait défiler jusqu'à la section commentaires pour déclencher le premier chargement ;
 *  2. si "chargement auto" est activé, on scrolle jusqu'à atteindre le nombre voulu
 *     ou jusqu'à ce que plus rien ne se charge ;
 *  3. on lit le DOM (sélecteurs ancien + nouveau format de YouTube).
 */
(() => {
  if (window.__ytSentimentLoaded) return; // évite une double injection
  window.__ytSentimentLoaded = true;

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  // Un commentaire = ytd-comment-view-model (nouveau DOM) ou ytd-comment-renderer (ancien DOM)
  const COMMENT_SELECTOR = "ytd-comment-view-model, ytd-comment-renderer";
  const THREAD_SELECTOR = "ytd-comment-thread-renderer";

  function countThreads() {
    return document.querySelectorAll(THREAD_SELECTOR).length;
  }

  function videoTitle() {
    const el =
      document.querySelector("ytd-watch-metadata h1 yt-formatted-string") ||
      document.querySelector("h1.ytd-watch-metadata") ||
      document.querySelector("h1.title");
    return (el?.textContent || document.title.replace(/ - YouTube$/, "")).trim();
  }

  async function ensureCommentsSection() {
    const section = document.querySelector("ytd-comments#comments, #comments");
    if (!section) return false;
    if (countThreads() > 0) return true;
    section.scrollIntoView({ behavior: "instant", block: "start" });
    for (let i = 0; i < 20 && countThreads() === 0; i++) {
      window.scrollBy(0, 400);
      await sleep(400);
    }
    return countThreads() > 0;
  }

  async function autoLoad(max, timeoutMs = 30000) {
    const start = Date.now();
    let last = -1;
    let stable = 0;
    while (countThreads() < max && Date.now() - start < timeoutMs) {
      window.scrollTo(0, document.documentElement.scrollHeight);
      await sleep(900);
      const n = countThreads();
      if (n === last) {
        stable += 1;
        if (stable >= 3) break; // plus rien ne se charge
      } else {
        stable = 0;
        last = n;
      }
    }
  }

  function readComments(max, includeReplies) {
    const seen = new Set();
    const out = [];
    for (const node of document.querySelectorAll(COMMENT_SELECTOR)) {
      const isReply = !!node.closest("ytd-comment-replies-renderer");
      if (isReply && !includeReplies) continue;
      const textEl = node.querySelector("#content-text");
      const text = (textEl?.innerText || "").trim();
      if (!text) continue;
      const author = (node.querySelector("#author-text")?.textContent || "").trim();
      const key = author + "|" + text;
      if (seen.has(key)) continue;
      seen.add(key);
      const likes = (node.querySelector("#vote-count-middle")?.textContent || "").trim();
      out.push({ id: out.length, author, text, likes, isReply });
      if (out.length >= max) break;
    }
    return out;
  }

  async function extract({ max = 100, autoScroll = true, includeReplies = false } = {}) {
    if (!location.pathname.startsWith("/watch")) {
      return { ok: false, error: "Ouvrez une vidéo YouTube (URL youtube.com/watch?v=…)." };
    }
    const scrollY = window.scrollY;
    const hasComments = await ensureCommentsSection();
    if (!hasComments) {
      window.scrollTo(0, scrollY);
      return { ok: false, error: "Aucun commentaire trouvé (commentaires désactivés ou pas encore chargés)." };
    }
    if (autoScroll) await autoLoad(max);
    const comments = readComments(max, includeReplies);
    window.scrollTo(0, scrollY);
    return { ok: true, comments, title: videoTitle(), url: location.href };
  }

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg?.action === "ping") {
      sendResponse({ ok: true });
      return false;
    }
    if (msg?.action === "extract") {
      extract(msg.options)
        .then(sendResponse)
        .catch((e) => sendResponse({ ok: false, error: String(e?.message || e) }));
      return true; // réponse asynchrone
    }
    return false;
  });
})();
