# tasks_list.py - واجهة قائمة المهام بالدوائر الملونة وإلغاء التحديد وضبط العربية ومنع نط السكرول
from common import *
from storage import *
from tasks_actions import TasksActionsMixin
from tasks_details import TasksDetailsMixin

class TasksListMixin(TasksActionsMixin, TasksDetailsMixin):
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
  self.clear();self.configure(bg=BG_VOID);self.title('Rasd // Smart Tasks Matrix')
  head=self.header('قائمة المهام الذكية');back=self.build_explorer if self._tasks_return_to_project else self.show_home
  ttk.Button(head,text=RLM+('← العودة للمشروع' if self._tasks_return_to_project else '← المشاريع'),command=back).pack(side='right',padx=5,pady=12)
  if self.task_scope:ttk.Button(head,text=RLM+'كل مهام المشاريع',command=self.show_tasks).pack(side='right',padx=5,pady=12)
  ttk.Button(head,text=RLM+'▦ التقويم',command=lambda:self.show_task_calendar(self.task_scope or None)).pack(side='right',padx=5,pady=12)
  body=tk.Frame(self,bg=BG_VOID);body.pack(fill='both',expand=True,padx=22,pady=(12,18));body.grid_columnconfigure(0,weight=1);body.grid_rowconfigure(3,weight=1)
  title=RLM+('مهام المشروع: '+self.task_scope if self.task_scope else 'كل المهام في مكان واحد')
  tk.Label(body,text=title,bg=BG_VOID,fg=ACCENT_MATRIX,font=(TERM_FONT,14,'bold'),anchor='e').grid(row=0,column=0,sticky='ew')
  tk.Label(body,text=RLM+'قائمة واحدة مترابطة: مهام كل مشروع وتقويمه والمرفقات المحفوظة داخل Log.',bg=BG_VOID,fg=FG_MUTED,font=(TERM_FONT,9),anchor='e').grid(row=1,column=0,sticky='ew',pady=(2,10))
  toolbar=tk.Frame(body,bg=BG_VOID);toolbar.grid(row=2,column=0,sticky='ew',pady=(0,8));self.task_filter_buttons={};self.task_filter_count_vars={}
  filters=(('كل المهام','open'),('اليوم','today'),('غدًا','tomorrow'),('القادمة','upcoming'),('المتأخرة','overdue'),('بدون موعد','inbox'),('المكتملة','completed'),('تخصيص الفترة','custom'))
  for label,key in filters:
   count=tk.StringVar(value='0');self.task_filter_count_vars[key]=count;active=key==self.task_filter;b=tk.Button(toolbar,text=RLM+f'{label} ({count.get()})',command=(self._task_custom_filter if key=='custom' else lambda value=key:self._task_set_filter(value)),bg=BG_SELECTED if active else BG_PANEL,fg=ACCENT_MATRIX if active else FG_MUTED,activebackground=BG_HOVER,relief='solid',borderwidth=1,font=(TERM_FONT,8,'bold' if active else 'normal'),padx=8,pady=6,cursor='hand2');b.pack(side='right',padx=(0,4));self.task_filter_buttons[key]=b
   count.trace_add('write',lambda *_args,k=key,text=label:self.task_filter_buttons[k].configure(text=RLM+f'{text} ({self.task_filter_count_vars[k].get()})'))
  self.task_search_var=tk.StringVar();search=ttk.Entry(toolbar,textvariable=self.task_search_var,width=20,justify='right');search.pack(side='left',fill='x',expand=True,padx=3);search.insert(0,'ابحث في المهام');search.bind('<FocusIn>',lambda e:search.delete(0,'end') if search.get()=='ابحث في المهام' else None);self.task_search_var.trace_add('write',lambda *_:self._task_set_search(self.task_search_var.get()))
  content=tk.Frame(body,bg=BG_VOID);content.grid(row=3,column=0,sticky='nsew');content.grid_columnconfigure(0,weight=0,minsize=310);content.grid_columnconfigure(1,weight=1);content.grid_rowconfigure(0,weight=1)
  self.task_preview_panel=tk.Frame(content,bg=BG_PANEL,highlightbackground=BORDER_DIM,highlightthickness=1,width=310);self.task_preview_panel.grid(row=0,column=0,sticky='nsew',padx=(0,8));self.task_preview_panel.grid_propagate(False);self._task_build_preview_panel(self.task_preview_panel)
  workarea=tk.Frame(content,bg=BG_VOID);workarea.grid(row=0,column=1,sticky='nsew');workarea.grid_columnconfigure(0,weight=1);workarea.grid_rowconfigure(2,weight=1)
  capture=tk.Frame(workarea,bg=BG_PANEL,highlightbackground=BORDER_DIM,highlightthickness=1);capture.grid(row=0,column=0,sticky='ew',pady=(0,8));capture.grid_columnconfigure(0,weight=1)
  self.task_quick_var=tk.StringVar();self.task_quick_entry=tk.Entry(capture,textvariable=self.task_quick_var,bg=BG_VOID,fg=ACCENT_MATRIX,insertbackground=ACCENT_MATRIX,relief='solid',borderwidth=1,font=(TERM_FONT,10),justify='right');self.task_quick_entry.grid(row=0,column=0,sticky='ew',padx=(12,4),pady=(8,4),ipady=6);self.task_quick_entry.insert(0,'اكتب مهمة سريعة')
  self.task_quick_entry.bind('<FocusIn>',lambda e:self.task_quick_entry.delete(0,'end') if self.task_quick_entry.get() in ('اكتب مهمة سريعة','لا توجد مشاريع — أنشئ مشروعًا أولًا') else None);self.task_quick_entry.bind('<Return>',lambda e:(self._task_add_quick(),'break'))
  self.task_quick_add_button=tk.Button(capture,text=RLM+'＋ إضافة مهمة',command=self._task_add_quick,bg=BG_HEADER,fg=ACCENT_MATRIX,activebackground=ACCENT_MATRIX,activeforeground=BG_VOID,relief='solid',borderwidth=1,font=(TERM_FONT,9,'bold'),padx=13,pady=5,cursor='hand2');self.task_quick_add_button.grid(row=0,column=1,padx=(3,10),pady=(8,4))
  opts=tk.Frame(capture,bg=BG_PANEL);opts.grid(row=1,column=0,columnspan=2,sticky='ew',padx=9,pady=(1,8))
  tk.Label(opts,text=RLM+'الموعد:',bg=BG_PANEL,fg=FG_MUTED,font=(TERM_FONT,8)).pack(side='right',padx=(6,2));self.task_due_var=tk.StringVar();self.task_due_entry=ttk.Entry(opts,textvariable=self.task_due_var,width=12,justify='center');self.task_due_entry.pack(side='right',padx=3);ttk.Button(opts,text=RLM+'🗓 التاريخ',command=lambda:self._task_pick_date(self.task_due_var,parent=self)).pack(side='right',padx=(0,4))
  tk.Label(opts,text=RLM+'الوقت:',bg=BG_PANEL,fg=FG_MUTED,font=(TERM_FONT,8)).pack(side='right',padx=(6,2));self.task_start_var=tk.StringVar();self.task_end_var=tk.StringVar();self._task_time_control(opts,self.task_start_var,'من');self._task_time_control(opts,self.task_end_var,'إلى')
  tk.Label(opts,text=RLM+'الأولوية:',bg=BG_PANEL,fg=FG_MUTED,font=(TERM_FONT,8)).pack(side='right',padx=(7,2));self.task_priority_var=tk.StringVar(value='عادية');ttk.Combobox(opts,textvariable=self.task_priority_var,values=('عاجلة','عادية','منخفضة'),state='readonly',width=9,justify='right',style='Office.TCombobox').pack(side='right',padx=3)
  tk.Label(opts,text=RLM+'المشروع:',bg=BG_PANEL,fg=FG_MUTED,font=(TERM_FONT,8)).pack(side='right',padx=(7,2));project_names=self._task_project_names();project_choices=[self.task_scope] if self.task_scope else project_names;default_project=self.task_scope or (project_names[0] if len(project_names)==1 else 'اختر مشروعًا…');self.task_project_var=tk.StringVar(value=default_project);self.task_project_combo=ttk.Combobox(opts,textvariable=self.task_project_var,values=project_choices,state='disabled' if self.task_scope or not project_names else 'readonly',width=19,justify='right',style='Office.TCombobox');self.task_project_combo.pack(side='right',padx=3)
  ttk.Button(opts,text=RLM+'غير محددة',command=lambda:self.task_due_var.set('')).pack(side='right',padx=3);ttk.Button(opts,text=RLM+'اليوم',command=lambda:self.task_due_var.set(date.today().isoformat())).pack(side='right',padx=3);ttk.Button(opts,text=RLM+'غدًا',command=lambda:self.task_due_var.set((date.today()+timedelta(days=1)).isoformat())).pack(side='right',padx=3)
  tagrow=tk.Frame(capture,bg=BG_PANEL);tagrow.grid(row=2,column=0,columnspan=2,sticky='ew',padx=10,pady=(0,8));tk.Label(tagrow,text=RLM+'هاشتاجات:',bg=BG_PANEL,fg=FG_MUTED,font=(TERM_FONT,8)).pack(side='right',padx=(5,3));self.task_quick_tags_var=tk.StringVar();ttk.Entry(tagrow,textvariable=self.task_quick_tags_var,justify='right').pack(side='right',fill='x',expand=True,padx=3);tk.Label(tagrow,text=RLM+'مثال: #مراجعة #موقع',bg=BG_PANEL,fg=FG_MUTED,font=(TERM_FONT,8)).pack(side='right',padx=5)
  self.task_quick_entry.configure(state='normal')
  if not project_choices:
   self.task_quick_entry.delete(0,'end');self.task_quick_entry.insert(0,'لا توجد مشاريع — أنشئ مشروعًا أولًا');self.task_quick_entry.configure(fg=FG_MUTED)
   hint=tk.Frame(capture,bg=BG_HEADER,highlightbackground=ACCENT_AMBER,highlightthickness=1)
   hint.grid(row=3,column=0,columnspan=2,sticky='ew',padx=10,pady=(0,8))
   opts.grid_remove();tagrow.grid_remove()
   tk.Label(hint,text=RLM+'لا توجد مشاريع بعد. أنشئ مشروعًا أولًا عشان تقدر تضيف مهام وتتابعها.',bg=BG_HEADER,fg=FG_PRIMARY,font=(TERM_FONT,9),anchor='e').pack(side='right',fill='x',expand=True,padx=8,pady=6)
   tk.Button(hint,text=RLM+'＋ مشروع جديد',command=self.new_project,bg=BG_SELECTED,fg=ACCENT_MATRIX,activebackground=ACCENT_MATRIX,activeforeground=BG_VOID,relief='solid',borderwidth=1,font=(TERM_FONT,9,'bold'),padx=12,pady=3,cursor='hand2').pack(side='left',padx=8)
  self.task_time_window=tk.Frame(workarea,bg=BG_HEADER,highlightbackground=BORDER_DIM,highlightthickness=1);self.task_time_window.grid(row=1,column=0,sticky='ew',pady=(0,8));self.task_time_window.grid_remove()
  tk.Label(self.task_time_window,text=RLM+'عرض مهام اليوم خلال الفترة:',bg=BG_HEADER,fg=ACCENT_CYAN,font=(TERM_FONT,8)).pack(side='right',padx=8);self.task_window_start=tk.StringVar(value='');self.task_window_end=tk.StringVar(value='');self._task_time_control(self.task_time_window,self.task_window_start,'من');self._task_time_control(self.task_time_window,self.task_window_end,'إلى');ttk.Button(self.task_time_window,text=RLM+'تطبيق',command=self._task_refresh_rows).pack(side='right',padx=5,pady=3)
  
  list_card=tk.Frame(workarea,bg=BG_PANEL,highlightbackground=BORDER_DIM,highlightthickness=1);list_card.grid(row=2,column=0,sticky='nsew');list_card.grid_rowconfigure(0,weight=1);list_card.grid_columnconfigure(0,weight=1)
  cols=('title','due','priority','project','tags')
  self.task_tree=ttk.Treeview(list_card,columns=cols,displaycolumns=('tags','project','priority','due','title'),show='headings',selectmode='extended')
  for col,label,width,anchor in (('title',RLM+'المهمة',350,'e'),('due',RLM+'الموعد',160,'center'),('priority',RLM+'الأولوية',95,'center'),('project',RLM+'المشروع',145,'e'),('tags',RLM+'التصنيفات',160,'e')):
   self.task_tree.heading(col,text=label);self.task_tree.column(col,width=width,minwidth=65,anchor=anchor,stretch=col=='title')
  
  # شريط الدوائر الملونة بجانب اسم المهمة (أحمر للعاجلة، أزرق للعادية، أصفر للمنخفضة)
  self.task_dots_canvas = tk.Canvas(list_card, width=28, bg=BG_PANEL, highlightthickness=0)
  self.task_dots_canvas._no_global_scroll = True
  self.task_tree.grid(row=0,column=0,sticky='nsew',padx=(5,0),pady=5)
  self.task_dots_canvas.grid(row=0,column=1,sticky='ns',pady=5)
  scroll=ttk.Scrollbar(list_card,orient='vertical',command=self._on_task_tree_vscroll);scroll.grid(row=0,column=2,sticky='ns',pady=5)
  self.task_tree.configure(yscrollcommand=lambda f,l:(scroll.set(f,l),self._schedule_task_dots_redraw()))
  self.task_empty_hint=tk.Label(list_card,text='',bg=BG_PANEL,fg=FG_MUTED,font=(TERM_FONT,10),justify='center',wraplength=420)
  self.task_empty_hint.place(relx=0.5,rely=0.5,anchor='center');self.task_empty_hint.lower()
  
  # إزالة تلوين الخلفية بالكامل والاكتفاء بخلفية التيرمينال الداكنة الموحدة
  self.task_tree.tag_configure('urgent',background=BG_PANEL,foreground=FG_PRIMARY)
  self.task_tree.tag_configure('normal',background=BG_PANEL,foreground=FG_PRIMARY)
  self.task_tree.tag_configure('low',background=BG_PANEL,foreground=FG_PRIMARY)
  self.task_tree.tag_configure('overdue',background=BG_PANEL,foreground=FG_PRIMARY)
  self.task_tree.tag_configure('today',background=BG_PANEL,foreground=FG_PRIMARY)
  self.task_tree.tag_configure('done',background=BG_ALT_ROW,foreground=FG_MUTED)
  self.task_tree.tag_configure('day_group',background=BG_HEADER,foreground=ACCENT_CYAN)
  
  self.task_tree.bind('<ButtonPress-1>', self._on_task_tree_click)
  self.task_tree.bind('<Double-1>',lambda e:self._task_open_selected_document())
  self.task_tree.bind('<<TreeviewSelect>>',lambda e:(self._task_preview_selected(),self._schedule_task_dots_redraw()))
  self.task_tree.bind('<Configure>',lambda e:self._schedule_task_dots_redraw(),add='+')
  self.task_dots_canvas.bind('<ButtonPress-1>', self._on_task_dots_click)
  self.task_dots_canvas.bind('<MouseWheel>', lambda e: (self.task_tree.yview_scroll(int(-e.delta/120), 'units'), self._schedule_task_dots_redraw(), 'break')[2])

  footer=tk.Frame(workarea,bg=BG_VOID);footer.grid(row=3,column=0,sticky='ew',pady=(7,0));ttk.Button(footer,text=RLM+'✓ إكمال',command=self._task_toggle_done).pack(side='right',padx=3);ttk.Button(footer,text=RLM+'✎ تعديل المهمة',command=self._task_edit_selected).pack(side='right',padx=3);self.task_postpone_button=ttk.Button(footer,text=RLM+'↷ تأجيل للغد',command=self._task_postpone);self.task_postpone_button.pack(side='right',padx=3);ttk.Button(footer,text=RLM+'× حذف المهام وملفاتها',command=self._task_delete_selected).pack(side='right',padx=3)
  ttk.Button(footer,text=RLM+'🖨 طباعة وتصدير PDF',command=self._task_export_print).pack(side='right',padx=3)
  self.task_page_size=400;self.task_page=0;self.task_page_var=tk.StringVar(value='');ttk.Button(footer,text=RLM+'التالي ›',command=lambda:self._task_page_shift(1)).pack(side='left',padx=2);tk.Label(footer,textvariable=self.task_page_var,bg=BG_VOID,fg=ACCENT_CYAN,font=(TERM_FONT,8)).pack(side='left',padx=4);ttk.Button(footer,text=RLM+'‹ السابق',command=lambda:self._task_page_shift(-1)).pack(side='left',padx=2);self.task_result_var=tk.StringVar(value='');tk.Label(footer,textvariable=self.task_result_var,bg=BG_VOID,fg=ACCENT_MATRIX,font=(TERM_FONT,8,'bold'),anchor='e').pack(side='left',fill='x',expand=True,padx=8)
  self._task_update_context_controls();self._task_refresh_rows();self.task_quick_entry.focus_set()
  self.after(30000,lambda token=rollover_token:self._task_rollover_tick(token))

 def _on_task_tree_vscroll(self, *args):
  self.task_tree.yview(*args)
  self._schedule_task_dots_redraw()

 def _on_task_tree_click(self, event):
  region = self.task_tree.identify_region(event.x, event.y)
  if region in ('heading', 'separator'):
   return
  row = self.task_tree.identify_row(event.y)
  if not row:
   self.task_tree.selection_remove(self.task_tree.selection())
   self._task_preview_selected()
   self._schedule_task_dots_redraw()
   return 'break'

 def _on_task_dots_click(self, event):
  row = self.task_tree.identify_row(event.y)
  if not row:
   self.task_tree.selection_remove(self.task_tree.selection())
  else:
   self.task_tree.selection_set(row)
   self.task_tree.focus(row)
  self._task_preview_selected()
  self._schedule_task_dots_redraw()
  return 'break'

 def _schedule_task_dots_redraw(self):
  job = getattr(self, '_task_dots_job', None)
  if job:
   try: self.after_cancel(job)
   except tk.TclError: pass
  self._task_dots_job = self.after(12, self._draw_task_priority_dots)

 def _draw_task_priority_dots(self):
  cv = getattr(self, 'task_dots_canvas', None)
  tree = getattr(self, 'task_tree', None)
  if not cv or not cv.winfo_exists() or not tree or not tree.winfo_exists():
   return
  cv.delete('all')
  w = max(24, cv.winfo_width())
  cv.create_rectangle(0, 0, w, 32, fill=BG_HEADER, outline='')
  selected = set(tree.selection())
  pri_map = getattr(self, '_task_row_priority_map', {})
  for iid in tree.get_children(''):
   bbox = tree.bbox(iid, column='title')
   if not bbox:
    continue
   _, y, _, h = bbox
   if y + h < 30:
    continue
   if iid in selected:
    cv.create_rectangle(0, y, w, y + h, fill=BG_SELECTED, outline='')
   info = pri_map.get(str(iid))
   if not info:
    continue
   pri, done = info
   color = FG_MUTED if done else {1: PRI_URGENT, 2: PRI_NORMAL, 3: PRI_LOW}.get(pri, PRI_NORMAL)
   cy = y + h // 2
   cx = w // 2
   r = 5
   cv.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color, outline='#070A0E', width=1)

 def _task_time_control(self,parent,var,label):
  box=tk.Frame(parent,bg=parent.cget('bg'));box.pack(side='right',padx=2);tk.Label(box,text=RLM+label,bg=parent.cget('bg'),fg=FG_MUTED,font=(TERM_FONT,8)).pack(side='right',padx=2)
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
    # لا نحرك أي Canvas إلا إذا كان خاصاً بالجدول الزمني للتقويم لمنع نط الأزرار والفلاتر
    if getattr(widget, '_no_global_scroll', False):
     return
    if not (hasattr(widget,'_sync_yscroll') or hasattr(widget,'_sync_xscroll')):
     return
    amount=int(-event.delta/120) or (-1 if event.delta>0 else 1)
    try:
     if event.state & 0x0001:
      if hasattr(widget,'_sync_xscroll'):widget._sync_xscroll(amount)
     else:
      if hasattr(widget,'_sync_yscroll'):widget._sync_yscroll(amount)
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
  top=tk.Toplevel(host);self.task_date_picker=top;top.title('اختيار التاريخ');top.configure(bg=BG_VOID);top.transient(host);top.resizable(False,False)
  header=tk.Frame(top,bg=BG_HEADER,height=42);header.pack(fill='x');header.pack_propagate(False)
  caption=tk.StringVar()
  tk.Button(header,text='‹',command=lambda:shift(-1),bg=BG_HEADER,fg=ACCENT_MATRIX,activebackground=BG_SELECTED,activeforeground=ACCENT_MATRIX,relief='flat',font=(TERM_FONT,12,'bold'),padx=10,cursor='hand2').pack(side='left',padx=6,pady=4)
  tk.Button(header,text='›',command=lambda:shift(1),bg=BG_HEADER,fg=ACCENT_MATRIX,activebackground=BG_SELECTED,activeforeground=ACCENT_MATRIX,relief='flat',font=(TERM_FONT,12,'bold'),padx=10,cursor='hand2').pack(side='right',padx=6,pady=4)
  tk.Label(header,textvariable=caption,bg=BG_HEADER,fg=ACCENT_CYAN,font=(TERM_FONT,10,'bold')).pack(side='top',pady=8)
  grid=tk.Frame(top,bg=BG_PANEL,highlightbackground=BORDER_DIM,highlightthickness=1);grid.pack(fill='both',expand=True,padx=10,pady=8)
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
   month=state['month'];caption.set(RLM+self._task_arabic_date(month,'month'))
   for c,name in enumerate(('إث','ثلا','أر','خمي','جمع','سبت','أحد')):tk.Label(grid,text=RLM+name,bg=BG_PANEL,fg=FG_MUTED,width=5,font=(TERM_FONT,8,'bold')).grid(row=0,column=c,pady=3)
   first=month;offset=first.weekday();days=(date(first.year+int(first.month==12),1 if first.month==12 else first.month+1,1)-first).days
   for daynum in range(1,days+1):
    idx=offset+daynum-1;r=1+idx//7;c=idx%7;d=first.replace(day=daynum);bg=ACCENT_MATRIX if d==state['chosen'] else (BG_SELECTED if d==date.today() else BG_PANEL);fg=BG_VOID if d==state['chosen'] else (ACCENT_MATRIX if d==date.today() else FG_PRIMARY)
    b=tk.Button(grid,text=str(daynum),width=4,bg=bg,fg=fg,activebackground=ACCENT_MATRIX,activeforeground=BG_VOID,relief='flat',font=(TERM_FONT,9,'bold' if d in (state['chosen'],date.today()) else 'normal'),cursor='hand2',command=lambda target=d:choose(target.isoformat()))
    b.grid(row=r,column=c,padx=1,pady=1)
   ttk.Button(grid,text=RLM+'بدون موعد',command=lambda:choose('')).grid(row=7,column=0,columnspan=3,sticky='ew',pady=(8,4),padx=4)
   ttk.Button(grid,text=RLM+'اليوم',command=lambda:choose(date.today().isoformat())).grid(row=7,column=4,columnspan=3,sticky='ew',pady=(8,4),padx=4)
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
  dialog=tk.Toplevel(self);dialog.title('تخصيص فترة المهام');dialog.configure(bg=BG_VOID);dialog.transient(self);dialog.grab_set();card=tk.Frame(dialog,bg=BG_PANEL,highlightbackground=BORDER_DIM,highlightthickness=1);card.pack(fill='both',expand=True,padx=14,pady=14);start=tk.StringVar(value=getattr(self,'task_range_start',date.today().isoformat()));end=tk.StringVar(value=getattr(self,'task_range_end',date.today().isoformat()));status_labels={'open':'غير المكتملة','completed':'المكتملة','all':'الكل'};status=tk.StringVar(value=status_labels.get(getattr(self,'task_range_status','open'),'غير المكتملة'))
  for row,(label,var) in enumerate((('من تاريخ',start),('إلى تاريخ',end))):
   tk.Label(card,text=RLM+label,bg=BG_PANEL,fg=FG_PRIMARY,font=(TERM_FONT,9)).grid(row=row,column=2,padx=6,pady=7);ttk.Entry(card,textvariable=var,width=14,justify='center').grid(row=row,column=1,padx=4);ttk.Button(card,text='▦',command=lambda v=var:self._task_pick_date(v,parent=dialog)).grid(row=row,column=0,padx=4)
  def apply():
   try:a=self._task_parse_date(start.get());b=self._task_parse_date(end.get());assert a and b and a<=b
   except Exception:return messagebox.showwarning('الفترة','اختر نطاقًا صحيحًا للتواريخ.',parent=dialog)
   self.task_range_start=a;self.task_range_end=b;self.task_range_status=next((key for key,label in status_labels.items() if label==status.get()),'open');dialog.destroy();self._task_set_filter('custom')
  tk.Label(card,text=RLM+'حالة المهام',bg=BG_PANEL,fg=FG_PRIMARY,font=(TERM_FONT,9)).grid(row=2,column=2,padx=6,pady=7);ttk.Combobox(card,textvariable=status,values=tuple(status_labels.values()),state='readonly',justify='right',style='Office.TCombobox').grid(row=2,column=0,columnspan=2,sticky='ew',padx=4)
  ttk.Button(card,text=RLM+'عرض الفترة',command=apply).grid(row=3,column=0,columnspan=3,pady=10);dialog.update_idletasks();dialog.geometry(f'+{self.winfo_rootx()+100}+{self.winfo_rooty()+100}')

 def _task_set_filter(self,key):
  self.task_filter=key;self.task_page=0
  try:
   with connect() as c:c.execute("INSERT INTO app_settings(key,value) VALUES('tasks_last_filter',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(key,))
  except sqlite3.Error:pass
  for value,button in self.task_filter_buttons.items():
   active=value==key;button.configure(bg=BG_SELECTED if active else BG_PANEL,fg=ACCENT_MATRIX if active else FG_MUTED,font=(TERM_FONT,8,'bold' if active else 'normal'))
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
   self.task_result_var.set(RLM+'تعذر تحميل المهام: '+str(exc)[:100]);return
  selected_before=self.task_tree.selection()
  for iid in self.task_tree.get_children():self.task_tree.delete(iid)
  self._task_row_priority_map = {}
  grouped=key=='upcoming';last_day=None
  for row in rows:
   due=row['due_date'] or '';done=bool(row['completed_at']);priority=int(row['priority']);tags=[x for x in (row['tags'] or '').split(',') if x]
   try: rec_icon = ' ↻' if row['recurrence'] and row['recurrence'] != 'لا يوجد' else ''
   except Exception: rec_icon = ''
   if grouped and due!=last_day:
    try:day=datetime.strptime(due,'%Y-%m-%d').date();label=day.strftime('%A %d-%m-%Y')
    except ValueError:label=due
    self.task_tree.insert('','end',iid='day:'+due,values=(RLM+'▾  '+label,'','','',''),tags=('day_group',));last_day=due
   time_label=' – '.join(x for x in (row['start_time'],row['end_time']) if x);due_label=RLM+self._task_date_text(due)+((' · '+time_label) if time_label else '')
   tag='done' if done else 'normal'
   pri_label=RLM+{1:'عاجلة',2:'عادية',3:'منخفضة'}.get(priority,'عادية')
   title_cell = RLM + (('✓  ' if done else '') + str(row['title']) + rec_icon)
   values=(title_cell, due_label, pri_label, RLM+str(row['project']), '  '.join('#'+x for x in tags))
   row_iid = str(row['id'])
   self._task_row_priority_map[row_iid] = (priority, done)
   self.task_tree.insert('','end',iid=row_iid,values=values,tags=(tag,))
  for iid in selected_before:
   if self.task_tree.exists(iid):self.task_tree.selection_add(iid)
  shown=len(rows);self.task_result_var.set(RLM+f'إجمالي المهام: {total:,}  ·  يعرض {offset+1 if total else 0}–{offset+shown:,} من {total:,}')
  self.task_page_var.set(RLM+f'صفحة {self.task_page+1:,} / {pages:,}')
  self._task_preview_selected()
  self._schedule_task_dots_redraw()
  self._task_update_empty_hint(total)

 def _task_update_empty_hint(self,total):
  hint=getattr(self,'task_empty_hint',None)
  if not hint or not hint.winfo_exists():return
  if total>0:
   hint.place_forget();return
  if self._task_project_names():text='لا توجد مهام مطابقة للفلتر الحالي.\nأضف مهمة من الأعلى أو غيّر الفلتر.'
  else:text='لا توجد مهام بعد.\nأنشئ مشروعًا أولًا ثم أضف مهمتك الأولى.'
  hint.configure(text=RLM+text);hint.place(relx=0.5,rely=0.5,anchor='center');hint.lift()

 def _task_page_shift(self,step):
  self.task_page=max(0,getattr(self,'task_page',0)+step);self._task_refresh_rows()
