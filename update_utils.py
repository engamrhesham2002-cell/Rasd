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

def file_sha256(path, chunk_size=1024 * 1024):
 """يحسب بصمة SHA-256 لملف بدون تحميله كله في الذاكرة."""
 try:
  digest = hashlib.sha256()
  with Path(path).open('rb') as handle:
   for block in iter(lambda: handle.read(chunk_size), b''):
    digest.update(block)
  return digest.hexdigest()
 except OSError:
  return ''

def queue_pending_update(installer_path, mode='standard', tag='', sha256=''):
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
   'sha256': str(sha256 or ''),
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

UPDATE_JOB = UPDATE_HOME / 'update_job.json'
UPDATE_HELPER = UPDATE_HOME / 'run_update.ps1'

# مساعد التحديث: سكربت PowerShell بترميز ASCII خالص. يقرأ مسار المثبت من ملف
# JSON بترميز UTF-8، لذلك لا تتأثر المسارات التي تحتوي حروفًا مثل ™ بترميز
# سطر الأوامر (وهو سبب فشل سكربت BAT القديم). يعمل بدون نافذة ومن دون أنابيب.
_UPDATE_HELPER_SCRIPT = r'''param([int]$AppPid = 0)
$ErrorActionPreference = 'SilentlyContinue'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$jobPath = Join-Path $here 'update_job.json'
$pendingPath = Join-Path $here 'pending.json'
$failurePath = Join-Path $here 'update_failed.txt'
$legacyBat = Join-Path $here 'run_update.bat'

$fallbackExe = Join-Path $env:LOCALAPPDATA 'Programs\Rasd\Rasd.exe'
$appExe = ''
if (Test-Path -LiteralPath $fallbackExe) { $appExe = $fallbackExe }
$installer = ''

function Exit-WithFailure([string]$text) {
    try {
        $enc = New-Object System.Text.UTF8Encoding($false)
        [System.IO.File]::WriteAllText($failurePath, $text, $enc)
    } catch { }
    try {
        if ($appExe -and (Test-Path -LiteralPath $appExe)) {
            Start-Process -FilePath $appExe
        }
    } catch { }
    exit 1
}

# Remove the legacy BAT helper and any old pending request
try { if (Test-Path -LiteralPath $legacyBat) { Remove-Item -LiteralPath $legacyBat -Force } } catch { }
try { if (Test-Path -LiteralPath $pendingPath) { Remove-Item -LiteralPath $pendingPath -Force } } catch { }

$job = $null
try {
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    if (Test-Path -LiteralPath $jobPath) {
        $raw = [System.IO.File]::ReadAllText($jobPath, $utf8)
        $job = $raw | ConvertFrom-Json
    }
} catch { $job = $null }

if ($job -eq $null) {
    Exit-WithFailure 'Update job file could not be read.'
}

$installer = [string]$job.installer
if ($job.exe_path) { $appExe = [string]$job.exe_path }

try { if (Test-Path -LiteralPath $jobPath) { Remove-Item -LiteralPath $jobPath -Force } } catch { }

if (-not $installer -or -not (Test-Path -LiteralPath $installer)) {
    Exit-WithFailure 'The downloaded update installer was not found.'
}

# Wait for the Rasd process that requested the update to exit (no pipes, no windows)
$deadline = (Get-Date).AddMinutes(10)
while ($AppPid -gt 0) {
    $running = Get-Process -Id $AppPid -ErrorAction SilentlyContinue
    if (-not $running) { break }
    if ((Get-Date) -gt $deadline) { break }
    Start-Sleep -Milliseconds 400
}
Start-Sleep -Milliseconds 900

# Silent install; fall back to the regular installer UI if silent start fails
$started = $false
try {
    $proc = Start-Process -FilePath $installer -ArgumentList '/SILENT','/NORESTART' -Wait -PassThru -ErrorAction Stop
    $started = $true
} catch { }

if (-not $started) {
    try {
        $proc = Start-Process -FilePath $installer -Wait -PassThru -ErrorAction Stop
        $started = $true
    } catch { }
}

if (-not $started) {
    Exit-WithFailure 'The update installer could not be started.'
}

# Some installers return before files settle; then relaunch the app
Start-Sleep -Milliseconds 1500
try { if (Test-Path -LiteralPath $failurePath) { Remove-Item -LiteralPath $failurePath -Force } } catch { }

if ($appExe -and (Test-Path -LiteralPath $appExe)) {
    try { Start-Process -FilePath $appExe } catch { }
}

exit 0
'''


def _powershell_exe():
 """مسار PowerShell النظامي إن وُجد، وإلا الاسم المجرد من PATH"""
 for candidate in (
  Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32' / 'WindowsPowerShell' / 'v1.0' / 'powershell.exe',
  Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'Sysnative' / 'WindowsPowerShell' / 'v1.0' / 'powershell.exe',
 ):
  try:
   if candidate.is_file():
    return str(candidate)
  except OSError:
   pass
 return 'powershell.exe'


def start_scheduled_update(pid, installer_path, target_dir, exe_path):
 """تشغيل مساعد تحديث مستقل ينتظر إغلاق البرنامج ثم يثبت التحديث ويعيد تشغيله"""
 try:
  installer = Path(installer_path).resolve()
  if not installer.is_file():
   return False
  UPDATE_HOME.mkdir(parents=True, exist_ok=True)
  # حذف مساعد BAT القديم إن كان موجودًا من نسخة سابقة
  try:
   (UPDATE_HOME / 'run_update.bat').unlink(missing_ok=True)
  except OSError:
   pass
  payload = {}
  try:
   if UPDATE_PENDING.is_file():
    payload = json.loads(UPDATE_PENDING.read_text(encoding='utf-8'))
  except (OSError, ValueError):
   payload = {}
  if not isinstance(payload, dict):
   payload = {}
  payload['installer'] = str(installer)
  payload['target_dir'] = str(Path(target_dir).resolve())
  payload['exe_path'] = str(Path(exe_path).resolve())
  payload['pid'] = int(pid)
  UPDATE_JOB.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
  try:
   UPDATE_PENDING.unlink(missing_ok=True)
  except OSError:
   pass
  UPDATE_HELPER.write_text(_UPDATE_HELPER_SCRIPT, encoding='ascii')
  flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
  flags |= getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0x00000200)
  try:
   subprocess.Popen(
    [_powershell_exe(), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
     '-WindowStyle', 'Hidden', '-File', str(UPDATE_HELPER), '-AppPid', str(int(pid))],
    cwd=str(UPDATE_HOME), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL, creationflags=flags, close_fds=True)
  except Exception:
   # تعذر تشغيل المساعد: أرجع الطلب حتى تُعاد المحاولة في التشغيل القادم
   try:
    UPDATE_PENDING.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    UPDATE_JOB.unlink(missing_ok=True)
   except OSError:
    pass
   raise
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
  # إزالة مساعد BAT القديم (كان يسبب نافذة find عالقة على المسارات غير الإنجليزية)
  if UPDATE_HOME.is_dir():
   try:
    (UPDATE_HOME / 'run_update.bat').unlink(missing_ok=True)
   except OSError:
    pass
  if not UPDATE_PENDING.is_file():
   return False
  data = json.loads(UPDATE_PENDING.read_text(encoding='utf-8'))
  installer = Path(data.get('installer', ''))
  tag = str(data.get('tag', ''))
  if not installer.is_file():
   UPDATE_PENDING.unlink(missing_ok=True)
   return False
  expected = str(data.get('sha256') or '').strip().lower()
  if expected and file_sha256(installer) != expected:
   # الملف اتغير بعد تنزيله: نرفض التثبيت ونمسح الطلب
   try:
    UPDATE_PENDING.unlink(missing_ok=True)
    UPDATE_HOME.mkdir(parents=True, exist_ok=True)
    UPDATE_FAILURE.write_text('تم إلغاء تحديث مجدول لأن بصمة الملف لا تطابق البصمة الأصلية.', encoding='utf-8')
   except OSError:
    pass
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