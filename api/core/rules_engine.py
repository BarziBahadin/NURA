import logging
import re
from typing import Optional, Tuple

from core.ml.arabic_normalizer import normalize_arabic

logger = logging.getLogger(__name__)

_STOPWORDS = {
    "كيف", "ما", "من", "هل", "اين", "متى", "لماذا", "الى", "على", "في",
    "عن", "مع", "هو", "هي", "هم", "انا", "انت", "نحن", "يمكن", "اريد",
    "اقدر", "ممكن", "عندي", "لدي", "عند", "لدى", "اي", "اذا", "لو",
    "لكن", "او", "حتى", "بعد", "قبل", "مثل", "بس", "فقط", "كل", "جدا",
    "يعني", "يكون", "شركة", "خدمة", "خدمات", "طريقة",
    "how", "what", "where", "when", "why", "can", "could", "would", "please",
    "the", "and", "or", "for", "with", "from", "this", "that", "need", "want",
}

# Common Arabic inflectional suffixes to strip (longest first)
_SUFFIXES = ("ات", "ون", "ين", "تي", "يا", "ها", "كم", "هم", "ني", "ة", "ي")
# Common Arabic definite/conjunctive prefixes to strip
_PREFIXES = ("وال", "بال", "كال", "ال", "وب", "فب", "لل")

_PUNCT = re.compile(r'[؟!.,،؛:؛\?\!\.\,\:\;\"\'ء]+')
_ALIASES = {
    "تحميل": {"download"},
    "تنزيل": {"download"},
    "download": {"تحميل"},
    "اندرويد": {"android"},
    "android": {"اندرويد"},
    "ايفون": {"iphone", "ios"},
    "iphone": {"ايفون"},
    "دخول": {"login"},
    "تسجيل": {"login"},
    "login": {"دخول"},
    "اوقات": {"hour", "hours"},
    "ساعات": {"hour", "hours"},
    "ساعة": {"hour", "hours"},
    "عمل": {"work", "working"},
    "hour": {"اوقات", "ساعة"},
    "hours": {"اوقات", "ساعة"},
    "work": {"عمل"},
    "working": {"عمل"},
}


def _normalize_word(word: str) -> str:
    """Strip punctuation/hamza, common prefixes, then common suffixes."""
    word = _PUNCT.sub('', word)
    # Strip prefix
    for pfx in _PREFIXES:
        if word.startswith(pfx) and len(word) > len(pfx) + 2:
            word = word[len(pfx):]
            break
    # Strip suffix to get approximate root
    for sfx in _SUFFIXES:
        if word.endswith(sfx) and len(word) > len(sfx) + 2:
            if sfx == "ات" and len(word) <= 5:
                continue
            word = word[:-len(sfx)]
            break
    for sfx in ("ing", "ed", "s"):
        if re.fullmatch(r"[a-z]+", word) and word.endswith(sfx) and len(word) > len(sfx) + 3:
            word = word[:-len(sfx)]
            break
    return word


def _tokenize(text: str) -> set:
    roots = set()
    for raw in normalize_arabic(text).split():
        word = _normalize_word(raw)
        if len(word) < 3 or word in _STOPWORDS or raw in _STOPWORDS:
            continue
        roots.add(word)
        roots.update(_ALIASES.get(word, set()))
    return roots


def _phrases(text: str) -> set[str]:
    tokens = [t for t in normalize_arabic(text).split() if len(t) > 2 and t not in _STOPWORDS]
    phrases = set()
    for size in (2, 3):
        for i in range(0, max(len(tokens) - size + 1, 0)):
            phrases.add(" ".join(tokens[i:i + size]))
    return phrases


_MAX_RESPONSE_CHARS = 1200
# Arabic sentence endings + common punctuation used as truncation boundaries
_SENTENCE_END_RE = re.compile(r'[.!?؟\n]')


def _truncate_response(text: str) -> str:
    """Trim to the last complete sentence within _MAX_RESPONSE_CHARS."""
    if len(text) <= _MAX_RESPONSE_CHARS:
        return text
    window = text[:_MAX_RESPONSE_CHARS]
    # Walk backwards to find the last sentence boundary
    for m in reversed(list(_SENTENCE_END_RE.finditer(window))):
        candidate = window[:m.end()].strip()
        if len(candidate) >= 80:  # avoid truncating to just a few chars
            return candidate
    return window.strip()


class RulesEngine:
    """
    Layer 0: direct article lookup via root-based keyword overlap.
    Score = hits / len(message_tokens) — "how much of the query is covered?"
    Runs before ML and OpenAI — zero cost, zero latency.
    """

    # Minimum fraction of message words that must hit article keywords
    _THRESHOLD = 0.50

    def __init__(self, articles: list):
        self._rules = []
        for article in articles:
            # Build keyword sets from title and body so imported articles with
            # English product names (Self-Care, APN, 4G) still match chat text.
            title = article.get("title", "")
            content = article.get("content_ar", "")
            # Use first 600 chars (the key topic terms appear early)
            keyword_text = f"{title}\n{content[:900]}"
            keyword_roots = _tokenize(keyword_text)
            if not keyword_roots:
                continue
            self._rules.append({
                "title": title,
                "keyword_roots": keyword_roots,
                "phrases": _phrases(keyword_text),
                "response": content,
            })
        logger.info(f"RulesEngine loaded {len(self._rules)} article rules")

    def match(self, message: str) -> Optional[Tuple[str, float]]:
        """
        Returns (response, confidence) if enough of the message words
        are covered by an article's keyword set, else None.
        """
        msg_roots = _tokenize(message)
        if not msg_roots:
            return None

        best_score = 0.0
        best_response = None
        best_title = None

        msg_phrases = _phrases(message)

        for rule in self._rules:
            hits = len(msg_roots & rule["keyword_roots"])
            if hits == 0:
                continue
            phrase_hits = len(msg_phrases & rule["phrases"])
            if len(msg_roots) <= 3 and hits < 2 and phrase_hits == 0:
                continue
            # Coverage: fraction of query words found in article
            score = (hits / len(msg_roots)) + min(phrase_hits * 0.12, 0.24)
            if phrase_hits == 0 and score < 0.90:
                continue
            if score > best_score:
                best_score = score
                best_response = rule["response"]
                best_title = rule["title"]

        if best_score >= self._THRESHOLD and best_response:
            confidence = min(0.70 + best_score * 0.28, 0.97)
            logger.info(
                f"Rules matched: '{best_title}' "
                f"(coverage={best_score:.0%}, conf={confidence:.2f})"
            )
            return _truncate_response(best_response), confidence

        return None
