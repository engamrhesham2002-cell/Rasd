# Rasd - قفل البرنامج وكلمة المرور
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
  self.title('Rasd Login')
  self.clear();self.unbind('<Return>');self.title('Rasd | فتح البرنامج');self.configure(bg='#e8edf1');self.geometry('560x400');self.minsize(520,360)
  self.geometry(f'560x400+{max(0,(self.winfo_screenwidth()-560)//2)}+{max(0,(self.winfo_screenheight()-400)//2)}')
  shell=tk.Frame(self,bg='#102c3d');shell.pack(fill='both',expand=True,padx=20,pady=20)
  card=tk.Frame(shell,bg='#f5f7f8',highlightbackground='#d9e4e9',highlightthickness=1);card.place(relx=.5,rely=.5,anchor='center',width=450,height=300)
  tk.Label(card,text='RASD',bg='#f5f7f8',fg='#102c3d',font=('Segoe UI',19,'bold')).pack(pady=(32,8))
  tk.Label(card,text='أدخل كلمة المرور لفتح البرنامج',bg='#f5f7f8',fg='#526b7c',font=('Segoe UI',11)).pack(pady=(0,18))
  self.login_status=tk.StringVar(value='')
  self.password_entry=ttk.Entry(card,show='●',font=('Segoe UI',12),justify='center');self.password_entry.pack(fill='x',padx=38,ipady=5)
  tk.Button(card,text='فتح البرنامج',command=self.unlock_app,bg='#167f8c',fg='white',activebackground='#106b76',activeforeground='white',relief='flat',font=('Segoe UI',10,'bold'),padx=18,pady=8,cursor='hand2').pack(pady=(15,5))
  tk.Label(card,textvariable=self.login_status,bg='#f5f7f8',fg='#bd4856',font=('Segoe UI',9)).pack()
  tk.Label(card,text='كلمة المرور تمنع الدخول للبرنامج فقط؛ ملفات المشروع تظل ملفات عادية.',bg='#f5f7f8',fg='#758692',font=('Segoe UI',8),wraplength=400).pack(side='bottom',pady=14)
  self.bind('<Return>',lambda e:(self.unlock_app(),'break'));self.password_entry.focus_set()

 def unlock_app(self):
  if self.verify_password(self.password_entry.get()):
   self.unbind('<Return>');self.show_welcome();self.animate_window_in();self.after(1800,self.check_for_updates)
  else:
   self.login_status.set('كلمة المرور غير صحيحة. حاول مرة أخرى.');self.password_entry.delete(0,'end');self.password_entry.focus_set()

 def manage_password(self):
  enabled=self.password_enabled();dialog=tk.Toplevel(self);dialog.title('حماية البرنامج');dialog.configure(bg='#eef2f5');dialog.resizable(False,False);dialog.transient(self);dialog.grab_set()
  frame=tk.Frame(dialog,bg='white',highlightbackground='#d7e1e6',highlightthickness=1);frame.pack(fill='both',expand=True,padx=14,pady=14)
  tk.Label(frame,text='حماية البرنامج',bg='white',fg='#19394e',font=('Segoe UI',14,'bold')).pack(anchor='e',padx=18,pady=(16,5))
  tk.Label(frame,text=('الحماية مفعلة. أدخل الحالية للتغيير أو الإلغاء.' if enabled else 'فعّل كلمة مرور اختيارية عند بدء البرنامج.'),bg='white',fg='#617789',font=('Segoe UI',9),justify='right').pack(anchor='e',padx=18,pady=(0,12))
  fields=tk.Frame(frame,bg='white');fields.pack(fill='x',padx=18);entries={}
  specs=([('old','كلمة المرور الحالية')] if enabled else [])+[('new','كلمة مرور جديدة'),('confirm','تأكيد كلمة المرور')]
  for key,label in specs:
   tk.Label(fields,text=label,bg='white',fg='#435b6d',font=('Segoe UI',9)).pack(anchor='e',pady=(5,2))
   entry=ttk.Entry(fields,show='●',justify='right',width=38);entry.pack(fill='x',ipady=3);entries[key]=entry
  status=tk.StringVar(value='')
  tk.Label(frame,textvariable=status,bg='white',fg='#bd4856',font=('Segoe UI',9),justify='right').pack(anchor='e',padx=18,pady=(7,0))
  actions=tk.Frame(frame,bg='white');actions.pack(fill='x',padx=18,pady=(8,14))
  def save():
   if enabled and not self.verify_password(entries['old'].get()):status.set('كلمة المرور الحالية غير صحيحة.');return
   password=entries['new'].get();confirm=entries['confirm'].get()
   if len(password)<6:status.set('استخدم 6 أحرف على الأقل.');return
   if password!=confirm:status.set('تأكيد كلمة المرور غير مطابق.');return
   self.store_password(password);messagebox.showinfo('حماية البرنامج','تم حفظ كلمة المرور. سيطلبها البرنامج عند تشغيله.',parent=dialog);dialog.destroy()
  def disable():
   if not self.verify_password(entries['old'].get()):status.set('كلمة المرور الحالية غير صحيحة.');return
   self.clear_password();messagebox.showinfo('حماية البرنامج','تم إلغاء كلمة المرور.',parent=dialog);dialog.destroy()
  tk.Button(actions,text=('تغيير كلمة المرور' if enabled else 'تفعيل كلمة المرور'),command=save,bg='#167f8c',fg='white',activebackground='#106b76',activeforeground='white',relief='flat',font=('Segoe UI',9,'bold'),padx=12,pady=6,cursor='hand2').pack(side='right',padx=3)
  if enabled:ttk.Button(actions,text='إلغاء الحماية',command=disable).pack(side='right',padx=3)
  ttk.Button(actions,text='إغلاق',command=dialog.destroy).pack(side='left',padx=3)
  if enabled:entries['old'].focus_set()
  else:entries['new'].focus_set()
  dialog.update_idletasks();dialog.geometry(f'+{self.winfo_rootx()+(self.winfo_width()-dialog.winfo_width())//2}+{self.winfo_rooty()+(self.winfo_height()-dialog.winfo_height())//2}')
