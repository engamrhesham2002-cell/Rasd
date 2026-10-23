class App(tk.Tk):
 def scan_worker(self,root):
  with self.scan_lock:
   project=root.name;seen=set();now=stamp(datetime.now().timestamp());rows=[];errors=0;old_by_path={};changes=[]
   def scan_error(exc):
    nonlocal errors
    errors+=1
   with connect() as c:
    old_by_path={r['path']:(r['size'],r['mtime']) for r in c.execute('select path,size,mtime from files where project=?',(project,))}
    scan_state=c.execute('select initial_scan_done from project_scan_state where project=?',(project,)).fetchone()
   first_scan=(scan_state is None and not old_by_path) or (scan_state is not None and not scan_state['initial_scan_done'])
   for d,dirs,files in os.walk(root,onerror=scan_error):
    dirs[:]=[x for x in dirs if not x.startswith('.')]
    for n in files:
     p=Path(d)/n
     try:
      st=p.stat();path=str(p.resolve());r=(path,project,p.relative_to(root).as_posix(),n,p.suffix.lower(),st.st_size,st.st_mtime,None,now);rows.append(r);seen.add(path)
      if path not in old_by_path:
       if not first_scan:changes.append((project,path,'added',now))
      elif old_by_path[path]!=(st.st_size,st.st_mtime):changes.append((project,path,'modified',now))
      if len(rows)%250==0:self.scanq.put(('progress',str(root.resolve()),len(rows),None))
     except OSError:errors+=1
   with connect() as c:
    c.executemany('insert into files values(?,?,?,?,?,?,?,?,?) on conflict(path) do update set project=excluded.project,rel=excluded.rel,name=excluded.name,ext=excluded.ext,size=excluded.size,mtime=excluded.mtime,indexed=excluded.indexed',rows)
    missing=[r['path'] for r in c.execute('select path from files where project=?',(project,)) if r['path'] not in seen]
    # Do not retire indexed files when any part of the tree could not be read.
    old=missing if errors==0 else []
    c.executemany('insert into file_changes(project,path,kind,changed_at) values(?,?,?,?)',changes)
    c.executemany('insert into file_changes(project,path,kind,changed_at) values(?,?,?,?)',[(project,p,'removed',now) for p in old])
    activity_rows=[]
    action_labels={'added':'إضافة ملف','modified':'تعديل ملف','removed':'إزالة ملف من مجلد المشروع'}
    for _,path,kind,changed_at in changes:
     action=action_labels[kind];activity_rows.append((project,action,f'{action}: {Path(path).name}',path,changed_at))
    if errors==0:
     for path in old:activity_rows.append((project,action_labels['removed'],f"{action_labels['removed']}: {Path(path).name}",path,now))
    if activity_rows:c.executemany('insert into activity_log(project,action,details,path,occurred_at) values(?,?,?,?,?)',activity_rows)
    c.execute('insert into project_scan_state(project,initial_scan_done) values(?,1) on conflict(project) do update set initial_scan_done=1',(project,))
    c.executemany('delete from tags where path=?',[(p,) for p in old]);c.executemany('delete from files where path=?',[(p,) for p in old])
   self.scanq.put(('done',str(root.resolve()),len(rows),errors))

 def populate(self):
  if not hasattr(self,'file_tree') or not self.current:return
  self.refresh_tag_filters()
  tree=self.file_tree;tree.delete(*tree.get_children());self.view_mode=getattr(self,'view_mode','files');directory_sizes={}
  if self.view_mode!='files':
   rows=self._collection_rows();data=[];self.activity_rows={}
   for r in rows:
    if self.view_mode=='changes':
     iid=f"activity:{r['id']}";target=r['path']
     if target:
      try:location=Path(target).resolve().relative_to(self.root.resolve()).as_posix()
      except (OSError,ValueError):location=target
     else:location='داخل البرنامج'
     event={'action':r['action'],'details':r['details'],'path':target,'occurred_at':r['occurred_at']};self.activity_rows[iid]=event
     data.append((iid,(r['details'],r['action'],'—','—',r['occurred_at'],'','',location),False));continue
    if not r['path']:continue
    if self.view_mode=='changes' and not r['name']:
     old=Path(r['path']);name=f"[محذوف] {old.name}";data.append((r['path'],(name,old.suffix.lower() or 'ملف','—','—',r['changed_at'] or '—','',old.as_posix()),False));continue
    if not Path(r['path']).exists():continue
    if 'kind' in r.keys() and r['kind']=='folder' and Path(r['path']).is_dir():
     p=Path(r['path']);rel=p.relative_to(self.root).as_posix();data.append((str(p.resolve()),(p.name,'مجلد',sizefmt(self.indexed_folder_size(p,directory_sizes)),stamp(p.stat().st_mtime),'—','',' '+rel),True));continue
    tags=r['tags'] or ''
    if not self._discipline_match(tags):continue
    name=r['name'];opened=r['last_open'] or '—';modified=r['mtime'] or 0
    if self.view_mode=='changes':name=f"[{r['change_kind'] or 'changed'}] {name}";opened=r['changed_at'] or opened
    data.append((r['path'],(name,r['ext'] or 'ملف',sizefmt(r['size'] or 0),stamp(modified),opened,tags,r['rel'] or ''),False))
  else:
   with connect() as c:
    allrows=c.execute("select f.*,group_concat(t.tag, ' ') tags from files f left join tags t on t.path=f.path where f.project=? group by f.path",(self.project,)).fetchall()
    folderrows=c.execute("select path,group_concat(tag, ' ') tags from folder_tags where project=? group by path",(self.project,)).fetchall()
    rowmap={r['path']:r for r in allrows};foldermap={r['path']:r['tags'] or '' for r in folderrows}
   for file_row in allrows:
    parts=(file_row['rel'] or '').split('/')[:-1];prefix=''
    for part in parts:
     prefix=f'{prefix}/{part}' if prefix else part
     directory_sizes[prefix]=directory_sizes.get(prefix,0)+(file_row['size'] or 0)
   data=[]
   if self.mode=='folder':
    try:items=list(self.current.iterdir())
    except OSError:items=[]
    for p in items:
     try:st=p.stat();isdir=p.is_dir()
     except OSError:continue
     rel=p.relative_to(self.root).as_posix();r=rowmap.get(str(p.resolve()))
     tags=(foldermap.get(p.relative_to(self.root).as_posix(), '') if isdir else ((r['tags'] or '') if r else ''));opened=(r['last_open'] or '—') if r else '—'
     if not isdir and self.folder_group!='الكل' and classify(p.suffix.lower())!=self.folder_group:continue
     if not isdir and not self._discipline_match(tags):continue
     data.append((str(p.resolve()),(p.name,('مجلد' if isdir else p.suffix.lower() or 'ملف'),(sizefmt(directory_sizes.get(rel,0)) if isdir else sizefmt(st.st_size)),stamp(st.st_mtime),opened,tags,rel),isdir))
    if self.folder_group!='الكل':
     prefix='' if self.current.resolve()==self.root.resolve() else self.current.relative_to(self.root).as_posix().rstrip('/')+'/'
     data=[]
     for r in allrows:
      if r['rel'].startswith(prefix) and classify(r['ext'] or '')==self.folder_group and self._discipline_match(r['tags']):data.append((r['path'],(r['name'],r['ext'] or 'ملف',sizefmt(r['size']),stamp(r['mtime']),r['last_open'] or '—',r['tags'] or '',r['rel']),False))
   else:
    for r in allrows:
     if self.project_group!='الكل' and classify(r['ext'] or '')!=self.project_group:continue
     if not self._discipline_match(r['tags']):continue
     data.append((r['path'],(r['name'],r['ext'] or 'ملف',sizefmt(r['size']),stamp(r['mtime']),r['last_open'] or '—',r['tags'] or '',r['rel']),False))
  sort_col=self.opened_sort_col if self.view_mode=='opened' else self.sort_col
  sort_desc=self.opened_sort_desc if self.view_mode=='opened' else self.sort_desc
  if sort_col=='name':idx=0;key=lambda x:x[1][idx].casefold()
  elif sort_col=='type':idx=1;key=lambda x:x[1][idx].casefold()
  elif sort_col=='size':key=lambda x:Path(x[0]).stat().st_size if Path(x[0]).is_file() else self.indexed_folder_size(x[0],directory_sizes) if Path(x[0]).is_dir() else -1
  elif sort_col=='mtime':key=lambda x:Path(x[0]).stat().st_mtime if Path(x[0]).exists() else -1
  elif sort_col=='opened':idx=4;key=lambda x:x[1][idx]
  elif sort_col=='tags':idx=5;key=lambda x:x[1][idx].casefold()
  else:idx=6;key=lambda x:x[1][idx].casefold()
  if self.view_mode!='changes':
   try:data.sort(key=lambda x:(not x[2],key(x)),reverse=sort_desc)
   except Exception:pass
  configured_tags={'folder':{'foreground':'#087e8b'},'file_folder':{'background':'#edf3f6','foreground':'#143e55'},'file_pdf':{'background':'#ffffff'},'file_excel':{'background':'#ffffff'},'file_word':{'background':'#ffffff'},'file_cad':{'background':'#ffffff'},'file_image':{'background':'#ffffff'},'file_other':{'background':'#ffffff'}}
  for name,options in configured_tags.items():tree.tag_configure(name,**options)
  configured_ext_tags=set()
  for path,values,isdir in data:
   try:
    display=list(values)
    if len(display)>5 and display[5]:display[5]=tag_badges(display[5])
    rowtag='file_other' if str(path).startswith('activity:') else self.file_row_tag(path,isdir)
    if rowtag.startswith('file_ext_') and rowtag not in configured_ext_tags:tree.tag_configure(rowtag,background='#ffffff');configured_ext_tags.add(rowtag)
    tree.insert('','end',iid=path,values=(display[0],'☐',*display[1:]),image=self.file_icon_image(path,isdir),tags=(rowtag,))
   except tk.TclError:continue
  if hasattr(self,'status'):
   count=len(tree.get_children());self.status.set(f'●  {count:,} ملف  ·  {len(tree.selection()):,} محدد' if tree.selection() else f'●  {count:,} عنصر')

 def activate(self,tree):
  sel=tree.selection()
  if not sel:return
  event=getattr(self,'activity_rows',{}).get(str(sel[0]))
  if event:
   target=Path(event['path']) if event['path'] else None
   if target and target.exists():
    if target.is_dir():self.navigate_to(target)
    else:self.open_file(target)
   return
  p=Path(sel[0])
  if p.is_dir():
   self.navigate_to(p);return
  self.open_file(p)

 def navigate_to(self,p):
  if not p.is_dir():return
  self.save_view_state();self.backstack.append(self.current);self.forwardstack.clear();self.current=p;self.mode='folder';self.folder_group='الكل';self.refresh_directory();self.log_activity('تنقل إلى مجلد',f'فتح المجلد «{p.name}»',path=p);self.animate_window_in()

 def open_file(self,p):
  try:os.startfile(str(p))
  except Exception as e:messagebox.showerror('تعذر فتح الملف',str(e));return
  opened_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S');key=str(p.resolve())
  with connect() as c:
   c.execute('update files set last_open=? where path=?',(opened_at,key))
   c.execute('insert or ignore into file_open_history(project,path,opened_at) values(?,?,?)',(self.project,key,opened_at))
  self.log_activity('فتح ملف',f'تم فتح الملف «{p.name}»',path=p)
  self.populate()
  if hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped():
   with connect() as c:self.search_cache=c.execute("select f.*,group_concat(t.tag, ' ') tags from files f left join tags t on t.path=f.path where f.project=? group by f.path",(self.project,)).fetchall()
   self.render_search_results()

 def selected_path(self):
  tree=getattr(self,'file_tree',None)
  if hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped() and self.search_nb.tabs():tree=self.search_views.get(self.search_nb.tab(self.search_nb.select(),'text'),tree)
  sel=tree.selection() if tree else [];return Path(sel[0]) if sel else None

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

 def edit_folder_specialties(self):
  folder=self.current
  if not folder or not folder.is_dir():return
  path=folder.relative_to(self.root).as_posix()
  with connect() as c:
   known=[r[0] for r in c.execute('select distinct tag from folder_tags where project=? order by tag',(self.project,))]
   selected={r[0] for r in c.execute('select tag from folder_tags where project=? and path=?',(self.project,path))}
  win=tk.Toplevel(self);win.title('تخصيص المجلد');win.transient(self);win.resizable(False,False);win.configure(bg='#e8edf1')
  tk.Label(win,text='تخصيص المجلد',bg='#e8edf1',fg='#19394e',font=('Segoe UI',12,'bold')).pack(anchor='e',padx=16,pady=(14,4))
  tk.Label(win,text=f'{folder.name} · التخصصات تخص هذا المجلد فقط ولا تغيّر هاشتاجات ملفاته.',bg='#e8edf1',fg='#526b7c',justify='right',wraplength=430).pack(anchor='e',padx=16)
  lb=tk.Listbox(win,selectmode='multiple',height=8,width=50,exportselection=False);lb.pack(fill='both',padx=16,pady=8)
  for tag in known:lb.insert('end',tag)
  for i,tag in enumerate(known):
   if tag in selected:lb.selection_set(i)
  row=tk.Frame(win,bg='#e8edf1');row.pack(fill='x',padx=16);value=tk.StringVar();entry=ttk.Entry(row,textvariable=value);entry.pack(side='right',fill='x',expand=True)
  def add_specialty():
   for tag in ['#'+x.strip().lstrip('#') for x in value.get().replace(',',' ').replace('،',' ').split() if x.strip()]:
    options=[lb.get(i) for i in range(lb.size())]
    if tag not in options:lb.insert('end',tag);lb.selection_set('end')
    else:lb.selection_set(options.index(tag))
   value.set('')
  ttk.Button(row,text='＋ إضافة تخصص',command=add_specialty).pack(side='left',padx=(6,0))
  def delete_specialty():
   indices=list(lb.curselection())
   if not indices:return messagebox.showinfo('حذف تخصص','حدد تخصصًا واحدًا أو أكثر من القائمة.',parent=win)
   to_delete={lb.get(i) for i in indices};saved=to_delete.intersection(known)
   if saved and not messagebox.askyesno('حذف التخصص',f'سيتم حذف {len(saved):,} تخصص من كل المجلدات التي تستخدمه في هذا المشروع. متابعة؟',parent=win):return
   remaining={lb.get(i) for i in lb.curselection() if i not in indices}
   if saved:
    with connect() as c:c.executemany('delete from folder_tags where project=? and tag=?',[(self.project,tag) for tag in saved])
    for tag in sorted(saved):self.log_activity('حذف تخصص',f'حذف التخصص {tag} من المجلدات',path=folder)
    known[:]=[tag for tag in known if tag not in saved];selected.difference_update(saved)
   for i in reversed(indices):lb.delete(i)
   for i in range(lb.size()):
    if lb.get(i) in remaining:lb.selection_set(i)
   if saved:
    if self.view_mode=='specialty' and getattr(self,'specialty_filter','') in saved:self.show_files_collection()
    else:self.refresh_tag_filters();self.populate();self.update_rail_selection()
  ttk.Button(row,text='− حذف التخصص المحدد',command=delete_specialty).pack(side='left',padx=3)
  buttons=tk.Frame(win,bg='#e8edf1');buttons.pack(fill='x',padx=16,pady=(8,14))
  def save():
   chosen={lb.get(i) for i in lb.curselection()}
   added=chosen-selected;removed=selected-chosen
   with connect() as c:
    c.execute('delete from folder_tags where project=? and path=?',(self.project,path))
    c.executemany('insert into folder_tags(project,path,tag,created) values(?,?,?,?)',[(self.project,path,tag,stamp(time.time())) for tag in chosen])
   if added:self.log_activity('تخصيص المجلد',f'إضافة تخصصات للمجلد «{folder.name}»: '+', '.join(sorted(added)),path=folder)
   if removed:self.log_activity('تخصيص المجلد',f'إزالة تخصصات من المجلد «{folder.name}»: '+', '.join(sorted(removed)),path=folder)
   self.refresh_tag_filters();self.populate();self.update_rail_selection();win.destroy()
  ttk.Button(buttons,text='حفظ التخصصات',command=save).pack(side='right');ttk.Button(buttons,text='إلغاء',command=win.destroy).pack(side='left');win.grab_set();entry.focus_set()

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

 def delete_selected_paths(self,tree=None):
  paths=[p.resolve() for p in self.selected_paths(tree) if p.exists()]
  if not paths:return
  root=self.root.resolve();safe=[]
  for path in paths:
   try:path.relative_to(root)
   except ValueError:continue
   if path!=root and path not in safe:safe.append(path)
  if not safe:return messagebox.showwarning('الحذف غير متاح','لا يمكن حذف ملفات خارج مجلد المشروع أو حذف مجلد المشروع نفسه.',parent=self)
  if os.name!='nt':return messagebox.showerror('الحذف غير متاح','إرسال العناصر إلى سلة المحذوفات متاح على Windows فقط.',parent=self)
  labels='، '.join(p.name for p in safe[:4]);extra=f' و{len(safe)-4} عناصر أخرى' if len(safe)>4 else ''
  if not messagebox.askyesno('إرسال إلى سلة المحذوفات',f'نقل {len(safe):,} عنصر إلى سلة المحذوفات؟\n{labels}{extra}',icon='warning',parent=self):return
  project=self.project;root=self.root.resolve()
  with connect() as c:rows=c.execute('select path,rel from files where project=?',(project,)).fetchall()
  tracked=set();folders=[p for p in safe if p.is_dir()]
  for item in safe:
   if item.is_dir():
    rel=item.relative_to(root).as_posix().rstrip('/');prefix=rel+'/'
    tracked.update(row['path'] for row in rows if row['rel']==rel or row['rel'].startswith(prefix))
   else:tracked.add(str(item))
  tracked.update(str(p) for p in safe if p.is_file())
  stamp_now=stamp(time.time());parent_hwnd=self.winfo_id()
  self.status.set('جارٍ نقل العناصر إلى سلة المحذوفات…')
  def worker():
   result=-1;aborted=False;error=None
   try:
    class SHFILEOPSTRUCTW(ctypes.Structure):
     _fields_=[('hwnd',ctypes.c_void_p),('wFunc',ctypes.c_uint),('pFrom',ctypes.c_wchar_p),('pTo',ctypes.c_wchar_p),('fFlags',ctypes.c_ushort),('fAnyOperationsAborted',ctypes.c_int),('hNameMappings',ctypes.c_void_p),('lpszProgressTitle',ctypes.c_wchar_p)]
    source='\0'.join(str(p) for p in safe)+'\0\0';operation=SHFILEOPSTRUCTW(parent_hwnd,3,source,None,0x0040|0x0010|0x0004|0x0400,False,None,None)
    shell=ctypes.windll.shell32;fn=shell.SHFileOperationW;fn.argtypes=[ctypes.POINTER(SHFILEOPSTRUCTW)];fn.restype=ctypes.c_int
    result=fn(ctypes.byref(operation));aborted=bool(operation.fAnyOperationsAborted)
    if result==0 and not aborted:
     try:
      with connect() as c:
       for key in tracked:
        c.execute('delete from tags where path=?',(key,));c.execute('delete from files where path=?',(key,))
        c.execute('insert into file_changes(project,path,kind,changed_at) values(?,?,?,?)',(project,key,'removed',stamp_now))
        c.execute('insert into activity_log(project,action,details,path,occurred_at) values(?,?,?,?,?)',(project,'حذف إلى سلة المحذوفات',f'تم نقل «{Path(key).name}» إلى سلة المحذوفات',key,stamp_now))
       favorites=c.execute('select path from favorites where project=?',(project,)).fetchall()
       for favorite in favorites:
        value=Path(favorite['path'])
        if any(value==item or (item.is_dir() and str(value).startswith(str(item).rstrip('\\/')+os.sep)) for item in safe):c.execute('delete from favorites where project=? and path=?',(project,favorite['path']))
       for folder in folders:c.execute('insert into activity_log(project,action,details,path,occurred_at) values(?,?,?,?,?)',(project,'حذف مجلد إلى سلة المحذوفات',f'تم نقل المجلد «{folder.name}» إلى سلة المحذوفات',str(folder),stamp_now))
     except Exception as exc:error=str(exc)
   except Exception as exc:error=str(exc)
   try:self.after(0,lambda:self._finish_delete(result,aborted,error,len(safe),project))
   except tk.TclError:pass
  threading.Thread(target=worker,daemon=True).start()

 def _finish_delete(self,result,aborted,error,count,project):
  if result==0 and not aborted:
   if self.project==project:
    self.status.set(f'تم نقل {count:,} عنصر إلى سلة المحذوفات');self._folder_size_cache=None;self.rebuild_project_tabs();self.rebuild_folder_tabs();self.populate()
    if hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped():self.refresh_search_cache();self.render_search_results()
   if error:messagebox.showwarning('تم الحذف مع تنبيه','نُقلت العناصر، لكن تعذر تحديث بعض بيانات السجل. سيحاول التحديث التالي مزامنتها.',parent=self)
  elif self.project==project:
   messagebox.showerror('تعذر الحذف',error or 'لم يكتمل النقل إلى سلة المحذوفات.',parent=self)
   self.status.set('لم يتم حذف العناصر')
   if aborted or result==0:self.rescan()

 def context_menu(self,e,tree):
  row=tree.identify_row(e.y)
  if not row:return
  if row not in tree.selection():tree.selection_set(row)
  event=getattr(self,'activity_rows',{}).get(str(row))
  if event:
   menu=tk.Menu(self,tearoff=0);target=Path(event['path']) if event['path'] else None
   if target and target.exists():menu.add_command(label='فتح الملف أو المجلد المرتبط',command=lambda p=target:self.navigate_to(p) if p.is_dir() else self.open_file(p))
   menu.add_command(label='نسخ تفاصيل الحدث',command=lambda d=event['details']:(self.clipboard_clear(),self.clipboard_append(d)))
   menu.tk_popup(e.x_root,e.y_root);return
  selected=self.selected_paths(tree);p=Path(row);files=[x for x in selected if x.is_file()];menu=tk.Menu(self,tearoff=0)
  fav_label='إزالة من المفضلة' if selected and all(self.is_favorite(x) for x in selected) else 'إضافة إلى المفضلة'
  menu.add_command(label=(fav_label+f' ({len(selected)} عناصر)' if len(selected)>1 else fav_label),command=lambda:self.toggle_favorite(selected))
  if p.is_dir():menu.add_command(label='فتح المجلد',command=lambda:self.navigate_to(p))
  else:
   menu.add_command(label='فتح الملف',command=lambda:self.open_file(p));menu.add_command(label='عرض ملفات اللوحة المرتبطة (DWG / PDF)',command=lambda:self.show_related_files(p));menu.add_command(label=f'هاشتج الملف ({len(files)} ملف)' if len(files)>1 else 'هاشتج الملف',command=self.edit_tags);menu.add_command(label=f'مسح كل الهاشتاجات ({len(files)} ملف)' if len(files)>1 else 'مسح كل الهاشتاجات',command=lambda:self.clear_selected_tags(tree));menu.add_command(label='إظهار مكان الملف في Explorer',command=lambda:subprocess.Popen(['explorer','/select,',str(p)]));menu.add_command(label='نسخ المسار',command=lambda:self.copy_selected_paths(tree))
  if selected and all(path.exists() for path in selected):
   menu.add_separator();menu.add_command(label=f'إرسال إلى سلة المحذوفات ({len(selected)} عنصر)' if len(selected)>1 else 'إرسال إلى سلة المحذوفات',command=lambda:self.delete_selected_paths(tree))
  menu.tk_popup(e.x_root,e.y_root)

 def go_back(self):
  if self.backstack:
   self.save_view_state();self.forwardstack.append(self.current);self.current=self.backstack.pop();self.mode='folder';self.folder_group='الكل';self.refresh_directory();self.log_activity('رجوع في المجلدات',f'رجوع إلى «{self.current.name}»',path=self.current);self.animate_window_in()

 def go_forward(self):
  if self.forwardstack:
   self.save_view_state();self.backstack.append(self.current);self.current=self.forwardstack.pop();self.mode='folder';self.folder_group='الكل';self.refresh_directory();self.log_activity('تقدم في المجلدات',f'فتح «{self.current.name}»',path=self.current);self.animate_window_in()

 def go_up(self):
  if self.current and self.current!=self.root:
   self.save_view_state();self.backstack.append(self.current);self.forwardstack.clear();self.current=self.current.parent;self.mode='folder';self.folder_group='الكل';self.refresh_directory();self.log_activity('الانتقال للمجلد الأعلى',f'فتح «{self.current.name}»',path=self.current);self.animate_window_in()

 def rescan(self):
  self.scan_summary.set('جارٍ تحديث فهرس المشروع...');self.start_scan_progress();threading.Thread(target=self.scan_worker,args=(self.root,),daemon=True).start()

