NEGATIVE_KEYWORDS = [
    # Arabic
    "غاضب", "محبط", "رديء", "سيء", "فضيحة", "استرجاع", "شكوى",
    "غير مقبول", "مزعج", "ما ينفع", "ضيعت", "كذب", "نصب", "وحش",
    # English
    "angry", "frustrated", "terrible", "awful", "horrible", "refund",
    "useless", "cancel", "unacceptable", "scam", "fraud", "hate",
    "worst", "disgusting", "incompetent", "never again",
]

ESCALATION_KEYWORDS = [
    # Arabic
    "مدير", "مشرف", "إنسان", "موظف بشري", "شكوى رسمية", "تصعيد",
    "تحدث مع شخص", "أريد مسؤول",
    # English
    "manager", "supervisor", "human", "real person", "escalate",
    "speak to someone", "complaint", "lawsuit", "legal",
]


def analyze_sentiment(text: str) -> dict:
    text_lower = text.lower()
    negative_hits = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text_lower)
    escalation_requested = any(kw in text_lower for kw in ESCALATION_KEYWORDS)

    return {
        "negative_score": negative_hits,
        "escalation_requested": escalation_requested,
        "is_negative": negative_hits >= 2,
    }
