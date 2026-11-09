# Rasd - اختبارات سريعة للدوال الأساسية (stdlib unittest)
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
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


if __name__ == '__main__':
    unittest.main()
