# Rasd - معاينة ملفات الإكسل
from common import *
from update_utils import *
from storage import *

class ExcelPreviewMixin:
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
