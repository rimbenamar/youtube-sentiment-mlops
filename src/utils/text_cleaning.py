"""Nettoyage de texte partagé entre l'entraînement et l'API.

IMPORTANT : la même fonction est utilisée à l'entraînement et à l'inférence,
sinon le vocabulaire TF-IDF ne correspondrait pas aux textes reçus par l'API.
"""
import html
import re
import unicodedata

URL_RE = re.compile(r"(https?://\S+|www\.\S+)")
MENTION_RE = re.compile(r"@[\w.\-]+")
HASHTAG_RE = re.compile(r"#(\w+)")
TIMESTAMP_RE = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b")  # "1:23" fréquent sur YouTube
REPEAT_RE = re.compile(r"(.)\1{2,}")  # "soooo" -> "soo"
NON_ALNUM_RE = re.compile(r"[^a-z0-9\s']")
MULTISPACE_RE = re.compile(r"\s+")

# Les emojis portent beaucoup de sentiment : on les traduit en mots
# avant de supprimer les caractères spéciaux (plutôt que de les perdre).
EMOJI_MAP = {
    "😀": " happy ", "😃": " happy ", "😄": " happy ", "😁": " happy ", "😊": " happy ",
    "🙂": " good ", "😍": " love ", "🥰": " love ", "❤": " love ", "♥": " love ",
    "💕": " love ", "💖": " love ", "😘": " love ", "👍": " good ", "👏": " great ",
    "🔥": " awesome ", "💯": " perfect ", "🙌": " great ", "✨": " great ", "🎉": " great ",
    "😂": " funny ", "🤣": " funny ", "😆": " funny ", "😅": " funny ",
    "😢": " sad ", "😭": " sad ", "😞": " sad ", "😔": " sad ", "💔": " sad ",
    "😡": " angry ", "😠": " angry ", "🤬": " angry ", "👎": " bad ", "🤮": " disgusting ",
    "🤢": " disgusting ", "😒": " bad ", "🙄": " annoying ", "😤": " angry ", "💩": " bad ",
    "😐": " ", "🤔": " ", "😮": " ",
}


def clean_text(text) -> str:
    """Nettoie un commentaire brut et renvoie un texte normalisé en minuscules."""
    if text is None:
        return ""
    text = str(text)
    text = html.unescape(text)
    for emo, word in EMOJI_MAP.items():
        if emo in text:
            text = text.replace(emo, word)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")  # accents / emojis restants
    text = text.lower()
    text = URL_RE.sub(" ", text)
    text = MENTION_RE.sub(" ", text)
    text = HASHTAG_RE.sub(r" \1 ", text)
    text = TIMESTAMP_RE.sub(" ", text)
    text = text.replace("\n", " ")
    text = NON_ALNUM_RE.sub(" ", text)
    text = REPEAT_RE.sub(r"\1\1", text)
    text = MULTISPACE_RE.sub(" ", text).strip()
    return text
