# Rasd - شاشة الترحيب والهيدر العلوي (مع روابط GitHub و LinkedIn التفاعلية بستايل التيرمينال)
from common import *
from update_utils import *
from storage import *

class WelcomeMixin:
 def header(self, title, show_search=False):
  h = tk.Frame(self, bg=BG_VOID, height=62, highlightbackground=ACCENT_MATRIX, highlightthickness=1)
  h.pack(fill='x', padx=2, pady=(2, 0))
  h.pack_propagate(False)
  
  brand = tk.Frame(h, bg=BG_VOID, cursor='hand2')
  brand.pack(side='left', padx=18, pady=5)
  try:
   with Image.open(Path(getattr(sys,'_MEIPASS',BASE))/'Assets'/'rasd_logo.png') as source:
    self.header_icon = ImageTk.PhotoImage(source.convert('RGBA').resize((36,36),Image.Resampling.LANCZOS))
   logo_lbl = tk.Label(brand, image=self.header_icon, bg=BG_VOID, cursor='hand2')
   logo_lbl.pack(side='left', padx=(0,8))
  except Exception:
   logo_lbl = tk.Label(brand, text='[>_]', font=(MONO_FONT,14,'bold'), fg=ACCENT_MATRIX, bg=BG_VOID, cursor='hand2')
   logo_lbl.pack(side='left', padx=(0,8))
   
  brand_text = tk.Frame(brand, bg=BG_VOID, cursor='hand2')
  brand_text.pack(side='left')
  t1 = tk.Label(brand_text, text='[>_ RASD]', font=(MONO_FONT,13,'bold'), fg=ACCENT_MATRIX, bg=BG_VOID, cursor='hand2')
  t1.pack(anchor='w')
  t2 = tk.Label(brand_text, text='SYS // ENG. Amr Hesham', font=(MONO_FONT,8), fg=FG_MUTED, bg=BG_VOID, cursor='hand2')
  t2.pack(anchor='w')

  def _go_home_click(event=None):
   if hasattr(self, 'show_home'):
    self.show_home()

  for w in (brand, logo_lbl, brand_text, t1, t2):
   w.bind('<Button-1>', _go_home_click)

  tk.Label(h, text=RLM + str(title), font=(TERM_FONT,13,'bold'), fg=ACCENT_CYAN, bg=BG_VOID).pack(side='right', padx=18)

  if show_search:
   pill_w, pill_h = 370, 34
   search_cv = tk.Canvas(h, width=pill_w, height=pill_h, bg=BG_VOID, highlightthickness=0, cursor='hand2')
   search_cv.place(relx=0.5, rely=0.5, anchor='center')
   search_cv._no_global_scroll = True
   
   search_cv.create_rectangle(1, 1, pill_w-1, pill_h-1, fill=BG_PANEL, outline=ACCENT_MATRIX, width=1, tags=('pill_bg',))
   search_cv.create_text(pill_w-16, pill_h//2, text='⌕', font=(MONO_FONT, 13, 'bold'), fill=ACCENT_CYAN, tags=('pill_fg',))
   search_cv.create_text(12, pill_h//2, text='>_ grep --project', font=(MONO_FONT, 9, 'bold'), fill=ACCENT_MATRIX, anchor='w', tags=('pill_fg',))
   search_cv.create_text(pill_w-38, pill_h//2, text=RLM + 'ابحث في المشروع... (Ctrl+F)', font=(TERM_FONT, 9), fill=FG_MUTED, anchor='e', tags=('pill_fg',))
   
   def _on_enter(e):
    search_cv.itemconfigure('pill_bg', fill=BG_HEADER, outline=ACCENT_CYAN)
   def _on_leave(e):
    search_cv.itemconfigure('pill_bg', fill=BG_PANEL, outline=ACCENT_MATRIX)
   def _on_click(e):
    if hasattr(self, 'show_search_page'):
     self.show_search_page()
     
   search_cv.bind('<Enter>', _on_enter)
   search_cv.bind('<Leave>', _on_leave)
   search_cv.bind('<Button-1>', _on_click)

  return h

 def show_welcome(self):
  self.title('Rasd // Boot Screen')
  self.clear();self.project='';self.configure(bg=BG_VOID);self.geometry('720x600');self.minsize(600,520)
  
  bg=tk.Frame(self,bg=BG_VOID);bg.pack(fill='both',expand=True)
  
  card=tk.Frame(bg,bg=BG_PANEL,highlightbackground=ACCENT_MATRIX,highlightthickness=1)
  # بطاقة الويلكوم مبنية أصلًا بتخطيط LTR؛ نمنع عكسها في الإنجليزية
  # لتظهر بنفس الشكل النظيف الذي تظهر به في العربية.
  card._rasd_natural_layout = True
  card.place(relx=.5,rely=.5,anchor='center',relwidth=.84,relheight=.86)
  
  term_title=tk.Frame(card,bg=BG_HEADER,height=32);term_title.pack(fill='x');term_title.pack_propagate(False)
  tk.Label(term_title, text=' root@rasd:~# neofetch --system-boot', bg=BG_HEADER, fg=ACCENT_MATRIX, font=(MONO_FONT, 10, 'bold')).pack(side='left', padx=10)
  
  content=tk.Frame(card,bg=BG_PANEL);content.pack(fill='both',expand=True,padx=22,pady=(14, 10))
  
  ascii_art = """
 ██████╗  █████╗ ███████╗██████╗ 
 ██╔══██╗██╔══██╗██╔════╝██╔══██╗
 ██████╔╝███████║███████╗██║  ██║
 ██╔══██╗██╔══██║╚════██║██║  ██║
 ██║  ██║██║  ██║███████║██████╔╝
 ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═════╝ """
  tk.Label(content, text=ascii_art, bg=BG_PANEL, fg=ACCENT_MATRIX, font=(MONO_FONT, 10, 'bold'), justify='left').pack(anchor='nw', pady=(0, 8))
  
  sys_info = (
   "OS: Rasd Engineering Core v0.44.4 [Linux/Win32 Hybrid]\n"
   "KERNEL: Python 3.x Tkinter Tiling Engine\n"
   "UPTIME: Ready for Operation\n"
   "DEVELOPER: ENG. Amr Hesham [Alexandria, Egypt]\n"
   "DATABASE: SQLite WAL Mode [Secure]"
  )
  tk.Label(content, text=sys_info, bg=BG_PANEL, fg=FG_PRIMARY, font=(MONO_FONT, 9), justify='left', anchor='w').pack(anchor='nw', fill='x', pady=(0, 12))

  # === روابط التيرمينال التفاعلية (GitHub & LinkedIn) ===
  links_frame = tk.Frame(content, bg=BG_PANEL)
  links_frame.pack(anchor='nw', fill='x', pady=(2, 6))

  def make_terminal_link(parent, key_label, display_url, target_url, accent_col):
   row = tk.Frame(parent, bg=BG_VOID, highlightbackground=BORDER_DIM, highlightthickness=1, cursor='hand2')
   row.pack(fill='x', pady=3)

   lbl_key = tk.Label(row, text=f' {key_label:<10}', bg=BG_HEADER, fg=accent_col, font=(MONO_FONT, 9, 'bold'), anchor='w', padx=6, pady=5, cursor='hand2')
   lbl_key.pack(side='left')

   lbl_url = tk.Label(row, text=display_url, bg=BG_VOID, fg=FG_PRIMARY, font=(MONO_FONT, 9, 'underline'), anchor='w', padx=10, pady=5, cursor='hand2')
   lbl_url.pack(side='left', fill='x', expand=True)

   lbl_act = tk.Label(row, text='[OPEN ↗]', bg=BG_VOID, fg=accent_col, font=(MONO_FONT, 8, 'bold'), padx=8, pady=5, cursor='hand2')
   lbl_act.pack(side='right')

   def _on_enter(e):
    row.configure(highlightbackground=accent_col)
    lbl_url.configure(fg=accent_col)
    lbl_act.configure(bg=BG_SELECTED, fg=ACCENT_MATRIX)

   def _on_leave(e):
    row.configure(highlightbackground=BORDER_DIM)
    lbl_url.configure(fg=FG_PRIMARY)
    lbl_act.configure(bg=BG_VOID, fg=accent_col)

   def _on_click(e):
    try:
     webbrowser.open(target_url)
    except Exception:
     pass

   for w in (row, lbl_key, lbl_url, lbl_act):
    w.bind('<Enter>', _on_enter)
    w.bind('<Leave>', _on_leave)
    w.bind('<Button-1>', _on_click)

  make_terminal_link(
   links_frame,
   'GITHUB:',
   'github.com/engamrhesham2002-cell/Rasd',
   'https://github.com/engamrhesham2002-cell/Rasd',
   ACCENT_MATRIX
  )
  make_terminal_link(
   links_frame,
   'LINKEDIN:',
   'linkedin.com/in/amr-hesham-mahmoud-zaki',
   'https://www.linkedin.com/in/amr-hesham-mahmoud-zaki-06a786406/',
   ACCENT_CYAN
  )
  
  start_btn = tk.Button(card, text='[ INITIALIZE_SYSTEM // ENTER ]', command=self.enter_app, bg=BG_HEADER, fg=ACCENT_MATRIX, activebackground=ACCENT_MATRIX, activeforeground=BG_VOID, relief='solid', borderwidth=1, font=(MONO_FONT, 11, 'bold'), padx=20, pady=9, cursor='hand2')
  start_btn.pack(side='bottom', pady=(6, 16))
  
  self.bind('<Return>',lambda e:self.enter_app())

 def enter_app(self):
  self.unbind('<Return>');self.set_workspace_geometry();self.show_home()

 def set_workspace_geometry(self):
  if hasattr(self, '_get_work_area'):
   wx, wy, screen_w, screen_h = self._get_work_area()
  else:
   wx, wy = 0, 0
   screen_w=max(720,self.winfo_screenwidth());screen_h=max(520,self.winfo_screenheight())
  width=min(1440,screen_w-30);height=min(860,screen_h-30)
  min_w=min(1050,width);min_h=min(650,height)
  self.minsize(min_w,min_h)
  self.geometry(f'{width}x{height}+{wx+max(0,(screen_w-width)//2)}+{wy+max(0,(screen_h-height)//2)}')
  self._normal_geometry = self.geometry()

 def animate_window_in(self):
  try:
   if getattr(self,'_fade_job',None):self.after_cancel(self._fade_job)
   self.wm_attributes('-alpha',0.94)
   def step(value=94):
    value=min(100,value+2);self.wm_attributes('-alpha',value/100)
    if value<100:self._fade_job=self.after(14,lambda:step(value))
   self._fade_job=self.after(14,lambda:step())
  except Exception:pass