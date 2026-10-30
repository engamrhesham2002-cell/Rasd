# Rasd - التاجات والتخصصات (إضافة/حذف/تعديل)
from common import *
from update_utils import *
from storage import *

class TagsMixin:
 def manage_file_tags(self):
  with connect() as c:
   tags=sorted({r[0] for r in c.execute('select tag from file_tag_catalog where project=? union select distinct t.tag from tags t join files f on f.path=t.path where f.project=?',(self.project,self.project))})
  win=tk.Toplevel(self);win.title('إدارة هاشتاجات الملفات');win.transient(self);win.resizable(False,False);win.configure(bg='#e8edf1')
  tk.Label(win,text='هاشتاجات الملفات المحفوظة',bg='#e8edf1',fg='#19394e',font=('Segoe UI',12,'bold')).pack(anchor='e',padx=16,pady=(14,4))
  tk.Label(win,text='إزالة هاشتاج مستخدم تمسحه من كل الملفات التي تحمله.',bg='#e8edf1',fg='#526b7c').pack(anchor='e',padx=16)
  lb=tk.Listbox(win,selectmode='extended',height=10,width=52,exportselection=False);lb.pack(fill='both',padx=16,pady=8)
  for tag in tags:lb.insert('end',tag)
  addrow=tk.Frame(win,bg='#e8edf1');addrow.pack(fill='x',padx=16);value=tk.StringVar();entry=ttk.Entry(addrow,textvariable=value);entry.pack(side='right',fill='x',expand=True)
  def add_tag():
   newtags=['#'+x.strip().lstrip('#') for x in value.get().replace(',',' ').replace('،',' ').split() if x.strip()]
   for tag in newtags:
    if tag not in [lb.get(i) for i in range(lb.size())]:lb.insert('end',tag)
   value.set('')
  ttk.Button(addrow,text='＋ إضافة',command=add_tag).pack(side='left',padx=(6,0))
  buttons=tk.Frame(win,bg='#e8edf1');buttons.pack(fill='x',padx=16,pady=(8,14))
  def remove_selected():
   selected=set(lb.curselection())
   for i in reversed(sorted(selected)):lb.delete(i)
  def save():
   current={lb.get(i) for i in range(lb.size())};removed=set(tags)-current;added=current-set(tags)
   if removed and not messagebox.askyesno('حذف هاشتاجات مستخدمة',f'سيتم حذف {len(removed)} هاشتاج من كتالوج المشروع ومن كل الملفات التي تحملها. متابعة؟',parent=win):return
   with connect() as c:
    for tag in removed:
     c.execute('delete from file_tag_catalog where project=? and tag=?',(self.project,tag))
     c.execute('delete from tags where tag=? and path in (select path from files where project=?)',(tag,self.project))
    c.executemany('insert or ignore into file_tag_catalog(project,tag,created) values(?,?,?)',[(self.project,tag,stamp(time.time())) for tag in current])
   if added:self.log_activity('إضافة هاشتاجات محفوظة','إضافة إلى كتالوج الملفات: '+', '.join(sorted(added)))
   if removed:self.log_activity('حذف هاشتاجات محفوظة','حذف من كتالوج الملفات والملفات المرتبطة: '+', '.join(sorted(removed)))
   self.refresh_tag_filters();self.populate()
   if hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped():self.refresh_search_cache();self.render_search_results()
   win.destroy()
  ttk.Button(buttons,text='حذف المحدد من القائمة',command=remove_selected).pack(side='left');ttk.Button(buttons,text='حفظ',command=save).pack(side='right');ttk.Button(buttons,text='إلغاء',command=win.destroy).pack(side='right',padx=4);win.grab_set();entry.focus_set()

 def _collect_project_folders_fast(self):
  found = {}
  root_res = self.root.resolve()
  try:
   for entry in os.scandir(root_res):
    if entry.is_dir(follow_symlinks=False) and not entry.name.startswith('.'):
     found[entry.name] = (Path(entry.path), entry.name)
     try:
      for sub in os.scandir(entry.path):
       if sub.is_dir(follow_symlinks=False) and not sub.name.startswith('.'):
        rel = f"{entry.name}/{sub.name}"
        found[rel] = (Path(sub.path), rel)
     except OSError: pass
  except OSError: pass

  try:
   with connect() as c:
    rows = c.execute('SELECT DISTINCT rel FROM files WHERE project=?', (self.project,)).fetchall()
    ft_rows = c.execute('SELECT DISTINCT path FROM folder_tags WHERE project=?', (self.project,)).fetchall()
   for r in rows:
    parts = (r[0] or '').split('/')[:-1]
    prefix = ''
    for part in parts:
     if part.startswith('.'): break
     prefix = f'{prefix}/{part}' if prefix else part
     if prefix not in found:
      found[prefix] = (root_res / prefix, prefix)
   for r in ft_rows:
    rel = (r[0] or '').strip()
    if rel and rel != '.' and rel not in found:
     p = root_res / rel
     if p.is_dir(): found[rel] = (p, rel)
  except Exception: pass

  result = list(found.values())
  result.sort(key=lambda x: x[1].casefold())
  return result

 def edit_folder_specialties(self, tree=None, preselect_tag=None):
  selected_dirs = [p.resolve() for p in self.selected_paths(tree) if p.is_dir()]
  if not selected_dirs and getattr(self, 'view_mode', 'files') == 'files':
   if self.current and self.current.is_dir() and self.current.resolve() != self.root.resolve():
    selected_dirs = [self.current.resolve()]
  
  rel_paths = []
  for d in selected_dirs:
   try:
    rel = d.relative_to(self.root.resolve()).as_posix()
    if rel and rel != '.' and not any(r == rel for _, r in rel_paths):
     rel_paths.append((d, rel))
   except ValueError: continue

  with connect() as c:
   c.execute('CREATE TABLE IF NOT EXISTS folder_specialty_catalog(project TEXT, tag TEXT, created TEXT, PRIMARY KEY(project, tag))')
   c.execute('INSERT OR IGNORE INTO folder_specialty_catalog(project, tag, created) SELECT DISTINCT project, tag, created FROM folder_tags WHERE project=?', (self.project,))
   known = sorted({r[0] for r in c.execute('SELECT tag FROM folder_specialty_catalog WHERE project=? UNION SELECT DISTINCT tag FROM folder_tags WHERE project=?', (self.project, self.project))})
   counts_by_tag = {r[0]: r[1] for r in c.execute('SELECT tag, COUNT(DISTINCT path) FROM folder_tags WHERE project=? GROUP BY tag', (self.project,)).fetchall()}

  def get_old_by_rel():
   res = {}
   with connect() as c:
    for _, rel in rel_paths:
     res[rel] = {r[0] for r in c.execute('SELECT tag FROM folder_tags WHERE project=? AND path=?', (self.project, rel))}
   return res

  old_by_rel = get_old_by_rel()
  initial_selected = set().union(*old_by_rel.values()) if old_by_rel else set()
  if preselect_tag:
   initial_selected.add(preselect_tag)

  win = tk.Toplevel(self); win.title('تخصيص المجلد وإدارة التخصصات'); win.transient(self); win.resizable(False, False); win.configure(bg='#e8edf1')
  tk.Label(win, text='تخصيص المجلدات والتخصصات', bg='#e8edf1', fg='#19394e', font=('Segoe UI', 13, 'bold')).pack(anchor='e', padx=16, pady=(14, 4))
  
  folder_bar = tk.Frame(win, bg='#dcebed', highlightbackground='#b8d4d8', highlightthickness=1)
  folder_bar.pack(fill='x', padx=16, pady=(0, 8))
  
  target_var = tk.StringVar()
  def update_target_label():
   if len(rel_paths) == 1:
    target_var.set(f'📁 المجلد المحدد حالياً: «{rel_paths[0][0].name}» ({rel_paths[0][1]})')
   elif len(rel_paths) > 1:
    target_var.set(f'📁 المجلدات المحددة ({len(rel_paths)}): ' + '، '.join(d.name for d, _ in rel_paths[:3]) + ('...' if len(rel_paths) > 3 else ''))
   else:
    target_var.set('📁 لم يتم تحديد مجلد بعينه · يمكنك اختيار مجلد أو الضغط على «اختر مجلدات لهذا التخصص»')

  tk.Button(folder_bar, text='📂 اختيار مجلد آخر...', command=lambda: open_folder_picker_modal(for_tag=None), bg='white', fg='#102c3d', activebackground='#eef5f6', relief='flat', font=('Segoe UI', 8, 'bold'), padx=8, pady=3, cursor='hand2').pack(side='left', padx=8, pady=6)
  update_target_label()
  tk.Label(folder_bar, textvariable=target_var, bg='#dcebed', fg='#102c3d', font=('Segoe UI', 9, 'bold'), justify='right', wraplength=340).pack(side='right', padx=10, pady=6)

  check_vars = {}

  def refresh_counts_map():
   nonlocal counts_by_tag
   with connect() as c:
    counts_by_tag = {r[0]: r[1] for r in c.execute('SELECT tag, COUNT(DISTINCT path) FROM folder_tags WHERE project=? GROUP BY tag', (self.project,)).fetchall()}

  def sync_checks_from_folders():
   nonlocal old_by_rel
   old_by_rel = get_old_by_rel()
   union_tags = set().union(*old_by_rel.values()) if old_by_rel else set()
   if preselect_tag:
    union_tags.add(preselect_tag)
   for t, v in check_vars.items():
    v.set(t in union_tags)

  def open_folder_picker_modal(for_tag=None):
   all_dirs = self._collect_project_folders_fast()
   if not all_dirs:
    return messagebox.showinfo('لا توجد مجلدات', 'لا توجد مجلدات فرعية داخل هذا المشروع بعد.', parent=win)
   
   try: win.grab_release()
   except tk.TclError: pass

   sub = tk.Toplevel(win)
   sub.title(f'اختيار مجلدات للتخصص {for_tag}' if for_tag else 'اختيار المجلدات المستهدفة')
   sub.transient(win); sub.configure(bg='#e8edf1'); sub.geometry('480x440')
   
   header_txt = f'ضع علامة (☑) أمام المجلدات المنتمية للتخصص «{for_tag}»:' if for_tag else 'ضع علامة (☑) أمام المجلدات التي تريد تخصيصها الآن:'
   tk.Label(sub, text=header_txt, bg='#e8edf1', fg='#19394e', font=('Segoe UI', 10, 'bold')).pack(anchor='e', padx=14, pady=(12, 4))
   
   search_frame = tk.Frame(sub, bg='#e8edf1'); search_frame.pack(fill='x', padx=14, pady=(0, 6))
   tk.Label(search_frame, text='بحث سريع:', bg='#e8edf1', fg='#526b7c', font=('Segoe UI', 9)).pack(side='right', padx=(0, 4))
   filter_var = tk.StringVar()
   filter_entry = ttk.Entry(search_frame, textvariable=filter_var, justify='right')
   filter_entry.pack(side='right', fill='x', expand=True)

   list_wrap = tk.Frame(sub, bg='white', highlightbackground='#d6e0e6', highlightthickness=1)
   list_wrap.pack(fill='both', expand=True, padx=14, pady=4)
   
   dir_tree = ttk.Treeview(list_wrap, columns=('mark', 'name', 'rel'), show='headings', selectmode='browse')
   dir_tree.heading('mark', text='تحديد'); dir_tree.column('mark', width=50, anchor='center', stretch=False)
   dir_tree.heading('name', text='اسم المجلد'); dir_tree.column('name', width=160, anchor='e')
   dir_tree.heading('rel', text='المسار داخل المشروع'); dir_tree.column('rel', width=220, anchor='e')
   
   sb = ttk.Scrollbar(list_wrap, orient='vertical', command=dir_tree.yview)
   dir_tree.configure(yscrollcommand=sb.set)
   sb.pack(side='left', fill='y'); dir_tree.pack(side='right', fill='both', expand=True)

   if for_tag:
    with connect() as c:
     selected_set = {r[0] for r in c.execute('SELECT path FROM folder_tags WHERE project=? AND tag=?', (self.project, for_tag)).fetchall()}
   else:
    selected_set = {r for _, r in rel_paths}

   dir_map = {r_str: fp for fp, r_str in all_dirs}

   def populate_dir_tree(*_):
    q = filter_var.get().strip().casefold()
    dir_tree.delete(*dir_tree.get_children())
    for fp, r_str in all_dirs:
     if q and q not in fp.name.casefold() and q not in r_str.casefold():
      continue
     mark = '☑' if r_str in selected_set else '☐'
     dir_tree.insert('', 'end', iid=r_str, values=(mark, f'📁 {fp.name}', r_str))

   def toggle_dir_row(event):
    iid = dir_tree.identify_row(event.y)
    if not iid: return
    if iid in selected_set: selected_set.remove(iid)
    else: selected_set.add(iid)
    vals = list(dir_tree.item(iid, 'values'))
    vals[0] = '☑' if iid in selected_set else '☐'
    dir_tree.item(iid, values=vals)
    return 'break'

   dir_tree.bind('<ButtonPress-1>', toggle_dir_row)
   dir_tree.bind('<Return>', lambda e: toggle_dir_row(e))
   filter_var.trace_add('write', populate_dir_tree)
   populate_dir_tree()

   def close_sub():
    try: sub.grab_release()
    except tk.TclError: pass
    sub.destroy()
    try:
     if win.winfo_exists(): win.grab_set(); win.lift(); win.focus_force()
    except tk.TclError: pass

   def confirm_dirs():
    if for_tag:
     now_str = stamp(time.time())
     with connect() as c:
      c.execute('INSERT OR IGNORE INTO folder_specialty_catalog(project, tag, created) VALUES(?,?,?)', (self.project, for_tag, now_str))
      c.execute('DELETE FROM folder_tags WHERE project=? AND tag=?', (self.project, for_tag))
      c.executemany('INSERT OR IGNORE INTO folder_tags(project, path, tag, created) VALUES(?,?,?,?)', [(self.project, r_str, for_tag, now_str) for r_str in sorted(selected_set)])
     self.log_activity('تخصيص المجلد', f'تحديث مجلدات التخصص {for_tag} ({len(selected_set)} مجلد)')
     refresh_counts_map()
     sync_checks_from_folders()
     render_specialty_checkboxes()
     self.refresh_tag_filters()
     self.populate()
     self.update_rail_selection()
    else:
     rel_paths.clear()
     for r_str in sorted(selected_set):
      if r_str in dir_map: rel_paths.append((dir_map[r_str], r_str))
     update_target_label()
     sync_checks_from_folders()
    close_sub()

   sub.protocol('WM_DELETE_WINDOW', close_sub)
   b_row = tk.Frame(sub, bg='#e8edf1'); b_row.pack(fill='x', padx=14, pady=10)
   tk.Button(b_row, text='✓ حفظ وتأكيد الاختيار', command=confirm_dirs, bg='#087e8b', fg='white', relief='flat', font=('Segoe UI', 9, 'bold'), padx=14, pady=5, cursor='hand2').pack(side='right')
   ttk.Button(b_row, text='تحديد الكل', command=lambda: (selected_set.update(dir_map.keys()), populate_dir_tree())).pack(side='right', padx=4)
   ttk.Button(b_row, text='إلغاء الكل', command=lambda: (selected_set.clear(), populate_dir_tree())).pack(side='right', padx=2)
   ttk.Button(b_row, text='إغلاق', command=close_sub).pack(side='left')
   
   sub.update_idletasks()
   bx = win.winfo_rootx() + (win.winfo_width() - 480) // 2
   by = win.winfo_rooty() + (win.winfo_height() - 440) // 2
   sub.geometry(f'480x440+{max(0, bx)}+{max(0, by)}')
   try: sub.grab_set(); filter_entry.focus_set()
   except tk.TclError: pass

  tk.Label(win, text='ضع علامة (☑) أمام التخصصات لربط المجلد بها (أو اضغط «اختر مجلدات لهذا التخصص» لتعيين عدة مجلدات):', bg='#e8edf1', fg='#526b7c', font=('Segoe UI', 9), justify='right', wraplength=480).pack(anchor='e', padx=16, pady=(2, 2))

  box_frame = tk.Frame(win, bg='white', highlightbackground='#d6e0e6', highlightthickness=1, height=210, width=490)
  box_frame.pack(fill='both', expand=True, padx=16, pady=4)
  box_frame.pack_propagate(False)
  
  spec_canvas = tk.Canvas(box_frame, bg='white', highlightthickness=0)
  spec_scroll = ttk.Scrollbar(box_frame, orient='vertical', command=spec_canvas.yview)
  spec_inner = tk.Frame(spec_canvas, bg='white')
  spec_scroll.pack(side='left', fill='y')
  spec_canvas.pack(side='right', fill='both', expand=True)
  spec_canvas.configure(yscrollcommand=spec_scroll.set)
  spec_win = spec_canvas.create_window((0, 0), window=spec_inner, anchor='nw')
  spec_inner.bind('<Configure>', lambda e: spec_canvas.configure(scrollregion=spec_canvas.bbox('all')))
  spec_canvas.bind('<Configure>', lambda e: spec_canvas.itemconfig(spec_win, width=e.width))

  def render_specialty_checkboxes():
   for w in spec_inner.winfo_children(): w.destroy()
   if not known:
    tk.Label(spec_inner, text='لا توجد تخصصات بعد. اكتب اسم التخصص بالأسفل واضغط إضافة.', bg='white', fg='#718491', font=('Segoe UI', 9)).pack(pady=30)
    return
   for tag in known:
    if tag not in check_vars:
     check_vars[tag] = tk.BooleanVar(value=(tag in initial_selected))
    row_f = tk.Frame(spec_inner, bg='white', highlightbackground='#eef2f5', highlightthickness=1)
    row_f.pack(fill='x', padx=6, pady=3)
    
    tk.Button(row_f, text='× حذف', command=lambda t=tag: delete_single_specialty(t), bg='#fff5f5', fg='#bd4856', activebackground='#fce4e4', relief='flat', font=('Segoe UI', 8), padx=6, cursor='hand2').pack(side='left', padx=4, pady=3)
    tk.Button(row_f, text='📁 اختر مجلدات لهذا التخصص...', command=lambda t=tag: open_folder_picker_modal(for_tag=t), bg='#f0f7f8', fg='#087e8b', activebackground='#dceef0', relief='flat', font=('Segoe UI', 8, 'bold'), padx=8, cursor='hand2').pack(side='left', padx=4, pady=3)
    
    cb = tk.Checkbutton(row_f, text=tag, variable=check_vars[tag], bg='white', activebackground='white', fg='#19394e', font=('Segoe UI', 10, 'bold'), anchor='e', cursor='hand2')
    cb.pack(side='right', padx=6, pady=3)
    
    cnt = counts_by_tag.get(tag, 0)
    tk.Label(row_f, text=f'({cnt} مجلد)', bg='white', fg='#82919b', font=('Segoe UI', 8)).pack(side='right', padx=2)

  def delete_single_specialty(tag):
   if not messagebox.askyesno('حذف التخصص نهائيًا', f'سيتم حذف التخصص «{tag}» من القائمة الجانبية للمشروع ومن كل المجلدات المرتبطة به. متابعة؟', parent=win):
    return
   with connect() as c:
    c.execute('DELETE FROM folder_specialty_catalog WHERE project=? AND tag=?', (self.project, tag))
    c.execute('DELETE FROM folder_tags WHERE project=? AND tag=?', (self.project, tag))
   self.log_activity('حذف تخصص', f'حذف التخصص {tag} من المشروع')
   if tag in known: known.remove(tag)
   check_vars.pop(tag, None)
   refresh_counts_map()
   render_specialty_checkboxes()
   if self.view_mode == 'specialty' and getattr(self, 'specialty_filter', '') == tag:
    self.show_files_collection()
   else:
    self.refresh_tag_filters(); self.populate(); self.update_rail_selection()

  render_specialty_checkboxes()

  row = tk.Frame(win, bg='#e8edf1'); row.pack(fill='x', padx=16, pady=(6, 2))
  value = tk.StringVar(); entry = ttk.Entry(row, textvariable=value, justify='right', font=('Segoe UI', 10)); entry.pack(side='right', fill='x', expand=True)

  def add_specialty(_=None):
   new_items = ['#' + x.strip().lstrip('#') for x in value.get().replace(',', ' ').replace('،', ' ').split() if x.strip()]
   if not new_items: return
   now_str = stamp(time.time())
   with connect() as c:
    for tag in new_items:
     c.execute('INSERT OR IGNORE INTO folder_specialty_catalog(project, tag, created) VALUES(?,?,?)', (self.project, tag, now_str))
   for tag in new_items:
    if tag not in known:
     known.append(tag)
    check_vars[tag] = tk.BooleanVar(value=True)
   value.set('')
   render_specialty_checkboxes()
   self.refresh_specialty_nav()

  entry.bind('<Return>', add_specialty)
  tk.Button(row, text='＋ إضافة تخصص جديد', command=add_specialty, bg='#102c3d', fg='white', relief='flat', font=('Segoe UI', 9, 'bold'), padx=10, pady=4, cursor='hand2').pack(side='left', padx=(6, 0))

  buttons = tk.Frame(win, bg='#e8edf1'); buttons.pack(fill='x', padx=16, pady=(12, 14))
  def save():
   if value.get().strip(): add_specialty()
   chosen = {t for t, v in check_vars.items() if v.get()}
   if chosen and not rel_paths:
    if messagebox.askyesno('اختر مجلدًا أولاً', 'لقد قمت بتحديد تخصصات ولكن لم تختر أي مجلد لربطه بها!\n\nهل تريد اختيار مجلد من المشروع الآن لوضعه في هذا التخصص؟', parent=win):
     open_folder_picker_modal(for_tag=None)
    return
   now_str = stamp(time.time())
   logs_to_write = []
   with connect() as c:
    c.executemany('INSERT OR IGNORE INTO folder_specialty_catalog(project, tag, created) VALUES(?,?,?)', [(self.project, t, now_str) for t in known])
    for d, rel in rel_paths:
     c.execute('DELETE FROM folder_tags WHERE project=? AND path=?', (self.project, rel))
     c.executemany('INSERT OR IGNORE INTO folder_tags(project, path, tag, created) VALUES(?,?,?,?)', [(self.project, rel, t, now_str) for t in chosen])
     prev = old_by_rel.get(rel, set())
     added = chosen - prev; removed = prev - chosen
     if added: logs_to_write.append(('تخصيص المجلد', f'إضافة تخصصات للمجلد «{d.name}»: ' + ', '.join(sorted(added)), d))
     if removed: logs_to_write.append(('تخصيص المجلد', f'إزالة تخصصات من المجلد «{d.name}»: ' + ', '.join(sorted(removed)), d))
   for act, det, p_log in logs_to_write:
    self.log_activity(act, det, path=p_log)
   self.refresh_tag_filters(); self.populate(); self.update_rail_selection(); win.destroy()

  tk.Button(buttons, text='✔ حفظ ربط المجلد بالتخصصات المحددة', command=save, bg='#087e8b', fg='white', activebackground='#066b76', relief='flat', font=('Segoe UI', 9, 'bold'), padx=14, pady=6, cursor='hand2').pack(side='right')
  ttk.Button(buttons, text='إغلاق', command=win.destroy).pack(side='left')
  win.update_idletasks()
  bx = self.winfo_rootx() + (self.winfo_width() - win.winfo_reqwidth()) // 2
  by = self.winfo_rooty() + (self.winfo_height() - win.winfo_reqheight()) // 2
  win.geometry(f'+{max(0, bx)}+{max(0, by)}')
  try: win.grab_set(); entry.focus_set()
  except tk.TclError: pass

 def edit_tags(self):
  paths=[p for p in self.selected_paths() if p.is_file()]
  if not paths:return messagebox.showinfo('اختيار ملف','حدد ملفًا أو أكثر أولًا.')
  keys=[str(p.resolve()) for p in paths]
  with connect() as c:
   known=sorted({r[0] for r in c.execute('select tag from file_tag_catalog where project=? union select distinct t.tag from tags t join files f on f.path=t.path where f.project=?',(self.project,self.project))})
   old_by_path={key:{r[0] for r in c.execute('select tag from tags where path=?',(key,))} for key in keys}
   old=set().union(*old_by_path.values()) if old_by_path else set()
  win=tk.Toplevel(self);win.title('هاشتج الملف');win.transient(self);win.resizable(False,False);win.configure(bg='#e8edf1')
  tk.Label(win,text=f'هاشتج الملف · {len(paths):,} ملف محدد',bg='#e8edf1',fg='#19394e',font=('Segoe UI',11,'bold')).pack(anchor='e',padx=16,pady=(14,6))
  tk.Label(win,text='اختر هاشتاجات محفوظة أو اكتب هاشتاجًا جديدًا. الاختيارات ستحل محل هاشتاجات الملفات المحددة.',bg='#e8edf1',fg='#526b7c',wraplength=420,justify='right').pack(anchor='e',padx=16)
  lb=tk.Listbox(win,selectmode='multiple',height=9,width=48,exportselection=False);lb.pack(fill='both',padx=16,pady=8)
  for tag in known:lb.insert('end',tag)
  for i,tag in enumerate(known):
   if tag in old:lb.selection_set(i)
  row=tk.Frame(win,bg='#e8edf1');row.pack(fill='x',padx=16)
  suggestions=ttk.Combobox(row,values=known,state='readonly',width=20,style='Office.TCombobox');suggestions.pack(side='left',padx=(0,6))
  def use_suggestion(_=None):
   selected=suggestions.get()
   if selected in known:lb.selection_set(known.index(selected))
  suggestions.bind('<<ComboboxSelected>>',use_suggestion)
  tk.Label(win,text='أضف هاشتاجات جديدة مفصولة بمسافات أو فواصل:',bg='#e8edf1',fg='#526b7c').pack(anchor='e',padx=16,pady=(8,0))
  state=tk.StringVar();new_entry=ttk.Entry(win,textvariable=state,width=52);new_entry.pack(fill='x',padx=16,pady=5)
  buttons=tk.Frame(win,bg='#e8edf1');buttons.pack(fill='x',padx=16,pady=(5,14))
  def save():
   selected={lb.get(i) for i in lb.curselection()};selected.update('#'+x.strip().lstrip('#') for x in state.get().replace(',',' ').replace('،',' ').split() if x.strip())
   changes=[]
   with connect() as c:
    for key in keys:
     c.execute('delete from tags where path=?',(key,));c.executemany('insert or ignore into tags(path,tag) values(?,?)',[(key,t) for t in selected])
    c.executemany('insert or ignore into file_tag_catalog(project,tag,created) values(?,?,?)',[(self.project,t,stamp(time.time())) for t in selected])
    for p,key in zip(paths,keys):
     previous=old_by_path.get(key,set());added=selected-previous;removed=previous-selected
     if added or removed:
      details=f'«{p.name}»'
      if added:details+=' · إضافة: '+', '.join(sorted(added))
      if removed:details+=' · إزالة: '+', '.join(sorted(removed))
      changes.append((p,details))
   for p,details in changes:self.log_activity('تعديل هاشتاجات الملف',details,path=p)
   self.refresh_tag_filters();self.populate()
   if hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped():self.refresh_search_cache();self.render_search_results()
   win.destroy()
  ttk.Button(buttons,text='حفظ الهاشتاجات',command=save).pack(side='right');ttk.Button(buttons,text='إلغاء',command=win.destroy).pack(side='left');win.grab_set();new_entry.focus_set()

 def copy_selected_paths(self,tree=None):
  paths=self.selected_paths(tree)
  if not paths:return
  self.clipboard_clear();self.clipboard_append('\n'.join(str(p) for p in paths))
  if hasattr(self,'status'):self.status.set(f'تم نسخ مسارات {len(paths):,} ملف')

 def selected_paths(self,tree=None):
  if tree is None:
   tree=getattr(self,'file_tree',None)
   if hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped() and self.search_nb.tabs():tree=self.search_views.get(self.search_nb.tab(self.search_nb.select(),'text'),tree)
  return [Path(p) for p in (tree.selection() if tree else ()) if not str(p).startswith('activity:')]

 def clear_selected_tags(self,tree):
  paths=[p for p in self.selected_paths(tree) if p.is_file()]
  if not paths:return
  count=len(paths)
  if count>1 and not messagebox.askyesno('مسح الهاشتاجات',f'مسح كل الهاشتاجات من {count} ملفات محددة؟',parent=self):return
  with connect() as c:
   old={str(p.resolve()):[r[0] for r in c.execute('select tag from tags where path=?',(str(p.resolve()),))] for p in paths}
   c.executemany('delete from tags where path=?',[(str(p.resolve()),) for p in paths])
  changed=[p for p in paths if old.get(str(p.resolve()))]
  if changed:self.log_activity('مسح هاشتاجات الملف',f'مسح الهاشتاجات من {len(changed):,} ملف · '+', '.join(p.name for p in changed),path=changed[0] if len(changed)==1 else None)
  if hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped():
   with connect() as c:self.search_cache=c.execute("select f.*,group_concat(t.tag, ' ') tags from files f left join tags t on t.path=f.path where f.project=? group by f.path",(self.project,)).fetchall()
   self.render_search_results()
  self.populate()