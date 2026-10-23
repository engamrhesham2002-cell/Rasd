import os,sys,sqlite3,subprocess,threading,queue,csv,io,textwrap,math,ctypes,hashlib,shutil,time,json,secrets,colorsys,tempfile,re,urllib.request,urllib.error,webbrowser
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
APP_VERSION='0.39'
LATEST_RELEASE_API='https://api.github.com/repos/engamrhesham2002-cell/Rasd/releases/latest'
UPDATE_HOME=Path(os.environ.get('LOCALAPPDATA',str(BASE)))/'Rasd'/'updates'
UPDATE_PENDING=UPDATE_HOME/'pending.json'
UPDATE_FAILURE=UPDATE_HOME/'update_failed.txt'
def start_scheduled_update(wait_pid,installer,target,app_path):
 if os.name!='nt':return False
 powershell=shutil.which('powershell.exe') or shutil.which('powershell')
 if not powershell:
  candidate=Path(os.environ.get('WINDIR',r'C:\Windows'))/'System32'/'WindowsPowerShell'/'v1.0'/'powershell.exe'
  if candidate.is_file():powershell=str(candidate)
 if not powershell:return False
 UPDATE_HOME.mkdir(parents=True,exist_ok=True)
 script=UPDATE_HOME/f'apply_update_{wait_pid}.ps1'
 body='''param([int]$WaitPid,[string]$InstallerPath,[string]$TargetPath,[string]$AppPath,[string]$PendingPath,[string]$FailurePath)
$ErrorActionPreference = 'Stop'
try {
  while (Get-Process -Id $WaitPid -ErrorAction SilentlyContinue) { Start-Sleep -Milliseconds 400 }
  $appName = [System.IO.Path]::GetFileName($AppPath)
  while ($true) {
    $running = Get-CimInstance Win32_Process -Filter "Name='$appName'" -ErrorAction SilentlyContinue | Where-Object { $_.ExecutablePath -ieq $AppPath }
    if (-not $running) { break }
    Start-Sleep -Milliseconds 500
  }
  $arguments = '/S "/D=' + $TargetPath + '"'
  $result = Start-Process -FilePath $InstallerPath -ArgumentList $arguments -Wait -PassThru
  if ($result.ExitCode -eq 0) {
    Remove-Item -LiteralPath $PendingPath -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $FailurePath -Force -ErrorAction SilentlyContinue
    Start-Process -FilePath $AppPath
  } else {
    Set-Content -LiteralPath $FailurePath -Value "The installer exited with code $($result.ExitCode)." -Encoding UTF8
    Remove-Item -LiteralPath $PendingPath -Force -ErrorAction SilentlyContinue
    Start-Process -FilePath $AppPath
  }
} catch {
  Set-Content -LiteralPath $FailurePath -Value $_.Exception.Message -Encoding UTF8
  Remove-Item -LiteralPath $PendingPath -Force -ErrorAction SilentlyContinue
  if (Test-Path -LiteralPath $AppPath) { Start-Process -FilePath $AppPath }
}
'''
 try:
  script.write_text(body,encoding='utf-8-sig')
  subprocess.Popen([powershell,'-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-WindowStyle','Hidden','-File',str(script),str(wait_pid),str(installer),str(target),str(app_path),str(UPDATE_PENDING),str(UPDATE_FAILURE)],cwd=str(UPDATE_HOME),stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
  return True
 except (OSError,ValueError):return False
def queue_pending_update(installer,mode,tag):
 if not getattr(sys,'frozen',False) or not Path(installer).is_file():return False
 portable=(BASE/'.rasd-portable').is_file()
 if mode!=('portable' if portable else 'standard'):return False
 record={'tag':tag,'installer':str(Path(installer).resolve()),'target':str(BASE.resolve()),'mode':mode,'queued_at':time.time()}
 try:
  UPDATE_HOME.mkdir(parents=True,exist_ok=True)
  temp=UPDATE_PENDING.with_suffix('.json.tmp');temp.write_text(json.dumps(record,ensure_ascii=False),encoding='utf-8');temp.replace(UPDATE_PENDING);return True
 except OSError:return False
def launch_pending_update_at_start():
 if not getattr(sys,'frozen',False) or not UPDATE_PENDING.is_file():return False
 try:
  record=json.loads(UPDATE_PENDING.read_text(encoding='utf-8'));installer=Path(record['installer']).resolve();target=Path(record['target']).resolve();mode=record['mode']
  portable=(BASE/'.rasd-portable').is_file()
  if target!=BASE.resolve() or mode!=('portable' if portable else 'standard') or not installer.is_file():raise ValueError('The pending update is missing or does not match this installation.')
  if start_scheduled_update(os.getpid(),installer,target,Path(sys.executable).resolve()):return True
  raise OSError('Windows PowerShell could not be started to apply the update.')
 except Exception as exc:
  try:UPDATE_FAILURE.parent.mkdir(parents=True,exist_ok=True);UPDATE_FAILURE.write_text(str(exc),encoding='utf-8');UPDATE_PENDING.unlink(missing_ok=True)
  except OSError:pass
  return False
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

