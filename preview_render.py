# Rasd - بناء صور المعاينة (مع تسريع فائق للوحات وملفات PDF الكبيرة ودعم الخط العربي)
from common import *
from update_utils import *
from storage import *

# حدود أمان للمعاينة: أي صفحة PDF أو صورة مضمنة أو صورة عادية تتجاوز هذه
# الحدود لا تُفكّ ضغطها كاملة حتى لا يستهلك البرنامج كل الذاكرة ويتجمد/يُغلق.
MAX_PDF_PIXEL_SIDE = 1600        # أقصى طول/عرض لبكسلات صفحة PDF
MAX_PDF_PIXELS = 4_000_000       # أقصى عدد بكسلات لصفحة PDF
MAX_IMAGE_PREVIEW_PIXELS = 40_000_000
MAX_EMBEDDED_IMAGE_PIXELS = 24_000_000
MAX_DWG_SCAN_BYTES = 32 * 1024 * 1024
MAX_DWG_PLOT_BYTES = 80 * 1024 * 1024
MAX_DXF_BYTES = 45 * 1024 * 1024

def pdf_render_scale(width,height):
    """مقياس رسم آمن لصفحة PDF مع سقف صارم للبكسلات (بدون حد أدنى)."""
    width=max(1.0,float(width or 1.0))
    height=max(1.0,float(height or 1.0))
    if width != width or height != height:width=height=1.0
    max_side=max(width,height)
    scale=min(1.2,760.0/max_side)
    scale=min(scale,MAX_PDF_PIXEL_SIDE/width,MAX_PDF_PIXEL_SIDE/height)
    est_pixels=(width*scale)*(height*scale)
    if est_pixels>MAX_PDF_PIXELS:
        scale*=math.sqrt(MAX_PDF_PIXELS/est_pixels)
    return max(scale,1e-4)

class PreviewRenderMixin:
 def build_preview(self,token,p,meta,page,key=None):
  if token != getattr(self, 'preview_token', 0):
   return
  fitz=PdfReader=Document=None
  try:import fitz
  except ImportError:pass
  try:from pypdf import PdfReader
  except ImportError:pass
  try:from docx import Document
  except ImportError:pass
  try:
   if p.is_dir():
    try:count=sum(1 for _ in p.iterdir())
    except OSError:count=0
    self.previewq.put(('image',token,self.make_card(p.name,'مجلد مشروع',f'يحتوي على {count} عنصر مباشر',kind='folder'),meta,key,''))
    return
   ext=p.suffix.lower()
   if ext in ('.png','.jpg','.jpeg','.bmp','.gif','.tif','.tiff'):
    with Image.open(p) as im:
     # صور ضخمة جدًا (سكانات/لوحات) لا تُفكّ كاملة داخل المعاينة
     if ext in ('.jpg','.jpeg'):
      try:im.draft('RGB',(1200,1000))
      except Exception:pass
     if int(im.width)*int(im.height)>MAX_IMAGE_PREVIEW_PIXELS:
      self.previewq.put(('image',token,self.make_card(p.name,'صورة كبيرة جدًا','هذه الصورة أكبر من أن تُعرض مباشرة هنا؛ انقر مرتين لفتحها في العارض الخارجي.'),meta,key,''))
      return
     frame=im.convert('RGB');frame.thumbnail((850,750),Image.Resampling.BILINEAR)
     self.previewq.put(('image',token,self.frame_image(frame,f'صورة {ext[1:].upper()} — {im.width}×{im.height}'),meta,key,''))
     return
   if ext=='.pdf' and fitz:
    doc=fitz.open(str(p))
    try:
     if token != getattr(self, 'preview_token', 0):
      return
     total=max(1,len(doc));page=min(max(0,page),total-1);self.preview_page=page
     pdf_page=doc[page]
     rect=pdf_page.rect
     # صفحات CAD المصدَّرة PDF قد تكون أبعادها أكبر بمئات المرات من A4.
     # الحد الأدنى القديم (0.35) كان ينتج pixmap بمليارات البكسلات فيستهلك
     # كل الذاكرة ويجمّد البرنامج. نحسب المقياس من أبعاد الصفحة مع سقف
     # صارم للبكسلات، بدون أي حد أدنى.
     width=max(1.0,float(getattr(rect,'width',1.0) or 1.0))
     height=max(1.0,float(getattr(rect,'height',1.0) or 1.0))
     target_scale=pdf_render_scale(width,height)
     pix=pdf_page.get_pixmap(matrix=fitz.Matrix(target_scale,target_scale),alpha=False)
     img=Image.frombytes('RGB',[pix.width,pix.height],pix.samples)
     del pix
    finally:
     doc.close()
    if token != getattr(self, 'preview_token', 0):
     return
    if img.width > 820 or img.height > 720:
     img.thumbnail((820,720),Image.Resampling.BILINEAR)
    note=f'صفحة PDF: {page+1} من {total}'
    self.previewq.put(('image',token,self.frame_image(img,note),meta+f'\n{RLM}{note}',key,note))
    return
   if ext=='.pdf' and PdfReader:
    reader=PdfReader(str(p));total=max(1,len(reader.pages));page=min(max(0,page),total-1);self.preview_page=page;txt=(reader.pages[page].extract_text() or '').strip()
    note=f'صفحة PDF نصية: {page+1} من {total}'
    img=self._text_image(p.name,note,(txt[:1500] if txt else 'هذه الصفحة لا تحتوي على نص قابل للاستخراج، أو أنها ممسوحة كصورة.').splitlines()[:22])
    self.previewq.put(('image',token,img,meta+f'\n{RLM}{note}',key,note));return
   if ext in ('.xlsx','.xlsm','.xltx','.xltm','.xls','.xlsb','.csv'):
    names,sheet_name,rows,start_row,total_rows,has_more,note=self.read_spreadsheet_preview(p,getattr(self,'excel_sheet_name',None),getattr(self,'excel_row_limit',150))
    self.previewq.put(('excel',token,str(p),meta+(f'\n{RLM}{note}' if note else ''),names,sheet_name,rows,start_row,total_rows,has_more,key));return
   if ext=='.docx' and Document:
    d=Document(str(p));lines=[x.text.strip() for x in d.paragraphs if x.text.strip()][:18]
    for tb in d.tables[:2]:
     for row in tb.rows[:5]:
      vals=[c.text.strip().replace('\n',' ') for c in row.cells if c.text.strip()]
      if vals:lines.append(' | '.join(vals[:5]))
    self.previewq.put(('image',token,self._text_image(p.name,'معاينة مستند Word',lines or ['المستند فارغ أو لا يحتوي على فقرات نصية ظاهرة.']),meta,key,''));return
   if ext in ('.txt','.md','.py','.json','.xml','.ini','.log','.lsp'):
    txt=p.read_text(encoding='utf-8',errors='replace').splitlines()[:22]
    self.previewq.put(('image',token,self._text_image(p.name,f'معاينة ملف نصي ({ext})',txt or ['الملف فارغ.']),meta,key,''));return
   if ext in ('.dwg','.dxf'):
    img,note=self._cad_preview(p,token)
    if token != getattr(self,'preview_token',0):return
    self.previewq.put(('image',token,img,meta+f'\n{RLM}{note}',key,note));return
   self.previewq.put(('image',token,self.make_card(p.name,classify(ext),'المعاينة المباشرة غير متاحة لهذا الامتداد؛ انقر مرتين لفتح الملف.'),meta,key,''))
  except Exception as e:
   self.previewq.put(('image',token,self.make_card(p.name,'تعذرت المعاينة',str(e)[:120]),meta,key,''))

 def frame_image(self,im,caption):
  w,h=im.size;canvas=Image.new('RGB',(max(440,w+24),h+52),(13,18,25));d=ImageDraw.Draw(canvas)
  d.rectangle((0,0,canvas.width-1,38),fill=(19,27,36),outline=(28,42,56));d.text((14,9),caption[:62],fill=(0,255,102),font=self._font(13,True))
  canvas.paste(im,((canvas.width-w)//2,44));d.rectangle((0,0,canvas.width-1,canvas.height-1),outline=(28,42,56),width=1);return canvas

 def make_card(self,title,subtitle,body,kind=None):
  im=Image.new('RGB',(520,390),(7,10,14));d=ImageDraw.Draw(im)
  d.rectangle((10,10,510,380),fill=(13,18,25),outline=(28,42,56),width=2)
  d.rectangle((10,10,510,76),fill=(19,27,36),outline=(0,255,102),width=1)
  d.text((24,26),str(subtitle)[:45],fill=(0,255,102),font=self._font(16,True))
  if kind=='folder':
   d.rectangle((195,108,325,192),fill=(19,27,36),outline=(0,229,255),width=2)
   d.rectangle((195,94,252,114),fill=(0,229,255),outline=(0,229,255),width=1)
   d.text((232,138),'[DIR]',fill=(0,229,255),font=self._font(18,True))
   y=218
  elif kind=='activity':
   d.rectangle((210,100,310,185),fill=(19,27,36),outline=(0,255,102),width=2)
   d.text((232,130),'[LOG]',fill=(0,255,102),font=self._font(18,True))
   y=210
  else:
   y=108
  for line in textwrap.wrap(str(title),width=30)[:3]:
   d.text((26,y),line,fill=(226,241,232),font=self._font(17,True));y+=32
  y+=12
  for line in textwrap.wrap(str(body),width=40)[:6]:
   d.text((26,y),line,fill=(94,118,106),font=self._font(13));y+=25
  return im

 def _text_image(self,title,subtitle,lines):
  im=Image.new('RGB',(660,540),(13,18,25));d=ImageDraw.Draw(im)
  d.rectangle((0,0,659,68),fill=(19,27,36),outline=(0,255,102),width=1);d.text((18,12),title[:48],fill=(0,255,102),font=self._font(15,True));d.text((18,40),subtitle[:62],fill=(0,229,255),font=self._font(11))
  y=84
  for line in lines[:20]:
   for sub in textwrap.wrap(line,width=64)[:2] or ['']:
    d.text((18,y),sub,fill=(226,241,232),font=self._font(12));y+=21
    if y>512:break
   if y>512:break
  d.rectangle((0,0,659,539),outline=(28,42,56),width=1)
  return im

 def _table_image(self,title,subtitle,rows):
  im=Image.new('RGB',(760,540),(13,18,25));d=ImageDraw.Draw(im)
  d.rectangle((0,0,759,66),fill=(19,27,36),outline=(0,255,102),width=1);d.text((16,11),title[:48],fill=(0,255,102),font=self._font(15,True));d.text((16,39),subtitle[:72],fill=(0,229,255),font=self._font(11))
  cols=max((len(r) for r in rows),default=1);cols=max(1,min(cols,7));cw=728//cols;rh=25;top=78
  for r_idx,row in enumerate(rows[:17]):
   for c_idx in range(cols):
    x1=16+c_idx*cw;y1=top+r_idx*rh;x2=x1+cw;y2=y1+rh
    fill=(19,27,36) if r_idx==0 else ((10,14,20) if r_idx%2 else (13,18,25))
    d.rectangle((x1,y1,x2,y2),fill=fill,outline=(28,42,56))
    val='' if c_idx>=len(row) or row[c_idx] is None else str(row[c_idx]).strip().replace('\n',' ')
    d.text((x1+6,y1+4),val[:18],fill=(0,255,102) if r_idx==0 else (226,241,232),font=self._font(11,r_idx==0))
  d.rectangle((0,0,759,539),outline=(28,42,56),width=1)
  return im

 def _cad_preview(self,p,token=None):
  ext=p.suffix.lower()
  ezdxf=None
  try:import ezdxf
  except ImportError:pass
  try:
   st=p.stat();cache_dir=LOG/'.preview_cache';cache_dir.mkdir(exist_ok=True);cache_key=hashlib.sha1(f'{p.resolve()}|{st.st_mtime_ns}|{st.st_size}'.encode('utf-8')).hexdigest();cached=cache_dir/f'{cache_key}.png'
   if cached.is_file():
    with Image.open(cached) as im:return im.convert('RGB').copy(),'معاينة CAD جاهزة من الذاكرة السريعة'
  except Exception:cached=None
  if ext=='.dxf' and ezdxf:
   try:dxf_size=p.stat().st_size
   except OSError:dxf_size=0
   if dxf_size>MAX_DXF_BYTES:
    return self.make_card(p.name,'DXF كبير الحجم',f'حجم الملف {sizefmt(dxf_size)} أكبر من حد المعاينة الآمن؛ انقر مرتين لفتحه في برنامج CAD.'),'ملف DXF كبير جدًا — تم تجاوز المعاينة المباشرة لحماية البرنامج'
   try:
    doc=ezdxf.readfile(str(p));msp=doc.modelspace();pts=[];segs=[]
    for e in msp:
     t=e.dxftype()
     if t=='LINE':
      a=(float(e.dxf.start.x),float(e.dxf.start.y));b=(float(e.dxf.end.x),float(e.dxf.end.y));segs.append((a,b));pts.extend((a,b))
     elif t in ('LWPOLYLINE','POLYLINE'):
      raw=[(float(pt[0]),float(pt[1])) for pt in (e.get_points() if t=='LWPOLYLINE' else [(v.dxf.location.x,v.dxf.location.y) for v in e.vertices])]
      for i in range(len(raw)-1):segs.append((raw[i],raw[i+1]))
      pts.extend(raw)
     elif t=='CIRCLE':
      cx,cy,r=float(e.dxf.center.x),float(e.dxf.center.y),float(e.dxf.radius);pts.extend([(cx-r,cy-r),(cx+r,cy+r)]);segs.append(('circle',cx,cy,r))
     if len(segs)>3500:break
    if pts:
     xs=[x for x,_ in pts];ys=[y for _,y in pts];minx,maxx=min(xs),max(xs);miny,maxy=min(ys),max(ys);spanx=max(1e-6,maxx-minx);spany=max(1e-6,maxy-miny)
     im=Image.new('RGB',(700,520),(7,10,14));d=ImageDraw.Draw(im)
     d.rectangle((0,0,699,58),fill=(19,27,36),outline=(0,255,102),width=1);d.text((16,16),f'[DXF_RENDER] {p.name[:42]}',fill=(0,255,102),font=self._font(14,True))
     def tr(pt):
      x=28+int((pt[0]-minx)/spanx*644);y=495-int((pt[1]-miny)/spany*410);return x,y
     for s in segs:
      if s[0]=='circle':
       _,cx,cy,r=s;x1,y1=tr((cx-r,cy+r));x2,y2=tr((cx+r,cy-r));d.ellipse((min(x1,x2),min(y1,y2),max(x1,x2),max(y1,y2)),outline=(0,229,255),width=1)
      else:d.line([tr(s[0]),tr(s[1])],fill=(0,255,102),width=1)
     if cached:
      try:im.save(cached,'PNG')
      except Exception:pass
     return im,f'تم رسم {len(segs)} عنصر هندسي من ملف DXF'
   except Exception as e:
    return self.make_card(p.name,'DXF',f'تعذر تحليل DXF: {str(e)[:90]}'),'تعذرت معاينة DXF'
  thumb,note=self._extract_dwg_thumbnail(p,token)
  if thumb:
   framed=self.frame_image(thumb,note)
   if cached and 'AutoCAD' in note:
    try:framed.save(cached,'PNG')
    except Exception:pass
   return framed,note
  return self.make_card(p.name,'لوحة AutoCAD DWG',note),note

 def _fit_embedded_image(self,raw,min_side=48):
  try:
   im=Image.open(io.BytesIO(raw));w,h=im.size
   if w<min_side or h<min_side or w*h>MAX_EMBEDDED_IMAGE_PIXELS:return None
   im.load();out=im.convert('RGB');out.thumbnail((900,750),Image.Resampling.BILINEAR)
   return out
  except Exception:return None

 def _extract_dwg_thumbnail(self,p,token=None):
  header_preview=None;header_note='معاينة DWG مضمنة من داخل الملف'
  try:
   # لا نقرأ ملف DWG كاملًا في الذاكرة (قد يتجاوز 100 ميجابايت)؛
   # نمسح أول 32 ميجابايت فقط حيث توجد رؤوس المقاطع والمعاينات المضمنة.
   with p.open('rb') as fh:data=fh.read(MAX_DWG_SCAN_BYTES)
   for sig,ext in ((b'\x89PNG\r\n\x1a\n','PNG'),(b'\xff\xd8\xff','JPEG')):
    idx=data.find(sig)
    while idx!=-1:
     out=self._fit_embedded_image(data[idx:idx+1_500_000])
     if out is not None:
      if max(out.size)>=360:return out,f'معاينة DWG مضمنة ({ext})'
      header_preview=out;break
     idx=data.find(sig,idx+4)
   if len(data)>=32 and data[:2]==b'AC' and header_preview is None:
    sentinel=bytes.fromhex('1F256D07D43628289D57CA3F9D44102B')
    pos=data.find(sentinel)
    candidates=[pos+16] if pos!=-1 else []
    try:candidates.append(int.from_bytes(data[13:17],'little'))
    except Exception:pass
    for start in candidates:
     if start<=0 or start+10>=len(data):continue
     try:
      count=data[start+4];cursor=start+5
      for _ in range(min(count,12)):
       if cursor+9>len(data):break
       code=data[cursor];offset=int.from_bytes(data[cursor+1:cursor+5],'little');size=int.from_bytes(data[cursor+5:cursor+9],'little');cursor+=9
       if offset<=0 or size<=40 or offset+size>len(data):continue
       chunk=data[offset:offset+size]
       if code==6 or chunk.startswith(b'\x89PNG\r\n\x1a\n'):
        out=self._fit_embedded_image(chunk,32)
        if out is not None:header_preview=out;header_note='معاينة DWG مضمنة (PNG)';break
       if code==2:
        bmp=chunk if chunk[:2]==b'BM' else b'BM'+(len(chunk)+14).to_bytes(4,'little')+b'\x00\x00\x00\x00'+int(54).to_bytes(4,'little')+chunk
        for raw in (bmp,chunk):
         out=self._fit_embedded_image(raw,32)
         if out is not None:
          header_preview=out;header_note='معاينة DWG مضمنة من رأس اللوحة';break
        if header_preview:break
      if header_preview:break
     except Exception:continue
  except Exception:pass
  try:dwg_size=p.stat().st_size
  except OSError:dwg_size=0
  if token is not None and token != getattr(self,'preview_token',0):
   return None,'تم إلغاء معاينة اللوحة السابقة'
  if dwg_size>MAX_DWG_PLOT_BYTES:
   acad_img,acad_note=None,'تم تجاوز الرسم عبر AutoCAD لأن ملف اللوحة كبير جدًا'
  else:
   acad_img,acad_note=self._plot_dwg_with_autocad(p,token)
  if acad_img:return acad_img,acad_note
  if header_preview is not None:
   if max(header_preview.size)<260:
    scale=max(2,min(3,360//max(1,max(header_preview.size))))
    header_preview=header_preview.resize((header_preview.width*scale,header_preview.height*scale),Image.Resampling.BICUBIC)
   return header_preview,header_note+(' — جودة المصغرة داخل هذا الملف منخفضة من المصدر' if max(header_preview.size)<420 else '')
  shell=self._windows_shell_thumbnail(p,512)
  if shell:return shell,'معاينة DWG عبر مصغرات Windows'
  version=''
  try:
   with p.open('rb') as f:version=f.read(6).decode('ascii',errors='ignore')
  except Exception:pass
  return None,f'هذا الملف ({version or "DWG"}) لا يحتوي على صورة معاينة مضمنة واضحـة، ولم تتوفر أداة رسم AutoCAD الخلفية ({acad_note}).'

 def _find_accoreconsole(self):
  cached=getattr(self,'_accoreconsole_path',None)
  if cached is not None:return cached if cached and cached.is_file() else None
  roots=[Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Autodesk',Path(os.environ.get('ProgramFiles(x86)','C:/Program Files (x86)'))/'Autodesk']
  found=[]
  for root in roots:
   if root.is_dir():
    try:found.extend(root.glob('AutoCAD */accoreconsole.exe'))
    except OSError:pass
  found=sorted(found,key=lambda x:str(x),reverse=True)
  self._accoreconsole_path=found[0] if found else False
  return found[0] if found else None

 def _plot_dwg_with_autocad(self,p,token=None):
  console=self._find_accoreconsole()
  if not console:return None,'accoreconsole غير موجود'
  fitz=None
  try:import fitz
  except ImportError:pass
  workdir=Path(tempfile.mkdtemp(prefix='rasd_dwg_'))
  try:
   if token is not None and token != getattr(self,'preview_token',0):return None,'تم إلغاء معاينة اللوحة السابقة'
   src=workdir/'input.dwg';out_png=workdir/'preview.png';out_pdf=workdir/'preview.pdf';scr=workdir/'render.scr'
   shutil.copy2(p,src)
   png_path=str(out_png).replace('\\','/');pdf_path=str(out_pdf).replace('\\','/')
   script='\n'.join([
    'FILEDIA 0','CMDDIA 0','BACKGROUNDPLOT 0','TILEMODE 1','_.ZOOM _E',
    f'_.PNGOUT "{png_path}" ','_.QUIT _Y',''
   ])
   scr.write_text(script,encoding='utf-8')
   flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
   proc=subprocess.Popen([str(console),'/i',str(src),'/s',str(scr),'/l','en-US'],cwd=str(workdir),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=flags)
   self.cad_preview_process=proc
   try:proc.wait(timeout=35)
   finally:
    if getattr(self,'cad_preview_process',None) is proc:self.cad_preview_process=None
   if out_png.is_file() and out_png.stat().st_size>200:
    with Image.open(out_png) as im:
     rendered=self._prepare_rendered_cad_image(im)
     if rendered:return rendered,'معاينة مرسومة بدقة عبر AutoCAD'
   if token is not None and token != getattr(self,'preview_token',0):return None,'تم إلغاء معاينة اللوحة السابقة'
   if fitz:
    pdf_layouts=[]
    for layout in ('Model','Layout1','Layout2'):
     candidate=workdir/f'preview_{layout}.pdf';cand_path=str(candidate).replace('\\','/')
     pdf_layouts.extend([
      f'_.-PLOT _Y "{layout}" "DWG To PDF.pc3" "ISO full bleed A3 (420.00 x 297.00 MM)" _M _L _E _F _C _Y "monochrome.ctb" _Y _N "{cand_path}" _N _Y',
      f'_.-PLOT _Y "{layout}" "AutoCAD PDF (General Documentation).pc3" "ISO full bleed A3 (420.00 x 297.00 MM)" _M _L _N _E _F _C _Y "." _Y _N "{cand_path}" _N _Y'
     ])
    scr.write_text('\n'.join(['FILEDIA 0','CMDDIA 0','BACKGROUNDPLOT 0',*pdf_layouts,'_.QUIT _Y','']),encoding='utf-8')
    if token is not None and token != getattr(self,'preview_token',0):return None,'تم إلغاء معاينة اللوحة السابقة'
    proc=subprocess.Popen([str(console),'/i',str(src),'/s',str(scr),'/l','en-US'],cwd=str(workdir),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=flags)
    self.cad_preview_process=proc
    try:proc.wait(timeout=45)
    finally:
     if getattr(self,'cad_preview_process',None) is proc:self.cad_preview_process=None
    if token is not None and token != getattr(self,'preview_token',0):return None,'تم إلغاء معاينة اللوحة السابقة'
    for candidate in sorted(workdir.glob('preview_*.pdf')):
     if candidate.stat().st_size<=400:continue
     doc=fitz.open(str(candidate))
     try:
      rect=doc[0].rect
      scale=min(1.8,2200.0/max(1.0,float(rect.width or 1.0)),2200.0/max(1.0,float(rect.height or 1.0)))
      pix=doc[0].get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False)
      im=Image.frombytes('RGB',[pix.width,pix.height],pix.samples);del pix
     finally:doc.close()
     rendered=self._prepare_rendered_cad_image(im)
     if rendered:return rendered,'معاينة PDF هندسية عبر AutoCAD'
   return None,'لم ينتج AutoCAD صورة لهذه اللوحة'
  except subprocess.TimeoutExpired:
   proc=getattr(self,'cad_preview_process',None)
   if proc and proc.poll() is None:
    try:proc.kill()
    except OSError:pass
   return None,'انتهت مهلة رسم اللوحة المعقدة'
  except Exception as e:
   return None,str(e)[:60]
  finally:
   shutil.rmtree(workdir,ignore_errors=True)

 def _prepare_rendered_cad_image(self,im):
  rgb=im.convert('RGB');bg=rgb.getpixel((0,0));diff=ImageChops.difference(rgb,Image.new('RGB',rgb.size,bg)).convert('L')
  bbox=diff.point(lambda p:255 if p>8 else 0).getbbox()
  if not bbox:return None
  pad=18;left=max(0,bbox[0]-pad);top=max(0,bbox[1]-pad);right=min(rgb.width,bbox[2]+pad);bottom=min(rgb.height,bbox[3]+pad)
  cropped=rgb.crop((left,top,right,bottom))
  if sum(bg)<120:cropped=ImageOps.invert(cropped)
  cropped.thumbnail((1100,850),Image.Resampling.BILINEAR)
  return cropped

 def _windows_shell_thumbnail(self,p,size=512):
  if os.name!='nt':return None
  try:
   from ctypes import wintypes
   class GUID(ctypes.Structure):
    _fields_=[('Data1',ctypes.c_ulong),('Data2',ctypes.c_ushort),('Data3',ctypes.c_ushort),('Data4',ctypes.c_ubyte*8)]
   class SIZE(ctypes.Structure):
    _fields_=[('cx',ctypes.c_long),('cy',ctypes.c_long)]
   class BITMAP(ctypes.Structure):
    _fields_=[('bmType',ctypes.c_long),('bmWidth',ctypes.c_long),('bmHeight',ctypes.c_long),('bmWidthBytes',ctypes.c_long),('bmPlanes',ctypes.c_ushort),('bmBitsPixel',ctypes.c_ushort),('bmBits',ctypes.c_void_p)]
   class BITMAPINFOHEADER(ctypes.Structure):
    _fields_=[('biSize',wintypes.DWORD),('biWidth', ctypes.c_long),('biHeight',ctypes.c_long),('biPlanes',wintypes.WORD),('biBitCount',wintypes.WORD),('biCompression',wintypes.DWORD),('biSizeImage',wintypes.DWORD),('biXPelsPerMeter',ctypes.c_long),('biYPelsPerMeter',ctypes.c_long),('biClrUsed',wintypes.DWORD),('biClrImportant',wintypes.DWORD)]
   class BITMAPINFO(ctypes.Structure):
    _fields_=[('bmiHeader',BITMAPINFOHEADER),('bmiColors',wintypes.DWORD*3)]
   ole32=ctypes.windll.ole32;shell32=ctypes.windll.shell32;gdi32=ctypes.windll.gdi32;user32=ctypes.windll.user32
   ole32.CoInitialize(None)
   try:
    iid=GUID(0xbcc18b79,0xba16,0x442f,(ctypes.c_ubyte*8)(0x80,0xc4,0x8a,0x59,0xc3,0x0c,0x46,0x3b))
    shell32.SHCreateItemFromParsingName.argtypes=[wintypes.LPCWSTR,ctypes.c_void_p,ctypes.POINTER(GUID),ctypes.POINTER(ctypes.c_void_p)]
    shell32.SHCreateItemFromParsingName.restype=ctypes.c_long
    item=ctypes.c_void_p()
    if shell32.SHCreateItemFromParsingName(str(p),None,ctypes.byref(iid),ctypes.byref(item))!=0 or not item:return None
    vtable=ctypes.cast(item,ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    get_image=ctypes.WINFUNCTYPE(ctypes.c_long,ctypes.c_void_p,SIZE,ctypes.c_int,ctypes.POINTER(wintypes.HBITMAP))(vtable[3])
    release=ctypes.WINFUNCTYPE(ctypes.c_ulong,ctypes.c_void_p)(vtable[2])
    hbmp=wintypes.HBITMAP()
    try:
     hr=get_image(item,SIZE(size,size),0x00000008,ctypes.byref(hbmp))
     if hr!=0 or not hbmp:hr=get_image(item,SIZE(size,size),0x00000000,ctypes.byref(hbmp))
     if hr!=0 or not hbmp:return None
     bmp=BITMAP()
     if gdi32.GetObjectW(hbmp,ctypes.sizeof(bmp),ctypes.byref(bmp))==0 or bmp.bmWidth<48 or bmp.bmHeight<48:return None
     bi=BITMAPINFO();bi.bmiHeader.biSize=ctypes.sizeof(BITMAPINFOHEADER);bi.bmiHeader.biWidth=bmp.bmWidth;bi.bmiHeader.biHeight=-bmp.bmHeight;bi.bmiHeader.biPlanes=1;bi.bmiHeader.biBitCount=32;bi.bmiHeader.biCompression=0
     buf=ctypes.create_string_buffer(bmp.bmWidth*bmp.bmHeight*4);hdc=user32.GetDC(0)
     try:gdi32.GetDIBits(hdc,hbmp,0,bmp.bmHeight,buf,ctypes.byref(bi),0)
     finally:user32.ReleaseDC(0,hdc)
     im=Image.frombuffer('RGBA',(bmp.bmWidth,bmp.bmHeight),buf,'raw','BGRA',0,1).convert('RGB')
     stat=ImageStat.Stat(im.convert('L'))
     if stat.stddev[0]<4.5:return None
     im.thumbnail((900,750),Image.Resampling.BILINEAR)
     return im
    finally:
     if hbmp:gdi32.DeleteObject(hbmp)
     release(item)
   finally:ole32.CoUninitialize()
  except Exception:
   return None

 def _font(self,size,bold=False):
  names=('segoeuib.ttf','arialbd.ttf','tahomabd.ttf','consolab.ttf') if bold else ('segoeui.ttf','tahoma.ttf','arial.ttf','consola.ttf')
  for name in names:
   for candidate in (Path('C:/Windows/Fonts')/name,Path(name)):
    try:return ImageFont.truetype(str(candidate),size)
    except Exception:pass
  return ImageFont.load_default()