import re
import math
import logging
from typing import List, Optional, Dict
from collections import Counter

logger = logging.getLogger(__name__)


class TextPreprocessor:
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.stats = {}

    def _log(self, message: str):
        if self.verbose:
            logger.debug(f"[PREPROCESSOR] {message}")

    def count_tokens(self, text: str) -> int:
        return len(text.split())

    def clean_text(self, text: str) -> str:
        self._log("STEP 1: Cleaning text...")
        original_tokens = self.count_tokens(text)

        text = re.sub(r'http\S+|www\S+|ftp\S+', '', text)
        text = re.sub(r'\S+@\S+\.\S+', '', text)
        text = re.sub(r'\+?1?\d{9,15}', '', text)
        text = ' '.join(text.split())
        text = re.sub(r'([!?.])\1{2,}', r'\1', text)
        text = re.sub(r'<[^>]+>', '', text)

        savings = original_tokens - self.count_tokens(text)
        self.stats['cleaning'] = savings
        self._log(f"✓ Removed URLs, emails, HTML. Saved ~{savings} tokens")
        return text

    def normalize_text(self, text: str, lowercase: bool = False) -> str:
        self._log("STEP 2: Normalizing text...")
        original_tokens = self.count_tokens(text)

        if lowercase:
            text = text.lower()

        text = re.sub(r'\s+([.,!?;:\)])', r'\1', text)
        text = re.sub(r'([(])\s+', r'\1', text)
        text = re.sub(r'\n\n+', '\n', text)
        text = '\n'.join(line.rstrip() for line in text.split('\n'))

        savings = original_tokens - self.count_tokens(text)
        self.stats['normalization'] = savings
        self._log(f"✓ Standardized formatting. Saved ~{savings} tokens")
        return text

    def remove_duplicates(self, text: str, by: str = 'sentence') -> str:
        self._log("STEP 3: Removing duplicates...")
        original_tokens = self.count_tokens(text)

        if by == 'sentence':
            sentences = re.split(r'(?<=[.!?])\s+', text)
            sentences = [s.strip() for s in sentences if s.strip()]
            seen = set()
            unique = []
            for sentence in sentences:
                normalized = sentence.lower().strip()
                if normalized not in seen:
                    seen.add(normalized)
                    unique.append(sentence)
            text = ' '.join(unique)

        elif by == 'paragraph':
            paragraphs = text.split('\n\n')
            seen = set()
            unique = []
            for para in paragraphs:
                normalized = para.lower().strip()
                if normalized not in seen and para.strip():
                    seen.add(normalized)
                    unique.append(para)
            text = '\n\n'.join(unique)

        savings = original_tokens - self.count_tokens(text)
        self.stats['deduplication'] = savings
        self._log(f"✓ Removed duplicates. Saved ~{savings} tokens")
        return text

    def extract_key_info(self, text: str, keywords: Optional[List[str]] = None) -> str:
        self._log("STEP 4: Extracting key information...")

        if keywords is None:
            keywords = [
                'important', 'urgent', 'critical', 'error', 'bug',
                'question', 'help', 'problem', 'issue', 'request',
                'required', 'must', 'need', 'should', 'why', 'how',
                'implement', 'create', 'build', 'fix', 'resolve',
            ]

        original_tokens = self.count_tokens(text)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        key_sentences = [s for s in sentences if any(kw in s.lower() for kw in keywords)]

        if not key_sentences:
            self._log("⚠ No key sentences found, keeping original text")
            return text

        text = ' '.join(key_sentences)
        savings = original_tokens - self.count_tokens(text)
        self.stats['extraction'] = savings
        self._log(f"✓ Extracted key info. Saved ~{savings} tokens")
        return text

    def summarize_text(self, text: str, max_length: int = 150, min_length: int = 50) -> str:
        self._log("STEP 5: Summarizing text...")
        original_tokens = self.count_tokens(text)
        sentences = re.split(r'(?<=[.!?])\s+', text)

        if len(sentences) < 3:
            self._log("⚠ Text too short to summarize")
            return text

        words = text.lower().split()
        word_freq = Counter(words)
        common = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'is', 'are', 'was', 'were', 'be', 'to', 'of', 'for', 'with', 'from'}
        word_freq = {word: freq for word, freq in word_freq.items() if word not in common}

        sentence_scores = {
            i: sum(word_freq.get(word.lower(), 0) for word in sentence.split())
            for i, sentence in enumerate(sentences)
        }

        top_indices = sorted(
            sorted(sentence_scores.items(), key=lambda x: x[1], reverse=True)[:len(sentences) // 2],
            key=lambda x: x[0],
        )
        summary = ' '.join(sentences[idx] for idx, _ in top_indices)

        savings = original_tokens - self.count_tokens(summary)
        self.stats['summarization'] = savings
        self._log(f"✓ Summarized text. Saved ~{savings} tokens")
        return summary

    def compress_whitespace(self, text: str) -> str:
        self._log("STEP 6: Compressing whitespace...")
        original_tokens = self.count_tokens(text)

        text = re.sub(r'[\t\r\n]+', ' ', text)
        text = re.sub(r' {2,}', ' ', text)
        text = text.strip()

        savings = original_tokens - self.count_tokens(text)
        self.stats['whitespace'] = savings
        self._log(f"✓ Compressed whitespace. Saved ~{savings} tokens")
        return text

    def fuzzy_deduplicate(self, text: str, threshold: float = 0.85) -> str:
        self._log("STEP 7: Fuzzy deduplication...")
        original_tokens = self.count_tokens(text)
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]

        def jaccard(a: str, b: str) -> float:
            sa, sb = set(a.lower().split()), set(b.lower().split())
            if not sa or not sb:
                return 0.0
            return len(sa & sb) / len(sa | sb)

        unique = []
        for candidate in sentences:
            if not any(jaccard(candidate, kept) >= threshold for kept in unique):
                unique.append(candidate)

        text = ' '.join(unique)
        savings = original_tokens - self.count_tokens(text)
        self.stats['fuzzy_dedup'] = savings
        self._log(f"✓ Fuzzy dedup (threshold={threshold}). Saved ~{savings} tokens")
        return text

    def extract_keywords_auto(self, text: str, top_n: int = 10) -> str:
        self._log("STEP 8: Auto keyword extraction (TF-IDF)...")
        original_tokens = self.count_tokens(text)

        STOPWORDS = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'is', 'are', 'was',
            'were', 'be', 'to', 'of', 'for', 'with', 'from', 'that', 'this',
            'it', 'as', 'at', 'by', 'on', 'we', 'i', 'you', 'he', 'she',
            'they', 'not', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'can', 'could', 'should', 'if', 'so', 'its', 'into',
            'about', 'up', 'out', 'than', 'then', 'just', 'more', 'also',
        }

        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
        num_docs = len(sentences)

        if num_docs < 2:
            self._log("⚠ Too few sentences for TF-IDF, keeping original")
            return text

        tf_per_sentence = []
        for sentence in sentences:
            words = [w.lower() for w in re.findall(r'\b\w+\b', sentence) if w.lower() not in STOPWORDS]
            freq = Counter(words)
            total = len(words) or 1
            tf_per_sentence.append({w: c / total for w, c in freq.items()})

        all_words = set(w for tf in tf_per_sentence for w in tf)
        idf = {
            word: math.log(num_docs / sum(1 for tf in tf_per_sentence if word in tf))
            for word in all_words
        }

        tfidf_scores: Dict[str, float] = Counter()
        for tf in tf_per_sentence:
            for word, tf_val in tf.items():
                tfidf_scores[word] += tf_val * idf.get(word, 0)

        top_keywords = {word for word, _ in tfidf_scores.most_common(top_n)}
        self._log(f"  Top keywords: {', '.join(sorted(top_keywords))}")

        key_sentences = [
            s for s in sentences
            if any(kw in re.findall(r'\b\w+\b', s.lower()) for kw in top_keywords)
        ]

        if not key_sentences:
            self._log("⚠ No keyword sentences found, keeping original")
            return text

        text = ' '.join(key_sentences)
        savings = original_tokens - self.count_tokens(text)
        self.stats['keyword_extraction'] = savings
        self._log(f"✓ Kept {len(key_sentences)}/{len(sentences)} sentences. Saved ~{savings} tokens")
        return text

    def full_pipeline(
        self,
        text: str,
        use_extraction: bool = False,
        use_summarization: bool = False,
        lowercase: bool = False,
        use_whitespace_compression: bool = True,
        use_fuzzy_dedup: bool = False,
        use_keyword_extraction: bool = False,
        fuzzy_threshold: float = 0.85,
        keyword_top_n: int = 10,
    ) -> str:
        original = self.count_tokens(text)

        text = self.clean_text(text)
        text = self.normalize_text(text, lowercase=lowercase)
        if use_whitespace_compression:
            text = self.compress_whitespace(text)
        text = self.remove_duplicates(text, by='sentence')
        if use_fuzzy_dedup:
            text = self.fuzzy_deduplicate(text, threshold=fuzzy_threshold)
        if use_extraction:
            text = self.extract_key_info(text)
        if use_keyword_extraction:
            text = self.extract_keywords_auto(text, top_n=keyword_top_n)
        if use_summarization and self.count_tokens(text) > 200:
            text = self.summarize_text(text)

        final = self.count_tokens(text)
        self._log(f"Pipeline complete: {original} → {final} tokens ({original - final} saved)")
        return text.strip()

    def get_stats(self) -> Dict[str, int]:
        return self.stats

    def reset_stats(self):
        self.stats = {}
