# repositories.py - استعلامات قراءة فقط مركزية (تبدأ بملخص المشاريع)
from common import *
from storage import *


def project_summary():
    """ملخص المشاريع: أعداد الملفات، المفضلة، الهاشتاجات، وصور الأغلفة."""
    summary = {'counts': {}, 'favorite_projects': set(), 'tag_map': {}, 'cover_map': {}}
    with connect() as c:
        summary['counts'] = {r['project']: (r['n'], r['latest'])
                             for r in c.execute('select project,count(*) n,max(mtime) latest from files group by project')}
        summary['favorite_projects'] = {r['project']
                                        for r in c.execute('SELECT project FROM favorites WHERE kind="folder"')}
        for r in c.execute('select f.project,t.tag,count(*) n from tags t join files f on f.path=t.path '
                           'group by f.project,t.tag order by f.project,n desc'):
            summary['tag_map'].setdefault(r['project'], []).append(r['tag'])
        for r in c.execute("select project,min(path) path from files "
                           "where ext in ('.png','.jpg','.jpeg','.bmp','.tif','.tiff') group by project"):
            summary['cover_map'][r['project']] = r['path']
        # الغلاف المخصص (كليك يمين على المشروع) له الأولوية على أول صورة في المشروع
        try:
            for r in c.execute('select project,path from project_covers'):
                custom = Path(r['path'])
                if custom.is_file():
                    summary['cover_map'][r['project']] = str(custom)
        except sqlite3.OperationalError:
            pass
    return summary


def recent_project_names(limit=8):
    """أسماء آخر المشاريع زيارة بالترتيب."""
    with connect() as c:
        return [r['project'] for r in c.execute(
            'select project from project_visits order by last_visit desc limit ?', (limit,))]
