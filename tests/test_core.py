# Rasd - اختبارات سريعة للدوال الأساسية (stdlib unittest)
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEST_HOME = tempfile.mkdtemp(prefix='rasd_test_')
os.environ['LOCALAPPDATA'] = TEST_HOME

import storage  # noqa: E402  (يجب ضبط LOCALAPPDATA قبله)


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

    def test_run_once_is_idempotent(self):
        with storage.connect() as c:
            c.execute('create table if not exists _test_run_once(x integer)')
            storage._run_once(c, 'test_run_once_key', 'insert into _test_run_once(x) values(1)')
        with storage.connect() as c:
            storage._run_once(c, 'test_run_once_key', 'insert into _test_run_once(x) values(1)')
            self.assertEqual(c.execute('select count(*) from _test_run_once').fetchone()[0], 1)


if __name__ == '__main__':
    unittest.main()
