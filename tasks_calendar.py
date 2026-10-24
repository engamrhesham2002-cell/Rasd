# Rasd - إدارة المهام والتقويم (محدث: محاذاة دقيقة 100% بين عمود الوقت ومربعات المهام)
from common import *
from storage import *

class TasksCalendarMixin:
 def show_tasks(self,project=None):
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
  footer=tk.Frame(workarea,bg='#eef3f7');footer.grid(row=3,column=0,sticky='ew',pady=(7,0));ttk.Button(footer,text='✓ إكمال',command=self._task_toggle_done).pack(side='right',padx=3);ttk.Button(footer,text='✎ بيانات المهمة',command=self._task_edit_selected).pack(side='right',padx=3);self.task_postpone_button=ttk.Button(footer,text='↷ تأجيل للغد',command=self._task_postpone);self.task_postpone_button.pack(side='right',padx=3);ttk.Button(footer,text='× حذف',command=self._task_delete_selected).pack(side='right',padx=3);self.task_page_size=400;self.task_page=0;self.task_page_var=tk.StringVar(value='');ttk.Button(footer,text='التالي ›',command=lambda:self._task_page_shift(1)).pack(side='left',padx=2);tk.Label(footer,textvariable=self.task_page_var,bg='#eef3f7',fg='#526b7b',font=('Segoe UI',8)).pack(side='left',padx=4);ttk.Button(footer,text='‹ السابق',command=lambda:self._task_page_shift(-1)).pack(side='left',padx=2);self.task_result_var=tk.StringVar(value='');tk.Label(footer,textvariable=self.task_result_var,bg='#eef3f7',fg='#718491',font=('Segoe UI',8),anchor='e').pack(side='left',fill='x',expand=True,padx=8)
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

 def _task_rollover_elapsed(self):
  """Only timed tasks roll forward when their end time has passed; date-only tasks remain overdue."""
  now=datetime.now();today=now.date().isoformat();clock=now.strftime('%H:%M');stamp=now.strftime('%Y-%m-%d %H:%M:%S')
  try:
   with connect() as c:
    cur=c.execute("UPDATE tasks SET due_date=?,updated_at=? WHERE completed_at IS NULL AND due_date=? AND end_time IS NOT NULL AND end_time<>'' AND end_time<=?",((now.date()+timedelta(days=1)).isoformat(),stamp,today,clock))
    return cur.rowcount>0
  except sqlite3.Error:return False

 def _task_rollover_tick(self,token=None):
  if token is not None and token!=getattr(self,'task_rollover_token',None):return
  if getattr(self,'task_calendar_active',False):
   if getattr(self,'task_calendar_drag_state',None) is None and self._task_rollover_elapsed():
    self._task_calendar_draw(preserve_scroll=True)
   self.after(30000,lambda:self._task_rollover_tick(token))
  elif getattr(self,'task_tree',None) and self.task_tree.winfo_exists():
   if self._task_rollover_elapsed():
    self._task_refresh_rows()
   self.after(30000,lambda:self._task_rollover_tick(token))

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
    try:rows=c.execute('SELECT t.id,t.title,t.due_date,t.start_time,t.end_time,t.priority,t.project,t.tags,t.completed_at,t.created_at FROM tasks t'+where+order+' LIMIT ? OFFSET ?',query_params+[page_size,offset]).fetchall()
    except sqlite3.OperationalError:
     if not search or not fts_query:raise
     query_where=query_where[:-1]+['(t.title LIKE ? OR t.description LIKE ? OR t.project LIKE ? OR t.tags LIKE ?)'];query_params=query_params[:-1]+['%'+search+'%']*4;where=' WHERE '+' AND '.join(query_where);total=int(c.execute('SELECT COUNT(*) FROM tasks t'+where,query_params).fetchone()[0]);pages=max(1,(total+page_size-1)//page_size);self.task_page=min(self.task_page,pages-1);offset=self.task_page*page_size;rows=c.execute('SELECT t.id,t.title,t.due_date,t.start_time,t.end_time,t.priority,t.project,t.tags,t.completed_at,t.created_at FROM tasks t'+where+order+' LIMIT ? OFFSET ?',query_params+[page_size,offset]).fetchall()
  except sqlite3.Error as exc:
   self.task_result_var.set('تعذر تحميل المهام: '+str(exc)[:100]);return
  selected_before=self.task_tree.selection()
  for iid in self.task_tree.get_children():self.task_tree.delete(iid)
  grouped=key=='upcoming';last_day=None
  for row in rows:
   due=row['due_date'] or '';done=bool(row['completed_at']);priority=int(row['priority']);tags=[x for x in (row['tags'] or '').split(',') if x]
   if grouped and due!=last_day:
    try:day=datetime.strptime(due,'%Y-%m-%d').date();label=day.strftime('%A %d-%m-%Y')
    except ValueError:label=due
    self.task_tree.insert('','end',iid='day:'+due,values=('▾  '+label,'','','',''),tags=('day_group',));last_day=due
   time_label=' – '.join(x for x in (row['start_time'],row['end_time']) if x);due_label=self._task_date_text(due)+((' · '+time_label) if time_label else '')
   tag='done' if done else ('overdue' if due and due<today else ('today' if due==today else ({1:'urgent',2:'normal',3:'low'}.get(priority,''))))
   values=(('✓  ' if done else '')+row['title'],due_label,{1:'عاجلة',2:'عادية',3:'منخفضة'}.get(priority,'عادية'),row['project'],'  '.join('#'+x for x in tags))
   self.task_tree.insert('','end',iid=str(row['id']),values=values,tags=(tag,) if tag else ())
  for iid in selected_before:
   if self.task_tree.exists(iid):self.task_tree.selection_add(iid)
  shown=len(rows);self.task_result_var.set(f'{total:,} مهمة في النتيجة · يعرض {offset+1 if total else 0}–{offset+shown:,} من {total:,} · انتهاء موعد المهمة المحددة بوقت ينقلها للغد')
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
  now=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
  with connect() as c:
   for task_id in ids:
    row=c.execute('SELECT completed_at FROM tasks WHERE id=?',(task_id,)).fetchone()
    if row:c.execute('UPDATE tasks SET completed_at=?,updated_at=? WHERE id=?',(None if row['completed_at'] else now,now,task_id))
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
  if not messagebox.askyesno('حذف المهام',f'حذف {len(ids)} مهمة؟ لا يمكن التراجع عن الحذف.',parent=self):return
  with connect() as c:c.executemany('DELETE FROM tasks WHERE id=?',[(x,) for x in ids])
  self._task_refresh_rows()

 def _task_edit_selected(self):
  ids=self._task_selected_ids()
  if len(ids)!=1:return messagebox.showinfo('المهام','حدد مهمة واحدة للتعديل.',parent=self)
  task_id=ids[0]
  with connect() as c:row=c.execute('SELECT * FROM tasks WHERE id=?',(task_id,)).fetchone()
  if not row:return self._task_refresh_rows()
  self._task_task_dialog(row=row,project_locked=bool(self.task_scope))

 def _task_build_preview_panel(self,panel):
  panel.grid_columnconfigure(0,weight=1);tk.Label(panel,text='معاينة المهمة',bg='#dfe7ec',fg='#19394e',font=('Segoe UI',12,'bold'),anchor='e',padx=12,pady=12).grid(row=0,column=0,sticky='ew')
  self.task_preview_title=tk.Label(panel,text='اختر مهمة من القائمة',bg='white',fg='#19394e',font=('Segoe UI',13,'bold'),anchor='e',justify='right',wraplength=275);self.task_preview_title.grid(row=1,column=0,sticky='ew',padx=12,pady=(16,8))
  self.task_preview_meta=tk.Label(panel,text='ستظهر تفاصيلها ومرفقاتها هنا.',bg='white',fg='#718491',font=('Segoe UI',9),anchor='e',justify='right',wraplength=275);self.task_preview_meta.grid(row=2,column=0,sticky='ew',padx=12,pady=(0,10))
  self.task_preview_text=tk.Text(panel,height=14,wrap='word',font=('Segoe UI',9),relief='flat',bg='#f7fafb',fg='#344c5b',state='disabled');self.task_preview_text.grid(row=3,column=0,sticky='nsew',padx=10,pady=4);panel.grid_rowconfigure(3,weight=1)
  self.task_preview_attachments=tk.Label(panel,text='',bg='white',fg='#607786',font=('Segoe UI',8),anchor='e',justify='right',wraplength=275);self.task_preview_attachments.grid(row=4,column=0,sticky='ew',padx=12,pady=7)
  self.task_preview_attachments_frame=tk.Frame(panel,bg='white');self.task_preview_attachments_frame.grid(row=5,column=0,sticky='ew',padx=8,pady=3)
  actions=tk.Frame(panel,bg='white');actions.grid(row=6,column=0,sticky='ew',padx=8,pady=(4,10));ttk.Button(actions,text='فتح ملف المهمة TXT',command=self._task_open_selected_document).pack(fill='x',pady=2);ttk.Button(actions,text='تعديل بيانات المهمة',command=self._task_edit_selected).pack(fill='x',pady=2);ttk.Button(actions,text='فتح مجلد المهمة',command=self._task_open_selected_folder).pack(fill='x',pady=2)

 def _task_preview_selected(self):
  if not hasattr(self,'task_preview_title'):return
  ids=self._task_selected_ids()
  if len(ids)!=1:
   self.task_preview_title.configure(text='اختر مهمة واحدة من القائمة');self.task_preview_meta.configure(text='ستظهر تفاصيلها ومرفقاتها هنا.');self.task_preview_text.configure(state='normal');self.task_preview_text.delete('1.0','end');self.task_preview_text.configure(state='disabled');self.task_preview_attachments.configure(text='');self.task_preview_task_id=None
   for child in self.task_preview_attachments_frame.winfo_children():child.destroy()
   return
  with connect() as c:row=c.execute('SELECT * FROM tasks WHERE id=?',(ids[0],)).fetchone()
  if not row:return
  self.task_preview_task_id=row['id'];self.task_preview_title.configure(text=row['title']);due=self._task_date_text(row['due_date'])+(' · '+(' – '.join(x for x in (row['start_time'],row['end_time']) if x) if row['start_time'] or row['end_time'] else ''));priority_text={1:'عاجلة',2:'عادية',3:'منخفضة'}.get(row['priority'],'عادية');state_text='مكتملة' if row['completed_at'] else 'مفتوحة';self.task_preview_meta.configure(text=f"المشروع: {row['project']}\nالموعد: {due}\nالأولوية: {priority_text}\nالحالة: {state_text}")
  self.task_preview_text.configure(state='normal');self.task_preview_text.delete('1.0','end');self.task_preview_text.insert('1.0',row['description'] or 'افتح صفحة المهمة لكتابة التفاصيل وإضافة المرفقات.');self.task_preview_text.configure(state='disabled')
  attachments=self._task_attachment_values(row);self.task_preview_attachments.configure(text=('المرفقات: '+str(len(attachments)) if attachments else 'لا توجد مرفقات'))
  for child in self.task_preview_attachments_frame.winfo_children():child.destroy()
  for item in attachments:
   path=(LOG/item['path']).resolve()
   line=tk.Frame(self.task_preview_attachments_frame,bg='white');line.pack(fill='x',pady=1)
   ttk.Button(line,text='×',width=3,command=lambda i=item:self._task_remove_attachment(row['id'],i)).pack(side='left')
   ttk.Button(line,text='📎 '+item.get('name',path.name),command=lambda p=path:os.startfile(str(p))).pack(side='right',fill='x',expand=True)

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
  if not row['project']:return messagebox.showwarning('المهمة','لا يمكن فتح مجلد مهمة غير مرتبطة بمشروع.',parent=self)
  folder=LOG/row['project']/('مهام '+row['project']);folder.mkdir(parents=True,exist_ok=True);os.startfile(str(folder))

 def _task_document_folder(self,row):
  project=str(row['project'] or '').strip()
  if not project:raise ValueError('لا يمكن حفظ مستند المهمة بدون مشروع.')
  project_root=(LOG/project).resolve()
  if not is_project_path(project_root):raise ValueError('مسار المشروع خارج مجلد Log.')
  folder=project_root/('مهام '+project);folder.mkdir(parents=True,exist_ok=True);return folder

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
  if not text_path.exists():
   legacy=text_path.with_suffix('.md');content=row['description'] or ''
   if legacy.is_file():
    old=legacy.read_text(encoding='utf-8',errors='replace')
    if old.startswith('# '):content=old.split('\n',2)[-1].lstrip('\n')
   text_path.write_text(content,encoding='utf-8')
  attachment_path=folder/f'مرفقات المهمة {task_id}';attachment_path.mkdir(exist_ok=True)
  try:attachments=json.loads(row['attachments'] or '[]')
  except (ValueError,TypeError):attachments=[]
  json_path=text_path.with_suffix('.json')
  metadata={'schema_version':1,'task_id':int(task_id),'title':row['title'],'project':row['project'],'due_date':row['due_date'],'start_time':row['start_time'],'end_time':row['end_time'],'priority':row['priority'],'tags':row['tags'],'attachments':attachments}
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
    sql='SELECT id,title,document_rel,document_mtime FROM tasks WHERE document_rel IS NOT NULL';params=()
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
    lines=content.splitlines()
    if lines and lines[0].strip().lstrip('#').strip()==str(row['title']).strip():content='\n'.join(lines[1:]).lstrip('\n')
    updates.append((content,self._task_log_relative(path),mtime,datetime.now().strftime('%Y-%m-%d %H:%M:%S'),row['id']))
   except (OSError,ValueError,TypeError):continue
  if updates:
   with connect() as c:c.executemany('UPDATE tasks SET description=?,document_rel=?,document_mtime=?,updated_at=? WHERE id=?',updates)
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
  folder=self._task_document_folder(row);attach_dir=folder/f'مرفقات المهمة {task_id}';attach_dir.mkdir(exist_ok=True);attachments=self._task_attachment_values(row)
  for raw in paths:
   source=Path(raw)
   if not source.is_file():continue
   target=attach_dir/(secrets.token_hex(4)+'_'+source.name);shutil.copy2(source,target);attachments.append({'name':source.name,'path':self._task_log_relative(target)})
  with connect() as c:c.execute('UPDATE tasks SET attachments=?,updated_at=? WHERE id=?',(json.dumps(attachments,ensure_ascii=False),datetime.now().strftime('%Y-%m-%d %H:%M:%S'),task_id))
  self._task_ensure_document_artifacts(task_id)

 def _task_remove_attachment(self,task_id,item):
  if not messagebox.askyesno('إزالة المرفق',f'إزالة الملف المرفق «{item.get("name","ملف")}» من هذه المهمة؟',parent=self):return
  try:
   with connect() as c:owner=c.execute('SELECT * FROM tasks WHERE id=?',(task_id,)).fetchone()
   row_folder=self._task_document_folder(owner) if owner else None;path=(LOG/item['path']).resolve()
   if path.is_file() and row_folder and path.is_relative_to(row_folder.resolve()):path.unlink()
  except (OSError,ValueError):pass
  with connect() as c:row=c.execute('SELECT * FROM tasks WHERE id=?',(task_id,)).fetchone()
  if not row:return
  attachments=[x for x in self._task_attachment_values(row) if x.get('path')!=item.get('path')]
  with connect() as c:c.execute('UPDATE tasks SET attachments=?,updated_at=? WHERE id=?',(json.dumps(attachments,ensure_ascii=False),datetime.now().strftime('%Y-%m-%d %H:%M:%S'),task_id))
  self._task_ensure_document_artifacts(task_id)
  if getattr(self,'task_preview_task_id',None)==task_id:self._task_preview_selected()

 def _task_task_dialog(self,row=None,project_locked=False,initial_date=None,project=None,initial_start=None,initial_end=None):
  dialog=tk.Toplevel(self);dialog.title('تعديل المهمة' if row else 'إضافة مهمة من التقويم');dialog.configure(bg='#eef3f7');dialog.transient(self);dialog.grab_set();dialog.resizable(False,False);card=tk.Frame(dialog,bg='white',highlightbackground='#d6e0e6',highlightthickness=1);card.pack(fill='both',expand=True,padx=14,pady=14);card.grid_columnconfigure(1,weight=1)
  tk.Label(card,text='تفاصيل المهمة',bg='white',fg='#19394e',font=('Segoe UI',14,'bold')).grid(row=0,column=0,columnspan=3,sticky='e',padx=14,pady=(14,8))
  project_locked=bool(project_locked or project is not None);title=tk.StringVar(value=(row['title'] if row else ''));due=tk.StringVar(value=(row['due_date'] or '' if row else (initial_date.isoformat() if initial_date else '')));start=tk.StringVar(value=(row['start_time'] or '' if row else (initial_start or '')));end=tk.StringVar(value=(row['end_time'] or '' if row else (initial_end or '')));priority=tk.StringVar(value={1:'عاجلة',2:'عادية',3:'منخفضة'}.get(row['priority'],'عادية') if row else 'عادية');chosen_project=project if project is not None else (row['project'] if row else (self.task_scope or ''));project_var=tk.StringVar(value=chosen_project or ('اختر مشروعًا…' if not row else ''));tags=tk.StringVar(value=(row['tags'] or '' if row else ''))
  def label(text,r):tk.Label(card,text=text,bg='white',fg='#607786',font=('Segoe UI',9)).grid(row=r,column=2,sticky='e',padx=12,pady=(5,2))
  label('عنوان المهمة',1);name=ttk.Entry(card,textvariable=title,width=42,justify='right');name.grid(row=2,column=0,columnspan=3,sticky='ew',padx=12,pady=(0,4))
  label('التاريخ',3);datebox=ttk.Entry(card,textvariable=due,width=15,justify='center');datebox.grid(row=4,column=1,padx=5,pady=(0,4),sticky='e');ttk.Button(card,text='🗓 اختر التاريخ',command=lambda:self._task_pick_date(due,initial_date,parent=dialog)).grid(row=4,column=0,padx=5,pady=(0,4),sticky='w');ttk.Button(card,text='بدون موعد',command=lambda:due.set('')).grid(row=4,column=2,padx=12,pady=(0,4),sticky='e')
  label('الوقت (اختياري)',5);timebox=tk.Frame(card,bg='white');timebox.grid(row=6,column=0,columnspan=3,sticky='ew',padx=12,pady=(0,4));self._task_time_control(timebox,start,'من');self._task_time_control(timebox,end,'إلى')
  label('الأولوية',7);ttk.Combobox(card,textvariable=priority,values=('عاجلة','عادية','منخفضة'),state='readonly',justify='right',style='Office.TCombobox').grid(row=8,column=0,columnspan=3,sticky='ew',padx=12,pady=(0,4))
  label('تابعة لأي مشروع؟',9);projects=self._task_project_names();project_values=([chosen_project] if project_locked and chosen_project else [])+projects;project_values=list(dict.fromkeys(project_values));project_combo=ttk.Combobox(card,textvariable=project_var,values=project_values,state='disabled' if project_locked else 'readonly',justify='right',style='Office.TCombobox');project_combo.grid(row=10,column=0,columnspan=3,sticky='ew',padx=12,pady=(0,4))
  label('هاشتاجات المهمة',11);ttk.Entry(card,textvariable=tags,justify='right').grid(row=12,column=0,columnspan=3,sticky='ew',padx=12,pady=(0,5))
  attachment_row=tk.Frame(card,bg='white');attachment_row.grid(row=13,column=0,columnspan=3,sticky='ew',padx=12,pady=4);pending_files=[];attachment_label=tk.StringVar(value='')
  ttk.Button(attachment_row,text='＋ إضافة ملف للمهمة',command=lambda:self._task_choose_pending_files(pending_files,attachment_label,row,parent=dialog)).pack(side='right');tk.Label(attachment_row,textvariable=attachment_label,bg='white',fg='#718491',font=('Segoe UI',8)).pack(side='right',padx=8)
  existing_count=len(self._task_attachment_values(row)) if row else 0;attachment_label.set(f'{existing_count} مرفق محفوظ' if existing_count else 'المرفقات تتحفظ داخل مجلد المهمة في Log')
  actions=tk.Frame(card,bg='white');actions.grid(row=14,column=0,columnspan=3,sticky='ew',padx=10,pady=(14,12))
  def save():
   name_value=title.get().strip()
   if not name_value:return messagebox.showwarning('المهام','عنوان المهمة مطلوب.',parent=dialog)
   try:due_value=self._task_parse_date(due.get())
   except ValueError as exc:return messagebox.showwarning('موعد المهمة',str(exc),parent=dialog)
   if (start.get() or end.get()) and not due_value:return messagebox.showwarning('موعد المهمة','حدد تاريخًا للمهمة قبل إدخال الوقت.',parent=dialog)
   if start.get() and end.get() and end.get()<=start.get():return messagebox.showwarning('وقت المهمة','وقت النهاية يجب أن يكون بعد البداية.',parent=dialog)
   if project_var.get() not in self._task_project_names():return messagebox.showwarning('المشروع','أنشئ مشروعًا أولًا، ثم اختر المشروع الذي تتبعه المهمة.',parent=dialog)
   project_value=project_var.get();tag_values=','.join(dict.fromkeys(t.strip().lstrip('#') for t in re.split(r'[،,\s]+',tags.get()) if t.strip()));description=(row['description'] or '' if row else '');rich_value=(row['rich_text'] or '' if row else '');now=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
   with connect() as c:
    if row:c.execute('UPDATE tasks SET title=?,description=?,rich_text=?,project=?,due_date=?,start_time=?,end_time=?,priority=?,tags=?,updated_at=? WHERE id=?',(name_value,description,rich_value,project_value,due_value,start.get() or None,end.get() or None,self._task_priority_num(priority.get()),tag_values,now,row['id']))
    else:
     cursor=c.execute('INSERT INTO tasks(title,description,rich_text,project,due_date,start_time,end_time,priority,tags,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(name_value,description,rich_value,project_value,due_value,start.get() or None,end.get() or None,self._task_priority_num(priority.get()),tag_values,now,now));self.new_task_document_id=cursor.lastrowid
   task_id=row['id'] if row else self.new_task_document_id
   try:
    self._task_ensure_document_artifacts(task_id)
    self._task_add_attachment_paths(task_id,pending_files)
   except (OSError,ValueError,sqlite3.Error) as exc:return messagebox.showerror('حفظ ملفات المهمة',str(exc),parent=dialog)
   dialog.destroy()
   if getattr(self,'task_calendar_active',False):
    self._task_calendar_draw(preserve_scroll=True)
    if getattr(self,'task_calendar_selected_id',None)==task_id:self._task_calendar_select_task(task_id)
   if hasattr(self,'task_tree') and self.task_tree.winfo_exists():self._task_refresh_rows()
  ttk.Button(actions,text='حفظ المهمة',command=save).pack(side='right',padx=3);ttk.Button(actions,text='إلغاء',command=dialog.destroy).pack(side='left',padx=3);dialog.bind('<Control-Return>',lambda e:(save(),'break'));dialog.update_idletasks();dialog.geometry(f'560x{max(470,dialog.winfo_reqheight())}+{max(0,self.winfo_rootx()+(self.winfo_width()-560)//2)}+{max(0,self.winfo_rooty()+(self.winfo_height()-dialog.winfo_reqheight())//2)}');name.focus_set()

 def _task_choose_pending_files(self,pending,label,row=None,parent=None):
  chosen=filedialog.askopenfilenames(parent=parent or self,title='اختر ملفات للمهمة')
  if not chosen:return
  for path in chosen:
   if path not in pending:pending.append(path)
  base=len(self._task_attachment_values(row)) if row else 0
  label.set(f'{base+len(pending)} مرفق · {len(pending)} جاهز للإضافة')

 def show_task_calendar(self,project=None,initial_date=None):
  if not project and not self._task_project_names():return messagebox.showinfo('التقويم','أنشئ مشروعًا أولًا حتى تتمكن من إضافة مهام مرتبطة به.',parent=self)
  self.task_rollover_token=getattr(self,'task_rollover_token',0)+1;rollover_token=self.task_rollover_token;self.task_calendar_scope=str(project or '');self.task_calendar_date=initial_date or date.today();self.task_calendar_view=getattr(self,'task_calendar_view','month');self.task_calendar_active=True;self.task_calendar_selected_id=None;self._task_rollover_elapsed();self.clear();self.configure(bg='#eef3f7');self.title('Rasd | التقويم والمهام');head=self.header('التقويم والمهام')
  ttk.Button(head,text=('← مهام المشروع' if project else '← قائمة المهام'),command=lambda:self.show_tasks(project)).pack(side='right',padx=5,pady=12)
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
  panel=self.task_calendar_preview;panel.grid_columnconfigure(0,weight=1);panel.grid_rowconfigure(3,weight=1)
  tk.Label(panel,text='معاينة المهمة',bg='#dfe7ec',fg='#19394e',font=('Segoe UI',12,'bold'),anchor='e',padx=12,pady=12).grid(row=0,column=0,sticky='ew')
  self.task_calendar_preview_title=tk.Label(panel,text='اضغط مهمة لمعاينتها',bg='white',fg='#19394e',font=('Segoe UI',12,'bold'),anchor='e',justify='right',wraplength=285);self.task_calendar_preview_title.grid(row=1,column=0,sticky='ew',padx=12,pady=12)
  self.task_calendar_preview_meta=tk.Label(panel,text='',bg='white',fg='#607786',font=('Segoe UI',9),anchor='e',justify='right');self.task_calendar_preview_meta.grid(row=2,column=0,sticky='ew',padx=12,pady=4)
  self.task_calendar_preview_text=tk.Text(panel,height=12,wrap='word',font=('Segoe UI',9),relief='flat',bg='#f7fafb',fg='#344c5b',state='disabled');self.task_calendar_preview_text.grid(row=3,column=0,sticky='nsew',padx=9,pady=6)
  self.task_calendar_preview_attachments=tk.Label(panel,text='',bg='white',fg='#607786',font=('Segoe UI',8),anchor='e',justify='right',wraplength=285);self.task_calendar_preview_attachments.grid(row=4,column=0,sticky='ew',padx=10,pady=4)
  actions=tk.Frame(panel,bg='white');actions.grid(row=5,column=0,sticky='ew',padx=9,pady=8);ttk.Button(actions,text='فتح ملف TXT',command=self._task_calendar_open_selected_text).pack(fill='x',pady=2);ttk.Button(actions,text='تعديل بيانات / الموعد',command=self._task_calendar_edit_selected).pack(fill='x',pady=2);ttk.Button(actions,text='فتح مجلد المهمة',command=self._task_calendar_open_selected_folder).pack(fill='x',pady=2);ttk.Button(actions,text='إخفاء المعاينة',command=self._task_calendar_hide_preview).pack(fill='x',pady=2)

 def _task_calendar_select_task(self,task_id):
  with connect() as c:row=c.execute('SELECT * FROM tasks WHERE id=?',(task_id,)).fetchone()
  if not row:return
  self.task_calendar_selected_id=int(task_id);self.task_calendar_preview.grid(row=0,column=1,sticky='nsew',padx=(8,0));self.task_calendar_layout.grid_columnconfigure(1,weight=0,minsize=320)
  self.task_calendar_preview_title.configure(text=row['title']);date_label=self._task_date_text(row['due_date']);time_label=' – '.join(x for x in (row['start_time'],row['end_time']) if x);priority={1:'عاجلة',2:'عادية',3:'منخفضة'}.get(row['priority'],'عادية');tags=' '.join('#'+x for x in (row['tags'] or '').split(',') if x);state='مكتملة' if row['completed_at'] else 'مفتوحة'
  self.task_calendar_preview_meta.configure(text=f"المشروع: {row['project']}\nالموعد: {date_label}{(' · '+time_label) if time_label else ''}\nالأولوية: {priority} · {state}\n{tags}")
  self.task_calendar_preview_text.configure(state='normal');self.task_calendar_preview_text.delete('1.0','end');self.task_calendar_preview_text.insert('1.0',row['description'] or 'لا توجد تفاصيل بعد.');self.task_calendar_preview_text.configure(state='disabled')
  attachments=self._task_attachment_values(row);self.task_calendar_preview_attachments.configure(text='المرفقات: '+(', '.join(x.get('name','ملف') for x in attachments) if attachments else 'لا يوجد'))

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
  except (OSError,ValueError) as exc:messagebox.showerror('مجلد المهمة',str(exc),parent=self)
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
  """Scrollable week/day calendar with pinned time column, pinned header, and exact pixel alignment."""
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

  day_width=max(base_width,min(max_lanes,8)*130);required_width=columns*day_width;timeline_height=24*60
  header_h=78

  main_area=tk.Frame(host,bg='white');main_area.pack(fill='both',expand=True)
  main_area.grid_rowconfigure(1,weight=1);main_area.grid_columnconfigure(1,weight=1)

  # الزاوية العلوية اليسرى الثابتة (فوق عمود الوقت مباشرة)
  corner=tk.Frame(main_area,bg='#dfe7ec',width=time_width,height=header_h)
  corner.grid(row=0,column=0,sticky='nsew');corner.grid_propagate(False)
  tk.Label(corner,text='اليوم / الوقت',bg='#dfe7ec',fg='#19394e',font=('Segoe UI',8,'bold')).place(x=0,y=0,width=time_width,height=36)
  tk.Label(corner,text='بدون ساعة',bg='#f1f5f7',fg='#607786',font=('Segoe UI',8,'bold')).place(x=0,y=36,width=time_width,height=42)

  # شريط عناوين الأيام العلوي (يتحرك أفقياً فقط مع الجدول)
  header_canvas=tk.Canvas(main_area,bg='white',height=header_h,highlightthickness=0)
  header_canvas.grid(row=0,column=1,sticky='ew')

  # عمود الساعات الثابت على اليسار (يبدأ من y=0 تماماً مثل مربعات المهام)
  time_canvas=tk.Canvas(main_area,bg='#edf2f5',width=time_width,highlightthickness=0)
  time_canvas.grid(row=1,column=0,sticky='ns')

  # مساحة رسم الساعات والمهام
  surface=tk.Canvas(main_area,bg='white',highlightthickness=0)
  surface.grid(row=1,column=1,sticky='nsew')
  self._cal_surface=surface;self._cal_time_canvas=time_canvas;self._cal_header_canvas=header_canvas

  def on_vscroll(*args):
   surface.yview(*args);time_canvas.yview(*args)
   try:self._cal_scroll_y=surface.yview()[0]
   except tk.TclError:pass

  def on_hscroll(*args):
   surface.xview(*args);header_canvas.xview(*args)
   try:self._cal_scroll_x=surface.xview()[0]
   except tk.TclError:pass

  scroll=ttk.Scrollbar(main_area,orient='vertical',command=on_vscroll)
  scroll.grid(row=1,column=2,sticky='ns')
  horizontal=ttk.Scrollbar(main_area,orient='horizontal',command=on_hscroll)
  horizontal.grid(row=2,column=1,sticky='ew')

  def update_yscroll(first,last):
   scroll.set(first,last);time_canvas.yview_moveto(first)
   try:self._cal_scroll_y=float(first)
   except ValueError:pass

  def update_xscroll(first,last):
   horizontal.set(first,last);header_canvas.xview_moveto(first)
   try:self._cal_scroll_x=float(first)
   except ValueError:pass

  surface.configure(yscrollcommand=update_yscroll,xscrollcommand=update_xscroll)
  time_canvas.configure(yscrollcommand=lambda f,l:scroll.set(f,l))
  header_canvas.configure(xscrollcommand=lambda f,l:horizontal.set(f,l))

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

  # بناء شريط العناوين العلوي
  header_frame=tk.Frame(header_canvas,bg='white',height=header_h)
  header_win=header_canvas.create_window((0,0),window=header_frame,anchor='nw',height=header_h)
  header_frame.grid_rowconfigure(0,minsize=36);header_frame.grid_rowconfigure(1,minsize=42)
  for col,target in enumerate(span):
   header_frame.grid_columnconfigure(col,weight=1,uniform='cal-hdr',minsize=day_width)
   tk.Button(header_frame,text=self._task_arabic_date(target),command=lambda t=target:self._task_task_dialog(initial_date=t,project=scope or None),bg='#d9eff0' if target==date.today() else '#dfe7ec',fg='#19394e',relief='flat',font=('Segoe UI',8,'bold'),wraplength=150).grid(row=0,column=col,sticky='nsew',padx=1,pady=(0,1))
   strip=tk.Frame(header_frame,bg='#f7fafb',height=41);strip.grid(row=1,column=col,sticky='nsew',padx=1,pady=(0,1));strip.grid_propagate(False);strip.bind('<Button-1>',lambda _e,t=target:self._task_task_dialog(initial_date=t,project=scope or None))
   for task in dated.get(target.isoformat(),[]):
    if not (task['start_time'] or task['end_time']):self._task_calendar_timeline_event(strip,task)
   tk.Button(strip,text='＋',command=lambda t=target:self._task_task_dialog(initial_date=t,project=scope or None),bg='#f7fafb',fg='#087e8b',relief='flat',font=('Segoe UI',8)).pack(side='left')

  # بناء عمود الساعات (يبدأ من y=0 بارتفاع 60 بيكسل لكل ساعة؛ الرقم في أعلى المربع عند بداية الساعة بالظبط)
  rail=tk.Frame(time_canvas,bg='#edf2f5',width=time_width,height=timeline_height)
  time_canvas.create_window((0,0),window=rail,anchor='nw',width=time_width,height=timeline_height)
  for hour in range(24):
   y=hour*60
   tk.Frame(rail,bg='#d6e0e6',height=1).place(x=0,y=y,width=time_width,height=1)
   tk.Label(rail,text=f'{hour:02d}:00',bg='#edf2f5',fg='#526b7b',font=('Segoe UI',8,'bold'),anchor='n').place(x=0,y=y+2,width=time_width,height=22)

  # بناء شبكة الساعات للأيام (تبدأ من y=0 تماماً مثل عمود الساعات)
  timeline=tk.Frame(surface,bg='white',height=timeline_height)
  window=surface.create_window((0,0),window=timeline,anchor='nw',height=timeline_height)
  timeline.grid_rowconfigure(0,weight=1)
  self.task_calendar_day_bodies={}
  for col,target in enumerate(span):
   timeline.grid_columnconfigure(col,minsize=day_width,weight=1,uniform='timeline-day')
   day=tk.Frame(timeline,bg='white',width=day_width,height=timeline_height,highlightbackground='#d6e0e6',highlightthickness=0);day.grid(row=0,column=col,sticky='nsew',padx=1);day.grid_propagate(False);day._task_calendar_date=target;self.task_calendar_day_bodies[target.isoformat()]=day
   for hour in range(24):
    slot=tk.Frame(day,bg='white',height=60,highlightbackground='#e3e9ed',highlightthickness=1,cursor='hand2');slot.place(x=0,y=hour*60,relwidth=1,height=60);slot.bind('<Button-1>',lambda e,t=target,h=hour,s=slot:self._task_calendar_add_at_pointer(e,t,h,s,scope))
    tk.Button(slot,text='＋',command=lambda t=target,h=hour:self._task_task_dialog(initial_date=t,project=scope or None,initial_start=f'{h:02d}:00',initial_end=('23:45' if h==23 else f'{h+1:02d}:00')),bg='white',fg='#b4c3cb',activebackground='#e7f3f4',relief='flat',font=('Segoe UI',8)).place(relx=1.0,rely=1.0,anchor='se')
   for item in intervals[target.isoformat()]:self._task_calendar_timeline_event(day,item['row'],item['start'],item['end'],item['lane'],item['lanes'],target)

  def sync_layout(_e=None):
   try:
    w=max(surface.winfo_width(),required_width)
    surface.itemconfigure(window,width=w,height=timeline_height)
    header_canvas.itemconfigure(header_win,width=w,height=header_h)
    surface.configure(scrollregion=(0,0,w,timeline_height))
    header_canvas.configure(scrollregion=(0,0,w,header_h))
    time_canvas.configure(scrollregion=(0,0,time_width,timeline_height))
   except tk.TclError:pass

  timeline.bind('<Configure>',sync_layout)
  surface.bind('<Configure>',sync_layout)

  def restore():
   try:
    sync_layout()
    surface.xview_moveto(saved_x);header_canvas.xview_moveto(saved_x)
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
  """Create a timed task at the clicked quarter-hour within a day cell."""
  height=max(1,slot.winfo_height());y=max(0,min(height-1,int(event.y)));quarter=min(3,int(y*4/height));start_minutes=hour*60+quarter*15;end_minutes=min(start_minutes+60,23*60+45)
  start=f'{start_minutes//60:02d}:{start_minutes%60:02d}';end=f'{end_minutes//60:02d}:{end_minutes%60:02d}' if end_minutes>start_minutes else None
  self._task_task_dialog(initial_date=target,project=project or None,initial_start=start,initial_end=end)

 def _task_calendar_timeline_event(self,parent,row,start_minute=None,end_minute=None,lane=0,lanes=1,day=None):
  if start_minute is None:
   priority=int(row['priority']);done=bool(row['completed_at']);color='#81909a' if done else {1:'#982934',2:'#244e70',3:'#725a16'}.get(priority,'#244e70');bg='#edf0f2' if done else {1:'#f8dddd',2:'#e5f0fa',3:'#fff1c9'}.get(priority,'#e5f0fa');caption=('✓ ' if done else '')+row['title'];b=tk.Button(parent,text=caption,command=lambda r=row:self._task_calendar_select_task(r['id']),bg=bg,fg=color,activebackground=bg,relief='flat',anchor='e',justify='right',wraplength=170,font=('Segoe UI',8,'bold' if priority==1 and not done else 'normal'));b.pack(fill='x',padx=2,pady=2);b.bind('<Double-Button-1>',lambda _e,r=row:(self._task_open_document(r['id']),'break'));return b
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

 def _task_arabic_date(self,d,month_only=False):
  months=('يناير','فبراير','مارس','أبريل','مايو','يونيو','يوليو','أغسطس','سبتمبر','أكتوبر','نوفمبر','ديسمبر');weekdays=('الاثنين','الثلاثاء','الأربعاء','الخميس','الجمعة','السبت','الأحد');return (months[d.month-1]+' '+str(d.year)) if month_only else (weekdays[d.weekday()]+' '+f'{d.day:02d} '+months[d.month-1]+' '+str(d.year))
 def _task_calendar_task_row(self,parent,target,row):
  color='#81909a' if row['completed_at'] else {1:'#b92f3b',2:'#3378a8',3:'#a47d1c'}.get(row['priority'],'#3378a8');text=('✓ ' if row['completed_at'] else '')+(row['start_time']+' · ' if row['start_time'] else '')+row['title']+('   ['+row['project']+']' if row['project'] else '');bg='#edf0f2' if row['completed_at'] else '#fce5e5' if row['priority']==1 else '#edf4fa' if row['priority']==2 else '#fff5dc';b=tk.Button(parent,text=text,command=lambda r=row:self._task_calendar_select_task(r['id']),anchor='e',bg=bg,fg=color,relief='flat',font=('Segoe UI',9));b.pack(fill='x',padx=5,pady=3);b.bind('<Double-Button-1>',lambda _e,r=row:(self._task_open_document(r['id']),'break'))