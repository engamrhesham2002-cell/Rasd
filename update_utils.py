# Rasd - دوال التحقق من التحديثات وجدولة التثبيت الآمن
from common import *

def normalize_version(ver_str):
 """إزالة حرف v وأي مسافات لتسهيل المقارنة بدقة"""
 if not ver_str: return "0.0"
 return str(ver_str).strip().lower().lstrip('v').strip()

def compare_versions(v1, v2):
 """مقارنة ذكية بين رقمين إصدار لتحديد أيهما أحدث"""
 n1 = [int(x) for x in normalize_version(v1).split('.') if x.isdigit()]
 n2 = [int(x) for x in normalize_version(v2).split('.') if x.isdigit()]
 if n1 > n2: return 1
 if n1 < n2: return -1
 return 0

def check_for_updates_silently(current_version):
 try:
  url = "https://raw.githubusercontent.com/engamrhesham2002-cell/Rasd/main/version.json"
  req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
  with urllib.request.urlopen(req, timeout=3) as response:
   data = json.loads(response.read().decode('utf-8'))
   latest_version = data.get('latest_version', current_version)
   if compare_versions(latest_version, current_version) > 0:
    return True, latest_version
 except Exception:
  pass
 return False, current_version

def queue_pending_update(installer_path, mode='standard', tag=''):
 """حفظ بيانات التحديث الذي تم تنزيله ليتم تثبيته الآن أو في التشغيل القادم"""
 try:
  installer = Path(installer_path).resolve()
  if not installer.is_file():
   return False
  UPDATE_HOME.mkdir(parents=True, exist_ok=True)
  payload = {
   'installer': str(installer),
   'mode': str(mode or 'standard'),
   'tag': str(tag or ''),
   'target_dir': str(BASE.resolve()),
   'exe_path': str(Path(sys.executable).resolve()),
   'queued_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
  }
  UPDATE_PENDING.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
  return True
 except Exception as exc:
  try:
   UPDATE_HOME.mkdir(parents=True, exist_ok=True)
   UPDATE_FAILURE.write_text(f"تعذر حفظ بيانات التحديث المجدول:\n{exc}", encoding='utf-8')
  except Exception:
   pass
  return False

def start_scheduled_update(pid, installer_path, target_dir, exe_path):
 """تشغيل سكربت تحديث مستقل ينتظر إغلاق البرنامج ثم يثبت التحديث ويعيد تشغيل البرنامج"""
 try:
  installer = Path(installer_path).resolve()
  if not installer.is_file():
   return False
  UPDATE_HOME.mkdir(parents=True, exist_ok=True)
  bat_path = UPDATE_HOME / 'run_update.bat'
  failure_file = str(UPDATE_FAILURE.resolve())
  pending_file = str(UPDATE_PENDING.resolve())
  exe_str = str(Path(exe_path).resolve())
  inst_str = str(installer)
  
  # إذا كان البرنامج يعمل من ملف بايثون أثناء التطوير، نكتفي بتشغيل المثبت مباشرة
  is_frozen = getattr(sys, 'frozen', False)
  relaunch_cmd = f'start "" "{exe_str}"' if is_frozen else ''

  bat_content = f"""@echo off
chcp 65001 >nul
setlocal
set "PID={int(pid)}"
set "INSTALLER={inst_str}"
set "PENDING={pending_file}"
set "FAILURE={failure_file}"

:waitloop
tasklist /FI "PID eq %PID%" 2>NUL | find /I "%PID%" >NUL
if "%ERRORLEVEL%"=="0" (
    timeout /t 1 /nobreak >NUL
    goto waitloop
)

del /f /q "%PENDING%" 2>NUL
start "" /wait "%INSTALLER%" /SILENT /NORESTART
if errorlevel 1 (
    start "" "%INSTALLER%"
)
{relaunch_cmd}
endlocal
"""
  bat_path.write_text(bat_content, encoding='utf-8')
  flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000) | getattr(subprocess, 'DETACHED_PROCESS', 0x00000008)
  subprocess.Popen(['cmd.exe', '/c', str(bat_path)], cwd=str(UPDATE_HOME), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
  return True
 except Exception as exc:
  try:
   UPDATE_HOME.mkdir(parents=True, exist_ok=True)
   UPDATE_FAILURE.write_text(f"تعذر تشغيل مساعد التحديث:\n{exc}", encoding='utf-8')
  except Exception:
   pass
  return False

def launch_pending_update_at_start():
 """فحص وجود تحديث مؤجل عند بداية تشغيل البرنامج وتنفيذه قبل فتح الواجهة"""
 try:
  if not UPDATE_PENDING.is_file():
   return False
  data = json.loads(UPDATE_PENDING.read_text(encoding='utf-8'))
  installer = Path(data.get('installer', ''))
  tag = str(data.get('tag', ''))
  if not installer.is_file():
   UPDATE_PENDING.unlink(missing_ok=True)
   return False
  if tag and compare_versions(tag, APP_VERSION) <= 0:
   UPDATE_PENDING.unlink(missing_ok=True)
   return False
  if start_scheduled_update(os.getpid(), installer, BASE, sys.executable):
   return True
 except Exception:
  try: UPDATE_PENDING.unlink(missing_ok=True)
  except Exception: pass
 return False