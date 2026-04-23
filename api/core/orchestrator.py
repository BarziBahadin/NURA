import json
import logging
from pathlib import Path
from typing import Tuple

from openai import AsyncOpenAI

from config import settings
from core.rag_engine import retrieve_context
from core.text_preprocessor import TextPreprocessor
from models.session import Session

logger = logging.getLogger(__name__)

_preprocessor = TextPreprocessor(verbose=False)

# Load ML local model at startup (optional — works without it)
_conversation_service = None
try:
    from core.ml.local_model import LocalModelService
    from core.ml.conversation import ConversationService
    _ml = LocalModelService(
        model_path=Path(settings.ml_model_path),
        vectorizer_path=Path(settings.ml_vectorizer_path),
        use_semantic=settings.use_semantic_embeddings,
        semantic_model_name=settings.semantic_model_name,
    )
    _conversation_service = ConversationService(_ml, confidence_threshold=settings.ml_confidence_threshold)
    logger.info(f"ML local model loaded (threshold={settings.ml_confidence_threshold})")
except FileNotFoundError:
    logger.info("ML model not found — run training/cli.py train-model to enable local ML layer")
except Exception as e:
    logger.warning(f"ML model could not be loaded: {e}")

# Load articles knowledge base at startup
_ARTICLES_KB = ""
_articles = []
_rules_engine = None
_articles_path = "/app/manafest/articals.json"
try:
    with open(_articles_path, "r", encoding="utf-8") as f:
        _articles = json.load(f)
    raw_kb = "\n\n".join(
        f"[{a['title']}]\n{a['content_ar']}" for a in _articles
    )
    # Compress whitespace and remove exact duplicate sentences once at startup
    _ARTICLES_KB = _preprocessor.compress_whitespace(
        _preprocessor.remove_duplicates(raw_kb, by="sentence")
    )
    logger.info(
        f"Loaded {len(_articles)} articles from knowledge base "
        f"({len(raw_kb)} chars → {len(_ARTICLES_KB)} chars after preprocessing)"
    )
except Exception as e:
    logger.warning(f"Could not load articles knowledge base: {e}")

try:
    from core.rules_engine import RulesEngine
    _rules_engine = RulesEngine(_articles)
except Exception as e:
    logger.warning(f"Rules engine could not be initialized: {e}")

SYSTEM_PROMPT_TEMPLATE = """أنت وكيل خدمة عملاء محترف في شركة {company_name} للاتصالات.
تحدث دائمًا باللغة العربية الفصحى بأسلوب رسمي ومهذب.
إذا كتب العميل بلغة أخرى، رد بنفس اللغة مع الحفاظ على الأسلوب الرسمي.

قاعدة المعرفة المعتمدة لخدمات الشركة:
---
{articles_kb}
---

معلومات إضافية من دليل الشركة:
---
{rag_context}
---

سجل المحادثة:
{conversation_history}

القواعد الصارمة التي يجب اتباعها دون استثناء:
1. أنت متخصص حصرياً في خدمات {company_name}. لا تجب على أي سؤال خارج نطاق خدمات الشركة مهما كان.
2. إذا سألك العميل عن موضوع غير متعلق بالشركة (أخبار، طقس، سياسة، تاريخ، علوم، تقنية عامة، إلخ)، أجب فقط: "أنا متخصص في خدمات {company_name} فقط. هل يمكنني مساعدتك في استفسار يتعلق بخدماتنا؟"
3. لا تخترع معلومات. إذا لم تجد الإجابة في قاعدة المعرفة أعلاه، قل فقط: "لا أملك معلومات محددة حول هذا الموضوع. هل يمكنني مساعدتك في شيء آخر يتعلق بخدماتنا؟" — لا تذكر التحويل إلى موظف إلا إذا كان العميل يطلب ذلك صراحةً.
4. لا تذكر أي شركة اتصالات منافسة أبداً ولا تقارن بها.
5. لا تعد بخدمات أو عروض غير مذكورة في قاعدة المعرفة.
6. إذا كان العميل غاضباً، اعترف بإحباطه بجملة واحدة قبل تقديم الحل.
7. اجعل ردودك مختصرة وواضحة ما لم يطلب العميل شرحاً تفصيلياً.
8. لا تبدأ أي رد بعبارة ترحيب مثل "أهلاً وسهلاً" أو "شكراً لتواصلك" — تم إرسال رسالة الترحيب مسبقاً تلقائياً ولا يجب تكرارها أبداً. ابدأ مباشرةً بالإجابة."""


async def generate_response(session: Session, message: str) -> Tuple[str, float, str]:
    # 0. Rules engine — exact article match, zero cost
    if _rules_engine is not None:
        rules_result = _rules_engine.match(message)
        if rules_result:
            response, confidence = rules_result
            return response, confidence, "rules"

    # 1. Try local ML model first — free, instant, no API call
    if _conversation_service is not None:
        ml_result = _conversation_service.process(message)
        if ml_result["response"] and ml_result["confidence"] >= settings.ml_confidence_threshold:
            logger.info(f"ML answered (conf={ml_result['confidence']:.2f}, cat={ml_result['category']})")
            return ml_result["response"], ml_result["confidence"], "local_model"

    # 2. Fall through to RAG + OpenAI
    rag_context, confidence = await retrieve_context(message)

    if not rag_context:
        rag_context = "لا يوجد سياق متاح من الدليل."
        confidence = 0.5  # articles KB is always loaded and covers most questions
    else:
        rag_context = _preprocessor.compress_whitespace(rag_context)

    history_text = ""
    if session.history:
        for turn in session.history[-6:]:
            role_label = "العميل" if turn.role == "customer" else "الوكيل"
            history_text += f"{role_label}: {turn.message}\n"
    else:
        history_text = "لا توجد محادثة سابقة."

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        company_name=settings.company_name,
        articles_kb=_ARTICLES_KB if _ARTICLES_KB else "غير متاح.",
        rag_context=rag_context,
        conversation_history=history_text,
    )

    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        resp = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            temperature=0.3,
            max_completion_tokens=500,
        )
        reply = resp.choices[0].message.content.strip()
        if not reply:
            reply = "عذرًا، لم أتمكن من معالجة طلبك. سأقوم بتحويلك إلى أحد أعضاء فريقنا."
        return reply, confidence, "openai"
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return (
            "عذرًا، يواجه النظام مشكلة مؤقتة. سيتم تحويلك إلى أحد أعضاء فريقنا.",
            0.0,
            "openai",
        )
