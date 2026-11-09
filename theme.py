# Rasd - ثوابت الثيم البصري + محرّك الثيمات (Matrix / Light / Dark) مع لون مميز
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# الثيم الافتراضي (Matrix) - نفس ألوان النسخة السابقة بالضبط
# ---------------------------------------------------------------------------
MATRIX_PALETTE = {
    'BG_VOID': '#070A0E',
    'BG_PANEL': '#0D1219',
    'BG_ALT_ROW': '#0A0E14',
    'BG_HEADER': '#131B24',
    'BG_SELECTED': '#0F291E',
    'BG_HOVER': '#162430',
    'BORDER_DIM': '#1C2A38',
    'BORDER_GLOW': '#00FF66',
    'FG_PRIMARY': '#E2F1E8',
    'FG_MUTED': '#5E766A',
    'ACCENT_MATRIX': '#00FF66',
    'ACCENT_CYAN': '#00E5FF',
    'ACCENT_AMBER': '#FFB800',
    'ACCENT_DANGER': '#FF3355',
    'PRI_URGENT': '#FF3355',
    'PRI_NORMAL': '#38BDF8',
    'PRI_LOW': '#FFB800',
}

COLOR_KEYS = tuple(MATRIX_PALETTE.keys())

THEME_NAMES = ('matrix', 'light', 'dark')
THEME_LABELS = {
    'matrix': {'ar': 'Matrix (التيرمينال)', 'en': 'Matrix (Terminal)'},
    'light': {'ar': 'أبيض تقليدي', 'en': 'Light'},
    'dark': {'ar': 'أسود', 'en': 'Dark'},
}

# ألوان جاهزة للاختيار السريع (شبيهة بلوحة ألوان Windows)
ACCENT_PRESETS = (
    '#0067C0',  # Windows blue
    '#0E7C66',  # teal
    '#00A86B',  # green
    '#7C3AED',  # violet
    '#D97706',  # amber
    '#DC2626',  # red
    '#0EA5E9',  # sky
    '#DB2777',  # pink
)

DEFAULT_ACCENTS = {'matrix': '#00FF66', 'light': '#0067C0', 'dark': '#4CC2FF'}


def _rgb(value):
    value = value.strip().lstrip('#')
    if len(value) == 3:
        value = ''.join(ch * 2 for ch in value)
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _hex(rgb):
    return '#%02X%02X%02X' % tuple(max(0, min(255, int(round(c)))) for c in rgb)


def mix(color_a, color_b, ratio):
    """يمزج لونين بنسبة ratio من color_b."""
    a, b = _rgb(color_a), _rgb(color_b)
    return _hex(tuple(a[i] + (b[i] - a[i]) * ratio for i in range(3)))


def lighten(color, ratio):
    return mix(color, '#FFFFFF', ratio)


def darken(color, ratio):
    return mix(color, '#000000', ratio)


def luminance(color):
    r, g, b = _rgb(color)
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0


def readable_accent(accent, background):
    """يضمن تباينًا كافيًا بين اللون المميز والخلفية."""
    accent = accent if accent and accent.startswith('#') and len(accent) == 7 else '#0067C0'
    if luminance(background) < 0.5:
        if luminance(accent) < 0.42:
            accent = lighten(accent, 0.42)
    else:
        if luminance(accent) > 0.5:
            accent = darken(accent, 0.38)
    return accent


def build_palette(theme='matrix', accent=None):
    theme = theme if theme in THEME_NAMES else 'matrix'
    if theme == 'matrix':
        return dict(MATRIX_PALETTE)

    accent = accent or DEFAULT_ACCENTS[theme]

    if theme == 'light':
        base = {
            'BG_VOID': '#F3F5F8',
            'BG_PANEL': '#FFFFFF',
            'BG_ALT_ROW': '#F7F9FB',
            'BG_HEADER': '#E9EEF4',
            'BORDER_DIM': '#C9D4DF',
            'FG_PRIMARY': '#17212B',
            'FG_MUTED': '#5B6B7B',
        }
        base['BORDER_GLOW'] = accent
        base['ACCENT_MATRIX'] = readable_accent(accent, '#FFFFFF')
        base['ACCENT_CYAN'] = readable_accent(mix(accent, '#0B4F6C', 0.35), '#FFFFFF')
        base['ACCENT_AMBER'] = '#9A6700'
        base['ACCENT_DANGER'] = '#C42B1C'
        base['BG_SELECTED'] = mix('#FFFFFF', base['ACCENT_MATRIX'], 0.14)
        base['BG_HOVER'] = mix('#FFFFFF', base['ACCENT_MATRIX'], 0.07)
        base['PRI_URGENT'] = '#C42B1C'
        base['PRI_NORMAL'] = '#0B6FB8'
        base['PRI_LOW'] = '#9A6700'
        return base

    # dark
    accent = readable_accent(accent, '#0B0E14')
    base = {
        'BG_VOID': '#0B0E14',
        'BG_PANEL': '#141925',
        'BG_ALT_ROW': '#101520',
        'BG_HEADER': '#1B2230',
        'BORDER_DIM': '#2B3444',
        'FG_PRIMARY': '#E7ECF3',
        'FG_MUTED': '#8B97A8',
    }
    base['BORDER_GLOW'] = accent
    base['ACCENT_MATRIX'] = accent
    base['ACCENT_CYAN'] = readable_accent(lighten(accent, 0.28), '#141925')
    base['ACCENT_AMBER'] = '#FFC857'
    base['ACCENT_DANGER'] = '#FF5C6C'
    base['BG_SELECTED'] = mix('#141925', accent, 0.22)
    base['BG_HOVER'] = mix('#141925', '#FFFFFF', 0.08)
    base['PRI_URGENT'] = '#FF5C6C'
    base['PRI_NORMAL'] = '#5BC8FF'
    base['PRI_LOW'] = '#FFC857'
    return base


CURRENT_THEME = 'matrix'
CURRENT_ACCENT = DEFAULT_ACCENTS['matrix']


def _push_namespace():
    """ينشر ألوان الثيم الحالي في كل وحدات المشروع (لأنها تستوردها بـ from common import *)."""
    palette = build_palette(CURRENT_THEME, CURRENT_ACCENT)
    module_dir = str(Path(__file__).resolve().parent).lower()
    for module in list(sys.modules.values()):
        try:
            path = getattr(module, '__file__', None)
            if not path:
                continue
            if not str(Path(path).resolve().parent).lower().startswith(module_dir):
                continue
        except Exception:
            continue
        for key, value in palette.items():
            setattr(module, key, value)
    return palette


def apply_theme(theme='matrix', accent=None):
    """يغيّر الثيم الحالي وينشره في كل الوحدات. يرجع لوحة الألوان الجديدة."""
    global CURRENT_THEME, CURRENT_ACCENT
    theme = theme if theme in THEME_NAMES else 'matrix'
    CURRENT_THEME = theme
    CURRENT_ACCENT = accent or DEFAULT_ACCENTS[theme]
    return _push_namespace()


_matrix = build_palette('matrix')
globals().update(_matrix)

# ألوان الأولويات الموحدة للمهام والتقويم (تُعاد ضبطها حسب الثيم)
PRI_URGENT = _matrix['PRI_URGENT']
PRI_NORMAL = _matrix['PRI_NORMAL']
PRI_LOW = _matrix['PRI_LOW']

# خط الواجهة الداعم للعربية بالكامل، وخط التيرمينال للعناوين الإنجليزية
TERM_FONT = 'Segoe UI'
MONO_FONT = 'Consolas'
RLM = '\u200f'
