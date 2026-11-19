# Rasd - نافذة إنشاء/تعديل موعد التقويم (مع التكرار والاستثناءات والتذكير).
from common import *
from storage import *
import calendar_core as core
import calendar_store as store

NO_REPEAT = 'بدون تكرار'

REMINDER_VALUES = (
    ('بدون تذكير', -1),
    ('عند الموعد', 0),
    ('قبل 5 دقائق', 5),
    ('قبل 10 دقائق', 10),
    ('قبل 15 دقيقة', 15),
    ('قبل 30 دقيقة', 30),
    ('قبل ساعة', 60),
    ('قبل يوم', 1440),
)

REPEAT_VALUES = (NO_REPEAT, 'يومياً', 'أسبوعياً', 'كل أسبوعين', 'شهرياً', 'سنوياً')


class CalendarDialogMixin:
    # ------------------------------------------------------------------
    # أدوات مساعدة
    # ------------------------------------------------------------------
    def _calendar_reminder_text(self, minutes):
        try:
            minutes = int(minutes)
        except (TypeError, ValueError):
            minutes = 10
        for label, value in REMINDER_VALUES:
            if value == minutes:
                return label
        return 'قبل 10 دقائق'

    def _calendar_reminder_minutes(self, text):
        for label, value in REMINDER_VALUES:
            if label == text:
                return value
        return 10

    def _calendar_repeat_text(self, rrule):
        if not rrule:
            return NO_REPEAT
        return core.rrule_to_preset(rrule)

    def _calendar_time_choices(self):
        return tuple(self._task_time_display(f'{hour:02d}:{minute:02d}')
                     for hour in range(24) for minute in (0, 15, 30, 45))

    def _calendar_parse_time(self, value):
        canonical = self._task_time_to_24(value)
        return core.parse_hhmm(canonical) if canonical else None

    def _calendar_unique_tag(self):
        self._calendar_dialog_seq = getattr(self, '_calendar_dialog_seq', 0) + 1
        return self._calendar_dialog_seq

    def _refresh_calendar_views(self, task_id=None):
        """يعيد رسم التقويم/القوائم بعد أي حفظ أو حذف."""
        if getattr(self, 'task_calendar_active', False):
            try:
                self._task_calendar_draw(preserve_scroll=True)
            except Exception:
                pass
        if getattr(self, 'task_tree', None) and self.task_tree.winfo_exists():
            try:
                self._task_refresh_rows()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # نافذة الموعد
    # ------------------------------------------------------------------
    def _calendar_event_dialog(self, event_id=None, occurrence=None, initial_date=None,
                               initial_start=None, initial_end=None, calendar_id=None,
                               item=None, default_all_day=False):
        event = store.get_event(event_id) if event_id else None
        calendars = store.calendar_rows()
        if not calendars:
            store.ensure_calendar_schema()
            calendars = store.calendar_rows()
        override = (occurrence or {}).get('override') or {}

        # تحديد القيم الابتدائية
        title_val = ''
        description_val = ''
        location_val = ''
        recurrence_val = NO_REPEAT
        reminder_val = 10
        color_val = None
        all_day_val = bool(default_all_day)
        start_local = end_local = None
        base_date = initial_date or date.today()
        start_text = initial_start or '09:00'
        end_text = initial_end or '10:00'

        if event:
            base_date, base_end = store.event_local_times(event)
            if base_date is None:
                base_date = date.today()
            title_val = event['title'] or ''
            description_val = event['description'] or ''
            location_val = event['location'] or ''
            recurrence_val = self._calendar_repeat_text(event['rrule'])
            reminder_val = int(event['reminder_minutes'] if event['reminder_minutes'] is not None else 10)
            color_val = event['color']
            all_day_val = bool(int(event['is_all_day'] or 0))
            start_text = f'{base_date.hour:02d}:{base_date.minute:02d}'
            end_text = f'{base_end.hour:02d}:{base_end.minute:02d}' if base_end else '10:00'
            calendar_id = event['calendar_id']
            if occurrence:
                base_date = occurrence['start'].date()
                all_day_val = bool(int(event['is_all_day'] or 0) or override.get('all_day'))
                if not all_day_val:
                    start_text = f"{occurrence['start'].hour:02d}:{occurrence['start'].minute:02d}"
                    end_text = f"{occurrence['end'].hour:02d}:{occurrence['end'].minute:02d}"
                title_val = override.get('title', title_val)
                description_val = override.get('description', description_val)
                location_val = override.get('location', location_val)
                color_val = override.get('color', color_val)

        calendar_lookup = {row['name']: row for row in calendars}
        current_calendar = calendars[0]
        if calendar_id:
            for row in calendars:
                if int(row['id']) == int(calendar_id):
                    current_calendar = row
                    break

        seq = self._calendar_unique_tag()
        win = tk.Toplevel(self)
        win.title('تعديل الموعد' if event_id else 'إضافة موعد')
        win.configure(bg=BG_VOID)
        win.transient(self)
        win.grab_set()
        win.resizable(True, True)
        card = tk.Frame(win, bg=BG_PANEL, highlightbackground=ACCENT_CYAN, highlightthickness=1)
        card.pack(fill='both', expand=True, padx=12, pady=12)
        card.grid_columnconfigure(0, weight=1)

        heading = 'تعديل الموعد' if event_id else 'إضافة موعد'
        tk.Label(card, text=RLM + heading, bg=BG_PANEL, fg=ACCENT_CYAN,
                 font=(TERM_FONT, 13, 'bold')).grid(row=0, column=0, sticky='e', padx=16, pady=(14, 6))

        # العنوان
        title_var = tk.StringVar(value=title_val)
        title_var._rasd_no_translate = True
        title_entry = ttk.Entry(card, textvariable=title_var, justify='right')
        title_entry._rasd_no_translate = True
        title_entry.grid(row=1, column=0, sticky='ew', padx=16, pady=(10, 6))

        meta = tk.Frame(card, bg=BG_PANEL)
        meta.grid(row=2, column=0, sticky='ew', padx=16, pady=2)
        meta.grid_columnconfigure(1, weight=1)

        # التقويم + اللون
        tk.Label(meta, text=RLM + 'التقويم:', bg=BG_PANEL, fg=ACCENT_CYAN,
                 font=(TERM_FONT, 9)).grid(row=0, column=0, sticky='e', padx=(0, 6), pady=3)
        calendar_var = tk.StringVar(value=current_calendar['name'])
        calendar_combo = ttk.Combobox(meta, textvariable=calendar_var,
                                      values=tuple(row['name'] for row in calendars),
                                      state='readonly', justify='right', style='Office.TCombobox')
        calendar_combo.grid(row=0, column=1, sticky='ew', pady=3)

        color_var = tk.StringVar(value=color_val or '')
        swatch = tk.Label(meta, text='  ', width=3, bg=(color_val or current_calendar['color']),
                          relief='solid', borderwidth=1, cursor='hand2')
        swatch.grid(row=0, column=2, sticky='e', padx=6)

        def pick_color(_event=None):
            chosen = colorchooser.askcolor(color=(color_var.get() or current_calendar['color']),
                                          parent=win, title='لون الموعد')
            if chosen and chosen[1]:
                color_var.set(chosen[1])
                swatch.configure(bg=chosen[1])

        swatch.bind('<Button-1>', pick_color)

        def on_calendar_change(_event=None):
            row = calendar_lookup.get(calendar_var.get())
            if row and not color_var.get():
                swatch.configure(bg=row['color'])

        calendar_combo.bind('<<ComboboxSelected>>', on_calendar_change)

        # التاريخ + كل اليوم
        row1 = tk.Frame(card, bg=BG_PANEL)
        row1.grid(row=3, column=0, sticky='ew', padx=16, pady=4)
        tk.Label(row1, text=RLM + 'التاريخ:', bg=BG_PANEL, fg=ACCENT_CYAN,
                 font=(TERM_FONT, 9)).pack(side='right', padx=(0, 6))
        date_var = tk.StringVar(value=base_date.isoformat())
        date_var._rasd_no_translate = True
        date_entry = ttk.Entry(row1, textvariable=date_var, width=14, justify='center')
        date_entry._rasd_no_translate = True
        date_entry.pack(side='right', padx=3)
        ttk.Button(row1, text=RLM + '🗓', width=3,
                   command=lambda: self._task_pick_date(date_var, base_date, parent=win)).pack(side='right', padx=3)
        all_day_var = tk.BooleanVar(value=all_day_val)
        tk.Checkbutton(row1, text=RLM + 'كل اليوم', variable=all_day_var,
                       bg=BG_PANEL, fg=FG_PRIMARY, activebackground=BG_PANEL,
                       selectcolor=BG_VOID, font=(TERM_FONT, 9)).pack(side='left', padx=6)

        # الوقت
        row2 = tk.Frame(card, bg=BG_PANEL)
        row2.grid(row=4, column=0, sticky='ew', padx=16, pady=4)
        tk.Label(row2, text=RLM + 'من:', bg=BG_PANEL, fg=ACCENT_CYAN,
                 font=(TERM_FONT, 9)).pack(side='right', padx=(0, 4))
        choices = self._calendar_time_choices()
        start_var = tk.StringVar(value=self._task_time_display(start_text))
        start_combo = ttk.Combobox(row2, textvariable=start_var, values=choices, state='readonly',
                                   width=10, justify='center', style='Office.TCombobox')
        start_combo.pack(side='right', padx=3)
        tk.Label(row2, text=RLM + 'إلى:', bg=BG_PANEL, fg=ACCENT_CYAN,
                 font=(TERM_FONT, 9)).pack(side='right', padx=(8, 4))
        end_var = tk.StringVar(value=self._task_time_display(end_text))
        end_combo = ttk.Combobox(row2, textvariable=end_var, values=choices, state='readonly',
                                 width=10, justify='center', style='Office.TCombobox')
        end_combo.pack(side='right', padx=3)

        def sync_all_day(*_args):
            state = 'disabled' if all_day_var.get() else 'readonly'
            start_combo.configure(state=state)
            end_combo.configure(state=state)

        all_day_var.trace_add('write', sync_all_day)
        sync_all_day()

        # المكان
        row3 = tk.Frame(card, bg=BG_PANEL)
        row3.grid(row=5, column=0, sticky='ew', padx=16, pady=4)
        tk.Label(row3, text=RLM + 'المكان:', bg=BG_PANEL, fg=ACCENT_CYAN,
                 font=(TERM_FONT, 9)).pack(side='right', padx=(0, 6))
        location_var = tk.StringVar(value=location_val)
        location_var._rasd_no_translate = True
        location_entry = ttk.Entry(row3, textvariable=location_var, justify='right')
        location_entry._rasd_no_translate = True
        location_entry.pack(side='right', fill='x', expand=True)

        # الوصف
        tk.Label(card, text=RLM + 'الوصف:', bg=BG_PANEL, fg=ACCENT_CYAN,
                 font=(TERM_FONT, 9)).grid(row=6, column=0, sticky='e', padx=16, pady=(6, 2))
        description_text = tk.Text(card, height=3, wrap='word', bg=BG_VOID, fg=FG_PRIMARY,
                                   insertbackground=ACCENT_MATRIX, relief='solid', borderwidth=1,
                                   font=(TERM_FONT, 9))
        description_text._rasd_no_translate = True
        description_text.grid(row=7, column=0, sticky='ew', padx=16, pady=(0, 4))
        description_text.insert('1.0', description_val or '')

        # التكرار + التذكير
        row4 = tk.Frame(card, bg=BG_PANEL)
        row4.grid(row=8, column=0, sticky='ew', padx=16, pady=4)
        tk.Label(row4, text=RLM + 'التكرار:', bg=BG_PANEL, fg=ACCENT_CYAN,
                 font=(TERM_FONT, 9)).pack(side='right', padx=(0, 4))
        repeat_var = tk.StringVar(value=recurrence_val)
        repeat_combo = ttk.Combobox(row4, textvariable=repeat_var, values=REPEAT_VALUES,
                                    state='readonly', width=12, justify='right',
                                    style='Office.TCombobox')
        repeat_combo.pack(side='right', padx=4)
        tk.Label(row4, text=RLM + 'التذكير:', bg=BG_PANEL, fg=ACCENT_CYAN,
                 font=(TERM_FONT, 9)).pack(side='right', padx=(12, 4))
        reminder_var = tk.StringVar(value=self._calendar_reminder_text(reminder_val))
        reminder_combo = ttk.Combobox(row4, textvariable=reminder_var,
                                      values=tuple(label for label, _v in REMINDER_VALUES),
                                      state='readonly', width=13, justify='right',
                                      style='Office.TCombobox')
        reminder_combo.pack(side='right', padx=4)

        # نطاق التعديل للسلسلة المتكررة
        scope_var = tk.StringVar(value='هذا الموعد فقط')
        scope_combo = None
        if event and event.get('rrule') and occurrence:
            scope_row = tk.Frame(card, bg=BG_PANEL)
            scope_row.grid(row=9, column=0, sticky='ew', padx=16, pady=4)
            tk.Label(scope_row, text=RLM + 'نطاق التعديل:', bg=BG_PANEL, fg=ACCENT_CYAN,
                     font=(TERM_FONT, 9)).pack(side='right', padx=(0, 6))
            scope_combo = ttk.Combobox(scope_row, textvariable=scope_var,
                                       values=('هذا الموعد فقط', 'كل المواعيد'),
                                       state='readonly', width=16, justify='right',
                                       style='Office.TCombobox')
            scope_combo.pack(side='right', padx=4)
        scope_row_index = 10 if scope_combo else 9

        # الأزرار
        actions = tk.Frame(card, bg=BG_PANEL)
        actions.grid(row=scope_row_index, column=0, sticky='ew', padx=12, pady=(10, 12))

        def save():
            title_value = title_var.get().strip()
            if not title_value:
                return messagebox.showwarning('الموعد', 'عنوان الموعد مطلوب.', parent=win)
            try:
                parsed_date = self._task_parse_date(date_var.get())
                chosen_date = date.fromisoformat(parsed_date) if parsed_date else None
            except ValueError as exc:
                return messagebox.showwarning('الموعد', str(exc), parent=win)
            if chosen_date is None:
                return messagebox.showwarning('الموعد', 'حدد تاريخ الموعد.', parent=win)
            all_day = bool(all_day_var.get())
            start_minutes = self._calendar_parse_time(start_var.get())
            end_minutes = self._calendar_parse_time(end_var.get())
            if not all_day:
                if start_minutes is None:
                    return messagebox.showwarning('الموعد', 'حدد وقت البداية.', parent=win)
                if end_minutes is None or end_minutes <= start_minutes:
                    end_minutes = min(24 * 60, start_minutes + 60)
            calendar_row = calendar_lookup.get(calendar_var.get()) or current_calendar
            repeat_text = repeat_var.get()
            rrule_value = None if repeat_text == NO_REPEAT else core.rrule_from_preset(repeat_text, chosen_date)
            reminder_minutes = self._calendar_reminder_minutes(reminder_var.get())
            description_value = description_text.get('1.0', 'end').strip()
            color_value = color_var.get() or None

            single_scope = bool(scope_combo and scope_var.get() == 'هذا الموعد فقط')
            try:
                if event and single_scope and occurrence:
                    overrides = core.parse_json_dict(event.get('overrides'))
                    key = (occurrence.get('rule_date') or occurrence['occurrence_date']).isoformat()
                    override = {'title': title_value, 'description': description_value,
                                'location': location_var.get().strip(), 'date': chosen_date.isoformat()}
                    if color_value:
                        override['color'] = color_value
                    if all_day:
                        override['all_day'] = True
                    else:
                        override['start'] = core.minutes_to_hhmm(start_minutes)
                        override['end'] = core.minutes_to_hhmm(end_minutes)
                    overrides[key] = override
                    store.update_event(event['id'], overrides=overrides)
                else:
                    if all_day:
                        start_local_value = datetime.combine(chosen_date, datetime.min.time())
                        end_local_value = start_local_value
                    else:
                        start_local_value = datetime.combine(chosen_date, datetime.min.time()) + timedelta(minutes=start_minutes)
                        end_local_value = datetime.combine(chosen_date, datetime.min.time()) + timedelta(minutes=end_minutes)
                    if event:
                        store.update_event(
                            event['id'],
                            calendar_id=calendar_row['id'], title=title_value,
                            description=description_value, location=location_var.get().strip(),
                            color=color_value, is_all_day=all_day,
                            start_utc=core.local_to_utc_iso(start_local_value),
                            end_utc=core.local_to_utc_iso(end_local_value),
                            rrule=rrule_value, reminder_minutes=reminder_minutes)
                    else:
                        store.create_event(
                            calendar_row['id'], title_value, start_local_value, end_local_value,
                            description=description_value, location=location_var.get().strip(),
                            color=color_value, is_all_day=all_day, rrule=rrule_value,
                            reminder_minutes=reminder_minutes)
            except (ValueError, sqlite3.Error) as exc:
                return messagebox.showerror('حفظ الموعد', str(exc), parent=win)
            win.destroy()
            self._refresh_calendar_views()

        def delete():
            if not event:
                return win.destroy()
            if event.get('rrule') and occurrence:
                answer = messagebox.askyesnocancel(
                    'حذف الموعد',
                    'هل تريد حذف هذا الموعد فقط من السلسلة؟\n\n'
                    'نعم: هذا الموعد فقط\nلا: كل المواعيد في السلسلة',
                    parent=win)
                if answer is None:
                    return
                if answer:
                    store.cancel_event_occurrence(event['id'], occurrence.get('rule_date') or occurrence['occurrence_date'])
                else:
                    store.delete_event(event['id'])
            else:
                if not messagebox.askyesno('حذف الموعد', 'هل تريد حذف هذا الموعد نهائيًا؟', parent=win):
                    return
                store.delete_event(event['id'])
            win.destroy()
            self._refresh_calendar_views()

        if event_id:
            tk.Button(actions, text=RLM + '× حذف', command=delete, bg=BG_PANEL, fg=ACCENT_DANGER,
                      activebackground=BG_SELECTED, relief='solid', borderwidth=1,
                      font=(TERM_FONT, 9, 'bold'), padx=12, pady=5, cursor='hand2').pack(side='left', padx=4)
        tk.Button(actions, text=RLM + 'إلغاء', command=win.destroy, bg=BG_HEADER, fg=FG_MUTED,
                  activebackground=BG_SELECTED, relief='solid', borderwidth=1,
                  font=(TERM_FONT, 9), padx=12, pady=5, cursor='hand2').pack(side='left', padx=4)
        tk.Button(actions, text=RLM + '✓ حفظ', command=save, bg=BG_HEADER, fg=ACCENT_MATRIX,
                  activebackground=ACCENT_MATRIX, activeforeground=BG_VOID, relief='solid',
                  borderwidth=1, font=(TERM_FONT, 9, 'bold'), padx=16, pady=5,
                  cursor='hand2').pack(side='right', padx=4)

        win.bind('<Control-Return>', lambda _e: (save(), 'break'))
        win.bind('<Escape>', lambda _e: win.destroy())

        win.update_idletasks()
        width = 560
        height = max(520, win.winfo_reqheight())
        x = self.winfo_rootx() + max(0, (self.winfo_width() - width) // 2)
        y = self.winfo_rooty() + max(0, (self.winfo_height() - height) // 2)
        win.geometry(f'{width}x{height}+{x}+{y}')
        title_entry.focus_set()

