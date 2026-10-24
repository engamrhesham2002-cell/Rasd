# Rasd - أدوات ومراجع مساحة العمل (Workspace Tools)
from common import *
from storage import *
import ssl

class WorkspaceMixin:
 def get_workspace_icon(self, kind, path):
  if not hasattr(self, 'workspace_icons_cache'):
   self.workspace_icons_cache = {}
  
  key = f"{kind}:{path}"
  if key in self.workspace_icons_cache:
   return self.workspace_icons_cache[key]

  image = None
  if kind == 'link':
   try:
    parse_path = path if '://' in path else 'https://' + path
    domain = urllib.parse.urlparse(parse_path).netloc or urllib.parse.urlparse(parse_path).path.split('/')[0]
    domain = domain.replace('www.', '')
    if domain:
     ctx = ssl.create_default_context()
     ctx.check_hostname = False
     ctx.verify_mode = ssl.CERT_NONE
     
     url = f"https://icons.duckduckgo.com/ip3/{domain}.ico"
     req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
     with urllib.request.urlopen(req, timeout=3.0, context=ctx) as response:
      image = Image.open(io.BytesIO(response.read())).convert('RGBA').resize((16, 16), Image.Resampling.LANCZOS)
   except Exception:
    pass
  elif kind == 'app':
   try:
    if hasattr(self, 'shell_thumbnail'):
     img = self.shell_thumbnail(Path(path).resolve())
     if img:
      image = img.resize((16, 16), Image.Resampling.LANCZOS)
    
    if not image and os.name == 'nt':
     import ctypes
     from ctypes import wintypes
     shell32 = ctypes.windll.shell32
     user32 = ctypes.windll.user32
     gdi32 = ctypes.windll.gdi32
     
     class SHFILEINFOW(ctypes.Structure):
      _fields_ = [("hIcon", wintypes.HICON), ("iIcon", ctypes.c_int), ("dwAttributes", wintypes.DWORD), ("szDisplayName", wintypes.WCHAR * 260), ("szTypeName", wintypes.WCHAR * 80)]
     
     shinfo = SHFILEINFOW()
     if shell32.SHGetFileInfoW(str(path), 0, ctypes.byref(shinfo), ctypes.sizeof(shinfo), 0x101) and shinfo.hIcon:
      class BITMAPINFOHEADER(ctypes.Structure):
       _fields_ = [('biSize', wintypes.DWORD), ('biWidth', ctypes.c_long), ('biHeight', ctypes.c_long), ('biPlanes', wintypes.WORD), ('biBitCount', wintypes.WORD), ('biCompression', wintypes.DWORD), ('biSizeImage', wintypes.DWORD), ('biXPelsPerMeter', ctypes.c_long), ('biYPelsPerMeter', ctypes.c_long), ('biClrUsed', wintypes.DWORD), ('biClrImportant', wintypes.DWORD)]
      class BITMAPINFO(ctypes.Structure):
       _fields_ = [('bmiHeader', BITMAPINFOHEADER), ('bmiColors', wintypes.DWORD * 3)]
      
      bmi = BITMAPINFO()
      bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
      bmi.bmiHeader.biWidth = 16
      bmi.bmiHeader.biHeight = -16
      bmi.bmiHeader.biPlanes = 1
      bmi.bmiHeader.biBitCount = 32
      
      hdc = user32.GetDC(0)
      mem_dc = gdi32.CreateCompatibleDC(hdc)
      pBits = ctypes.c_void_p()
      hbmp = gdi32.CreateDIBSection(mem_dc, ctypes.byref(bmi), 0, ctypes.byref(pBits), None, 0)
      old_bmp = gdi32.SelectObject(mem_dc, hbmp)
      
      user32.DrawIconEx(mem_dc, 0, 0, shinfo.hIcon, 16, 16, 0, None, 3)
      buf = ctypes.string_at(pBits, 16 * 16 * 4)
      raw_img = Image.frombuffer('RGBA', (16, 16), buf, 'raw', 'BGRA', 0, 1).copy()
      
      gdi32.SelectObject(mem_dc, old_bmp)
      gdi32.DeleteObject(hbmp)
      gdi32.DeleteDC(mem_dc)
      user32.ReleaseDC(0, hdc)
      user32.DestroyIcon(shinfo.hIcon)
      
      if raw_img.getextrema()[3][1] == 0:
       data = raw_img.getdata()
       new_data = [(r,g,b, 255 if (r,g,b) != (0,0,0) else 0) for r,g,b,a in data]
       raw_img.putdata(new_data)
      image = raw_img
   except Exception:
    pass

  if not image:
   image = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
   d = ImageDraw.Draw(image)
   color = '#087e8b' if kind == 'link' else '#435b6d'
   d.rounded_rectangle((0, 0, 15, 15), radius=3, fill=color)
   if kind == 'app':
    d.polygon([(5,4), (11,8), (5,12)], fill='white')
   else:
    d.ellipse((3,3,12,12), outline='white', width=2)
  
  photo = ImageTk.PhotoImage(image)
  self.workspace_icons_cache[key] = photo
  return photo

 def show_workspace_menu(self, widget):
  menu = tk.Menu(self, tearoff=0, bg='white', fg='#19394e', activebackground='#dcebed', activeforeground='#19394e', font=('Segoe UI', 10), borderwidth=1, relief='solid')
  
  with connect() as c:
   tools = c.execute('SELECT * FROM workspace_tools WHERE project=? ORDER BY kind, title', (self.project,)).fetchall()
  
  apps = [t for t in tools if t['kind'] == 'app']
  links = [t for t in tools if t['kind'] == 'link']

  def launch(kind, path):
   try:
    if kind == 'link':
     if not path.startswith(('http://', 'https://')): path = 'https://' + path
     webbrowser.open(path)
    else:
     os.startfile(path)
    self.log_activity('مساحة العمل', f'فتح {"موقع" if kind=="link" else "برنامج"}: {path}')
   except Exception as e:
    messagebox.showerror('خطأ', f'تعذر الفتح:\n{str(e)[:100]}', parent=self)

  if apps:
   menu.add_command(label=' 💻 البرامج والتطبيقات:', state='disabled')
   for app in apps:
    img = self.get_workspace_icon('app', app['path'])
    menu.add_command(label='  ' + app['title'], image=img, compound='left', command=lambda p=app['path']: launch('app', p))
    
  if apps and links:
   menu.add_separator()
    
  if links:
   menu.add_command(label=' 🌐 المواقع المرجعية:', state='disabled')
   for link in links:
    img = self.get_workspace_icon('link', link['path'])
    menu.add_command(label='  ' + link['title'], image=img, compound='left', command=lambda p=link['path']: launch('link', p))
  
  if not apps and not links:
   menu.add_command(label=' القائمة فارغة', state='disabled')
    
  menu.add_separator()
  menu.add_command(label='⚙  إدارة الأدوات والمراجع...', command=self.manage_workspace_tools)
  
  x = widget.winfo_rootx()
  y = widget.winfo_rooty() + widget.winfo_height() + 4
  menu.tk_popup(x, y)

 def manage_workspace_tools(self):
  win = tk.Toplevel(self); win.title('إدارة الأدوات والمراجع'); win.transient(self); win.resizable(False, False); win.configure(bg='#e8edf1')
  
  tk.Label(win, text='أدوات ومراجع المشروع', bg='#e8edf1', fg='#19394e', font=('Segoe UI', 13, 'bold')).pack(anchor='e', padx=16, pady=(14, 4))
  tk.Label(win, text='أضف البرامج الهندسية وروابط الويب للوصول السريع من داخل المشروع.', bg='#e8edf1', fg='#526b7c', font=('Segoe UI', 9)).pack(anchor='e', padx=16, pady=(0,8))
  
  list_frame = tk.Frame(win, bg='white', highlightbackground='#d6e0e6', highlightthickness=1)
  list_frame.pack(fill='both', expand=True, padx=16, pady=4)
  
  tree = ttk.Treeview(list_frame, columns=('title', 'kind', 'path', 'id'), show='headings', height=7)
  tree.heading('title', text='الاسم'); tree.heading('kind', text='النوع'); tree.heading('path', text='المسار / الرابط')
  tree.column('title', width=120, anchor='e'); tree.column('kind', width=60, anchor='center'); tree.column('path', width=240, anchor='e'); tree.column('id', width=0, stretch=False)
  
  ybar = ttk.Scrollbar(list_frame, orient='vertical', command=tree.yview)
  tree.configure(yscrollcommand=ybar.set)
  tree.pack(side='right', fill='both', expand=True); ybar.pack(side='left', fill='y')
  
  def refresh_list():
   for iid in tree.get_children(): tree.delete(iid)
   with connect() as c:
    rows = c.execute('SELECT * FROM workspace_tools WHERE project=? ORDER BY kind, title', (self.project,)).fetchall()
   for r in rows:
    tree.insert('', 'end', values=(r['title'], 'موقع' if r['kind'] == 'link' else 'برنامج', r['path'], r['id']))
  refresh_list()
  
  add_frame = tk.Frame(win, bg='#e8edf1'); add_frame.pack(fill='x', padx=16, pady=8)
  
  tk.Label(add_frame, text='الاسم:', bg='#e8edf1', font=('Segoe UI', 9)).grid(row=0, column=4, sticky='e', padx=2)
  title_var = tk.StringVar()
  ttk.Entry(add_frame, textvariable=title_var, justify='right', width=18, font=('Segoe UI', 9)).grid(row=0, column=3, padx=2)
  
  kind_var_ar = tk.StringVar(value='برنامج')
  cb = ttk.Combobox(add_frame, textvariable=kind_var_ar, values=('برنامج', 'موقع'), state='readonly', width=8, justify='right', style='Office.TCombobox')
  cb.grid(row=0, column=2, padx=2)
  
  tk.Label(add_frame, text='المسار/الرابط:', bg='#e8edf1', font=('Segoe UI', 9)).grid(row=1, column=4, sticky='e', padx=2, pady=6)
  path_var = tk.StringVar()
  path_entry = ttk.Entry(add_frame, textvariable=path_var, justify='left', width=28, font=('Segoe UI', 9))
  path_entry.grid(row=1, column=2, columnspan=2, sticky='ew', padx=2, pady=6)
  
  def auto_extract_link_name(*_):
   if kind_var_ar.get() == 'موقع' and not title_var.get().strip():
    p = path_var.get().strip()
    if p and p != 'https://':
     try:
      domain = urllib.parse.urlparse(p if '://' in p else 'https://' + p).netloc
      name = domain.replace('www.', '').split('.')[0].capitalize()
      if name: title_var.set(name)
     except Exception: pass
     
  path_entry.bind('<FocusOut>', auto_extract_link_name)
  
  def browse_app():
   p = filedialog.askopenfilename(parent=win, title='اختر البرنامج', filetypes=[('Executable/Shortcut', '*.exe *.lnk'), ('All Files', '*.*')])
   if p: 
    path_var.set(p)
    if not title_var.get().strip():
     title_var.set(Path(p).stem.capitalize())
  
  browse_btn = ttk.Button(add_frame, text='استعراض...', command=browse_app, width=10)
  browse_btn.grid(row=1, column=1, padx=2, pady=6)
  
  def on_kind_change(*_):
   if kind_var_ar.get() == 'موقع':
    browse_btn.configure(state='disabled')
    if not path_var.get(): path_var.set('https://')
   else:
    browse_btn.configure(state='normal')
    if path_var.get() == 'https://': path_var.set('')
  kind_var_ar.trace_add('write', on_kind_change)
  
  def add_tool():
   t, p, k = title_var.get().strip(), path_var.get().strip(), 'link' if kind_var_ar.get() == 'موقع' else 'app'
   if not t or not p: return messagebox.showwarning('تنبيه', 'أدخل الاسم والمسار بشكل صحيح.', parent=win)
   with connect() as c: c.execute('INSERT INTO workspace_tools(project, title, kind, path) VALUES(?,?,?,?)', (self.project, t, k, p))
   title_var.set(''); path_var.set('https://' if k == 'link' else '')
   
   cache_key = f"{k}:{p}"
   if hasattr(self, 'workspace_icons_cache') and cache_key in self.workspace_icons_cache:
    del self.workspace_icons_cache[cache_key]
    
   refresh_list()
      
  tk.Button(add_frame, text='＋ إضافة', command=add_tool, bg='#087e8b', fg='white', activebackground='#066b76', relief='flat', font=('Segoe UI', 9, 'bold'), padx=10, cursor='hand2').grid(row=0, column=0, rowspan=2, padx=6)
  
  import_frame = tk.Frame(win, bg='#dfe7ec')
  import_frame.pack(fill='x', padx=16, pady=4, ipady=4)
  
  tk.Label(import_frame, text='استيراد أدوات من مشروع سابق:', bg='#dfe7ec', fg='#19394e', font=('Segoe UI', 9, 'bold')).pack(side='right', padx=8)
  with connect() as c:
   other_projects = [r[0] for r in c.execute('SELECT DISTINCT project FROM workspace_tools WHERE project != ?', (self.project,)).fetchall()]
  
  import_var = tk.StringVar()
  import_cb = ttk.Combobox(import_frame, textvariable=import_var, values=other_projects, state='readonly', width=16, justify='right', style='Office.TCombobox')
  import_cb.pack(side='right', padx=5)
  
  def import_tools():
   src = import_var.get()
   if not src: return
   with connect() as c:
    tools = c.execute('SELECT title, kind, path FROM workspace_tools WHERE project=?', (src,)).fetchall()
    for t in tools:
     if not c.execute('SELECT 1 FROM workspace_tools WHERE project=? AND path=?', (self.project, t['path'])).fetchone():
      c.execute('INSERT INTO workspace_tools(project, title, kind, path) VALUES(?,?,?,?)', (self.project, t['title'], t['kind'], t['path']))
   refresh_list()
   messagebox.showinfo('استيراد', f'تم استيراد الأدوات بنجاح من {src}.', parent=win)
      
  ttk.Button(import_frame, text='استيراد ↧', command=import_tools).pack(side='right', padx=2)
  if not other_projects:
   import_cb.configure(state='disabled'); import_cb.set('لا توجد مشاريع سابقة')
  
  actions = tk.Frame(win, bg='#e8edf1'); actions.pack(fill='x', padx=16, pady=(8, 14))
  
  def remove_tool():
   sel = tree.selection()
   if not sel: return
   item_id = tree.item(sel[0])['values'][3]
   with connect() as c: c.execute('DELETE FROM workspace_tools WHERE id=?', (item_id,))
   refresh_list()
      
  ttk.Button(actions, text='− حذف المحدد', command=remove_tool).pack(side='right')
  ttk.Button(actions, text='إغلاق', command=win.destroy).pack(side='left')
  
  win.geometry(f'+{self.winfo_rootx() + 50}+{self.winfo_rooty() + 50}')
  win.grab_set()