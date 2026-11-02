# tasks_details.py - تفاصيل المهمة والخطوات الفرعية والمستندات ونافذة التحرير
from common import *
from storage import *

class TasksDetailsMixin:
 def _task_build_preview_panel(self,panel):
  panel.grid_columnconfigure(0,weight=1)
  tk.Label(panel,text=RLM+'معاينة المهمة',bg=BG_HEADER,fg=ACCENT_MATRIX,font=(TERM_FONT,10,'bold'),anchor='e',padx=12,pady=10).grid(row=0,column=0,sticky='ew')
  self.task_preview_title=tk.Label(panel,text=RLM+'اختر مهمة من القائمة',bg=BG_PANEL,fg=FG_PRIMARY,font=(TERM_FONT,11,'bold'),anchor='e',justify='right',wraplength=275);self.task_preview_title.grid(row=1,column=0,sticky='ew',padx=12,pady=(16,8))
  self.task_preview_meta=tk.Label(panel,text=RLM+'ستظهر تفاصيلها ومرفقاتها هنا.',bg=BG_PANEL,fg=ACCENT_CYAN,font=(TERM_FONT,9),anchor='e',justify='right',wraplength=275);self.task_preview_meta.grid(row=2,column=0,sticky='ew',padx=12,pady=(0,10))
  self.task_preview_subtasks_frame=tk.Frame(panel,bg=BG_PANEL);self.task_preview_subtasks_frame.grid(row=3,column=0,sticky='nsew',padx=10,pady=4)
  panel.grid_rowconfigure(3,weight=1) 
  self.task_preview_attachments=tk.Label(panel,text='',bg=BG_PANEL,fg=FG_MUTED,font=(TERM_FONT,8),anchor='e',justify='right',wraplength=275);self.task_preview_attachments.grid(row=4,column=0,sticky='ew',padx=12,pady=7)
  self.task_preview_attachments_frame=tk.Frame(panel,bg=BG_PANEL);self.task_preview_attachments_frame.grid(row=5,column=0,sticky='ew',padx=8,pady=3)
  actions=tk.Frame(panel,bg=BG_PANEL);actions.grid(row=6,column=0,sticky='ew',padx=8,pady=(4,10));ttk.Button(actions,text=RLM+'فتح ملف المهمة TXT',command=self._task_open_selected_document).pack(fill='x',pady=2);ttk.Button(actions,text=RLM+'تعديل المهمة',command=self._task_edit_selected).pack(fill='x',pady=2);ttk.Button(actions,text=RLM+'فتح مجلد المهمة',command=self._task_open_selected_folder).pack(fill='x',pady=2)

 def _task_toggle_subtask(self, task_id, index, var):
  with connect() as c:
   try:
    row = c.execute('SELECT subtasks FROM tasks WHERE id=?', (task_id,)).fetchone()
    if row:
     subs = json.loads(row['subtasks']) if row['subtasks'] else []
     subs[index]['done'] = bool(var.get())
     c.execute('UPDATE tasks SET subtasks=?, updated_at=? WHERE id=?', (json.dumps(subs, ensure_ascii=False), datetime.now().strftime('%Y-%m-%d %H:%M:%S'), task_id))
   except Exception: pass
  self._task_ensure_document_artifacts(task_id)
  if getattr(self,'task_preview_task_id',None)==task_id:self._task_preview_selected()

 def _task_delete_subtask(self, task_id, index):
  with connect() as c:
   try:
    row = c.execute('SELECT subtasks FROM tasks WHERE id=?', (task_id,)).fetchone()
    if row:
     subs = json.loads(row['subtasks']) if row['subtasks'] else []
     del subs[index]
     c.execute('UPDATE tasks SET subtasks=?, updated_at=? WHERE id=?', (json.dumps(subs, ensure_ascii=False), datetime.now().strftime('%Y-%m-%d %H:%M:%S'), task_id))
   except Exception: pass
  self._task_ensure_document_artifacts(task_id)
  if getattr(self,'task_preview_task_id',None)==task_id:self._task_preview_selected()
  
 def _task_edit_subtask(self, task_id, index):
  with connect() as c:
   try:
    row = c.execute('SELECT subtasks FROM tasks WHERE id=?', (task_id,)).fetchone()
    if not row or not row['subtasks']: return
    subs = json.loads(row['subtasks'])
    current = subs[index]['title']
   except Exception: return
  new_title = simpledialog.askstring('تعديل خطوة', 'قم بتعديل الخطوة:', initialvalue=current, parent=self)
  if new_title and new_title.strip():
   subs[index]['title'] = new_title.strip()
   with connect() as c:c.execute('UPDATE tasks SET subtasks=?, updated_at=? WHERE id=?', (json.dumps(subs, ensure_ascii=False), datetime.now().strftime('%Y-%m-%d %H:%M:%S'), task_id))
   self._task_ensure_document_artifacts(task_id)
   if getattr(self,'task_preview_task_id',None)==task_id:self._task_preview_selected()
   if getattr(self,'task_calendar_selected_id',None)==task_id:self._task_calendar_select_task(task_id)

 def _task_add_subtask(self, task_id, var, widget_to_focus=None):
  title = var.get().strip()
  if not title: return
  var.set('')
  with connect() as c:
   try:
    row = c.execute('SELECT subtasks FROM tasks WHERE id=?', (task_id,)).fetchone()
    subs = json.loads(row['subtasks']) if row and row['subtasks'] else []
   except Exception: subs = []
   subs.append({'title': title, 'done': False})
   c.execute('UPDATE tasks SET subtasks=?, updated_at=? WHERE id=?', (json.dumps(subs, ensure_ascii=False), datetime.now().strftime('%Y-%m-%d %H:%M:%S'), task_id))
  self._task_ensure_document_artifacts(task_id)
  if getattr(self,'task_preview_task_id',None)==task_id:self._task_preview_selected()
  if getattr(self,'task_calendar_selected_id',None)==task_id:self._task_calendar_select_task(task_id)
  if widget_to_focus: self.after_idle(lambda: widget_to_focus.focus_set())

 def _task_preview_selected(self):
  if not hasattr(self,'task_preview_title'):return
  ids=self._task_selected_ids()
  if len(ids)!=1:
   self.task_preview_title.configure(text=RLM+'اختر مهمة واحدة من القائمة');self.task_preview_meta.configure(text=RLM+'ستظهر تفاصيلها ومرفقاتها هنا.');self.task_preview_attachments.configure(text='');self.task_preview_task_id=None
   for child in getattr(self, 'task_preview_attachments_frame', tk.Frame()).winfo_children():child.destroy()
   for child in getattr(self, 'task_preview_subtasks_frame', tk.Frame()).winfo_children():child.destroy()
   return
  with connect() as c:
   try: row=c.execute('SELECT * FROM tasks WHERE id=?',(ids[0],)).fetchone()
   except sqlite3.Error: return
  if not row:return
  self.task_preview_task_id=row['id'];self.task_preview_title.configure(text=RLM+str(row['title']));due=self._task_date_text(row['due_date'])+(' · '+(' – '.join(x for x in (row['start_time'],row['end_time']) if x) if row['start_time'] or row['end_time'] else ''));priority_text={1:'عاجلة',2:'عادية',3:'منخفضة'}.get(row['priority'],'عادية');state_text='مكتملة' if row['completed_at'] else 'مفتوحة'
  try: rec_text = f" · دورية: {row['recurrence']}" if row['recurrence'] and row['recurrence']!='لا يوجد' else ""
  except Exception: rec_text = ""
  meta_lines = [
   RLM+f"المشروع: {row['project']}",
   RLM+f"الموعد: {due}",
   RLM+f"الأولوية: {priority_text} · {state_text}{rec_text}"
  ]
  self.task_preview_meta.configure(text='\n'.join(meta_lines))
  for child in self.task_preview_subtasks_frame.winfo_children():child.destroy()
  try: subtasks = json.loads(row['subtasks']) if row['subtasks'] else []
  except Exception: subtasks = []
  completed_subs = sum(1 for s in subtasks if s.get('done'))
  tk.Label(self.task_preview_subtasks_frame, text=RLM+f'قائمة خطوات التنفيذ ({completed_subs}/{len(subtasks)}):', bg=BG_PANEL, fg=ACCENT_MATRIX, font=(TERM_FONT, 9, 'bold')).pack(anchor='e', pady=(0,4))
  for i, sub in enumerate(subtasks):
   f = tk.Frame(self.task_preview_subtasks_frame, bg=BG_PANEL)
   f.pack(fill='x', pady=2)
   var = tk.BooleanVar(value=sub.get('done', False))
   cb = tk.Checkbutton(f, text=RLM+sub.get('title', ''), variable=var, bg=BG_PANEL, activebackground=BG_PANEL, selectcolor=BG_VOID, fg=FG_PRIMARY, font=(TERM_FONT, 9), command=lambda idx=i, v=var: self._task_toggle_subtask(row['id'], idx, v))
   cb.pack(side='right', fill='x', expand=True, anchor='e')
   ttk.Button(f, text='×', width=2, command=lambda idx=i: self._task_delete_subtask(row['id'], idx)).pack(side='left', padx=1)
   ttk.Button(f, text='✎', width=2, command=lambda idx=i: self._task_edit_subtask(row['id'], idx)).pack(side='left', padx=1)
  add_f = tk.Frame(self.task_preview_subtasks_frame, bg=BG_PANEL)
  add_f.pack(fill='x', pady=6)
  new_sub_var = tk.StringVar()
  sub_entry = ttk.Entry(add_f, textvariable=new_sub_var, justify='right')
  sub_entry.pack(side='right', fill='x', expand=True, padx=2)
  sub_entry.bind('<Return>', lambda e, t=row['id'], v=new_sub_var: self._task_add_subtask(t, v, e.widget))
  ttk.Button(add_f, text=RLM+'＋ خطوة', width=7, command=lambda t=row['id'], v=new_sub_var: self._task_add_subtask(t, v, sub_entry)).pack(side='left', padx=2)
  try: attachments=self._task_attachment_values(row)
  except Exception: attachments = []
  self.task_preview_attachments.configure(text=RLM+('المرفقات والروابط: '+str(len(attachments)) if attachments else 'لا توجد مرفقات'))
  if hasattr(self, 'task_preview_attachments_frame'):
   for child in self.task_preview_attachments_frame.winfo_children():child.destroy()
   for item in attachments:
    line=tk.Frame(self.task_preview_attachments_frame,bg=BG_PANEL);line.pack(fill='x',pady=1)
    ttk.Button(line,text='×',width=3,command=lambda i=item:self._task_remove_attachment(row['id'],i)).pack(side='left', padx=1)
    ttk.Button(line,text='👁',width=3,command=lambda i=item:self._task_open_attachment(i)).pack(side='left', padx=1)
    btn_text = item.get('name', Path(item['path']).name)
    tk.Label(line,text=RLM+btn_text, bg=BG_PANEL, fg=ACCENT_CYAN, font=(TERM_FONT, 8), anchor='e').pack(side='right',fill='x',expand=True)

 def _task_selected_row(self):
  ids=self._task_selected_ids()
  if len(ids)!=1:return None
  with connect() as c:return c.execute('SELECT * FROM tasks WHERE id=?',(ids[0],)).fetchone()
  
 def _task_open_selected_document(self):
  row=self._task_selected_row()
  if row:self._task_open_document(row['id'])
  
 def _task_open_selected_folder(self):
  row=self._task_selected_row()
  if not row:return
  try:os.startfile(str(self._task_document_folder(row)))
  except Exception as exc:messagebox.showwarning('المهمة',str(exc),parent=self)

 def _task_task_dialog(self,row=None,project_locked=False,initial_date=None,project=None,initial_start=None,initial_end=None):
  def safe_val(r, col, default=''):
   if not r: return default
   try: return r[col] if r[col] is not None else default
   except Exception: return default
  title_val = safe_val(row, 'title', '')
  due_val = safe_val(row, 'due_date', '') or (initial_date.isoformat() if hasattr(initial_date, 'isoformat') else str(initial_date) if initial_date else '')
  start_val = safe_val(row, 'start_time', '') or (initial_start or '')
  end_val = safe_val(row, 'end_time', '') or (initial_end or '')
  try: pri_val = {1:'عاجلة',2:'عادية',3:'منخفضة'}.get(int(safe_val(row, 'priority', 2)), 'عادية')
  except Exception: pri_val = 'عادية'
  proj_val = project if project is not None else (safe_val(row, 'project', '') or getattr(self, 'task_scope', ''))
  tags_val = safe_val(row, 'tags', '')
  rec_val = safe_val(row, 'recurrence', 'لا يوجد')
  if not rec_val: rec_val = 'لا يوجد'
  existing_attachments = self._task_attachment_values(row) if row else []
  pending_files = []
  files_to_remove = []
  dialog=tk.Toplevel(self);dialog.title('تعديل المهمة' if row else 'إضافة مهمة من التقويم');dialog.configure(bg=BG_VOID);dialog.transient(self);dialog.grab_set();dialog.resizable(False,False);card=tk.Frame(dialog,bg=BG_PANEL,highlightbackground=ACCENT_MATRIX,highlightthickness=1);card.pack(fill='both',expand=True,padx=14,pady=14);card.grid_columnconfigure(1,weight=1)
  tk.Label(card,text=RLM+('تعديل المهمة' if row else 'إضافة مهمة من التقويم'),bg=BG_PANEL,fg=ACCENT_MATRIX,font=(TERM_FONT,12,'bold')).grid(row=0,column=0,columnspan=3,sticky='e',padx=14,pady=(14,8))
  project_locked=bool(project_locked or project is not None)
  title=tk.StringVar(value=title_val); due=tk.StringVar(value=due_val)
  start=tk.StringVar(value=start_val); end=tk.StringVar(value=end_val)
  priority=tk.StringVar(value=pri_val); tags=tk.StringVar(value=tags_val)
  project_var=tk.StringVar(value=proj_val or ('اختر مشروعًا…' if not row else ''))
  recurrence = tk.StringVar(value=rec_val)
  def label(text,r):tk.Label(card,text=RLM+text,bg=BG_PANEL,fg=ACCENT_CYAN,font=(TERM_FONT,9)).grid(row=r,column=2,sticky='e',padx=12,pady=(5,2))
  label('عنوان المهمة:',1);name=ttk.Entry(card,textvariable=title,width=42,justify='right');name.grid(row=2,column=0,columnspan=3,sticky='ew',padx=12,pady=(0,4))
  label('التاريخ:',3);datebox=ttk.Entry(card,textvariable=due,width=15,justify='center');datebox.grid(row=4,column=1,padx=5,pady=(0,4),sticky='e');ttk.Button(card,text=RLM+'🗓 اختر التاريخ',command=lambda:self._task_pick_date(due,initial_date,parent=dialog)).grid(row=4,column=0,padx=5,pady=(0,4),sticky='w');ttk.Button(card,text=RLM+'بدون موعد',command=lambda:due.set('')).grid(row=4,column=2,padx=12,pady=(0,4),sticky='e')
  label('الوقت (اختياري):',5);timebox=tk.Frame(card,bg=BG_PANEL);timebox.grid(row=6,column=0,columnspan=3,sticky='ew',padx=12,pady=(0,4));self._task_time_control(timebox,start,'من');self._task_time_control(timebox,end,'إلى')
  label('الأولوية:',7);ttk.Combobox(card,textvariable=priority,values=('عاجلة','عادية','منخفضة'),state='readonly',justify='right',style='Office.TCombobox').grid(row=8,column=1,columnspan=2,sticky='ew',padx=12,pady=(0,4))
  label('التكرار:',7);ttk.Combobox(card,textvariable=recurrence,values=('لا يوجد','يومياً','أسبوعياً','شهرياً'),state='readonly',width=10,justify='right',style='Office.TCombobox').grid(row=8,column=0,sticky='ew',padx=12,pady=(0,4))
  label('تابعة لأي مشروع؟',9);projects=self._task_project_names();project_values=([proj_val] if project_locked and proj_val else [])+projects;project_values=list(dict.fromkeys(project_values));project_combo=ttk.Combobox(card,textvariable=project_var,values=project_values,state='disabled' if project_locked else 'readonly',justify='right',style='Office.TCombobox');project_combo.grid(row=10,column=0,columnspan=3,sticky='ew',padx=12,pady=(0,4))
  label('هاشتاجات المهمة:',11);ttk.Entry(card,textvariable=tags,justify='right').grid(row=12,column=0,columnspan=3,sticky='ew',padx=12,pady=(0,5))
  attachment_row=tk.Frame(card,bg=BG_PANEL);attachment_row.grid(row=13,column=0,columnspan=3,sticky='ew',padx=12,pady=4)
  def choose_files():
   chosen = filedialog.askopenfilenames(parent=dialog, title='اختر ملفات للمهمة')
   if chosen:
    for path in chosen:
     if path not in pending_files: pending_files.append(path)
    render_attach_list()
  def link_file():
   proj = project_var.get()
   if not proj or proj == 'اختر مشروعًا…': return messagebox.showwarning('المشروع', 'يرجى اختيار المشروع أولاً من القائمة.', parent=dialog)
   project_root = (LOG / proj).resolve()
   if not project_root.exists(): return
   chosen = filedialog.askopenfilename(initialdir=str(project_root), parent=dialog, title='اختر ملفاً من المشروع لربطه بالمهمة')
   if chosen:
    try:
     rel_path = Path(chosen).resolve().relative_to(LOG.resolve()).as_posix()
     pending_files.append({'name': '<-> ' + Path(chosen).name, 'path': rel_path, 'is_link': True})
     render_attach_list()
    except ValueError: messagebox.showwarning('مسار خاطئ', 'يجب اختيار ملف من داخل مجلد المشروع المختار.', parent=dialog)
  ttk.Button(attachment_row,text=RLM+'＋ إضافة ملف',command=choose_files).pack(side='right', padx=2)
  ttk.Button(attachment_row,text=RLM+'🔗 ربط بملف هندسي',command=link_file).pack(side='right',padx=4)
  attach_list_frame = tk.Frame(card, bg=BG_PANEL)
  attach_list_frame.grid(row=14, column=0, columnspan=3, sticky='ew', padx=12, pady=2)
  def render_attach_list():
   for child in attach_list_frame.winfo_children(): child.destroy()
   for item in existing_attachments:
    f = tk.Frame(attach_list_frame, bg=BG_HEADER); f.pack(fill='x', pady=1)
    tk.Label(f, text=RLM+item.get('name', Path(item['path']).name), bg=BG_HEADER, fg=FG_PRIMARY, font=(TERM_FONT, 8)).pack(side='right', padx=4)
    ttk.Button(f, text='×', width=2, command=lambda i=item: remove_existing(i)).pack(side='left')
   for p in pending_files:
    f = tk.Frame(attach_list_frame, bg=BG_SELECTED); f.pack(fill='x', pady=1)
    name = p.get('name') if isinstance(p, dict) else Path(p).name
    tk.Label(f, text=RLM+name + ' (جديد)', bg=BG_SELECTED, fg=ACCENT_MATRIX, font=(TERM_FONT, 8)).pack(side='right', padx=4)
    ttk.Button(f, text='×', width=2, command=lambda p_=p: remove_pending(p_)).pack(side='left')
  def remove_existing(item):
   existing_attachments.remove(item); files_to_remove.append(item); render_attach_list()
  def remove_pending(p):
   pending_files.remove(p); render_attach_list()
  render_attach_list()
  actions=tk.Frame(card,bg=BG_PANEL);actions.grid(row=15,column=0,columnspan=3,sticky='ew',padx=10,pady=(14,12))
  def save():
   name_value=title.get().strip()
   if not name_value:return messagebox.showwarning('المهام','عنوان المهمة مطلوب.',parent=dialog)
   try:due_value=self._task_parse_date(due.get())
   except ValueError as exc:return messagebox.showwarning('موعد المهمة',str(exc),parent=dialog)
   if (start.get() or end.get()) and not due_value:return messagebox.showwarning('موعد المهمة','حدد تاريخًا للمهمة قبل إدخال الوقت.',parent=dialog)
   if start.get() and end.get() and end.get()<=start.get():return messagebox.showwarning('وقت المهمة','وقت النهاية يجب أن يكون بعد البداية.',parent=dialog)
   if project_var.get() not in self._task_project_names():return messagebox.showwarning('المشروع','أنشئ مشروعًا أولًا، ثم اختر المشروع الذي تتبعه المهمة.',parent=dialog)
   project_value=project_var.get();tag_values=','.join(dict.fromkeys(t.strip().lstrip('#') for t in re.split(r'[،,\s]+',tags.get()) if t.strip()));description=(safe_val(row, 'description', ''));rich_value=(safe_val(row, 'rich_text', ''));now=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
   with connect() as c:
    if row:
     c.execute('UPDATE tasks SET title=?,description=?,rich_text=?,project=?,due_date=?,start_time=?,end_time=?,priority=?,tags=?,recurrence=?,attachments=?,updated_at=? WHERE id=?',(name_value,description,rich_value,project_value,due_value,start.get() or None,end.get() or None,self._task_priority_num(priority.get()),tag_values,recurrence.get(),json.dumps(existing_attachments, ensure_ascii=False),now,row['id']))
     row_folder = self._task_document_folder(row)
     for item in files_to_remove:
      if not item.get('is_link'):
       try:
        p = (LOG/item['path']).resolve()
        if p.is_file() and p.is_relative_to(row_folder.resolve()): p.unlink()
       except Exception: pass
    else:
     cursor=c.execute('INSERT INTO tasks(title,description,rich_text,project,due_date,start_time,end_time,priority,tags,recurrence,attachments,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(name_value,description,rich_value,project_value,due_value,start.get() or None,end.get() or None,self._task_priority_num(priority.get()),tag_values,recurrence.get(),json.dumps(existing_attachments, ensure_ascii=False),now,now));self.new_task_document_id=cursor.lastrowid
   task_id=row['id'] if row else self.new_task_document_id
   try:
    self._task_ensure_document_artifacts(task_id)
    if pending_files: self._task_add_attachment_paths(task_id,pending_files)
   except (OSError,ValueError,sqlite3.Error) as exc:return messagebox.showerror('حفظ ملفات المهمة',str(exc),parent=dialog)
   dialog.destroy()
   if getattr(self,'task_calendar_active',False):
    self._task_calendar_draw(preserve_scroll=True)
    if getattr(self,'task_calendar_selected_id',None)==task_id:self._task_calendar_select_task(task_id)
   if hasattr(self,'task_tree') and self.task_tree.winfo_exists():self._task_refresh_rows()
  tk.Button(actions,text=RLM+'✓ حفظ المهمة',command=save,bg=BG_HEADER,fg=ACCENT_MATRIX,activebackground=ACCENT_MATRIX,activeforeground=BG_VOID,relief='solid',borderwidth=1,font=(TERM_FONT,9,'bold'),padx=14,pady=5,cursor='hand2').pack(side='right',padx=3);ttk.Button(actions,text=RLM+'إلغاء',command=dialog.destroy).pack(side='left',padx=3);dialog.bind('<Control-Return>',lambda e:(save(),'break'))
  dialog.update_idletasks()
  bx = self.winfo_rootx() + (self.winfo_width() - 580) // 2
  by = self.winfo_rooty() + (self.winfo_height() - 640) // 2
  dialog.geometry(f'580x{max(640, dialog.winfo_reqheight())}+{max(0,bx)}+{max(0,by)}')
  name.focus_set()
