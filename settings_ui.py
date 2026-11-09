# Rasd - نافذة الإعدادات (اللغة + الثيم + اللون المميز) وزر الإعدادات الدائم
from common import *
from storage import get_app_setting, set_app_setting
import theme as theme_engine

SETTING_LANGUAGE = 'ui_language'
SETTING_THEME = 'ui_theme'
SETTING_ACCENT = 'ui_accent'

THEME_ORDER = ('matrix', 'light', 'dark')


def load_ui_settings():
    """يُستدعى عند بدء التطبيق قبل إنشاء أي واجهة، لتطبيق اللغة والثيم المحفوظين."""
    language = get_app_setting(SETTING_LANGUAGE, 'ar') or 'ar'
    theme_name = get_app_setting(SETTING_THEME, 'matrix') or 'matrix'
    accent = get_app_setting(SETTING_ACCENT, '') or ''
    set_language(language)
    theme_engine.apply_theme(theme_name, accent or None)
    return language, theme_name, accent


def current_accent(theme_name=None):
    theme_name = theme_name or theme_engine.CURRENT_THEME
    saved = get_app_setting(SETTING_ACCENT, '') or ''
    return saved or theme_engine.DEFAULT_ACCENTS.get(theme_name, '#00FF66')


class SettingsMixin:
    # ------------------------------------------------------------------
    # التطبيق الفوري
    # ------------------------------------------------------------------
    def apply_ui_settings(self, language=None, theme=None, accent=None, persist=True):
        if language:
            set_language(language)
            if persist:
                set_app_setting(SETTING_LANGUAGE, language)
        if theme:
            if persist:
                set_app_setting(SETTING_THEME, theme)
        if accent is not None:
            if persist:
                set_app_setting(SETTING_ACCENT, accent or '')

        theme_engine.apply_theme(theme or theme_engine.CURRENT_THEME,
                                 accent if accent is not None else (get_app_setting(SETTING_ACCENT, '') or None))
        for step in (self.setup_style, self._apply_widget_defaults, self._restyle_titlebar):
            try:
                step()
            except Exception:
                pass
        try:
            import localize_ui
            localize_ui.retranslate_tree(self)
        except Exception:
            pass
        self.rebuild_current_screen()
        self._render_settings_body()
        return True

    # ------------------------------------------------------------------
    # النافذة
    # ------------------------------------------------------------------
    def open_settings(self):
        win = getattr(self, '_settings_dialog', None)
        try:
            if win is not None and win.winfo_exists():
                win.lift()
                win.focus_force()
                return
        except tk.TclError:
            pass
        win = tk.Toplevel(self)
        win.withdraw()
        win.title(tr('الإعدادات'))
        win.configure(bg=BG_VOID)
        win.resizable(False, False)
        win.transient(self)
        win.protocol('WM_DELETE_WINDOW', self.close_settings)
        self._settings_dialog = win
        self._settings_body = None
        self._render_settings_body()
        try:
            self._center_settings_window(win)
            win.deiconify()
            win.lift()
            win.focus_force()
        except Exception:
            win.deiconify()

    def _center_settings_window(self, win):
        win.update_idletasks()
        width = max(520, win.winfo_reqwidth())
        height = max(420, win.winfo_reqheight())
        x = self.winfo_x() + max(0, (self.winfo_width() - width) // 2)
        y = self.winfo_y() + max(0, (self.winfo_height() - height) // 2)
        win.geometry(f'{width}x{height}+{x}+{y}')

    def close_settings(self):
        win = getattr(self, '_settings_dialog', None)
        try:
            if win is not None and win.winfo_exists():
                win.destroy()
        except tk.TclError:
            pass
        self._settings_dialog = None
        self._settings_body = None

    # ------------------------------------------------------------------
    # بناء المحتوى (يُعاد بناؤه بعد كل تغيير حتى تتبدل الألوان فورًا)
    # ------------------------------------------------------------------
    def _t(self, text):
        value = tr(text)
        return RLM + value if is_rtl() else value

    def _render_settings_body(self):
        win = getattr(self, '_settings_dialog', None)
        try:
            if win is None or not win.winfo_exists():
                return
        except tk.TclError:
            return
        win.configure(bg=BG_VOID)
        win.title(tr('الإعدادات'))
        old = getattr(self, '_settings_body', None)
        if old is not None:
            try:
                old.destroy()
            except tk.TclError:
                pass

        side = 'right'
        anchor = 'e'

        body = tk.Frame(win, bg=BG_VOID)
        body.pack(fill='both', expand=True, padx=14, pady=14)
        self._settings_body = body

        head = tk.Frame(body, bg=BG_HEADER, height=44, highlightbackground=ACCENT_MATRIX, highlightthickness=1)
        head.pack(fill='x')
        head.pack_propagate(False)
        tk.Label(head, text=self._t('الإعدادات'), bg=BG_HEADER, fg=ACCENT_MATRIX,
                 font=(TERM_FONT, 12, 'bold'), anchor=anchor).pack(side=side, padx=14, pady=10)
        tk.Button(head, text=tr('[✖]'), command=self.close_settings,
                  bg=BG_HEADER, fg=ACCENT_DANGER, activebackground=ACCENT_DANGER,
                  activeforeground=BG_VOID, relief='solid', borderwidth=1,
                  font=(MONO_FONT, 9, 'bold'), padx=6, pady=0, cursor='hand2').pack(side='left' if side == 'right' else 'right', padx=8)

        self._build_language_section(body, side, anchor)
        self._build_theme_section(body, side, anchor)
        self._build_accent_section(body, side, anchor)

        foot = tk.Frame(body, bg=BG_VOID)
        foot.pack(fill='x', pady=(10, 0))
        tk.Label(foot, text=self._t('يتم الحفظ والتطبيق فورًا.'), bg=BG_VOID, fg=FG_MUTED,
                 font=(TERM_FONT, 9), anchor=anchor).pack(side=side, padx=4)
        tk.Button(foot, text=self._t('إغلاق'), command=self.close_settings,
                  bg=ACCENT_MATRIX, fg=BG_VOID, activebackground=BG_SELECTED,
                  activeforeground=FG_PRIMARY, relief='solid', borderwidth=1,
                  font=(TERM_FONT, 10, 'bold'), padx=18, pady=6, cursor='hand2').pack(side='left' if side == 'right' else 'right', padx=4)

        try:
            self._center_settings_window(win)
        except Exception:
            pass

    def _section(self, parent, title, side, anchor):
        card = tk.Frame(parent, bg=BG_PANEL, highlightbackground=BORDER_DIM, highlightthickness=1)
        card.pack(fill='x', pady=(10, 0))
        tk.Label(card, text=self._t(title), bg=BG_PANEL, fg=FG_PRIMARY,
                 font=(TERM_FONT, 10, 'bold'), anchor=anchor).pack(fill='x', padx=12, pady=(8, 4))
        inner = tk.Frame(card, bg=BG_PANEL)
        inner.pack(fill='x', padx=12, pady=(0, 10))
        return inner

    def _build_language_section(self, parent, side, anchor):
        inner = self._section(parent, 'اللغة', side, anchor)
        current = get_language()
        for code, label in (('ar', 'العربية'), ('en', 'English')):
            active = current == code
            tk.Button(
                inner, text=(RLM + label if code == 'ar' else label),
                command=lambda c=code: self.apply_ui_settings(language=c),
                bg=BG_SELECTED if active else BG_HEADER,
                fg=ACCENT_MATRIX if active else FG_PRIMARY,
                activebackground=BG_HOVER, activeforeground=ACCENT_MATRIX,
                relief='solid', borderwidth=1, font=(TERM_FONT, 10, 'bold'),
                padx=22, pady=7, cursor='hand2',
            ).pack(side=side, padx=(0, 8) if side == 'left' else (8, 0))

    def _build_theme_section(self, parent, side, anchor):
        inner = self._section(parent, 'الثيم', side, anchor)
        current = theme_engine.CURRENT_THEME
        accent = current_accent()
        for name in THEME_ORDER:
            active = current == name
            palette = theme_engine.build_palette(name, accent if name != 'matrix' else None)
            card = tk.Frame(inner, bg=BG_ALT_ROW,
                            highlightbackground=ACCENT_MATRIX if active else BORDER_DIM,
                            highlightthickness=2 if active else 1, cursor='hand2')
            card.pack(side=side, padx=6, pady=2)

            preview = tk.Frame(card, bg=palette['BG_VOID'], width=96, height=44)
            preview.pack(fill='x')
            preview.pack_propagate(False)
            tk.Frame(preview, bg=palette['BG_HEADER'], height=10).pack(fill='x')
            bar = tk.Frame(preview, bg=palette['BG_VOID'])
            bar.pack(fill='both', expand=True, padx=6, pady=(4, 0))
            tk.Frame(bar, bg=palette['ACCENT_MATRIX'], width=24, height=5).pack(anchor='w')
            tk.Frame(bar, bg=palette['FG_MUTED'], width=54, height=3).pack(anchor='w', pady=(4, 0))

            label = theme_engine.THEME_LABELS.get(name, {}).get(get_language(), name)
            theme_label = tk.Label(card, text=label, bg=BG_ALT_ROW,
                                   fg=ACCENT_MATRIX if active else FG_PRIMARY,
                                   font=(TERM_FONT, 9, 'bold'), cursor='hand2')
            theme_label.pack(padx=8, pady=5)

            for widget in (card, preview, bar, theme_label):
                widget.bind('<Button-1>', lambda e, n=name: self.apply_ui_settings(theme=n))
            for child in (preview,) + tuple(preview.winfo_children()):
                child.bind('<Button-1>', lambda e, n=name: self.apply_ui_settings(theme=n))

    def _build_accent_section(self, parent, side, anchor):
        inner = self._section(parent, 'اللون المميز', side, anchor)
        theme_name = theme_engine.CURRENT_THEME
        current = current_accent()
        if theme_name == 'matrix':
            tk.Label(inner, text=self._t('ثيم Matrix يستخدم اللون الأخضر المميز افتراضيًا.'),
                     bg=BG_PANEL, fg=FG_MUTED, font=(TERM_FONT, 9), anchor=anchor).pack(fill='x')
            return
        row = tk.Frame(inner, bg=BG_PANEL)
        row.pack(fill='x', pady=(0, 6))
        for color in theme_engine.ACCENT_PRESETS:
            selected = color.upper() == current.upper()
            swatch = tk.Frame(row, bg=color, width=26, height=26, cursor='hand2',
                              highlightbackground=ACCENT_MATRIX if selected else BORDER_DIM,
                              highlightthickness=2 if selected else 1)
            swatch.pack(side=side, padx=3)
            swatch.bind('<Button-1>', lambda e, c=color: self.apply_ui_settings(accent=c))
        tk.Button(row, text=self._t('لون مخصص...'), command=self._pick_custom_accent,
                  bg=BG_HEADER, fg=FG_PRIMARY, activebackground=BG_HOVER,
                  activeforeground=ACCENT_MATRIX, relief='solid', borderwidth=1,
                  font=(TERM_FONT, 9, 'bold'), padx=10, pady=4, cursor='hand2').pack(side='left' if side == 'right' else 'right', padx=6)

    def _pick_custom_accent(self):
        win = getattr(self, '_settings_dialog', None)
        try:
            _, color = colorchooser.askcolor(color=current_accent(), parent=win, title=tr('اختر اللون المميز'))
        except Exception:
            _, color = colorchooser.askcolor(color=current_accent())
        if color:
            self.apply_ui_settings(accent=color)

    # ------------------------------------------------------------------
    # زر الإعدادات في شريط العنوان
    # ------------------------------------------------------------------
    def _settings_button(self, parent):
        btn = tk.Button(parent, text='[⚙]', command=self.open_settings,
                        bg=BG_HEADER, fg=ACCENT_MATRIX, activebackground=ACCENT_MATRIX,
                        activeforeground=BG_VOID, relief='solid', borderwidth=1,
                        font=(MONO_FONT, 10, 'bold'), padx=8, pady=1, cursor='hand2')
        btn.pack(side='left', padx=(8, 2), pady=4)
        self._settings_btn = btn
        return btn
