# Rasd - النافذة الرئيسية (تجمع كل الأجزاء)
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
from tasks_calendar import TasksCalendarMixin

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
    TasksCalendarMixin,
    tk.Tk):
 def __init__(self):
  super().__init__();self.title('Rasd | مدير ملفات المشاريع');self.geometry('720x600');self.minsize(720,600);self.configure(bg='#e8edf1');self.project='';self.root=None;self.scanq=queue.Queue();self.previewq=queue.Queue();self.searchq=queue.Queue();self.updateq=queue.Queue();self.preview_token=0;self.preview_executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='office-preview');self.cad_preview_executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='office-cad-preview');self.search_executor=ThreadPoolExecutor(max_workers=2,thread_name_prefix='office-search');self.update_executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='rasd-update');self._update_check_running=False;self._update_install_on_close=False;self._update_download_dialog=None;self.cad_preview_process=None;self.preview_future=None;self.search_future=None;self.search_serial=0;self.search_engine_lock=threading.Lock();self.preview_cache=OrderedDict();self.backstack=[];self.forwardstack=[];self.search_job=None;self.everything_hwnd=None;self.everything_windows={};self.everything_proc=None;self.everything_key=None;self.everything_instance=None;self.everything_data=None;self.everything_exe=None;self.everything_cli=None;self.everything_root=None;self.everything_attempts=0;self.watch_root=None;self.watch_stop=threading.Event();self.scan_lock=threading.Lock();self.sort_col='name';self.sort_desc=False;self.opened_sort_col='opened';self.opened_sort_desc=True;self.discipline='الكل';self.index_total=0;self.index_errors=0;self.preview_page=0;self.preview_zoom=1.0;self.view_mode='files';self._home_refresh_job=None;self.bind('<Configure>',self.schedule_home_refresh,add='+');self.bind_all('<MouseWheel>',self._task_route_mousewheel,add='+');self.bind('<FocusIn>',self._task_external_focus_sync,add='+');self._set_window_icon();self.protocol('WM_DELETE_WINDOW',self.close_app);self.setup_style();self.show_lock_screen() if self.password_enabled() else self.show_welcome();self._poll_after_id=self.after(150,self.poll_queue)
  if UPDATE_FAILURE.is_file():
   try:self.after(900,lambda:self._show_update_failure(UPDATE_FAILURE.read_text(encoding='utf-8',errors='replace')))
   except Exception:pass
  if not self.password_enabled():self.after(2200,self.check_for_updates)

 def _set_window_icon(self):
  try:
   icon_path=Path(getattr(sys,'_MEIPASS',BASE))/'Assets'/'rasd_logo.png'
   with Image.open(icon_path) as source:
    self.app_icon=ImageTk.PhotoImage(source.convert('RGBA').resize((64,64),Image.Resampling.LANCZOS))
   self.iconphoto(True,self.app_icon)
  except Exception:pass

 def setup_style(self):
  s=ttk.Style(self);s.theme_use('clam')
  s.configure('Treeview',rowheight=34,font=('Segoe UI',10),background='#f5f7f8',fieldbackground='#f5f7f8',foreground='#243746',borderwidth=0)
  s.configure('Treeview.Heading',font=('Segoe UI',9,'bold'),background='#dfe7ec',foreground='#19394e',padding=(7,9),relief='flat')
  s.map('Treeview',background=[('selected','#d9eff0')],foreground=[('selected','#102c3d')])
  s.configure('TNotebook',background='#e8edf1',borderwidth=0,tabmargins=(0,0,0,0))
  s.configure('TNotebook.Tab',font=('Segoe UI',9,'bold'),padding=(12,8),background='#e4ebef',foreground='#526b7c')
  s.map('TNotebook.Tab',background=[('selected','#ffffff')],foreground=[('selected','#087e8b')])
  s.configure('Toolbutton',font=('Segoe UI',9,'bold'),padding=(10,6),background='#e6edf1',foreground='#526b7c',borderwidth=0)
  s.map('Toolbutton',background=[('selected','#0d8190'),('active','#d5e9eb')],foreground=[('selected','#ffffff'),('active','#19394e')])
  s.configure('TButton',font=('Segoe UI',9),padding=(8,6),background='#ffffff',foreground='#28465a',borderwidth=0,relief='flat')
  s.map('TButton',background=[('active','#e3f0f1'),('pressed','#d1e7e9')],foreground=[('active','#087e8b')])
  s.configure('Office.TCombobox',font=('Segoe UI',9),padding=(8,6),fieldbackground='#ffffff',background='#ffffff',foreground='#19394e',arrowcolor='#0b7785',borderwidth=0,relief='flat')
  s.map('Office.TCombobox',fieldbackground=[('readonly','#ffffff')],foreground=[('readonly','#19394e')],selectbackground=[('readonly','#dcebed')],selectforeground=[('readonly','#19394e')])
  s.configure('Office.TMenubutton',font=('Segoe UI',9),padding=(8,6),background='#ffffff',foreground='#19394e',arrowcolor='#0b7785',borderwidth=0,relief='flat')
  s.configure('TEntry',padding=(8,7),fieldbackground='#ffffff',foreground='#19394e')
  s.configure('TCombobox',padding=(5,4),fieldbackground='#ffffff',foreground='#19394e')

 def clear(self):
  for w in self.winfo_children():w.destroy()