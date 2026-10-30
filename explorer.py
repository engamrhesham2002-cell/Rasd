# Rasd - مستكشف الملفات: الواجهة، التبويبات، الفلاتر، المفضلة، الملفات المرتبطة
from common import *
from update_utils import *
from storage import *

class ExplorerMixin:
 def build_explorer(self):
  with connect() as c:
   c.execute('CREATE TABLE IF NOT EXISTS file_links(project TEXT, path1 TEXT, path2 TEXT, PRIMARY KEY(path1, path2))')
   c.execute('CREATE TABLE IF NOT EXISTS recycle_bin(id INTEGER PRIMARY KEY AUTOINCREMENT, project TEXT, original_path TEXT, bin_path TEXT, deleted_at TEXT)')
   c.execute('CREATE TABLE IF NOT EXISTS folder_specialty_catalog(project TEXT, tag TEXT, created TEXT, PRIMARY KEY(project, tag))')
   c.execute('INSERT OR IGNORE INTO folder_specialty_catalog(project, tag, created) SELECT DISTINCT project, tag, created FROM folder_tags WHERE project=?', (self.project,))

  self.clear()
  h = self.header(self.project, show_search=True)
  ttk.Button(h,text='← المشاريع',command=self.show_home).pack(side='right',padx=10,pady=12)
  
  self.explorer_page=tk.Frame(self,bg='#e8edf1');self.explorer_page.pack(fill='both',expand=True,padx=10,pady=9)
  self.query=tk.StringVar();self.mode=getattr(self,'mode','folder');self.project_group=getattr(self,'project_group','الكل');self.local_group='محتويات هذا المجلد';self.preview_photo=None;self.view_mode='files'
  self.explorer_page.grid_rowconfigure(0,weight=1);self.explorer_page.grid_columnconfigure(0,weight=0,minsize=350);self.explorer_page.grid_columnconfigure(1,weight=1);self.explorer_page.grid_columnconfigure(2,weight=0,minsize=176)
  self.preview_area=tk.Frame(self.explorer_page,bg='#eef2f5',highlightbackground='#d6e0e6',highlightthickness=1,width=350);self.preview_area.grid(row=0,column=0,sticky='nsew',padx=(0,8));self.preview_area.grid_propagate(False);self.preview_area.grid_rowconfigure(1,weight=1);self.preview_area.grid_columnconfigure(0,weight=1)
  preview_head=tk.Frame(self.preview_area,bg='#dfe7ec');preview_head.grid(row=0,column=0,sticky='ew')
  tk.Label(preview_head,text='معاينة وتفاصيل',bg='#dfe7ec',fg='#19394e',font=('Segoe UI',11,'bold')).pack(side='right',padx=13,pady=10)
  self.preview_panel_close=ttk.Button(preview_head,text='×',width=3,command=self.toggle_preview_panel);self.preview_panel_close.pack(side='left',padx=5,pady=4)
  self.preview_image=tk.Canvas(self.preview_area,bg='#eef2f5',highlightthickness=0);self.preview_image.grid(row=1,column=0,sticky='nsew',padx=7,pady=7);self.preview_image.bind('<ButtonPress-1>',self.preview_pan_start);self.preview_image.bind('<B1-Motion>',self.preview_pan_move);self.preview_image.bind('<MouseWheel>',self.preview_wheel)
  self.preview_meta=tk.Label(self.preview_area,text='اختر ملفًا لعرض المعاينة والتفاصيل.\n\nانقر مرة للمعاينة، وانقر مرتين لفتح الملف.',bg='white',fg='#526b7c',font=('Segoe UI',9),justify='right',anchor='ne',wraplength=330);self.preview_meta.grid(row=2,column=0,sticky='ew',padx=12,pady=(0,8))
  
  self.preview_related_container = tk.Frame(self.preview_area, bg='#edf2f5')
  self.preview_related_container.grid(row=3, column=0, sticky='ew', padx=8, pady=(0,4))
  self.preview_related_container.grid_columnconfigure(0, weight=1)
  self.preview_related_container.grid_remove()
  
  self.preview_related_canvas = tk.Canvas(self.preview_related_container, bg='#edf2f5', height=42, width=120, highlightthickness=0)
  self.preview_related_canvas.grid(row=0, column=0, sticky='ew')
  
  self.preview_related_label = tk.Label(self.preview_related_container, text='', bg='#edf2f5', fg='#617789', font=('Segoe UI',8,'bold'))
  self.preview_related_label.grid(row=0, column=1, sticky='e', padx=(3,5))
  
  self.preview_related_strip = tk.Frame(self.preview_related_canvas, bg='#edf2f5')
  self.preview_related_window = self.preview_related_canvas.create_window((0,0), window=self.preview_related_strip, anchor='nw')
  
  def _on_related_configure(event):
   self.preview_related_canvas.configure(scrollregion=self.preview_related_canvas.bbox('all'))
  self.preview_related_strip.bind('<Configure>', _on_related_configure)
  self.preview_related_canvas.bind('<MouseWheel>', lambda e: self.preview_related_canvas.xview_scroll(int(-e.delta/120), 'units'))
  self.preview_related_canvas.bind('<Shift-MouseWheel>', lambda e: self.preview_related_canvas.xview_scroll(int(-e.delta/120), 'units'))

  controls=tk.Frame(self.preview_area,bg='white');controls.grid(row=4,column=0,sticky='ew',padx=8,pady=(0,8))
  ttk.Button(controls,text='−',width=3,command=lambda:self.zoom_preview(-.15)).pack(side='left');ttk.Button(controls,text='＋',width=3,command=lambda:self.zoom_preview(.15)).pack(side='left');ttk.Button(controls,text='◀ صفحة',command=lambda:self.change_pdf_page(-1)).pack(side='right',padx=2);ttk.Button(controls,text='صفحة ▶',command=lambda:self.change_pdf_page(1)).pack(side='right',padx=2)
  self.center=tk.Frame(self.explorer_page,bg='#e8edf1');self.center.grid(row=0,column=1,sticky='nsew');self.center.grid_rowconfigure(5,weight=1);self.center.grid_columnconfigure(0,weight=1)
  self.project_tabs_bar=tk.Frame(self.center,bg='#e8edf1');self.project_nb=ttk.Notebook(self.project_tabs_bar);self.project_nb.bind('<<NotebookTabChanged>>',self.project_tab_changed)
  
  self.filter_bar=tk.Frame(self.center,bg='#e8edf1');self.filter_bar.grid(row=1,column=0,sticky='ew',pady=(0,1))
  self.filter_bar.grid_columnconfigure(0, weight=1)
  self.filter_bar.grid_columnconfigure(1, weight=0)
  
  self.project_filter_canvas=tk.Canvas(self.filter_bar,bg='#e8edf1',height=40,highlightthickness=0);self.project_filter_canvas.grid(row=0,column=0,sticky='ew')
  self.type_filter_controls=tk.Frame(self.project_filter_canvas,bg='#e8edf1');self.project_filter_window=self.project_filter_canvas.create_window((0,0),window=self.type_filter_controls,anchor='nw');self.type_filter_controls.bind('<Configure>',lambda e:self.project_filter_canvas.configure(scrollregion=self.project_filter_canvas.bbox('all')));self.project_filter_canvas.bind('<MouseWheel>',lambda e:self.project_filter_canvas.xview_scroll(int(-e.delta/120),'units'));self.project_filter_canvas.bind('<Shift-MouseWheel>',lambda e:self.project_filter_canvas.xview_scroll(int(-e.delta/120),'units'))
  
  filter_labels=tk.Frame(self.filter_bar,bg='#e8edf1');filter_labels.grid(row=0,column=1,sticky='e')
  self.filter_context=tk.Label(filter_labels,text='المشروع بالكامل',bg='#e8edf1',fg='#526a7a',font=('Segoe UI',9,'bold'));self.filter_context.pack(side='right',padx=8);tk.Label(filter_labels,text='أنواع ملفات المشروع',bg='#e8edf1',fg='#526a7a',font=('Segoe UI',9,'bold')).pack(side='right',padx=(4,2))
  
  self.folder_filter_bar=tk.Frame(self.center,bg='#e8edf1');self.folder_filter_bar.grid(row=2,column=0,sticky='ew',pady=(0,2))
  self.folder_filter_bar.grid_columnconfigure(0, weight=1);self.folder_filter_bar.grid_columnconfigure(1, weight=0)
  
  self.folder_menu_var=tk.StringVar(value='الكل');self.folder_menu_items={};self.folder_type_menu=tk.Menu(self.folder_filter_bar,tearoff=0,bg='#ffffff',fg='#19394e',activebackground='#dcebed',activeforeground='#19394e',font=('Segoe UI',9),borderwidth=1,relief='solid');self.folder_type_button=ttk.Menubutton(self.folder_filter_bar,textvariable=self.folder_menu_var,menu=self.folder_type_menu,style='Office.TMenubutton',direction='above');self.folder_type_button.grid(row=0,column=0,sticky='w',padx=5);self.folder_type_filter_controls=None
  self.folder_filter_context=tk.Label(self.folder_filter_bar,text='المجلد الحالي',bg='#e8edf1',fg='#526a7a',font=('Segoe UI',9,'bold'));self.folder_filter_context.grid(row=0,column=1,sticky='e',padx=8)

  bar=tk.Frame(self.center,bg='white',highlightbackground='#d6e0e6',highlightthickness=1);bar.grid(row=3,column=0,sticky='ew',pady=(5,5));ttk.Button(bar,text='←',command=self.go_back,width=4).pack(side='left',padx=(4,2),pady=4);ttk.Button(bar,text='→',command=self.go_forward,width=4).pack(side='left',padx=2,pady=4);ttk.Button(bar,text='↑',command=self.go_up,width=4).pack(side='left',padx=2,pady=4);ttk.Button(bar,text='↻',command=self.rescan,width=4).pack(side='left',padx=2,pady=4)
  self.breadcrumb=tk.StringVar();tk.Label(bar,textvariable=self.breadcrumb,bg='white',fg='#087e8b',font=('Segoe UI',10,'bold'),anchor='e').pack(side='right',fill='x',expand=True,padx=10)
  actions=tk.Frame(self.center,bg='#e8edf1');actions.grid(row=4,column=0,sticky='ew',pady=(0,5))
  self.preview_toggle_button=ttk.Button(actions,text='◧ إظهار المعاينة',command=self.toggle_preview_panel)
  
  self.workspace_btn=ttk.Button(actions,text='⚡ وصول سريع',command=lambda:self.show_workspace_menu(self.workspace_btn));self.workspace_btn.pack(side='left',padx=2)
  
  self.tag_filter_frame = tk.Frame(actions, bg='#e8edf1')
  self.tag_filter_frame.pack(side='left', padx=2)
  tk.Label(self.tag_filter_frame,text='فلتر الهاشتاج',bg='#e8edf1',fg='#435b6d',font=('Segoe UI',9)).pack(side='left',padx=(5,2))
  self.tag_filter_var=tk.StringVar(value='الكل')
  self.tag_filter_box=ttk.Combobox(self.tag_filter_frame,textvariable=self.tag_filter_var,values=('الكل',),state='readonly',width=16,justify='right',style='Office.TCombobox')
  self.tag_filter_box.pack(side='left')
  self.tag_filter_box.bind('<<ComboboxSelected>>',self.tag_filter_changed)
  self.tag_manager_button=ttk.Button(self.tag_filter_frame,text='⚙',width=3,command=self.manage_file_tags)
  self.tag_manager_button.pack(side='left',padx=(3,2))
  self.tag_manager_button.configure(cursor='hand2')
  
  self.add_to_specialty_btn = tk.Button(actions, text='📁 + إضافة مجلد لهذا التخصص', command=lambda: self.edit_folder_specialties(preselect_tag=getattr(self, 'specialty_filter', None)), bg='#087e8b', fg='white', activebackground='#066b76', relief='flat', font=('Segoe UI', 8, 'bold'), padx=10, pady=5, cursor='hand2')

  self.changes_filter_frame = tk.Frame(actions, bg='#e8edf1')
  self.activity_date_mode = getattr(self, 'activity_date_mode', 'all')
  self.activity_custom_date = getattr(self, 'activity_custom_date', tk.StringVar(value=''))
  tk.Label(self.changes_filter_frame, text='تاريخ النشاط:', bg='#e8edf1', fg='#435b6d', font=('Segoe UI', 9, 'bold')).pack(side='left', padx=(5, 4))
  self.activity_filter_btns = {}
  for lbl, m in [('الكل', 'all'), ('اليوم', 'today'), ('أمس', 'yesterday')]:
   b = tk.Button(self.changes_filter_frame, text=lbl, command=lambda mode=m: self.set_activity_date_filter(mode), bg='#087e8b' if self.activity_date_mode==m else 'white', fg='white' if self.activity_date_mode==m else '#28465a', relief='flat', font=('Segoe UI', 8, 'bold'), padx=8, pady=4, cursor='hand2')
   b.pack(side='left', padx=2)
   self.activity_filter_btns[m] = b
  self.activity_cal_btn = tk.Button(self.changes_filter_frame, text='🗓 اختر يوم...', command=self.pick_activity_date, bg='white', fg='#28465a', relief='flat', font=('Segoe UI', 8, 'bold'), padx=8, pady=4, cursor='hand2')
  self.activity_cal_btn.pack(side='left', padx=2)
  self.activity_Filter_btns_cal = self.activity_cal_btn
  self.activity_days_var = tk.StringVar(value='كل الأيام المسجلة')
  self.activity_days_box = ttk.Combobox(self.changes_filter_frame, textvariable=self.activity_days_var, values=('كل الأيام المسجلة',), state='readonly', width=15, justify='center', style='Office.TCombobox')
  self.activity_days_box.pack(side='left', padx=4)
  self.activity_days_box.bind('<<ComboboxSelected>>', self.on_activity_day_combo)
  tk.Button(self.changes_filter_frame, text='🗑 مسح السجل المعروض', command=self.clear_displayed_activity_log, bg='white', fg='#bd4856', activebackground='#fce4e4', relief='flat', font=('Segoe UI', 8, 'bold'), padx=8, pady=4, cursor='hand2').pack(side='left', padx=4)

  self.collection_button=ttk.Button(actions,text='عرض الملفات',command=self.show_files_collection)
  self.file_list_frame=tk.Frame(self.center,bg='#e8edf1');self.file_list_frame.grid(row=5,column=0,sticky='nsew');self.file_list_frame.grid_rowconfigure(0,weight=1);self.file_list_frame.grid_columnconfigure(0,weight=1)
  self.file_tree=self.make_list(self.file_list_frame);self.file_tree.grid(row=0,column=0,sticky='nsew')
  self.file_tree_ybar=ttk.Scrollbar(self.file_list_frame,orient='vertical',command=self.file_tree.yview);self.file_tree_ybar.grid(row=0,column=1,sticky='ns');self.file_tree_xbar=ttk.Scrollbar(self.file_list_frame,orient='horizontal',command=self.file_tree.xview);self.file_tree_xbar.grid(row=1,column=0,sticky='ew');self.file_tree.configure(yscrollcommand=self.file_tree_ybar.set,xscrollcommand=self.file_tree_xbar.set)
  self.selection_bar,self.selection_label=self.make_selection_bar(self.center);self.selection_bar.grid(row=6,column=0,sticky='ew',pady=(4,0));self.selection_bar.grid_remove()
  self.status=tk.StringVar(value='جاهز');tk.Label(self.center,textvariable=self.status,anchor='e',bg='#dfe7ec',fg='#147b87',font=('Segoe UI',9,'bold')).grid(row=7,column=0,sticky='ew',pady=(4,0));self.scan_progress=ttk.Progressbar(self.center,mode='indeterminate',length=180);self.scan_progress.grid(row=8,column=0,sticky='ew',pady=(2,0));self.scan_progress.grid_remove();self.scan_summary=tk.StringVar(value='');tk.Label(self.center,textvariable=self.scan_summary,anchor='e',bg='#e8edf1',fg='#617789',font=('Segoe UI',8)).grid(row=9,column=0,sticky='ew',pady=(1,0))
  rail=tk.Frame(self.explorer_page,bg='#102c3d',width=188);rail.grid(row=0,column=2,sticky='nsew',padx=(0,8));rail.grid_propagate(False)
  tk.Label(rail,text='مساحة المشروع',bg='#102c3d',fg='#a9c3d0',font=('Segoe UI',9,'bold')).pack(anchor='e',padx=15,pady=(17,3))
  tk.Label(rail,text=self.project,bg='#102c3d',fg='white',font=('Segoe UI',12,'bold'),anchor='e',wraplength=175).pack(anchor='e',fill='x',padx=15,pady=(0,14))
  self.rail_nav_buttons={}
  def rail_button(label,command,active=False,key=None):
   key=key or label;b=tk.Button(rail,text=label,command=command,anchor='e',bg='#1b4053' if active else '#102c3d',fg='white' if active else '#d3e2e9',activebackground='#24546a',activeforeground='white',relief='flat',font=('Segoe UI',9,'bold' if active else 'normal'),padx=14,pady=8,cursor='hand2',borderwidth=0);b.pack(fill='x',padx=7,pady=1);self.rail_nav_buttons[key]=b;return b
  tk.Label(rail,text='التصفح',bg='#102c3d',fg='#83a8b9',font=('Segoe UI',8,'bold')).pack(anchor='e',padx=15,pady=(2,4))
  rail_button('▦ ملفات المجلدات',self.show_folder_mode,active=self.mode=='folder',key='folder');rail_button('◈ ملفات المشروع',lambda:self.select_project_scope(),active=self.mode=='project',key='project')
  tk.Label(rail,text='الوصول السريع',bg='#102c3d',fg='#83a8b9',font=('Segoe UI',8,'bold')).pack(anchor='e',padx=15,pady=(15,4))
  rail_button('★ المفضلة',lambda:self.show_collection('favorites'),key='favorites');rail_button('◷ آخر ما فتحته',lambda:self.show_collection('opened'),key='opened');rail_button('＋ أضيف حديثًا',lambda:self.show_collection('added'),key='added');rail_button('↻ سجل التغييرات',lambda:self.show_collection('changes'),key='changes');rail_button('☑ قائمة المهام',lambda:self.show_tasks(self.project),key='tasks');rail_button('▦ تقويم المشروع',lambda:self.show_task_calendar(self.project),key='calendar')
  rail_button('🗑 سلة المهملات',lambda:self.show_collection('recycle_bin'),key='recycle_bin')
  
  spec_head=tk.Frame(rail,bg='#102c3d');spec_head.pack(fill='x',padx=12,pady=(15,4))
  tk.Label(spec_head,text='التخصصات',bg='#102c3d',fg='#83a8b9',font=('Segoe UI',9,'bold')).pack(side='right')
  tk.Button(spec_head,text='＋',command=lambda:self.edit_folder_specialties(),bg='#1b4053',fg='white',activebackground='#24546a',activeforeground='white',relief='flat',font=('Segoe UI',8,'bold'),padx=6,pady=0,cursor='hand2').pack(side='left')
  
  self.rail_tags=tk.Frame(rail,bg='#102c3d');self.rail_tags.pack(fill='x');self.refresh_tag_filters()
  tk.Frame(rail,bg='#23485b',height=1).pack(fill='x',padx=12,pady=12)
  rail_button('▱ فتح مجلد المشروع',lambda:os.startfile(str(self.root)),key='open_root')
  self.export_project_btn=rail_button('📦 تصدير المشروع',self._export_current_project,key='export_project')
  
  self._bind_explorer_shortcuts()
  self.rebuild_project_tabs();self.rebuild_folder_tabs();self.refresh_directory()
  self.after(100, lambda: self.file_tree.focus_set() if hasattr(self, 'file_tree') and self.file_tree.winfo_exists() else None)

 def _update_top_action_bars(self):
  if not hasattr(self, 'tag_filter_frame') or not hasattr(self, 'changes_filter_frame'): return
  if hasattr(self, 'add_to_specialty_btn'):
   self.add_to_specialty_btn.pack_forget()
  if getattr(self, 'view_mode', 'files') == 'changes':
   self.tag_filter_frame.pack_forget()
   self.changes_filter_frame.pack(side='left', padx=2)
   self.refresh_activity_days_combo()
   self._sync_activity_filter_buttons()
  else:
   self.changes_filter_frame.pack_forget()
   self.tag_filter_frame.pack(side='left', padx=2)
   if getattr(self, 'view_mode', 'files') == 'specialty' and hasattr(self, 'add_to_specialty_btn'):
    self.add_to_specialty_btn.pack(side='left', padx=4)

 def refresh_activity_days_combo(self):
  if not hasattr(self, 'activity_days_box') or not self.activity_days_box.winfo_exists(): return
  try:
   with connect() as c:
    days = [r[0] for r in c.execute("SELECT DISTINCT substr(occurred_at, 1, 10) d FROM activity_log WHERE project=? AND d IS NOT NULL ORDER BY d DESC", (self.project,)).fetchall() if r[0]]
   vals = ['كل الأيام المسجلة'] + days
   self.activity_days_box.configure(values=vals)
   if self.activity_date_mode == 'custom' and self.activity_custom_date.get() in vals:
    self.activity_days_var.set(self.activity_custom_date.get())
   elif self.activity_date_mode == 'all':
    self.activity_days_var.set('كل الأيام المسجلة')
  except Exception: pass

 def _sync_activity_filter_buttons(self):
  mode = getattr(self, 'activity_date_mode', 'all')
  for m, b in getattr(self, 'activity_filter_btns', {}).items():
   if b.winfo_exists():
    b.configure(bg='#087e8b' if mode == m else 'white', fg='white' if mode == m else '#28465a')
  if hasattr(self, 'activity_cal_btn') and self.activity_cal_btn.winfo_exists():
   if mode == 'custom' and self.activity_custom_date.get():
    self.activity_cal_btn.configure(text=f"🗓 {self.activity_custom_date.get()}", bg='#087e8b', fg='white')
   else:
    self.activity_cal_btn.configure(text='🗓 اختر يوم...', bg='white', fg='#28465a')

 def set_activity_date_filter(self, mode, custom_date=None):
  self.activity_date_mode = mode
  if custom_date is not None:
   self.activity_custom_date.set(custom_date)
  self._sync_activity_filter_buttons()
  self.refresh_activity_days_combo()
  self.populate()

 def on_activity_day_combo(self, event=None):
  val = self.activity_days_var.get()
  if val == 'كل الأيام المسجلة' or not val:
   self.set_activity_date_filter('all')
  else:
   self.set_activity_date_filter('custom', val)

 def pick_activity_date(self):
  if not hasattr(self, '_task_pick_date'): return
  var = tk.StringVar(value=self.activity_custom_date.get() or date.today().isoformat())
  def on_change(*_):
   chosen = var.get().strip()
   if chosen: self.set_activity_date_filter('custom', chosen)
   else: self.set_activity_date_filter('all', '')
  var.trace_add('write', on_change)
  self._task_pick_date(var, parent=self)

 def delete_selected_activity_logs(self, tree=None):
  tree = tree or getattr(self, 'file_tree', None)
  if not tree or not tree.winfo_exists(): return
  sel = [iid for iid in tree.selection() if str(iid).startswith('activity:')]
  if not sel: return
  ids = [int(str(iid).split(':', 1)[1]) for iid in sel if str(iid).split(':', 1)[1].isdigit()]
  if not ids: return
  if len(ids) > 1 and not messagebox.askyesno('مسح من السجل', f'هل تريد مسح {len(ids):,} حدث محدد من سجل التغييرات؟', parent=self):
   return
  with connect() as c:
   c.executemany('DELETE FROM activity_log WHERE id=? AND project=?', [(i, self.project) for i in ids])
  self.refresh_activity_days_combo()
  self.populate()

 def clear_displayed_activity_log(self):
  tree = getattr(self, 'file_tree', None)
  if not tree or not tree.winfo_exists(): return
  all_iids = [iid for iid in tree.get_children('') if str(iid).startswith('activity:')]
  if not all_iids:
   return messagebox.showinfo('سجل التغييرات', 'لا توجد أحداث معروضة حالياً لمسحها.', parent=self)
  ids = [int(str(iid).split(':', 1)[1]) for iid in all_iids if str(iid).split(':', 1)[1].isdigit()]
  if not messagebox.askyesno('مسح السجل المعروض', f'هل أنت متأكد من مسح {len(ids):,} حدث معروض من سجل التغييرات نهائياً؟', parent=self):
   return
  with connect() as c:
   c.executemany('DELETE FROM activity_log WHERE id=? AND project=?', [(i, self.project) for i in ids])
  self.refresh_activity_days_combo()
  self.populate()

 def blank_icon_image(self):
  if not hasattr(self, '_blank_tree_icon'):
   im = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
   self._blank_tree_icon = ImageTk.PhotoImage(im)
  return self._blank_tree_icon

 def activity_row_icon(self, r):
  target = r.get('path')
  action = str(r.get('action') or '')
  details = str(r.get('details') or '')
  general_actions = ('فتح قسم', 'تغيير فلتر الهاشتاج', 'تغيير فلتر النوع', 'تغيير فلتر التخصص', 'تغيير نطاق العرض', 'ترتيب الملفات', 'بحث', 'حفظ بحث', 'حذف بحث محفوظ', 'عرض تخصص', 'إعدادات النظام', 'أدوات مساحة العمل')
  if action in general_actions:
   return self.blank_icon_image()
  if target:
   p = Path(target)
   if p.is_dir() or 'مجلد' in action or action in ('فتح مشروع', 'إنشاء مشروع'):
    return self.file_icon_image(str(p), is_dir=True)
   if p.suffix:
    return self.file_icon_image(str(p), is_dir=False)
  m = re.search(r'([A-Za-z0-9_\-\u0600-\u06FF\s]+\.[A-Za-z0-9]{2,5})', details)
  if m:
   return self.file_icon_image(m.group(1), is_dir=False)
  if 'مجلد' in action:
   return self.file_icon_image('folder', is_dir=True)
  return self.blank_icon_image()

 def _is_typing_in_input(self, event=None):
  w = event.widget if event and getattr(event, 'widget', None) else self.focus_get()
  if not w: return False
  try: return w.winfo_class() in ('Entry', 'TEntry', 'Text', 'Combobox', 'TCombobox', 'Spinbox', 'TSpinbox')
  except Exception: return False

 def _in_explorer_context(self):
  if hasattr(self, 'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped():
   return True
  return hasattr(self, 'explorer_page') and self.explorer_page.winfo_exists() and self.explorer_page.winfo_ismapped()

 def _on_global_ctrl_key(self, event):
  if not self._in_explorer_context() or self._is_typing_in_input(event):
   return
  kc = getattr(event, 'keycode', 0)
  ks = getattr(event, 'keysym', '').lower()
  tree = self.current_selection_tree()
  
  if kc == 65 or ks == 'a': # Ctrl + A
   self.select_all_visible(tree)
   return 'break'
  elif kc == 67 or ks == 'c': # Ctrl + C
   self.copy_files_to_clipboard(tree, is_cut=False)
   return 'break'
  elif kc == 88 or ks == 'x': # Ctrl + X
   self.copy_files_to_clipboard(tree, is_cut=True)
   return 'break'
  elif kc == 86 or ks == 'v': # Ctrl + V
   self.paste_files()
   return 'break'
  elif kc == 70 or ks == 'f': # Ctrl + F
   self.show_search_page()
   return 'break'
  elif kc == 79 or ks == 'o': # Ctrl + O
   if tree: self.activate(tree)
   return 'break'

 def _bind_explorer_shortcuts(self):
  self.bind_all('<Control-KeyPress>', self._on_global_ctrl_key)
  self.bind_all('<Delete>', lambda e: (self._handle_delete_shortcut(self.current_selection_tree()), 'break') if self._in_explorer_context() and not self._is_typing_in_input(e) else None)
  self.bind_all('<BackSpace>', lambda e: (self.go_back(), 'break') if self._in_explorer_context() and not self._is_typing_in_input(e) else None)
  self.bind_all('<Alt-Left>', lambda e: (self.go_back(), 'break') if self._in_explorer_context() else None)
  self.bind_all('<Alt-Right>', lambda e: (self.go_forward(), 'break') if self._in_explorer_context() else None)
  self.bind_all('<Alt-Up>', lambda e: (self.go_up(), 'break') if self._in_explorer_context() else None)
  self.bind_all('<F5>', lambda e: (self.rescan(), 'break') if self._in_explorer_context() else None)
  self.bind_all('<Escape>', lambda e: (self._handle_escape_shortcut(), 'break') if self._in_explorer_context() else None)

 def _handle_delete_shortcut(self, tree=None):
  tree = tree or self.current_selection_tree()
  if not tree or not tree.winfo_exists(): return
  if getattr(self, 'view_mode', '') == 'recycle_bin':
   sel = self.selected_paths(tree)
   if sel: self.empty_recycle_bin(sel)
  elif getattr(self, 'view_mode', '') == 'changes':
   self.delete_selected_activity_logs(tree)
  else:
   self.delete_selected_paths(tree)

 def _handle_escape_shortcut(self):
  tree = self.current_selection_tree()
  if tree and tree.winfo_exists() and tree.selection():
   tree.selection_remove(tree.selection())
   self.sync_selection_marks(tree)
   self.update_selection_status(tree)
   self.preview_selected(tree)
  elif getattr(self, 'view_mode', 'files') != 'files':
   self.show_files_collection()

 def _export_current_project(self):
  if not getattr(self, 'project', None): return
  if hasattr(self, 'password_enabled') and self.password_enabled():
   pwd = simpledialog.askstring('تأكيد الأمان', 'أدخل كلمة المرور الخاصة بالبرنامج للتصدير:', show='*', parent=self)
   if not pwd or not self.verify_password(pwd):
    if pwd is not None: messagebox.showerror('خطأ', 'كلمة المرور غير صحيحة.', parent=self)
    return
  dialog = tk.Toplevel(self)
  dialog.title('تصدير المشروع الحالي')
  dialog.configure(bg='#eef3f7')
  dialog.geometry('350x200')
  dialog.transient(self)
  dialog.grab_set()
  tk.Label(dialog, text=f'تصدير مشروع: {self.project}', bg='#eef3f7', fg='#19394e', font=('Segoe UI', 12, 'bold')).pack(pady=(20, 10))
  include_tasks = tk.BooleanVar(value=True)
  tk.Checkbutton(dialog, text='تضمين المهام والتقويم (.tasks)', variable=include_tasks, bg='#eef3f7', font=('Segoe UI', 10, 'bold'), fg='#087e8b').pack(pady=10)
  def do_export():
   save_path = filedialog.asksaveasfilename(title='حفظ ملف التصدير', defaultextension='.zip', filetypes=[('ZIP Files', '*.zip')], initialfile=f"{self.project}_backup.zip", parent=dialog)
   if not save_path: return
   dialog.destroy()
   if hasattr(self, '_sync_run_export_thread'):
    self._sync_run_export_thread([self.project], save_path, include_tasks.get())
  ttk.Button(dialog, text='بدء التصدير', command=do_export).pack(pady=10)

 def toggle_preview_panel(self):
  searching=hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped()
  area=self.search_preview_area if searching else self.preview_area
  page=self.search_page if searching else self.explorer_page
  button=self.search_preview_toggle if searching else self.preview_toggle_button
  visible=area.winfo_manager()!=''
  if visible:
   area.grid_remove();page.grid_columnconfigure(0,minsize=0,weight=0);button.configure(text='◧ إظهار المعاينة');button.pack(side='right',padx=(3,0)) if not searching else None
  else:
   area.grid();page.grid_columnconfigure(0,minsize=350,weight=0);button.configure(text='◧ إخفاء المعاينة');button.pack_forget() if not searching else None
  self.after_idle(lambda:self.paint_preview() if getattr(self,'preview_base',None) and not searching else None)

 def make_selection_bar(self,parent):
  bar=tk.Frame(parent,bg='#e4f2f3',highlightbackground='#c6e2e4',highlightthickness=1)
  label=tk.Label(bar,text='',bg='#e4f2f3',fg='#164b5b',font=('Segoe UI',9,'bold'));label.pack(side='right',padx=12,pady=8)
  
  btn_folder_spec = tk.Button(bar,text='📁 تخصيص المجلد',command=lambda:self.edit_folder_specialties(self.current_selection_tree()),bg='white',fg='#087e8b',activebackground='#d5ebed',relief='flat',font=('Segoe UI',8,'bold'),padx=9,pady=5,cursor='hand2')
  btn_remove_spec = tk.Button(bar,text='× إزالة من التخصص',command=lambda:self.remove_selected_from_current_specialty(self.current_selection_tree()),bg='white',fg='#bd4856',activebackground='#fce4e4',relief='flat',font=('Segoe UI',8,'bold'),padx=9,pady=5,cursor='hand2')
  btn_file_tag = tk.Button(bar,text='🏷 هاشتج الملف',command=self.edit_tags,bg='white',fg='#28465a',activebackground='#d5ebed',relief='flat',font=('Segoe UI',8,'bold'),padx=9,pady=5,cursor='hand2')
  btn_fav = tk.Button(bar,text='★ المفضلة',command=self.toggle_favorite,bg='white',fg='#d69637',activebackground='#d5ebed',relief='flat',font=('Segoe UI',8,'bold'),padx=9,pady=5,cursor='hand2')
  btn_copy = tk.Button(bar,text='⧉ نسخ المسارات',command=lambda:self.copy_selected_paths(),bg='white',fg='#28465a',activebackground='#d5ebed',relief='flat',font=('Segoe UI',8,'bold'),padx=9,pady=5,cursor='hand2')
  btn_clear_tags = tk.Button(bar,text='× مسح الهاشتاجات',command=lambda:self.clear_selected_tags(self.current_selection_tree()),bg='white',fg='#bd4856',activebackground='#d5ebed',relief='flat',font=('Segoe UI',8,'bold'),padx=9,pady=5,cursor='hand2')
  
  bar._btn_folder_spec = btn_folder_spec
  bar._btn_remove_spec = btn_remove_spec
  bar._btn_file_tag = btn_file_tag
  bar._btn_fav = btn_fav
  bar._btn_copy = btn_copy
  bar._btn_clear_tags = btn_clear_tags
  return bar,label

 def current_selection_tree(self):
  if hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped() and getattr(self,'search_nb',None) and self.search_nb.tabs():return self.search_views.get(self.search_nb.tab(self.search_nb.select(),'text'),getattr(self,'file_tree',None))
  return getattr(self,'file_tree',None)

 def select_project_scope(self):
  if not self.current:return
  self.mode='project';self.view_mode='files';self.collection_button.pack_forget();self._update_top_action_bars();self.rebuild_folder_tabs(preferred=self.project_group);self.save_view_state();self.populate();self.update_rail_selection()

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
  t.heading('#0',text='');t.column('#0',width=44,minwidth=44,stretch=False,anchor='center');t.heading('mark',text='');t.column('mark',width=34,minwidth=34,stretch=False,anchor='center')
  
  # ضبط المسافات وعرض الأعمدة خصوصاً للتواريخ لضمان عدم تآكل الأرقام نهائياً
  col_specs = [
   ('name', 'اسم الملف', 200, 130, True, 'w'),
   ('type', 'النوع', 68, 56, False, 'center'),
   ('size', 'الحجم', 76, 64, False, 'center'),
   ('mtime', 'تاريخ الملف', 142, 132, False, 'center'),
   ('opened', 'آخر فتح', 142, 132, False, 'center'),
   ('tags', 'الهاشتاجات', 120, 85, False, 'e'),
   ('path', 'المسار داخل المشروع', 210, 120, True, 'e')
  ]
  saved_widths = getattr(self, 'column_widths', {})
  for col, title, default_w, min_w, is_stretch, align in col_specs:
   t.heading(col, text=title, command=lambda c=col: self.sort_by(c))
   actual_w = max(min_w, int(saved_widths.get(col, default_w)))
   t.column(col, width=actual_w, minwidth=min_w, stretch=is_stretch, anchor=align)
  
  t.bind('<<TreeviewSelect>>',lambda e,tree=t:self.on_tree_selection(tree))
  t.bind('<ButtonPress-1>',lambda e,tree=t:self.on_tree_click(e,tree))
  t.bind('<B1-Motion>',lambda e,tree=t:self.on_tree_drag(e,tree))
  t.bind('<Shift-Up>',lambda e,tree=t:self.on_tree_shift_arrow(e,tree,-1))
  t.bind('<Shift-Down>',lambda e,tree=t:self.on_tree_shift_arrow(e,tree,1))
  
  t.bind('<Configure>',lambda e,tree=t:self.remember_column_widths(tree),add='+')
  t.bind('<Double-1>',lambda e,tree=t:self.activate(tree))
  t.bind('<Button-3>',lambda e,tree=t:self.context_menu(e,tree))
  t.bind('<Return>',lambda e,tree=t:(self.activate(tree),'break'))
  return t

 def on_tree_selection(self,tree):
  self.sync_selection_marks(tree);self.preview_selected(tree);self.update_selection_status(tree)

 def sync_selection_marks(self,tree):
  selected=set(tree.selection())
  for item in tree.get_children():
   values=list(tree.item(item,'values'))
   if len(values)<2:continue
   mark='☑' if item in selected else '☐'
   if values[1]!=mark:values[1]=mark;tree.item(item,values=values)

 def on_tree_click(self, event, tree):
  tree.focus_set()
  region = tree.identify_region(event.x, event.y)
  if region == 'heading' or region == 'separator':
   return
  
  row = tree.identify_row(event.y)
  col = tree.identify_column(event.x)
  
  if not row:
   tree.selection_remove(tree.selection())
   self.on_tree_selection(tree)
   return 'break'

  ctrl = (event.state & 0x0004) != 0
  shift = (event.state & 0x0001) != 0

  if col == '#2' and not shift:
   if row in tree.selection():
    tree.selection_remove(row)
   else:
    tree.selection_add(row)
    tree.focus(row)
    tree._selection_anchor = row
   self.on_tree_selection(tree)
   return 'break'

  if shift:
   items = list(tree.get_children(''))
   anchor = getattr(tree, '_selection_anchor', None)
   if not anchor or anchor not in items:
    anchor = tree.focus() or (tree.selection()[0] if tree.selection() else row)
   if anchor in items and row in items:
    i1, i2 = items.index(anchor), items.index(row)
    start, end = min(i1, i2), max(i1, i2)
    span = items[start:end+1]
    if ctrl:
     tree.selection_add(span)
    else:
     tree.selection_set(span)
    tree.focus(row)
   else:
    tree.selection_set(row)
    tree.focus(row)
    tree._selection_anchor = row
   self.on_tree_selection(tree)
   return 'break'

  if ctrl:
   if row in tree.selection():
    tree.selection_remove(row)
   else:
    tree.selection_add(row)
   tree.focus(row)
   tree._selection_anchor = row
   self.on_tree_selection(tree)
   return 'break'

  tree.selection_set(row)
  tree.focus(row)
  tree._selection_anchor = row
  self.on_tree_selection(tree)
  return 'break'

 def on_tree_drag(self, event, tree):
  row = tree.identify_row(event.y)
  if not row: return
  items = list(tree.get_children(''))
  anchor = getattr(tree, '_selection_anchor', None)
  if not anchor or anchor not in items:
   anchor = row
   tree._selection_anchor = row
  if anchor in items and row in items:
   i1, i2 = items.index(anchor), items.index(row)
   span = items[min(i1, i2):max(i1, i2)+1]
   if set(tree.selection()) != set(span):
    tree.selection_set(span)
    tree.focus(row)
    tree.see(row)
    self.on_tree_selection(tree)
  return 'break'

 def on_tree_shift_arrow(self, event, tree, delta):
  items = list(tree.get_children(''))
  if not items: return 'break'
  cur = tree.focus() or (tree.selection()[-1] if tree.selection() else items[0])
  if cur not in items: return 'break'
  anchor = getattr(tree, '_selection_anchor', None)
  if not anchor or anchor not in items:
   anchor = cur
   tree._selection_anchor = anchor
  new_idx = max(0, min(len(items) - 1, items.index(cur) + delta))
  target = items[new_idx]
  i1, i2 = items.index(anchor), new_idx
  span = items[min(i1, i2):max(i1, i2)+1]
  tree.selection_set(span)
  tree.focus(target)
  tree.see(target)
  self.on_tree_selection(tree)
  return 'break'

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
  self.project_type_labels=current_project_types
  self.folder_menu_items={}
  self.folder_type_menu.delete(0,'end')
  for label in ['الكل']+sorted(folder_counts,key=order):
   count=sum(folder_counts.values()) if label=='الكل' else folder_counts[label]
   display=f'{label} · {count:,}'
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
  self.mode=new_mode;self.view_mode='files';self.collection_button.pack_forget();self._update_top_action_bars()
  self.save_view_state();self.rebuild_folder_tabs();self.populate();self.update_rail_selection()
  self.log_activity('تغيير نطاق العرض','عرض '+('ملفات المجلد' if new_mode=='folder' else 'كل ملفات المشروع'),path=self.current)

 def type_filter_changed(self,scope,selected):
  self.view_mode='files';self.collection_button.pack_forget();self.mode=scope;self._update_top_action_bars()
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
  if tree is getattr(self,'file_tree',None) and getattr(self,'view_mode','') in ('changes', 'recycle_bin'):
   bar=getattr(self,'selection_bar',None)
   if bar and bar.winfo_exists():bar.grid_remove()
   if hasattr(self,'status'):
    if getattr(self,'view_mode','')=='changes':
     self.status.set(f'{len(tree.get_children()):,} حدث في سجل النشاط' + (f' · {len(selected):,} محدد' if selected else ''))
    else:
     self.status.set(f'{len(tree.get_children()):,} عنصر في السلة' + (f' · {len(selected):,} محدد' if selected else ''))
   return
  n=len(selected)
  if tree is getattr(self,'file_tree',None):
   bar=getattr(self,'selection_bar',None);label=getattr(self,'selection_label',None)
   if hasattr(self,'status') and self.view_mode=='files':self.status.set(f'{len(tree.get_children()):,} عنصر · {n:,} محدد' if n else f'{len(tree.get_children()):,} عنصر')
  else:
   bar=getattr(self,'search_selection_bar',None);label=getattr(self,'search_selection_label',None)
  if bar and bar.winfo_exists():
   if n:
    paths = [Path(p) for p in selected if not str(p).startswith('activity:')]
    dirs = [p for p in paths if p.is_dir()]
    files = [p for p in paths if p.is_file()]
    if dirs and not files:
     label.configure(text=f'تم تحديد {len(dirs):,} مجلد')
    elif files and not dirs:
     label.configure(text=f'تم تحديد {len(files):,} ملف')
    else:
     label.configure(text=f'تم تحديد {n:,} عنصر ({len(dirs)} مجلد، {len(files)} ملف)')
    
    for b in (bar._btn_folder_spec, bar._btn_remove_spec, bar._btn_file_tag, bar._btn_fav, bar._btn_copy, bar._btn_clear_tags):
     b.pack_forget()
    if dirs:
     bar._btn_folder_spec.pack(side='right', padx=3, pady=4)
     if getattr(self, 'view_mode', '') == 'specialty' and getattr(self, 'specialty_filter', None):
      bar._btn_remove_spec.configure(text=f"× إزالة من «{self.specialty_filter}»")
      bar._btn_remove_spec.pack(side='right', padx=3, pady=4)
    if files:
     bar._btn_file_tag.pack(side='right', padx=3, pady=4)
    bar._btn_fav.pack(side='right', padx=3, pady=4)
    bar._btn_copy.pack(side='right', padx=3, pady=4)
    if files:
     bar._btn_clear_tags.pack(side='right', padx=3, pady=4)
    bar.grid()
   else:bar.grid_remove()

 def select_all_visible(self, tree=None):
  tree = tree or self.current_selection_tree()
  if not tree or not tree.winfo_exists():return
  rows=tree.get_children('')
  if rows:
   tree.selection_set(rows)
   tree.focus(rows[0])
   tree._selection_anchor = rows[0]
   self.sync_selection_marks(tree)
   self.update_selection_status(tree)
   self.preview_selected(tree)

 def show_collection(self,kind):
  self.save_view_state();self.view_mode=kind;self.collection_button.pack(side='right',padx=3);self._update_top_action_bars();self.populate()
  labels={'favorites':'المفضلة','opened':'آخر ما فتحته','added':'أضيف حديثًا','changes':'سجل التغييرات', 'recycle_bin': 'سلة المهملات'}
  label=labels.get(kind,kind);self.breadcrumb.set(f'{self.project} › {label}');self.update_rail_selection();self.log_activity('فتح قسم',label)

 def show_files_collection(self):
  self.view_mode='files';self.collection_button.pack_forget();self._update_top_action_bars();self.refresh_directory();self.update_rail_selection()

 def toggle_favorite(self,path=None):
  paths=([path] if isinstance(path,(str,Path)) else list(path)) if path else self.selected_paths()
  paths=[Path(p) for p in paths if p]
  if not paths:return messagebox.showinfo('المفضلة','حدد ملفًا أو مجلدًا أولًا.',parent=self)
  added=[];removed=[]
  with connect() as c:
   for p in paths:
    key=str(p.resolve());exists=c.execute('select 1 from favorites where project=? and lower(path)=lower(?)',(self.project,key)).fetchone()
    if exists:
     c.execute('delete from favorites where project=? and lower(path)=lower(?)',(self.project,key));removed.append(p)
    else:
     c.execute('insert into favorites(project,path,kind,created) values(?,?,?,?)',(self.project,key,'folder' if p.is_dir() else 'file',stamp(time.time())));added.append(p)
  if added:self.log_activity('إضافة إلى المفضلة','إضافة: '+', '.join(p.name for p in added),path=added[0] if len(added)==1 else None)
  if removed:self.log_activity('إزالة من المفضلة','إزالة: '+', '.join(p.name for p in removed),path=removed[0] if len(removed)==1 else None)
  self.status.set(f'تم تحديث المفضلة لـ {len(paths):,} عنصر')
  self.populate()
  if hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped():
   self.render_search_results()

 def is_favorite(self,path):
  with connect() as c:return c.execute('select 1 from favorites where project=? and lower(path)=lower(?)',(self.project,str(Path(path).resolve()))).fetchone() is not None

 def get_smart_links(self, path):
  try:
   target = str(Path(path).resolve()).casefold()
   with connect() as c:
    links = c.execute("SELECT path1, path2 FROM file_links").fetchall()
   res = []
   for r in links:
    p1 = str(Path(r[0]).resolve()).casefold()
    p2 = str(Path(r[1]).resolve()).casefold()
    if p1 == target: res.append(Path(r[1]))
    if p2 == target: res.append(Path(r[0]))
   return [p for p in res if p.exists()]
  except Exception: return []

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
  if not getattr(self,'preview_related_container',None) or not self.preview_related_container.winfo_exists():return
  for widget in self.preview_related_strip.winfo_children():widget.destroy()
  self.preview_related_strip._related_photos=[]
  
  smart_links = self.get_smart_links(current)
  all_paths = list(dict.fromkeys(paths + smart_links))
  
  if not all_paths:
   self.preview_related_container.grid_remove();return
  self.preview_related_container.grid()
  self.preview_related_label.configure(text=f'مرتبط ({len(all_paths)}):')
  
  for path in all_paths:
   photo=self.related_file_thumbnail(path);self.preview_related_strip._related_photos.append(photo)
   btn=tk.Button(self.preview_related_strip,text=path.name[:15],image=photo,compound='left',command=lambda p=path:self.preview_related_file(p),bg='white',fg='#28465a',activebackground='#dceef0',relief='flat',font=('Segoe UI',8),padx=5,pady=3,cursor='hand2')
   btn.pack(side='right',padx=2)
   btn.bind('<MouseWheel>', lambda e: self.preview_related_canvas.xview_scroll(int(-e.delta/120), 'units'))
   btn.bind('<Shift-MouseWheel>', lambda e: self.preview_related_canvas.xview_scroll(int(-e.delta/120), 'units'))
   
  def reset_scroll():
   if self.preview_related_canvas.winfo_exists():
    self.preview_related_canvas.configure(scrollregion=self.preview_related_canvas.bbox('all'))
    self.preview_related_canvas.xview_moveto(1.0)
  self.after(50, reset_scroll)

 def preview_related_file(self,path):
  p=Path(path)
  if not p.is_file():return
  searching=hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped()
  if searching:self.hide_search_page()
  if self.view_mode!='files' or self.mode!='folder' or self.current.resolve()!=p.parent.resolve():
   self.save_view_state()
   if self.current and self.current.resolve()!=p.parent.resolve():self.backstack.append(self.current)
   self.forwardstack.clear();self.current=p.parent;self.mode='folder';self.folder_group='الكل';self.view_mode='files';self.collection_button.pack_forget();self._update_top_action_bars();self.refresh_directory();self.animate_window_in()
  iid=str(p.resolve())
  if self.file_tree.exists(iid):self.file_tree.selection_set(iid);self.file_tree.focus(iid);self.file_tree.see(iid)

 def leave_search_for(self,kind,value=None):
  self.hide_search_page()
  if kind=='folder':self.show_folder_mode()
  elif kind=='project':self.select_project_scope()
  elif kind in ('favorites','opened','added','changes', 'recycle_bin'):self.show_collection(kind)
  elif kind=='specialty' and value:self.show_specialty(value)

 def _collection_rows(self):
  with connect() as c:
   if self.view_mode=='recycle_bin':
    try:
     rows = c.execute("SELECT * FROM recycle_bin WHERE project=? ORDER BY deleted_at DESC", (self.project,)).fetchall()
     out = []
     for row in rows:
      try:
       p = Path(row['original_path'])
       bin_p = Path(row['bin_path'])
       if not bin_p.name or not bin_p.exists(): continue
       out.append({'path':str(bin_p.resolve()),'kind':'recycle_item','rel':p.name,'name':f"{p.name}",'ext':p.suffix.lower() if bin_p.is_file() else 'مجلد','size':bin_p.stat().st_size if bin_p.is_file() else 0,'mtime':bin_p.stat().st_mtime if bin_p.exists() else 0,'last_open':row['deleted_at'],'tags':''})
      except Exception: continue
     return out
    except Exception: return []
   if self.view_mode=='specialty':
    rows=c.execute("select path,group_concat(tag, ' ') tags from folder_tags where project=? and tag=? group by path order by path",(self.project,self.specialty_filter)).fetchall();out=[]
    for row in rows:
     rel=row['path'] or '.';p=(self.root/rel).resolve()
     if not p.is_dir():continue
     all_t = [r[0] for r in c.execute("select tag from folder_tags where project=? and path=? order by tag",(self.project,rel)).fetchall()]
     out.append({'path':str(p.resolve()),'kind':'folder','rel':rel,'name':p.name,'ext':'مجلد','size':0,'mtime':p.stat().st_mtime,'last_open':'','tags':' '.join(all_t)})
    return out
   if self.view_mode=='favorites':
    return c.execute("select v.path,v.kind,f.rel,f.name,f.ext,f.size,f.mtime,f.last_open,group_concat(t.tag,' ') tags from favorites v left join files f on lower(f.path)=lower(v.path) left join tags t on lower(t.path)=lower(f.path) where v.project=? group by v.path order by v.created desc",(self.project,)).fetchall()
   if self.view_mode=='opened':
    return c.execute("select f.path,f.project,f.rel,f.name,f.ext,f.size,f.mtime,max(h.opened_at) last_open,f.indexed,group_concat(t.tag,' ') tags from file_open_history h join files f on f.path=h.path and f.project=h.project left join tags t on t.path=f.path where h.project=? group by f.path order by max(h.opened_at) desc,max(h.id) desc limit 500",(self.project,)).fetchall()
   if self.view_mode=='added':
    return c.execute("select f.*,group_concat(t.tag,' ') tags,max(a.occurred_at) added_at from activity_log a join files f on f.path=a.path and f.project=a.project left join tags t on t.path=f.path where a.project=? and a.action='إضافة ملف' and a.occurred_at>=? group by f.path order by max(a.id) desc limit 500",(self.project,stamp(time.time()-30*86400))).fetchall()
   if self.view_mode=='changes':
    mode = getattr(self, 'activity_date_mode', 'all')
    target_date = None
    if mode == 'today': target_date = date.today().isoformat()
    elif mode == 'yesterday': target_date = (date.today() - timedelta(days=1)).isoformat()
    elif mode == 'custom' and hasattr(self, 'activity_custom_date') and self.activity_custom_date.get():
     target_date = self.activity_custom_date.get()
    if target_date:
     return c.execute("select id,project,action,details,path,occurred_at from activity_log where project=? and substr(occurred_at, 1, 10)=? order by id desc limit 2000",(self.project, target_date)).fetchall()
    return c.execute("select id,project,action,details,path,occurred_at from activity_log where project=? order by id desc limit 2000",(self.project,)).fetchall()
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
   with connect() as c:
    c.execute('CREATE TABLE IF NOT EXISTS folder_specialty_catalog(project TEXT, tag TEXT, created TEXT, PRIMARY KEY(project, tag))')
    tags=sorted({r[0] for r in c.execute('select tag from folder_specialty_catalog where project=? union select distinct tag from folder_tags where project=?',(self.project,self.project))})
   for key in [k for k in self.rail_nav_buttons if k.startswith('specialty:')]:self.rail_nav_buttons.pop(key,None)
   for w in self.rail_tags.winfo_children():w.destroy()
   for tag in tags:
    key='specialty:'+tag
    btn=tk.Button(self.rail_tags,text='● '+tag,command=lambda t=tag:self.show_specialty(t),anchor='e',bg='#102c3d',fg='#d3e2e9',activebackground='#24546a',relief='flat',font=('Segoe UI',9),padx=14,pady=6,cursor='hand2',borderwidth=0)
    btn.pack(fill='x',padx=7,pady=1);self.rail_nav_buttons[key]=btn
   self.update_rail_selection()
  except Exception:pass

 def update_rail_selection(self):
  buttons=getattr(self,'rail_nav_buttons',{})
  if not buttons:return
  if self.view_mode=='specialty':active='specialty:'+getattr(self,'specialty_filter','')
  elif self.view_mode in ('favorites','opened','added','changes', 'recycle_bin', 'related'):
   active=self.view_mode if self.view_mode != 'related' else 'folder'
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
  self.view_mode='specialty';self.specialty_filter=tag;self.collection_button.pack(side='right',padx=3);self._update_top_action_bars();self.populate();self.breadcrumb.set(f'{self.project} › التخصصات › {tag}');self.update_rail_selection();self.log_activity('عرض تخصص',tag)

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
  self.view_mode='files';self.collection_button.pack_forget();self._update_top_action_bars()
  preferred=self.project_group if self.mode=='project' else self.folder_group
  self.rebuild_folder_tabs(preferred=preferred)
  if hasattr(self,'project_nb'):
   for tab in self.project_nb.tabs():
    if self.project_nb.tab(tab,'text')==('تصفح المجلدات' if self.mode=='folder' else 'المشروع بالكامل'):self.project_nb.select(tab);break
  self.save_view_state();self.populate();self.update_rail_selection()

 def show_folder_mode(self,from_tab=False):
  self.mode='folder';self.view_mode='files';self.folder_group='الكل';self.collection_button.pack_forget();self._update_top_action_bars();self.rebuild_folder_tabs(preferred='الكل')
  if not from_tab and hasattr(self,'project_nb'):
   for tab in self.project_nb.tabs():
    if self.project_nb.tab(tab,'text')=='تصفح المجلدات':self.project_nb.select(tab);break
  self.populate();self.update_rail_selection()