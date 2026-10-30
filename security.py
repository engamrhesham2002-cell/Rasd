# Rasd - قفل البرنامج وكلمة المرور (ستايل التيرمينال الداكن)
from common import *
from update_utils import *
from storage import *

class SecurityMixin:
 def password_record(self):
  with connect() as c:values={r['key']:r['value'] for r in c.execute("select key,value from app_settings where key in ('password_salt','password_hash','password_iterations')")}
  if not all(k in values for k in ('password_salt','password_hash','password_iterations')):return None
  try:return values['password_salt'],values['password_hash'],int(values['password_iterations'])
  except (TypeError,ValueError):return None

 def password_enabled(self):return self.password_record() is not None

 def verify_password(self,password):
  record=self.password_record()
  if not record:return False
  salt,digest,iterations=record
  try:candidate=hashlib.pbkdf2_hmac('sha256',password.encode('utf-8'),bytes.fromhex(salt),iterations).hex()
  except (ValueError,TypeError):return False
  return secrets.compare_digest(candidate,digest)

 def store_password(self,password):
  salt=secrets.token_bytes(16);iterations=310000;digest=hashlib.pbkdf2_hmac('sha256',password.encode('utf-8'),salt,iterations).hex()
  with connect() as c:c.executemany('insert into app_settings(key,value) values(?,?) on conflict(key) do update set value=excluded.value',[('password_salt',salt.hex()),('password_hash',digest),('password_iterations',str(iterations))])

 def clear_password(self):
  with connect() as c:c.execute("delete from app_settings where key in ('password_salt','password_hash','password_iterations')")

 def show_lock_screen(self):
  self.title('Rasd // SEC_AUTH')
  self.clear();self.unbind('<Return>');self.title('Rasd // قفل الأمان');self.configure(bg=BG_VOID);self.geometry('560x400');self.minsize(520,360)
  self.geometry(f'560x400+{max(0,(self.winfo_screenwidth()-560)//2)}+{max(0,(self.winfo_screenheight()-400)//2)}')
  shell=tk.Frame(self,bg=BG_VOID);shell.pack(fill='both',expand=True,padx=20,pady=20)
  card=tk.Frame(shell,bg=BG_PANEL,highlightbackground=ACCENT_MATRIX,highlightthickness=1);card.place(relx=.5,rely=.5,anchor='center',width=460,height=310)
  
  head=tk.Frame(card,bg=BG_HEADER,height=32);head.pack(fill='x');head.pack_propagate(False)
  tk.Label(head,text=' root@rasd:~# sudo --authenticate',bg=BG_HEADER,fg=ACCENT_MATRIX,font=(TERM_FONT,9,'bold')).pack(side='left',padx=10)
  
  tk.Label(card,text='[>_ RASD SEC_LOCK]',bg=BG_PANEL,fg=ACCENT_MATRIX,font=(TERM_FONT,17,'bold')).pack(pady=(22,6))
  tk.Label(card,text='أدخل كلمة المرور لفتح النظام',bg=BG_PANEL,fg=ACCENT_CYAN,font=(TERM_FONT,10)).pack(pady=(0,16))
  self.login_status=tk.StringVar(value='')
  self.password_entry=tk.Entry(card,show='*',bg=BG_VOID,fg=ACCENT_MATRIX,insertbackground=ACCENT_MATRIX,relief='solid',borderwidth=1,font=(TERM_FONT,12,'bold'),justify='center');self.password_entry.pack(fill='x',padx=38,ipady=6)
  tk.Button(card,text='[ UNLOCK_SYSTEM // فتح البرنامج ]',command=self.unlock_app,bg=BG_HEADER,fg=ACCENT_MATRIX,activebackground=ACCENT_MATRIX,activeforeground=BG_VOID,relief='solid',borderwidth=1,font=(TERM_FONT,10,'bold'),padx=18,pady=8,cursor='hand2').pack(pady=(15,5))
  tk.Label(card,textvariable=self.login_status,bg=BG_PANEL,fg=ACCENT_DANGER,font=(TERM_FONT,9,'bold')).pack()
  tk.Label(card,text='كلمة المرور تمنع الدخول للبرنامج فقط؛ ملفات المشروع تظل ملفات عادية.',bg=BG_PANEL,fg=FG_MUTED,font=(TERM_FONT,8),wraplength=400).pack(side='bottom',pady=12)
  self.bind('<Return>',lambda e:(self.unlock_app(),'break'));self.password_entry.focus_set()

 def unlock_app(self):
  if self.verify_password(self.password_entry.get()):
   self.unbind('<Return>');self.show_welcome();self.animate_window_in();self.after(1800,self.check_for_updates)
  else:
   self.login_status.set('[ACCESS_DENIED] كلمة المرور غير صحيحة.');self.password_entry.delete(0,'end');self.password_entry.focus_set()

 def manage_password(self):
  enabled=self.password_enabled();dialog=tk.Toplevel(self);dialog.title('حماية البرنامج');dialog.configure(bg=BG_VOID);dialog.resizable(False,False);dialog.transient(self);dialog.grab_set()
  frame=tk.Frame(dialog,bg=BG_PANEL,highlightbackground=BORDER_DIM,highlightthickness=1);frame.pack(fill='both',expand=True,padx=14,pady=14)
  tk.Label(frame,text='[ SEC_CONFIG // حماية البرنامج ]',bg=BG_PANEL,fg=ACCENT_MATRIX,font=(TERM_FONT,12,'bold')).pack(anchor='e',padx=18,pady=(16,5))
  tk.Label(frame,text=('الحماية مفعلة. أدخل الحالية للتغيير أو الإلغاء.' if enabled else 'فعّل كلمة مرور اختيارية عند بدء البرنامج.'),bg=BG_PANEL,fg=FG_MUTED,font=(TERM_FONT,9),justify='right').pack(anchor='e',padx=18,pady=(0,12))
  fields=tk.Frame(frame,bg=BG_PANEL);fields.pack(fill='x',padx=18);entries={}
  specs=([('old','كلمة المرور الحالية')] if enabled else [])+[('new','كلمة مرور جديدة'),('confirm','تأكيد كلمة المرور')]
  for key,label in specs:
   tk.Label(fields,text=label,bg=BG_PANEL,fg=ACCENT_CYAN,font=(TERM_FONT,9)).pack(anchor='e',pady=(5,2))
   entry=tk.Entry(fields,show='*',bg=BG_VOID,fg=ACCENT_MATRIX,insertbackground=ACCENT_MATRIX,relief='solid',borderwidth=1,font=(TERM_FONT,10),justify='right',width=38);entry.pack(fill='x',ipady=4);entries[key]=entry
  status=tk.StringVar(value='')
  tk.Label(frame,textvariable=status,bg=BG_PANEL,fg=ACCENT_DANGER,font=(TERM_FONT,9),justify='right').pack(anchor='e',padx=18,pady=(7,0))
  actions=tk.Frame(frame,bg=BG_PANEL);actions.pack(fill='x',padx=18,pady=(8,14))
  def save():
   if enabled and not self.verify_password(entries['old'].get()):status.set('كلمة المرور الحالية غير صحيحة.');return
   password=entries['new'].get();confirm=entries['confirm'].get()
   if len(password)<6:status.set('استخدم 6 أحرف على الأقل.');return
   if password!=confirm:status.set('تأكيد كلمة المرور غير مطابق.');return
   self.store_password(password);messagebox.showinfo('حماية البرنامج','تم حفظ كلمة المرور. سيطلبها البرنامج عند تشغيله.',parent=dialog);dialog.destroy()
  def disable():
   if not self.verify_password(entries['old'].get()):status.set('كلمة المرور الحالية غير صحيحة.');return
   self.clear_password();messagebox.showinfo('حماية البرنامج','تم إلغاء كلمة المرور.',parent=dialog);dialog.destroy()
  tk.Button(actions,text=('[تغيير كلمة المرور]' if enabled else '[تفعيل كلمة المرور]'),command=save,bg=BG_HEADER,fg=ACCENT_MATRIX,activebackground=ACCENT_MATRIX,activeforeground=BG_VOID,relief='solid',borderwidth=1,font=(TERM_FONT,9,'bold'),padx=12,pady=6,cursor='hand2').pack(side='right',padx=3)
  if enabled:ttk.Button(actions,text='[إلغاء الحماية]',command=disable).pack(side='right',padx=3)
  ttk.Button(actions,text='[إغلاق]',command=dialog.destroy).pack(side='left',padx=3)
  if enabled:entries['old'].focus_set()
  else:entries['new'].focus_set()
  dialog.update_idletasks();dialog.geometry(f'+{self.winfo_rootx()+(self.winfo_width()-dialog.winfo_width())//2}+{self.winfo_rooty()+(self.winfo_height()-dialog.winfo_height())//2}')