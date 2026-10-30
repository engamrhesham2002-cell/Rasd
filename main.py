# Rasd - ملف التشغيل الرئيسي
from rasd_app import App
from update_utils import launch_pending_update_at_start
from perf import configure as configure_perf
from storage import LOG

if __name__ == '__main__':
 configure_perf(LOG / 'rasd.log')
 if not launch_pending_update_at_start(): App().mainloop()
