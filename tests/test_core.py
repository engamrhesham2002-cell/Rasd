# Rasd - اختبارات سريعة للدوال الأساسية (stdlib unittest)
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

    def test_run_once_is_idempotent(self):
        with storage.connect() as c:
            c.execute('create table if not exists _test_run_once(x integer)')
            storage._run_once(c, 'test_run_once_key', 'insert into _test_run_once(x) values(1)')
        with storage.connect() as c:
            storage._run_once(c, 'test_run_once_key', 'insert into _test_run_once(x) values(1)')
            self.assertEqual(c.execute('select count(*) from _test_run_once').fetchone()[0], 1)


if __name__ == '__main__':
    unittest.main()
