# Rasd - طبقة بيانات التقويم: التقويمات، المواعيد، التكرار، والدمج مع المهام.
import json
import sqlite3
from datetime import date, datetime, time, timedelta

from storage import connect
import calendar_core as core

DEFAULT_CALENDARS = (
    ('العمل', '#3B82F6', 'work'),
    ('شخصي', '#22C55E', 'personal'),
    ('المهام', '#F59E0B', 'tasks'),
)

_EVENT_COLUMNS = (
    'calendar_id', 'title', 'description', 'location', 'color',
    'start_utc', 'end_utc', 'is_all_day', 'rrule', 'exdates',
    'overrides', 'reminder_minutes', 'timezone',
)


def _now_text():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def ensure_calendar_schema():
    """ينشئ جداول التقويم ويزرع التقويمات الافتراضية (آمن للاستدعاء المتكرر)."""
    with connect() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS calendars(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            color TEXT NOT NULL,
            visible INTEGER NOT NULL DEFAULT 1,
            kind TEXT NOT NULL DEFAULT 'custom',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS calendar_events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            calendar_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            location TEXT NOT NULL DEFAULT '',
            color TEXT,
            start_utc TEXT NOT NULL,
            end_utc TEXT,
            is_all_day INTEGER NOT NULL DEFAULT 0,
            rrule TEXT,
            exdates TEXT NOT NULL DEFAULT '[]',
            overrides TEXT NOT NULL DEFAULT '{}',
            reminder_minutes INTEGER NOT NULL DEFAULT 10,
            timezone TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(calendar_id) REFERENCES calendars(id)
        );
        CREATE INDEX IF NOT EXISTS idx_calendar_events_start
            ON calendar_events(start_utc, end_utc);
        CREATE INDEX IF NOT EXISTS idx_calendar_events_calendar
            ON calendar_events(calendar_id, start_utc);
        ''')
        for name, color, kind in DEFAULT_CALENDARS:
            exists = c.execute('SELECT 1 FROM calendars WHERE kind=?', (kind,)).fetchone()
            if not exists:
                c.execute(
                    'INSERT OR IGNORE INTO calendars(name,color,visible,kind,created_at) VALUES(?,?,?,?,?)',
                    (name, color, 1, kind, _now_text()))
    return True


def calendar_rows():
    ensure_calendar_schema()
    with connect() as c:
        return [dict(row) for row in c.execute(
            "SELECT * FROM calendars ORDER BY CASE kind WHEN 'work' THEN 0 WHEN 'personal' THEN 1 "
            "WHEN 'tasks' THEN 2 ELSE 3 END, id").fetchall()]


def calendar_map():
    return {row['id']: row for row in calendar_rows()}


def tasks_calendar_id():
    for row in calendar_rows():
        if row['kind'] == 'tasks':
            return row['id']
    with connect() as c:
        c.execute('INSERT OR IGNORE INTO calendars(name,color,visible,kind,created_at) VALUES(?,?,?,?,?)',
                  ('المهام', '#F59E0B', 1, 'tasks', _now_text()))
        found = c.execute("SELECT id FROM calendars WHERE kind='tasks' LIMIT 1").fetchone()
    return found['id'] if found else None


def visible_calendar_ids():
    return {row['id'] for row in calendar_rows() if int(row['visible'] or 0)}


def set_calendar_visible(calendar_id, visible):
    with connect() as c:
        c.execute('UPDATE calendars SET visible=? WHERE id=?', (1 if visible else 0, int(calendar_id)))


def add_calendar(name, color):
    name = str(name or '').strip()
    if not name:
        raise ValueError('اسم التقويم مطلوب.')
    with connect() as c:
        if c.execute('SELECT 1 FROM calendars WHERE name=?', (name,)).fetchone():
            raise ValueError('يوجد تقويم بهذا الاسم بالفعل.')
        cursor = c.execute(
            'INSERT INTO calendars(name,color,visible,kind,created_at) VALUES(?,?,?,?,?)',
            (name, color or '#3B82F6', 1, 'custom', _now_text()))
        return cursor.lastrowid


def update_calendar(calendar_id, name=None, color=None):
    fields, params = [], []
    if name is not None:
        fields.append('name=?')
        params.append(str(name).strip())
    if color is not None:
        fields.append('color=?')
        params.append(color)
    if not fields:
        return False
    params.append(int(calendar_id))
    with connect() as c:
        c.execute(f'UPDATE calendars SET {", ".join(fields)} WHERE id=?', params)
    return True


def delete_calendar(calendar_id):
    with connect() as c:
        row = c.execute('SELECT * FROM calendars WHERE id=?', (int(calendar_id),)).fetchone()
        if not row:
            return False
        if row['kind'] == 'tasks':
            raise ValueError('لا يمكن حذف تقويم المهام الافتراضي.')
        used = c.execute('SELECT COUNT(*) FROM calendar_events WHERE calendar_id=?', (int(calendar_id),)).fetchone()[0]
        if used:
            raise ValueError('انقل مواعيد هذا التقويم أو احذفها أولًا.')
        c.execute('DELETE FROM calendars WHERE id=?', (int(calendar_id),))
    return True


# ---------------------------------------------------------------------------
# CRUD المواعيد
# ---------------------------------------------------------------------------
def get_event(event_id):
    ensure_calendar_schema()
    with connect() as c:
        row = c.execute('SELECT * FROM calendar_events WHERE id=?', (int(event_id),)).fetchone()
    return dict(row) if row else None


def create_event(calendar_id, title, start_local, end_local=None, description='', location='',
                 color=None, is_all_day=False, rrule=None, reminder_minutes=10,
                 exdates=None, overrides=None):
    ensure_calendar_schema()
    if not title or not str(title).strip():
        raise ValueError('عنوان الموعد مطلوب.')
    start_local = start_local if isinstance(start_local, datetime) else datetime.combine(start_local, time.min)
    if is_all_day:
        start_local = start_local.replace(hour=0, minute=0, second=0, microsecond=0)
        end_local = start_local
    else:
        end_local = end_local or (start_local + timedelta(hours=1))
        if end_local <= start_local:
            raise ValueError('وقت النهاية يجب أن يكون بعد البداية.')
    now = _now_text()
    with connect() as c:
        cursor = c.execute(
            'INSERT INTO calendar_events(calendar_id,title,description,location,color,start_utc,end_utc,'
            'is_all_day,rrule,exdates,overrides,reminder_minutes,timezone,created_at,updated_at) '
            'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (int(calendar_id), str(title).strip(), description or '', location or '', color,
             core.local_to_utc_iso(start_local), core.local_to_utc_iso(end_local),
             1 if is_all_day else 0, rrule or None,
             json.dumps(exdates or [], ensure_ascii=False),
             json.dumps(overrides or {}, ensure_ascii=False),
             int(reminder_minutes if reminder_minutes is not None else 10),
             core.local_timezone_label(), now, now))
        return cursor.lastrowid


def update_event(event_id, **fields):
    ensure_calendar_schema()
    allowed = set(_EVENT_COLUMNS)
    updates, params = [], []
    for key, value in fields.items():
        if key not in allowed:
            continue
        if key in ('start_utc', 'end_utc') and isinstance(value, datetime):
            value = core.local_to_utc_iso(value)
        if key in ('exdates', 'overrides') and not isinstance(value, str):
            value = json.dumps(value or ([] if key == 'exdates' else {}), ensure_ascii=False)
        if key == 'is_all_day':
            value = 1 if value else 0
        updates.append(f'{key}=?')
        params.append(value)
    if not updates:
        return False
    updates.append('updated_at=?')
    params.append(_now_text())
    params.append(int(event_id))
    with connect() as c:
        c.execute(f'UPDATE calendar_events SET {", ".join(updates)} WHERE id=?', params)
    return True


def delete_event(event_id):
    with connect() as c:
        c.execute('DELETE FROM calendar_events WHERE id=?', (int(event_id),))
    return True


def set_event_override(event_id, occurrence_date, override):
    """يحفظ استثناء موعد واحد داخل سلسلة متكررة."""
    event = get_event(event_id)
    if not event:
        return False
    overrides = core.parse_json_dict(event['overrides'])
    overrides[occurrence_date.isoformat() if hasattr(occurrence_date, 'isoformat') else str(occurrence_date)] = override
    return update_event(event_id, overrides=overrides)


def cancel_event_occurrence(event_id, occurrence_date):
    return set_event_override(event_id, occurrence_date, {'cancelled': True})


def event_local_times(event):
    """يعيد (start, end) محليين لصف موعد."""
    start = core.utc_iso_to_local(event.get('start_utc'))
    end = core.utc_iso_to_local(event.get('end_utc')) if event.get('end_utc') else start
    if start is None:
        return None, None
    if int(event.get('is_all_day') or 0):
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start
    return start, end


# ---------------------------------------------------------------------------
# تحويل المهام إلى عناصر تقويم (لتبقى قائمة المهام هي المصدر)
# ---------------------------------------------------------------------------
def _task_rrule(row):
    recurrence = str(row['recurrence'] or '').strip()
    if not recurrence or recurrence in ('لا يوجد', 'بدون تكرار'):
        return None
    try:
        due = date.fromisoformat(str(row['due_date'])[:10])
    except ValueError:
        return None
    return core.rrule_from_preset(recurrence, due)


def _task_item(row, calendar, occurrence=None, virtual=False):
    due = None
    try:
        due = date.fromisoformat(str(row['due_date'])[:10])
    except (TypeError, ValueError):
        return None
    start_minutes = core.parse_hhmm(row['start_time'])
    end_minutes = core.parse_hhmm(row['end_time'])
    all_day = start_minutes is None
    if all_day:
        start = datetime.combine(due, time.min)
        end = start
        start_minutes, end_minutes = 0, 0
    else:
        if end_minutes is None or end_minutes <= start_minutes:
            end_minutes = min(24 * 60, start_minutes + 60)
        start = datetime.combine(due, time.min) + timedelta(minutes=start_minutes)
        end = datetime.combine(due, time.min) + timedelta(minutes=end_minutes)
    if occurrence:
        start = occurrence['start']
        end = occurrence['end']
        if all_day:
            start = datetime.combine(occurrence['occurrence_date'], time.min)
            end = start
            start_minutes = end_minutes = 0
        else:
            start_minutes = start.hour * 60 + start.minute
            end_minutes = max(start_minutes + 15, end.hour * 60 + end.minute)
    completed = bool(row['completed_at'])
    return {
        'source': 'task',
        'id': f'task:{row["id"]}',
        'task_id': int(row['id']),
        'event_id': None,
        'calendar_id': calendar['id'] if calendar else None,
        'calendar_name': calendar['name'] if calendar else 'المهام',
        'color': (calendar or {}).get('color') or '#F59E0B',
        'title': row['title'] or 'مهمة',
        'description': row['description'] or '',
        'location': '',
        'start': start,
        'end': end,
        'start_min': start_minutes,
        'end_min': end_minutes,
        'all_day': all_day,
        'completed': completed,
        'priority': int(row['priority'] or 2),
        'project': row['project'] or '',
        'tags': row['tags'] or '',
        'rrule': _task_rrule(row),
        'recurrence': row['recurrence'] or '',
        'occurrence_date': occurrence['occurrence_date'] if occurrence else due,
        'rule_date': occurrence.get('rule_date') if occurrence else due,
        'reminder_minutes': 15,
        'virtual': bool(virtual),
        'raw': row,
    }


def _event_item(row, calendar, occurrence, base_date):
    start = occurrence['start']
    end = occurrence['end']
    override = occurrence.get('override') or {}
    all_day = bool(int(row['is_all_day'] or 0) or override.get('all_day'))
    if all_day:
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start
        start_minutes = end_minutes = 0
    else:
        start_minutes = start.hour * 60 + start.minute
        end_minutes = max(start_minutes + 15, end.hour * 60 + end.minute)
    return {
        'source': 'event',
        'id': f'event:{row["id"]}',
        'task_id': None,
        'event_id': int(row['id']),
        'calendar_id': calendar['id'] if calendar else row['calendar_id'],
        'calendar_name': calendar['name'] if calendar else '',
        'color': override.get('color') or row.get('color') or (calendar or {}).get('color') or '#3B82F6',
        'title': override.get('title') or row['title'],
        'description': override.get('description', row['description'] or ''),
        'location': override.get('location', row['location'] or ''),
        'start': start,
        'end': end,
        'start_min': start_minutes,
        'end_min': end_minutes,
        'all_day': all_day,
        'completed': False,
        'priority': 2,
        'project': '',
        'tags': '',
        'rrule': row['rrule'],
        'recurrence': core.rrule_to_preset(row['rrule']) if row['rrule'] else '',
        'occurrence_date': occurrence['occurrence_date'],
        'rule_date': occurrence.get('rule_date') or occurrence['occurrence_date'],
        'reminder_minutes': int(row['reminder_minutes'] if row['reminder_minutes'] is not None else 10),
        'override': override,
        'virtual': occurrence['occurrence_date'] != base_date or bool(override),
        'raw': row,
    }


def load_items(start_date, end_date, project=None):
    """يجمع مهام المشروع ومواعيد التقويم في قائمة واحدة داخل نطاق الأيام."""
    ensure_calendar_schema()
    calendars = calendar_map()
    visible = {cid for cid, row in calendars.items() if int(row['visible'] or 0)}
    range_start = datetime.combine(start_date, time.min)
    range_end = datetime.combine(end_date + timedelta(days=1), time.min)
    items = []

    tasks_cal = calendars.get(tasks_calendar_id())
    if tasks_cal and tasks_cal['id'] in visible:
        sql = ('SELECT * FROM tasks WHERE due_date IS NOT NULL AND due_date<>\'\' AND ('
               '(due_date>=? AND due_date<?) OR (recurrence IS NOT NULL AND recurrence NOT IN (\'\',\'لا يوجد\')))')
        params = [start_date.isoformat(), (end_date + timedelta(days=1)).isoformat()]
        if project:
            sql += ' AND project=?'
            params.append(project)
        with connect() as c:
            rows = c.execute(sql, params).fetchall()
        for row in rows:
            try:
                due = date.fromisoformat(str(row['due_date'])[:10])
            except ValueError:
                continue
            rrule = _task_rrule(row)
            if rrule:
                start_minutes = core.parse_hhmm(row['start_time'])
                end_minutes = core.parse_hhmm(row['end_time'])
                if start_minutes is None:
                    base_start = datetime.combine(due, time.min)
                    duration = timedelta(0)
                else:
                    if end_minutes is None or end_minutes <= start_minutes:
                        end_minutes = min(24 * 60, start_minutes + 60)
                    base_start = datetime.combine(due, time.min) + timedelta(minutes=start_minutes)
                    duration = timedelta(minutes=end_minutes - start_minutes)
                for occurrence in core.expand_occurrences(base_start, duration, rrule, range_start, range_end):
                    item = _task_item(row, tasks_cal, occurrence,
                                      virtual=occurrence['occurrence_date'] != due)
                    if item:
                        items.append(item)
            else:
                item = _task_item(row, tasks_cal)
                if item and item['start'] < range_end and item['start'] >= range_start:
                    items.append(item)

    with connect() as c:
        event_rows = c.execute('SELECT * FROM calendar_events').fetchall()
    for raw_row in event_rows:
        row = dict(raw_row)
        calendar = calendars.get(row['calendar_id'])
        if not calendar or calendar['id'] not in visible:
            continue
        base_start, base_end = event_local_times(row)
        if base_start is None:
            continue
        duration = timedelta(0) if int(row['is_all_day'] or 0) else max(timedelta(minutes=0), base_end - base_start)
        occurrences = core.expand_occurrences(
            base_start, duration, row['rrule'], range_start, range_end,
            core.parse_json_list(row['exdates']), core.parse_json_dict(row['overrides']))
        for occurrence in occurrences:
            items.append(_event_item(row, calendar, occurrence, base_start.date()))

    items.sort(key=lambda item: (
        item['occurrence_date'], 0 if item['all_day'] else 1,
        item['start_min'] if not item['all_day'] else 0,
        str(item['title']).casefold()))
    return items


def group_items_by_date(items, start_date, end_date):
    grouped = {}
    for item in items:
        key = item['occurrence_date'].isoformat()
        if start_date <= item['occurrence_date'] <= end_date:
            grouped.setdefault(key, []).append(item)
    return grouped


def get_task_item(task_id):
    """يعيد عنصر تقويم لمهمة واحدة (للمعاينة والاختيار من خارج التقويم)."""
    ensure_calendar_schema()
    with connect() as c:
        row = c.execute('SELECT * FROM tasks WHERE id=?', (int(task_id),)).fetchone()
    if not row:
        return None
    calendars = calendar_map()
    return _task_item(row, calendars.get(tasks_calendar_id()))


# ---------------------------------------------------------------------------
# أدوات النقل والتذكير
# ---------------------------------------------------------------------------
def item_key(item):
    """مفتاح فريد لكل ظهور لموعد أو مهمة (لمنع تكرار التنبيه)."""
    return f"{item.get('source')}:{item.get('id')}:{item['occurrence_date'].isoformat()}"


def move_item(item, new_date, new_start_minutes=None, new_end_minutes=None):
    """ينقل عنصر تقويم إلى يوم/وقت جديد مع الحفاظ على نوع المصدر."""
    new_date = new_date if isinstance(new_date, date) else date.fromisoformat(str(new_date)[:10])
    if new_start_minutes is None:
        new_start_minutes = item['start_min'] if not item['all_day'] else None
    if new_end_minutes is None:
        new_end_minutes = item['end_min'] if not item['all_day'] else None
    if item['source'] == 'task':
        return _move_task_item(item, new_date, new_start_minutes, new_end_minutes)
    return _move_event_item(item, new_date, new_start_minutes, new_end_minutes)


def _move_task_item(item, new_date, start_minutes, end_minutes):
    task_id = item['task_id']
    if item.get('virtual'):
        # نسخة افتراضية من مهمة متكررة: نعدل السلسلة نفسها (لا يوجد استثناء للمهام).
        pass
    if start_minutes is None:
        start_text = end_text = None
    else:
        start_minutes = max(0, min(23 * 60 + 45, int(start_minutes)))
        if end_minutes is None or end_minutes <= start_minutes:
            end_minutes = min(24 * 60, start_minutes + 60)
        end_minutes = max(start_minutes + 15, min(24 * 60, int(end_minutes)))
        start_text = core.minutes_to_hhmm(start_minutes)
        end_text = core.minutes_to_hhmm(end_minutes)
    with connect() as c:
        c.execute('UPDATE tasks SET due_date=?,start_time=?,end_time=?,updated_at=? WHERE id=?',
                  (new_date.isoformat(), start_text, end_text,
                   _now_text(), task_id))
    return True


def _move_event_item(item, new_date, start_minutes, end_minutes):
    event = get_event(item['event_id'])
    if not event:
        return False
    if event.get('rrule') and item.get('rule_date'):
        # موعد متكرر: ننقل ظهورًا واحدًا فقط عبر استثناء.
        start_local, end_local = event_local_times(event)
        duration = timedelta(0) if int(event.get('is_all_day') or 0) else (end_local - start_local)
        override = dict(core.parse_json_dict(event.get('overrides')).get(item['rule_date'].isoformat()) or {})
        override.pop('cancelled', None)
        if int(event.get('is_all_day') or 0) or item.get('all_day'):
            override['all_day'] = True
            override['date'] = new_date.isoformat()
        else:
            override['date'] = new_date.isoformat()
            override['start'] = core.minutes_to_hhmm(start_minutes or 0)
            if end_minutes is not None:
                override['end'] = core.minutes_to_hhmm(end_minutes)
        return set_event_override(item['event_id'], item['rule_date'], override)
    if int(event.get('is_all_day') or 0):
        start_local = datetime.combine(new_date, time.min)
        end_local = start_local
    else:
        start_minutes = max(0, min(23 * 60 + 45, int(start_minutes or 0)))
        if end_minutes is None or end_minutes <= start_minutes:
            end_minutes = min(24 * 60, start_minutes + 60)
        start_local = datetime.combine(new_date, time.min) + timedelta(minutes=start_minutes)
        end_local = datetime.combine(new_date, time.min) + timedelta(minutes=end_minutes)
    return update_event(event['id'],
                        start_utc=core.local_to_utc_iso(start_local),
                        end_utc=core.local_to_utc_iso(end_local))


def toggle_task_completed(task_id):
    with connect() as c:
        row = c.execute('SELECT completed_at FROM tasks WHERE id=?', (int(task_id),)).fetchone()
        if not row:
            return False
        done = _now_text() if not row['completed_at'] else None
        c.execute('UPDATE tasks SET completed_at=?,updated_at=? WHERE id=?', (done, _now_text(), int(task_id)))
    return bool(done)


# ---------------------------------------------------------------------------
# تنبيهات المواعيد
# ---------------------------------------------------------------------------
def reminder_candidates(now=None):
    """يعيد المواعيد التي حان وقت تذكيرها الآن (بدون تكرار الإرسال)."""
    now = now or datetime.now()
    today = now.date()
    items = load_items(today, today)
    ready = []
    for item in items:
        if item.get('completed'):
            continue
        reminder = int(item.get('reminder_minutes') or 0)
        if reminder < 0:
            continue
        if item['all_day']:
            # تذكير المواعيد اليومية في التاسعة صباحًا.
            if item['occurrence_date'] == today and now.hour >= 9:
                ready.append(item)
            continue
        start = item['start']
        minutes = (start - now).total_seconds() / 60.0
        if 0 <= minutes <= reminder:
            ready.append(item)
    return ready
