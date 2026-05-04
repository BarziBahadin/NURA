"""
Extract training pairs from raw Rcell chat logs (base chat.csv + base requests.csv).
Also loads articles from .manafest/articals.json as additional training pairs.
"""
import json
import re
import logging
import pandas as pd

from training.config import (
    EXCLUDED_CATEGORIES,
    PUK_KEYWORDS,
    ARTICLES_JSON,
    MANUAL_TRAINING_CSV,
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)

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
    if any(w in t for w in ['بطيء', 'سرعة', 'شبكة', 'slow', 'network', 'internet', 'apn', '5g', 'coverage', 'fttx']):
        return 'network_internet'
    if any(w in t for w in ['حساب', 'كلمة', 'password', 'login', 'مرور', 'pin', 'puk', 'sim']):
        return 'account_security'
    if any(w in t for w in ['باقة', 'رصيد', 'package', 'balance', 'نقاط', 'recharge', 'card']):
        return 'packages_billing'
    if any(w in t for w in ['تطبيق', 'self-care', 'app', 'hakki', 'ana']):
        return 'apps'
    if any(w in t for w in ['hd call', 'volte']):
        return 'voice_services'
    return 'general'


def _article_category(title: str, content: str) -> str:
    return _detect_category(f"{title} {content[:300]}")


def _article_topic_terms(title: str) -> list[str]:
    t = title.lower()
    terms = []
    if 'self-care' in t or 'self care' in t:
        terms += ['تطبيق Self-Care', 'تطبيق الرعاية الذاتية', 'الخدمة الذاتية']
    if 'hakki' in t:
        terms += ['تطبيق Hakki', 'تطبيق حكي']
    if 'ana' in t:
        terms += ['منصة آنا', 'Ana']
    if 'internet' in t or 'connectivity' in t:
        terms += ['الإنترنت', 'الاتصال', 'بيانات الهاتف']
    if 'apn' in t:
        terms += ['إعدادات APN', 'نقطة الوصول APN']
    if 'hd call' in t or 'volte' in t:
        terms += ['HD Call', 'VoLTE', 'المكالمات عالية الدقة']
    if 'password' in t:
        terms += ['كلمة المرور', 'الباسورد']
    if 'pin' in t:
        terms += ['الرمز السري PIN', 'PIN']
    if 'puk' in t or 'locked sim' in t:
        terms += ['رمز PUK', 'الشريحة المقفلة', 'SIM مقفلة']
    if 'package' in t:
        terms += ['الباقات', 'أسعار الباقات']
    if 'points' in t:
        terms += ['النقاط', 'إرسال النقاط']
    if 'sim' in t and 'puk' not in t:
        terms += ['شريحة SIM', 'الشريحة']
    if 'esim' in t:
        terms += ['eSIM', 'الشريحة الرقمية']
    if '5g' in t:
        terms += ['شبكة 5G', 'الجيل الخامس']
    if 'coverage' in t:
        terms += ['التغطية', 'مراكز الشركة']
    if 'business' in t or 'fttx' in t:
        terms += ['إنترنت الأعمال', 'FTTx']
    if 'working hours' in t or 'show room' in t:
        terms += ['ساعات العمل', 'أوقات الدوام', 'المعرض']
    if 'recharge' in t or 'card' in t:
        terms += ['بطاقة الشحن', 'كرت الشحن']
    if 'fast data' in t or 'drain' in t:
        terms += ['نفاد الرصيد بسرعة', 'استهلاك البيانات']
    return list(dict.fromkeys(terms))


def _specific_article_questions(title: str) -> list[str]:
    t = title.lower()
    questions: list[str] = []
    if 'downloading self-care' in t:
        questions += [
            'كيف أحمل تطبيق Self-Care؟',
            'أريد رابط تحميل تطبيق الرعاية الذاتية',
            'من أين أحصل على تطبيق Self-Care للأندرويد؟',
            'هل يوجد تطبيق Self-Care على الآيفون؟',
            'أرسلوا لي رابط تحميل تطبيق الخدمة الذاتية',
        ]
    if 'inability to access self-care' in t:
        questions += [
            'لا أستطيع فتح تطبيق Self-Care ماذا أفعل؟',
            'تطبيق الرعاية الذاتية لا يعمل عندي',
            'الموقع لا يفتح معي لكن الإنترنت يعمل',
            'عندي مشكلة في الوصول إلى الخدمة الذاتية',
            'Self-Care لا يدخلني إلى الحساب',
        ]
    if 'pin' in t:
        questions += [
            'كيف أفعل الرمز السري PIN؟',
            'أريد تفعيل PIN على حسابي',
            'ما طريقة استخدام الرمز السري؟',
            'هل أحتاج PIN لحماية حسابي؟',
            'كيف أغير أو أفعل رمز PIN؟',
        ]
    if 'connectivity' in t:
        questions += [
            'لا يوجد اتصال بالإنترنت عندي',
            'البيانات لا تعمل على الهاتف',
            'عندي شبكة لكن الإنترنت لا يفتح',
            'ما خطوات فحص الاتصال؟',
            'الإنترنت منقطع رغم وجود إشارة',
        ]
    if 'sending points' in t:
        questions += [
            'كيف أرسل نقاط لشخص آخر؟',
            'أريد تحويل نقاط من رقمي',
            'هل يمكن إرسال النقاط بين المستخدمين؟',
            'عملية إرسال النقاط فشلت لماذا؟',
            'ما طريقة مشاركة النقاط؟',
        ]
    if 'downloading hakki' in t:
        questions += [
            'كيف أحمل تطبيق Hakki؟',
            'أين رابط تحميل تطبيق حكي؟',
            'هل تطبيق Hakki متوفر للأندرويد؟',
            'أريد تحميل حكي على الآيفون',
            'أرسلوا لي رابط تطبيق Hakki',
        ]
    if 'slow internet' in t:
        questions += [
            'الإنترنت بطيء جداً عندي',
            'سرعة النت ضعيفة منذ الصباح',
            'عندي تقطيع في الإنترنت',
            'البيانات تعمل لكن ببطء شديد',
            'كيف أحل مشكلة بطء الإنترنت؟',
        ]
    if 'hd call' in t or 'volte' in t:
        questions += [
            'ما هي خدمة HD Call؟',
            'كيف أفعل VoLTE على هاتفي؟',
            'هل هاتفي يدعم HD Call؟',
            'المكالمات عالية الدقة لا تعمل',
            'ما فائدة خدمة VoLTE؟',
        ]
    if 'log in' in t or 'login' in t:
        questions += [
            'لا أستطيع تسجيل الدخول',
            'تظهر لي مشكلة عند تسجيل الدخول',
            'الحساب لا يقبل الدخول في Self-Care',
            'عندي خطأ في تسجيل الدخول للتطبيق',
            'لماذا لا يعمل تسجيل الدخول؟',
        ]
    if 'password' in t:
        questions += [
            'نسيت كلمة المرور ماذا أفعل؟',
            'كيف أستعيد الباسورد؟',
            'أريد تغيير كلمة المرور',
            'كلمة المرور لا تعمل معي',
            'كيف أعيد تعيين كلمة المرور؟',
        ]
    if 'package' in t:
        questions += [
            'أريد معرفة أسعار الباقات',
            'ما هي الباقات المتوفرة؟',
            'كيف أستفسر عن باقتي؟',
            'ما الباقة المناسبة للإنترنت؟',
            'أين أجد تفاصيل الباقات؟',
        ]
    if 'working hours' in t or 'show room' in t:
        questions += [
            'ما هي ساعات العمل؟',
            'متى يفتح مركز الخدمة؟',
            'أريد معرفة أوقات الدوام',
            'هل تعملون يوم الجمعة؟',
            'متى يغلق المعرض؟',
        ]
    if 'sim enquiry' in t:
        questions += [
            'أريد الاستفسار عن شريحة SIM',
            'كيف أحصل على شريحة جديدة؟',
            'لدي سؤال عن الشريحة',
            'هل يمكن تبديل شريحة SIM؟',
            'ما معلومات الشريحة المتوفرة؟',
        ]
    if 'ana platform' in t:
        questions += [
            'ما هي منصة آنا؟',
            'كيف أستخدم Ana؟',
            'أريد الدخول إلى منصة آنا',
            'هل منصة Ana مرتبطة بالحساب؟',
            'ما فائدة منصة آنا؟',
        ]
    if 'apn' in t:
        questions += [
            'ما هي إعدادات APN؟',
            'كيف أضبط نقطة الوصول؟',
            'أحتاج إعدادات الإنترنت APN',
            'الإنترنت لا يعمل بعد تغيير APN',
            'ما إعدادات APN الصحيحة؟',
        ]
    if 'fast data' in t or 'drain' in t:
        questions += [
            'الرصيد ينتهي بسرعة',
            'البيانات تستهلك بسرعة كبيرة',
            'لماذا تنتهي الباقة بسرعة؟',
            'أريد معرفة سبب نفاد الإنترنت',
            'رصيدي يخلص بدون استخدام كثير',
        ]
    if 'puk' in t or 'locked sim' in t:
        questions += [
            'الشريحة مقفلة وتطلب رمز PUK',
            'أحتاج رمز PUK للشريحة',
            'أدخلت الرمز خطأ والشريحة انقفلت',
            'كيف أفتح SIM مقفلة؟',
            'ما الحل إذا طلب الهاتف PUK؟',
        ]
    if 'esim' in t:
        questions += [
            'هل توفرون eSIM؟',
            'أريد شريحة رقمية',
            'كيف أحصل على eSIM؟',
            'هل تعمل الشريحة الرقمية على رقمي؟',
            'ما الفرق بين eSIM والشريحة العادية؟',
        ]
    if '5g' in t:
        questions += [
            'هل شبكة 5G متوفرة؟',
            'متى يتم تشغيل الجيل الخامس؟',
            'هل هاتفي يدعم 5G مع شبكتكم؟',
            'أريد معرفة موعد توفر 5G',
            'هل يوجد تغطية 5G حالياً؟',
        ]
    if 'coverage' in t:
        questions += [
            'كيف أعرف التغطية في منطقتي؟',
            'هل يوجد مركز خدمة قريب؟',
            'أريد معلومات عن تغطية الشركة',
            'التغطية ضعيفة في منطقتي',
            'كم عدد مراكز الشركة؟',
        ]
    if 'business' in t or 'fttx' in t:
        questions += [
            'أريد إنترنت أعمال',
            'هل لديكم خدمة FTTx؟',
            'أحتاج إنترنت للشركة',
            'ما حلول الإنترنت للمكاتب؟',
            'كيف أتواصل مع مبيعات إنترنت الأعمال؟',
        ]
    if 'hakki emergency' in t:
        questions += [
            'هل أستطيع الاتصال بدون رصيد عبر Hakki؟',
            'كيف يعمل الاستخدام المجاني في الطوارئ؟',
            'تطبيق حكي يسمح بالمكالمة بعد نفاد الرصيد؟',
            'أحتاج مكالمة طارئة ولا يوجد رصيد',
            'ما شروط مكالمات الطوارئ في Hakki؟',
        ]
    if 'damaged recharge' in t:
        questions += [
            'بطاقة الشحن انمسح جزء من الكود',
            'كرت الشحن مخدوش ولا أستطيع قراءة الرقم',
            'اشتريت بطاقة شحن تالفة ماذا أفعل؟',
            'هل يمكن مساعدتي بصورة بطاقة الشحن؟',
            'الكود غير واضح على كرت الشحن',
        ]
    return questions


def _generic_article_questions(title: str) -> list[str]:
    terms = _article_topic_terms(title) or [title]
    prefixes = [
        'أريد معلومات عن {term}',
        'ما تفاصيل {term}؟',
        'كيف أستخدم {term}؟',
        'عندي مشكلة في {term}',
        'هل يمكنكم شرح {term}؟',
        'ما الخطوات المطلوبة بخصوص {term}؟',
        'أحتاج مساعدة في {term}',
        'لم أفهم موضوع {term} وأحتاج توضيحاً',
        'هل توجد طريقة لحل مشكلة {term}؟',
        'أريد جواباً واضحاً عن {term}',
    ]
    questions = []
    for term in terms[:3]:
        questions.extend(template.format(term=term) for template in prefixes)
    return questions


def _article_questions(title: str) -> list[str]:
    questions = [title]
    questions.extend(_specific_article_questions(title))
    questions.extend(_generic_article_questions(title))
    return list(dict.fromkeys(q.strip() for q in questions if q and q.strip()))


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
            category = _article_category(title, content)
            for idx, question in enumerate(_article_questions(title)):
                pairs.append({
                    'request_id': f"article_{title[:20]}_{idx}",
                    'category': category,
                    'customer_question': question,
                    'agent_response': content,
                })
    logger.info(f"Loaded {len(pairs)} pairs from articles")
    return pairs


def _manual_question_variants(question: str) -> list[str]:
    q = question.strip()
    if not q:
        return []
    variants = [
        q,
        f"لو سمحت {q}",
        f"عندي سؤال: {q}",
        f"ممكن تساعدوني؟ {q}",
        f"السلام عليكم، {q}",
    ]
    if not q.endswith(("؟", "?")):
        variants.append(f"{q}؟")
    return list(dict.fromkeys(variants))


def load_manual_training_pairs() -> list[dict]:
    if not MANUAL_TRAINING_CSV.exists():
        logger.info(f"Manual training file not found: {MANUAL_TRAINING_CSV}")
        return []
    df = pd.read_csv(MANUAL_TRAINING_CSV)
    required = {"customer_question", "agent_response", "category"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Manual training file missing columns: {', '.join(sorted(missing))}")
    df = df.fillna("")
    rows = []
    for i, row in df.iterrows():
        question = _clean(row["customer_question"])
        answer = _clean(row["agent_response"])
        category = str(row["category"]).strip() or _detect_category(question)
        if len(question) < _MIN_CUSTOMER_LEN or len(answer) < _MIN_AGENT_LEN:
            continue
        base_id = str(row.get("request_id") or f"manual_{i}")
        for variant_idx, variant in enumerate(_manual_question_variants(question)):
            rows.append({
                "request_id": f"{base_id}_{variant_idx}",
                "category": category,
                "customer_question": variant,
                "agent_response": answer,
            })
    logger.info(f"Loaded {len(rows)} pairs from manual training file")
    return rows


async def _fetch_approved_gap_rows(limit: int) -> list[dict]:
    try:
        import asyncpg
    except ImportError:
        logger.info("asyncpg is not installed — trying docker compose postgres export.")
        return _fetch_approved_gap_rows_via_docker(limit)

    if not POSTGRES_PASSWORD:
        logger.warning("POSTGRES_PASSWORD is missing — skipping approved knowledge gaps.")
        return []

    conn = None
    try:
        conn = await asyncpg.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
        )
        rows = await conn.fetch(
            """
            SELECT id, customer_message, approved_answer, intent, sub_intent, gap_reason
            FROM knowledge_gap_reviews
            WHERE status IN ('approved', 'resolved')
              AND approved_answer IS NOT NULL
              AND approved_answer != ''
              AND customer_message IS NOT NULL
              AND customer_message != ''
            ORDER BY reviewed_at DESC NULLS LAST, updated_at DESC
            LIMIT $1
            """,
            limit,
        )
        return [dict(row) for row in rows]
    except Exception as e:
        logger.warning(f"Could not load approved knowledge gaps from Postgres: {e}")
        return []
    finally:
        if conn is not None:
            await conn.close()


def _fetch_approved_gap_rows_via_docker(limit: int) -> list[dict]:
    import subprocess

    query = f"""
    COPY (
      SELECT COALESCE(json_agg(row_to_json(t)), '[]'::json)
      FROM (
        SELECT id, customer_message, approved_answer, intent, sub_intent, gap_reason
        FROM knowledge_gap_reviews
        WHERE status IN ('approved', 'resolved')
          AND approved_answer IS NOT NULL
          AND approved_answer != ''
          AND customer_message IS NOT NULL
          AND customer_message != ''
        ORDER BY reviewed_at DESC NULLS LAST, updated_at DESC
        LIMIT {int(limit)}
      ) t
    ) TO STDOUT
    """
    cmd = [
        "docker",
        "compose",
        "exec",
        "-T",
        "postgres",
        "psql",
        "-U",
        POSTGRES_USER,
        "-d",
        POSTGRES_DB,
        "-t",
        "-A",
        "-c",
        query,
    ]
    try:
        result = subprocess.run(cmd, check=True, text=True, capture_output=True)
        output = result.stdout.strip()
        return json.loads(output) if output else []
    except subprocess.CalledProcessError as e:
        detail = (e.stderr or str(e)).strip()
        logger.warning(f"Could not load approved knowledge gaps through docker compose: {detail}")
        return []
    except Exception as e:
        logger.warning(f"Could not load approved knowledge gaps through docker compose: {e}")
        return []


def load_approved_gap_pairs(limit: int = 1000) -> list[dict]:
    """
    Convert admin-approved knowledge gaps into ML training pairs.
    This closes the correction loop: failed answer -> reviewed answer -> retrain.
    """
    import asyncio

    rows = asyncio.run(_fetch_approved_gap_rows(limit))
    pairs = []
    for row in rows:
        question = _clean(row.get("customer_message") or "")
        answer = _clean(row.get("approved_answer") or "")
        if len(question) < _MIN_CUSTOMER_LEN or len(answer) < _MIN_QUALITY_LEN:
            continue
        category = (
            row.get("intent")
            or row.get("sub_intent")
            or row.get("gap_reason")
            or _detect_category(question)
        )
        pairs.append({
            "request_id": f"gap_{row['id']}",
            "category": category,
            "customer_question": question,
            "agent_response": answer,
        })

    logger.info(f"Loaded {len(pairs)} pairs from approved knowledge gaps")
    return pairs
