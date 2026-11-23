# Rasd - اختبارات عميقة لنظام التقويم (منطق + طبقة بيانات).
import os
import shutil
import sys
import tempfile
import time
import unittest
from datetime import date, datetime, time as dtime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _testhome import HOME as TEST_HOME  # noqa: E402  (يضبط LOCALAPPDATA قبل storage)

import storage  # noqa: E402
import calendar_core as core  # noqa: E402
import calendar_store as store  # noqa: E402


# التنظيف يتم عبر tests/_testhome.py بعد انتهاء كل ملفات الاختبار.
def tearDownModule():
    pass


class CalendarLogicTests(unittest.TestCase):
    def test_until_date_is_inclusive(self):
        values = core.expand_occurrences(
            datetime(2026, 3, 1, 9, 0), timedelta(hours=1),
            'FREQ=DAILY;UNTIL=20260304',
            datetime(2026, 3, 1), datetime(2026, 3, 10))
        self.assertEqual([item['occurrence_date'] for item in values],
                         [date(2026, 3, 1), date(2026, 3, 2),
                          date(2026, 3, 3), date(2026, 3, 4)])

    def test_monthly_day31_clamps_then_returns(self):
        values = core.expand_occurrences(
            datetime(2026, 1, 31, 9, 0), timedelta(hours=1), 'FREQ=MONTHLY',
            datetime(2026, 1, 1), datetime(2026, 5, 1))
        self.assertEqual([item['occurrence_date'] for item in values],
                         [date(2026, 1, 31), date(2026, 2, 28),
                          date(2026, 3, 31), date(2026, 4, 30)])

    def test_yearly_leap_day(self):
        values = core.expand_occurrences(
            datetime(2024, 2, 29, 9, 0), timedelta(hours=1), 'FREQ=YEARLY',
            datetime(2024, 1, 1), datetime(2030, 1, 1))
        self.assertEqual([item['occurrence_date'] for item in values],
                         [date(2024, 2, 29), date(2025, 2, 28),
                          date(2026, 2, 28), date(2027, 2, 28),
                          date(2028, 2, 29), date(2029, 2, 28)])

    def test_weekly_interval_two_byday(self):
        values = core.expand_occurrences(
            datetime(2026, 3, 1, 9, 0), timedelta(hours=1),
            'FREQ=WEEKLY;INTERVAL=2;BYDAY=SU',
            datetime(2026, 3, 1), datetime(2026, 3, 31))
        self.assertEqual([item['occurrence_date'] for item in values],
                         [date(2026, 3, 1), date(2026, 3, 15), date(2026, 3, 29)])

    def test_count_counts_from_series_start_not_range(self):
        values = core.expand_occurrences(
            datetime(2026, 3, 1, 9, 0), timedelta(hours=1), 'FREQ=DAILY;COUNT=3',
            datetime(2026, 3, 2), datetime(2026, 3, 10))
        self.assertEqual([item['occurrence_date'] for item in values],
                         [date(2026, 3, 2), date(2026, 3, 3)])

    def test_override_time_only_keeps_date(self):
        overrides = {'2026-03-02': {'start': '14:00', 'end': '15:00'}}
        values = core.expand_occurrences(
            datetime(2026, 3, 1, 9, 0), timedelta(hours=1), 'FREQ=DAILY',
            datetime(2026, 3, 2), datetime(2026, 3, 3), None, overrides)
        self.assertEqual(len(values), 1)
        self.assertEqual(values[0]['occurrence_date'], date(2026, 3, 2))
        self.assertEqual(values[0]['start'].strftime('%H:%M'), '14:00')
        self.assertEqual(values[0]['end'].strftime('%H:%M'), '15:00')

    def test_moved_occurrence_visible_only_on_new_date(self):
        overrides = {'2026-03-02': {'date': '2026-03-09', 'start': '12:00', 'end': '13:00'}}
        moved = core.expand_occurrences(
            datetime(2026, 3, 1, 9, 0), timedelta(hours=1), 'FREQ=DAILY',
            datetime(2026, 3, 9), datetime(2026, 3, 10), None, overrides)
        # يوم 9 مارس يحمل الموعد الطبيعي + الموعد المنقول من يوم 2.
        self.assertEqual(sorted(item['occurrence_date'] for item in moved),
                         [date(2026, 3, 9), date(2026, 3, 9)])
        self.assertEqual(sorted(item['rule_date'] for item in moved),
                         [date(2026, 3, 2), date(2026, 3, 9)])
        original = core.expand_occurrences(
            datetime(2026, 3, 1, 9, 0), timedelta(hours=1), 'FREQ=DAILY',
            datetime(2026, 3, 2), datetime(2026, 3, 3), None, overrides)
        self.assertEqual(original, [])

    def test_all_day_override_zero_duration(self):
        overrides = {'2026-03-02': {'all_day': True}}
        values = core.expand_occurrences(
            datetime(2026, 3, 1, 9, 0), timedelta(hours=1), 'FREQ=DAILY',
            datetime(2026, 3, 2), datetime(2026, 3, 3), None, overrides)
        self.assertEqual(len(values), 1)
        self.assertEqual(values[0]['start'], values[0]['end'])
        self.assertEqual(values[0]['start'].hour, 0)

    def test_utc_roundtrip_across_seasons(self):
        for moment in (datetime(2026, 1, 15, 12, 30), datetime(2026, 7, 15, 12, 30),
                       datetime(2026, 10, 30, 1, 15), datetime(2028, 2, 29, 23, 45)):
            stored = core.local_to_utc_iso(moment)
            self.assertTrue(stored.endswith('+00:00'), stored)
            self.assertEqual(core.utc_iso_to_local(stored), moment)

    def test_layout_nested_and_chain(self):
        events = [
            {'start_min': 540, 'end_min': 720},   # 09:00-12:00
            {'start_min': 600, 'end_min': 660},   # 10:00-11:00 nested
            {'start_min': 690, 'end_min': 780},   # 11:30-13:00 overlaps first
            {'start_min': 800, 'end_min': 830},   # 13:20-13:50 free
        ]
        lanes = core.layout_overlaps(events)
        self.assertEqual(lanes, 2)
        self.assertEqual(events[0]['lanes'], 2)
        self.assertEqual(events[1]['lanes'], 2)
        self.assertEqual(events[2]['lanes'], 2)
        self.assertNotEqual(events[0]['lane'], events[1]['lane'])
        self.assertNotEqual(events[2]['lane'], events[0]['lane'])

    def test_layout_identical_times(self):
        events = [{'start_min': 60, 'end_min': 120} for _ in range(3)]
        lanes = core.layout_overlaps(events)
        self.assertEqual(lanes, 3)
        self.assertEqual(sorted(item['lane'] for item in events), [0, 1, 2])

    def test_parse_hhmm_variants(self):
        self.assertEqual(core.parse_hhmm('09:05'), 545)
        self.assertEqual(core.parse_hhmm('9:05 PM'), 21 * 60 + 5)
        self.assertEqual(core.parse_hhmm('12:00 AM'), 0)
        self.assertEqual(core.parse_hhmm('12:00 PM'), 12 * 60)
        self.assertIsNone(core.parse_hhmm('24:00'))
        self.assertIsNone(core.parse_hhmm('nope'))
        self.assertIsNone(core.parse_hhmm(''))

    def test_all_day_single_day_visible_at_range_start(self):
        values = core.expand_occurrences(
            datetime(2026, 6, 1, 0, 0), timedelta(0), None,
            datetime(2026, 6, 1), datetime(2026, 6, 2))
        self.assertEqual(len(values), 1)
        self.assertEqual(values[0]['occurrence_date'], date(2026, 6, 1))

    def test_timed_event_to_midnight_end_min(self):
        store.ensure_calendar_schema()
        calendar_id = store.add_calendar('متأخر-' + str(time.time()), '#123456')
        try:
            event_id = store.create_event(
                calendar_id, 'سهرة', datetime(2026, 6, 5, 23, 30),
                datetime(2026, 6, 6, 0, 0))
            items = store.load_items(date(2026, 6, 5), date(2026, 6, 5))
            matched = [item for item in items if item.get('event_id') == event_id]
            self.assertEqual(len(matched), 1)
            self.assertEqual(matched[0]['end_min'], 24 * 60)
        finally:
            with storage.connect() as c:
                c.execute('DELETE FROM calendar_events WHERE calendar_id=?', (calendar_id,))
                c.execute('DELETE FROM calendars WHERE id=?', (calendar_id,))


class CalendarStoreTests(unittest.TestCase):
    def setUp(self):
        store.ensure_calendar_schema()
        self.created_events = []
        self.created_calendars = []
        self.created_tasks = []

    def tearDown(self):
        with storage.connect() as c:
            for event_id in self.created_events:
                c.execute('DELETE FROM calendar_events WHERE id=?', (event_id,))
            for task_id in self.created_tasks:
                c.execute('DELETE FROM tasks WHERE id=?', (task_id,))
            for calendar_id in self.created_calendars:
                c.execute('DELETE FROM calendar_events WHERE calendar_id=?', (calendar_id,))
                c.execute('DELETE FROM calendars WHERE id=?', (calendar_id,))

    def _calendar(self, name=None):
        calendar_id = store.add_calendar(
            (name or 'تقويم-اختبار') + '-' + str(time.time()), '#3366CC')
        self.created_calendars.append(calendar_id)
        return calendar_id

    def test_add_calendar_validates(self):
        with self.assertRaises(ValueError):
            store.add_calendar('   ', '#000000')
        name = 'مكرر-' + str(time.time())
        calendar_id = store.add_calendar(name, '#000000')
        self.created_calendars.append(calendar_id)
        with self.assertRaises(ValueError):
            store.add_calendar(name, '#111111')

    def test_delete_calendar_rules(self):
        with self.assertRaises(ValueError):
            store.delete_calendar(store.tasks_calendar_id())
        calendar_id = self._calendar()
        event_id = store.create_event(calendar_id, 'مرتبط', datetime(2026, 8, 1, 9, 0),
                                      datetime(2026, 8, 1, 10, 0))
        self.created_events.append(event_id)
        with self.assertRaises(ValueError):
            store.delete_calendar(calendar_id)
        store.delete_event(event_id)
        self.assertTrue(store.delete_calendar(calendar_id))
        self.created_calendars.remove(calendar_id)

    def test_create_event_validates(self):
        calendar_id = self._calendar()
        with self.assertRaises(ValueError):
            store.create_event(calendar_id, '   ', datetime(2026, 8, 1, 9, 0))
        with self.assertRaises(ValueError):
            store.create_event(calendar_id, 'خطأ', datetime(2026, 8, 1, 10, 0),
                               datetime(2026, 8, 1, 9, 0))

    def test_visibility_filters_events_and_tasks(self):
        calendar_id = self._calendar()
        event_id = store.create_event(calendar_id, 'ظهور', datetime(2026, 8, 2, 9, 0),
                                      datetime(2026, 8, 2, 10, 0))
        self.created_events.append(event_id)
        day = date(2026, 8, 2)
        self.assertTrue([i for i in store.load_items(day, day) if i.get('event_id') == event_id])
        store.set_calendar_visible(calendar_id, False)
        try:
            self.assertFalse([i for i in store.load_items(day, day) if i.get('event_id') == event_id])
        finally:
            store.set_calendar_visible(calendar_id, True)

    def test_scope_keeps_events_and_filters_tasks(self):
        project_a = 'مشروع-أ-' + str(time.time())
        project_b = 'مشروع-ب-' + str(time.time())
        with storage.connect() as c:
            ids = []
            for project, title in ((project_a, 'مهمة أ'), (project_b, 'مهمة ب')):
                cursor = c.execute(
                    'INSERT INTO tasks(title,project,due_date,start_time,end_time,priority,created_at,updated_at) '
                    'VALUES(?,?,?,?,?,?,?,?)',
                    (title, project, '2026-09-03', '10:00', '11:00', 2,
                     '2026-09-01 00:00:00', '2026-09-01 00:00:00'))
                ids.append(cursor.lastrowid)
        self.created_tasks.extend(ids)
        calendar_id = self._calendar()
        event_id = store.create_event(calendar_id, 'حدث عام', datetime(2026, 9, 3, 12, 0),
                                      datetime(2026, 9, 3, 13, 0))
        self.created_events.append(event_id)
        items = store.load_items(date(2026, 9, 3), date(2026, 9, 3), project_a)
        task_titles = {i['title'] for i in items if i['source'] == 'task'}
        self.assertIn('مهمة أ', task_titles)
        self.assertNotIn('مهمة ب', task_titles)
        self.assertTrue([i for i in items if i.get('event_id') == event_id])

    def test_move_all_day_event_stays_all_day(self):
        calendar_id = self._calendar()
        event_id = store.create_event(calendar_id, 'يوم كامل', datetime(2026, 9, 10),
                                      is_all_day=True)
        self.created_events.append(event_id)
        item = [i for i in store.load_items(date(2026, 9, 10), date(2026, 9, 10))
                if i.get('event_id') == event_id][0]
        self.assertTrue(store.move_item(item, date(2026, 9, 12)))
        moved = [i for i in store.load_items(date(2026, 9, 12), date(2026, 9, 12))
                 if i.get('event_id') == event_id]
        self.assertEqual(len(moved), 1)
        self.assertTrue(moved[0]['all_day'])

    def test_move_task_updates_due_and_times(self):
        project = 'مشروع-نقل-' + str(time.time())
        with storage.connect() as c:
            cursor = c.execute(
                'INSERT INTO tasks(title,project,due_date,start_time,end_time,priority,created_at,updated_at) '
                'VALUES(?,?,?,?,?,?,?,?)',
                ('مهمة نقل', project, '2026-09-20', '10:00', '11:00', 2,
                 '2026-09-01 00:00:00', '2026-09-01 00:00:00'))
            task_id = cursor.lastrowid
        self.created_tasks.append(task_id)
        item = [i for i in store.load_items(date(2026, 9, 20), date(2026, 9, 20))
                if i.get('task_id') == task_id][0]
        self.assertTrue(store.move_item(item, date(2026, 9, 21), 13 * 60, 14 * 60))
        with storage.connect() as c:
            row = c.execute('SELECT due_date,start_time,end_time FROM tasks WHERE id=?', (task_id,)).fetchone()
        self.assertEqual(tuple(row), ('2026-09-21', '13:00', '14:00'))

    def test_toggle_task_completed(self):
        project = 'مشروع-إتمام-' + str(time.time())
        with storage.connect() as c:
            cursor = c.execute(
                'INSERT INTO tasks(title,project,due_date,priority,created_at,updated_at) '
                'VALUES(?,?,?,?,?,?)',
                ('مهمة إتمام', project, '2026-09-25', 2,
                 '2026-09-01 00:00:00', '2026-09-01 00:00:00'))
            task_id = cursor.lastrowid
        self.created_tasks.append(task_id)
        self.assertTrue(store.toggle_task_completed(task_id))
        self.assertTrue(store.toggle_task_completed(task_id) is False)
        item = store.get_task_item(task_id)
        self.assertFalse(item['completed'])

    def test_reminder_window(self):
        calendar_id = self._calendar()
        now = datetime(2026, 10, 5, 9, 0)

        def event(name, start, reminder):
            event_id = store.create_event(calendar_id, name, start,
                                          start + timedelta(hours=1),
                                          reminder_minutes=reminder)
            self.created_events.append(event_id)
            return event_id

        soon = event('بعد خمس دقائق', now + timedelta(minutes=5), 10)
        later = event('بعد ساعة', now + timedelta(hours=1), 10)
        disabled = event('بدون تذكير', now + timedelta(minutes=5), -1)
        candidates = {i.get('event_id') for i in store.reminder_candidates(now)}
        self.assertIn(soon, candidates)
        self.assertNotIn(later, candidates)
        self.assertNotIn(disabled, candidates)

    def test_reminder_long_window_into_tomorrow(self):
        calendar_id = self._calendar()
        now = datetime(2026, 10, 5, 20, 0)
        event_id = store.create_event(
            calendar_id, 'غدًا صباحًا', datetime(2026, 10, 6, 8, 0),
            datetime(2026, 10, 6, 9, 0), reminder_minutes=24 * 60)
        self.created_events.append(event_id)
        candidates = {i.get('event_id') for i in store.reminder_candidates(now)}
        self.assertIn(event_id, candidates)

    def test_reminder_late_night_for_next_day(self):
        calendar_id = self._calendar()
        now = datetime(2026, 10, 5, 23, 55)
        event_id = store.create_event(
            calendar_id, 'بعد منتصف الليل', datetime(2026, 10, 6, 0, 5),
            datetime(2026, 10, 6, 1, 0), reminder_minutes=10)
        self.created_events.append(event_id)
        candidates = {i.get('event_id') for i in store.reminder_candidates(now)}
        self.assertIn(event_id, candidates)

    def test_reminder_all_day_at_nine(self):
        calendar_id = self._calendar()
        event_id = store.create_event(calendar_id, 'عيد', datetime(2026, 10, 7),
                                      is_all_day=True, reminder_minutes=10)
        self.created_events.append(event_id)
        morning = {i.get('event_id') for i in store.reminder_candidates(datetime(2026, 10, 7, 9, 1))}
        self.assertIn(event_id, morning)
        early = {i.get('event_id') for i in store.reminder_candidates(datetime(2026, 10, 7, 8, 0))}
        self.assertNotIn(event_id, early)

    def test_reminder_skips_hidden_calendar(self):
        calendar_id = self._calendar()
        now = datetime(2026, 10, 8, 9, 0)
        event_id = store.create_event(calendar_id, 'مخفي', now + timedelta(minutes=5),
                                      now + timedelta(hours=1), reminder_minutes=10)
        self.created_events.append(event_id)
        store.set_calendar_visible(calendar_id, False)
        try:
            candidates = {i.get('event_id') for i in store.reminder_candidates(now)}
            self.assertNotIn(event_id, candidates)
        finally:
            store.set_calendar_visible(calendar_id, True)

    def test_recurring_event_delete_and_override_persist(self):
        calendar_id = self._calendar()
        event_id = store.create_event(
            calendar_id, 'أسبوعي', datetime(2026, 10, 12, 9, 0),
            datetime(2026, 10, 12, 10, 0), rrule='FREQ=WEEKLY')
        self.created_events.append(event_id)
        store.cancel_event_occurrence(event_id, date(2026, 10, 19))
        store.set_event_override(event_id, date(2026, 10, 26),
                                 {'title': 'عنوان مستثنى', 'start': '11:00', 'end': '12:00'})
        items = [i for i in store.load_items(date(2026, 10, 12), date(2026, 10, 31))
                 if i.get('event_id') == event_id]
        by_date = {i['occurrence_date']: i for i in items}
        self.assertNotIn(date(2026, 10, 19), by_date)
        self.assertIn(date(2026, 10, 26), by_date)
        self.assertEqual(by_date[date(2026, 10, 26)]['title'], 'عنوان مستثنى')
        self.assertEqual(by_date[date(2026, 10, 26)]['start_min'], 11 * 60)


if __name__ == '__main__':
    unittest.main()
