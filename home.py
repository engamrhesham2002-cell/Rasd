# Rasd - الشاشة الرئيسية وقائمة المشاريع (مع ضبط اتجاه العربية ومحاذاة الكروت لليمين وإيقاف السكرول الفارغ)
from common import *
from update_utils import *
from storage import *
from repositories import project_summary
from perf import timed_method
import shutil

class HomeMixin:
 def show_home(self):
  self.invalidate_home_summary()
  if hasattr(self,'watch_stop'):self.watch_stop.set();self.watch_root=None
  self.clear();self.project='';self.configure(bg=BG_VOID);self.title('Rasd // Project Matrix')
  self.selected_home_projects = {}
  
  # === الشريط العلوي (Polybar Style) ===
  top=tk.Frame(self,bg=BG_HEADER,height=58,highlightbackground=BORDER_DIM,highlightthickness=1);top.pack(fill='x',padx=2,pady=(2,0));top.pack_propagate(False)
  brand=tk.Frame(top,bg=BG_HEADER,cursor='hand2');brand.pack(side='left',padx=24)
  try:
   with Image.open(Path(getattr(sys,'_MEIPASS',BASE))/'Assets'/'rasd_logo.png') as source:
    self.brand_icon=ImageTk.PhotoImage(source.convert('RGBA').resize((32,32),Image.Resampling.LANCZOS))
    b_ico=tk.Label(brand,image=self.brand_icon,bg=BG_HEADER,cursor='hand2');b_ico.pack(side='left',padx=(0,8))
  except Exception:
   b_ico=tk.Label(brand,text='[>_]',font=(MONO_FONT,14,'bold'),fg=ACCENT_MATRIX,bg=BG_HEADER,cursor='hand2');b_ico.pack(side='left',padx=(0,8))
  b_t1=tk.Label(brand,text='[ RASD ]',font=(MONO_FONT,14,'bold'),fg=ACCENT_MATRIX,bg=BG_HEADER,cursor='hand2');b_t1.pack(side='left')
  b_t2=tk.Label(brand,text='SYS // ENG. Amr Hesham',font=(MONO_FONT,8),fg=FG_MUTED,bg=BG_HEADER,cursor='hand2');b_t2.pack(side='left',padx=(9,0),pady=(6,0))
  for w in (brand, b_ico, b_t1, b_t2):
   w.bind('<Button-1>', lambda e: self.show_home())
  
  for btn_text, cmd in [('حماية البرنامج', self.manage_password), ('تحديث البرنامج', lambda: self.check_for_updates(manual=True)), ('استيراد / تصدير', self.show_sync_dialog), ('مسار الحفظ', self.change_log_path), ('مجلد Log', lambda: os.startfile(str(LOG)))]:
   tk.Button(top,text=RLM+btn_text,command=cmd,bg=BG_PANEL,fg=ACCENT_CYAN,activebackground=BG_SELECTED,activeforeground=ACCENT_MATRIX,relief='solid',borderwidth=1,font=(TERM_FONT,9,'bold'),padx=10,cursor='hand2').pack(side='right',padx=3,pady=12)
  
  # === منطقة المحتوى الرئيسية ===
  wrap=tk.Frame(self,bg=BG_VOID);wrap.pack(fill='both',expand=True,padx=32,pady=(12,0))
  controls=tk.Frame(wrap,bg=BG_VOID);controls.pack(fill='x',pady=(3,12))
  tk.Button(controls,text=RLM+'＋ مشروع جديد',command=self.new_project,bg=BG_HEADER,fg=ACCENT_MATRIX,activebackground=ACCENT_MATRIX,activeforeground=BG_VOID,relief='solid',borderwidth=1,font=(TERM_FONT,10,'bold'),padx=14,pady=6,cursor='hand2').pack(side='right',padx=(12,0))
  
  self.project_search=tk.StringVar(value='ابحث عن مشروع...')
  search_wrap=tk.Frame(controls,bg=BG_PANEL,highlightbackground=BORDER_DIM,highlightthickness=1);search_wrap.pack(side='right',fill='x',expand=True)
  tk.Label(search_wrap,text='>_',font=(MONO_FONT,11,'bold'),fg=ACCENT_CYAN,bg=BG_PANEL).pack(side='right',padx=(10,3))
  entry=tk.Entry(search_wrap,textvariable=self.project_search,bg=BG_PANEL,fg=FG_PRIMARY,insertbackground=ACCENT_MATRIX,relief='flat',font=(TERM_FONT,10),justify='right');entry.pack(side='right',fill='x',expand=True,ipady=7,padx=6)
  entry.bind('<FocusIn>',lambda e:entry.delete(0,'end') if entry.get()=='ابحث عن مشروع...' else None);entry.bind('<FocusOut>',lambda e:entry.insert(0,'ابحث عن مشروع...') if not entry.get() else None)
  
  self.home_filter_mode=getattr(self,'home_filter_mode','all');self.home_filter_buttons={}
  
  sort_text = RLM + 'الترتيب: ' + ('الأحدث' if getattr(self,'home_sort_mode','name')=='recent' else 'الأبجدي')
  self.home_sort_button=tk.Button(controls,text=sort_text,command=self.toggle_project_sort,bg=BG_PANEL,fg=FG_PRIMARY,activebackground=BG_SELECTED,relief='solid',borderwidth=1,font=(TERM_FONT,9,'bold'),padx=10,pady=6,cursor='hand2',state='disabled' if self.home_filter_mode in ('visited','added') else 'normal')
  self.home_sort_button.pack(side='left',padx=(7,0))
  
  for label,command in reversed([('الكل','all'),('المفضلة','favorites'),('آخر زيارة','visited'),('أضيف حديثاً','added')]):
   active=command==self.home_filter_mode
   b=tk.Button(controls,text=RLM+label,command=lambda c=command:self.home_project_filter(c),bg=BG_SELECTED if active else BG_PANEL,fg=ACCENT_MATRIX if active else FG_MUTED,activebackground=BG_SELECTED,relief='solid',borderwidth=1,font=(TERM_FONT,9,'bold' if active else 'normal'),padx=12,pady=6,cursor='hand2');b.pack(side='left',padx=3);self.home_filter_buttons[command]=b
  
  project_total=sum(1 for p in LOG.iterdir() if p.is_dir() and not p.name.startswith('.') and is_project_path(p))
  with connect() as c:
   indexed_total=c.execute('select count(*) from files').fetchone()[0]
   favorite_total=c.execute('select count(*) from favorites').fetchone()[0]
   
  summary=tk.Frame(wrap,bg=BG_VOID);summary.pack(fill='x',pady=(0,7))
  self.home_stat_labels={}
  for key,title,value,accent in [('projects','المشاريع النشطة',f'{project_total:,}',ACCENT_CYAN),('files','الملفات المفهرسة',f'{indexed_total:,}',ACCENT_MATRIX),('favorites','المفضلة',f'{favorite_total:,}',ACCENT_AMBER)]:
   tile=tk.Frame(summary,bg=BG_PANEL,highlightbackground=BORDER_DIM,highlightthickness=1);tile.pack(side='right',fill='x',expand=True,padx=(5,0))
   value_label=tk.Label(tile,text=value,bg=BG_PANEL,fg=accent,font=(MONO_FONT,16,'bold'));value_label.pack(anchor='e',padx=12,pady=(6,0));self.home_stat_labels[key]=value_label
   tk.Label(tile,text=RLM+title,bg=BG_PANEL,fg=FG_MUTED,font=(TERM_FONT,9,'bold')).pack(anchor='e',padx=12,pady=(0,6))
  self.project_count_label=tk.Label(wrap,text='',bg=BG_VOID,fg=FG_MUTED,font=(TERM_FONT,9));self.project_count_label.pack(anchor='e',pady=(0,2))
  
  self.cards_canvas = tk.Canvas(wrap, bg=BG_VOID, highlightthickness=0)
  self.cards_canvas._no_global_scroll = True
  self.cards_scroll = ttk.Scrollbar(wrap, orient='vertical', command=self.cards_canvas.yview)
  self.cards = tk.Frame(self.cards_canvas, bg=BG_VOID)
  
  self.cards_scroll.pack(side='left', fill='y')
  self.cards_canvas.pack(side='right', fill='both', expand=True)
  self.cards_canvas.configure(yscrollcommand=self.cards_scroll.set)
  self.cards_canvas.create_window((0, 0), window=self.cards, anchor='nw', tags='cards_frame')
  
  def _on_cards_configure(event=None):
   if not self.cards_canvas.winfo_exists() or not self.cards.winfo_exists():
    return
   cw = max(100, self.cards_canvas.winfo_width())
   ch = max(100, self.cards_canvas.winfo_height())
   req_h = self.cards.winfo_reqheight()
   self.cards_canvas.itemconfig('cards_frame', width=cw)
   self.cards_canvas.configure(scrollregion=(0, 0, cw, max(ch, req_h)))
   if req_h <= ch:
    self.cards_canvas.yview_moveto(0.0)

  self.cards.bind('<Configure>', _on_cards_configure)
  self.cards_canvas.bind('<Configure>', _on_cards_configure)

  def _on_mousewheel(event):
   if self.cards.winfo_exists() and self.cards_canvas.winfo_exists():
    if self.cards.winfo_reqheight() > self.cards_canvas.winfo_height() + 8:
     self.cards_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
   return 'break'
  self.cards_canvas.bind("<MouseWheel>", _on_mousewheel)
  self.cards.bind("<MouseWheel>", _on_mousewheel)

  self.bulk_action_bar = tk.Frame(self, bg=BG_HEADER, height=45, highlightbackground=ACCENT_CYAN, highlightthickness=1)
  self.bulk_action_bar.pack(fill='x', side='bottom');self.bulk_action_bar.pack_propagate(False)
  self.bulk_label = tk.Label(self.bulk_action_bar, text='', bg=BG_HEADER, fg=ACCENT_CYAN, font=(TERM_FONT, 10, 'bold'))
  self.bulk_label.pack(side='right', padx=15, pady=10)
  tk.Button(self.bulk_action_bar, text=RLM+'🗑 حذف المحدد', command=self.bulk_delete_projects, bg=BG_PANEL, fg=ACCENT_DANGER, relief='solid', borderwidth=1, font=(TERM_FONT, 9, 'bold'), padx=10, cursor='hand2').pack(side='left', padx=10, pady=8)
  tk.Button(self.bulk_action_bar, text=RLM+'★ المفضلة', command=self.bulk_favorite_projects, bg=BG_PANEL, fg=ACCENT_AMBER, relief='solid', borderwidth=1, font=(TERM_FONT, 9, 'bold'), padx=10, cursor='hand2').pack(side='left', padx=5, pady=8)
  self.bulk_action_bar.pack_forget()

  self.footer = tk.Frame(self, bg=BG_HEADER, height=45, highlightbackground=BORDER_DIM, highlightthickness=1)
  self.footer.pack(fill='x', side='bottom', padx=2, pady=(0,2));self.footer.pack_propagate(False)
  tk.Button(self.footer, text=RLM+'☑ مهامي', command=self.show_tasks, bg=BG_PANEL, fg=ACCENT_MATRIX, activebackground=BG_SELECTED, relief='solid', borderwidth=1, font=(TERM_FONT, 10, 'bold'), padx=15, pady=4, cursor='hand2').pack(side='right', padx=10, pady=6)
  tk.Button(self.footer, text=RLM+'▦ التقويم', command=lambda:self.show_task_calendar(), bg=BG_PANEL, fg=ACCENT_CYAN, activebackground=BG_SELECTED, relief='solid', borderwidth=1, font=(TERM_FONT, 10, 'bold'), padx=15, pady=4, cursor='hand2').pack(side='right', padx=6, pady=6)

  self.project_card_photos=[]
  self.project_search.trace_add('write',lambda *_:self.render_projects());self.render_projects()
  self.animate_window_in()

 def change_log_path(self):
  dialog = tk.Toplevel(self);dialog.title('مسار الحفظ (Log)');dialog.configure(bg=BG_VOID);dialog.geometry('450x220');dialog.transient(self);dialog.grab_set()
  tk.Label(dialog, text=RLM+'تغيير مسار حفظ المشاريع والبيانات', bg=BG_VOID, fg=ACCENT_MATRIX, font=(TERM_FONT, 12, 'bold')).pack(pady=(20, 10))
  tk.Label(dialog, text=f'المسار الحالي:\n{LOG}', bg=BG_VOID, fg=FG_MUTED, font=(TERM_FONT, 9), justify='center').pack(pady=(0, 20))
  
  btn_frame = tk.Frame(dialog, bg=BG_VOID);btn_frame.pack(fill='x', padx=20)
  
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
   self.footer.pack_forget();self.bulk_label.configure(text=RLM+f'تم تحديد {selected_count} مشروع');self.bulk_action_bar.pack(fill='x', side='bottom')
  else:
   self.bulk_action_bar.pack_forget();self.footer.pack(fill='x', side='bottom', padx=2, pady=(0,2))

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
  self.selected_home_projects.clear();self.update_bulk_action_bar();self.invalidate_home_summary();self.render_projects()

 def bulk_favorite_projects(self):
  selected_projs = [p for p, v in self.selected_home_projects.items() if v.get()]
  with connect() as c:
   for p_name in selected_projs:
    p_path = LOG / p_name
    c.execute('INSERT OR IGNORE INTO favorites(project,path,kind,created) VALUES(?,?,?,?)', (p_name, str(p_path.resolve()), 'folder', stamp(time.time())))
  self.selected_home_projects.clear();self.update_bulk_action_bar();self.invalidate_home_summary();self.render_projects()

 def toggle_project_favorite(self, p_name, p_path):
  with connect() as c:
   exists = c.execute('SELECT 1 FROM favorites WHERE project=? AND path=?', (p_name, str(p_path.resolve()))).fetchone()
   if exists: c.execute('DELETE FROM favorites WHERE project=? AND path=?', (p_name, str(p_path.resolve())))
   else: c.execute('INSERT INTO favorites(project,path,kind,created) VALUES(?,?,?,?)', (p_name, str(p_path.resolve()), 'folder', stamp(time.time())))
  self.invalidate_home_summary();self.render_projects()

 def show_project_context_menu(self, event, p_name, p_path):
  menu = tk.Menu(self, tearoff=0, bg=BG_PANEL, fg=FG_PRIMARY, activebackground=BG_SELECTED, activeforeground=ACCENT_MATRIX, font=(TERM_FONT, 10))
  is_fav = False
  with connect() as c:
   is_fav = bool(c.execute('SELECT 1 FROM favorites WHERE project=? AND path=?', (p_name, str(p_path.resolve()))).fetchone())
  fav_label = RLM + ('★ إزالة من المفضلة' if is_fav else '★ إضافة للمفضلة')
  
  menu.add_command(label=RLM+'📂 فتح المشروع', command=lambda: self.open_project(p_path))
  menu.add_command(label=fav_label, command=lambda: self.toggle_project_favorite(p_name, p_path))
  menu.add_separator()
  menu.add_command(label=RLM+'🖼 تعيين صورة للمشروع...', command=lambda: self.choose_project_cover(p_name))
  if get_project_cover(p_name):
   menu.add_command(label=RLM+'× إزالة صورة المشروع', command=lambda: self.remove_project_cover(p_name))
  menu.add_separator()
  menu.add_command(label=RLM+'📦 تصدير المشروع', command=lambda: self._quick_export_project(p_name))
  menu.add_command(label=RLM+'🗑 خيارات الحذف...', command=lambda: self.delete_project_dialog(p_name, p_path), foreground=ACCENT_DANGER)
  menu.tk_popup(event.x_root, event.y_root)

 def choose_project_cover(self, p_name):
  """اختيار صورة مخصصة للمشروع من أي مكان على الجهاز ونسخها لمجلد بيانات البرنامج."""
  path = filedialog.askopenfilename(
   parent=self, title='اختر صورة للمشروع',
   filetypes=[('Images', '*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.webp;*.tif;*.tiff'), ('All files', '*.*')])
  if not path: return
  try:
   set_project_cover(p_name, path)
  except Exception as e:
   messagebox.showerror('خطأ', str(e), parent=self); return
  self.invalidate_home_summary()
  self.render_projects()

 def remove_project_cover(self, p_name):
  """إزالة صورة الغلاف المخصصة والعودة للصورة التلقائية."""
  try:
   clear_project_cover(p_name)
  except Exception as e:
   messagebox.showerror('خطأ', str(e), parent=self); return
  self.invalidate_home_summary()
  self.render_projects()

 def _quick_export_project(self, p_name):
  save_path = filedialog.asksaveasfilename(title='حفظ ملف التصدير', defaultextension='.zip', filetypes=[('ZIP Files', '*.zip')], initialfile=f"{p_name}_backup.zip", parent=self)
  if save_path and hasattr(self, '_sync_run_export_thread'):
   self._sync_run_export_thread([p_name], save_path, True)

 def delete_project_dialog(self, p_name, p_path):
  dialog = tk.Toplevel(self);dialog.title('خيارات حذف المشروع');dialog.configure(bg=BG_VOID);dialog.geometry('450x250');dialog.transient(self);dialog.grab_set()
  tk.Label(dialog, text=RLM+f'حذف مشروع: {p_name}', bg=BG_VOID, fg=ACCENT_MATRIX, font=(TERM_FONT, 13, 'bold')).pack(pady=(20, 5))
  tk.Label(dialog, text=RLM+'اختر طريقة الحذف المناسبة لك:', bg=BG_VOID, fg=FG_MUTED, font=(TERM_FONT, 10)).pack(pady=(0, 20))
  
  def hide_project():
   try:
    new_path = p_path.parent / ('.' + p_name)
    p_path.rename(new_path)
    with connect() as c:
     c.execute("DELETE FROM files WHERE project=?", (p_name,))
     c.execute("DELETE FROM favorites WHERE project=?", (p_name,))
     c.execute("DELETE FROM tasks WHERE project=?", (p_name,))
    messagebox.showinfo('تم الإخفاء', 'تم تنويم وإخفاء المشروع من الواجهة والمهام، لكن ملفاته لا تزال موجودة في مجلد Log.', parent=self)
    dialog.destroy();self.invalidate_home_summary();self.render_projects()
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
     dialog.destroy();self.invalidate_home_summary();self.render_projects()
    except Exception as e:
     messagebox.showerror('خطأ', str(e), parent=dialog)

  tk.Button(dialog, text=RLM+'💤 تنويم (إخفاء من الواجهة فقط)', command=hide_project, bg=BG_HEADER, fg=ACCENT_CYAN, font=(TERM_FONT, 10, 'bold'), width=30).pack(pady=5)
  tk.Button(dialog, text=RLM+'🗑 حذف جذري (مسح نهائي من القرص)', command=deep_delete, bg=BG_HEADER, fg=ACCENT_DANGER, font=(TERM_FONT, 10, 'bold'), width=30).pack(pady=5)

 def home_project_filter(self,mode):
  self.home_filter_mode={'recent':'visited'}.get(mode,mode)
  if getattr(self,'home_sort_button',None):self.home_sort_button.configure(state='disabled' if self.home_filter_mode in ('visited','added') else 'normal')
  for key,button in getattr(self,'home_filter_buttons',{}).items():
   active=key==self.home_filter_mode;button.configure(bg=BG_SELECTED if active else BG_PANEL,fg=ACCENT_MATRIX if active else FG_MUTED,font=(TERM_FONT,9,'bold' if active else 'normal'))
  self.render_projects()

 def toggle_project_sort(self):
  self.home_sort_mode='recent' if getattr(self,'home_sort_mode','name')=='name' else 'name'
  sort_text = RLM + 'الترتيب: ' + ('الأحدث' if self.home_sort_mode=='recent' else 'الأبجدي')
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
   if getattr(self,'project','') or not cards or not cards.winfo_exists() or not cards.winfo_ismapped():return
   width=max(720,self.winfo_width() if self.winfo_width()>200 else self.winfo_screenwidth())
   columns=max(1,min(4,max(280,width-84)//280))
   if columns==getattr(self,'project_columns',0):
    if hasattr(self,'cards_canvas') and self.cards_canvas.winfo_exists():
     cw=max(100,self.cards_canvas.winfo_width());ch=max(100,self.cards_canvas.winfo_height());req_h=self.cards.winfo_reqheight()
     self.cards_canvas.configure(scrollregion=(0,0,cw,max(ch,req_h)))
    return
   self.after_idle(self.render_projects)
  except tk.TclError:pass

 def invalidate_home_summary(self):
  self._home_summary_cache=None

 def _load_home_summary(self):
  """ملخص المشاريع (أعداد/هاشتاجات/أغلفة) مع كاش قصير حتى لا تتكرر الاستعلامات مع كل ضغطة بحث."""
  cached=getattr(self,'_home_summary_cache',None)
  now=time.time()
  if cached and now-cached[0]<5.0:return cached[1]
  summary=project_summary()
  self._home_summary_cache=(now,summary)
  return summary

 @timed_method('home.render_projects')
 def render_projects(self):
  for w in self.cards.winfo_children():w.destroy()
  
  summary=self._load_home_summary()
  counts=summary['counts'];favorite_projects=summary['favorite_projects']
  tag_map=summary['tag_map'];cover_map=summary['cover_map']

  projects=[p for p in LOG.iterdir() if p.is_dir() and not p.name.startswith('.') and is_project_path(p)]
  active_total=len(projects)
  mode=getattr(self,'home_filter_mode','all')
  
  if mode=='favorites': projects=[p for p in projects if p.name in favorite_projects]
  elif mode=='visited':
   with connect() as c:visited=[r['project'] for r in c.execute('select project from project_visits order by last_visit desc limit 8')]
   by_name={p.name:p for p in projects};projects=[by_name[name] for name in visited if name in by_name]
  elif mode=='added': projects=sorted(projects,key=lambda p:(p.stat().st_ctime if p.exists() else 0),reverse=True)[:8]
  
  if mode not in ('visited','added'):
   projects=sorted(projects,key=(lambda p:p.stat().st_mtime) if getattr(self,'home_sort_mode','name')=='recent' else (lambda p:p.name.lower()),reverse=getattr(self,'home_sort_mode','name')=='recent')
  
  query=getattr(self,'project_search',tk.StringVar(value='')).get().strip().casefold()
  if query and query!='ابحث عن مشروع...':projects=[p for p in projects if query in p.name.casefold()]
  self.project_card_photos=[]
  stat_labels=getattr(self,'home_stat_labels',{})
  if 'projects' in stat_labels:stat_labels['projects'].configure(text=f'{active_total:,}')
  if 'files' in stat_labels:stat_labels['files'].configure(text=f'{sum(n for n,_ in counts.values()):,}')
  if 'favorites' in stat_labels:stat_labels['favorites'].configure(text=f'{len(favorite_projects):,}')
  if hasattr(self,'project_count_label'):self.project_count_label.configure(text=RLM+f'عدد المشاريع المعروضة: {len(projects)}')
  
  if not projects:
   empty=tk.Frame(self.cards,bg=BG_PANEL,highlightbackground=BORDER_DIM,highlightthickness=1);empty.pack(fill='x',pady=25)
   if mode == 'favorites':
    tk.Label(empty,text=RLM+'لا توجد مشاريع في المفضلة حالياً',font=(TERM_FONT,15,'bold'),fg=ACCENT_AMBER,bg=BG_PANEL).pack(anchor='center',pady=(35,10))
    tk.Label(empty,text=RLM+'اضغط على رمز النجمة على أي مشروع لتثبيته هنا.',font=(TERM_FONT,10),fg=FG_MUTED,bg=BG_PANEL).pack(anchor='center',pady=(0,35))
   else:
    tk.Button(empty,text=RLM+'＋ إنشاء مشروع جديد',command=self.new_project,bg=BG_HEADER,fg=ACCENT_MATRIX,activebackground=ACCENT_MATRIX,activeforeground=BG_VOID,relief='solid',borderwidth=1,font=(TERM_FONT,11,'bold'),padx=24,pady=10,cursor='hand2').pack(anchor='center',pady=(35,12))
    tk.Label(empty,text='root@rasd:~/ Log is empty',font=(MONO_FONT,11),fg=ACCENT_CYAN,bg=BG_PANEL).pack(anchor='center',pady=(0,35))
   self.cards.update_idletasks()
   if hasattr(self, 'cards_canvas') and self.cards_canvas.winfo_exists():
    self.cards_canvas.yview_moveto(0.0)
   return
  
  screen_width=max(720,self.winfo_width() if self.winfo_width()>200 else self.winfo_screenwidth())
  card_area_width=max(280,screen_width-84)
  columns=max(1,min(4,card_area_width//280))
  for col in range(max(columns,getattr(self,'project_columns',0))):self.cards.grid_columnconfigure(col,weight=1 if col<columns else 0,uniform='project-card' if col<columns else '')
  self.project_columns=columns
  
  for i,p in enumerate(projects):
   if p.name not in self.selected_home_projects: self.selected_home_projects[p.name] = tk.BooleanVar(value=False)
   indexed=counts.get(p.name);n=indexed[0] if indexed else None;count_text=f'{n:,} ملف' if n is not None else 'فهرسة جارية...'
   image_path=cover_map.get(p.name)
   try:
    children=list(p.iterdir())
    child_count=sum(1 for x in children if x.is_dir() and not x.name.startswith('.'))
    if not image_path:image_path=next((x for x in children if x.is_file() and x.suffix.lower() in ('.png','.jpg','.jpeg','.bmp','.tif','.tiff')),None)
    latest=indexed[1] if indexed and indexed[1] else p.stat().st_mtime;modified=datetime.fromtimestamp(latest).strftime('%d-%m-%Y')
   except OSError:child_count=0;modified='—'
   
   # في العربية يبدأ المشروع الأول من أقصى اليمين، وفي الإنجليزية من أقصى اليسار
   col_index = (columns - 1 - (i % columns)) if is_rtl() else (i % columns)
   box=tk.Frame(self.cards,bg=BG_PANEL,highlightbackground=BORDER_DIM,highlightthickness=1,cursor='hand2');box.grid(row=i//columns,column=col_index,sticky='nsew',padx=7,pady=7)
   
   def _box_enter(e, b=box): b.configure(highlightbackground=ACCENT_MATRIX)
   def _box_leave(e, b=box): b.configure(highlightbackground=BORDER_DIM)
   box.bind('<Enter>', _box_enter)
   box.bind('<Leave>', _box_leave)
   
   is_fav = p.name in favorite_projects
   star_btn = tk.Button(box, text='★' if is_fav else '☆', fg=ACCENT_AMBER if is_fav else FG_MUTED, bg=BG_PANEL, relief='flat', font=(TERM_FONT, 11, 'bold'), cursor='hand2', command=lambda proj_name=p.name, proj_path=p: self.toggle_project_favorite(proj_name, proj_path))
   star_btn.place(relx=0.03, rely=0.03, anchor='nw')

   chk = tk.Checkbutton(box, variable=self.selected_home_projects[p.name], bg=BG_PANEL, activebackground=BG_PANEL, selectcolor=BG_VOID, cursor='hand2', command=self.update_bulk_action_bar)
   chk.place(relx=0.97, rely=0.03, anchor='ne')

   try:
    if image_path:
     with Image.open(image_path) as src:thumb=ImageOps.fit(src.convert('RGB'),(430,175),method=Image.Resampling.LANCZOS)
     photo=ImageTk.PhotoImage(thumb);self.project_card_photos.append(photo)
     pic=tk.Label(box,image=photo,bg=BG_VOID,borderwidth=0);pic.pack(fill='x')
    else:
     art=tk.Canvas(box,height=145,bg=BG_VOID,highlightthickness=0);art.pack(fill='x')
     art._no_global_scroll = True
     art.create_rectangle(0,0,430,145,fill=BG_VOID,outline='')
     art.create_line(0,100, 80,40, 160,110, 240,30, 320,95, 430,50, fill=ACCENT_MATRIX, width=2)
     art.create_text(20, 25, text=f"root@rasd:~/{p.name[:22]}", anchor='nw', fill=ACCENT_CYAN, font=(MONO_FONT, 9, 'bold'))
   except Exception:
    art=tk.Frame(box,bg=BG_VOID,height=145);art.pack(fill='x');art.pack_propagate(False)
   
   details=tk.Frame(box,bg=BG_PANEL);details.pack(fill='x',padx=11,pady=(9,0))
   tk.Label(details,text=RLM+p.name,font=(TERM_FONT,11,'bold'),fg=FG_PRIMARY,bg=BG_PANEL,anchor='e').pack(anchor='e',fill='x')
   tk.Label(details,text=RLM+f'عدد الملفات: {count_text}   ·   آخر تعديل: {modified}',font=(TERM_FONT,8),fg=FG_MUTED,bg=BG_PANEL,anchor='e').pack(anchor='e',fill='x',pady=(4,0))
   
   tags=tag_map.get(p.name,[])[:3]
   
   tagrow=tk.Frame(box,bg=BG_PANEL);tagrow.pack(fill='x',padx=8,pady=(7,10))
   if tags:
    for tag in tags:tk.Label(tagrow,text='#'+tag.lstrip('#'),bg=BG_HEADER,fg=ACCENT_CYAN,font=(TERM_FONT,8,'bold'),padx=6,pady=3).pack(side='left',padx=2)
   else:tk.Label(tagrow,text=RLM+f'{child_count} مجلد فرعي',bg=BG_HEADER,fg=FG_MUTED,font=(TERM_FONT,8),padx=6,pady=3).pack(side='left',padx=2)
   
   def bind_open(widget,project=p):
    if widget.winfo_class() not in ('Checkbutton', 'Button'):
     widget.bind('<Button-1>',lambda e,x=project:self.open_project(x))
     widget.bind('<MouseWheel>', lambda e: self.cards_canvas.event_generate('<MouseWheel>', delta=e.delta))
    for child in widget.winfo_children():bind_open(child,project)
   bind_open(box)
   
   def bind_context(widget, project_name=p.name, project_path=p):
    widget.bind('<Button-3>', lambda e, n=project_name, pt=project_path: self.show_project_context_menu(e, n, pt))
    for child in widget.winfo_children(): bind_context(child, project_name, project_path)
   bind_context(box)

  self.cards.update_idletasks()
  if hasattr(self, 'cards_canvas') and self.cards_canvas.winfo_exists():
   cw = max(100, self.cards_canvas.winfo_width())
   ch = max(100, self.cards_canvas.winfo_height())
   req_h = self.cards.winfo_reqheight()
   self.cards_canvas.configure(scrollregion=(0, 0, cw, max(ch, req_h)))
   self.cards_canvas.yview_moveto(0.0)

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
  self.invalidate_home_summary();self.render_projects()

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

 @timed_method('home.open_project')
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
   # استعادة آخر مكان وفلاتر كان المستخدم واقف عليها في المشروع
   if state:
    if state['mode'] in ('folder','project'):self.mode=state['mode']
    if state['folder_filter']:self.folder_group=state['folder_filter']
    if state['project_filter']:self.project_group=state['project_filter']
    if state['discipline']:self.discipline=state['discipline']
    self._restore_tag_filter=state['tag_filter'] or 'الكل'
    saved_rel=str(state['current_rel'] or '').strip()
    if saved_rel:
     try:
      candidate=(root/saved_rel).resolve()
      candidate.relative_to(root)
      if candidate.is_dir():self.current=candidate
     except (OSError,ValueError):self.current=root
   else:
    self._restore_tag_filter='الكل'

  self.log_activity('فتح مشروع',f'تم فتح المشروع «{self.project}»',path=root)
  
  self.build_explorer();self.reset_empty_restored_filters();self.animate_window_in();self.scan_summary.set(RLM+'جارٍ فهرسة ملفات المشروع...');self.start_scan_progress();threading.Thread(target=self.scan_worker,args=(root,),daemon=True).start()

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
        time.sleep(1.2)
        if stop.is_set():break
        if self.root==root:
         try:self.scan_worker(root)
         except Exception:pass
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
    if self.root==root:
     try:self.scan_worker(root)
     except Exception:pass