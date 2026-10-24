# Rasd - المعاينة: اختيار الملف وكاش المعاينة
from common import *
from update_utils import *
from storage import *

class PreviewMixin:
 def dwg_preview_cache_path(self,p):
  p=Path(p);st=p.stat()
  def cache_relative_path(value):
   value=Path(value)
   try:return str(value.resolve().relative_to(LOG.resolve()))
   except ValueError:return value.name
  parts=[cache_relative_path(p),str(st.st_mtime_ns),str(st.st_size)]
  for ext in ('.pdf','.png','.jpg','.jpeg'):
   side=p.with_suffix(ext)
   try:
    if side.is_file():ss=side.stat();parts.extend((cache_relative_path(side),str(ss.st_mtime_ns),str(ss.st_size)))
   except OSError:pass
  key=hashlib.sha1('|'.join(parts).encode('utf-8')).hexdigest()
  return LOG/'.preview_cache'/(key+'.png')

 def preview_selected(self,tree):
  sel=tree.selection()
  if not sel:return
  self.preview_token+=1
  event=getattr(self,'activity_rows',{}).get(str(sel[0]))
  if event:
   self.hide_excel_preview();self.preview_current_path=None
   try:self.preview_related_strip.grid_remove()
   except (AttributeError,tk.TclError):pass
   target=event['path'] or 'داخل البرنامج';when=event['occurred_at']
   try:target=Path(target).resolve().relative_to(self.root.resolve()).as_posix()
   except (OSError,ValueError):pass
   meta=f"النشاط: {event['action']}\nالتفاصيل: {event['details']}\nالتاريخ: {when}\nالمسار: {target}"
   self.render_preview(self.make_card(event['action'],'HISTORY',event['details']),meta);return
  p=Path(sel[0])
  if p.is_dir():
   if getattr(self,'preview_current_path',None)!=str(p.resolve()):self.log_activity('معاينة مجلد',f'عرض المجلد «{p.name}»',path=p)
   self.preview_current_path=str(p.resolve());self.render_related_strip(p,[])
   self.render_preview(self.make_card(p.name,'مجلد','انقر مرتين لفتح محتوياته.'),f'المجلد: {p.name}\nانقر مرتين لفتحه.');return
  self.hide_excel_preview()
  if getattr(self,'preview_current_path',None)!=str(p.resolve()):
   self.preview_page=0;self.preview_zoom=1.0;self.preview_current_path=str(p.resolve());self.log_activity('معاينة ملف',f'عرض معاينة «{p.name}»',path=p)
  try:st=p.stat();rel=p.relative_to(self.root).as_posix()
  except OSError:return
  with connect() as c:tags=[r[0] for r in c.execute('select tag from tags where path=? order by tag',(str(p.resolve()),))];r=c.execute('select last_open from files where path=?',(str(p.resolve()),)).fetchone()
  related=[]
  if p.suffix.lower() in ('.dwg','.dxf','.pdf'):
   try:related=[x for x in p.parent.iterdir() if x.is_file() and x.stem.casefold()==p.stem.casefold() and x.suffix.lower() in ('.dwg','.dxf','.pdf','.png','.jpg','.jpeg') and x!=p]
   except OSError:pass
  meta=f'الملف: {p.name}\nالنوع: {p.suffix or "بدون امتداد"}\nالحجم: {sizefmt(st.st_size)}\nالمجلد: {rel}\nتاريخ الملف: {stamp(st.st_mtime)}\nآخر فتح: {r[0] if r and r[0] else "لم يفتح بعد"}\nالهاشتاجات: {" ".join(tags) or "لا توجد"}'
  self.render_related_strip(p,related)
  if related:meta+='\nلوحات مرتبطة متاحة أسفل المعاينة: '+', '.join(x.name for x in related[:3])
  token=self.preview_token;self.preview_meta.configure(text=meta+'\n\nجارٍ تجهيز المعاينة…');self.preview_image.delete('all');self.preview_image.create_text(24,24,text='جارٍ تجهيز المعاينة…',anchor='nw',fill='#617789')
  key=(str(p.resolve()),st.st_mtime_ns,st.st_size,self.preview_page,str(self.dwg_preview_cache_path(p)) if p.suffix.lower()=='.dwg' else '')
  cached=self.preview_cache.get(key)
  if cached:
   self.preview_cache.move_to_end(key);image,note=cached;self.previewq.put((token,image.copy(),meta+'\n\n'+note));return
  if p.suffix.lower()=='.dwg':
   try:
    cad_png=self.dwg_preview_cache_path(p)
    if cad_png.is_file():
     with Image.open(cad_png) as cached_image:image=cached_image.convert('RGB').copy()
     note='معاينة DWG مخزنة · تم فتحها مباشرة من الذاكرة المؤقتة';self.preview_cache[key]=(image.copy(),note);self.previewq.put((token,image,meta+'\n\n'+note,key,note));return
   except (OSError,ValueError):pass
  if self.preview_future and not self.preview_future.done():
   proc=getattr(self,'cad_preview_process',None)
   if proc and proc.poll() is None and getattr(self,'cad_preview_path',None)!=p.resolve():
    try:proc.kill()
    except OSError:pass
   self.preview_future.cancel()
  if p.suffix.lower() in ('.xlsx','.xls','.xlsm','.xlsb','.csv','.tsv'):
   self.preview_meta.configure(text=meta+'\n\nجارٍ تجهيز معاينة ورقة Excel…');self.preview_image.delete('all');self.preview_image.create_text(24,24,text='جارٍ تجهيز معاينة Excel…',anchor='nw',fill='#617789')
   self.preview_future=self.preview_executor.submit(self.preview_excel_worker,p,token,meta,None,key)
  else:
   if p.suffix.lower()=='.dwg':
    self.render_preview(self.make_card(p.name,'DWG','جارٍ البحث عن معاينة جاهزة أو تحويل اللوحة في الخلفية…'),meta+'\n\nجارٍ تجهيز المعاينة. سيظهر الرسم هنا فور اكتمالها، وتُحفظ لتفتح أسرع لاحقًا.')
    self.preview_future=self.cad_preview_executor.submit(self.dwg_preview_worker,p,token,meta,key)
   else:self.preview_future=self.preview_executor.submit(self.preview_worker,p,token,meta,key)
