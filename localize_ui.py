# Rasd - ترجمة واجهة Tk تلقائيًا (بدون تعديل يدوي لكل عنصر)
#
# الفكرة: نلفّ دوال إنشاء وتحديث عناصر Tk/ttk بحيث تمرّ نصوص الواجهة العربية
# على tr() قبل عرضها. عند اختيار العربية ترجع tr() النص كما هو، لذا لا يتغير
# سلوك النسخة الحالية إطلاقًا. عند اختيار الإنجليزية تتحول كل النصوص المعروفة
# في القاموس، وتبقى أسماء المشاريع والملفات والمسارات كما هي.
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

from i18n import tr, is_rtl

INSTALLED = False
_ARABIC_RANGE = ('\u0600', '\u06ff')
_VARIABLES = {}

# اتجاه الواجهة: الكود مكتوب بتخطيط RTL، وعند اختيار الإنجليزية نعكس اتجاه العناصر
_SIDE_MIRROR = {'left': 'right', 'right': 'left'}
_ANCHOR_MIRROR = {'e': 'w', 'w': 'e', 'ne': 'nw', 'nw': 'ne', 'se': 'sw', 'sw': 'se',
                  'east': 'west', 'west': 'east'}
_JUSTIFY_MIRROR = {'right': 'left', 'left': 'right'}


def _natural_layout(widget):
    """هل هذا العنصر أو أحد آبائه يطلب تخطيطًا طبيعيًا غير معكوس؟

    يُستخدم في شاشات مبنية أصلًا بتخطيط LTR (الترحيب وشريط العنوان) حتى
    تبقى بنفس الشكل في العربية والإنجليزية بدل انقلابها الكامل.
    """
    node = widget
    depth = 0
    while node is not None and depth < 60:
        if getattr(node, '_rasd_natural_layout', False):
            return True
        try:
            node = node.master
        except Exception:
            node = None
        depth += 1
    return False


def _mirror_options(kw, widget=None):
    if is_rtl():
        return kw
    # التخطيط الطبيعي: لا نعكس أي خيار (side/anchor/justify/sticky) للعنصر
    # أو لأي عنصر داخل حاوية طلبت ذلك.
    if widget is not None and _natural_layout(widget):
        return kw
    # يمكن لعنصر أو حاوية أن تطلب عدم عكس جهة الترتيب (side) مع بقاء عكس
    # المحاذاة (anchor/justify). يُستخدم في أشرطة التنقل حتى لا ينعكس ترتيب
    # أزرار الرجوع/التقدم عند التحويل للإنجليزية.
    natural_side = False
    if widget is not None:
        if getattr(widget, '_rasd_no_side_mirror', False):
            natural_side = True
        else:
            parent = getattr(widget, 'master', None)
            if parent is not None and getattr(parent, '_rasd_natural_order', False):
                natural_side = True
    if not natural_side and 'side' in kw and isinstance(kw['side'], str):
        kw['side'] = _SIDE_MIRROR.get(kw['side'], kw['side'])
    if 'anchor' in kw and isinstance(kw['anchor'], str):
        kw['anchor'] = _ANCHOR_MIRROR.get(kw['anchor'], kw['anchor'])
    if 'justify' in kw and isinstance(kw['justify'], str):
        kw['justify'] = _JUSTIFY_MIRROR.get(kw['justify'], kw['justify'])
    if 'sticky' in kw and isinstance(kw['sticky'], str):
        kw['sticky'] = ''.join(_ANCHOR_MIRROR.get(ch, ch) if ch in 'ew' else ch for ch in kw['sticky'])
    if 'labelanchor' in kw and isinstance(kw['labelanchor'], str):
        kw['labelanchor'] = _ANCHOR_MIRROR.get(kw['labelanchor'], kw['labelanchor'])
    return kw


def _has_arabic(value):
    return isinstance(value, str) and any(_ARABIC_RANGE[0] <= ch <= _ARABIC_RANGE[1] for ch in value)


def _remember(widget, value):
    if getattr(widget, '_rasd_i18n_busy', False):
        return
    try:
        widget._rasd_i18n_text = value
    except Exception:
        pass


def _translate_value(value):
    return tr(value) if isinstance(value, str) else value


# ---------------------------------------------------------------------------
# عناصر Tk الكلاسيكية: text / cnf
# ---------------------------------------------------------------------------
def _patch_text_widget(cls):
    original_init = cls.__init__
    original_configure = cls.configure

    def __init__(self, master=None, cnf=None, **kw):
        kw = _mirror_options(kw, master)
        if 'text' in kw:
            _remember(self, kw['text'])
            kw['text'] = _translate_value(kw['text'])
        elif isinstance(cnf, dict) and 'text' in cnf:
            cnf = dict(cnf)
            _remember(self, cnf['text'])
            cnf['text'] = _translate_value(cnf['text'])
        original_init(self, master, cnf, **kw)

    def configure(self, cnf=None, **kw):
        kw = _mirror_options(kw)
        if 'text' in kw:
            _remember(self, kw['text'])
            kw['text'] = _translate_value(kw['text'])
        elif isinstance(cnf, dict) and 'text' in cnf:
            cnf = dict(cnf)
            _remember(self, cnf['text'])
            cnf['text'] = _translate_value(cnf['text'])
        return original_configure(self, cnf, **kw)

    cls.__init__ = __init__
    cls.configure = configure
    cls.config = configure


def _patch_init_configure(cls):
    """نسخة مبسطة تصلح لعناصر ttk التي لا تقبل cnf كوسيط ثانٍ."""
    original_init = cls.__init__
    original_configure = cls.configure

    def __init__(self, master=None, **kw):
        kw = _mirror_options(kw, master)
        if 'text' in kw:
            _remember(self, kw['text'])
            kw['text'] = _translate_value(kw['text'])
        original_init(self, master, **kw)

    def configure(self, cnf=None, **kw):
        kw = _mirror_options(kw)
        if 'text' in kw:
            _remember(self, kw['text'])
            kw['text'] = _translate_value(kw['text'])
        return original_configure(self, cnf, **kw)

    cls.__init__ = __init__
    cls.configure = configure
    cls.config = configure


# ---------------------------------------------------------------------------
# القوائم المنبثقة (كليك يمين)
# ---------------------------------------------------------------------------
def _patch_menu():
    cls = tk.Menu

    def _wrap_add(name):
        original = getattr(cls, name)

        def wrapper(self, *args, **kwargs):
            cnf = kwargs
            label = kwargs.get('label')
            if label is None and args and isinstance(args[0], dict):
                label = args[0].get('label')
            if isinstance(label, str):
                translated = _translate_value(label)
                if 'label' in kwargs:
                    kwargs['label'] = translated
                if args and isinstance(args[0], dict):
                    first = dict(args[0]); first['label'] = translated
                    args = (first,) + args[1:]
            result = original(self, *args, **kwargs)
            try:
                index = self.index('end')
                if index is not None and label is not None:
                    self._rasd_i18n_items = getattr(self, '_rasd_i18n_items', [])
                    self._rasd_i18n_items.append((int(index), label))
            except Exception:
                pass
            return result

        setattr(cls, name, wrapper)

    for name in ('add_command', 'add_cascade', 'add_checkbutton', 'add_radiobutton',
                 'insert_command', 'insert_cascade'):
        if hasattr(cls, name):
            _wrap_add(name)

    original_entryconfigure = cls.entryconfigure

    def entryconfigure(self, index, cnf=None, **kw):
        if 'label' in kw:
            kw['label'] = _translate_value(kw['label'])
        elif isinstance(cnf, dict) and 'label' in cnf:
            cnf = dict(cnf); cnf['label'] = _translate_value(cnf['label'])
        return original_entryconfigure(self, index, cnf, **kw)

    cls.entryconfigure = entryconfigure
    cls.entryconfig = entryconfigure


# ---------------------------------------------------------------------------
# Treeview: العناوين وصفوف القيم
# ---------------------------------------------------------------------------
def _translate_values(values):
    if isinstance(values, (list, tuple)):
        return type(values)(_translate_value(v) for v in values)
    return values


def _patch_treeview():
    cls = ttk.Treeview

    original_heading = cls.heading

    def heading(self, column, option=None, **kw):
        kw = _mirror_options(kw)
        if 'text' in kw:
            originals = getattr(self, '_rasd_i18n_headings', None)
            if originals is None:
                originals = {}
                self._rasd_i18n_headings = originals
            originals[str(column)] = kw['text']
            kw['text'] = _translate_value(kw['text'])
        if option is not None:
            return original_heading(self, column, option, **kw)
        return original_heading(self, column, **kw)

    original_insert = cls.insert
    original_item = cls.item
    original_column = cls.column

    def column(self, column, option=None, **kw):
        kw = _mirror_options(kw)
        if option is not None:
            return original_column(self, column, option, **kw)
        return original_column(self, column, **kw)

    def insert(self, parent, index, iid=None, **kw):
        if 'values' in kw:
            kw['values'] = _translate_values(kw['values'])
        if 'text' in kw:
            kw['text'] = _translate_value(kw['text'])
        return original_insert(self, parent, index, iid, **kw)

    def item(self, item, option=None, **kw):
        if 'values' in kw:
            kw['values'] = _translate_values(kw['values'])
        if 'text' in kw:
            kw['text'] = _translate_value(kw['text'])
        if option is not None:
            return original_item(self, item, option, **kw)
        return original_item(self, item, **kw)

    cls.heading = heading
    cls.insert = insert
    cls.item = item
    cls.column = column


# ---------------------------------------------------------------------------
# Notebook: أسماء التبويبات
# ---------------------------------------------------------------------------
def _patch_notebook():
    cls = ttk.Notebook

    original_add = cls.add
    original_tab = cls.tab

    def add(self, child, **kw):
        if 'text' in kw:
            tabs = getattr(self, '_rasd_i18n_tabs', None)
            if tabs is None:
                tabs = {}
                self._rasd_i18n_tabs = tabs
            tabs[str(child)] = kw['text']
            kw['text'] = _translate_value(kw['text'])
        return original_add(self, child, **kw)

    def _original_text(self, tab_id, value):
        original = getattr(self, '_rasd_i18n_tabs', {}).get(str(tab_id))
        return original if original is not None else value

    def tab(self, tab_id, option=None, **kw):
        if 'text' in kw:
            kw['text'] = _translate_value(kw['text'])
        if option is not None:
            result = original_tab(self, tab_id, option, **kw)
            if option == 'text':
                return _original_text(self, tab_id, result)
            return result
        result = original_tab(self, tab_id, **kw)
        if isinstance(result, dict) and 'text' in result:
            result = dict(result)
            result['text'] = _original_text(self, tab_id, result['text'])
        return result

    cls.add = add
    cls.tab = tab


# ---------------------------------------------------------------------------
# Canvas / Listbox
# ---------------------------------------------------------------------------
def _patch_canvas():
    cls = tk.Canvas
    original_create_text = cls.create_text
    original_itemconfigure = cls.itemconfigure

    def create_text(self, *args, **kw):
        # لا نعكس anchor هنا: النصوص داخل Canvas مرسومة يدويًا بمواضع ثابتة،
        # وعكسها يخرج بها خارج حدود اللوحة. نكتفي بالترجمة.
        if 'text' in kw:
            kw['text'] = _translate_value(kw['text'])
        return original_create_text(self, *args, **kw)

    def itemconfigure(self, tagOrId, cnf=None, **kw):
        if 'text' in kw:
            kw['text'] = _translate_value(kw['text'])
        if isinstance(cnf, dict) and 'text' in cnf:
            cnf = dict(cnf); cnf['text'] = _translate_value(cnf['text'])
        return original_itemconfigure(self, tagOrId, cnf, **kw)

    cls.create_text = create_text
    cls.itemconfigure = itemconfigure
    cls.itemconfig = itemconfigure


def _patch_listbox():
    cls = tk.Listbox
    original_insert = cls.insert
    original_configure = cls.configure

    def insert(self, index, *elements):
        return original_insert(self, index, *[_translate_value(e) for e in elements])

    def configure(self, cnf=None, **kw):
        if 'label' in kw:
            kw['label'] = _translate_value(kw['label'])
        return original_configure(self, cnf, **kw)

    cls.insert = insert
    cls.configure = configure
    cls.config = configure


# ---------------------------------------------------------------------------
# StringVar / عنوان النافذة / نوافذ اختيار الملفات
# ---------------------------------------------------------------------------
def _reverse_variable_value(variable, value):
    """يرجع النص العربي الأصلي بدل ترجمته عند قراءة قيمة متغير واجهة."""
    if not isinstance(value, str):
        return value
    original = getattr(variable, '_rasd_i18n_var_original', None)
    if isinstance(original, str):
        try:
            if value == _translate_value(original):
                return original
        except Exception:
            pass
    return value


def _make_get_wrapper(original_get):
    def get(self):
        return _reverse_variable_value(self, original_get(self))
    return get


def _patch_variables():
    original_set = tk.Variable.set
    original_get = tk.Variable.get
    original_initialize = tk.Variable.initialize
    registry = _VARIABLES

    def _register(variable):
        try:
            registry[str(variable)] = variable
        except Exception:
            pass

    def initialize(self, value):
        _register(self)
        if isinstance(value, str):
            _remember(self, value)
            try:
                self._rasd_i18n_var_original = value
            except Exception:
                pass
            value = _translate_value(value)
        return original_initialize(self, value)

    def set(self, value):
        _register(self)
        if isinstance(value, str):
            _remember(self, value)
            translated = _translate_value(value)
            try:
                self._rasd_i18n_var_original = value
            except Exception:
                pass
            value = translated
        return original_set(self, value)

    def get(self):
        return _reverse_variable_value(self, original_get(self))

    tk.Variable.initialize = initialize
    tk.Variable.set = set
    tk.Variable.get = get
    # في Python 3.11 تعرّف StringVar.get بنفسها (تقرأ من Tcl مباشرة)،
    # لذلك لا يكفي ترقيع Variable.get ويجب ترقيع الصنف الفرعي أيضًا.
    for cls in (tk.StringVar, tk.IntVar, tk.DoubleVar, tk.BooleanVar):
        cls_get = cls.__dict__.get('get')
        if cls_get is not None:
            cls.get = _make_get_wrapper(cls_get)


def _reverse_from_variable(widget, value):
    """يعيد النص العربي الأصلي لعنصر إدخال مرتبط بـ StringVar مترجمة."""
    if not isinstance(value, str):
        return value
    try:
        name = widget.cget('textvariable')
    except Exception:
        return value
    if not name:
        return value
    variable = _VARIABLES.get(str(name))
    original = getattr(variable, '_rasd_i18n_var_original', None)
    if isinstance(original, str) and value == _translate_value(original):
        return original
    return value


def _patch_wm_title():
    original_title = tk.Wm.title

    def title(self, string=None):
        if string is not None:
            string = _translate_value(string)
        return original_title(self, string)

    tk.Wm.title = title


def _patch_entry():
    for cls in (tk.Entry, ttk.Entry):
        original_insert = cls.insert
        original_get = cls.get

        def insert(self, index, string, _orig=original_insert):
            translated = _translate_value(string)
            if isinstance(string, str) and translated != string:
                mapping = getattr(self, '_rasd_i18n_entry', None)
                if mapping is None:
                    mapping = {}
                    self._rasd_i18n_entry = mapping
                mapping[translated] = string
            return _orig(self, index, translated)

        def get(self, _orig=original_get):
            value = _orig(self)
            value = getattr(self, '_rasd_i18n_entry', {}).get(value, value)
            return _reverse_from_variable(self, value)

        cls.insert = insert
        cls.get = get


def _patch_combobox():
    cls = ttk.Combobox
    original_init = cls.__init__
    original_configure = cls.configure
    original_get = cls.get
    original_set = cls.set

    def _translate_values_for(widget, values):
        if not isinstance(values, (list, tuple)):
            return values
        mapping = getattr(widget, '_rasd_i18n_combo', None)
        if mapping is None:
            mapping = {}
            widget._rasd_i18n_combo = mapping
        result = []
        for value in values:
            translated = _translate_value(value)
            if isinstance(value, str) and translated != value:
                mapping[translated] = value
            result.append(translated)
        return result

    def __init__(self, master=None, **kw):
        if 'values' in kw:
            kw['values'] = _translate_values_for(self, kw['values'])
        original_init(self, master, **kw)

    def configure(self, cnf=None, **kw):
        if 'values' in kw:
            kw['values'] = _translate_values_for(self, kw['values'])
        return original_configure(self, cnf, **kw)

    def get(self):
        value = original_get(self)
        value = getattr(self, '_rasd_i18n_combo', {}).get(value, value)
        return _reverse_from_variable(self, value)

    def set(self, value):
        return original_set(self, _translate_value(value))

    cls.__init__ = __init__
    cls.configure = configure
    cls.config = configure
    cls.get = get
    cls.set = set


# ---------------------------------------------------------------------------
# اتجاه التخطيط: عكس pack/grid/place عند الإنجليزية
# ---------------------------------------------------------------------------
def _patch_geometry():
    def wrap_method(cls, name):
        original = getattr(cls, name, None)
        if original is None:
            return

        def wrapper(self, cnf=None, **kw):
            if cnf is None:
                cnf = {}
            kw = _mirror_options(kw, self)
            if isinstance(cnf, dict):
                cnf = _mirror_options(dict(cnf), self)
            return original(self, cnf, **kw)

        setattr(cls, name, wrapper)

    wrap_method(tk.Pack, 'pack')
    wrap_method(tk.Grid, 'grid')
    wrap_method(tk.Grid, 'grid_configure')
    wrap_method(tk.Place, 'place')


def _patch_dialogs():
    """يترجم عناوين ونصوص رسائل messagebox و simpledialog (وسائط positional)."""
    def wrap(func, positions):
        def wrapper(*args, **kw):
            args = list(args)
            for index in positions:
                if index < len(args) and isinstance(args[index], str):
                    args[index] = _translate_value(args[index])
            for key in ('title', 'message', 'detail', 'prompt', 'initialvalue'):
                if isinstance(kw.get(key), str):
                    kw[key] = _translate_value(kw[key])
            return func(*args, **kw)
        return wrapper

    for name in ('showinfo', 'showwarning', 'showerror', 'askyesno',
                 'askokcancel', 'askretrycancel', 'askyesnocancel'):
        original = getattr(messagebox, name, None)
        if original is not None:
            setattr(messagebox, name, wrap(original, (0, 1)))
    for name in ('askstring', 'askinteger', 'askfloat'):
        original = getattr(simpledialog, name, None)
        if original is not None:
            setattr(simpledialog, name, wrap(original, (0, 1)))


def _patch_filedialogs():
    for name in ('askopenfilename', 'askopenfilenames', 'asksaveasfilename', 'askdirectory'):
        original = getattr(filedialog, name, None)
        if original is None:
            continue

        def make(original):
            def wrapper(**options):
                if 'title' in options:
                    options['title'] = _translate_value(options['title'])
                return original(**options)
            return wrapper

        setattr(filedialog, name, make(original))


# ---------------------------------------------------------------------------
# التركيب وإعادة الترجمة
# ---------------------------------------------------------------------------
def install():
    """يُستدعى مرة واحدة عند بدء التطبيق وقبل إنشاء أي عنصر واجهة."""
    global INSTALLED
    if INSTALLED:
        return
    INSTALLED = True
    for cls in (tk.Label, tk.Button, tk.Checkbutton, tk.Radiobutton,
                tk.Menubutton, tk.LabelFrame, tk.Message, tk.Scale):
        try:
            _patch_text_widget(cls)
        except Exception:
            pass
    for cls in (ttk.Label, ttk.Button, ttk.Checkbutton, ttk.Radiobutton,
                ttk.Menubutton, ttk.LabelFrame):
        try:
            _patch_init_configure(cls)
        except Exception:
            pass
    for patcher in (_patch_menu, _patch_treeview, _patch_notebook,
                    _patch_canvas, _patch_listbox, _patch_variables,
                    _patch_entry, _patch_combobox, _patch_geometry,
                    _patch_dialogs, _patch_wm_title, _patch_filedialogs):
        try:
            patcher()
        except Exception:
            pass


def _retranslate_widget(widget):
    original = getattr(widget, '_rasd_i18n_text', None)
    if isinstance(original, str) and not getattr(widget, '_rasd_i18n_busy', False):
        try:
            widget._rasd_i18n_busy = True
            widget.configure(text=tr(original))
        except Exception:
            pass
        finally:
            try:
                widget._rasd_i18n_busy = False
            except Exception:
                pass

    headings = getattr(widget, '_rasd_i18n_headings', None)
    if isinstance(headings, dict):
        for column, text in headings.items():
            try:
                widget.heading(column, text=tr(text))
            except Exception:
                pass

    items = getattr(widget, '_rasd_i18n_items', None)
    if isinstance(items, list):
        for index, text in items:
            try:
                widget.entryconfigure(index, label=tr(text))
            except Exception:
                pass

    tabs = getattr(widget, '_rasd_i18n_tabs', None)
    if isinstance(tabs, dict):
        for child, text in tabs.items():
            try:
                widget.tab(child, text=tr(text))
            except Exception:
                pass


def retranslate_tree(root):
    """يعيد ترجمة كل العناصر الموجودة (يُستخدم عند تغيير اللغة دون إعادة بناء)."""
    try:
        _retranslate_widget(root)
    except Exception:
        pass
    try:
        children = root.winfo_children()
    except Exception:
        return
    for child in children:
        retranslate_tree(child)
