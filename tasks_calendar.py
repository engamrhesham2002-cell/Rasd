# tasks_calendar.py - تقويم متكامل على نمط Google Calendar:
# عروض الشهر/الأسبوع/اليوم/الأجندة، شريط جانبي، تقويم مصغّر، تقويمات ملوّنة،
# سحب وإفلات، تغيير المدة، مواعيد متكررة، فروق توقيت، وتنبيهات.
from common import *
from storage import *
from theme import mix, readable_accent

import ui_dialogs
import calendar_core as core
import calendar_store as store
from calendar_dialog import CalendarDialogMixin

WEEKDAY_NAMES = ('الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت')
WEEKDAY_SHORT = ('ح', 'ن', 'ث', 'ر', 'خ', 'ج', 'س')
MONTH_NAMES = core.MONTH_NAMES_AR


def _sunday_index(value):
    """ترتيب اليوم بحيث الأحد = 0 (بداية الأسبوع)."""
    return (value.weekday() + 1) % 7


def _start_of_week(value):
    return value - timedelta(days=_sunday_index(value))


class TasksCalendarMixin(CalendarDialogMixin):
    # ------------------------------------------------------------------
    # الشاشة والبناء الأساسي
    # ------------------------------------------------------------------
    def show_task_calendar(self, project=None, initial_date=None):
        try:
            with connect() as c:
                for col in ('subtasks', 'recurrence'):
                    try:
                        c.execute(f'ALTER TABLE tasks ADD COLUMN {col} TEXT')
                    except sqlite3.OperationalError:
                        pass
        except sqlite3.Error:
            pass
        store.ensure_calendar_schema()
        self.task_scope = str(project or '')
        self.task_rollover_token = getattr(self, 'task_rollover_token', 0) + 1
        rollover_token = self.task_rollover_token
        self.task_calendar_scope = str(project or '')
        self.task_calendar_date = initial_date or date.today()
        self.task_calendar_view = getattr(self, 'task_calendar_view', 'month')
        if self.task_calendar_view not in ('month', 'week', 'day', 'agenda'):
            self.task_calendar_view = 'month'
        self.task_calendar_active = True
        self.task_calendar_selected_id = None
        self.task_calendar_mini_date = self.task_calendar_date.replace(day=1)
        self.task_calendar_drag_state = None
        self._cal_initial_scroll_done = False
        self._cal_saved_y = None
        self._task_rollover_elapsed()
        self.clear()
        self.configure(bg=BG_VOID)
        self.title('Rasd // Calendar')

        head = self.header('التقويم والمهام')
        if project:
            ttk.Button(head, text=RLM + '← الرجوع للمشروع',
                       command=self.build_explorer).pack(side='right', padx=5, pady=12)
            ttk.Button(head, text=RLM + '☑ مهام المشروع',
                       command=lambda: self.show_tasks(project)).pack(side='right', padx=5, pady=12)
        else:
            ttk.Button(head, text=RLM + '← الرجوع للمشاريع',
                       command=self.show_home).pack(side='right', padx=5, pady=12)
            ttk.Button(head, text=RLM + '☑ قائمة المهام',
                       command=lambda: self.show_tasks(None)).pack(side='right', padx=5, pady=12)

        top = tk.Frame(self, bg=BG_VOID)
        top.pack(fill='x', padx=16, pady=(10, 6))
        self._calendar_build_topbar(top)

        body = tk.Frame(self, bg=BG_VOID)
        body.pack(fill='both', expand=True, padx=16, pady=(0, 12))
        body.grid_rowconfigure(0, weight=1)
        rtl = is_rtl()
        sidebar_col = 1 if rtl else 0
        main_col = 0 if rtl else 1
        body.grid_columnconfigure(main_col, weight=1)
        body.grid_columnconfigure(sidebar_col, weight=0)

        sidebar = tk.Frame(body, bg=BG_PANEL, width=248,
                           highlightbackground=BORDER_DIM, highlightthickness=1)
        sidebar.grid(row=0, column=sidebar_col, sticky='nsew', padx=(0, 8) if rtl else (8, 0))
        sidebar.grid_propagate(False)
        self.task_calendar_sidebar = sidebar
        tk.Button(sidebar, text=RLM + '＋ إنشاء', command=self._calendar_create_clicked,
                  bg=BG_HEADER, fg=ACCENT_MATRIX, activebackground=ACCENT_MATRIX,
                  activeforeground=BG_VOID, relief='solid', borderwidth=1,
                  font=(TERM_FONT, 11, 'bold'), padx=14, pady=8,
                  cursor='hand2').pack(fill='x', padx=12, pady=(12, 10))
        self.task_calendar_mini_frame = tk.Frame(sidebar, bg=BG_PANEL)
        self.task_calendar_mini_frame.pack(fill='x', padx=8, pady=(0, 8))
        tk.Frame(sidebar, bg=BORDER_DIM, height=1).pack(fill='x', padx=12, pady=4)
        calendars_head = tk.Frame(sidebar, bg=BG_PANEL)
        calendars_head.pack(fill='x', padx=12, pady=(4, 2))
        tk.Label(calendars_head, text=RLM + 'تقويماتي', bg=BG_PANEL, fg=ACCENT_CYAN,
                 font=(TERM_FONT, 10, 'bold')).pack(side='right')
        tk.Button(calendars_head, text='＋', command=self._calendar_add_calendar,
                  bg=BG_PANEL, fg=ACCENT_MATRIX, activebackground=BG_SELECTED,
                  relief='flat', font=(TERM_FONT, 11, 'bold'), cursor='hand2').pack(side='left')
        self.task_calendar_calendars_frame = tk.Frame(sidebar, bg=BG_PANEL)
        self.task_calendar_calendars_frame.pack(fill='x', padx=6, pady=2)

        self.task_calendar_main = tk.Frame(body, bg=BG_PANEL,
                                           highlightbackground=BORDER_DIM, highlightthickness=1)
        self.task_calendar_main.grid(row=0, column=main_col, sticky='nsew')
        self.task_calendar_main.grid_rowconfigure(0, weight=1)
        self.task_calendar_main.grid_columnconfigure(0, weight=1)
        self.task_calendar_main.bind('<Configure>', self._calendar_on_resize)
        # إبقاء الاسم القديم متوافقًا مع بقية الوحدات.
        self.task_calendar_canvas = self.task_calendar_main

        self._task_calendar_draw(preserve_scroll=False)
        self.after(30000, lambda: self._task_rollover_tick(rollover_token))

    def _calendar_build_topbar(self, parent):
        nav = tk.Frame(parent, bg=BG_VOID)
        nav.pack(side='right')
        tk.Button(nav, text=RLM + 'اليوم', command=lambda: self._task_calendar_goto(date.today()),
                  bg=BG_HEADER, fg=ACCENT_MATRIX, activebackground=ACCENT_MATRIX,
                  activeforeground=BG_VOID, relief='solid', borderwidth=1,
                  font=(TERM_FONT, 9, 'bold'), padx=12, pady=5,
                  cursor='hand2').pack(side='right', padx=(0, 8))
        tk.Button(nav, text='‹', command=lambda: self._task_calendar_shift(-1),
                  bg=BG_HEADER, fg=FG_PRIMARY, activebackground=BG_SELECTED,
                  relief='solid', borderwidth=1, font=(TERM_FONT, 12, 'bold'),
                  padx=10, pady=2, cursor='hand2').pack(side='right', padx=2)
        tk.Button(nav, text='›', command=lambda: self._task_calendar_shift(1),
                  bg=BG_HEADER, fg=FG_PRIMARY, activebackground=BG_SELECTED,
                  relief='solid', borderwidth=1, font=(TERM_FONT, 12, 'bold'),
                  padx=10, pady=2, cursor='hand2').pack(side='right', padx=2)
        self.task_calendar_title = tk.StringVar()
        tk.Label(nav, textvariable=self.task_calendar_title, bg=BG_VOID, fg=ACCENT_CYAN,
                 font=(TERM_FONT, 15, 'bold')).pack(side='right', padx=14)

        views = tk.Frame(parent, bg=BG_VOID)
        views.pack(side='left')
        self._calendar_view_buttons = {}
        for label, mode in (('شهر', 'month'), ('أسبوع', 'week'), ('يوم', 'day'), ('أجندة', 'agenda')):
            button = tk.Button(views, text=RLM + label,
                               command=lambda m=mode: self._task_calendar_set_view(m),
                               bg=BG_HEADER, fg=FG_MUTED, activebackground=BG_SELECTED,
                               relief='solid', borderwidth=1, font=(TERM_FONT, 9),
                               padx=10, pady=5, cursor='hand2')
            button.pack(side='left', padx=2)
            self._calendar_view_buttons[mode] = button
        tk.Button(views, text=RLM + '＋ إنشاء', command=self._calendar_create_clicked,
                  bg=BG_HEADER, fg=ACCENT_MATRIX, activebackground=ACCENT_MATRIX,
                  activeforeground=BG_VOID, relief='solid', borderwidth=1,
                  font=(TERM_FONT, 9, 'bold'), padx=12, pady=5,
                  cursor='hand2').pack(side='left', padx=(10, 0))

    # ------------------------------------------------------------------
    # التنقل والعرض
    # ------------------------------------------------------------------
    def _calendar_create_clicked(self):
        now = datetime.now()
        start_minutes = min(23 * 60 + 30, ((now.hour * 60 + now.minute) // 30 + 1) * 30)
        end_minutes = min(24 * 60, start_minutes + 60)
        self._calendar_event_dialog(
            initial_date=self.task_calendar_date,
            initial_start=core.minutes_to_hhmm(start_minutes),
            initial_end=core.minutes_to_hhmm(end_minutes))

    def _task_calendar_set_view(self, mode):
        self.task_calendar_view = mode
        self._task_calendar_draw(preserve_scroll=False)

    def _calendar_on_resize(self, event=None):
        width = event.width if event is not None else self.task_calendar_main.winfo_width()
        if abs(int(width) - int(getattr(self, '_cal_last_width', 0))) < 30:
            return
        self._cal_last_width = width
        job = getattr(self, '_cal_resize_job', None)
        if job:
            try:
                self.after_cancel(job)
            except tk.TclError:
                pass
        self._cal_resize_job = self.after(300, lambda: self._task_calendar_draw(preserve_scroll=True)
                                         if getattr(self, 'task_calendar_drag_state', None) is None else None)

    def _task_calendar_goto(self, target):
        self.task_calendar_date = target if isinstance(target, date) else date.fromisoformat(str(target))
        self.task_calendar_mini_date = self.task_calendar_date.replace(day=1)
        self._task_calendar_draw(preserve_scroll=False)

    def _task_calendar_shift(self, step):
        d = self.task_calendar_date
        mode = self.task_calendar_view
        try:
            if mode == 'month':
                month_index = d.year * 12 + (d.month - 1) + int(step)
                year, month = divmod(month_index, 12)
                self.task_calendar_date = date(year, month + 1, 1)
            elif mode == 'week':
                self.task_calendar_date = d + timedelta(days=7 * step)
            elif mode == 'agenda':
                self.task_calendar_date = d + timedelta(days=30 * step)
            else:
                self.task_calendar_date = d + timedelta(days=step)
        except ValueError:
            return
        self.task_calendar_mini_date = self.task_calendar_date.replace(day=1)
        self._task_calendar_draw(preserve_scroll=False)

    def _task_calendar_select_task(self, task_id):
        """توافقية: تُستدعى من بقية الوحدات بعد تعديل مهمة معروضة."""
        try:
            self.task_calendar_selected_id = int(task_id)
        except (TypeError, ValueError):
            self.task_calendar_selected_id = None
        self._task_calendar_draw(preserve_scroll=True)

    def _task_calendar_hide_preview(self):
        # لم يعد هناك لوحة معاينة منفصلة؛ نُبقي الدالة للتوافق.
        return

    # ------------------------------------------------------------------
    # الرسم الرئيسي
    # ------------------------------------------------------------------
    def _task_calendar_draw(self, preserve_scroll=True):
        if not getattr(self, 'task_calendar_active', False):
            return
        if not hasattr(self, 'task_calendar_main') or not self.task_calendar_main.winfo_exists():
            return
        body_canvas = getattr(self, '_cal_surface', None)
        if preserve_scroll and body_canvas is not None and body_canvas.winfo_exists():
            try:
                self._cal_saved_y = body_canvas.yview()[0]
            except tk.TclError:
                pass
        elif not preserve_scroll:
            self._cal_saved_y = None
        self._cal_surface = None
        for child in self.task_calendar_main.winfo_children():
            child.destroy()
        self._calendar_update_view_buttons()
        self._calendar_rebuild_sidebar()

        d = self.task_calendar_date
        view = self.task_calendar_view
        if view == 'month':
            grid_start = d.replace(day=1) - timedelta(days=_sunday_index(d.replace(day=1)))
            range_start = grid_start
            range_end = grid_start + timedelta(days=41)
        elif view == 'week':
            range_start = _start_of_week(d)
            range_end = range_start + timedelta(days=6)
        elif view == 'day':
            range_start = range_end = d
        else:
            range_start = d
            range_end = d + timedelta(days=29)

        try:
            items = store.load_items(range_start, range_end, self.task_calendar_scope or None)
        except (sqlite3.Error, ValueError):
            items = []
        grouped = store.group_items_by_date(items, range_start, range_end)
        self._cal_grouped = grouped
        self._cal_range = (range_start, range_end)

        title = self._calendar_title_text(view, d.replace(day=1) if view == 'month' else range_start, range_end)
        self.task_calendar_title.set(RLM + title)

        try:
            if view == 'month':
                self._calendar_draw_month(grid_start, grouped)
            elif view in ('week', 'day'):
                span = [range_start + timedelta(days=i) for i in range((range_end - range_start).days + 1)]
                self._calendar_draw_timeline(span, grouped)
            else:
                span = [range_start + timedelta(days=i) for i in range(30)]
                self._calendar_draw_agenda(span, grouped)
        except tk.TclError:
            pass

    def _calendar_title_text(self, view, start, end):
        if view == 'month':
            return f'{MONTH_NAMES[start.month - 1]} {start.year}'
        if view == 'week':
            if start.year != end.year:
                return f'{start.day} {MONTH_NAMES[start.month - 1]} {start.year} – {end.day} {MONTH_NAMES[end.month - 1]} {end.year}'
            if start.month != end.month:
                return f'{start.day} {MONTH_NAMES[start.month - 1]} – {end.day} {MONTH_NAMES[end.month - 1]} {start.year}'
            return f'{start.day} – {end.day} {MONTH_NAMES[start.month - 1]} {start.year}'
        if view == 'day':
            return f'{WEEKDAY_NAMES[_sunday_index(start)]} {start.day} {MONTH_NAMES[start.month - 1]} {start.year}'
        return f'الأجندة · {start.day} {MONTH_NAMES[start.month - 1]} {start.year}'

    def _calendar_update_view_buttons(self):
        for mode, button in getattr(self, '_calendar_view_buttons', {}).items():
            active = mode == self.task_calendar_view
            try:
                button.configure(bg=BG_SELECTED if active else BG_HEADER,
                                 fg=ACCENT_MATRIX if active else FG_MUTED,
                                 font=(TERM_FONT, 9, 'bold' if active else 'normal'))
            except tk.TclError:
                pass

    # ------------------------------------------------------------------
    # الشريط الجانبي: تقويم مصغّر + قائمة التقويمات
    # ------------------------------------------------------------------
    def _calendar_rebuild_sidebar(self):
        self._calendar_rebuild_mini()
        self._calendar_rebuild_calendar_list()

    def _calendar_rebuild_mini(self):
        frame = getattr(self, 'task_calendar_mini_frame', None)
        if frame is None or not frame.winfo_exists():
            return
        for child in frame.winfo_children():
            child.destroy()
        if not hasattr(self, 'task_calendar_mini_date'):
            self.task_calendar_mini_date = self.task_calendar_date.replace(day=1)
        mini = self.task_calendar_mini_date.replace(day=1)
        head = tk.Frame(frame, bg=BG_PANEL)
        head.pack(fill='x', pady=(4, 2))
        tk.Button(head, text='›', command=lambda: self._calendar_mini_shift(-1),
                  bg=BG_PANEL, fg=FG_MUTED, activebackground=BG_SELECTED, relief='flat',
                  font=(TERM_FONT, 10, 'bold'), cursor='hand2').pack(side='left', padx=2)
        tk.Button(head, text='‹', command=lambda: self._calendar_mini_shift(1),
                  bg=BG_PANEL, fg=FG_MUTED, activebackground=BG_SELECTED, relief='flat',
                  font=(TERM_FONT, 10, 'bold'), cursor='hand2').pack(side='left', padx=2)
        tk.Label(head, text=RLM + f'{MONTH_NAMES[mini.month - 1]} {mini.year}',
                 bg=BG_PANEL, fg=ACCENT_CYAN, font=(TERM_FONT, 9, 'bold')).pack(side='right', padx=4)

        grid = tk.Frame(frame, bg=BG_PANEL)
        grid.pack(fill='x')
        rtl = is_rtl()
        for visual in range(7):
            logical = 6 - visual if rtl else visual
            tk.Label(grid, text=RLM + WEEKDAY_SHORT[logical], bg=BG_PANEL, fg=FG_MUTED,
                     font=(TERM_FONT, 7, 'bold')).grid(row=0, column=visual, sticky='ew', pady=1)
            grid.grid_columnconfigure(visual, weight=1, uniform='mini')
        first_offset = _sunday_index(mini)
        start_day = mini - timedelta(days=first_offset)
        today = date.today()
        selected = self.task_calendar_date
        for index in range(42):
            current = start_day + timedelta(days=index)
            row = 1 + index // 7
            logical = index % 7
            visual = (6 - logical) if rtl else logical
            in_month = current.month == mini.month
            bg = BG_PANEL
            fg = FG_PRIMARY if in_month else FG_MUTED
            if current == today:
                bg = BG_SELECTED
                fg = ACCENT_MATRIX
            label = tk.Label(grid, text=str(current.day), bg=bg, fg=fg,
                             font=(TERM_FONT, 8, 'bold' if current == today else 'normal'),
                             cursor='hand2', width=2)
            if current == selected:
                label.configure(relief='solid', borderwidth=1, highlightbackground=ACCENT_CYAN)
            label.grid(row=row, column=visual, sticky='nsew', padx=1, pady=1)
            label.bind('<Button-1>', lambda _e, target=current: self._task_calendar_goto(target))

    def _calendar_mini_shift(self, step):
        mini = getattr(self, 'task_calendar_mini_date', self.task_calendar_date.replace(day=1))
        month_index = mini.year * 12 + (mini.month - 1) + int(step)
        year, month = divmod(month_index, 12)
        self.task_calendar_mini_date = date(year, month + 1, 1)
        self._calendar_rebuild_mini()

    def _calendar_rebuild_calendar_list(self):
        frame = getattr(self, 'task_calendar_calendars_frame', None)
        if frame is None or not frame.winfo_exists():
            return
        for child in frame.winfo_children():
            child.destroy()
        try:
            rows = store.calendar_rows()
        except sqlite3.Error:
            rows = []
        for row in rows:
            line = tk.Frame(frame, bg=BG_PANEL)
            line.pack(fill='x', pady=1)
            variable = tk.BooleanVar(value=bool(int(row['visible'] or 0)))
            check = tk.Checkbutton(line, variable=variable, bg=BG_PANEL, activebackground=BG_PANEL,
                                   selectcolor=BG_VOID, bd=0, highlightthickness=0,
                                   command=lambda cid=row['id'], var=variable: self._calendar_toggle_visible(cid, var))
            check.pack(side='right', padx=(2, 0))
            tk.Label(line, text='', bg=row['color'] or ACCENT_CYAN, width=2,
                     relief='solid', borderwidth=1).pack(side='right', padx=4)
            tk.Label(line, text=RLM + str(row['name']), bg=BG_PANEL, fg=FG_PRIMARY,
                     font=(TERM_FONT, 9), anchor='e').pack(side='right', fill='x', expand=True)

    def _calendar_toggle_visible(self, calendar_id, variable):
        try:
            store.set_calendar_visible(calendar_id, variable.get())
        except sqlite3.Error:
            pass
        self._task_calendar_draw(preserve_scroll=True)

    def _calendar_add_calendar(self):
        name = ui_dialogs.ask_string(self, 'إضافة تقويم', 'اسم التقويم الجديد:')
        if not name:
            return
        chosen = colorchooser.askcolor(color='#3B82F6', parent=self, title='لون التقويم')
        color = (chosen[1] if chosen and chosen[1] else '#3B82F6')
        try:
            store.add_calendar(name, color)
        except (ValueError, sqlite3.Error) as exc:
            messagebox.showwarning('إضافة تقويم', str(exc), parent=self)
            return
        self._task_calendar_draw(preserve_scroll=True)

    # ------------------------------------------------------------------
    # عرض الشهر
    # ------------------------------------------------------------------
    def _calendar_draw_month(self, grid_start, grouped):
        host = tk.Frame(self.task_calendar_main, bg=BG_PANEL)
        host.grid(row=0, column=0, sticky='nsew')
        host.grid_columnconfigure(0, weight=1)
        host.grid_rowconfigure(1, weight=1)
        header = tk.Frame(host, bg=BG_HEADER)
        header.grid(row=0, column=0, sticky='ew')
        for visual in range(7):
            logical = 6 - visual if is_rtl() else visual
            tk.Label(header, text=RLM + WEEKDAY_NAMES[logical], bg=BG_HEADER, fg=ACCENT_CYAN,
                     font=(TERM_FONT, 9, 'bold')).grid(row=0, column=visual, sticky='ew', padx=1, pady=5)
            header.grid_columnconfigure(visual, weight=1, uniform='calhdr')
        grid = tk.Frame(host, bg=BORDER_DIM)
        grid.grid(row=1, column=0, sticky='nsew')
        for visual in range(7):
            grid.grid_columnconfigure(visual, weight=1, uniform='calcol')
        for row in range(6):
            grid.grid_rowconfigure(row, weight=1, uniform='calrow')
        today = date.today()
        selected = self.task_calendar_date
        for index in range(42):
            current = grid_start + timedelta(days=index)
            row, logical = divmod(index, 7)
            visual = (6 - logical) if is_rtl() else logical
            in_month = current.month == selected.month and current.year == selected.year
            bg = BG_PANEL if in_month else BG_ALT_ROW
            cell = tk.Frame(grid, bg=bg, highlightbackground=BORDER_DIM, highlightthickness=1,
                            cursor='hand2')
            cell.grid(row=row, column=visual, sticky='nsew', padx=1, pady=1)
            cell.grid_propagate(False)
            head = tk.Frame(cell, bg=bg)
            head.pack(fill='x')
            day_color = ACCENT_MATRIX if current == today else (FG_PRIMARY if in_month else FG_MUTED)
            day_label = tk.Label(head, text=str(current.day), bg=bg, fg=day_color,
                                 font=(TERM_FONT, 9, 'bold' if current == today else 'normal'),
                                 cursor='hand2')
            day_label.pack(side='right', padx=4)
            add_label = tk.Label(head, text='＋', bg=bg, fg=FG_MUTED, font=(TERM_FONT, 8),
                                 cursor='hand2')
            add_label.pack(side='left', padx=3)
            for widget in (cell, head, day_label, add_label):
                widget.bind('<Button-1>', lambda _e, target=current: self._calendar_create_for_date(target))

            body = tk.Frame(cell, bg=bg, cursor='hand2')
            body.pack(fill='both', expand=True, padx=2, pady=(0, 2))
            body.bind('<Button-1>', lambda _e, target=current: self._calendar_create_for_date(target))
            day_items = grouped.get(current.isoformat(), [])
            max_chips = 3
            for item in day_items[:max_chips]:
                chip = self._calendar_month_chip(body, item, bg)
                chip.pack(fill='x', pady=1)
            if len(day_items) > max_chips:
                extra = tk.Label(body, text=RLM + f'+{len(day_items) - max_chips}',
                                 bg=bg, fg=FG_MUTED, font=(TERM_FONT, 7), anchor='e')
                extra.pack(fill='x', padx=2)
                extra.bind('<Button-1>', lambda _e, target=current: self._task_calendar_goto(target))

    def _calendar_month_chip(self, parent, item, cell_bg):
        color, chip_bg, text_color = self._calendar_item_colors(item)
        title = str(item.get('title') or '')
        if item.get('completed'):
            title = '✓ ' + title
        if item['all_day']:
            text = title
        else:
            text = f"{item['start'].strftime('%H:%M')}  {title}"
        label = tk.Label(parent, text=RLM + text, bg=chip_bg, fg=text_color,
                         font=(TERM_FONT, 7, 'bold' if item['source'] == 'event' else 'normal'),
                         anchor='e', justify='right', padx=3, pady=1,
                         relief='solid', borderwidth=0, cursor='hand2')
        label.configure(wraplength=150)
        label.bind('<Button-1>', lambda _e, current=item: self._calendar_open_item(current))
        return label

    def _calendar_create_for_date(self, target):
        self._calendar_event_dialog(initial_date=target, initial_start='09:00', initial_end='10:00')
        return 'break'

    # ------------------------------------------------------------------
    # أدوات الألوان والعناصر
    # ------------------------------------------------------------------
    def _calendar_item_colors(self, item):
        color = item.get('color') or ACCENT_CYAN
        if item.get('completed'):
            return color, mix(BG_PANEL, FG_MUTED, 0.12), FG_MUTED
        strength = 0.24 if item.get('source') == 'event' else 0.16
        return color, mix(BG_PANEL, color, strength), readable_accent(color, BG_PANEL)

    def _calendar_open_item(self, item):
        try:
            if item.get('source') == 'task':
                row = item.get('raw')
                if row:
                    self._task_task_dialog(row=row,
                                           project_locked=bool(self.task_calendar_scope),
                                           project=self.task_calendar_scope or None)
                return 'break'
            self._calendar_event_dialog(
                event_id=item.get('event_id'),
                occurrence={'start': item['start'], 'end': item['end'],
                            'occurrence_date': item['occurrence_date'],
                            'rule_date': item.get('rule_date') or item['occurrence_date'],
                            'override': item.get('override') or {}},
                item=item)
        except (sqlite3.Error, ValueError) as exc:
            messagebox.showerror('التقويم', str(exc), parent=self)
        return 'break'

    # ------------------------------------------------------------------
    # عرض الأسبوع/اليوم (الخط الزمني)
    # ------------------------------------------------------------------
    def _calendar_draw_timeline(self, span, grouped):
        host = tk.Frame(self.task_calendar_main, bg=BG_PANEL)
        host.grid(row=0, column=0, sticky='nsew')
        host.grid_columnconfigure(0, weight=1)
        host.grid_rowconfigure(2, weight=1)

        rtl = is_rtl()
        visual_span = list(reversed(span)) if rtl else list(span)
        gutter = 58
        count = max(1, len(visual_span))
        available = max(self.task_calendar_main.winfo_width(), self.winfo_width() - 310, 720)
        col_width = max(88, int((available - gutter) / count))
        total_width = gutter + col_width * count
        header_h = 50

        header = tk.Canvas(host, height=header_h, bg=BG_HEADER, highlightthickness=0)
        header.grid(row=0, column=0, sticky='ew')
        has_all_day = any(item['all_day'] for day in span for item in grouped.get(day.isoformat(), []))
        all_day_h = 40 if has_all_day else 0
        all_day = None
        if has_all_day:
            all_day = tk.Canvas(host, height=all_day_h, bg=BG_ALT_ROW, highlightthickness=0)
            all_day.grid(row=1, column=0, sticky='ew')

        body = tk.Canvas(host, bg=BG_PANEL, highlightthickness=0)
        body.grid(row=2, column=0, sticky='nsew')
        scroll = ttk.Scrollbar(host, orient='vertical', command=body.yview)
        scroll.grid(row=2, column=1, sticky='ns')
        body.configure(yscrollcommand=scroll.set)
        self._cal_surface = body
        self._cal_visual_span = visual_span
        self._cal_geometry = {'gutter': gutter, 'col_width': col_width,
                              'total_width': total_width, 'header_h': header_h,
                              'all_day_h': all_day_h}
        body._sync_yscroll = lambda units: body.yview_scroll(units, 'units')

        def header_click(event):
            x = header.canvasx(event.x)
            if x < gutter:
                return
            visual = int((x - gutter) // col_width)
            if 0 <= visual < len(visual_span):
                self._calendar_create_for_date(visual_span[visual])

        header.bind('<Button-1>', header_click)

        def timeline_click(event):
            x = body.canvasx(event.x)
            y = body.canvasy(event.y)
            if x < gutter:
                return
            visual = int((x - gutter) // col_width)
            if not 0 <= visual < len(visual_span):
                return
            minutes = self._calendar_round_minutes(y)
            minutes = max(0, min(23 * 60 + 45, minutes))
            start = core.minutes_to_hhmm(minutes)
            end = core.minutes_to_hhmm(min(minutes + 60, 24 * 60))
            self._calendar_event_dialog(initial_date=visual_span[visual],
                                        initial_start=start, initial_end=end)

        body.bind('<Button-1>', timeline_click)

        # --- رأس الأيام ---
        header.delete('all')
        header.configure(scrollregion=(0, 0, total_width, header_h))
        header.create_rectangle(0, 0, total_width, header_h, fill=BG_HEADER, outline='')
        header.create_text(gutter // 2, header_h // 2,
                           text=core.local_timezone_label(), fill=FG_MUTED,
                           font=(MONO_FONT, 6), width=gutter - 6, justify='center')
        today = date.today()
        for visual, day in enumerate(visual_span):
            x0 = gutter + visual * col_width
            if day == today:
                header.create_rectangle(x0 + 1, 1, x0 + col_width - 1, header_h - 1,
                                        fill=BG_SELECTED, outline=ACCENT_MATRIX)
            header.create_text(x0 + col_width / 2, 16, text=RLM + WEEKDAY_NAMES[_sunday_index(day)],
                               fill=ACCENT_CYAN if day == today else FG_MUTED,
                               font=(TERM_FONT, 8, 'bold'))
            header.create_text(x0 + col_width / 2, 35, text=str(day.day),
                               fill=ACCENT_MATRIX if day == today else FG_PRIMARY,
                               font=(TERM_FONT, 14, 'bold'))

        # --- شريط طول اليوم ---
        if all_day is not None:
            all_day.delete('all')
            all_day.configure(scrollregion=(0, 0, total_width, all_day_h))
            all_day.create_rectangle(0, 0, total_width, all_day_h, fill=BG_ALT_ROW, outline='')
            all_day.create_text(gutter // 2, all_day_h // 2, text=RLM + 'كل اليوم',
                                fill=FG_MUTED, font=(TERM_FONT, 7, 'bold'))
            for visual, day in enumerate(visual_span):
                x0 = gutter + visual * col_width
                if visual:
                    all_day.create_line(x0, 0, x0, all_day_h, fill=BORDER_DIM)
                day_all_day = [item for item in grouped.get(day.isoformat(), []) if item['all_day']]
                for index, item in enumerate(day_all_day[:2]):
                    color, chip_bg, text_color = self._calendar_item_colors(item)
                    y0 = 4 + index * 17
                    tag = f'allday{visual}_{index}'
                    all_day.create_rectangle(x0 + 3, y0, x0 + col_width - 3, y0 + 15,
                                             fill=chip_bg, outline=color, tags=(tag,))
                    all_day.create_text(x0 + col_width - 6, y0 + 7, text=RLM + str(item['title']),
                                        anchor='e', fill=text_color, font=(TERM_FONT, 7),
                                        width=col_width - 14, tags=(tag,))
                    handler = lambda event, current=item: self._calendar_item_quick_open(current)
                    all_day.tag_bind(tag, '<Button-1>', handler)
                if len(day_all_day) > 2:
                    all_day.create_text(gutter + visual * col_width + col_width / 2,
                                        all_day_h - 6, text=f'+{len(day_all_day) - 2}',
                                        fill=FG_MUTED, font=(TERM_FONT, 7))

        # --- جسم الخط الزمني ---
        body.delete('all')
        minutes_total = 24 * 60
        body.configure(scrollregion=(0, 0, total_width, minutes_total))
        body.create_rectangle(0, 0, total_width, minutes_total, fill=BG_PANEL, outline='')
        for visual, day in enumerate(visual_span):
            x0 = gutter + visual * col_width
            if day == today:
                body.create_rectangle(x0, 0, x0 + col_width, minutes_total,
                                      fill=BG_SELECTED, outline='')
        for hour in range(25):
            y = min(minutes_total, hour * 60)
            body.create_line(gutter, y, total_width, y, fill=BORDER_DIM)
        for half in range(48):
            if half % 2 == 0:
                continue
            y = half * 30
            body.create_line(gutter, y, total_width, y, fill=BG_HOVER, dash=(1, 4))
        body.create_rectangle(0, 0, gutter, minutes_total, fill=BG_HEADER, outline='')
        for hour in range(24):
            body.create_text(gutter - 6, hour * 60 + 3, text=f'{hour:02d}:00', anchor='ne',
                             fill=ACCENT_CYAN, font=(MONO_FONT, 7, 'bold'))
        for visual in range(1, len(visual_span)):
            x = gutter + visual * col_width
            body.create_line(x, 0, x, minutes_total, fill=BORDER_DIM)

        # خط الوقت الحالي
        now = datetime.now()
        if now.date() in visual_span:
            visual = visual_span.index(now.date())
            x0 = gutter + visual * col_width
            y = now.hour * 60 + now.minute
            body.create_line(x0, y, x0 + col_width, y, fill=ACCENT_DANGER, width=2)
            body.create_oval(x0 - 3, y - 3, x0 + 3, y + 3, fill=ACCENT_DANGER, outline='')

        # المواعيد
        for visual, day in enumerate(visual_span):
            day_items = [item for item in grouped.get(day.isoformat(), []) if not item['all_day']]
            if not day_items:
                continue
            blocks = []
            for item in day_items:
                start_min = max(0, min(23 * 60 + 45, int(item['start_min'])))
                end_min = max(start_min + 15, min(24 * 60, int(item['end_min'])))
                blocks.append({'item': item, 'start_min': start_min, 'end_min': end_min})
            core.layout_overlaps(blocks)
            for index, block in enumerate(blocks):
                item = block['item']
                lane = int(block.get('lane', 0))
                lanes = max(1, int(block.get('lanes', 1)))
                x0 = gutter + visual * col_width + 3
                width = (col_width - 6) / lanes
                left = x0 + lane * width
                top = block['start_min']
                bottom = block['end_min']
                self._calendar_draw_timeline_item(body, item, left, top, width, bottom,
                                                  f'cal{visual}_{index}')

        # استعادة موضع التمرير: نطبّقها فورًا ثم نعيد المحاولة بعد ظهور الحجم الحقيقي
        # لأن yview_moveto قبل اكتمال التخطيط لا يحرّك شيئًا.
        saved = self._cal_saved_y
        if saved is None and not self._cal_initial_scroll_done:
            saved = (7 * 60) / minutes_total
        self._cal_initial_scroll_done = True
        if saved is None:
            saved = (7 * 60) / minutes_total

        def apply_scroll():
            self._calendar_restore_timeline_scroll(saved)

        apply_scroll()
        self.after_idle(apply_scroll)
        self.after(120, apply_scroll)

    def _calendar_restore_timeline_scroll(self, saved):
        try:
            surface = getattr(self, '_cal_surface', None)
            if saved is not None and surface is not None and surface.winfo_exists():
                surface.yview_moveto(min(1.0, max(0.0, saved)))
        except tk.TclError:
            pass

    def _calendar_draw_timeline_item(self, canvas, item, left, top, width, bottom, tag):
        color, chip_bg, text_color = self._calendar_item_colors(item)
        height = max(16, bottom - top)
        if item.get('completed'):
            outline = FG_MUTED
            fill = mix(BG_PANEL, FG_MUTED, 0.10)
        else:
            outline = color
            fill = chip_bg
        canvas.create_rectangle(left, top, left + width, bottom,
                                fill=fill, outline=outline, width=1, tags=(tag,))
        canvas.create_rectangle(left, top, left + 3, bottom,
                                fill=color if not item.get('completed') else FG_MUTED,
                                outline='', tags=(tag,))
        title = str(item.get('title') or '')
        if item.get('completed'):
            title = '✓ ' + title
        if height >= 30:
            text = f"{item['start'].strftime('%H:%M')}  {title}"
        else:
            text = title
        canvas.create_text(left + 7, top + 3, text=RLM + text, anchor='nw',
                           fill=text_color, font=(TERM_FONT, 8, 'bold' if item['source'] == 'event' else 'normal'),
                           width=max(20, width - 10), tags=(tag,))
        if height >= 48 and item.get('location'):
            canvas.create_text(left + 7, top + 20, text=RLM + str(item['location']), anchor='nw',
                               fill=FG_MUTED, font=(TERM_FONT, 7),
                               width=max(20, width - 10), tags=(tag,))
        canvas.tag_bind(tag, '<ButtonPress-1>',
                        lambda event, current=item, t=tag: self._calendar_timeline_press(event, current, t))
        canvas.tag_bind(tag, '<B1-Motion>', self._calendar_timeline_motion)
        canvas.tag_bind(tag, '<ButtonRelease-1>', self._calendar_timeline_release)

    # ------------------------------------------------------------------
    # السحب والإفلات وتغيير المدة
    # ------------------------------------------------------------------
    def _calendar_round_minutes(self, minutes, step=15):
        try:
            value = int(round(float(minutes) / step) * step)
        except (TypeError, ValueError):
            return 0
        return max(0, min(24 * 60, value))

    def _calendar_timeline_press(self, event, item, tag):
        canvas = event.widget
        bbox = canvas.bbox(tag)
        if not bbox:
            return 'break'
        y = canvas.canvasy(event.y)
        mode = 'resize' if y >= bbox[3] - 7 else 'move'
        self.task_calendar_drag_state = {
            'item': item,
            'canvas': canvas,
            'tag': tag,
            'mode': mode,
            'press_x': event.x_root,
            'press_y': event.y_root,
            'moved': False,
            'grab_offset': max(0.0, y - bbox[1]),
            'start_min': int(item['start_min']),
            'end_min': int(item['end_min']),
            'duration': max(15, int(item['end_min']) - int(item['start_min'])),
            'ghost': None,
        }
        return 'break'

    def _calendar_timeline_motion(self, event):
        state = getattr(self, 'task_calendar_drag_state', None)
        if not state:
            return 'break'
        if not state['moved'] and abs(event.x_root - state['press_x']) + abs(event.y_root - state['press_y']) < 5:
            return 'break'
        state['moved'] = True
        canvas = state['canvas']
        geometry = getattr(self, '_cal_geometry', None)
        if not geometry:
            return 'break'
        gutter = geometry['gutter']
        col_width = geometry['col_width']
        visual_span = getattr(self, '_cal_visual_span', [])
        x = canvas.canvasx(event.x)
        y = canvas.canvasy(event.y)
        visual = int((x - gutter) // col_width) if x >= gutter else 0
        visual = max(0, min(len(visual_span) - 1, visual)) if visual_span else 0
        if state['mode'] == 'resize':
            new_end = max(state['start_min'] + 15, self._calendar_round_minutes(y))
            new_end = min(24 * 60, new_end)
            day = state['item']['occurrence_date']
            state['preview'] = (day, state['start_min'], new_end)
            left = gutter + visual_span.index(day) * col_width + 3 if day in visual_span else gutter + 3
            top, bottom = state['start_min'], new_end
            width = col_width - 6
            self.task_calendar_title.set(RLM + f"نهاية الموعد: {core.minutes_to_hhmm(new_end)}")
        else:
            new_start = self._calendar_round_minutes(y - state['grab_offset'])
            new_start = max(0, min(24 * 60 - state['duration'], new_start))
            new_end = new_start + state['duration']
            day = visual_span[visual] if visual_span else state['item']['occurrence_date']
            state['preview'] = (day, new_start, new_end)
            left = gutter + visual * col_width + 3
            top, bottom = new_start, new_end
            width = col_width - 6
            self.task_calendar_title.set(RLM + f"نقل الموعد: {day.day} {MONTH_NAMES[day.month - 1]} · {core.minutes_to_hhmm(new_start)}")
        if state['ghost'] is not None:
            try:
                canvas.delete(state['ghost'])
            except tk.TclError:
                pass
        try:
            state['ghost'] = canvas.create_rectangle(left, top, left + width, bottom,
                                                     outline=ACCENT_CYAN, width=2, dash=(4, 3))
        except tk.TclError:
            state['ghost'] = None
        return 'break'

    def _calendar_timeline_release(self, event):
        state = getattr(self, 'task_calendar_drag_state', None)
        if not state:
            return 'break'
        self.task_calendar_drag_state = None
        canvas = state['canvas']
        if state.get('ghost') is not None:
            try:
                canvas.delete(state['ghost'])
            except tk.TclError:
                pass
        if not state['moved']:
            self._calendar_open_item(state['item'])
            return 'break'
        preview = state.get('preview')
        if not preview:
            self._task_calendar_draw(preserve_scroll=True)
            return 'break'
        day, start_min, end_min = preview
        try:
            store.move_item(state['item'], day, start_min, end_min)
        except (ValueError, sqlite3.Error) as exc:
            messagebox.showerror('تعديل الموعد', str(exc), parent=self)
        self._task_calendar_draw(preserve_scroll=True)
        return 'break'

    def _calendar_item_quick_open(self, item):
        self._calendar_open_item(item)
        return 'break'

    # ------------------------------------------------------------------
    # عرض الأجندة
    # ------------------------------------------------------------------
    def _calendar_draw_agenda(self, span, grouped):
        host = tk.Frame(self.task_calendar_main, bg=BG_VOID)
        host.grid(row=0, column=0, sticky='nsew')
        host.grid_rowconfigure(0, weight=1)
        host.grid_columnconfigure(0, weight=1)
        canvas = tk.Canvas(host, bg=BG_VOID, highlightthickness=0)
        canvas.grid(row=0, column=0, sticky='nsew')
        scroll = ttk.Scrollbar(host, orient='vertical', command=canvas.yview)
        scroll.grid(row=0, column=1, sticky='ns')
        canvas.configure(yscrollcommand=scroll.set)
        canvas._sync_yscroll = lambda units: canvas.yview_scroll(units, 'units')
        inner = tk.Frame(canvas, bg=BG_VOID)
        window = canvas.create_window((0, 0), window=inner, anchor='nw')
        inner.bind('<Configure>', lambda _e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda event: canvas.itemconfigure(window, width=event.width))

        any_items = False
        for target in span:
            day_items = grouped.get(target.isoformat(), [])
            if not day_items:
                continue
            any_items = True
            head = tk.Frame(inner, bg=BG_HEADER)
            head.pack(fill='x', padx=6, pady=(10, 2))
            tk.Label(head, text=RLM + f'{WEEKDAY_NAMES[_sunday_index(target)]} {target.day} {MONTH_NAMES[target.month - 1]} {target.year}',
                     bg=BG_HEADER, fg=ACCENT_MATRIX, font=(TERM_FONT, 9, 'bold'),
                     anchor='e').pack(side='right', padx=10, pady=4)
            for item in day_items:
                self._calendar_agenda_row(inner, item)
        if not any_items:
            tk.Label(inner, text=RLM + 'لا توجد مواعيد في هذا النطاق.',
                     bg=BG_VOID, fg=FG_MUTED, font=(TERM_FONT, 12)).pack(expand=True, pady=60)

    def _calendar_agenda_row(self, parent, item):
        color, chip_bg, text_color = self._calendar_item_colors(item)
        row = tk.Frame(parent, bg=BG_PANEL, highlightbackground=BORDER_DIM, highlightthickness=1,
                       cursor='hand2')
        row.pack(fill='x', padx=6, pady=2)
        tk.Frame(row, bg=color, width=4).pack(side='right', fill='y')
        when = 'كل اليوم' if item['all_day'] else f"{item['start'].strftime('%H:%M')} – {item['end'].strftime('%H:%M')}"
        time_label = tk.Label(row, text=RLM + when, bg=BG_PANEL, fg=ACCENT_CYAN,
                              font=(MONO_FONT, 8), width=14, anchor='e')
        time_label.pack(side='right', padx=6, pady=8)
        title_text = str(item.get('title') or '')
        if item.get('completed'):
            title_text = '✓ ' + title_text
        title = tk.Label(row, text=RLM + title_text, bg=BG_PANEL, fg=text_color,
                         font=(TERM_FONT, 9, 'bold' if item['source'] == 'event' else 'normal'),
                         anchor='e', justify='right')
        title.pack(side='right', fill='x', expand=True, pady=8)
        meta_parts = [item.get('calendar_name') or '']
        if item.get('location'):
            meta_parts.append(str(item['location']))
        if item.get('recurrence'):
            meta_parts.append(str(item['recurrence']))
        if any(meta_parts):
            tk.Label(row, text=RLM + ' · '.join(part for part in meta_parts if part),
                     bg=BG_PANEL, fg=FG_MUTED, font=(TERM_FONT, 7), anchor='e').pack(side='right', padx=6)
        for widget in (row, time_label, title):
            widget.bind('<Button-1>', lambda _e, current=item: self._calendar_open_item(current))
        if item.get('source') == 'task':
            done_var = tk.BooleanVar(value=bool(item.get('completed')))
            tk.Checkbutton(row, variable=done_var, bg=BG_PANEL, activebackground=BG_PANEL,
                           selectcolor=BG_VOID, bd=0, highlightthickness=0,
                           command=lambda current=item, var=done_var: self._calendar_toggle_task(current, var)
                           ).pack(side='left', padx=4)

    def _calendar_toggle_task(self, item, variable):
        if not item.get('task_id'):
            return
        try:
            store.toggle_task_completed(item['task_id'])
        except sqlite3.Error as exc:
            messagebox.showerror('المهمة', str(exc), parent=self)
            return
        self._task_calendar_draw(preserve_scroll=True)

    # ------------------------------------------------------------------
    # التنبيهات الخلفية
    # ------------------------------------------------------------------
    def _calendar_reminder_tick(self):
        if not hasattr(self, 'calendar_notified'):
            self.calendar_notified = set()
        try:
            candidates = store.reminder_candidates()
        except (sqlite3.Error, ValueError):
            candidates = []
        now = datetime.now()
        for item in candidates:
            key = store.item_key(item)
            if key in self.calendar_notified:
                continue
            self.calendar_notified.add(key)
            if item['all_day']:
                when = 'كل اليوم'
            else:
                minutes = int((item['start'] - now).total_seconds() // 60)
                if minutes <= 0:
                    when = f"الآن · {item['start'].strftime('%H:%M')}"
                else:
                    when = f"بعد {minutes} دقيقة · {item['start'].strftime('%H:%M')}"
            message = f"{item.get('title') or ''}\n{when}"
            if item.get('calendar_name'):
                message += f" · {item['calendar_name']}"
            try:
                self._task_show_toast('[ALERT // تذكير موعد]', message)
            except Exception:
                pass
        if len(self.calendar_notified) > 800:
            self.calendar_notified = set(list(self.calendar_notified)[-200:])

    def _calendar_global_tick(self):
        try:
            self._calendar_reminder_tick()
        except Exception:
            pass
        try:
            if getattr(self, 'task_calendar_active', False) and getattr(self, 'task_calendar_drag_state', None) is None:
                self._task_calendar_draw(preserve_scroll=True)
        except Exception:
            pass
        try:
            self.after(60000, self._calendar_global_tick)
        except tk.TclError:
            pass
