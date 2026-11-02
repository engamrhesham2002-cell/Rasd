# ui_dialogs.py - نوافذ حوار داخلية بنفس ثيم التطبيق الداكن
import tkinter as tk
from theme import *


def _shell(parent, title):
    """ينشئ نافذة حوار داكنة مع شريط عنوان ومساحة محتوى، ويرجع (win, body)."""
    owner = parent.winfo_toplevel() if parent is not None and hasattr(parent, 'winfo_toplevel') else parent
    win = tk.Toplevel(owner or tk._default_root)
    win.title(title)
    win.configure(bg=BG_VOID)
    win.resizable(False, False)
    try: win.transient(owner)
    except tk.TclError: pass
    card = tk.Frame(win, bg=BG_PANEL, highlightbackground=BORDER_DIM, highlightthickness=1)
    card.pack(fill='both', expand=True, padx=14, pady=14)
    head = tk.Frame(card, bg=BG_HEADER, height=36)
    head.pack(fill='x')
    head.pack_propagate(False)
    tk.Label(head, text=RLM + title, bg=BG_HEADER, fg=ACCENT_MATRIX, font=(TERM_FONT, 10, 'bold'),
             anchor='e').pack(fill='x', padx=10, pady=8)
    body = tk.Frame(card, bg=BG_PANEL)
    body.pack(fill='both', expand=True, padx=14, pady=10)
    return win, body


def _center(win, parent):
    win.update_idletasks()
    w, h = win.winfo_width(), win.winfo_height()
    owner = parent.winfo_toplevel() if parent is not None and hasattr(parent, 'winfo_toplevel') else parent
    if owner is not None and getattr(owner, 'winfo_exists', lambda: 0)():
        x = owner.winfo_rootx() + max(0, (owner.winfo_width() - w) // 2)
        y = owner.winfo_rooty() + max(0, (owner.winfo_height() - h) // 2)
    else:
        x, y = (win.winfo_screenwidth() - w) // 2, (win.winfo_screenheight() - h) // 3
    win.geometry(f'+{max(0, x)}+{max(0, y)}')


def _button(parent, text, command, danger=False):
    tk.Button(parent, text=RLM + text, command=command, bg=BG_HEADER,
              fg=ACCENT_DANGER if danger else ACCENT_MATRIX,
              activebackground=ACCENT_MATRIX, activeforeground=BG_VOID,
              relief='solid', borderwidth=1, font=(TERM_FONT, 9, 'bold'),
              padx=14, pady=4, cursor='hand2').pack(side='right', padx=4)


def _run(win, parent):
    previous = None
    try: previous = parent.grab_current() if parent is not None and hasattr(parent, 'grab_current') else None
    except tk.TclError: pass
    _center(win, parent)
    try: win.grab_set()
    except tk.TclError: pass
    win.focus_force()
    win.wait_window()
    try:
        if previous is not None and previous.winfo_exists(): previous.grab_set()
    except tk.TclError: pass


def _message(parent, title, message, color):
    win, body = _shell(parent, title)
    tk.Label(body, text='●', bg=BG_PANEL, fg=color, font=(TERM_FONT, 14, 'bold')).pack(side='right', padx=(8, 0))
    tk.Label(body, text=RLM + str(message), bg=BG_PANEL, fg=FG_PRIMARY, font=(TERM_FONT, 10),
             justify='right', anchor='e', wraplength=420).pack(side='right', fill='x', expand=True, padx=6)
    win.bind('<Return>', lambda e: win.destroy())
    win.bind('<Escape>', lambda e: win.destroy())
    _button(body, '[ موافق ]', win.destroy)
    _run(win, parent)


def showinfo(parent, title, message=''):
    _message(parent, title, message, ACCENT_MATRIX)


def showwarning(parent, title, message=''):
    _message(parent, title, message, ACCENT_AMBER)


def showerror(parent, title, message=''):
    _message(parent, title, message, ACCENT_DANGER)


def askyesno(parent, title, message=''):
    result = {'ok': False}
    win, body = _shell(parent, title)
    tk.Label(body, text='؟', bg=BG_PANEL, fg=ACCENT_AMBER, font=(TERM_FONT, 14, 'bold')).pack(side='right', padx=(8, 0))
    tk.Label(body, text=RLM + str(message), bg=BG_PANEL, fg=FG_PRIMARY, font=(TERM_FONT, 10),
             justify='right', anchor='e', wraplength=420).pack(side='right', fill='x', expand=True, padx=6)
    def yes():
        result['ok'] = True
        win.destroy()
    win.bind('<Return>', lambda e: yes())
    win.bind('<Escape>', lambda e: win.destroy())
    _button(body, '[ نعم ]', yes)
    _button(body, '[ إلغاء ]', win.destroy)
    _run(win, parent)
    return result['ok']


def ask_string(parent, title, prompt, initialvalue='', show=None):
    result = {'value': None}
    win, body = _shell(parent, title)
    tk.Label(body, text=RLM + prompt, bg=BG_PANEL, fg=FG_MUTED, font=(TERM_FONT, 9),
             justify='right', anchor='e', wraplength=420).pack(fill='x', pady=(0, 6))
    var = tk.StringVar(value=initialvalue or '')
    entry = tk.Entry(body, textvariable=var, bg=BG_VOID, fg=FG_PRIMARY,
                     insertbackground=ACCENT_MATRIX, relief='solid', borderwidth=1,
                     highlightthickness=1, highlightbackground=BORDER_DIM,
                     highlightcolor=ACCENT_MATRIX, font=(TERM_FONT, 11), justify='right')
    if show: entry.configure(show=show)
    entry.pack(fill='x', ipady=6, pady=(0, 10))
    def ok():
        result['value'] = var.get().strip()
        win.destroy()
    win.bind('<Return>', lambda e: ok())
    win.bind('<Escape>', lambda e: win.destroy())
    _button(body, '[ حفظ ]', ok)
    _button(body, '[ إلغاء ]', win.destroy)
    entry.focus_set()
    entry.select_range(0, 'end')
    _run(win, parent)
    return result['value']
