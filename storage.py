# Rasd - مجلد المشاريع، قاعدة البيانات، تصنيف الملفات، الأيقونات، فلاتر Everything
from common import *

def resolve_project_root():
 base_dir = Path(os.environ.get('LOCALAPPDATA', str(BASE))) / 'Rasd'
 root = (base_dir / 'Log').resolve()
 root.mkdir(parents=True, exist_ok=True)
 return root

LOG = resolve_project_root()
DB = LOG / '.office_index.db'

def is_project_path(path):
 try:
  return Path(path).resolve() != LOG.resolve() and Path(path).resolve().is_relative_to(LOG.resolve())
 except (OSError, ValueError, AttributeError):
  return False

def is_task_internal_artifact(path):
 try:
  p = Path(path); parts = [part.casefold() for part in p.parts]; in_task_folder = any(part.startswith('مهام ') for part in parts)
  return in_task_folder and p.name.startswith('مهمة-') and p.suffix.casefold() in ('.json', '.md')
 except (OSError, TypeError, ValueError):
  return False

GROUPS = {'لوحات CAD': {'.dwg', '.dxf'}, 'PDF': {'.pdf'}, 'Excel': {'.xlsx', '.xls', '.xlsm', '.xlsb', '.csv', '.tsv'}, 'Word': {'.doc', '.docx'}, 'الصور': {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tif', '.tiff'}, 'أخرى': set()}
EXCEL_PREVIEW_PAGE_SIZE = 100

@contextmanager
def connect():
 c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
 try:
  yield c; c.commit()
 finally:
  c.close()

with connect() as c:
 c.executescript('CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY,project TEXT,rel TEXT,name TEXT,ext TEXT,size INTEGER,mtime REAL,last_open TEXT,indexed TEXT); CREATE TABLE IF NOT EXISTS tags(path TEXT,tag TEXT,PRIMARY KEY(path,tag)); CREATE TABLE IF NOT EXISTS file_tag_catalog(project TEXT,tag TEXT,created TEXT,PRIMARY KEY(project,tag)); CREATE TABLE IF NOT EXISTS folder_tags(project TEXT,path TEXT,tag TEXT,created TEXT,PRIMARY KEY(project,path,tag)); CREATE TABLE IF NOT EXISTS extension_colors(ext TEXT PRIMARY KEY,accent TEXT UNIQUE,soft TEXT); CREATE TABLE IF NOT EXISTS search_history(project TEXT,query TEXT,mode TEXT,searched_at TEXT,PRIMARY KEY(project,query,mode)); CREATE TABLE IF NOT EXISTS saved_searches(project TEXT,query TEXT,mode TEXT,created TEXT,PRIMARY KEY(project,query,mode)); CREATE TABLE IF NOT EXISTS project_search_state(project TEXT PRIMARY KEY,query TEXT,mode TEXT,file_type TEXT); CREATE TABLE IF NOT EXISTS favorites(project TEXT,path TEXT,kind TEXT,created TEXT,PRIMARY KEY(project,path)); CREATE TABLE IF NOT EXISTS project_view_state(project TEXT PRIMARY KEY,current_rel TEXT,mode TEXT,folder_filter TEXT,project_filter TEXT,discipline TEXT,sort_col TEXT,sort_desc INTEGER,column_widths TEXT); CREATE TABLE IF NOT EXISTS file_changes(id INTEGER PRIMARY KEY AUTOINCREMENT,project TEXT,path TEXT,kind TEXT,changed_at TEXT); CREATE INDEX IF NOT EXISTS idx_changes_project ON file_changes(project,changed_at); CREATE TABLE IF NOT EXISTS project_visits(project TEXT PRIMARY KEY,last_visit TEXT); CREATE TABLE IF NOT EXISTS file_open_history(id INTEGER PRIMARY KEY AUTOINCREMENT,project TEXT NOT NULL,path TEXT NOT NULL,opened_at TEXT NOT NULL,UNIQUE(project,path,opened_at)); CREATE INDEX IF NOT EXISTS idx_open_history_project ON file_open_history(project,opened_at); CREATE TABLE IF NOT EXISTS project_scan_state(project TEXT PRIMARY KEY,initial_scan_done INTEGER NOT NULL DEFAULT 0); CREATE TABLE IF NOT EXISTS activity_log(id INTEGER PRIMARY KEY AUTOINCREMENT,project TEXT NOT NULL,action TEXT NOT NULL,details TEXT NOT NULL,path TEXT,occurred_at TEXT NOT NULL); CREATE INDEX IF NOT EXISTS idx_activity_project ON activity_log(project,occurred_at); CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,description TEXT NOT NULL DEFAULT \'\',project TEXT NOT NULL DEFAULT \'\',due_date TEXT,start_time TEXT,end_time TEXT,priority INTEGER NOT NULL DEFAULT 2,tags TEXT NOT NULL DEFAULT \'\',created_at TEXT NOT NULL,updated_at TEXT NOT NULL,completed_at TEXT,attachments TEXT NOT NULL DEFAULT \'[]\',document_rel TEXT); CREATE INDEX IF NOT EXISTS idx_tasks_project_due ON tasks(project,due_date,completed_at); CREATE INDEX IF NOT EXISTS idx_tasks_completed ON tasks(completed_at,updated_at); CREATE TABLE IF NOT EXISTS workspace_tools(id INTEGER PRIMARY KEY AUTOINCREMENT, project TEXT NOT NULL, title TEXT NOT NULL, kind TEXT NOT NULL, path TEXT NOT NULL);')
 
 # التريجر السحري لمنع مجلد المهام من الظهور في الأكسبلورر للأبد
 c.executescript('''
 CREATE TRIGGER IF NOT EXISTS ignore_dot_tasks_insert BEFORE INSERT ON files WHEN NEW.rel = '.tasks' OR NEW.rel LIKE '.tasks/%' OR NEW.rel LIKE '%/.tasks/%' OR NEW.rel LIKE '%/.tasks' BEGIN SELECT RAISE(IGNORE); END;
 CREATE TRIGGER IF NOT EXISTS ignore_dot_tasks_update BEFORE UPDATE ON files WHEN NEW.rel = '.tasks' OR NEW.rel LIKE '.tasks/%' OR NEW.rel LIKE '%/.tasks/%' OR NEW.rel LIKE '%/.tasks' BEGIN SELECT RAISE(IGNORE); END;
 ''')
 c.execute("DELETE FROM files WHERE rel = '.tasks' OR rel LIKE '.tasks/%' OR rel LIKE '%/.tasks/%' OR rel LIKE '%/.tasks'")

with connect() as c:
 task_columns = {r['name'] for r in c.execute('PRAGMA table_info(tasks)')}
 for column in ('start_time', 'end_time', 'rich_text', 'attachments', 'document_rel', 'document_mtime'):
  if column not in task_columns:
   c.execute(f'ALTER TABLE tasks ADD COLUMN {column} TEXT')
 c.execute('CREATE INDEX IF NOT EXISTS idx_tasks_status_due_project ON tasks(completed_at,due_date,project,priority,start_time)')
 c.execute('CREATE INDEX IF NOT EXISTS idx_tasks_project_status_due ON tasks(project,completed_at,due_date,priority,start_time)')
with connect() as c:
 c.execute("insert or ignore into file_open_history(project,path,opened_at) select project,path,last_open from files where coalesce(last_open,'')<>''")
with connect() as c:
 c.execute('CREATE TABLE IF NOT EXISTS app_settings(key TEXT PRIMARY KEY,value TEXT NOT NULL)')
try:
 with connect() as c:
  c.executescript("CREATE VIRTUAL TABLE IF NOT EXISTS task_fts USING fts5(title,description,project,tags,content='tasks',content_rowid='id'); CREATE TRIGGER IF NOT EXISTS task_fts_ai AFTER INSERT ON tasks BEGIN INSERT INTO task_fts(rowid,title,description,project,tags) VALUES(new.id,new.title,new.description,new.project,new.tags); END; CREATE TRIGGER IF NOT EXISTS task_fts_ad AFTER DELETE ON tasks BEGIN INSERT INTO task_fts(task_fts,rowid,title,description,project,tags) VALUES('delete',old.id,old.title,old.description,old.project,old.tags); END; CREATE TRIGGER IF NOT EXISTS task_fts_au AFTER UPDATE OF title,description,project,tags ON tasks BEGIN INSERT INTO task_fts(task_fts,rowid,title,description,project,tags) VALUES('delete',old.id,old.title,old.description,old.project,old.tags); INSERT INTO task_fts(rowid,title,description,project,tags) VALUES(new.id,new.title,new.description,new.project,new.tags); END;")
  if not c.execute("SELECT 1 FROM app_settings WHERE key='task_fts_initialized'").fetchone():
   c.execute("INSERT INTO task_fts(task_fts) VALUES('rebuild')")
   c.execute("INSERT INTO app_settings(key,value) VALUES('task_fts_initialized','1')")
except sqlite3.OperationalError:
 pass

def stamp(t):
 try:
  return datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M')
 except:
  return '—'

def sizefmt(n):
 for u in ('B', 'KB', 'MB', 'GB'):
  if n < 1024:
   return f'{n:.0f} {u}'
  n /= 1024
 return f'{n:.1f} TB'

def classify(ext):
 ext = (ext or '').lower()
 if ext and not ext.startswith('.'):
  ext = '.' + ext
 for k, v in GROUPS.items():
  if k != 'أخرى' and ext in v:
   return k
 return ext[1:].upper() if ext else 'بدون امتداد'

def file_icon(path, is_dir=False):
 if is_dir:
  return '📁'
 ext = Path(path).suffix.lower()
 return {'.pdf': '📕', '.xlsx': '📗', '.xls': '📗', '.xlsm': '📗', '.csv': '📗', '.doc': '📘', '.docx': '📘', '.dwg': '📐', '.dxf': '📐', '.png': '🖼', '.jpg': '🖼', '.jpeg': '🖼', '.bmp': '🖼'}.get(ext, '📄')

def type_icon(kind):
 return {'لوحات CAD': '📐', 'PDF': '📕', 'Excel': '📗', 'Word': '📘', 'الصور': '🖼', 'أخرى': '📄'}.get(kind, '📄')

def tag_badges(value):
 tags = [x for x in (value or '').split() if x]
 out = []
 for i, tag in enumerate(tags):
  key = tag.casefold()
  if any(k in key for k in ('ري', 'irrig')):
   dot = '🟢'
  elif 'زراع' in key:
   dot = '🟡'
  elif 'صح' in key or 'sewag' in key:
   dot = '🔵'
  elif 'مطر' in key or 'storm' in key:
   dot = '🟣'
  elif 'معتمد' in key or 'approved' in key:
   dot = '✅'
  else:
   dot = ('🟦', '🟠', '🟣', '🟢')[i % 4]
  out.append(f'{dot} {tag}')
 return '   '.join(out)

FILTER_COLUMNS = ['Name', 'Case', 'Whole Word', 'Path', 'Diacritics', 'Prefix', 'Suffix', 'Ignore Punctuation', 'Ignore Whitespace', 'Regex', 'Search', 'Columns', 'Sort', 'Descending', 'View', 'Macro', 'Key']

def sync_everything_filters(data, instance, extensions):
 path = data / f'Filters-{instance}.csv'; rows = []
 if path.exists():
  for encoding in ('utf-8-sig', 'mbcs', 'cp1252'):
   try:
    with path.open('r', encoding=encoding, newline='') as f:
     rows = list(csv.reader(f))
    break
   except (UnicodeError, OSError, csv.Error):
    rows = []
 if rows and rows[0] and rows[0][0].strip().casefold() == 'name':
  rows = rows[1:]
 managed = '[Project Type] '
 preserved = [row for row in rows if not (row and row[0].startswith(managed))]
 for ext in sorted({e.lower().lstrip('.') for e in extensions if e and e.startswith('.') and e[1:].replace('_', '').replace('-', '').replace('.', '').isalnum()}):
  macro = 'ol_' + ''.join(ch if ch.isalnum() else '_' for ch in ext)
  preserved.append([managed + ext.upper() + f' (*.{ext})', 0, 0, 0, 0, 0, 0, 0, 0, 0, 'ext:' + ext, '', '', 0, '', macro, ''])
 temp = path.with_suffix('.csv.tmp')
 with temp.open('w', encoding='utf-8-sig', newline='') as f:
  writer = csv.writer(f, lineterminator='\n'); writer.writerow(FILTER_COLUMNS); writer.writerows((row + [''] * len(FILTER_COLUMNS))[:len(FILTER_COLUMNS)] for row in preserved)
 temp.replace(path)