# -*- coding: utf-8 -*-
"""
Байкал Downloader 5.5.7 (плейлисты, конвертация в MP3, донат Boosty, Что нового)
"""

import http.server
import json
import subprocess
import threading
import queue
import os
import sys
import urllib.request
import urllib.parse
import socketserver
import time
import shutil
import zipfile
import re
import webbrowser
import gzip
import ssl
import html  # Для раскодирования HTML-сущностей (&amp; и т.д.)

# --- ФИКС ДЛЯ MACOS: Отключаем строгую проверку SSL сертификатов ---
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context
# -------------------------------------------------------------------

try:
    import webview
except Exception:
    webview = None

# ================== PATCH: logo splash PyInstaller ==================

def splash_text(text):
    try:
        import pyi_splash
        pyi_splash.update_text(str(text))
    except Exception:
        pass


def close_splash():
    try:
        import pyi_splash
        pyi_splash.close()
    except Exception:
        pass

# ====================================================================


