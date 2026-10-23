# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPECPATH)
vendor = root / 'vendor'
a = Analysis(
    [str(root / 'full code' / 'app.py')],
    pathex=[str(root), str(vendor)] if vendor.is_dir() else [str(root)],
    binaries=[],
    datas=[
        (str(root / 'Assets' / 'welcome_art.jpg'), 'Assets'),
        (str(root / 'Assets' / 'rasd_logo.png'), 'Assets'),
        (str(root / 'Assets' / 'rasd_wordmark.png'), 'Assets'),
        (str(root / 'Everything' / 'Everything.exe'), 'Everything'),
        (str(root / 'Everything' / 'es.exe'), 'Everything'),
        (str(root / 'Everything' / 'Everything.lng'), 'Everything'),
        (str(root / 'Everything' / 'License.txt'), 'Everything'),
    ],
    hiddenimports=[
        'PIL', 'PIL.Image', 'PIL.ImageTk', 'PIL.ImageDraw', 'PIL.ImageFont',
        'PIL.ImageOps', 'PIL.ImageFilter', 'PIL.ImageStat', 'PIL.ImageChops',
    ],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False, optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [], name='Rasd',
    icon=str(root / 'Assets' / 'product.ico'), debug=False,
    bootloader_ignore_signals=False, strip=False, upx=True, upx_exclude=[],
    runtime_tmpdir=None, console=False, disable_windowed_traceback=False,
    argv_emulation=False, target_arch=None, codesign_identity=None,
    entitlements_file=None,
)
