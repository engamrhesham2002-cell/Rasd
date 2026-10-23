class App(tk.Tk):
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

 def preview_excel_worker(self,p,token,meta,sheet_name=None,key=None,start_row=1):
  try:
   p=Path(p);start_row=max(1,int(start_row));page_size=EXCEL_PREVIEW_PAGE_SIZE;max_columns=12;ext=p.suffix.lower();names=[];rows=[];total_rows=None;has_more=False
   if key is None:
    stat=p.stat();key=(str(p.resolve()),stat.st_mtime_ns,stat.st_size,start_row)
   if ext in ('.csv','.tsv'):
    name='CSV' if ext=='.csv' else 'TSV';names=[name]
    with p.open('r',encoding='utf-8-sig',errors='replace',newline='') as f:
     reader=csv.reader(f,delimiter='\t' if ext=='.tsv' else ',')
     for row_number,row in enumerate(reader,1):
      if row_number<start_row:continue
      if len(rows)>=page_size:has_more=True;break
      rows.append(row[:max_columns])
   elif ext=='.xlsb' and open_xlsb_workbook:
    with open_xlsb_workbook(str(p)) as book:
     names=list(book.sheets)
     if not names:raise RuntimeError('لا توجد أوراق في المصنف')
     name=sheet_name if sheet_name in names else names[0]
     with book.get_sheet(name) as sheet:
      for row_number,row in enumerate(sheet.rows(sparse=True),1):
       if row_number<start_row:continue
       if len(rows)>=page_size:has_more=True;break
       rows.append([cell.v if cell is not None else None for cell in row[:max_columns]])
   elif ext=='.xls' and xlrd:
    book=xlrd.open_workbook(str(p),on_demand=True)
    try:
     names=book.sheet_names()
     if not names:raise RuntimeError('لا توجد أوراق في المصنف')
     name=sheet_name if sheet_name in names else names[0];ws=book.sheet_by_name(name);total_rows=ws.nrows;end=min(total_rows,start_row+page_size-1)
     rows=[[ws.cell_value(r,c) for c in range(min(ws.ncols,max_columns))] for r in range(start_row-1,end)]
     has_more=end<total_rows
    finally:book.release_resources()
   elif openpyxl:
    wb=openpyxl.load_workbook(p,read_only=True,data_only=True)
    try:
     names=wb.sheetnames
     if not names:raise RuntimeError('لا توجد أوراق في المصنف')
     name=sheet_name if sheet_name in names else names[0];ws=wb[name];total_rows=ws.max_row or 0;end=min(total_rows,start_row+page_size)
     raw=[list(row) for row in ws.iter_rows(min_row=start_row,max_row=end,max_col=max_columns,values_only=True)] if total_rows and start_row<=total_rows else []
     rows=raw[:page_size];has_more=len(raw)>page_size
    finally:wb.close()
   else:raise RuntimeError('مكتبة قراءة Excel غير متاحة')
   last_row=start_row+len(rows)-1
   range_text=f'الصفوف {start_row:,}–{last_row:,}' if rows else f'لا توجد صفوف تبدأ من {start_row:,}'
   if total_rows is not None:range_text+=f' من {total_rows:,}'
   note=f'ورقة {name} · {range_text}'
   self.previewq.put(('excel',token,str(p),meta,names,name,rows,start_row,total_rows,has_more,key))
  except Exception as e:
   note=f'تعذر عرض ورقة Excel: {str(e)[:90]}'
   self.previewq.put(('image',token,self.make_card(Path(p).name,'Excel',note),meta+'\n\n'+note,key,note))

 def hide_excel_preview(self):
  frame=getattr(self,'excel_preview_frame',None)
  if frame is not None:
   try:
    if frame.winfo_exists():frame.destroy()
   except tk.TclError:pass
  self.excel_preview_frame=None
  try:self.preview_image.grid()
  except (tk.TclError,AttributeError):pass

 def render_excel_preview(self,path,meta,names,sheet_name,rows,start_row=1,total_rows=None,has_more=False,key=None):
  canvas=self.preview_image;parent=canvas.master;self.hide_excel_preview();canvas.grid_remove()
  self.preview_excel_path=Path(path);self.preview_excel_meta=meta;self.preview_excel_names=names;self.preview_excel_selected=sheet_name;self.excel_preview_start_row=start_row;self.excel_preview_total_rows=total_rows;self.excel_preview_has_more=has_more;self.excel_preview_key=key
  frame=tk.Frame(parent,bg='#eef2f5');frame.grid(row=1,column=0,sticky='nsew',padx=5,pady=5);frame.grid_rowconfigure(1,weight=1);frame.grid_columnconfigure(0,weight=1);self.excel_preview_frame=frame
  toolbar=tk.Frame(frame,bg='#dfe7ec');toolbar.grid(row=0,column=0,columnspan=2,sticky='ew',pady=(0,4))
  tk.Label(toolbar,text='Excel',bg='#dfe7ec',fg='#24744f',font=('Segoe UI',9,'bold')).pack(side='left',padx=7,pady=4)
  self.excel_formula=tk.StringVar(value='حدد خلية لعرض محتواها');self.excel_cell_name=tk.StringVar(value='—')
  tk.Entry(toolbar,textvariable=self.excel_cell_name,width=6,state='readonly',readonlybackground='#f5f7f8',relief='flat',justify='center',font=('Segoe UI',9)).pack(side='left',padx=(5,2),pady=3)
  tk.Entry(toolbar,textvariable=self.excel_formula,state='readonly',readonlybackground='white',relief='flat',font=('Segoe UI',9)).pack(side='left',fill='x',expand=True,padx=(2,6),pady=3)
  if len(names)>1:
   self.excel_sheet_box=ttk.Combobox(toolbar,values=names,state='readonly',width=12,justify='right',style='Office.TCombobox');self.excel_sheet_box.set(sheet_name);self.excel_sheet_box.pack(side='right',padx=4);self.excel_sheet_box.bind('<<ComboboxSelected>>',self.excel_sheet_changed)
  cols=max(1,max((len(r) for r in rows),default=1));letters=[self.excel_col_name(i+1) for i in range(cols)]
  tree=ttk.Treeview(frame,columns=letters,show='tree headings',selectmode='browse');tree.heading('#0',text='#');tree.column('#0',width=42,minwidth=42,stretch=False,anchor='center')
  for col in letters:tree.heading(col,text=col);tree.column(col,width=92,minwidth=70,stretch=False,anchor='w')
  ybar=ttk.Scrollbar(frame,orient='vertical',command=tree.yview);xbar=ttk.Scrollbar(frame,orient='horizontal',command=tree.xview);tree.configure(yscrollcommand=ybar.set,xscrollcommand=xbar.set)
  tree.grid(row=1,column=0,sticky='nsew');ybar.grid(row=1,column=1,sticky='ns');xbar.grid(row=2,column=0,sticky='ew')
  for offset,row in enumerate(rows):
   row_number=start_row+offset;values=[self.excel_cell(v) for v in row]+['']*(cols-len(row));tree.insert('','end',iid=str(row_number),text=str(row_number),values=values)
  tree.tag_configure('sheet_header',background='#e7eef3',foreground='#19394e')
  if start_row==1 and rows and tree.exists('1'):tree.item('1',tags=('sheet_header',))
  tree.bind('<<TreeviewSelect>>',lambda e:self.excel_cell_selected(tree));tree.bind('<ButtonRelease-1>',lambda e:self.excel_cell_selected(tree),add='+');tree.bind('<Next>',lambda e:(self.load_excel_preview_page(1),'break'));tree.bind('<Prior>',lambda e:(self.load_excel_preview_page(-1),'break'));self.excel_preview_tree=tree
  nav=tk.Frame(frame,bg='#e4ebef');nav.grid(row=3,column=0,columnspan=2,sticky='ew',pady=(4,0))
  self.excel_page_label=tk.StringVar(value='')
  self.excel_page_prev_button=ttk.Button(nav,text='← السابق',command=lambda:self.load_excel_preview_page(-1),state=('normal' if start_row>1 else 'disabled'));self.excel_page_prev_button.pack(side='left',padx=4,pady=3)
  self.excel_page_next_button=ttk.Button(nav,text='التالي →',command=lambda:self.load_excel_preview_page(1),state=('normal' if has_more else 'disabled'));self.excel_page_next_button.pack(side='left',padx=2,pady=3)
  last_row=start_row+len(rows)-1;range_text=f'الصفوف {start_row:,}–{last_row:,}' if rows else 'لا توجد بيانات في هذه الورقة'
  if total_rows is not None:range_text+=f' من {total_rows:,}'
  self.excel_page_label.set(range_text);tk.Label(nav,textvariable=self.excel_page_label,bg='#e4ebef',fg='#526b7c',font=('Segoe UI',8,'bold')).pack(side='right',padx=8)
  self.preview_meta.configure(text=meta+'\n\nمعاينة Excel تفاعلية · غيّر الورقة أو استخدم أزرار السابق والتالي للتنقل بين الصفوف.')

 def excel_col_name(self,n):
  out=''
  while n:n,rem=divmod(n-1,26);out=chr(65+rem)+out
  return out

 def excel_cell(self,value):
  if value is None:return ''
  if isinstance(value,float) and value.is_integer():return str(int(value))
  return str(value).replace('\\n',' ')[:180]

 def excel_cell_selected(self,tree):
  sel=tree.selection()
  if not sel:return
  row=int(sel[0]);col=tree.identify_column(tree.winfo_pointerx()-tree.winfo_rootx());idx=max(0,min(len(tree.item(sel[0],"values"))-1,int(col.lstrip("#") or 1)-1));self.excel_cell_name.set(f'{self.excel_col_name(idx+1)}{row}');self.excel_formula.set(str(tree.item(sel[0],"values")[idx]))

 def excel_sheet_changed(self,e=None):
  if not getattr(self,'preview_excel_path',None):return
  name=self.excel_sheet_box.get();self.preview_token+=1;token=self.preview_token
  self.preview_meta.configure(text=self.preview_excel_meta+'\n\nجارٍ تحميل الورقة…')
  self.preview_future=self.preview_executor.submit(self.preview_excel_worker,self.preview_excel_path,token,self.preview_excel_meta,name)

 def load_excel_preview_page(self,delta):
  if not getattr(self,'preview_excel_path',None) or (delta>0 and not self.excel_preview_has_more):return
  start=max(1,self.excel_preview_start_row+delta*EXCEL_PREVIEW_PAGE_SIZE)
  if start==self.excel_preview_start_row:return
  if self.preview_future and not self.preview_future.done():self.preview_future.cancel()
  self.preview_token+=1;token=self.preview_token
  if getattr(self,'excel_page_label',None):self.excel_page_label.set('جارٍ تحميل الصفوف…')
  self.preview_future=self.preview_executor.submit(self.preview_excel_worker,self.preview_excel_path,token,self.preview_excel_meta,self.preview_excel_selected,self.excel_preview_key,start)

 def preview_worker(self,p,token,meta,key):
  try:
   image,note=self.make_file_preview(p)
   image.thumbnail((1400,1000),Image.Resampling.BILINEAR)
  except Exception as e:image,note=self.make_card(p.name,p.suffix.upper() or 'FILE','تعذرت معاينة المحتوى في هذه الصيغة.'),str(e)[:100]
  self.previewq.put((token,image,meta+'\n\n'+note,key,note))

 def dwg_preview_worker(self,p,token,meta,key):
  try:
   self.cad_preview_path=Path(p).resolve()
   quick_image,quick_note=self.make_file_preview(p,allow_autocad=False)
   if quick_note.startswith(('معاينة من الملف المرتبط','معاينة من ملف اللوحة المرتبط')):
    quick_image.thumbnail((1400,1000),Image.Resampling.BILINEAR);image,note=quick_image,quick_note
    cache_path=self.dwg_preview_cache_path(p);cache_path.parent.mkdir(parents=True,exist_ok=True)
    if not cache_path.exists():image.save(cache_path,format='PNG',optimize=False,compress_level=2)
    self.previewq.put((token,image.copy(),meta+'\n\n'+note,key,note));return
   if quick_note.startswith('صورة مصغرة من Windows'):
    quick_image.thumbnail((1400,1000),Image.Resampling.BILINEAR)
    self.previewq.put(('image',token,quick_image.copy(),meta+'\n\nمعاينة سريعة من Windows · يجري تجهيز معاينة الرسم في الخلفية.'))
   image=self.make_autocad_dwg_preview(p)
   if image:note='معاينة لوحة DWG من AutoCAD · تحفظ مؤقتًا لتسريع العرض التالي'
   else:image,note=quick_image,quick_note
   image.thumbnail((1400,1000),Image.Resampling.BILINEAR)
   if 'لم تتوفر' not in note and 'لم يعثر' not in note and 'صورة مصغرة من Windows' not in note:
    cache_path=self.dwg_preview_cache_path(p);cache_path.parent.mkdir(parents=True,exist_ok=True)
    if not cache_path.exists():image.save(cache_path,format='PNG',optimize=False,compress_level=2)
  except Exception as e:image,note=self.make_card(p.name,'DWG','تعذرت معاينة الرسم في الوقت الحالي.'),f'تعذرت معاينة الرسم: {str(e)[:90]}'
  self.previewq.put((token,image,meta+'\n\n'+note,key,note))

 def make_card(self,title,kind,note):
  image=Image.new('RGB',(1200,560),'#f7fafc');d=ImageDraw.Draw(image);d.rounded_rectangle((38,35,1160,525),radius=22,fill='white',outline='#c8d7e2',width=3);d.rounded_rectangle((70,70,220,220),radius=20,fill='#0b7785');font=self._font(34,True);small=self._font(24);d.text((106,120),kind[:6],font=small,fill='white');d.text((260,90),title[:60],font=font,fill='#173b50');d.text((260,165),note[:100],font=small,fill='#667d8d');return image

 def _font(self,size,bold=False):
  path=Path(os.environ.get('WINDIR',r'C:\Windows'))/'Fonts'/('segoeuib.ttf' if bold else 'segoeui.ttf')
  try:return ImageFont.truetype(str(path),size)
  except OSError:return ImageFont.load_default()

 def _text_image(self,title,lines,kind):
  image=Image.new('RGB',(1200,620),'white');d=ImageDraw.Draw(image);d.rectangle((0,0,1200,62),fill='#e7eef3');d.text((22,14),title[:78],font=self._font(25,True),fill='#173b50');d.text((1090,18),kind,font=self._font(20,True),fill='#087e8b')
  y=82;regular=self._font(18);small=self._font(15)
  expanded=[]
  for line in lines:
   expanded.extend(textwrap.wrap(str(line).replace('\t','    '),width=118,break_long_words=True) or [''])
  for line in expanded[:27]:
   d.text((24,y),line,font=regular,fill='#29475a');y+=20
   if y>590:break
  d.rectangle((1,1,1198,618),outline='#c8d7e2',width=2);return image

 def _table_image(self,title,rows,kind):
  rows=[list(r)[:8] for r in rows[:22]];cols=max([len(r) for r in rows] or [1]);im=Image.new('RGB',(1200,560),'white');d=ImageDraw.Draw(im);head=self._font(18,True);font=self._font(15);d.rectangle((0,0,1200,48),fill='#e7eef3');d.text((18,10),title[:78],font=head,fill='#173b50');top=58;row_h=min(27,max(20,(480-top)//max(len(rows),1)));col_w=1200//cols
  for ri,row in enumerate(rows):
   y=top+ri*row_h;fill='#0b7785' if ri==0 else ('#f2f7f9' if ri%2==0 else 'white');d.rectangle((0,y,1200,y+row_h),fill=fill)
   for ci in range(cols):
    x=ci*col_w;d.rectangle((x,y,x+col_w,y+row_h),outline='#c8d7e2',width=1);value='' if ci>=len(row) or row[ci] is None else str(row[ci]).replace('\n',' ');limit=max(5,int(col_w/9));d.text((x+6,y+4),value[:limit]+('…' if len(value)>limit else ''),font=head if ri==0 else font,fill='white' if ri==0 else '#29475a')
  d.rectangle((1,1,1198,558),outline='#c8d7e2',width=2);return im

 def make_file_preview(self,p,allow_autocad=True):
  ext=p.suffix.lower()
  if ext in ('.png','.jpg','.jpeg','.bmp','.gif','.tif','.tiff'):
   with Image.open(p) as im:
    im.thumbnail((1400,1000),Image.Resampling.BILINEAR);return im.convert('RGB'),'معاينة الصورة'
  if ext=='.pdf' and fitz:
   with fitz.open(str(p)) as doc:
    page_index=max(0,min(self.preview_page,len(doc)-1));page=doc.load_page(page_index);rect=page.rect;scale=min(1.8,1800/max(rect.width,1),1400/max(rect.height,1));pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False,annots=False)
    with Image.open(io.BytesIO(pix.tobytes('png'))) as im:return im.convert('RGB'),f'صفحة {page_index+1} من {len(doc)} · PDF'
  if ext=='.pdf' and PdfReader:
   page=PdfReader(str(p)).pages[0];text=page.extract_text() or ''
   if text.strip():return self._text_image(p.name,text.splitlines(),'PDF'),'معاينة نص الصفحة الأولى'
   try:return Image.open(io.BytesIO(page.images[0].data)).convert('RGB'),'صورة مستخرجة من الصفحة الأولى'
   except Exception:return self.make_card(p.name,'PDF','صفحة مصورة؛ محتوى النص غير قابل للاستخراج.'),'معاينة الصفحة الأولى'
  if ext in ('.docx',) and Document:
   doc=Document(p);lines=[x.text for x in doc.paragraphs if x.text.strip()]
   for table in doc.tables[:2]:
    for row in table.rows[:12]:lines.append('  |  '.join(c.text.replace('\n',' ') for c in row.cells))
   return self._text_image(p.name,lines or ['المستند لا يحتوي نصًا قابلًا للمعاينة.'],'Word'),'معاينة محتوى المستند'
  if ext in ('.txt','.md','.log','.ini','.xml','.json','.html','.py','.sql'):
   lines=p.read_text(encoding='utf-8',errors='replace').splitlines();return self._text_image(p.name,lines,'TEXT'),'معاينة بداية الملف'
  if ext in ('.csv','.tsv'):
   with p.open('r',encoding='utf-8-sig',errors='replace',newline='') as f:rows=list(csv.reader(f,delimiter='\t' if ext=='.tsv' else ','))[:28]
   return self._text_image(p.name,['  |  '.join(row[:8]) for row in rows],'TABLE'),'معاينة أول الصفوف'
  if ext=='.dxf' and ezdxf:return self.make_dxf_preview(p)
  if ext=='.dwg':
   for side_ext in ('.pdf','.png','.jpg','.jpeg'):
    side=p.with_suffix(side_ext)
    if side.exists():
     image,note=self.make_file_preview(side);return image,f'معاينة من الملف المرتبط {side.name} · {note}'
    try:
     with connect() as c:
      candidates=[Path(r['path']) for r in c.execute("select path from files where project=? and lower(name)=lower(?) and lower(ext) in ('.pdf','.png','.jpg','.jpeg')",(self.project,p.stem+".pdf"))]
      if not candidates:
       candidates=[Path(r['path']) for r in c.execute("select path from files where project=? and lower(name) in (lower(?),lower(?),lower(?),lower(?)) and lower(ext) in ('.png','.jpg','.jpeg')",(self.project,p.stem+'.png',p.stem+'.jpg',p.stem+'.jpeg',p.stem+'.pdf'))]
     for side in candidates:
      if side.is_file():
       image,note=self.make_file_preview(side);return image,f'معاينة من ملف اللوحة المرتبط {side.name} · {note}'
    except Exception:pass
    if allow_autocad:
     cad_image=self.make_autocad_dwg_preview(p)
     if cad_image:return cad_image,'معاينة لوحة DWG من AutoCAD · تحفظ مؤقتًا لتسريع العرض التالي'
   shell=self.shell_thumbnail(p)
   if shell:return shell,'صورة مصغرة من Windows أو برنامج CAD المثبت'
   note='لم تتوفر معاينة مصغرة أو ملف لوحة مرتبط، ولم يتوفر AutoCAD للتحويل. يمكن فتح الرسم بالنقر المزدوج.'
   return self.make_card(p.name,'DWG',note),note
  shell=self.shell_thumbnail(p)
  if shell:return shell,'معاينة مصغرة من Windows أو البرنامج المرتبط بالملف'
  return self.make_card(p.name,ext[1:].upper() if ext else 'FILE',f'ملف {sizefmt(p.stat().st_size)} · معاينة النظام غير متاحة لهذه الصيغة.'),'معاينة معلومات الملف'

 def shell_thumbnail(self,p):
  if os.name!='nt':return None
  class GUID(ctypes.Structure):_fields_=[('Data1',ctypes.c_ulong),('Data2',ctypes.c_ushort),('Data3',ctypes.c_ushort),('Data4',ctypes.c_ubyte*8)]
  class SIZE(ctypes.Structure):_fields_=[('cx',ctypes.c_long),('cy',ctypes.c_long)]
  class HEADER(ctypes.Structure):_fields_=[('biSize',ctypes.c_uint32),('biWidth',ctypes.c_int32),('biHeight',ctypes.c_int32),('biPlanes',ctypes.c_ushort),('biBitCount',ctypes.c_ushort),('biCompression',ctypes.c_uint32),('biSizeImage',ctypes.c_uint32),('biXPelsPerMeter',ctypes.c_int32),('biYPelsPerMeter',ctypes.c_int32),('biClrUsed',ctypes.c_uint32),('biClrImportant',ctypes.c_uint32)]
  class INFO(ctypes.Structure):_fields_=[('bmiHeader',HEADER),('bmiColors',ctypes.c_uint32*3)]
  item=ctypes.c_void_p();bitmap=ctypes.c_void_p();hdc=None
  try:
   iid=GUID();ctypes.windll.ole32.CLSIDFromString('{bcc18b79-ba16-442f-80c4-8a59c30c463b}',ctypes.byref(iid))
   comhr=ctypes.windll.ole32.CoInitializeEx(None,2);com_initialized=comhr>=0
   create=ctypes.windll.shell32.SHCreateItemFromParsingName;create.argtypes=[ctypes.c_wchar_p,ctypes.c_void_p,ctypes.POINTER(GUID),ctypes.POINTER(ctypes.c_void_p)];create.restype=ctypes.c_long
   if create(str(p),None,ctypes.byref(iid),ctypes.byref(item))<0:return None
   vtable=ctypes.cast(item,ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
   get_image=ctypes.WINFUNCTYPE(ctypes.c_long,ctypes.c_void_p,SIZE,ctypes.c_uint,ctypes.POINTER(ctypes.c_void_p))(vtable[3])
   if get_image(item,SIZE(1100,540),0x01,ctypes.byref(bitmap))<0:return None
   class BITMAP(ctypes.Structure):_fields_=[('bmType',ctypes.c_long),('bmWidth',ctypes.c_long),('bmHeight',ctypes.c_long),('bmWidthBytes',ctypes.c_long),('bmPlanes',ctypes.c_ushort),('bmBitsPixel',ctypes.c_ushort),('bmBits',ctypes.c_void_p)]
   bm=BITMAP();ctypes.windll.gdi32.GetObjectW(bitmap,ctypes.sizeof(bm),ctypes.byref(bm));w,h=bm.bmWidth,abs(bm.bmHeight)
   if not w or not h:return None
   info=INFO();info.bmiHeader=HEADER(ctypes.sizeof(HEADER),w,-h,1,32,0,w*h*4,0,0,0,0);buf=(ctypes.c_ubyte*(w*h*4))();hdc=ctypes.windll.gdi32.CreateCompatibleDC(None)
   if not ctypes.windll.gdi32.GetDIBits(hdc,bitmap,0,h,buf,ctypes.byref(info),0):return None
   return Image.frombuffer('RGBA',(w,h),bytes(buf),'raw','BGRA',0,1).convert('RGB')
  except Exception:return None
  finally:
   if hdc:ctypes.windll.gdi32.DeleteDC(hdc)
   if bitmap:ctypes.windll.gdi32.DeleteObject(bitmap)
   if item:
    try:
     vt=ctypes.cast(item,ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents;release=ctypes.WINFUNCTYPE(ctypes.c_ulong,ctypes.c_void_p)(vt[2]);release(item)
    except Exception:pass
   if locals().get('com_initialized',False):ctypes.windll.ole32.CoUninitialize()

 def autocad_core_console_path(self):
  if getattr(self,'_autocad_core_resolved',False):return getattr(self,'_autocad_core_path',None)
  candidates=[];found=shutil.which('accoreconsole.exe')
  if found:candidates.append(Path(found))
  for base in (Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Autodesk',Path(os.environ.get('ProgramFiles(x86)','C:/Program Files (x86)'))/'Autodesk',Path('C:/2020')):
   try:candidates.extend(base.glob('AutoCAD */accoreconsole.exe'))
   except OSError:pass
  try:
   import winreg
   for hive_path in (r'SOFTWARE\Autodesk\AutoCAD',r'SOFTWARE\WOW6432Node\Autodesk\AutoCAD'):
    try:key=winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,hive_path)
    except OSError:continue
    with key:
     for i in range(winreg.QueryInfoKey(key)[0]):
      try:release=winreg.EnumKey(key,i);release_key=winreg.OpenKey(key,release)
      except OSError:continue
      with release_key:
       for j in range(winreg.QueryInfoKey(release_key)[0]):
        try:product=winreg.EnumKey(release_key,j);product_key=winreg.OpenKey(release_key,product)
        except OSError:continue
        with product_key:
         try:location=Path(winreg.QueryValueEx(product_key,'GlobUPILocation')[0])
         except OSError:continue
         for base in (location,location.parent,location.parent.parent):candidates.append(base/'accoreconsole.exe')
  except (ImportError,OSError):pass
  seen=set()
  for candidate in candidates:
   try:
    candidate=candidate.resolve()
    if str(candidate).casefold() not in seen and candidate.is_file():self._autocad_core_path=candidate;self._autocad_core_resolved=True;return candidate
    seen.add(str(candidate).casefold())
   except OSError:continue
  self._autocad_core_path=None;self._autocad_core_resolved=True;return None

 def short_windows_path(self,path):
  try:
   buf=ctypes.create_unicode_buffer(32768);fn=ctypes.windll.kernel32.GetShortPathNameW;fn.argtypes=[ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_uint];fn.restype=ctypes.c_uint;n=fn(str(path),buf,len(buf))
   if n and n<len(buf):return buf.value
  except Exception:pass
  return str(path)

 def crop_cad_preview(self,image):
  try:
   image=image.convert('RGB');w,h=image.size
   mask=ImageChops.difference(image,Image.new('RGB',(w,h),'white')).convert('L').point(lambda value:255 if value>20 else 0)
   box=mask.getbbox()
   if not box:return image
   x0,y0,x1,y1=box;pad=max(8,int(max(x1-x0,y1-y0)*.06));x0=max(0,x0-pad);x1=min(w,x1+pad);y0=max(0,y0-pad);y1=min(h,y1+pad)
   crop=image.crop((x0,y0,x1,y1));scale=min(w/max(crop.width,1),h/max(crop.height,1));size=(max(1,int(crop.width*scale)),max(1,int(crop.height*scale)))
   crop=crop.resize(size,Image.Resampling.BILINEAR);canvas=Image.new('RGB',(w,h),'white');canvas.paste(crop,((w-size[0])//2,(h-size[1])//2));return canvas
  except Exception:return image

 def make_autocad_dwg_preview(self,p):
  if fitz is None:return None
  core=self.autocad_core_console_path()
  if not core:return None
  temp_dwg=None;plot_log=p.parent/'plot.log';plot_log_existed=False;plot_log_data=None;plot_log_stat=None
  try:
   plot_log_existed=plot_log.is_file()
   if plot_log_existed:plot_log_data=plot_log.read_bytes();plot_log_stat=plot_log.stat()
   png=self.dwg_preview_cache_path(p);cache=png.parent;cache.mkdir(parents=True,exist_ok=True);key=png.stem
   if png.is_file():
    with Image.open(png) as im:return im.convert('RGB').copy()
   pdf=cache/(key+'.pdf');script=cache/(key+'.scr');fd,temp_name=tempfile.mkstemp(prefix='.officelog-preview-',suffix=p.suffix,dir=str(p.parent));os.close(fd);temp_dwg=Path(temp_name);shutil.copy2(p,temp_dwg)
   output_path=self.short_windows_path(pdf)
   commands=('FILEDIA','0','CMDDIA','0','EXPERT','5','_.ZOOM','_E','_.-PLOT','Y','Model','DWG To PDF.pc3','ANSI A (11.00 x 8.50 Inches)','Inches','Landscape','N','Extents','Fit','Center','Y','monochrome.ctb','N','Wireframe',f'"{output_path}"','N','Y','_.QUIT','N','')
   script.write_text('\n'.join(commands),encoding='mbcs')
   process=subprocess.Popen([str(core),'/i',str(temp_dwg.resolve()),'/s',str(script),'/l','en-US'],cwd=str(p.parent),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));self.cad_preview_process=process
   try:process.wait(timeout=75)
   except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)
   finally:
    if getattr(self,'cad_preview_process',None) is process:self.cad_preview_process=None
   if not pdf.is_file() or pdf.stat().st_size<2048:return None
   with fitz.open(str(pdf)) as document:
    if not len(document):return None
    page=document.load_page(0);rect=page.rect;scale=min(2.2,1800/max(rect.width,1),1300/max(rect.height,1));pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False,annots=False)
    with Image.open(io.BytesIO(pix.tobytes('png'))) as im:image=im.convert('RGB').copy()
   image=self.crop_cad_preview(image)
   image.thumbnail((1400,1000),Image.Resampling.LANCZOS)
   image.save(png,format='PNG',optimize=False,compress_level=2)
   cached=sorted(cache.glob('*.png'),key=lambda f:f.stat().st_mtime,reverse=True)
   for old in cached[250:]:
    try:old.unlink()
    except OSError:pass
   return image
  except Exception:return None
  finally:
   temp_dwg=locals().get('temp_dwg');temp_related=(temp_dwg.with_suffix('.bak'),temp_dwg.with_suffix('.dwl'),temp_dwg.with_suffix('.dwl2')) if temp_dwg else ()
   for temporary in (locals().get('pdf'),locals().get('script'),temp_dwg,*temp_related):
    if temporary:
     try:temporary.unlink(missing_ok=True)
     except OSError:pass
   try:
    if plot_log_existed:
     plot_log.write_bytes(plot_log_data);os.utime(plot_log,ns=(plot_log_stat.st_atime_ns,plot_log_stat.st_mtime_ns))
    else:plot_log.unlink(missing_ok=True)
   except OSError:pass

 def make_dxf_preview(self,p):
  doc=ezdxf.readfile(str(p));entities=list(doc.modelspace());points=[];shapes=[]
  for ent in entities:
   typ=ent.dxftype()
   try:
    if typ=='LINE':pts=[(ent.dxf.start.x,ent.dxf.start.y),(ent.dxf.end.x,ent.dxf.end.y)];shapes.append(('line',pts))
    elif typ in ('LWPOLYLINE','POLYLINE'):
     pts=[(v[0],v[1]) if typ=='LWPOLYLINE' else (v.dxf.location.x,v.dxf.location.y) for v in (ent.get_points('xy') if typ=='LWPOLYLINE' else ent.vertices)]
     if len(pts)>1:shapes.append(('poly',pts+[pts[0]] if ent.closed else pts))
    elif typ=='CIRCLE':
     c=ent.dxf.center;r=ent.dxf.radius;pts=[(c.x-r,c.y-r),(c.x+r,c.y+r)];shapes.append(('circle',[(c.x,c.y,r)]))
    elif typ=='ARC':
     c=ent.dxf.center;r=ent.dxf.radius;a0=ent.dxf.start_angle;a1=ent.dxf.end_angle
     if a1<a0:a1+=360
     pts=[(c.x+r*math.cos(math.radians(a)),c.y+r*math.sin(math.radians(a))) for a in [a0+(a1-a0)*i/32 for i in range(33)]];shapes.append(('line',pts))
    else:continue
    points.extend(pts)
   except Exception:continue
  if not points:return self.make_card(p.name,'DXF','لم يتم العثور على عناصر رسم قابلة للمعاينة.'),'معاينة الرسم'
  minx=min(x for x,y in points);maxx=max(x for x,y in points);miny=min(y for x,y in points);maxy=max(y for x,y in points);dx=max(maxx-minx,1e-6);dy=max(maxy-miny,1e-6);scale=min(1100/dx,480/dy);ox=(1200-dx*scale)/2;oy=(560-dy*scale)/2
  def xy(x,y):return (ox+(x-minx)*scale,560-(oy+(y-miny)*scale))
  im=Image.new('RGB',(1200,560),'white');d=ImageDraw.Draw(im);d.rectangle((1,1,1198,558),outline='#c8d7e2',width=2);d.rectangle((0,0,1200,42),fill='#e7eef3');d.text((18,10),p.name,font=self._font(18,True),fill='#173b50')
  for kind,pts in shapes:
   if kind=='circle':
    x,y,r=pts[0];cx,cy=xy(x,y);rr=r*scale;d.ellipse((cx-rr,cy-rr,cx+rr,cy+rr),outline='#087e8b',width=2)
   else:d.line([xy(x,y) for x,y in pts],fill='#087e8b',width=2)
  return im,'معاينة هندسية لعناصر DXF'

 def render_preview(self,image,meta):
  self.hide_excel_preview();self.preview_base=image.copy();self.preview_meta.configure(text=meta);self.paint_preview()

 def paint_preview(self):
  canvas=self.preview_image
  if not canvas.winfo_exists() or not getattr(self,'preview_base',None):return
  self.update_idletasks();max_w=max(240,canvas.winfo_width()-16);max_h=max(140,canvas.winfo_height()-16);im=self.preview_base.copy();im.thumbnail((max_w,max_h),Image.Resampling.LANCZOS)
  if getattr(self,'preview_zoom',1.0)!=1.0:im=im.resize((max(1,int(im.width*self.preview_zoom)),max(1,int(im.height*self.preview_zoom))),Image.Resampling.LANCZOS)
  self.preview_photo=ImageTk.PhotoImage(im);canvas.delete('all');self.preview_image_id=canvas.create_image(max(canvas.winfo_width(),im.width)//2,max(canvas.winfo_height(),im.height)//2,image=self.preview_photo,anchor='center');canvas.configure(scrollregion=(0,0,max(canvas.winfo_width(),im.width),max(canvas.winfo_height(),im.height)))

 def preview_pan_start(self,event):self.preview_pan=(event.x,event.y)

 def preview_pan_move(self,event):
  if not hasattr(self,'preview_pan') or not getattr(self,'preview_image_id',None):return
  dx=event.x-self.preview_pan[0];dy=event.y-self.preview_pan[1];self.preview_image.move(self.preview_image_id,dx,dy);self.preview_pan=(event.x,event.y)

 def preview_wheel(self,event):self.zoom_preview(.1 if event.delta>0 else -.1);return 'break'

 def zoom_preview(self,amount):
  self.preview_zoom=max(.35,min(3.0,getattr(self,'preview_zoom',1.0)+amount))
  if getattr(self,'preview_base',None):self.paint_preview()

 def change_pdf_page(self,amount):
  p=Path(getattr(self,'preview_current_path',''))
  if not p.is_file() or p.suffix.lower()!='.pdf':return
  try:
   if fitz:
    with fitz.open(str(p)) as doc:count=len(doc)
   elif PdfReader:count=len(PdfReader(str(p)).pages)
   else:return
   page=self.preview_page+amount
   if 0<=page<count:
    self.preview_page=page;tree=self.file_tree
    if hasattr(self,'search_page') and self.search_page.winfo_exists() and self.search_page.winfo_ismapped() and self.search_nb.tabs():tree=self.search_views.get(self.search_nb.tab(self.search_nb.select(),'text'),tree)
    if tree and tree.exists(str(p.resolve())):tree.selection_set(str(p.resolve()));self.preview_selected(tree)
  except Exception:pass

