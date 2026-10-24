# Rasd - حذف/نسخ المسارات، القائمة اليمنى، التنقل (رجوع/أمام/أعلى)
from common import *
from update_utils import *
from storage import *

class FileOpsMixin:
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
