# Rasd - ملف التشغيل الرئيسي
from rasd_app import App
from update_utils import launch_pending_update_at_start

if __name__ == '__main__':
 if not launch_pending_update_at_start(): App().mainloop()
