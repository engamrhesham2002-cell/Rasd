# Rasd - معاينة ملفات Excel و CSV داخل نافذة المعاينة (ستايل التيرمينال الداكن)
from common import *
from update_utils import *
from storage import *

class ExcelPreviewMixin:
 def hide_excel_preview(self):
  self.excel_preview_active=False
  frame=getattr(self,'excel_preview_frame',None)
  if frame and frame.winfo_exists():frame.grid_remove()
  if hasattr(self,'preview_image') and self.preview_image.winfo_exists():self.preview_image.grid()

 def ensure_excel_preview_widgets(self):
  frame=getattr(self,'excel_preview_frame',None)
  if frame and frame.winfo_exists() and frame.master is self.preview_image.master:return frame
  host=self.preview_image.master
  frame=tk.Frame(host,bg=BG_PANEL,highlightbackground=BORDER_DIM,highlightthickness=1);frame.grid(row=1,column=0,sticky='nsew',padx=7,pady=7);frame.grid_rowconfigure(1,weight=1);frame.grid_columnconfigure(0,weight=1)
  top=tk.Frame(frame,bg=BG_HEADER);top.grid(row=0,column=0,columnspan=2,sticky='ew')
  tk.Label(top,text='الشيت:',bg=BG_HEADER,fg=ACCENT_MATRIX,font=(TERM_FONT,8,'bold')).pack(side='right',padx=(8,3),pady=5)
  self.excel_sheet_var=tk.StringVar(value='')
  self.excel_sheet_box=ttk.Combobox(top,textvariable=self.excel_sheet_var,state='readonly',width=16,justify='right',style='Office.TCombobox');self.excel_sheet_box.pack(side='right',padx=3,pady=4);self.excel_sheet_box.bind('<<ComboboxSelected>>',self.change_excel_sheet)
  self.excel_more_button=ttk.Button(top,text='[تحميل المزيد]',command=self.load_more_excel_rows);self.excel_more_button.pack(side='left',padx=4,pady=4)
  self.excel_info_label=tk.Label(top,text='',bg=BG_HEADER,fg=ACCENT_CYAN,font=(TERM_FONT,8));self.excel_info_label.pack(side='left',padx=4)
  self.excel_font_size=getattr(self,'excel_font_size',9)
  style=ttk.Style(self);style.configure('ExcelPreview.Treeview',rowheight=24,font=(TERM_FONT,self.excel_font_size),background=BG_PANEL,fieldbackground=BG_PANEL,foreground=FG_PRIMARY);style.configure('ExcelPreview.Treeview.Heading',font=(TERM_FONT,max(8,self.excel_font_size),'bold'),background=BG_HEADER,foreground=ACCENT_MATRIX,padding=(5,4))
  tree=ttk.Treeview(frame,show='headings',selectmode='browse',style='ExcelPreview.Treeview');tree.grid(row=1,column=0,sticky='nsew')
  ybar=ttk.Scrollbar(frame,orient='vertical',command=tree.yview);ybar.grid(row=1,column=1,sticky='ns')
  xbar=ttk.Scrollbar(frame,orient='horizontal',command=tree.xview);xbar.grid(row=2,column=0,sticky='ew')
  tree.configure(yscrollcommand=ybar.set,xscrollcommand=xbar.set)
  tree.bind('<Control-MouseWheel>',lambda e:(self.zoom_excel_preview(1 if e.delta>0 else -1),'break'))
  tree.bind('<Shift-MouseWheel>',lambda e:(tree.xview_scroll(-1 if e.delta>0 else 1,'units'),'break'))
  self.excel_preview_frame=frame;self.excel_preview_tree=tree;return frame

 def zoom_excel_preview(self,step):
  self.excel_font_size=min(15,max(7,getattr(self,'excel_font_size',9)+step))
  style=ttk.Style(self);style.configure('ExcelPreview.Treeview',rowheight=max(20,self.excel_font_size*2+6),font=(TERM_FONT,self.excel_font_size));style.configure('ExcelPreview.Treeview.Heading',font=(TERM_FONT,max(8,self.excel_font_size),'bold'))

 def change_excel_sheet(self,e=None):
  p=self.selected_path()
  if not p:return
  self.excel_sheet_name=self.excel_sheet_var.get();self.excel_row_limit=150;self.request_preview(p)

 def load_more_excel_rows(self):
  p=self.selected_path()
  if not p:return
  self.excel_row_limit=min(2000,getattr(self,'excel_row_limit',150)+250);self.request_preview(p)

 def excel_column_name(self,index):
  label='';n=index
  while n>0:n,rem=divmod(n-1,26);label=chr(65+rem)+label
  return label or 'A'

 def format_excel_cell(self,value):
  if value is None:return ''
  if isinstance(value,datetime):return value.strftime('%Y-%m-%d %H:%M') if (value.hour or value.minute) else value.strftime('%Y-%m-%d')
  if isinstance(value,float):return f'{value:,.2f}'.rstrip('0').rstrip('.') if abs(value)>=1000 or not value.is_integer() else str(int(value))
  return str(value).strip().replace('\n',' ')

 def read_spreadsheet_preview(self,p,requested_sheet=None,row_limit=150):
  ext=p.suffix.lower();rows=[];names=['بيانات'];sheet_name='بيانات';start_row=1;total_rows=0;has_more=False
  if ext=='.csv':
   raw=None
   for enc in ('utf-8-sig','cp1256','utf-8','latin-1'):
    try:
     with p.open('r',encoding=enc,errors='strict',newline='') as f:raw=list(csv.reader(f));break
    except Exception:continue
   if raw is None:
    with p.open('r',encoding='utf-8',errors='replace',newline='') as f:raw=list(csv.reader(f))
   non_empty=[idx for idx,r in enumerate(raw) if any(str(x or '').strip() for x in r)]
   if non_empty:
    first=non_empty[0];start_row=first+1;usable=raw[first:];total_rows=len(usable);has_more=total_rows>row_limit;rows=[[self.format_excel_cell(x) for x in r[:40]] for r in usable[:row_limit]]
   note=f'ملف CSV · {len(rows):,} صف معروض'
   return names,sheet_name,rows,start_row,total_rows,has_more,note
  if ext=='.xls':
   if not xlrd:raise RuntimeError('مكتبة xlrd غير متاحة لمعاينة ملفات XLS القديمة')
   book=xlrd.open_workbook(str(p),on_demand=True)
   try:
    names=list(book.sheet_names()) or ['Sheet1'];sheet_name=requested_sheet if requested_sheet in names else names[0];sh=book.sheet_by_name(sheet_name)
    first=None
    for r_idx in range(min(sh.nrows,5000)):
     vals=[sh.cell_value(r_idx,c_idx) for c_idx in range(min(sh.ncols,40))]
     if any(str(x or '').strip() for x in vals):
      if first is None:first=r_idx;start_row=r_idx+1
      if len(rows)<row_limit:rows.append([self.format_excel_cell(x) for x in vals])
      else:has_more=True;break
    total_rows=max(0,sh.nrows-(first or 0)) if first is not None else 0
   finally:
    try:book.release_resources()
    except Exception:pass
   return names,sheet_name,rows,start_row,total_rows,has_more,f'الشيت: {sheet_name} · {len(names)} شيت'
  if ext=='.xlsb':
   if not open_xlsb_workbook:raise RuntimeError('مكتبة pyxlsb غير متاحة لمعاينة ملفات XLSB')
   with open_xlsb_workbook(str(p)) as wb:
    names=list(wb.sheets) or ['Sheet1'];sheet_name=requested_sheet if requested_sheet in names else names[0]
    with wb.get_sheet(sheet_name) as sh:
     first=None
     for r_idx,row in enumerate(sh.rows()):
      vals=[cell.v for cell in row[:40]]
      if any(str(x or '').strip() for x in vals):
       if first is None:first=r_idx;start_row=r_idx+1
       total_rows+=1
       if len(rows)<row_limit:rows.append([self.format_excel_cell(x) for x in vals])
       else:has_more=True
      if r_idx>5000:break
   return names,sheet_name,rows,start_row,total_rows,has_more,f'الشيت: {sheet_name} · {len(names)} شيت'
  if not openpyxl:raise RuntimeError('مكتبة openpyxl غير متاحة لمعاينة ملفات Excel')
  wb=openpyxl.load_workbook(str(p),read_only=True,data_only=True)
  try:
   names=list(wb.sheetnames) or ['Sheet1']
   if requested_sheet in names:sheet_name=requested_sheet
   else:
    sheet_name=names[0]
    for candidate in names:
     ws_try=wb[candidate]
     if any(any(x is not None and str(x).strip()!='' for x in r[:25]) for r in ws_try.iter_rows(min_row=1,max_row=40,max_col=25,values_only=True)):sheet_name=candidate;break
   ws=wb[sheet_name];first=None
   for r_idx,row in enumerate(ws.iter_rows(min_row=1,max_row=5000,max_col=40,values_only=True),start=1):
    if any(x is not None and str(x).strip()!='' for x in row):
     if first is None:first=r_idx;start_row=r_idx
     total_rows+=1
     if len(rows)<row_limit:rows.append([self.format_excel_cell(x) for x in row])
     else:has_more=True
  finally:wb.close()
  return names,sheet_name,rows,start_row,total_rows,has_more,f'الشيت: {sheet_name} · {len(names)} شيت'

 def render_excel_preview(self,path,meta,names,sheet_name,rows,start_row,total_rows,has_more,key=None):
  self.preview_image.grid_remove();frame=self.ensure_excel_preview_widgets();frame.grid();self.excel_preview_active=True
  self.excel_sheet_box.configure(values=names);self.excel_sheet_var.set(sheet_name);self.excel_sheet_name=sheet_name
  if has_more:self.excel_more_button.pack(side='left',padx=4,pady=4)
  else:self.excel_more_button.pack_forget()
  tree=self.excel_preview_tree;tree.delete(*tree.get_children())
  trimmed=[]
  max_col=0
  for r in rows:
   last=0
   for idx,val in enumerate(r):
    if str(val).strip()!='':last=idx+1
   max_col=max(max_col,last);trimmed.append(r)
  max_col=max(1,min(max_col or 1,40))
  header_idx=0
  for idx,r in enumerate(trimmed[:10]):
   non_empty=[str(x).strip() for x in r[:max_col] if str(x).strip()]
   if len(non_empty)>=2:header_idx=idx;break
  headers=trimmed[header_idx][:max_col] if trimmed else []
  columns=['row_num']+[f'c{i}' for i in range(1,max_col+1)]
  tree.configure(columns=columns)
  tree.heading('row_num',text='#');tree.column('row_num',width=44,minwidth=38,stretch=False,anchor='center')
  font=tkfont.Font(family=TERM_FONT,size=getattr(self,'excel_font_size',9))
  for i in range(1,max_col+1):
   col_id=f'c{i}';col_letter=self.excel_column_name(i);head_val=str(headers[i-1]).strip() if i-1<len(headers) else ''
   title=f'{head_val[:22]} ({col_letter})' if head_val and head_val!=col_letter else col_letter
   sample=[title]+[str(r[i-1])[:36] for r in trimmed[:60] if i-1<len(r) and str(r[i-1]).strip()]
   width=min(240,max(78,max((font.measure(s) for s in sample),default=70)+22))
   tree.heading(col_id,text=title);tree.column(col_id,width=width,minwidth=64,stretch=False,anchor='e')
  tree.tag_configure('header',background='#0F291E',foreground=ACCENT_MATRIX)
  tree.tag_configure('even',background=BG_PANEL,foreground=FG_PRIMARY)
  tree.tag_configure('odd',background=BG_ALT_ROW,foreground=FG_PRIMARY)
  if not trimmed:
   tree.insert('','end',values=('—','هذا الشيت لا يحتوي على بيانات ظاهرة',*(['']*(max_col-1))),tags=('even',))
  else:
   for offset,row in enumerate(trimmed):
    vals=[row[i] if i<len(row) else '' for i in range(max_col)]
    tag='header' if offset==header_idx else ('odd' if offset%2 else 'even')
    tree.insert('','end',values=(start_row+offset,*vals),tags=(tag,))
  shown=len(trimmed);self.excel_info_label.configure(text=f'{shown:,} صف × {max_col} عمود'+(f' من {total_rows:,}' if total_rows>shown else ''))
  self.preview_meta.configure(text=meta)