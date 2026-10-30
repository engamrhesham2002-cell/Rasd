# Rasd - الشاشة الرئيسية وقائمة المشاريع وإنشاء/فتح مشروع
from common import *
from update_utils import *
from storage import *
import shutil

class HomeMixin:
 def show_home(self):
  if hasattr(self,'watch_stop'):self.watch_stop.set();self.watch_root=None
  self.clear();self.project='';self.configure(bg='#eef3f7');self.title('Rasd | مدير ملفات المشاريع')
  self.selected_home_projects = {}
  
  # === الشريط العلوي ===
  top=tk.Frame(self,bg='#eef2f5',height=58,highlightbackground='#e0e8ed',highlightthickness=1);top.pack(fill='x');top.pack_propagate(False)
  brand=tk.Frame(top,bg='#eef2f5',cursor='hand2');brand.pack(side='left',padx=24)
  try:
   with Image.open(Path(getattr(sys,'_MEIPASS',BASE))/'Assets'/'rasd_logo.png') as source:
    self.brand_icon=ImageTk.PhotoImage(source.convert('RGBA').resize((32,32),Image.Resampling.LANCZOS))
    b_ico=tk.Label(brand,image=self.brand_icon,bg='#eef2f5',cursor='hand2');b_ico.pack(side='left',padx=(0,8))
  except Exception:
   b_ico=tk.Label(brand,text='◉',font=('Segoe UI Symbol',22,'bold'),fg='#1595a5',bg='#eef2f5',cursor='hand2');b_ico.pack(side='left',padx=(0,8))
  b_t1=tk.Label(brand,text='RASD',font=('Segoe UI',15,'bold'),fg='#253c4b',bg='#eef2f5',cursor='hand2');b_t1.pack(side='left')
  b_t2=tk.Label(brand,text='Made by ENG. Amr Hesham',font=('Segoe UI',8),fg='#718491',bg='#eef2f5',cursor='hand2');b_t2.pack(side='left',padx=(9,0),pady=(6,0))
  for w in (brand, b_ico, b_t1, b_t2):
   w.bind('<Button-1>', lambda e: self.show_home())
  
  tk.Button(top,text='📂 مجلد Log',command=lambda:os.startfile(str(LOG)),bg='#eef2f5',fg='#607786',activebackground='#e9f0f4',relief='flat',font=('Segoe UI',9,'bold'),padx=5,cursor='hand2').pack(side='right',padx=(2,18))
  tk.Button(top,text='⚙ مسار الحفظ',command=self.change_log_path,bg='#eef2f5',fg='#607786',activebackground='#e9f0f4',relief='flat',font=('Segoe UI',9,'bold'),padx=5,cursor='hand2').pack(side='right',padx=2)
  tk.Button(top,text='📦 استيراد/تصدير',command=self.show_sync_dialog,bg='#eef2f5',fg='#607786',activebackground='#e9f0f4',relief='flat',font=('Segoe UI',9,'bold'),padx=5,cursor='hand2').pack(side='right',padx=2)
  tk.Button(top,text='↻ تحديث البرنامج',command=lambda:self.check_for_updates(manual=True),bg='#eef2f5',fg='#607786',activebackground='#e9f0f4',relief='flat',font=('Segoe UI',9,'bold'),padx=5,cursor='hand2').pack(side='right',padx=2)
  tk.Button(top,text='🔒 حماية البرنامج',command=self.manage_password,bg='#eef2f5',fg='#607786',activebackground='#e9f0f4',relief='flat',font=('Segoe UI',9,'bold'),padx=5,cursor='hand2').pack(side='right',padx=2)
  
  # === منطقة المحتوى الرئيسية ===
  wrap=tk.Frame(self,bg='#eef3f7');wrap.pack(fill='both',expand=True,padx=42,pady=(12,0))
  controls=tk.Frame(wrap,bg='#eef3f7');controls.pack(fill='x',pady=(3,12))
  tk.Button(controls,text='＋ مشروع جديد',command=self.new_project,bg='#3478e5',fg='white',activebackground='#2868ce',activeforeground='white',relief='flat',font=('Segoe UI',10,'bold'),padx=15,pady=6,cursor='hand2').pack(side='right',padx=(12,0))
  
  self.project_search=tk.StringVar(value='ابحث عن مشروع')
  search_wrap=tk.Frame(controls,bg='white',highlightbackground='#d8e1e7',highlightthickness=1);search_wrap.pack(side='right',fill='x',expand=True)
  tk.Label(search_wrap,text='⌕',font=('Segoe UI',16),fg='#8496a3',bg='white').pack(side='right',padx=(10,3))
  entry=tk.Entry(search_wrap,textvariable=self.project_search,bg='white',fg='#344c5b',insertbackground='#3478e5',relief='flat',font=('Segoe UI',10),justify='right');entry.pack(side='right',fill='x',expand=True,ipady=7,padx=6)
  entry.bind('<FocusIn>',lambda e:entry.delete(0,'end') if entry.get()=='ابحث عن مشروع' else None);entry.bind('<FocusOut>',lambda e:entry.insert(0,'ابحث عن مشروع') if not entry.get() else None)
  
  self.home_filter_mode=getattr(self,'home_filter_mode','all');self.home_filter_buttons={}
  
  sort_text = '☷ الترتيب: ' + ('الأحدث' if getattr(self,'home_sort_mode','name')=='recent' else 'الأبجدي')
  self.home_sort_button=tk.Button(controls,text=sort_text,command=self.toggle_project_sort,bg='#eef3f7',fg='#527083',activebackground='#e2ebf0',relief='flat',font=('Segoe UI',9,'bold'),padx=10,pady=6,cursor='hand2',state='disabled' if self.home_filter_mode in ('visited','added') else 'normal')
  self.home_sort_button.pack(side='left',padx=(7,0))
  
  for label,command in reversed([('الكل','all'),('المفضلة','favorites'),('آخر زيارة','visited'),('أضيف حديثاً','added')]):
   active=command==self.home_filter_mode
   b=tk.Button(controls,text=label,command=lambda c=command:self.home_project_filter(c),bg='#3478e5' if active else '#e5ecf0',fg='white' if active else '#526b7b',activebackground='#2868ce',relief='flat',font=('Segoe UI',9,'bold' if active else 'normal'),padx=12,pady=6,cursor='hand2');b.pack(side='left',padx=3);self.home_filter_buttons[command]=b
  
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
  
  self.cards_canvas = tk.Canvas(wrap, bg='#eef3f7', highlightthickness=0)
  self.cards_scroll = ttk.Scrollbar(wrap, orient='vertical', command=self.cards_canvas.yview)
  self.cards = tk.Frame(self.cards_canvas, bg='#eef3f7')
  
  self.cards_scroll.pack(side='left', fill='y')
  self.cards_canvas.pack(side='right', fill='both', expand=True)
  self.cards_canvas.configure(yscrollcommand=self.cards_scroll.set)
  self.cards_canvas.create_window((0, 0), window=self.cards, anchor='ne', tags='cards_frame')
  
  def _on_cards_configure(event):
   self.cards_canvas.configure(scrollregion=self.cards_canvas.bbox('all'))
   self.cards_canvas.itemconfig('cards_frame', width=self.cards_canvas.winfo_width())
  self.cards.bind('<Configure>', _on_cards_configure);self.cards_canvas.bind('<Configure>', _on_cards_configure)

  def _on_mousewheel(event):
   if self.cards.winfo_exists() and self.cards.winfo_reqheight() > self.cards_canvas.winfo_height():
    self.cards_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
  self.cards_canvas.bind("<MouseWheel>", _on_mousewheel)

  self.bulk_action_bar = tk.Frame(self, bg='#e4f2f3', height=45, highlightbackground='#c6e2e4', highlightthickness=1)
  self.bulk_action_bar.pack(fill='x', side='bottom');self.bulk_action_bar.pack_propagate(False)
  self.bulk_label = tk.Label(self.bulk_action_bar, text='', bg='#e4f2f3', fg='#164b5b', font=('Segoe UI', 10, 'bold'))
  self.bulk_label.pack(side='right', padx=15, pady=10)
  tk.Button(self.bulk_action_bar, text='🗑 حذف المحدد', command=self.bulk_delete_projects, bg='white', fg='#bd4856', relief='flat', font=('Segoe UI', 9, 'bold'), padx=10, cursor='hand2').pack(side='left', padx=10, pady=8)
  tk.Button(self.bulk_action_bar, text='★ المفضلة', command=self.bulk_favorite_projects, bg='white', fg='#d69637', relief='flat', font=('Segoe UI', 9, 'bold'), padx=10, cursor='hand2').pack(side='left', padx=5, pady=8)
  self.bulk_action_bar.pack_forget()

  self.footer = tk.Frame(self, bg='#102c3d', height=45)
  self.footer.pack(fill='x', side='bottom');self.footer.pack_propagate(False)
  tk.Button(self.footer, text='☑ مهامي', command=self.show_tasks, bg='#102c3d', fg='white', activebackground='#1b455c', activeforeground='white', relief='flat', font=('Segoe UI', 10, 'bold'), padx=15, pady=5, cursor='hand2').pack(side='right', padx=10, pady=5)
  tk.Button(self.footer, text='▦ التقويم', command=lambda:self.show_task_calendar(), bg='#102c3d', fg='white', activebackground='#1b455c', activeforeground='white', relief='flat', font=('Segoe UI', 10, 'bold'), padx=15, pady=5, cursor='hand2').pack(side='right', padx=10, pady=5)

  self.project_card_photos=[]
  self.project_search.trace_add('write',lambda *_:self.render_projects());self.render_projects()
  self.animate_window_in()

 def change_log_path(self):
  dialog = tk.Toplevel(self);dialog.title('مسار الحفظ (Log)');dialog.configure(bg='#eef3f7');dialog.geometry('450x220');dialog.transient(self);dialog.grab_set()
  tk.Label(dialog, text='تغيير مسار حفظ المشاريع والبيانات', bg='#eef3f7', fg='#19394e', font=('Segoe UI', 12, 'bold')).pack(pady=(20, 10))
  tk.Label(dialog, text=f'المسار الحالي:\n{LOG}', bg='#eef3f7', fg='#617789', font=('Segoe UI', 9), justify='center').pack(pady=(0, 20))
  
  btn_frame = tk.Frame(dialog, bg='#eef3f7');btn_frame.pack(fill='x', padx=20)
  
  def choose_custom():
   new_path = filedialog.askdirectory(title='اختر مجلد جديد لحفظ بيانات البرنامج', parent=dialog)
   if new_path:
    move_files = messagebox.askyesno('نقل البيانات', 'هل تريد نقل جميع مشاريعك والمهام وقاعدة البيانات من المسار القديم إلى المسار الجديد؟\n\n(اختر "نعم" لنقل البيانات، أو "لا" لبدء سجل جديد فارغ)', parent=dialog)
    if move_files:
     try:
      for item in LOG.iterdir():
       target = Path(new_path) / item.name
       if item.is_dir(): shutil.copytree(item, target, dirs_exist_ok=True)
       else: shutil.copy2(item, target)
     except Exception as e:
      messagebox.showerror('خطأ في النقل', f'حدث خطأ أثناء النقل: {e}', parent=dialog)
    
    base_dir = Path(os.environ.get('LOCALAPPDATA', str(BASE))) / 'Rasd';base_dir.mkdir(parents=True, exist_ok=True)
    config_file = base_dir / 'config.json';config_data = {}
    if config_file.exists():
     try: config_data = json.loads(config_file.read_text(encoding='utf-8'))
     except Exception: pass
    config_data['custom_log_path'] = new_path
    config_file.write_text(json.dumps(config_data, ensure_ascii=False), encoding='utf-8')
    
    self.log_activity('إعدادات النظام', f'تم تغيير مسار حفظ المشاريع إلى: {new_path}', project='ALL')
    
    messagebox.showinfo('تم بنجاح', 'تم تغيير المسار.\nسيغلق البرنامج الآن لتطبيق التغييرات، يرجى إعادة فتحه.', parent=dialog)
    self.close_app(force=True)
    
  def reset_default():
   base_dir = Path(os.environ.get('LOCALAPPDATA', str(BASE))) / 'Rasd';config_file = base_dir / 'config.json'
   if config_file.exists():
    try:
     config_data = json.loads(config_file.read_text(encoding='utf-8'))
     if 'custom_log_path' in config_data:
      del config_data['custom_log_path']
      config_file.write_text(json.dumps(config_data, ensure_ascii=False), encoding='utf-8')
      self.log_activity('إعدادات النظام', 'تم استعادة مسار حفظ المشاريع الافتراضي', project='ALL')
    except Exception: pass
   messagebox.showinfo('تم', 'تم استعادة المسار الافتراضي. سيغلق البرنامج الآن، يرجى إعادة فتحه.', parent=dialog)
   self.close_app(force=True)

  ttk.Button(btn_frame, text='اختيار مسار مخصص', command=choose_custom).pack(side='right', padx=10)
  ttk.Button(btn_frame, text='استعادة الافتراضي', command=reset_default).pack(side='left', padx=10)

 def update_bulk_action_bar(self):
  selected_count = sum(1 for v in self.selected_home_projects.values() if v.get())
  if selected_count > 0:
   self.footer.pack_forget();self.bulk_label.configure(text=f'تم تحديد {selected_count} مشروع');self.bulk_action_bar.pack(fill='x', side='bottom')
  else:
   self.bulk_action_bar.pack_forget();self.footer.pack(fill='x', side='bottom')

 def bulk_delete_projects(self):
  selected_projs = [p for p, v in self.selected_home_projects.items() if v.get()]
  if not selected_projs: return
  if not messagebox.askyesno('تأكيد الحذف', f'هل تريد مسح {len(selected_projs)} مشروع نهائياً من القرص الصلب؟', parent=self): return
  for p_name in selected_projs:
   p_path = LOG / p_name
   try:
    try: import send2trash; send2trash.send2trash(str(p_path))
    except ImportError: shutil.rmtree(str(p_path), ignore_errors=True)
    with connect() as c:
     c.execute("DELETE FROM files WHERE project=?", (p_name,))
     c.execute("DELETE FROM favorites WHERE project=?", (p_name,))
     c.execute("DELETE FROM tasks WHERE project=?", (p_name,))
   except Exception as e:
    messagebox.showerror('خطأ', f'لم يتم حذف {p_name}:\n{e}', parent=self)
  self.selected_home_projects.clear();self.update_bulk_action_bar();self.render_projects()

 def bulk_favorite_projects(self):
  selected_projs = [p for p, v in self.selected_home_projects.items() if v.get()]
  with connect() as c:
   for p_name in selected_projs:
    p_path = LOG / p_name
    c.execute('INSERT OR IGNORE INTO favorites(project,path,kind,created) VALUES(?,?,?,?)', (p_name, str(p_path.resolve()), 'folder', stamp(time.time())))
  self.selected_home_projects.clear();self.update_bulk_action_bar();self.render_projects()

 def toggle_project_favorite(self, p_name, p_path):
  with connect() as c:
   exists = c.execute('SELECT 1 FROM favorites WHERE project=? AND path=?', (p_name, str(p_path.resolve()))).fetchone()
   if exists: c.execute('DELETE FROM favorites WHERE project=? AND path=?', (p_name, str(p_path.resolve())))
   else: c.execute('INSERT INTO favorites(project,path,kind,created) VALUES(?,?,?,?)', (p_name, str(p_path.resolve()), 'folder', stamp(time.time())))
  self.render_projects()

 def show_project_context_menu(self, event, p_name, p_path):
  menu = tk.Menu(self, tearoff=0, bg='white', fg='#19394e', font=('Segoe UI', 10))
  is_fav = False
  with connect() as c:
   is_fav = bool(c.execute('SELECT 1 FROM favorites WHERE project=? AND path=?', (p_name, str(p_path.resolve()))).fetchone())
  fav_label = '☆ إزالة من المفضلة' if is_fav else '★ إضافة للمفضلة'
  
  menu.add_command(label='📂 فتح المشروع', command=lambda: self.open_project(p_path))
  menu.add_command(label=fav_label, command=lambda: self.toggle_project_favorite(p_name, p_path))
  menu.add_separator()
  menu.add_command(label='📦 تصدير المشروع', command=lambda: self._quick_export_project(p_name))
  menu.add_command(label='🗑 خيارات الحذف...', command=lambda: self.delete_project_dialog(p_name, p_path), foreground='#bd4856')
  menu.tk_popup(event.x_root, event.y_root)

 def _quick_export_project(self, p_name):
  save_path = filedialog.asksaveasfilename(title='حفظ ملف التصدير', defaultextension='.zip', filetypes=[('ZIP Files', '*.zip')], initialfile=f"{p_name}_backup.zip", parent=self)
  if save_path and hasattr(self, '_sync_run_export_thread'):
   self._sync_run_export_thread([p_name], save_path, True)

 def delete_project_dialog(self, p_name, p_path):
  dialog = tk.Toplevel(self);dialog.title('خيارات حذف المشروع');dialog.configure(bg='#eef3f7');dialog.geometry('450x250');dialog.transient(self);dialog.grab_set()
  tk.Label(dialog, text=f'حذف مشروع: {p_name}', bg='#eef3f7', fg='#19394e', font=('Segoe UI', 13, 'bold')).pack(pady=(20, 5))
  tk.Label(dialog, text='اختر طريقة الحذف المناسبة لك:', bg='#eef3f7', fg='#617789', font=('Segoe UI', 10)).pack(pady=(0, 20))
  
  def hide_project():
   try:
    new_path = p_path.parent / ('.' + p_name)
    p_path.rename(new_path)
    with connect() as c:
     c.execute("DELETE FROM files WHERE project=?", (p_name,))
     c.execute("DELETE FROM favorites WHERE project=?", (p_name,))
     c.execute("DELETE FROM tasks WHERE project=?", (p_name,))
    messagebox.showinfo('تم الإخفاء', 'تم تنويم وإخفاء المشروع من الواجهة والمهام، لكن ملفاته لا تزال موجودة في مجلد Log.', parent=self)
    dialog.destroy();self.render_projects()
   except Exception as e:
    messagebox.showerror('خطأ', str(e), parent=dialog)
    
  def deep_delete():
   if messagebox.askyesno('تأكيد الحذف الجذري', 'سيتم مسح جميع الملفات من القرص الصلب نهائياً. هل أنت متأكد؟', parent=dialog):
    try:
     try: import send2trash; send2trash.send2trash(str(p_path))
     except ImportError: shutil.rmtree(str(p_path), ignore_errors=True)
     with connect() as c:
      c.execute("DELETE FROM files WHERE project=?", (p_name,))
      c.execute("DELETE FROM favorites WHERE project=?", (p_name,))
      c.execute("DELETE FROM tasks WHERE project=?", (p_name,))
     messagebox.showinfo('تم الحذف', 'تم حذف المشروع نهائياً.', parent=self)
     dialog.destroy();self.render_projects()
    except Exception as e:
     messagebox.showerror('خطأ', str(e), parent=dialog)

  tk.Button(dialog, text='💤 تنويم (إخفاء من الواجهة فقط)', command=hide_project, bg='#087e8b', fg='white', font=('Segoe UI', 10, 'bold'), width=30).pack(pady=5)
  tk.Button(dialog, text='🗑 حذف جذري (مسح نهائي من القرص)', command=deep_delete, bg='#bd4856', fg='white', font=('Segoe UI', 10, 'bold'), width=30).pack(pady=5)

 def home_project_filter(self,mode):
  self.home_filter_mode={'recent':'visited'}.get(mode,mode)
  if getattr(self,'home_sort_button',None):self.home_sort_button.configure(state='disabled' if self.home_filter_mode in ('visited','added') else 'normal')
  for key,button in getattr(self,'home_filter_buttons',{}).items():
   active=key==self.home_filter_mode;button.configure(bg='#3478e5' if active else '#e5ecf0',fg='white' if active else '#526b7b',font=('Segoe UI',9,'bold' if active else 'normal'))
  self.render_projects()

 def toggle_project_sort(self):
  self.home_sort_mode='recent' if getattr(self,'home_sort_mode','name')=='name' else 'name'
  sort_text = '☷ الترتيب: ' + ('الأحدث' if self.home_sort_mode=='recent' else 'الأبجدي')
  self.home_sort_button.configure(text=sort_text)
  self.render_projects()

 def schedule_home_refresh(self,event=None):
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
  
  with connect() as c:
   counts={r['project']:(r['n'],r['latest']) for r in c.execute('select project,count(*) n,max(mtime) latest from files group by project')}
   fav_rows = c.execute('SELECT project FROM favorites WHERE kind="folder"').fetchall()
   favorite_projects = {r['project'] for r in fav_rows}

  projects=[p for p in LOG.iterdir() if p.is_dir() and not p.name.startswith('.') and is_project_path(p)]
  mode=getattr(self,'home_filter_mode','all')
  
  if mode=='favorites': projects=[p for p in projects if p.name in favorite_projects]
  elif mode=='visited':
   with connect() as c:visited=[r['project'] for r in c.execute('select project from project_visits order by last_visit desc limit 8')]
   by_name={p.name:p for p in projects};projects=[by_name[name] for name in visited if name in by_name]
  elif mode=='added': projects=sorted(projects,key=lambda p:(p.stat().st_ctime if p.exists() else 0),reverse=True)[:8]
  
  if mode not in ('visited','added'):
   projects=sorted(projects,key=(lambda p:p.stat().st_mtime) if getattr(self,'home_sort_mode','name')=='recent' else (lambda p:p.name.lower()),reverse=getattr(self,'home_sort_mode','name')=='recent')
  
  query=getattr(self,'project_search',tk.StringVar(value='')).get().strip().casefold()
  if query and query!='ابحث عن مشروع':projects=[p for p in projects if query in p.name.casefold()]
  self.project_card_photos=[]
  if hasattr(self,'project_count_label'):self.project_count_label.configure(text=f'{len(projects)} مشروع')
  
  if not projects:
   empty=tk.Frame(self.cards,bg='white',highlightbackground='#d8e2ea',highlightthickness=1);empty.pack(fill='x',pady=25)
   if mode == 'favorites':
    tk.Label(empty,text='لا توجد مشاريع في المفضلة',font=('Segoe UI',17,'bold'),fg='#15374d',bg='white').pack(anchor='center',pady=(45,15))
    tk.Label(empty,text='أضف مشاريع للمفضلة باستخدام زر النجمة للوصول السريع إليها.',font=('Segoe UI',11),fg='#617789',bg='white').pack(anchor='center',pady=(0,45))
   else:
    tk.Button(empty,text='＋ إنشاء مشروع جديد',command=self.new_project,bg='#087e8b',fg='white',activebackground='#066b76',activeforeground='white',relief='flat',font=('Segoe UI',14,'bold'),padx=32,pady=12,cursor='hand2').pack(anchor='center',pady=(45,15))
    tk.Label(empty,text='ابدأ بمشروعك الأول',font=('Segoe UI',17,'bold'),fg='#15374d',bg='white').pack(anchor='center',pady=(0,6))
   return
  
  screen_width=max(720,self.winfo_screenwidth());window_width=min(1440,screen_width-40);card_area_width=max(280,window_width-84);columns=max(1,min(4,card_area_width//280))
  for col in range(max(columns,getattr(self,'project_columns',0))):self.cards.grid_columnconfigure(col,weight=1 if col<columns else 0,uniform='project-card' if col<columns else '')
  self.project_columns=columns
  
  for i,p in enumerate(projects):
   if p.name not in self.selected_home_projects: self.selected_home_projects[p.name] = tk.BooleanVar(value=False)
   indexed=counts.get(p.name);n=indexed[0] if indexed else None;count_text=f'{n:,} ملف' if n is not None else 'جارٍ تجهيز الفهرس'
   try:
    child_count=sum(1 for x in p.iterdir() if x.is_dir() and not x.name.startswith('.'))
    latest=indexed[1] if indexed and indexed[1] else p.stat().st_mtime;modified=datetime.fromtimestamp(latest).strftime('%d-%m-%Y')
   except OSError:child_count=0;modified='—'
   
   box=tk.Frame(self.cards,bg='white',highlightbackground='#d7e1e7',highlightthickness=1,cursor='hand2');box.grid(row=i//columns,column=i%columns,sticky='nsew',padx=7,pady=7)
   
   is_fav = p.name in favorite_projects
   star_btn = tk.Button(box, text='★' if is_fav else '☆', fg='#d69637' if is_fav else '#b0c4cf', bg='white', relief='flat', font=('Segoe UI', 16), cursor='hand2', command=lambda proj_name=p.name, proj_path=p: self.toggle_project_favorite(proj_name, proj_path))
   star_btn.place(relx=0.03, rely=0.03, anchor='nw')

   chk = tk.Checkbutton(box, variable=self.selected_home_projects[p.name], bg='white', activebackground='white', cursor='hand2', command=self.update_bulk_action_bar)
   chk.place(relx=0.97, rely=0.03, anchor='ne')

   image_path=None
   try:image_path=next(x for x in p.rglob('*') if x.is_file() and x.suffix.lower() in ('.png','.jpg','.jpeg','.bmp','.tif','.tiff'))
   except (StopIteration,OSError):pass
   
   try:
    if image_path:
     with Image.open(image_path) as src:thumb=ImageOps.fit(src.convert('RGB'),(430,175),method=Image.Resampling.LANCZOS)
     photo=ImageTk.PhotoImage(thumb);self.project_card_photos.append(photo)
     pic=tk.Label(box,image=photo,bg='#dce8ed',borderwidth=0);pic.pack(fill='x')
    else:
     art=tk.Canvas(box,height=145,bg='#dce8ed',highlightthickness=0);art.pack(fill='x');art.create_rectangle(0,0,430,145,fill='#dce8ed',outline='');art.create_line(0,110,110,35,225,98,340,25,430,105,fill='#83b4bc',width=3);art.create_text(390,112,text='RASD / PROJECT',anchor='e',fill='#416a79',font=('Segoe UI',9,'bold'))
   except Exception:
    art=tk.Frame(box,bg='#dce8ed',height=145);art.pack(fill='x');art.pack_propagate(False)
   
   details=tk.Frame(box,bg='white');details.pack(fill='x',padx=11,pady=(9,0))
   tk.Label(details,text=p.name,font=('Segoe UI',11,'bold'),fg='#253c4b',bg='white',anchor='e').pack(anchor='e',fill='x')
   tk.Label(details,text=f'▤ {count_text} ◷ {modified}',font=('Segoe UI',8),fg='#87949d',bg='white',anchor='e').pack(anchor='e',fill='x',pady=(4,0))
   
   tags=[]
   try:
    with connect() as c:tags=[r['tag'] for r in c.execute('select t.tag,count(*) n from tags t join files f on f.path=t.path where f.project=? group by t.tag order by n desc limit 3',(p.name,))]
   except Exception:pass
   
   tagrow=tk.Frame(box,bg='white');tagrow.pack(fill='x',padx=8,pady=(7,10))
   if tags:
    for tag in tags:tk.Label(tagrow,text='#'+tag.lstrip('#'),bg='#f0f3f5',fg='#687987',font=('Segoe UI',7),padx=6,pady=3).pack(side='left',padx=2)
   else:tk.Label(tagrow,text=f'{child_count} مجلدات',bg='#f0f3f5',fg='#687987',font=('Segoe UI',7),padx=6,pady=3).pack(side='left',padx=2)
   
   def bind_open(widget,project=p):
    if widget.winfo_class() not in ('Checkbutton', 'Button'):
     widget.bind('<Button-1>',lambda e,x=project:self.open_project(x))
    for child in widget.winfo_children():bind_open(child,project)
   bind_open(box)
   
   def bind_context(widget, project_name=p.name, project_path=p):
    widget.bind('<Button-3>', lambda e, n=project_name, pt=project_path: self.show_project_context_menu(e, n, pt))
    for child in widget.winfo_children(): bind_context(child, project_name, project_path)
   bind_context(box)

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
  project = project or getattr(self,'project','')
  if not project: return
  
  target = str(Path(path).resolve()) if path else None
  when = occurred_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
  
  with connect() as c:
   if project == 'ALL':
    projs = [r[0] for r in c.execute("SELECT DISTINCT project FROM files").fetchall()]
    if projs: c.executemany("INSERT INTO activity_log(project,action,details,path,occurred_at) VALUES(?,?,?,?,?)", [(p, str(action), str(details), target, when) for p in projs])
   else:
    c.execute("INSERT INTO activity_log(project,action,details,path,occurred_at) VALUES(?,?,?,?,?)", (project, str(action), str(details), target, when))

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
   
   # الفتح دائماً يبدأ من المسار الرئيسي للمشروع (ملفات المجلدات) بدلاً من آخر مجلد فرعي
   self.mode='folder'
   self.view_mode='files'
   self.folder_group='الكل'
   self.project_group='الكل'
   self.discipline='الكل'
   self.sort_col=state['sort_col'] if state and state['sort_col'] else 'name'
   self.sort_desc=bool(state['sort_desc']) if state else False
   try:self.column_widths=json.loads(state['column_widths']) if state and state['column_widths'] else {}
   except Exception:self.column_widths={}
   self.current=root
   self.preview_current_path=None

  self.log_activity('فتح مشروع',f'تم فتح المشروع «{self.project}»',path=root)
  
  self.build_explorer();self.animate_window_in();self.scan_summary.set('جارٍ فهرسة ملفات المشروع...');self.start_scan_progress();threading.Thread(target=self.scan_worker,args=(root,),daemon=True).start()

 def rebase_project_index(self,root):
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