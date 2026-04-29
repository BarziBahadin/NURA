import asyncio
import json
import logging
from typing import Optional

import httpx

from config import settings
from core.handoff_controller import HANDOFF_MESSAGE_AR, check_handoff_triggers, trigger_handoff
from core.job_queue import JOB_INTENT_CLASSIFICATION, enqueue_job
from core.logger import log_conversation, log_session_outcome
from core.orchestrator import generate_response
from core.session_manager import append_turn, get_or_create_session, save_session
from models.session import SessionStatus

logger = logging.getLogger(__name__)

_TG_BASE = "https://api.telegram.org/bot{token}/{method}"

WELCOME_AR = (
    "مرحبًا بك في خدمة عملاء {company}! 👋\n"
    "اختر موضوعًا من القائمة أو اكتب سؤالك مباشرة:"
)
AGENT_WAITING_AR = "تم استلام رسالتك. سيتواصل معك أحد أعضاء الفريق قريبًا."

# ── Topic tree (mirrors widget.js TOPIC_TREE, Arabic labels) ──────────────

_TOPIC_TREE: dict = {
    "id": "root",
    "label": "كيف يمكنني مساعدتك؟",
    "children": [
        {"id": "apps", "label": "📱 التطبيقات", "children": [
            {"id": "selfcare", "label": "تطبيق Self-Care", "children": [
                {"id": "sc_dl",     "label": "تحميل التطبيق",            "article": 0},
                {"id": "sc_login",  "label": "مشكلة في تسجيل الدخول",    "article": 13},
                {"id": "sc_access", "label": "لا أستطيع الوصول للموقع",  "article": 1},
            ]},
            {"id": "hakki", "label": "تطبيق حكي", "children": [
                {"id": "hk_dl",  "label": "تحميل التطبيق",                "article": 5},
                {"id": "hk_sos", "label": "الاستخدام المجاني في الطوارئ", "article": 28},
            ]},
            {"id": "ana", "label": "منصة آنا (Ana)", "article": 20},
        ]},
        {"id": "internet", "label": "🌐 الإنترنت والاتصال", "children": [
            {"id": "slow",   "label": "الإنترنت بطيء",   "article": 6},
            {"id": "noconn", "label": "لا يوجد اتصال",   "article": 3},
            {"id": "apn",    "label": "إعدادات APN",      "article": 21},
            {"id": "fiveg",  "label": "5G — قريباً",      "article": 25},
            {"id": "hdcall", "label": "HD Call (VoLTE)", "children": [
                {"id": "hd_what", "label": "ما هو HD Call؟",   "article": 7},
                {"id": "hd_why",  "label": "مميزاته",           "article": 8},
                {"id": "hd_sup",  "label": "هل هاتفي يدعمه؟",  "article": 9},
                {"id": "hd_act",  "label": "كيف أفعّله؟",       "article": 10},
                {"id": "hd_use",  "label": "كيف أستخدمه؟",     "article": 11},
                {"id": "hd_fix",  "label": "مشكلة في HD Call",  "article": 12},
            ]},
        ]},
        {"id": "account", "label": "🔐 الحساب والأمان", "children": [
            {"id": "password", "label": "كلمة المرور", "children": [
                {"id": "pw_change",  "label": "تغيير كلمة المرور",  "article": 14},
                {"id": "pw_recover", "label": "نسيت كلمة المرور",   "article": 19},
            ]},
            {"id": "pin",        "label": "الرمز السري PIN",         "article": 2},
            {"id": "login_prob", "label": "مشكلة في تسجيل الدخول",  "article": 13},
            {"id": "puk",        "label": "SIM مقفلة / رمز PUK",    "article": 23},
        ]},
        {"id": "packages", "label": "📦 الباقات والخدمات", "children": [
            {"id": "pkg_prices",  "label": "أسعار الباقات",        "article": 16},
            {"id": "sim",         "label": "شريحة SIM",            "article": 18},
            {"id": "esim",        "label": "eSIM الرقمية",         "article": 24},
            {"id": "points",      "label": "إرسال النقاط",         "article": 4},
            {"id": "fastdata",    "label": "الرصيد ينتهي بسرعة",   "article": 22},
            {"id": "scratchcard", "label": "بطاقة شحن محكوكة",     "article": 29},
        ]},
        {"id": "info", "label": "ℹ️ معلومات عامة", "children": [
            {"id": "hours",    "label": "ساعات العمل",           "article": 17},
            {"id": "coverage", "label": "تغطية الشركة ومراكزها", "article": 26},
            {"id": "business", "label": "إنترنت الأعمال FTTx",   "article": 27},
        ]},
    ],
}


def _index_tree(node: dict, parent_id: str = "root", idx: dict = None) -> dict:
    if idx is None:
        idx = {}
    node["parent_id"] = parent_id
    idx[node["id"]] = node
    for child in node.get("children", []):
        _index_tree(child, node["id"], idx)
    return idx


_TREE_INDEX: dict = _index_tree(_TOPIC_TREE)


def _find_node(node_id: str) -> Optional[dict]:
    return _TREE_INDEX.get(node_id)


# ── Articles ──────────────────────────────────────────────────────────────

_ARTICLES: list = []
try:
    with open("/app/manafest/articals.json", "r", encoding="utf-8") as f:
        _ARTICLES = json.load(f)
    logger.info(f"Telegram: loaded {len(_ARTICLES)} articles")
except Exception as e:
    logger.warning(f"Telegram: could not load articles: {e}")


def _article_text(idx: int) -> str:
    if 0 <= idx < len(_ARTICLES):
        a = _ARTICLES[idx]
        return f"{a.get('title', '')}\n\n{a.get('content_ar', '')}"
    return "المعلومات غير متاحة حالياً."


# ── Keyboard builder ──────────────────────────────────────────────────────

def _build_keyboard(node: dict) -> dict:
    rows = []
    for child in node.get("children", []):
        suffix = " ›" if child.get("children") else ""
        rows.append([{"text": child["label"] + suffix, "callback_data": f"t:{child['id']}"}])
    if node["id"] != "root":
        rows.append([
            {"text": "🔙 رجوع",      "callback_data": f"t:{node.get('parent_id', 'root')}"},
            {"text": "🏠 الرئيسية", "callback_data": "t:root"},
        ])
    return {"inline_keyboard": rows}


# ── Telegram HTTP helpers ─────────────────────────────────────────────────

async def _call(method: str, http_timeout: float = 10.0, **kwargs) -> dict:
    url = _TG_BASE.format(token=settings.telegram_bot_token, method=method)
    async with httpx.AsyncClient(timeout=http_timeout) as client:
        r = await client.post(url, json=kwargs)
        return r.json()


async def _send(chat_id: int, text: str, **kwargs) -> None:
    try:
        await _call("sendMessage", http_timeout=10.0, chat_id=chat_id, text=text, **kwargs)
    except Exception as e:
        logger.warning(f"Telegram sendMessage failed: {e}")


# ── Callback query handler (inline button taps) ───────────────────────────

async def _handle_callback(cb: dict) -> None:
    await _call("answerCallbackQuery", http_timeout=5.0, callback_query_id=cb["id"])

    data: str = cb.get("data", "")
    if not data.startswith("t:"):
        return

    node_id = data[2:]
    node = _find_node(node_id)
    if not node:
        return

    chat_id: int = cb["message"]["chat"]["id"]
    msg_id: int  = cb["message"]["message_id"]

    if node.get("children"):
        await _call(
            "editMessageText",
            http_timeout=10.0,
            chat_id=chat_id,
            message_id=msg_id,
            text=f"📂 {node['label']}\n\nاختر موضوعاً:",
            reply_markup=_build_keyboard(node),
        )
    elif "article" in node:
        keyboard = {"inline_keyboard": [[
            {"text": "🔙 رجوع",      "callback_data": f"t:{node.get('parent_id', 'root')}"},
            {"text": "🏠 الرئيسية", "callback_data": "t:root"},
        ]]}
        await _call(
            "editMessageText",
            http_timeout=10.0,
            chat_id=chat_id,
            message_id=msg_id,
            text=_article_text(node["article"]),
            reply_markup=keyboard,
        )


# ── Message handler ───────────────────────────────────────────────────────

async def _handle_message(msg: dict) -> None:
    chat_id: int = msg["chat"]["id"]
    text: str = (msg.get("text") or "").strip()
    if not text:
        return

    if text == "/start":
        await _send(
            chat_id,
            WELCOME_AR.format(company=settings.company_name),
            reply_markup=_build_keyboard(_TOPIC_TREE),
        )
        return

    if text == "/menu":
        await _send(
            chat_id,
            "القائمة الرئيسية:",
            reply_markup=_build_keyboard(_TOPIC_TREE),
        )
        return

    session_id = f"tg_{chat_id}"
    customer_id = str(chat_id)

    session = await get_or_create_session(
        session_id=session_id,
        customer_id=customer_id,
        channel="telegram",
    )

    if session.status in (SessionStatus.pending_handoff, SessionStatus.human_active):
        await append_turn(session, "customer", text, source="customer")
        await save_session(session)
        await _send(chat_id, AGENT_WAITING_AR)
        return

    response_text, confidence, source, source_doc = await generate_response(session, text)

    should_escalate, handoff_reason = check_handoff_triggers(session, text, confidence)
    if should_escalate:
        session = trigger_handoff(session)
        session.metadata["handoff_reason"] = handoff_reason
        response_text = HANDOFF_MESSAGE_AR
        await log_session_outcome(
            session_id=session.session_id,
            status="pending_handoff",
            handoff_reason=handoff_reason,
        )

    await append_turn(session, "customer", text)
    await append_turn(session, "agent", response_text, confidence)
    await save_session(session)

    await log_conversation(
        session_id=session.session_id,
        customer_id=customer_id,
        channel="telegram",
        customer_message=text,
        agent_response=response_text,
        confidence=confidence,
        escalated=should_escalate,
        source=source if not should_escalate else "escalated",
    )
    await enqueue_job(
        JOB_INTENT_CLASSIFICATION,
        session_id=session.session_id,
        customer_id=customer_id,
        channel="telegram",
        message_text=text,
        confidence=confidence,
        source=source if not should_escalate else "escalated",
        escalated=should_escalate,
    )

    # After AI reply, show the menu again so user can easily navigate
    keyboard = _build_keyboard(_TOPIC_TREE)
    await _send(chat_id, response_text, reply_markup=keyboard)


# ── Update dispatcher ─────────────────────────────────────────────────────

async def _handle_update(update: dict) -> None:
    if "callback_query" in update:
        await _handle_callback(update["callback_query"])
        return
    msg = update.get("message") or update.get("edited_message")
    if msg:
        await _handle_message(msg)


# ── Long-polling loop ─────────────────────────────────────────────────────

async def run_telegram_poller() -> None:
    if not settings.telegram_bot_token:
        logger.info("TELEGRAM_BOT_TOKEN not set — Telegram polling disabled")
        return

    logger.info("Telegram long-polling started")
    offset = 0

    while True:
        try:
            data = await _call(
                "getUpdates",
                http_timeout=35.0,
                offset=offset,
                timeout=30,
                allowed_updates=["message", "callback_query"],
            )
            if data.get("ok"):
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    asyncio.create_task(_handle_update(update))
        except asyncio.CancelledError:
            logger.info("Telegram poller cancelled")
            break
        except Exception as e:
            logger.warning(f"Telegram polling error: {e}")
            await asyncio.sleep(5)
