# Rasd - المعاينة: ضبط اتجاه النصوص العربية بالكامل وتسريع جلب الملفات المرتبطة بدون تجميد الواجهة
from common import *
from update_utils import *
from storage import *

class PreviewMixin:
 def _rtl_lines(self, lines):
  out = []
  for line in lines:
   if line:
    out.append(RLM + str(line))
  return '\n'.join(out)

 def preview_selected(self,tree):
  if not tree or not tree.winfo_exists():
   return
  sel=tree.selection()
  if not sel:
   self.preview_token+=1
   self.preview_current_path=None
   if hasattr(self,'hide_excel_preview'):self.hide_excel_preview()
   if hasattr(self,'preview_image') and self.preview_image.winfo_exists():
    self.preview_image.delete('all')
   if hasattr(self,'preview_meta') and self.preview_meta.winfo_exists():
    self.preview_meta.configure(text=RLM+'اختر ملفًا أو مجلدًا لعرض المعاينة والتفاصيل.')
   if getattr(self,'preview_related_container',None) and self.preview_related_container.winfo_exists():
    self.preview_related_container.grid_remove()
   return

  event=getattr(self,'activity_rows',{}).get(str(sel[0])) if tree is getattr(self,'file_tree',None) else None
  if event:
   self.preview_token+=1;self.hide_excel_preview();self.preview_current_path=None;self.preview_page=0;self.preview_zoom=1.0
   card=self.make_card('سجل النشاط',event['action'],f"التفاصيل: {event['details']}\nالوقت: {event['occurred_at']}",kind='activity')
   meta_lines=[
    f"العملية: {event['action']}",
    f"التفاصيل: {event['details']}",
    f"التاريخ والوقت: \u200e{event['occurred_at']}\u200f"
   ]
   if event['path']:meta_lines.append(f"المسار: \u200e{event['path']}\u200f")
   self.render_related_strip(Path('.'),[])
   self.render_preview(card,self._rtl_lines(meta_lines));return
  p=Path(sel[0])
  if self.preview_current_path!=str(p):self.preview_page=0;self.preview_zoom=1.0;self.excel_sheet_name=None;self.excel_row_limit=150;self.preview_current_path=str(p)
  self.request_preview(p)

 def find_related_project_files(self,path):
  p=Path(path)
  if not self.project or p.is_dir():return []
  stem=re.sub(r'[\s_\-]+',' ',p.stem).strip().casefold()
  if len(stem)<2:return []
  
  cached = getattr(self, '_project_files_mem_cache', None)
  if not cached or cached[0] != self.project:
   with connect() as c:
    rows = c.execute('select path,name from files where project=?',(self.project,)).fetchall()
   cached = (self.project, [(r['path'], r['name']) for r in rows if r['path'] and r['name']])
   self._project_files_mem_cache = cached
  
  p_norm = os.path.normcase(str(p))
  exact=[];partial=[]
  for row_path, row_name in cached[1]:
   if os.path.normcase(row_path) == p_norm:
    continue
   if is_task_internal_artifact(row_path):
    continue
   other_stem = re.sub(r'[\s_\-]+',' ',Path(row_name).stem).strip().casefold()
   if other_stem == stem:
    exact.append(Path(row_path))
   elif len(stem)>=4 and (stem in other_stem or other_stem in stem):
    partial.append(Path(row_path))
  
  candidates = (exact + partial)[:12]
  return [cand for cand in candidates if cand.is_file()][:8]

 def request_preview(self,p):
  self.preview_token+=1;token=self.preview_token;page=self.preview_page
  if p.suffix.lower() not in ('.xlsx','.xlsm','.xltx','.xltm','.xls','.xlsb','.csv'):self.hide_excel_preview()
  if not p.exists():
   self.render_related_strip(p,[])
   self.render_preview(self.make_card(p.name,'عنصر غير موجود حالياً','ربما تم نقله أو حذفه من المجلد.'),self._rtl_lines([f'الاسم: \u200e{p.name}\u200f','الحالة: غير موجود في المجلد حالياً']));return
  try:st=p.stat()
  except OSError:return
  with connect() as c:
   open_row=c.execute('select last_open from files where path=?',(str(p.resolve()),)).fetchone()
   tags=[r[0] for r in c.execute('select tag from tags where path=? order by tag',(str(p.resolve()),))]
  related=self.find_related_project_files(p) if p.is_file() else []
  self.render_related_strip(p,related)
  
  kind_txt = 'مجلد' if p.is_dir() else classify(p.suffix.lower())
  size_txt = sizefmt(self.indexed_folder_size(p)) if p.is_dir() else sizefmt(st.st_size)
  mtime_txt = stamp(st.st_mtime)
  open_txt = (open_row['last_open'] if open_row and open_row['last_open'] else '—')
  
  meta_lines = [
   f"الاسم: \u200e{p.name}\u200f",
   f"النوع: \u200e{kind_txt}\u200f",
   f"الحجم: \u200e{size_txt}\u200f",
   f"آخر تعديل: \u200e{mtime_txt}\u200f",
   f"آخر فتح: \u200e{open_txt}\u200f"
  ]
  if tags:
   meta_lines.append(f"الهاشتاجات: {' '.join('#'+x for x in tags)}")
  if related:
   rel_names = ' ، '.join(f"\u200e{x.name}\u200f" for x in related[:3])
   meta_lines.append(f"ملفات مرتبطة بالاسم: {rel_names}")
  meta = self._rtl_lines(meta_lines)

  key=(str(p.resolve()),st.st_mtime_ns,st.st_size,page,getattr(self,'excel_sheet_name',None),getattr(self,'excel_row_limit',150))
  if key in self.preview_cache and p.suffix.lower() not in ('.xlsx','.xlsm','.xltx','.xltm','.xls','.xlsb','.csv'):
   image,note=self.preview_cache[key];self.preview_cache.move_to_end(key)
   full_meta = meta + (f'\n{RLM}{note}' if note else '')
   self.render_preview(image,full_meta);return
  self.preview_meta.configure(text=meta+f'\n{RLM}جارٍ تجهيز المعاينة...')
  if p.suffix.lower()=='.dwg':
   proc=getattr(self,'cad_preview_process',None)
   if proc and proc.poll() is None:
    try:proc.kill()
    except OSError:pass
   self.cad_preview_executor.submit(self.build_preview,token,p,meta,page,key)
   return
  if self.preview_future and not self.preview_future.done():self.preview_future.cancel()
  self.preview_future=self.preview_executor.submit(self.build_preview,token,p,meta,page,key)

 def render_preview(self,image,meta):
  self.hide_excel_preview();self.preview_base=image;self.preview_pan=[0,0];self.paint_preview();self.preview_meta.configure(text=meta)

 def paint_preview(self):
  if not getattr(self,'preview_base',None):return
  canvas=self.preview_image;canvas.update_idletasks()
  cw=max(260,canvas.winfo_width()-10);ch=max(220,canvas.winfo_height()-10)
  bw,bh=self.preview_base.size;scale=min(cw/max(1,bw),ch/max(1,bh))*self.preview_zoom
  w=max(80,min(2600,int(bw*scale)));h=max(80,min(2600,int(bh*scale)))
  method=Image.Resampling.BILINEAR
  img=self.preview_base.resize((w,h),method);self.preview_photo=ImageTk.PhotoImage(img)
  canvas.delete('all');x=cw//2+self.preview_pan[0];y=ch//2+self.preview_pan[1]
  canvas.create_rectangle(max(2,x-w//2-4),max(2,y-h//2-4),x+w//2+4,y+h//2+4,fill=BG_PANEL,outline=BORDER_DIM)
  canvas.create_image(x,y,image=self.preview_photo,anchor='center')

 def preview_pan_start(self,e):self.preview_drag=(e.x,e.y)

 def preview_pan_move(self,e):
  if hasattr(self,'preview_drag') and getattr(self,'preview_base',None):
   dx=e.x-self.preview_drag[0];dy=e.y-self.preview_drag[1];self.preview_drag=(e.x,e.y);self.preview_pan[0]+=dx;self.preview_pan[1]+=dy;self.paint_preview()

 def preview_wheel(self,e):
  self.zoom_preview(.12 if e.delta>0 else -.12)
  return 'break'

 def zoom_preview(self,delta):
  if getattr(self,'excel_preview_active',False):return self.zoom_excel_preview(1 if delta>0 else -1)
  if getattr(self,'preview_base',None):self.preview_zoom=min(3.0,max(.45,round(self.preview_zoom+delta,2)));self.paint_preview()

 def change_pdf_page(self,delta):
  p=self.selected_path()
  if not p or p.suffix.lower()!='.pdf':return
  self.preview_page=max(0,self.preview_page+delta);self.request_preview(p)