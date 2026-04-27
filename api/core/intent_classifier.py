import json
import logging
from typing import Any, Dict

from openai import AsyncOpenAI

from config import settings
from core.logger import log_llm_usage, log_message_insight

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


def estimate_chat_cost(prompt_tokens: int, completion_tokens: int) -> float:
    return round(
        (prompt_tokens / 1000) * settings.openai_cost_input_per_1k
        + (completion_tokens / 1000) * settings.openai_cost_output_per_1k,
        8,
    )


def _fallback_bucket(confidence: float) -> str:
    if confidence >= 0.75:
        return "high"
    if confidence >= 0.45:
        return "medium"
    return "low"


async def classify_and_log_message(
    *,
    session_id: str,
    customer_id: str,
    channel: str,
    message_text: str,
    confidence: float,
    source: str,
    escalated: bool,
) -> None:
    base: Dict[str, Any] = {
        "language": "unknown",
        "intent": "unknown",
        "sub_intent": "",
        "sentiment": "neutral",
        "confidence_bucket": _fallback_bucket(confidence),
        "is_knowledge_gap": bool(escalated or confidence < 0.45),
        "gap_reason": "low_confidence" if confidence < 0.45 else "",
    }

    if not settings.openai_api_key:
        await log_message_insight(session_id, customer_id, channel, message_text, **base)
        return

    system = (
        "Classify a telecom customer-support message for reporting. "
        "Return compact JSON only with keys: language, intent, sub_intent, "
        "sentiment, confidence_bucket, is_knowledge_gap, gap_reason. "
        "Use broad telecom intents such as packages, recharge, internet, apn, sim, esim, "
        "self_care_app, volte, coverage, billing, complaint, agent_request, other."
    )
    user = json.dumps(
        {
            "message": message_text,
            "answer_source": source,
            "answer_confidence": confidence,
            "escalated": escalated,
        },
        ensure_ascii=False,
    )

    try:
        resp = await get_client().chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0,
            max_completion_tokens=180,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "{}"
        parsed = json.loads(content)
        usage = getattr(resp, "usage", None)
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        await log_llm_usage(
            session_id=session_id,
            model=settings.openai_model,
            operation="intent_classification",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_cost=estimate_chat_cost(prompt_tokens, completion_tokens),
        )
        base.update({
            "language": str(parsed.get("language") or base["language"])[:40],
            "intent": str(parsed.get("intent") or base["intent"])[:80],
            "sub_intent": str(parsed.get("sub_intent") or "")[:120],
            "sentiment": str(parsed.get("sentiment") or base["sentiment"])[:40],
            "confidence_bucket": str(parsed.get("confidence_bucket") or base["confidence_bucket"])[:40],
            "is_knowledge_gap": bool(parsed.get("is_knowledge_gap", base["is_knowledge_gap"])),
            "gap_reason": str(parsed.get("gap_reason") or base["gap_reason"])[:240],
        })
    except Exception as e:
        logger.warning(f"Intent classification failed: {e}")

    await log_message_insight(session_id, customer_id, channel, message_text, **base)
