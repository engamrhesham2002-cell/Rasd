# Rasd - إغلاق البرنامج بالكامل، فحص المجلدات، عرض الملفات بستايل التيرمينال، وتسريع التصفح
from common import *
from update_utils import *
from storage import *
from perf import timed_method

class ScanningMixin:
 def _get_active_background_task_name(self):
  active = getattr(self, '_active_bg_task', None)
  if active:
   return str(active)
  if getattr(self, '_update_download_dialog', None):
   try:
    if self._update_download_dialog.winfo_exists():
     return 'تنزيل تحديث البرنامج'
   except Exception:
    pass
  if getattr(self, '_scan_progress_running', False):
   return 'فهرسة ملفات المشروع'
  return None

 def close_app(self, force=False):
  if not force and not getattr(self, '_update_install_on_close', False):
   task_name = self._get_active_background_task_name()
   if task_name:
    if not messagebox.askyesno(
     'تنبيه عملية جارية',
     f'هل أنت متأكد أنك تريد غلق البرنامج الآن؟\n\nيتم حالياً عمل: ({task_name})\nوقد يؤدي الإغلاق إلى عدم اكتمال العملية.',
     icon='warning',
     parent=self
    ):
     return

  try:
   for job in self.tk.call('after','info'):
    try: self.after_cancel(job)
    except Exception: pass
  except Exception: pass
  self._poll_after_id=None
  
  try:
   if hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped():
    if getattr(self,'search_history_job',None):
     try:self.after_cancel(self.search_history_job)
     except Exception:pass
    self.record_search_history();self.save_search_state()
  except Exception: pass

  try: self.save_view_state()
  except Exception: pass

  try: self.watch_stop.set()
  except Exception: pass

  try:
   for hwnd in list(getattr(self, 'everything_windows', {}).values()):
    ctypes.windll.user32.PostMessageW(hwnd,0x0010,0,0)
  except Exception: pass

  self.search_serial = getattr(self, 'search_serial', 0) + 1
  try: self.stop_everything_instance()
  except Exception: pass

  for attr in ('preview_executor', 'cad_preview_executor', 'search_executor', 'update_executor'):
   ex = getattr(self, attr, None)
   if ex:
    try: ex.shutdown(wait=False, cancel_futures=True)
    except Exception: pass

  for proc_attr in ('cad_preview_process', 'everything_proc', 'everything_exit_proc'):
   proc = getattr(self, proc_attr, None)
   if proc:
    try:
     if proc.poll() is None:
      proc.kill()
    except Exception: pass

  try:
   self.quit()
   self.destroy()
  except Exception:
   pass
  
  os._exit(0)

 def stop_everything_instance(self):
  exe=getattr(self,'everything_exe',None);instance=getattr(self,'everything_instance',None);data=getattr(self,'everything_data',None)
  if exe and instance and data and Path(exe).exists():
   try:subprocess.Popen([str(exe),'-instance',instance,'-exit'],cwd=str(data),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
   except OSError:pass
  proc = getattr(self, 'everything_proc', None)
  if proc:
   try:
    if proc.poll() is None: proc.kill()
   except Exception: pass
  self.everything_proc=None;self.everything_key=None;self.everything_instance=None;self.everything_data=None;self.everything_exe=None;self.everything_cli=None;self.everything_root=None

 def hide_search_page(self):
  self.preview_token+=1;self.search_serial+=1
  try: self.save_search_state()
  except Exception: pass
  self.stop_everything_instance()
  if hasattr(self,'search_page') and self.search_page.winfo_exists():
   self.search_page.destroy()
  if hasattr(self, 'active_preview') and self.active_preview:
   self.preview_image,self.preview_meta,self.preview_related_strip=self.active_preview
  if hasattr(self, 'explorer_page') and self.explorer_page.winfo_exists():
   self.explorer_page.pack(fill='both',expand=True,padx=8,pady=8)
  self.title('Rasd // ' + str(self.project))
  self.populate()
  self.animate_window_in()

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
       self.scan_summary.set(RLM+f'جارٍ الفحص... تمت قراءة {n:,} ملف');continue
      self.stop_scan_progress()
      self.index_total=n;self.index_errors=extra or 0;self._folder_size_cache=None;self._project_files_mem_cache=None
      self.rebuild_project_tabs();self.rebuild_folder_tabs();self.populate()
      with connect() as c:counts=c.execute("select sum(kind='added') added,sum(kind='modified') modified from file_changes where project=? and changed_at>=?",(self.project,getattr(self,'visit_since','0000'))).fetchone()
      added=counts['added'] or 0;modified=counts['modified'] or 0
      self.scan_summary.set(RLM+f'الفهرس محدّث: {n:,} ملف  ·  جديد: {added:,}  ·  معدل: {modified:,}  ·  أخطاء: {self.index_errors:,}')
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
        while len(self.preview_cache)>16:self.preview_cache.popitem(last=False)
       self.render_preview(image,meta)
     except Exception as exc:
      try:self.preview_meta.configure(text=RLM+f'تعذر عرض المعاينة: {str(exc)[:120]}')
      except (tk.TclError,AttributeError):pass
   except queue.Empty:pass
   self._poll_update_queue()
  finally:
   try:
    if self.winfo_exists():self._poll_after_id=self.after(120,self.poll_queue)
   except tk.TclError:pass

 @timed_method('scan.scan_worker')
 def scan_worker(self,root):
  with self.scan_lock:
   project=root.name;seen=set();now=stamp(datetime.now().timestamp());write_rows=[];scanned=0;errors=0;old_by_path={};changes=[]
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
     if is_task_internal_artifact(p):continue
     try:
      st=p.stat();path=str(p.resolve());scanned+=1;seen.add(path)
      old=old_by_path.get(path)
      if old is None:
       # ملف جديد: نكتبه فقط دون المساس بصفوف الملفات غير المتغيرة
       write_rows.append((path,project,p.relative_to(root).as_posix(),n,p.suffix.lower(),st.st_size,st.st_mtime,None,now))
       if not first_scan:changes.append((project,path,'added',now))
      elif old!=(st.st_size,st.st_mtime):
       # ملف تغيّر حجمه أو تاريخه فقط
       write_rows.append((path,project,p.relative_to(root).as_posix(),n,p.suffix.lower(),st.st_size,st.st_mtime,None,now))
       changes.append((project,path,'modified',now))
      if scanned%250==0:self.scanq.put(('progress',str(root.resolve()),scanned,None))
     except OSError:errors+=1
   with connect() as c:
    if write_rows:
     c.executemany('insert into files values(?,?,?,?,?,?,?,?,?) on conflict(path) do update set project=excluded.project,rel=excluded.rel,name=excluded.name,ext=excluded.ext,size=excluded.size,mtime=excluded.mtime,indexed=excluded.indexed',write_rows)
    indexed_paths=list(old_by_path)
    internal=[path for path in indexed_paths if is_task_internal_artifact(path)]
    missing=[path for path in indexed_paths if path not in seen and path not in internal]
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
    cleanup=old+internal;c.executemany('delete from tags where path=?',[(p,) for p in cleanup]);c.executemany('delete from files where path=?',[(p,) for p in cleanup])
   self.scanq.put(('done',str(root.resolve()),scanned,errors))

 def run_when_populate_rendered(self,callback):
  """ينفذ callback بعد اكتمال الرسم التدريجي للشجرة، أو فورًا إن كان الرسم منتهيًا."""
  if getattr(self,'_populate_render_job',None):
   self._populate_render_callbacks=getattr(self,'_populate_render_callbacks',[])+[callback]
  else:
   try:callback()
   except Exception:pass

 @timed_method('explorer.populate')
 def populate(self):
  if not hasattr(self,'file_tree') or not self.current:return
  self.refresh_tag_filters()
  if hasattr(self, '_update_top_action_bars'): self._update_top_action_bars()
  tree=self.file_tree;tree.delete(*tree.get_children());tree._prev_selected_set=set()
  self.view_mode=getattr(self,'view_mode','files');directory_sizes={}
  
  try:
   with connect() as c:
    linked_rows = c.execute("SELECT path1 FROM file_links UNION SELECT path2 FROM file_links").fetchall()
    linked_paths_set = {os.path.normcase(str(Path(r[0]).resolve())) for r in linked_rows if r[0]}
    fav_rows = c.execute("SELECT path FROM favorites WHERE project=?", (self.project,)).fetchall()
    favorite_paths_set = {os.path.normcase(str(Path(r[0]).resolve())) for r in fav_rows if r[0]}
  except Exception:
   linked_paths_set = set()
   favorite_paths_set = set()

  data=[];sort_meta={}
  def add(item_id,values,is_folder,size=0,mtime=0):
   data.append((item_id,values,is_folder));sort_meta[item_id]=(size or 0,mtime or 0)

  if self.view_mode!='files':
   rows=self._collection_rows();data=[];self.activity_rows={}
   for row_item in rows:
    try: r = dict(row_item)
    except Exception: r = row_item
    
    if r.get('path') and is_task_internal_artifact(r.get('path')):continue
    if self.view_mode=='changes':
     iid=f"activity:{r.get('id')}";target=r.get('path')
     if target:
      try:location=Path(target).resolve().relative_to(self.root.resolve()).as_posix()
      except (OSError,ValueError):location=target
     else:location='داخل البرنامج'
     occ_raw = str(r.get('occurred_at') or '')
     occ_fmt = occ_raw[:16] if occ_raw else '—'
     event={'id':r.get('id'),'action':r.get('action'),'details':r.get('details'),'path':target,'occurred_at':occ_raw,'icon':self.activity_row_icon(r) if hasattr(self,'activity_row_icon') else None};self.activity_rows[iid]=event
     add(iid,(RLM+str(r.get('details') or ''),RLM+str(r.get('action') or ''),'—','—',' '+occ_fmt+' ','',' '+location),False);continue
    if not r.get('path'):continue
    if self.view_mode=='changes' and not r.get('name'):
     old=Path(r.get('path'));name=f"[محذوف] {old.name}";add(r.get('path'),(name,old.suffix.lower() or 'ملف','—','—',r.get('changed_at') or '—','',old.as_posix()),False);continue
    if not Path(r.get('path')).exists() and self.view_mode != 'recycle_bin':continue
    if r.get('kind')=='folder' and Path(r.get('path')).is_dir():
     p=Path(r.get('path'));rel=p.relative_to(self.root).as_posix();st=p.stat();folder_size=self.indexed_folder_size(p,directory_sizes);add(str(p.resolve()),(p.name,RLM+'مجلد',sizefmt(folder_size),' '+stamp(st.st_mtime)+' ','—',r.get('tags') or '',' '+rel),True,folder_size,st.st_mtime);continue
    tags=r.get('tags') or ''
    if not self._discipline_match(tags):continue
    name=r.get('name');opened_raw=r.get('last_open');opened=(' '+opened_raw[:16]+' ' if opened_raw else '—');modified=r.get('mtime') or 0
    if self.view_mode=='changes':name=f"[{r.get('change_kind') or 'changed'}] {name}";opened=r.get('changed_at') or opened
    add(r.get('path'),(name,r.get('ext') or (RLM+'ملف'),sizefmt(r.get('size') or 0),' '+stamp(modified)+' ',opened,tags,r.get('rel') or ''),False,r.get('size') or 0,modified)
  else:
   with connect() as c:
    allrows=c.execute(FILE_ROWS_SQL,(self.project,)).fetchall()
    folderrows=c.execute("select path,group_concat(tag, ' ') tags from folder_tags where project=? group by path",(self.project,)).fetchall()
    rowmap={r['path']:r for r in allrows};foldermap={r['path']:r['tags'] or '' for r in folderrows}
   self._project_files_mem_cache = (self.project, [(r['path'], r['name']) for r in allrows if r['path'] and r['name']])
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
     try:
      if is_task_internal_artifact(p) or p.name.startswith('.'):continue
      st=p.stat();isdir=p.is_dir()
     except OSError:continue
     rel=p.relative_to(self.root).as_posix();r=rowmap.get(str(p.resolve()))
     tags=(foldermap.get(rel, '') if isdir else ((r['tags'] or '') if r else ''));opened=((' '+r['last_open'][:16]+' ') if r and r['last_open'] else '—')
     if not isdir and self.folder_group!='الكل' and classify(p.suffix.lower())!=self.folder_group:continue
     if not isdir and not self._discipline_match(tags):continue
     add(str(p.resolve()),(p.name,(RLM+'مجلد' if isdir else p.suffix.lower() or (RLM+'ملف')),(sizefmt(directory_sizes.get(rel,0)) if isdir else sizefmt(st.st_size)),' '+stamp(st.st_mtime)+' ',opened,tags,rel),isdir,(directory_sizes.get(rel,0) if isdir else st.st_size),st.st_mtime)
    if self.folder_group!='الكل':
     prefix='' if self.current.resolve()==self.root.resolve() else self.current.relative_to(self.root).as_posix().rstrip('/')+'/'
     data=[]
     for r in allrows:
      if is_task_internal_artifact(r['path']):continue
      if r['rel'].startswith(prefix) and classify(r['ext'] or '')==self.folder_group and self._discipline_match(r['tags']):add(r['path'],(r['name'],r['ext'] or (RLM+'ملف'),sizefmt(r['size']),' '+stamp(r['mtime'])+' ',(' '+r['last_open'][:16]+' ') if r['last_open'] else '—',r['tags'] or '',r['rel']),False,r['size'] or 0,r['mtime'] or 0)
   else:
    for r in allrows:
     if is_task_internal_artifact(r['path']):continue
     if self.project_group!='الكل' and classify(r['ext'] or '')!=self.project_group:continue
     if not self._discipline_match(r['tags']):continue
     add(r['path'],(r['name'],r['ext'] or (RLM+'ملف'),sizefmt(r['size']),' '+stamp(r['mtime'])+' ',(' '+r['last_open'][:16]+' ') if r['last_open'] else '—',r['tags'] or '',r['rel']),False,r['size'] or 0,r['mtime'] or 0)
  sort_col=self.opened_sort_col if self.view_mode=='opened' else self.sort_col
  sort_desc=self.opened_sort_desc if self.view_mode=='opened' else self.sort_desc
  if sort_col=='name':key=lambda x:x[1][0].casefold()
  elif sort_col=='type':key=lambda x:x[1][1].casefold()
  elif sort_col=='size':key=lambda x:sort_meta.get(x[0],(0,0))[0]
  elif sort_col=='mtime':key=lambda x:sort_meta.get(x[0],(0,0))[1]
  elif sort_col=='opened':key=lambda x:x[1][4]
  elif sort_col=='tags':key=lambda x:x[1][5].casefold()
  else:key=lambda x:x[1][6].casefold()
  if self.view_mode!='changes':
   try:
    folders=[x for x in data if x[2]];files=[x for x in data if not x[2]]
    folders.sort(key=key,reverse=sort_desc);files.sort(key=key,reverse=sort_desc)
    data=folders+files
   except Exception:pass
   
  configured_tags={
   'folder':{'foreground':ACCENT_CYAN},
   'file_folder':{'background':'#111923','foreground':ACCENT_CYAN},
   'file_pdf':{'background':BG_PANEL,'foreground':FG_PRIMARY},
   'file_excel':{'background':BG_PANEL,'foreground':FG_PRIMARY},
   'file_word':{'background':BG_PANEL,'foreground':FG_PRIMARY},
   'file_cad':{'background':BG_PANEL,'foreground':FG_PRIMARY},
   'file_image':{'background':BG_PANEL,'foreground':FG_PRIMARY},
   'file_other':{'background':BG_PANEL,'foreground':FG_PRIMARY}
  }
  for name,options in configured_tags.items():tree.tag_configure(name,**options)
  configured_ext_tags=set()

  def render_slice(start,end):
   for path,values,isdir in data[start:end]:
    try:
     display=list(values)
     name_text = str(display[0])
     
     if not str(path).startswith('activity:'):
      norm_p = os.path.normcase(str(path))
      badges = []
      if norm_p in favorite_paths_set:
       badges.append('★')
      if norm_p in linked_paths_set:
       badges.append('<->')
      if badges:
       name_text = ' '.join(badges) + ' ' + name_text
       
     display[0] = '  ' + name_text
     
     if len(display)>5 and display[5]:display[5]=tag_badges(display[5])
     if str(path).startswith('activity:'):
      rowtag = 'file_other'
      ev = self.activity_rows.get(str(path), {})
      row_img = ev.get('icon') or self.blank_icon_image()
     else:
      rowtag = self.file_row_tag(path,isdir)
      if rowtag.startswith('file_ext_') and rowtag not in configured_ext_tags:
       tree.tag_configure(rowtag,background=BG_PANEL,foreground=FG_PRIMARY)
       configured_ext_tags.add(rowtag)
      row_img = self.file_icon_image(path,isdir)
     tree.insert('','end',iid=path,values=(display[0],'[ ]',*display[1:]),image=row_img,tags=(rowtag,))
    except tk.TclError:continue

  def finalize_render():
   self._populate_render_job=None
   if hasattr(self,'status'):
    count=len(tree.get_children())
    if self.view_mode == 'changes':
     self.status.set(RLM+f'عدد الأحداث في السجل: {count:,}')
    else:
     self.status.set(RLM+(f'الإجمالي: {count:,} عنصر  ·  المحدد: {len(tree.selection()):,}' if tree.selection() else f'الإجمالي: {count:,} عنصر'))
   self.update_selection_status(tree)
   self.schedule_preview_selected(tree)
   callbacks=getattr(self,'_populate_render_callbacks',[])
   self._populate_render_callbacks=[]
   for callback in callbacks:
    try:callback()
    except Exception:pass

  self._populate_render_token=getattr(self,'_populate_render_token',0)+1
  token=self._populate_render_token
  pending=getattr(self,'_populate_render_job',None)
  if pending:
   try:self.after_cancel(pending)
   except tk.TclError:pass
  self._populate_render_job=None

  chunk=800
  def render_chunk(start):
   if token!=getattr(self,'_populate_render_token',0):return
   try:
    if not tree.winfo_exists():return
   except tk.TclError:return
   end=min(start+chunk,len(data))
   render_slice(start,end)
   if end<len(data):
    if hasattr(self,'status'):self.status.set(RLM+f'جارٍ عرض {end:,} من {len(data):,} عنصر...')
    try:self._populate_render_job=self.after(1,lambda:render_chunk(end))
    except tk.TclError:return
   else:
    finalize_render()

  if len(data)<=chunk:
   render_slice(0,len(data));finalize_render()
  else:
   render_chunk(0)

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
  opened_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
  key=str(p.resolve())
  
  with connect() as c:
   exact_path_row = c.execute("SELECT path FROM files WHERE lower(path)=lower(?)", (key,)).fetchone()
   db_path = exact_path_row['path'] if exact_path_row else key
   
   c.execute('update files set last_open=? where path=?',(opened_at,db_path))
   c.execute('insert or ignore into file_open_history(project,path,opened_at) values(?,?,?)',(self.project,db_path,opened_at))
  
  self.log_activity('فتح ملف',f'تم فتح الملف «{p.name}»',path=p)
  tree=getattr(self,'file_tree',None)
  refresh_for_opened = getattr(self,'view_mode','')=='opened' or getattr(self,'sort_col','')=='opened'
  if refresh_for_opened and tree is not None and tree.winfo_exists():
   self.populate()
  elif tree is not None:
   def update_opened_row():
    try:
     if not tree.winfo_exists():return
     for iid in (db_path,key):
      if tree.exists(iid):
       tree.set(iid,'opened',' '+opened_at[:16]+' ');return
    except tk.TclError:pass
   update_opened_row()
   if getattr(self,'_populate_render_job',None):self.run_when_populate_rendered(update_opened_row)
  if hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped():
   with connect() as c:self.search_cache=c.execute(FILE_ROWS_SQL,(self.project,)).fetchall()
   self.render_search_results()

 def selected_path(self):
  tree=getattr(self,'file_tree',None)
  if hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped() and self.search_nb.tabs():tree=self.search_views.get(self.search_nb.tab(self.search_nb.select(),'text'),tree)
  sel=tree.selection() if tree else [];return Path(sel[0]) if sel else None