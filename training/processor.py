"""
Extract training pairs from raw Rcell chat logs (base chat.csv + base requests.csv).
Also loads articles from .manafest/articals.json as additional training pairs.
"""
import json
import re
import logging
import pandas as pd

from training.config import EXCLUDED_CATEGORIES, PUK_KEYWORDS, ARTICLES_JSON

logger = logging.getLogger(__name__)

_MIN_CUSTOMER_LEN = 5
_MIN_AGENT_LEN = 12
_MIN_QUALITY_LEN = 30

_SYSTEM_RE = re.compile(
    r'(^action:\s|^operator:\s|'
    r'اهل[اًا]\s*وسهل[اًا]\s*بكم\s*يسعدنا|'
    r'شكر[اًاً]?\s{0,3}(لاختيارك|لتواصلك)|'
    r'^\s*[\d\s،,.!؟?\[\]]+\s*$)',
    re.IGNORECASE | re.DOTALL,
)

_CLARIFICATION_RE = re.compile(
    r'(وضح|توضيح|هل يمكنك|هل بإمكانك|'
    r'ارسل صورة|أرسل صورة|صورة واضحة|صورة من|'
    r'التقط صورة|أعد الإرسال|'
    r'يرجى زيارة|زيارة أقرب|مركز معتمد|'
    r'ما هو رقمك|ما رقم|أعطني رقم|'
    r'هل يمكنك إعادة)',
    re.IGNORECASE,
)

_PURE_QUESTION_RE = re.compile(r'^[^.،\n]{0,80}[؟?]\s*$')


def _is_puk(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in PUK_KEYWORDS)


def _is_system(text: str) -> bool:
    return len(text.strip()) < _MIN_AGENT_LEN or bool(_SYSTEM_RE.search(text.strip()))


def _is_quality(text: str) -> bool:
    s = text.strip()
    if len(s) < _MIN_QUALITY_LEN:
        return False
    if _CLARIFICATION_RE.search(s):
        return False
    if _PURE_QUESTION_RE.match(s):
        return False
    return True


def _clean(text: str) -> str:
    text = str(text).strip()
    text = re.sub(r'http\S+|www\S+', '[URL]', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _detect_category(question: str) -> str:
    t = question.lower()
    if any(w in t for w in ['بطيء', 'سرعة', 'شبكة', 'slow', 'network']):
        return 'Speed/Signal Issues'
    if any(w in t for w in ['حساب', 'كلمة', 'password', 'login', 'مرور']):
        return 'Account Issues'
    if any(w in t for w in ['باقة', 'رصيد', 'package', 'balance', 'نقاط']):
        return 'Billing/Packages'
    if any(w in t for w in ['تطبيق', 'self-care', 'app', 'hakki']):
        return 'App Support'
    return 'General'


def extract_from_chat_logs(messages_df: pd.DataFrame, requests_df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Extracting training pairs from chat logs...")

    messages_df = messages_df.copy()
    messages_df['request_id'] = pd.to_numeric(messages_df['request_id'], errors='coerce')
    messages_df = messages_df.dropna(subset=['request_id'])
    messages_df['request_id'] = messages_df['request_id'].astype(int)

    requests_df = requests_df.copy()
    requests_df['id'] = pd.to_numeric(requests_df['id'], errors='coerce')
    requests_df = requests_df.dropna(subset=['id'])
    requests_df['id'] = requests_df['id'].astype(int)

    cat_lookup = requests_df.set_index('id')['issue_category_name'].to_dict()
    details_lookup = (
        requests_df.set_index('id')['details'].to_dict()
        if 'details' in requests_df.columns else {}
    )

    pairs = []
    for req_id, group in messages_df.groupby('request_id'):
        group = group.sort_values('sent_at', na_position='last')
        category = cat_lookup.get(req_id) or _detect_category(
            ' '.join(group['message'].tolist())
        )

        customer_msg = None
        for _, row in group.iterrows():
            raw = str(row.get('message', '')).strip()
            if not raw:
                continue
            text = _clean(raw)
            if row['account_type'] == 'customer':
                if len(text) >= _MIN_CUSTOMER_LEN:
                    customer_msg = text
            elif row['account_type'] == 'agent':
                if _is_system(text):
                    continue
                if customer_msg and _is_quality(text):
                    pairs.append({
                        'request_id': req_id,
                        'category': category,
                        'customer_question': customer_msg,
                        'agent_response': text,
                    })
                customer_msg = None

        # Proactive: ticket description → first agent reply
        details_raw = details_lookup.get(req_id, '') or ''
        try:
            ticket_desc = json.loads(details_raw).get('description', '').strip()
        except Exception:
            ticket_desc = ''

        if ticket_desc and len(ticket_desc) >= _MIN_CUSTOMER_LEN:
            first_agent = next(
                (_clean(str(r.get('message', '')))
                 for _, r in group.iterrows()
                 if r['account_type'] == 'agent'
                 and not _is_system(_clean(str(r.get('message', ''))))),
                None,
            )
            if first_agent and _is_quality(first_agent):
                pairs.append({
                    'request_id': f"{req_id}_desc",
                    'category': category,
                    'customer_question': ticket_desc,
                    'agent_response': first_agent,
                })

    df = pd.DataFrame(pairs)
    if df.empty:
        return df

    df = df.drop_duplicates(subset=['customer_question', 'agent_response'])
    df = df[df['customer_question'].str.len() >= _MIN_CUSTOMER_LEN]
    df = df[df['agent_response'].str.len() >= _MIN_QUALITY_LEN]

    # Remove PUK
    mask = (
        df['category'].str.upper().isin({c.upper() for c in EXCLUDED_CATEGORIES})
        | df['customer_question'].str.lower().apply(_is_puk)
        | df['agent_response'].str.lower().apply(_is_puk)
    )
    df = df[~mask].reset_index(drop=True)
    logger.info(f"Extracted {len(df)} pairs from chat logs")
    return df


def load_articles_as_pairs() -> list[dict]:
    if not ARTICLES_JSON.exists():
        logger.warning(f"Articles file not found: {ARTICLES_JSON}")
        return []
    with open(ARTICLES_JSON, encoding='utf-8') as f:
        articles = json.load(f)
    pairs = []
    for a in articles:
        title = a.get('title', '')
        content = a.get('content_ar', '')
        if title and content and len(content) >= _MIN_QUALITY_LEN:
            pairs.append({
                'request_id': f"article_{title[:20]}",
                'category': 'General',
                'customer_question': title,
                'agent_response': content,
            })
    logger.info(f"Loaded {len(pairs)} pairs from articles")
    return pairs
