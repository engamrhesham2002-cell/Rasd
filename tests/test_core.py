# Rasd - اختبارات سريعة للدوال الأساسية (stdlib unittest)
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEST_HOME = tempfile.mkdtemp(prefix='rasd_test_')
os.environ['LOCALAPPDATA'] = TEST_HOME

import storage  # noqa: E402  (يجب ضبط LOCALAPPDATA قبله)
import sync_ops  # noqa: E402
import tasks_utils  # noqa: E402
import update_utils  # noqa: E402
import repositories  # noqa: E402
import i18n  # noqa: E402
import localize_ui  # noqa: E402
import preview_render  # noqa: E402
import file_ops  # noqa: E402


def tearDownModule():
    shutil.rmtree(TEST_HOME, ignore_errors=True)


class CoreTests(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(storage.classify('.pdf'), 'PDF')
        self.assertEqual(storage.classify('dwg'), 'لوحات CAD')
        self.assertEqual(storage.classify('.xlsx'), 'Excel')
        self.assertEqual(storage.classify(''), 'بدون امتداد')

    def test_sizefmt(self):
        self.assertEqual(storage.sizefmt(0), '0 B')
        self.assertEqual(storage.sizefmt(1024), '1 KB')
        self.assertEqual(storage.sizefmt(1024 * 1024), '1 MB')
        self.assertEqual(storage.sizefmt(512 * 1024), '512 KB')

    def test_tag_badges(self):
        badges = storage.tag_badges('ري زراع')
        self.assertIn('🟢', badges)
        self.assertIn('🟡', badges)

    def test_is_project_path(self):
        self.assertFalse(storage.is_project_path(storage.LOG))
        self.assertTrue(storage.is_project_path(storage.LOG / 'Project'))

    def test_file_rows_sql(self):
        path = str(storage.LOG / 'Project' / 'a.pdf')
        with storage.connect() as c:
            c.execute(
                'insert or replace into files(path,project,rel,name,ext,size,mtime,last_open,indexed) '
                'values(?,?,?,?,?,?,?,?,?)',
                (path, 'Project', 'a.pdf', 'a.pdf', '.pdf', 1234, 1700000000.0, None, 'x'),
            )
            c.execute('insert or replace into tags(path,tag) values(?,?)', (path, 'ري'))
            rows = c.execute(storage.FILE_ROWS_SQL, ('Project',)).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['name'], 'a.pdf')
        self.assertEqual(rows[0]['tags'], 'ري')

    def test_next_recurring_date_month_end(self):
        from datetime import date
        self.assertEqual(tasks_utils.next_recurring_date('2026-01-31', 'شهرياً'), date(2026, 2, 28))
        self.assertEqual(tasks_utils.next_recurring_date('2024-01-31', 'شهرياً'), date(2024, 2, 29))
        self.assertEqual(tasks_utils.next_recurring_date('2026-12-31', 'شهرياً'), date(2027, 1, 31))
        self.assertEqual(tasks_utils.next_recurring_date('2026-03-15', 'شهرياً'), date(2026, 4, 15))
        self.assertEqual(tasks_utils.next_recurring_date('2026-03-15', 'يومياً'), date(2026, 3, 16))
        self.assertEqual(tasks_utils.next_recurring_date('2026-03-15', 'أسبوعياً'), date(2026, 3, 22))
        self.assertIsNone(tasks_utils.next_recurring_date('bad', 'شهرياً'))

    def test_safe_zip_target_rejects_zip_slip(self):
        root = storage.LOG
        self.assertIsNone(sync_ops.safe_zip_target(root, 'Project/../../evil.txt'))
        self.assertIsNone(sync_ops.safe_zip_target(root, '../evil.txt'))
        self.assertIsNone(sync_ops.safe_zip_target(root, 'C:/Windows/evil.txt'))
        target = sync_ops.safe_zip_target(root, 'Project/sub/file.txt')
        self.assertIsNotNone(target)
        self.assertTrue(str(target).startswith(str(root.resolve())))

    def test_cleanup_history_removes_old_rows(self):
        old_time = '2000-01-01 00:00'
        with storage.connect() as c:
            c.execute("insert into file_changes(project,path,kind,changed_at) values('P','x','added',?)", (old_time,))
            c.execute("insert into activity_log(project,action,details,path,occurred_at) values('P','a','d','x',?)", (old_time,))
            c.execute("insert into file_open_history(project,path,opened_at) values('P','x',?)", (old_time,))
            c.execute("insert into file_changes(project,path,kind,changed_at) values('P','y','added',?)", (storage.stamp(time.time()),))
        removed = storage.cleanup_history(force=True)
        with storage.connect() as c:
            old = c.execute("select count(*) from file_changes where path='x'").fetchone()[0]
            new = c.execute("select count(*) from file_changes where path='y'").fetchone()[0]
        self.assertEqual(old, 0)
        self.assertEqual(new, 1)
        self.assertGreaterEqual(removed, 3)

    def test_cleanup_orphans_removes_stale_rows(self):
        root = storage.LOG / 'OrphanProj'
        (root / 'KeepFolder').mkdir(parents=True, exist_ok=True)
        kept = str(root / 'keep.pdf')
        gone = str(root / 'gone.pdf')
        now = storage.stamp(time.time())
        with storage.connect() as c:
            c.execute(
                'insert or replace into files(path,project,rel,name,ext,size,mtime,last_open,indexed) '
                'values(?,?,?,?,?,?,?,?,?)',
                (kept, 'OrphanProj', 'keep.pdf', 'keep.pdf', '.pdf', 1, 1.0, None, 'x'),
            )
            c.execute("insert into project_scan_state(project,initial_scan_done) values('OrphanProj',1) "
                      "on conflict(project) do update set initial_scan_done=1")
            c.execute("insert or ignore into file_links(project,path1,path2) values('OrphanProj',?,?)", (kept, gone))
            c.execute("insert or ignore into file_links(project,path1,path2) values('OrphanProj',?,?)", (kept, kept))
            c.execute("insert or ignore into favorites(project,path,kind,created) values('OrphanProj',?,'file',?)", (gone, now))
            c.execute("insert or ignore into favorites(project,path,kind,created) values('OrphanProj',?,'file',?)", (kept, now))
            c.execute("insert or ignore into folder_tags(project,path,tag,created) values('OrphanProj','KeepFolder','t',?)", (now,))
            c.execute("insert or ignore into folder_tags(project,path,tag,created) values('OrphanProj','GoneFolder','t',?)", (now,))
        removed = storage.cleanup_orphans(force=True)
        with storage.connect() as c:
            links = c.execute("select count(*) from file_links where project='OrphanProj'").fetchone()[0]
            favorites = c.execute("select count(*) from favorites where project='OrphanProj' and kind='file'").fetchone()[0]
            folder_tags = c.execute("select count(*) from folder_tags where project='OrphanProj'").fetchone()[0]
        self.assertEqual(links, 1)
        self.assertEqual(favorites, 1)
        self.assertEqual(folder_tags, 1)
        self.assertGreaterEqual(removed, 3)

    def test_pending_update_rejects_tampered_file(self):
        installer = storage.LOG / 'fake_update.exe'
        installer.write_bytes(b'original-bytes')
        good = update_utils.file_sha256(installer)
        self.assertEqual(good, hashlib.sha256(b'original-bytes').hexdigest())
        self.assertTrue(update_utils.queue_pending_update(installer, 'standard', 'v999.0', good))
        payload = json.loads(update_utils.UPDATE_PENDING.read_text(encoding='utf-8'))
        self.assertEqual(payload['sha256'], good)
        installer.write_bytes(b'tampered-bytes')
        self.assertFalse(update_utils.launch_pending_update_at_start())
        self.assertFalse(update_utils.UPDATE_PENDING.exists())

    def test_pdf_render_scale_caps_huge_pages(self):
        for w, h in ((595, 842), (3370, 2384), (20000, 15000), (200000, 150000), (2000000, 1500000)):
            scale = preview_render.pdf_render_scale(w, h)
            self.assertGreater(scale, 0)
            self.assertLessEqual(w * scale, preview_render.MAX_PDF_PIXEL_SIDE + 1)
            self.assertLessEqual(h * scale, preview_render.MAX_PDF_PIXEL_SIDE + 1)
            self.assertLessEqual((w * scale) * (h * scale), preview_render.MAX_PDF_PIXELS * 1.01)

    def test_pdf_render_scale_keeps_normal_pages_readable(self):
        scale = preview_render.pdf_render_scale(595, 842)
        self.assertLessEqual(595 * scale, 761)
        self.assertGreaterEqual(595 * scale, 400)
        self.assertGreater(scale, 0.35)

    def test_arabic_ui_counter_translation_keeps_user_names(self):
        previous = i18n.get_language()
        try:
            i18n.set_language('en')
            self.assertEqual(i18n.tr('صفحة PDF: 2 من 7'), 'PDF page: 2 of 7')
            self.assertEqual(i18n.tr('صفحة PDF نصية: 1 من 3'), 'Text PDF page: 1 of 3')
            self.assertEqual(i18n.tr('1,234 صف × 12 عمود من 5,000'),
                             '1,234 rows × 12 columns of 5,000')
            # بيانات المستخدم لا تُترجم ولو احتوت «من» أو أرقامًا حولها.
            self.assertEqual(i18n.tr('تقرير 3 من 5'), 'تقرير 3 من 5')
            self.assertEqual(i18n.tr('هندس احمد من ملفات مرسله'), 'هندس احمد من ملفات مرسله')
        finally:
            i18n.set_language(previous)

    def test_verbatim_variable_skips_translation(self):
        class FakeVariable:
            _rasd_no_translate = True
            _rasd_i18n_var_original = 'هندس احمد من ملفات مرسله'

        self.assertEqual(localize_ui._reverse_variable_value(FakeVariable(), 'of'), 'of')

        class TranslatedVariable:
            _rasd_i18n_var_original = 'إعادة تسمية'

        previous = i18n.get_language()
        try:
            i18n.set_language('en')
            self.assertEqual(localize_ui._reverse_variable_value(TranslatedVariable(), 'Rename'),
                             'إعادة تسمية')
        finally:
            i18n.set_language(previous)

    def test_arabic_preview_text_is_shaped(self):
        if preview_render._arabic_reshaper is None or preview_render._bidi_get_display is None:
            self.skipTest('arabic-reshaper/python-bidi غير متاحين')
        shown = preview_render.PreviewRenderMixin._display_text(None, 'عقد من الشركة')
        self.assertNotEqual(shown, 'عقد من الشركة')
        self.assertTrue(any('\ufe70' <= ch <= '\ufeff' for ch in shown))

    def test_nav_bar_side_not_mirrored_in_english(self):
        class FakeWidget:
            master = None

        previous = i18n.get_language()
        try:
            i18n.set_language('en')
            pinned = FakeWidget()
            pinned._rasd_no_side_mirror = True
            opts = localize_ui._mirror_options({'side': 'left', 'anchor': 'e'}, pinned)
            self.assertEqual(opts['side'], 'left')
            self.assertEqual(opts['anchor'], 'w')

            parent = FakeWidget()
            parent._rasd_natural_order = True
            child = FakeWidget()
            child.master = parent
            self.assertEqual(localize_ui._mirror_options({'side': 'left'}, child)['side'], 'left')

            natural = FakeWidget()
            natural._rasd_natural_layout = True
            opts = localize_ui._mirror_options({'side': 'left', 'anchor': 'e', 'sticky': 'ew'}, natural)
            self.assertEqual(opts, {'side': 'left', 'anchor': 'e', 'sticky': 'ew'})
            nested = FakeWidget()
            nested.master = natural
            self.assertEqual(localize_ui._mirror_options({'side': 'left', 'anchor': 'e'}, nested),
                             {'side': 'left', 'anchor': 'e'})

            self.assertEqual(localize_ui._mirror_options({'side': 'left'}, FakeWidget())['side'], 'right')
            self.assertEqual(localize_ui._mirror_options({'side': 'left'})['side'], 'right')

            i18n.set_language('ar')
            self.assertEqual(localize_ui._mirror_options({'side': 'left'}, FakeWidget())['side'], 'left')
            self.assertEqual(localize_ui._mirror_options({'side': 'left', 'anchor': 'e'}, pinned)['anchor'], 'e')
        finally:
            i18n.set_language(previous)

    def test_update_helper_avoids_console_pipes(self):
        script = update_utils._UPDATE_HELPER_SCRIPT
        self.assertTrue(script.isascii())
        lowered = script.lower()
        for blocked in ('tasklist', 'find /i', 'cmd.exe'):
            self.assertNotIn(blocked, lowered)
        self.assertIn('get-process -id $apppid', lowered)
        self.assertIn('start-process -filepath $installer', lowered)
        self.assertIn('/silent', lowered)

    def test_start_scheduled_update_writes_utf8_job(self):
        installer = Path(TEST_HOME) / 'مجلد™' / 'RasdSetup.exe'
        installer.parent.mkdir(parents=True, exist_ok=True)
        installer.write_bytes(b'fake-installer')
        calls = []
        original = update_utils.subprocess.Popen

        class FakeProc:
            pid = 1

        def fake_popen(args, **kwargs):
            calls.append((list(args), dict(kwargs)))
            return FakeProc()

        update_utils.subprocess.Popen = fake_popen
        try:
            ok = update_utils.start_scheduled_update(4321, installer, Path(TEST_HOME), Path(TEST_HOME) / 'Rasd.exe')
        finally:
            update_utils.subprocess.Popen = original
        self.assertTrue(ok)
        job = json.loads(update_utils.UPDATE_JOB.read_text(encoding='utf-8'))
        self.assertEqual(job['installer'], str(installer.resolve()))
        self.assertEqual(job['pid'], 4321)
        self.assertIn('™', update_utils.UPDATE_JOB.read_text(encoding='utf-8'))
        self.assertTrue(update_utils.UPDATE_HELPER.read_bytes().isascii())
        self.assertEqual(len(calls), 1)
        args, kwargs = calls[0]
        self.assertEqual(args[0], update_utils._powershell_exe())
        self.assertIn('-AppPid', args)
        self.assertNotIn('cmd.exe', ' '.join(args).lower())
        self.assertEqual(kwargs['creationflags'] & 0x08000000, 0x08000000)
        self.assertFalse(update_utils.UPDATE_PENDING.exists())
        self.assertFalse((update_utils.UPDATE_HOME / 'run_update.bat').exists())

    def test_launch_pending_update_removes_legacy_bat(self):
        update_utils.UPDATE_HOME.mkdir(parents=True, exist_ok=True)
        update_utils.UPDATE_PENDING.unlink(missing_ok=True)
        legacy = update_utils.UPDATE_HOME / 'run_update.bat'
        legacy.write_text('@echo off\n', encoding='utf-8')
        self.assertFalse(update_utils.launch_pending_update_at_start())
        self.assertFalse(legacy.exists())

    def test_rename_migrates_related_rows(self):
        root = storage.LOG / 'RenameMigrateProj'
        old = root / 'OldFolder'
        new = root / 'NewFolder'
        old_file = str(old / 'a.txt')
        new_file = str(new / 'a.txt')
        now = storage.stamp(time.time())
        with storage.connect() as c:
            c.execute('insert or replace into files(path,project,rel,name,ext,size,mtime,last_open,indexed) '
                      'values(?,?,?,?,?,?,?,?,?)',
                      (old_file, 'RenameMigrateProj', 'OldFolder/a.txt', 'a.txt', '.txt', 1, 1.0, None, 'x'))
            c.execute('insert or replace into tags(path,tag) values(?,?)', (old_file, 'tag1'))
            c.execute('insert or replace into folder_tags(project,path,tag,created) values(?,?,?,?)',
                      ('RenameMigrateProj', 'OldFolder', 'ftag', now))
            c.execute('insert or replace into favorites(project,path,kind,created) values(?,?,?,?)',
                      ('RenameMigrateProj', old_file, 'file', now))
            c.execute('insert or ignore into file_links(project,path1,path2) values(?,?,?)',
                      ('RenameMigrateProj', old_file, old_file))
            c.execute('insert into file_open_history(project,path,opened_at) values(?,?,?)',
                      ('RenameMigrateProj', old_file, now))
        fake = type('FakeApp', (), {'root': root, 'project': 'RenameMigrateProj'})()
        file_ops.FileOpsMixin._migrate_renamed_path(fake, old, new)
        with storage.connect() as c:
            file_row = c.execute('select path,rel,name from files where project=?', ('RenameMigrateProj',)).fetchone()
            tag_row = c.execute('select path from tags where tag=?', ('tag1',)).fetchone()
            folder_row = c.execute('select path from folder_tags where project=?', ('RenameMigrateProj',)).fetchone()
            fav_row = c.execute('select path from favorites where project=?', ('RenameMigrateProj',)).fetchone()
            link_row = c.execute('select path1,path2 from file_links where project=?', ('RenameMigrateProj',)).fetchone()
            hist_row = c.execute('select path from file_open_history where project=?', ('RenameMigrateProj',)).fetchone()
        self.assertEqual(file_row['path'], new_file)
        self.assertEqual(file_row['rel'], 'NewFolder/a.txt')
        self.assertEqual(tag_row['path'], new_file)
        self.assertEqual(folder_row['path'], 'NewFolder')
        self.assertEqual(fav_row['path'], new_file)
        self.assertEqual(tuple(link_row), (new_file, new_file))
        self.assertEqual(hist_row['path'], new_file)

    def test_project_summary_reads_counts_tags_and_cover(self):
        root = storage.LOG / 'SummaryProj'
        root.mkdir(parents=True, exist_ok=True)
        doc = str(root / 'a.pdf')
        pic = str(root / 'cover.png')
        with storage.connect() as c:
            c.execute('insert or replace into files(path,project,rel,name,ext,size,mtime,last_open,indexed) '
                      'values(?,?,?,?,?,?,?,?,?)', (doc, 'SummaryProj', 'a.pdf', 'a.pdf', '.pdf', 10, 5.0, None, 'x'))
            c.execute('insert or replace into files(path,project,rel,name,ext,size,mtime,last_open,indexed) '
                      'values(?,?,?,?,?,?,?,?,?)', (pic, 'SummaryProj', 'cover.png', 'cover.png', '.png', 20, 6.0, None, 'x'))
            c.execute('insert or replace into tags(path,tag) values(?,?)', (doc, 'ري'))
            c.execute("insert or ignore into favorites(project,path,kind,created) values('SummaryProj',?,'folder',?)",
                      (str(root), storage.stamp(time.time())))
        summary = repositories.project_summary()
        self.assertEqual(summary['counts']['SummaryProj'][0], 2)
        self.assertIn('SummaryProj', summary['favorite_projects'])
        self.assertIn('ري', summary['tag_map']['SummaryProj'])
        self.assertEqual(summary['cover_map']['SummaryProj'], pic)

    def test_run_once_is_idempotent(self):
        with storage.connect() as c:
            c.execute('create table if not exists _test_run_once(x integer)')
            storage._run_once(c, 'test_run_once_key', 'insert into _test_run_once(x) values(1)')
        with storage.connect() as c:
            storage._run_once(c, 'test_run_once_key', 'insert into _test_run_once(x) values(1)')
            self.assertEqual(c.execute('select count(*) from _test_run_once').fetchone()[0], 1)


class CalendarTests(unittest.TestCase):
    def setUp(self):
        import calendar_store
        import calendar_core
        self.store = calendar_store
        self.core = calendar_core
        calendar_store.ensure_calendar_schema()
        self.created_calendars = []
        self.created_events = []
        self.created_tasks = []

    def tearDown(self):
        with storage.connect() as c:
            for event_id in self.created_events:
                c.execute('DELETE FROM calendar_events WHERE id=?', (event_id,))
            for task_id in self.created_tasks:
                c.execute('DELETE FROM tasks WHERE id=?', (task_id,))
            for calendar_id in self.created_calendars:
                c.execute('DELETE FROM calendars WHERE id=?', (calendar_id,))

    def _calendar(self, name='تقويم اختبار'):
        calendar_id = self.store.add_calendar(name + '-' + str(time.time()), '#3366CC')
        self.created_calendars.append(calendar_id)
        return calendar_id

    def test_rrule_parse_build(self):
        rule = self.core.parse_rrule('RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=SU,MO;COUNT=5')
        self.assertEqual(rule['freq'], 'WEEKLY')
        self.assertEqual(rule['interval'], 2)
        self.assertEqual(rule['byday'], ['SU', 'MO'])
        self.assertEqual(rule['count'], 5)
        built = self.core.build_rrule('WEEKLY', 2, ['SU'])
        self.assertIn('FREQ=WEEKLY', built)
        self.assertIn('INTERVAL=2', built)
        self.assertIn('BYDAY=SU', built)

    def test_weekly_byday_expands_inside_range(self):
        from datetime import datetime, timedelta
        base = datetime(2026, 3, 1, 9, 0)  # الأحد
        rule = self.core.build_rrule('WEEKLY', 1, ['SU', 'WE'])
        values = self.core.expand_occurrences(
            base, timedelta(hours=1), rule,
            datetime(2026, 3, 1), datetime(2026, 3, 15))
        dates = [item['occurrence_date'] for item in values]
        self.assertEqual(dates, [date(2026, 3, 1), date(2026, 3, 4),
                                 date(2026, 3, 8), date(2026, 3, 11)])

    def test_count_and_until_limit_series(self):
        from datetime import datetime, timedelta
        base = datetime(2026, 3, 1, 9, 0)
        values = self.core.expand_occurrences(
            base, timedelta(hours=1), 'FREQ=DAILY;COUNT=3',
            datetime(2026, 3, 1), datetime(2026, 3, 10))
        self.assertEqual(len(values), 3)
        values = self.core.expand_occurrences(
            base, timedelta(hours=1), 'FREQ=DAILY;UNTIL=20260304',
            datetime(2026, 3, 1), datetime(2026, 3, 10))
        self.assertEqual(len(values), 3)

    def test_cancelled_occurrence_is_skipped(self):
        from datetime import datetime, timedelta
        base = datetime(2026, 3, 1, 9, 0)
        overrides = {'2026-03-02': {'cancelled': True}}
        values = self.core.expand_occurrences(
            base, timedelta(hours=1), 'FREQ=DAILY', datetime(2026, 3, 1),
            datetime(2026, 3, 4), None, overrides)
        self.assertEqual([item['occurrence_date'] for item in values],
                         [date(2026, 3, 1), date(2026, 3, 3)])

    def test_override_moves_single_occurrence(self):
        from datetime import datetime, timedelta
        base = datetime(2026, 3, 1, 9, 0)
        overrides = {'2026-03-02': {'date': '2026-03-05', 'start': '14:00', 'end': '15:30'}}
        values = self.core.expand_occurrences(
            base, timedelta(hours=1), 'FREQ=DAILY', datetime(2026, 3, 1),
            datetime(2026, 3, 8), None, overrides)
        moved = [item for item in values if item.get('rule_date') == date(2026, 3, 2)][0]
        self.assertEqual(moved['occurrence_date'], date(2026, 3, 5))
        self.assertEqual(moved['start'].strftime('%H:%M'), '14:00')
        self.assertEqual(moved['end'].strftime('%H:%M'), '15:30')

    def test_utc_roundtrip_keeps_local_time(self):
        from datetime import datetime
        local = datetime(2026, 7, 1, 13, 45)
        stored = self.core.local_to_utc_iso(local)
        self.assertTrue(stored.endswith('+00:00'))
        self.assertEqual(self.core.utc_iso_to_local(stored), local)

    def test_layout_overlaps_assigns_parallel_lanes(self):
        events = [
            {'start_min': 60, 'end_min': 120},
            {'start_min': 90, 'end_min': 150},
            {'start_min': 200, 'end_min': 230},
        ]
        max_lanes = self.core.layout_overlaps(events)
        self.assertEqual(max_lanes, 2)
        overlapping = [item for item in events if item['start_min'] in (60, 90)]
        self.assertEqual(sorted(item['lane'] for item in overlapping), [0, 1])
        self.assertEqual(overlapping[0]['lanes'], 2)

    def test_store_event_crud_and_visibility(self):
        from datetime import datetime
        calendar_id = self._calendar()
        event_id = self.store.create_event(
            calendar_id, 'اجتماع اختبار', datetime(2026, 3, 10, 14, 0),
            datetime(2026, 3, 10, 15, 0), location='غرفة 1', reminder_minutes=10)
        self.created_events.append(event_id)
        items = self.store.load_items(date(2026, 3, 10), date(2026, 3, 10))
        matched = [item for item in items if item.get('event_id') == event_id]
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]['start_min'], 14 * 60)
        self.assertEqual(matched[0]['end_min'], 15 * 60)
        self.store.set_calendar_visible(calendar_id, False)
        items = self.store.load_items(date(2026, 3, 10), date(2026, 3, 10))
        self.assertFalse([item for item in items if item.get('event_id') == event_id])
        self.store.set_calendar_visible(calendar_id, True)

    def test_store_recurring_event_override_and_cancel(self):
        from datetime import datetime
        calendar_id = self._calendar()
        event_id = self.store.create_event(
            calendar_id, 'متكرر اختبار', datetime(2026, 3, 1, 9, 0),
            datetime(2026, 3, 1, 10, 0), rrule='FREQ=DAILY')
        self.created_events.append(event_id)
        self.store.cancel_event_occurrence(event_id, date(2026, 3, 2))
        overrides = self.core.parse_json_dict(self.store.get_event(event_id)['overrides'])
        self.assertTrue(overrides['2026-03-02']['cancelled'])
        items = self.store.load_items(date(2026, 3, 1), date(2026, 3, 3))
        dates = [item['occurrence_date'] for item in items if item.get('event_id') == event_id]
        self.assertEqual(dates, [date(2026, 3, 1), date(2026, 3, 3)])

    def test_load_items_merges_tasks_and_events(self):
        from datetime import datetime
        project = 'مشروع-تقويم-اختبار'
        with storage.connect() as c:
            cursor = c.execute(
                'INSERT INTO tasks(title,project,due_date,start_time,end_time,priority,created_at,updated_at) '
                'VALUES(?,?,?,?,?,?,?,?)',
                ('مهمة تقويم', project, '2026-04-05', '10:00', '11:00', 2,
                 '2026-04-01 00:00:00', '2026-04-01 00:00:00'))
            task_id = cursor.lastrowid
        self.created_tasks.append(task_id)
        calendar_id = self._calendar()
        event_id = self.store.create_event(
            calendar_id, 'موعد تقويم', datetime(2026, 4, 5, 12, 0),
            datetime(2026, 4, 5, 13, 0))
        self.created_events.append(event_id)
        items = self.store.load_items(date(2026, 4, 5), date(2026, 4, 5), project)
        sources = {(item['source'], item.get('task_id'), item.get('event_id')) for item in items}
        self.assertIn(('task', task_id, None), sources)
        self.assertIn(('event', None, event_id), sources)

    def test_calendar_ui_translations(self):
        previous = i18n.get_language()
        try:
            i18n.set_language('en')
            self.assertEqual(i18n.tr('تقويماتي'), 'My calendars')
            self.assertEqual(i18n.tr('كل اليوم'), 'All day')
            self.assertEqual(i18n.tr('هذا الموعد فقط'), 'This event only')
            self.assertEqual(i18n.tr('الأحد 05 مارس 2026'), 'Sunday 05 March 2026')
        finally:
            i18n.set_language(previous)

    def test_all_day_event_on_range_start_is_visible(self):
        from datetime import datetime
        calendar_id = self._calendar()
        day = date(2026, 6, 1)
        event_id = self.store.create_event(calendar_id, 'عيد ميلاد', datetime.combine(day, datetime.min.time()),
                                           is_all_day=True)
        self.created_events.append(event_id)
        items = self.store.load_items(day, day)
        matched = [item for item in items if item.get('event_id') == event_id]
        self.assertEqual(len(matched), 1)
        self.assertTrue(matched[0]['all_day'])

    def test_move_item_creates_override_for_recurring_event(self):
        from datetime import datetime
        calendar_id = self._calendar()
        event_id = self.store.create_event(
            calendar_id, 'نقل اختبار', datetime(2026, 5, 4, 9, 0),
            datetime(2026, 5, 4, 10, 0), rrule='FREQ=WEEKLY')
        self.created_events.append(event_id)
        items = self.store.load_items(date(2026, 5, 11), date(2026, 5, 11))
        occurrence = [item for item in items if item.get('event_id') == event_id][0]
        self.store.move_item(occurrence, date(2026, 5, 12), 15 * 60, 16 * 60)
        overrides = self.core.parse_json_dict(self.store.get_event(event_id)['overrides'])
        self.assertIn('2026-05-11', overrides)
        self.assertEqual(overrides['2026-05-11']['date'], '2026-05-12')
        self.assertEqual(overrides['2026-05-11']['start'], '15:00')


if __name__ == '__main__':
    unittest.main()
