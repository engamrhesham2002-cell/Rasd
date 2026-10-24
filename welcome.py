# Rasd - شاشة الترحيب وفتح نافذة العمل
from common import *
from update_utils import *
from storage import *

class WelcomeMixin:
 def header(self,title):
  h=tk.Frame(self,bg='#102c3d',height=66);h.pack(fill='x')
  brand=tk.Frame(h,bg='#102c3d');brand.pack(side='left',padx=18,pady=5)
  try:
   with Image.open(Path(getattr(sys,'_MEIPASS',BASE))/'Assets'/'rasd_logo.png') as source:
    self.header_icon=ImageTk.PhotoImage(source.convert('RGBA').resize((38,38),Image.Resampling.LANCZOS))
   tk.Label(brand,image=self.header_icon,bg='#102c3d').pack(side='left',padx=(0,8))
  except Exception:pass
  brand_text=tk.Frame(brand,bg='#102c3d');brand_text.pack(side='left')
  tk.Label(brand_text,text='RASD',font=('Segoe UI',17,'bold'),fg='white',bg='#102c3d').pack(anchor='w')
  tk.Label(brand_text,text='Made by ENG. Amr Hesham',font=('Segoe UI',8),fg='#a9c3d0',bg='#102c3d').pack(anchor='w')
  tk.Label(h,text=title,font=('Segoe UI',14,'bold'),fg='#d8e7ef',bg='#102c3d').pack(side='right',padx=22);return h

 def show_welcome(self):
  self.title('Rasd | Start')
  self.clear();self.project='';self.configure(bg='#c8d2d8');self.geometry('720x600');self.minsize(600,520)
  try:self.state('normal')
  except tk.TclError:pass
  art_path=Path(getattr(sys,'_MEIPASS',BASE))/'Assets'/'welcome_art.jpg'
  bg=tk.Frame(self,bg='#c8d2d8');bg.pack(fill='both',expand=True)
  try:
   with Image.open(art_path) as src:
    backdrop=ImageOps.fit(src.convert('RGB'),(720,600),method=Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(10))
    backdrop=Image.blend(backdrop,Image.new('RGB',(720,600),'#e5edf1'),.42)
   self._welcome_background_source=backdrop.copy();self.welcome_background_photo=ImageTk.PhotoImage(backdrop)
   self._welcome_background_label=tk.Label(bg,image=self.welcome_background_photo,borderwidth=0,bg='#c8d2d8');self._welcome_background_label.place(x=0,y=0,relwidth=1,relheight=1)
   def resize_welcome_background(event):
    if event.width<2 or event.height<2:return
    resized=ImageOps.fit(self._welcome_background_source,(event.width,event.height),method=Image.Resampling.LANCZOS)
    self.welcome_background_photo=ImageTk.PhotoImage(resized);self._welcome_background_label.configure(image=self.welcome_background_photo)
   bg.bind('<Configure>',resize_welcome_background)
  except Exception:pass
  card=tk.Frame(bg,bg='#edf2f5',highlightbackground='#ffffff',highlightthickness=2);card.place(relx=.5,rely=.5,anchor='center',relwidth=.86,relheight=.88)
  brand=tk.Frame(card,bg='#edf2f5');brand.pack(pady=(12,0))
  try:
   with Image.open(Path(getattr(sys,'_MEIPASS',BASE))/'Assets'/'rasd_logo.png') as source:self.welcome_logo=ImageTk.PhotoImage(source.convert('RGBA').resize((40,40),Image.Resampling.LANCZOS))
   tk.Label(brand,image=self.welcome_logo,bg='#edf2f5').pack(side='left',padx=(0,8))
  except Exception:pass
  brand_stack=tk.Frame(brand,bg='#edf2f5');brand_stack.pack(side='left',anchor='w')
  tk.Label(brand_stack,text='RASD',font=('Segoe UI',17,'bold'),fg='#102c3d',bg='#edf2f5').pack(anchor='w')
  tk.Label(brand_stack,text='Made by ENG. Amr Hesham',font=('Segoe UI',8),fg='#718491',bg='#edf2f5').pack(anchor='w')
  tk.Label(card,text='تعالى نعمل واحد ... مشروع جامد',font=('Segoe UI',18,'bold'),fg='#187db2',bg='#edf2f5',justify='center',wraplength=570).pack(fill='x',padx=18,pady=(8,8))
  image_holder=tk.Frame(card,bg='white',highlightbackground='#d8e2e8',highlightthickness=1);image_holder.pack(fill='both',expand=True,padx=24,pady=(0,78))
  try:
   with Image.open(art_path) as src:art=ImageOps.fit(src.convert('RGB'),(650,380),method=Image.Resampling.LANCZOS)
   self.welcome_photo=ImageTk.PhotoImage(art);tk.Label(image_holder,image=self.welcome_photo,bg='white',borderwidth=0).pack(fill='both',expand=True,padx=4,pady=4)
  except Exception:tk.Label(image_holder,text='👷',font=('Segoe UI Emoji',90),bg='white').pack(expand=True)
  pill=Image.new('RGBA',(300,64),(0,0,0,0));pd=ImageDraw.Draw(pill);pd.rounded_rectangle((8,8,292,60),radius=27,fill=(70,92,111,45));pd.rounded_rectangle((5,2,295,54),radius=27,fill=(249,252,254,250),outline=(231,239,245,255),width=2)
  self.start_photo=ImageTk.PhotoImage(pill);start=tk.Canvas(card,width=300,height=64,bg='#edf2f5',highlightthickness=0,cursor='hand2');start.create_image(150,32,image=self.start_photo);start.create_text(150,27,text='Start',font=('Segoe UI',18,'bold'),fill='#263946');start.bind('<Button-1>',lambda e:self.enter_app());start.place(relx=.5,rely=.97,anchor='s');self.bind('<Return>',lambda e:self.enter_app())

 def enter_app(self):
  self.unbind('<Return>');self.set_workspace_geometry();self.show_home()

 def set_workspace_geometry(self):
  screen_w=max(720,self.winfo_screenwidth());screen_h=max(520,self.winfo_screenheight())
  width=min(1440,screen_w-40);height=min(880,screen_h-80)
  min_w=min(1050,width);min_h=min(650,height)
  self.minsize(min_w,min_h);self.geometry(f'{width}x{height}+{max(0,(screen_w-width)//2)}+{max(0,(screen_h-height)//2)}')

 def animate_window_in(self):
  try:
   if getattr(self,'_fade_job',None):self.after_cancel(self._fade_job)
   self.wm_attributes('-alpha',0.94)
   def step(value=94):
    value=min(100,value+2);self.wm_attributes('-alpha',value/100)
    if value<100:self._fade_job=self.after(14,lambda:step(value))
   self._fade_job=self.after(14,lambda:step())
  except Exception:pass
