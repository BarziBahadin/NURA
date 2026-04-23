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
}

# Common Arabic inflectional suffixes to strip (longest first)
_SUFFIXES = ("ات", "ون", "ين", "تي", "يا", "ها", "كم", "هم", "ني", "ة", "ي")
# Common Arabic definite/conjunctive prefixes to strip
_PREFIXES = ("وال", "بال", "كال", "ال", "وب", "فب", "لل")

_PUNCT = re.compile(r'[؟!.,،؛:؛\?\!\.\,\:\;\"\'ء]+')


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
    return roots


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
            # Titles may be English — build keyword set from Arabic content
            content = article.get("content_ar", "")
            # Use first 600 chars (the key topic terms appear early)
            keyword_roots = _tokenize(content[:600])
            if not keyword_roots:
                continue
            self._rules.append({
                "title": article["title"],
                "keyword_roots": keyword_roots,
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

        for rule in self._rules:
            hits = len(msg_roots & rule["keyword_roots"])
            if hits == 0:
                continue
            # Coverage: fraction of query words found in article
            score = hits / len(msg_roots)
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
            return best_response, confidence

        return None
