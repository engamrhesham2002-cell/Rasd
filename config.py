# Rasd - المسارات الأساسية وإصدار التطبيق وإعدادات التحديث
import os
import sys
from pathlib import Path

BASE = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
APP_VERSION = 'v0.44.1'
LATEST_RELEASE_API = 'https://api.github.com/repos/engamrhesham2002-cell/Rasd/releases/latest'
UPDATE_HOME = Path(os.environ.get('LOCALAPPDATA', str(BASE))) / 'Rasd' / 'updates'
UPDATE_PENDING = UPDATE_HOME / 'pending.json'
UPDATE_FAILURE = UPDATE_HOME / 'update_failed.txt'
