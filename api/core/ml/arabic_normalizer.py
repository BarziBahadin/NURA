import re

_DIACRITICS = re.compile(r'[ؐ-ًؚ-ٰٟـ]')
_ALEF = re.compile(r'[أإآٱ]')
_NOISE = re.compile(r'[^؀-ۿ\w\s]')
_SPACES = re.compile(r'\s+')


def normalize_arabic(text: str) -> str:
    text = _DIACRITICS.sub('', text)
    text = _ALEF.sub('ا', text)
    text = text.replace('ؤ', 'و')
    text = text.replace('ئ', 'ي')
    text = text.replace('ى', 'ي')
    text = _NOISE.sub(' ', text)
    text = _SPACES.sub(' ', text).strip()
    return text.lower()
