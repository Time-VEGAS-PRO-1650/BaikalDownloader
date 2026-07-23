# -*- coding: utf-8 -*-
"""
Байкал Downloader 5.6.0 (плейлисты, авто-Deno, авто-Node.js, MP3, обход блокировок, звуковое оповещение)
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

# =====================================================================
def find_auth_browser():
    """Ищет браузер на ПК для окна авторизации"""
    candidates = []
    if sys.platform == "win32":
        pf = os.environ.get("PROGRAMFILES", "")
        pfx86 = os.environ.get("PROGRAMFILES(X86)", "")
        local = os.environ.get("LOCALAPPDATA", "")
        candidates += [
            os.path.join(pf, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(pfx86, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(local, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(local, "Yandex", "YandexBrowser", "Application", "browser.exe"),
            os.path.join(pf, "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(pfx86, "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(local, "Programs", "Opera", "launcher.exe"),
            os.path.join(local, "Programs", "Opera GX", "launcher.exe"),
            os.path.join(pf, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
            os.path.join(local, "Vivaldi", "Application", "vivaldi.exe"),
        ]
    elif sys.platform == "darwin":
        candidates += [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Yandex.app/Contents/MacOS/Yandex",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Opera.app/Contents/MacOS/Opera",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        ]
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return None
# =====================================================================

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


