# Rasd - الإعدادات العامة والمكتبات والمسارات وثوابت الثيم البصري
import os,sys,sqlite3,subprocess,threading,queue,csv,io,textwrap,math,ctypes,hashlib,shutil,time,json,secrets,colorsys,tempfile,re,urllib.request,urllib.error,webbrowser
from concurrent.futures import ThreadPoolExecutor
from collections import OrderedDict
from pathlib import Path
from datetime import datetime, date, timedelta
from contextlib import contextmanager
import tkinter as tk
from tkinter import ttk,messagebox,simpledialog,filedialog,colorchooser
from tkinter import font as tkfont
from PIL import Image,ImageTk,ImageDraw,ImageFont,ImageOps,ImageFilter,ImageStat,ImageChops

# المسارات والإصدار وثوابت الثيم صارت في ملفات مستقلة، وتُعاد تصديرها هنا
# حتى يبقى `from common import *` صالحًا في كل الوحدات دون تغيير.
from config import BASE, APP_VERSION, LATEST_RELEASE_API, UPDATE_HOME, UPDATE_PENDING, UPDATE_FAILURE
from theme import (
    BG_VOID, BG_PANEL, BG_ALT_ROW, BG_HEADER, BG_SELECTED, BG_HOVER,
    BORDER_DIM, BORDER_GLOW, FG_PRIMARY, FG_MUTED,
    ACCENT_MATRIX, ACCENT_CYAN, ACCENT_AMBER, ACCENT_DANGER,
    PRI_URGENT, PRI_NORMAL, PRI_LOW,
    TERM_FONT, MONO_FONT, RLM,
)
from theme import apply_theme, build_palette, THEME_LABELS, THEME_NAMES, ACCENT_PRESETS, DEFAULT_ACCENTS

# الترجمة (عربي/إنجليزي): tr() تُرجع النص كما هو في العربية، وتترجمه في الإنجليزية.
# تُركّب طبقة ترجمة Tk هنا حتى تسري على كل الوحدات التي تستورد common.
from i18n import tr, set_language, get_language, is_english, is_rtl
import localize_ui
localize_ui.install()
