import re
import logging

from core.ml.arabic_normalizer import normalize_arabic

logger = logging.getLogger(__name__)

_GREETINGS_AR = {
    'مرحبا', 'مرحباً', 'مرحبه', 'هلا', 'هلاً', 'اهلا', 'أهلاً', 'أهلا', 'اهلاً',
    'السلام عليكم', 'سلام', 'صباح الخير', 'مساء الخير', 'صباح النور', 'مساء النور',
    'هاي', 'هي', 'hello', 'hi', 'hey', 'good morning', 'good evening',
}

_GREETING_RE = re.compile(
    r'^(' + '|'.join(re.escape(k) for k in _GREETINGS_AR) + r')[\s،,.!؟?]*$',
    re.IGNORECASE,
)

_GRATITUDE_AR = {
    'شكرا', 'شكراً', 'شكر', 'ممنون', 'ممنونة', 'مشكور', 'مشكورة',
    'تسلم', 'تسلمي', 'تسلموا', 'يسلموا', 'يسلمك', 'يعطيك العافية',
    'الله يسلمك', 'الله يسلمكم', 'الله يعطيك العافية',
    'thanks', 'thank you', 'thx', 'ty',
}

_GRATITUDE_RE = re.compile(
    r'(?:^|\s)(' + '|'.join(re.escape(k) for k in _GRATITUDE_AR) + r')(?:\s|$|[،,.!؟?])',
    re.IGNORECASE,
)

_FOLLOW_UP = '\n\nهل يمكنني مساعدتك بشيء آخر؟'

_NO_ANSWER = (
    'عذراً، لم أتمكن من فهم طلبك بشكل كافٍ.\n'
    'يمكنك التواصل مع خدمة العملاء مباشرةً:\n'
    '• الاتصال من شريحة Rcell: 111\n'
    '• أو أعد صياغة سؤالك وسأحاول مساعدتك.'
)

_STOP = {
    'انا', 'أنا', 'نحن', 'هو', 'هي', 'هم', 'انت', 'أنت', 'انتم', 'أنتم',
    'هذا', 'هذه', 'هؤلاء', 'ذلك', 'تلك', 'الذي', 'التي', 'الذين',
    'في', 'من', 'على', 'إلى', 'الى', 'عن', 'مع', 'بعد', 'قبل', 'حتى', 'عند',
    'هل', 'لا', 'نعم', 'لكن', 'و', 'أو', 'او', 'ثم', 'لأن', 'لان', 'إذا', 'اذا',
    'كان', 'كانت', 'يكون', 'تكون', 'قد', 'قال', 'قالت', 'يقول',
    'اريد', 'أريد', 'اقدر', 'أقدر', 'ممكن', 'يمكن', 'تقدر', 'تقدري',
    'كيف', 'ماذا', 'متى', 'اين', 'أين', 'ما', 'من',
    'بعض', 'كل', 'اي', 'أي', 'لدي', 'عندي', 'عندك', 'لديك',
    'جداً', 'جدا', 'كثير', 'قليل', 'فقط', 'دائماً', 'دائما',
    'شكرا', 'شكراً', 'ممنون', 'مشكور',
}

_INTENT_KEYWORDS: dict[str, list[str]] = {
    'speed':     ['بطيء', 'بطيئ', 'بطيئة', 'ضعيف', 'انقطع', 'شبكة', 'نت', 'انترنت', 'إنترنت', 'apn', '4g', '5g'],
    'sim_price': ['شريحة', 'شريحه', 'sim', 'سيم', 'سعر شريحة', 'ثمن الشريحة'],
    'billing':   ['باقة', 'باقه', 'باقات', 'رصيد', 'شحن', 'سعر', 'اسعار', 'أسعار', 'نقطة', 'نقاط', 'gb', 'جيجا'],
    'account':   ['كلمة المرور', 'مرور', 'تسجيل', 'دخول', 'حساب', 'رقم سري', 'تطبيق', 'self-care'],
    'hours':     ['ساعات', 'ساعة', 'وقت', 'مفتوح', 'عمل', 'مواعيد', 'جمعة', 'سبت'],
}


def is_greeting(text: str) -> bool:
    return bool(_GREETING_RE.match(normalize_arabic(text).strip()))


def is_gratitude(text: str) -> bool:
    cleaned = normalize_arabic(text).strip()
    if len(cleaned.split()) <= 5 and _GRATITUDE_RE.search(cleaned):
        return True
    return cleaned in {normalize_arabic(k) for k in _GRATITUDE_AR}


def extract_intent(text: str) -> str:
    if len(text.strip()) <= 60:
        return text
    normalized = normalize_arabic(text)
    for _cat, keywords in _INTENT_KEYWORDS.items():
        hits = [kw for kw in keywords if kw in normalized]
        if hits:
            return ' '.join(hits)
    words = re.split(r'[\s،,.!؟?]+', text)
    filtered = [w for w in words if w and normalize_arabic(w) not in _STOP]
    result = ' '.join(filtered).strip()
    return result if len(result) >= 10 else text


class ConversationService:
    def __init__(self, local_model, confidence_threshold: float = 0.70):
        self.model = local_model
        self.threshold = confidence_threshold

    def process(self, message: str) -> dict:
        if is_greeting(message):
            return {"response": "", "confidence": 0.0, "category": "Greeting", "source": "conversation"}

        if is_gratitude(message):
            return {
                "response": "العفو! يسعدنا دائماً خدمتك. 😊\nهل يمكنني مساعدتك بشيء آخر؟",
                "confidence": 1.0,
                "category": "General",
                "source": "conversation",
            }

        intent_query = extract_intent(message)
        if intent_query != message:
            logger.debug(f"Intent extracted: {intent_query!r}")

        result = self.model.generate(intent_query, threshold=self.threshold)

        if result["confidence"] < self.threshold and intent_query != message:
            alt = self.model.generate(message, threshold=self.threshold)
            if alt["confidence"] > result["confidence"]:
                result = alt

        if result["confidence"] >= self.threshold and result["response"]:
            response_text = result["response"] + _FOLLOW_UP
            return {**result, "response": response_text}

        return {**result, "response": ""}
