# tasks_calendar.py - واجهة التقويم والجدول الزمني التفاعلي
from common import *
from storage import *

class TasksCalendarMixin:
 def show_task_calendar(self,project=None,initial_date=None):
  try:
   with connect() as c:
    for col in ('subtasks', 'recurrence'):
     try: c.execute(f'ALTER TABLE tasks ADD COLUMN {col} TEXT')
     except sqlite3.OperationalError: pass
  except Exception: pass
  self.task_scope = str(project or '')
  if not project and not self._task_project_names():return messagebox.showinfo('التقويم','أنشئ مشروعًا أولًا حتى تتمكن من إضافة مهام مرتبطة به.',parent=self)
  self.task_rollover_token=getattr(self,'task_rollover_token',0)+1;rollover_token=self.task_rollover_token;self.task_calendar_scope=str(project or '');self.task_calendar_date=initial_date or date.today();self.task_calendar_view=getattr(self,'task_calendar_view','month');self.task_calendar_active=True;self.task_calendar_selected_id=None;self._task_rollover_elapsed();self.clear();self.configure(bg='#eef3f7');self.title('Rasd | التقويم والمهام')
  head=self.header('التقويم والمهام')
  
  # أزرار الرجوع الذكية بناءً على مصدر الدخول (من داخل مشروع أو من قائمة المشاريع الرئيسية)
  if project and getattr(self, 'root', None):
   ttk.Button(head, text='← الرجوع للمشروع', command=self.build_explorer).pack(side='right', padx=5, pady=12)
   ttk.Button(head, text='☑ مهام المشروع', command=lambda:self.show_tasks(project)).pack(side='right', padx=5, pady=12)
  else:
   ttk.Button(head, text='← الرجوع للمشاريع', command=self.show_home).pack(side='right', padx=5, pady=12)
   ttk.Button(head, text='☑ قائمة المهام', command=lambda:self.show_tasks(None)).pack(side='right', padx=5, pady=12)

  body=tk.Frame(self,bg='#eef3f7');body.pack(fill='both',expand=True,padx=18,pady=12);top=tk.Frame(body,bg='#eef3f7');top.pack(fill='x',pady=(0,10))
  tk.Button(top,text='＋ إضافة مهمة',command=lambda:self._task_task_dialog(initial_date=self.task_calendar_date,project=self.task_calendar_scope or None),bg='#087e8b',fg='white',activebackground='#066b76',relief='flat',font=('Segoe UI',9,'bold'),padx=13,pady=7,cursor='hand2').pack(side='right',padx=4)
  for label,mode in (('الشهر','month'),('الأسبوع','week'),('يومي','day'),('أجندة','agenda')):ttk.Button(top,text=label,command=lambda m=mode:self._task_calendar_set_view(m)).pack(side='right',padx=3)
  ttk.Button(top,text='اليوم',command=lambda:self._task_calendar_goto(date.today())).pack(side='left',padx=3);ttk.Button(top,text='‹ التالي',command=lambda:self._task_calendar_shift(1)).pack(side='left',padx=3);ttk.Button(top,text='السابق ›',command=lambda:self._task_calendar_shift(-1)).pack(side='left',padx=3);self.task_calendar_title=tk.StringVar();tk.Label(top,textvariable=self.task_calendar_title,bg='#eef3f7',fg='#19394e',font=('Segoe UI',14,'bold')).pack(side='left',padx=10)
  tags=self._task_calendar_tag_values();self.task_calendar_tag_var=tk.StringVar(value='الكل');tk.Label(top,text='هاشتاج',bg='#eef3f7',fg='#607786',font=('Segoe UI',8)).pack(side='left',padx=(12,3));self.task_calendar_tag_combo=ttk.Combobox(top,textvariable=self.task_calendar_tag_var,values=('الكل',)+tuple('#'+x for x in tags),state='readonly',width=16,justify='right',style='Office.TCombobox');self.task_calendar_tag_combo.pack(side='left');self.task_calendar_tag_combo.bind('<<ComboboxSelected>>',lambda _e:self._task_calendar_draw(preserve_scroll=True))
  self.task_calendar_layout=tk.Frame(body,bg='#eef3f7');self.task_calendar_layout.pack(fill='both',expand=True);self.task_calendar_layout.grid_rowconfigure(0,weight=1);self.task_calendar_layout.grid_columnconfigure(0,weight=1)
  self.task_calendar_canvas=tk.Frame(self.task_calendar_layout,bg='white',highlightbackground='#d6e0e6',highlightthickness=1);self.task_calendar_canvas.grid(row=0,column=0,sticky='nsew')
  self.task_calendar_preview=tk.Frame(self.task_calendar_layout,bg='white',highlightbackground='#d6e0e6',highlightthickness=1,width=320);self.task_calendar_preview.grid_propagate(False);self._task_calendar_build_preview();self.task_calendar_preview.grid_remove()
  self._task_calendar_draw();self.after(30000,lambda:self._task_rollover_tick(rollover_token))

 def _task_calendar_tag_values(self):
  scope=getattr(self,'task_calendar_scope','')
  try:
   with connect() as c:rows=c.execute('SELECT tags FROM tasks WHERE tags<>?'+(' AND project=?' if scope else '')+' GROUP BY tags LIMIT 2000',('',scope) if scope else ('',)).fetchall()
   return sorted({tag.strip().lstrip('#') for row in rows for tag in str(row['tags'] or '').split(',') if tag.strip()},key=str.casefold)
  except sqlite3.Error:return []

 def _task_calendar_build_preview(self):
  panel=self.task_calendar_preview;panel.grid_columnconfigure(0,weight=1)
  tk.Label(panel,text='معاينة المهمة',bg='#dfe7ec',fg='#19394e',font=('Segoe UI',12,'bold'),anchor='e',padx=12,pady=12).grid(row=0,column=0,sticky='ew')
  self.task_calendar_preview_title=tk.Label(panel,text='اضغط مهمة لمعاينتها',bg='white',fg='#19394e',font=('Segoe UI',12,'bold'),anchor='e',justify='right',wraplength=285);self.task_calendar_preview_title.grid(row=1,column=0,sticky='ew',padx=12,pady=12)
  self.task_calendar_preview_meta=tk.Label(panel,text='',bg='white',fg='#607786',font=('Segoe UI',9),anchor='e',justify='right');self.task_calendar_preview_meta.grid(row=2,column=0,sticky='ew',padx=12,pady=4)
  self.task_calendar_preview_subtasks_frame=tk.Frame(panel,bg='white');self.task_calendar_preview_subtasks_frame.grid(row=3,column=0,sticky='nsew',padx=10,pady=4)
  panel.grid_rowconfigure(3,weight=1)
  self.task_calendar_preview_attachments=tk.Label(panel,text='',bg='white',fg='#607786',font=('Segoe UI',8),anchor='e',justify='right',wraplength=285);self.task_calendar_preview_attachments.grid(row=4,column=0,sticky='ew',padx=10,pady=4)
  self.task_calendar_preview_attachments_frame=tk.Frame(panel,bg='white');self.task_calendar_preview_attachments_frame.grid(row=5,column=0,sticky='ew',padx=8,pady=3)
  actions=tk.Frame(panel,bg='white');actions.grid(row=6,column=0,sticky='ew',padx=9,pady=8)
  ttk.Button(actions,text='تعديل المهمة',command=self._task_calendar_edit_selected).pack(fill='x',pady=2)
  ttk.Button(actions,text='فتح مجلد المهمة',command=self._task_calendar_open_selected_folder).pack(fill='x',pady=2)
  ttk.Button(actions,text='× حذف المهمة وملفاتها',command=self._task_calendar_delete_selected).pack(fill='x',pady=2)
  ttk.Button(actions,text='إخفاء المعاينة',command=self._task_calendar_hide_preview).pack(fill='x',pady=2)

 def _task_calendar_delete_selected(self):
  task_id=getattr(self,'task_calendar_selected_id',None)
  if not task_id:return
  if not messagebox.askyesno('حذف المهمة','هل أنت متأكد من حذف هذه المهمة بكل ملفاتها المرفقة نهائياً؟',parent=self):return
  self._task_delete_artifacts([task_id])
  with connect() as c:c.execute('DELETE FROM tasks WHERE id=?',(task_id,))
  self.task_calendar_selected_id = None
  self._task_calendar_hide_preview()
  self._task_calendar_draw(preserve_scroll=True)
  if getattr(self,'task_tree',None) and self.task_tree.winfo_exists():self._task_refresh_rows()

 def _task_calendar_select_task(self,task_id):
  with connect() as c:
   try: row=c.execute('SELECT * FROM tasks WHERE id=?',(task_id,)).fetchone()
   except sqlite3.Error: return
  if not row:return
  self.task_calendar_selected_id=int(task_id);self.task_calendar_preview.grid(row=0,column=1,sticky='nsew',padx=(8,0));self.task_calendar_layout.grid_columnconfigure(1,weight=0,minsize=320)
  self.task_calendar_preview_title.configure(text=row['title']);date_label=self._task_date_text(row['due_date']);time_label=' – '.join(x for x in (row['start_time'],row['end_time']) if x);priority={1:'عاجلة',2:'عادية',3:'منخفضة'}.get(row['priority'],'عادية');tags=' '.join('#'+x for x in (row['tags'] or '').split(',') if x);state='مكتملة' if row['completed_at'] else 'مفتوحة'
  try: rec_text = f" · دورية: {row['recurrence']}" if row['recurrence'] and row['recurrence']!='لا يوجد' else ""
  except Exception: rec_text = ""
  self.task_calendar_preview_meta.configure(text=f"المشروع: {row['project']}\nالموعد: {date_label}{(' · '+time_label) if time_label else ''}\nالأولوية: {priority} · {state}{rec_text}\n{tags}")
  for child in self.task_calendar_preview_subtasks_frame.winfo_children():child.destroy()
  try: subtasks = json.loads(row['subtasks']) if row['subtasks'] else []
  except Exception: subtasks = []
  completed_subs = sum(1 for s in subtasks if s.get('done'))
  tk.Label(self.task_calendar_preview_subtasks_frame, text=f'قائمة خطوات التنفيذ ({completed_subs}/{len(subtasks)}):', bg='white', fg='#19394e', font=('Segoe UI', 9, 'bold')).pack(anchor='e', pady=(0,4))
  for i, sub in enumerate(subtasks):
   f = tk.Frame(self.task_calendar_preview_subtasks_frame, bg='white')
   f.pack(fill='x', pady=2)
   var = tk.BooleanVar(value=sub.get('done', False))
   cb = tk.Checkbutton(f, text=sub.get('title', ''), variable=var, bg='white', activebackground='white', command=lambda idx=i, v=var: self._task_toggle_subtask(row['id'], idx, v))
   cb.pack(side='right', fill='x', expand=True, anchor='e')
   ttk.Button(f, text='×', width=2, command=lambda idx=i: self._task_delete_subtask(row['id'], idx)).pack(side='left', padx=1)
   ttk.Button(f, text='✎', width=2, command=lambda idx=i: self._task_edit_subtask(row['id'], idx)).pack(side='left', padx=1)
  add_f = tk.Frame(self.task_calendar_preview_subtasks_frame, bg='white')
  add_f.pack(fill='x', pady=6)
  new_sub_var = tk.StringVar()
  sub_entry = ttk.Entry(add_f, textvariable=new_sub_var, justify='right')
  sub_entry.pack(side='right', fill='x', expand=True, padx=2)
  sub_entry.bind('<Return>', lambda e, t=row['id'], v=new_sub_var: self._task_add_subtask(t, v, e.widget))
  ttk.Button(add_f, text='＋ خطوة', width=7, command=lambda t=row['id'], v=new_sub_var: self._task_add_subtask(t, v, sub_entry)).pack(side='left', padx=2)
  try: attachments=self._task_attachment_values(row)
  except Exception: attachments = []
  self.task_calendar_preview_attachments.configure(text='المرفقات والروابط: '+(str(len(attachments)) if attachments else 'لا يوجد'))
  if hasattr(self, 'task_calendar_preview_attachments_frame'):
   for child in self.task_calendar_preview_attachments_frame.winfo_children():child.destroy()
   for item in attachments:
    line=tk.Frame(self.task_calendar_preview_attachments_frame,bg='white');line.pack(fill='x',pady=1)
    ttk.Button(line,text='×',width=3,command=lambda i=item:self._task_remove_attachment(row['id'],i)).pack(side='left', padx=1)
    ttk.Button(line,text='👁',width=3,command=lambda i=item:self._task_open_attachment(i)).pack(side='left', padx=1)
    btn_text = item.get('name', Path(item['path']).name)
    tk.Label(line,text=btn_text, bg='white', fg='#3478e5', font=('Segoe UI', 8), anchor='e').pack(side='right',fill='x',expand=True)

 def _task_calendar_open_selected_text(self):
  if getattr(self,'task_calendar_selected_id',None):self._task_open_document(self.task_calendar_selected_id)
 def _task_calendar_edit_selected(self):
  task_id=getattr(self,'task_calendar_selected_id',None)
  if task_id:
   with connect() as c:row=c.execute('SELECT * FROM tasks WHERE id=?',(task_id,)).fetchone()
   if row:self._task_task_dialog(row=row,project_locked=bool(self.task_calendar_scope))
 def _task_calendar_open_selected_folder(self):
  task_id=getattr(self,'task_calendar_selected_id',None)
  if not task_id:return
  with connect() as c:row=c.execute('SELECT * FROM tasks WHERE id=?',(task_id,)).fetchone()
  if not row:return
  try:os.startfile(str(self._task_document_folder(row)))
  except Exception as exc:messagebox.showwarning('مجلد المهمة',str(exc),parent=self)
 def _task_calendar_hide_preview(self):
  self.task_calendar_preview.grid_remove();self.task_calendar_layout.grid_columnconfigure(1,weight=0,minsize=0)

 def _task_calendar_set_view(self,mode):self.task_calendar_view=mode;self._task_calendar_draw(preserve_scroll=False)
 def _task_calendar_goto(self,target):self.task_calendar_date=target;self._task_calendar_draw(preserve_scroll=False)
 def _task_calendar_shift(self,step):
  d=self.task_calendar_date;mode=self.task_calendar_view
  if mode=='month':self.task_calendar_date=date(d.year+((d.month-1+step)//12),(d.month-1+step)%12+1,1)
  elif mode=='week':self.task_calendar_date=d+timedelta(days=7*step)
  else:self.task_calendar_date=d+timedelta(days=step)
  self._task_calendar_draw(preserve_scroll=False)

 def _task_calendar_draw(self,preserve_scroll=True):
  if not getattr(self,'task_calendar_active',False) or not hasattr(self,'task_calendar_canvas'):return
  saved_x=getattr(self,'_cal_scroll_x',0.0);saved_y=getattr(self,'_cal_scroll_y',0.0)
  surf=getattr(self,'_cal_surface',None)
  if preserve_scroll and surf and surf.winfo_exists():
   try:saved_x=surf.xview()[0];saved_y=surf.yview()[0]
   except tk.TclError:pass
  elif not preserve_scroll:
   saved_x,saved_y=0.0,0.0
  self._cal_scroll_x,self._cal_scroll_y=saved_x,saved_y
  for w in self.task_calendar_canvas.winfo_children():w.destroy()
  scope=self.task_calendar_scope;d=self.task_calendar_date;view=self.task_calendar_view
  if view=='month':start=d.replace(day=1);end=date(d.year+int(d.month==12),1 if d.month==12 else d.month+1,1)
  elif view=='week':start=d-timedelta(days=d.weekday());end=start+timedelta(days=7)
  elif view=='agenda':start=d;end=d+timedelta(days=30)
  else:start=d;end=d+timedelta(days=1)
  sql='SELECT id,title,due_date,start_time,end_time,priority,project,tags,completed_at FROM tasks WHERE due_date>=? AND due_date<?';params=[start.isoformat(),end.isoformat()]
  if scope:sql+=' AND project=?';params.append(scope)
  tag_value=getattr(self,'task_calendar_tag_var',tk.StringVar(value='الكل')).get().strip().lstrip('#')
  if tag_value and tag_value!='الكل':sql+=" AND instr(','||tags||',', ','||?||',')>0";params.append(tag_value)
  sql+=' ORDER BY due_date,CASE WHEN start_time IS NULL THEN 1 ELSE 0 END,start_time,priority,title'
  with connect() as c:rows=c.execute(sql,params).fetchall()
  dated={}
  for row in rows:
   if row['due_date']:dated.setdefault(row['due_date'],[]).append(row)
  self.task_calendar_title.set(self._task_arabic_date(d,'month') if view=='month' else ('الأجندة · '+self._task_arabic_date(d) if view=='agenda' else (self._task_arabic_date(d) if view=='day' else 'الأسبوع · '+self._task_arabic_date(d))))
  if view=='month':
   grid=self.task_calendar_canvas;days=('الاثنين','الثلاثاء','الأربعاء','الخميس','الجمعة','السبت','الأحد')
   for col,label in enumerate(days):tk.Label(grid,text=label,bg='#dfe7ec',fg='#19394e',font=('Segoe UI',9,'bold')).grid(row=0,column=col,sticky='ew',padx=1,pady=1);grid.grid_columnconfigure(col,weight=1,uniform='month')
   first=d.replace(day=1);offset=first.weekday();ndays=(date(d.year+int(d.month==12),1 if d.month==12 else d.month+1,1)-first).days
   for day in range(1,ndays+1):
    current=first.replace(day=day);idx=offset+day-1;r=1+idx//7;cidx=idx%7;cell=tk.Frame(grid,bg='#f7fafb' if current!=date.today() else '#e8f5f4',highlightbackground='#d9e3e8',highlightthickness=1,height=100);cell.grid(row=r,column=cidx,sticky='nsew',padx=1,pady=1);cell.grid_propagate(False);grid.grid_rowconfigure(r,weight=1,uniform='monthrow');tk.Button(cell,text=str(day)+'  ＋',command=lambda target=current:self._task_task_dialog(initial_date=target,project=scope or None),bg=cell.cget('bg'),fg='#087e8b' if current==date.today() else '#526b7b',relief='flat',anchor='e',font=('Segoe UI',9,'bold')).pack(fill='x')
    for task in dated.get(current.isoformat(),[])[:3]:
     color='#81909a' if task['completed_at'] else {1:'#b92f3b',2:'#3378a8',3:'#a47d1c'}.get(task['priority'],'#3378a8');bg_task='#edf0f2' if task['completed_at'] else '#fce5e5' if task['priority']==1 else '#edf4fa' if task['priority']==2 else '#fff5dc';b=tk.Button(cell,text=('✓ ' if task['completed_at'] else '')+task['title'][:24],command=lambda r=task:self._task_calendar_select_task(r['id']),bg=bg_task,fg=color,anchor='e',relief='flat',font=('Segoe UI',8));b.pack(fill='x',padx=3,pady=1);b.bind('<Double-Button-1>',lambda _e,r=task:(self._task_open_document(r['id']),'break'))
    count=len(dated.get(current.isoformat(),[]))-3
    if count>0:tk.Label(cell,text=f'+ {count} مهام',bg=cell.cget('bg'),fg='#718491',font=('Segoe UI',8)).pack(anchor='e',padx=4)
    cell.bind('<Button-1>',lambda e,target=current:self._task_task_dialog(initial_date=target,project=scope or None))
  else:
   if view=='week':start=d-timedelta(days=d.weekday());span=[start+timedelta(days=i) for i in range(7)]
   elif view=='agenda':span=[d+timedelta(days=i) for i in range(30)]
   else:span=[d]
   if view=='agenda':
    for target in span:
     day_rows=dated.get(target.isoformat(),[])
     if day_rows:tk.Label(self.task_calendar_canvas,text=self._task_arabic_date(target),bg='#dfe7ec',fg='#19394e',anchor='e',font=('Segoe UI',9,'bold')).pack(fill='x',padx=6,pady=(7,1))
     for row in day_rows:self._task_calendar_task_row(self.task_calendar_canvas,target,row)
    if not any(target.isoformat() in dated for target in span):tk.Label(self.task_calendar_canvas,text='لا توجد مهام في الثلاثين يومًا القادمة.',bg='white',fg='#718491',font=('Segoe UI',11)).pack(expand=True,pady=30)
   else:self._task_calendar_timeline(span,dated,scope,saved_x,saved_y)

 def _task_calendar_timeline(self,span,dated,scope,saved_x=0.0,saved_y=0.0):
  host=self.task_calendar_canvas
  hint='انقر مساحة فارغة لتحديد الوقت كل 15 دقيقة · اسحب المهمة لتغيير موعدها · اسحب الحافة السفلية لتغيير مدتها · نقرة للمعاينة ونقرتان لفتح TXT'
  tk.Label(host,text=hint,bg='#e7f1f3',fg='#466575',font=('Segoe UI',8),anchor='e').pack(side='bottom',fill='x',pady=(4,0),ipady=4)
  time_width=82;columns=len(span);base_width=260 if self.task_calendar_view=='week' else 180;intervals={};max_lanes=1
  for target in span:
   events=[]
   for task in dated.get(target.isoformat(),[]):
    interval=self._task_calendar_interval(task)
    if interval:events.append({'row':task,'start':interval[0],'end':interval[1]})
   events.sort(key=lambda item:(item['start'],item['end'],int(item['row']['priority'])))
   groups=[];group=[];group_end=-1
   for item in events:
    if group and item['start']>=group_end:groups.append(group);group=[];group_end=-1
    group.append(item);group_end=max(group_end,item['end'])
   if group:groups.append(group)
   for overlap in groups:
    lane_ends=[]
    for item in overlap:
     lane=next((i for i,end in enumerate(lane_ends) if end<=item['start']),len(lane_ends))
     if lane==len(lane_ends):lane_ends.append(item['end'])
     else:lane_ends[lane]=item['end']
     item['lane']=lane
    for item in overlap:item['lanes']=len(lane_ends)
    max_lanes=max(max_lanes,len(lane_ends))
   intervals[target.isoformat()]=events
  day_width=max(base_width,min(max_lanes,8)*130);required_width=columns*day_width;timeline_height=24*60;header_h=78
  main_area=tk.Frame(host,bg='white');main_area.pack(fill='both',expand=True)
  main_area.grid_rowconfigure(1,weight=1);main_area.grid_columnconfigure(1,weight=1)
  corner=tk.Frame(main_area,bg='#dfe7ec',width=time_width,height=header_h);corner.grid(row=0,column=0,sticky='nsew');corner.grid_propagate(False)
  tk.Label(corner,text='اليوم / الوقت',bg='#dfe7ec',fg='#19394e',font=('Segoe UI',8,'bold')).place(x=0,y=0,width=time_width,height=36)
  tk.Label(corner,text='بدون ساعة',bg='#f1f5f7',fg='#607786',font=('Segoe UI',8,'bold')).place(x=0,y=36,width=time_width,height=42)
  header_canvas=tk.Canvas(main_area,bg='white',height=header_h,highlightthickness=0);header_canvas.grid(row=0,column=1,sticky='ew')
  time_canvas=tk.Canvas(main_area,bg='#edf2f5',width=time_width,highlightthickness=0);time_canvas.grid(row=1,column=0,sticky='ns')
  surface=tk.Canvas(main_area,bg='white',highlightthickness=0);surface.grid(row=1,column=1,sticky='nsew')
  self._cal_surface=surface;self._cal_time_canvas=time_canvas;self._cal_header_canvas=header_canvas
  def on_vscroll(*args):
   surface.yview(*args);time_canvas.yview(*args)
   try:self._cal_scroll_y=surface.yview()[0]
   except tk.TclError:pass
  def on_hscroll(*args):
   surface.xview(*args);header_canvas.xview(*args)
   try:self._cal_scroll_x=surface.xview()[0]
   except tk.TclError:pass
  scroll=ttk.Scrollbar(main_area,orient='vertical',command=on_vscroll);scroll.grid(row=1,column=2,sticky='ns')
  horizontal=ttk.Scrollbar(main_area,orient='horizontal',command=on_hscroll);horizontal.grid(row=2,column=1,sticky='ew')
  def update_yscroll(first,last):
   scroll.set(first,last);time_canvas.yview_moveto(first)
   try:self._cal_scroll_y=float(first)
   except ValueError:pass
  def update_xscroll(first,last):
   horizontal.set(first,last);header_canvas.xview_moveto(first)
   try:self._cal_scroll_x=float(first)
   except ValueError:pass
  surface.configure(yscrollcommand=update_yscroll,xscrollcommand=update_xscroll)
  time_canvas.configure(yscrollcommand=lambda f,l:scroll.set(f,l));header_canvas.configure(xscrollcommand=lambda f,l:horizontal.set(f,l))
  def sync_yscroll(units):
   surface.yview_scroll(units,'units');time_canvas.yview_scroll(units,'units')
   try:self._cal_scroll_y=surface.yview()[0]
   except tk.TclError:pass
  def sync_xscroll(units):
   surface.xview_scroll(units,'units');header_canvas.xview_scroll(units,'units')
   try:self._cal_scroll_x=surface.xview()[0]
   except tk.TclError:pass
  for c in (surface,time_canvas,header_canvas):
   c._sync_yscroll=sync_yscroll;c._sync_xscroll=sync_xscroll
  header_frame=tk.Frame(header_canvas,bg='white',height=header_h);header_win=header_canvas.create_window((0,0),window=header_frame,anchor='nw',height=header_h)
  header_frame.grid_rowconfigure(0,minsize=36);header_frame.grid_rowconfigure(1,minsize=42)
  for col,target in enumerate(span):
   header_frame.grid_columnconfigure(col,weight=1,uniform='cal-hdr',minsize=day_width)
   tk.Button(header_frame,text=self._task_arabic_date(target),command=lambda t=target:self._task_task_dialog(initial_date=t,project=scope or None),bg='#d9eff0' if target==date.today() else '#dfe7ec',fg='#19394e',relief='flat',font=('Segoe UI',8,'bold'),wraplength=150).grid(row=0,column=col,sticky='nsew',padx=1,pady=(0,1))
   strip=tk.Frame(header_frame,bg='#f7fafb',height=41);strip.grid(row=1,column=col,sticky='nsew',padx=1,pady=(0,1));strip.grid_propagate(False);strip.bind('<Button-1>',lambda _e,t=target:self._task_task_dialog(initial_date=t,project=scope or None))
   for task in dated.get(target.isoformat(),[]):
    if not (task['start_time'] or task['end_time']):self._task_calendar_timeline_event(strip,task)
   tk.Button(strip,text='＋',command=lambda t=target:self._task_task_dialog(initial_date=t,project=scope or None),bg='#f7fafb',fg='#087e8b',relief='flat',font=('Segoe UI',8)).pack(side='left')
  rail=tk.Frame(time_canvas,bg='#edf2f5',width=time_width,height=timeline_height);time_canvas.create_window((0,0),window=rail,anchor='nw',width=time_width,height=timeline_height)
  for hour in range(24):
   y=hour*60;tk.Frame(rail,bg='#d6e0e6',height=1).place(x=0,y=y,width=time_width,height=1)
   tk.Label(rail,text=f'{hour:02d}:00',bg='#edf2f5',fg='#526b7b',font=('Segoe UI',8,'bold'),anchor='n').place(x=0,y=y+2,width=time_width,height=22)
  timeline=tk.Frame(surface,bg='white',height=timeline_height);window=surface.create_window((0,0),window=timeline,anchor='nw',height=timeline_height)
  timeline.grid_rowconfigure(0,weight=1);self.task_calendar_day_bodies={}
  for col,target in enumerate(span):
   timeline.grid_columnconfigure(col,minsize=day_width,weight=1,uniform='timeline-day')
   day=tk.Frame(timeline,bg='white',width=day_width,height=timeline_height,highlightbackground='#d6e0e6',highlightthickness=0);day.grid(row=0,column=col,sticky='nsew',padx=1);day.grid_propagate(False);day._task_calendar_date=target;self.task_calendar_day_bodies[target.isoformat()]=day
   for hour in range(24):
    slot=tk.Frame(day,bg='white',height=60,highlightbackground='#e3e9ed',highlightthickness=1,cursor='hand2');slot.place(x=0,y=hour*60,relwidth=1,height=60);slot.bind('<Button-1>',lambda e,t=target,h=hour,s=slot:self._task_calendar_add_at_pointer(e,t,h,s,scope))
    tk.Button(slot,text='＋',command=lambda t=target,h=hour:self._task_task_dialog(initial_date=t,project=scope or None,initial_start=f'{h:02d}:00',initial_end=('23:45' if h==23 else f'{h+1:02d}:00')),bg='white',fg='#b4c3cb',activebackground='#e7f3f4',relief='flat',font=('Segoe UI',8)).place(relx=1.0,rely=1.0,anchor='se')
   for item in intervals[target.isoformat()]:self._task_calendar_timeline_event(day,item['row'],item['start'],item['end'],item['lane'],item['lanes'],target)
  def sync_layout(_e=None):
   try:
    w=max(surface.winfo_width(),required_width);surface.itemconfigure(window,width=w,height=timeline_height);header_canvas.itemconfigure(header_win,width=w,height=header_h)
    surface.configure(scrollregion=(0,0,w,timeline_height));header_canvas.configure(scrollregion=(0,0,w,header_h));time_canvas.configure(scrollregion=(0,0,time_width,timeline_height))
   except tk.TclError:pass
  timeline.bind('<Configure>',sync_layout);surface.bind('<Configure>',sync_layout)
  def restore():
   try:
    sync_layout();surface.xview_moveto(saved_x);header_canvas.xview_moveto(saved_x)
    surface.yview_moveto(saved_y);time_canvas.yview_moveto(saved_y)
   except tk.TclError:pass
  self.after_idle(restore)

 def _task_calendar_interval(self,row):
  start=self._task_time_to_24(row['start_time']) if row['start_time'] else None;end=self._task_time_to_24(row['end_time']) if row['end_time'] else None
  start_min=int(start[:2])*60+int(start[3:]) if start else None;end_min=int(end[:2])*60+int(end[3:]) if end else None
  if start_min is None and end_min is None:return None
  if start_min is None:start_min=max(0,(end_min or 30)-30)
  if end_min is None or end_min<=start_min:end_min=min(24*60,start_min+60)
  return start_min,max(start_min+15,end_min)

 def _task_calendar_add_at_pointer(self,event,target,hour,slot,project):
  height=max(1,slot.winfo_height());y=max(0,min(height-1,int(event.y)));quarter=min(3,int(y*4/height));start_minutes=hour*60+quarter*15;end_minutes=min(start_minutes+60,23*60+45)
  start=f'{start_minutes//60:02d}:{start_minutes%60:02d}';end=f'{end_minutes//60:02d}:{end_minutes%60:02d}' if end_minutes>start_minutes else None
  self._task_task_dialog(initial_date=target,project=project or None,initial_start=start,initial_end=end)

 def _task_calendar_timeline_event(self,parent,row,start_minute=None,end_minute=None,lane=0,lanes=1,day=None):
  if start_minute is None:
   priority=int(row['priority']);done=bool(row['completed_at']);color='#81909a' if done else {1:'#b92f3b',2:'#3378a8',3:'#a47d1c'}.get(priority,'#3378a8');text=('✓ ' if done else '')+(row['start_time']+' · ' if row['start_time'] else '')+row['title']+('   ['+row['project']+']' if row['project'] else '');bg='#edf0f2' if done else '#fce5e5' if priority==1 else '#edf4fa' if priority==2 else '#fff5dc';b=tk.Button(parent,text=text,command=lambda r=row:self._task_calendar_select_task(r['id']),anchor='e',bg=bg,fg=color,relief='flat',font=('Segoe UI',8));b.pack(fill='x',padx=2,pady=2);b.bind('<Double-Button-1>',lambda _e,r=row:(self._task_open_document(r['id']),'break'));return b
  priority=int(row['priority']);done=bool(row['completed_at']);color='#81909a' if done else {1:'#982934',2:'#244e70',3:'#725a16'}.get(priority,'#244e70');bg='#edf0f2' if done else {1:'#f8dddd',2:'#e5f0fa',3:'#fff1c9'}.get(priority,'#e5f0fa');height=max(15,end_minute-start_minute);caption=('✓ ' if done else '')+row['title']
  if height>=32:
   start_label=f'{start_minute//60:02d}:{start_minute%60:02d}';end_label=f'{end_minute//60:02d}:{end_minute%60:02d}'
   caption=f'{caption}\n{start_label}–{end_label}'
  label=tk.Label(parent,text=caption,bg=bg,fg=color,relief='solid',bd=1,anchor='ne',justify='right',wraplength=140,padx=4,pady=1,font=('Segoe UI',8,'bold' if priority==1 and not done else 'normal'),cursor='fleur');label.place(relx=lane/lanes,x=1,y=start_minute,relwidth=1/lanes,width=-3,height=height)
  label.bind('<ButtonPress-1>',lambda e,r=row,t=day,d=parent:self._task_calendar_event_press(e,r,t,d));label.bind('<B1-Motion>',self._task_calendar_event_motion);label.bind('<ButtonRelease-1>',self._task_calendar_event_release);label.bind('<Motion>',lambda e,w=label:w.configure(cursor='sb_v_double_arrow' if e.y>=w.winfo_height()-max(4,min(8,w.winfo_height()//4)) else 'fleur'));label.bind('<Leave>',lambda _e,w=label:w.configure(cursor='fleur'))
  return label

 def _task_calendar_event_press(self,event,row,day,day_body):
  interval=self._task_calendar_interval(row)
  if not interval:return 'break'
  resize_grip=max(4,min(8,event.widget.winfo_height()//4))
  self.task_calendar_drag_state={'id':int(row['id']),'row':dict(row),'day':day,'body':day_body,'start':interval[0],'end':interval[1],'duration':interval[1]-interval[0],'explicit_end':bool(row['end_time']),'mode':'resize' if event.y>=event.widget.winfo_height()-resize_grip else 'move','press_x':event.x_root,'press_y':event.y_root,'moved':False,'widget':event.widget}

 def _task_calendar_pointer_location(self,x_root,y_root,preferred_day=None):
  bodies=getattr(self,'task_calendar_day_bodies',{})
  for key,body in bodies.items():
   try:
    left,top,width,height=body.winfo_rootx(),body.winfo_rooty(),body.winfo_width(),body.winfo_height()
    if left<=x_root<left+width and top<=y_root<top+height:return date.fromisoformat(key),max(0,min(24*60,(y_root-top)*24*60/max(1,height)))
   except (tk.TclError,ValueError):continue
  if preferred_day is not None:
   body=bodies.get(preferred_day.isoformat())
   if body and body.winfo_exists():
    try:return preferred_day,max(0,min(24*60,(y_root-body.winfo_rooty())*24*60/max(1,body.winfo_height())))
    except tk.TclError:pass
  return None

 def _task_calendar_round_quarter(self,minutes):return min(23*60+45,max(0,int((minutes+7.5)//15)*15))

 def _task_calendar_event_motion(self,event):
  state=getattr(self,'task_calendar_drag_state',None)
  if not state:return
  if not state['moved'] and abs(event.x_root-state['press_x'])+abs(event.y_root-state['press_y'])<6:return
  state['moved']=True;event.widget.configure(relief='sunken',cursor='sb_v_double_arrow' if state['mode']=='resize' else 'fleur')
  location=self._task_calendar_pointer_location(event.x_root,event.y_root,state['day'] if state['mode']=='resize' else None)
  if location:
   target,minutes=location;minute=self._task_calendar_round_quarter(minutes);stamp=f'{minute//60:02d}:{minute%60:02d}'
   if state['mode']=='resize':self.task_calendar_title.set('تغيير نهاية المهمة إلى '+stamp)
   else:self.task_calendar_title.set('إفلات المهمة: '+self._task_arabic_date(target)+' · '+stamp)
  return 'break'

 def _task_calendar_event_release(self,event):
  state=getattr(self,'task_calendar_drag_state',None)
  if not state:return
  self.task_calendar_drag_state=None
  try:event.widget.configure(relief='solid',cursor='fleur')
  except tk.TclError:pass
  if not state['moved']:
   now=time.monotonic();last=getattr(self,'task_calendar_last_event_click',None)
   if last and last[0]==state['id'] and now-last[1]<=0.5:
    self.task_calendar_last_event_click=None;self._task_open_document(state['id'])
   else:
    self.task_calendar_last_event_click=(state['id'],now);self._task_calendar_select_task(state['id'])
   return 'break'
  self.task_calendar_last_event_click=None;row=state['row'];new_day=state['day'];new_start=state['start'];new_end=state['end']
  if state['mode']=='resize':
   location=self._task_calendar_pointer_location(event.x_root,event.y_root,state['day']);minute=self._task_calendar_round_quarter(location[1] if location else state['end'])
   new_end=max(state['start']+15,minute);new_end=min(new_end,23*60+45)
   if new_end<=state['start']:return 'break'
  else:
   location=self._task_calendar_pointer_location(event.x_root,event.y_root)
   if not location:return 'break'
   new_day,minutes=location;new_start=self._task_calendar_round_quarter(minutes);duration=state['duration']
   if new_start+duration>23*60+45:new_start=max(0,23*60+45-duration)
   new_end=new_start+duration
  start_text=f'{new_start//60:02d}:{new_start%60:02d}'
  end_text=(f'{new_end//60:02d}:{new_end%60:02d}' if new_end<=23*60+45 else None) if state['mode']=='resize' or state['explicit_end'] else None
  try:
   with connect() as c:c.execute('UPDATE tasks SET due_date=?,start_time=?,end_time=?,updated_at=? WHERE id=?',(new_day.isoformat(),start_text,end_text,datetime.now().strftime('%Y-%m-%d %H:%M:%S'),state['id']))
   self._task_ensure_document_artifacts(state['id']);self._task_calendar_draw(preserve_scroll=True)
   if getattr(self,'task_tree',None) and self.task_tree.winfo_exists():self._task_refresh_rows()
   self._task_calendar_select_task(state['id'])
  except (OSError,ValueError,sqlite3.Error) as exc:
   self._task_calendar_draw(preserve_scroll=True);messagebox.showerror('تعديل موعد المهمة',str(exc),parent=self)
  return 'break'

 def _task_calendar_task_row(self,parent,target,row):
  color='#81909a' if row['completed_at'] else {1:'#b92f3b',2:'#3378a8',3:'#a47d1c'}.get(row['priority'],'#3378a8');text=('✓ ' if row['completed_at'] else '')+(row['start_time']+' · ' if row['start_time'] else '')+row['title']+('   ['+row['project']+']' if row['project'] else '');bg='#edf0f2' if row['completed_at'] else '#fce5e5' if row['priority']==1 else '#edf4fa' if row['priority']==2 else '#fff5dc';b=tk.Button(parent,text=text,command=lambda r=row:self._task_calendar_select_task(r['id']),anchor='e',bg=bg,fg=color,relief='flat',font=('Segoe UI',9));b.pack(fill='x',padx=5,pady=3);b.bind('<Double-Button-1>',lambda _e,r=row:(self._task_open_document(r['id']),'break'))