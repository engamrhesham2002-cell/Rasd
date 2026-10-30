# Rasd - حذف/نسخ المسارات، القائمة اليمنى، التنقل الذكي (رجوع/أمام/أعلى)، وإزالة من التخصص
from common import *
from update_utils import *
from storage import *
import shutil
import uuid
import threading
import time

class FileOpsMixin:
 def copy_files_to_clipboard(self, tree=None, is_cut=False):
  paths = [p.resolve() for p in self.selected_paths(tree) if p.exists()]
  if not paths: return
  self.app_clipboard = {'action': 'cut' if is_cut else 'copy', 'paths': paths}
  if hasattr(self, 'status'):
   self.status.set(f"تم {'قص' if is_cut else 'نسخ'} {len(paths):,} عنصر. جاهز للصق.")

 def paste_files(self):
  clip = getattr(self, 'app_clipboard', None)
  if not clip or not clip['paths']: return
  
  target_dir = self.current
  if not target_dir or not target_dir.is_dir(): return
  
  action = clip['action']
  paths = clip['paths']
  
  self.status.set("جارٍ اللصق...")
  self.update_idletasks()
  
  def _paste_worker():
   now_str = stamp(time.time())
   for p in paths:
    if not p.exists(): continue
    target_path = target_dir / p.name
    
    counter = 1
    while target_path.exists():
     target_path = target_dir / f"{p.stem}_{counter}{p.suffix}"
     counter += 1
     
    try:
     if action == 'cut': shutil.move(str(p), str(target_path))
     else:
      if p.is_dir(): shutil.copytree(str(p), str(target_path))
      else: shutil.copy2(str(p), str(target_path))
      
     with connect() as c:
      c.execute("INSERT INTO activity_log(project,action,details,path,occurred_at) VALUES(?,?,?,?,?)", (self.project, f"{'نقل' if action == 'cut' else 'نسخ'} ملف", f"إلى: {target_path.name}", str(target_path), now_str))
    except Exception as e:
     self.after(0, lambda err=e, name=p.name: messagebox.showerror("خطأ في اللصق", f"تعذر لصق {name}\n{err}", parent=self))
   
   if action == 'cut': self.app_clipboard = None
   self.after(0, self.rescan)

  threading.Thread(target=_paste_worker, daemon=True).start()

 def remove_selected_from_current_specialty(self, tree=None):
  spec_tag = getattr(self, 'specialty_filter', None)
  if getattr(self, 'view_mode', '') != 'specialty' or not spec_tag:
   return
  selected_dirs = [p.resolve() for p in self.selected_paths(tree) if p.is_dir()]
  if not selected_dirs:
   return messagebox.showinfo('التخصصات', 'حدد مجلداً أو أكثر أولاً لإزالته من هذا التخصص.', parent=self)
  
  rels = []
  for d in selected_dirs:
   try:
    rel = d.relative_to(self.root.resolve()).as_posix()
    if rel and rel != '.':
     rels.append((d, rel))
   except ValueError:
    continue
  if not rels:
   return

  with connect() as c:
   for _, rel in rels:
    c.execute('DELETE FROM folder_tags WHERE project=? AND path=? AND tag=?', (self.project, rel, spec_tag))
  
  for d, _ in rels:
   self.log_activity('تخصيص المجلد', f'إزالة المجلد «{d.name}» من التخصص {spec_tag}', path=d)
  
  if hasattr(self, 'status'):
   self.status.set(f'تمت إزالة {len(rels):,} مجلد من التخصص {spec_tag}')
  self.refresh_tag_filters()
  self.populate()
  self.update_rail_selection()

 def delete_selected_paths(self, tree=None):
  paths = [p.resolve() for p in self.selected_paths(tree) if p.exists()]
  if not paths: return
  root = self.root.resolve()
  safe = []
  for path in paths:
   try: path.relative_to(root)
   except ValueError: continue
   if path != root and path not in safe: safe.append(path)
  
  if not safe: return messagebox.showwarning('الحذف غير متاح', 'لا يمكن حذف ملفات خارج مجلد المشروع أو حذف مجلد المشروع نفسه.', parent=self)
  
  if not messagebox.askyesno('سلة المهملات', f'هل تريد نقل {len(safe):,} عنصر إلى سلة المهملات الداخلية للمشروع؟\n\n(يمكنك استرجاعهم لاحقاً من قسم سلة المهملات)', icon='warning', parent=self): return
  
  self.status.set("جارٍ نقل العناصر إلى السلة...")
  
  if hasattr(self, 'hide_excel_preview'): self.hide_excel_preview()
  if hasattr(self, 'preview_image'): self.preview_image.delete('all')
  if getattr(self, 'preview_future', None) and not self.preview_future.done():
   self.preview_future.cancel()

  bin_dir = LOG / '.recycle_bin' / self.project
  bin_dir.mkdir(parents=True, exist_ok=True)
  if os.name == 'nt':
   try:
    import ctypes
    ctypes.windll.kernel32.SetFileAttributesW(str(LOG / '.recycle_bin'), 2)
   except: pass

  def _delete_worker():
   time.sleep(0.3)
   now_str = stamp(time.time())
   deleted_count = 0
   errors = []
   
   db_records = []
   activities = []
   for p in safe:
    unique_name = f"{uuid.uuid4().hex[:8]}_{p.name}"
    bin_path = bin_dir / unique_name
    try:
     shutil.move(str(p), str(bin_path))
     db_records.append({'orig': str(p), 'bin': str(bin_path)})
     activities.append((self.project, "حذف إلى السلة", f"تم نقل {p.name} إلى السلة.", str(p), now_str))
     deleted_count += 1
    except Exception as e:
     errors.append(f"{p.name}: {str(e)[:50]}")
   
   if db_records:
    for attempt in range(5):
     try:
      with connect() as c:
       for r in db_records:
        c.execute("INSERT INTO recycle_bin(project, original_path, bin_path, deleted_at) VALUES(?,?,?,?)", (self.project, r['orig'], r['bin'], now_str))
        c.execute('DELETE FROM tags WHERE path=?', (r['orig'],))
        c.execute('DELETE FROM files WHERE path=?', (r['orig'],))
        c.execute('DELETE FROM favorites WHERE path=?', (r['orig'],))
        c.execute('DELETE FROM file_links WHERE path1=? OR path2=?', (r['orig'], r['orig']))
       c.executemany("INSERT INTO activity_log(project,action,details,path,occurred_at) VALUES(?,?,?,?,?)", activities)
      break
     except sqlite3.OperationalError as db_err:
      if 'locked' in str(db_err).lower(): time.sleep(0.5)
      else: raise db_err
   
   def _update_ui():
    if errors:
     msg = "\n".join(errors[:4])
     if len(errors) > 4: msg += f"\n... و {len(errors)-4} أخطاء أخرى."
     messagebox.showerror('خطأ في الحذف', f'تعذر حذف بعض الملفات، ربما تكون مفتوحة في برنامج آخر:\n{msg}', parent=self)
    self.status.set(f"تم نقل {deleted_count} عنصر إلى السلة.")
    self.rescan()

   self.after(0, _update_ui)
  
  threading.Thread(target=_delete_worker, daemon=True).start()

 def restore_recycled_files(self, bin_paths):
  if not bin_paths: return
  self.status.set("جارٍ استرجاع الملفات...")
  
  def _restore_worker():
   time.sleep(0.1)
   errors = []
   restored = 0
   now_str = stamp(time.time())
   
   records_to_restore = []
   with connect() as c:
    for b_path in bin_paths:
     r = c.execute("SELECT * FROM recycle_bin WHERE bin_path=?", (str(b_path),)).fetchone()
     if r: records_to_restore.append(dict(r))
     
   success_ids = []
   activities = []
   for rec in records_to_restore:
    orig = Path(rec['original_path'])
    b_path = Path(rec['bin_path'])
    try:
     if b_path.exists():
      orig.parent.mkdir(parents=True, exist_ok=True)
      shutil.move(str(b_path), str(orig))
     success_ids.append(rec['id'])
     activities.append((self.project, "استرجاع ملف", f"تم استرجاع {orig.name} لمكانه الأصلي", str(orig), now_str))
     restored += 1
    except Exception as e:
     errors.append(f"{orig.name}: {str(e)[:50]}")
     
   if success_ids:
    for attempt in range(5):
     try:
      with connect() as c:
       c.executemany("DELETE FROM recycle_bin WHERE id=?", [(i,) for i in success_ids])
       c.executemany("INSERT INTO activity_log(project,action,details,path,occurred_at) VALUES(?,?,?,?,?)", activities)
      break
     except sqlite3.OperationalError as db_err:
      if 'locked' in str(db_err).lower(): time.sleep(0.5)
      else: raise db_err
       
   def _update_ui():
    if errors:
     msg = "\n".join(errors[:4])
     messagebox.showerror('خطأ', f'تعذر استرجاع بعض الملفات:\n{msg}', parent=self)
    self.status.set(f"تم استرجاع {restored} ملفات.")
    self.show_collection('recycle_bin')
    self.rescan()
    
   self.after(0, _update_ui)

  threading.Thread(target=_restore_worker, daemon=True).start()

 def empty_recycle_bin(self, specific_paths=None):
  msg = f"حذف {len(specific_paths)} عنصر نهائياً؟" if specific_paths else "هل تريد إفراغ سلة المهملات بالكامل لهذا المشروع؟\n\n(لا يمكن التراجع عن هذا الإجراء)"
  if not messagebox.askyesno('تفريغ السلة', msg, parent=self): return
  
  self.status.set("جارٍ الحذف النهائي...")
  
  def _empty_worker():
   time.sleep(0.1)
   now_str = stamp(time.time())
   logs = []
   
   if specific_paths:
    for b_path in specific_paths:
     try:
      p = Path(b_path)
      if p.is_dir(): shutil.rmtree(str(p))
      else: p.unlink(missing_ok=True)
      logs.append((self.project, "تفريغ السلة", f"تم الحذف النهائي لـ {p.name}", str(p), now_str))
     except: pass
   else:
    bin_dir = LOG / '.recycle_bin' / self.project
    if bin_dir.exists(): shutil.rmtree(str(bin_dir), ignore_errors=True)
    logs.append((self.project, "تفريغ السلة", "تم تفريغ سلة المهملات بالكامل من المجلد المؤقت", "", now_str))
      
   for attempt in range(5):
    try:
     with connect() as c:
      if specific_paths:
       c.executemany("DELETE FROM recycle_bin WHERE bin_path=?", [(str(b_path),) for b_path in specific_paths])
      else:
       c.execute("DELETE FROM recycle_bin WHERE project=?", (self.project,))
      
      if logs:
       c.executemany("INSERT INTO activity_log(project,action,details,path,occurred_at) VALUES(?,?,?,?,?)", logs)
     break
    except sqlite3.OperationalError as db_err:
     if 'locked' in str(db_err).lower(): time.sleep(0.5)
     else: raise db_err
   
   def _update_ui():
    self.show_collection('recycle_bin')
    self.status.set("تم تفريغ الملفات بنجاح.")
    
   self.after(0, _update_ui)
   
  threading.Thread(target=_empty_worker, daemon=True).start()

 def context_menu(self, e, tree):
  row = tree.identify_row(e.y)
  if not row:
   menu = tk.Menu(self, tearoff=0, font=('Segoe UI', 10))
   clip = getattr(self, 'app_clipboard', None)
   if clip and clip['paths'] and getattr(self, 'view_mode', 'files') == 'files':
    menu.add_command(label='📋 لصق (Paste)', command=self.paste_files)
   if getattr(self, 'view_mode', '') == 'recycle_bin':
    menu.add_command(label='🗑 تفريغ السلة بالكامل', command=self.empty_recycle_bin, foreground='#bd4856')
   elif getattr(self, 'view_mode', '') == 'changes':
    menu.add_command(label='🗑 مسح كل أحداث السجل المعروض', command=self.clear_displayed_activity_log, foreground='#bd4856')
   if menu.index('end') is not None:
    menu.tk_popup(e.x_root, e.y_root)
   return

  if row not in tree.selection():
   tree.selection_set(row)
   tree.focus(row)
   self.on_tree_selection(tree)
  
  event=getattr(self,'activity_rows',{}).get(str(row))
  if event:
   menu=tk.Menu(self,tearoff=0,font=('Segoe UI', 10));target=Path(event['path']) if event['path'] else None
   if target and target.exists():menu.add_command(label='📂 فتح الملف أو المجلد المرتبط',command=lambda p=target:self.navigate_to(p) if p.is_dir() else self.open_file(p))
   menu.add_command(label='📋 نسخ تفاصيل الحدث',command=lambda d=event['details']:(self.clipboard_clear(),self.clipboard_append(d)))
   menu.add_separator()
   sel_events = [iid for iid in tree.selection() if str(iid).startswith('activity:')]
   lbl_del = f'🗑 مسح الأحداث المحددة ({len(sel_events)})' if len(sel_events) > 1 else '🗑 مسح هذا الحدث من السجل'
   menu.add_command(label=lbl_del, command=lambda: self.delete_selected_activity_logs(tree), foreground='#bd4856')
   menu.add_command(label='🧹 مسح السجل المعروض بالكامل...', command=self.clear_displayed_activity_log, foreground='#bd4856')
   menu.tk_popup(e.x_root,e.y_root);return

  if getattr(self, 'view_mode', '') == 'recycle_bin':
   menu = tk.Menu(self, tearoff=0, font=('Segoe UI', 10))
   selected = self.selected_paths(tree)
   menu.add_command(label='↩️ استرجاع لمكانه الأصلي', command=lambda: self.restore_recycled_files(selected))
   menu.add_command(label='🗑 حذف نهائي', command=lambda: self.empty_recycle_bin(selected), foreground='#bd4856')
   menu.tk_popup(e.x_root, e.y_root)
   return

  selected = self.selected_paths(tree)
  p = Path(row)
  files = [x for x in selected if x.is_file()]
  dirs = [x for x in selected if x.is_dir()]
  menu = tk.Menu(self, tearoff=0, font=('Segoe UI', 10))
  
  if len(selected) == 1:
   if p.is_dir(): menu.add_command(label='📂 فتح المجلد', command=lambda: self.navigate_to(p))
   else: menu.add_command(label='📄 فتح الملف', command=lambda: self.open_file(p))
   menu.add_separator()

  if len(selected) == 1 and p.is_file():
   menu.add_command(label='🔗 إدارة ربط الملفات...', command=lambda: self.manage_file_links(p))
   menu.add_separator()

  menu.add_command(label='✂️ قص (Cut)', command=lambda: self.copy_files_to_clipboard(tree, is_cut=True))
  menu.add_command(label='📑 نسخ (Copy)', command=lambda: self.copy_files_to_clipboard(tree, is_cut=False))
  
  clip = getattr(self, 'app_clipboard', None)
  if clip and clip['paths'] and len(selected) == 1 and p.is_dir():
   menu.add_command(label='📋 لصق داخل المجلد', command=lambda target=p: self._paste_into(target))
      
  menu.add_separator()
  
  fav_label = '☆ إزالة من المفضلة' if selected and all(self.is_favorite(x) for x in selected) else '★ إضافة إلى المفضلة'
  menu.add_command(label=fav_label, command=lambda: self.toggle_favorite(selected))
  
  if dirs:
   menu.add_command(label=f'📁 تخصيص المجلد ({len(dirs)} مجلد)' if len(dirs)>1 else '📁 تخصيص المجلد', command=lambda: self.edit_folder_specialties(tree))
   if getattr(self, 'view_mode', '') == 'specialty' and getattr(self, 'specialty_filter', None):
    spec_t = self.specialty_filter
    rm_lbl = f'× إزالة من التخصص «{spec_t}» ({len(dirs)} مجلد)' if len(dirs)>1 else f'× إزالة من التخصص «{spec_t}»'
    menu.add_command(label=rm_lbl, command=lambda: self.remove_selected_from_current_specialty(tree), foreground='#bd4856')

  if files:
   menu.add_command(label=f'🏷 هاشتج الملف ({len(files)} ملف)' if len(files)>1 else '🏷 هاشتج الملف', command=self.edit_tags)
   menu.add_command(label=f'مسح كل الهاشتاجات ({len(files)} ملف)' if len(files)>1 else 'مسح كل الهاشتاجات',command=lambda:self.clear_selected_tags(tree))
   
  if selected and all(path.exists() for path in selected):
   menu.add_separator()
   menu.add_command(label=f'🗑 إرسال إلى سلة المحذوفات ({len(selected)})', command=lambda: self.delete_selected_paths(tree), foreground='#bd4856')
      
  menu.tk_popup(e.x_root, e.y_root)

 def _paste_into(self, target_dir):
  old_current = self.current
  self.current = target_dir
  self.paste_files()
  self.current = old_current

 def manage_file_links(self, path):
  path = Path(path).resolve()
  str_path = str(path)
  
  win = tk.Toplevel(self); win.title('إدارة ربط الملفات'); win.transient(self); win.resizable(False, False); win.configure(bg='#e8edf1')
  tk.Label(win, text='🔗 شبكة الملفات المرتبطة', bg='#e8edf1', fg='#19394e', font=('Segoe UI', 13, 'bold')).pack(anchor='e', padx=16, pady=(14, 4))
  tk.Label(win, text=f'الملف: {path.name}\nاربط هذا الملف بملفات أخرى لتظهر معاً في المعاينة في نفس اللحظة.', bg='#e8edf1', fg='#526b7c', font=('Segoe UI', 9), justify='right').pack(anchor='e', padx=16, pady=(0,8))
  
  list_frame = tk.Frame(win, bg='white', highlightbackground='#d6e0e6', highlightthickness=1)
  list_frame.pack(fill='both', expand=True, padx=16, pady=4)
  
  tree = ttk.Treeview(list_frame, columns=('name', 'path'), show='headings', height=6)
  tree.heading('name', text='الملف المرتبط'); tree.heading('path', text='المسار')
  tree.column('name', width=180, anchor='e'); tree.column('path', width=220, anchor='e')
  
  ybar = ttk.Scrollbar(list_frame, orient='vertical', command=tree.yview)
  tree.configure(yscrollcommand=ybar.set)
  tree.pack(side='right', fill='both', expand=True); ybar.pack(side='left', fill='y')
  
  def refresh_links():
   for iid in tree.get_children(): tree.delete(iid)
   with connect() as c:
    links = c.execute("SELECT path2 FROM file_links WHERE path1=? UNION SELECT path1 FROM file_links WHERE path2=?", (str_path, str_path)).fetchall()
   for r in links:
    linked_p = Path(r[0])
    if linked_p.exists():
     try: rel = linked_p.relative_to(self.root).as_posix()
     except: rel = str(linked_p)
     tree.insert('', 'end', values=(linked_p.name, rel), tags=(str(linked_p),))
  
  refresh_links()
  
  btn_frame = tk.Frame(win, bg='#e8edf1'); btn_frame.pack(fill='x', padx=16, pady=10)
  
  def add_link():
   chosen = filedialog.askopenfilenames(parent=win, initialdir=str(self.root), title='اختر الملفات للربط')
   if not chosen: return
   with connect() as c:
    for c_path in chosen:
     c_path = str(Path(c_path).resolve())
     if c_path == str_path: continue
     p1, p2 = min(str_path, c_path), max(str_path, c_path)
     c.execute("INSERT OR IGNORE INTO file_links(project, path1, path2) VALUES(?,?,?)", (self.project, p1, p2))
   self.log_activity('ربط ملفات', f'تم ربط {len(chosen)} ملف بـ {path.name}', path=path)
   refresh_links()
   self.populate()
   if getattr(self, 'preview_current_path', None) == str_path:
    self.preview_selected(self.file_tree)

  def remove_link():
   sel = tree.selection()
   if not sel: return messagebox.showinfo('تنبيه', 'حدد ملفاً لفك الربط.', parent=win)
   linked_name = tree.item(sel[0])['values'][0]
   linked_path = tree.item(sel[0])['tags'][0]
   p1, p2 = min(str_path, linked_path), max(str_path, linked_path)
   with connect() as c:
    c.execute("DELETE FROM file_links WHERE path1=? AND path2=?", (p1, p2))
   self.log_activity('فك ارتباط', f'تم فك ارتباط الملف مع {linked_name}', path=path)
   refresh_links()
   self.populate()
   if getattr(self, 'preview_current_path', None) == str_path:
    self.preview_selected(self.file_tree)

  ttk.Button(btn_frame, text='− فك الارتباط المحدد', command=remove_link).pack(side='right', padx=4)
  tk.Button(btn_frame, text='＋ ربط بملف جديد', command=add_link, bg='#087e8b', fg='white', relief='flat', font=('Segoe UI', 9, 'bold'), padx=10, cursor='hand2').pack(side='left', padx=4)
  
  win.geometry(f'+{self.winfo_rootx() + 50}+{self.winfo_rooty() + 50}')
  win.grab_set()

 def go_back(self):
  if getattr(self, 'view_mode', 'files') != 'files':
   self.show_files_collection()
   self.animate_window_in()
   return
  if self.backstack:
   self.save_view_state();self.forwardstack.append(self.current);self.current=self.backstack.pop();self.mode='folder';self.folder_group='الكل';self.refresh_directory();self.log_activity('رجوع في المجلدات',f'رجوع إلى «{self.current.name}»',path=self.current);self.animate_window_in()

 def go_forward(self):
  if self.forwardstack:
   self.save_view_state();self.backstack.append(self.current);self.current=self.forwardstack.pop();self.mode='folder';self.folder_group='الكل';self.refresh_directory();self.log_activity('تقدم في المجلدات',f'فتح «{self.current.name}»',path=self.current);self.animate_window_in()

 def go_up(self):
  # سلوك ذكي وسياقي لزر السهم لأعلى (↑) حسب المكان الحالي في البرنامج
  if getattr(self, 'view_mode', 'files') != 'files':
   self.show_folder_mode()
   self.animate_window_in()
   return
  if getattr(self, 'mode', 'folder') == 'project':
   self.show_folder_mode()
   self.animate_window_in()
   return
  if getattr(self, 'folder_group', 'الكل') != 'الكل':
   self.folder_group = 'الكل'
   self.refresh_directory()
   self.animate_window_in()
   return
  if self.current and self.root and self.current.resolve() != self.root.resolve():
   self.save_view_state();self.backstack.append(self.current);self.forwardstack.clear();self.current=self.current.parent;self.mode='folder';self.folder_group='الكل';self.refresh_directory();self.log_activity('الانتقال للمجلد الأعلى',f'فتح «{self.current.name}»',path=self.current);self.animate_window_in()
  else:
   # إذا كنا بالفعل في الجذر الرئيسي للمشروع، يعيدنا السهم لأعلى إلى شاشة المشاريع الرئيسية
   self.show_home()

 def rescan(self):
  self.scan_summary.set('جارٍ تحديث فهرس المشروع...');self.start_scan_progress();threading.Thread(target=self.scan_worker,args=(self.root,),daemon=True).start()