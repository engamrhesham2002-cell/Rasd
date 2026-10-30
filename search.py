# Rasd - صفحة البحث (Everything) ونتائجه وحفظ البحث
from common import *
from update_utils import *
from storage import *

class SearchMixin:
 def show_search_page(self, initial_query=None):
  if not self.root or not self.root.is_dir():return
  if hasattr(self, 'search_page') and self.search_page.winfo_exists():
   try: self.search_page.destroy()
   except tk.TclError: pass
  self.preview_token+=1
  if hasattr(self, 'explorer_page') and self.explorer_page.winfo_exists():
   self.explorer_page.pack_forget()
  self.search_page=tk.Frame(self,bg='#e8edf1');self.search_page.pack(fill='both',expand=True,padx=10,pady=9)
  self.search_page.grid_rowconfigure(0,weight=1);self.search_page.grid_columnconfigure(0,weight=0,minsize=350);self.search_page.grid_columnconfigure(1,weight=1);self.search_page.grid_columnconfigure(2,weight=0,minsize=176)
  
  self.search_preview_area=tk.Frame(self.search_page,bg='#eef2f5',highlightbackground='#d6e0e6',highlightthickness=1,width=350);self.search_preview_area.grid(row=0,column=0,sticky='nsew',padx=(0,8));self.search_preview_area.grid_propagate(False);self.search_preview_area.grid_rowconfigure(1,weight=1);self.search_preview_area.grid_columnconfigure(0,weight=1)
  preview_head=tk.Frame(self.search_preview_area,bg='#dfe7ec');preview_head.grid(row=0,column=0,sticky='ew')
  tk.Label(preview_head,text='معاينة وتفاصيل',bg='#dfe7ec',fg='#19394e',font=('Segoe UI',11,'bold'),anchor='e').pack(side='right',fill='x',expand=True,ipady=10,padx=10)
  ttk.Button(preview_head,text='×',width=3,command=self.toggle_preview_panel).pack(side='left',padx=5,pady=4)
  self.search_preview_image=tk.Canvas(self.search_preview_area,bg='#eef2f5',highlightthickness=0);self.search_preview_image.grid(row=1,column=0,sticky='nsew',padx=7,pady=7);self.search_preview_image.bind('<ButtonPress-1>',self.preview_pan_start);self.search_preview_image.bind('<B1-Motion>',self.preview_pan_move);self.search_preview_image.bind('<MouseWheel>',self.preview_wheel)
  self.search_preview_meta=tk.Label(self.search_preview_area,text='اختر نتيجة لمعاينتها.',bg='white',fg='#526b7c',font=('Segoe UI',9),justify='right',anchor='ne',wraplength=330);self.search_preview_meta.grid(row=2,column=0,sticky='ew',padx=12,pady=(0,8))
  self.search_preview_related_strip=tk.Frame(self.search_preview_area,bg='#edf2f5');self.search_preview_related_strip.grid(row=3,column=0,sticky='ew',padx=8,pady=(0,4));self.search_preview_related_strip.grid_remove()
  ctr=tk.Frame(self.search_preview_area,bg='white');ctr.grid(row=4,column=0,sticky='ew',padx=8,pady=(0,8))
  ttk.Button(ctr,text='−',width=3,command=lambda:self.zoom_preview(-.15)).pack(side='left')
  ttk.Button(ctr,text='＋',width=3,command=lambda:self.zoom_preview(.15)).pack(side='left')
  ttk.Button(ctr,text='◀ صفحة',command=lambda:self.change_pdf_page(-1)).pack(side='right',padx=2)
  ttk.Button(ctr,text='صفحة ▶',command=lambda:self.change_pdf_page(1)).pack(side='right',padx=2)
  ttk.Button(ctr,text='🔗 ربط ملفات',command=self.open_related_from_preview).pack(side='right',padx=3)

  self.search_center=tk.Frame(self.search_page,bg='#e8edf1');self.search_center.grid(row=0,column=1,sticky='nsew');self.search_center.grid_columnconfigure(0,weight=1)
  head=tk.Frame(self.search_center,bg='#102c3d');head.grid(row=0,column=0,sticky='ew')
  tk.Label(head,text='بحث المشروع',font=('Segoe UI',15,'bold'),fg='white',bg='#102c3d').pack(side='right',padx=16,pady=11)
  ttk.Button(head,text='← رجوع للملفات',command=self.hide_search_page).pack(side='left',padx=10,pady=7)
  self.search_preview_toggle=ttk.Button(head,text='◧  إخفاء المعاينة',command=self.toggle_preview_panel);self.search_preview_toggle.pack(side='left',padx=4,pady=7)
  
  scope=tk.Frame(self.search_center,bg='#dfe7ec');scope.grid(row=1,column=0,sticky='ew',pady=(6,7))
  tk.Label(scope,text=f'نتائج البحث محصورة في مشروع «{self.project}»',bg='#dfe7ec',fg='#28465a',anchor='e',font=('Segoe UI',9,'bold')).pack(side='right',padx=12,pady=7)
  tk.Label(scope,text='المشروع بالكامل',bg='#dfe7ec',fg='#087e8b',font=('Segoe UI',9)).pack(side='left',padx=12)
  
  with connect() as c:
   state=c.execute('select query,mode,file_type from project_search_state where project=?',(self.project,)).fetchone()
   self.search_cache=c.execute("select f.*,group_concat(t.tag, ' ') tags from files f left join tags t on t.path=f.path where f.project=? group by f.path",(self.project,)).fetchall()
   saved=c.execute('select query,mode from saved_searches where project=? order by created desc',(self.project,)).fetchall()
   history=c.execute('select query,mode from search_history where project=? order by searched_at desc limit 20',(self.project,)).fetchall()
  
  q,mode,kind=(state['query'],state['mode'],state['file_type']) if state else ('','الكل','كل النتائج')
  if initial_query is not None:
   q = str(initial_query)
  self.search_type=kind or 'كل النتائج';self.search_query=tk.StringVar(value=q or '');self.search_mode=tk.StringVar(value=mode or 'الكل');self.search_search_job=None;self.search_history_job=None
  
  bar=tk.Frame(self.search_center,bg='white',highlightbackground='#d6e0e6',highlightthickness=1);bar.grid(row=2,column=0,sticky='ew',pady=(0,6))
  tk.Label(bar,text='ابحث بالاسم أو المسار أو الامتداد أو الهاشتاج',bg='white',fg='#617789',font=('Segoe UI',9)).pack(side='right',padx=(8,0))
  entry=ttk.Entry(bar,textvariable=self.search_query,font=('Segoe UI',12),justify='right');entry.pack(side='right',fill='x',expand=True,padx=8,pady=6)
  self.search_mode_box=ttk.Combobox(bar,textvariable=self.search_mode,values=('الكل','اسم الملف','المسار','الامتداد','الهاشتاج'),state='readonly',width=13,justify='right',style='Office.TCombobox');self.search_mode_box.pack(side='right',padx=4);self.search_mode_box.bind('<<ComboboxSelected>>',self.search_mode_changed)
  ttk.Button(bar,text='مسح',command=lambda:self.search_query.set('')).pack(side='right',padx=3);ttk.Button(bar,text='☆ حفظ البحث',command=self.save_search_bookmark).pack(side='left',padx=5)
  
  presets=tk.Frame(self.search_center,bg='#e8edf1');presets.grid(row=3,column=0,sticky='new',pady=(0,4));self.search_center.grid_rowconfigure(4,weight=1);tk.Label(presets,text='محفوظ:',bg='#e8edf1',fg='#617789').pack(side='right')
  self.saved_search_box=ttk.Combobox(presets,values=[f"{r['query']}  ·  {r['mode']}" for r in saved],state='readonly',width=26,justify='right',style='Office.TCombobox');self.saved_search_box.pack(side='right',padx=5);self.saved_search_rows=list(saved);self.saved_search_box.bind('<<ComboboxSelected>>',self.load_search_bookmark)
  ttk.Button(presets,text='حذف المحفوظ',command=self.delete_search_bookmark).pack(side='right',padx=3)
  tk.Label(presets,text='حديث:',bg='#e8edf1',fg='#617789').pack(side='right',padx=(12,2));self.history_rows=list(history);self.history_box=ttk.Combobox(presets,values=[f"{r['query']}  ·  {r['mode']}" for r in history],state='readonly',width=36,justify='right',style='Office.TCombobox');self.history_box.pack(side='right',padx=4);self.history_box.bind('<<ComboboxSelected>>',self.load_search_history)
  
  self.search_nb=ttk.Notebook(self.search_center);self.search_nb.grid(row=4,column=0,sticky='nsew');self.search_nb.bind('<<NotebookTabChanged>>',self.search_tab_changed);self.search_views={};self.search_tab_types={}
  self.search_selection_bar,self.search_selection_label=self.make_selection_bar(self.search_center);self.search_selection_bar.grid(row=5,column=0,sticky='ew',pady=(5,0));self.search_selection_bar.grid_remove()
  self.search_status=tk.StringVar(value='');tk.Label(self.search_center,textvariable=self.search_status,bg='#dfe7ec',fg='#617789',anchor='e',font=('Segoe UI',9)).grid(row=6,column=0,sticky='ew',pady=(4,0))
  
  rail=tk.Frame(self.search_page,bg='#102c3d',width=176);rail.grid(row=0,column=2,sticky='nsew',padx=(0,8));rail.grid_propagate(False)
  tk.Label(rail,text='بحث داخل المشروع',bg='#102c3d',fg='white',font=('Segoe UI',12,'bold')).pack(anchor='e',padx=14,pady=(13,2));tk.Label(rail,text=self.project,bg='#102c3d',fg='#a9c3d0',font=('Segoe UI',9),wraplength=162,anchor='e').pack(anchor='e',fill='x',padx=14,pady=(0,7))
  tk.Label(rail,text='التصفح',bg='#102c3d',fg='#83a8b9',font=('Segoe UI',8,'bold')).pack(anchor='e',padx=14,pady=(1,3))
  def search_exit(kind,value=None):self.leave_search_for(kind,value)
  for label,kind in [('ملفات المجلدات','folder'),('ملفات المشروع','project')]:
   tk.Button(rail,text='▦  '+label,command=lambda k=kind:search_exit(k),anchor='e',bg='#102c3d',fg='#d3e2e9',activebackground='#24546a',activeforeground='white',relief='flat',font=('Segoe UI',8),padx=11,pady=5,cursor='hand2').pack(fill='x',padx=7,pady=1)
  tk.Label(rail,text='الوصول السريع',bg='#102c3d',fg='#83a8b9',font=('Segoe UI',8,'bold')).pack(anchor='e',padx=14,pady=(7,2))
  for label,kind in [('المفضلة','favorites'),('آخر ما فتحته','opened'),('أضيف حديثًا','added'),('سجل التغييرات','changes'),('سلة المهملات','recycle_bin')]:
   tk.Button(rail,text='•  '+label,command=lambda k=kind:search_exit(k),anchor='e',bg='#102c3d',fg='#d3e2e9',activebackground='#24546a',activeforeground='white',relief='flat',font=('Segoe UI',8),padx=11,pady=4,cursor='hand2').pack(fill='x',padx=7,pady=1)
  with connect() as c:
   search_specialties=sorted({r[0] for r in c.execute('select tag from folder_specialty_catalog where project=? union select distinct tag from folder_tags where project=?',(self.project,self.project))})
  if search_specialties:
   tk.Label(rail,text='التخصصات',bg='#102c3d',fg='#83a8b9',font=('Segoe UI',8,'bold')).pack(anchor='e',padx=14,pady=(7,2))
   for tag in search_specialties[:5]:
    tk.Button(rail,text='●  '+tag,command=lambda t=tag:search_exit('specialty',t),anchor='e',bg='#102c3d',fg='#d3e2e9',activebackground='#24546a',relief='flat',font=('Segoe UI',8),padx=11,pady=4,cursor='hand2').pack(fill='x',padx=7,pady=1)
  tk.Label(rail,text='نطاق النتائج: المشروع بالكامل',bg='#1b4053',fg='white',font=('Segoe UI',8),justify='right',anchor='e',padx=8,pady=6,wraplength=158).pack(fill='x',padx=7,pady=(6,0))
  tk.Label(rail,text='طرق البحث',bg='#102c3d',fg='#83a8b9',font=('Segoe UI',8,'bold')).pack(anchor='e',padx=14,pady=(8,2))
  for label,mode_name in [('الكل','الكل'),('اسم الملف','اسم الملف'),('المسار','المسار'),('الامتداد','الامتداد'),('الهاشتاج','الهاشتاج')]:
   tk.Button(rail,text='⌕  '+label,command=lambda x=mode_name:self.search_mode.set(x),anchor='e',bg='#102c3d',fg='#d3e2e9',activebackground='#24546a',activeforeground='white',relief='flat',font=('Segoe UI',8),padx=11,pady=4,cursor='hand2').pack(fill='x',padx=7,pady=1)
  tk.Frame(rail,bg='#23485b',height=1).pack(fill='x',padx=12,pady=7);tk.Label(rail,text='النتائج تتحدث أثناء الكتابة. اختر نوعًا من التبويبات أعلى القائمة.',bg='#102c3d',fg='#a9c3d0',font=('Segoe UI',8),justify='right',wraplength=158).pack(anchor='e',padx=12)
  
  self.active_preview=(self.preview_image,self.preview_meta,self.preview_related_strip)
  self.preview_image=self.search_preview_image;self.preview_meta=self.search_preview_meta;self.preview_related_strip=self.search_preview_related_strip
  self.search_query.trace_add('write',self.schedule_search_results);self.search_mode.trace_add('write',self.schedule_search_results)
  entry.bind('<Return>',self.record_search_history);entry.bind('<Control-f>',lambda e:(entry.focus_set(),'break'));entry.bind('<Escape>',lambda e:(self.hide_search_page(),'break'))
  self.render_search_results();entry.focus_set();self.animate_window_in()

 def open_related_from_preview(self):
  p_str = getattr(self, 'preview_current_path', None)
  if not p_str:
   return messagebox.showinfo('الملفات المرتبطة', 'حدد ملفاً من النتائج أولاً لإدارة أو فتح ملفاته المرتبطة.', parent=self)
  p = Path(p_str)
  if p.is_file() and hasattr(self, 'manage_file_links'):
   self.manage_file_links(p)

 def refresh_search_cache(self):
  with connect() as c:self.search_cache=c.execute("select f.*,group_concat(t.tag, ' ') tags from files f left join tags t on t.path=f.path where f.project=? group by f.path",(self.project,)).fetchall()

 def save_search_state(self):
  if not hasattr(self,'search_query') or not hasattr(self,'search_page') or not self.search_page.winfo_exists():return
  with connect() as c:c.execute('insert into project_search_state(project,query,mode,file_type) values(?,?,?,?) on conflict(project) do update set query=excluded.query,mode=excluded.mode,file_type=excluded.file_type',(self.project,self.search_query.get(),self.search_mode.get(),self.search_type))

 def load_search_bookmark(self,e=None):
  i=self.saved_search_box.current()
  if i>=0 and i<len(self.saved_search_rows):r=self.saved_search_rows[i];self.search_mode.set(r['mode']);self.search_query.set(r['query']);self.record_search_history()

 def load_search_history(self,e=None):
  i=self.history_box.current()
  if i>=0 and i<len(self.history_rows):r=self.history_rows[i];self.search_mode.set(r['mode']);self.search_query.set(r['query'])

 def save_search_bookmark(self):
  q=self.search_query.get().strip()
  if not q:return messagebox.showinfo('حفظ البحث','اكتب كلمة البحث أولًا.',parent=self)
  mode=self.search_mode.get()
  with connect() as c:c.execute('insert or replace into saved_searches(project,query,mode,created) values(?,?,?,?)',(self.project,q,mode,stamp(time.time())))
  self.log_activity('حفظ بحث',f'تم حفظ البحث «{q[:300]}» · {mode}')
  with connect() as c:self.saved_search_rows=c.execute('select query,mode from saved_searches where project=? order by created desc',(self.project,)).fetchall()
  self.saved_search_box.configure(values=[f"{r['query']}  ·  {r['mode']}" for r in self.saved_search_rows]);self.saved_search_box.current(0)

 def delete_search_bookmark(self):
  i=self.saved_search_box.current()
  if i<0 or i>=len(self.saved_search_rows):return
  r=self.saved_search_rows[i]
  with connect() as c:c.execute('delete from saved_searches where project=? and query=? and mode=?',(self.project,r['query'],r['mode']))
  self.log_activity('حذف بحث محفوظ',f'تم حذف البحث المحفوظ «{r["query"][:300]}» · {r["mode"]}')
  with connect() as c:self.saved_search_rows=c.execute('select query,mode from saved_searches where project=? order by created desc',(self.project,)).fetchall()
  self.saved_search_box.set('');self.saved_search_box.configure(values=[f"{x['query']}  ·  {x['mode']}" for x in self.saved_search_rows])

 def record_search_history(self,e=None):
  q=self.search_query.get().strip()
  if q:
   mode=self.search_mode.get()
   with connect() as c:c.execute('insert or replace into search_history(project,query,mode,searched_at) values(?,?,?,?)',(self.project,q,mode,stamp(time.time())))
   search_key=(self.project,q,mode)
   if getattr(self,'_last_activity_search',None)!=search_key:
    self.log_activity('بحث',f'بحث عن «{q[:300]}» · {mode}')
    self._last_activity_search=search_key
   with connect() as c:self.history_rows=c.execute('select query,mode from search_history where project=? order by searched_at desc limit 20',(self.project,)).fetchall()
   self.history_box.configure(values=[f"{r['query']}  ·  {r['mode']}" for r in self.history_rows]);self.history_box.set('')
  self.save_search_state()

 def search_mode_changed(self,e=None):self.schedule_search_results()

 def search_tab_changed(self,e=None):
  if getattr(self,'search_rendering',False) or not self.search_nb.tabs():return
  label=self.search_nb.tab(self.search_nb.select(),'text');self.search_type=self.search_tab_types.get(label,'كل النتائج');self.save_search_state()

 def launch_everything_search(self):
  exe=Path(getattr(sys,'_MEIPASS',BASE))/'Everything'/'Everything.exe'
  if not exe.exists():return self.show_search_page()
  try:
   root=self.root.resolve()
   if not is_project_path(root):raise ValueError('يمكن لـ Everything البحث داخل مجلدات المشاريع الموجودة في Log فقط')
   key=hashlib.sha256(str(root).casefold().encode('utf-8')).hexdigest()[:16]
   data=LOG/'.everything_data'/key;data.mkdir(parents=True,exist_ok=True)
   ini=data/'Everything.ini';db=data/'Everything.db'
   if not ini.exists():ini.write_text('[Everything]\napp_data=0\nrun_as_admin=0\nindex_as_admin=0\nauto_include_fixed_volumes=0\nauto_include_removable_volumes=0\nauto_include_network_volumes=0\nallow_options=0\nallow_admin_options=0\nallow_plugins=0\nsearch_history_enabled=1\nsearch_history_keep_forever=1\nsearch_history_always_suggest=1\n',encoding='utf-8')
   local_exe=data/'Everything.exe';local_lng=data/'Everything.lng'
   for source,target in ((exe,local_exe),(exe.with_name('Everything.lng'),local_lng)):
    if source.exists() and (not target.exists() or target.stat().st_size!=source.stat().st_size):
     try:shutil.copy2(source,target)
     except OSError:pass
   if not local_exe.exists():local_exe=exe
   if ini.exists():
    content=ini.read_text(encoding='utf-8',errors='replace')
    for setting in ('search_history_enabled=1','search_history_keep_forever=1','search_history_always_suggest=1'):
     name,value=setting.split('=',1);lines=content.splitlines();match=[i for i,line in enumerate(lines) if line.strip().split('=',1)[0].casefold()==name.casefold()]
     if match:lines[match[-1]]=setting
     else:lines.append(setting)
     content='\n'.join(lines)+'\n'
    ini.write_text(content,encoding='utf-8')
   self.explorer_page.pack_forget();self.everything_page=tk.Frame(self,bg='#e8edf1');self.everything_page.pack(fill='both',expand=True,padx=10,pady=8)
   head=tk.Frame(self.everything_page,bg='#102c3d');head.pack(fill='x');tk.Label(head,text=f'بحث Everything داخل {self.project}',font=('Segoe UI',15,'bold'),fg='white',bg='#102c3d').pack(side='right',padx=18,pady=10);ttk.Button(head,text='← الرجوع للمجلد',command=self.hide_everything_page).pack(side='left',padx=12,pady=7)
   self.everything_host=tk.Frame(self.everything_page,bg='white',highlightbackground='#d8e2ea',highlightthickness=1);self.everything_host.pack(fill='both',expand=True,pady=(8,0));self.everything_key=key;self.everything_status=tk.StringVar(value='جارٍ فتح واجهة البحث وفهرسة ملفات هذا المشروع...');tk.Label(self.everything_page,textvariable=self.everything_status,anchor='e',bg='#e8edf1',fg='#617789').pack(fill='x')
   instance='OfficeLogSearch_'+key
   with connect() as c:extensions=[r[0] for r in c.execute('select distinct ext from files where project=? and ext is not null and ext<>\'\'',(self.project,))]
   self.everything_launch=(local_exe,instance,ini,db,data,root,extensions);self.everything_instance=instance;self.everything_data=data;self.everything_exe=local_exe
   self.everything_attempts=0;self.everything_exe_path=str(local_exe.resolve())
   self.everything_exit_proc=subprocess.Popen([str(local_exe),'-instance',instance,'-exit','-wait'],cwd=str(data),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
   self.after(100,self.start_everything_instance)
  except Exception as e:messagebox.showerror('تعذر تشغيل Everything',str(e),parent=self)

 def start_everything_instance(self):
  if not hasattr(self,'everything_host') or not self.everything_host.winfo_exists():return
  if self.everything_exit_proc and self.everything_exit_proc.poll() is None:
   self.everything_attempts+=1
   if self.everything_attempts>60:
    self.everything_status.set('تعذر إغلاق جلسة البحث السابقة. ارجع للمجلد ثم أعد فتح البحث.')
    return
   self.after(100,self.start_everything_instance);return
  try:
   exe,instance,ini,db,data,root,extensions=self.everything_launch
   sync_everything_filters(data,instance,extensions)
   self.everything_proc=subprocess.Popen([str(exe),'-instance',instance,'-config',str(ini),'-db',str(db),'-no-auto-index','-volumes','','-folders',str(root),'-no-menu','-no-folders-sidebar','-bookmarks-sidebar','-filters-sidebar','-focus-search','-details','-sort','Name','-sort-ascending'],cwd=str(data))
   self.everything_attempts=0;self.after(250,self.attach_everything_window)
  except Exception as e:self.everything_status.set(f'تعذر تشغيل Everything: {e}')

 def attach_everything_window(self):
  if not hasattr(self,'everything_host') or not self.everything_host.winfo_exists():return
  key='OfficeLogSearch_'+str(self.everything_key);found=[];user32=ctypes.windll.user32;target_pid=self.everything_proc.pid if self.everything_proc else 0;target_exe=os.path.normcase(os.path.abspath(getattr(self,'everything_exe_path','')))
  remembered=self.everything_windows.get(key)
  if remembered and user32.IsWindow(remembered):found.append(remembered)
  enum_type=ctypes.WINFUNCTYPE(ctypes.c_bool,ctypes.c_void_p,ctypes.c_void_p)
  def visit(hwnd,_):
   if not user32.IsWindowVisible(hwnd):return True
   n=user32.GetWindowTextLengthW(hwnd)
   if not n:return True
   title=ctypes.create_unicode_buffer(n+1);user32.GetWindowTextW(hwnd,title,n+1)
   pid=ctypes.c_ulong();user32.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
   matches=key in title.value or (target_pid and pid.value==target_pid)
   if not matches and target_exe:
    kernel32=ctypes.windll.kernel32;handle=kernel32.OpenProcess(0x1000,False,pid.value)
    if handle:
     size=ctypes.c_ulong(32768);path=ctypes.create_unicode_buffer(size.value)
     try:matches=bool(kernel32.QueryFullProcessImageNameW(handle,0,path,ctypes.byref(size))) and os.path.normcase(os.path.abspath(path.value))==target_exe
     finally:kernel32.CloseHandle(handle)
   if matches:found.append(hwnd);return False
   return True
  if not found:user32.EnumWindows(enum_type(visit),0)
  if not found:
   self.everything_attempts+=1
   if self.everything_proc and self.everything_proc.poll() is not None and self.everything_attempts>12:
    self.everything_status.set('تعذر إظهار نافذة البحث. اضغط رجوع ثم أعد فتح البحث.')
    ttk.Button(self.everything_page,text='إعادة المحاولة',command=self.launch_everything_search).pack(anchor='e',pady=6)
    return
   if self.everything_attempts>80:
    self.everything_status.set('استغرق فتح البحث وقتًا أطول من المتوقع. اضغط رجوع ثم أعد المحاولة.')
    return
   self.after(250,self.attach_everything_window);return
  hwnd=found[0];self.everything_hwnd=hwnd;self.everything_windows[key]=hwnd;parent=self.everything_host.winfo_id();user32.SetParent(hwnd,parent)
  GWL_STYLE=-16;style=user32.GetWindowLongW(hwnd,GWL_STYLE);remove=0x80000000|0x00C00000|0x00040000|0x00080000|0x00020000|0x00010000;style=(style&~remove)|0x40000000|0x10000000;user32.SetWindowLongW(hwnd,GWL_STYLE,style);self.everything_host.bind('<Configure>',self.resize_everything_window);self.resize_everything_window();user32.ShowWindow(hwnd,5);self.everything_status.set('بحث سريع داخل ملفات المشروع المفتوح فقط')

 def resize_everything_window(self,event=None):
  if self.everything_hwnd and self.everything_host.winfo_exists():
   user32=ctypes.windll.user32;user32.MoveWindow(self.everything_hwnd,0,0,max(1,self.everything_host.winfo_width()),max(1,self.everything_host.winfo_height()),True)

 def hide_everything_page(self):
  if self.everything_hwnd:
   hwnd=self.everything_hwnd;user32=ctypes.windll.user32;user32.ShowWindow(hwnd,0);user32.SetParent(hwnd,0);user32.PostMessageW(hwnd,0x0010,0,0);self.everything_hwnd=None;self.everything_windows.clear()
  self.stop_everything_instance()
  if hasattr(self,'everything_page'):self.everything_page.destroy()
  self.explorer_page.pack(fill='both',expand=True,padx=10,pady=9);self.status.set('تم الرجوع إلى ملفات المشروع')

 def prepare_everything_search(self,requested_root=None):
  if os.name!='nt':raise RuntimeError('بحث Everything متاح على Windows فقط')
  resource=Path(getattr(sys,'_MEIPASS',BASE))/'Everything';source_exe=resource/'Everything.exe';source_cli=resource/'es.exe'
  if not source_exe.is_file() or not source_cli.is_file():raise FileNotFoundError('ملفات محرك Everything غير موجودة بجوار البرنامج')
  root=Path(requested_root or self.root).resolve()
  if not is_project_path(root):raise ValueError('يمكن لـ Everything البحث داخل مجلدات المشاريع الموجودة في Log فقط')
  key=hashlib.sha256(str(root).casefold().encode('utf-8')).hexdigest()[:16];instance='OfficeLogSearch_'+key;data=LOG/'.everything_data'/key;data.mkdir(parents=True,exist_ok=True)
  local_exe=data/'Everything.exe';ini=data/'Everything.ini';db=data/'Everything.db'
  with self.search_engine_lock:
   if self.everything_key==key and self.everything_proc and self.everything_proc.poll() is None:
    return local_exe,source_cli,instance,data,root
   if self.everything_instance and self.everything_instance!=instance:self.stop_everything_instance()
   if not local_exe.exists() or local_exe.stat().st_size!=source_exe.stat().st_size:shutil.copy2(source_exe,local_exe)
   if not ini.exists():ini.write_text('[Everything]\napp_data=0\nrun_as_admin=0\nindex_as_admin=0\nauto_include_fixed_volumes=0\nauto_include_removable_volumes=0\nauto_include_network_volumes=0\n',encoding='utf-8')
   if db.exists():
    try:subprocess.run([str(local_exe),'-instance',instance,'-exit','-wait'],cwd=str(data),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),check=False)
    except (OSError,subprocess.TimeoutExpired):pass
   flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
   args=[str(local_exe),'-instance',instance,'-config',str(ini),'-db',str(db),'-no-auto-index','-volumes','','-folders',str(root),'-startup']
   self.everything_proc=subprocess.Popen(args,cwd=str(data),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=flags)
   self.everything_key=key;self.everything_instance=instance;self.everything_data=data;self.everything_exe=local_exe;self.everything_cli=source_cli;self.everything_root=root
  return local_exe,source_cli,instance,data,root

 def search_row_matches(self,row,term,mode):
  if is_task_internal_artifact(row.get('path') or ''):return False
  query=(term or '').strip().casefold()
  if not query:return True
  name=str(row.get('name') or '')
  rel=str(row.get('rel') or '')
  ext=str(row.get('ext') or '')
  tags=str(row.get('tags') or '')
  if mode=='اسم الملف':source=name
  elif mode=='المسار':source=rel
  elif mode=='الامتداد':
   source=ext
   query=query.lstrip('*.')
  elif mode=='الهاشتاج':source=tags
  else:source=' '.join((name,rel,ext,tags,str(row.get('description') or '')))
  terms=[phrase or word for phrase,word in re.findall(r'"([^"]+)"|(\S+)',query)]
  if not terms:terms=[query]
  folded=source.casefold()
  return all(term in folded for term in terms)

 def search_task_documents(self,project,term):
  if not term:return []
  try:self._task_sync_text_documents(project)
  except Exception:pass
  tokens=re.findall(r'[^\W_]+',str(term).casefold(),flags=re.UNICODE);expression=' AND '.join('"'+x.replace('"','""')+'"*' for x in tokens)
  if not expression:return []
  with connect() as c:
   try:rows=c.execute('SELECT t.id,t.title,t.project,t.tags,t.description,t.document_rel FROM tasks t WHERE t.project=? AND t.id IN (SELECT rowid FROM task_fts WHERE task_fts MATCH ?)',(project,expression)).fetchall()
   except sqlite3.OperationalError:rows=c.execute('SELECT id,title,project,tags,description,document_rel FROM tasks WHERE project=? AND (title LIKE ? OR description LIKE ? OR project LIKE ? OR tags LIKE ?)',(project,)+tuple('%'+str(term)+'%' for _ in range(4))).fetchall()
  result=[]
  for row in rows:
   try:
    path=(LOG/row['document_rel']).resolve()
    if not path.is_file() or is_task_internal_artifact(path):continue
    stat=path.stat();rel=path.relative_to(LOG/str(project)).as_posix()
   except (OSError,ValueError,TypeError):continue
   result.append({'path':str(path),'project':str(project),'rel':rel,'name':path.name,'ext':'.txt','size':stat.st_size,'mtime':stat.st_mtime,'last_open':None,'tags':row['tags'] or '','description':row['description'] or ''})
  return result

 def everything_search_worker(self,token,term,mode,root):
  temp_csv=None
  try:
   local_exe,cli,instance,data,root=self.prepare_everything_search(root)
   temp_csv=data/f'search-{secrets.token_hex(8)}.csv'
   args=[str(cli),'-instance',instance,'-timeout','20000','-path',str(root),'-full-path','-count','10000','-export-csv',str(temp_csv),'-utf8-bom']
   search_text=term
   if mode=='الامتداد':
    extension=term.strip().lower().lstrip('*.')
    search_text='ext:'+extension if extension else ''
   elif mode in ('الكل','المسار'):
    args.append('-match-path')
   if search_text:args.extend(['-search',search_text])
   result=subprocess.run(args,cwd=str(data),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=28,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),check=False)
   if result.returncode not in (0,9):
    detail=result.stderr.decode('utf-8','replace').strip()[:180] if result.stderr else f'رمز الخطأ {result.returncode}'
    raise RuntimeError(detail or 'تعذر الاتصال بمحرك البحث')
   paths=[]
   if temp_csv.is_file():
    root_text=os.path.normcase(str(root))
    with temp_csv.open('r',encoding='utf-8-sig',errors='replace',newline='') as f:
     for row in csv.reader(f):
      for value in row:
       value=value.strip().strip('"')
       if not value or not os.path.isabs(value):continue
       try:
        p=Path(value).resolve()
        if os.path.commonpath((root_text,os.path.normcase(str(p))))!=root_text:continue
       except (OSError,ValueError):continue
       if p.is_file() and not is_task_internal_artifact(p):paths.append(p)
       break
   with connect() as c:indexed=c.execute("select f.*,group_concat(t.tag, ' ') tags from files f left join tags t on t.path=f.path where f.project=? group by f.path",(root.name,)).fetchall()
   by_path={os.path.normcase(r['path']):dict(r) for r in indexed};rows=[];seen=set()
   for p in paths:
    key=os.path.normcase(str(p))
    if key in seen:continue
    seen.add(key);item=by_path.get(key)
    if item is None:
     try:st=p.stat();rel=p.relative_to(root).as_posix()
     except (OSError,ValueError):continue
     item={'path':str(p),'project':root.name,'rel':rel,'name':p.name,'ext':p.suffix.lower(),'size':st.st_size,'mtime':st.st_mtime,'last_open':None,'tags':''}
    rows.append(item)
   if mode=='الكل':
    for r in indexed:
     item=dict(r)
     if self.search_row_matches(item,term,'الهاشتاج') and os.path.normcase(item['path']) not in seen:
      seen.add(os.path.normcase(item['path']));rows.append(item)
   if mode=='الكل':
    for item in self.search_task_documents(self.project or root.name,term):
     key=os.path.normcase(item['path'])
     if key not in seen:seen.add(key);rows.append(item)
   rows=[r for r in rows if self.search_row_matches(r,term,mode)]
   note=f'محرك Everything · {len(rows):,} نتيجة داخل هذا المشروع'
   if len(rows)>=10000:note+=' · يعرض أول 10,000 نتيجة'
   self.searchq.put((token,rows,note))
  except Exception as exc:
   rows=[]
   try:
    with connect() as c:rows=[dict(r) for r in c.execute("select f.*,group_concat(t.tag, ' ') tags from files f left join tags t on t.path=f.path where f.project=? group by f.path",(root.name,)).fetchall()]
    rows=[r for r in rows if not is_task_internal_artifact(r['path'])]
    rows.extend(self.search_task_documents(self.project or root.name,term) if mode=='الكل' else [])
    rows=[r for r in rows if self.search_row_matches(r,term,mode)]
   except Exception:rows=[]
   self.searchq.put((token,rows,f'بحث محلي احتياطي · محرك Everything غير متاح: {str(exc)[:100]}'))
  finally:
   if temp_csv:
    try:temp_csv.unlink(missing_ok=True)
    except OSError:pass

 def render_search_results(self,*_):
  if not hasattr(self,'search_nb') or not self.search_nb.winfo_exists():return
  term=self.search_query.get().strip().casefold();mode=self.search_mode.get();rows=[dict(r) for r in getattr(self,'search_cache',[])]
  self.search_serial+=1;token=self.search_serial
  if self.search_future and not self.search_future.done():self.search_future.cancel()
  if term and mode!='الهاشتاج':
   self.search_status.set('جارٍ البحث بمحرك Everything داخل المشروع…')
   self.search_future=self.search_executor.submit(self.everything_search_worker,token,term,mode,self.root.resolve())
   return
  if term:
   rows=[r for r in rows if self.search_row_matches(r,term,mode)]
  self.render_search_rows(rows,'الفهرس المحلي'+(' · بحث بالهاشتاج' if term else ''))

 def render_search_rows(self,rows,source_note=''):
  if not hasattr(self,'search_nb') or not self.search_nb.winfo_exists():return
  term=self.search_query.get().strip();mode=self.search_mode.get()
  rows=[dict(r) for r in rows]
  
  try:
   with connect() as c:
    linked_rows = c.execute("SELECT path1 FROM file_links UNION SELECT path2 FROM file_links").fetchall()
    linked_paths_set = {os.path.normcase(str(Path(r[0]).resolve())) for r in linked_rows if r[0]}
    fav_rows = c.execute("SELECT path FROM favorites WHERE project=?", (self.project,)).fetchall()
    favorite_paths_set = {os.path.normcase(str(Path(r[0]).resolve())) for r in fav_rows if r[0]}
  except Exception:
   linked_paths_set = set()
   favorite_paths_set = set()

  kinds=sorted({classify(r.get('ext') or '') for r in rows},key=lambda x:(x not in ('لوحات CAD','PDF','Excel','Word','الصور'),x.casefold()))
  labels=['كل النتائج']+kinds
  if self.search_type not in labels:self.search_type='كل النتائج'
  self.search_rendering=True
  for tab in self.search_nb.tabs():self.search_nb.forget(tab)
  self.search_views={};self.search_tab_types={}
  for kind in labels:
   subset=rows if kind=='كل النتائج' else [r for r in rows if classify(r.get('ext') or '')==kind]
   title=f'{kind} · {len(subset):,}';frame=tk.Frame(self.search_nb,bg='white');frame.grid_rowconfigure(0,weight=1);frame.grid_columnconfigure(0,weight=1);self.search_nb.add(frame,text=title,image=self.file_icon_image(self.type_icon_path(kind)),compound='left');tree=self.make_list(frame);tree.grid(row=0,column=0,sticky='nsew');ybar=ttk.Scrollbar(frame,orient='vertical',command=tree.yview);ybar.grid(row=0,column=1,sticky='ns');xbar=ttk.Scrollbar(frame,orient='horizontal',command=tree.xview);xbar.grid(row=1,column=0,sticky='ew');tree.configure(yscrollcommand=ybar.set,xscrollcommand=xbar.set)
   for r in sorted(subset,key=lambda x:(self.search_sort_key(x),str(x.get('rel') or '').casefold()),reverse=self.sort_desc):
    p_str = str(r['path'])
    rowtag=self.file_row_tag(p_str)
    if rowtag.startswith('file_ext_'):tree.tag_configure(rowtag,background='#ffffff')
    norm_p = os.path.normcase(str(Path(p_str).resolve()))
    badges = []
    if norm_p in favorite_paths_set: badges.append('★')
    if norm_p in linked_paths_set: badges.append('🔗')
    name_txt = '    ' + (' '.join(badges) + ' ' if badges else '') + str(r.get('name') or '')
    opened_raw = r.get('last_open')
    opened_fmt = (' ' + str(opened_raw)[:16] + ' ') if opened_raw else '—'
    mtime_fmt = ' ' + stamp(r.get('mtime') or 0) + ' '
    tree.insert('','end',iid=p_str,values=(name_txt,'☐',r.get('ext') or 'ملف',sizefmt(r.get('size') or 0),mtime_fmt,opened_fmt,tag_badges(r.get('tags') or ''),r.get('rel') or ''),image=self.file_icon_image(p_str),tags=(rowtag,))
   tree.bind('<Double-1>',lambda e,tr=tree:self.open_file(Path(tr.selection()[0])) if tr.selection() else None)
   self.search_views[title]=tree;self.search_tab_types[title]=kind
   if kind==self.search_type:self.search_nb.select(frame)
  self.search_rendering=False
  self.search_status.set(f'{len(rows):,} نتيجة في {self.project} · {source_note} · بحث في {mode.lower()}'+(f' عن «{term}»' if term else ''))
  self.title(f'Rasd | بحث {len(rows):,} نتيجة | {self.project}')

 def search_sort_key(self,r):
  fields={'name':str(r.get('name') or '').casefold(),'type':str(r.get('ext') or '').casefold(),'size':r.get('size') or 0,'mtime':r.get('mtime') or 0,'opened':r.get('last_open') or '', 'tags':str(r.get('tags') or '').casefold(),'path':str(r.get('rel') or '').casefold()}
  return fields.get(self.sort_col,str(r.get('name') or '').casefold())

 def schedule_search_results(self,*_):
  if getattr(self,'search_job',None):
   try: self.after_cancel(self.search_job)
   except tk.TclError: pass
  if getattr(self,'search_history_job',None):
   try: self.after_cancel(self.search_history_job)
   except tk.TclError: pass
  self.search_job=self.after(130,self.render_search_results)
  self.search_history_job=self.after(900,self.record_search_history)