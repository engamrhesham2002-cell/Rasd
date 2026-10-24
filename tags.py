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
