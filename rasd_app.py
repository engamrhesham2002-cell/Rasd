# Rasd - النافذة الرئيسية وشريط العنوان المخصص بستايل التيرمينال (Custom Retro-Terminal Titlebar)
from common import *
from update_utils import *
from storage import *

from security import SecurityMixin
from welcome import WelcomeMixin
from home import HomeMixin
from explorer import ExplorerMixin
from updates import UpdatesMixin
from scanning import ScanningMixin
from tags import TagsMixin
from file_ops import FileOpsMixin
from search import SearchMixin
from preview import PreviewMixin
from excel_preview import ExcelPreviewMixin
from preview_render import PreviewRenderMixin
from tasks_utils import TasksUtilsMixin
from tasks_list import TasksListMixin
from tasks_calendar import TasksCalendarMixin
from workspace import WorkspaceMixin
from sync_ops import SyncOpsMixin
import ui_dialogs

class App(SecurityMixin,
    WelcomeMixin,
    HomeMixin,
    ExplorerMixin,
    UpdatesMixin,
    ScanningMixin,
    TagsMixin,
    FileOpsMixin,
    SearchMixin,
    PreviewMixin,
    ExcelPreviewMixin,
    PreviewRenderMixin,
    TasksUtilsMixin,
    TasksListMixin,
    TasksCalendarMixin,
    WorkspaceMixin,
    SyncOpsMixin,
    tk.Tk):
 def __init__(self):
  super().__init__()
  self._apply_widget_defaults()
  self._install_themed_dialogs()
  self._is_maximized = False
  self._normal_geometry = '1280x800+80+40'
  self._titlebar = None
  self._titlebar_label = None
  self.configure(bg=BG_VOID)
  self._build_custom_titlebar()
  self.title('Rasd | مدير ملفات المشاريع')
  self.geometry('720x600')
  self.minsize(720,600)
  self.project='';self.root=None;self.scanq=queue.Queue();self.previewq=queue.Queue();self.searchq=queue.Queue();self.updateq=queue.Queue();self.preview_token=0;self.preview_executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='office-preview');self.cad_preview_executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='office-cad-preview');self.search_executor=ThreadPoolExecutor(max_workers=2,thread_name_prefix='office-search');self.update_executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='rasd-update');self._update_check_running=False;self._update_install_on_close=False;self._update_download_dialog=None;self.cad_preview_process=None;self.preview_future=None;self.search_future=None;self.search_serial=0;self.search_engine_lock=threading.Lock();self.preview_cache=OrderedDict();self.backstack=[];self.forwardstack=[];self.search_job=None;self.everything_hwnd=None;self.everything_windows={};self.everything_proc=None;self.everything_key=None;self.everything_instance=None;self.everything_data=None;self.everything_exe=None;self.everything_cli=None;self.everything_root=None;self.everything_attempts=0;self.watch_root=None;self.watch_stop=threading.Event();self.scan_lock=threading.Lock();self.sort_col='name';self.sort_desc=False;self.opened_sort_col='opened';self.opened_sort_desc=True;self.discipline='الكل';self.index_total=0;self.index_errors=0;self.preview_page=0;self.preview_zoom=1.0;self.view_mode='files';self._home_refresh_job=None
  self.bind('<Configure>',self.schedule_home_refresh,add='+')
  self.bind_all('<MouseWheel>',self._task_route_mousewheel,add='+')
  self.bind('<FocusIn>',self._task_external_focus_sync,add='+')
  self._set_window_icon()
  self.protocol('WM_DELETE_WINDOW',lambda:self.close_app())
  self.setup_style()
  self.bind_all('<Map>', self._on_widget_map, add='+')
  self.after(10, self._apply_frameless_terminal_window)
  self.show_lock_screen() if self.password_enabled() else self.show_welcome()
  self._poll_after_id=self.after(150,self.poll_queue)
  if UPDATE_FAILURE.is_file():
   try:self.after(900,lambda:self._show_update_failure(UPDATE_FAILURE.read_text(encoding='utf-8',errors='replace')))
   except Exception:pass
  if not self.password_enabled():self.after(2200,self.check_for_updates)

 def _apply_widget_defaults(self):
  """ألوان افتراضية لعناصر Tk الكلاسيكية: إطار تركيز أخضر خفيف بدل الأزرق، وتحديد داكن."""
  for pattern, color in (
   ('*highlightColor', ACCENT_MATRIX),
   ('*highlightBackground', BORDER_DIM),
   ('*selectBackground', BG_SELECTED),
   ('*selectForeground', ACCENT_MATRIX),
   ('*insertBackground', ACCENT_MATRIX),
   ('*TCombobox*Listbox.background', BG_PANEL),
   ('*TCombobox*Listbox.foreground', FG_PRIMARY),
   ('*TCombobox*Listbox.selectBackground', BG_SELECTED),
   ('*TCombobox*Listbox.selectForeground', ACCENT_MATRIX),
  ):
   try: self.option_add(pattern, color)
   except tk.TclError: pass

 def _on_widget_map(self,event):
  widget=event.widget
  if isinstance(widget,tk.Toplevel):
   try:self.after_idle(lambda w=widget:self._darken_dialog_chrome(w))
   except tk.TclError:pass

 def _darken_dialog_chrome(self,win):
  """يجعل شريط عنوان نافذة الحوار داكنًا بدل الأزرق الافتراضي (Windows 10/11)."""
  if getattr(win,'_rasd_dark_chrome',False):return
  try:
   if not win.winfo_exists():return
  except tk.TclError:return
  win._rasd_dark_chrome=True
  try:
   hwnd=ctypes.windll.user32.GetParent(win.winfo_id())
   dwm=ctypes.windll.dwmapi
   def attr(number,value):
    v=ctypes.c_int(value)
    return dwm.DwmSetWindowAttribute(hwnd,number,ctypes.byref(v),ctypes.sizeof(v))
   if attr(20,1)!=0:attr(19,1)
   attr(35,0x00241B13)
   attr(36,0x00E8F1E2)
   attr(34,0x00382A1C)
  except Exception:pass

 def _install_themed_dialogs(self):
  """تحويل نوافذ الرسائل والإدخال من ستايل ويندوز الأبيض إلى نوافذ داخلية داكنة."""
  def info(title,message='',**kw):ui_dialogs.showinfo(kw.get('parent'),title,message)
  def warning(title,message='',**kw):ui_dialogs.showwarning(kw.get('parent'),title,message)
  def error(title,message='',**kw):ui_dialogs.showerror(kw.get('parent'),title,message)
  def yesno(title,message='',**kw):return ui_dialogs.askyesno(kw.get('parent'),title,message)
  def askstring(title,prompt,**kw):
   return ui_dialogs.ask_string(kw.get('parent'),title,prompt,kw.get('initialvalue',''),kw.get('show'))
  messagebox.showinfo=info
  messagebox.showwarning=warning
  messagebox.showerror=error
  messagebox.askyesno=yesno
  simpledialog.askstring=askstring

 def _build_custom_titlebar(self):
  bar = tk.Frame(self, bg=BG_VOID, height=36, highlightbackground=ACCENT_MATRIX, highlightthickness=1)
  bar.pack(fill='x', side='top', padx=2, pady=(2, 0))
  bar.pack_propagate(False)
  self._titlebar = bar

  title_lbl = tk.Label(
   bar,
   text=f'[ [RASD] ] SYSTEM://RASD_TERMINAL_{APP_VERSION} > RETRO_MODE',
   bg=BG_VOID,
   fg=ACCENT_MATRIX,
   font=(MONO_FONT, 10, 'bold'),
   anchor='w'
  )
  title_lbl.pack(side='left', padx=12, fill='x', expand=True)
  self._titlebar_label = title_lbl

  btn_close = tk.Button(
   bar, text='[✖]', command=self.close_app,
   bg='#260B12', fg=ACCENT_DANGER, activebackground=ACCENT_DANGER, activeforeground=BG_VOID,
   relief='solid', borderwidth=1, font=(MONO_FONT, 9, 'bold'), padx=6, pady=1, cursor='hand2'
  )
  btn_close.pack(side='right', padx=(3, 6), pady=4)

  btn_max = tk.Button(
   bar, text='[□]', command=self._toggle_window_maximize,
   bg='#091D15', fg=ACCENT_MATRIX, activebackground=ACCENT_MATRIX, activeforeground=BG_VOID,
   relief='solid', borderwidth=1, font=(MONO_FONT, 9, 'bold'), padx=6, pady=1, cursor='hand2'
  )
  btn_max.pack(side='right', padx=3, pady=4)
  self._titlebar_max_btn = btn_max

  btn_min = tk.Button(
   bar, text='[-]', command=self._minimize_window,
   bg='#091D15', fg=ACCENT_MATRIX, activebackground=ACCENT_MATRIX, activeforeground=BG_VOID,
   relief='solid', borderwidth=1, font=(MONO_FONT, 9, 'bold'), padx=6, pady=1, cursor='hand2'
  )
  btn_min.pack(side='right', padx=3, pady=4)

  for w in (bar, title_lbl):
   w.bind('<ButtonPress-1>', self._start_window_drag)
   w.bind('<B1-Motion>', self._on_window_drag)
   w.bind('<Double-Button-1>', lambda e: self._toggle_window_maximize())

 def _apply_frameless_terminal_window(self):
  if os.name != 'nt':
   return
  try:
   self.update_idletasks()
   self.overrideredirect(True)
   hwnd = ctypes.windll.user32.GetParent(self.winfo_id()) or self.winfo_id()
   GWL_EXSTYLE = -20
   WS_EX_APPWINDOW = 0x00040000
   WS_EX_TOOLWINDOW = 0x00000080
   ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
   ex_style = (ex_style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
   ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
   ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0004 | 0x0020)
  except Exception:
   try: self.overrideredirect(False)
   except Exception: pass

 def _start_window_drag(self, event):
  if self._is_maximized:
   return
  self._drag_offset_x = event.x_root - self.winfo_x()
  self._drag_offset_y = event.y_root - self.winfo_y()

 def _on_window_drag(self, event):
  if self._is_maximized:
   return
  x = event.x_root - getattr(self, '_drag_offset_x', 0)
  y = event.y_root - getattr(self, '_drag_offset_y', 0)
  self.geometry(f'+{x}+{y}')

 def _get_work_area(self):
  if os.name == 'nt':
   try:
    from ctypes import wintypes
    rect = wintypes.RECT()
    ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)
    return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top
   except Exception:
    pass
  return 0, 0, self.winfo_screenwidth(), max(500, self.winfo_screenheight() - 48)

 def _toggle_window_maximize(self):
  try:
   if not self._is_maximized:
    self._normal_geometry = self.geometry()
    wx, wy, ww, wh = self._get_work_area()
    self.geometry(f'{ww}x{wh}+{wx}+{wy}')
    self._is_maximized = True
    if getattr(self, '_titlebar_max_btn', None):
     self._titlebar_max_btn.configure(text='[❐]')
   else:
    self.geometry(self._normal_geometry)
    self._is_maximized = False
    if getattr(self, '_titlebar_max_btn', None):
     self._titlebar_max_btn.configure(text='[□]')
  except Exception:
   pass

 def _minimize_window(self):
  try:
   self.overrideredirect(False)
   self.iconify()
   def _restore_override(event=None):
    if self.state() == 'normal':
     self.unbind('<Map>')
     self.after(10, self._apply_frameless_terminal_window)
   self.bind('<Map>', _restore_override)
  except Exception:
   pass

 def title(self, string=None):
  if string is None:
   return super().title()
  super().title(string)
  if getattr(self, '_titlebar_label', None) and self._titlebar_label.winfo_exists():
   proj_part = getattr(self, 'project', '') or 'RETRO_MODE'
   self._titlebar_label.configure(text=f'[ [RASD] ] SYSTEM://RASD_TERMINAL_{APP_VERSION} > {proj_part}')

 def _set_window_icon(self):
  try:
   icon_path=Path(getattr(sys,'_MEIPASS',BASE))/'Assets'/'rasd_logo.png'
   with Image.open(icon_path) as source:
    self.app_icon=ImageTk.PhotoImage(source.convert('RGBA').resize((64,64),Image.Resampling.LANCZOS))
   self.iconphoto(True,self.app_icon)
  except Exception:pass

 def setup_style(self):
  s=ttk.Style(self);s.theme_use('clam')
  s.configure('Treeview',rowheight=30,font=(TERM_FONT,10),background=BG_PANEL,fieldbackground=BG_PANEL,foreground=FG_PRIMARY,borderwidth=0)
  s.configure('Treeview.Heading',font=(TERM_FONT,9,'bold'),background=BG_HEADER,foreground=ACCENT_MATRIX,padding=(7,8),relief='flat')
  s.map('Treeview',background=[('selected',BG_SELECTED)],foreground=[('selected',ACCENT_MATRIX)])
  s.configure('TNotebook',background=BG_VOID,borderwidth=0,tabmargins=(0,0,0,0))
  s.configure('TNotebook.Tab',font=(TERM_FONT,9,'bold'),padding=(12,6),background=BG_PANEL,foreground=FG_MUTED)
  s.map('TNotebook.Tab',background=[('selected',BG_HEADER)],foreground=[('selected',ACCENT_MATRIX)])
  s.configure('Toolbutton',font=(TERM_FONT,9,'bold'),padding=(10,6),background=BG_HEADER,foreground=FG_MUTED,borderwidth=0)
  s.map('Toolbutton',background=[('selected',ACCENT_MATRIX),('active',BG_HOVER)],foreground=[('selected',BG_VOID),('active',FG_PRIMARY)])
  s.configure('TButton',font=(TERM_FONT,9,'bold'),padding=(8,5),background=BG_HEADER,foreground=ACCENT_MATRIX,borderwidth=1,relief='solid',focuscolor=ACCENT_MATRIX,bordercolor=BORDER_DIM,lightcolor=BG_HEADER,darkcolor=BORDER_DIM)
  s.map('TButton',background=[('active',BG_SELECTED),('pressed',ACCENT_MATRIX)],foreground=[('active',ACCENT_MATRIX),('pressed',BG_VOID)])
  s.configure('Office.TCombobox',font=(TERM_FONT,9),padding=(8,6),fieldbackground=BG_PANEL,background=BG_PANEL,foreground=FG_PRIMARY,arrowcolor=ACCENT_MATRIX,borderwidth=1,relief='solid',focuscolor=ACCENT_MATRIX,selectbackground=BG_SELECTED,selectforeground=ACCENT_MATRIX,bordercolor=BORDER_DIM,lightcolor=BG_PANEL,darkcolor=BORDER_DIM)
  s.map('Office.TCombobox',fieldbackground=[('readonly',BG_PANEL)],foreground=[('readonly',FG_PRIMARY)],selectbackground=[('readonly',BG_SELECTED)],selectforeground=[('readonly',ACCENT_MATRIX)])
  s.configure('Office.TMenubutton',font=(TERM_FONT,9),padding=(8,6),background=BG_PANEL,foreground=FG_PRIMARY,arrowcolor=ACCENT_MATRIX,borderwidth=1,relief='solid',focuscolor=ACCENT_MATRIX,bordercolor=BORDER_DIM,lightcolor=BG_PANEL,darkcolor=BORDER_DIM)
  s.configure('TEntry',padding=(8,7),fieldbackground=BG_PANEL,foreground=FG_PRIMARY,insertcolor=ACCENT_MATRIX,focuscolor=ACCENT_MATRIX,selectbackground=BG_SELECTED,selectforeground=ACCENT_MATRIX,bordercolor=BORDER_DIM,lightcolor=BG_PANEL,darkcolor=BORDER_DIM)
  s.configure('TCombobox',padding=(5,4),fieldbackground=BG_PANEL,foreground=FG_PRIMARY,focuscolor=ACCENT_MATRIX,selectbackground=BG_SELECTED,selectforeground=ACCENT_MATRIX,bordercolor=BORDER_DIM,lightcolor=BG_PANEL,darkcolor=BORDER_DIM)
  for bar in ('TScrollbar','Vertical.TScrollbar','Horizontal.TScrollbar'):
   s.configure(bar,troughcolor=BG_VOID,background=BORDER_DIM,arrowcolor=ACCENT_MATRIX,bordercolor=BG_VOID,darkcolor=BORDER_DIM,lightcolor=BORDER_DIM,arrowsize=9,width=11,relief='flat')
   s.map(bar,background=[('active',BG_HOVER),('pressed',ACCENT_MATRIX)],arrowcolor=[('active',ACCENT_MATRIX),('pressed',BG_VOID)])

 def clear(self):
  for w in self.winfo_children():
   if w is not getattr(self, '_titlebar', None):
    w.destroy()