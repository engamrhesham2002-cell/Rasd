class App(tk.Tk):
 def __init__(self):
  super().__init__();self.title('Rasd | مدير ملفات المشاريع');self.geometry('720x600');self.minsize(720,600);self.configure(bg='#e8edf1');self.project='';self.root=None;self.scanq=queue.Queue();self.previewq=queue.Queue();self.searchq=queue.Queue();self.updateq=queue.Queue();self.preview_token=0;self.preview_executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='office-preview');self.cad_preview_executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='office-cad-preview');self.search_executor=ThreadPoolExecutor(max_workers=2,thread_name_prefix='office-search');self.update_executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='rasd-update');self._update_check_running=False;self._update_install_on_close=False;self._update_download_dialog=None;self.cad_preview_process=None;self.preview_future=None;self.search_future=None;self.search_serial=0;self.search_engine_lock=threading.Lock();self.preview_cache=OrderedDict();self.backstack=[];self.forwardstack=[];self.search_job=None;self.everything_hwnd=None;self.everything_windows={};self.everything_proc=None;self.everything_key=None;self.everything_instance=None;self.everything_data=None;self.everything_exe=None;self.everything_cli=None;self.everything_root=None;self.everything_attempts=0;self.watch_root=None;self.watch_stop=threading.Event();self.scan_lock=threading.Lock();self.sort_col='name';self.sort_desc=False;self.opened_sort_col='opened';self.opened_sort_desc=True;self.discipline='الكل';self.index_total=0;self.index_errors=0;self.preview_page=0;self.preview_zoom=1.0;self.view_mode='files';self._home_refresh_job=None;self.bind('<Configure>',self.schedule_home_refresh,add='+');self._set_window_icon();self.protocol('WM_DELETE_WINDOW',self.close_app);self.setup_style();self.show_lock_screen() if self.password_enabled() else self.show_welcome();self._poll_after_id=self.after(150,self.poll_queue)
  if UPDATE_FAILURE.is_file():
   try:self.after(900,lambda:self._show_update_failure(UPDATE_FAILURE.read_text(encoding='utf-8',errors='replace')))
   except Exception:pass
  if not self.password_enabled():self.after(2200,self.check_for_updates)

 def _set_window_icon(self):
  try:
   icon_path=Path(getattr(sys,'_MEIPASS',BASE))/'Assets'/'rasd_logo.png'
   with Image.open(icon_path) as source:
    self.app_icon=ImageTk.PhotoImage(source.convert('RGBA').resize((64,64),Image.Resampling.LANCZOS))
   self.iconphoto(True,self.app_icon)
  except Exception:pass

 def setup_style(self):
  s=ttk.Style(self);s.theme_use('clam')
  s.configure('Treeview',rowheight=34,font=('Segoe UI',10),background='#f5f7f8',fieldbackground='#f5f7f8',foreground='#243746',borderwidth=0)
  s.configure('Treeview.Heading',font=('Segoe UI',9,'bold'),background='#dfe7ec',foreground='#19394e',padding=(7,9),relief='flat')
  s.map('Treeview',background=[('selected','#d9eff0')],foreground=[('selected','#102c3d')])
  s.configure('TNotebook',background='#e8edf1',borderwidth=0,tabmargins=(0,0,0,0))
  s.configure('TNotebook.Tab',font=('Segoe UI',9,'bold'),padding=(12,8),background='#e4ebef',foreground='#526b7c')
  s.map('TNotebook.Tab',background=[('selected','#ffffff')],foreground=[('selected','#087e8b')])
  s.configure('Toolbutton',font=('Segoe UI',9,'bold'),padding=(10,6),background='#e6edf1',foreground='#526b7c',borderwidth=0)
  s.map('Toolbutton',background=[('selected','#0d8190'),('active','#d5e9eb')],foreground=[('selected','#ffffff'),('active','#19394e')])
  s.configure('TButton',font=('Segoe UI',9),padding=(8,6),background='#ffffff',foreground='#28465a',borderwidth=0,relief='flat')
  s.map('TButton',background=[('active','#e3f0f1'),('pressed','#d1e7e9')],foreground=[('active','#087e8b')])
  s.configure('Office.TCombobox',font=('Segoe UI',9),padding=(8,6),fieldbackground='#ffffff',background='#ffffff',foreground='#19394e',arrowcolor='#0b7785',borderwidth=0,relief='flat')
  s.map('Office.TCombobox',fieldbackground=[('readonly','#ffffff')],foreground=[('readonly','#19394e')],selectbackground=[('readonly','#dcebed')],selectforeground=[('readonly','#19394e')])
  s.configure('Office.TMenubutton',font=('Segoe UI',9),padding=(8,6),background='#ffffff',foreground='#19394e',arrowcolor='#0b7785',borderwidth=0,relief='flat')
  s.configure('TEntry',padding=(8,7),fieldbackground='#ffffff',foreground='#19394e')
  s.configure('TCombobox',padding=(5,4),fieldbackground='#ffffff',foreground='#19394e')

 def clear(self):
  for w in self.winfo_children():w.destroy()

 def password_record(self):
  with connect() as c:values={r['key']:r['value'] for r in c.execute("select key,value from app_settings where key in ('password_salt','password_hash','password_iterations')")}
  if not all(k in values for k in ('password_salt','password_hash','password_iterations')):return None
  try:return values['password_salt'],values['password_hash'],int(values['password_iterations'])
  except (TypeError,ValueError):return None

 def password_enabled(self):return self.password_record() is not None

 def verify_password(self,password):
  record=self.password_record()
  if not record:return False
  salt,digest,iterations=record
  try:candidate=hashlib.pbkdf2_hmac('sha256',password.encode('utf-8'),bytes.fromhex(salt),iterations).hex()
  except (ValueError,TypeError):return False
  return secrets.compare_digest(candidate,digest)

 def store_password(self,password):
  salt=secrets.token_bytes(16);iterations=310000;digest=hashlib.pbkdf2_hmac('sha256',password.encode('utf-8'),salt,iterations).hex()
  with connect() as c:c.executemany('insert into app_settings(key,value) values(?,?) on conflict(key) do update set value=excluded.value',[('password_salt',salt.hex()),('password_hash',digest),('password_iterations',str(iterations))])

 def clear_password(self):
  with connect() as c:c.execute("delete from app_settings where key in ('password_salt','password_hash','password_iterations')")

 def show_lock_screen(self):
  self.title('Rasd Login')
  self.clear();self.unbind('<Return>');self.title('Rasd | فتح البرنامج');self.configure(bg='#e8edf1');self.geometry('560x400');self.minsize(520,360)
  self.geometry(f'560x400+{max(0,(self.winfo_screenwidth()-560)//2)}+{max(0,(self.winfo_screenheight()-400)//2)}')
  shell=tk.Frame(self,bg='#102c3d');shell.pack(fill='both',expand=True,padx=20,pady=20)
  card=tk.Frame(shell,bg='#f5f7f8',highlightbackground='#d9e4e9',highlightthickness=1);card.place(relx=.5,rely=.5,anchor='center',width=450,height=300)
  tk.Label(card,text='RASD',bg='#f5f7f8',fg='#102c3d',font=('Segoe UI',19,'bold')).pack(pady=(32,8))
  tk.Label(card,text='أدخل كلمة المرور لفتح البرنامج',bg='#f5f7f8',fg='#526b7c',font=('Segoe UI',11)).pack(pady=(0,18))
  self.login_status=tk.StringVar(value='')
  self.password_entry=ttk.Entry(card,show='●',font=('Segoe UI',12),justify='center');self.password_entry.pack(fill='x',padx=38,ipady=5)
  tk.Button(card,text='فتح البرنامج',command=self.unlock_app,bg='#167f8c',fg='white',activebackground='#106b76',activeforeground='white',relief='flat',font=('Segoe UI',10,'bold'),padx=18,pady=8,cursor='hand2').pack(pady=(15,5))
  tk.Label(card,textvariable=self.login_status,bg='#f5f7f8',fg='#bd4856',font=('Segoe UI',9)).pack()
  tk.Label(card,text='كلمة المرور تمنع الدخول للبرنامج فقط؛ ملفات المشروع تظل ملفات عادية.',bg='#f5f7f8',fg='#758692',font=('Segoe UI',8),wraplength=400).pack(side='bottom',pady=14)
  self.bind('<Return>',lambda e:(self.unlock_app(),'break'));self.password_entry.focus_set()

 def unlock_app(self):
  if self.verify_password(self.password_entry.get()):
   self.unbind('<Return>');self.show_welcome();self.animate_window_in();self.after(1800,self.check_for_updates)
  else:
   self.login_status.set('كلمة المرور غير صحيحة. حاول مرة أخرى.');self.password_entry.delete(0,'end');self.password_entry.focus_set()

 def manage_password(self):
  enabled=self.password_enabled();dialog=tk.Toplevel(self);dialog.title('حماية البرنامج');dialog.configure(bg='#eef2f5');dialog.resizable(False,False);dialog.transient(self);dialog.grab_set()
  frame=tk.Frame(dialog,bg='white',highlightbackground='#d7e1e6',highlightthickness=1);frame.pack(fill='both',expand=True,padx=14,pady=14)
  tk.Label(frame,text='حماية البرنامج',bg='white',fg='#19394e',font=('Segoe UI',14,'bold')).pack(anchor='e',padx=18,pady=(16,5))
  tk.Label(frame,text=('الحماية مفعلة. أدخل الحالية للتغيير أو الإلغاء.' if enabled else 'فعّل كلمة مرور اختيارية عند بدء البرنامج.'),bg='white',fg='#617789',font=('Segoe UI',9),justify='right').pack(anchor='e',padx=18,pady=(0,12))
  fields=tk.Frame(frame,bg='white');fields.pack(fill='x',padx=18);entries={}
  specs=([('old','كلمة المرور الحالية')] if enabled else [])+[('new','كلمة مرور جديدة'),('confirm','تأكيد كلمة المرور')]
  for key,label in specs:
   tk.Label(fields,text=label,bg='white',fg='#435b6d',font=('Segoe UI',9)).pack(anchor='e',pady=(5,2))
   entry=ttk.Entry(fields,show='●',justify='right',width=38);entry.pack(fill='x',ipady=3);entries[key]=entry
  status=tk.StringVar(value='')
  tk.Label(frame,textvariable=status,bg='white',fg='#bd4856',font=('Segoe UI',9),justify='right').pack(anchor='e',padx=18,pady=(7,0))
  actions=tk.Frame(frame,bg='white');actions.pack(fill='x',padx=18,pady=(8,14))
  def save():
   if enabled and not self.verify_password(entries['old'].get()):status.set('كلمة المرور الحالية غير صحيحة.');return
   password=entries['new'].get();confirm=entries['confirm'].get()
   if len(password)<6:status.set('استخدم 6 أحرف على الأقل.');return
   if password!=confirm:status.set('تأكيد كلمة المرور غير مطابق.');return
   self.store_password(password);messagebox.showinfo('حماية البرنامج','تم حفظ كلمة المرور. سيطلبها البرنامج عند تشغيله.',parent=dialog);dialog.destroy()
  def disable():
   if not self.verify_password(entries['old'].get()):status.set('كلمة المرور الحالية غير صحيحة.');return
   self.clear_password();messagebox.showinfo('حماية البرنامج','تم إلغاء كلمة المرور.',parent=dialog);dialog.destroy()
  tk.Button(actions,text=('تغيير كلمة المرور' if enabled else 'تفعيل كلمة المرور'),command=save,bg='#167f8c',fg='white',activebackground='#106b76',activeforeground='white',relief='flat',font=('Segoe UI',9,'bold'),padx=12,pady=6,cursor='hand2').pack(side='right',padx=3)
  if enabled:ttk.Button(actions,text='إلغاء الحماية',command=disable).pack(side='right',padx=3)
  ttk.Button(actions,text='إغلاق',command=dialog.destroy).pack(side='left',padx=3)
  if enabled:entries['old'].focus_set()
  else:entries['new'].focus_set()
  dialog.update_idletasks();dialog.geometry(f'+{self.winfo_rootx()+(self.winfo_width()-dialog.winfo_width())//2}+{self.winfo_rooty()+(self.winfo_height()-dialog.winfo_height())//2}')

 def header(self,title):
  h=tk.Frame(self,bg='#102c3d',height=66);h.pack(fill='x')
  brand=tk.Frame(h,bg='#102c3d');brand.pack(side='left',padx=18,pady=5)
  try:
   with Image.open(Path(getattr(sys,'_MEIPASS',BASE))/'Assets'/'rasd_logo.png') as source:
    self.header_icon=ImageTk.PhotoImage(source.convert('RGBA').resize((38,38),Image.Resampling.LANCZOS))
   tk.Label(brand,image=self.header_icon,bg='#102c3d').pack(side='left',padx=(0,8))
  except Exception:pass
  brand_text=tk.Frame(brand,bg='#102c3d');brand_text.pack(side='left')
  tk.Label(brand_text,text='RASD',font=('Segoe UI',17,'bold'),fg='white',bg='#102c3d').pack(anchor='w')
  tk.Label(brand_text,text='Made by ENG. Amr Hesham',font=('Segoe UI',8),fg='#a9c3d0',bg='#102c3d').pack(anchor='w')
  tk.Label(h,text=title,font=('Segoe UI',14,'bold'),fg='#d8e7ef',bg='#102c3d').pack(side='right',padx=22);return h

 def show_welcome(self):
  self.title('Rasd | Start')
  self.clear();self.project='';self.configure(bg='#c8d2d8');self.geometry('720x600');self.minsize(600,520)
  try:self.state('normal')
  except tk.TclError:pass
  art_path=Path(getattr(sys,'_MEIPASS',BASE))/'Assets'/'welcome_art.jpg'
  bg=tk.Frame(self,bg='#c8d2d8');bg.pack(fill='both',expand=True)
  try:
   with Image.open(art_path) as src:
    backdrop=ImageOps.fit(src.convert('RGB'),(720,600),method=Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(10))
    backdrop=Image.blend(backdrop,Image.new('RGB',(720,600),'#e5edf1'),.42)
   self._welcome_background_source=backdrop.copy();self.welcome_background_photo=ImageTk.PhotoImage(backdrop)
   self._welcome_background_label=tk.Label(bg,image=self.welcome_background_photo,borderwidth=0,bg='#c8d2d8');self._welcome_background_label.place(x=0,y=0,relwidth=1,relheight=1)
   def resize_welcome_background(event):
    if event.width<2 or event.height<2:return
    resized=ImageOps.fit(self._welcome_background_source,(event.width,event.height),method=Image.Resampling.LANCZOS)
    self.welcome_background_photo=ImageTk.PhotoImage(resized);self._welcome_background_label.configure(image=self.welcome_background_photo)
   bg.bind('<Configure>',resize_welcome_background)
  except Exception:pass
  card=tk.Frame(bg,bg='#edf2f5',highlightbackground='#ffffff',highlightthickness=2);card.place(relx=.5,rely=.5,anchor='center',relwidth=.86,relheight=.88)
  brand=tk.Frame(card,bg='#edf2f5');brand.pack(pady=(12,0))
  try:
   with Image.open(Path(getattr(sys,'_MEIPASS',BASE))/'Assets'/'rasd_logo.png') as source:self.welcome_logo=ImageTk.PhotoImage(source.convert('RGBA').resize((40,40),Image.Resampling.LANCZOS))
   tk.Label(brand,image=self.welcome_logo,bg='#edf2f5').pack(side='left',padx=(0,8))
  except Exception:pass
  brand_stack=tk.Frame(brand,bg='#edf2f5');brand_stack.pack(side='left',anchor='w')
  tk.Label(brand_stack,text='RASD',font=('Segoe UI',17,'bold'),fg='#102c3d',bg='#edf2f5').pack(anchor='w')
  tk.Label(brand_stack,text='Made by ENG. Amr Hesham',font=('Segoe UI',8),fg='#718491',bg='#edf2f5').pack(anchor='w')
  tk.Label(card,text='تعالى نعمل واحد ... مشروع جامد',font=('Segoe UI',18,'bold'),fg='#187db2',bg='#edf2f5',justify='center',wraplength=570).pack(fill='x',padx=18,pady=(8,8))
  image_holder=tk.Frame(card,bg='white',highlightbackground='#d8e2e8',highlightthickness=1);image_holder.pack(fill='both',expand=True,padx=24,pady=(0,78))
  try:
   with Image.open(art_path) as src:art=ImageOps.fit(src.convert('RGB'),(650,380),method=Image.Resampling.LANCZOS)
   self.welcome_photo=ImageTk.PhotoImage(art);tk.Label(image_holder,image=self.welcome_photo,bg='white',borderwidth=0).pack(fill='both',expand=True,padx=4,pady=4)
  except Exception:tk.Label(image_holder,text='👷',font=('Segoe UI Emoji',90),bg='white').pack(expand=True)
  pill=Image.new('RGBA',(300,64),(0,0,0,0));pd=ImageDraw.Draw(pill);pd.rounded_rectangle((8,8,292,60),radius=27,fill=(70,92,111,45));pd.rounded_rectangle((5,2,295,54),radius=27,fill=(249,252,254,250),outline=(231,239,245,255),width=2)
  self.start_photo=ImageTk.PhotoImage(pill);start=tk.Canvas(card,width=300,height=64,bg='#edf2f5',highlightthickness=0,cursor='hand2');start.create_image(150,32,image=self.start_photo);start.create_text(150,27,text='Start',font=('Segoe UI',18,'bold'),fill='#263946');start.bind('<Button-1>',lambda e:self.enter_app());start.place(relx=.5,rely=.97,anchor='s');self.bind('<Return>',lambda e:self.enter_app())

 def enter_app(self):
  self.unbind('<Return>');self.set_workspace_geometry();self.show_home()

 def set_workspace_geometry(self):
  screen_w=max(720,self.winfo_screenwidth());screen_h=max(520,self.winfo_screenheight())
  width=min(1440,screen_w-40);height=min(880,screen_h-80)
  min_w=min(1050,width);min_h=min(650,height)
  self.minsize(min_w,min_h);self.geometry(f'{width}x{height}+{max(0,(screen_w-width)//2)}+{max(0,(screen_h-height)//2)}')

 def animate_window_in(self):
  try:
   if getattr(self,'_fade_job',None):self.after_cancel(self._fade_job)
   self.wm_attributes('-alpha',0.94)
   def step(value=94):
    value=min(100,value+2);self.wm_attributes('-alpha',value/100)
    if value<100:self._fade_job=self.after(14,lambda:step(value))
   self._fade_job=self.after(14,lambda:step())
  except Exception:pass

 def show_home(self):
  if hasattr(self,'watch_stop'):self.watch_stop.set();self.watch_root=None
  self.clear();self.project='';self.configure(bg='#eef3f7')
  top=tk.Frame(self,bg='#eef2f5',height=58,highlightbackground='#e0e8ed',highlightthickness=1);top.pack(fill='x');top.pack_propagate(False)
  brand=tk.Frame(top,bg='#eef2f5');brand.pack(side='left',padx=24)
  try:
   with Image.open(Path(getattr(sys,'_MEIPASS',BASE))/'Assets'/'rasd_logo.png') as source:
    self.brand_icon=ImageTk.PhotoImage(source.convert('RGBA').resize((32,32),Image.Resampling.LANCZOS))
   tk.Label(brand,image=self.brand_icon,bg='#eef2f5').pack(side='left',padx=(0,8))
  except Exception:tk.Label(brand,text='◉',font=('Segoe UI Symbol',22,'bold'),fg='#1595a5',bg='#eef2f5').pack(side='left',padx=(0,8))
  tk.Label(brand,text='RASD',font=('Segoe UI',15,'bold'),fg='#253c4b',bg='#eef2f5').pack(side='left')
  tk.Label(brand,text='Made by ENG. Amr Hesham',font=('Segoe UI',8),fg='#718491',bg='#eef2f5').pack(side='left',padx=(9,0),pady=(6,0))
  tk.Button(top,text='📁  مجلد Log',command=lambda:os.startfile(str(LOG)),bg='#eef2f5',fg='#607786',activebackground='#e9f0f4',relief='flat',font=('Segoe UI',9),padx=10,cursor='hand2').pack(side='right',padx=(4,18))
  tk.Button(top,text='↻  التحديثات',command=lambda:self.check_for_updates(manual=True),bg='#eef2f5',fg='#607786',activebackground='#e9f0f4',relief='flat',font=('Segoe UI',9),padx=10,cursor='hand2').pack(side='right',padx=4)
  tk.Button(top,text='⚙  حماية البرنامج',command=self.manage_password,bg='#eef2f5',fg='#607786',activebackground='#e9f0f4',relief='flat',font=('Segoe UI',9),padx=10,cursor='hand2').pack(side='right',padx=4)
  tk.Button(top,text='＋ مشروع جديد',command=self.new_project,bg='#3478e5',fg='white',activebackground='#2868ce',activeforeground='white',relief='flat',font=('Segoe UI',9,'bold'),padx=13,pady=7,cursor='hand2').pack(side='right',padx=5)
  tk.Label(top,text='مساحة المشاريع',font=('Segoe UI',9),fg='#617889',bg='#eef2f5').pack(side='right',padx=10)
  wrap=tk.Frame(self,bg='#eef3f7');wrap.pack(fill='both',expand=True,padx=42,pady=(12,22))
  controls=tk.Frame(wrap,bg='#eef3f7');controls.pack(fill='x',pady=(3,12))
  self.project_search=tk.StringVar(value='ابحث عن مشروع')
  search_wrap=tk.Frame(controls,bg='white',highlightbackground='#d8e1e7',highlightthickness=1);search_wrap.pack(side='left',fill='x',expand=True,padx=(0,12))
  tk.Label(search_wrap,text='⌕',font=('Segoe UI',17),fg='#8496a3',bg='white').pack(side='left',padx=(11,3))
  entry=tk.Entry(search_wrap,textvariable=self.project_search,bg='white',fg='#344c5b',insertbackground='#3478e5',relief='flat',font=('Segoe UI',10),justify='left');entry.pack(side='left',fill='x',expand=True,ipady=8,padx=6)
  entry.bind('<FocusIn>',lambda e:entry.delete(0,'end') if entry.get()=='ابحث عن مشروع' else None);entry.bind('<FocusOut>',lambda e:entry.insert(0,'ابحث عن مشروع') if not entry.get() else None)
  self.home_filter_mode=getattr(self,'home_filter_mode','all');self.home_filter_buttons={}
  for label,command in [('الكل','all'),('المفضلة','favorites'),('آخر زيارة','visited'),('أضيف حديثاً','added')]:
   active=command==self.home_filter_mode
   b=tk.Button(controls,text=label,command=lambda c=command:self.home_project_filter(c),bg='#3478e5' if active else '#e8eef3',fg='white' if active else '#526b7b',activebackground='#2868ce',relief='flat',font=('Segoe UI',9,'bold' if active else 'normal'),padx=12,pady=8,cursor='hand2');b.pack(side='left',padx=3);self.home_filter_buttons[command]=b
  self.home_sort_button=tk.Button(controls,text='☷  ترتيب المشاريع',command=self.toggle_project_sort,bg='#eef3f7',fg='#527083',activebackground='#e2ebf0',relief='flat',font=('Segoe UI',9),padx=10,pady=8,cursor='hand2',state='disabled' if self.home_filter_mode in ('visited','added') else 'normal');self.home_sort_button.pack(side='right',padx=(7,0))
  project_total=sum(1 for p in LOG.iterdir() if p.is_dir() and not p.name.startswith('.') and is_project_path(p))
  with connect() as c:
   indexed_total=c.execute('select count(*) from files').fetchone()[0]
   favorite_total=c.execute('select count(*) from favorites').fetchone()[0]
  summary=tk.Frame(wrap,bg='#eef3f7');summary.pack(fill='x',pady=(0,7))
  for title,value,accent in [('المشاريع',f'{project_total:,}','#3285c7'),('الملفات المفهرسة',f'{indexed_total:,}','#1a9a83'),('المفضلة',f'{favorite_total:,}','#d69637')]:
   tile=tk.Frame(summary,bg='white',highlightbackground='#dbe4e9',highlightthickness=1);tile.pack(side='right',fill='x',expand=True,padx=(5,0))
   tk.Label(tile,text=value,bg='white',fg=accent,font=('Segoe UI',16,'bold')).pack(anchor='e',padx=12,pady=(6,0))
   tk.Label(tile,text=title,bg='white',fg='#718592',font=('Segoe UI',8)).pack(anchor='e',padx=12,pady=(0,6))
  self.project_count_label=tk.Label(wrap,text='',bg='#eef3f7',fg='#82919b',font=('Segoe UI',8));self.project_count_label.pack(anchor='e',pady=(0,1))
  self.cards=tk.Frame(wrap,bg='#eef3f7');self.cards.pack(fill='both',expand=True,pady=1);self.project_card_photos=[]
  self.project_search.trace_add('write',lambda *_:self.render_projects());self.render_projects();self.animate_window_in()

 def home_project_filter(self,mode):
  self.home_filter_mode={'recent':'visited'}.get(mode,mode)
  if getattr(self,'home_sort_button',None):self.home_sort_button.configure(state='disabled' if self.home_filter_mode in ('visited','added') else 'normal')
  for key,button in getattr(self,'home_filter_buttons',{}).items():
   active=key==self.home_filter_mode;button.configure(bg='#3478e5' if active else '#e8eef3',fg='white' if active else '#526b7b',font=('Segoe UI',9,'bold' if active else 'normal'))
  self.render_projects()

 def toggle_project_sort(self):
  self.home_sort_mode='recent' if getattr(self,'home_sort_mode','name')=='name' else 'name'
  self.render_projects()

 def schedule_home_refresh(self,event=None):
  # Defer project-card rebuilding until the native window resize has settled.
  if event is not None and getattr(event,'widget',self) is not self:return
  job=getattr(self,'_home_refresh_job',None)
  if job:
   try:self.after_cancel(job)
   except tk.TclError:pass
  try:self._home_refresh_job=self.after(240,self.refresh_home_after_resize)
  except tk.TclError:self._home_refresh_job=None

 def refresh_home_after_resize(self):
  self._home_refresh_job=None
  cards=getattr(self,'cards',None)
  try:
   if not getattr(self,'project','') and cards and cards.winfo_exists() and cards.winfo_ismapped():
    self.after_idle(self.render_projects)
  except tk.TclError:pass

 def render_projects(self):
  for w in self.cards.winfo_children():w.destroy()
  with connect() as c:counts={r['project']:(r['n'],r['latest']) for r in c.execute('select project,count(*) n,max(mtime) latest from files group by project')}
  projects=[p for p in LOG.iterdir() if p.is_dir() and not p.name.startswith('.') and is_project_path(p)]
  mode=getattr(self,'home_filter_mode','all')
  if mode=='favorites':
   with connect() as c:names={r['project'] for r in c.execute('select distinct project from favorites')}
   projects=[p for p in projects if p.name in names]
  elif mode=='visited':
   with connect() as c:visited=[r['project'] for r in c.execute('select project from project_visits order by last_visit desc limit 8')]
   by_name={p.name:p for p in projects};projects=[by_name[name] for name in visited if name in by_name]
  elif mode=='added':
   projects=sorted(projects,key=lambda p:(p.stat().st_ctime if p.exists() else 0),reverse=True)[:8]
  if mode not in ('visited','added'):
   projects=sorted(projects,key=(lambda p:p.stat().st_mtime) if getattr(self,'home_sort_mode','name')=='recent' else (lambda p:p.name.lower()),reverse=getattr(self,'home_sort_mode','name')=='recent')
  query=getattr(self,'project_search',tk.StringVar(value='')).get().strip().casefold()
  if query and query!='ابحث عن مشروع':projects=[p for p in projects if query in p.name.casefold()]
  self.project_card_photos=[]
  if hasattr(self,'project_count_label'):self.project_count_label.configure(text=f'{len(projects)} مشروع')
  if not projects:
   empty=tk.Frame(self.cards,bg='white',highlightbackground='#d8e2ea',highlightthickness=1);empty.pack(fill='x',pady=25)
   tk.Label(empty,text='ابدأ بمشروعك الأول',font=('Segoe UI',17,'bold'),fg='#15374d',bg='white').pack(anchor='e',padx=24,pady=(22,4))
   tk.Label(empty,text='أنشئ مشروعًا جديدًا أو انسخ مجلد مشروعك إلى مجلد Log.',font=('Segoe UI',11),fg='#617789',bg='white').pack(anchor='e',padx=24,pady=(0,22));return
  screen_width=max(720,self.winfo_screenwidth());window_width=min(1440,screen_width-40);card_area_width=max(280,window_width-84);columns=max(1,min(4,card_area_width//280))
  for col in range(max(columns,getattr(self,'project_columns',0))):self.cards.grid_columnconfigure(col,weight=1 if col<columns else 0,uniform='project-card' if col<columns else '')
  self.project_columns=columns
  for i,p in enumerate(projects):
   indexed=counts.get(p.name);n=indexed[0] if indexed else None;count_text=f'{n:,} ملف' if n is not None else 'جارٍ تجهيز الفهرس'
   try:
    child_count=sum(1 for x in p.iterdir() if x.is_dir() and not x.name.startswith('.'))
    latest=indexed[1] if indexed and indexed[1] else p.stat().st_mtime;modified=datetime.fromtimestamp(latest).strftime('%d-%m-%Y')
   except OSError:child_count=0;modified='—'
   box=tk.Frame(self.cards,bg='white',highlightbackground='#d7e1e7',highlightthickness=1,cursor='hand2');box.grid(row=i//columns,column=i%columns,sticky='nsew',padx=7,pady=7)
   image_path=None
   if image_path is None:
    try:image_path=next(x for x in p.rglob('*') if x.is_file() and x.suffix.lower() in ('.png','.jpg','.jpeg','.bmp','.tif','.tiff'))
    except (StopIteration,OSError):pass
   try:
    if image_path:
     with Image.open(image_path) as src:thumb=ImageOps.fit(src.convert('RGB'),(430,175),method=Image.Resampling.LANCZOS)
     photo=ImageTk.PhotoImage(thumb);self.project_card_photos.append(photo)
     pic=tk.Label(box,image=photo,bg='#dce8ed',borderwidth=0);pic.pack(fill='x')
    else:
     art=tk.Canvas(box,height=145,bg='#dce8ed',highlightthickness=0);art.pack(fill='x');art.create_rectangle(0,0,430,145,fill='#dce8ed',outline='');art.create_line(0,110,110,35,225,98,340,25,430,105,fill='#83b4bc',width=3);art.create_text(390,112,text='RASD  /  PROJECT',anchor='e',fill='#416a79',font=('Segoe UI',9,'bold'))
   except Exception:
    art=tk.Frame(box,bg='#dce8ed',height=145);art.pack(fill='x');art.pack_propagate(False)
   details=tk.Frame(box,bg='white');details.pack(fill='x',padx=11,pady=(9,0))
   tk.Label(details,text=p.name,font=('Segoe UI',11,'bold'),fg='#253c4b',bg='white',anchor='e').pack(anchor='e',fill='x')
   tk.Label(details,text=f'▤  {count_text}     ◷  {modified}',font=('Segoe UI',8),fg='#87949d',bg='white',anchor='e').pack(anchor='e',fill='x',pady=(4,0))
   tags=[]
   try:
    with connect() as c:tags=[r['tag'] for r in c.execute('select t.tag,count(*) n from tags t join files f on f.path=t.path where f.project=? group by t.tag order by n desc limit 3',(p.name,))]
   except Exception:pass
   tagrow=tk.Frame(box,bg='white');tagrow.pack(fill='x',padx=8,pady=(7,10))
   if tags:
    for tag in tags:tk.Label(tagrow,text='#'+tag.lstrip('#'),bg='#f0f3f5',fg='#687987',font=('Segoe UI',7),padx=6,pady=3).pack(side='left',padx=2)
   else:tk.Label(tagrow,text=f'{child_count} مجلدات',bg='#f0f3f5',fg='#687987',font=('Segoe UI',7),padx=6,pady=3).pack(side='left',padx=2)
   open_badge=tk.Label(box,text='↗',font=('Segoe UI',11,'bold'),fg='#638293',bg='white',width=2,cursor='hand2');open_badge.place(relx=.95,rely=.04,anchor='ne')
   def bind_open(widget,project=p):
    widget.bind('<Button-1>',lambda e,x=project:self.open_project(x))
    for child in widget.winfo_children():bind_open(child,project)
   bind_open(box)

 def new_project(self):
  name=simpledialog.askstring('مشروع جديد','اسم المشروع:',parent=self)
  if not name:return
  name=name.strip()
  if not name or name.startswith('.') or name in ('.','..') or name[-1:] in (' ','.') or any(ch in name for ch in '<>:"/\\|?*'):
   return messagebox.showwarning('اسم غير صالح','اكتب اسم مجلد مشروع صالحًا من دون رموز المسارات.',parent=self)
  p=LOG/name
  if p.exists():return messagebox.showwarning('موجود','يوجد مشروع بهذا الاسم.')
  p.mkdir(parents=True)
  self.log_activity('إنشاء مشروع',f'تم إنشاء المشروع «{p.name}»',path=p,project=p.name)
  self.render_projects()

 def log_activity(self,action,details,path=None,project=None,occurred_at=None):
  project=project or getattr(self,'project','')
  if not project:return
  target=str(Path(path).resolve()) if path else None
  when=occurred_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
  with connect() as c:c.execute('insert into activity_log(project,action,details,path,occurred_at) values(?,?,?,?,?)',(project,str(action),str(details),target,when))

 def open_project(self,root):
  root=Path(root).resolve()
  if not is_project_path(root) or not root.is_dir():
   return messagebox.showwarning('مسار مشروع غير مسموح','ضع مجلد المشروع داخل مجلد Log الموجود بجوار Rasd.exe.',parent=self)
  self.search_serial+=1
  self.stop_everything_instance()
  self.watch_stop.set();self.watch_stop=threading.Event();self.watch_root=None;self.root=root;self.project=root.name;self.backstack=[];self.forwardstack=[]
  self.rebase_project_index(root)
  with connect() as c:
   state=c.execute('select * from project_view_state where project=?',(self.project,)).fetchone()
   visit=c.execute('select last_visit from project_visits where project=?',(self.project,)).fetchone()
   self.visit_since=visit['last_visit'] if visit else '0000'
   c.execute('insert into project_visits(project,last_visit) values(?,?) on conflict(project) do update set last_visit=excluded.last_visit',(self.project,stamp(time.time())))
  self.log_activity('فتح مشروع',f'تم فتح المشروع «{self.project}»',path=root)
  self.mode=state['mode'] if state and state['mode'] in ('folder','project') else 'folder'
  self.folder_group=state['folder_filter'] if state and state['folder_filter'] else 'الكل'
  self.project_group=state['project_filter'] if state and state['project_filter'] else 'الكل'
  self.discipline=state['discipline'] if state else 'الكل'
  self.sort_col=state['sort_col'] if state else 'name'
  self.sort_desc=bool(state['sort_desc']) if state else False
  try:self.column_widths=json.loads(state['column_widths']) if state and state['column_widths'] else {}
  except Exception:self.column_widths={}
  self.current=root;self.preview_current_path=None
  if state and state['current_rel']:
   try:
    restored=(root/Path(state['current_rel'])).resolve();restored.relative_to(root)
    if restored.is_dir():self.current=restored
   except (OSError,ValueError,TypeError):pass
  self.build_explorer();self.animate_window_in();self.scan_summary.set('جارٍ فهرسة ملفات المشروع...');self.start_scan_progress();threading.Thread(target=self.scan_worker,args=(root,),daemon=True).start()

 def rebase_project_index(self,root):
  """Keep tags, favorites, and change history attached when the portable Log folder moves."""
  root=Path(root).resolve();project=root.name
  with connect() as c:
   rows=c.execute('select path,rel from files where project=?',(project,)).fetchall();old_roots=set()
   for row in rows:
    rel=Path(row['rel'] or '')
    if not rel.parts:continue
    old=Path(row['path'])
    for _ in rel.parts:old=old.parent
    if os.path.normcase(str(old))!=os.path.normcase(str(root)):old_roots.add(str(old))
   for old_root in old_roots:
    old_prefix=old_root.rstrip('\\/')+os.sep;prefix=os.path.normcase(old_prefix);old_root_key=os.path.normcase(old_root)
    for favorite in c.execute('select path from favorites where project=?',(project,)).fetchall():
     old_path=str(favorite['path'])
     old_key=os.path.normcase(old_path)
     if old_key==old_root_key or old_key.startswith(prefix):
      new_path=str(root) if old_key==old_root_key else str(root/old_path[len(old_prefix):])
      if c.execute('select 1 from favorites where project=? and path=?',(project,new_path)).fetchone():c.execute('delete from favorites where project=? and path=?',(project,old_path))
      else:c.execute('update favorites set path=? where project=? and path=?',(new_path,project,old_path))
    for change in c.execute('select id,path from file_changes where project=?',(project,)).fetchall():
     old_path=str(change['path'])
     if os.path.normcase(old_path).startswith(prefix):c.execute('update file_changes set path=? where id=?',(str(root/old_path[len(old_prefix):]),change['id']))
    for table in ('file_open_history','activity_log'):
     for item in c.execute(f'select id,path from {table} where project=? and path is not null',(project,)).fetchall():
      old_path=str(item['path']);old_key=os.path.normcase(old_path)
      if old_key==old_root_key or old_key.startswith(prefix):
       new_path=str(root) if old_key==old_root_key else str(root/old_path[len(old_prefix):])
       c.execute(f'update {table} set path=? where id=?',(new_path,item['id']))
   for row in rows:
    old_path=str(row['path']);target=root/Path(row['rel'] or '')
    if not target.is_file() or os.path.normcase(old_path)==os.path.normcase(str(target)):continue
    new_path=str(target);tags=[r['tag'] for r in c.execute('select tag from tags where path=?',(old_path,)).fetchall()]
    c.executemany('insert or ignore into tags(path,tag) values(?,?)',[(new_path,tag) for tag in tags]);c.execute('delete from tags where path=?',(old_path,))
    if c.execute('select 1 from files where path=?',(new_path,)).fetchone():c.execute('delete from files where path=?',(old_path,))
    else:c.execute('update files set path=? where path=?',(new_path,old_path))
    if c.execute('select 1 from favorites where project=? and path=?',(project,new_path)).fetchone():c.execute('delete from favorites where project=? and path=?',(project,old_path))
    else:c.execute('update favorites set path=? where project=? and path=?',(new_path,project,old_path))
    c.execute('update file_changes set path=? where project=? and path=?',(new_path,project,old_path))

 def watch_project_worker(self,root,stop):
  if os.name=='nt':
   try:
    kernel=ctypes.windll.kernel32;kernel.FindFirstChangeNotificationW.argtypes=[ctypes.c_wchar_p,ctypes.c_bool,ctypes.c_uint32];kernel.FindFirstChangeNotificationW.restype=ctypes.c_void_p;kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint32];kernel.WaitForSingleObject.restype=ctypes.c_uint32;kernel.FindNextChangeNotification.argtypes=[ctypes.c_void_p];kernel.FindNextChangeNotification.restype=ctypes.c_bool;kernel.FindCloseChangeNotification.argtypes=[ctypes.c_void_p];kernel.FindCloseChangeNotification.restype=ctypes.c_bool;handle=kernel.FindFirstChangeNotificationW(str(root),True,0x00000001|0x00000002|0x00000004|0x00000008|0x00000010)
    if handle and handle!=ctypes.c_void_p(-1).value:
     try:
      while not stop.is_set():
       result=kernel.WaitForSingleObject(handle,500)
       if result==0:
        if self.root==root:threading.Thread(target=self.scan_worker,args=(root,),daemon=True).start()
        if not kernel.FindNextChangeNotification(handle):break
       elif result==0xFFFFFFFF:break
     finally:kernel.FindCloseChangeNotification(handle)
     return
   except Exception:pass
  def signature():
   found=[];stack=[root]
   while stack:
    directory=stack.pop()
    try:
     with os.scandir(directory) as entries:
      for entry in entries:
       if entry.is_dir(follow_symlinks=False) and not entry.name.startswith('.'):
        try:found.append((entry.path,entry.stat(follow_symlinks=False).st_mtime_ns))
        except OSError:pass
        stack.append(Path(entry.path))
     found.append((str(directory),directory.stat().st_mtime_ns))
    except OSError:continue
   return tuple(sorted(found))
  previous=signature()
  while not stop.wait(10):
   current=signature()
   if current!=previous:
    previous=current
    if self.root==root:threading.Thread(target=self.scan_worker,args=(root,),daemon=True).start()

 def build_explorer(self):
  self.clear();h=self.header(self.project);ttk.Button(h,text='← المشاريع',command=self.show_home).pack(side='right',padx=10,pady=12)
  self.explorer_page=tk.Frame(self,bg='#e8edf1');self.explorer_page.pack(fill='both',expand=True,padx=10,pady=9)
  self.query=tk.StringVar();self.mode=getattr(self,'mode','folder');self.project_group=getattr(self,'project_group','الكل');self.local_group='محتويات هذا المجلد';self.preview_photo=None;self.view_mode='files'
  self.explorer_page.grid_rowconfigure(0,weight=1);self.explorer_page.grid_columnconfigure(0,weight=0,minsize=350);self.explorer_page.grid_columnconfigure(1,weight=1);self.explorer_page.grid_columnconfigure(2,weight=0,minsize=176)
  # RTL workspace: preview at far left, file list in the center, project navigation at far right.
  self.preview_area=tk.Frame(self.explorer_page,bg='#eef2f5',highlightbackground='#d6e0e6',highlightthickness=1,width=350);self.preview_area.grid(row=0,column=0,sticky='nsew',padx=(0,8));self.preview_area.grid_propagate(False);self.preview_area.grid_rowconfigure(1,weight=1);self.preview_area.grid_columnconfigure(0,weight=1)
  preview_head=tk.Frame(self.preview_area,bg='#dfe7ec');preview_head.grid(row=0,column=0,sticky='ew')
  tk.Label(preview_head,text='معاينة وتفاصيل',bg='#dfe7ec',fg='#19394e',font=('Segoe UI',11,'bold')).pack(side='right',padx=13,pady=10)
  self.preview_panel_close=ttk.Button(preview_head,text='×',width=3,command=self.toggle_preview_panel);self.preview_panel_close.pack(side='left',padx=5,pady=4)
  self.preview_image=tk.Canvas(self.preview_area,bg='#eef2f5',highlightthickness=0);self.preview_image.grid(row=1,column=0,sticky='nsew',padx=7,pady=7);self.preview_image.bind('<ButtonPress-1>',self.preview_pan_start);self.preview_image.bind('<B1-Motion>',self.preview_pan_move);self.preview_image.bind('<MouseWheel>',self.preview_wheel)
  self.preview_meta=tk.Label(self.preview_area,text='اختر ملفًا لعرض المعاينة والتفاصيل.\n\nانقر مرة للمعاينة، وانقر مرتين لفتح الملف.',bg='white',fg='#526b7c',font=('Segoe UI',9),justify='right',anchor='ne',wraplength=330);self.preview_meta.grid(row=2,column=0,sticky='ew',padx=12,pady=(0,8))
  self.preview_related_strip=tk.Frame(self.preview_area,bg='#edf2f5');self.preview_related_strip.grid(row=3,column=0,sticky='ew',padx=8,pady=(0,4));self.preview_related_strip.grid_remove()
  controls=tk.Frame(self.preview_area,bg='white');controls.grid(row=4,column=0,sticky='ew',padx=8,pady=(0,8))
  ttk.Button(controls,text='−',width=3,command=lambda:self.zoom_preview(-.15)).pack(side='left');ttk.Button(controls,text='＋',width=3,command=lambda:self.zoom_preview(.15)).pack(side='left');ttk.Button(controls,text='◀ صفحة',command=lambda:self.change_pdf_page(-1)).pack(side='right',padx=2);ttk.Button(controls,text='صفحة ▶',command=lambda:self.change_pdf_page(1)).pack(side='right',padx=2);ttk.Button(controls,text='ملفات مرتبطة',command=self.open_related_from_preview).pack(side='right',padx=3)
  # Main file workspace.
  self.center=tk.Frame(self.explorer_page,bg='#e8edf1');self.center.grid(row=0,column=1,sticky='nsew');self.center.grid_rowconfigure(5,weight=1);self.center.grid_columnconfigure(0,weight=1)
  self.project_tabs_bar=tk.Frame(self.center,bg='#e8edf1');self.project_nb=ttk.Notebook(self.project_tabs_bar);self.project_nb.bind('<<NotebookTabChanged>>',self.project_tab_changed)
  self.filter_bar=tk.Frame(self.center,bg='#e8edf1');self.filter_bar.grid(row=1,column=0,sticky='ew',pady=(0,1));self.filter_context=tk.Label(self.filter_bar,text='المشروع بالكامل',bg='#e8edf1',fg='#526a7a',font=('Segoe UI',9,'bold'));self.filter_context.pack(side='right',padx=8);tk.Label(self.filter_bar,text='أنواع ملفات المشروع',bg='#e8edf1',fg='#526a7a',font=('Segoe UI',9,'bold')).pack(side='right',padx=(4,2));self.project_filter_canvas=tk.Canvas(self.filter_bar,bg='#e8edf1',height=40,highlightthickness=0);self.project_filter_canvas.pack(side='left',fill='x',expand=True);self.type_filter_controls=tk.Frame(self.project_filter_canvas,bg='#e8edf1');self.project_filter_window=self.project_filter_canvas.create_window((0,0),window=self.type_filter_controls,anchor='nw');self.type_filter_controls.bind('<Configure>',lambda e:self.project_filter_canvas.configure(scrollregion=self.project_filter_canvas.bbox('all')));self.project_filter_canvas.bind('<MouseWheel>',lambda e:self.project_filter_canvas.xview_scroll(int(-e.delta/120),'units'));self.project_filter_canvas.bind('<Shift-MouseWheel>',lambda e:self.project_filter_canvas.xview_scroll(int(-e.delta/120),'units'))
  self.folder_filter_bar=tk.Frame(self.center,bg='#e8edf1');self.folder_filter_bar.grid(row=2,column=0,sticky='ew',pady=(0,2));self.folder_filter_context=tk.Label(self.folder_filter_bar,text='المجلد الحالي',bg='#e8edf1',fg='#526a7a',font=('Segoe UI',9,'bold'));self.folder_filter_context.pack(side='right',padx=8);self.folder_menu_var=tk.StringVar(value='الكل');self.folder_menu_items={};self.folder_type_menu=tk.Menu(self.folder_filter_bar,tearoff=0,bg='#ffffff',fg='#19394e',activebackground='#dcebed',activeforeground='#19394e',font=('Segoe UI',9),borderwidth=1,relief='solid');self.folder_type_button=ttk.Menubutton(self.folder_filter_bar,textvariable=self.folder_menu_var,menu=self.folder_type_menu,style='Office.TMenubutton',direction='above');self.folder_type_button.pack(side='left',padx=5);self.folder_type_filter_controls=None
  bar=tk.Frame(self.center,bg='white',highlightbackground='#d6e0e6',highlightthickness=1);bar.grid(row=3,column=0,sticky='ew',pady=(5,5));ttk.Button(bar,text='←',command=self.go_back,width=4).pack(side='left',padx=(4,2),pady=4);ttk.Button(bar,text='→',command=self.go_forward,width=4).pack(side='left',padx=2,pady=4);ttk.Button(bar,text='↑',command=self.go_up,width=4).pack(side='left',padx=2,pady=4);ttk.Button(bar,text='↻',command=self.rescan,width=4).pack(side='left',padx=2,pady=4)
  self.breadcrumb=tk.StringVar();tk.Label(bar,textvariable=self.breadcrumb,bg='white',fg='#087e8b',font=('Segoe UI',10,'bold'),anchor='e').pack(side='right',fill='x',expand=True,padx=10)
  actions=tk.Frame(self.center,bg='#e8edf1');actions.grid(row=4,column=0,sticky='ew',pady=(0,5))
  self.search_button=tk.Button(actions,text='⌕  بحث في المشروع',command=self.show_search_page,bg='#102c3d',fg='white',activebackground='#1b455c',activeforeground='white',relief='flat',font=('Segoe UI',9,'bold'),padx=10,pady=7,cursor='hand2');self.search_button.pack(side='right',padx=(3,0));self.preview_toggle_button=ttk.Button(actions,text='◧  إظهار المعاينة',command=self.toggle_preview_panel)
  ttk.Button(actions,text='تخصيص المجلد',command=self.edit_folder_specialties).pack(side='left',padx=2);ttk.Button(actions,text='هاشتج الملف',command=self.edit_tags).pack(side='left',padx=2)
  tk.Label(actions,text='فلتر الهاشتاج',bg='#e8edf1',fg='#435b6d',font=('Segoe UI',9)).pack(side='left',padx=(7,2));self.tag_filter_var=tk.StringVar(value='الكل');self.tag_filter_box=ttk.Combobox(actions,textvariable=self.tag_filter_var,values=('الكل',),state='readonly',width=16,justify='right',style='Office.TCombobox');self.tag_filter_box.pack(side='left');self.tag_filter_box.bind('<<ComboboxSelected>>',self.tag_filter_changed);self.tag_manager_button=ttk.Button(actions,text='⚙',width=3,command=self.manage_file_tags);self.tag_manager_button.pack(side='left',padx=(3,2));self.tag_manager_button.configure(cursor='hand2')
  self.collection_button=ttk.Button(actions,text='عرض الملفات',command=self.show_files_collection)
  self.file_list_frame=tk.Frame(self.center,bg='#e8edf1');self.file_list_frame.grid(row=5,column=0,sticky='nsew');self.file_list_frame.grid_rowconfigure(0,weight=1);self.file_list_frame.grid_columnconfigure(0,weight=1)
  self.file_tree=self.make_list(self.file_list_frame);self.file_tree.grid(row=0,column=0,sticky='nsew')
  self.file_tree_ybar=ttk.Scrollbar(self.file_list_frame,orient='vertical',command=self.file_tree.yview);self.file_tree_ybar.grid(row=0,column=1,sticky='ns');self.file_tree_xbar=ttk.Scrollbar(self.file_list_frame,orient='horizontal',command=self.file_tree.xview);self.file_tree_xbar.grid(row=1,column=0,sticky='ew');self.file_tree.configure(yscrollcommand=self.file_tree_ybar.set,xscrollcommand=self.file_tree_xbar.set)
  self.selection_bar,self.selection_label=self.make_selection_bar(self.center);self.selection_bar.grid(row=6,column=0,sticky='ew',pady=(4,0));self.selection_bar.grid_remove()
  self.status=tk.StringVar(value='جاهز');tk.Label(self.center,textvariable=self.status,anchor='e',bg='#dfe7ec',fg='#147b87',font=('Segoe UI',9,'bold')).grid(row=7,column=0,sticky='ew',pady=(4,0));self.scan_progress=ttk.Progressbar(self.center,mode='indeterminate',length=180);self.scan_progress.grid(row=8,column=0,sticky='ew',pady=(2,0));self.scan_progress.grid_remove();self.scan_summary=tk.StringVar(value='');tk.Label(self.center,textvariable=self.scan_summary,anchor='e',bg='#e8edf1',fg='#617789',font=('Segoe UI',8)).grid(row=9,column=0,sticky='ew',pady=(1,0))
  # Right navigation rail: project-wide destinations are separate from current-folder type filters.
  rail=tk.Frame(self.explorer_page,bg='#102c3d',width=188);rail.grid(row=0,column=2,sticky='nsew',padx=(0,8));rail.grid_propagate(False)
  tk.Label(rail,text='مساحة المشروع',bg='#102c3d',fg='#a9c3d0',font=('Segoe UI',9,'bold')).pack(anchor='e',padx=15,pady=(17,3))
  tk.Label(rail,text=self.project,bg='#102c3d',fg='white',font=('Segoe UI',12,'bold'),anchor='e',wraplength=175).pack(anchor='e',fill='x',padx=15,pady=(0,14))
  self.rail_nav_buttons={}
  def rail_button(label,command,active=False,key=None):
   key=key or label;b=tk.Button(rail,text=label,command=command,anchor='e',bg='#1b4053' if active else '#102c3d',fg='white' if active else '#d3e2e9',activebackground='#24546a',activeforeground='white',relief='flat',font=('Segoe UI',9,'bold' if active else 'normal'),padx=14,pady=8,cursor='hand2',borderwidth=0);b.pack(fill='x',padx=7,pady=1);self.rail_nav_buttons[key]=b;return b
  tk.Label(rail,text='التصفح',bg='#102c3d',fg='#83a8b9',font=('Segoe UI',8,'bold')).pack(anchor='e',padx=15,pady=(2,4))
  rail_button('▦  ملفات المجلدات',self.show_folder_mode,active=self.mode=='folder',key='folder');rail_button('◈  ملفات المشروع',lambda:self.select_project_scope(),active=self.mode=='project',key='project')
  tk.Label(rail,text='الوصول السريع',bg='#102c3d',fg='#83a8b9',font=('Segoe UI',8,'bold')).pack(anchor='e',padx=15,pady=(15,4))
  rail_button('★  المفضلة',lambda:self.show_collection('favorites'),key='favorites');rail_button('◷  آخر ما فتحته',lambda:self.show_collection('opened'),key='opened');rail_button('＋  أضيف حديثًا',lambda:self.show_collection('added'),key='added');rail_button('↻  سجل التغييرات',lambda:self.show_collection('changes'),key='changes')
  tk.Label(rail,text='التخصصات',bg='#102c3d',fg='#83a8b9',font=('Segoe UI',9,'bold')).pack(anchor='e',padx=15,pady=(17,4))
  self.rail_tags=tk.Frame(rail,bg='#102c3d');self.rail_tags.pack(fill='x');self.refresh_tag_filters()
  tk.Frame(rail,bg='#23485b',height=1).pack(fill='x',padx=12,pady=12)
  rail_button('▱  فتح مجلد المشروع',lambda:os.startfile(str(self.root)),key='open_root')
  self.bind('<Control-f>',lambda e:(self.show_search_page(),'break'));self.bind('<Alt-Left>',lambda e:(self.go_back(),'break'));self.bind('<Alt-Up>',lambda e:(self.go_up(),'break'));self.bind('<F5>',lambda e:(self.rescan(),'break'));self.bind('<Control-o>',lambda e:(self.activate(self.file_tree),'break'));self.bind('<Control-a>',lambda e:(self.select_all_visible(),'break'));self.bind('<Escape>',lambda e:(self.show_files_collection() if self.view_mode!='files' else None,'break'))
  self.rebuild_project_tabs();self.rebuild_folder_tabs();self.refresh_directory()

 def toggle_preview_panel(self):
  searching=hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped()
  area=self.search_preview_area if searching else self.preview_area
  page=self.search_page if searching else self.explorer_page
  button=self.search_preview_toggle if searching else self.preview_toggle_button
  visible=area.winfo_manager()!=''
  if visible:
   area.grid_remove();page.grid_columnconfigure(0,minsize=0,weight=0);button.configure(text='◧  إظهار المعاينة');button.pack(side='right',padx=(3,0)) if not searching else None
  else:
   area.grid();page.grid_columnconfigure(0,minsize=350,weight=0);button.configure(text='◧  إخفاء المعاينة');button.pack_forget() if not searching else None
  self.after_idle(lambda:self.paint_preview() if getattr(self,'preview_base',None) and not searching else None)

 def make_selection_bar(self,parent):
  bar=tk.Frame(parent,bg='#e4f2f3',highlightbackground='#c6e2e4',highlightthickness=1)
  label=tk.Label(bar,text='',bg='#e4f2f3',fg='#164b5b',font=('Segoe UI',9,'bold'));label.pack(side='right',padx=12,pady=8)
  actions=[('🏷 هاشتج الملف',self.edit_tags),('★ المفضلة',self.toggle_favorite),('⧉ نسخ المسارات',lambda:self.copy_selected_paths()),('× مسح الهاشتاجات',lambda:self.clear_selected_tags(self.current_selection_tree()))]
  for text,command in actions:tk.Button(bar,text=text,command=command,bg='white',fg='#28465a',activebackground='#d5ebed',relief='flat',font=('Segoe UI',8,'bold'),padx=9,pady=5,cursor='hand2').pack(side='right',padx=3,pady=4)
  return bar,label

 def current_selection_tree(self):
  if hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped() and getattr(self,'search_nb',None) and self.search_nb.tabs():return self.search_views.get(self.search_nb.tab(self.search_nb.select(),'text'),getattr(self,'file_tree',None))
  return getattr(self,'file_tree',None)

 def select_project_scope(self):
  if not self.current:return
  self.mode='project';self.view_mode='files';self.collection_button.pack_forget();self.rebuild_folder_tabs(preferred=self.project_group);self.save_view_state();self.populate();self.update_rail_selection()

 def type_color(self,label):
  defaults={'PDF':('#d94f63','#fff0f2'),'Excel':('#299765','#edf8f1'),'لوحات CAD':('#3176c8','#eef5ff'),'Word':('#4379bb','#eef5fc'),'الصور':('#9a5bb4','#f8f0fb'),'الكل':('#526a7a','#e9eef2'),'كل النتائج':('#526a7a','#e9eef2'),'مجلد':('#e8ae43','#fff4d8'),'بدون امتداد':('#647b8a','#eef2f5')}
  if label in defaults:return defaults[label]
  ext='.'+str(label).strip().lstrip('.').lower()
  cache=getattr(self,'extension_color_cache',None)
  if cache is None:self.extension_color_cache={};cache=self.extension_color_cache
  if ext in cache:return cache[ext]
  with connect() as c:row=c.execute('select accent,soft from extension_colors where ext=?',(ext,)).fetchone()
  if row:cache[ext]=(row['accent'],row['soft']);return cache[ext]
  used={accent.lower() for accent,soft_color in defaults.values()}
  with connect() as c:used.update(r[0].lower() for r in c.execute('select accent from extension_colors'))
  candidates=[]
  for hue in range(360):
   for saturation,value in ((.72,.78),(.60,.67)):
    red,green,blue=colorsys.hsv_to_rgb(hue/360,saturation,value);accent='#{:02x}{:02x}{:02x}'.format(round(red*255),round(green*255),round(blue*255))
    if accent.lower() not in used:candidates.append(accent)
  accent=secrets.choice(candidates) if candidates else '#526a7a';rgb=tuple(int(accent[i:i+2],16) for i in (1,3,5));soft='#{:02x}{:02x}{:02x}'.format(*(round(channel*.13+255*.87) for channel in rgb))
  with connect() as c:
   c.execute('insert or ignore into extension_colors(ext,accent,soft) values(?,?,?)',(ext,accent,soft));row=c.execute('select accent,soft from extension_colors where ext=?',(ext,)).fetchone()
  cache[ext]=(row['accent'],row['soft']);return cache[ext]

 def type_icon_path(self,label):
  return {'لوحات CAD':'sample.dwg','PDF':'sample.pdf','Excel':'sample.xlsx','Word':'sample.docx','الصور':'sample.png','الكل':'','كل النتائج':'','بدون امتداد':''}.get(label,'sample.'+str(label).strip().lstrip('.').lower())

 def file_type_color(self,path):
  return self.type_color(classify(Path(path).suffix.lower()))

 def make_filter_pill(self,controls,label,count,selected,command):
  accent,soft=self.type_color(label);font=tkfont.Font(family='Segoe UI',size=9,weight='bold' if selected else 'normal');caption=str(label);count_text=f'{count:,}';bubble_width=max(27,tkfont.Font(family='Segoe UI',size=8,weight='bold').measure(count_text)+14);width=max(94,font.measure(caption)+bubble_width+58);pill=tk.Canvas(controls,width=width,height=42,bg='#e8edf1',highlightthickness=0,cursor='hand2')
  fill=soft if selected else '#ffffff';outline=accent if selected else '#d8e1e6';pill.create_polygon(3,21,3,15,5,9,10,5,width-10,5,width-5,9,width-3,15,width-3,27,width-5,33,width-10,37,10,37,5,33,3,27,fill=fill,outline=outline,smooth=True,width=2 if selected else 1,tags=('pill',))
  pill.create_oval(width-bubble_width-8,8,width-8,34,fill=accent,outline=accent,tags=('pill',));pill.create_text(width-bubble_width/2-8,21,text=count_text,fill='white',font=('Segoe UI',8,'bold'),tags=('pill',))
  icon=self.file_icon_image(self.type_icon_path(label));pill._tab_icon=icon;pill.create_image(19,21,image=icon,tags=('pill',));pill.create_text(38,21,text=caption,anchor='w',fill='#263f50',font=font,tags=('pill',))
  pill.tag_bind('pill','<Button-1>',lambda e:command());pill.bind('<MouseWheel>',lambda e:controls.master.xview_scroll(int(-e.delta/120),'units'));pill.pack(side='left',padx=4,pady=2)

 def set_discipline(self,value):
  if hasattr(self,'discipline_var'):
   self.discipline_var.set(value);self.discipline_changed()

 def file_icon_image(self,path,is_dir=False):
  cache=getattr(self,'file_icon_images',None)
  if cache is None:self.file_icon_images={};cache=self.file_icon_images
  ext=Path(path).suffix.lower();group=classify(ext) if not is_dir else 'مجلد';key='folder' if is_dir else (group if group in ('لوحات CAD','PDF','Excel','Word','الصور') else 'ext:'+ext)
  if key in cache:return cache[key]
  accent,soft=self.type_color('مجلد' if is_dir else (group if group in ('لوحات CAD','PDF','Excel','Word','الصور','بدون امتداد') else ext[1:].upper()));im=Image.new('RGBA',(32,32),(0,0,0,0));d=ImageDraw.Draw(im)
  if is_dir:
   d.rounded_rectangle((2,8,30,28),radius=5,fill=accent);d.rounded_rectangle((4,4,16,12),radius=3,fill=accent);d.rounded_rectangle((5,12,27,25),radius=3,fill='#fff7e5')
  else:
   d.rounded_rectangle((4,2,28,30),radius=4,fill=soft,outline=accent,width=2);d.polygon((20,2,28,10,20,10),fill=accent)
   label={'PDF':'PDF','Excel':'XLS','Word':'DOC','لوحات CAD':'CAD','الصور':'IMG'}.get(group,(ext[1:].upper()[:4] if ext else 'FILE'))
   d.rounded_rectangle((4,17,28,29),radius=3,fill=accent);font=self._font(7,True);bbox=d.textbbox((0,0),label,font=font);d.text(((32-(bbox[2]-bbox[0]))/2,18),label,font=font,fill='white')
  photo=ImageTk.PhotoImage(im);cache[key]=photo;return photo

 def file_row_tag(self,path,is_dir=False):
  if is_dir:return 'file_folder'
  ext=Path(path).suffix.lower();group=classify(ext);known={'PDF':'file_pdf','Excel':'file_excel','Word':'file_word','لوحات CAD':'file_cad','الصور':'file_image'}
  return known.get(group,'file_ext_'+hashlib.sha1(ext.encode('utf-8')).hexdigest()[:12])

 def make_list(self,parent):
  t=ttk.Treeview(parent,columns=('name','mark','type','size','mtime','opened','tags','path'),show='tree headings',selectmode='extended')
  # Keep the type icon (#0) directly beside the filename; the multi-select mark follows the name.
  t.heading('#0',text='');t.column('#0',width=44,minwidth=44,stretch=False,anchor='center');t.heading('mark',text='');t.column('mark',width=32,minwidth=32,stretch=False,anchor='center')
  for col,title,w in [('name','اسم الملف',170),('type','النوع',58),('size','الحجم',64),('mtime','تاريخ الملف',88),('opened','آخر فتح',88),('tags','الهاشتاجات',100),('path','المسار داخل المشروع',185)]:t.heading(col,text=title,command=lambda c=col:self.sort_by(c));t.column(col,width=min(getattr(self,'column_widths',{}).get(col,w),w),minwidth=52 if col not in ('name','path') else 100,stretch=(col=='name'),anchor='w' if col=='name' else 'e')
  t.bind('<<TreeviewSelect>>',lambda e,tree=t:self.on_tree_selection(tree));t.bind('<Button-1>',lambda e,tree=t:self.toggle_row_mark(e,tree),add='+');t.bind('<Configure>',lambda e,tree=t:self.remember_column_widths(tree),add='+');t.bind('<Double-1>',lambda e,tree=t:self.activate(tree));t.bind('<Button-3>',lambda e,tree=t:self.context_menu(e,tree));t.bind('<Return>',lambda e,tree=t:(self.activate(tree),'break'));return t

 def on_tree_selection(self,tree):
  self.sync_selection_marks(tree);self.preview_selected(tree);self.update_selection_status(tree)

 def sync_selection_marks(self,tree):
  selected=set(tree.selection())
  for item in tree.get_children():
   values=list(tree.item(item,'values'))
   if len(values)<2:continue
   mark='☑' if item in selected else '☐'
   if values[1]!=mark:values[1]=mark;tree.item(item,values=values)

 def toggle_row_mark(self,event,tree):
  if tree.identify_column(event.x)!='#2':return
  row=tree.identify_row(event.y)
  if not row:return 'break'
  if row in tree.selection():tree.selection_remove(row)
  else:tree.selection_add(row);tree.focus(row)
  self.sync_selection_marks(tree)
  self.update_selection_status(tree);return 'break'

 def rebuild_project_tabs(self):
  if not hasattr(self,'project_nb') or not self.current:return
  for tab in self.project_nb.tabs():self.project_nb.forget(tab)
  self.project_nb.add(tk.Frame(self.project_nb,bg='#e8edf1'),text='تصفح المجلدات')
  self.project_nb.add(tk.Frame(self.project_nb,bg='#e8edf1'),text='المشروع بالكامل')
  target='تصفح المجلدات' if self.mode=='folder' else 'المشروع بالكامل'
  self.project_nb.select(next(t for t in self.project_nb.tabs() if self.project_nb.tab(t,'text')==target))

 def rebuild_folder_tabs(self,preferred=None):
  if not hasattr(self,'type_filter_controls') or not self.current:return
  if preferred is not None:
   if self.mode=='folder':self.folder_group=preferred
   else:self.project_group=preferred
  old_project_types=set(getattr(self,'project_type_labels',set()))
  for w in self.type_filter_controls.winfo_children():w.destroy()
  with connect() as c:rows=c.execute('select rel,ext from files where project=?',(self.project,)).fetchall()
  folder_rel='' if self.current.resolve()==self.root.resolve() else self.current.relative_to(self.root).as_posix().rstrip('/')+'/';local_rows=[r for r in rows if r['rel'].startswith(folder_rel)]
  def type_counts(source):
   counts={}
   for row in source:
    kind=classify(row['ext'] or '');counts[kind]=counts.get(kind,0)+1
   return counts
  project_counts=type_counts(rows);folder_counts=type_counts(local_rows);order=lambda x:(x not in ('لوحات CAD','PDF','Excel','Word','الصور'),x.casefold())
  self.filter_context.configure(text=f'{len(rows):,} ملف');self.folder_filter_context.configure(text=f'داخل «{self.current.name or self.project}» · {len(local_rows):,} ملف')
  if self.project_group not in ['الكل',*project_counts]:self.project_group='الكل'
  if self.folder_group not in ['الكل',*folder_counts]:self.folder_group='الكل'
  current_project_types=set(project_counts)
  for label in ['الكل']+sorted(project_counts,key=order):
   count=sum(project_counts.values()) if label=='الكل' else project_counts[label]
   self.make_filter_pill(self.type_filter_controls,label,count,self.mode=='project' and label==self.project_group,lambda value=label:self.type_filter_changed('project',value))
   # Keep the project-wide type pills anchored at the beginning when a new extension appears.
   # Auto-scrolling to the end hid the common PDF / Excel / CAD filters on large projects.
  self.project_type_labels=current_project_types
  self.folder_menu_items={}
  self.folder_type_menu.delete(0,'end')
  for label in ['الكل']+sorted(folder_counts,key=order):
   count=sum(folder_counts.values()) if label=='الكل' else folder_counts[label]
   display=f'{label}  ·  {count:,}'
   self.folder_menu_items[display]=label
   self.folder_type_menu.add_command(label=display,command=lambda value=label:self.type_filter_changed('folder',value))
  selected=next((display for display,label in self.folder_menu_items.items() if label==self.folder_group),next(iter(self.folder_menu_items),'الكل'))
  self.folder_menu_var.set(selected)
  self.refresh_tag_filters()

 def scroll_project_filter_to_end(self):
  canvas=getattr(self,'project_filter_canvas',None)
  if not canvas or not canvas.winfo_exists():return
  target=1.0;start=canvas.xview()[0] if canvas.xview() else 0.0
  def step(i):
   if not canvas.winfo_exists():return
   value=start+(target-start)*i/7;canvas.xview_moveto(value)
   if i<7:canvas.after(18,lambda:step(i+1))
  step(1)

 def project_tab_changed(self,e=None):
  if not getattr(self,'project_nb',None) or not self.project_nb.tabs():return
  tab=self.project_nb.tab(self.project_nb.select(),'text')
  new_mode='folder' if tab=='تصفح المجلدات' else 'project'
  if self.mode==new_mode:return
  self.mode=new_mode;self.view_mode='files';self.collection_button.pack_forget()
  self.save_view_state();self.rebuild_folder_tabs();self.populate();self.update_rail_selection()
  self.log_activity('تغيير نطاق العرض','عرض '+('ملفات المجلد' if new_mode=='folder' else 'كل ملفات المشروع'),path=self.current)

 def type_filter_changed(self,scope,selected):
  self.view_mode='files';self.collection_button.pack_forget();self.mode=scope
  if hasattr(self,'project_nb'):
   target='تصفح المجلدات' if scope=='folder' else 'المشروع بالكامل'
   for tab in self.project_nb.tabs():
    if self.project_nb.tab(tab,'text')==target:self.project_nb.select(tab);break
  if scope=='folder':self.folder_group=selected
  else:self.project_group=selected
  self.rebuild_folder_tabs();self.save_view_state();self.populate();self.update_rail_selection()
  self.log_activity('تغيير فلتر النوع',f'{"المجلد الحالي" if scope=="folder" else "المشروع بالكامل"} · {selected}',path=self.current)

 def discipline_changed(self,e=None):
  self.save_view_state();self.populate()
  if hasattr(self,'discipline_var'):self.log_activity('تغيير فلتر التخصص',f'تصفية حسب {self.discipline_var.get()}',path=self.current)

 def sort_by(self,col):
  if getattr(self,'view_mode','files')=='opened':
   if getattr(self,'opened_sort_col','opened')==col:self.opened_sort_desc=not getattr(self,'opened_sort_desc',True)
   else:self.opened_sort_col=col;self.opened_sort_desc=False
   self.populate();self.log_activity('ترتيب الملفات',f'{col} · {"تنازلي" if self.opened_sort_desc else "تصاعدي"}',path=self.current);return
  if getattr(self,'sort_col','name')==col:self.sort_desc=not self.sort_desc
  else:self.sort_col=col;self.sort_desc=False
  self.save_view_state()
  if hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped():self.render_search_results()
  else:self.populate()
  self.log_activity('ترتيب الملفات',f'{col} · {"تنازلي" if self.sort_desc else "تصاعدي"}',path=self.current)

 def remember_column_widths(self,tree):
  if getattr(self,'remember_width_job',None):
   try:self.after_cancel(self.remember_width_job)
   except tk.TclError:pass
  self.remember_width_job=self.after(500,lambda:self._store_widths(tree))

 def _store_widths(self,tree):
  if tree.winfo_exists():self.column_widths={c:tree.column(c,'width') for c in tree['columns']};self.save_view_state()

 def save_view_state(self):
  if not getattr(self,'project',''):return
  try:
   rel=self.current.relative_to(self.root).as_posix() if self.current and self.root else ''
   widths=json.dumps(getattr(self,'column_widths',{}))
   with connect() as c:c.execute('insert into project_view_state(project,current_rel,mode,folder_filter,project_filter,discipline,sort_col,sort_desc,column_widths) values(?,?,?,?,?,?,?,?,?) on conflict(project) do update set current_rel=excluded.current_rel,mode=excluded.mode,folder_filter=excluded.folder_filter,project_filter=excluded.project_filter,discipline=excluded.discipline,sort_col=excluded.sort_col,sort_desc=excluded.sort_desc,column_widths=excluded.column_widths',(self.project,rel,getattr(self,'mode','folder'),getattr(self,'folder_group','الكل'),getattr(self,'project_group','الكل'),getattr(self,'discipline','الكل'),getattr(self,'sort_col','name'),int(getattr(self,'sort_desc',False)),widths))
  except Exception:pass

 def update_selection_status(self,tree):
  selected=set(tree.selection())
  for iid in tree.get_children(''):
   try:tree.set(iid,'mark','☑' if iid in selected else '☐')
   except tk.TclError:pass
  if tree is getattr(self,'file_tree',None) and getattr(self,'view_mode','')=='changes':
   bar=getattr(self,'selection_bar',None)
   if bar and bar.winfo_exists():bar.grid_remove()
   if hasattr(self,'status'):self.status.set(f'{len(tree.get_children()):,} حدث في سجل النشاط')
   return
  n=len(selected)
  if tree is getattr(self,'file_tree',None):
   bar=getattr(self,'selection_bar',None);label=getattr(self,'selection_label',None)
   if hasattr(self,'status') and self.view_mode=='files':self.status.set(f'{len(tree.get_children()):,} عنصر · {n:,} محدد' if n else f'{len(tree.get_children()):,} عنصر')
  else:
   bar=getattr(self,'search_selection_bar',None);label=getattr(self,'search_selection_label',None)
  if bar and bar.winfo_exists():
   if n:
    label.configure(text=f'تم تحديد {n:,} ملف')
    bar.grid()
   else:bar.grid_remove()

 def select_all_visible(self):
  tree=self.current_selection_tree()
  if not tree or not tree.winfo_exists():return
  rows=tree.get_children('')
  if rows:tree.selection_set(rows);tree.focus(rows[0]);self.update_selection_status(tree)

 def show_collection(self,kind):
  self.save_view_state();self.view_mode=kind;self.collection_button.pack(side='right',padx=3);self.populate()
  labels={'favorites':'المفضلة','opened':'آخر ما فتحته','added':'أضيف حديثًا','changes':'سجل التغييرات'}
  label=labels.get(kind,kind);self.breadcrumb.set(f'{self.project}  ›  {label}');self.update_rail_selection();self.log_activity('فتح قسم',label)

 def show_files_collection(self):
  self.view_mode='files';self.collection_button.pack_forget();self.refresh_directory();self.update_rail_selection()

 def toggle_favorite(self,path=None):
  paths=([path] if isinstance(path,(str,Path)) else list(path)) if path else self.selected_paths()
  paths=[Path(p) for p in paths if p]
  if not paths:return messagebox.showinfo('المفضلة','حدد ملفًا أو مجلدًا أولًا.',parent=self)
  added=[];removed=[]
  with connect() as c:
   for p in paths:
    key=str(p.resolve());exists=c.execute('select 1 from favorites where project=? and path=?',(self.project,key)).fetchone()
    if exists:
     c.execute('delete from favorites where project=? and path=?',(self.project,key));removed.append(p)
    else:
     c.execute('insert into favorites(project,path,kind,created) values(?,?,?,?)',(self.project,key,'folder' if p.is_dir() else 'file',stamp(time.time())));added.append(p)
  if added:self.log_activity('إضافة إلى المفضلة','إضافة: '+', '.join(p.name for p in added),path=added[0] if len(added)==1 else None)
  if removed:self.log_activity('إزالة من المفضلة','إزالة: '+', '.join(p.name for p in removed),path=removed[0] if len(removed)==1 else None)
  self.status.set(f'تم تحديث المفضلة لـ {len(paths):,} عنصر')
  if self.view_mode!='files':self.populate()

 def is_favorite(self,path):
  with connect() as c:return c.execute('select 1 from favorites where project=? and path=?',(self.project,str(Path(path).resolve()))).fetchone() is not None

 def show_related_files(self,path):
  searching=hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped()
  if searching:self.hide_search_page()
  p=Path(path)
  try:self.related_parent=p.parent.relative_to(self.root).as_posix()
  except ValueError:return
  self.related_stem=p.stem.casefold();self.view_mode='related';self.collection_button.pack(side='right',padx=3);self.populate();self.breadcrumb.set(f'{self.project}  ›  ملفات اللوحة المرتبطة بـ {p.stem}')

 def open_related_from_preview(self):
  path=getattr(self,'preview_current_path',None)
  if path and Path(path).is_file():self.show_related_files(path)

 def related_file_thumbnail(self,path):
  p=Path(path);image=None;resolved=str(p.resolve())
  for cache_key,(cached,note) in reversed(list(self.preview_cache.items())):
   if isinstance(cache_key,tuple) and cache_key and cache_key[0]==resolved:image=cached.copy();break
  if image is None and p.suffix.lower()=='.dwg':
   try:
    st=p.stat();key=hashlib.sha1(f'{p.resolve()}|{st.st_mtime_ns}|{st.st_size}'.encode('utf-8')).hexdigest();cached_path=LOG/'.preview_cache'/(key+'.png')
    if cached_path.is_file():
     with Image.open(cached_path) as cached:image=cached.convert('RGB').copy()
   except (OSError,ValueError):pass
  if image is None and p.suffix.lower() in ('.png','.jpg','.jpeg','.bmp','.gif','.tif','.tiff'):
   try:
    with Image.open(p) as source:image=source.convert('RGB').copy()
   except (OSError,ValueError):pass
  if image is None:return self.file_icon_image(str(p))
  image=ImageOps.fit(image,(44,30),method=Image.Resampling.BILINEAR);photo=ImageTk.PhotoImage(image);return photo

 def render_related_strip(self,current,paths):
  frame=getattr(self,'preview_related_strip',None)
  if not frame or not frame.winfo_exists():return
  for widget in frame.winfo_children():widget.destroy()
  frame._related_photos=[]
  if not paths:
   frame.grid_remove();return
  frame.grid();tk.Label(frame,text='مرتبط:',bg='#edf2f5',fg='#617789',font=('Segoe UI',8,'bold')).pack(side='right',padx=(3,5))
  for path in paths[:3]:
   photo=self.related_file_thumbnail(path);frame._related_photos.append(photo)
   tk.Button(frame,text=path.name[:15],image=photo,compound='left',command=lambda p=path:self.preview_related_file(p),bg='white',fg='#28465a',activebackground='#dceef0',relief='flat',font=('Segoe UI',8),padx=5,pady=3,cursor='hand2').pack(side='right',padx=2)

 def preview_related_file(self,path):
  p=Path(path)
  if not p.is_file():return
  searching=hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped()
  if searching:self.hide_search_page()
  if self.view_mode!='files' or self.mode!='folder' or self.current.resolve()!=p.parent.resolve():
   self.save_view_state()
   if self.current and self.current.resolve()!=p.parent.resolve():self.backstack.append(self.current)
   self.forwardstack.clear();self.current=p.parent;self.mode='folder';self.folder_group='الكل';self.view_mode='files';self.collection_button.pack_forget();self.refresh_directory();self.animate_window_in()
  iid=str(p.resolve())
  if self.file_tree.exists(iid):self.file_tree.selection_set(iid);self.file_tree.focus(iid);self.file_tree.see(iid)

 def leave_search_for(self,kind,value=None):
  self.hide_search_page()
  if kind=='folder':self.show_folder_mode()
  elif kind=='project':self.select_project_scope()
  elif kind in ('favorites','opened','added','changes'):self.show_collection(kind)
  elif kind=='specialty' and value:self.show_specialty(value)

 def _collection_rows(self):
  with connect() as c:
   if self.view_mode=='specialty':
    rows=c.execute("select path,group_concat(tag, ' ') tags from folder_tags where project=? and tag=? group by path order by path",(self.project,self.specialty_filter)).fetchall();out=[]
    for row in rows:
     rel=row['path'] or '.';p=(self.root/rel).resolve()
     if not p.is_dir():continue
     out.append({'path':str(p.resolve()),'kind':'folder','rel':rel,'name':p.name,'ext':'مجلد','size':0,'mtime':p.stat().st_mtime,'last_open':'','tags':row['tags'] or ''})
    return out
   if self.view_mode=='favorites':
    return c.execute("select v.path,v.kind,f.rel,f.name,f.ext,f.size,f.mtime,f.last_open,group_concat(t.tag,' ') tags from favorites v left join files f on f.path=v.path left join tags t on t.path=f.path where v.project=? group by v.path order by v.created desc",(self.project,)).fetchall()
   if self.view_mode=='opened':
    return c.execute("select f.path,f.project,f.rel,f.name,f.ext,f.size,f.mtime,max(h.opened_at) last_open,f.indexed,group_concat(t.tag,' ') tags from file_open_history h join files f on f.path=h.path and f.project=h.project left join tags t on t.path=f.path where h.project=? group by f.path order by max(h.opened_at) desc,max(h.id) desc limit 500",(self.project,)).fetchall()
   if self.view_mode=='added':
    return c.execute("select f.*,group_concat(t.tag,' ') tags,max(a.occurred_at) added_at from activity_log a join files f on f.path=a.path and f.project=a.project left join tags t on t.path=f.path where a.project=? and a.action='إضافة ملف' and a.occurred_at>=? group by f.path order by max(a.id) desc limit 500",(self.project,stamp(time.time()-30*86400))).fetchall()
   if self.view_mode=='changes':
    return c.execute("select id,project,action,details,path,occurred_at from activity_log where project=? order by id desc limit 2000",(self.project,)).fetchall()
   if self.view_mode=='related' and getattr(self,'related_stem',None):
    return [r for r in c.execute("select f.*,group_concat(t.tag,' ') tags from files f left join tags t on t.path=f.path where f.project=? and f.ext in ('.dwg','.pdf','.dxf','.png','.jpg','.jpeg') group by f.path",(self.project,)).fetchall() if Path(r['name']).stem.casefold()==self.related_stem and Path(r['rel']).parent.as_posix()==self.related_parent]
  return []

 def _discipline_match(self,tags):
  selected=getattr(self,'tag_filter_var',None)
  selected=selected.get() if selected else 'الكل'
  return selected=='الكل' or selected.casefold() in (tags or '').casefold().split()

 def refresh_tag_filters(self):
  if not getattr(self,'project',''):return
  try:
   with connect() as c:
    tags=sorted({r[0] for r in c.execute('select tag from file_tag_catalog where project=? union select distinct t.tag from tags t join files f on f.path=t.path where f.project=?',(self.project,self.project))})
   values=['الكل']+tags
   if hasattr(self,'tag_filter_box'):
    current=self.tag_filter_var.get();self.tag_filter_box.configure(values=values)
    if current not in values:self.tag_filter_var.set('الكل')
   self.refresh_specialty_nav()
  except Exception:pass

 def refresh_specialty_nav(self):
  if not hasattr(self,'rail_tags') or not self.rail_tags.winfo_exists():return
  try:
   with connect() as c:tags=[r[0] for r in c.execute('select distinct tag from folder_tags where project=? order by tag',(self.project,))]
   for key in [k for k in self.rail_nav_buttons if k.startswith('specialty:')]:self.rail_nav_buttons.pop(key,None)
   for w in self.rail_tags.winfo_children():w.destroy()
   for tag in tags:
    key='specialty:'+tag
    btn=tk.Button(self.rail_tags,text='●  '+tag,command=lambda t=tag:self.show_specialty(t),anchor='e',bg='#102c3d',fg='#d3e2e9',activebackground='#24546a',relief='flat',font=('Segoe UI',9),padx=14,pady=6,cursor='hand2',borderwidth=0)
    btn.pack(fill='x',padx=7,pady=1);self.rail_nav_buttons[key]=btn
   self.update_rail_selection()
  except Exception:pass

 def update_rail_selection(self):
  buttons=getattr(self,'rail_nav_buttons',{})
  if not buttons:return
  if self.view_mode=='specialty':active='specialty:'+getattr(self,'specialty_filter','')
  elif self.view_mode in ('favorites','opened','added','changes'):active=self.view_mode
  else:active='folder' if self.mode=='folder' else 'project'
  previous=getattr(self,'_nav_active_key',None);self._nav_active_key=active
  if getattr(self,'_nav_animation_job',None):
   try:self.after_cancel(self._nav_animation_job)
   except tk.TclError:pass
  starts={}
  for key,button in list(buttons.items()):
   try:starts[key]=button.cget('bg')
   except tk.TclError:continue
  def color(key,step):
   target='#1b5268' if key==active else '#102c3d';source=starts.get(key,target)
   if previous==active:return target
   try:
    a=tuple(int(source[i:i+2],16) for i in (1,3,5));b=tuple(int(target[i:i+2],16) for i in (1,3,5));v=step/5
    return '#'+''.join(f'{round(x+(y-x)*v):02x}' for x,y in zip(a,b))
   except Exception:return target
  def animate(step):
   for key,button in list(buttons.items()):
    try:
     selected=key==active;button.configure(bg=color(key,step),fg='white' if selected else '#d3e2e9',font=('Segoe UI',9,'bold' if selected else 'normal'))
    except tk.TclError:pass
   if step<5:self._nav_animation_job=self.after(18,lambda:animate(step+1))
   else:self._nav_animation_job=None
  animate(1 if previous!=active else 5)

 def show_specialty(self,tag):
  self.view_mode='specialty';self.specialty_filter=tag;self.collection_button.pack(side='right',padx=3);self.populate();self.breadcrumb.set(f'{self.project}  ›  التخصصات  ›  {tag}');self.update_rail_selection();self.log_activity('عرض تخصص',tag)

 def apply_tag_filter(self,value):
  if hasattr(self,'tag_filter_var'):self.tag_filter_var.set(value);self.populate()

 def tag_filter_changed(self,e=None):
  self.populate()
  value=self.tag_filter_var.get() if hasattr(self,'tag_filter_var') else 'الكل'
  self.log_activity('تغيير فلتر الهاشتاج',value,path=self.current)

 def indexed_folder_size(self,path,size_map=None):
  p=Path(path)
  try:rel=p.relative_to(self.root).as_posix().rstrip('/')
  except (ValueError,TypeError):return 0
  if size_map and rel in size_map:return size_map[rel]
  cached=getattr(self,'_folder_size_cache',None)
  if not cached or cached[0]!=self.project:
   sizes={}
   with connect() as c:rows=c.execute('select rel,size from files where project=?',(self.project,)).fetchall()
   for row in rows:
    prefix=''
    for part in (row['rel'] or '').split('/')[:-1]:
     prefix=f'{prefix}/{part}' if prefix else part;sizes[prefix]=sizes.get(prefix,0)+(row['size'] or 0)
   self._folder_size_cache=(self.project,sizes)
  return self._folder_size_cache[1].get(rel,0)

 def refresh_directory(self):
  if not self.current:return
  try:self.breadcrumb.set(self.project if self.current==self.root else self.current.relative_to(self.root).as_posix())
  except ValueError:self.breadcrumb.set(str(self.current))
  self.view_mode='files';self.collection_button.pack_forget()
  preferred=self.project_group if self.mode=='project' else self.folder_group
  self.rebuild_folder_tabs(preferred=preferred)
  if hasattr(self,'project_nb'):
   for tab in self.project_nb.tabs():
    if self.project_nb.tab(tab,'text')==('تصفح المجلدات' if self.mode=='folder' else 'المشروع بالكامل'):self.project_nb.select(tab);break
  self.save_view_state();self.populate();self.update_rail_selection()

 def show_folder_mode(self,from_tab=False):
  self.mode='folder';self.view_mode='files';self.folder_group='الكل';self.collection_button.pack_forget();self.rebuild_folder_tabs(preferred='الكل')
  if not from_tab and hasattr(self,'project_nb'):
   for tab in self.project_nb.tabs():
    if self.project_nb.tab(tab,'text')=='تصفح المجلدات':self.project_nb.select(tab);break
  self.populate();self.update_rail_selection()

 def _fetch_latest_release(self):
  request=urllib.request.Request(LATEST_RELEASE_API,headers={'Accept':'application/vnd.github+json','User-Agent':'Rasd-Desktop-Updater','X-GitHub-Api-Version':'2022-11-28'})
  with urllib.request.urlopen(request,timeout=10) as response:data=json.loads(response.read(2_000_000).decode('utf-8'))
  if data.get('draft') or data.get('prerelease'):raise ValueError('GitHub returned a draft or prerelease as the latest release.')
  tag=str(data.get('tag_name',''));match=re.search(r'(\d+(?:\.\d+){1,3})',tag)
  if not match:raise ValueError('Release version is missing or invalid.')
  version=tuple(int(part) for part in match.group(1).split('.'))
  assets=data.get('assets') or []
  return {'tag':tag,'version':version,'name':str(data.get('name') or tag),'body':str(data.get('body') or ''),'html_url':str(data.get('html_url') or ''),'assets':assets}

 def check_for_updates(self,manual=False):
  if self._update_check_running:
   if manual:messagebox.showinfo('التحديثات','جارٍ بالفعل فحص الإصدارات.',parent=self)
   return
  self._update_check_running=True
  future=self.update_executor.submit(self._fetch_latest_release)
  future.add_done_callback(lambda done:self.updateq.put(('release',manual,done)))

 def _update_version_tuple(self):
  return tuple(int(part) for part in APP_VERSION.split('.'))

 def _release_asset(self,release):
  mode='portable' if (BASE/'.rasd-portable').is_file() else 'standard'
  prefix='RasdPortableSetup_' if mode=='portable' else 'RasdSetup_'
  expected=f'{prefix}{release["tag"]}.exe'
  for asset in release['assets']:
   if asset.get('name')==expected and asset.get('state','uploaded')=='uploaded':return mode,asset
  return mode,None

 def _handle_update_check(self,manual,future):
  self._update_check_running=False
  try:release=future.result()
  except Exception as exc:
   if manual:messagebox.showwarning('تعذر فحص التحديثات',f'تعذر الاتصال بـ GitHub الآن. تحقق من الإنترنت وحاول مرة أخرى.\n\n{str(exc)[:240]}',parent=self)
   return
  if release['version']<=self._update_version_tuple():
   if manual:messagebox.showinfo('التحديثات','أنت تستخدم أحدث إصدار من Rasd.',parent=self)
   return
  try:
   with connect() as c:row=c.execute("select value from app_settings where key='updates_snooze_until'").fetchone()
   if not manual and row and float(row['value'])>time.time():return
  except (OSError,ValueError,TypeError,sqlite3.Error):pass
  mode,asset=self._release_asset(release)
  self._show_update_dialog(release,mode,asset)

 def _show_update_dialog(self,release,mode,asset):
  if not self.winfo_exists():return
  dialog=tk.Toplevel(self);dialog.title('تحديث Rasd');dialog.configure(bg='#eef3f7');dialog.resizable(False,False);dialog.transient(self);dialog.grab_set()
  card=tk.Frame(dialog,bg='white',highlightbackground='#d6e1e7',highlightthickness=1);card.pack(fill='both',expand=True,padx=14,pady=14)
  tk.Label(card,text='أهم من الشغل تظبيط الشغل، فحدّثني يا معلم 😄',bg='white',fg='#19394e',font=('Segoe UI',14,'bold'),wraplength=470,justify='right').pack(fill='x',padx=20,pady=(20,7),anchor='e')
  tk.Label(card,text=f'إصدار جديد متاح: {release["tag"]}   ·   إصدارك الحالي: {APP_VERSION}',bg='white',fg='#167f8c',font=('Segoe UI',10,'bold'),justify='right').pack(fill='x',padx=20,pady=(0,10),anchor='e')
  body=re.sub(r'[`*_#>]', '',release['body']).strip()
  if len(body)>580:body=body[:577].rstrip()+'…'
  tk.Label(card,text=body or 'يتضمن هذا الإصدار تحسينات وإصلاحات جديدة.',bg='#f4f7f9',fg='#526b7c',font=('Segoe UI',9),justify='right',anchor='ne',wraplength=465,height=6,padx=12,pady=10).pack(fill='x',padx=18,pady=(0,10))
  if asset is None:
   tk.Label(card,text='ملف التثبيت المناسب لهذا النوع من النسخ غير مرفوع بعد. يمكنك فتح صفحة الإصدار والتحميل يدويًا.',bg='white',fg='#b44b53',font=('Segoe UI',9),justify='right',wraplength=465).pack(fill='x',padx=20,pady=(0,8))
  actions=tk.Frame(card,bg='white');actions.pack(fill='x',padx=18,pady=(8,18))
  def dismiss():
   try:
    with connect() as c:c.execute("insert into app_settings(key,value) values('updates_snooze_until',?) on conflict(key) do update set value=excluded.value",(str(time.time()+86400),))
   except sqlite3.Error:pass
   dialog.destroy()
  def update_now():
   if asset is None:
    if release['html_url']:webbrowser.open(release['html_url'])
    return
   dialog.destroy();self._begin_update_download(release,mode,asset,'now')
  def update_next():
   if asset is None:
    if release['html_url']:webbrowser.open(release['html_url'])
    return
   dialog.destroy();self._begin_update_download(release,mode,asset,'next')
  ttk.Button(actions,text='طنّشني ليوم',command=dismiss).pack(side='left',padx=3)
  if asset is not None:ttk.Button(actions,text='حدّثني لما أشتغل تاني',command=update_next).pack(side='right',padx=3)
  ttk.Button(actions,text='حدّثني الآن ❤️',command=update_now).pack(side='right',padx=3)
  dialog.protocol('WM_DELETE_WINDOW',dismiss);dialog.update_idletasks();dialog.geometry(f'520x{max(300,dialog.winfo_reqheight())}+{max(0,self.winfo_rootx()+(self.winfo_width()-520)//2)}+{max(0,self.winfo_rooty()+(self.winfo_height()-dialog.winfo_reqheight())//2)}')

 def _download_release_asset(self,asset):
  url=str(asset.get('browser_download_url') or '')
  if not url.startswith('https://github.com/engamrhesham2002-cell/Rasd/releases/download/'):raise ValueError('رابط ملف التحديث لا يخص إصدارات Rasd الرسمية.')
  size=int(asset.get('size') or 0)
  if size<=0 or size>350_000_000:raise ValueError('حجم ملف التحديث غير صالح.')
  UPDATE_HOME.mkdir(parents=True,exist_ok=True);downloads=UPDATE_HOME/'downloads';downloads.mkdir(parents=True,exist_ok=True)
  name=Path(str(asset.get('name') or '')).name
  if not name.lower().endswith('.exe') or name!=str(asset.get('name') or ''):raise ValueError('اسم ملف التحديث غير صالح.')
  target=downloads/name;partial=target.with_suffix(target.suffix+'.part');digest=hashlib.sha256();written=0
  request=urllib.request.Request(url,headers={'User-Agent':'Rasd-Desktop-Updater'})
  try:
   with urllib.request.urlopen(request,timeout=30) as response,partial.open('wb') as output:
    while True:
     chunk=response.read(1024*1024)
     if not chunk:break
     written+=len(chunk)
     if written>size:raise ValueError('ملف التحديث أكبر من الحجم المعلن.')
     output.write(chunk);digest.update(chunk)
   if written!=size:raise ValueError(f'اكتمل تنزيل {written:,} بايت فقط من أصل {size:,}.')
   expected=str(asset.get('digest') or '')
   if not re.fullmatch(r'sha256:[a-fA-F0-9]{64}',expected):raise ValueError('تعذر التحقق من بصمة SHA-256 المنشورة لهذا الملف؛ لن يتم تثبيته.')
   if digest.hexdigest().lower()!=expected.split(':',1)[1].lower():raise ValueError('فشل التحقق من سلامة ملف التحديث (SHA-256).')
   partial.replace(target);return target
  except Exception:
   try:partial.unlink(missing_ok=True)
   except OSError:pass
   raise

 def _begin_update_download(self,release,mode,asset,when):
  if mode!=('portable' if (BASE/'.rasd-portable').is_file() else 'standard'):
   messagebox.showerror('نوع التثبيت','ملف التحديث لا يطابق نوع النسخة المثبتة.',parent=self);return
  dialog=tk.Toplevel(self);dialog.title('تنزيل تحديث Rasd');dialog.configure(bg='white');dialog.resizable(False,False);dialog.transient(self);dialog.grab_set()
  frame=tk.Frame(dialog,bg='white');frame.pack(fill='both',expand=True,padx=22,pady=20)
  tk.Label(frame,text=f'جارٍ تنزيل Rasd {release["tag"]}…',bg='white',fg='#19394e',font=('Segoe UI',11,'bold')).pack(pady=(0,12))
  bar=ttk.Progressbar(frame,mode='indeterminate',length=360);bar.pack();bar.start(12)
  tk.Label(frame,text='سيتم التحقق من سلامة الملف قبل تثبيته.',bg='white',fg='#718491',font=('Segoe UI',9)).pack(pady=(10,0))
  dialog.protocol('WM_DELETE_WINDOW',lambda:None);dialog.update_idletasks();dialog.geometry(f'+{self.winfo_rootx()+(self.winfo_width()-dialog.winfo_width())//2}+{self.winfo_rooty()+(self.winfo_height()-dialog.winfo_height())//2}')
  future=self.update_executor.submit(self._download_release_asset,asset)
  future.add_done_callback(lambda done:self.updateq.put(('download',when,release['tag'],dialog,done)))

 def _handle_update_download(self,when,tag,dialog,future):
  try:installer=future.result()
  except Exception as exc:
   try:dialog.destroy()
   except tk.TclError:pass
   messagebox.showerror('فشل تنزيل التحديث',f'لم يكتمل تنزيل التحديث. يمكنك المحاولة لاحقًا.\n\n{str(exc)[:300]}',parent=self);return
  try:dialog.destroy()
  except tk.TclError:pass
  mode='portable' if (BASE/'.rasd-portable').is_file() else 'standard'
  if not queue_pending_update(installer,mode,tag):
   messagebox.showerror('تعذر تجهيز التحديث','تعذر حفظ التحديث لهذا التثبيت. تأكد من صلاحية الكتابة داخل مجلد البرنامج وحاول مرة أخرى.',parent=self);return
  if when=='now':
   if not start_scheduled_update(os.getpid(),installer,BASE,sys.executable):
    UPDATE_PENDING.unlink(missing_ok=True);messagebox.showerror('تعذر بدء التحديث','تعذر تشغيل مساعد التثبيت المدمج في Windows؛ سيظل البرنامج مفتوحًا. جرّب تنزيل المثبّت وتشغيله يدويًا.',parent=self);return
   self._update_install_on_close=True
   messagebox.showinfo('التحديث جاهز',f'تم تنزيل Rasd {tag}. سيُغلق البرنامج الآن لتثبيت التحديث ثم يُفتح تلقائيًا.',parent=self)
   if self.winfo_exists():self.close_app()
  else:
   messagebox.showinfo('التحديث جاهز',f'تم تنزيل Rasd {tag} والتحقق منه. سيبدأ التثبيت تلقائيًا في المرة القادمة التي تفتح فيها البرنامج.',parent=self)

 def _show_update_failure(self,detail):
  try:UPDATE_FAILURE.unlink(missing_ok=True)
  except OSError:pass
  if self.winfo_exists():messagebox.showwarning('تعذر تثبيت التحديث','لم يكتمل تثبيت التحديث؛ فتح Rasd الإصدار الحالي. يمكنك إعادة المحاولة أو تشغيل ملف التثبيت يدويًا.\n\n'+detail[:300],parent=self)

 def _poll_update_queue(self):
  try:
   while True:
    item=self.updateq.get_nowait()
    if item[0]=='release':self._handle_update_check(item[1],item[2])
    elif item[0]=='download':self._handle_update_download(item[1],item[2],item[3],item[4])
  except queue.Empty:pass

 def close_app(self):
  try:
   for job in self.tk.call('after','info'):self.after_cancel(job)
  except tk.TclError:pass
  self._poll_after_id=None
  if hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped():
   if getattr(self,'search_history_job',None):
    try:self.after_cancel(self.search_history_job)
    except tk.TclError:pass
   self.record_search_history();self.save_search_state()
  self.save_view_state()
  self.watch_stop.set()
  for hwnd in self.everything_windows.values():ctypes.windll.user32.PostMessageW(hwnd,0x0010,0,0)
  self.search_serial+=1
  self.stop_everything_instance()
  try:self.preview_executor.shutdown(wait=False,cancel_futures=True);self.cad_preview_executor.shutdown(wait=False,cancel_futures=True);self.search_executor.shutdown(wait=False,cancel_futures=True)
  except Exception:pass
  try:self.update_executor.shutdown(wait=False,cancel_futures=True)
  except Exception:pass
  proc=getattr(self,'cad_preview_process',None)
  if proc and proc.poll() is None:
   try:proc.kill()
   except OSError:pass
  self.destroy()

 def stop_everything_instance(self):
  exe=getattr(self,'everything_exe',None);instance=getattr(self,'everything_instance',None);data=getattr(self,'everything_data',None)
  if exe and instance and data and Path(exe).exists():
   try:subprocess.Popen([str(exe),'-instance',instance,'-exit'],cwd=str(data),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
   except OSError:pass
  self.everything_proc=None;self.everything_key=None;self.everything_instance=None;self.everything_data=None;self.everything_exe=None;self.everything_cli=None;self.everything_root=None

 def hide_search_page(self):
  self.preview_token+=1;self.search_serial+=1
  self.save_search_state()
  self.stop_everything_instance()
  if hasattr(self,'search_page'):self.search_page.destroy()
  self.preview_image,self.preview_meta,self.preview_related_strip=self.active_preview;self.explorer_page.pack(fill='both',expand=True,padx=12,pady=10);self.title('Rasd | مدير ملفات المشاريع');self.populate();self.animate_window_in()

 def start_scan_progress(self):
  bar=getattr(self,'scan_progress',None)
  if not bar or not bar.winfo_exists():return
  try:
   bar.grid();bar.start(12);self._scan_progress_running=True
  except tk.TclError:pass

 def stop_scan_progress(self):
  bar=getattr(self,'scan_progress',None)
  if not bar or not bar.winfo_exists():return
  try:bar.stop();bar.grid_remove();self._scan_progress_running=False
  except tk.TclError:pass

 def poll_queue(self):
  try:
   try:
    while True:
     kind,scan_root,n,extra=self.scanq.get_nowait()
     if self.root and Path(scan_root).resolve()==self.root.resolve():
      if kind=='progress':
       if not getattr(self,'_scan_progress_running',False):self.start_scan_progress()
       self.scan_summary.set(f'جارٍ فهرسة المشروع… تمت قراءة {n:,} ملف');continue
      self.stop_scan_progress()
      self.index_total=n;self.index_errors=extra or 0;self._folder_size_cache=None;self.rebuild_project_tabs();self.rebuild_folder_tabs();self.populate()
      with connect() as c:counts=c.execute("select sum(kind='added') added,sum(kind='modified') modified from file_changes where project=? and changed_at>=?",(self.project,getattr(self,'visit_since','0000'))).fetchone()
      added=counts['added'] or 0;modified=counts['modified'] or 0
      self.scan_summary.set(f'اكتمل الفهرس: {n:,} ملف · جديد {added:,} · معدل {modified:,} · تعذر قراءته {self.index_errors:,}')
      if hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped():self.refresh_search_cache();self.render_search_results()
     if self.root and self.watch_root!=self.root:
      self.watch_root=self.root;threading.Thread(target=self.watch_project_worker,args=(self.root,self.watch_stop),daemon=True).start()
   except queue.Empty:pass
   try:
    while True:
     token,rows,note=self.searchq.get_nowait()
     if token==self.search_serial and hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped():self.render_search_rows(rows,note)
   except queue.Empty:pass
   try:
    while True:
     item=self.previewq.get_nowait()
     try:
      if item[0]=='excel':
       _,token,path,meta,names,sheet_name,rows,start_row,total_rows,has_more,key=item
       if token==self.preview_token and self.winfo_exists():self.render_excel_preview(path,meta,names,sheet_name,rows,start_row,total_rows,has_more,key)
       continue
      if item[0]=='image':
       _,token,image,meta,*extra=item
       key,note=(extra[0],extra[1]) if len(extra)>=2 else (None,None)
      else:
       token,image,meta=item[:3];key,note=(item[3],item[4]) if len(item)>=5 else (None,None)
      if token==self.preview_token and self.winfo_exists():
       cache_error=bool(note and any(word in note for word in ('لم تتوفر','لم يعثر','تعذرت معاينة')) and key and Path(key[0]).suffix.lower()=='.dwg')
       if key is not None and not cache_error:
        self.preview_cache[key]=(image.copy(),note or '');self.preview_cache.move_to_end(key)
        while len(self.preview_cache)>12:self.preview_cache.popitem(last=False)
       self.render_preview(image,meta)
     except Exception as exc:
      try:self.preview_meta.configure(text=f'تعذر عرض المعاينة: {str(exc)[:120]}')
      except (tk.TclError,AttributeError):pass
   except queue.Empty:pass
   self._poll_update_queue()
  finally:
   try:
    if self.winfo_exists():self._poll_after_id=self.after(180,self.poll_queue)
   except tk.TclError:pass

