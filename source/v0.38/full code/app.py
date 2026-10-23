import os,sys,sqlite3,subprocess,threading,queue,csv,io,textwrap,math,ctypes,hashlib,shutil,time,json,secrets,colorsys,tempfile,re
from concurrent.futures import ThreadPoolExecutor
from collections import OrderedDict
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
import tkinter as tk
from tkinter import ttk,messagebox,simpledialog
from tkinter import font as tkfont
from PIL import Image,ImageTk,ImageDraw,ImageFont,ImageOps,ImageFilter,ImageStat,ImageChops
try:import fitz
except ImportError:fitz=None
try:import openpyxl
except ImportError:openpyxl=None
try:from docx import Document
except ImportError:Document=None
try:import xlrd
except ImportError:xlrd=None
try:from pyxlsb import open_workbook as open_xlsb_workbook
except ImportError:open_xlsb_workbook=None
try:import ezdxf
except ImportError:ezdxf=None
try:from pypdf import PdfReader
except ImportError:PdfReader=None
BASE=Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
def resolve_project_root():
 # Projects and all app-managed data live beside the executable. This also
 # keeps portable installs self-contained when the whole folder is moved.
 root=(BASE/'Log').resolve()
 root.mkdir(parents=True,exist_ok=True)
 return root
LOG=resolve_project_root();DB=LOG/'.office_index.db'
def is_project_path(path):
 try:
  root=LOG.resolve();candidate=Path(path).resolve()
  return candidate!=root and candidate.is_relative_to(root)
 except (OSError,ValueError,AttributeError):return False
GROUPS={'لوحات CAD':{'.dwg','.dxf'},'PDF':{'.pdf'},'Excel':{'.xlsx','.xls','.xlsm','.xlsb','.csv','.tsv'},'Word':{'.doc','.docx'},'الصور':{'.png','.jpg','.jpeg','.bmp','.gif','.tif','.tiff'},'أخرى':set()}
EXCEL_PREVIEW_PAGE_SIZE=100
@contextmanager
def connect():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row
 try:yield c;c.commit()
 finally:c.close()
with connect() as c:c.executescript('CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY,project TEXT,rel TEXT,name TEXT,ext TEXT,size INTEGER,mtime REAL,last_open TEXT,indexed TEXT); CREATE TABLE IF NOT EXISTS tags(path TEXT,tag TEXT,PRIMARY KEY(path,tag)); CREATE TABLE IF NOT EXISTS file_tag_catalog(project TEXT,tag TEXT,created TEXT,PRIMARY KEY(project,tag)); CREATE TABLE IF NOT EXISTS folder_tags(project TEXT,path TEXT,tag TEXT,created TEXT,PRIMARY KEY(project,path,tag)); CREATE TABLE IF NOT EXISTS extension_colors(ext TEXT PRIMARY KEY,accent TEXT UNIQUE,soft TEXT); CREATE TABLE IF NOT EXISTS search_history(project TEXT,query TEXT,mode TEXT,searched_at TEXT,PRIMARY KEY(project,query,mode)); CREATE TABLE IF NOT EXISTS saved_searches(project TEXT,query TEXT,mode TEXT,created TEXT,PRIMARY KEY(project,query,mode)); CREATE TABLE IF NOT EXISTS project_search_state(project TEXT PRIMARY KEY,query TEXT,mode TEXT,file_type TEXT); CREATE TABLE IF NOT EXISTS favorites(project TEXT,path TEXT,kind TEXT,created TEXT,PRIMARY KEY(project,path)); CREATE TABLE IF NOT EXISTS project_view_state(project TEXT PRIMARY KEY,current_rel TEXT,mode TEXT,folder_filter TEXT,project_filter TEXT,discipline TEXT,sort_col TEXT,sort_desc INTEGER,column_widths TEXT); CREATE TABLE IF NOT EXISTS file_changes(id INTEGER PRIMARY KEY AUTOINCREMENT,project TEXT,path TEXT,kind TEXT,changed_at TEXT); CREATE INDEX IF NOT EXISTS idx_changes_project ON file_changes(project,changed_at); CREATE TABLE IF NOT EXISTS project_visits(project TEXT PRIMARY KEY,last_visit TEXT); CREATE TABLE IF NOT EXISTS file_open_history(id INTEGER PRIMARY KEY AUTOINCREMENT,project TEXT NOT NULL,path TEXT NOT NULL,opened_at TEXT NOT NULL,UNIQUE(project,path,opened_at)); CREATE INDEX IF NOT EXISTS idx_open_history_project ON file_open_history(project,opened_at); CREATE TABLE IF NOT EXISTS project_scan_state(project TEXT PRIMARY KEY,initial_scan_done INTEGER NOT NULL DEFAULT 0); CREATE TABLE IF NOT EXISTS activity_log(id INTEGER PRIMARY KEY AUTOINCREMENT,project TEXT NOT NULL,action TEXT NOT NULL,details TEXT NOT NULL,path TEXT,occurred_at TEXT NOT NULL); CREATE INDEX IF NOT EXISTS idx_activity_project ON activity_log(project,occurred_at);')
with connect() as c:c.execute("insert or ignore into file_open_history(project,path,opened_at) select project,path,last_open from files where coalesce(last_open,'')<>''")
with connect() as c:c.execute('CREATE TABLE IF NOT EXISTS app_settings(key TEXT PRIMARY KEY,value TEXT NOT NULL)')
def stamp(t):
 try:return datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M')
 except:return '—'
def sizefmt(n):
 for u in ('B','KB','MB','GB'):
  if n<1024:return f'{n:.0f} {u}'
  n/=1024
 return f'{n:.1f} TB'
def classify(ext):
 ext=(ext or '').lower()
 if ext and not ext.startswith('.'):ext='.'+ext
 for k,v in GROUPS.items():
  if k!='أخرى' and ext in v:return k
 return ext[1:].upper() if ext else 'بدون امتداد'
def file_icon(path,is_dir=False):
 if is_dir:return '📁'
 ext=Path(path).suffix.lower()
 return {'.pdf':'📕','.xlsx':'📗','.xls':'📗','.xlsm':'📗','.csv':'📗','.doc':'📘','.docx':'📘','.dwg':'📐','.dxf':'📐','.png':'🖼','.jpg':'🖼','.jpeg':'🖼','.bmp':'🖼'}.get(ext,'📄')
def type_icon(kind):
 return {'لوحات CAD':'📐','PDF':'📕','Excel':'📗','Word':'📘','الصور':'🖼','أخرى':'📄'}.get(kind,'📄')
def tag_badges(value):
 tags=[x for x in (value or '').split() if x]
 out=[]
 for i,tag in enumerate(tags):
  key=tag.casefold()
  if any(k in key for k in ('ري','irrig')):dot='🟢'
  elif 'زراع' in key:dot='🟡'
  elif 'صح' in key or 'sewag' in key:dot='🔵'
  elif 'مطر' in key or 'storm' in key:dot='🟣'
  elif 'معتمد' in key or 'approved' in key:dot='✅'
  else:dot=('🟦','🟠','🟣','🟢')[i%4]
  out.append(f'{dot} {tag}')
 return '   '.join(out)
FILTER_COLUMNS=['Name','Case','Whole Word','Path','Diacritics','Prefix','Suffix','Ignore Punctuation','Ignore Whitespace','Regex','Search','Columns','Sort','Descending','View','Macro','Key']
def sync_everything_filters(data,instance,extensions):
 path=data/f'Filters-{instance}.csv';rows=[]
 if path.exists():
  for encoding in ('utf-8-sig','mbcs','cp1252'):
   try:
    with path.open('r',encoding=encoding,newline='') as f:rows=list(csv.reader(f))
    break
   except (UnicodeError,OSError,csv.Error):rows=[]
 if rows and rows[0] and rows[0][0].strip().casefold()=='name':rows=rows[1:]
 managed='[Project Type] '
 preserved=[row for row in rows if not (row and row[0].startswith(managed))]
 for ext in sorted({e.lower().lstrip('.') for e in extensions if e and e.startswith('.') and e[1:].replace('_','').replace('-','').replace('.','').isalnum()}):
  macro='ol_'+''.join(ch if ch.isalnum() else '_' for ch in ext)
  preserved.append([managed+ext.upper()+f' (*.{ext})',0,0,0,0,0,0,0,0,0,'ext:'+ext,'','',0,'',macro,''])
 temp=path.with_suffix('.csv.tmp')
 with temp.open('w',encoding='utf-8-sig',newline='') as f:
  writer=csv.writer(f,lineterminator='\n');writer.writerow(FILTER_COLUMNS);writer.writerows((row+['']*len(FILTER_COLUMNS))[:len(FILTER_COLUMNS)] for row in preserved)
 temp.replace(path)

class App(tk.Tk):
 def __init__(self):
  super().__init__();self.title('Rasd | مدير ملفات المشاريع');self.geometry('720x600');self.minsize(720,600);self.configure(bg='#e8edf1');self.project='';self.root=None;self.scanq=queue.Queue();self.previewq=queue.Queue();self.searchq=queue.Queue();self.preview_token=0;self.preview_executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='office-preview');self.cad_preview_executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='office-cad-preview');self.search_executor=ThreadPoolExecutor(max_workers=2,thread_name_prefix='office-search');self.cad_preview_process=None;self.preview_future=None;self.search_future=None;self.search_serial=0;self.search_engine_lock=threading.Lock();self.preview_cache=OrderedDict();self.backstack=[];self.forwardstack=[];self.search_job=None;self.everything_hwnd=None;self.everything_windows={};self.everything_proc=None;self.everything_key=None;self.everything_instance=None;self.everything_data=None;self.everything_exe=None;self.everything_cli=None;self.everything_root=None;self.everything_attempts=0;self.watch_root=None;self.watch_stop=threading.Event();self.scan_lock=threading.Lock();self.sort_col='name';self.sort_desc=False;self.opened_sort_col='opened';self.opened_sort_desc=True;self.discipline='الكل';self.index_total=0;self.index_errors=0;self.preview_page=0;self.preview_zoom=1.0;self.view_mode='files';self._home_refresh_job=None;self.bind('<Configure>',self.schedule_home_refresh,add='+');self._set_window_icon();self.protocol('WM_DELETE_WINDOW',self.close_app);self.setup_style();self.show_lock_screen() if self.password_enabled() else self.show_welcome();self._poll_after_id=self.after(150,self.poll_queue)

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

 def password_record(self):
  with connect() as c:values={r['key']:r['value'] for r in c.execute("select key,value from app_settings where key in ('password_salt','password_hash','password_iterations')")}
  if not all(k in values for k in ('password_salt','password_hash','password_iterations')):return None
  try:return values['password_salt'],values['password_hash'],int(values['password_iterations'])
  except (TypeError,ValueError):return None

 def password_enabled(self):return self.password_record() is not None

 def verify_password(self,password):
  record=self.password_record()
  if not record:return False
  salt,digest,iterations=record
  try:candidate=hashlib.pbkdf2_hmac('sha256',password.encode('utf-8'),bytes.fromhex(salt),iterations).hex()
  except (ValueError,TypeError):return False
  return secrets.compare_digest(candidate,digest)

 def store_password(self,password):
  salt=secrets.token_bytes(16);iterations=310000;digest=hashlib.pbkdf2_hmac('sha256',password.encode('utf-8'),salt,iterations).hex()
  with connect() as c:c.executemany('insert into app_settings(key,value) values(?,?) on conflict(key) do update set value=excluded.value',[('password_salt',salt.hex()),('password_hash',digest),('password_iterations',str(iterations))])

 def clear_password(self):
  with connect() as c:c.execute("delete from app_settings where key in ('password_salt','password_hash','password_iterations')")

 def show_lock_screen(self):
  self.title('Rasd Login')
  self.clear();self.unbind('<Return>');self.title('Rasd | فتح البرنامج');self.configure(bg='#e8edf1');self.geometry('560x400');self.minsize(520,360)
  self.geometry(f'560x400+{max(0,(self.winfo_screenwidth()-560)//2)}+{max(0,(self.winfo_screenheight()-400)//2)}')
  shell=tk.Frame(self,bg='#102c3d');shell.pack(fill='both',expand=True,padx=20,pady=20)
  card=tk.Frame(shell,bg='#f5f7f8',highlightbackground='#d9e4e9',highlightthickness=1);card.place(relx=.5,rely=.5,anchor='center',width=450,height=300)
  tk.Label(card,text='RASD',bg='#f5f7f8',fg='#102c3d',font=('Segoe UI',19,'bold')).pack(pady=(32,8))
  tk.Label(card,text='أدخل كلمة المرور لفتح البرنامج',bg='#f5f7f8',fg='#526b7c',font=('Segoe UI',11)).pack(pady=(0,18))
  self.login_status=tk.StringVar(value='')
  self.password_entry=ttk.Entry(card,show='●',font=('Segoe UI',12),justify='center');self.password_entry.pack(fill='x',padx=38,ipady=5)
  tk.Button(card,text='فتح البرنامج',command=self.unlock_app,bg='#167f8c',fg='white',activebackground='#106b76',activeforeground='white',relief='flat',font=('Segoe UI',10,'bold'),padx=18,pady=8,cursor='hand2').pack(pady=(15,5))
  tk.Label(card,textvariable=self.login_status,bg='#f5f7f8',fg='#bd4856',font=('Segoe UI',9)).pack()
  tk.Label(card,text='كلمة المرور تمنع الدخول للبرنامج فقط؛ ملفات المشروع تظل ملفات عادية.',bg='#f5f7f8',fg='#758692',font=('Segoe UI',8),wraplength=400).pack(side='bottom',pady=14)
  self.bind('<Return>',lambda e:(self.unlock_app(),'break'));self.password_entry.focus_set()

 def unlock_app(self):
  if self.verify_password(self.password_entry.get()):
   self.unbind('<Return>');self.show_welcome();self.animate_window_in()
  else:
   self.login_status.set('كلمة المرور غير صحيحة. حاول مرة أخرى.');self.password_entry.delete(0,'end');self.password_entry.focus_set()

 def manage_password(self):
  enabled=self.password_enabled();dialog=tk.Toplevel(self);dialog.title('حماية البرنامج');dialog.configure(bg='#eef2f5');dialog.resizable(False,False);dialog.transient(self);dialog.grab_set()
  frame=tk.Frame(dialog,bg='white',highlightbackground='#d7e1e6',highlightthickness=1);frame.pack(fill='both',expand=True,padx=14,pady=14)
  tk.Label(frame,text='حماية البرنامج',bg='white',fg='#19394e',font=('Segoe UI',14,'bold')).pack(anchor='e',padx=18,pady=(16,5))
  tk.Label(frame,text=('الحماية مفعلة. أدخل الحالية للتغيير أو الإلغاء.' if enabled else 'فعّل كلمة مرور اختيارية عند بدء البرنامج.'),bg='white',fg='#617789',font=('Segoe UI',9),justify='right').pack(anchor='e',padx=18,pady=(0,12))
  fields=tk.Frame(frame,bg='white');fields.pack(fill='x',padx=18);entries={}
  specs=([('old','كلمة المرور الحالية')] if enabled else [])+[('new','كلمة مرور جديدة'),('confirm','تأكيد كلمة المرور')]
  for key,label in specs:
   tk.Label(fields,text=label,bg='white',fg='#435b6d',font=('Segoe UI',9)).pack(anchor='e',pady=(5,2))
   entry=ttk.Entry(fields,show='●',justify='right',width=38);entry.pack(fill='x',ipady=3);entries[key]=entry
  status=tk.StringVar(value='')
  tk.Label(frame,textvariable=status,bg='white',fg='#bd4856',font=('Segoe UI',9),justify='right').pack(anchor='e',padx=18,pady=(7,0))
  actions=tk.Frame(frame,bg='white');actions.pack(fill='x',padx=18,pady=(8,14))
  def save():
   if enabled and not self.verify_password(entries['old'].get()):status.set('كلمة المرور الحالية غير صحيحة.');return
   password=entries['new'].get();confirm=entries['confirm'].get()
   if len(password)<6:status.set('استخدم 6 أحرف على الأقل.');return
   if password!=confirm:status.set('تأكيد كلمة المرور غير مطابق.');return
   self.store_password(password);messagebox.showinfo('حماية البرنامج','تم حفظ كلمة المرور. سيطلبها البرنامج عند تشغيله.',parent=dialog);dialog.destroy()
  def disable():
   if not self.verify_password(entries['old'].get()):status.set('كلمة المرور الحالية غير صحيحة.');return
   self.clear_password();messagebox.showinfo('حماية البرنامج','تم إلغاء كلمة المرور.',parent=dialog);dialog.destroy()
  tk.Button(actions,text=('تغيير كلمة المرور' if enabled else 'تفعيل كلمة المرور'),command=save,bg='#167f8c',fg='white',activebackground='#106b76',activeforeground='white',relief='flat',font=('Segoe UI',9,'bold'),padx=12,pady=6,cursor='hand2').pack(side='right',padx=3)
  if enabled:ttk.Button(actions,text='إلغاء الحماية',command=disable).pack(side='right',padx=3)
  ttk.Button(actions,text='إغلاق',command=dialog.destroy).pack(side='left',padx=3)
  if enabled:entries['old'].focus_set()
  else:entries['new'].focus_set()
  dialog.update_idletasks();dialog.geometry(f'+{self.winfo_rootx()+(self.winfo_width()-dialog.winfo_width())//2}+{self.winfo_rooty()+(self.winfo_height()-dialog.winfo_height())//2}')

 def header(self,title):
  h=tk.Frame(self,bg='#102c3d',height=66);h.pack(fill='x')
  brand=tk.Frame(h,bg='#102c3d');brand.pack(side='left',padx=18,pady=5)
  try:
   with Image.open(Path(getattr(sys,'_MEIPASS',BASE))/'Assets'/'rasd_logo.png') as source:
    self.header_icon=ImageTk.PhotoImage(source.convert('RGBA').resize((38,38),Image.Resampling.LANCZOS))
   tk.Label(brand,image=self.header_icon,bg='#102c3d').pack(side='left',padx=(0,8))
  except Exception:pass
  brand_text=tk.Frame(brand,bg='#102c3d');brand_text.pack(side='left')
  tk.Label(brand_text,text='RASD',font=('Segoe UI',17,'bold'),fg='white',bg='#102c3d').pack(anchor='w')
  tk.Label(brand_text,text='Made by ENG. Amr Hesham',font=('Segoe UI',8),fg='#a9c3d0',bg='#102c3d').pack(anchor='w')
  tk.Label(h,text=title,font=('Segoe UI',14,'bold'),fg='#d8e7ef',bg='#102c3d').pack(side='right',padx=22);return h

 def show_welcome(self):
  self.title('Rasd | Start')
  self.clear();self.project='';self.configure(bg='#c8d2d8');self.geometry('720x600');self.minsize(600,520)
  try:self.state('normal')
  except tk.TclError:pass
  art_path=Path(getattr(sys,'_MEIPASS',BASE))/'Assets'/'welcome_art.jpg'
  bg=tk.Frame(self,bg='#c8d2d8');bg.pack(fill='both',expand=True)
  try:
   with Image.open(art_path) as src:
    backdrop=ImageOps.fit(src.convert('RGB'),(720,600),method=Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(10))
    backdrop=Image.blend(backdrop,Image.new('RGB',(720,600),'#e5edf1'),.42)
   self._welcome_background_source=backdrop.copy();self.welcome_background_photo=ImageTk.PhotoImage(backdrop)
   self._welcome_background_label=tk.Label(bg,image=self.welcome_background_photo,borderwidth=0,bg='#c8d2d8');self._welcome_background_label.place(x=0,y=0,relwidth=1,relheight=1)
   def resize_welcome_background(event):
    if event.width<2 or event.height<2:return
    resized=ImageOps.fit(self._welcome_background_source,(event.width,event.height),method=Image.Resampling.LANCZOS)
    self.welcome_background_photo=ImageTk.PhotoImage(resized);self._welcome_background_label.configure(image=self.welcome_background_photo)
   bg.bind('<Configure>',resize_welcome_background)
  except Exception:pass
  card=tk.Frame(bg,bg='#edf2f5',highlightbackground='#ffffff',highlightthickness=2);card.place(relx=.5,rely=.5,anchor='center',relwidth=.86,relheight=.88)
  brand=tk.Frame(card,bg='#edf2f5');brand.pack(pady=(12,0))
  try:
   with Image.open(Path(getattr(sys,'_MEIPASS',BASE))/'Assets'/'rasd_logo.png') as source:self.welcome_logo=ImageTk.PhotoImage(source.convert('RGBA').resize((40,40),Image.Resampling.LANCZOS))
   tk.Label(brand,image=self.welcome_logo,bg='#edf2f5').pack(side='left',padx=(0,8))
  except Exception:pass
  brand_stack=tk.Frame(brand,bg='#edf2f5');brand_stack.pack(side='left',anchor='w')
  tk.Label(brand_stack,text='RASD',font=('Segoe UI',17,'bold'),fg='#102c3d',bg='#edf2f5').pack(anchor='w')
  tk.Label(brand_stack,text='Made by ENG. Amr Hesham',font=('Segoe UI',8),fg='#718491',bg='#edf2f5').pack(anchor='w')
  tk.Label(card,text='تعالى نعمل واحد ... مشروع جامد',font=('Segoe UI',18,'bold'),fg='#187db2',bg='#edf2f5',justify='center',wraplength=570).pack(fill='x',padx=18,pady=(8,8))
  image_holder=tk.Frame(card,bg='white',highlightbackground='#d8e2e8',highlightthickness=1);image_holder.pack(fill='both',expand=True,padx=24,pady=(0,78))
  try:
   with Image.open(art_path) as src:art=ImageOps.fit(src.convert('RGB'),(650,380),method=Image.Resampling.LANCZOS)
   self.welcome_photo=ImageTk.PhotoImage(art);tk.Label(image_holder,image=self.welcome_photo,bg='white',borderwidth=0).pack(fill='both',expand=True,padx=4,pady=4)
  except Exception:tk.Label(image_holder,text='👷',font=('Segoe UI Emoji',90),bg='white').pack(expand=True)
  pill=Image.new('RGBA',(300,64),(0,0,0,0));pd=ImageDraw.Draw(pill);pd.rounded_rectangle((8,8,292,60),radius=27,fill=(70,92,111,45));pd.rounded_rectangle((5,2,295,54),radius=27,fill=(249,252,254,250),outline=(231,239,245,255),width=2)
  self.start_photo=ImageTk.PhotoImage(pill);start=tk.Canvas(card,width=300,height=64,bg='#edf2f5',highlightthickness=0,cursor='hand2');start.create_image(150,32,image=self.start_photo);start.create_text(150,27,text='Start',font=('Segoe UI',18,'bold'),fill='#263946');start.bind('<Button-1>',lambda e:self.enter_app());start.place(relx=.5,rely=.97,anchor='s');self.bind('<Return>',lambda e:self.enter_app())

 def enter_app(self):
  self.unbind('<Return>');self.set_workspace_geometry();self.show_home()

 def set_workspace_geometry(self):
  screen_w=max(720,self.winfo_screenwidth());screen_h=max(520,self.winfo_screenheight())
  width=min(1440,screen_w-40);height=min(880,screen_h-80)
  min_w=min(1050,width);min_h=min(650,height)
  self.minsize(min_w,min_h);self.geometry(f'{width}x{height}+{max(0,(screen_w-width)//2)}+{max(0,(screen_h-height)//2)}')

 def animate_window_in(self):
  try:
   if getattr(self,'_fade_job',None):self.after_cancel(self._fade_job)
   self.wm_attributes('-alpha',0.94)
   def step(value=94):
    value=min(100,value+2);self.wm_attributes('-alpha',value/100)
    if value<100:self._fade_job=self.after(14,lambda:step(value))
   self._fade_job=self.after(14,lambda:step())
  except Exception:pass

 def show_home(self):
  if hasattr(self,'watch_stop'):self.watch_stop.set();self.watch_root=None
  self.clear();self.project='';self.configure(bg='#eef3f7')
  top=tk.Frame(self,bg='#eef2f5',height=58,highlightbackground='#e0e8ed',highlightthickness=1);top.pack(fill='x');top.pack_propagate(False)
  brand=tk.Frame(top,bg='#eef2f5');brand.pack(side='left',padx=24)
  try:
   with Image.open(Path(getattr(sys,'_MEIPASS',BASE))/'Assets'/'rasd_logo.png') as source:
    self.brand_icon=ImageTk.PhotoImage(source.convert('RGBA').resize((32,32),Image.Resampling.LANCZOS))
   tk.Label(brand,image=self.brand_icon,bg='#eef2f5').pack(side='left',padx=(0,8))
  except Exception:tk.Label(brand,text='◉',font=('Segoe UI Symbol',22,'bold'),fg='#1595a5',bg='#eef2f5').pack(side='left',padx=(0,8))
  tk.Label(brand,text='RASD',font=('Segoe UI',15,'bold'),fg='#253c4b',bg='#eef2f5').pack(side='left')
  tk.Label(brand,text='Made by ENG. Amr Hesham',font=('Segoe UI',8),fg='#718491',bg='#eef2f5').pack(side='left',padx=(9,0),pady=(6,0))
  tk.Button(top,text='📁  مجلد Log',command=lambda:os.startfile(str(LOG)),bg='#eef2f5',fg='#607786',activebackground='#e9f0f4',relief='flat',font=('Segoe UI',9),padx=10,cursor='hand2').pack(side='right',padx=(4,18))
  tk.Button(top,text='⚙  حماية البرنامج',command=self.manage_password,bg='#eef2f5',fg='#607786',activebackground='#e9f0f4',relief='flat',font=('Segoe UI',9),padx=10,cursor='hand2').pack(side='right',padx=4)
  tk.Button(top,text='＋ مشروع جديد',command=self.new_project,bg='#3478e5',fg='white',activebackground='#2868ce',activeforeground='white',relief='flat',font=('Segoe UI',9,'bold'),padx=13,pady=7,cursor='hand2').pack(side='right',padx=5)
  tk.Label(top,text='مساحة المشاريع',font=('Segoe UI',9),fg='#617889',bg='#eef2f5').pack(side='right',padx=10)
  wrap=tk.Frame(self,bg='#eef3f7');wrap.pack(fill='both',expand=True,padx=42,pady=(12,22))
  controls=tk.Frame(wrap,bg='#eef3f7');controls.pack(fill='x',pady=(3,12))
  self.project_search=tk.StringVar(value='ابحث عن مشروع')
  search_wrap=tk.Frame(controls,bg='white',highlightbackground='#d8e1e7',highlightthickness=1);search_wrap.pack(side='left',fill='x',expand=True,padx=(0,12))
  tk.Label(search_wrap,text='⌕',font=('Segoe UI',17),fg='#8496a3',bg='white').pack(side='left',padx=(11,3))
  entry=tk.Entry(search_wrap,textvariable=self.project_search,bg='white',fg='#344c5b',insertbackground='#3478e5',relief='flat',font=('Segoe UI',10),justify='left');entry.pack(side='left',fill='x',expand=True,ipady=8,padx=6)
  entry.bind('<FocusIn>',lambda e:entry.delete(0,'end') if entry.get()=='ابحث عن مشروع' else None);entry.bind('<FocusOut>',lambda e:entry.insert(0,'ابحث عن مشروع') if not entry.get() else None)
  self.home_filter_mode=getattr(self,'home_filter_mode','all');self.home_filter_buttons={}
  for label,command in [('الكل','all'),('المفضلة','favorites'),('آخر زيارة','visited'),('أضيف حديثاً','added')]:
   active=command==self.home_filter_mode
   b=tk.Button(controls,text=label,command=lambda c=command:self.home_project_filter(c),bg='#3478e5' if active else '#e8eef3',fg='white' if active else '#526b7b',activebackground='#2868ce',relief='flat',font=('Segoe UI',9,'bold' if active else 'normal'),padx=12,pady=8,cursor='hand2');b.pack(side='left',padx=3);self.home_filter_buttons[command]=b
  self.home_sort_button=tk.Button(controls,text='☷  ترتيب المشاريع',command=self.toggle_project_sort,bg='#eef3f7',fg='#527083',activebackground='#e2ebf0',relief='flat',font=('Segoe UI',9),padx=10,pady=8,cursor='hand2',state='disabled' if self.home_filter_mode in ('visited','added') else 'normal');self.home_sort_button.pack(side='right',padx=(7,0))
  project_total=sum(1 for p in LOG.iterdir() if p.is_dir() and not p.name.startswith('.') and is_project_path(p))
  with connect() as c:
   indexed_total=c.execute('select count(*) from files').fetchone()[0]
   favorite_total=c.execute('select count(*) from favorites').fetchone()[0]
  summary=tk.Frame(wrap,bg='#eef3f7');summary.pack(fill='x',pady=(0,7))
  for title,value,accent in [('المشاريع',f'{project_total:,}','#3285c7'),('الملفات المفهرسة',f'{indexed_total:,}','#1a9a83'),('المفضلة',f'{favorite_total:,}','#d69637')]:
   tile=tk.Frame(summary,bg='white',highlightbackground='#dbe4e9',highlightthickness=1);tile.pack(side='right',fill='x',expand=True,padx=(5,0))
   tk.Label(tile,text=value,bg='white',fg=accent,font=('Segoe UI',16,'bold')).pack(anchor='e',padx=12,pady=(6,0))
   tk.Label(tile,text=title,bg='white',fg='#718592',font=('Segoe UI',8)).pack(anchor='e',padx=12,pady=(0,6))
  self.project_count_label=tk.Label(wrap,text='',bg='#eef3f7',fg='#82919b',font=('Segoe UI',8));self.project_count_label.pack(anchor='e',pady=(0,1))
  self.cards=tk.Frame(wrap,bg='#eef3f7');self.cards.pack(fill='both',expand=True,pady=1);self.project_card_photos=[]
  self.project_search.trace_add('write',lambda *_:self.render_projects());self.render_projects();self.animate_window_in()

 def home_project_filter(self,mode):
  self.home_filter_mode={'recent':'visited'}.get(mode,mode)
  if getattr(self,'home_sort_button',None):self.home_sort_button.configure(state='disabled' if self.home_filter_mode in ('visited','added') else 'normal')
  for key,button in getattr(self,'home_filter_buttons',{}).items():
   active=key==self.home_filter_mode;button.configure(bg='#3478e5' if active else '#e8eef3',fg='white' if active else '#526b7b',font=('Segoe UI',9,'bold' if active else 'normal'))
  self.render_projects()

 def toggle_project_sort(self):
  self.home_sort_mode='recent' if getattr(self,'home_sort_mode','name')=='name' else 'name'
  self.render_projects()

 def schedule_home_refresh(self,event=None):
  # Defer project-card rebuilding until the native window resize has settled.
  if event is not None and getattr(event,'widget',self) is not self:return
  job=getattr(self,'_home_refresh_job',None)
  if job:
   try:self.after_cancel(job)
   except tk.TclError:pass
  try:self._home_refresh_job=self.after(240,self.refresh_home_after_resize)
  except tk.TclError:self._home_refresh_job=None

 def refresh_home_after_resize(self):
  self._home_refresh_job=None
  cards=getattr(self,'cards',None)
  try:
   if not getattr(self,'project','') and cards and cards.winfo_exists() and cards.winfo_ismapped():
    self.after_idle(self.render_projects)
  except tk.TclError:pass

 def render_projects(self):
  for w in self.cards.winfo_children():w.destroy()
  with connect() as c:counts={r['project']:(r['n'],r['latest']) for r in c.execute('select project,count(*) n,max(mtime) latest from files group by project')}
  projects=[p for p in LOG.iterdir() if p.is_dir() and not p.name.startswith('.') and is_project_path(p)]
  mode=getattr(self,'home_filter_mode','all')
  if mode=='favorites':
   with connect() as c:names={r['project'] for r in c.execute('select distinct project from favorites')}
   projects=[p for p in projects if p.name in names]
  elif mode=='visited':
   with connect() as c:visited=[r['project'] for r in c.execute('select project from project_visits order by last_visit desc limit 8')]
   by_name={p.name:p for p in projects};projects=[by_name[name] for name in visited if name in by_name]
  elif mode=='added':
   projects=sorted(projects,key=lambda p:(p.stat().st_ctime if p.exists() else 0),reverse=True)[:8]
  if mode not in ('visited','added'):
   projects=sorted(projects,key=(lambda p:p.stat().st_mtime) if getattr(self,'home_sort_mode','name')=='recent' else (lambda p:p.name.lower()),reverse=getattr(self,'home_sort_mode','name')=='recent')
  query=getattr(self,'project_search',tk.StringVar(value='')).get().strip().casefold()
  if query and query!='ابحث عن مشروع':projects=[p for p in projects if query in p.name.casefold()]
  self.project_card_photos=[]
  if hasattr(self,'project_count_label'):self.project_count_label.configure(text=f'{len(projects)} مشروع')
  if not projects:
   empty=tk.Frame(self.cards,bg='white',highlightbackground='#d8e2ea',highlightthickness=1);empty.pack(fill='x',pady=25)
   tk.Label(empty,text='ابدأ بمشروعك الأول',font=('Segoe UI',17,'bold'),fg='#15374d',bg='white').pack(anchor='e',padx=24,pady=(22,4))
   tk.Label(empty,text='أنشئ مشروعًا جديدًا أو انسخ مجلد مشروعك إلى مجلد Log.',font=('Segoe UI',11),fg='#617789',bg='white').pack(anchor='e',padx=24,pady=(0,22));return
  screen_width=max(720,self.winfo_screenwidth());window_width=min(1440,screen_width-40);card_area_width=max(280,window_width-84);columns=max(1,min(4,card_area_width//280))
  for col in range(max(columns,getattr(self,'project_columns',0))):self.cards.grid_columnconfigure(col,weight=1 if col<columns else 0,uniform='project-card' if col<columns else '')
  self.project_columns=columns
  for i,p in enumerate(projects):
   indexed=counts.get(p.name);n=indexed[0] if indexed else None;count_text=f'{n:,} ملف' if n is not None else 'جارٍ تجهيز الفهرس'
   try:
    child_count=sum(1 for x in p.iterdir() if x.is_dir() and not x.name.startswith('.'))
    latest=indexed[1] if indexed and indexed[1] else p.stat().st_mtime;modified=datetime.fromtimestamp(latest).strftime('%d-%m-%Y')
   except OSError:child_count=0;modified='—'
   box=tk.Frame(self.cards,bg='white',highlightbackground='#d7e1e7',highlightthickness=1,cursor='hand2');box.grid(row=i//columns,column=i%columns,sticky='nsew',padx=7,pady=7)
   image_path=None
   if image_path is None:
    try:image_path=next(x for x in p.rglob('*') if x.is_file() and x.suffix.lower() in ('.png','.jpg','.jpeg','.bmp','.tif','.tiff'))
    except (StopIteration,OSError):pass
   try:
    if image_path:
     with Image.open(image_path) as src:thumb=ImageOps.fit(src.convert('RGB'),(430,175),method=Image.Resampling.LANCZOS)
     photo=ImageTk.PhotoImage(thumb);self.project_card_photos.append(photo)
     pic=tk.Label(box,image=photo,bg='#dce8ed',borderwidth=0);pic.pack(fill='x')
    else:
     art=tk.Canvas(box,height=145,bg='#dce8ed',highlightthickness=0);art.pack(fill='x');art.create_rectangle(0,0,430,145,fill='#dce8ed',outline='');art.create_line(0,110,110,35,225,98,340,25,430,105,fill='#83b4bc',width=3);art.create_text(390,112,text='RASD  /  PROJECT',anchor='e',fill='#416a79',font=('Segoe UI',9,'bold'))
   except Exception:
    art=tk.Frame(box,bg='#dce8ed',height=145);art.pack(fill='x');art.pack_propagate(False)
   details=tk.Frame(box,bg='white');details.pack(fill='x',padx=11,pady=(9,0))
   tk.Label(details,text=p.name,font=('Segoe UI',11,'bold'),fg='#253c4b',bg='white',anchor='e').pack(anchor='e',fill='x')
   tk.Label(details,text=f'▤  {count_text}     ◷  {modified}',font=('Segoe UI',8),fg='#87949d',bg='white',anchor='e').pack(anchor='e',fill='x',pady=(4,0))
   tags=[]
   try:
    with connect() as c:tags=[r['tag'] for r in c.execute('select t.tag,count(*) n from tags t join files f on f.path=t.path where f.project=? group by t.tag order by n desc limit 3',(p.name,))]
   except Exception:pass
   tagrow=tk.Frame(box,bg='white');tagrow.pack(fill='x',padx=8,pady=(7,10))
   if tags:
    for tag in tags:tk.Label(tagrow,text='#'+tag.lstrip('#'),bg='#f0f3f5',fg='#687987',font=('Segoe UI',7),padx=6,pady=3).pack(side='left',padx=2)
   else:tk.Label(tagrow,text=f'{child_count} مجلدات',bg='#f0f3f5',fg='#687987',font=('Segoe UI',7),padx=6,pady=3).pack(side='left',padx=2)
   open_badge=tk.Label(box,text='↗',font=('Segoe UI',11,'bold'),fg='#638293',bg='white',width=2,cursor='hand2');open_badge.place(relx=.95,rely=.04,anchor='ne')
   def bind_open(widget,project=p):
    widget.bind('<Button-1>',lambda e,x=project:self.open_project(x))
    for child in widget.winfo_children():bind_open(child,project)
   bind_open(box)

 def new_project(self):
  name=simpledialog.askstring('مشروع جديد','اسم المشروع:',parent=self)
  if not name:return
  name=name.strip()
  if not name or name.startswith('.') or name in ('.','..') or name[-1:] in (' ','.') or any(ch in name for ch in '<>:"/\\|?*'):
   return messagebox.showwarning('اسم غير صالح','اكتب اسم مجلد مشروع صالحًا من دون رموز المسارات.',parent=self)
  p=LOG/name
  if p.exists():return messagebox.showwarning('موجود','يوجد مشروع بهذا الاسم.')
  p.mkdir(parents=True)
  self.log_activity('إنشاء مشروع',f'تم إنشاء المشروع «{p.name}»',path=p,project=p.name)
  self.render_projects()

 def log_activity(self,action,details,path=None,project=None,occurred_at=None):
  project=project or getattr(self,'project','')
  if not project:return
  target=str(Path(path).resolve()) if path else None
  when=occurred_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
  with connect() as c:c.execute('insert into activity_log(project,action,details,path,occurred_at) values(?,?,?,?,?)',(project,str(action),str(details),target,when))

 def open_project(self,root):
  root=Path(root).resolve()
  if not is_project_path(root) or not root.is_dir():
   return messagebox.showwarning('مسار مشروع غير مسموح','ضع مجلد المشروع داخل مجلد Log الموجود بجوار Rasd.exe.',parent=self)
  self.search_serial+=1
  self.stop_everything_instance()
  self.watch_stop.set();self.watch_stop=threading.Event();self.watch_root=None;self.root=root;self.project=root.name;self.backstack=[];self.forwardstack=[]
  self.rebase_project_index(root)
  with connect() as c:
   state=c.execute('select * from project_view_state where project=?',(self.project,)).fetchone()
   visit=c.execute('select last_visit from project_visits where project=?',(self.project,)).fetchone()
   self.visit_since=visit['last_visit'] if visit else '0000'
   c.execute('insert into project_visits(project,last_visit) values(?,?) on conflict(project) do update set last_visit=excluded.last_visit',(self.project,stamp(time.time())))
  self.log_activity('فتح مشروع',f'تم فتح المشروع «{self.project}»',path=root)
  self.mode=state['mode'] if state and state['mode'] in ('folder','project') else 'folder'
  self.folder_group=state['folder_filter'] if state and state['folder_filter'] else 'الكل'
  self.project_group=state['project_filter'] if state and state['project_filter'] else 'الكل'
  self.discipline=state['discipline'] if state else 'الكل'
  self.sort_col=state['sort_col'] if state else 'name'
  self.sort_desc=bool(state['sort_desc']) if state else False
  try:self.column_widths=json.loads(state['column_widths']) if state and state['column_widths'] else {}
  except Exception:self.column_widths={}
  self.current=root;self.preview_current_path=None
  if state and state['current_rel']:
   try:
    restored=(root/Path(state['current_rel'])).resolve();restored.relative_to(root)
    if restored.is_dir():self.current=restored
   except (OSError,ValueError,TypeError):pass
  self.build_explorer();self.animate_window_in();self.scan_summary.set('جارٍ فهرسة ملفات المشروع...');self.start_scan_progress();threading.Thread(target=self.scan_worker,args=(root,),daemon=True).start()

 def rebase_project_index(self,root):
  """Keep tags, favorites, and change history attached when the portable Log folder moves."""
  root=Path(root).resolve();project=root.name
  with connect() as c:
   rows=c.execute('select path,rel from files where project=?',(project,)).fetchall();old_roots=set()
   for row in rows:
    rel=Path(row['rel'] or '')
    if not rel.parts:continue
    old=Path(row['path'])
    for _ in rel.parts:old=old.parent
    if os.path.normcase(str(old))!=os.path.normcase(str(root)):old_roots.add(str(old))
   for old_root in old_roots:
    old_prefix=old_root.rstrip('\\/')+os.sep;prefix=os.path.normcase(old_prefix);old_root_key=os.path.normcase(old_root)
    for favorite in c.execute('select path from favorites where project=?',(project,)).fetchall():
     old_path=str(favorite['path'])
     old_key=os.path.normcase(old_path)
     if old_key==old_root_key or old_key.startswith(prefix):
      new_path=str(root) if old_key==old_root_key else str(root/old_path[len(old_prefix):])
      if c.execute('select 1 from favorites where project=? and path=?',(project,new_path)).fetchone():c.execute('delete from favorites where project=? and path=?',(project,old_path))
      else:c.execute('update favorites set path=? where project=? and path=?',(new_path,project,old_path))
    for change in c.execute('select id,path from file_changes where project=?',(project,)).fetchall():
     old_path=str(change['path'])
     if os.path.normcase(old_path).startswith(prefix):c.execute('update file_changes set path=? where id=?',(str(root/old_path[len(old_prefix):]),change['id']))
    for table in ('file_open_history','activity_log'):
     for item in c.execute(f'select id,path from {table} where project=? and path is not null',(project,)).fetchall():
      old_path=str(item['path']);old_key=os.path.normcase(old_path)
      if old_key==old_root_key or old_key.startswith(prefix):
       new_path=str(root) if old_key==old_root_key else str(root/old_path[len(old_prefix):])
       c.execute(f'update {table} set path=? where id=?',(new_path,item['id']))
   for row in rows:
    old_path=str(row['path']);target=root/Path(row['rel'] or '')
    if not target.is_file() or os.path.normcase(old_path)==os.path.normcase(str(target)):continue
    new_path=str(target);tags=[r['tag'] for r in c.execute('select tag from tags where path=?',(old_path,)).fetchall()]
    c.executemany('insert or ignore into tags(path,tag) values(?,?)',[(new_path,tag) for tag in tags]);c.execute('delete from tags where path=?',(old_path,))
    if c.execute('select 1 from files where path=?',(new_path,)).fetchone():c.execute('delete from files where path=?',(old_path,))
    else:c.execute('update files set path=? where path=?',(new_path,old_path))
    if c.execute('select 1 from favorites where project=? and path=?',(project,new_path)).fetchone():c.execute('delete from favorites where project=? and path=?',(project,old_path))
    else:c.execute('update favorites set path=? where project=? and path=?',(new_path,project,old_path))
    c.execute('update file_changes set path=? where project=? and path=?',(new_path,project,old_path))

 def watch_project_worker(self,root,stop):
  if os.name=='nt':
   try:
    kernel=ctypes.windll.kernel32;kernel.FindFirstChangeNotificationW.argtypes=[ctypes.c_wchar_p,ctypes.c_bool,ctypes.c_uint32];kernel.FindFirstChangeNotificationW.restype=ctypes.c_void_p;kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint32];kernel.WaitForSingleObject.restype=ctypes.c_uint32;kernel.FindNextChangeNotification.argtypes=[ctypes.c_void_p];kernel.FindNextChangeNotification.restype=ctypes.c_bool;kernel.FindCloseChangeNotification.argtypes=[ctypes.c_void_p];kernel.FindCloseChangeNotification.restype=ctypes.c_bool;handle=kernel.FindFirstChangeNotificationW(str(root),True,0x00000001|0x00000002|0x00000004|0x00000008|0x00000010)
    if handle and handle!=ctypes.c_void_p(-1).value:
     try:
      while not stop.is_set():
       result=kernel.WaitForSingleObject(handle,500)
       if result==0:
        if self.root==root:threading.Thread(target=self.scan_worker,args=(root,),daemon=True).start()
        if not kernel.FindNextChangeNotification(handle):break
       elif result==0xFFFFFFFF:break
     finally:kernel.FindCloseChangeNotification(handle)
     return
   except Exception:pass
  def signature():
   found=[];stack=[root]
   while stack:
    directory=stack.pop()
    try:
     with os.scandir(directory) as entries:
      for entry in entries:
       if entry.is_dir(follow_symlinks=False) and not entry.name.startswith('.'):
        try:found.append((entry.path,entry.stat(follow_symlinks=False).st_mtime_ns))
        except OSError:pass
        stack.append(Path(entry.path))
     found.append((str(directory),directory.stat().st_mtime_ns))
    except OSError:continue
   return tuple(sorted(found))
  previous=signature()
  while not stop.wait(10):
   current=signature()
   if current!=previous:
    previous=current
    if self.root==root:threading.Thread(target=self.scan_worker,args=(root,),daemon=True).start()

 def build_explorer(self):
  self.clear();h=self.header(self.project);ttk.Button(h,text='← المشاريع',command=self.show_home).pack(side='right',padx=10,pady=12)
  self.explorer_page=tk.Frame(self,bg='#e8edf1');self.explorer_page.pack(fill='both',expand=True,padx=10,pady=9)
  self.query=tk.StringVar();self.mode=getattr(self,'mode','folder');self.project_group=getattr(self,'project_group','الكل');self.local_group='محتويات هذا المجلد';self.preview_photo=None;self.view_mode='files'
  self.explorer_page.grid_rowconfigure(0,weight=1);self.explorer_page.grid_columnconfigure(0,weight=0,minsize=350);self.explorer_page.grid_columnconfigure(1,weight=1);self.explorer_page.grid_columnconfigure(2,weight=0,minsize=176)
  # RTL workspace: preview at far left, file list in the center, project navigation at far right.
  self.preview_area=tk.Frame(self.explorer_page,bg='#eef2f5',highlightbackground='#d6e0e6',highlightthickness=1,width=350);self.preview_area.grid(row=0,column=0,sticky='nsew',padx=(0,8));self.preview_area.grid_propagate(False);self.preview_area.grid_rowconfigure(1,weight=1);self.preview_area.grid_columnconfigure(0,weight=1)
  preview_head=tk.Frame(self.preview_area,bg='#dfe7ec');preview_head.grid(row=0,column=0,sticky='ew')
  tk.Label(preview_head,text='معاينة وتفاصيل',bg='#dfe7ec',fg='#19394e',font=('Segoe UI',11,'bold')).pack(side='right',padx=13,pady=10)
  self.preview_panel_close=ttk.Button(preview_head,text='×',width=3,command=self.toggle_preview_panel);self.preview_panel_close.pack(side='left',padx=5,pady=4)
  self.preview_image=tk.Canvas(self.preview_area,bg='#eef2f5',highlightthickness=0);self.preview_image.grid(row=1,column=0,sticky='nsew',padx=7,pady=7);self.preview_image.bind('<ButtonPress-1>',self.preview_pan_start);self.preview_image.bind('<B1-Motion>',self.preview_pan_move);self.preview_image.bind('<MouseWheel>',self.preview_wheel)
  self.preview_meta=tk.Label(self.preview_area,text='اختر ملفًا لعرض المعاينة والتفاصيل.\n\nانقر مرة للمعاينة، وانقر مرتين لفتح الملف.',bg='white',fg='#526b7c',font=('Segoe UI',9),justify='right',anchor='ne',wraplength=330);self.preview_meta.grid(row=2,column=0,sticky='ew',padx=12,pady=(0,8))
  self.preview_related_strip=tk.Frame(self.preview_area,bg='#edf2f5');self.preview_related_strip.grid(row=3,column=0,sticky='ew',padx=8,pady=(0,4));self.preview_related_strip.grid_remove()
  controls=tk.Frame(self.preview_area,bg='white');controls.grid(row=4,column=0,sticky='ew',padx=8,pady=(0,8))
  ttk.Button(controls,text='−',width=3,command=lambda:self.zoom_preview(-.15)).pack(side='left');ttk.Button(controls,text='＋',width=3,command=lambda:self.zoom_preview(.15)).pack(side='left');ttk.Button(controls,text='◀ صفحة',command=lambda:self.change_pdf_page(-1)).pack(side='right',padx=2);ttk.Button(controls,text='صفحة ▶',command=lambda:self.change_pdf_page(1)).pack(side='right',padx=2);ttk.Button(controls,text='ملفات مرتبطة',command=self.open_related_from_preview).pack(side='right',padx=3)
  # Main file workspace.
  self.center=tk.Frame(self.explorer_page,bg='#e8edf1');self.center.grid(row=0,column=1,sticky='nsew');self.center.grid_rowconfigure(5,weight=1);self.center.grid_columnconfigure(0,weight=1)
  self.project_tabs_bar=tk.Frame(self.center,bg='#e8edf1');self.project_nb=ttk.Notebook(self.project_tabs_bar);self.project_nb.bind('<<NotebookTabChanged>>',self.project_tab_changed)
  self.filter_bar=tk.Frame(self.center,bg='#e8edf1');self.filter_bar.grid(row=1,column=0,sticky='ew',pady=(0,1));self.filter_context=tk.Label(self.filter_bar,text='المشروع بالكامل',bg='#e8edf1',fg='#526a7a',font=('Segoe UI',9,'bold'));self.filter_context.pack(side='right',padx=8);tk.Label(self.filter_bar,text='أنواع ملفات المشروع',bg='#e8edf1',fg='#526a7a',font=('Segoe UI',9,'bold')).pack(side='right',padx=(4,2));self.project_filter_canvas=tk.Canvas(self.filter_bar,bg='#e8edf1',height=40,highlightthickness=0);self.project_filter_canvas.pack(side='left',fill='x',expand=True);self.type_filter_controls=tk.Frame(self.project_filter_canvas,bg='#e8edf1');self.project_filter_window=self.project_filter_canvas.create_window((0,0),window=self.type_filter_controls,anchor='nw');self.type_filter_controls.bind('<Configure>',lambda e:self.project_filter_canvas.configure(scrollregion=self.project_filter_canvas.bbox('all')));self.project_filter_canvas.bind('<MouseWheel>',lambda e:self.project_filter_canvas.xview_scroll(int(-e.delta/120),'units'));self.project_filter_canvas.bind('<Shift-MouseWheel>',lambda e:self.project_filter_canvas.xview_scroll(int(-e.delta/120),'units'))
  self.folder_filter_bar=tk.Frame(self.center,bg='#e8edf1');self.folder_filter_bar.grid(row=2,column=0,sticky='ew',pady=(0,2));self.folder_filter_context=tk.Label(self.folder_filter_bar,text='المجلد الحالي',bg='#e8edf1',fg='#526a7a',font=('Segoe UI',9,'bold'));self.folder_filter_context.pack(side='right',padx=8);self.folder_menu_var=tk.StringVar(value='الكل');self.folder_menu_items={};self.folder_type_menu=tk.Menu(self.folder_filter_bar,tearoff=0,bg='#ffffff',fg='#19394e',activebackground='#dcebed',activeforeground='#19394e',font=('Segoe UI',9),borderwidth=1,relief='solid');self.folder_type_button=ttk.Menubutton(self.folder_filter_bar,textvariable=self.folder_menu_var,menu=self.folder_type_menu,style='Office.TMenubutton',direction='above');self.folder_type_button.pack(side='left',padx=5);self.folder_type_filter_controls=None
  bar=tk.Frame(self.center,bg='white',highlightbackground='#d6e0e6',highlightthickness=1);bar.grid(row=3,column=0,sticky='ew',pady=(5,5));ttk.Button(bar,text='←',command=self.go_back,width=4).pack(side='left',padx=(4,2),pady=4);ttk.Button(bar,text='→',command=self.go_forward,width=4).pack(side='left',padx=2,pady=4);ttk.Button(bar,text='↑',command=self.go_up,width=4).pack(side='left',padx=2,pady=4);ttk.Button(bar,text='↻',command=self.rescan,width=4).pack(side='left',padx=2,pady=4)
  self.breadcrumb=tk.StringVar();tk.Label(bar,textvariable=self.breadcrumb,bg='white',fg='#087e8b',font=('Segoe UI',10,'bold'),anchor='e').pack(side='right',fill='x',expand=True,padx=10)
  actions=tk.Frame(self.center,bg='#e8edf1');actions.grid(row=4,column=0,sticky='ew',pady=(0,5))
  self.search_button=tk.Button(actions,text='⌕  بحث في المشروع',command=self.show_search_page,bg='#102c3d',fg='white',activebackground='#1b455c',activeforeground='white',relief='flat',font=('Segoe UI',9,'bold'),padx=10,pady=7,cursor='hand2');self.search_button.pack(side='right',padx=(3,0));self.preview_toggle_button=ttk.Button(actions,text='◧  إظهار المعاينة',command=self.toggle_preview_panel)
  ttk.Button(actions,text='تخصيص المجلد',command=self.edit_folder_specialties).pack(side='left',padx=2);ttk.Button(actions,text='هاشتج الملف',command=self.edit_tags).pack(side='left',padx=2)
  tk.Label(actions,text='فلتر الهاشتاج',bg='#e8edf1',fg='#435b6d',font=('Segoe UI',9)).pack(side='left',padx=(7,2));self.tag_filter_var=tk.StringVar(value='الكل');self.tag_filter_box=ttk.Combobox(actions,textvariable=self.tag_filter_var,values=('الكل',),state='readonly',width=16,justify='right',style='Office.TCombobox');self.tag_filter_box.pack(side='left');self.tag_filter_box.bind('<<ComboboxSelected>>',self.tag_filter_changed);self.tag_manager_button=ttk.Button(actions,text='⚙',width=3,command=self.manage_file_tags);self.tag_manager_button.pack(side='left',padx=(3,2));self.tag_manager_button.configure(cursor='hand2')
  self.collection_button=ttk.Button(actions,text='عرض الملفات',command=self.show_files_collection)
  self.file_list_frame=tk.Frame(self.center,bg='#e8edf1');self.file_list_frame.grid(row=5,column=0,sticky='nsew');self.file_list_frame.grid_rowconfigure(0,weight=1);self.file_list_frame.grid_columnconfigure(0,weight=1)
  self.file_tree=self.make_list(self.file_list_frame);self.file_tree.grid(row=0,column=0,sticky='nsew')
  self.file_tree_ybar=ttk.Scrollbar(self.file_list_frame,orient='vertical',command=self.file_tree.yview);self.file_tree_ybar.grid(row=0,column=1,sticky='ns');self.file_tree_xbar=ttk.Scrollbar(self.file_list_frame,orient='horizontal',command=self.file_tree.xview);self.file_tree_xbar.grid(row=1,column=0,sticky='ew');self.file_tree.configure(yscrollcommand=self.file_tree_ybar.set,xscrollcommand=self.file_tree_xbar.set)
  self.selection_bar,self.selection_label=self.make_selection_bar(self.center);self.selection_bar.grid(row=6,column=0,sticky='ew',pady=(4,0));self.selection_bar.grid_remove()
  self.status=tk.StringVar(value='جاهز');tk.Label(self.center,textvariable=self.status,anchor='e',bg='#dfe7ec',fg='#147b87',font=('Segoe UI',9,'bold')).grid(row=7,column=0,sticky='ew',pady=(4,0));self.scan_progress=ttk.Progressbar(self.center,mode='indeterminate',length=180);self.scan_progress.grid(row=8,column=0,sticky='ew',pady=(2,0));self.scan_progress.grid_remove();self.scan_summary=tk.StringVar(value='');tk.Label(self.center,textvariable=self.scan_summary,anchor='e',bg='#e8edf1',fg='#617789',font=('Segoe UI',8)).grid(row=9,column=0,sticky='ew',pady=(1,0))
  # Right navigation rail: project-wide destinations are separate from current-folder type filters.
  rail=tk.Frame(self.explorer_page,bg='#102c3d',width=188);rail.grid(row=0,column=2,sticky='nsew',padx=(0,8));rail.grid_propagate(False)
  tk.Label(rail,text='مساحة المشروع',bg='#102c3d',fg='#a9c3d0',font=('Segoe UI',9,'bold')).pack(anchor='e',padx=15,pady=(17,3))
  tk.Label(rail,text=self.project,bg='#102c3d',fg='white',font=('Segoe UI',12,'bold'),anchor='e',wraplength=175).pack(anchor='e',fill='x',padx=15,pady=(0,14))
  self.rail_nav_buttons={}
  def rail_button(label,command,active=False,key=None):
   key=key or label;b=tk.Button(rail,text=label,command=command,anchor='e',bg='#1b4053' if active else '#102c3d',fg='white' if active else '#d3e2e9',activebackground='#24546a',activeforeground='white',relief='flat',font=('Segoe UI',9,'bold' if active else 'normal'),padx=14,pady=8,cursor='hand2',borderwidth=0);b.pack(fill='x',padx=7,pady=1);self.rail_nav_buttons[key]=b;return b
  tk.Label(rail,text='التصفح',bg='#102c3d',fg='#83a8b9',font=('Segoe UI',8,'bold')).pack(anchor='e',padx=15,pady=(2,4))
  rail_button('▦  ملفات المجلدات',self.show_folder_mode,active=self.mode=='folder',key='folder');rail_button('◈  ملفات المشروع',lambda:self.select_project_scope(),active=self.mode=='project',key='project')
  tk.Label(rail,text='الوصول السريع',bg='#102c3d',fg='#83a8b9',font=('Segoe UI',8,'bold')).pack(anchor='e',padx=15,pady=(15,4))
  rail_button('★  المفضلة',lambda:self.show_collection('favorites'),key='favorites');rail_button('◷  آخر ما فتحته',lambda:self.show_collection('opened'),key='opened');rail_button('＋  أضيف حديثًا',lambda:self.show_collection('added'),key='added');rail_button('↻  سجل التغييرات',lambda:self.show_collection('changes'),key='changes')
  tk.Label(rail,text='التخصصات',bg='#102c3d',fg='#83a8b9',font=('Segoe UI',9,'bold')).pack(anchor='e',padx=15,pady=(17,4))
  self.rail_tags=tk.Frame(rail,bg='#102c3d');self.rail_tags.pack(fill='x');self.refresh_tag_filters()
  tk.Frame(rail,bg='#23485b',height=1).pack(fill='x',padx=12,pady=12)
  rail_button('▱  فتح مجلد المشروع',lambda:os.startfile(str(self.root)),key='open_root')
  self.bind('<Control-f>',lambda e:(self.show_search_page(),'break'));self.bind('<Alt-Left>',lambda e:(self.go_back(),'break'));self.bind('<Alt-Up>',lambda e:(self.go_up(),'break'));self.bind('<F5>',lambda e:(self.rescan(),'break'));self.bind('<Control-o>',lambda e:(self.activate(self.file_tree),'break'));self.bind('<Control-a>',lambda e:(self.select_all_visible(),'break'));self.bind('<Escape>',lambda e:(self.show_files_collection() if self.view_mode!='files' else None,'break'))
  self.rebuild_project_tabs();self.rebuild_folder_tabs();self.refresh_directory()

 def toggle_preview_panel(self):
  searching=hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped()
  area=self.search_preview_area if searching else self.preview_area
  page=self.search_page if searching else self.explorer_page
  button=self.search_preview_toggle if searching else self.preview_toggle_button
  visible=area.winfo_manager()!=''
  if visible:
   area.grid_remove();page.grid_columnconfigure(0,minsize=0,weight=0);button.configure(text='◧  إظهار المعاينة');button.pack(side='right',padx=(3,0)) if not searching else None
  else:
   area.grid();page.grid_columnconfigure(0,minsize=350,weight=0);button.configure(text='◧  إخفاء المعاينة');button.pack_forget() if not searching else None
  self.after_idle(lambda:self.paint_preview() if getattr(self,'preview_base',None) and not searching else None)

 def make_selection_bar(self,parent):
  bar=tk.Frame(parent,bg='#e4f2f3',highlightbackground='#c6e2e4',highlightthickness=1)
  label=tk.Label(bar,text='',bg='#e4f2f3',fg='#164b5b',font=('Segoe UI',9,'bold'));label.pack(side='right',padx=12,pady=8)
  actions=[('🏷 هاشتج الملف',self.edit_tags),('★ المفضلة',self.toggle_favorite),('⧉ نسخ المسارات',lambda:self.copy_selected_paths()),('× مسح الهاشتاجات',lambda:self.clear_selected_tags(self.current_selection_tree()))]
  for text,command in actions:tk.Button(bar,text=text,command=command,bg='white',fg='#28465a',activebackground='#d5ebed',relief='flat',font=('Segoe UI',8,'bold'),padx=9,pady=5,cursor='hand2').pack(side='right',padx=3,pady=4)
  return bar,label

 def current_selection_tree(self):
  if hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped() and getattr(self,'search_nb',None) and self.search_nb.tabs():return self.search_views.get(self.search_nb.tab(self.search_nb.select(),'text'),getattr(self,'file_tree',None))
  return getattr(self,'file_tree',None)

 def select_project_scope(self):
  if not self.current:return
  self.mode='project';self.view_mode='files';self.collection_button.pack_forget();self.rebuild_folder_tabs(preferred=self.project_group);self.save_view_state();self.populate();self.update_rail_selection()

 def type_color(self,label):
  defaults={'PDF':('#d94f63','#fff0f2'),'Excel':('#299765','#edf8f1'),'لوحات CAD':('#3176c8','#eef5ff'),'Word':('#4379bb','#eef5fc'),'الصور':('#9a5bb4','#f8f0fb'),'الكل':('#526a7a','#e9eef2'),'كل النتائج':('#526a7a','#e9eef2'),'مجلد':('#e8ae43','#fff4d8'),'بدون امتداد':('#647b8a','#eef2f5')}
  if label in defaults:return defaults[label]
  ext='.'+str(label).strip().lstrip('.').lower()
  cache=getattr(self,'extension_color_cache',None)
  if cache is None:self.extension_color_cache={};cache=self.extension_color_cache
  if ext in cache:return cache[ext]
  with connect() as c:row=c.execute('select accent,soft from extension_colors where ext=?',(ext,)).fetchone()
  if row:cache[ext]=(row['accent'],row['soft']);return cache[ext]
  used={accent.lower() for accent,soft_color in defaults.values()}
  with connect() as c:used.update(r[0].lower() for r in c.execute('select accent from extension_colors'))
  candidates=[]
  for hue in range(360):
   for saturation,value in ((.72,.78),(.60,.67)):
    red,green,blue=colorsys.hsv_to_rgb(hue/360,saturation,value);accent='#{:02x}{:02x}{:02x}'.format(round(red*255),round(green*255),round(blue*255))
    if accent.lower() not in used:candidates.append(accent)
  accent=secrets.choice(candidates) if candidates else '#526a7a';rgb=tuple(int(accent[i:i+2],16) for i in (1,3,5));soft='#{:02x}{:02x}{:02x}'.format(*(round(channel*.13+255*.87) for channel in rgb))
  with connect() as c:
   c.execute('insert or ignore into extension_colors(ext,accent,soft) values(?,?,?)',(ext,accent,soft));row=c.execute('select accent,soft from extension_colors where ext=?',(ext,)).fetchone()
  cache[ext]=(row['accent'],row['soft']);return cache[ext]

 def type_icon_path(self,label):
  return {'لوحات CAD':'sample.dwg','PDF':'sample.pdf','Excel':'sample.xlsx','Word':'sample.docx','الصور':'sample.png','الكل':'','كل النتائج':'','بدون امتداد':''}.get(label,'sample.'+str(label).strip().lstrip('.').lower())

 def file_type_color(self,path):
  return self.type_color(classify(Path(path).suffix.lower()))

 def make_filter_pill(self,controls,label,count,selected,command):
  accent,soft=self.type_color(label);font=tkfont.Font(family='Segoe UI',size=9,weight='bold' if selected else 'normal');caption=str(label);count_text=f'{count:,}';bubble_width=max(27,tkfont.Font(family='Segoe UI',size=8,weight='bold').measure(count_text)+14);width=max(94,font.measure(caption)+bubble_width+58);pill=tk.Canvas(controls,width=width,height=42,bg='#e8edf1',highlightthickness=0,cursor='hand2')
  fill=soft if selected else '#ffffff';outline=accent if selected else '#d8e1e6';pill.create_polygon(3,21,3,15,5,9,10,5,width-10,5,width-5,9,width-3,15,width-3,27,width-5,33,width-10,37,10,37,5,33,3,27,fill=fill,outline=outline,smooth=True,width=2 if selected else 1,tags=('pill',))
  pill.create_oval(width-bubble_width-8,8,width-8,34,fill=accent,outline=accent,tags=('pill',));pill.create_text(width-bubble_width/2-8,21,text=count_text,fill='white',font=('Segoe UI',8,'bold'),tags=('pill',))
  icon=self.file_icon_image(self.type_icon_path(label));pill._tab_icon=icon;pill.create_image(19,21,image=icon,tags=('pill',));pill.create_text(38,21,text=caption,anchor='w',fill='#263f50',font=font,tags=('pill',))
  pill.tag_bind('pill','<Button-1>',lambda e:command());pill.bind('<MouseWheel>',lambda e:controls.master.xview_scroll(int(-e.delta/120),'units'));pill.pack(side='left',padx=4,pady=2)

 def set_discipline(self,value):
  if hasattr(self,'discipline_var'):
   self.discipline_var.set(value);self.discipline_changed()

 def file_icon_image(self,path,is_dir=False):
  cache=getattr(self,'file_icon_images',None)
  if cache is None:self.file_icon_images={};cache=self.file_icon_images
  ext=Path(path).suffix.lower();group=classify(ext) if not is_dir else 'مجلد';key='folder' if is_dir else (group if group in ('لوحات CAD','PDF','Excel','Word','الصور') else 'ext:'+ext)
  if key in cache:return cache[key]
  accent,soft=self.type_color('مجلد' if is_dir else (group if group in ('لوحات CAD','PDF','Excel','Word','الصور','بدون امتداد') else ext[1:].upper()));im=Image.new('RGBA',(32,32),(0,0,0,0));d=ImageDraw.Draw(im)
  if is_dir:
   d.rounded_rectangle((2,8,30,28),radius=5,fill=accent);d.rounded_rectangle((4,4,16,12),radius=3,fill=accent);d.rounded_rectangle((5,12,27,25),radius=3,fill='#fff7e5')
  else:
   d.rounded_rectangle((4,2,28,30),radius=4,fill=soft,outline=accent,width=2);d.polygon((20,2,28,10,20,10),fill=accent)
   label={'PDF':'PDF','Excel':'XLS','Word':'DOC','لوحات CAD':'CAD','الصور':'IMG'}.get(group,(ext[1:].upper()[:4] if ext else 'FILE'))
   d.rounded_rectangle((4,17,28,29),radius=3,fill=accent);font=self._font(7,True);bbox=d.textbbox((0,0),label,font=font);d.text(((32-(bbox[2]-bbox[0]))/2,18),label,font=font,fill='white')
  photo=ImageTk.PhotoImage(im);cache[key]=photo;return photo

 def file_row_tag(self,path,is_dir=False):
  if is_dir:return 'file_folder'
  ext=Path(path).suffix.lower();group=classify(ext);known={'PDF':'file_pdf','Excel':'file_excel','Word':'file_word','لوحات CAD':'file_cad','الصور':'file_image'}
  return known.get(group,'file_ext_'+hashlib.sha1(ext.encode('utf-8')).hexdigest()[:12])

 def make_list(self,parent):
  t=ttk.Treeview(parent,columns=('name','mark','type','size','mtime','opened','tags','path'),show='tree headings',selectmode='extended')
  # Keep the type icon (#0) directly beside the filename; the multi-select mark follows the name.
  t.heading('#0',text='');t.column('#0',width=44,minwidth=44,stretch=False,anchor='center');t.heading('mark',text='');t.column('mark',width=32,minwidth=32,stretch=False,anchor='center')
  for col,title,w in [('name','اسم الملف',170),('type','النوع',58),('size','الحجم',64),('mtime','تاريخ الملف',88),('opened','آخر فتح',88),('tags','الهاشتاجات',100),('path','المسار داخل المشروع',185)]:t.heading(col,text=title,command=lambda c=col:self.sort_by(c));t.column(col,width=min(getattr(self,'column_widths',{}).get(col,w),w),minwidth=52 if col not in ('name','path') else 100,stretch=(col=='name'),anchor='w' if col=='name' else 'e')
  t.bind('<<TreeviewSelect>>',lambda e,tree=t:self.on_tree_selection(tree));t.bind('<Button-1>',lambda e,tree=t:self.toggle_row_mark(e,tree),add='+');t.bind('<Configure>',lambda e,tree=t:self.remember_column_widths(tree),add='+');t.bind('<Double-1>',lambda e,tree=t:self.activate(tree));t.bind('<Button-3>',lambda e,tree=t:self.context_menu(e,tree));t.bind('<Return>',lambda e,tree=t:(self.activate(tree),'break'));return t

 def on_tree_selection(self,tree):
  self.sync_selection_marks(tree);self.preview_selected(tree);self.update_selection_status(tree)

 def sync_selection_marks(self,tree):
  selected=set(tree.selection())
  for item in tree.get_children():
   values=list(tree.item(item,'values'))
   if len(values)<2:continue
   mark='☑' if item in selected else '☐'
   if values[1]!=mark:values[1]=mark;tree.item(item,values=values)

 def toggle_row_mark(self,event,tree):
  if tree.identify_column(event.x)!='#2':return
  row=tree.identify_row(event.y)
  if not row:return 'break'
  if row in tree.selection():tree.selection_remove(row)
  else:tree.selection_add(row);tree.focus(row)
  self.sync_selection_marks(tree)
  self.update_selection_status(tree);return 'break'

 def rebuild_project_tabs(self):
  if not hasattr(self,'project_nb') or not self.current:return
  for tab in self.project_nb.tabs():self.project_nb.forget(tab)
  self.project_nb.add(tk.Frame(self.project_nb,bg='#e8edf1'),text='تصفح المجلدات')
  self.project_nb.add(tk.Frame(self.project_nb,bg='#e8edf1'),text='المشروع بالكامل')
  target='تصفح المجلدات' if self.mode=='folder' else 'المشروع بالكامل'
  self.project_nb.select(next(t for t in self.project_nb.tabs() if self.project_nb.tab(t,'text')==target))

 def rebuild_folder_tabs(self,preferred=None):
  if not hasattr(self,'type_filter_controls') or not self.current:return
  if preferred is not None:
   if self.mode=='folder':self.folder_group=preferred
   else:self.project_group=preferred
  old_project_types=set(getattr(self,'project_type_labels',set()))
  for w in self.type_filter_controls.winfo_children():w.destroy()
  with connect() as c:rows=c.execute('select rel,ext from files where project=?',(self.project,)).fetchall()
  folder_rel='' if self.current.resolve()==self.root.resolve() else self.current.relative_to(self.root).as_posix().rstrip('/')+'/';local_rows=[r for r in rows if r['rel'].startswith(folder_rel)]
  def type_counts(source):
   counts={}
   for row in source:
    kind=classify(row['ext'] or '');counts[kind]=counts.get(kind,0)+1
   return counts
  project_counts=type_counts(rows);folder_counts=type_counts(local_rows);order=lambda x:(x not in ('لوحات CAD','PDF','Excel','Word','الصور'),x.casefold())
  self.filter_context.configure(text=f'{len(rows):,} ملف');self.folder_filter_context.configure(text=f'داخل «{self.current.name or self.project}» · {len(local_rows):,} ملف')
  if self.project_group not in ['الكل',*project_counts]:self.project_group='الكل'
  if self.folder_group not in ['الكل',*folder_counts]:self.folder_group='الكل'
  current_project_types=set(project_counts)
  for label in ['الكل']+sorted(project_counts,key=order):
   count=sum(project_counts.values()) if label=='الكل' else project_counts[label]
   self.make_filter_pill(self.type_filter_controls,label,count,self.mode=='project' and label==self.project_group,lambda value=label:self.type_filter_changed('project',value))
   # Keep the project-wide type pills anchored at the beginning when a new extension appears.
   # Auto-scrolling to the end hid the common PDF / Excel / CAD filters on large projects.
  self.project_type_labels=current_project_types
  self.folder_menu_items={}
  self.folder_type_menu.delete(0,'end')
  for label in ['الكل']+sorted(folder_counts,key=order):
   count=sum(folder_counts.values()) if label=='الكل' else folder_counts[label]
   display=f'{label}  ·  {count:,}'
   self.folder_menu_items[display]=label
   self.folder_type_menu.add_command(label=display,command=lambda value=label:self.type_filter_changed('folder',value))
  selected=next((display for display,label in self.folder_menu_items.items() if label==self.folder_group),next(iter(self.folder_menu_items),'الكل'))
  self.folder_menu_var.set(selected)
  self.refresh_tag_filters()

 def scroll_project_filter_to_end(self):
  canvas=getattr(self,'project_filter_canvas',None)
  if not canvas or not canvas.winfo_exists():return
  target=1.0;start=canvas.xview()[0] if canvas.xview() else 0.0
  def step(i):
   if not canvas.winfo_exists():return
   value=start+(target-start)*i/7;canvas.xview_moveto(value)
   if i<7:canvas.after(18,lambda:step(i+1))
  step(1)

 def project_tab_changed(self,e=None):
  if not getattr(self,'project_nb',None) or not self.project_nb.tabs():return
  tab=self.project_nb.tab(self.project_nb.select(),'text')
  new_mode='folder' if tab=='تصفح المجلدات' else 'project'
  if self.mode==new_mode:return
  self.mode=new_mode;self.view_mode='files';self.collection_button.pack_forget()
  self.save_view_state();self.rebuild_folder_tabs();self.populate();self.update_rail_selection()
  self.log_activity('تغيير نطاق العرض','عرض '+('ملفات المجلد' if new_mode=='folder' else 'كل ملفات المشروع'),path=self.current)

 def type_filter_changed(self,scope,selected):
  self.view_mode='files';self.collection_button.pack_forget();self.mode=scope
  if hasattr(self,'project_nb'):
   target='تصفح المجلدات' if scope=='folder' else 'المشروع بالكامل'
   for tab in self.project_nb.tabs():
    if self.project_nb.tab(tab,'text')==target:self.project_nb.select(tab);break
  if scope=='folder':self.folder_group=selected
  else:self.project_group=selected
  self.rebuild_folder_tabs();self.save_view_state();self.populate();self.update_rail_selection()
  self.log_activity('تغيير فلتر النوع',f'{"المجلد الحالي" if scope=="folder" else "المشروع بالكامل"} · {selected}',path=self.current)

 def discipline_changed(self,e=None):
  self.save_view_state();self.populate()
  if hasattr(self,'discipline_var'):self.log_activity('تغيير فلتر التخصص',f'تصفية حسب {self.discipline_var.get()}',path=self.current)

 def sort_by(self,col):
  if getattr(self,'view_mode','files')=='opened':
   if getattr(self,'opened_sort_col','opened')==col:self.opened_sort_desc=not getattr(self,'opened_sort_desc',True)
   else:self.opened_sort_col=col;self.opened_sort_desc=False
   self.populate();self.log_activity('ترتيب الملفات',f'{col} · {"تنازلي" if self.opened_sort_desc else "تصاعدي"}',path=self.current);return
  if getattr(self,'sort_col','name')==col:self.sort_desc=not self.sort_desc
  else:self.sort_col=col;self.sort_desc=False
  self.save_view_state()
  if hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped():self.render_search_results()
  else:self.populate()
  self.log_activity('ترتيب الملفات',f'{col} · {"تنازلي" if self.sort_desc else "تصاعدي"}',path=self.current)

 def remember_column_widths(self,tree):
  if getattr(self,'remember_width_job',None):
   try:self.after_cancel(self.remember_width_job)
   except tk.TclError:pass
  self.remember_width_job=self.after(500,lambda:self._store_widths(tree))

 def _store_widths(self,tree):
  if tree.winfo_exists():self.column_widths={c:tree.column(c,'width') for c in tree['columns']};self.save_view_state()

 def save_view_state(self):
  if not getattr(self,'project',''):return
  try:
   rel=self.current.relative_to(self.root).as_posix() if self.current and self.root else ''
   widths=json.dumps(getattr(self,'column_widths',{}))
   with connect() as c:c.execute('insert into project_view_state(project,current_rel,mode,folder_filter,project_filter,discipline,sort_col,sort_desc,column_widths) values(?,?,?,?,?,?,?,?,?) on conflict(project) do update set current_rel=excluded.current_rel,mode=excluded.mode,folder_filter=excluded.folder_filter,project_filter=excluded.project_filter,discipline=excluded.discipline,sort_col=excluded.sort_col,sort_desc=excluded.sort_desc,column_widths=excluded.column_widths',(self.project,rel,getattr(self,'mode','folder'),getattr(self,'folder_group','الكل'),getattr(self,'project_group','الكل'),getattr(self,'discipline','الكل'),getattr(self,'sort_col','name'),int(getattr(self,'sort_desc',False)),widths))
  except Exception:pass

 def update_selection_status(self,tree):
  selected=set(tree.selection())
  for iid in tree.get_children(''):
   try:tree.set(iid,'mark','☑' if iid in selected else '☐')
   except tk.TclError:pass
  if tree is getattr(self,'file_tree',None) and getattr(self,'view_mode','')=='changes':
   bar=getattr(self,'selection_bar',None)
   if bar and bar.winfo_exists():bar.grid_remove()
   if hasattr(self,'status'):self.status.set(f'{len(tree.get_children()):,} حدث في سجل النشاط')
   return
  n=len(selected)
  if tree is getattr(self,'file_tree',None):
   bar=getattr(self,'selection_bar',None);label=getattr(self,'selection_label',None)
   if hasattr(self,'status') and self.view_mode=='files':self.status.set(f'{len(tree.get_children()):,} عنصر · {n:,} محدد' if n else f'{len(tree.get_children()):,} عنصر')
  else:
   bar=getattr(self,'search_selection_bar',None);label=getattr(self,'search_selection_label',None)
  if bar and bar.winfo_exists():
   if n:
    label.configure(text=f'تم تحديد {n:,} ملف')
    bar.grid()
   else:bar.grid_remove()

 def select_all_visible(self):
  tree=self.current_selection_tree()
  if not tree or not tree.winfo_exists():return
  rows=tree.get_children('')
  if rows:tree.selection_set(rows);tree.focus(rows[0]);self.update_selection_status(tree)

 def show_collection(self,kind):
  self.save_view_state();self.view_mode=kind;self.collection_button.pack(side='right',padx=3);self.populate()
  labels={'favorites':'المفضلة','opened':'آخر ما فتحته','added':'أضيف حديثًا','changes':'سجل التغييرات'}
  label=labels.get(kind,kind);self.breadcrumb.set(f'{self.project}  ›  {label}');self.update_rail_selection();self.log_activity('فتح قسم',label)

 def show_files_collection(self):
  self.view_mode='files';self.collection_button.pack_forget();self.refresh_directory();self.update_rail_selection()

 def toggle_favorite(self,path=None):
  paths=([path] if isinstance(path,(str,Path)) else list(path)) if path else self.selected_paths()
  paths=[Path(p) for p in paths if p]
  if not paths:return messagebox.showinfo('المفضلة','حدد ملفًا أو مجلدًا أولًا.',parent=self)
  added=[];removed=[]
  with connect() as c:
   for p in paths:
    key=str(p.resolve());exists=c.execute('select 1 from favorites where project=? and path=?',(self.project,key)).fetchone()
    if exists:
     c.execute('delete from favorites where project=? and path=?',(self.project,key));removed.append(p)
    else:
     c.execute('insert into favorites(project,path,kind,created) values(?,?,?,?)',(self.project,key,'folder' if p.is_dir() else 'file',stamp(time.time())));added.append(p)
  if added:self.log_activity('إضافة إلى المفضلة','إضافة: '+', '.join(p.name for p in added),path=added[0] if len(added)==1 else None)
  if removed:self.log_activity('إزالة من المفضلة','إزالة: '+', '.join(p.name for p in removed),path=removed[0] if len(removed)==1 else None)
  self.status.set(f'تم تحديث المفضلة لـ {len(paths):,} عنصر')
  if self.view_mode!='files':self.populate()

 def is_favorite(self,path):
  with connect() as c:return c.execute('select 1 from favorites where project=? and path=?',(self.project,str(Path(path).resolve()))).fetchone() is not None

 def show_related_files(self,path):
  searching=hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped()
  if searching:self.hide_search_page()
  p=Path(path)
  try:self.related_parent=p.parent.relative_to(self.root).as_posix()
  except ValueError:return
  self.related_stem=p.stem.casefold();self.view_mode='related';self.collection_button.pack(side='right',padx=3);self.populate();self.breadcrumb.set(f'{self.project}  ›  ملفات اللوحة المرتبطة بـ {p.stem}')

 def open_related_from_preview(self):
  path=getattr(self,'preview_current_path',None)
  if path and Path(path).is_file():self.show_related_files(path)

 def related_file_thumbnail(self,path):
  p=Path(path);image=None;resolved=str(p.resolve())
  for cache_key,(cached,note) in reversed(list(self.preview_cache.items())):
   if isinstance(cache_key,tuple) and cache_key and cache_key[0]==resolved:image=cached.copy();break
  if image is None and p.suffix.lower()=='.dwg':
   try:
    st=p.stat();key=hashlib.sha1(f'{p.resolve()}|{st.st_mtime_ns}|{st.st_size}'.encode('utf-8')).hexdigest();cached_path=LOG/'.preview_cache'/(key+'.png')
    if cached_path.is_file():
     with Image.open(cached_path) as cached:image=cached.convert('RGB').copy()
   except (OSError,ValueError):pass
  if image is None and p.suffix.lower() in ('.png','.jpg','.jpeg','.bmp','.gif','.tif','.tiff'):
   try:
    with Image.open(p) as source:image=source.convert('RGB').copy()
   except (OSError,ValueError):pass
  if image is None:return self.file_icon_image(str(p))
  image=ImageOps.fit(image,(44,30),method=Image.Resampling.BILINEAR);photo=ImageTk.PhotoImage(image);return photo

 def render_related_strip(self,current,paths):
  frame=getattr(self,'preview_related_strip',None)
  if not frame or not frame.winfo_exists():return
  for widget in frame.winfo_children():widget.destroy()
  frame._related_photos=[]
  if not paths:
   frame.grid_remove();return
  frame.grid();tk.Label(frame,text='مرتبط:',bg='#edf2f5',fg='#617789',font=('Segoe UI',8,'bold')).pack(side='right',padx=(3,5))
  for path in paths[:3]:
   photo=self.related_file_thumbnail(path);frame._related_photos.append(photo)
   tk.Button(frame,text=path.name[:15],image=photo,compound='left',command=lambda p=path:self.preview_related_file(p),bg='white',fg='#28465a',activebackground='#dceef0',relief='flat',font=('Segoe UI',8),padx=5,pady=3,cursor='hand2').pack(side='right',padx=2)

 def preview_related_file(self,path):
  p=Path(path)
  if not p.is_file():return
  searching=hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped()
  if searching:self.hide_search_page()
  if self.view_mode!='files' or self.mode!='folder' or self.current.resolve()!=p.parent.resolve():
   self.save_view_state()
   if self.current and self.current.resolve()!=p.parent.resolve():self.backstack.append(self.current)
   self.forwardstack.clear();self.current=p.parent;self.mode='folder';self.folder_group='الكل';self.view_mode='files';self.collection_button.pack_forget();self.refresh_directory();self.animate_window_in()
  iid=str(p.resolve())
  if self.file_tree.exists(iid):self.file_tree.selection_set(iid);self.file_tree.focus(iid);self.file_tree.see(iid)

 def leave_search_for(self,kind,value=None):
  self.hide_search_page()
  if kind=='folder':self.show_folder_mode()
  elif kind=='project':self.select_project_scope()
  elif kind in ('favorites','opened','added','changes'):self.show_collection(kind)
  elif kind=='specialty' and value:self.show_specialty(value)

 def _collection_rows(self):
  with connect() as c:
   if self.view_mode=='specialty':
    rows=c.execute("select path,group_concat(tag, ' ') tags from folder_tags where project=? and tag=? group by path order by path",(self.project,self.specialty_filter)).fetchall();out=[]
    for row in rows:
     rel=row['path'] or '.';p=(self.root/rel).resolve()
     if not p.is_dir():continue
     out.append({'path':str(p.resolve()),'kind':'folder','rel':rel,'name':p.name,'ext':'مجلد','size':0,'mtime':p.stat().st_mtime,'last_open':'','tags':row['tags'] or ''})
    return out
   if self.view_mode=='favorites':
    return c.execute("select v.path,v.kind,f.rel,f.name,f.ext,f.size,f.mtime,f.last_open,group_concat(t.tag,' ') tags from favorites v left join files f on f.path=v.path left join tags t on t.path=f.path where v.project=? group by v.path order by v.created desc",(self.project,)).fetchall()
   if self.view_mode=='opened':
    return c.execute("select f.path,f.project,f.rel,f.name,f.ext,f.size,f.mtime,max(h.opened_at) last_open,f.indexed,group_concat(t.tag,' ') tags from file_open_history h join files f on f.path=h.path and f.project=h.project left join tags t on t.path=f.path where h.project=? group by f.path order by max(h.opened_at) desc,max(h.id) desc limit 500",(self.project,)).fetchall()
   if self.view_mode=='added':
    return c.execute("select f.*,group_concat(t.tag,' ') tags,max(a.occurred_at) added_at from activity_log a join files f on f.path=a.path and f.project=a.project left join tags t on t.path=f.path where a.project=? and a.action='إضافة ملف' and a.occurred_at>=? group by f.path order by max(a.id) desc limit 500",(self.project,stamp(time.time()-30*86400))).fetchall()
   if self.view_mode=='changes':
    return c.execute("select id,project,action,details,path,occurred_at from activity_log where project=? order by id desc limit 2000",(self.project,)).fetchall()
   if self.view_mode=='related' and getattr(self,'related_stem',None):
    return [r for r in c.execute("select f.*,group_concat(t.tag,' ') tags from files f left join tags t on t.path=f.path where f.project=? and f.ext in ('.dwg','.pdf','.dxf','.png','.jpg','.jpeg') group by f.path",(self.project,)).fetchall() if Path(r['name']).stem.casefold()==self.related_stem and Path(r['rel']).parent.as_posix()==self.related_parent]
  return []

 def _discipline_match(self,tags):
  selected=getattr(self,'tag_filter_var',None)
  selected=selected.get() if selected else 'الكل'
  return selected=='الكل' or selected.casefold() in (tags or '').casefold().split()

 def refresh_tag_filters(self):
  if not getattr(self,'project',''):return
  try:
   with connect() as c:
    tags=sorted({r[0] for r in c.execute('select tag from file_tag_catalog where project=? union select distinct t.tag from tags t join files f on f.path=t.path where f.project=?',(self.project,self.project))})
   values=['الكل']+tags
   if hasattr(self,'tag_filter_box'):
    current=self.tag_filter_var.get();self.tag_filter_box.configure(values=values)
    if current not in values:self.tag_filter_var.set('الكل')
   self.refresh_specialty_nav()
  except Exception:pass

 def refresh_specialty_nav(self):
  if not hasattr(self,'rail_tags') or not self.rail_tags.winfo_exists():return
  try:
   with connect() as c:tags=[r[0] for r in c.execute('select distinct tag from folder_tags where project=? order by tag',(self.project,))]
   for key in [k for k in self.rail_nav_buttons if k.startswith('specialty:')]:self.rail_nav_buttons.pop(key,None)
   for w in self.rail_tags.winfo_children():w.destroy()
   for tag in tags:
    key='specialty:'+tag
    btn=tk.Button(self.rail_tags,text='●  '+tag,command=lambda t=tag:self.show_specialty(t),anchor='e',bg='#102c3d',fg='#d3e2e9',activebackground='#24546a',relief='flat',font=('Segoe UI',9),padx=14,pady=6,cursor='hand2',borderwidth=0)
    btn.pack(fill='x',padx=7,pady=1);self.rail_nav_buttons[key]=btn
   self.update_rail_selection()
  except Exception:pass

 def update_rail_selection(self):
  buttons=getattr(self,'rail_nav_buttons',{})
  if not buttons:return
  if self.view_mode=='specialty':active='specialty:'+getattr(self,'specialty_filter','')
  elif self.view_mode in ('favorites','opened','added','changes'):active=self.view_mode
  else:active='folder' if self.mode=='folder' else 'project'
  previous=getattr(self,'_nav_active_key',None);self._nav_active_key=active
  if getattr(self,'_nav_animation_job',None):
   try:self.after_cancel(self._nav_animation_job)
   except tk.TclError:pass
  starts={}
  for key,button in list(buttons.items()):
   try:starts[key]=button.cget('bg')
   except tk.TclError:continue
  def color(key,step):
   target='#1b5268' if key==active else '#102c3d';source=starts.get(key,target)
   if previous==active:return target
   try:
    a=tuple(int(source[i:i+2],16) for i in (1,3,5));b=tuple(int(target[i:i+2],16) for i in (1,3,5));v=step/5
    return '#'+''.join(f'{round(x+(y-x)*v):02x}' for x,y in zip(a,b))
   except Exception:return target
  def animate(step):
   for key,button in list(buttons.items()):
    try:
     selected=key==active;button.configure(bg=color(key,step),fg='white' if selected else '#d3e2e9',font=('Segoe UI',9,'bold' if selected else 'normal'))
    except tk.TclError:pass
   if step<5:self._nav_animation_job=self.after(18,lambda:animate(step+1))
   else:self._nav_animation_job=None
  animate(1 if previous!=active else 5)

 def show_specialty(self,tag):
  self.view_mode='specialty';self.specialty_filter=tag;self.collection_button.pack(side='right',padx=3);self.populate();self.breadcrumb.set(f'{self.project}  ›  التخصصات  ›  {tag}');self.update_rail_selection();self.log_activity('عرض تخصص',tag)

 def apply_tag_filter(self,value):
  if hasattr(self,'tag_filter_var'):self.tag_filter_var.set(value);self.populate()

 def tag_filter_changed(self,e=None):
  self.populate()
  value=self.tag_filter_var.get() if hasattr(self,'tag_filter_var') else 'الكل'
  self.log_activity('تغيير فلتر الهاشتاج',value,path=self.current)

 def indexed_folder_size(self,path,size_map=None):
  p=Path(path)
  try:rel=p.relative_to(self.root).as_posix().rstrip('/')
  except (ValueError,TypeError):return 0
  if size_map and rel in size_map:return size_map[rel]
  cached=getattr(self,'_folder_size_cache',None)
  if not cached or cached[0]!=self.project:
   sizes={}
   with connect() as c:rows=c.execute('select rel,size from files where project=?',(self.project,)).fetchall()
   for row in rows:
    prefix=''
    for part in (row['rel'] or '').split('/')[:-1]:
     prefix=f'{prefix}/{part}' if prefix else part;sizes[prefix]=sizes.get(prefix,0)+(row['size'] or 0)
   self._folder_size_cache=(self.project,sizes)
  return self._folder_size_cache[1].get(rel,0)

 def refresh_directory(self):
  if not self.current:return
  try:self.breadcrumb.set(self.project if self.current==self.root else self.current.relative_to(self.root).as_posix())
  except ValueError:self.breadcrumb.set(str(self.current))
  self.view_mode='files';self.collection_button.pack_forget()
  preferred=self.project_group if self.mode=='project' else self.folder_group
  self.rebuild_folder_tabs(preferred=preferred)
  if hasattr(self,'project_nb'):
   for tab in self.project_nb.tabs():
    if self.project_nb.tab(tab,'text')==('تصفح المجلدات' if self.mode=='folder' else 'المشروع بالكامل'):self.project_nb.select(tab);break
  self.save_view_state();self.populate();self.update_rail_selection()

 def show_folder_mode(self,from_tab=False):
  self.mode='folder';self.view_mode='files';self.folder_group='الكل';self.collection_button.pack_forget();self.rebuild_folder_tabs(preferred='الكل')
  if not from_tab and hasattr(self,'project_nb'):
   for tab in self.project_nb.tabs():
    if self.project_nb.tab(tab,'text')=='تصفح المجلدات':self.project_nb.select(tab);break
  self.populate();self.update_rail_selection()

 def close_app(self):
  try:
   for job in self.tk.call('after','info'):self.after_cancel(job)
  except tk.TclError:pass
  self._poll_after_id=None
  if hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped():
   if getattr(self,'search_history_job',None):
    try:self.after_cancel(self.search_history_job)
    except tk.TclError:pass
   self.record_search_history();self.save_search_state()
  self.save_view_state()
  self.watch_stop.set()
  for hwnd in self.everything_windows.values():ctypes.windll.user32.PostMessageW(hwnd,0x0010,0,0)
  self.search_serial+=1
  self.stop_everything_instance()
  try:self.preview_executor.shutdown(wait=False,cancel_futures=True);self.cad_preview_executor.shutdown(wait=False,cancel_futures=True);self.search_executor.shutdown(wait=False,cancel_futures=True)
  except Exception:pass
  proc=getattr(self,'cad_preview_process',None)
  if proc and proc.poll() is None:
   try:proc.kill()
   except OSError:pass
  self.destroy()

 def stop_everything_instance(self):
  exe=getattr(self,'everything_exe',None);instance=getattr(self,'everything_instance',None);data=getattr(self,'everything_data',None)
  if exe and instance and data and Path(exe).exists():
   try:subprocess.Popen([str(exe),'-instance',instance,'-exit'],cwd=str(data),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
   except OSError:pass
  self.everything_proc=None;self.everything_key=None;self.everything_instance=None;self.everything_data=None;self.everything_exe=None;self.everything_cli=None;self.everything_root=None

 def hide_search_page(self):
  self.preview_token+=1;self.search_serial+=1
  self.save_search_state()
  self.stop_everything_instance()
  if hasattr(self,'search_page'):self.search_page.destroy()
  self.preview_image,self.preview_meta,self.preview_related_strip=self.active_preview;self.explorer_page.pack(fill='both',expand=True,padx=12,pady=10);self.title('Rasd | مدير ملفات المشاريع');self.populate();self.animate_window_in()

 def start_scan_progress(self):
  bar=getattr(self,'scan_progress',None)
  if not bar or not bar.winfo_exists():return
  try:
   bar.grid();bar.start(12);self._scan_progress_running=True
  except tk.TclError:pass

 def stop_scan_progress(self):
  bar=getattr(self,'scan_progress',None)
  if not bar or not bar.winfo_exists():return
  try:bar.stop();bar.grid_remove();self._scan_progress_running=False
  except tk.TclError:pass

 def poll_queue(self):
  try:
   try:
    while True:
     kind,scan_root,n,extra=self.scanq.get_nowait()
     if self.root and Path(scan_root).resolve()==self.root.resolve():
      if kind=='progress':
       if not getattr(self,'_scan_progress_running',False):self.start_scan_progress()
       self.scan_summary.set(f'جارٍ فهرسة المشروع… تمت قراءة {n:,} ملف');continue
      self.stop_scan_progress()
      self.index_total=n;self.index_errors=extra or 0;self._folder_size_cache=None;self.rebuild_project_tabs();self.rebuild_folder_tabs();self.populate()
      with connect() as c:counts=c.execute("select sum(kind='added') added,sum(kind='modified') modified from file_changes where project=? and changed_at>=?",(self.project,getattr(self,'visit_since','0000'))).fetchone()
      added=counts['added'] or 0;modified=counts['modified'] or 0
      self.scan_summary.set(f'اكتمل الفهرس: {n:,} ملف · جديد {added:,} · معدل {modified:,} · تعذر قراءته {self.index_errors:,}')
      if hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped():self.refresh_search_cache();self.render_search_results()
     if self.root and self.watch_root!=self.root:
      self.watch_root=self.root;threading.Thread(target=self.watch_project_worker,args=(self.root,self.watch_stop),daemon=True).start()
   except queue.Empty:pass
   try:
    while True:
     token,rows,note=self.searchq.get_nowait()
     if token==self.search_serial and hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped():self.render_search_rows(rows,note)
   except queue.Empty:pass
   try:
    while True:
     item=self.previewq.get_nowait()
     try:
      if item[0]=='excel':
       _,token,path,meta,names,sheet_name,rows,start_row,total_rows,has_more,key=item
       if token==self.preview_token and self.winfo_exists():self.render_excel_preview(path,meta,names,sheet_name,rows,start_row,total_rows,has_more,key)
       continue
      if item[0]=='image':
       _,token,image,meta,*extra=item
       key,note=(extra[0],extra[1]) if len(extra)>=2 else (None,None)
      else:
       token,image,meta=item[:3];key,note=(item[3],item[4]) if len(item)>=5 else (None,None)
      if token==self.preview_token and self.winfo_exists():
       cache_error=bool(note and any(word in note for word in ('لم تتوفر','لم يعثر','تعذرت معاينة')) and key and Path(key[0]).suffix.lower()=='.dwg')
       if key is not None and not cache_error:
        self.preview_cache[key]=(image.copy(),note or '');self.preview_cache.move_to_end(key)
        while len(self.preview_cache)>12:self.preview_cache.popitem(last=False)
       self.render_preview(image,meta)
     except Exception as exc:
      try:self.preview_meta.configure(text=f'تعذر عرض المعاينة: {str(exc)[:120]}')
      except (tk.TclError,AttributeError):pass
   except queue.Empty:pass
  finally:
   try:
    if self.winfo_exists():self._poll_after_id=self.after(180,self.poll_queue)
   except tk.TclError:pass
 def scan_worker(self,root):
  with self.scan_lock:
   project=root.name;seen=set();now=stamp(datetime.now().timestamp());rows=[];errors=0;old_by_path={};changes=[]
   def scan_error(exc):
    nonlocal errors
    errors+=1
   with connect() as c:
    old_by_path={r['path']:(r['size'],r['mtime']) for r in c.execute('select path,size,mtime from files where project=?',(project,))}
    scan_state=c.execute('select initial_scan_done from project_scan_state where project=?',(project,)).fetchone()
   first_scan=(scan_state is None and not old_by_path) or (scan_state is not None and not scan_state['initial_scan_done'])
   for d,dirs,files in os.walk(root,onerror=scan_error):
    dirs[:]=[x for x in dirs if not x.startswith('.')]
    for n in files:
     p=Path(d)/n
     try:
      st=p.stat();path=str(p.resolve());r=(path,project,p.relative_to(root).as_posix(),n,p.suffix.lower(),st.st_size,st.st_mtime,None,now);rows.append(r);seen.add(path)
      if path not in old_by_path:
       if not first_scan:changes.append((project,path,'added',now))
      elif old_by_path[path]!=(st.st_size,st.st_mtime):changes.append((project,path,'modified',now))
      if len(rows)%250==0:self.scanq.put(('progress',str(root.resolve()),len(rows),None))
     except OSError:errors+=1
   with connect() as c:
    c.executemany('insert into files values(?,?,?,?,?,?,?,?,?) on conflict(path) do update set project=excluded.project,rel=excluded.rel,name=excluded.name,ext=excluded.ext,size=excluded.size,mtime=excluded.mtime,indexed=excluded.indexed',rows)
    missing=[r['path'] for r in c.execute('select path from files where project=?',(project,)) if r['path'] not in seen]
    # Do not retire indexed files when any part of the tree could not be read.
    old=missing if errors==0 else []
    c.executemany('insert into file_changes(project,path,kind,changed_at) values(?,?,?,?)',changes)
    c.executemany('insert into file_changes(project,path,kind,changed_at) values(?,?,?,?)',[(project,p,'removed',now) for p in old])
    activity_rows=[]
    action_labels={'added':'إضافة ملف','modified':'تعديل ملف','removed':'إزالة ملف من مجلد المشروع'}
    for _,path,kind,changed_at in changes:
     action=action_labels[kind];activity_rows.append((project,action,f'{action}: {Path(path).name}',path,changed_at))
    if errors==0:
     for path in old:activity_rows.append((project,action_labels['removed'],f"{action_labels['removed']}: {Path(path).name}",path,now))
    if activity_rows:c.executemany('insert into activity_log(project,action,details,path,occurred_at) values(?,?,?,?,?)',activity_rows)
    c.execute('insert into project_scan_state(project,initial_scan_done) values(?,1) on conflict(project) do update set initial_scan_done=1',(project,))
    c.executemany('delete from tags where path=?',[(p,) for p in old]);c.executemany('delete from files where path=?',[(p,) for p in old])
   self.scanq.put(('done',str(root.resolve()),len(rows),errors))

 def populate(self):
  if not hasattr(self,'file_tree') or not self.current:return
  self.refresh_tag_filters()
  tree=self.file_tree;tree.delete(*tree.get_children());self.view_mode=getattr(self,'view_mode','files');directory_sizes={}
  if self.view_mode!='files':
   rows=self._collection_rows();data=[];self.activity_rows={}
   for r in rows:
    if self.view_mode=='changes':
     iid=f"activity:{r['id']}";target=r['path']
     if target:
      try:location=Path(target).resolve().relative_to(self.root.resolve()).as_posix()
      except (OSError,ValueError):location=target
     else:location='داخل البرنامج'
     event={'action':r['action'],'details':r['details'],'path':target,'occurred_at':r['occurred_at']};self.activity_rows[iid]=event
     data.append((iid,(r['details'],r['action'],'—','—',r['occurred_at'],'','',location),False));continue
    if not r['path']:continue
    if self.view_mode=='changes' and not r['name']:
     old=Path(r['path']);name=f"[محذوف] {old.name}";data.append((r['path'],(name,old.suffix.lower() or 'ملف','—','—',r['changed_at'] or '—','',old.as_posix()),False));continue
    if not Path(r['path']).exists():continue
    if 'kind' in r.keys() and r['kind']=='folder' and Path(r['path']).is_dir():
     p=Path(r['path']);rel=p.relative_to(self.root).as_posix();data.append((str(p.resolve()),(p.name,'مجلد',sizefmt(self.indexed_folder_size(p,directory_sizes)),stamp(p.stat().st_mtime),'—','',' '+rel),True));continue
    tags=r['tags'] or ''
    if not self._discipline_match(tags):continue
    name=r['name'];opened=r['last_open'] or '—';modified=r['mtime'] or 0
    if self.view_mode=='changes':name=f"[{r['change_kind'] or 'changed'}] {name}";opened=r['changed_at'] or opened
    data.append((r['path'],(name,r['ext'] or 'ملف',sizefmt(r['size'] or 0),stamp(modified),opened,tags,r['rel'] or ''),False))
  else:
   with connect() as c:
    allrows=c.execute("select f.*,group_concat(t.tag, ' ') tags from files f left join tags t on t.path=f.path where f.project=? group by f.path",(self.project,)).fetchall()
    folderrows=c.execute("select path,group_concat(tag, ' ') tags from folder_tags where project=? group by path",(self.project,)).fetchall()
    rowmap={r['path']:r for r in allrows};foldermap={r['path']:r['tags'] or '' for r in folderrows}
   for file_row in allrows:
    parts=(file_row['rel'] or '').split('/')[:-1];prefix=''
    for part in parts:
     prefix=f'{prefix}/{part}' if prefix else part
     directory_sizes[prefix]=directory_sizes.get(prefix,0)+(file_row['size'] or 0)
   data=[]
   if self.mode=='folder':
    try:items=list(self.current.iterdir())
    except OSError:items=[]
    for p in items:
     try:st=p.stat();isdir=p.is_dir()
     except OSError:continue
     rel=p.relative_to(self.root).as_posix();r=rowmap.get(str(p.resolve()))
     tags=(foldermap.get(p.relative_to(self.root).as_posix(), '') if isdir else ((r['tags'] or '') if r else ''));opened=(r['last_open'] or '—') if r else '—'
     if not isdir and self.folder_group!='الكل' and classify(p.suffix.lower())!=self.folder_group:continue
     if not isdir and not self._discipline_match(tags):continue
     data.append((str(p.resolve()),(p.name,('مجلد' if isdir else p.suffix.lower() or 'ملف'),(sizefmt(directory_sizes.get(rel,0)) if isdir else sizefmt(st.st_size)),stamp(st.st_mtime),opened,tags,rel),isdir))
    if self.folder_group!='الكل':
     prefix='' if self.current.resolve()==self.root.resolve() else self.current.relative_to(self.root).as_posix().rstrip('/')+'/'
     data=[]
     for r in allrows:
      if r['rel'].startswith(prefix) and classify(r['ext'] or '')==self.folder_group and self._discipline_match(r['tags']):data.append((r['path'],(r['name'],r['ext'] or 'ملف',sizefmt(r['size']),stamp(r['mtime']),r['last_open'] or '—',r['tags'] or '',r['rel']),False))
   else:
    for r in allrows:
     if self.project_group!='الكل' and classify(r['ext'] or '')!=self.project_group:continue
     if not self._discipline_match(r['tags']):continue
     data.append((r['path'],(r['name'],r['ext'] or 'ملف',sizefmt(r['size']),stamp(r['mtime']),r['last_open'] or '—',r['tags'] or '',r['rel']),False))
  sort_col=self.opened_sort_col if self.view_mode=='opened' else self.sort_col
  sort_desc=self.opened_sort_desc if self.view_mode=='opened' else self.sort_desc
  if sort_col=='name':idx=0;key=lambda x:x[1][idx].casefold()
  elif sort_col=='type':idx=1;key=lambda x:x[1][idx].casefold()
  elif sort_col=='size':key=lambda x:Path(x[0]).stat().st_size if Path(x[0]).is_file() else self.indexed_folder_size(x[0],directory_sizes) if Path(x[0]).is_dir() else -1
  elif sort_col=='mtime':key=lambda x:Path(x[0]).stat().st_mtime if Path(x[0]).exists() else -1
  elif sort_col=='opened':idx=4;key=lambda x:x[1][idx]
  elif sort_col=='tags':idx=5;key=lambda x:x[1][idx].casefold()
  else:idx=6;key=lambda x:x[1][idx].casefold()
  if self.view_mode!='changes':
   try:data.sort(key=lambda x:(not x[2],key(x)),reverse=sort_desc)
   except Exception:pass
  configured_tags={'folder':{'foreground':'#087e8b'},'file_folder':{'background':'#edf3f6','foreground':'#143e55'},'file_pdf':{'background':'#ffffff'},'file_excel':{'background':'#ffffff'},'file_word':{'background':'#ffffff'},'file_cad':{'background':'#ffffff'},'file_image':{'background':'#ffffff'},'file_other':{'background':'#ffffff'}}
  for name,options in configured_tags.items():tree.tag_configure(name,**options)
  configured_ext_tags=set()
  for path,values,isdir in data:
   try:
    display=list(values)
    if len(display)>5 and display[5]:display[5]=tag_badges(display[5])
    rowtag='file_other' if str(path).startswith('activity:') else self.file_row_tag(path,isdir)
    if rowtag.startswith('file_ext_') and rowtag not in configured_ext_tags:tree.tag_configure(rowtag,background='#ffffff');configured_ext_tags.add(rowtag)
    tree.insert('','end',iid=path,values=(display[0],'☐',*display[1:]),image=self.file_icon_image(path,isdir),tags=(rowtag,))
   except tk.TclError:continue
  if hasattr(self,'status'):
   count=len(tree.get_children());self.status.set(f'●  {count:,} ملف  ·  {len(tree.selection()):,} محدد' if tree.selection() else f'●  {count:,} عنصر')

 def activate(self,tree):
  sel=tree.selection()
  if not sel:return
  event=getattr(self,'activity_rows',{}).get(str(sel[0]))
  if event:
   target=Path(event['path']) if event['path'] else None
   if target and target.exists():
    if target.is_dir():self.navigate_to(target)
    else:self.open_file(target)
   return
  p=Path(sel[0])
  if p.is_dir():
   self.navigate_to(p);return
  self.open_file(p)

 def navigate_to(self,p):
  if not p.is_dir():return
  self.save_view_state();self.backstack.append(self.current);self.forwardstack.clear();self.current=p;self.mode='folder';self.folder_group='الكل';self.refresh_directory();self.log_activity('تنقل إلى مجلد',f'فتح المجلد «{p.name}»',path=p);self.animate_window_in()

 def open_file(self,p):
  try:os.startfile(str(p))
  except Exception as e:messagebox.showerror('تعذر فتح الملف',str(e));return
  opened_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S');key=str(p.resolve())
  with connect() as c:
   c.execute('update files set last_open=? where path=?',(opened_at,key))
   c.execute('insert or ignore into file_open_history(project,path,opened_at) values(?,?,?)',(self.project,key,opened_at))
  self.log_activity('فتح ملف',f'تم فتح الملف «{p.name}»',path=p)
  self.populate()
  if hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped():
   with connect() as c:self.search_cache=c.execute("select f.*,group_concat(t.tag, ' ') tags from files f left join tags t on t.path=f.path where f.project=? group by f.path",(self.project,)).fetchall()
   self.render_search_results()

 def selected_path(self):
  tree=getattr(self,'file_tree',None)
  if hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped() and self.search_nb.tabs():tree=self.search_views.get(self.search_nb.tab(self.search_nb.select(),'text'),tree)
  sel=tree.selection() if tree else [];return Path(sel[0]) if sel else None

 def manage_file_tags(self):
  with connect() as c:
   tags=sorted({r[0] for r in c.execute('select tag from file_tag_catalog where project=? union select distinct t.tag from tags t join files f on f.path=t.path where f.project=?',(self.project,self.project))})
  win=tk.Toplevel(self);win.title('إدارة هاشتاجات الملفات');win.transient(self);win.resizable(False,False);win.configure(bg='#e8edf1')
  tk.Label(win,text='هاشتاجات الملفات المحفوظة',bg='#e8edf1',fg='#19394e',font=('Segoe UI',12,'bold')).pack(anchor='e',padx=16,pady=(14,4))
  tk.Label(win,text='إزالة هاشتاج مستخدم تمسحه من كل الملفات التي تحمله.',bg='#e8edf1',fg='#526b7c').pack(anchor='e',padx=16)
  lb=tk.Listbox(win,selectmode='extended',height=10,width=52,exportselection=False);lb.pack(fill='both',padx=16,pady=8)
  for tag in tags:lb.insert('end',tag)
  addrow=tk.Frame(win,bg='#e8edf1');addrow.pack(fill='x',padx=16);value=tk.StringVar();entry=ttk.Entry(addrow,textvariable=value);entry.pack(side='right',fill='x',expand=True)
  def add_tag():
   newtags=['#'+x.strip().lstrip('#') for x in value.get().replace(',',' ').replace('،',' ').split() if x.strip()]
   for tag in newtags:
    if tag not in [lb.get(i) for i in range(lb.size())]:lb.insert('end',tag)
   value.set('')
  ttk.Button(addrow,text='＋ إضافة',command=add_tag).pack(side='left',padx=(6,0))
  buttons=tk.Frame(win,bg='#e8edf1');buttons.pack(fill='x',padx=16,pady=(8,14))
  def remove_selected():
   selected=set(lb.curselection())
   for i in reversed(sorted(selected)):lb.delete(i)
  def save():
   current={lb.get(i) for i in range(lb.size())};removed=set(tags)-current;added=current-set(tags)
   if removed and not messagebox.askyesno('حذف هاشتاجات مستخدمة',f'سيتم حذف {len(removed)} هاشتاج من كتالوج المشروع ومن كل الملفات التي تحملها. متابعة؟',parent=win):return
   with connect() as c:
    for tag in removed:
     c.execute('delete from file_tag_catalog where project=? and tag=?',(self.project,tag))
     c.execute('delete from tags where tag=? and path in (select path from files where project=?)',(tag,self.project))
    c.executemany('insert or ignore into file_tag_catalog(project,tag,created) values(?,?,?)',[(self.project,tag,stamp(time.time())) for tag in current])
   if added:self.log_activity('إضافة هاشتاجات محفوظة','إضافة إلى كتالوج الملفات: '+', '.join(sorted(added)))
   if removed:self.log_activity('حذف هاشتاجات محفوظة','حذف من كتالوج الملفات والملفات المرتبطة: '+', '.join(sorted(removed)))
   self.refresh_tag_filters();self.populate()
   if hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped():self.refresh_search_cache();self.render_search_results()
   win.destroy()
  ttk.Button(buttons,text='حذف المحدد من القائمة',command=remove_selected).pack(side='left');ttk.Button(buttons,text='حفظ',command=save).pack(side='right');ttk.Button(buttons,text='إلغاء',command=win.destroy).pack(side='right',padx=4);win.grab_set();entry.focus_set()

 def edit_folder_specialties(self):
  folder=self.current
  if not folder or not folder.is_dir():return
  path=folder.relative_to(self.root).as_posix()
  with connect() as c:
   known=[r[0] for r in c.execute('select distinct tag from folder_tags where project=? order by tag',(self.project,))]
   selected={r[0] for r in c.execute('select tag from folder_tags where project=? and path=?',(self.project,path))}
  win=tk.Toplevel(self);win.title('تخصيص المجلد');win.transient(self);win.resizable(False,False);win.configure(bg='#e8edf1')
  tk.Label(win,text='تخصيص المجلد',bg='#e8edf1',fg='#19394e',font=('Segoe UI',12,'bold')).pack(anchor='e',padx=16,pady=(14,4))
  tk.Label(win,text=f'{folder.name} · التخصصات تخص هذا المجلد فقط ولا تغيّر هاشتاجات ملفاته.',bg='#e8edf1',fg='#526b7c',justify='right',wraplength=430).pack(anchor='e',padx=16)
  lb=tk.Listbox(win,selectmode='multiple',height=8,width=50,exportselection=False);lb.pack(fill='both',padx=16,pady=8)
  for tag in known:lb.insert('end',tag)
  for i,tag in enumerate(known):
   if tag in selected:lb.selection_set(i)
  row=tk.Frame(win,bg='#e8edf1');row.pack(fill='x',padx=16);value=tk.StringVar();entry=ttk.Entry(row,textvariable=value);entry.pack(side='right',fill='x',expand=True)
  def add_specialty():
   for tag in ['#'+x.strip().lstrip('#') for x in value.get().replace(',',' ').replace('،',' ').split() if x.strip()]:
    options=[lb.get(i) for i in range(lb.size())]
    if tag not in options:lb.insert('end',tag);lb.selection_set('end')
    else:lb.selection_set(options.index(tag))
   value.set('')
  ttk.Button(row,text='＋ إضافة تخصص',command=add_specialty).pack(side='left',padx=(6,0))
  def delete_specialty():
   indices=list(lb.curselection())
   if not indices:return messagebox.showinfo('حذف تخصص','حدد تخصصًا واحدًا أو أكثر من القائمة.',parent=win)
   to_delete={lb.get(i) for i in indices};saved=to_delete.intersection(known)
   if saved and not messagebox.askyesno('حذف التخصص',f'سيتم حذف {len(saved):,} تخصص من كل المجلدات التي تستخدمه في هذا المشروع. متابعة؟',parent=win):return
   remaining={lb.get(i) for i in lb.curselection() if i not in indices}
   if saved:
    with connect() as c:c.executemany('delete from folder_tags where project=? and tag=?',[(self.project,tag) for tag in saved])
    for tag in sorted(saved):self.log_activity('حذف تخصص',f'حذف التخصص {tag} من المجلدات',path=folder)
    known[:]=[tag for tag in known if tag not in saved];selected.difference_update(saved)
   for i in reversed(indices):lb.delete(i)
   for i in range(lb.size()):
    if lb.get(i) in remaining:lb.selection_set(i)
   if saved:
    if self.view_mode=='specialty' and getattr(self,'specialty_filter','') in saved:self.show_files_collection()
    else:self.refresh_tag_filters();self.populate();self.update_rail_selection()
  ttk.Button(row,text='− حذف التخصص المحدد',command=delete_specialty).pack(side='left',padx=3)
  buttons=tk.Frame(win,bg='#e8edf1');buttons.pack(fill='x',padx=16,pady=(8,14))
  def save():
   chosen={lb.get(i) for i in lb.curselection()}
   added=chosen-selected;removed=selected-chosen
   with connect() as c:
    c.execute('delete from folder_tags where project=? and path=?',(self.project,path))
    c.executemany('insert into folder_tags(project,path,tag,created) values(?,?,?,?)',[(self.project,path,tag,stamp(time.time())) for tag in chosen])
   if added:self.log_activity('تخصيص المجلد',f'إضافة تخصصات للمجلد «{folder.name}»: '+', '.join(sorted(added)),path=folder)
   if removed:self.log_activity('تخصيص المجلد',f'إزالة تخصصات من المجلد «{folder.name}»: '+', '.join(sorted(removed)),path=folder)
   self.refresh_tag_filters();self.populate();self.update_rail_selection();win.destroy()
  ttk.Button(buttons,text='حفظ التخصصات',command=save).pack(side='right');ttk.Button(buttons,text='إلغاء',command=win.destroy).pack(side='left');win.grab_set();entry.focus_set()

 def edit_tags(self):
  paths=[p for p in self.selected_paths() if p.is_file()]
  if not paths:return messagebox.showinfo('اختيار ملف','حدد ملفًا أو أكثر أولًا.')
  keys=[str(p.resolve()) for p in paths]
  with connect() as c:
   known=sorted({r[0] for r in c.execute('select tag from file_tag_catalog where project=? union select distinct t.tag from tags t join files f on f.path=t.path where f.project=?',(self.project,self.project))})
   old_by_path={key:{r[0] for r in c.execute('select tag from tags where path=?',(key,))} for key in keys}
   old=set().union(*old_by_path.values()) if old_by_path else set()
  win=tk.Toplevel(self);win.title('هاشتج الملف');win.transient(self);win.resizable(False,False);win.configure(bg='#e8edf1')
  tk.Label(win,text=f'هاشتج الملف · {len(paths):,} ملف محدد',bg='#e8edf1',fg='#19394e',font=('Segoe UI',11,'bold')).pack(anchor='e',padx=16,pady=(14,6))
  tk.Label(win,text='اختر هاشتاجات محفوظة أو اكتب هاشتاجًا جديدًا. الاختيارات ستحل محل هاشتاجات الملفات المحددة.',bg='#e8edf1',fg='#526b7c',wraplength=420,justify='right').pack(anchor='e',padx=16)
  lb=tk.Listbox(win,selectmode='multiple',height=9,width=48,exportselection=False);lb.pack(fill='both',padx=16,pady=8)
  for tag in known:lb.insert('end',tag)
  for i,tag in enumerate(known):
   if tag in old:lb.selection_set(i)
  row=tk.Frame(win,bg='#e8edf1');row.pack(fill='x',padx=16)
  suggestions=ttk.Combobox(row,values=known,state='readonly',width=20,style='Office.TCombobox');suggestions.pack(side='left',padx=(0,6))
  def use_suggestion(_=None):
   selected=suggestions.get()
   if selected in known:lb.selection_set(known.index(selected))
  suggestions.bind('<<ComboboxSelected>>',use_suggestion)
  tk.Label(win,text='أضف هاشتاجات جديدة مفصولة بمسافات أو فواصل:',bg='#e8edf1',fg='#526b7c').pack(anchor='e',padx=16,pady=(8,0))
  state=tk.StringVar();new_entry=ttk.Entry(win,textvariable=state,width=52);new_entry.pack(fill='x',padx=16,pady=5)
  buttons=tk.Frame(win,bg='#e8edf1');buttons.pack(fill='x',padx=16,pady=(5,14))
  def save():
   selected={lb.get(i) for i in lb.curselection()};selected.update('#'+x.strip().lstrip('#') for x in state.get().replace(',',' ').replace('،',' ').split() if x.strip())
   changes=[]
   with connect() as c:
    for key in keys:
     c.execute('delete from tags where path=?',(key,));c.executemany('insert or ignore into tags(path,tag) values(?,?)',[(key,t) for t in selected])
    c.executemany('insert or ignore into file_tag_catalog(project,tag,created) values(?,?,?)',[(self.project,t,stamp(time.time())) for t in selected])
    for p,key in zip(paths,keys):
     previous=old_by_path.get(key,set());added=selected-previous;removed=previous-selected
     if added or removed:
      details=f'«{p.name}»'
      if added:details+=' · إضافة: '+', '.join(sorted(added))
      if removed:details+=' · إزالة: '+', '.join(sorted(removed))
      changes.append((p,details))
   for p,details in changes:self.log_activity('تعديل هاشتاجات الملف',details,path=p)
   self.refresh_tag_filters();self.populate()
   if hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped():self.refresh_search_cache();self.render_search_results()
   win.destroy()
  ttk.Button(buttons,text='حفظ الهاشتاجات',command=save).pack(side='right');ttk.Button(buttons,text='إلغاء',command=win.destroy).pack(side='left');win.grab_set();new_entry.focus_set()

 def copy_selected_paths(self,tree=None):
  paths=self.selected_paths(tree)
  if not paths:return
  self.clipboard_clear();self.clipboard_append('\n'.join(str(p) for p in paths))
  if hasattr(self,'status'):self.status.set(f'تم نسخ مسارات {len(paths):,} ملف')

 def selected_paths(self,tree=None):
  if tree is None:
   tree=getattr(self,'file_tree',None)
   if hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped() and self.search_nb.tabs():tree=self.search_views.get(self.search_nb.tab(self.search_nb.select(),'text'),tree)
  return [Path(p) for p in (tree.selection() if tree else ()) if not str(p).startswith('activity:')]

 def clear_selected_tags(self,tree):
  paths=[p for p in self.selected_paths(tree) if p.is_file()]
  if not paths:return
  count=len(paths)
  if count>1 and not messagebox.askyesno('مسح الهاشتاجات',f'مسح كل الهاشتاجات من {count} ملفات محددة؟',parent=self):return
  with connect() as c:
   old={str(p.resolve()):[r[0] for r in c.execute('select tag from tags where path=?',(str(p.resolve()),))] for p in paths}
   c.executemany('delete from tags where path=?',[(str(p.resolve()),) for p in paths])
  changed=[p for p in paths if old.get(str(p.resolve()))]
  if changed:self.log_activity('مسح هاشتاجات الملف',f'مسح الهاشتاجات من {len(changed):,} ملف · '+', '.join(p.name for p in changed),path=changed[0] if len(changed)==1 else None)
  if hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped():
   with connect() as c:self.search_cache=c.execute("select f.*,group_concat(t.tag, ' ') tags from files f left join tags t on t.path=f.path where f.project=? group by f.path",(self.project,)).fetchall()
   self.render_search_results()
  self.populate()

 def delete_selected_paths(self,tree=None):
  paths=[p.resolve() for p in self.selected_paths(tree) if p.exists()]
  if not paths:return
  root=self.root.resolve();safe=[]
  for path in paths:
   try:path.relative_to(root)
   except ValueError:continue
   if path!=root and path not in safe:safe.append(path)
  if not safe:return messagebox.showwarning('الحذف غير متاح','لا يمكن حذف ملفات خارج مجلد المشروع أو حذف مجلد المشروع نفسه.',parent=self)
  if os.name!='nt':return messagebox.showerror('الحذف غير متاح','إرسال العناصر إلى سلة المحذوفات متاح على Windows فقط.',parent=self)
  labels='، '.join(p.name for p in safe[:4]);extra=f' و{len(safe)-4} عناصر أخرى' if len(safe)>4 else ''
  if not messagebox.askyesno('إرسال إلى سلة المحذوفات',f'نقل {len(safe):,} عنصر إلى سلة المحذوفات؟\n{labels}{extra}',icon='warning',parent=self):return
  project=self.project;root=self.root.resolve()
  with connect() as c:rows=c.execute('select path,rel from files where project=?',(project,)).fetchall()
  tracked=set();folders=[p for p in safe if p.is_dir()]
  for item in safe:
   if item.is_dir():
    rel=item.relative_to(root).as_posix().rstrip('/');prefix=rel+'/'
    tracked.update(row['path'] for row in rows if row['rel']==rel or row['rel'].startswith(prefix))
   else:tracked.add(str(item))
  tracked.update(str(p) for p in safe if p.is_file())
  stamp_now=stamp(time.time());parent_hwnd=self.winfo_id()
  self.status.set('جارٍ نقل العناصر إلى سلة المحذوفات…')
  def worker():
   result=-1;aborted=False;error=None
   try:
    class SHFILEOPSTRUCTW(ctypes.Structure):
     _fields_=[('hwnd',ctypes.c_void_p),('wFunc',ctypes.c_uint),('pFrom',ctypes.c_wchar_p),('pTo',ctypes.c_wchar_p),('fFlags',ctypes.c_ushort),('fAnyOperationsAborted',ctypes.c_int),('hNameMappings',ctypes.c_void_p),('lpszProgressTitle',ctypes.c_wchar_p)]
    source='\0'.join(str(p) for p in safe)+'\0\0';operation=SHFILEOPSTRUCTW(parent_hwnd,3,source,None,0x0040|0x0010|0x0004|0x0400,False,None,None)
    shell=ctypes.windll.shell32;fn=shell.SHFileOperationW;fn.argtypes=[ctypes.POINTER(SHFILEOPSTRUCTW)];fn.restype=ctypes.c_int
    result=fn(ctypes.byref(operation));aborted=bool(operation.fAnyOperationsAborted)
    if result==0 and not aborted:
     try:
      with connect() as c:
       for key in tracked:
        c.execute('delete from tags where path=?',(key,));c.execute('delete from files where path=?',(key,))
        c.execute('insert into file_changes(project,path,kind,changed_at) values(?,?,?,?)',(project,key,'removed',stamp_now))
        c.execute('insert into activity_log(project,action,details,path,occurred_at) values(?,?,?,?,?)',(project,'حذف إلى سلة المحذوفات',f'تم نقل «{Path(key).name}» إلى سلة المحذوفات',key,stamp_now))
       favorites=c.execute('select path from favorites where project=?',(project,)).fetchall()
       for favorite in favorites:
        value=Path(favorite['path'])
        if any(value==item or (item.is_dir() and str(value).startswith(str(item).rstrip('\\/')+os.sep)) for item in safe):c.execute('delete from favorites where project=? and path=?',(project,favorite['path']))
       for folder in folders:c.execute('insert into activity_log(project,action,details,path,occurred_at) values(?,?,?,?,?)',(project,'حذف مجلد إلى سلة المحذوفات',f'تم نقل المجلد «{folder.name}» إلى سلة المحذوفات',str(folder),stamp_now))
     except Exception as exc:error=str(exc)
   except Exception as exc:error=str(exc)
   try:self.after(0,lambda:self._finish_delete(result,aborted,error,len(safe),project))
   except tk.TclError:pass
  threading.Thread(target=worker,daemon=True).start()

 def _finish_delete(self,result,aborted,error,count,project):
  if result==0 and not aborted:
   if self.project==project:
    self.status.set(f'تم نقل {count:,} عنصر إلى سلة المحذوفات');self._folder_size_cache=None;self.rebuild_project_tabs();self.rebuild_folder_tabs();self.populate()
    if hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped():self.refresh_search_cache();self.render_search_results()
   if error:messagebox.showwarning('تم الحذف مع تنبيه','نُقلت العناصر، لكن تعذر تحديث بعض بيانات السجل. سيحاول التحديث التالي مزامنتها.',parent=self)
  elif self.project==project:
   messagebox.showerror('تعذر الحذف',error or 'لم يكتمل النقل إلى سلة المحذوفات.',parent=self)
   self.status.set('لم يتم حذف العناصر')
   if aborted or result==0:self.rescan()

 def context_menu(self,e,tree):
  row=tree.identify_row(e.y)
  if not row:return
  if row not in tree.selection():tree.selection_set(row)
  event=getattr(self,'activity_rows',{}).get(str(row))
  if event:
   menu=tk.Menu(self,tearoff=0);target=Path(event['path']) if event['path'] else None
   if target and target.exists():menu.add_command(label='فتح الملف أو المجلد المرتبط',command=lambda p=target:self.navigate_to(p) if p.is_dir() else self.open_file(p))
   menu.add_command(label='نسخ تفاصيل الحدث',command=lambda d=event['details']:(self.clipboard_clear(),self.clipboard_append(d)))
   menu.tk_popup(e.x_root,e.y_root);return
  selected=self.selected_paths(tree);p=Path(row);files=[x for x in selected if x.is_file()];menu=tk.Menu(self,tearoff=0)
  fav_label='إزالة من المفضلة' if selected and all(self.is_favorite(x) for x in selected) else 'إضافة إلى المفضلة'
  menu.add_command(label=(fav_label+f' ({len(selected)} عناصر)' if len(selected)>1 else fav_label),command=lambda:self.toggle_favorite(selected))
  if p.is_dir():menu.add_command(label='فتح المجلد',command=lambda:self.navigate_to(p))
  else:
   menu.add_command(label='فتح الملف',command=lambda:self.open_file(p));menu.add_command(label='عرض ملفات اللوحة المرتبطة (DWG / PDF)',command=lambda:self.show_related_files(p));menu.add_command(label=f'هاشتج الملف ({len(files)} ملف)' if len(files)>1 else 'هاشتج الملف',command=self.edit_tags);menu.add_command(label=f'مسح كل الهاشتاجات ({len(files)} ملف)' if len(files)>1 else 'مسح كل الهاشتاجات',command=lambda:self.clear_selected_tags(tree));menu.add_command(label='إظهار مكان الملف في Explorer',command=lambda:subprocess.Popen(['explorer','/select,',str(p)]));menu.add_command(label='نسخ المسار',command=lambda:self.copy_selected_paths(tree))
  if selected and all(path.exists() for path in selected):
   menu.add_separator();menu.add_command(label=f'إرسال إلى سلة المحذوفات ({len(selected)} عنصر)' if len(selected)>1 else 'إرسال إلى سلة المحذوفات',command=lambda:self.delete_selected_paths(tree))
  menu.tk_popup(e.x_root,e.y_root)

 def go_back(self):
  if self.backstack:
   self.save_view_state();self.forwardstack.append(self.current);self.current=self.backstack.pop();self.mode='folder';self.folder_group='الكل';self.refresh_directory();self.log_activity('رجوع في المجلدات',f'رجوع إلى «{self.current.name}»',path=self.current);self.animate_window_in()

 def go_forward(self):
  if self.forwardstack:
   self.save_view_state();self.backstack.append(self.current);self.current=self.forwardstack.pop();self.mode='folder';self.folder_group='الكل';self.refresh_directory();self.log_activity('تقدم في المجلدات',f'فتح «{self.current.name}»',path=self.current);self.animate_window_in()

 def go_up(self):
  if self.current and self.current!=self.root:
   self.save_view_state();self.backstack.append(self.current);self.forwardstack.clear();self.current=self.current.parent;self.mode='folder';self.folder_group='الكل';self.refresh_directory();self.log_activity('الانتقال للمجلد الأعلى',f'فتح «{self.current.name}»',path=self.current);self.animate_window_in()

 def rescan(self):
  self.scan_summary.set('جارٍ تحديث فهرس المشروع...');self.start_scan_progress();threading.Thread(target=self.scan_worker,args=(self.root,),daemon=True).start()
 def show_search_page(self):
  if not self.root or not self.root.is_dir():return
  self.preview_token+=1;self.explorer_page.pack_forget();self.search_page=tk.Frame(self,bg='#e8edf1');self.search_page.pack(fill='both',expand=True,padx=10,pady=9)
  self.search_page.grid_rowconfigure(0,weight=1);self.search_page.grid_columnconfigure(0,weight=0,minsize=350);self.search_page.grid_columnconfigure(1,weight=1);self.search_page.grid_columnconfigure(2,weight=0,minsize=176)
  self.search_preview_area=tk.Frame(self.search_page,bg='#eef2f5',highlightbackground='#d6e0e6',highlightthickness=1,width=350);self.search_preview_area.grid(row=0,column=0,sticky='nsew',padx=(0,8));self.search_preview_area.grid_propagate(False);self.search_preview_area.grid_rowconfigure(1,weight=1);self.search_preview_area.grid_columnconfigure(0,weight=1)
  preview_head=tk.Frame(self.search_preview_area,bg='#dfe7ec');preview_head.grid(row=0,column=0,sticky='ew')
  tk.Label(preview_head,text='معاينة وتفاصيل',bg='#dfe7ec',fg='#19394e',font=('Segoe UI',11,'bold'),anchor='e').pack(side='right',fill='x',expand=True,ipady=10,padx=10)
  ttk.Button(preview_head,text='×',width=3,command=self.toggle_preview_panel).pack(side='left',padx=5,pady=4)
  self.search_preview_image=tk.Canvas(self.search_preview_area,bg='#eef2f5',highlightthickness=0);self.search_preview_image.grid(row=1,column=0,sticky='nsew',padx=7,pady=7);self.search_preview_image.bind('<ButtonPress-1>',self.preview_pan_start);self.search_preview_image.bind('<B1-Motion>',self.preview_pan_move);self.search_preview_image.bind('<MouseWheel>',self.preview_wheel)
  self.search_preview_meta=tk.Label(self.search_preview_area,text='اختر نتيجة لمعاينتها.',bg='white',fg='#526b7c',font=('Segoe UI',9),justify='right',anchor='ne',wraplength=330);self.search_preview_meta.grid(row=2,column=0,sticky='ew',padx=12,pady=(0,8))
  self.search_preview_related_strip=tk.Frame(self.search_preview_area,bg='#edf2f5');self.search_preview_related_strip.grid(row=3,column=0,sticky='ew',padx=8,pady=(0,4));self.search_preview_related_strip.grid_remove()
  ctr=tk.Frame(self.search_preview_area,bg='white');ctr.grid(row=4,column=0,sticky='ew',padx=8,pady=(0,8));ttk.Button(ctr,text='−',width=3,command=lambda:self.zoom_preview(-.15)).pack(side='left');ttk.Button(ctr,text='＋',width=3,command=lambda:self.zoom_preview(.15)).pack(side='left');ttk.Button(ctr,text='◀ صفحة',command=lambda:self.change_pdf_page(-1)).pack(side='right',padx=2);ttk.Button(ctr,text='صفحة ▶',command=lambda:self.change_pdf_page(1)).pack(side='right',padx=2);ttk.Button(ctr,text='ملفات مرتبطة',command=self.open_related_from_preview).pack(side='right',padx=3)
  self.search_center=tk.Frame(self.search_page,bg='#e8edf1');self.search_center.grid(row=0,column=1,sticky='nsew');self.search_center.grid_columnconfigure(0,weight=1)
  head=tk.Frame(self.search_center,bg='#102c3d');head.grid(row=0,column=0,sticky='ew');tk.Label(head,text='بحث المشروع',font=('Segoe UI',15,'bold'),fg='white',bg='#102c3d').pack(side='right',padx=16,pady=11);ttk.Button(head,text='← رجوع للملفات',command=self.hide_search_page).pack(side='left',padx=10,pady=7);self.search_preview_toggle=ttk.Button(head,text='◧  إخفاء المعاينة',command=self.toggle_preview_panel);self.search_preview_toggle.pack(side='left',padx=4,pady=7)
  scope=tk.Frame(self.search_center,bg='#dfe7ec');scope.grid(row=1,column=0,sticky='ew',pady=(6,7));tk.Label(scope,text=f'نتائج البحث محصورة في مشروع «{self.project}»',bg='#dfe7ec',fg='#28465a',anchor='e',font=('Segoe UI',9,'bold')).pack(side='right',padx=12,pady=7);tk.Label(scope,text='المشروع بالكامل',bg='#dfe7ec',fg='#087e8b',font=('Segoe UI',9)).pack(side='left',padx=12)
  with connect() as c:
   state=c.execute('select query,mode,file_type from project_search_state where project=?',(self.project,)).fetchone()
   self.search_cache=c.execute("select f.*,group_concat(t.tag, ' ') tags from files f left join tags t on t.path=f.path where f.project=? group by f.path",(self.project,)).fetchall()
   saved=c.execute('select query,mode from saved_searches where project=? order by created desc',(self.project,)).fetchall()
   history=c.execute('select query,mode from search_history where project=? order by searched_at desc limit 20',(self.project,)).fetchall()
  q,mode,kind=(state['query'],state['mode'],state['file_type']) if state else ('','الكل','كل النتائج')
  self.search_type=kind or 'كل النتائج';self.search_query=tk.StringVar(value=q or '');self.search_mode=tk.StringVar(value=mode or 'الكل');self.search_search_job=None;self.search_history_job=None
  bar=tk.Frame(self.search_center,bg='white',highlightbackground='#d6e0e6',highlightthickness=1);bar.grid(row=2,column=0,sticky='ew',pady=(0,6))
  tk.Label(bar,text='ابحث بالاسم أو المسار أو الامتداد أو الهاشتاج',bg='white',fg='#617789',font=('Segoe UI',9)).pack(side='right',padx=(8,0))
  entry=ttk.Entry(bar,textvariable=self.search_query,font=('Segoe UI',12));entry.pack(side='right',fill='x',expand=True,padx=8,pady=6)
  self.search_mode_box=ttk.Combobox(bar,textvariable=self.search_mode,values=('الكل','اسم الملف','المسار','الامتداد','الهاشتاج'),state='readonly',width=13,justify='right',style='Office.TCombobox');self.search_mode_box.pack(side='right',padx=4);self.search_mode_box.bind('<<ComboboxSelected>>',self.search_mode_changed)
  ttk.Button(bar,text='مسح',command=lambda:self.search_query.set('')).pack(side='right',padx=3);ttk.Button(bar,text='☆ حفظ البحث',command=self.save_search_bookmark).pack(side='left',padx=5)
  presets=tk.Frame(self.search_center,bg='#e8edf1');presets.grid(row=3,column=0,sticky='new',pady=(0,4));self.search_center.grid_rowconfigure(4,weight=1);tk.Label(presets,text='محفوظ:',bg='#e8edf1',fg='#617789').pack(side='right')
  self.saved_search_box=ttk.Combobox(presets,values=[f"{r['query']}  ·  {r['mode']}" for r in saved],state='readonly',width=26,justify='right',style='Office.TCombobox');self.saved_search_box.pack(side='right',padx=5);self.saved_search_rows=list(saved);self.saved_search_box.bind('<<ComboboxSelected>>',self.load_search_bookmark)
  ttk.Button(presets,text='حذف المحفوظ',command=self.delete_search_bookmark).pack(side='right',padx=3)
  tk.Label(presets,text='حديث:',bg='#e8edf1',fg='#617789').pack(side='right',padx=(12,2));self.history_rows=list(history);self.history_box=ttk.Combobox(presets,values=[f"{r['query']}  ·  {r['mode']}" for r in history],state='readonly',width=36,justify='right',style='Office.TCombobox');self.history_box.pack(side='right',padx=4);self.history_box.bind('<<ComboboxSelected>>',self.load_search_history)
  self.search_nb=ttk.Notebook(self.search_center);self.search_nb.grid(row=4,column=0,sticky='nsew');self.search_nb.bind('<<NotebookTabChanged>>',self.search_tab_changed);self.search_views={};self.search_tab_types={}
  self.search_selection_bar,self.search_selection_label=self.make_selection_bar(self.search_center);self.search_selection_bar.grid(row=5,column=0,sticky='ew',pady=(5,0));self.search_selection_bar.grid_remove()
  self.search_status=tk.StringVar(value='');tk.Label(self.search_center,textvariable=self.search_status,bg='#dfe7ec',fg='#617789',anchor='e',font=('Segoe UI',9)).grid(row=6,column=0,sticky='ew',pady=(4,0))
  rail=tk.Frame(self.search_page,bg='#102c3d',width=176);rail.grid(row=0,column=2,sticky='nsew',padx=(0,8));rail.grid_propagate(False)
  tk.Label(rail,text='بحث داخل المشروع',bg='#102c3d',fg='white',font=('Segoe UI',12,'bold')).pack(anchor='e',padx=14,pady=(13,2));tk.Label(rail,text=self.project,bg='#102c3d',fg='#a9c3d0',font=('Segoe UI',9),wraplength=162,anchor='e').pack(anchor='e',fill='x',padx=14,pady=(0,7))
  tk.Label(rail,text='التصفح',bg='#102c3d',fg='#83a8b9',font=('Segoe UI',8,'bold')).pack(anchor='e',padx=14,pady=(1,3))
  def search_exit(kind,value=None):self.leave_search_for(kind,value)
  for label,kind in [('ملفات المجلدات','folder'),('ملفات المشروع','project')]:
   tk.Button(rail,text='▦  '+label,command=lambda k=kind:search_exit(k),anchor='e',bg='#102c3d',fg='#d3e2e9',activebackground='#24546a',activeforeground='white',relief='flat',font=('Segoe UI',8),padx=11,pady=5,cursor='hand2').pack(fill='x',padx=7,pady=1)
  tk.Label(rail,text='الوصول السريع',bg='#102c3d',fg='#83a8b9',font=('Segoe UI',8,'bold')).pack(anchor='e',padx=14,pady=(7,2))
  for label,kind in [('المفضلة','favorites'),('آخر ما فتحته','opened'),('أضيف حديثًا','added'),('سجل التغييرات','changes')]:
   tk.Button(rail,text='•  '+label,command=lambda k=kind:search_exit(k),anchor='e',bg='#102c3d',fg='#d3e2e9',activebackground='#24546a',activeforeground='white',relief='flat',font=('Segoe UI',8),padx=11,pady=4,cursor='hand2').pack(fill='x',padx=7,pady=1)
  with connect() as c:search_specialties=[r[0] for r in c.execute('select distinct tag from folder_tags where project=? order by tag',(self.project,))]
  if search_specialties:
   tk.Label(rail,text='التخصصات',bg='#102c3d',fg='#83a8b9',font=('Segoe UI',8,'bold')).pack(anchor='e',padx=14,pady=(7,2))
   for tag in search_specialties[:4]:
    tk.Button(rail,text='●  '+tag,command=lambda t=tag:search_exit('specialty',t),anchor='e',bg='#102c3d',fg='#d3e2e9',activebackground='#24546a',relief='flat',font=('Segoe UI',8),padx=11,pady=4,cursor='hand2').pack(fill='x',padx=7,pady=1)
  tk.Label(rail,text='نطاق النتائج: المشروع بالكامل',bg='#1b4053',fg='white',font=('Segoe UI',8),justify='right',anchor='e',padx=8,pady=6,wraplength=158).pack(fill='x',padx=7,pady=(6,0))
  tk.Label(rail,text='طرق البحث',bg='#102c3d',fg='#83a8b9',font=('Segoe UI',8,'bold')).pack(anchor='e',padx=14,pady=(8,2))
  for label,mode_name in [('الكل','الكل'),('اسم الملف','اسم الملف'),('المسار','المسار'),('الامتداد','الامتداد'),('الهاشتاج','الهاشتاج')]:
   tk.Button(rail,text='⌕  '+label,command=lambda x=mode_name:self.search_mode.set(x),anchor='e',bg='#102c3d',fg='#d3e2e9',activebackground='#24546a',activeforeground='white',relief='flat',font=('Segoe UI',8),padx=11,pady=4,cursor='hand2').pack(fill='x',padx=7,pady=1)
  tk.Frame(rail,bg='#23485b',height=1).pack(fill='x',padx=12,pady=7);tk.Label(rail,text='النتائج تتحدث أثناء الكتابة. اختر نوعًا من التبويبات أعلى القائمة.',bg='#102c3d',fg='#a9c3d0',font=('Segoe UI',8),justify='right',wraplength=158).pack(anchor='e',padx=12)
  self.active_preview=(self.preview_image,self.preview_meta,self.preview_related_strip);self.preview_image=self.search_preview_image;self.preview_meta=self.search_preview_meta;self.preview_related_strip=self.search_preview_related_strip
  self.search_query.trace_add('write',self.schedule_search_results);self.search_mode.trace_add('write',self.schedule_search_results);entry.bind('<Return>',self.record_search_history);entry.bind('<Control-f>',lambda e:(entry.focus_set(),'break'));entry.bind('<Escape>',lambda e:(self.hide_search_page(),'break'))
  self.render_search_results();entry.focus_set();self.animate_window_in()

 def refresh_search_cache(self):
  with connect() as c:self.search_cache=c.execute("select f.*,group_concat(t.tag, ' ') tags from files f left join tags t on t.path=f.path where f.project=? group by f.path",(self.project,)).fetchall()

 def save_search_state(self):
  if not hasattr(self,'search_query') or not hasattr(self,'search_page') or not self.search_page.winfo_exists():return
  with connect() as c:c.execute('insert into project_search_state(project,query,mode,file_type) values(?,?,?,?) on conflict(project) do update set query=excluded.query,mode=excluded.mode,file_type=excluded.file_type',(self.project,self.search_query.get(),self.search_mode.get(),self.search_type))

 def load_search_bookmark(self,e=None):
  i=self.saved_search_box.current()
  if i>=0 and i<len(self.saved_search_rows):r=self.saved_search_rows[i];self.search_mode.set(r['mode']);self.search_query.set(r['query']);self.record_search_history()

 def load_search_history(self,e=None):
  i=self.history_box.current()
  if i>=0 and i<len(self.history_rows):r=self.history_rows[i];self.search_mode.set(r['mode']);self.search_query.set(r['query'])

 def save_search_bookmark(self):
  q=self.search_query.get().strip()
  if not q:return messagebox.showinfo('حفظ البحث','اكتب كلمة البحث أولًا.',parent=self)
  mode=self.search_mode.get()
  with connect() as c:c.execute('insert or replace into saved_searches(project,query,mode,created) values(?,?,?,?)',(self.project,q,mode,stamp(time.time())))
  self.log_activity('حفظ بحث',f'تم حفظ البحث «{q[:300]}» · {mode}')
  with connect() as c:self.saved_search_rows=c.execute('select query,mode from saved_searches where project=? order by created desc',(self.project,)).fetchall()
  self.saved_search_box.configure(values=[f"{r['query']}  ·  {r['mode']}" for r in self.saved_search_rows]);self.saved_search_box.current(0)

 def delete_search_bookmark(self):
  i=self.saved_search_box.current()
  if i<0 or i>=len(self.saved_search_rows):return
  r=self.saved_search_rows[i]
  with connect() as c:c.execute('delete from saved_searches where project=? and query=? and mode=?',(self.project,r['query'],r['mode']))
  self.log_activity('حذف بحث محفوظ',f'تم حذف البحث المحفوظ «{r["query"][:300]}» · {r["mode"]}')
  with connect() as c:self.saved_search_rows=c.execute('select query,mode from saved_searches where project=? order by created desc',(self.project,)).fetchall()
  self.saved_search_box.set('');self.saved_search_box.configure(values=[f"{x['query']}  ·  {x['mode']}" for x in self.saved_search_rows])

 def record_search_history(self,e=None):
  q=self.search_query.get().strip()
  if q:
   mode=self.search_mode.get()
   with connect() as c:c.execute('insert or replace into search_history(project,query,mode,searched_at) values(?,?,?,?)',(self.project,q,mode,stamp(time.time())))
   search_key=(self.project,q,mode)
   if getattr(self,'_last_activity_search',None)!=search_key:
    self.log_activity('بحث',f'بحث عن «{q[:300]}» · {mode}')
    self._last_activity_search=search_key
   with connect() as c:self.history_rows=c.execute('select query,mode from search_history where project=? order by searched_at desc limit 20',(self.project,)).fetchall()
   self.history_box.configure(values=[f"{r['query']}  ·  {r['mode']}" for r in self.history_rows]);self.history_box.set('')
  self.save_search_state()

 def search_mode_changed(self,e=None):self.schedule_search_results()

 def search_tab_changed(self,e=None):
  if getattr(self,'search_rendering',False) or not self.search_nb.tabs():return
  label=self.search_nb.tab(self.search_nb.select(),'text');self.search_type=self.search_tab_types.get(label,'كل النتائج');self.save_search_state()

 def launch_everything_search(self):
  exe=Path(getattr(sys,'_MEIPASS',BASE))/'Everything'/'Everything.exe'
  if not exe.exists():return self.show_search_page()
  try:
   root=self.root.resolve()
   if not is_project_path(root):raise ValueError('يمكن لـ Everything البحث داخل مجلدات المشاريع الموجودة في Log فقط')
   key=hashlib.sha256(str(root).casefold().encode('utf-8')).hexdigest()[:16]
   data=LOG/'.everything_data'/key;data.mkdir(parents=True,exist_ok=True)
   ini=data/'Everything.ini';db=data/'Everything.db'
   if not ini.exists():ini.write_text('[Everything]\napp_data=0\nrun_as_admin=0\nindex_as_admin=0\nauto_include_fixed_volumes=0\nauto_include_removable_volumes=0\nauto_include_network_volumes=0\nallow_options=0\nallow_admin_options=0\nallow_plugins=0\nsearch_history_enabled=1\nsearch_history_keep_forever=1\nsearch_history_always_suggest=1\n',encoding='utf-8')
   # Keep Everything's per-project settings and history alongside the project.
   local_exe=data/'Everything.exe';local_lng=data/'Everything.lng'
   for source,target in ((exe,local_exe),(exe.with_name('Everything.lng'),local_lng)):
    if source.exists() and (not target.exists() or target.stat().st_size!=source.stat().st_size):
     try:shutil.copy2(source,target)
     except OSError:pass
   if not local_exe.exists():local_exe=exe
   if ini.exists():
    content=ini.read_text(encoding='utf-8',errors='replace')
    for setting in ('search_history_enabled=1','search_history_keep_forever=1','search_history_always_suggest=1'):
     name,value=setting.split('=',1);lines=content.splitlines();match=[i for i,line in enumerate(lines) if line.strip().split('=',1)[0].casefold()==name.casefold()]
     if match:lines[match[-1]]=setting
     else:lines.append(setting)
     content='\n'.join(lines)+'\n'
    ini.write_text(content,encoding='utf-8')
   self.explorer_page.pack_forget();self.everything_page=tk.Frame(self,bg='#e8edf1');self.everything_page.pack(fill='both',expand=True,padx=10,pady=8)
   head=tk.Frame(self.everything_page,bg='#102c3d');head.pack(fill='x');tk.Label(head,text=f'بحث Everything داخل {self.project}',font=('Segoe UI',15,'bold'),fg='white',bg='#102c3d').pack(side='right',padx=18,pady=10);ttk.Button(head,text='← الرجوع للمجلد',command=self.hide_everything_page).pack(side='left',padx=12,pady=7)
   self.everything_host=tk.Frame(self.everything_page,bg='white',highlightbackground='#d8e2ea',highlightthickness=1);self.everything_host.pack(fill='both',expand=True,pady=(8,0));self.everything_key=key;self.everything_status=tk.StringVar(value='جارٍ فتح واجهة البحث وفهرسة ملفات هذا المشروع...');tk.Label(self.everything_page,textvariable=self.everything_status,anchor='e',bg='#e8edf1',fg='#617789').pack(fill='x')
   instance='OfficeLogSearch_'+key
   with connect() as c:extensions=[r[0] for r in c.execute('select distinct ext from files where project=? and ext is not null and ext<>\'\'',(self.project,))]
   self.everything_launch=(local_exe,instance,ini,db,data,root,extensions);self.everything_instance=instance;self.everything_data=data;self.everything_exe=local_exe
   self.everything_attempts=0;self.everything_exe_path=str(local_exe.resolve())
   self.everything_exit_proc=subprocess.Popen([str(local_exe),'-instance',instance,'-exit','-wait'],cwd=str(data),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
   self.after(100,self.start_everything_instance)
  except Exception as e:messagebox.showerror('تعذر تشغيل Everything',str(e),parent=self)

 def start_everything_instance(self):
  if not hasattr(self,'everything_host') or not self.everything_host.winfo_exists():return
  if self.everything_exit_proc and self.everything_exit_proc.poll() is None:
   self.everything_attempts+=1
   if self.everything_attempts>60:
    self.everything_status.set('تعذر إغلاق جلسة البحث السابقة. ارجع للمجلد ثم أعد فتح البحث.')
    return
   self.after(100,self.start_everything_instance);return
  try:
   exe,instance,ini,db,data,root,extensions=self.everything_launch
   sync_everything_filters(data,instance,extensions)
   self.everything_proc=subprocess.Popen([str(exe),'-instance',instance,'-config',str(ini),'-db',str(db),'-no-auto-index','-volumes','','-folders',str(root),'-no-menu','-no-folders-sidebar','-bookmarks-sidebar','-filters-sidebar','-focus-search','-details','-sort','Name','-sort-ascending'],cwd=str(data))
   self.everything_attempts=0;self.after(250,self.attach_everything_window)
  except Exception as e:self.everything_status.set(f'تعذر تشغيل Everything: {e}')

 def attach_everything_window(self):
  if not hasattr(self,'everything_host') or not self.everything_host.winfo_exists():return
  key='OfficeLogSearch_'+str(self.everything_key);found=[];user32=ctypes.windll.user32;target_pid=self.everything_proc.pid if self.everything_proc else 0;target_exe=os.path.normcase(os.path.abspath(getattr(self,'everything_exe_path','')))
  remembered=self.everything_windows.get(key)
  if remembered and user32.IsWindow(remembered):found.append(remembered)
  enum_type=ctypes.WINFUNCTYPE(ctypes.c_bool,ctypes.c_void_p,ctypes.c_void_p)
  def visit(hwnd,_):
   if not user32.IsWindowVisible(hwnd):return True
   n=user32.GetWindowTextLengthW(hwnd)
   if not n:return True
   title=ctypes.create_unicode_buffer(n+1);user32.GetWindowTextW(hwnd,title,n+1)
   pid=ctypes.c_ulong();user32.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
   matches=key in title.value or (target_pid and pid.value==target_pid)
   if not matches and target_exe:
    kernel32=ctypes.windll.kernel32;handle=kernel32.OpenProcess(0x1000,False,pid.value)
    if handle:
     size=ctypes.c_ulong(32768);path=ctypes.create_unicode_buffer(size.value)
     try:matches=bool(kernel32.QueryFullProcessImageNameW(handle,0,path,ctypes.byref(size))) and os.path.normcase(os.path.abspath(path.value))==target_exe
     finally:kernel32.CloseHandle(handle)
   if matches:found.append(hwnd);return False
   return True
  if not found:user32.EnumWindows(enum_type(visit),0)
  if not found:
   self.everything_attempts+=1
   if self.everything_proc and self.everything_proc.poll() is not None and self.everything_attempts>12:
    self.everything_status.set('تعذر إظهار نافذة البحث. اضغط رجوع ثم أعد فتح البحث.')
    ttk.Button(self.everything_page,text='إعادة المحاولة',command=self.launch_everything_search).pack(anchor='e',pady=6)
    return
   if self.everything_attempts>80:
    self.everything_status.set('استغرق فتح البحث وقتًا أطول من المتوقع. اضغط رجوع ثم أعد المحاولة.')
    return
   self.after(250,self.attach_everything_window);return
  hwnd=found[0];self.everything_hwnd=hwnd;self.everything_windows[key]=hwnd;parent=self.everything_host.winfo_id();user32.SetParent(hwnd,parent)
  GWL_STYLE=-16;style=user32.GetWindowLongW(hwnd,GWL_STYLE);remove=0x80000000|0x00C00000|0x00040000|0x00080000|0x00020000|0x00010000;style=(style&~remove)|0x40000000|0x10000000;user32.SetWindowLongW(hwnd,GWL_STYLE,style);self.everything_host.bind('<Configure>',self.resize_everything_window);self.resize_everything_window();user32.ShowWindow(hwnd,5);self.everything_status.set('بحث سريع داخل ملفات المشروع المفتوح فقط')

 def resize_everything_window(self,event=None):
  if self.everything_hwnd and self.everything_host.winfo_exists():
   user32=ctypes.windll.user32;user32.MoveWindow(self.everything_hwnd,0,0,max(1,self.everything_host.winfo_width()),max(1,self.everything_host.winfo_height()),True)

 def hide_everything_page(self):
  if self.everything_hwnd:
   hwnd=self.everything_hwnd;user32=ctypes.windll.user32;user32.ShowWindow(hwnd,0);user32.SetParent(hwnd,0);user32.PostMessageW(hwnd,0x0010,0,0);self.everything_hwnd=None;self.everything_windows.clear()
  self.stop_everything_instance()
  if hasattr(self,'everything_page'):self.everything_page.destroy()
  self.explorer_page.pack(fill='both',expand=True,padx=12,pady=10);self.status.set('تم الرجوع إلى ملفات المشروع')

 def prepare_everything_search(self,requested_root=None):
  if os.name!='nt':raise RuntimeError('بحث Everything متاح على Windows فقط')
  resource=Path(getattr(sys,'_MEIPASS',BASE))/'Everything';source_exe=resource/'Everything.exe';source_cli=resource/'es.exe'
  if not source_exe.is_file() or not source_cli.is_file():raise FileNotFoundError('ملفات محرك Everything غير موجودة بجوار البرنامج')
  root=Path(requested_root or self.root).resolve()
  if not is_project_path(root):raise ValueError('يمكن لـ Everything البحث داخل مجلدات المشاريع الموجودة في Log فقط')
  key=hashlib.sha256(str(root).casefold().encode('utf-8')).hexdigest()[:16];instance='OfficeLogSearch_'+key;data=LOG/'.everything_data'/key;data.mkdir(parents=True,exist_ok=True)
  local_exe=data/'Everything.exe';ini=data/'Everything.ini';db=data/'Everything.db'
  with self.search_engine_lock:
   if self.everything_key==key and self.everything_proc and self.everything_proc.poll() is None:
    return local_exe,source_cli,instance,data,root
   if self.everything_instance and self.everything_instance!=instance:self.stop_everything_instance()
   if not local_exe.exists() or local_exe.stat().st_size!=source_exe.stat().st_size:shutil.copy2(source_exe,local_exe)
   if not ini.exists():ini.write_text('[Everything]\napp_data=0\nrun_as_admin=0\nindex_as_admin=0\nauto_include_fixed_volumes=0\nauto_include_removable_volumes=0\nauto_include_network_volumes=0\n',encoding='utf-8')
   if db.exists():
    try:subprocess.run([str(local_exe),'-instance',instance,'-exit','-wait'],cwd=str(data),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),check=False)
    except (OSError,subprocess.TimeoutExpired):pass
   flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
   args=[str(local_exe),'-instance',instance,'-config',str(ini),'-db',str(db),'-no-auto-index','-volumes','','-folders',str(root),'-startup']
   self.everything_proc=subprocess.Popen(args,cwd=str(data),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=flags)
   self.everything_key=key;self.everything_instance=instance;self.everything_data=data;self.everything_exe=local_exe;self.everything_cli=source_cli;self.everything_root=root
  return local_exe,source_cli,instance,data,root

 def search_row_matches(self,row,term,mode):
  query=(term or '').strip().casefold()
  if not query:return True
  name=str(row.get('name') or '')
  rel=str(row.get('rel') or '')
  ext=str(row.get('ext') or '')
  tags=str(row.get('tags') or '')
  if mode=='اسم الملف':source=name
  elif mode=='المسار':source=rel
  elif mode=='الامتداد':
   source=ext
   query=query.lstrip('*.')
  elif mode=='الهاشتاج':source=tags
  else:source=' '.join((name,rel,ext,tags))
  # Keep the result gate consistent with Everything's default AND behavior:
  # unquoted words may occur anywhere in the selected fields, while a quoted
  # phrase must occur contiguously. This gate also prevents a project-root
  # name from making every result appear to match a path search.
  terms=[phrase or word for phrase,word in re.findall(r'"([^"]+)"|(\S+)',query)]
  if not terms:terms=[query]
  folded=source.casefold()
  return all(term in folded for term in terms)

 def everything_search_worker(self,token,term,mode,root):
  temp_csv=None
  try:
   local_exe,cli,instance,data,root=self.prepare_everything_search(root)
   temp_csv=data/f'search-{secrets.token_hex(8)}.csv'
   args=[str(cli),'-instance',instance,'-timeout','20000','-path',str(root),'-full-path','-count','10000','-export-csv',str(temp_csv),'-utf8-bom']
   search_text=term
   if mode=='الامتداد':
    extension=term.strip().lower().lstrip('*.')
    search_text='ext:'+extension if extension else ''
   elif mode in ('الكل','المسار'):
    args.append('-match-path')
   if search_text:args.extend(['-search',search_text])
   result=subprocess.run(args,cwd=str(data),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=28,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),check=False)
   if result.returncode not in (0,9):
    detail=result.stderr.decode('utf-8','replace').strip()[:180] if result.stderr else f'رمز الخطأ {result.returncode}'
    raise RuntimeError(detail or 'تعذر الاتصال بمحرك البحث')
   paths=[]
   if temp_csv.is_file():
    root_text=os.path.normcase(str(root))
    with temp_csv.open('r',encoding='utf-8-sig',errors='replace',newline='') as f:
     for row in csv.reader(f):
      for value in row:
       value=value.strip().strip('"')
       if not value or not os.path.isabs(value):continue
       try:
        p=Path(value).resolve()
        if os.path.commonpath((root_text,os.path.normcase(str(p))))!=root_text:continue
       except (OSError,ValueError):continue
       if p.is_file():paths.append(p)
       break
   with connect() as c:indexed=c.execute("select f.*,group_concat(t.tag, ' ') tags from files f left join tags t on t.path=f.path where f.project=? group by f.path",(root.name,)).fetchall()
   by_path={os.path.normcase(r['path']):dict(r) for r in indexed};rows=[];seen=set()
   for p in paths:
    key=os.path.normcase(str(p))
    if key in seen:continue
    seen.add(key);item=by_path.get(key)
    if item is None:
     try:st=p.stat();rel=p.relative_to(root).as_posix()
     except (OSError,ValueError):continue
     item={'path':str(p),'project':root.name,'rel':rel,'name':p.name,'ext':p.suffix.lower(),'size':st.st_size,'mtime':st.st_mtime,'last_open':None,'tags':''}
    rows.append(item)
   if mode=='الكل':
    for r in indexed:
     item=dict(r)
     if self.search_row_matches(item,term,'الهاشتاج') and os.path.normcase(item['path']) not in seen:
      seen.add(os.path.normcase(item['path']));rows.append(item)
   # Everything's path matching includes the project folder itself. Recheck
   # against project-relative fields so a word in the root name cannot match
   # every file in the project.
   rows=[r for r in rows if self.search_row_matches(r,term,mode)]
   note=f'محرك Everything · {len(rows):,} نتيجة داخل هذا المشروع'
   if len(rows)>=10000:note+=' · يعرض أول 10,000 نتيجة'
   self.searchq.put((token,rows,note))
  except Exception as exc:
   rows=[]
   try:
    with connect() as c:rows=[dict(r) for r in c.execute("select f.*,group_concat(t.tag, ' ') tags from files f left join tags t on t.path=f.path where f.project=? group by f.path",(root.name,)).fetchall()]
    rows=[r for r in rows if self.search_row_matches(r,term,mode)]
   except Exception:rows=[]
   self.searchq.put((token,rows,f'بحث محلي احتياطي · محرك Everything غير متاح: {str(exc)[:100]}'))
  finally:
   if temp_csv:
    try:temp_csv.unlink(missing_ok=True)
    except OSError:pass

 def render_search_results(self,*_):
  if not hasattr(self,'search_nb') or not self.search_nb.winfo_exists():return
  term=self.search_query.get().strip().casefold();mode=self.search_mode.get();rows=list(getattr(self,'search_cache',[]))
  self.search_serial+=1;token=self.search_serial
  if self.search_future and not self.search_future.done():self.search_future.cancel()
  if term and mode!='الهاشتاج':
   self.search_status.set('جارٍ البحث بمحرك Everything داخل المشروع…')
   self.search_future=self.search_executor.submit(self.everything_search_worker,token,term,mode,self.root.resolve())
   return
  if term:
   rows=[r for r in rows if self.search_row_matches(r,term,mode)]
  self.render_search_rows(rows,'الفهرس المحلي'+(' · بحث بالهاشتاج' if term else ''))

 def render_search_rows(self,rows,source_note=''):
  if not hasattr(self,'search_nb') or not self.search_nb.winfo_exists():return
  term=self.search_query.get().strip();mode=self.search_mode.get()
  kinds=sorted({classify(r['ext'] or '') for r in rows},key=lambda x:(x not in ('لوحات CAD','PDF','Excel','Word','الصور'),x.casefold()))
  counts={k:sum(1 for r in rows if classify(r['ext'] or '')==k) for k in kinds};labels=['كل النتائج']+kinds
  if self.search_type not in labels:self.search_type='كل النتائج'
  self.search_rendering=True
  for tab in self.search_nb.tabs():self.search_nb.forget(tab)
  self.search_views={};self.search_tab_types={}
  for kind in labels:
   subset=rows if kind=='كل النتائج' else [r for r in rows if classify(r['ext'] or '')==kind]
   title=f'{kind} · {len(subset):,}';frame=tk.Frame(self.search_nb,bg='white');frame.grid_rowconfigure(0,weight=1);frame.grid_columnconfigure(0,weight=1);self.search_nb.add(frame,text=title,image=self.file_icon_image(self.type_icon_path(kind)),compound='left');tree=self.make_list(frame);tree.grid(row=0,column=0,sticky='nsew');ybar=ttk.Scrollbar(frame,orient='vertical',command=tree.yview);ybar.grid(row=0,column=1,sticky='ns');xbar=ttk.Scrollbar(frame,orient='horizontal',command=tree.xview);xbar.grid(row=1,column=0,sticky='ew');tree.configure(yscrollcommand=ybar.set,xscrollcommand=xbar.set)
   for r in sorted(subset,key=lambda x:(self.search_sort_key(x),x['rel'].casefold()),reverse=self.sort_desc):
    rowtag=self.file_row_tag(r['path']);
    if rowtag.startswith('file_ext_'):tree.tag_configure(rowtag,background='#ffffff')
    tree.insert('','end',iid=r['path'],values=(r['name'],'☐',r['ext'] or 'ملف',sizefmt(r['size']),stamp(r['mtime']),r['last_open'] or '—',tag_badges(r['tags'] or ''),r['rel']),image=self.file_icon_image(r['path']),tags=(rowtag,))
   tree.bind('<Double-1>',lambda e,tr=tree:self.open_file(Path(tr.selection()[0])) if tr.selection() else None)
   self.search_views[title]=tree;self.search_tab_types[title]=kind
   if kind==self.search_type:self.search_nb.select(frame)
  self.search_rendering=False
  self.search_status.set(f'{len(rows):,} نتيجة في {self.project} · {source_note} · بحث في {mode.lower()}'+(f' عن «{term}»' if term else ''))
  self.title(f'Rasd | بحث {len(rows):,} نتيجة | {self.project}')

 def search_sort_key(self,r):
  fields={'name':r['name'].casefold(),'type':(r['ext'] or '').casefold(),'size':r['size'] or 0,'mtime':r['mtime'] or 0,'opened':r['last_open'] or '', 'tags':(r['tags'] or '').casefold(),'path':r['rel'].casefold()}
  return fields.get(self.sort_col,r['name'].casefold())

 def schedule_search_results(self,*_):
  if getattr(self,'search_job',None):self.after_cancel(self.search_job)
  if getattr(self,'search_history_job',None):self.after_cancel(self.search_history_job)
  self.search_job=self.after(130,self.render_search_results)
  self.search_history_job=self.after(900,self.record_search_history)
 def dwg_preview_cache_path(self,p):
  p=Path(p);st=p.stat()
  def cache_relative_path(value):
   value=Path(value)
   try:return str(value.resolve().relative_to(LOG.resolve()))
   except ValueError:return value.name
  parts=[cache_relative_path(p),str(st.st_mtime_ns),str(st.st_size)]
  for ext in ('.pdf','.png','.jpg','.jpeg'):
   side=p.with_suffix(ext)
   try:
    if side.is_file():ss=side.stat();parts.extend((cache_relative_path(side),str(ss.st_mtime_ns),str(ss.st_size)))
   except OSError:pass
  key=hashlib.sha1('|'.join(parts).encode('utf-8')).hexdigest()
  return LOG/'.preview_cache'/(key+'.png')

 def preview_selected(self,tree):
  sel=tree.selection()
  if not sel:return
  self.preview_token+=1
  event=getattr(self,'activity_rows',{}).get(str(sel[0]))
  if event:
   self.hide_excel_preview();self.preview_current_path=None
   try:self.preview_related_strip.grid_remove()
   except (AttributeError,tk.TclError):pass
   target=event['path'] or 'داخل البرنامج';when=event['occurred_at']
   try:target=Path(target).resolve().relative_to(self.root.resolve()).as_posix()
   except (OSError,ValueError):pass
   meta=f"النشاط: {event['action']}\nالتفاصيل: {event['details']}\nالتاريخ: {when}\nالمسار: {target}"
   self.render_preview(self.make_card(event['action'],'HISTORY',event['details']),meta);return
  p=Path(sel[0])
  if p.is_dir():
   if getattr(self,'preview_current_path',None)!=str(p.resolve()):self.log_activity('معاينة مجلد',f'عرض المجلد «{p.name}»',path=p)
   self.preview_current_path=str(p.resolve());self.render_related_strip(p,[])
   self.render_preview(self.make_card(p.name,'مجلد','انقر مرتين لفتح محتوياته.'),f'المجلد: {p.name}\nانقر مرتين لفتحه.');return
  self.hide_excel_preview()
  if getattr(self,'preview_current_path',None)!=str(p.resolve()):
   self.preview_page=0;self.preview_zoom=1.0;self.preview_current_path=str(p.resolve());self.log_activity('معاينة ملف',f'عرض معاينة «{p.name}»',path=p)
  try:st=p.stat();rel=p.relative_to(self.root).as_posix()
  except OSError:return
  with connect() as c:tags=[r[0] for r in c.execute('select tag from tags where path=? order by tag',(str(p.resolve()),))];r=c.execute('select last_open from files where path=?',(str(p.resolve()),)).fetchone()
  related=[]
  if p.suffix.lower() in ('.dwg','.dxf','.pdf'):
   try:related=[x for x in p.parent.iterdir() if x.is_file() and x.stem.casefold()==p.stem.casefold() and x.suffix.lower() in ('.dwg','.dxf','.pdf','.png','.jpg','.jpeg') and x!=p]
   except OSError:pass
  meta=f'الملف: {p.name}\nالنوع: {p.suffix or "بدون امتداد"}\nالحجم: {sizefmt(st.st_size)}\nالمجلد: {rel}\nتاريخ الملف: {stamp(st.st_mtime)}\nآخر فتح: {r[0] if r and r[0] else "لم يفتح بعد"}\nالهاشتاجات: {" ".join(tags) or "لا توجد"}'
  self.render_related_strip(p,related)
  if related:meta+='\nلوحات مرتبطة متاحة أسفل المعاينة: '+', '.join(x.name for x in related[:3])
  token=self.preview_token;self.preview_meta.configure(text=meta+'\n\nجارٍ تجهيز المعاينة…');self.preview_image.delete('all');self.preview_image.create_text(24,24,text='جارٍ تجهيز المعاينة…',anchor='nw',fill='#617789')
  key=(str(p.resolve()),st.st_mtime_ns,st.st_size,self.preview_page,str(self.dwg_preview_cache_path(p)) if p.suffix.lower()=='.dwg' else '')
  cached=self.preview_cache.get(key)
  if cached:
   self.preview_cache.move_to_end(key);image,note=cached;self.previewq.put((token,image.copy(),meta+'\n\n'+note));return
  if p.suffix.lower()=='.dwg':
   try:
    cad_png=self.dwg_preview_cache_path(p)
    if cad_png.is_file():
     with Image.open(cad_png) as cached_image:image=cached_image.convert('RGB').copy()
     note='معاينة DWG مخزنة · تم فتحها مباشرة من الذاكرة المؤقتة';self.preview_cache[key]=(image.copy(),note);self.previewq.put((token,image,meta+'\n\n'+note,key,note));return
   except (OSError,ValueError):pass
  if self.preview_future and not self.preview_future.done():
   proc=getattr(self,'cad_preview_process',None)
   if proc and proc.poll() is None and getattr(self,'cad_preview_path',None)!=p.resolve():
    try:proc.kill()
    except OSError:pass
   self.preview_future.cancel()
  if p.suffix.lower() in ('.xlsx','.xls','.xlsm','.xlsb','.csv','.tsv'):
   self.preview_meta.configure(text=meta+'\n\nجارٍ تجهيز معاينة ورقة Excel…');self.preview_image.delete('all');self.preview_image.create_text(24,24,text='جارٍ تجهيز معاينة Excel…',anchor='nw',fill='#617789')
   self.preview_future=self.preview_executor.submit(self.preview_excel_worker,p,token,meta,None,key)
  else:
   if p.suffix.lower()=='.dwg':
    self.render_preview(self.make_card(p.name,'DWG','جارٍ البحث عن معاينة جاهزة أو تحويل اللوحة في الخلفية…'),meta+'\n\nجارٍ تجهيز المعاينة. سيظهر الرسم هنا فور اكتمالها، وتُحفظ لتفتح أسرع لاحقًا.')
    self.preview_future=self.cad_preview_executor.submit(self.dwg_preview_worker,p,token,meta,key)
   else:self.preview_future=self.preview_executor.submit(self.preview_worker,p,token,meta,key)

 def preview_excel_worker(self,p,token,meta,sheet_name=None,key=None,start_row=1):
  try:
   p=Path(p);start_row=max(1,int(start_row));page_size=EXCEL_PREVIEW_PAGE_SIZE;max_columns=12;ext=p.suffix.lower();names=[];rows=[];total_rows=None;has_more=False
   if key is None:
    stat=p.stat();key=(str(p.resolve()),stat.st_mtime_ns,stat.st_size,start_row)
   if ext in ('.csv','.tsv'):
    name='CSV' if ext=='.csv' else 'TSV';names=[name]
    with p.open('r',encoding='utf-8-sig',errors='replace',newline='') as f:
     reader=csv.reader(f,delimiter='\t' if ext=='.tsv' else ',')
     for row_number,row in enumerate(reader,1):
      if row_number<start_row:continue
      if len(rows)>=page_size:has_more=True;break
      rows.append(row[:max_columns])
   elif ext=='.xlsb' and open_xlsb_workbook:
    with open_xlsb_workbook(str(p)) as book:
     names=list(book.sheets)
     if not names:raise RuntimeError('لا توجد أوراق في المصنف')
     name=sheet_name if sheet_name in names else names[0]
     with book.get_sheet(name) as sheet:
      for row_number,row in enumerate(sheet.rows(sparse=True),1):
       if row_number<start_row:continue
       if len(rows)>=page_size:has_more=True;break
       rows.append([cell.v if cell is not None else None for cell in row[:max_columns]])
   elif ext=='.xls' and xlrd:
    book=xlrd.open_workbook(str(p),on_demand=True)
    try:
     names=book.sheet_names()
     if not names:raise RuntimeError('لا توجد أوراق في المصنف')
     name=sheet_name if sheet_name in names else names[0];ws=book.sheet_by_name(name);total_rows=ws.nrows;end=min(total_rows,start_row+page_size-1)
     rows=[[ws.cell_value(r,c) for c in range(min(ws.ncols,max_columns))] for r in range(start_row-1,end)]
     has_more=end<total_rows
    finally:book.release_resources()
   elif openpyxl:
    wb=openpyxl.load_workbook(p,read_only=True,data_only=True)
    try:
     names=wb.sheetnames
     if not names:raise RuntimeError('لا توجد أوراق في المصنف')
     name=sheet_name if sheet_name in names else names[0];ws=wb[name];total_rows=ws.max_row or 0;end=min(total_rows,start_row+page_size)
     raw=[list(row) for row in ws.iter_rows(min_row=start_row,max_row=end,max_col=max_columns,values_only=True)] if total_rows and start_row<=total_rows else []
     rows=raw[:page_size];has_more=len(raw)>page_size
    finally:wb.close()
   else:raise RuntimeError('مكتبة قراءة Excel غير متاحة')
   last_row=start_row+len(rows)-1
   range_text=f'الصفوف {start_row:,}–{last_row:,}' if rows else f'لا توجد صفوف تبدأ من {start_row:,}'
   if total_rows is not None:range_text+=f' من {total_rows:,}'
   note=f'ورقة {name} · {range_text}'
   self.previewq.put(('excel',token,str(p),meta,names,name,rows,start_row,total_rows,has_more,key))
  except Exception as e:
   note=f'تعذر عرض ورقة Excel: {str(e)[:90]}'
   self.previewq.put(('image',token,self.make_card(Path(p).name,'Excel',note),meta+'\n\n'+note,key,note))

 def hide_excel_preview(self):
  frame=getattr(self,'excel_preview_frame',None)
  if frame is not None:
   try:
    if frame.winfo_exists():frame.destroy()
   except tk.TclError:pass
  self.excel_preview_frame=None
  try:self.preview_image.grid()
  except (tk.TclError,AttributeError):pass

 def render_excel_preview(self,path,meta,names,sheet_name,rows,start_row=1,total_rows=None,has_more=False,key=None):
  canvas=self.preview_image;parent=canvas.master;self.hide_excel_preview();canvas.grid_remove()
  self.preview_excel_path=Path(path);self.preview_excel_meta=meta;self.preview_excel_names=names;self.preview_excel_selected=sheet_name;self.excel_preview_start_row=start_row;self.excel_preview_total_rows=total_rows;self.excel_preview_has_more=has_more;self.excel_preview_key=key
  frame=tk.Frame(parent,bg='#eef2f5');frame.grid(row=1,column=0,sticky='nsew',padx=5,pady=5);frame.grid_rowconfigure(1,weight=1);frame.grid_columnconfigure(0,weight=1);self.excel_preview_frame=frame
  toolbar=tk.Frame(frame,bg='#dfe7ec');toolbar.grid(row=0,column=0,columnspan=2,sticky='ew',pady=(0,4))
  tk.Label(toolbar,text='Excel',bg='#dfe7ec',fg='#24744f',font=('Segoe UI',9,'bold')).pack(side='left',padx=7,pady=4)
  self.excel_formula=tk.StringVar(value='حدد خلية لعرض محتواها');self.excel_cell_name=tk.StringVar(value='—')
  tk.Entry(toolbar,textvariable=self.excel_cell_name,width=6,state='readonly',readonlybackground='#f5f7f8',relief='flat',justify='center',font=('Segoe UI',9)).pack(side='left',padx=(5,2),pady=3)
  tk.Entry(toolbar,textvariable=self.excel_formula,state='readonly',readonlybackground='white',relief='flat',font=('Segoe UI',9)).pack(side='left',fill='x',expand=True,padx=(2,6),pady=3)
  if len(names)>1:
   self.excel_sheet_box=ttk.Combobox(toolbar,values=names,state='readonly',width=12,justify='right',style='Office.TCombobox');self.excel_sheet_box.set(sheet_name);self.excel_sheet_box.pack(side='right',padx=4);self.excel_sheet_box.bind('<<ComboboxSelected>>',self.excel_sheet_changed)
  cols=max(1,max((len(r) for r in rows),default=1));letters=[self.excel_col_name(i+1) for i in range(cols)]
  tree=ttk.Treeview(frame,columns=letters,show='tree headings',selectmode='browse');tree.heading('#0',text='#');tree.column('#0',width=42,minwidth=42,stretch=False,anchor='center')
  for col in letters:tree.heading(col,text=col);tree.column(col,width=92,minwidth=70,stretch=False,anchor='w')
  ybar=ttk.Scrollbar(frame,orient='vertical',command=tree.yview);xbar=ttk.Scrollbar(frame,orient='horizontal',command=tree.xview);tree.configure(yscrollcommand=ybar.set,xscrollcommand=xbar.set)
  tree.grid(row=1,column=0,sticky='nsew');ybar.grid(row=1,column=1,sticky='ns');xbar.grid(row=2,column=0,sticky='ew')
  for offset,row in enumerate(rows):
   row_number=start_row+offset;values=[self.excel_cell(v) for v in row]+['']*(cols-len(row));tree.insert('','end',iid=str(row_number),text=str(row_number),values=values)
  tree.tag_configure('sheet_header',background='#e7eef3',foreground='#19394e')
  if start_row==1 and rows and tree.exists('1'):tree.item('1',tags=('sheet_header',))
  tree.bind('<<TreeviewSelect>>',lambda e:self.excel_cell_selected(tree));tree.bind('<ButtonRelease-1>',lambda e:self.excel_cell_selected(tree),add='+');tree.bind('<Next>',lambda e:(self.load_excel_preview_page(1),'break'));tree.bind('<Prior>',lambda e:(self.load_excel_preview_page(-1),'break'));self.excel_preview_tree=tree
  nav=tk.Frame(frame,bg='#e4ebef');nav.grid(row=3,column=0,columnspan=2,sticky='ew',pady=(4,0))
  self.excel_page_label=tk.StringVar(value='')
  self.excel_page_prev_button=ttk.Button(nav,text='← السابق',command=lambda:self.load_excel_preview_page(-1),state=('normal' if start_row>1 else 'disabled'));self.excel_page_prev_button.pack(side='left',padx=4,pady=3)
  self.excel_page_next_button=ttk.Button(nav,text='التالي →',command=lambda:self.load_excel_preview_page(1),state=('normal' if has_more else 'disabled'));self.excel_page_next_button.pack(side='left',padx=2,pady=3)
  last_row=start_row+len(rows)-1;range_text=f'الصفوف {start_row:,}–{last_row:,}' if rows else 'لا توجد بيانات في هذه الورقة'
  if total_rows is not None:range_text+=f' من {total_rows:,}'
  self.excel_page_label.set(range_text);tk.Label(nav,textvariable=self.excel_page_label,bg='#e4ebef',fg='#526b7c',font=('Segoe UI',8,'bold')).pack(side='right',padx=8)
  self.preview_meta.configure(text=meta+'\n\nمعاينة Excel تفاعلية · غيّر الورقة أو استخدم أزرار السابق والتالي للتنقل بين الصفوف.')

 def excel_col_name(self,n):
  out=''
  while n:n,rem=divmod(n-1,26);out=chr(65+rem)+out
  return out

 def excel_cell(self,value):
  if value is None:return ''
  if isinstance(value,float) and value.is_integer():return str(int(value))
  return str(value).replace('\\n',' ')[:180]

 def excel_cell_selected(self,tree):
  sel=tree.selection()
  if not sel:return
  row=int(sel[0]);col=tree.identify_column(tree.winfo_pointerx()-tree.winfo_rootx());idx=max(0,min(len(tree.item(sel[0],"values"))-1,int(col.lstrip("#") or 1)-1));self.excel_cell_name.set(f'{self.excel_col_name(idx+1)}{row}');self.excel_formula.set(str(tree.item(sel[0],"values")[idx]))

 def excel_sheet_changed(self,e=None):
  if not getattr(self,'preview_excel_path',None):return
  name=self.excel_sheet_box.get();self.preview_token+=1;token=self.preview_token
  self.preview_meta.configure(text=self.preview_excel_meta+'\n\nجارٍ تحميل الورقة…')
  self.preview_future=self.preview_executor.submit(self.preview_excel_worker,self.preview_excel_path,token,self.preview_excel_meta,name)

 def load_excel_preview_page(self,delta):
  if not getattr(self,'preview_excel_path',None) or (delta>0 and not self.excel_preview_has_more):return
  start=max(1,self.excel_preview_start_row+delta*EXCEL_PREVIEW_PAGE_SIZE)
  if start==self.excel_preview_start_row:return
  if self.preview_future and not self.preview_future.done():self.preview_future.cancel()
  self.preview_token+=1;token=self.preview_token
  if getattr(self,'excel_page_label',None):self.excel_page_label.set('جارٍ تحميل الصفوف…')
  self.preview_future=self.preview_executor.submit(self.preview_excel_worker,self.preview_excel_path,token,self.preview_excel_meta,self.preview_excel_selected,self.excel_preview_key,start)

 def preview_worker(self,p,token,meta,key):
  try:
   image,note=self.make_file_preview(p)
   image.thumbnail((1400,1000),Image.Resampling.BILINEAR)
  except Exception as e:image,note=self.make_card(p.name,p.suffix.upper() or 'FILE','تعذرت معاينة المحتوى في هذه الصيغة.'),str(e)[:100]
  self.previewq.put((token,image,meta+'\n\n'+note,key,note))

 def dwg_preview_worker(self,p,token,meta,key):
  try:
   self.cad_preview_path=Path(p).resolve()
   quick_image,quick_note=self.make_file_preview(p,allow_autocad=False)
   if quick_note.startswith(('معاينة من الملف المرتبط','معاينة من ملف اللوحة المرتبط')):
    quick_image.thumbnail((1400,1000),Image.Resampling.BILINEAR);image,note=quick_image,quick_note
    cache_path=self.dwg_preview_cache_path(p);cache_path.parent.mkdir(parents=True,exist_ok=True)
    if not cache_path.exists():image.save(cache_path,format='PNG',optimize=False,compress_level=2)
    self.previewq.put((token,image.copy(),meta+'\n\n'+note,key,note));return
   if quick_note.startswith('صورة مصغرة من Windows'):
    quick_image.thumbnail((1400,1000),Image.Resampling.BILINEAR)
    self.previewq.put(('image',token,quick_image.copy(),meta+'\n\nمعاينة سريعة من Windows · يجري تجهيز معاينة الرسم في الخلفية.'))
   image=self.make_autocad_dwg_preview(p)
   if image:note='معاينة لوحة DWG من AutoCAD · تحفظ مؤقتًا لتسريع العرض التالي'
   else:image,note=quick_image,quick_note
   image.thumbnail((1400,1000),Image.Resampling.BILINEAR)
   if 'لم تتوفر' not in note and 'لم يعثر' not in note and 'صورة مصغرة من Windows' not in note:
    cache_path=self.dwg_preview_cache_path(p);cache_path.parent.mkdir(parents=True,exist_ok=True)
    if not cache_path.exists():image.save(cache_path,format='PNG',optimize=False,compress_level=2)
  except Exception as e:image,note=self.make_card(p.name,'DWG','تعذرت معاينة الرسم في الوقت الحالي.'),f'تعذرت معاينة الرسم: {str(e)[:90]}'
  self.previewq.put((token,image,meta+'\n\n'+note,key,note))

 def make_card(self,title,kind,note):
  image=Image.new('RGB',(1200,560),'#f7fafc');d=ImageDraw.Draw(image);d.rounded_rectangle((38,35,1160,525),radius=22,fill='white',outline='#c8d7e2',width=3);d.rounded_rectangle((70,70,220,220),radius=20,fill='#0b7785');font=self._font(34,True);small=self._font(24);d.text((106,120),kind[:6],font=small,fill='white');d.text((260,90),title[:60],font=font,fill='#173b50');d.text((260,165),note[:100],font=small,fill='#667d8d');return image

 def _font(self,size,bold=False):
  path=Path(os.environ.get('WINDIR',r'C:\Windows'))/'Fonts'/('segoeuib.ttf' if bold else 'segoeui.ttf')
  try:return ImageFont.truetype(str(path),size)
  except OSError:return ImageFont.load_default()

 def _text_image(self,title,lines,kind):
  image=Image.new('RGB',(1200,620),'white');d=ImageDraw.Draw(image);d.rectangle((0,0,1200,62),fill='#e7eef3');d.text((22,14),title[:78],font=self._font(25,True),fill='#173b50');d.text((1090,18),kind,font=self._font(20,True),fill='#087e8b')
  y=82;regular=self._font(18);small=self._font(15)
  expanded=[]
  for line in lines:
   expanded.extend(textwrap.wrap(str(line).replace('\t','    '),width=118,break_long_words=True) or [''])
  for line in expanded[:27]:
   d.text((24,y),line,font=regular,fill='#29475a');y+=20
   if y>590:break
  d.rectangle((1,1,1198,618),outline='#c8d7e2',width=2);return image

 def _table_image(self,title,rows,kind):
  rows=[list(r)[:8] for r in rows[:22]];cols=max([len(r) for r in rows] or [1]);im=Image.new('RGB',(1200,560),'white');d=ImageDraw.Draw(im);head=self._font(18,True);font=self._font(15);d.rectangle((0,0,1200,48),fill='#e7eef3');d.text((18,10),title[:78],font=head,fill='#173b50');top=58;row_h=min(27,max(20,(480-top)//max(len(rows),1)));col_w=1200//cols
  for ri,row in enumerate(rows):
   y=top+ri*row_h;fill='#0b7785' if ri==0 else ('#f2f7f9' if ri%2==0 else 'white');d.rectangle((0,y,1200,y+row_h),fill=fill)
   for ci in range(cols):
    x=ci*col_w;d.rectangle((x,y,x+col_w,y+row_h),outline='#c8d7e2',width=1);value='' if ci>=len(row) or row[ci] is None else str(row[ci]).replace('\n',' ');limit=max(5,int(col_w/9));d.text((x+6,y+4),value[:limit]+('…' if len(value)>limit else ''),font=head if ri==0 else font,fill='white' if ri==0 else '#29475a')
  d.rectangle((1,1,1198,558),outline='#c8d7e2',width=2);return im

 def make_file_preview(self,p,allow_autocad=True):
  ext=p.suffix.lower()
  if ext in ('.png','.jpg','.jpeg','.bmp','.gif','.tif','.tiff'):
   with Image.open(p) as im:
    im.thumbnail((1400,1000),Image.Resampling.BILINEAR);return im.convert('RGB'),'معاينة الصورة'
  if ext=='.pdf' and fitz:
   with fitz.open(str(p)) as doc:
    page_index=max(0,min(self.preview_page,len(doc)-1));page=doc.load_page(page_index);rect=page.rect;scale=min(1.8,1800/max(rect.width,1),1400/max(rect.height,1));pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False,annots=False)
    with Image.open(io.BytesIO(pix.tobytes('png'))) as im:return im.convert('RGB'),f'صفحة {page_index+1} من {len(doc)} · PDF'
  if ext=='.pdf' and PdfReader:
   page=PdfReader(str(p)).pages[0];text=page.extract_text() or ''
   if text.strip():return self._text_image(p.name,text.splitlines(),'PDF'),'معاينة نص الصفحة الأولى'
   try:return Image.open(io.BytesIO(page.images[0].data)).convert('RGB'),'صورة مستخرجة من الصفحة الأولى'
   except Exception:return self.make_card(p.name,'PDF','صفحة مصورة؛ محتوى النص غير قابل للاستخراج.'),'معاينة الصفحة الأولى'
  if ext in ('.docx',) and Document:
   doc=Document(p);lines=[x.text for x in doc.paragraphs if x.text.strip()]
   for table in doc.tables[:2]:
    for row in table.rows[:12]:lines.append('  |  '.join(c.text.replace('\n',' ') for c in row.cells))
   return self._text_image(p.name,lines or ['المستند لا يحتوي نصًا قابلًا للمعاينة.'],'Word'),'معاينة محتوى المستند'
  if ext in ('.txt','.md','.log','.ini','.xml','.json','.html','.py','.sql'):
   lines=p.read_text(encoding='utf-8',errors='replace').splitlines();return self._text_image(p.name,lines,'TEXT'),'معاينة بداية الملف'
  if ext in ('.csv','.tsv'):
   with p.open('r',encoding='utf-8-sig',errors='replace',newline='') as f:rows=list(csv.reader(f,delimiter='\t' if ext=='.tsv' else ','))[:28]
   return self._text_image(p.name,['  |  '.join(row[:8]) for row in rows],'TABLE'),'معاينة أول الصفوف'
  if ext=='.dxf' and ezdxf:return self.make_dxf_preview(p)
  if ext=='.dwg':
   for side_ext in ('.pdf','.png','.jpg','.jpeg'):
    side=p.with_suffix(side_ext)
    if side.exists():
     image,note=self.make_file_preview(side);return image,f'معاينة من الملف المرتبط {side.name} · {note}'
    try:
     with connect() as c:
      candidates=[Path(r['path']) for r in c.execute("select path from files where project=? and lower(name)=lower(?) and lower(ext) in ('.pdf','.png','.jpg','.jpeg')",(self.project,p.stem+".pdf"))]
      if not candidates:
       candidates=[Path(r['path']) for r in c.execute("select path from files where project=? and lower(name) in (lower(?),lower(?),lower(?),lower(?)) and lower(ext) in ('.png','.jpg','.jpeg')",(self.project,p.stem+'.png',p.stem+'.jpg',p.stem+'.jpeg',p.stem+'.pdf'))]
     for side in candidates:
      if side.is_file():
       image,note=self.make_file_preview(side);return image,f'معاينة من ملف اللوحة المرتبط {side.name} · {note}'
    except Exception:pass
    if allow_autocad:
     cad_image=self.make_autocad_dwg_preview(p)
     if cad_image:return cad_image,'معاينة لوحة DWG من AutoCAD · تحفظ مؤقتًا لتسريع العرض التالي'
   shell=self.shell_thumbnail(p)
   if shell:return shell,'صورة مصغرة من Windows أو برنامج CAD المثبت'
   note='لم تتوفر معاينة مصغرة أو ملف لوحة مرتبط، ولم يتوفر AutoCAD للتحويل. يمكن فتح الرسم بالنقر المزدوج.'
   return self.make_card(p.name,'DWG',note),note
  shell=self.shell_thumbnail(p)
  if shell:return shell,'معاينة مصغرة من Windows أو البرنامج المرتبط بالملف'
  return self.make_card(p.name,ext[1:].upper() if ext else 'FILE',f'ملف {sizefmt(p.stat().st_size)} · معاينة النظام غير متاحة لهذه الصيغة.'),'معاينة معلومات الملف'

 def shell_thumbnail(self,p):
  if os.name!='nt':return None
  class GUID(ctypes.Structure):_fields_=[('Data1',ctypes.c_ulong),('Data2',ctypes.c_ushort),('Data3',ctypes.c_ushort),('Data4',ctypes.c_ubyte*8)]
  class SIZE(ctypes.Structure):_fields_=[('cx',ctypes.c_long),('cy',ctypes.c_long)]
  class HEADER(ctypes.Structure):_fields_=[('biSize',ctypes.c_uint32),('biWidth',ctypes.c_int32),('biHeight',ctypes.c_int32),('biPlanes',ctypes.c_ushort),('biBitCount',ctypes.c_ushort),('biCompression',ctypes.c_uint32),('biSizeImage',ctypes.c_uint32),('biXPelsPerMeter',ctypes.c_int32),('biYPelsPerMeter',ctypes.c_int32),('biClrUsed',ctypes.c_uint32),('biClrImportant',ctypes.c_uint32)]
  class INFO(ctypes.Structure):_fields_=[('bmiHeader',HEADER),('bmiColors',ctypes.c_uint32*3)]
  item=ctypes.c_void_p();bitmap=ctypes.c_void_p();hdc=None
  try:
   iid=GUID();ctypes.windll.ole32.CLSIDFromString('{bcc18b79-ba16-442f-80c4-8a59c30c463b}',ctypes.byref(iid))
   comhr=ctypes.windll.ole32.CoInitializeEx(None,2);com_initialized=comhr>=0
   create=ctypes.windll.shell32.SHCreateItemFromParsingName;create.argtypes=[ctypes.c_wchar_p,ctypes.c_void_p,ctypes.POINTER(GUID),ctypes.POINTER(ctypes.c_void_p)];create.restype=ctypes.c_long
   if create(str(p),None,ctypes.byref(iid),ctypes.byref(item))<0:return None
   vtable=ctypes.cast(item,ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
   get_image=ctypes.WINFUNCTYPE(ctypes.c_long,ctypes.c_void_p,SIZE,ctypes.c_uint,ctypes.POINTER(ctypes.c_void_p))(vtable[3])
   if get_image(item,SIZE(1100,540),0x01,ctypes.byref(bitmap))<0:return None
   class BITMAP(ctypes.Structure):_fields_=[('bmType',ctypes.c_long),('bmWidth',ctypes.c_long),('bmHeight',ctypes.c_long),('bmWidthBytes',ctypes.c_long),('bmPlanes',ctypes.c_ushort),('bmBitsPixel',ctypes.c_ushort),('bmBits',ctypes.c_void_p)]
   bm=BITMAP();ctypes.windll.gdi32.GetObjectW(bitmap,ctypes.sizeof(bm),ctypes.byref(bm));w,h=bm.bmWidth,abs(bm.bmHeight)
   if not w or not h:return None
   info=INFO();info.bmiHeader=HEADER(ctypes.sizeof(HEADER),w,-h,1,32,0,w*h*4,0,0,0,0);buf=(ctypes.c_ubyte*(w*h*4))();hdc=ctypes.windll.gdi32.CreateCompatibleDC(None)
   if not ctypes.windll.gdi32.GetDIBits(hdc,bitmap,0,h,buf,ctypes.byref(info),0):return None
   return Image.frombuffer('RGBA',(w,h),bytes(buf),'raw','BGRA',0,1).convert('RGB')
  except Exception:return None
  finally:
   if hdc:ctypes.windll.gdi32.DeleteDC(hdc)
   if bitmap:ctypes.windll.gdi32.DeleteObject(bitmap)
   if item:
    try:
     vt=ctypes.cast(item,ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents;release=ctypes.WINFUNCTYPE(ctypes.c_ulong,ctypes.c_void_p)(vt[2]);release(item)
    except Exception:pass
   if locals().get('com_initialized',False):ctypes.windll.ole32.CoUninitialize()

 def autocad_core_console_path(self):
  if getattr(self,'_autocad_core_resolved',False):return getattr(self,'_autocad_core_path',None)
  candidates=[];found=shutil.which('accoreconsole.exe')
  if found:candidates.append(Path(found))
  for base in (Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Autodesk',Path(os.environ.get('ProgramFiles(x86)','C:/Program Files (x86)'))/'Autodesk',Path('C:/2020')):
   try:candidates.extend(base.glob('AutoCAD */accoreconsole.exe'))
   except OSError:pass
  try:
   import winreg
   for hive_path in (r'SOFTWARE\Autodesk\AutoCAD',r'SOFTWARE\WOW6432Node\Autodesk\AutoCAD'):
    try:key=winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,hive_path)
    except OSError:continue
    with key:
     for i in range(winreg.QueryInfoKey(key)[0]):
      try:release=winreg.EnumKey(key,i);release_key=winreg.OpenKey(key,release)
      except OSError:continue
      with release_key:
       for j in range(winreg.QueryInfoKey(release_key)[0]):
        try:product=winreg.EnumKey(release_key,j);product_key=winreg.OpenKey(release_key,product)
        except OSError:continue
        with product_key:
         try:location=Path(winreg.QueryValueEx(product_key,'GlobUPILocation')[0])
         except OSError:continue
         for base in (location,location.parent,location.parent.parent):candidates.append(base/'accoreconsole.exe')
  except (ImportError,OSError):pass
  seen=set()
  for candidate in candidates:
   try:
    candidate=candidate.resolve()
    if str(candidate).casefold() not in seen and candidate.is_file():self._autocad_core_path=candidate;self._autocad_core_resolved=True;return candidate
    seen.add(str(candidate).casefold())
   except OSError:continue
  self._autocad_core_path=None;self._autocad_core_resolved=True;return None

 def short_windows_path(self,path):
  try:
   buf=ctypes.create_unicode_buffer(32768);fn=ctypes.windll.kernel32.GetShortPathNameW;fn.argtypes=[ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_uint];fn.restype=ctypes.c_uint;n=fn(str(path),buf,len(buf))
   if n and n<len(buf):return buf.value
  except Exception:pass
  return str(path)

 def crop_cad_preview(self,image):
  try:
   image=image.convert('RGB');w,h=image.size
   mask=ImageChops.difference(image,Image.new('RGB',(w,h),'white')).convert('L').point(lambda value:255 if value>20 else 0)
   box=mask.getbbox()
   if not box:return image
   x0,y0,x1,y1=box;pad=max(8,int(max(x1-x0,y1-y0)*.06));x0=max(0,x0-pad);x1=min(w,x1+pad);y0=max(0,y0-pad);y1=min(h,y1+pad)
   crop=image.crop((x0,y0,x1,y1));scale=min(w/max(crop.width,1),h/max(crop.height,1));size=(max(1,int(crop.width*scale)),max(1,int(crop.height*scale)))
   crop=crop.resize(size,Image.Resampling.BILINEAR);canvas=Image.new('RGB',(w,h),'white');canvas.paste(crop,((w-size[0])//2,(h-size[1])//2));return canvas
  except Exception:return image

 def make_autocad_dwg_preview(self,p):
  if fitz is None:return None
  core=self.autocad_core_console_path()
  if not core:return None
  temp_dwg=None;plot_log=p.parent/'plot.log';plot_log_existed=False;plot_log_data=None;plot_log_stat=None
  try:
   plot_log_existed=plot_log.is_file()
   if plot_log_existed:plot_log_data=plot_log.read_bytes();plot_log_stat=plot_log.stat()
   png=self.dwg_preview_cache_path(p);cache=png.parent;cache.mkdir(parents=True,exist_ok=True);key=png.stem
   if png.is_file():
    with Image.open(png) as im:return im.convert('RGB').copy()
   pdf=cache/(key+'.pdf');script=cache/(key+'.scr');fd,temp_name=tempfile.mkstemp(prefix='.officelog-preview-',suffix=p.suffix,dir=str(p.parent));os.close(fd);temp_dwg=Path(temp_name);shutil.copy2(p,temp_dwg)
   output_path=self.short_windows_path(pdf)
   commands=('FILEDIA','0','CMDDIA','0','EXPERT','5','_.ZOOM','_E','_.-PLOT','Y','Model','DWG To PDF.pc3','ANSI A (11.00 x 8.50 Inches)','Inches','Landscape','N','Extents','Fit','Center','Y','monochrome.ctb','N','Wireframe',f'"{output_path}"','N','Y','_.QUIT','N','')
   script.write_text('\n'.join(commands),encoding='mbcs')
   process=subprocess.Popen([str(core),'/i',str(temp_dwg.resolve()),'/s',str(script),'/l','en-US'],cwd=str(p.parent),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));self.cad_preview_process=process
   try:process.wait(timeout=75)
   except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)
   finally:
    if getattr(self,'cad_preview_process',None) is process:self.cad_preview_process=None
   if not pdf.is_file() or pdf.stat().st_size<2048:return None
   with fitz.open(str(pdf)) as document:
    if not len(document):return None
    page=document.load_page(0);rect=page.rect;scale=min(2.2,1800/max(rect.width,1),1300/max(rect.height,1));pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False,annots=False)
    with Image.open(io.BytesIO(pix.tobytes('png'))) as im:image=im.convert('RGB').copy()
   image=self.crop_cad_preview(image)
   image.thumbnail((1400,1000),Image.Resampling.LANCZOS)
   image.save(png,format='PNG',optimize=False,compress_level=2)
   cached=sorted(cache.glob('*.png'),key=lambda f:f.stat().st_mtime,reverse=True)
   for old in cached[250:]:
    try:old.unlink()
    except OSError:pass
   return image
  except Exception:return None
  finally:
   temp_dwg=locals().get('temp_dwg');temp_related=(temp_dwg.with_suffix('.bak'),temp_dwg.with_suffix('.dwl'),temp_dwg.with_suffix('.dwl2')) if temp_dwg else ()
   for temporary in (locals().get('pdf'),locals().get('script'),temp_dwg,*temp_related):
    if temporary:
     try:temporary.unlink(missing_ok=True)
     except OSError:pass
   try:
    if plot_log_existed:
     plot_log.write_bytes(plot_log_data);os.utime(plot_log,ns=(plot_log_stat.st_atime_ns,plot_log_stat.st_mtime_ns))
    else:plot_log.unlink(missing_ok=True)
   except OSError:pass

 def make_dxf_preview(self,p):
  doc=ezdxf.readfile(str(p));entities=list(doc.modelspace());points=[];shapes=[]
  for ent in entities:
   typ=ent.dxftype()
   try:
    if typ=='LINE':pts=[(ent.dxf.start.x,ent.dxf.start.y),(ent.dxf.end.x,ent.dxf.end.y)];shapes.append(('line',pts))
    elif typ in ('LWPOLYLINE','POLYLINE'):
     pts=[(v[0],v[1]) if typ=='LWPOLYLINE' else (v.dxf.location.x,v.dxf.location.y) for v in (ent.get_points('xy') if typ=='LWPOLYLINE' else ent.vertices)]
     if len(pts)>1:shapes.append(('poly',pts+[pts[0]] if ent.closed else pts))
    elif typ=='CIRCLE':
     c=ent.dxf.center;r=ent.dxf.radius;pts=[(c.x-r,c.y-r),(c.x+r,c.y+r)];shapes.append(('circle',[(c.x,c.y,r)]))
    elif typ=='ARC':
     c=ent.dxf.center;r=ent.dxf.radius;a0=ent.dxf.start_angle;a1=ent.dxf.end_angle
     if a1<a0:a1+=360
     pts=[(c.x+r*math.cos(math.radians(a)),c.y+r*math.sin(math.radians(a))) for a in [a0+(a1-a0)*i/32 for i in range(33)]];shapes.append(('line',pts))
    else:continue
    points.extend(pts)
   except Exception:continue
  if not points:return self.make_card(p.name,'DXF','لم يتم العثور على عناصر رسم قابلة للمعاينة.'),'معاينة الرسم'
  minx=min(x for x,y in points);maxx=max(x for x,y in points);miny=min(y for x,y in points);maxy=max(y for x,y in points);dx=max(maxx-minx,1e-6);dy=max(maxy-miny,1e-6);scale=min(1100/dx,480/dy);ox=(1200-dx*scale)/2;oy=(560-dy*scale)/2
  def xy(x,y):return (ox+(x-minx)*scale,560-(oy+(y-miny)*scale))
  im=Image.new('RGB',(1200,560),'white');d=ImageDraw.Draw(im);d.rectangle((1,1,1198,558),outline='#c8d7e2',width=2);d.rectangle((0,0,1200,42),fill='#e7eef3');d.text((18,10),p.name,font=self._font(18,True),fill='#173b50')
  for kind,pts in shapes:
   if kind=='circle':
    x,y,r=pts[0];cx,cy=xy(x,y);rr=r*scale;d.ellipse((cx-rr,cy-rr,cx+rr,cy+rr),outline='#087e8b',width=2)
   else:d.line([xy(x,y) for x,y in pts],fill='#087e8b',width=2)
  return im,'معاينة هندسية لعناصر DXF'

 def render_preview(self,image,meta):
  self.hide_excel_preview();self.preview_base=image.copy();self.preview_meta.configure(text=meta);self.paint_preview()

 def paint_preview(self):
  canvas=self.preview_image
  if not canvas.winfo_exists() or not getattr(self,'preview_base',None):return
  self.update_idletasks();max_w=max(240,canvas.winfo_width()-16);max_h=max(140,canvas.winfo_height()-16);im=self.preview_base.copy();im.thumbnail((max_w,max_h),Image.Resampling.LANCZOS)
  if getattr(self,'preview_zoom',1.0)!=1.0:im=im.resize((max(1,int(im.width*self.preview_zoom)),max(1,int(im.height*self.preview_zoom))),Image.Resampling.LANCZOS)
  self.preview_photo=ImageTk.PhotoImage(im);canvas.delete('all');self.preview_image_id=canvas.create_image(max(canvas.winfo_width(),im.width)//2,max(canvas.winfo_height(),im.height)//2,image=self.preview_photo,anchor='center');canvas.configure(scrollregion=(0,0,max(canvas.winfo_width(),im.width),max(canvas.winfo_height(),im.height)))

 def preview_pan_start(self,event):self.preview_pan=(event.x,event.y)

 def preview_pan_move(self,event):
  if not hasattr(self,'preview_pan') or not getattr(self,'preview_image_id',None):return
  dx=event.x-self.preview_pan[0];dy=event.y-self.preview_pan[1];self.preview_image.move(self.preview_image_id,dx,dy);self.preview_pan=(event.x,event.y)

 def preview_wheel(self,event):self.zoom_preview(.1 if event.delta>0 else -.1);return 'break'

 def zoom_preview(self,amount):
  self.preview_zoom=max(.35,min(3.0,getattr(self,'preview_zoom',1.0)+amount))
  if getattr(self,'preview_base',None):self.paint_preview()

 def change_pdf_page(self,amount):
  p=Path(getattr(self,'preview_current_path',''))
  if not p.is_file() or p.suffix.lower()!='.pdf':return
  try:
   if fitz:
    with fitz.open(str(p)) as doc:count=len(doc)
   elif PdfReader:count=len(PdfReader(str(p)).pages)
   else:return
   page=self.preview_page+amount
   if 0<=page<count:
    self.preview_page=page;tree=self.file_tree
    if hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped() and self.search_nb.tabs():tree=self.search_views.get(self.search_nb.tab(self.search_nb.select(),'text'),tree)
    if tree and tree.exists(str(p.resolve())):tree.selection_set(str(p.resolve()));self.preview_selected(tree)
  except Exception:pass

if __name__ == '__main__':
 App().mainloop()
