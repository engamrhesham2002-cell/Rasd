# Rasd - الإعدادات العامة والمكتبات والمسارات
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
try:import fitz
except ImportError:fitz=None
try:import openpyxl
except ImportError:openpyxl=None
try:from docx import Document
except ImportError:Document=None
try:import xlrd
except ImportError:xlrd=None
try:from pyxlsb import open_workbook as open_xlsb_workbook
except ImportError:open_xlsb_workbook=None
try:import ezdxf
except ImportError:ezdxf=None
try:from pypdf import PdfReader
except ImportError:PdfReader=None
BASE=Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
APP_VERSION='0.40'
LATEST_RELEASE_API='https://api.github.com/repos/engamrhesham2002-cell/Rasd/releases/latest'
UPDATE_HOME=Path(os.environ.get('LOCALAPPDATA',str(BASE)))/'Rasd'/'updates'
UPDATE_PENDING=UPDATE_HOME/'pending.json'
UPDATE_FAILURE=UPDATE_HOME/'update_failed.txt'