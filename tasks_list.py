# tasks_list.py - واجهة قائمة المهام والنافذة المنبثقة
from common import *
from storage import *

class TasksListMixin:
 def show_tasks(self,project=None):
  try:
   with connect() as c:
    for col in ('subtasks', 'recurrence'):
     try: c.execute(f'ALTER TABLE tasks ADD COLUMN {col} TEXT')
     except sqlite3.OperationalError: pass
    c.execute("DELETE FROM files WHERE rel = '.tasks' OR rel LIKE '.tasks/%' OR rel LIKE '%/.tasks/%'")
    c.execute("DELETE FROM folder_tags WHERE path = '.tasks' OR path LIKE '.tasks/%' OR path LIKE '%/.tasks/%'")
  except Exception: pass
  self.task_rollover_token=getattr(self,'task_rollover_token',0)+1;rollover_token=self.task_rollover_token;self.task_calendar_active=False
  if project and getattr(self,'project',''):
   self.save_view_state();self._tasks_return_to_project=True
  else:self._tasks_return_to_project=False
  self.task_scope=str(project or '');self._task_rollover_elapsed();self._task_sync_text_documents(self.task_scope or None)
  try:
   with connect() as c:saved=c.execute("SELECT value FROM app_settings WHERE key='tasks_last_filter'").fetchone()
   self.task_filter=saved['value'] if saved and saved['value'] in ('open','today','tomorrow','upcoming','overdue','inbox','completed','custom') else getattr(self,'task_filter','open')
  except sqlite3.Error:self.task_filter=getattr(self,'task_filter','open')
  self.clear();self.configure(bg='#eef3f7');self.title('Rasd | قائمة المهام')
  head=self.header('قائمة المهام الذكية');back=self.build_explorer if self._tasks_return_to_project else self.show_home
  ttk.Button(head,text=('← العودة للمشروع' if self._tasks_return_to_project else '← المشاريع'),command=back).pack(side='right',padx=5,pady=12)
  if self.task_scope:ttk.Button(head,text='كل مهام المشاريع',command=self.show_tasks).pack(side='right',padx=5,pady=12)
  ttk.Button(head,text='▦ التقويم',command=lambda:self.show_task_calendar(self.task_scope or None)).pack(side='right',padx=5,pady=12)
  body=tk.Frame(self,bg='#eef3f7');body.pack(fill='both',expand=True,padx=22,pady=(12,18));body.grid_columnconfigure(0,weight=1);body.grid_rowconfigure(3,weight=1)
  title='مهام '+self.task_scope if self.task_scope else 'كل المهام في مكان واحد'
  tk.Label(body,text=title,bg='#eef3f7',fg='#19394e',font=('Segoe UI',16,'bold'),anchor='e').grid(row=0,column=0,sticky='ew')
  tk.Label(body,text='قائمة واحدة مترابطة: مهام كل مشروع وتقويمه والمرفقات المحفوظة داخل Log.',bg='#eef3f7',fg='#718491',font=('Segoe UI',9),anchor='e').grid(row=1,column=0,sticky='ew',pady=(2,10))
  toolbar=tk.Frame(body,bg='#eef3f7');toolbar.grid(row=2,column=0,sticky='ew',pady=(0,8));self.task_filter_buttons={};self.task_filter_count_vars={}
  filters=(('كل المهام','open'),('اليوم','today'),('غدًا','tomorrow'),('القادمة','upcoming'),('المتأخرة','overdue'),('بدون موعد','inbox'),('المكتملة','completed'),('تخصيص الفترة','custom'))
  for label,key in filters:
   count=tk.StringVar(value='0');self.task_filter_count_vars[key]=count;active=key==self.task_filter;b=tk.Button(toolbar,text=f'{label}  {count.get()}',command=(self._task_custom_filter if key=='custom' else lambda value=key:self._task_set_filter(value)),bg='#3478e5' if active else '#e5edf2',fg='white' if active else '#526b7b',activebackground='#2868ce',relief='flat',font=('Segoe UI',8,'bold' if active else 'normal'),padx=8,pady=7,cursor='hand2',borderwidth=0);b.pack(side='right',padx=(0,4));self.task_filter_buttons[key]=b
   count.trace_add('write',lambda *_args,k=key,text=label:self.task_filter_buttons[k].configure(text=f'{text}  {self.task_filter_count_vars[k].get()}'))
  self.task_search_var=tk.StringVar();search=ttk.Entry(toolbar,textvariable=self.task_search_var,width=20,justify='right');search.pack(side='left',fill='x',expand=True,padx=3);search.insert(0,'ابحث في المهام');search.bind('<FocusIn>',lambda e:search.delete(0,'end') if search.get()=='ابحث في المهام' else None);self.task_search_var.trace_add('write',lambda *_:self._task_set_search(self.task_search_var.get()))
  content=tk.Frame(body,bg='#eef3f7');content.grid(row=3,column=0,sticky='nsew');content.grid_columnconfigure(0,weight=0,minsize=310);content.grid_columnconfigure(1,weight=1);content.grid_rowconfigure(0,weight=1)
  self.task_preview_panel=tk.Frame(content,bg='white',highlightbackground='#d6e0e6',highlightthickness=1,width=310);self.task_preview_panel.grid(row=0,column=0,sticky='nsew',padx=(0,8));self.task_preview_panel.grid_propagate(False);self._task_build_preview_panel(self.task_preview_panel)
  workarea=tk.Frame(content,bg='#eef3f7');workarea.grid(row=0,column=1,sticky='nsew');workarea.grid_columnconfigure(0,weight=1);workarea.grid_rowconfigure(2,weight=1)
  capture=tk.Frame(workarea,bg='white',highlightbackground='#d6e0e6',highlightthickness=1);capture.grid(row=0,column=0,sticky='ew',pady=(0,8));capture.grid_columnconfigure(0,weight=1)
  self.task_quick_var=tk.StringVar();self.task_quick_entry=tk.Entry(capture,textvariable=self.task_quick_var,bg='white',fg='#243746',insertbackground='#3478e5',relief='flat',font=('Segoe UI',10),justify='right');self.task_quick_entry.grid(row=0,column=0,sticky='ew',padx=(12,4),pady=(8,2),ipady=7);self.task_quick_entry.insert(0,'اكتب مهمة سريعة')
  self.task_quick_entry.bind('<FocusIn>',lambda e:self.task_quick_entry.delete(0,'end') if self.task_quick_entry.get()=='اكتب مهمة سريعة' else None);self.task_quick_entry.bind('<Return>',lambda e:(self._task_add_quick(),'break'))
  self.task_quick_add_button=tk.Button(capture,text='＋ إضافة مهمة',command=self._task_add_quick,bg='#087e8b',fg='white',activebackground='#066b76',relief='flat',font=('Segoe UI',9,'bold'),padx=13,pady=5,cursor='hand2');self.task_quick_add_button.grid(row=0,column=1,padx=(3,10),pady=(8,2))
  opts=tk.Frame(capture,bg='white');opts.grid(row=1,column=0,columnspan=2,sticky='ew',padx=9,pady=(1,8))
  tk.Label(opts,text='الموعد',bg='white',fg='#607786',font=('Segoe UI',8)).pack(side='right',padx=(6,2));self.task_due_var=tk.StringVar();self.task_due_entry=ttk.Entry(opts,textvariable=self.task_due_var,width=12,justify='center');self.task_due_entry.pack(side='right',padx=3);ttk.Button(opts,text='🗓 التاريخ',command=lambda:self._task_pick_date(self.task_due_var,parent=self)).pack(side='right',padx=(0,4))
  tk.Label(opts,text='الوقت',bg='white',fg='#607786',font=('Segoe UI',8)).pack(side='right',padx=(6,2));self.task_start_var=tk.StringVar();self.task_end_var=tk.StringVar();self._task_time_control(opts,self.task_start_var,'من');self._task_time_control(opts,self.task_end_var,'إلى')
  tk.Label(opts,text='الأولوية',bg='white',fg='#607786',font=('Segoe UI',8)).pack(side='right',padx=(7,2));self.task_priority_var=tk.StringVar(value='عادية');ttk.Combobox(opts,textvariable=self.task_priority_var,values=('عاجلة','عادية','منخفضة'),state='readonly',width=9,justify='right',style='Office.TCombobox').pack(side='right',padx=3)
  tk.Label(opts,text='المشروع',bg='white',fg='#607786',font=('Segoe UI',8)).pack(side='right',padx=(7,2));project_names=self._task_project_names();project_choices=[self.task_scope] if self.task_scope else project_names;default_project=self.task_scope or (project_names[0] if len(project_names)==1 else 'اختر مشروعًا…');self.task_project_var=tk.StringVar(value=default_project);self.task_project_combo=ttk.Combobox(opts,textvariable=self.task_project_var,values=project_choices,state='disabled' if self.task_scope or not project_names else 'readonly',width=19,justify='right',style='Office.TCombobox');self.task_project_combo.pack(side='right',padx=3)
  ttk.Button(opts,text='غير محددة',command=lambda:self.task_due_var.set('')).pack(side='right',padx=3);ttk.Button(opts,text='اليوم',command=lambda:self.task_due_var.set(date.today().isoformat())).pack(side='right',padx=3);ttk.Button(opts,text='غدًا',command=lambda:self.task_due_var.set((date.today()+timedelta(days=1)).isoformat())).pack(side='right',padx=3)
  tagrow=tk.Frame(capture,bg='white');tagrow.grid(row=2,column=0,columnspan=2,sticky='ew',padx=10,pady=(0,8));tk.Label(tagrow,text='هاشتاجات',bg='white',fg='#607786',font=('Segoe UI',8)).pack(side='right',padx=(5,3));self.task_quick_tags_var=tk.StringVar();ttk.Entry(tagrow,textvariable=self.task_quick_tags_var,justify='right').pack(side='right',fill='x',expand=True,padx=3);tk.Label(tagrow,text='مثال: #مراجعة #موقع',bg='white',fg='#9aabb4',font=('Segoe UI',8)).pack(side='right',padx=5)
  self.task_quick_entry.configure(state='normal' if project_choices else 'disabled')
  if not project_choices:self.task_quick_add_button.configure(state='disabled')
  self.task_time_window=tk.Frame(workarea,bg='#e7f1f3');self.task_time_window.grid(row=1,column=0,sticky='ew',pady=(0,8));self.task_time_window.grid_remove()
  tk.Label(self.task_time_window,text='عرض مهام اليوم خلال الفترة',bg='#e7f1f3',fg='#466575',font=('Segoe UI',8)).pack(side='right',padx=8);self.task_window_start=tk.StringVar(value='');self.task_window_end=tk.StringVar(value='');self._task_time_control(self.task_time_window,self.task_window_start,'من');self._task_time_control(self.task_time_window,self.task_window_end,'إلى');ttk.Button(self.task_time_window,text='تطبيق',command=self._task_refresh_rows).pack(side='right',padx=5)
  list_card=tk.Frame(workarea,bg='white',highlightbackground='#d6e0e6',highlightthickness=1);list_card.grid(row=2,column=0,sticky='nsew');list_card.grid_rowconfigure(0,weight=1);list_card.grid_columnconfigure(0,weight=1);cols=('title','due','priority','project','tags');self.task_tree=ttk.Treeview(list_card,columns=cols,displaycolumns=('tags','project','priority','due','title'),show='headings',selectmode='extended')
  for col,label,width,anchor in (('title','المهمة',370,'e'),('due','الموعد',160,'center'),('priority','الأولوية',95,'center'),('project','المشروع',145,'e'),('tags','التصنيفات',160,'e')):self.task_tree.heading(col,text=label);self.task_tree.column(col,width=width,minwidth=65,anchor=anchor,stretch=col=='title')
  self.task_tree.grid(row=0,column=0,sticky='nsew',padx=(5,0),pady=5);scroll=ttk.Scrollbar(list_card,orient='vertical',command=self.task_tree.yview);scroll.grid(row=0,column=1,sticky='ns',pady=5);self.task_tree.configure(yscrollcommand=scroll.set)
  self.task_tree.tag_configure('urgent',background='#fce4e4',foreground='#8d2028');self.task_tree.tag_configure('normal',background='#e9f2fb',foreground='#244e70');self.task_tree.tag_configure('low',background='#fff4d6',foreground='#725a16');self.task_tree.tag_configure('overdue',background='#f8dddd',foreground='#922c35');self.task_tree.tag_configure('today',background='#e4f3f1',foreground='#1b5b57');self.task_tree.tag_configure('done',foreground='#8997a1');self.task_tree.tag_configure('day_group',background='#dfe9ef',foreground='#19394e');self.task_tree.bind('<Double-1>',lambda e:self._task_open_selected_document());self.task_tree.bind('<<TreeviewSelect>>',lambda e:self._task_preview_selected())
  footer=tk.Frame(workarea,bg='#eef3f7');footer.grid(row=3,column=0,sticky='ew',pady=(7,0));ttk.Button(footer,text='✓ إكمال',command=self._task_toggle_done).pack(side='right',padx=3);ttk.Button(footer,text='✎ تعديل المهمة',command=self._task_edit_selected).pack(side='right',padx=3);self.task_postpone_button=ttk.Button(footer,text='↷ تأجيل للغد',command=self._task_postpone);self.task_postpone_button.pack(side='right',padx=3);ttk.Button(footer,text='× حذف المهام وملفاتها',command=self._task_delete_selected).pack(side='right',padx=3)
  ttk.Button(footer,text='🖨 طباعة وتصدير PDF',command=self._task_export_print).pack(side='right',padx=3)
  self.task_page_size=400;self.task_page=0;self.task_page_var=tk.StringVar(value='');ttk.Button(footer,text='التالي ›',command=lambda:self._task_page_shift(1)).pack(side='left',padx=2);tk.Label(footer,textvariable=self.task_page_var,bg='#eef3f7',fg='#526b7b',font=('Segoe UI',8)).pack(side='left',padx=4);ttk.Button(footer,text='‹ السابق',command=lambda:self._task_page_shift(-1)).pack(side='left',padx=2);self.task_result_var=tk.StringVar(value='');tk.Label(footer,textvariable=self.task_result_var,bg='#eef3f7',fg='#718491',font=('Segoe UI',8),anchor='e').pack(side='left',fill='x',expand=True,padx=8)
  self._task_update_context_controls();self._task_refresh_rows();self.task_quick_entry.focus_set()
  self.after(30000,lambda token=rollover_token:self._task_rollover_tick(token))

 def _task_time_control(self,parent,var,label):
  box=tk.Frame(parent,bg=parent.cget('bg'));box.pack(side='right',padx=2);tk.Label(box,text=label,bg=parent.cget('bg'),fg='#607786',font=('Segoe UI',8)).pack(side='right',padx=2)
  display=tk.StringVar(value=self._task_time_display(var.get()));values=tuple(self._task_time_display(f'{h:02d}:{m:02d}') for h in range(24) for m in (0,15,30,45))
  combo=ttk.Combobox(box,textvariable=display,values=values,state='readonly',width=11,justify='center',style='Office.TCombobox');combo.pack(side='right')
  def from_display(_event=None):
   canonical=self._task_time_to_24(display.get())
   if canonical is not None:var.set(canonical)
  def from_model(*_):
   shown=self._task_time_display(var.get())
   if display.get()!=shown:display.set(shown)
  combo.bind('<<ComboboxSelected>>',from_display);var.trace_add('write',from_model)

 def _task_route_mousewheel(self,event):
  try:target=self.winfo_containing(event.x_root,event.y_root)
  except tk.TclError:return
  if target is None:return
  picker=getattr(self,'task_date_picker',None)
  if picker and picker.winfo_exists():
   try:
    if target.winfo_toplevel()==picker:
     shift=getattr(self,'task_date_picker_state',{}).get('shift')
     if shift:shift(-1 if event.delta>0 else 1);return 'break'
   except tk.TclError:pass
  if target.winfo_class() in ('Treeview','Text','Listbox','Combobox','TCombobox'):return
  widget=target
  while widget is not None and widget is not self:
   if isinstance(widget,tk.Canvas):
    if widget in (getattr(self,'preview_image',None),getattr(self,'search_preview_image',None)):return
    amount=int(-event.delta/120) or (-1 if event.delta>0 else 1)
    try:
     if event.state & 0x0001:
      if hasattr(widget,'_sync_xscroll'):widget._sync_xscroll(amount)
      else:widget.xview_scroll(amount,'units')
     else:
      if hasattr(widget,'_sync_yscroll'):widget._sync_yscroll(amount)
      else:widget.yview_scroll(amount,'units')
     return 'break'
    except tk.TclError:pass
   widget=getattr(widget,'master',None)

 def _task_external_focus_sync(self,event=None):
  if not getattr(self,'task_tree',None) or not self.task_tree.winfo_exists():return
  now=time.monotonic()
  if now-getattr(self,'task_last_focus_sync',0)<1.0:return
  self.task_last_focus_sync=now
  if self._task_sync_text_documents(getattr(self,'task_scope','') or None):self._task_refresh_rows()

 def _task_pick_date(self,var,initial=None,parent=None):
  try:chosen=datetime.strptime(var.get(),'%Y-%m-%d').date() if var.get() else (initial or date.today())
  except ValueError:chosen=initial or date.today()
  host=parent if (parent and parent.winfo_exists()) else self
  previous_grab=self.grab_current()
  existing=getattr(self,'task_date_picker',None)
  if existing and existing.winfo_exists():
   try:existing.destroy()
   except tk.TclError:pass
  top=tk.Toplevel(host);self.task_date_picker=top;top.title('اختيار التاريخ');top.configure(bg='#eef3f7');top.transient(host);top.resizable(False,False)
  header=tk.Frame(top,bg='#102c3d',height=42);header.pack(fill='x');header.pack_propagate(False)
  caption=tk.StringVar()
  tk.Button(header,text='‹',command=lambda:shift(-1),bg='#102c3d',fg='white',activebackground='#1b455c',activeforeground='white',relief='flat',font=('Segoe UI',12,'bold'),padx=10,cursor='hand2').pack(side='left',padx=6,pady=4)
  tk.Button(header,text='›',command=lambda:shift(1),bg='#102c3d',fg='white',activebackground='#1b455c',activeforeground='white',relief='flat',font=('Segoe UI',12,'bold'),padx=10,cursor='hand2').pack(side='right',padx=6,pady=4)
  tk.Label(header,textvariable=caption,bg='#102c3d',fg='white',font=('Segoe UI',11,'bold')).pack(side='top',pady=8)
  grid=tk.Frame(top,bg='white');grid.pack(fill='both',expand=True,padx=10,pady=8)
  state={'var':var,'chosen':chosen,'month':chosen.replace(day=1)};self.task_date_picker_state=state
  def close():
   if getattr(self,'task_date_picker',None) is top:self.task_date_picker=None;self.task_date_picker_state=None
   try:top.grab_release()
   except tk.TclError:pass
   try:top.destroy()
   except tk.TclError:pass
   if previous_grab and previous_grab.winfo_exists():
    try:previous_grab.grab_set();previous_grab.lift();previous_grab.focus_force()
    except tk.TclError:pass
  def choose(value):
   state['var'].set(value)
   close()
  def draw():
   for w in grid.winfo_children():w.destroy()
   month=state['month'];caption.set(self._task_arabic_date(month,'month'))
   for c,name in enumerate(('إث','ثلا','أر','خمي','جمع','سبت','أحد')):tk.Label(grid,text=name,bg='white',fg='#718491',width=5,font=('Segoe UI',8,'bold')).grid(row=0,column=c,pady=3)
   first=month;offset=first.weekday();days=(date(first.year+int(first.month==12),1 if first.month==12 else first.month+1,1)-first).days
   for daynum in range(1,days+1):
    idx=offset+daynum-1;r=1+idx//7;c=idx%7;d=first.replace(day=daynum);bg='#3478e5' if d==state['chosen'] else ('#d9eff0' if d==date.today() else 'white');fg='white' if d==state['chosen'] else '#19394e'
    b=tk.Button(grid,text=str(daynum),width=4,bg=bg,fg=fg,activebackground='#2868ce',activeforeground='white',relief='flat',font=('Segoe UI',9,'bold' if d in (state['chosen'],date.today()) else 'normal'),cursor='hand2',command=lambda target=d:choose(target.isoformat()))
    b.grid(row=r,column=c,padx=1,pady=1)
   ttk.Button(grid,text='بدون موعد',command=lambda:choose('')).grid(row=7,column=0,columnspan=3,sticky='ew',pady=(8,0))
   ttk.Button(grid,text='اليوم',command=lambda:choose(date.today().isoformat())).grid(row=7,column=4,columnspan=3,sticky='ew',pady=(8,0))
  def shift(amount):
   m=state['month'];state['month']=(date(m.year+1,1,1) if m.month==12 and amount>0 else date(m.year-1,12,1) if m.month==1 and amount<0 else date(m.year,m.month+amount,1));draw()
  state['draw']=draw;state['shift']=shift
  draw()
  top.bind('<Escape>',lambda _e:close());top.protocol('WM_DELETE_WINDOW',close)
  top.update_idletasks()
  bx=host.winfo_rootx()+(host.winfo_width()-top.winfo_width())//2
  by=host.winfo_rooty()+(host.winfo_height()-top.winfo_height())//2
  top.geometry(f'+{max(0,bx)}+{max(0,by)}')
  try:top.grab_set();top.lift();top.focus_force()
  except tk.TclError:pass

 def _task_custom_filter(self):
  dialog=tk.Toplevel(self);dialog.title('تخصيص فترة المهام');dialog.configure(bg='#eef3f7');dialog.transient(self);dialog.grab_set();card=tk.Frame(dialog,bg='white');card.pack(fill='both',expand=True,padx=14,pady=14);start=tk.StringVar(value=getattr(self,'task_range_start',date.today().isoformat()));end=tk.StringVar(value=getattr(self,'task_range_end',date.today().isoformat()));status_labels={'open':'غير المكتملة','completed':'المكتملة','all':'الكل'};status=tk.StringVar(value=status_labels.get(getattr(self,'task_range_status','open'),'غير المكتملة'))
  for row,(label,var) in enumerate((('من تاريخ',start),('إلى تاريخ',end))):
   tk.Label(card,text=label,bg='white',fg='#19394e').grid(row=row,column=2,padx=6,pady=7);ttk.Entry(card,textvariable=var,width=14,justify='center').grid(row=row,column=1,padx=4);ttk.Button(card,text='▦',command=lambda v=var:self._task_pick_date(v,parent=dialog)).grid(row=row,column=0,padx=4)
  def apply():
   try:a=self._task_parse_date(start.get());b=self._task_parse_date(end.get());assert a and b and a<=b
   except Exception:return messagebox.showwarning('الفترة','اختر نطاقًا صحيحًا للتواريخ.',parent=dialog)
   self.task_range_start=a;self.task_range_end=b;self.task_range_status=next((key for key,label in status_labels.items() if label==status.get()),'open');dialog.destroy();self._task_set_filter('custom')
  tk.Label(card,text='حالة المهام',bg='white',fg='#19394e').grid(row=2,column=2,padx=6,pady=7);ttk.Combobox(card,textvariable=status,values=tuple(status_labels.values()),state='readonly',justify='right',style='Office.TCombobox').grid(row=2,column=0,columnspan=2,sticky='ew',padx=4)
  ttk.Button(card,text='عرض الفترة',command=apply).grid(row=3,column=0,columnspan=3,pady=10);dialog.update_idletasks();dialog.geometry(f'+{self.winfo_rootx()+100}+{self.winfo_rooty()+100}')

 def _task_set_filter(self,key):
  self.task_filter=key;self.task_page=0
  try:
   with connect() as c:c.execute("INSERT INTO app_settings(key,value) VALUES('tasks_last_filter',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(key,))
  except sqlite3.Error:pass
  for value,button in self.task_filter_buttons.items():
   active=value==key;button.configure(bg='#3478e5' if active else '#e5edf2',fg='white' if active else '#526b7b',font=('Segoe UI',8,'bold' if active else 'normal'))
  self._task_update_context_controls();self._task_refresh_rows()
 def _task_update_context_controls(self):
  if not hasattr(self,'task_time_window'):return
  self.task_time_window.grid() if self.task_filter=='today' and self.task_time_window.winfo_exists() else self.task_time_window.grid_remove()
  if hasattr(self,'task_postpone_button'):self.task_postpone_button.pack(side='right',padx=3) if self.task_filter=='today' else self.task_postpone_button.pack_forget()
 def _task_set_search(self,value):
  self.task_search_value='' if value=='ابحث في المهام' else str(value);self.task_page=0
  job=getattr(self,'task_search_job',None)
  if job:
   try:self.after_cancel(job)
   except tk.TclError:pass
  self.task_search_job=self.after(220,self._task_refresh_rows)

 def _task_refresh_rows(self):
  if not hasattr(self,'task_tree') or not self.task_tree.winfo_exists():return
  self._task_rollover_elapsed();search=str(getattr(self,'task_search_value','')).casefold().strip();scope=getattr(self,'task_scope','')
  if search:self._task_sync_text_documents(scope or None)
  today=date.today().isoformat();tomorrow=(date.today()+timedelta(days=1)).isoformat()
  try:
   with connect() as c:
    base=' WHERE project=?' if scope else '';base_params=(scope,) if scope else ()
    aggregate=c.execute('SELECT COUNT(*) total,SUM(completed_at IS NULL) open,SUM(completed_at IS NULL AND due_date=?) today,SUM(completed_at IS NULL AND due_date=?) tomorrow,SUM(completed_at IS NULL AND due_date IS NOT NULL AND due_date>?) upcoming,SUM(completed_at IS NULL AND due_date IS NOT NULL AND due_date<?) overdue,SUM(completed_at IS NULL AND due_date IS NULL) inbox,SUM(completed_at IS NOT NULL) completed FROM tasks'+base,(today,tomorrow,tomorrow,today)+base_params).fetchone()
    counts={key:int(aggregate[key] or 0) for key in ('open','today','tomorrow','upcoming','overdue','inbox','completed')}
    if getattr(self,'task_range_start','') and getattr(self,'task_range_end',''):
     status=getattr(self,'task_range_status','open');extra=' AND due_date BETWEEN ? AND ?';params=list(base_params)+[self.task_range_start,self.task_range_end]
     if status=='open':extra+=' AND completed_at IS NULL'
     elif status=='completed':extra+=' AND completed_at IS NOT NULL'
     counts['custom']=int(c.execute('SELECT COUNT(*) FROM tasks'+base+extra,params).fetchone()[0])
    for key,var in getattr(self,'task_filter_count_vars',{}).items():var.set(f'{counts.get(key,0):,}')
    clauses=[];params=[]
    if scope:clauses.append('t.project=?');params.append(scope)
    key=getattr(self,'task_filter','open')
    if key=='today':clauses.extend(('t.completed_at IS NULL','t.due_date=?'));params.append(today)
    elif key=='tomorrow':clauses.extend(('t.completed_at IS NULL','t.due_date=?'));params.append(tomorrow)
    elif key=='upcoming':clauses.extend(('t.completed_at IS NULL','t.due_date>?'));params.append(tomorrow)
    elif key=='overdue':clauses.extend(('t.completed_at IS NULL','t.due_date IS NOT NULL','t.due_date<?'));params.append(today)
    elif key=='inbox':clauses.extend(('t.completed_at IS NULL','t.due_date IS NULL'))
    elif key=='completed':clauses.append('t.completed_at IS NOT NULL')
    elif key!='custom':clauses.append('t.completed_at IS NULL')
    if key=='custom':
     clauses.append('t.due_date BETWEEN ? AND ?');params.extend((getattr(self,'task_range_start',''),getattr(self,'task_range_end','')))
     status=getattr(self,'task_range_status','open')
     if status=='open':clauses.append('t.completed_at IS NULL')
     elif status=='completed':clauses.append('t.completed_at IS NOT NULL')
     elif status!='all':clauses.append('t.completed_at IS NULL')
    if key=='today':
     a=self.task_window_start.get() if hasattr(self,'task_window_start') else '';b=self.task_window_end.get() if hasattr(self,'task_window_end') else ''
     if a:clauses.append('(t.end_time IS NULL OR t.end_time>=?)');params.append(a)
     if b:clauses.append('(t.start_time IS NULL OR t.start_time<=?)');params.append(b)
    query_where=list(clauses);query_params=list(params);fts_query=''
    if search:
     tokens=re.findall(r'[^\W_]+',search,flags=re.UNICODE)
     fts_query=' AND '.join('"'+token.replace('"','""')+'"*' for token in tokens)
     if fts_query:query_where.append('t.id IN (SELECT rowid FROM task_fts WHERE task_fts MATCH ?)');query_params.append(fts_query)
     else:query_where.append('(t.title LIKE ? OR t.description LIKE ? OR t.project LIKE ? OR t.tags LIKE ?)');query_params.extend(['%'+search+'%']*4)
    where=' WHERE '+' AND '.join(query_where) if query_where else ''
    try:total=int(c.execute('SELECT COUNT(*) FROM tasks t'+where,query_params).fetchone()[0])
    except sqlite3.OperationalError:
     if not search or not fts_query:raise
     query_where=query_where[:-1]+['(t.title LIKE ? OR t.description LIKE ? OR t.project LIKE ? OR t.tags LIKE ?)'];query_params=query_params[:-1]+['%'+search+'%']*4;where=' WHERE '+' AND '.join(query_where);total=int(c.execute('SELECT COUNT(*) FROM tasks t'+where,query_params).fetchone()[0])
    page_size=max(50,int(getattr(self,'task_page_size',400)));pages=max(1,(total+page_size-1)//page_size);self.task_page=max(0,min(getattr(self,'task_page',0),pages-1));offset=self.task_page*page_size
    order=" ORDER BY CASE WHEN t.completed_at IS NULL THEN 0 ELSE 1 END,CASE WHEN t.due_date IS NULL THEN 1 ELSE 0 END,t.due_date, t.priority,CASE WHEN t.start_time IS NULL THEN 1 ELSE 0 END,t.start_time,t.created_at DESC"
    try: rows=c.execute('SELECT t.id,t.title,t.due_date,t.start_time,t.end_time,t.priority,t.project,t.tags,t.completed_at,t.created_at,t.subtasks,t.recurrence FROM tasks t'+where+order+' LIMIT ? OFFSET ?',query_params+[page_size,offset]).fetchall()
    except sqlite3.OperationalError: rows=c.execute('SELECT t.id,t.title,t.due_date,t.start_time,t.end_time,t.priority,t.project,t.tags,t.completed_at,t.created_at FROM tasks t'+where+order+' LIMIT ? OFFSET ?',query_params+[page_size,offset]).fetchall()
  except sqlite3.Error as exc:
   self.task_result_var.set('تعذر تحميل المهام: '+str(exc)[:100]);return
  selected_before=self.task_tree.selection()
  for iid in self.task_tree.get_children():self.task_tree.delete(iid)
  grouped=key=='upcoming';last_day=None
  for row in rows:
   due=row['due_date'] or '';done=bool(row['completed_at']);priority=int(row['priority']);tags=[x for x in (row['tags'] or '').split(',') if x]
   try: rec_icon = ' 🔄' if row['recurrence'] and row['recurrence'] != 'لا يوجد' else ''
   except Exception: rec_icon = ''
   if grouped and due!=last_day:
    try:day=datetime.strptime(due,'%Y-%m-%d').date();label=day.strftime('%A %d-%m-%Y')
    except ValueError:label=due
    self.task_tree.insert('','end',iid='day:'+due,values=('▾  '+label,'','','',''),tags=('day_group',));last_day=due
   time_label=' – '.join(x for x in (row['start_time'],row['end_time']) if x);due_label=self._task_date_text(due)+((' · '+time_label) if time_label else '')
   tag='done' if done else ('overdue' if due and due<today else ('today' if due==today else ({1:'urgent',2:'normal',3:'low'}.get(priority,''))))
   values=(('✓  ' if done else '')+row['title']+rec_icon,due_label,{1:'عاجلة',2:'عادية',3:'منخفضة'}.get(priority,'عادية'),row['project'],'  '.join('#'+x for x in tags))
   self.task_tree.insert('','end',iid=str(row['id']),values=values,tags=(tag,) if tag else ())
  for iid in selected_before:
   if self.task_tree.exists(iid):self.task_tree.selection_add(iid)
  shown=len(rows);self.task_result_var.set(f'{total:,} مهمة في النتيجة · يعرض {offset+1 if total else 0}–{offset+shown:,} من {total:,}')
  self.task_page_var.set(f'صفحة {self.task_page+1:,} / {pages:,}')
  self._task_preview_selected()

 def _task_page_shift(self,step):
  self.task_page=max(0,getattr(self,'task_page',0)+step);self._task_refresh_rows()

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
        d = datetime.strptime(row['due_date'], '%Y-%m-%d').date()
        if rec == 'يومياً': next_d = d + timedelta(days=1)
        elif rec == 'أسبوعياً': next_d = d + timedelta(days=7)
        elif rec == 'شهرياً': next_d = date(d.year + (d.month // 12), (d.month % 12) + 1, d.day)
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
  html += "<style>body{font-family:'Segoe UI', Tahoma, Arial; padding:30px; color:#19394e; background:#f4f7f9;} "
  html += "table{width:100%; border-collapse:collapse; margin-top:25px; background:white; box-shadow: 0 1px 3px rgba(0,0,0,0.1);} "
  html += "th, td{border:1px solid #d6e0e6; padding:12px; text-align:right;} "
  html += "th{background-color:#087e8b; color:white; font-weight:bold;} "
  html += "h2{color:#102c3d; border-bottom: 2px solid #087e8b; padding-bottom: 10px;} "
  html += ".header-row{background-color:#dfe7ec; font-weight:bold; color:#102c3d;} "
  html += "@media print { body{background:white;} table{box-shadow:none;} }</style></head><body>"
  html += f"<h2>تقرير المهام - النطاق: {self.task_scope or 'كل المشاريع'}</h2>"
  html += f"<p style='color:#617789;'>تاريخ التقرير: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>"
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

 def _task_build_preview_panel(self,panel):
  panel.grid_columnconfigure(0,weight=1)
  tk.Label(panel,text='معاينة المهمة',bg='#dfe7ec',fg='#19394e',font=('Segoe UI',12,'bold'),anchor='e',padx=12,pady=12).grid(row=0,column=0,sticky='ew')
  self.task_preview_title=tk.Label(panel,text='اختر مهمة من القائمة',bg='white',fg='#19394e',font=('Segoe UI',13,'bold'),anchor='e',justify='right',wraplength=275);self.task_preview_title.grid(row=1,column=0,sticky='ew',padx=12,pady=(16,8))
  self.task_preview_meta=tk.Label(panel,text='ستظهر تفاصيلها ومرفقاتها هنا.',bg='white',fg='#718491',font=('Segoe UI',9),anchor='e',justify='right',wraplength=275);self.task_preview_meta.grid(row=2,column=0,sticky='ew',padx=12,pady=(0,10))
  self.task_preview_subtasks_frame=tk.Frame(panel,bg='white');self.task_preview_subtasks_frame.grid(row=3,column=0,sticky='nsew',padx=10,pady=4)
  panel.grid_rowconfigure(3,weight=1) 
  self.task_preview_attachments=tk.Label(panel,text='',bg='white',fg='#607786',font=('Segoe UI',8),anchor='e',justify='right',wraplength=275);self.task_preview_attachments.grid(row=4,column=0,sticky='ew',padx=12,pady=7)
  self.task_preview_attachments_frame=tk.Frame(panel,bg='white');self.task_preview_attachments_frame.grid(row=5,column=0,sticky='ew',padx=8,pady=3)
  actions=tk.Frame(panel,bg='white');actions.grid(row=6,column=0,sticky='ew',padx=8,pady=(4,10));ttk.Button(actions,text='فتح ملف المهمة TXT',command=self._task_open_selected_document).pack(fill='x',pady=2);ttk.Button(actions,text='تعديل المهمة',command=self._task_edit_selected).pack(fill='x',pady=2);ttk.Button(actions,text='فتح مجلد المهمة',command=self._task_open_selected_folder).pack(fill='x',pady=2)

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
   self.task_preview_title.configure(text='اختر مهمة واحدة من القائمة');self.task_preview_meta.configure(text='ستظهر تفاصيلها ومرفقاتها هنا.');self.task_preview_attachments.configure(text='');self.task_preview_task_id=None
   for child in getattr(self, 'task_preview_attachments_frame', tk.Frame()).winfo_children():child.destroy()
   for child in getattr(self, 'task_preview_subtasks_frame', tk.Frame()).winfo_children():child.destroy()
   return
  with connect() as c:
   try: row=c.execute('SELECT * FROM tasks WHERE id=?',(ids[0],)).fetchone()
   except sqlite3.Error: return
  if not row:return
  self.task_preview_task_id=row['id'];self.task_preview_title.configure(text=row['title']);due=self._task_date_text(row['due_date'])+(' · '+(' – '.join(x for x in (row['start_time'],row['end_time']) if x) if row['start_time'] or row['end_time'] else ''));priority_text={1:'عاجلة',2:'عادية',3:'منخفضة'}.get(row['priority'],'عادية');state_text='مكتملة' if row['completed_at'] else 'مفتوحة'
  try: rec_text = f" · دورية: {row['recurrence']}" if row['recurrence'] and row['recurrence']!='لا يوجد' else ""
  except Exception: rec_text = ""
  self.task_preview_meta.configure(text=f"المشروع: {row['project']}\nالموعد: {due}\nالأولوية: {priority_text} · {state_text}{rec_text}")
  for child in self.task_preview_subtasks_frame.winfo_children():child.destroy()
  try: subtasks = json.loads(row['subtasks']) if row['subtasks'] else []
  except Exception: subtasks = []
  completed_subs = sum(1 for s in subtasks if s.get('done'))
  tk.Label(self.task_preview_subtasks_frame, text=f'قائمة خطوات التنفيذ ({completed_subs}/{len(subtasks)}):', bg='white', fg='#19394e', font=('Segoe UI', 9, 'bold')).pack(anchor='e', pady=(0,4))
  for i, sub in enumerate(subtasks):
   f = tk.Frame(self.task_preview_subtasks_frame, bg='white')
   f.pack(fill='x', pady=2)
   var = tk.BooleanVar(value=sub.get('done', False))
   cb = tk.Checkbutton(f, text=sub.get('title', ''), variable=var, bg='white', activebackground='white', command=lambda idx=i, v=var: self._task_toggle_subtask(row['id'], idx, v))
   cb.pack(side='right', fill='x', expand=True, anchor='e')
   ttk.Button(f, text='×', width=2, command=lambda idx=i: self._task_delete_subtask(row['id'], idx)).pack(side='left', padx=1)
   ttk.Button(f, text='✎', width=2, command=lambda idx=i: self._task_edit_subtask(row['id'], idx)).pack(side='left', padx=1)
  add_f = tk.Frame(self.task_preview_subtasks_frame, bg='white')
  add_f.pack(fill='x', pady=6)
  new_sub_var = tk.StringVar()
  sub_entry = ttk.Entry(add_f, textvariable=new_sub_var, justify='right')
  sub_entry.pack(side='right', fill='x', expand=True, padx=2)
  sub_entry.bind('<Return>', lambda e, t=row['id'], v=new_sub_var: self._task_add_subtask(t, v, e.widget))
  ttk.Button(add_f, text='＋ خطوة', width=7, command=lambda t=row['id'], v=new_sub_var: self._task_add_subtask(t, v, sub_entry)).pack(side='left', padx=2)
  try: attachments=self._task_attachment_values(row)
  except Exception: attachments = []
  self.task_preview_attachments.configure(text=('المرفقات والروابط: '+str(len(attachments)) if attachments else 'لا توجد مرفقات'))
  if hasattr(self, 'task_preview_attachments_frame'):
   for child in self.task_preview_attachments_frame.winfo_children():child.destroy()
   for item in attachments:
    line=tk.Frame(self.task_preview_attachments_frame,bg='white');line.pack(fill='x',pady=1)
    ttk.Button(line,text='×',width=3,command=lambda i=item:self._task_remove_attachment(row['id'],i)).pack(side='left', padx=1)
    ttk.Button(line,text='👁',width=3,command=lambda i=item:self._task_open_attachment(i)).pack(side='left', padx=1)
    btn_text = item.get('name', Path(item['path']).name)
    tk.Label(line,text=btn_text, bg='white', fg='#3478e5', font=('Segoe UI', 8), anchor='e').pack(side='right',fill='x',expand=True)

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
  dialog=tk.Toplevel(self);dialog.title('تعديل المهمة' if row else 'إضافة مهمة من التقويم');dialog.configure(bg='#eef3f7');dialog.transient(self);dialog.grab_set();dialog.resizable(False,False);card=tk.Frame(dialog,bg='white',highlightbackground='#d6e0e6',highlightthickness=1);card.pack(fill='both',expand=True,padx=14,pady=14);card.grid_columnconfigure(1,weight=1)
  tk.Label(card,text='تعديل المهمة' if row else 'إضافة مهمة من التقويم',bg='white',fg='#19394e',font=('Segoe UI',14,'bold')).grid(row=0,column=0,columnspan=3,sticky='e',padx=14,pady=(14,8))
  project_locked=bool(project_locked or project is not None)
  title=tk.StringVar(value=title_val); due=tk.StringVar(value=due_val)
  start=tk.StringVar(value=start_val); end=tk.StringVar(value=end_val)
  priority=tk.StringVar(value=pri_val); tags=tk.StringVar(value=tags_val)
  project_var=tk.StringVar(value=proj_val or ('اختر مشروعًا…' if not row else ''))
  recurrence = tk.StringVar(value=rec_val)
  def label(text,r):tk.Label(card,text=text,bg='white',fg='#607786',font=('Segoe UI',9)).grid(row=r,column=2,sticky='e',padx=12,pady=(5,2))
  label('عنوان المهمة',1);name=ttk.Entry(card,textvariable=title,width=42,justify='right');name.grid(row=2,column=0,columnspan=3,sticky='ew',padx=12,pady=(0,4))
  label('التاريخ',3);datebox=ttk.Entry(card,textvariable=due,width=15,justify='center');datebox.grid(row=4,column=1,padx=5,pady=(0,4),sticky='e');ttk.Button(card,text='🗓 اختر التاريخ',command=lambda:self._task_pick_date(due,initial_date,parent=dialog)).grid(row=4,column=0,padx=5,pady=(0,4),sticky='w');ttk.Button(card,text='بدون موعد',command=lambda:due.set('')).grid(row=4,column=2,padx=12,pady=(0,4),sticky='e')
  label('الوقت (اختياري)',5);timebox=tk.Frame(card,bg='white');timebox.grid(row=6,column=0,columnspan=3,sticky='ew',padx=12,pady=(0,4));self._task_time_control(timebox,start,'من');self._task_time_control(timebox,end,'إلى')
  label('الأولوية',7);ttk.Combobox(card,textvariable=priority,values=('عاجلة','عادية','منخفضة'),state='readonly',justify='right',style='Office.TCombobox').grid(row=8,column=1,columnspan=2,sticky='ew',padx=12,pady=(0,4))
  label('التكرار',7);ttk.Combobox(card,textvariable=recurrence,values=('لا يوجد','يومياً','أسبوعياً','شهرياً'),state='readonly',width=10,justify='right',style='Office.TCombobox').grid(row=8,column=0,sticky='ew',padx=12,pady=(0,4))
  label('تابعة لأي مشروع؟',9);projects=self._task_project_names();project_values=([proj_val] if project_locked and proj_val else [])+projects;project_values=list(dict.fromkeys(project_values));project_combo=ttk.Combobox(card,textvariable=project_var,values=project_values,state='disabled' if project_locked else 'readonly',justify='right',style='Office.TCombobox');project_combo.grid(row=10,column=0,columnspan=3,sticky='ew',padx=12,pady=(0,4))
  label('هاشتاجات المهمة',11);ttk.Entry(card,textvariable=tags,justify='right').grid(row=12,column=0,columnspan=3,sticky='ew',padx=12,pady=(0,5))
  attachment_row=tk.Frame(card,bg='white');attachment_row.grid(row=13,column=0,columnspan=3,sticky='ew',padx=12,pady=4)
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
     pending_files.append({'name': '🔗 ' + Path(chosen).name, 'path': rel_path, 'is_link': True})
     render_attach_list()
    except ValueError: messagebox.showwarning('مسار خاطئ', 'يجب اختيار ملف من داخل مجلد المشروع المختار.', parent=dialog)
  ttk.Button(attachment_row,text='＋ إضافة ملف',command=choose_files).pack(side='right', padx=2)
  ttk.Button(attachment_row,text='🔗 ربط بملف هندسي',command=link_file).pack(side='right',padx=4)
  attach_list_frame = tk.Frame(card, bg='white')
  attach_list_frame.grid(row=14, column=0, columnspan=3, sticky='ew', padx=12, pady=2)
  def render_attach_list():
   for child in attach_list_frame.winfo_children(): child.destroy()
   for item in existing_attachments:
    f = tk.Frame(attach_list_frame, bg='#f0f3f5'); f.pack(fill='x', pady=1)
    tk.Label(f, text=item.get('name', Path(item['path']).name), bg='#f0f3f5', fg='#19394e', font=('Segoe UI', 8)).pack(side='right', padx=4)
    ttk.Button(f, text='×', width=2, command=lambda i=item: remove_existing(i)).pack(side='left')
   for p in pending_files:
    f = tk.Frame(attach_list_frame, bg='#e9f2fb'); f.pack(fill='x', pady=1)
    name = p.get('name') if isinstance(p, dict) else Path(p).name
    tk.Label(f, text=name + ' (جديد)', bg='#e9f2fb', fg='#244e70', font=('Segoe UI', 8)).pack(side='right', padx=4)
    ttk.Button(f, text='×', width=2, command=lambda p_=p: remove_pending(p_)).pack(side='left')
  def remove_existing(item):
   existing_attachments.remove(item); files_to_remove.append(item); render_attach_list()
  def remove_pending(p):
   pending_files.remove(p); render_attach_list()
  render_attach_list()
  actions=tk.Frame(card,bg='white');actions.grid(row=15,column=0,columnspan=3,sticky='ew',padx=10,pady=(14,12))
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
  ttk.Button(actions,text='حفظ المهمة',command=save).pack(side='right',padx=3);ttk.Button(actions,text='إلغاء',command=dialog.destroy).pack(side='left',padx=3);dialog.bind('<Control-Return>',lambda e:(save(),'break'))
  dialog.update_idletasks()
  bx = self.winfo_rootx() + (self.winfo_width() - 580) // 2
  by = self.winfo_rooty() + (self.winfo_height() - 640) // 2
  dialog.geometry(f'580x{max(640, dialog.winfo_reqheight())}+{max(0,bx)}+{max(0,by)}')
  name.focus_set()