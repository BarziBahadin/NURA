import re
import math
from typing import List, Optional, Dict
from collections import Counter

class TextPreprocessor:
    """
    Complete text preprocessing pipeline combining all techniques.
    Reduces tokens by: cleaning, normalizing, deduplicating, extracting, and summarizing.
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.stats = {}

    def log(self, message: str):
        """Print log messages if verbose mode enabled"""
        if self.verbose:
            print(f"[PREPROCESSOR] {message}")

    def count_tokens(self, text: str) -> int:
        """Estimate token count (rough: 1 token ≈ 0.75 words)"""
        return len(text.split())

    # ============== STEP 1: CLEANING ==============
    def clean_text(self, text: str) -> str:
        """Remove URLs, emails, special characters, and extra whitespace"""
        self.log("STEP 1: Cleaning text...")
        original_tokens = self.count_tokens(text)

        # Remove URLs
        text = re.sub(r'http\S+|www\S+|ftp\S+', '', text)

        # Remove email addresses
        text = re.sub(r'\S+@\S+\.\S+', '', text)

        # Remove phone numbers
        text = re.sub(r'\+?1?\d{9,15}', '', text)

        # Remove extra whitespace
        text = ' '.join(text.split())

        # Fix multiple punctuation (!!!!, ????)
        text = re.sub(r'([!?.])\1{2,}', r'\1', text)

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)

        cleaned_tokens = self.count_tokens(text)
        savings = original_tokens - cleaned_tokens
        self.stats['cleaning'] = savings

        self.log(f"✓ Removed URLs, emails, HTML. Saved ~{savings} tokens")
        return text

    # ============== STEP 2: NORMALIZATION ==============
    def normalize_text(self, text: str, lowercase: bool = False) -> str:
        """Standardize text formatting"""
        self.log("STEP 2: Normalizing text...")
        original_tokens = self.count_tokens(text)

        if lowercase:
            text = text.lower()

        # Fix spacing around punctuation
        text = re.sub(r'\s+([.,!?;:\)])', r'\1', text)
        text = re.sub(r'([(])\s+', r'\1', text)

        # Normalize line breaks
        text = re.sub(r'\n\n+', '\n', text)

        # Remove trailing whitespace on each line
        text = '\n'.join(line.rstrip() for line in text.split('\n'))

        normalized_tokens = self.count_tokens(text)
        savings = original_tokens - normalized_tokens
        self.stats['normalization'] = savings

        self.log(f"✓ Standardized formatting. Saved ~{savings} tokens")
        return text

    # ============== STEP 3: DEDUPLICATION ==============
    def remove_duplicates(self, text: str, by: str = 'sentence') -> str:
        """Remove duplicate sentences or paragraphs"""
        self.log("STEP 3: Removing duplicates...")
        original_tokens = self.count_tokens(text)

        if by == 'sentence':
            # Split by sentence endings
            sentences = re.split(r'(?<=[.!?])\s+', text)
            sentences = [s.strip() for s in sentences if s.strip()]

            # Remove duplicates (preserve order)
            seen = set()
            unique = []
            for sentence in sentences:
                normalized = sentence.lower().strip()
                if normalized not in seen:
                    seen.add(normalized)
                    unique.append(sentence)

            text = ' '.join(unique)

        elif by == 'paragraph':
            # Split by blank lines
            paragraphs = text.split('\n\n')
            seen = set()
            unique = []
            for para in paragraphs:
                normalized = para.lower().strip()
                if normalized not in seen and para.strip():
                    seen.add(normalized)
                    unique.append(para)

            text = '\n\n'.join(unique)

        dedup_tokens = self.count_tokens(text)
        savings = original_tokens - dedup_tokens
        self.stats['deduplication'] = savings

        self.log(f"✓ Removed duplicates. Saved ~{savings} tokens")
        return text

    # ============== STEP 4: EXTRACTION ==============
    def extract_key_info(self, text: str, keywords: Optional[List[str]] = None) -> str:
        """Extract only sentences containing important keywords"""
        self.log("STEP 4: Extracting key information...")

        if keywords is None:
            keywords = [
                'important', 'urgent', 'critical', 'error', 'bug',
                'question', 'help', 'problem', 'issue', 'request',
                'required', 'must', 'need', 'should', 'why', 'how',
                'implement', 'create', 'build', 'fix', 'resolve'
            ]

        original_tokens = self.count_tokens(text)

        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)

        # Filter for key sentences
        key_sentences = []
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in keywords):
                key_sentences.append(sentence)

        # If no key sentences found, return original (safety check)
        if not key_sentences:
            self.log("⚠ No key sentences found, keeping original text")
            return text

        text = ' '.join(key_sentences)
        extracted_tokens = self.count_tokens(text)
        savings = original_tokens - extracted_tokens
        self.stats['extraction'] = savings

        self.log(f"✓ Extracted key info. Saved ~{savings} tokens")
        return text

    # ============== STEP 5: SUMMARIZATION ==============
    def summarize_text(self, text: str, max_length: int = 150, min_length: int = 50) -> str:
        """Summarize long text using extractive summarization"""
        self.log("STEP 5: Summarizing text...")
        original_tokens = self.count_tokens(text)

        # Simple extractive summarization (based on sentence frequency)
        sentences = re.split(r'(?<=[.!?])\s+', text)

        if len(sentences) < 3:
            self.log("⚠ Text too short to summarize")
            return text

        # Score sentences by word frequency
        words = text.lower().split()
        word_freq = Counter(words)

        # Remove common words
        common = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'is', 'are', 'was', 'were', 'be', 'to', 'of', 'for', 'with', 'from'}
        word_freq = {word: freq for word, freq in word_freq.items() if word not in common}

        sentence_scores = {}
        for i, sentence in enumerate(sentences):
            score = sum(word_freq.get(word.lower(), 0) for word in sentence.split())
            sentence_scores[i] = score

        # Select top sentences (keep order)
        top_indices = sorted(
            sorted(sentence_scores.items(), key=lambda x: x[1], reverse=True)[:len(sentences)//2],
            key=lambda x: x[0]
        )
        top_indices = [idx for idx, _ in top_indices]

        summary = ' '.join(sentences[i] for i in top_indices)

        summary_tokens = self.count_tokens(summary)
        savings = original_tokens - summary_tokens
        self.stats['summarization'] = savings

        self.log(f"✓ Summarized text. Saved ~{savings} tokens")
        return summary

    # ============== STEP 6: AGGRESSIVE WHITESPACE COMPRESSION ==============
    def compress_whitespace(self, text: str) -> str:
        """Collapse tabs, newlines, and repeated spaces into single spaces"""
        self.log("STEP 6: Compressing whitespace...")
        original_tokens = self.count_tokens(text)

        # Replace tabs and newlines with a space
        text = re.sub(r'[\t\r\n]+', ' ', text)
        # Collapse multiple spaces
        text = re.sub(r' {2,}', ' ', text)
        # Remove spaces at start/end of lines (after newline normalization above there are none,
        # but handle edge cases)
        text = text.strip()

        savings = original_tokens - self.count_tokens(text)
        self.stats['whitespace'] = savings
        self.log(f"✓ Compressed whitespace. Saved ~{savings} tokens")
        return text

    # ============== STEP 7: FUZZY DEDUPLICATION ==============
    def fuzzy_deduplicate(self, text: str, threshold: float = 0.85) -> str:
        """Remove near-duplicate sentences using word-overlap (Jaccard similarity)"""
        self.log("STEP 7: Fuzzy deduplication...")
        original_tokens = self.count_tokens(text)

        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

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
        self.log(f"✓ Fuzzy dedup (threshold={threshold}). Saved ~{savings} tokens")
        return text

    # ============== STEP 8: AUTO KEYWORD EXTRACTION (TF-IDF) ==============
    def extract_keywords_auto(self, text: str, top_n: int = 10) -> str:
        """Auto-discover top keywords via TF-IDF and keep only sentences containing them"""
        self.log("STEP 8: Auto keyword extraction (TF-IDF)...")
        original_tokens = self.count_tokens(text)

        STOPWORDS = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'is', 'are', 'was',
            'were', 'be', 'to', 'of', 'for', 'with', 'from', 'that', 'this',
            'it', 'as', 'at', 'by', 'on', 'we', 'i', 'you', 'he', 'she',
            'they', 'not', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'can', 'could', 'should', 'if', 'so', 'its', 'into',
            'about', 'up', 'out', 'than', 'then', 'just', 'more', 'also',
        }

        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        num_docs = len(sentences)

        if num_docs < 2:
            self.log("⚠ Too few sentences for TF-IDF, keeping original")
            return text

        # TF per sentence
        tf_per_sentence = []
        for sentence in sentences:
            words = [w.lower() for w in re.findall(r'\b\w+\b', sentence) if w.lower() not in STOPWORDS]
            freq = Counter(words)
            total = len(words) or 1
            tf_per_sentence.append({w: c / total for w, c in freq.items()})

        # IDF across sentences
        all_words = set(w for tf in tf_per_sentence for w in tf)
        idf = {
            word: math.log(num_docs / sum(1 for tf in tf_per_sentence if word in tf))
            for word in all_words
        }

        # Global TF-IDF score per word
        tfidf_scores: Dict[str, float] = Counter()
        for tf in tf_per_sentence:
            for word, tf_val in tf.items():
                tfidf_scores[word] += tf_val * idf.get(word, 0)

        top_keywords = {word for word, _ in tfidf_scores.most_common(top_n)}
        self.log(f"  Top keywords: {', '.join(sorted(top_keywords))}")

        key_sentences = [
            s for s in sentences
            if any(kw in re.findall(r'\b\w+\b', s.lower()) for kw in top_keywords)
        ]

        if not key_sentences:
            self.log("⚠ No keyword sentences found, keeping original")
            return text

        text = ' '.join(key_sentences)
        savings = original_tokens - self.count_tokens(text)
        self.stats['keyword_extraction'] = savings
        self.log(f"✓ Kept {len(key_sentences)}/{len(sentences)} sentences. Saved ~{savings} tokens")
        return text

    # ============== MAIN PIPELINE ==============
    def full_pipeline(self, text: str, use_extraction: bool = False,
                     use_summarization: bool = False, lowercase: bool = False,
                     use_whitespace_compression: bool = True,
                     use_fuzzy_dedup: bool = False,
                     use_keyword_extraction: bool = False,
                     fuzzy_threshold: float = 0.85,
                     keyword_top_n: int = 10) -> str:
        """
        Run complete preprocessing pipeline.

        Args:
            text: Raw input text
            use_extraction: Whether to extract key info using predefined keywords
            use_summarization: Whether to summarize (for long texts)
            lowercase: Whether to convert to lowercase
            use_whitespace_compression: Aggressively collapse tabs/newlines (default True)
            use_fuzzy_dedup: Remove near-duplicate sentences by word overlap
            use_keyword_extraction: Auto-discover and keep top TF-IDF keyword sentences
            fuzzy_threshold: Jaccard similarity threshold for fuzzy dedup (0-1)
            keyword_top_n: Number of top keywords to extract in auto keyword extraction

        Returns:
            Processed text with reduced tokens
        """
        self.log("=" * 50)
        self.log("STARTING FULL PREPROCESSING PIPELINE")
        self.log("=" * 50)

        original = self.count_tokens(text)
        self.log(f"Original tokens: {original}\n")

        # Step 1: Clean
        text = self.clean_text(text)

        # Step 2: Normalize
        text = self.normalize_text(text, lowercase=lowercase)

        # Step 3: Whitespace compression (default on)
        if use_whitespace_compression:
            text = self.compress_whitespace(text)

        # Step 4: Exact deduplication
        text = self.remove_duplicates(text, by='sentence')

        # Step 5: Fuzzy deduplication (optional)
        if use_fuzzy_dedup:
            text = self.fuzzy_deduplicate(text, threshold=fuzzy_threshold)

        # Step 6: Predefined keyword extraction (optional)
        if use_extraction:
            text = self.extract_key_info(text)

        # Step 7: Auto TF-IDF keyword extraction (optional)
        if use_keyword_extraction:
            text = self.extract_keywords_auto(text, top_n=keyword_top_n)

        # Step 8: Summarize (optional)
        if use_summarization and self.count_tokens(text) > 200:
            text = self.summarize_text(text)

        final = self.count_tokens(text)
        total_savings = original - final
        percent_saved = (total_savings / original * 100) if original > 0 else 0

        self.log("\n" + "=" * 50)
        self.log("PIPELINE COMPLETE")
        self.log("=" * 50)
        self.log(f"Original tokens: {original}")
        self.log(f"Final tokens: {final}")
        self.log(f"Total savings: ~{total_savings} tokens ({percent_saved:.1f}%)")
        self.log("=" * 50 + "\n")

        return text.strip()

    def get_stats(self) -> Dict[str, int]:
        """Return savings statistics from last run"""
        return self.stats

    def reset_stats(self):
        """Reset statistics"""
        self.stats = {}
