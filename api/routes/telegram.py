import asyncio
import json
import logging
from typing import Optional

import httpx

from config import settings
from core.message_pipeline import process_customer_message
from core.session_manager import SESSION_TTL, append_turn, get_or_create_session, get_redis, save_session
from core.utils import fire_task
from models.session import SessionStatus

logger = logging.getLogger(__name__)

_TG_BASE = "https://api.telegram.org/bot{token}/{method}"

WELCOME_AR = (
    "مرحبًا بك في خدمة عملاء {company}! 👋\n"
    "اختر موضوعًا من القائمة أو اكتب سؤالك مباشرة:"
)
AGENT_WAITING_AR = "تم استلام رسالتك. سيتواصل معك أحد أعضاء الفريق قريبًا."
AGENT_REQUESTED_AR = "⏳ تم تحويلك إلى موظف بشري. سيتواصل معك أحد أعضاء الفريق قريبًا."
RESOLVED_AR = (
    "✅ تم إغلاق المحادثة. نشكرك على تواصلك مع {company}!\n\n"
    "كيف تقيّم تجربتك معنا؟"
)
RATING_THANKS_AR = "شكراً على تقييمك {stars}! رأيك يهمنا."
COMPLAINT_AR = (
    "لتقديم شكوى أو اقتراح:\n\n"
    "يمكنك التواصل معنا عبر إحدى الطرق التالية:\n\n"
    "• الدردشة المباشرة: اضغط على زر «التحدث مع موظف» أدناه.\n"
    "• الهاتف: تواصل مع خدمة العملاء على الرقم المعتمد.\n"
    "• مراكز Rcell: قم بزيارة أقرب مركز خدمة.\n\n"
    "سيتم التعامل مع شكواك أو اقتراحك في أقرب وقت ممكن."
)

# ── Topic tree ─────────────────────────────────────────────────────────────

_TOPIC_TREE: dict = {"id": "root", "label": "القائمة", "children": []}

try:
    with open("/app/manafest/topic_tree.json", "r", encoding="utf-8") as f:
        _TOPIC_TREE = json.load(f)
    logger.info("Telegram: loaded shared topic tree")
except Exception as e:
    logger.error(f"Could not load topic tree: {e}")


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


async def _get_chat_session(chat_id: int):
    r = get_redis()
    mapped_id = await r.get(f"tg:session:{chat_id}")
    session_id = mapped_id or f"tg_{chat_id}"
    session = await get_or_create_session(
        session_id=session_id,
        customer_id=str(chat_id),
        channel="telegram",
    )
    if session.session_id != session_id:
        await r.set(f"tg:session:{chat_id}", session.session_id, ex=SESSION_TTL)
    elif not mapped_id:
        await r.set(f"tg:session:{chat_id}", session.session_id, ex=SESSION_TTL)
    return session


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


def _rating_keyboard() -> dict:
    return {"inline_keyboard": [[
        {"text": "⭐ 1", "callback_data": "r:1"},
        {"text": "⭐⭐ 2", "callback_data": "r:2"},
        {"text": "⭐⭐⭐ 3", "callback_data": "r:3"},
        {"text": "⭐⭐⭐⭐ 4", "callback_data": "r:4"},
        {"text": "⭐⭐⭐⭐⭐ 5", "callback_data": "r:5"},
    ]]}


async def send_resolved_to_telegram(chat_id: int) -> None:
    """Call this from session/handoff routes when a Telegram session is closed."""
    await _send(
        chat_id,
        RESOLVED_AR.format(company=settings.company_name),
        reply_markup=_rating_keyboard(),
    )


# ── Callback query handler (inline button taps) ───────────────────────────

async def _handle_callback(cb: dict) -> None:
    await _call("answerCallbackQuery", http_timeout=5.0, callback_query_id=cb["id"])

    data: str = cb.get("data", "")
    chat_id: int = cb["message"]["chat"]["id"]
    msg_id: int  = cb["message"]["message_id"]

    # Rating callback
    if data.startswith("r:"):
        score = int(data[2:])
        stars = "⭐" * score
        await _call(
            "editMessageReplyMarkup",
            http_timeout=10.0,
            chat_id=chat_id,
            message_id=msg_id,
            reply_markup={"inline_keyboard": []},
        )
        await _send(chat_id, RATING_THANKS_AR.format(stars=stars))
        await _send(
            chat_id,
            WELCOME_AR.format(company=settings.company_name),
            reply_markup=_build_keyboard(_TOPIC_TREE),
        )
        return

    if not data.startswith("t:"):
        return

    node_id = data[2:]
    node = _find_node(node_id)
    if not node:
        return

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
    elif node.get("action") == "complaint":
        keyboard = {"inline_keyboard": [
            [{"text": "🎧 التحدث مع موظف مباشرة", "callback_data": "t:other_agent"}],
            [
                {"text": "🔙 رجوع",      "callback_data": f"t:{node.get('parent_id', 'root')}"},
                {"text": "🏠 الرئيسية", "callback_data": "t:root"},
            ],
        ]}
        await _call(
            "editMessageText",
            http_timeout=10.0,
            chat_id=chat_id,
            message_id=msg_id,
            text=COMPLAINT_AR,
            reply_markup=keyboard,
        )
    elif node.get("action") == "agent":
        session = await _get_chat_session(chat_id)
        if session.status not in (SessionStatus.pending_handoff, SessionStatus.human_active):
            session.status = SessionStatus.pending_handoff
            session.metadata["handoff_reason"] = "direct_request"
            await save_session(session)
        await _call(
            "editMessageText",
            http_timeout=10.0,
            chat_id=chat_id,
            message_id=msg_id,
            text=AGENT_REQUESTED_AR,
            reply_markup={"inline_keyboard": []},
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

    customer_id = str(chat_id)
    session = await _get_chat_session(chat_id)

    if session.status in (SessionStatus.pending_handoff, SessionStatus.human_active):
        await append_turn(session, "customer", text, source="customer")
        await save_session(session)
        return

    result = await process_customer_message(
        session_id=session.session_id,
        customer_id=customer_id,
        channel="telegram",
        message=text,
        include_session_token=False,
    )

    # After AI reply, show the menu again so user can easily navigate
    keyboard = _build_keyboard(_TOPIC_TREE)
    await _send(chat_id, result.response_text or AGENT_WAITING_AR, reply_markup=keyboard)


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
    if not settings.telegram_poller_enabled:
        logger.info("Telegram polling disabled by TELEGRAM_POLLER_ENABLED")
        return
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
                    fire_task(_handle_update(update), label="tg:handle_update")
        except asyncio.CancelledError:
            logger.info("Telegram poller cancelled")
            break
        except Exception as e:
            logger.warning(f"Telegram polling error: {e}")
            await asyncio.sleep(5)
