# tasks_actions.py - إضافة/إنجاز/تأجيل/حذف/تصدير المهام
from common import *
from storage import *
from tasks_utils import next_recurring_date

class TasksActionsMixin:
 def _task_add_quick(self):
  raw=self.task_quick_var.get().strip()
  if not raw or raw=='اكتب مهمة سريعة':return
  title,smart_due,smart_priority,tags=self._task_parse_capture(raw)
  if not title:return messagebox.showwarning('المهام','اكتب وصف المهمة أولًا.',parent=self)
  try:due=self._task_parse_date(self.task_due_var.get()) if self.task_due_var.get().strip() else smart_due
  except ValueError as exc:return messagebox.showwarning('موعد المهمة',str(exc),parent=self)
  start=self.task_start_var.get() or None;end=self.task_end_var.get() or None
  if (start or end) and not due:return messagebox.showwarning('موعد المهمة','حدد تاريخًا قبل إضافة وقت للمهمة.',parent=self)
  if start and end and end<=start:return messagebox.showwarning('وقت المهمة','يجب أن يكون وقت النهاية بعد البداية في اليوم نفسه.',parent=self)
  project=self.task_scope or self.task_project_var.get();available=self._task_project_names()
  if not project or project=='اختر مشروعًا…' or project not in available:return messagebox.showwarning('المشروع','أنشئ مشروعًا أولًا، ثم اختر المشروع الذي ستتبعه المهمة.',parent=self)
  tag_value=self.task_quick_tags_var.get() if hasattr(self,'task_quick_tags_var') else '';extra_tags=[t.strip().lstrip('#') for t in re.split(r'[،,\s]+',tag_value) if t.strip()]
  tags=list(dict.fromkeys(tags+extra_tags));now=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
  with connect() as c:cursor=c.execute('INSERT INTO tasks(title,project,due_date,start_time,end_time,priority,tags,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',(title,project,due,start,end,smart_priority or self._task_priority_num(self.task_priority_var.get()),','.join(tags),now,now));task_id=cursor.lastrowid
  try:self._task_ensure_document_artifacts(task_id)
  except (OSError,ValueError,sqlite3.Error) as exc:messagebox.showwarning('مستند المهمة',str(exc),parent=self)
  self.task_quick_var.set('');self.task_quick_tags_var.set('');self.task_due_var.set('');self.task_start_var.set('');self.task_end_var.set('');self.task_priority_var.set('عادية');self._task_refresh_rows();self.task_quick_entry.focus_set()

 def _task_selected_ids(self):
  if not getattr(self,'task_tree',None):return []
  ids=[]
  for iid in self.task_tree.selection():
   if str(iid).isdigit():ids.append(int(iid))
  return ids
  
 def _task_toggle_done(self):
  ids=self._task_selected_ids()
  if not ids:return messagebox.showinfo('المهام','حدد مهمة واحدة على الأقل.',parent=self)
  now=datetime.now(); now_str=now.strftime('%Y-%m-%d %H:%M:%S')
  with connect() as c:
   for task_id in ids:
    try: row=c.execute('SELECT * FROM tasks WHERE id=?',(task_id,)).fetchone()
    except sqlite3.Error: continue
    if row:
     if row['completed_at']:
      c.execute('UPDATE tasks SET completed_at=NULL, updated_at=? WHERE id=?',(now_str,task_id))
     else:
      c.execute('UPDATE tasks SET completed_at=?, updated_at=? WHERE id=?',(now_str,now_str,task_id))
      try: rec = row['recurrence'] if row['recurrence'] else None
      except Exception: rec = None
      if rec and rec != 'لا يوجد' and row['due_date']:
       try:
        next_d = next_recurring_date(row['due_date'], rec)
        if next_d is None: raise ValueError('نوع تكرار غير معروف')
        new_subs = []
        try:
         if row['subtasks']:
          for s in json.loads(row['subtasks']):
           s['done'] = False
           new_subs.append(s)
        except Exception: pass
        c.execute('''INSERT INTO tasks(title,description,rich_text,project,due_date,start_time,end_time,priority,tags,attachments,subtasks,recurrence,created_at,updated_at)
                     VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                  (row['title'], row['description'], '', row['project'], next_d.isoformat(), row['start_time'], row['end_time'], row['priority'], row['tags'], '[]', json.dumps(new_subs, ensure_ascii=False), rec, now_str, now_str))
       except Exception: pass
  self._task_refresh_rows()
  
 def _task_postpone(self):
  if self.task_filter!='today':return
  ids=self._task_selected_ids()
  if not ids:return messagebox.showinfo('المهام','حدد المهمة التي تريد تأجيلها.',parent=self)
  now=datetime.now().strftime('%Y-%m-%d %H:%M:%S');new_due=(date.today()+timedelta(days=1)).isoformat()
  with connect() as c:
   for task_id in ids:c.execute('UPDATE tasks SET due_date=?,start_time=NULL,end_time=NULL,updated_at=? WHERE id=? AND completed_at IS NULL',(new_due,now,task_id))
  self._task_refresh_rows()
   
 def _task_delete_selected(self):
  ids=self._task_selected_ids()
  if not ids:return messagebox.showinfo('المهام','حدد مهمة واحدة على الأقل.',parent=self)
  if not messagebox.askyesno('حذف المهام',f'حذف {len(ids)} مهمة وملفاتها المرفقة نهائياً؟',parent=self):return
  self._task_delete_artifacts(ids)
  with connect() as c:c.executemany('DELETE FROM tasks WHERE id=?',[(x,) for x in ids])
  self._task_refresh_rows()

 def _task_export_print(self):
  if not hasattr(self, 'task_tree'): return
  items = []
  for iid in self.task_tree.get_children():
   if self.task_tree.item(iid, 'tags') and 'day_group' in self.task_tree.item(iid, 'tags'):
    items.append(('header', self.task_tree.item(iid, 'values')[0]))
   else:
    items.append(('task', self.task_tree.item(iid, 'values')))
  html = "<html dir='rtl'><head><meta charset='utf-8'><title>تقرير المهام - Rasd</title>"
  html += "<style>body{font-family:'Segoe UI', Tahoma, Arial; padding:30px; color:#E2F1E8; background:#070A0E;} "
  html += "table{width:100%; border-collapse:collapse; margin-top:25px; background:#0D1219; border: 1px solid #1C2A38;} "
  html += "th, td{border:1px solid #1C2A38; padding:12px; text-align:right;} "
  html += "th{background-color:#131B24; color:#00FF66; font-weight:bold;} "
  html += "h2{color:#00FF66; border-bottom: 2px solid #00FF66; padding-bottom: 10px;} "
  html += ".header-row{background-color:#131B24; font-weight:bold; color:#00E5FF;} "
  html += "@media print { body{background:white; color:black;} table{background:white;} th{background:#f0f0f0; color:black;} }</style></head><body>"
  html += f"<h2>[>_ RASD] تقرير المهام - النطاق: {self.task_scope or 'كل المشاريع'}</h2>"
  html += f"<p style='color:#5E766A;'>تاريخ التقرير: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>"
  html += "<table><tr><th>المهمة</th><th>الموعد</th><th>الأولوية</th><th>المشروع</th><th>الهاشتاجات</th></tr>"
  for kind, val in items:
   if kind == 'header':html += f"<tr class='header-row'><td colspan='5'>{val}</td></tr>"
   else:html += f"<tr><td>{val[0]}</td><td>{val[1]}</td><td>{val[2]}</td><td>{val[3]}</td><td>{val[4]}</td></tr>"
  html += "</table><script>setTimeout(function(){ window.print(); }, 500);</script></body></html>"
  export_path = LOG / '.tasks' / 'export.html'
  export_path.parent.mkdir(exist_ok=True, parents=True)
  export_path.write_text(html, encoding='utf-8')
  webbrowser.open(str(export_path))

 def _task_edit_selected(self):
  ids=self._task_selected_ids()
  if len(ids)!=1:return messagebox.showinfo('المهام','حدد مهمة واحدة للتعديل.',parent=self)
  task_id=ids[0]
  with connect() as c:
   try: row=c.execute('SELECT * FROM tasks WHERE id=?',(task_id,)).fetchone()
   except sqlite3.Error: return
  if not row:return self._task_refresh_rows()
  self._task_task_dialog(row=row,project_locked=bool(self.task_scope))
