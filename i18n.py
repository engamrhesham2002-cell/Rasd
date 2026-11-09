# Rasd - محرّك الترجمة (العربية / الإنجليزية)
#
# الطريقة: كل نصوص الواجهة العربية تُترجم لحظيًا عبر tr() عند إنشاء العنصر أو
# تحديثه. لا تُلمس البيانات (أسماء المشاريع، المسارات، الملفات) لأن الترجمة
# تتم فقط عند تطابق النص مع قاموس الواجهة أو قواعد العبارات.
import re
from functools import lru_cache

from i18n_data import EN, PHRASES

LANGUAGES = ('ar', 'en')
LANGUAGE = 'ar'

ARABIC_RE = re.compile(r'[\u0600-\u06FF]')
_RLM = '\u200f'
_LRM = '\u200e'

# قواعد العبارات المركبة (f-strings): الأطول أولًا حتى لا تُستبدل أجزاء قبل الكل
_PHRASES_SORTED = tuple(sorted(PHRASES, key=lambda item: len(item[0]), reverse=True))

# قواعد الجمع للأرقام + وحدات عربية
_PLURAL_RULES = (
    (re.compile(r'(\d[\d,]*)\s*مجلدات فرعية|(\d[\d,]*)\s*مجلد فرعي'), 'subfolders'),
    (re.compile(r'(\d[\d,]*)\s*ملفات?'), 'files'),
    (re.compile(r'(\d[\d,]*)\s*مجلدات?'), 'folders'),
    (re.compile(r'(\d[\d,]*)\s*مشاريع|(\d[\d,]*)\s*مشروع'), 'projects'),
    (re.compile(r'(\d[\d,]*)\s*عناصر?'), 'items'),
    (re.compile(r'(\d[\d,]*)\s*أحداث|(\d[\d,]*)\s*حدث'), 'events'),
    (re.compile(r'(\d[\d,]*)\s*مهام|(\d[\d,]*)\s*مهمة'), 'tasks'),
    (re.compile(r'(\d[\d,]*)\s*صفوف|(\d[\d,]*)\s*صف'), 'rows'),
    (re.compile(r'(\d[\d,]*)\s*أعمدة|(\d[\d,]*)\s*عمود'), 'columns'),
    (re.compile(r'(\d[\d,]*)\s*شيت'), 'sheets'),
    (re.compile(r'(\d[\d,]*)\s*ملاحظات|(\d[\d,]*)\s*ملاحظة'), 'notes'),
    (re.compile(r'(\d[\d,]*)\s*تعليقات|(\d[\d,]*)\s*تعليق'), 'comments'),
    (re.compile(r'(\d[\d,]*)\s*أيام|(\d[\d,]*)\s*يوم'), 'days'),
    (re.compile(r'(\d[\d,]*)\s*ساعات|(\d[\d,]*)\s*ساعة'), 'hours'),
    (re.compile(r'(\d[\d,]*)\s*دقائق|(\d[\d,]*)\s*دقيقة'), 'minutes'),
)


def get_language():
    return LANGUAGE


def is_english():
    return LANGUAGE == 'en'


def is_rtl():
    return LANGUAGE == 'ar'


def set_language(lang):
    """يغيّر لغة الواجهة. القيمة المقبولة: ar / en."""
    global LANGUAGE
    LANGUAGE = 'en' if str(lang).lower().startswith('en') else 'ar'
    _translate.cache_clear()
    return LANGUAGE


def tr(text):
    """يترجم نص واجهة عربي إلى الإنجليزية لو اللغة الحالية إنجليزية."""
    if LANGUAGE != 'en' or not isinstance(text, str) or not text:
        return text
    return _translate(text)


def _clean(value):
    return value.replace(_RLM, '').replace(_LRM, '').strip()


@lru_cache(maxsize=8192)
def _translate(text):
    cleaned = _clean(text)
    if not cleaned:
        return text
    if not ARABIC_RE.search(cleaned):
        return text

    if cleaned in EN:
        return EN[cleaned]
    # بعض النصوص تحتوي مسافات طرفية مقصودة (مثل تسميات «عرض » أو «إضافة: »)
    raw = text.replace(_RLM, '').replace(_LRM, '')
    if raw in EN:
        return EN[raw]

    result = cleaned
    for pattern, unit in _PLURAL_RULES:
        def _repl(match, unit=unit):
            raw = next(group for group in match.groups() if group)
            number = raw.replace(',', '')
            try:
                value = int(number)
            except ValueError:
                value = 2
            return f'{raw} {unit[:-1] if value == 1 else unit}'
        result = pattern.sub(_repl, result)

    for arabic, english in _PHRASES_SORTED:
        if arabic not in result:
            continue
        prefix = r'(?<![\u0600-\u06FF])' if ARABIC_RE.match(arabic[:1]) else ''
        suffix = r'(?![\u0600-\u06FF])' if ARABIC_RE.match(arabic[-1:]) else ''
        pattern = prefix + re.escape(arabic) + suffix
        result = re.sub(pattern, lambda m, value=english: value, result)

    # نُبقي أي بقايا عربية كما هي لأنها غالبًا أسماء مشاريع/ملفات أو بيانات مستخدم.
    # النصوص لم تعد كما هي إلا إذا لم تُطابق أي قاعدة، وفي هذه الحالة نعيد النص الأصلي.
    if result == cleaned:
        return cleaned
    return result


def translate_widget_text(value):
    """يُستخدم من طبقة Tk لترجمة خيار text فقط دون لمس الأنواع الأخرى."""
    if isinstance(value, str):
        return tr(value)
    return value
