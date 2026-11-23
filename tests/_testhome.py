# Rasd - مجلد بيانات مشترك لكل اختبارات الجلسة الواحدة.
# يُستورد قبل storage حتى تستخدم كل الملفات نفس قاعدة البيانات المؤقتة،
# ويُحذف المجلد مرة واحدة عند انتهاء العملية بدل حذفه بين ملفات الاختبار.
import atexit
import os
import shutil
import tempfile

HOME = os.environ.get('RASD_TEST_HOME')
if not HOME:
    HOME = tempfile.mkdtemp(prefix='rasd_test_')
    os.environ['RASD_TEST_HOME'] = HOME

os.environ['LOCALAPPDATA'] = HOME


def _cleanup():
    shutil.rmtree(HOME, ignore_errors=True)


atexit.register(_cleanup)
