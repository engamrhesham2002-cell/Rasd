# tasks_utils.py - الوظائف المساعدة وإدارة البيانات والملفات
from common import *
from storage import *

class TasksUtilsMixin:
 def _task_time_display(self,value):
  canonical=self._task_time_to_24(value)
  if canonical is None:return ''
  hour,minute=(int(part) for part in canonical.split(':'))
  return f'{hour%12 or 12:02d}:{minute:02d} '+('AM' if hour<12 else 'PM')

 def _task_time_to_24(self,value):
  text=str(value or '').strip().upper()
  try:
   if text.endswith((' AM',' PM')):
    clock,period=text.rsplit(' ',1);hour,minute=(int(part) for part in clock.split(':'))
    if not 1<=hour<=12 or not 0<=minute<60:return None
    hour=(hour%12)+(12 if period=='PM' else 0);return f'{hour:02d}:{minute:02d}'
   hour,minute=(int(part) for part in text.split(':'))
   if 0<=hour<24 and 0<=minute<60:return f'{hour:02d}:{minute:02d}'
  except (ValueError,TypeError):pass
  return None

 def _task_ampm(self,value):
  return self._task_time_display(value)

 def _task_project_names(self):
  try:return sorted((p.name for p in LOG.iterdir() if p.is_dir() and not p.name.startswith('.')),key=str.casefold)
  except OSError:return []

 def _task_parse_capture(self,text):
  priority=None;due=None;tags=[];remaining=[];today=date.today()
  for raw in str(text).strip().split():
   token=raw.strip('،,.;:()[]{}');lower=token.casefold().rstrip('!?')
   if re.fullmatch(r'!([1-3])',lower):priority=int(lower[1]);continue
   if token.startswith('#') and len(token)>1:tags.append(token[1:]);continue
   if lower in ('اليوم','النهارده','النهاردة','today'):due=today.isoformat();continue
   if lower in ('غدا','غدًا','بكره','بكرة','غداً','tomorrow'):due=(today+timedelta(days=1)).isoformat();continue
   if re.fullmatch(r'\d{4}-\d{2}-\d{2}',token):
    try:datetime.strptime(token,'%Y-%m-%d');due=token;continue
    except ValueError:pass
   remaining.append(raw)
  return ' '.join(remaining).strip(),due,priority,tags

 def _task_parse_date(self,text):
  value=str(text or '').strip()
  if not value:return None
  if value in ('اليوم','today'):return date.today().isoformat()
  if value in ('غدًا','غدا','غداً','tomorrow'):return (date.today()+timedelta(days=1)).isoformat()
  try:return datetime.strptime(value,'%Y-%m-%d').date().isoformat()
  except ValueError:raise ValueError('اختر الموعد من التقويم أو استخدم YYYY-MM-DD أو اليوم أو غدًا.')

 def _task_priority_num(self,value):return {'عاجلة':1,'عادية':2,'منخفضة':3}.get(str(value),2)
 
 def _task_date_text(self,value):
  if not value:return 'بدون موعد'
  target=datetime.strptime(value,'%Y-%m-%d').date();today=date.today()
  if target<today:return 'متأخرة · '+target.strftime('%d-%m-%Y')
  if target==today:return 'اليوم · '+target.strftime('%d-%m-%Y')
  if target==today+timedelta(days=1):return 'غدًا · '+target.strftime('%d-%m-%Y')
  return target.strftime('%d-%m-%Y')

 def _task_arabic_date(self,d,month_only=False):
  months=('يناير','فبراير','مارس','أبريل','مايو','يونيو','يوليو','أغسطس','سبتمبر','أكتوبر','نوفمبر','ديسمبر');weekdays=('الاثنين','الثلاثاء','الأربعاء','الخميس','الجمعة','السبت','الأحد');return (months[d.month-1]+' '+str(d.year)) if month_only else (weekdays[d.weekday()]+' '+f'{d.day:02d} '+months[d.month-1]+' '+str(d.year))

 def _task_document_folder(self,row):
  project=str(row['project'] or '').strip()
  if not project:raise ValueError('لا يمكن حفظ مستند المهمة بدون مشروع.')
  project_root=(LOG/project).resolve()
  if not is_project_path(project_root):raise ValueError('مسار المشروع خارج مجلد Log.')
  folder=project_root/'.tasks'
  old_folder=project_root/('مهام '+project)
  if old_folder.exists() and not folder.exists():
   try:old_folder.rename(folder)
   except OSError:folder=old_folder
  folder.mkdir(parents=True,exist_ok=True)
  if os.name == 'nt':
   try:
    import ctypes
    ctypes.windll.kernel32.SetFileAttributesW(str(folder), 2)
   except Exception: pass
  return folder

 def _task_ensure_document_artifacts(self,task_id):
  with connect() as c:row=c.execute('SELECT * FROM tasks WHERE id=?',(task_id,)).fetchone()
  if not row:return None
  folder=self._task_document_folder(row);safe_title=re.sub(r'[<>:"/\\|?*]','_',row['title']).strip()[:70] or 'مهمة'
  relative=row['document_rel']
  if relative:
   stored=(LOG/relative).resolve()
   if not is_project_path(stored) or stored.parent!=folder.resolve():raise ValueError('مسار مستند المهمة خارج مجلد المهمة.')
   text_path=stored if stored.suffix.casefold()=='.txt' else stored.with_suffix('.txt')
  else:text_path=folder/f'مهمة-{task_id}-{safe_title}.txt'
  content=row['description'] or ''
  try:subtasks=json.loads(row['subtasks']) if row['subtasks'] else []
  except Exception:subtasks=[]
  if subtasks:
   content += '\n\n--- خطوات التنفيذ ---\n'
   for s in subtasks:
    content += f"- [{'x' if s.get('done') else ' '}] {s.get('title', '')}\n"
  text_path.write_text(content,encoding='utf-8')
  attachment_path=folder/f'مرفقات المهمة {task_id}';attachment_path.mkdir(exist_ok=True)
  try:attachments=json.loads(row['attachments'] or '[]')
  except (ValueError,TypeError):attachments=[]
  try: rec = row['recurrence'] if row['recurrence'] else 'لا يوجد'
  except Exception: rec = 'لا يوجد'
  json_path=text_path.with_suffix('.json')
  metadata={'schema_version':1,'task_id':int(task_id),'title':row['title'],'project':row['project'],'due_date':row['due_date'],'start_time':row['start_time'],'end_time':row['end_time'],'priority':row['priority'],'tags':row['tags'],'recurrence':rec,'subtasks':subtasks,'attachments':attachments}
  json_path.write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
  mtime=text_path.stat().st_mtime
  with connect() as c:c.execute('UPDATE tasks SET document_rel=?,document_mtime=? WHERE id=?',(self._task_log_relative(text_path),mtime,task_id))
  return text_path

 def _task_log_relative(self,path):
  relative=os.path.relpath(str(Path(path).resolve()),str(Path(LOG).resolve()))
  if relative=='..' or relative.startswith('..'+os.sep):raise ValueError('مسار المستند خارج مجلد Log.')
  return relative.replace('\\','/')

 def _task_sync_text_documents(self,project=None):
  try:
   with connect() as c:
    sql='SELECT id,title,document_rel,document_mtime,subtasks FROM tasks WHERE document_rel IS NOT NULL';params=()
    if project:sql+=' AND project=?';params=(project,)
    rows=c.execute(sql,params).fetchall()
  except sqlite3.Error:return 0
  updates=[]
  for row in rows:
   try:
    stored=(LOG/row['document_rel']).resolve();path=stored if stored.suffix.casefold()=='.txt' else stored.with_suffix('.txt')
    if not is_project_path(path) or not path.is_file():continue
    mtime=path.stat().st_mtime
    if row['document_mtime'] is not None and abs(float(row['document_mtime'])-mtime)<0.001:continue
    content=path.read_text(encoding='utf-8',errors='replace')
    parts = content.split('--- خطوات التنفيذ ---')
    desc_part = parts[0].strip()
    lines=desc_part.splitlines()
    if lines and lines[0].strip().lstrip('#').strip()==str(row['title']).strip():desc_part='\n'.join(lines[1:]).lstrip('\n')
    new_subs_json = row['subtasks']
    if len(parts) > 1:
     parsed_subs = []
     for line in parts[1].splitlines():
      line = line.strip()
      if line.startswith('- [x]') or line.startswith('- [X]'): parsed_subs.append({'title': line[5:].strip(), 'done': True})
      elif line.startswith('- [ ]'): parsed_subs.append({'title': line[5:].strip(), 'done': False})
     new_subs_json = json.dumps(parsed_subs, ensure_ascii=False)
    updates.append((desc_part,new_subs_json,self._task_log_relative(path),mtime,datetime.now().strftime('%Y-%m-%d %H:%M:%S'),row['id']))
   except Exception:continue
  if updates:
   with connect() as c:c.executemany('UPDATE tasks SET description=?,subtasks=?,document_rel=?,document_mtime=?,updated_at=? WHERE id=?',updates)
  return len(updates)

 def _task_open_document(self,task_id):
  try:path=self._task_ensure_document_artifacts(task_id)
  except (OSError,ValueError,sqlite3.Error) as exc:return messagebox.showwarning('ملف المهمة',str(exc),parent=self)
  if path and path.is_file():
   try:os.startfile(str(path))
   except OSError as exc:messagebox.showerror('فتح ملف المهمة',str(exc),parent=self)

 def _task_attachment_values(self,row):
  try:values=json.loads(row['attachments'] or '[]')
  except (ValueError,TypeError):values=[]
  return [item for item in values if isinstance(item,dict) and item.get('path')]

 def _task_add_attachment_paths(self,task_id,paths):
  if not paths:return
  with connect() as c:row=c.execute('SELECT * FROM tasks WHERE id=?',(task_id,)).fetchone()
  if not row:return
  folder=self._task_document_folder(row);attach_dir=folder/f'مرفقات المهمة {task_id}';attachments=self._task_attachment_values(row)
  for item in paths:
   if isinstance(item,dict) and item.get('is_link'):
    if item not in attachments: attachments.append(item)
    continue
   source=Path(item)
   if not source.is_file():continue
   attach_dir.mkdir(exist_ok=True)
   target=attach_dir/(secrets.token_hex(4)+'_'+source.name);shutil.copy2(source,target);attachments.append({'name':source.name,'path':self._task_log_relative(target)})
  with connect() as c:c.execute('UPDATE tasks SET attachments=?,updated_at=? WHERE id=?',(json.dumps(attachments,ensure_ascii=False),datetime.now().strftime('%Y-%m-%d %H:%M:%S'),task_id))
  self._task_ensure_document_artifacts(task_id)

 def _task_remove_attachment(self,task_id,item):
  if not messagebox.askyesno('إزالة المرفق',f'إزالة الملف المرفق «{item.get("name","ملف")}» نهائياً من القرص الصلب؟',parent=self):return
  try:
   with connect() as c:owner=c.execute('SELECT * FROM tasks WHERE id=?',(task_id,)).fetchone()
   row_folder=self._task_document_folder(owner) if owner else None;path=(LOG/item['path']).resolve()
   if not item.get('is_link') and path.is_file() and row_folder and path.is_relative_to(row_folder.resolve()):path.unlink()
  except (OSError,ValueError):pass
  with connect() as c:row=c.execute('SELECT * FROM tasks WHERE id=?',(task_id,)).fetchone()
  if not row:return
  attachments=[x for x in self._task_attachment_values(row) if x.get('path')!=item.get('path')]
  with connect() as c:c.execute('UPDATE tasks SET attachments=?,updated_at=? WHERE id=?',(json.dumps(attachments,ensure_ascii=False),datetime.now().strftime('%Y-%m-%d %H:%M:%S'),task_id))
  self._task_ensure_document_artifacts(task_id)
  if getattr(self,'task_preview_task_id',None)==task_id:self._task_preview_selected()
  if getattr(self,'task_calendar_selected_id',None)==task_id:self._task_calendar_select_task(task_id)

 def _task_open_attachment(self, item):
  try:
   p = (LOG/item['path']).resolve()
   if not p.exists(): return messagebox.showwarning('غير موجود','الملف لم يعد موجوداً في المسار.',parent=self)
   if item.get('is_link'):
    self._task_jump_to_explorer(p)
   else:
    os.startfile(str(p))
  except Exception as exc: messagebox.showerror('خطأ',str(exc),parent=self)

 def _task_jump_to_explorer(self, target_path):
  p = Path(target_path).resolve()
  if not p.exists(): return
  try:
   rel = p.relative_to(LOG.resolve())
   self.project = rel.parts[0]
   self.root = (LOG/self.project).resolve()
  except ValueError: return
  self.current = p.parent; self.mode = 'folder'; self.folder_group = 'الكل'; self.view_mode = 'files'
  self.backstack=[]; self.forwardstack=[]
  if hasattr(self, 'hide_search_page'): self.hide_search_page()
  if hasattr(self, 'collection_button'): self.collection_button.pack_forget()
  self.build_explorer(); self.animate_window_in()
  iid = str(p)
  if getattr(self,'file_tree',None):
   try:self.file_tree.selection_set(iid);self.file_tree.focus(iid);self.file_tree.see(iid)
   except tk.TclError: pass

 def _task_link_project_file(self, pending, label, row, project_name, parent):
  if not project_name or project_name=='اختر مشروعًا…':return messagebox.showwarning('المشروع','يرجى اختيار المشروع أولاً من القائمة.',parent=parent)
  project_root = (LOG/project_name).resolve()
  if not project_root.exists(): return
  chosen=filedialog.askopenfilename(initialdir=str(project_root),parent=parent,title='اختر ملفاً من المشروع لربطه بالمهمة')
  if not chosen:return
  try:
   rel_path = Path(chosen).resolve().relative_to(LOG.resolve()).as_posix()
   pending.append({'name': '🔗 ' + Path(chosen).name, 'path': rel_path, 'is_link': True})
   base=len(self._task_attachment_values(row)) if row else 0
   label.set(f'{base+len(pending)} مرفق/رابط')
  except ValueError:messagebox.showwarning('مسار خاطئ','يجب اختيار ملف من داخل مجلد المشروع المختار.',parent=parent)

 def _task_delete_artifacts(self, task_ids):
  with connect() as c:rows = c.execute(f'SELECT * FROM tasks WHERE id IN ({",".join("?" for _ in task_ids)})', task_ids).fetchall()
  for row in rows:
   try:
    folder = self._task_document_folder(row)
    if row['document_rel']:
     stored = (LOG/row['document_rel']).resolve()
     if stored.is_file() and stored.parent == folder:
      stored.unlink(missing_ok=True);stored.with_suffix('.json').unlink(missing_ok=True);stored.with_suffix('.md').unlink(missing_ok=True)
    else:
     for f in folder.glob(f'مهمة-{row["id"]}-*.*'): f.unlink(missing_ok=True)
    attach_dir = folder/f'مرفقات المهمة {row["id"]}'
    if attach_dir.exists() and attach_dir.is_dir():shutil.rmtree(attach_dir, ignore_errors=True)
   except Exception: pass

 def _task_rollover_elapsed(self):
  now=datetime.now();today=now.date().isoformat();clock=now.strftime('%H:%M');stamp=now.strftime('%Y-%m-%d %H:%M:%S')
  try:
   with connect() as c:
    cur=c.execute("UPDATE tasks SET due_date=?,updated_at=? WHERE completed_at IS NULL AND due_date=? AND end_time IS NOT NULL AND end_time<>'' AND end_time<=?",((now.date()+timedelta(days=1)).isoformat(),stamp,today,clock))
    return cur.rowcount>0
  except sqlite3.Error:return False

 def _task_show_toast(self, title, message):
  toast = tk.Toplevel(self)
  toast.overrideredirect(True)
  toast.attributes('-topmost', True)
  toast.configure(bg='#102c3d')
  tk.Label(toast, text=title, fg='#4caf50', bg='#102c3d', font=('Segoe UI', 10, 'bold')).pack(anchor='e', padx=16, pady=(12, 2))
  tk.Label(toast, text=message, fg='white', bg='#102c3d', font=('Segoe UI', 9), wraplength=250, justify='right').pack(anchor='e', padx=16, pady=(0, 12))
  toast.update_idletasks();w, h = toast.winfo_width(), toast.winfo_height();x = self.winfo_screenwidth() - w - 25;y = self.winfo_screenheight() - h - 65;toast.geometry(f'{w}x{h}+{x}+{y}')
  def fade(alpha):
   if alpha > 0:
    toast.attributes('-alpha', alpha)
    try: self.after(50, lambda: fade(alpha - 0.05))
    except tk.TclError: pass
   else:
    try: toast.destroy()
    except tk.TclError: pass
  self.after(5000, lambda: fade(1.0))

 def _task_rollover_tick(self,token=None):
  if token is not None and token!=getattr(self,'task_rollover_token',None):return
  if not hasattr(self, 'notified_tasks'): self.notified_tasks = set()
  now = datetime.now(); upcoming = now + timedelta(minutes=15);today_iso = now.date().isoformat(); up_time = upcoming.strftime('%H:%M')
  try:
   with connect() as c:
    tasks = c.execute('SELECT id, title FROM tasks WHERE completed_at IS NULL AND due_date=? AND start_time=?', (today_iso, up_time)).fetchall()
    for t in tasks:
     if t['id'] not in self.notified_tasks:
      self._task_show_toast("⏳ مهمة تقترب (15 دقيقة)", t['title'])
      self.notified_tasks.add(t['id'])
  except Exception: pass
  if getattr(self,'task_calendar_active',False):
   if getattr(self,'task_calendar_drag_state',None) is None and self._task_rollover_elapsed():self._task_calendar_draw(preserve_scroll=True)
   self.after(30000,lambda:self._task_rollover_tick(token))
  elif getattr(self,'task_tree',None) and self.task_tree.winfo_exists():
   if self._task_rollover_elapsed():self._task_refresh_rows()
   self.after(30000,lambda:self._task_rollover_tick(token))