# sync_ops.py - تصدير واستيراد المشاريع والمهام (Backup & Sync) مع تتبع العمليات الجارية
from common import *
from storage import *
import zipfile
import shutil
import tempfile
import threading
import secrets
import json

class SyncOpsMixin:
 def show_sync_dialog(self):
  dialog = tk.Toplevel(self)
  dialog.title('تصدير واستيراد Log')
  dialog.configure(bg='#eef3f7')
  dialog.geometry('450x300')
  dialog.transient(self)
  dialog.grab_set()
  
  tk.Label(dialog, text='إدارة النسخ الاحتياطية والمشاركة', bg='#eef3f7', fg='#19394e', font=('Segoe UI', 14, 'bold')).pack(pady=(20, 10))
  tk.Label(dialog, text='اختر العملية التي تريد القيام بها:', bg='#eef3f7', fg='#617789', font=('Segoe UI', 10)).pack(pady=(0, 20))
  
  btn_frame = tk.Frame(dialog, bg='#eef3f7')
  btn_frame.pack(fill='x', padx=40)
  
  tk.Button(btn_frame, text='📦 تصدير مشاريع (Export)', command=lambda: [dialog.destroy(), self._sync_export_flow()], bg='#087e8b', fg='white', font=('Segoe UI', 11, 'bold'), pady=10, cursor='hand2', relief='flat').pack(fill='x', pady=10)
  tk.Button(btn_frame, text='📥 استيراد مشاريع (Import)', command=lambda: [dialog.destroy(), self._sync_import_flow()], bg='#3478e5', fg='white', font=('Segoe UI', 11, 'bold'), pady=10, cursor='hand2', relief='flat').pack(fill='x', pady=10)

 def _sync_export_flow(self):
  if hasattr(self, 'password_enabled') and self.password_enabled():
   pwd = simpledialog.askstring('تأكيد الأمان', 'أدخل كلمة المرور الخاصة بالبرنامج للتصدير:', show='*', parent=self)
   if not pwd or not self.verify_password(pwd):
    if pwd is not None: messagebox.showerror('خطأ', 'كلمة المرور غير صحيحة.', parent=self)
    return
    
  projects = [p.name for p in LOG.iterdir() if p.is_dir() and not p.name.startswith('.')]
  if not projects:
   return messagebox.showinfo('تصدير', 'لا توجد مشاريع لتصديرها.', parent=self)
   
  dialog = tk.Toplevel(self)
  dialog.title('تصدير المشاريع')
  dialog.configure(bg='#eef3f7')
  dialog.geometry('400x500')
  dialog.transient(self)
  dialog.grab_set()
  
  tk.Label(dialog, text='اختر المشاريع للتصدير', bg='#eef3f7', fg='#19394e', font=('Segoe UI', 12, 'bold')).pack(pady=10)
  
  list_frame = tk.Frame(dialog, bg='white', highlightbackground='#d6e0e6', highlightthickness=1)
  list_frame.pack(fill='both', expand=True, padx=20, pady=10)
  
  canvas = tk.Canvas(list_frame, bg='white', highlightthickness=0)
  scroll = ttk.Scrollbar(list_frame, orient='vertical', command=canvas.yview)
  scroll.pack(side='left', fill='y')
  canvas.pack(side='right', fill='both', expand=True)
  canvas.configure(yscrollcommand=scroll.set)
  
  inner_frame = tk.Frame(canvas, bg='white')
  canvas.create_window((0, 0), window=inner_frame, anchor='nw', width=340)
  
  project_vars = {}
  for p in projects:
   var = tk.BooleanVar(value=True)
   project_vars[p] = var
   tk.Checkbutton(inner_frame, text=p, variable=var, bg='white', font=('Segoe UI', 10), anchor='e').pack(fill='x', padx=10, pady=2)
   
  def _on_frame_configure(event):
   canvas.configure(scrollregion=canvas.bbox('all'))
  inner_frame.bind('<Configure>', _on_frame_configure)
  
  include_tasks = tk.BooleanVar(value=True)
  tk.Checkbutton(dialog, text='تضمين المهام والتقويم والبيانات الوصفية (.tasks)', variable=include_tasks, bg='#eef3f7', font=('Segoe UI', 10, 'bold'), fg='#087e8b').pack(pady=10)
  
  def start_export():
   selected = [p for p, v in project_vars.items() if v.get()]
   if not selected:
    return messagebox.showwarning('تصدير', 'يجب اختيار مشروع واحد على الأقل.', parent=dialog)
   
   save_path = filedialog.asksaveasfilename(title='حفظ ملف التصدير', defaultextension='.zip', filetypes=[('ZIP Files', '*.zip')], parent=dialog)
   if not save_path: return
   
   dialog.destroy()
   self._sync_run_export_thread(selected, save_path, include_tasks.get())
   
  ttk.Button(dialog, text='تصدير الآن', command=start_export).pack(pady=10)

 def _sync_run_export_thread(self, projects, save_path, include_tasks):
  self._active_bg_task = 'تصدير المشاريع والنسخة الاحتياطية'
  progress_win = tk.Toplevel(self)
  progress_win.title('جاري التصدير')
  progress_win.geometry('350x150')
  progress_win.configure(bg='#eef3f7')
  progress_win.transient(self)
  progress_win.grab_set()
  progress_win.protocol('WM_DELETE_WINDOW', lambda: None)
  tk.Label(progress_win, text='جاري تجميع وضغط الملفات والبيانات...', bg='#eef3f7', font=('Segoe UI', 11)).pack(pady=20)
  progress_var = tk.DoubleVar(value=0.0)
  bar = ttk.Progressbar(progress_win, variable=progress_var, maximum=100)
  bar.pack(fill='x', padx=30)
  status_lbl = tk.Label(progress_win, text='', bg='#eef3f7', fg='#617789')
  status_lbl.pack(pady=10)
  
  def worker():
   try:
    files_to_zip = []
    for p in projects:
     p_path = LOG / p
     
     if include_tasks:
      if hasattr(self, '_task_sync_text_documents'):
       self._task_sync_text_documents(p)
      
      with connect() as c:
       tasks_rows = c.execute("SELECT * FROM tasks WHERE project=?", (p,)).fetchall()
       tasks_list = [dict(row) for row in tasks_rows]
       
       links = [dict(r) for r in c.execute("SELECT path1, path2 FROM file_links WHERE project=?", (p,)).fetchall()]
       tags_rows = [dict(r) for r in c.execute("SELECT t.path, t.tag FROM tags t JOIN files f ON f.path=t.path WHERE f.project=?", (p,)).fetchall()]
       folder_tags_rows = [dict(r) for r in c.execute("SELECT path, tag FROM folder_tags WHERE project=?", (p,)).fetchall()]
       favorites_rows = [dict(r) for r in c.execute("SELECT path, kind, created FROM favorites WHERE project=?", (p,)).fetchall()]
       activity_rows = [dict(r) for r in c.execute("SELECT action, details, path, occurred_at FROM activity_log WHERE project=?", (p,)).fetchall()]
       
      meta_dir = p_path / '.tasks'
      meta_dir.mkdir(parents=True, exist_ok=True)
      
      if tasks_list:
       backup_json = meta_dir / 'tasks_backup.json'
       backup_json.write_text(json.dumps(tasks_list, ensure_ascii=False), encoding='utf-8')
       
      project_meta_json = meta_dir / 'project_meta.json'
      meta_payload = {
       'file_links': links,
       'tags': tags_rows,
       'folder_tags': folder_tags_rows,
       'favorites': favorites_rows,
       'activity_log': activity_rows
      }
      project_meta_json.write_text(json.dumps(meta_payload, ensure_ascii=False), encoding='utf-8')

      if os.name == 'nt':
       try:
        import ctypes
        ctypes.windll.kernel32.SetFileAttributesW(str(meta_dir), 2)
       except Exception: pass

     for f in p_path.rglob('*'):
      if f.is_file():
       rel = f.relative_to(LOG)
       if not include_tasks and '.tasks' in rel.parts: continue
       files_to_zip.append((f, rel))
       
    total_f = max(1, len(files_to_zip))
    with zipfile.ZipFile(save_path, 'w', zipfile.ZIP_DEFLATED) as zf:
     for i, (f_path, rel_path) in enumerate(files_to_zip):
      zf.write(f_path, arcname=str(rel_path))
      pct = ((i + 1) / total_f) * 100
      proj_part = str(rel_path.parts[0])
      self.after(0, lambda v=pct, txt=proj_part: (progress_var.set(v), status_lbl.configure(text=txt)) if progress_win.winfo_exists() else None)
      
    self._active_bg_task = None
    self.after(0, lambda: [progress_win.destroy(), messagebox.showinfo('نجاح', 'تم تصدير المشاريع والبيانات بنجاح!', parent=self)])
   except Exception as e:
    self._active_bg_task = None
    self.after(0, lambda err=e: [progress_win.destroy(), messagebox.showerror('خطأ', f'حدث خطأ أثناء التصدير:\n{err}', parent=self)])
    
  threading.Thread(target=worker, daemon=True).start()

 def _sync_import_flow(self):
  zip_path = filedialog.askopenfilename(title='اختر ملف النسخة الاحتياطية', filetypes=[('ZIP Files', '*.zip'), ('All Files', '*.*')], parent=self)
  if not zip_path: return
  
  try:
   with zipfile.ZipFile(zip_path, 'r') as zf:
    items = zf.namelist()
    projects_in_zip = sorted(list(set([Path(p).parts[0] for p in items if Path(p).parts])))
  except Exception as e:
   return messagebox.showerror('خطأ', 'الملف غير صالح أو تالف.', parent=self)
   
  if not projects_in_zip:
   return messagebox.showinfo('فارغ', 'لا توجد مشاريع في هذا الملف.', parent=self)
   
  dialog = tk.Toplevel(self)
  dialog.title('استيراد المشاريع')
  dialog.configure(bg='#eef3f7')
  dialog.geometry('400x500')
  dialog.transient(self)
  dialog.grab_set()
  
  tk.Label(dialog, text='اختر المشاريع للاستيراد', bg='#eef3f7', fg='#19394e', font=('Segoe UI', 12, 'bold')).pack(pady=10)
  
  list_frame = tk.Frame(dialog, bg='white', highlightbackground='#d6e0e6', highlightthickness=1)
  list_frame.pack(fill='both', expand=True, padx=20, pady=10)
  
  canvas = tk.Canvas(list_frame, bg='white', highlightthickness=0)
  scroll = ttk.Scrollbar(list_frame, orient='vertical', command=canvas.yview)
  scroll.pack(side='left', fill='y')
  canvas.pack(side='right', fill='both', expand=True)
  canvas.configure(yscrollcommand=scroll.set)
  
  inner_frame = tk.Frame(canvas, bg='white')
  canvas.create_window((0, 0), window=inner_frame, anchor='nw', width=340)
  
  project_vars = {}
  existing_projects = [p.name for p in LOG.iterdir() if p.is_dir() and not p.name.startswith('.')]
  
  for p in projects_in_zip:
   var = tk.BooleanVar(value=True)
   project_vars[p] = var
   lbl = p + (' (موجود مسبقاً)' if p in existing_projects else ' (جديد)')
   tk.Checkbutton(inner_frame, text=lbl, variable=var, bg='white', font=('Segoe UI', 10), anchor='e', fg='#b92f3b' if p in existing_projects else '#19394e').pack(fill='x', padx=10, pady=2)
   
  def _on_frame_configure(event):
   canvas.configure(scrollregion=canvas.bbox('all'))
  inner_frame.bind('<Configure>', _on_frame_configure)
  
  include_tasks = tk.BooleanVar(value=True)
  tk.Checkbutton(dialog, text='استيراد المهام والبيانات الوصفية (.tasks)', variable=include_tasks, bg='#eef3f7', font=('Segoe UI', 10, 'bold'), fg='#087e8b').pack(pady=10)
  
  def start_import():
   selected = [p for p, v in project_vars.items() if v.get()]
   if not selected:
    return messagebox.showwarning('استيراد', 'يجب اختيار مشروع واحد على الأقل.', parent=dialog)
   
   conflicts = [p for p in selected if p in existing_projects]
   mode = 'merge'
   if conflicts:
    conflict_msg = f"المشاريع التالية موجودة مسبقاً:\n{', '.join(conflicts[:3])}" + ("..." if len(conflicts)>3 else "") + "\n\nهل تريد استبدالها بالكامل (Overwrite) أم دمج الملفات والبيانات (Merge)؟"
    conflict_dialog = tk.Toplevel(dialog)
    conflict_dialog.title('تعارض في المشاريع')
    conflict_dialog.geometry('400x200')
    conflict_dialog.configure(bg='white')
    conflict_dialog.transient(dialog)
    conflict_dialog.grab_set()
    
    tk.Label(conflict_dialog, text=conflict_msg, bg='white', justify='right', font=('Segoe UI', 10)).pack(pady=20, padx=20)
    user_choice = tk.StringVar(value='')
    btn_frame2 = tk.Frame(conflict_dialog, bg='white')
    btn_frame2.pack(pady=10)
    
    ttk.Button(btn_frame2, text='استبدال (Overwrite)', command=lambda: [user_choice.set('overwrite'), conflict_dialog.destroy()]).pack(side='right', padx=10)
    ttk.Button(btn_frame2, text='دمج (Merge)', command=lambda: [user_choice.set('merge'), conflict_dialog.destroy()]).pack(side='left', padx=10)
    
    dialog.wait_window(conflict_dialog)
    if not user_choice.get(): return
    mode = user_choice.get()
    
   dialog.destroy()
   self._sync_run_import_thread(zip_path, selected, include_tasks.get(), mode)
   
  ttk.Button(dialog, text='استيراد الآن', command=start_import).pack(pady=10)

 def _sync_run_import_thread(self, zip_path, projects, include_tasks, mode):
  self._active_bg_task = 'استيراد المشاريع وفك ضغط الملفات'
  progress_win = tk.Toplevel(self)
  progress_win.title('جاري الاستيراد')
  progress_win.geometry('350x150')
  progress_win.configure(bg='#eef3f7')
  progress_win.transient(self)
  progress_win.grab_set()
  progress_win.protocol('WM_DELETE_WINDOW', lambda: None)
  tk.Label(progress_win, text='جاري استخراج الملفات...', bg='#eef3f7', font=('Segoe UI', 11)).pack(pady=20)
  progress_var = tk.DoubleVar(value=0.0)
  bar = ttk.Progressbar(progress_win, variable=progress_var, maximum=100)
  bar.pack(fill='x', padx=30)
  status_lbl = tk.Label(progress_win, text='', bg='#eef3f7', fg='#617789')
  status_lbl.pack(pady=10)
  
  def worker():
   try:
    with zipfile.ZipFile(zip_path, 'r') as zf:
     items = zf.namelist()
     relevant_items = []
     for item in items:
      parts = Path(item).parts
      if not parts: continue
      proj_name = parts[0]
      if proj_name in projects:
       if not include_tasks and '.tasks' in parts: continue
       relevant_items.append(item)
     
     cleared_projects = set()
     for p in projects:
      if not (LOG / p).exists():
       with connect() as c:
        c.execute("DELETE FROM tasks WHERE project=?", (p,))
       cleared_projects.add(p)

     extracted_backups = []
     extracted_metas = []
     total_items = max(1, len(relevant_items))

     for i, item in enumerate(relevant_items):
      parts = Path(item).parts
      proj_name = parts[0]
      target_path = LOG / item
      
      if mode == 'overwrite' and (LOG / proj_name).exists() and proj_name not in cleared_projects:
       shutil.rmtree(LOG / proj_name, ignore_errors=True)
       cleared_projects.add(proj_name)
       with connect() as c:
        c.execute("DELETE FROM tasks WHERE project=?", (proj_name,))
        c.execute("DELETE FROM file_links WHERE project=?", (proj_name,))
        c.execute("DELETE FROM favorites WHERE project=?", (proj_name,))
      
      if item.endswith('/'):
       target_path.mkdir(parents=True, exist_ok=True)
       continue
       
      if '.tasks' in parts:
       if not include_tasks: continue
       if target_path.name == 'tasks_backup.json':
        temp_dir = Path(tempfile.gettempdir()) / 'rasd_import'
        temp_dir.mkdir(exist_ok=True)
        temp_file = temp_dir / f"{proj_name}_tasks_backup_{secrets.token_hex(4)}.json"
        with zf.open(item) as source, open(temp_file, "wb") as f:
         shutil.copyfileobj(source, f)
        extracted_backups.append((proj_name, temp_file))
        continue
       elif target_path.name == 'project_meta.json':
        temp_dir = Path(tempfile.gettempdir()) / 'rasd_import'
        temp_dir.mkdir(exist_ok=True)
        temp_file = temp_dir / f"{proj_name}_project_meta_{secrets.token_hex(4)}.json"
        with zf.open(item) as source, open(temp_file, "wb") as f:
         shutil.copyfileobj(source, f)
        extracted_metas.append((proj_name, temp_file))
        continue
      
      target_path.parent.mkdir(parents=True, exist_ok=True)
      with zf.open(item) as source, open(target_path, "wb") as f:
       shutil.copyfileobj(source, f)
       
      pct = ((i + 1) / total_items) * 100
      self.after(0, lambda v=pct, txt=str(proj_name): (progress_var.set(v), status_lbl.configure(text=txt)) if progress_win.winfo_exists() else None)
      
     for proj_name, backup_file in extracted_backups:
      self._sync_restore_tasks_from_backup(backup_file, proj_name, mode)

     for proj_name, meta_file in extracted_metas:
      self._sync_restore_project_meta(meta_file, proj_name, mode)

     processed_projs = [p for p, _ in extracted_backups]
     for p in projects:
      if p not in processed_projs:
       p_tasks = LOG / p / '.tasks'
       if p_tasks.exists():
        for json_file in p_tasks.glob('مهمة-*.json'):
         self._sync_merge_task_json_fallback(json_file, p, mode)

     for p in projects:
      proj_dir = LOG / p
      if proj_dir.is_dir():
       threading.Thread(target=self.scan_worker, args=(proj_dir,), daemon=True).start()

    self._active_bg_task = None
    self.after(0, lambda: [progress_win.destroy(), messagebox.showinfo('نجاح', 'تم استيراد المشاريع والبيانات بنجاح وفهرستها!', parent=self), getattr(self, 'render_projects', lambda: None)()])
   except Exception as e:
    self._active_bg_task = None
    self.after(0, lambda err=e: [progress_win.destroy(), messagebox.showerror('خطأ', f'حدث خطأ أثناء الاستيراد:\n{err}', parent=self)])
    
  threading.Thread(target=worker, daemon=True).start()

 def _sync_restore_project_meta(self, meta_file, proj_name, mode):
  try:
   data = json.loads(meta_file.read_text(encoding='utf-8'))
   project_root = (LOG / proj_name).resolve()
   with connect() as c:
    for link in data.get('file_links', []):
     p1 = str(project_root / Path(link['path1']).name) if not os.path.isabs(link['path1']) else link['path1']
     p2 = str(project_root / Path(link['path2']).name) if not os.path.isabs(link['path2']) else link['path2']
     c.execute("INSERT OR IGNORE INTO file_links(project, path1, path2) VALUES(?,?,?)", (proj_name, p1, p2))
     
    for tg in data.get('tags', []):
     p = str(project_root / Path(tg['path']).name) if not os.path.isabs(tg['path']) else tg['path']
     c.execute("INSERT OR IGNORE INTO tags(path, tag) VALUES(?,?)", (p, tg['tag']))
     c.execute("INSERT OR IGNORE INTO file_tag_catalog(project, tag, created) VALUES(?,?,?)", (proj_name, tg['tag'], stamp(time.time())))

    for ftg in data.get('folder_tags', []):
     c.execute("INSERT OR IGNORE INTO folder_tags(project, path, tag, created) VALUES(?,?,?,?)", (proj_name, ftg['path'], ftg['tag'], stamp(time.time())))
     c.execute("INSERT OR IGNORE INTO folder_specialty_catalog(project, tag, created) VALUES(?,?,?)", (proj_name, ftg['tag'], stamp(time.time())))

    for fav in data.get('favorites', []):
     p = str(project_root / Path(fav['path']).name) if not os.path.isabs(fav['path']) else fav['path']
     c.execute("INSERT OR IGNORE INTO favorites(project, path, kind, created) VALUES(?,?,?,?)", (proj_name, p, fav.get('kind','file'), fav.get('created', stamp(time.time()))))

    for act in data.get('activity_log', []):
     target_p = str(project_root / Path(act['path']).name) if act.get('path') and not os.path.isabs(act['path']) else act.get('path')
     c.execute("INSERT INTO activity_log(project, action, details, path, occurred_at) VALUES(?,?,?,?,?)", (proj_name, act['action'], act['details'], target_p, act['occurred_at']))
  except Exception: pass

 def _sync_restore_tasks_from_backup(self, backup_file, proj_name, mode):
  try:
   tasks_list = json.loads(backup_file.read_text(encoding='utf-8'))
   with connect() as c:
    for t in tasks_list:
     old_id = t['id']
     existing = c.execute("SELECT id, updated_at FROM tasks WHERE title=? AND project=?", (t['title'], proj_name)).fetchone()
     final_id = None
     
     if existing:
      if mode == 'merge':
       local_dt = existing['updated_at']
       zip_dt = t.get('updated_at', '')
       if zip_dt > local_dt:
        c.execute('''UPDATE tasks SET description=?, rich_text=?, due_date=?, start_time=?, end_time=?,
                     priority=?, tags=?, recurrence=?, subtasks=?, attachments=?, completed_at=?,
                     updated_at=?, document_rel=?, document_mtime=? WHERE id=?''',
                  (t.get('description',''), t.get('rich_text',''), t.get('due_date'), t.get('start_time'),
                   t.get('end_time'), t.get('priority',2), t.get('tags',''), t.get('recurrence','لا يوجد'),
                   t.get('subtasks','[]'), t.get('attachments','[]'), t.get('completed_at'),
                   t.get('updated_at'), t.get('document_rel'), t.get('document_mtime'), existing['id']))
        final_id = existing['id']
     else:
      cursor = c.execute('''INSERT INTO tasks(title, description, rich_text, project, due_date, start_time, end_time,
                   priority, tags, recurrence, subtasks, attachments, completed_at, created_at, updated_at,
                   document_rel, document_mtime)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (t['title'], t.get('description',''), t.get('rich_text',''), proj_name, t.get('due_date'),
                 t.get('start_time'), t.get('end_time'), t.get('priority',2), t.get('tags',''),
                 t.get('recurrence','لا يوجد'), t.get('subtasks','[]'), t.get('attachments','[]'),
                 t.get('completed_at'), t.get('created_at'), t.get('updated_at'),
                 t.get('document_rel'), t.get('document_mtime')))
      final_id = cursor.lastrowid

     if final_id and final_id != old_id:
      old_attach = LOG / proj_name / '.tasks' / f"مرفقات المهمة {old_id}"
      new_attach = LOG / proj_name / '.tasks' / f"مرفقات المهمة {final_id}"
      if old_attach.exists() and not new_attach.exists():
       try: old_attach.rename(new_attach)
       except OSError: pass
      
      fixed_attachments = []
      for att in json.loads(t.get('attachments', '[]')):
       att['path'] = att['path'].replace(f"مرفقات المهمة {old_id}", f"مرفقات المهمة {final_id}")
       fixed_attachments.append(att)
      
      c.execute("UPDATE tasks SET attachments=? WHERE id=?", (json.dumps(fixed_attachments, ensure_ascii=False), final_id))
      
      tasks_dir = LOG / proj_name / '.tasks'
      for old_file in tasks_dir.glob(f"مهمة-{old_id}-*.*"):
       try: old_file.unlink()
       except OSError: pass

     if final_id and hasattr(self, '_task_ensure_document_artifacts'):
      self._task_ensure_document_artifacts(final_id)
  except Exception: pass

 def _sync_merge_task_json_fallback(self, json_path, proj_name, mode):
  try:
   data = json.loads(json_path.read_text(encoding='utf-8'))
   title = data.get('title')
   if not title: return
   old_id = data.get('task_id')
   due_date = data.get('due_date')
   start_time = data.get('start_time')
   end_time = data.get('end_time')
   priority = data.get('priority', 2)
   tags = data.get('tags', '')
   recurrence = data.get('recurrence', 'لا يوجد')
   subtasks = data.get('subtasks', [])
   attachments = data.get('attachments', [])
   
   txt_path = json_path.with_suffix('.txt')
   description = ''
   if txt_path.exists():
    content = txt_path.read_text(encoding='utf-8', errors='replace')
    parts = content.split('--- خطوات التنفيذ ---')
    desc_part = parts[0].strip()
    lines = desc_part.splitlines()
    if lines and lines[0].strip().lstrip('#').strip() == title:
     description = '\n'.join(lines[1:]).lstrip('\n')
    else:
     description = desc_part

   with connect() as c:
    existing = c.execute("SELECT id FROM tasks WHERE title=? AND project=?", (title, proj_name)).fetchone()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    final_id = None
    
    if existing:
     if mode == 'merge':
      c.execute('UPDATE tasks SET due_date=?,start_time=?,end_time=?,priority=?,tags=?,recurrence=?,subtasks=?,attachments=?,updated_at=?,description=? WHERE id=?', 
                (due_date, start_time, end_time, priority, tags, recurrence, json.dumps(subtasks, ensure_ascii=False), json.dumps(attachments, ensure_ascii=False), now, description, existing['id']))
      final_id = existing['id']
    else:
     cursor = c.execute('INSERT INTO tasks(title,description,project,due_date,start_time,end_time,priority,tags,recurrence,subtasks,attachments,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
               (title, description, proj_name, due_date, start_time, end_time, priority, tags, recurrence, json.dumps(subtasks, ensure_ascii=False), json.dumps(attachments, ensure_ascii=False), now, now))
     final_id = cursor.lastrowid
     
    if final_id and old_id and final_id != old_id:
     old_attach = LOG / proj_name / '.tasks' / f"مرفقات المهمة {old_id}"
     new_attach = LOG / proj_name / '.tasks' / f"مرفقات المهمة {final_id}"
     if old_attach.exists() and not new_attach.exists():
      try: old_attach.rename(new_attach)
      except OSError: pass
     
     fixed_attachments = []
     for att in attachments:
      att['path'] = att['path'].replace(f"مرفقات المهمة {old_id}", f"مرفقات المهمة {final_id}")
      fixed_attachments.append(att)
     c.execute("UPDATE tasks SET attachments=? WHERE id=?", (json.dumps(fixed_attachments, ensure_ascii=False), final_id))
     
     for old_file in (LOG / proj_name / '.tasks').glob(f"مهمة-{old_id}-*.*"):
      try: old_file.unlink()
      except OSError: pass
      
    if final_id and hasattr(self, '_task_ensure_document_artifacts'):
     self._task_ensure_document_artifacts(final_id)
  except Exception: pass