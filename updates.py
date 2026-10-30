# Rasd - فحص وتنزيل تحديثات البرنامج من GitHub
from common import *
from update_utils import *
from storage import *

class UpdatesMixin:
 def _fetch_latest_release(self):
  request=urllib.request.Request(LATEST_RELEASE_API,headers={'Accept':'application/vnd.github+json','User-Agent':'Rasd-Desktop-Updater','X-GitHub-Api-Version':'2022-11-28'})
  with urllib.request.urlopen(request,timeout=10) as response:data=json.loads(response.read(2_000_000).decode('utf-8'))
  if data.get('draft') or data.get('prerelease'):raise ValueError('GitHub returned a draft or prerelease as the latest release.')
  tag=str(data.get('tag_name',''))
  # استخراج الأرقام بمرونة بغض النظر عن وجود حرف v أو نقاط إضافية
  match=re.search(r'v?(\d+(?:\.\d+){1,3})',tag,re.IGNORECASE)
  if not match:match=re.search(r'(\d+)',tag)
  if not match:raise ValueError('Release version is missing or invalid.')
  
  ver_str=match.group(1)
  version=tuple(int(part) for part in ver_str.split('.'))
  assets=data.get('assets') or []
  return {'tag':tag,'version':version,'name':str(data.get('name') or tag),'body':str(data.get('body') or ''),'html_url':str(data.get('html_url') or ''),'assets':assets}

 def check_for_updates(self,manual=False):
  if self._update_check_running:
   if manual:messagebox.showinfo('التحديثات','جارٍ بالفعل فحص الإصدارات.',parent=self)
   return
  self._update_check_running=True
  future=self.update_executor.submit(self._fetch_latest_release)
  future.add_done_callback(lambda done:self.updateq.put(('release',manual,done)))

 def _update_version_tuple(self):
  # استخراج أرقام الإصدار الحالي من common.py بمرونة مطابقة
  clean_ver=re.sub(r'[^0-9.]','',APP_VERSION)
  parts=[int(p) for p in clean_ver.split('.') if p.isdigit()]
  return tuple(parts) if parts else (0, 40)

 def _release_asset(self, release):
  # البحث بمرونة عن أي ملف بصيغة .exe مرفوع في الـ Release
  for asset in release['assets']:
   name = str(asset.get('name', ''))
   if name.lower().endswith('.exe') and asset.get('state', 'uploaded') == 'uploaded':
    return 'standard', asset
  return 'standard', None

 def _handle_update_check(self,manual,future):
  self._update_check_running=False
  try:release=future.result()
  except Exception as exc:
   if manual:messagebox.showwarning('تعذر فحص التحديثات',f'تعذر الاتصال بـ GitHub الآن. تحقق من الإنترنت وحاول مرة أخرى.\n\n{str(exc)[:240]}',parent=self)
   return
  
  # مقارنة الإصدارات بدقة: إذا كان إصدار جيت هاب <= إصدارك الحالي، فلا جديد
  if release['version']<=self._update_version_tuple():
   if manual:messagebox.showinfo('التحديثات','أنت تستخدم أحدث إصدار من Rasd.',parent=self)
   return
  try:
   with connect() as c:row=c.execute("select value from app_settings where key='updates_snooze_until'").fetchone()
   if not manual and row and float(row['value'])>time.time():return
  except (OSError,ValueError,TypeError,sqlite3.Error):pass
  mode,asset=self._release_asset(release)
  self._show_update_dialog(release,mode,asset)

 def _show_update_dialog(self,release,mode,asset):
  if not self.winfo_exists():return
  dialog=tk.Toplevel(self);dialog.title('تحديث Rasd');dialog.configure(bg='#eef3f7');dialog.resizable(False,False);dialog.transient(self);dialog.grab_set()
  card=tk.Frame(dialog,bg='white',highlightbackground='#d6e1e7',highlightthickness=1);card.pack(fill='both',expand=True,padx=14,pady=14)
  tk.Label(card,text='أهم من الشغل تظبيط الشغل، فحدّثني يا معلم 😄',bg='white',fg='#19394e',font=('Segoe UI',14,'bold'),wraplength=470,justify='right').pack(fill='x',padx=20,pady=(20,7),anchor='e')
  tk.Label(card,text=f'إصدار جديد متاح: {release["tag"]}   ·   إصدارك الحالي: {APP_VERSION}',bg='white',fg='#167f8c',font=('Segoe UI',10,'bold'),justify='right').pack(fill='x',padx=20,pady=(0,10),anchor='e')
  body=re.sub(r'[`*_#>]', '',release['body']).strip()
  if len(body)>580:body=body[:577].rstrip()+'…'
  tk.Label(card,text=body or 'يتضمن هذا الإصدار تحسينات وإصلاحات جديدة.',bg='#f4f7f9',fg='#526b7c',font=('Segoe UI',9),justify='right',anchor='ne',wraplength=465,height=6,padx=12,pady=10).pack(fill='x',padx=18,pady=(0,10))
  if asset is None:
   tk.Label(card,text='ملف التثبيت المناسب لهذا النوع من النسخ غير مرفوع بعد. يمكنك فتح صفحة الإصدار والتحميل يدويًا.',bg='white',fg='#b44b53',font=('Segoe UI',9),justify='right',wraplength=465).pack(fill='x',padx=20,pady=(0,8))
  actions=tk.Frame(card,bg='white');actions.pack(fill='x',padx=18,pady=(8,18))
  def dismiss():
   try:
    with connect() as c:c.execute("insert into app_settings(key,value) values('updates_snooze_until',?) on conflict(key) do update set value=excluded.value",(str(time.time()+86400),))
   except sqlite3.Error:pass
   dialog.destroy()
  def update_now():
   if asset is None:
    if release['html_url']:webbrowser.open(release['html_url'])
    return
   dialog.destroy();self._begin_update_download(release,mode,asset,'now')
  def update_next():
   if asset is None:
    if release['html_url']:webbrowser.open(release['html_url'])
    return
   dialog.destroy();self._begin_update_download(release,mode,asset,'next')
  ttk.Button(actions,text='طنّشني ليوم',command=dismiss).pack(side='left',padx=3)
  if asset is not None:ttk.Button(actions,text='حدّثني لما أشتغل تاني',command=update_next).pack(side='right',padx=3)
  ttk.Button(actions,text='حدّثني الآن ❤️',command=update_now).pack(side='right',padx=3)
  dialog.protocol('WM_DELETE_WINDOW',dismiss);dialog.update_idletasks();dialog.geometry(f'520x{max(300,dialog.winfo_reqheight())}+{max(0,self.winfo_rootx()+(self.winfo_width()-520)//2)}+{max(0,self.winfo_rooty()+(self.winfo_height()-dialog.winfo_reqheight())//2)}')

 def _download_release_asset(self,asset):
  url=str(asset.get('browser_download_url') or '')
  if not url.startswith('https://github.com/engamrhesham2002-cell/Rasd/releases/download/'):raise ValueError('رابط ملف التحديث لا يخص إصدارات Rasd الرسمية.')
  size=int(asset.get('size') or 0)
  if size<=0 or size>350_000_000:raise ValueError('حجم ملف التحديث غير صالح.')
  UPDATE_HOME.mkdir(parents=True,exist_ok=True);downloads=UPDATE_HOME/'downloads';downloads.mkdir(parents=True,exist_ok=True)
  name=Path(str(asset.get('name') or '')).name
  if not name.lower().endswith('.exe') or name!=str(asset.get('name') or ''):raise ValueError('اسم ملف التحديث غير صالح.')
  target=downloads/name;partial=target.with_suffix(target.suffix+'.part');written=0
  request=urllib.request.Request(url,headers={'User-Agent':'Rasd-Desktop-Updater'})
  try:
   with urllib.request.urlopen(request,timeout=30) as response,partial.open('wb') as output:
    while True:
     chunk=response.read(1024*1024)
     if not chunk:break
     written+=len(chunk)
     if written>size:raise ValueError('ملف التحديث أكبر من الحجم المعلن.')
     output.write(chunk)
   if written!=size:raise ValueError(f'اكتمل تنزيل {written:,} بايت فقط من أصل {size:,}.')
   partial.replace(target);return target
  except Exception:
   try:partial.unlink(missing_ok=True)
   except OSError:pass
   raise

 def _begin_update_download(self,release,mode,asset,when):
  dialog=tk.Toplevel(self);dialog.title('تنزيل تحديث Rasd');dialog.configure(bg='white');dialog.resizable(False,False);dialog.transient(self);dialog.grab_set()
  frame=tk.Frame(dialog,bg='white');frame.pack(fill='both',expand=True,padx=22,pady=20)
  tk.Label(frame,text=f'جارٍ تنزيل Rasd {release["tag"]}…',bg='white',fg='#19394e',font=('Segoe UI',11,'bold')).pack(pady=(0,12))
  bar=ttk.Progressbar(frame,mode='indeterminate',length=360);bar.pack();bar.start(12)
  tk.Label(frame,text='سيتم التحقق من سلامة الملف قبل تثبيته.',bg='white',fg='#718491',font=('Segoe UI',9)).pack(pady=(10,0))
  dialog.protocol('WM_DELETE_WINDOW',lambda:None);dialog.update_idletasks();dialog.geometry(f'+{self.winfo_rootx()+(self.winfo_width()-dialog.winfo_width())//2}+{self.winfo_rooty()+(self.winfo_height()-dialog.winfo_reqheight())//2}')
  future=self.update_executor.submit(self._download_release_asset,asset)
  future.add_done_callback(lambda done:self.updateq.put(('download',when,release['tag'],dialog,done)))

 def _handle_update_download(self,when,tag,dialog,future):
  try:installer=future.result()
  except Exception as exc:
   try:dialog.destroy()
   except tk.TclError:pass
   messagebox.showerror('فشل تنزيل التحديث',f'لم يكتمل تنزيل التحديث. يمكنك المحاولة لاحقًا.\n\n{str(exc)[:300]}',parent=self);return
  try:dialog.destroy()
  except tk.TclError:pass
  mode='standard'
  if not queue_pending_update(installer,mode,tag):
   messagebox.showerror('تعذر تجهيز التحديث','تعذر حفظ التحديث لهذا التثبيت. تأكد من صلاحية الكتابة داخل مجلد البرنامج وحاول مرة أخرى.',parent=self);return
  if when=='now':
   if not start_scheduled_update(os.getpid(),installer,BASE,sys.executable):
    UPDATE_PENDING.unlink(missing_ok=True);messagebox.showerror('تعذر بدء التحديث','تعذر تشغيل مساعد التثبيت المدمج في Windows؛ سيظل البرنامج مفتوحًا. جرّب تنزيل المثبّت وتشغيله يدويًا.',parent=self);return
   self._update_install_on_close=True
   messagebox.showinfo('التحديث جاهز',f'تم تنزيل Rasd {tag}. سيُغلق البرنامج الآن تثبيت التحديث ثم يُفتح تلقائيًا.',parent=self)
   if self.winfo_exists():self.close_app()
  else:
   messagebox.showinfo('التحديث جاهز',f'تم تنزيل Rasd {tag} والتحقق منه. سيبدأ التثبيت تلقائيًا في المرة القادمة التي تفتح فيها البرنامج.',parent=self)

 def _show_update_failure(self,detail):
  try:UPDATE_FAILURE.unlink(missing_ok=True)
  except OSError:pass
  if self.winfo_exists():messagebox.showwarning('تعذر تثبيت التحديث','لم يكتمل تثبيت التحديث؛ فتح Rasd الإصدار الحالي. يمكنك إعادة المحاولة أو تشغيل ملف التثبيت يدويًا.\n\n'+detail[:300],parent=self)

 def _poll_update_queue(self):
  try:
   while True:
    item=self.updateq.get_nowait()
    if item[0]=='release':self._handle_update_check(item[1],item[2])
    elif item[0]=='download':self._handle_update_download(item[1],item[2],item[3],item[4])
  except queue.Empty:pass