# Rasd - سجل التغييرات وأيقونات أحداث النشاط داخل المستكشف
from common import *
from update_utils import *
from storage import *

class ExplorerActivityMixin:
 def refresh_activity_days_combo(self):
  if not hasattr(self, 'activity_days_box') or not self.activity_days_box.winfo_exists(): return
  try:
   with connect() as c:
    days = [r[0] for r in c.execute("SELECT DISTINCT substr(occurred_at, 1, 10) d FROM activity_log WHERE project=? AND d IS NOT NULL ORDER BY d DESC", (self.project,)).fetchall() if r[0]]
   vals = ['كل الأيام المسجلة'] + days
   self.activity_days_box.configure(values=vals)
   if self.activity_date_mode == 'custom' and self.activity_custom_date.get() in vals:
    self.activity_days_var.set(self.activity_custom_date.get())
   elif self.activity_date_mode == 'all':
    self.activity_days_var.set('كل الأيام المسجلة')
  except Exception: pass

 def _sync_activity_filter_buttons(self):
  mode = getattr(self, 'activity_date_mode', 'all')
  for m, b in getattr(self, 'activity_filter_btns', {}).items():
   if b.winfo_exists():
    b.configure(bg=BG_SELECTED if mode == m else BG_PANEL, fg=ACCENT_MATRIX if mode == m else FG_MUTED)
  if hasattr(self, 'activity_cal_btn') and self.activity_cal_btn.winfo_exists():
   if mode == 'custom' and self.activity_custom_date.get():
    self.activity_cal_btn.configure(text=RLM+f"🗓 {self.activity_custom_date.get()}", bg=BG_SELECTED, fg=ACCENT_MATRIX)
   else:
    self.activity_cal_btn.configure(text=RLM+'🗓 اختر يوم...', bg=BG_PANEL, fg=FG_PRIMARY)

 def set_activity_date_filter(self, mode, custom_date=None):
  self.activity_date_mode = mode
  if custom_date is not None:
   self.activity_custom_date.set(custom_date)
  self._sync_activity_filter_buttons()
  self.refresh_activity_days_combo()
  self.populate()

 def on_activity_day_combo(self, event=None):
  val = self.activity_days_var.get()
  if val == 'كل الأيام المسجلة' or not val:
   self.set_activity_date_filter('all')
  else:
   self.set_activity_date_filter('custom', val)

 def pick_activity_date(self):
  if not hasattr(self, '_task_pick_date'): return
  var = tk.StringVar(value=self.activity_custom_date.get() or date.today().isoformat())
  def on_change(*_):
   chosen = var.get().strip()
   if chosen: self.set_activity_date_filter('custom', chosen)
   else: self.set_activity_date_filter('all', '')
  var.trace_add('write', on_change)
  self._task_pick_date(var, parent=self)

 def delete_selected_activity_logs(self, tree=None):
  tree = tree or getattr(self, 'file_tree', None)
  if not tree or not tree.winfo_exists(): return
  sel = [iid for iid in tree.selection() if str(iid).startswith('activity:')]
  if not sel: return
  ids = [int(str(iid).split(':', 1)[1]) for iid in sel if str(iid).split(':', 1)[1].isdigit()]
  if not ids: return
  if len(ids) > 1 and not messagebox.askyesno('مسح من السجل', f'هل تريد مسح {len(ids):,} حدث محدد من سجل التغييرات؟', parent=self):
   return
  with connect() as c:
   c.executemany('DELETE FROM activity_log WHERE id=? AND project=?', [(i, self.project) for i in ids])
  self.refresh_activity_days_combo()
  self.populate()

 def clear_displayed_activity_log(self):
  tree = getattr(self, 'file_tree', None)
  if not tree or not tree.winfo_exists(): return
  all_iids = [iid for iid in tree.get_children('') if str(iid).startswith('activity:')]
  if not all_iids:
   return messagebox.showinfo('سجل التغييرات', 'لا توجد أحداث معروضة حالياً لمسحها.', parent=self)
  ids = [int(str(iid).split(':', 1)[1]) for iid in all_iids if str(iid).split(':', 1)[1].isdigit()]
  if not messagebox.askyesno('مسح السجل المعروض', f'هل أنت متأكد من مسح {len(ids):,} حدث معروض من سجل التغييرات نهائياً؟', parent=self):
   return
  with connect() as c:
   c.executemany('DELETE FROM activity_log WHERE id=? AND project=?', [(i, self.project) for i in ids])
  self.refresh_activity_days_combo()
  self.populate()

 def blank_icon_image(self):
  if not hasattr(self, '_blank_tree_icon'):
   im = Image.new('RGBA', (32, 24), (0, 0, 0, 0))
   self._blank_tree_icon = ImageTk.PhotoImage(im)
  return self._blank_tree_icon

 def activity_row_icon(self, r):
  target = r.get('path')
  action = str(r.get('action') or '')
  details = str(r.get('details') or '')
  general_actions = ('فتح قسم', 'تغيير فلتر الهاشتاج', 'تغيير فلتر النوع', 'تغيير فلتر التخصص', 'تغيير نطاق العرض', 'ترتيب الملفات', 'بحث', 'حفظ بحث', 'حذف بحث محفوظ', 'عرض تخصص', 'إعدادات النظام', 'أدوات مساحة العمل')
  if action in general_actions:
   return self.blank_icon_image()
  if target:
   p = Path(target)
   if p.is_dir() or 'مجلد' in action or action in ('فتح مشروع', 'إنشاء مشروع'):
    return self.file_icon_image(str(p), is_dir=True)
   if p.suffix:
    return self.file_icon_image(str(p), is_dir=False)
  m = re.search(r'([A-Za-z0-9_\-\u0600-\u06FF\s]+\.[A-Za-z0-9]{2,5})', details)
  if m:
   return self.file_icon_image(m.group(1), is_dir=False)
  if 'مجلد' in action:
   return self.file_icon_image('folder', is_dir=True)
  return self.blank_icon_image()
