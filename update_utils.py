# Rasd - دوال التحديث التلقائي (المستقلة)
from common import *

def start_scheduled_update(wait_pid,installer,target,app_path):
 if os.name!='nt':return False
 powershell=shutil.which('powershell.exe') or shutil.which('powershell')
 if not powershell:
  candidate=Path(os.environ.get('WINDIR',r'C:\Windows'))/'System32'/'WindowsPowerShell'/'v1.0'/'powershell.exe'
  if candidate.is_file():powershell=str(candidate)
 if not powershell:return False
 UPDATE_HOME.mkdir(parents=True,exist_ok=True)
 script=UPDATE_HOME/f'apply_update_{wait_pid}.ps1'
 body='''param([int]$WaitPid,[string]$InstallerPath,[string]$TargetPath,[string]$AppPath,[string]$PendingPath,[string]$FailurePath)
$ErrorActionPreference = 'Stop'
try {
  while (Get-Process -Id $WaitPid -ErrorAction SilentlyContinue) { Start-Sleep -Milliseconds 400 }
  $appName = [System.IO.Path]::GetFileName($AppPath)
  while ($true) {
    $running = Get-CimInstance Win32_Process -Filter "Name='$appName'" -ErrorAction SilentlyContinue | Where-Object { $_.ExecutablePath -ieq $AppPath }
    if (-not $running) { break }
    Start-Sleep -Milliseconds 500
  }
  $arguments = '/S "/D=' + $TargetPath + '"'
  $result = Start-Process -FilePath $InstallerPath -ArgumentList $arguments -Wait -PassThru
  if ($result.ExitCode -eq 0) {
    Remove-Item -LiteralPath $PendingPath -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $FailurePath -Force -ErrorAction SilentlyContinue
    Start-Process -FilePath $AppPath
  } else {
    Set-Content -LiteralPath $FailurePath -Value "The installer exited with code $($result.ExitCode)." -Encoding UTF8
    Remove-Item -LiteralPath $PendingPath -Force -ErrorAction SilentlyContinue
    Start-Process -FilePath $AppPath
  }
} catch {
  Set-Content -LiteralPath $FailurePath -Value $_.Exception.Message -Encoding UTF8
  Remove-Item -LiteralPath $PendingPath -Force -ErrorAction SilentlyContinue
  if (Test-Path -LiteralPath $AppPath) { Start-Process -FilePath $AppPath }
}
'''
 try:
  script.write_text(body,encoding='utf-8-sig')
  subprocess.Popen([powershell,'-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-WindowStyle','Hidden','-File',str(script),str(wait_pid),str(installer),str(target),str(app_path),str(UPDATE_PENDING),str(UPDATE_FAILURE)],cwd=str(UPDATE_HOME),stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
  return True
 except (OSError,ValueError):return False
def queue_pending_update(installer,mode,tag):
 if not getattr(sys,'frozen',False) or not Path(installer).is_file():return False
 portable=(BASE/'.rasd-portable').is_file()
 if mode!=('portable' if portable else 'standard'):return False
 record={'tag':tag,'installer':str(Path(installer).resolve()),'target':str(BASE.resolve()),'mode':mode,'queued_at':time.time()}
 try:
  UPDATE_HOME.mkdir(parents=True,exist_ok=True)
  temp=UPDATE_PENDING.with_suffix('.json.tmp');temp.write_text(json.dumps(record,ensure_ascii=False),encoding='utf-8');temp.replace(UPDATE_PENDING);return True
 except OSError:return False
def launch_pending_update_at_start():
 if not getattr(sys,'frozen',False) or not UPDATE_PENDING.is_file():return False
 try:
  record=json.loads(UPDATE_PENDING.read_text(encoding='utf-8'));installer=Path(record['installer']).resolve();target=Path(record['target']).resolve();mode=record['mode']
  portable=(BASE/'.rasd-portable').is_file()
  if target!=BASE.resolve() or mode!=('portable' if portable else 'standard') or not installer.is_file():raise ValueError('The pending update is missing or does not match this installation.')
  if start_scheduled_update(os.getpid(),installer,target,Path(sys.executable).resolve()):return True
  raise OSError('Windows PowerShell could not be started to apply the update.')
 except Exception as exc:
  try:UPDATE_FAILURE.parent.mkdir(parents=True,exist_ok=True);UPDATE_FAILURE.write_text(str(exc),encoding='utf-8');UPDATE_PENDING.unlink(missing_ok=True)
  except OSError:pass
  return False
