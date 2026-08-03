# -*- coding: utf-8 -*-
"""
Байкал Downloader 5.6.14 (плейлисты, авто-Deno, авто-Node.js, MP3, обход блокировок, прямые ссылки)
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

# ================== PATCH: скрыть консоли subprocess на Windows ==================

_ORIGINAL_SUBPROCESS_POPEN = subprocess.Popen


def _hidden_subprocess_popen(*args, **kwargs):
    """
    Скрывает консольные окна для yt-dlp.exe, ffmpeg.exe, node.exe, deno.exe, powershell.exe, cmd.exe и т.д.
    Работает на Windows.
    """

    if os.name == "nt":
        startupinfo = kwargs.get("startupinfo")

        if startupinfo is None:
            startupinfo = subprocess.STARTUPINFO()

        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0

        kwargs["startupinfo"] = startupinfo

        flags = kwargs.get("creationflags", 0)

        if hasattr(subprocess, "CREATE_NEW_CONSOLE"):
            flags &= ~subprocess.CREATE_NEW_CONSOLE

        flags |= subprocess.CREATE_NO_WINDOW

        kwargs["creationflags"] = flags

    return _ORIGINAL_SUBPROCESS_POPEN(*args, **kwargs)


# Подменяем subprocess.Popen globally.
subprocess.Popen = _hidden_subprocess_popen

# ===============================================================================
PORT = 9872
APP_TITLE = "Байкал Downloader 5.6.14"
APP_VERSION = "5.6.14"
APP_AUTHOR = "Iurii Cojocari (Time VEGAS PRO)"

# Константы Донатов
APP_PAYPAL = "paypal.me/studioyouar"
APP_PAYPAL_URL = "https://paypal.me/studioyouar"
APP_BOOSTY = "boosty.to/time_vegas_pro"
APP_BOOSTY_URL = "https://boosty.to/time_vegas_pro/donate"

# Ссылка на обновление.
UPDATE_VERSION = "5.6.14"
UPDATE_EXE_URL = "https://github.com/Time-VEGAS-PRO-1650/BaikalDownloader/releases/download/v5.6.14/Baikal.Downloader.Setup.5.6.14.exe"


# Автообновление через GitHub Releases.
GITHUB_REPO = "Time-VEGAS-PRO-1650/BaikalDownloader"
GITHUB_RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
GITHUB_RELEASES_TAG_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/tags/v{UPDATE_VERSION}"

# Если в релизе несколько .exe, программа выберет тот, в имени которого есть эта строка.
UPDATE_ASSET_NAME_CONTAINS = "Setup"

APP_WIDTH = 1280
APP_HEIGHT = 860
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
    BUNDLE_DIR = getattr(sys, "_MEIPASS", BASE_DIR)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = BASE_DIR

DATA_DIR = os.path.join(BASE_DIR, "data")
TOOLS_DIR = os.path.join(BASE_DIR, "tools")
FONTS_DIR = os.path.join(DATA_DIR, "fonts")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TOOLS_DIR, exist_ok=True)
os.makedirs(FONTS_DIR, exist_ok=True)

SETTINGS_FILE = os.path.join(DATA_DIR, "baikal_settings.txt")

def get_system_downloads_folder():
    """Автоматически находит стандартную папку загрузок для ЛЮБОЙ ОС"""
    return os.path.join(os.path.expanduser("~"), "Downloads")

DEFAULT_APP_SETTINGS = {
    "directory": get_system_downloads_folder(),
    "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
    "segmentDuration": "12",
    "maxDuration": "",
    "browserCookies": "none",
    "useRealNames": "true",
}

import platform

IS_WIN = os.name == "nt"
IS_MAC = platform.system() == "Darwin"
EXE_EXT = ".exe" if IS_WIN else ""

# yt-dlp хранится в tools
YTDLP_PATH = os.path.join(TOOLS_DIR, f"yt-dlp{EXE_EXT}")
YTDLP_VERSION_FILE = os.path.join(TOOLS_DIR, "yt-dlp.version")

# Пути к JS-рантаймам в tools
DENO_PATH = os.path.join(TOOLS_DIR, f"deno{EXE_EXT}")
NODE_PATH = os.path.join(TOOLS_DIR, f"node{EXE_EXT}")

# ffmpeg хранится в tools/ffmpeg/bin
FFMPEG_DIR = os.path.join(TOOLS_DIR, "ffmpeg")
FFMPEG_BIN_DIR = os.path.join(FFMPEG_DIR, "bin")
FFMPEG_PATH = os.path.join(FFMPEG_BIN_DIR, f"ffmpeg{EXE_EXT}")

FFMPEG_VERSION_FILE = os.path.join(DATA_DIR, "ffmpeg.version")

GITHUB_YTDLP_API = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
if IS_WIN:
    GITHUB_FFMPEG_API = "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/latest"
else:
    GITHUB_FFMPEG_API = "https://api.github.com/repos/yt-dlp/FFmpeg-Builds/releases/latest"

PIXABAY_API_KEY = "38175657-c82251544174972b0251b5145"
PEXELS_API_KEY = "xyx5EWLtzB0M11Z2wEZPXkkCb5mMfI1tDXEiYklBDnW7WoEd18y8QLXE"

USE_BROWSER_COOKIES = False
BROWSER_COOKIES = "chrome"

message_queue = queue.Queue()
is_running = False
start_time = 0
cancel_requested = False
current_process = None

def load_app_settings():
    settings = dict(DEFAULT_APP_SETTINGS)

    if not os.path.exists(SETTINGS_FILE):
        return settings

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")

                if not line.strip():
                    continue

                if line.lstrip().startswith("#"):
                    continue

                if "=" not in line:
                    continue

                key, value = line.split("=", 1)
                key = key.strip()

                if key in settings:
                    settings[key] = value.strip()
    except Exception:
        pass

    return settings


def save_app_settings(settings):
    current = load_app_settings()

    for key in DEFAULT_APP_SETTINGS:
        if key in settings:
            current[key] = str(settings.get(key, "")).strip()

    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            f.write("# Байкал Downloader settings\n")
            f.write("# Этот файл можно редактировать вручную.\n")
            f.write("# directory может быть относительным или полным путём.\n")
            f.write(f"directory={current.get('directory', DEFAULT_APP_SETTINGS['directory'])}\n")
            f.write(f"format={current.get('format', DEFAULT_APP_SETTINGS['format'])}\n")
            f.write(f"segmentDuration={current.get('segmentDuration', '12')}\n")
            f.write(f"maxDuration={current.get('maxDuration', '')}\n")
            f.write(f"browserCookies={current.get('browserCookies', 'none')}\n")
            f.write(f"useRealNames={current.get('useRealNames', 'true')}\n")

        return True
    except Exception as e:
        log(f"Не удалось сохранить настройки: {e}", "warn")
        return False


def get_download_dir_from_setting(directory):
    directory = str(directory or DEFAULT_APP_SETTINGS["directory"]).strip()

    if not directory:
        directory = DEFAULT_APP_SETTINGS["directory"]

    expanded = os.path.expanduser(os.path.expandvars(directory))

    if os.path.isabs(expanded):
        return expanded

    return os.path.join(BASE_DIR, expanded)


HTML_PAGE = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Байкал Downloader 5.6.14</title>

<script async src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
<style>
/* MANROPE */
@font-face { font-family: 'Manrope'; font-style: normal; font-weight: 400; src: url('/fonts/manrope-cyrillic-400-normal.woff2') format('woff2'); unicode-range: U+0301, U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116; font-display: swap; }
@font-face { font-family: 'Manrope'; font-style: normal; font-weight: 400; src: url('/fonts/manrope-latin-400-normal.woff2') format('woff2'); unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+2074, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD; font-display: swap; }
@font-face { font-family: 'Manrope'; font-style: normal; font-weight: 700; src: url('/fonts/manrope-cyrillic-700-normal.woff2') format('woff2'); unicode-range: U+0301, U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116; font-display: swap; }
@font-face { font-family: 'Manrope'; font-style: normal; font-weight: 700; src: url('/fonts/manrope-latin-700-normal.woff2') format('woff2'); unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+2074, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD; font-display: swap; }

/* UNBOUNDED */
@font-face { font-family: 'Unbounded'; font-style: normal; font-weight: 400; src: url('/fonts/unbounded-cyrillic-400-normal.woff2') format('woff2'); unicode-range: U+0301, U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116; font-display: swap; }
@font-face { font-family: 'Unbounded'; font-style: normal; font-weight: 400; src: url('/fonts/unbounded-latin-400-normal.woff2') format('woff2'); unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+2074, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD; font-display: swap; }
@font-face { font-family: 'Unbounded'; font-style: normal; font-weight: 800; src: url('/fonts/unbounded-cyrillic-800-normal.woff2') format('woff2'); unicode-range: U+0301, U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116; font-display: swap; }
@font-face { font-family: 'Unbounded'; font-style: normal; font-weight: 800; src: url('/fonts/unbounded-latin-800-normal.woff2') format('woff2'); unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+2074, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD; font-display: swap; }

/* JETBRAINS MONO */
@font-face { font-family: 'JetBrains Mono'; font-style: normal; font-weight: 400; src: url('/fonts/jetbrains-mono-cyrillic-400-normal.woff2') format('woff2'); unicode-range: U+0301, U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116; font-display: swap; }
@font-face { font-family: 'JetBrains Mono'; font-style: normal; font-weight: 400; src: url('/fonts/jetbrains-mono-latin-400-normal.woff2') format('woff2'); unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+2074, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD; font-display: swap; }


:root{
  /* ——— НОЧЬ НАД БАЙКАЛОМ ——— */
  --abyss:#02060e; --deep:#04101f; --panel:#071a2e;
  --line:rgba(125,200,255,.14); --line2:rgba(125,200,255,.42);
  --text:#e8f6ff; --muted:#7d97b3;
  --cyan:#34d6f6;        
  --cyan-deep:#0a63d6;   
  --azure:#38bdf8;       
  --ice:#cdeeff;         
  --teal:#39c0e8;
  --amber:#fbbf24; --green:#34d399; --red:#fb6f84;
  /* Указываем наши шрифты, а если они еще не скачались - берем системные */
  --font: 'Manrope', system-ui, sans-serif;
  --display: 'Unbounded', var(--font);
  --mono: 'JetBrains Mono', Consolas, monospace;
}
*{box-sizing:border-box;margin:0;padding:0}
*{scrollbar-width:thin;scrollbar-color:rgba(103,232,249,.3) transparent}
::-webkit-scrollbar{width:13px;height:13px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:rgba(103,232,249,.22);border-radius:10px;border:4px solid rgba(5,17,27,.95);background-clip:padding-box}
::-webkit-scrollbar-thumb:hover{background:rgba(37,224,242,.55);border:4px solid rgba(5,17,27,.95);background-clip:padding-box}
::-webkit-scrollbar-corner{background:transparent}
::selection{background:rgba(37,224,242,.3)}
button,input,select,textarea{font:inherit}
button{border:0}
button:focus,summary:focus,.btn:focus,.icon-btn:focus,.tab-btn:focus{outline:none}

body{
  height:100vh;width:100vw;overflow:hidden;font-family:var(--font);color:var(--text);
  background:
    radial-gradient(1200px 420px at 50% 47%, rgba(40,150,230,.20), transparent 62%),
    radial-gradient(900px 600px at 50% -12%, rgba(20,90,180,.16), transparent 60%),
    radial-gradient(700px 500px at 8% 108%, rgba(10,99,214,.12), transparent 60%),
    linear-gradient(180deg,#02060e 0%,#04101f 42%,#03101d 56%,#02080f 100%);
}
.bg-grid{position:fixed;inset:0;z-index:0;pointer-events:none;opacity:.55;
  background-image:
    linear-gradient(rgba(103,232,249,.045) 1px,transparent 1px),
    linear-gradient(90deg,rgba(103,232,249,.045) 1px,transparent 1px);
  background-size:44px 44px;
  -webkit-mask-image:radial-gradient(ellipse at 60% 0%,#000 25%,transparent 78%);
  mask-image:radial-gradient(ellipse at 60% 0%,#000 25%,transparent 78%);}
.bg-sweep{position:fixed;top:-46vmax;right:-46vmax;width:96vmax;height:96vmax;z-index:0;
  pointer-events:none;border-radius:50%;
  background:conic-gradient(from 0deg,transparent 0deg,rgba(37,224,242,.06) 14deg,transparent 36deg);
  animation:sweep 16s linear infinite;}
@keyframes sweep{to{transform:rotate(360deg)}}

.btn-icon-only {
  width: 32px !important;
  height: 30px !important;
  padding: 0 !important;
  display: grid !important;
  place-items: center !important;
  font-size: 13px !important;
  border-radius: 8px !important;
  background: rgba(255, 255, 255, 0.04) !important;
  border: 1px solid var(--line) !important;
  transition: .15s ease !important;
}
.btn-icon-only:hover {
  background: rgba(37, 224, 242, 0.12) !important;
  border-color: var(--cyan) !important;
  transform: translateY(-1px) !important;
}



/* ============ БАЙКАЛ: горизонт-вода + ледяные трещины ============ */
.bg-horizon{position:fixed;left:0;right:0;top:47%;height:2px;z-index:0;pointer-events:none;
  background:linear-gradient(90deg,transparent,rgba(56,189,248,.0) 8%,rgba(120,210,255,.55) 50%,rgba(56,189,248,.0) 92%,transparent);
  box-shadow:0 0 26px 6px rgba(40,150,230,.35),0 0 90px 24px rgba(20,90,180,.22);
  filter:blur(.3px);opacity:.85;}
.bg-horizon::after{content:"";position:absolute;left:0;right:0;top:2px;height:34vh;
  background:linear-gradient(180deg,rgba(40,150,230,.16),rgba(10,60,140,.05) 40%,transparent 75%);
  -webkit-mask-image:linear-gradient(180deg,#000,transparent);mask-image:linear-gradient(180deg,#000,transparent);}
.bg-ice{position:fixed;left:0;right:0;bottom:0;height:42vh;z-index:0;pointer-events:none;opacity:.5;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1200' height='420' viewBox='0 0 1200 420'%3E%3Cg fill='none' stroke='%237dd3fc' stroke-opacity='.5' stroke-width='1'%3E%3Cpolyline points='40,420 150,300 120,210 240,150 210,60'/%3E%3Cpolyline points='150,300 320,330 410,250 380,160'/%3E%3Cpolyline points='320,330 470,420'/%3E%3Cpolyline points='410,250 560,280 640,190 600,90'/%3E%3Cpolyline points='560,280 720,330 800,420'/%3E%3Cpolyline points='720,330 880,300 960,210 920,120'/%3E%3Cpolyline points='880,300 1040,340 1160,420'/%3E%3Cpolyline points='960,210 1100,240 1180,150'/%3E%3C/g%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:center bottom;background-size:cover;
  -webkit-mask-image:linear-gradient(0deg,#000 8%,transparent 80%);mask-image:linear-gradient(0deg,#000 8%,transparent 80%);}

/* ============ орбиты-дуги вокруг логотипа (как на сплэше) ============ */
.brand{position:relative}
.brand .logo{position:relative;z-index:2}
.brand::before,.brand::after{content:"";position:absolute;border-radius:50%;pointer-events:none;z-index:1;
  border:1px dashed rgba(120,210,255,.28);}
.brand::before{width:92px;height:92px;left:-23px;top:-23px;
  border-top-color:rgba(52,214,246,.6);border-right-color:rgba(52,214,246,.12);
  animation:orbit 18s linear infinite;}
.brand::after{width:124px;height:124px;left:-39px;top:-39px;
  border-bottom-color:rgba(56,189,248,.5);border-left-color:rgba(56,189,248,.1);
  animation:orbit 26s linear infinite reverse;}
@keyframes orbit{to{transform:rotate(360deg)}}
.brand h1,.brand p{position:relative;z-index:2}

/* ================= КАРКАС ================= */
.app{position:relative;z-index:1;height:100vh;display:grid;overflow:hidden;
  grid-template-columns:252px minmax(0,1fr);
  grid-template-rows:minmax(0,1fr) auto;
  grid-template-areas:"side main" "dock dock";}

/* ---- блюр-оверлей: ВНУТРИ .app, чтобы всплывающие панели (z70) оставались ЧЁТКИМИ ---- */
body.popup-open .app::before{content:"";position:fixed;inset:0;z-index:50;pointer-events:none;
  background:rgba(2,8,14,.45);backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px);
  opacity:1;transition:opacity .18s ease;}

/* ================= САЙДБАР ================= */
.sidebar{grid-area:side;position:relative;display:flex;flex-direction:column;gap:12px;
  padding:20px 16px 14px;border-right:1px solid var(--line);
  background:linear-gradient(180deg,rgba(9,31,47,.9),rgba(4,15,24,.94));}
.sidebar::after{content:"";position:absolute;top:14px;bottom:14px;right:5px;width:1px;opacity:.45;
  background:repeating-linear-gradient(180deg,rgba(103,232,249,.5) 0 1px,transparent 1px 13px);}

.brand{display:flex;align-items:center;gap:12px}
.logo{width:46px;height:46px;border-radius:11px;object-fit:cover;flex:0 0 auto;
  box-shadow:0 8px 22px rgba(0,0,0,.5),0 0 0 1px rgba(103,232,249,.3);}
.brand h1{font:800 17px/1.05 var(--display);letter-spacing:.07em;text-transform:uppercase;color:#ecf8ff}
.brand p{margin-top:6px;font:600 8.5px var(--mono);letter-spacing:.26em;text-transform:uppercase;color:var(--cyan)}

.btn{position:relative;display:flex;align-items:center;justify-content:flex-start;gap:10px;
  height:41px;padding:0 13px;border-radius:10px;cursor:pointer;white-space:nowrap;
  color:var(--text);background:rgba(255,255,255,.045);border:1px solid var(--line);
  font:600 12.5px var(--font);transition:.18s;}
.btn:hover:not(:disabled){transform:translateX(3px);border-color:var(--line2);background:rgba(103,232,249,.08)}
.btn:disabled{opacity:.45;cursor:not-allowed}
.btn-ico{width:20px;text-align:center;flex:0 0 auto;font-size:14px}
.sidebar .btn{width:100%}

.btn-primary{height:56px;justify-content:center;overflow:hidden;margin-top:4px;
  font:800 14px var(--display);letter-spacing:.09em;text-transform:uppercase;color:#03131c;
    background:linear-gradient(135deg,#3fd2f6 0%,#1aa0ec 45%,#0a63d6 100%);border:1px solid rgba(190,250,255,.55);
  animation:primGlow 3.2s ease-in-out infinite;}
@keyframes primGlow{0%,100%{box-shadow:0 10px 28px rgba(37,224,242,.22),inset 0 1px 0 rgba(255,255,255,.45)}
  50%{box-shadow:0 12px 40px rgba(37,224,242,.42),inset 0 1px 0 rgba(255,255,255,.45)}}
.btn-primary::after{content:"";position:absolute;top:0;bottom:0;left:-60%;width:40%;
  background:linear-gradient(100deg,transparent,rgba(255,255,255,.55),transparent);
  transform:skewX(-20deg);transition:.5s;}
.btn-primary:hover:not(:disabled){transform:translateY(-2px);  background:linear-gradient(135deg,#5fdcf8 0%,#28aef0 45%,#0f74e6 100%);}
.btn-primary:hover::after{left:130%}

.btn-stop{justify-content:center;font:700 13px var(--display);text-transform:uppercase;letter-spacing:.06em;
  color:#ffd7de;background:rgba(251,111,132,.13);border-color:rgba(251,111,132,.45);
  animation:stopPulse 2.2s ease-in-out infinite;}
.btn-stop:hover:not(:disabled){background:rgba(251,111,132,.24);border-color:rgba(251,111,132,.7)}
@keyframes stopPulse{0%,100%{box-shadow:0 0 0 0 rgba(251,111,132,.25)}50%{box-shadow:0 0 22px 2px rgba(251,111,132,.3)}}

.btn-ghost-red{color:#ffb9c5;border-color:rgba(251,111,132,.3);background:rgba(251,111,132,.07)}
.btn-ghost-red:hover:not(:disabled){background:rgba(251,111,132,.16);border-color:rgba(251,111,132,.55)}
.btn-green{color:#a9f5cd;border-color:rgba(52,211,153,.35);background:rgba(52,211,153,.09)}
.btn-green:hover:not(:disabled){background:rgba(52,211,153,.18);border-color:rgba(52,211,153,.6)}
.btn-blue{color:#a8d4ff;border-color:rgba(96,165,250,.35);background:rgba(96,165,250,.09)}
.btn-blue:hover:not(:disabled){background:rgba(96,165,250,.18);border-color:rgba(96,165,250,.6)}
.btn-red{color:#ffb9c5;border-color:rgba(251,111,132,.35);background:rgba(251,111,132,.09)}
.btn-red:hover:not(:disabled){background:rgba(251,111,132,.18)}
.btn-main{height:40px;justify-content:center;font:800 12px var(--display);letter-spacing:.05em;
  text-transform:uppercase;color:#03131c;background:linear-gradient(135deg,#3fd2f6 0%,#1aa0ec 45%,#0a63d6 100%);
  border-color:rgba(190,250,255,.5);box-shadow:0 8px 24px rgba(37,224,242,.25);}
.btn-main:hover:not(:disabled){background:linear-gradient(135deg,#5fdcf8 0%,#28aef0 45%,#0f74e6 100%);}
.btn-slim{height:38px;padding:0 13px;flex:0 0 auto;font-size:11.5px;justify-content:center}
.btn-icon{width:32px;height:32px;padding:0;border-radius:50%;justify-content:center;font-size:13px}
.playlist-footer .btn,.playlist-controls .btn,.dock-input-row .btn,
.settings-window .btn,.about-actions .btn{justify-content:center}

.side-label{font:700 9px var(--mono);letter-spacing:.24em;text-transform:uppercase;color:var(--muted);
  margin:8px 2px -2px;display:flex;align-items:center;gap:8px;}
.side-label::after{content:"";flex:1;height:1px;background:var(--line)}

.side-footer{margin-top:auto;padding:10px 4px 0;border-top:1px solid var(--line);text-align:center;
  font:500 8.5px var(--mono);letter-spacing:.16em;text-transform:uppercase;color:var(--muted);}

/* ================= ВЕРХНЯЯ ЛИНИЯ ================= */
.main{grid-area:main;display:flex;flex-direction:column;gap:10px;padding:14px 18px 12px;min-height:0;min-width:0;overflow:hidden}
.topline{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:12px;flex:0 0 auto}
.session{display:flex;align-items:center;gap:10px;justify-self:start;
  font:700 10px var(--mono);letter-spacing:.24em;text-transform:uppercase;color:var(--muted)}
.session-dot{width:7px;height:7px;border-radius:2px;background:var(--cyan);box-shadow:0 0 10px var(--cyan);animation:blinkDot 2.4s ease-in-out infinite}
@keyframes blinkDot{0%,100%{opacity:1}50%{opacity:.3}}
.session-clock{padding:5px 9px;border:1px solid var(--line);border-radius:8px;background:rgba(4,16,25,.55);
  color:#9fd8ea;letter-spacing:.12em;font-weight:600;}

/* ---- статистика в шапке: подписи видны ВСЕГДА ---- */
.topstats{display:flex;align-items:stretch;gap:6px;justify-self:center}
.tstat{position:relative;display:flex;align-items:center;gap:8px;padding:6px 11px;border-radius:9px;
  border:1px solid var(--line);background:rgba(255,255,255,.03);transition:.2s;min-width:0;}
.tstat:hover{border-color:var(--line2);transform:translateY(-2px)}
.tstat b{font:800 16px/1 var(--display);color:var(--cyan)}
.tstat span{font:600 7.5px var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--muted);white-space:nowrap}
.tstat.danger{border-color:rgba(251,111,132,.4);background:rgba(251,111,132,.08)}
.tstat.danger b{color:var(--red)}
.tstat.danger::after{content:"";position:absolute;top:6px;right:6px;width:6px;height:6px;border-radius:50%;
  background:var(--red);box-shadow:0 0 8px var(--red);animation:blinkDot 1.4s ease-in-out infinite}

.topline-right{display:flex;align-items:center;gap:9px;justify-self:end}

.server{display:flex;align-items:center;gap:8px;height:40px;padding:0 13px;border-radius:10px;
  border:1px solid var(--line);background:rgba(4,16,25,.6);
  font:600 10.5px var(--mono);letter-spacing:.04em;color:var(--muted);transition:.25s;}
.server-dot{width:8px;height:8px;border-radius:50%;background:var(--red);position:relative;flex:0 0 auto}
.server-dot::after{content:"";position:absolute;inset:-4px;border-radius:50%;
  border:1px solid rgba(251,111,132,.55);animation:ping 1.8s ease-out infinite;}
@keyframes ping{0%{transform:scale(.5);opacity:.9}80%,100%{transform:scale(1.7);opacity:0}}
.server.connected{color:#c8f7e4;border-color:rgba(52,211,153,.32)}
.server.connected .server-dot{background:var(--green)}
.server.connected .server-dot::after{border-color:rgba(52,211,153,.55)}

.icon-btn{width:40px;height:40px;display:grid;place-items:center;cursor:pointer;list-style:none;
  border-radius:10px;border:1px solid var(--line);background:rgba(255,255,255,.045);
  color:#bfe6f5;font-size:16px;line-height:1;transition:.18s;}
.icon-btn::-webkit-details-marker{display:none}
.icon-btn:hover{transform:translateY(-2px);border-color:var(--line2);background:rgba(37,224,242,.1);
  color:#fff;box-shadow:0 8px 20px rgba(37,224,242,.16);}
.ico{display:block;transition:transform .4s cubic-bezier(.2,.8,.2,1)}
.icon-btn:hover .ico-gear{transform:rotate(75deg)}
/* иконки и их панели — ВЫШЕ блюр-оверлея (z50), поэтому остаются чёткими */
details.settings,details.about-menu{position:relative;z-index:60}
.about-menu[open] > .icon-btn,.settings[open] > .icon-btn{
  border-color:rgba(37,224,242,.6);background:rgba(37,224,242,.14);color:#fff;
  box-shadow:0 0 0 3px rgba(37,224,242,.1);}

.settings-window,.about-window{position:absolute;right:0;top:calc(100% + 12px);z-index:70;padding:14px;
  border-radius:14px;border:1px solid var(--line2);background:rgba(8,26,41,.985);
  box-shadow:0 28px 80px rgba(0,0,0,.62);
  opacity:0;visibility:hidden;pointer-events:none;
  transform:translateY(-8px) scale(.97);transform-origin:top right;
  transition:opacity .18s ease,transform .22s cubic-bezier(.2,.8,.2,1),visibility 0s linear .22s;}
.settings-window{width:392px}
.about-window{width:352px}
details:not([open]) > .about-window,details:not([open]) > .settings-window{display:block}
.about-menu[open] .about-window,.settings[open] .settings-window{
  opacity:1;visibility:visible;pointer-events:auto;transform:translateY(0) scale(1);
  transition:opacity .18s ease,transform .22s cubic-bezier(.2,.8,.2,1),visibility 0s;}
.about-menu.is-closing .about-window,.settings.is-closing .settings-window{
  opacity:0;visibility:visible;pointer-events:none;transform:translateY(-6px) scale(.97);}

.settings-title{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:11px;font:700 12.5px var(--font);color:#dff6ff}
.settings-title small{font:500 9px var(--mono);color:var(--muted);letter-spacing:.06em}
.settings-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.field{display:grid;gap:6px}
.field.full{grid-column:1/-1}
.field label{font:600 9.5px var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
input,select{width:100%;height:37px;padding:0 11px;border-radius:9px;outline:none;color:var(--text);
  background:rgba(3,12,20,.8);border:1px solid var(--line);font:500 11.5px var(--mono);transition:.2s;}
input:focus,select:focus{border-color:rgba(37,224,242,.55);box-shadow:0 0 0 3px rgba(37,224,242,.09)}
.btn-auth{width:100%;height:43px;color:#fff;border-color:rgba(255,255,255,.3);font-weight:800;text-shadow:0 1px 3px rgba(0,0,0,.35)}
#auth-hint{margin-top:7px;font:500 9.5px/1.45 var(--mono);color:var(--muted)}

.about-head{display:flex;align-items:center;gap:11px;margin-bottom:11px}
.about-logo{width:52px;height:52px;border-radius:12px;object-fit:cover;
  box-shadow:0 8px 22px rgba(0,0,0,.5),0 0 0 1px rgba(103,232,249,.3)}
.about-title b{display:block;font:700 13.5px var(--display);color:#ecf8ff}
.about-title span{display:block;margin-top:4px;font:500 10px var(--mono);color:var(--muted)}
.about-text{display:grid;gap:6px;padding:11px;border-radius:11px;border:1px solid rgba(255,255,255,.07);
  background:rgba(255,255,255,.03);font:500 10.5px/1.5 var(--mono);color:#cfe6f7;}
.about-text a{color:#6fe3f7;text-decoration:none}
.about-text a:hover{text-decoration:underline}
.about-actions{display:grid;gap:7px;margin-top:11px}
.update-status{min-height:18px;margin-top:10px;font:500 10px/1.5 var(--mono);color:var(--muted);white-space:pre-wrap}
.update-status.ok{color:var(--green)}
.update-status.warn{color:var(--amber)}
.update-status.error{color:var(--red)}

/* ================= КОМПАКТНЫЙ ПРОГРЕСС-БАР ================= */
.gauge{position:relative;display:flex;align-items:center;gap:14px;padding:9px 16px;flex:0 0 auto;
  border:1px solid var(--line);border-radius:11px;overflow:hidden;
  background:linear-gradient(120deg,rgba(13,42,62,.7),rgba(6,22,36,.7));}
.gauge::before,.gauge::after,.workspace::before,.workspace::after{content:"";position:absolute;width:12px;height:12px;pointer-events:none;z-index:3}
.gauge::before,.workspace::before{top:-1px;left:-1px;border-top:2px solid rgba(37,224,242,.5);border-left:2px solid rgba(37,224,242,.5);border-top-left-radius:11px}
.gauge::after,.workspace::after{bottom:-1px;right:-1px;border-bottom:2px solid rgba(37,224,242,.5);border-right:2px solid rgba(37,224,242,.5);border-bottom-right-radius:11px}
.gauge-ratio{flex:0 0 auto;text-align:center}
.gauge-ratio b{display:block;font:800 17px/1 var(--display);color:#ecf8ff;letter-spacing:.02em}
.gauge-ratio span{display:block;margin-top:3px;font:600 7px var(--mono);letter-spacing:.22em;text-transform:uppercase;color:var(--muted)}
.gauge-sep{width:1px;align-self:stretch;background:var(--line)}
.gauge-mid{flex:1;min-width:0}
.gauge-meta{display:flex;justify-content:space-between;align-items:baseline;gap:12px;margin-bottom:5px}
#progressLabel{font:600 11px var(--font);color:var(--text)}
.gauge-pct{font:700 10px var(--mono);color:var(--cyan)}
.progress-track{position:relative;height:8px;border-radius:6px;overflow:hidden;
  background:rgba(3,12,20,.85);border:1px solid rgba(103,232,249,.14);}
.progress-track::after{content:"";position:absolute;inset:0;pointer-events:none;
  background:repeating-linear-gradient(90deg,transparent 0 calc(25% - 1px),rgba(3,10,17,.9) calc(25% - 1px) 25%);}
.progress-fill{height:100%;width:0%;position:relative;border-radius:6px;transition:width .3s;
  background:linear-gradient(90deg,#0a63d6,#1aa0ec,#34d6f6,#cdeeff);box-shadow:0 0 14px rgba(37,224,242,.5);}
.progress-fill::after{content:"";position:absolute;inset:0;border-radius:6px;
  background:linear-gradient(100deg,transparent 30%,rgba(255,255,255,.35) 50%,transparent 70%);
  background-size:220% 100%;animation:flow 1.7s linear infinite;}
@keyframes flow{from{background-position:130% 0}to{background-position:-90% 0}}
.progress-fill.loading{width:34%;animation:load 1.1s ease-in-out infinite}
@keyframes load{0%{margin-left:-35%}100%{margin-left:105%}}

/* ================= ВКЛАДКИ ================= */
.workspace{position:relative;display:flex;flex-direction:column;flex:1;min-height:0;
  border:1px solid var(--line);border-radius:12px;overflow:hidden;background:rgba(8,28,43,.72);}
.tabs{display:flex;align-items:stretch;gap:2px;flex:0 0 auto;padding:0 8px;
  border-bottom:1px solid rgba(103,232,249,.12);background:rgba(255,255,255,.02);}
.tab-btn{position:relative;height:42px;padding:0 16px;background:transparent;border:0;
  border-bottom:2px solid transparent;cursor:pointer;color:var(--muted);
  font:700 10px var(--display);letter-spacing:.18em;text-transform:uppercase;
  display:flex;align-items:center;gap:8px;transition:.18s;}
.tab-btn .tab-ico{font-size:13px;line-height:1}
.tab-btn:hover{color:var(--text)}
.tab-btn.active{color:var(--cyan);border-bottom-color:var(--cyan)}
.tab-btn.active .tab-ico{filter:drop-shadow(0 0 6px rgba(37,224,242,.6))}
.tab-btn .tab-pulse{width:6px;height:6px;border-radius:50%;background:var(--cyan);box-shadow:0 0 8px var(--cyan);
  opacity:0;transition:.2s}
.tab-btn.live .tab-pulse{opacity:1;animation:blinkDot 1.2s ease-in-out infinite}
.tab-pane{display:none;flex:1;min-height:0;flex-direction:column}
.tab-pane.active{display:flex}

/* ---- панель ссылок ---- */
.panel{position:relative;display:flex;flex-direction:column;flex:1;min-height:0;overflow:hidden}
.panel-head{display:flex;align-items:center;justify-content:space-between;gap:12px;flex:0 0 auto;
  padding:11px 15px;border-bottom:1px solid rgba(103,232,249,.07);background:rgba(255,255,255,.015);}
.panel-title{display:flex;align-items:center;gap:9px;font:700 10px var(--display);letter-spacing:.24em;text-transform:uppercase;color:#bfeffb}
.panel-title::before{content:"";width:9px;height:9px;background:var(--cyan);clip-path:polygon(0 0,100% 50%,0 100%);box-shadow:0 0 10px var(--cyan)}
.panel-note{font:500 10px var(--mono);color:var(--muted)}
.panel-body{display:flex;flex-direction:column;gap:10px;flex:1;min-height:0;padding:13px;overflow:auto}

textarea{width:100%;flex:1;min-height:110px;resize:none;padding:13px;border-radius:10px;outline:none;
  border:1px solid var(--line);background:rgba(3,12,20,.78);color:var(--text);
  font:500 12.5px/1.6 var(--mono);transition:.2s;}
textarea:focus{border-color:rgba(37,224,242,.55);box-shadow:0 0 0 3px rgba(37,224,242,.1),inset 0 0 26px rgba(37,224,242,.04)}
textarea.has-duplicates{border-color:rgba(251,111,132,.72);box-shadow:0 0 0 3px rgba(251,111,132,.12)}
textarea::placeholder{color:#5b7590}

/* ---- компактные платформы-полоски ---- */
#platformsBox{display:none;flex:0 0 auto;flex-direction:column;cursor:pointer;padding:4px;
  border:1px dashed transparent;border-radius:10px;transition:.2s;}
.platforms-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px;width:100%}
.platform-card{position:relative;height:42px;display:flex;align-items:center;overflow:hidden;
  border-radius:9px;border:1px solid rgba(255,255,255,.09);background:rgba(255,255,255,.03);transition:.2s;}
.platform-card:hover{transform:translateY(-2px);border-color:var(--line2);box-shadow:0 10px 22px rgba(0,0,0,.35)}
.platform-card.active{border-color:rgba(37,224,242,.28)}
.platform-card.done{border-color:rgba(52,211,153,.5)}
.platform-progress{position:absolute;inset:0}
.platform-progress-fill{position:relative;height:100%;width:0%;transition:width .3s;
  background:linear-gradient(90deg,rgba(10,99,214,.18),rgba(52,214,246,.34));
  border-right:2px solid rgba(94,240,250,.85);box-shadow:0 0 16px rgba(37,224,242,.28);}
.platform-progress-fill::after{content:"";position:absolute;inset:0;
  background:linear-gradient(100deg,transparent 30%,rgba(255,255,255,.16) 50%,transparent 70%);
  background-size:220% 100%;animation:flow 2.4s linear infinite;}
.platform-card.done .platform-progress-fill{background:linear-gradient(90deg,rgba(16,185,129,.16),rgba(52,211,153,.34));
  border-right-color:rgba(110,231,183,.95);}
.platform-top{position:relative;z-index:1;order:1;flex:1;min-width:0;display:flex;align-items:center;gap:9px;padding:0 10px}
.platform-icon{width:24px;height:24px;border-radius:6px;display:grid;place-items:center;flex:0 0 auto;
  background:var(--color,#334155);color:#fff;font:800 8px var(--display);box-shadow:0 2px 8px rgba(0,0,0,.45);}
.platform-info{position:relative;z-index:1;display:flex;align-items:baseline;gap:7px;min-width:0;flex:1}
.platform-name{font:700 11px var(--font);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.platform-sub{font:500 8.5px var(--mono);color:var(--muted);white-space:nowrap}
.platform-count{position:relative;z-index:1;order:2;margin-right:8px;min-width:24px;height:21px;padding:0 6px;
  display:grid;place-items:center;border-radius:6px;background:rgba(4,16,25,.75);
  border:1px solid var(--line);color:var(--cyan);font:800 9.5px var(--mono);}

/* ---- ЕДИНЫЙ стиль строк: превью дублей выглядит как системный список ---- */
#dupPreview{display:none;flex-direction:column;margin-top:8px;max-height:240px;overflow:auto;padding-right:4px}
#dupPreview:empty{display:none}
.duprow{position:relative;display:flex;align-items:center;gap:11px;padding:8px 12px;margin-bottom:6px;
  border-radius:9px;border:1px solid rgba(255,255,255,.05);background:rgba(255,255,255,.02);
  font:500 11px var(--mono);transition:.15s;}
.duprow:hover{border-color:var(--line);background:rgba(103,232,249,.045);transform:translateX(3px)}
.duprow-n{flex:0 0 auto;width:24px;text-align:right;font:700 10px var(--mono);letter-spacing:.05em;color:#587d95;transition:.2s}
.duprow:hover .duprow-n{color:var(--cyan)}
.duprow-u{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#cfe2f2}
.duprow.uns{opacity:.5}
.duprow.uns .duprow-u{color:var(--muted)}
.duprow.dup{border-color:rgba(251,111,132,.45);background:rgba(251,111,132,.08)}
.duprow.dup:hover{border-color:rgba(251,111,132,.65);background:rgba(251,111,132,.13);transform:translateX(3px)}
.duprow.dup .duprow-u{color:#ffb3c0}
.duprow.dup .duprow-n{color:rgba(251,111,132,.8)}
.duprow-tag{flex:0 0 auto;font:700 8px var(--mono);letter-spacing:.1em;text-transform:uppercase;
  color:#04141c;background:var(--red);padding:2px 7px;border-radius:5px;}
.duprow-del{flex:0 0 auto;width:24px;height:24px;border-radius:7px;border:1px solid rgba(251,111,132,.35);
  background:rgba(251,111,132,.1);color:#ffb9c5;cursor:pointer;display:grid;place-items:center;
  font-size:13px;line-height:1;transition:.15s;}
.duprow-del:hover{background:rgba(251,111,132,.3);border-color:rgba(251,111,132,.75);color:#fff;transform:scale(1.1)}
.duprow[data-tip]:hover::after{content:attr(data-tip);position:absolute;left:50%;bottom:calc(100% + 7px);
  transform:translateX(-50%);white-space:nowrap;background:rgba(8,20,30,.98);border:1px solid var(--line2);
  color:#ffd7de;padding:5px 10px;border-radius:7px;font:600 10px var(--mono);z-index:40;
  box-shadow:0 10px 26px rgba(0,0,0,.55);pointer-events:none;}
.duprow[data-tip]:hover::before{content:"";position:absolute;left:50%;bottom:calc(100% + 3px);
  transform:translateX(-50%);border:5px solid transparent;border-top-color:var(--line2);z-index:40;}

/* ---- системный список загрузки: пустой — прячем, чтобы не дублировал превью ---- */
#detailedLinksList{display:none;flex-direction:column;flex:1;overflow-y:auto;margin-top:10px;padding-right:4px;counter-reset:job}
#detailedLinksList:empty{display:none !important;margin:0}
.job-item{counter-increment:job;display:flex;align-items:center;gap:11px;padding:8px 12px;margin-bottom:6px;
  border-radius:9px;border:1px solid rgba(255,255,255,.05);background:rgba(255,255,255,.02);
  font:500 11px var(--mono);transition:.2s;}
.job-item::before{content:counter(job,decimal-leading-zero);flex:0 0 auto;width:24px;text-align:right;
  font:700 10px var(--mono);letter-spacing:.05em;color:#587d95;transition:.2s;}
.job-item:hover{border-color:var(--line);background:rgba(103,232,249,.045);transform:translateX(3px)}
.job-item:hover::before{color:var(--cyan)}
.job-item.success{border-color:rgba(52,211,153,.35);background:rgba(52,211,153,.06);color:#7ff0c4}
.job-item.success::before{color:rgba(52,211,153,.75)}
.job-item.error{border-color:rgba(251,111,132,.35);background:rgba(251,111,132,.06);color:#ffb3c0}
.job-item.error::before{color:rgba(251,111,132,.75)}
.job-url{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.job-status{font-size:14px}

#linksInfo{display:none !important;}

/* ---- журнал как вкладка 2 ---- */
.logview{display:flex;flex-direction:column;flex:1;min-height:0;overflow:hidden}
.termbar{height:34px;padding:0 15px;display:flex;align-items:center;gap:7px;flex:0 0 auto;
  border-bottom:1px solid rgba(255,255,255,.05);background:rgba(0,0,0,.22);}
.dot{width:8px;height:8px;border-radius:50%}
.r{background:#ff5f57}.y{background:#febc2e}.g{background:#28c840}
.term-name{flex:1;font:500 10px var(--mono);color:var(--muted)}
.term-status{font:600 10px var(--mono);color:var(--muted)}
.term-status.running{color:var(--cyan)}
.term-status.done{color:var(--green)}
.term-status.error{color:var(--red)}
.term-body{flex:1;min-height:0;overflow:auto;padding:13px 15px;
  font:400 11px/1.6 var(--mono);white-space:pre-wrap;word-break:break-word;}
.line-info{color:#a9bfd2}.line-ok{color:var(--green)}.line-error{color:var(--red)}
.line-warn{color:var(--amber)}.line-cmd{color:#6f8aa1}.line-url{color:#6fe3f7}
.line-sep{color:#3d5a70}.line-done{color:var(--green);font-weight:700}
.cursor{display:inline-block;width:7px;height:12px;background:var(--cyan);vertical-align:-2px;animation:blink 1s steps(1) infinite}
.cursor.hidden{display:none}
@keyframes blink{50%{opacity:0}}

/* ================= НИЖНИЙ ДОК ================= */
.dockbar{grid-area:dock;display:flex;align-items:center;gap:18px;padding:12px 20px;border-top:1px solid var(--line);
  background:linear-gradient(180deg,rgba(8,26,40,.94),rgba(4,15,24,.97));}
.dock-label{display:block;margin-bottom:6px;font:700 8.5px var(--mono);letter-spacing:.22em;text-transform:uppercase;color:var(--muted)}
.dock-path{flex:1;min-width:0}
.dock-input-row{display:flex;gap:8px}
.dock-input-row input{flex:1;min-width:0;height:38px}
.dock-sep{width:1px;align-self:stretch;background:var(--line)}
.dock-format{flex:0 0 auto;width:236px}

/* ================= МОДАЛКИ ================= */
.modal-backdrop{position:fixed;inset:0;z-index:9999;display:none;align-items:center;justify-content:center;
  padding:14px;background:rgba(2,8,14,.78);backdrop-filter:blur(6px);}
.modal-backdrop.show{display:flex}
.playlist-modal{width:min(680px,100%);max-height:86vh;display:flex;flex-direction:column;overflow:hidden;
  border-radius:14px;border:1px solid var(--line2);background:linear-gradient(170deg,#0b2539,#071a2a);
  box-shadow:0 30px 90px rgba(0,0,0,.65);animation:mSlide .24s cubic-bezier(.2,.8,.2,1);}
.modal-sm{width:min(540px,100%)}
.modal-sm2{width:min(560px,100%)}
@keyframes mSlide{from{transform:translateY(18px) scale(.98);opacity:0}to{transform:none;opacity:1}}
.playlist-header{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:14px 17px;
  border-bottom:1px solid var(--line);background:rgba(255,255,255,.02);}
.playlist-header h3{font:800 13px var(--display);letter-spacing:.04em;color:var(--cyan)}
.playlist-header h3.h-amber{color:#fcd34d}
.playlist-body{flex:1;overflow-y:auto;padding:16px 18px;display:flex;flex-direction:column;gap:12px;font:500 13px/1.6 var(--font);color:var(--text)}
.playlist-controls{display:flex;gap:8px}
.playlist-list{max-height:400px;overflow-y:auto;padding:7px;border-radius:11px;border:1px solid var(--line);background:rgba(3,12,20,.72)}
.playlist-item{display:flex;align-items:center;gap:11px;padding:9px 11px;margin-bottom:3px;border-radius:8px;cursor:pointer;transition:.12s}
.playlist-item:hover{background:rgba(103,232,249,.06)}
.playlist-item input[type="checkbox"]{width:17px;height:17px;margin:0;cursor:pointer;accent-color:var(--cyan)}
.playlist-item-title{font:600 12.5px var(--font);color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;user-select:none}
.playlist-footer{display:flex;justify-content:flex-end;gap:9px;padding:13px 17px;border-top:1px solid var(--line);background:rgba(255,255,255,.015)}
.changelog{padding:14px 16px;border-radius:12px;border:1px solid rgba(37,224,242,.16);background:rgba(37,224,242,.045)}
.changelog-lead{display:block;margin-bottom:9px;color:var(--cyan);font:700 12.5px var(--font)}
.changelog ul{padding-left:20px;display:grid;gap:8px;list-style:disc;font:500 12.5px/1.55 var(--font)}
.changelog b{color:#cdeeff}
.changelog hr{border:0;border-top:1px solid rgba(255,255,255,.06);margin:4px 0}
.time-list{margin-top:12px;display:flex;flex-direction:column;gap:8px}
#timeApplyAllWrap{display:none;align-items:center;gap:9px;margin-top:14px;cursor:pointer;font-size:12.5px;user-select:none}
#timeApplyAllWrap input{width:17px;height:17px;accent-color:var(--cyan);cursor:pointer}

.toast{position:fixed;right:20px;bottom:86px;z-index:10000;max-width:min(400px,calc(100vw - 40px));
  padding:12px 15px;border-radius:11px;border:1px solid var(--line2);background:rgba(8,26,41,.97);
  color:var(--text);font:600 11.5px var(--mono);box-shadow:0 20px 60px rgba(0,0,0,.5);
  transform:translateY(24px);opacity:0;pointer-events:none;transition:.24s;}
.toast.show{transform:translateY(0);opacity:1}

#rightClickMenu,#listRightClickMenu{position:fixed;z-index:9999;display:none;min-width:220px;padding:6px;
  border-radius:11px;border:1px solid var(--line2);background:rgba(10,28,44,.98);
  box-shadow:0 16px 44px rgba(0,0,0,.6);backdrop-filter:blur(10px);}
.rc-btn{width:100%;height:32px;border:none;border-radius:7px;background:transparent;color:#dcecff;
  text-align:left;padding:0 10px;cursor:pointer;display:flex;align-items:center;gap:10px;
  font:500 12.5px var(--font);transition:.1s ease;}
.rc-btn:hover{background:rgba(37,224,242,.14);color:#fff}
.rc-btn.danger:hover{background:rgba(251,111,132,.15);color:#ffb4c0}
.rc-sep{height:1px;background:rgba(255,255,255,.08);margin:4px 6px}
.rc-icon{font-size:14px;opacity:.8;width:18px;text-align:center}

/* ================= АДАПТИВ ================= */
@media(max-width:1180px){
  .app{grid-template-columns:232px minmax(0,1fr)}
  .session-text{display:none}
  .tstat{padding:6px 9px}
}
@media(max-width:940px){
  .app{grid-template-columns:1fr;grid-template-rows:auto minmax(0,1fr) auto;grid-template-areas:"side" "main" "dock"}
  .sidebar{flex-direction:row;flex-wrap:wrap;align-items:center;gap:10px;padding:12px 14px;border-right:0;border-bottom:1px solid var(--line)}
  .sidebar::after{display:none}
  .brand{margin-right:auto}
  .sidebar .btn{width:auto}
  .side-label,.side-footer{display:none}
  .topline{grid-template-columns:1fr auto;gap:10px}
  .topstats{order:3;grid-column:1/-1;justify-self:stretch;overflow:auto}
  .settings-window,.about-window{position:fixed;left:12px;right:12px;top:64px;width:auto;transform-origin:top center}
  .dockbar{flex-direction:column;align-items:stretch;gap:12px}
  .dock-format{width:100%}
  .dock-sep{display:none}
}
@media(max-width:560px){.settings-grid{grid-template-columns:1fr}.main{padding:12px}.platforms-grid{grid-template-columns:1fr}}

/* =====================================================================
   БАЙКАЛ v4 — горы как на сплэше + «аквариум»-панели + живой глубиномер
   (вставлено последним — перебивает v3; комментарии закрыты корректно)
   ===================================================================== */

/* ---- СИЛУЭТЫ ГОР: два плана по краям, световой провал по центру ---- */
.bg-mountains {
  position: fixed;
  left: 0; right: 0; top: 0;
  height: 52vh;
  z-index: 0;
  pointer-events: none;
  opacity: .6;
  
  /* В SVG добавлен <filter id="blur"> и применен к полигонам */
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1440 400' preserveAspectRatio='none'%3E%3Cdefs%3E%3Cfilter id='b'%3E%3CfeGaussianBlur stdDeviation='8'/%3E%3C/filter%3E%3C/defs%3E%3Cg filter='url(%23b)'%3E%3Cpolygon fill='%230e2c4a' fill-opacity='.7' points='0,400 0,120 90,150 180,90 280,170 380,110 470,210 560,300 720,400'/%3E%3Cpolygon fill='%230e2c4a' fill-opacity='.7' points='1440,400 1440,120 1350,150 1260,90 1160,170 1060,110 970,210 880,300 720,400'/%3E%3Cpolyline fill='none' stroke='%23bfe6ff' stroke-opacity='.5' stroke-width='2' points='0,120 90,150 180,90 280,170 380,110 470,210 560,300'/%3E%3Cpolyline fill='none' stroke='%23bfe6ff' stroke-opacity='.5' stroke-width='2' points='1440,120 1350,150 1260,90 1160,170 1060,110 970,210 880,300'/%3E%3Cpolygon fill='%23061426' fill-opacity='.92' points='0,400 0,250 120,210 240,270 360,230 520,330 720,400'/%3E%3Cpolygon fill='%23061426' fill-opacity='.92' points='1440,400 1440,250 1320,210 1200,270 1080,230 920,330 720,400'/%3E%3C/g%3E%3C/svg%3E");
  
  background-repeat: no-repeat;
  background-position: center top;
  background-size: 100% 100%;
  -webkit-mask-image: linear-gradient(180deg, #000 55%, transparent 100%);
  mask-image: linear-gradient(180deg, #000 55%, transparent 100%);
}

/* ---- мерцание горизонта + дрейф отражения на воде ---- */
.bg-horizon{animation:horizonPulse 7s ease-in-out infinite}
@keyframes horizonPulse{0%,100%{opacity:.78;box-shadow:0 0 22px 5px rgba(40,150,230,.30),0 0 80px 22px rgba(20,90,180,.18)}
  50%{opacity:1;box-shadow:0 0 34px 9px rgba(56,189,248,.5),0 0 110px 30px rgba(20,90,180,.28)}}
.bg-horizon::after{animation:waterDrift 14s ease-in-out infinite alternate}
@keyframes waterDrift{from{transform:translateX(-2%) scaleY(1)}to{transform:translateX(2%) scaleY(1.06)}}

/* ---- «АКВАРИУМ»: панели слегка прозрачны, трещины проступают мягко ---- */
.workspace{background:linear-gradient(180deg,rgba(7,22,36,.74),rgba(5,16,28,.80));
  backdrop-filter:blur(2px);-webkit-backdrop-filter:blur(2px);}
.gauge{background:linear-gradient(120deg,rgba(11,36,54,.76),rgba(6,20,34,.82));
  backdrop-filter:blur(2px);-webkit-backdrop-filter:blur(2px);}
.tabs{background:rgba(8,24,38,.42)}
.panel-head{background:rgba(8,24,38,.40)}
.panel-body{background:transparent}
.termbar{background:rgba(2,10,18,.40)}
.logview{background:linear-gradient(180deg,rgba(5,16,28,.30),rgba(3,11,20,.42))}
textarea{background:rgba(3,12,20,.66)}
.platform-card{background:rgba(10,28,44,.50);border-color:rgba(125,211,252,.14)}
.platform-card:hover{background:rgba(14,36,56,.66)}
.platform-card.active{background:rgba(12,32,52,.55)}
.platform-card.active.done{background:linear-gradient(150deg,rgba(16,92,72,.42),rgba(9,42,34,.34))}
.duprow,.job-item{background:rgba(10,28,44,.45)}
.duprow.dup{background:rgba(62,20,32,.45)}
.job-item.success{background:rgba(13,48,40,.45)}
.job-item.error{background:rgba(62,20,32,.45)}
.tstat{background:rgba(8,24,38,.50)}
.icon-btn{background:rgba(8,24,38,.50)}
.server{background:rgba(4,16,25,.50)}

/* ---- ГЛУБИНОМЕР: полное рабочее правило (перебивает съеденное комментарием) ---- */
.depth-gauge{
  position:relative;left:auto;right:auto;top:auto;bottom:auto;
  width:auto;height:auto;overflow:hidden;
  display:flex;flex-direction:column;align-items:stretch;gap:11px;
  flex:1 1 auto;min-height:150px;margin:6px 0 2px;padding:13px 13px 13px 15px;
  border:1px solid var(--line);border-radius:12px;
  background:linear-gradient(180deg,rgba(6,22,38,.55),rgba(4,14,26,.40));
  backdrop-filter:blur(2px);-webkit-backdrop-filter:blur(2px);
  font-family:var(--mono);}
.depth-gauge::before,.depth-gauge::after{content:"";position:absolute;width:10px;height:10px;pointer-events:none}
.depth-gauge::before{top:-1px;left:-1px;border-top:2px solid rgba(37,224,242,.45);border-left:2px solid rgba(37,224,242,.45);border-top-left-radius:12px}
.depth-gauge::after{bottom:-1px;right:-1px;border-bottom:2px solid rgba(37,224,242,.45);border-right:2px solid rgba(37,224,242,.45);border-bottom-right-radius:12px}
.dg-head{position:relative;z-index:2;display:flex;align-items:baseline;justify-content:space-between;gap:8px}
.dg-cap{font:700 8px var(--mono);letter-spacing:.22em;text-transform:uppercase;color:var(--muted);text-align:left}
.dg-now{display:flex;align-items:baseline;gap:3px}
.dg-num{width:auto;text-align:left;padding:0;font:800 23px/1 var(--display);color:var(--cyan);
  text-shadow:0 0 14px rgba(37,224,242,.5);font-variant-numeric:tabular-nums}
.dg-unit{font:600 9px var(--mono);color:var(--muted)}
.dg-track{position:relative;z-index:2;flex:1 1 auto;min-height:0;margin-left:5px}
.dg-track::before{content:"";position:absolute;left:0;top:2px;bottom:2px;width:3px;border-radius:3px;
  background:linear-gradient(180deg,rgba(125,211,252,.5),rgba(37,224,242,.22) 45%,rgba(15,180,212,.08))}
.dg-fill{position:absolute;left:0;top:2px;width:3px;height:0;border-radius:3px;
  background:linear-gradient(180deg,#7dd3fc,#25e0f2);box-shadow:0 0 12px rgba(37,224,242,.7);transition:height .12s linear}
.dg-mark{position:absolute;left:-4px;right:auto;top:0;transform:translateY(-50%);
  display:flex;align-items:center;transition:top .12s linear}
.dg-dot{position:static;left:auto;width:11px;height:11px;border-radius:50%;
  background:#eaf7ff;border:2px solid #25e0f2;box-shadow:0 0 12px rgba(37,224,242,.9)}
.dg-mark::after{content:"";width:9px;height:2px;background:rgba(125,211,252,.7);margin-left:2px;border-radius:2px}
.dg-scale i{position:absolute;left:-2px;width:7px;height:1px;background:rgba(125,211,252,.4)}
.dg-scale i:nth-child(1){top:2px}
.dg-scale i:nth-child(2){top:25%}
.dg-scale i:nth-child(3){top:50%}
.dg-scale i:nth-child(4){top:75%}
.dg-scale i:nth-child(5){top:auto;bottom:2px}
.dg-labels{position:absolute;left:16px;top:0;bottom:0;display:flex;flex-direction:column;
  justify-content:space-between;font:500 8px var(--mono);color:rgba(126,151,171,.62)}
.dg-max{display:none}

/* ---- ПУЗЫРЬКИ СО ДНА в сайдбаре (воздух поднимается из глубины) ---- */
.bubbles{position:absolute;inset:0;z-index:0;pointer-events:none;overflow:hidden;border-radius:0}
.bubbles i{position:absolute;bottom:-16px;border-radius:50%;
  border:1px solid rgba(125,211,252,.30);background:rgba(125,211,252,.06);
  box-shadow:0 0 6px rgba(56,189,248,.18);animation:bubbleRise linear infinite}
.bubbles i:nth-child(1){left:14%;width:6px;height:6px;animation-duration:11s}
.bubbles i:nth-child(2){left:38%;width:4px;height:4px;animation-duration:15s;animation-delay:2s}
.bubbles i:nth-child(3){left:62%;width:8px;height:8px;animation-duration:13s;animation-delay:5s}
.bubbles i:nth-child(4){left:82%;width:5px;height:5px;animation-duration:17s;animation-delay:1s}
.bubbles i:nth-child(5){left:50%;width:3px;height:3px;animation-duration:9s;animation-delay:3.5s}
@keyframes bubbleRise{0%{transform:translateY(0) translateX(0);opacity:0}
  10%{opacity:.7}90%{opacity:.5}
  100%{transform:translateY(-780px) translateX(10px);opacity:0}}
/* контент сайдбара — поверх пузырьков */
.sidebar > *:not(.bubbles){position:relative;z-index:1}

/* ---- пульс-свечение логотипа (лёгкое «дыхание») ---- */
.logo{animation:logoBreathe 5s ease-in-out infinite}
@keyframes logoBreathe{0%,100%{box-shadow:0 8px 22px rgba(0,0,0,.5),0 0 0 1px rgba(103,232,249,.3),0 0 0 0 rgba(56,189,248,0)}
  50%{box-shadow:0 8px 22px rgba(0,0,0,.5),0 0 0 1px rgba(103,232,249,.45),0 0 22px 2px rgba(56,189,248,.25)}}

@media(max-width:940px){.depth-gauge{display:none}.bg-mountains{opacity:.5}}


</style>
</head>
<body>
<div class="bg-grid" aria-hidden="true"></div>
<div class="bg-sweep" aria-hidden="true"></div>
<div class="bg-horizon" aria-hidden="true"></div>
<div class="bg-ice" aria-hidden="true"></div>
<div class="bg-mountains" aria-hidden="true"></div>

<div class="app">

  <!-- ================= СЛЕВА ================= -->
  <aside class="sidebar">
    <div class="bubbles" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></div>
    <div class="brand">
      <img class="logo" src="/bkL.png" alt="Logo">
      <div>
        <h1>Байкал</h1>
        <p>Downloader 5.6.14</p>
      </div>
    </div>

    <button class="btn btn-primary" id="btnStart" onclick="startDownload()">▶&nbsp;Скачать</button>
    <button class="btn btn-stop" id="btnStop" onclick="cancelDownload()" style="display: none;">■&nbsp;Стоп</button>

    <div class="side-label">Инструменты</div>
    <button class="btn" onclick="pasteFromClipboard()"><span class="btn-ico">📋</span>Вставить ссылки</button>
    <button class="btn btn-ghost-red" onclick="clearLinks()"><span class="btn-ico">🧹</span>Очистить очередь</button>

    <div class="side-footer">Умные загрузки · без границ</div>
  </aside>

  <!-- ================= СПРАВА ================= -->
  <main class="main" id="mainArea">

    <header class="topline">
      <div class="session">
        <span class="session-dot"></span>
        <span class="session-text">Сессия</span>
        <span id="liveClock" class="session-clock">--:--:--</span>
      </div>

      <div class="topstats">
        <div class="tstat"><b id="totalCount">0</b><span>Уник.</span></div>
        <div class="tstat"><b id="doneCount">0</b><span>Готово</span></div>
        <div class="tstat" id="dupStatBox"><b id="duplicateCount">0</b><span>Дубли</span></div>
        <div class="tstat"><b id="retainCount">0</b><span>Не подд.</span></div>
      </div>

      <div class="topline-right">
        <div id="serverPill" class="server disconnected">
          <span class="server-dot"></span>
          <span id="serverPillText">Проверяю сервер...</span>
        </div>
        <details class="settings">
          <summary class="icon-btn" title="Настройки"><span class="ico ico-gear">⚙</span></summary>
          <div class="settings-window">
            <div class="settings-title"><span>Настройки загрузки</span><small>сохраняются автоматически</small></div>
            <div class="settings-grid">
              <div class="field">
                <label>Сегмент YouTube, сек</label>
                <input id="segment-duration" type="number" value="12" min="1">
              </div>
              <div class="field">
                <label>Макс. длительность, сек</label>
                <input id="max-duration" type="number" value="" min="0" placeholder="без ограничения">
              </div>
              <div class="field full">
                <label>Имена сохранённых файлов</label>
                <select id="use-real-names">
                  <option value="true">Оригинальные (названия видео)</option>
                  <option value="false">Классические (числовые 597, -pxl, -pxb)</option>
                </select>
              </div>
              <div class="field full">
                <label>Авторизация YouTube (для 18+ и закрытых видео)</label>
                <select id="browser-cookies">
                  <option value="none">Не использовать (Анонимно)</option>
                  <option value="auth_profile">Использовать встроенный профиль (Кнопка ниже)</option>
                </select>
              </div>
              <div class="field full">
                <button id="btn-auth" class="btn btn-auth" style="background: __AUTH_COLOR__;" onclick="openYoutubeAuth()">__AUTH_BTN_TEXT__</button>
                <p id="auth-hint">__AUTH_HINT__</p>
              </div>
              <div class="field full">
                <button class="btn btn-green" onclick="saveCurrentSettings(true, true)">💾 Сохранить настройки</button>
              </div>
            </div>
          </div>
        </details>
        <details class="about-menu" id="aboutMenu">
          <summary class="icon-btn" title="О программе"><span class="ico">ℹ</span></summary>
          <div class="about-window">
            <div class="about-head">
              <img class="about-logo" src="/bkL.png" alt="Logo">
              <div class="about-title">
                <b>Байкал Downloader</b>
                <span id="aboutVersion">версия: 5.6.14</span>
              </div>
            </div>
            <div class="about-text">
              <div>Автор: <b id="aboutAuthor">Iurii Cojocari (Time VEGAS PRO)</b></div>
              <div>Донат PayPal: <a id="aboutPaypal" href="#" onclick="openDonate(); return false;">paypal.me/studioyouar</a></div>
              <div>Донат Boosty: <a id="aboutBoosty" href="#" onclick="openBoosty(); return false;">boosty.to/time_vegas_pro</a></div>
              
              <div style="opacity:.6;font-size:9px;margin-top:4px;border-top:1px solid rgba(255,255,255,.05);padding-top:4px;">
                Версия ядра yt-dlp: <span id="aboutYtdlpVersion">определяется...</span>
              </div>
            </div>
            <div class="about-actions">
              <button class="btn btn-blue" onclick="openWhatsNewModal()">💡 Что нового в v5.6.14</button>
              <button class="btn" onclick="checkProgramUpdate()">🔄 Проверить обновление</button>
              <button class="btn btn-green" onclick="installProgramUpdate()">⬇ Обновить программу</button>
            </div>
            <div id="updateStatus" class="update-status">Готово к проверке обновлений.</div>
          </div>
        </details>
      </div>
    </header>

    <section class="gauge">
      <div class="gauge-ratio"><b id="progressRatio">0 / 0</b><span>очередь</span></div>
      <div class="gauge-sep"></div>
      <div class="gauge-mid">
        <div class="gauge-meta">
          <span id="progressLabel">Ожидание...</span>
          <span id="progressPct" class="gauge-pct">0%</span>
        </div>
        <div class="progress-track"><div id="progressBar" class="progress-fill"></div></div>
      </div>
    </section>

    <section class="workspace">
      <div class="tabs">
        <button class="tab-btn active" data-tab="tabLinks"><span class="tab-ico">▶</span>Ссылки и платформы</button>
        <button class="tab-btn" data-tab="tabLog" id="tabLogBtn"><span class="tab-ico">📟</span>Журнал<span class="tab-pulse"></span></button>
      </div>

      <div class="tab-pane active" id="tabLinks">
        <section class="panel workspace-panel">
          <div class="panel-head">
            <div class="panel-title">Рабочее пространство</div>
            <div class="panel-note" id="workspaceNote">Вставь ссылки — они превратятся в карточки</div>
          </div>
          <div class="panel-body">
            <textarea id="inputLinks" placeholder="Вставь ссылки сюда, каждая с новой строки.

Поддерживаются ВИДЕО:
YouTube (и плейлисты), RuTube, Dzen, VK, Facebook, Instagram, TikTok, Vimeo, Twitch и др.
Поддерживается МУЗЫКА:
SoundCloud, Yandex Music, Apple Music, Spotify, Bandcamp. (скачиваются в MP3)"></textarea>

            <div id="platformsBox" style="display: none;" title="Кликни, чтобы редактировать ссылки">
              <div id="platforms" class="platforms-grid"></div>
            </div>

            <!-- единственный превью-список строк: дубли красные + тултип + крестик -->
            <div id="dupPreview"></div>

            <div id="detailedLinksList" style="display: none;"></div>
            <div id="linksInfo" class="info-box"></div>
          </div>
        </section>
      </div>

      <div class="tab-pane" id="tabLog">
        <div class="logview">
          <div class="termbar">
            <span class="dot r"></span><span class="dot y"></span><span class="dot g"></span>
            <span class="term-name">журнал_скачивания.log</span>
            <span id="termStatus" class="term-status idle">● ожидание</span>
          </div>
          <div id="termBody" class="term-body">
            <span class="line-info">Ожидание...</span><br>
            <span class="line-ok">Система готова.</span><br>
            <span id="cursor" class="cursor hidden"></span>
          </div>
        </div>
      </div>
    </section>

  </main>

  <!-- ================= СНИЗУ: путь сразу раскрытый (сервер отдаёт абсолютный) ================= -->
 <footer class="dockbar">
    <div class="dock-group dock-path">
      <label class="dock-label" for="directory">Путь сохранения</label>
      <div class="dock-input-row">
        <input id="directory" type="text" value="" placeholder="Например: C:\Users\Имя\Downloads">
        <!-- Скрытый инпут для выбора папки на ПК без громоздких PowerShell диалогов -->
        <input type="file" id="folderPickerInput" webkitdirectory directory style="display:none;" onchange="onFolderPicked(event)">
        <button class="btn btn-slim" onclick="browseFolder()">🔎 Обзор</button>
        <button class="btn btn-slim" onclick="openFolder()"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--cyan);">
                      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                    </svg> Открыть</button>
        </div>
    </div>
    <div class="dock-sep"></div>
        <div class="dock-group" style="width: 130px;">
      <label class="dock-label" for="dock-segment-duration">Сегмент,  сек</label>
      <input id="dock-segment-duration" type="number" value="12" min="1" style="height: 38px;">
    </div>
    <div class="dock-group" style="width: 150px;">
      <label class="dock-label" for="dock-max-duration">Макс. лимит, сек</label>
      <input id="dock-max-duration" type="number" value="" min="0" placeholder="без лимита" style="height: 38px;">
    </div>
    <div class="dock-sep"></div>
    <div class="dock-group dock-format">
      <label class="dock-label" for="format">Качество / формат</label>
              <select id="format" style="height: 38px;">
        <option value="bestvideo+bestaudio/best">Максимальное 4K - webm/av1 (Оригинал)</option>
        
        <option value="bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best">Лучшее MP4</option>
        <option value="bestvideo[height<=1080][vcodec^=avc]+bestaudio[ext=m4a]/best[height<=1080][vcodec^=avc]/best">1080p</option>
        <option value="bestvideo[height<=720][vcodec^=avc]+bestaudio[ext=m4a]/best[height<=720][vcodec^=avc]/best">720p</option>
        <option value="bestvideo[height<=480][vcodec^=avc]+bestaudio[ext=m4a]/best[height<=480][vcodec^=avc]/best">480p</option>
        <option value="bestaudio-mp3">Только аудио (MP3)</option>
      </select>
    </div>
  </footer>

</div>

<!-- ================= МОДАЛКИ ================= -->
<div id="playlistModal" class="modal-backdrop">
  <div class="playlist-modal">
    <div class="playlist-header">
      <h3 id="playlistModalTitle">Обнаружен плейлист</h3>
      <button class="btn btn-icon" onclick="closePlaylistModal()">✕</button>
    </div>
    <div class="playlist-body">
      <div class="playlist-controls">
        <button class="btn btn-green" onclick="toggleAllPlaylist(true)">✓ Выбрать все</button>
        <button class="btn btn-red" onclick="toggleAllPlaylist(false)">𗙚 Снять все</button>
      </div>
      <div id="playlistContainer" class="playlist-list"></div>
    </div>
    <div class="playlist-footer">
      <button class="btn" onclick="closePlaylistModal()">Отмена</button>
      <button class="btn btn-main" id="btnConfirmPlaylist" onclick="confirmPlaylistDownload()">Загрузить выбранное</button>
    </div>
  </div>
</div>

<div id="whatsNewModal" class="modal-backdrop">
  <div class="playlist-modal modal-sm">
    <div class="playlist-header">
      <h3>🚀 Что нового в версии 5.6.14</h3>
      <button class="btn btn-icon" onclick="closeWhatsNewModal()">✕</button>
    </div>
    <div class="playlist-body">
      <div class="changelog">
        <b class="changelog-lead">✨ Главные нововведения:</b>
        <ul>
          <li><b>🎬 Автоперекодировка в H.264 (AVC):</b> После скачивания программа сама проверяет кодеки видео. Если найдёт VP9, AV1 или другой формат — предложит перекодировать файлы в H.264. Просто нажмите «Да»!</li>
          <li><b>⏱ Умный выбор для видео с таймкодом:</b> Кидаете ссылку с привязкой ко времени (<b>?t=</b>)? Теперь программа спросит: скачать только короткий сегмент или всё видео целиком. А если таких видео много — можно применить выбор сразу ко всем одной галочкой.</li>
          <li><b>✅ Умное возобновление по ссылке:</b> Логика пропуска скачанных файлов стала точнее. Теперь программа сравнивает сами ссылки, а не их порядок в списке — поэтому новые ссылки больше никогда не помечаются ложным статусом «Уже скачано».</li>
          <hr>
          <li><b>Умное возобновление загрузки:</b> Если вы нажали «Стоп», а затем снова запустили скачивание, программа автоматически пропустит уже скачанные файлы (✅) и продолжит работу с того места, где остановилась.</li>
          <li><b>Меню для списка ссылок:</b> По ссылкам в списке загрузок можно кликнуть правой кнопкой мыши: выделенный фрагмент можно скопировать, а видео — сразу открыть в браузере.</li>
          <li><b>Умное рабочее пространство:</b> Панели «Ссылки» и «Платформы» объединены — текстовое поле красиво превращается в компактные карточки платформ.</li>
          <li><b>Мгновенная отмена (Кнопка «Стоп»):</b> Прервите загрузку и очистите очередь одним кликом в любой момент.</li>
          <li><b>Бесшовная авторизация YouTube:</b> Поддержка Яндекс Браузера, Opera, Brave, Vivaldi и macOS без устаревших всплывающих окон.</li>
          <li><b>Авто-Deno и Node.js:</b> Решение проблемы «This video is not available» — движки для расшифровки алгоритмов YouTube качаются автоматически.</li>
          <li><b>Авто-MP3 для музыки:</b> Spotify, Яндекс.Музыка, Apple Music, SoundCloud, Bandcamp и Mixcloud скачиваются в MP3 автоматически.</li>
        </ul>
      </div>
    </div>
    <div class="playlist-footer">
      <button class="btn btn-main" onclick="closeWhatsNewModal()">Отлично!</button>
    </div>
  </div>
</div>

<div id="convertModal" class="modal-backdrop">
  <div class="playlist-modal modal-sm">
    <div class="playlist-header">
      <h3 class="h-amber">🎬 Обнаружены файлы с другим кодеком</h3>
    </div>
    <div class="playlist-body">
      <div id="convertInfo">Проверка...</div>
    </div>
    <div class="playlist-footer">
      <button class="btn btn-red" onclick="cancelConvertH264()">Нет, оставить</button>
      <button class="btn btn-green" onclick="confirmConvertH264()">✅ Да, перекодировать</button>
    </div>
  </div>
</div>

<div id="timeModal" class="modal-backdrop">
  <div class="playlist-modal modal-sm2">
    <div class="playlist-header">
      <h3>⏱ Обнаружены видео с таймкодом</h3>
    </div>
    <div class="playlist-body">
      <div id="timeModalInfo">Проверка...</div>
      <div id="timeModalList" class="time-list"></div>
      <label id="timeApplyAllWrap">
        <input type="checkbox" id="timeApplyAll">
        <span>Применить выбор ко всем видео с таймкодом</span>
      </label>
    </div>
    <div class="playlist-footer">
      <button class="btn btn-blue" onclick="resolveTimeChoice('segment')">✂ Только сегмент (12 сек)</button>
      <button class="btn btn-green" onclick="resolveTimeChoice('full')">🎬 Скачать целиком</button>
    </div>
  </div>
</div>

<div id="toast" class="toast"></div>

<!-- ================================================================
     МИНИ-СКРИПТЫ ИНТЕРФЕЙСА (часы + вкладки + единый список дублей).
     НЕ заменяют основную логику — только дополняют её.
================================================================ -->
<script>
/* ---- живые часы ---- */
setInterval(function(){
  var c = document.getElementById('liveClock');
  if(c){ c.textContent = new Date().toLocaleTimeString('ru-RU'); }
}, 1000);

/* ---- вкладки (без авто-открытия журнала при старте) ---- */
function activateTab(id){
  document.querySelectorAll('.tab-btn').forEach(function(x){
    x.classList.toggle('active', x.getAttribute('data-tab') === id);
  });
  document.querySelectorAll('.tab-pane').forEach(function(p){
    p.classList.toggle('active', p.id === id);
  });
}
document.querySelectorAll('.tab-btn').forEach(function(b){
  b.addEventListener('click', function(){ activateTab(b.getAttribute('data-tab')); });
});
/* только пульс-индикатор на вкладке «Журнал» во время загрузки — НЕ переключаем вкладку сами */
(function(){
  var ts = document.getElementById('termStatus');
  var btn = document.getElementById('tabLogBtn');
  if(!ts) return;
  new MutationObserver(function(){
    if(btn) btn.classList.toggle('live', /running/.test(ts.className));
  }).observe(ts, {attributes:true, attributeFilter:['class']});
})();

/* ---- удаление строки-дубля из поля ссылок ---- */
function removeDupLine(lineNum){
  var inp = document.getElementById('inputLinks');
  if(!inp) return;
  var lines = inp.value.split('\n');
  var idx = lineNum - 1;
  if(idx >= 0 && idx < lines.length){ lines.splice(idx, 1); inp.value = lines.join('\n'); }
  if(typeof updateCounts === 'function') updateCounts();
  renderDupPreview();
  showToast('🗑 Дубликат удалён из очереди');
}

/* ---- единый превью-список: стиль как у системного, дубли красные + тултип + крестик ---- */
function renderDupPreview(){
  var box = document.getElementById('dupPreview');
  if(!box || typeof analyzeLinks !== 'function') return;
  var a = analyzeLinks();
  if(!a || !a.links || !a.links.length){ box.innerHTML = ''; return; }
  var h = '';
  a.links.forEach(function(it){
    var cls = 'duprow', tip = '';
    if(it.duplicate){ cls += ' dup'; tip = 'Дубликат строки ' + it.firstLine; }
    else if(!it.supported){ cls += ' uns'; tip = 'Не поддерживается'; }
    var safe = (typeof escapeHtml === 'function') ? escapeHtml(it.url) : String(it.url);
    var num = String(it.line).padStart(2,'0');
    var del = it.duplicate
      ? '<button class="duprow-del" title="Удалить этот дубликат" onclick="event.stopPropagation();removeDupLine(' + it.line + ')">✕</button>'
      : '';
    h += '<div class="' + cls + '"' + (tip ? ' data-tip="' + tip.replace(/"/g,'&quot;') + '"' : '') + '>'
       + '<span class="duprow-n">' + num + '</span>'
       + '<span class="duprow-u">' + safe + '</span>'
       + (it.duplicate ? '<span class="duprow-tag">дубль</span>' : '')
       + del + '</div>';
  });
  box.innerHTML = h;
}

/* ---- видимость превью: ТОЛЬКО в режиме карточек ДО загрузки (иначе системный список) ---- */
function syncDupPreview(){
  var pb = document.getElementById('platformsBox');
  var bs = document.getElementById('btnStop');
  var dl = document.getElementById('detailedLinksList');
  var box = document.getElementById('dupPreview');
  if(!pb || !box) return;
  var pbVis   = pb.style.display && pb.style.display !== 'none';
  var running = bs && bs.style.display && bs.style.display !== 'none' && bs.style.display !== '';
  var listHas = dl && dl.childElementCount > 0;          /* системный список уже построен */
  if(pbVis && !running && !listHas){ box.style.display = 'flex'; renderDupPreview(); }
  else { box.style.display = 'none'; }
}
(function(){
  var pb = document.getElementById('platformsBox');
  var bs = document.getElementById('btnStop');
  var dl = document.getElementById('detailedLinksList');
  var inp = document.getElementById('inputLinks');
  if(pb) new MutationObserver(syncDupPreview).observe(pb, {attributes:true, attributeFilter:['style']});
  if(bs) new MutationObserver(syncDupPreview).observe(bs, {attributes:true, attributeFilter:['style']});
  if(dl) new MutationObserver(syncDupPreview).observe(dl, {childList:true, attributes:true, attributeFilter:['style']});
  if(inp) inp.addEventListener('input', function(){
    var box = document.getElementById('dupPreview');
    if(box && box.style.display !== 'none') renderDupPreview();
  });
})();


</script>



<script>
const SERVER = window.location.origin;

function setUpdateStatus(text, cls=''){
  const el = document.getElementById('updateStatus');

  if(!el){
    return;
  }

  el.className = `update-status ${cls || ''}`;
  el.textContent = text;
}

function openWhatsNewModal(){
  const about = document.getElementById('aboutMenu');
  if(about){
    about.open = false;
    about.classList.remove('is-closing');
    document.body.classList.remove('popup-open');
  }
  document.getElementById('whatsNewModal').classList.add('show');
}

function closeWhatsNewModal(){
  document.getElementById('whatsNewModal').classList.remove('show');
}

async function loadAppInfo(){
  try{
    const r = await fetch(`${SERVER}/app-info`, {
      method:'GET',
      cache:'no-store'
    });

    if(!r.ok){
      return;
    }

    const d = await r.json();

    const versionEl = document.getElementById('aboutVersion');
    const authorEl = document.getElementById('aboutAuthor');
    const paypalEl = document.getElementById('aboutPaypal');
    const boostyEl = document.getElementById('aboutBoosty');
    const updEl = document.getElementById('aboutUpdateVersion');

    if(versionEl){
      versionEl.textContent = `версия: ${d.version || 'неизвестно'}`;
    }

    if(authorEl){
      authorEl.textContent = d.author || 'Iurii Cojocari (Time VEGAS PRO)';
    }

    if(paypalEl){
      paypalEl.textContent = d.paypal || 'paypal.me/studioyouar';
      if(d.paypal_url){
        paypalEl.onclick = async () => {
          try{
            await fetch(`${SERVER}/open-url`, {
              method:'POST',
              headers:{'Content-Type':'application/json'},
              body:JSON.stringify({ url:d.paypal_url })
            });
          }catch(e){
            window.open(d.paypal_url, '_blank');
          }
          return false;
        };
      }
    }

    if(boostyEl){
      boostyEl.textContent = d.boosty || 'boosty.to/time_vegas_pro';
      if(d.boosty_url){
        boostyEl.onclick = async () => {
          try {
            await fetch(`${SERVER}/open-url`, {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({ url: d.boosty_url })
            });
          } catch(e) {
            window.open(d.boosty_url, '_blank');
          }
          return false;
        }
      }
    }

    if(updEl){
      updEl.textContent = d.update_version ? `v${d.update_version}` : 'неизвестно';
    }
  }catch(e){}
}

async function checkProgramUpdate(){
  setUpdateStatus('Проверяю обновление...', '');

  try{
    const r = await fetch(`${SERVER}/check-update`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({})
    });

    const d = await r.json();

    if(!r.ok || !d.ok){
      setUpdateStatus(d.error || 'Не удалось проверить обновление', 'error');
      showToast('⚠ Ошибка проверки обновления');
      return;
    }

    if(d.has_update){
      setUpdateStatus(
        `Доступно обновление: ${d.current_version} → ${d.update_version}\nРазмер: ${d.size_text || 'неизвестно'}`,
        'warn'
      );
      showToast('⬇ Доступно обновление');
    }else{
      setUpdateStatus(`Установлена актуальная версия: ${d.current_version}`, 'ok');
      showToast('✅ Обновлений нет');
    }
  }catch(e){
    setUpdateStatus(`Ошибка проверки: ${e.message}`, 'error');
    showToast('⚠ Сервер недоступен');
  }
}

async function installProgramUpdate(){
  const ok = true;

  if(!ok){
    return;
  }

  setUpdateStatus('Скачиваю обновление...', 'warn');
  showToast('⬇ Скачиваю обновление...');

  try{
    const r = await fetch(`${SERVER}/install-update`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({})
    });

    const d = await r.json();

    if(!r.ok || !d.ok){
      setUpdateStatus(d.error || 'Не удалось установить обновление', 'error');
      showToast('⚠ Ошибка обновления');
      return;
    }

    setUpdateStatus(d.message || 'Обновление загружено', 'ok');
    showToast('✅ Обновление загружено');

    if(d.will_restart){
      setUpdateStatus('Установщик загружен. Программа сейчас закроется и начнёт установку...', 'ok');
    }
  }catch(e){
    setUpdateStatus(`Ошибка обновления: ${e.message}`, 'error');
    showToast('⚠ Сервер недоступен');
  }
}

async function loadSavedSettings(){
  try{
    const r = await fetch(`${SERVER}/settings`, {
      method:'GET',
      cache:'no-store'
    });

    if(!r.ok){
      return;
    }

    const s = await r.json();

    if(s.directory !== undefined){
      document.getElementById('directory').value = s.directory;
    }

    if(s.format !== undefined){
      const fmt = document.getElementById('format');
      const exists = [...fmt.options].some(o => o.value === s.format);

      if(exists){
        fmt.value = s.format;
      }
    }

    if(s.segmentDuration !== undefined){
      document.getElementById('segment-duration').value = s.segmentDuration || 12;
      if(document.getElementById('dock-segment-duration')) {
        document.getElementById('dock-segment-duration').value = s.segmentDuration || 12;
      }
    }

    if(s.maxDuration !== undefined){
      document.getElementById('max-duration').value = s.maxDuration || '';
      if(document.getElementById('dock-max-duration')) {
        document.getElementById('dock-max-duration').value = s.maxDuration || '';
      }
    }
    
    if(s.browserCookies !== undefined){
      const bc = document.getElementById('browser-cookies');
      const exists = [...bc.options].some(o => o.value === s.browserCookies);
      if(exists){
        bc.value = s.browserCookies;
      }
    }
    if(s.useRealNames !== undefined){
      const ur = document.getElementById('use-real-names');
      if(ur) [...ur.options].some(o => o.value === s.useRealNames) && (ur.value = s.useRealNames);
    }
  }catch(e){}
}

async function saveCurrentSettings(showMessage=true, closeMenu=false){
  if (closeMenu) {
    const settingsMenu = document.querySelector('.settings');
    if (settingsMenu && settingsMenu.open) {
      settingsMenu.classList.add('is-closing');
      setTimeout(() => {
        settingsMenu.open = false;
        settingsMenu.classList.remove('is-closing');
        document.body.classList.remove('popup-open');
      }, 210);
    }
  }

   const settings = {
    directory:document.getElementById('directory').value || '%USERPROFILE%\\Downloads',
    format:document.getElementById('format').value,
    segmentDuration:document.getElementById('segment-duration').value || '12',
    maxDuration:document.getElementById('max-duration').value || '',
    browserCookies:document.getElementById('browser-cookies').value || 'none',
    useRealNames:document.getElementById('use-real-names') ? document.getElementById('use-real-names').value : 'true'
  };

  try{
    const r = await fetch(`${SERVER}/save-settings`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify(settings)
    });

    if(r.ok){
      if(showMessage){
        showToast('💾 Настройки сохранены');
      }
      return true;
    }
  }catch(e){}

  if(showMessage){
    showToast('⚠ Не удалось сохранить настройки');
  }

  return false;
}

function bindSettingsAutosave(){
  const ids = [
    'directory',
    'format',
    'segment-duration',
    'max-duration',
    'dock-segment-duration', // Добавили нижнее поле
    'dock-max-duration',     // Добавили нижнее поле
    'browser-cookies',
    'use-real-names'
  ];

  // СИНХРОНИЗАЦИЯ ПОЛЕЙ: Если меняем в доке - меняется в настройках, и наоборот
  const mainSeg = document.getElementById('segment-duration');
  const dockSeg = document.getElementById('dock-segment-duration');
  const mainMax = document.getElementById('max-duration');
  const dockMax = document.getElementById('dock-max-duration');

  if(mainSeg && dockSeg) {
    mainSeg.addEventListener('input', () => dockSeg.value = mainSeg.value);
    dockSeg.addEventListener('input', () => mainSeg.value = dockSeg.value);
  }
  if(mainMax && dockMax) {
    mainMax.addEventListener('input', () => dockMax.value = mainMax.value);
    dockMax.addEventListener('input', () => mainMax.value = dockMax.value);
  }

  // АВТОСОХРАНЕНИЕ
  ids.forEach(id => {
    const el = document.getElementById(id);
    if(!el) return;

    el.addEventListener('change', () => saveCurrentSettings(true));

    if(id === 'directory' || id === 'segment-duration' || id === 'max-duration' || id === 'dock-segment-duration' || id === 'dock-max-duration'){
      let timer = null;

      el.addEventListener('input', () => {
        clearTimeout(timer);
        timer = setTimeout(() => {
          saveCurrentSettings(false);
        }, 700);
      });
    }
  });
}

function bindSmoothPopupDetails(){
  const menus = [
    document.getElementById('aboutMenu'),
    document.querySelector('.settings')
  ].filter(Boolean);

  function hasOpenedMenu(){
    return menus.some(menu => menu.open && !menu.classList.contains('is-closing'));
  }

  function updateBodyState(){
    document.body.classList.toggle('popup-open', hasOpenedMenu());
  }

  function closeMenu(menu){
    if(!menu || !menu.open || menu.classList.contains('is-closing')){
      return;
    }

    menu.classList.add('is-closing');

    setTimeout(() => {
      menu.open = false;
      menu.classList.remove('is-closing');
      updateBodyState();
    }, 210);
  }

  function closeAllExcept(exceptMenu=null){
    menus.forEach(menu => {
      if(menu !== exceptMenu){
        closeMenu(menu);
      }
    });
  }

  function openMenu(menu){
    if(!menu){
      return;
    }

    closeAllExcept(menu);

    menu.classList.remove('is-closing');
    menu.open = true;

    updateBodyState();
  }

  function toggleMenu(menu){
    if(!menu){
      return;
    }

    if(menu.open && !menu.classList.contains('is-closing')){
      closeMenu(menu);
    }else{
      openMenu(menu);
    }
  }

  menus.forEach(menu => {
    const summary = menu.querySelector('summary');

    if(summary){
      summary.addEventListener('click', e => {
        e.preventDefault();
        e.stopPropagation();
        toggleMenu(menu);
      });
    }

    menu.addEventListener('click', e => {
      e.stopPropagation();
    });
  });

  document.addEventListener('mousedown', e => {
    const clickedInsideMenu = menus.some(menu => menu.contains(e.target));

    if(!clickedInsideMenu){
      closeAllExcept(null);
    }
  });

    document.addEventListener('keydown', e => {
    if(e.key === 'Escape'){
      closeAllExcept(null);
      closePlaylistModal();
      closeWhatsNewModal();
      // Если открыт вопрос о таймкоде — по Escape выбираем "сегмент" по умолчанию
      const tm = document.getElementById('timeModal');
      if(tm && tm.classList.contains('show')){
        resolveTimeChoice('segment');
      }
    }
  });
}

function openAboutMenu(){
  const about = document.getElementById('aboutMenu');
  const settings = document.querySelector('.settings');

  if(settings){
    settings.open = false;
    settings.classList.remove('is-closing');
  }

  if(about){
    about.classList.remove('is-closing');
    openAboutMenu();
    document.body.classList.add('popup-open');
  }
}

let isRunning = false;
let completedJobs = 0;
let totalJobs = 0;
let sse = null;

let platformTotals = {};
let platformDone = {};
let platformFailed = {};

// --- ДОБАВЛЕНА ПРЯМАЯ ССЫЛКА ---
const PLATFORMS = [
  ['direct', 'Прямая ссылка', 'DL', '#10b981'],
  ['youtube','YouTube','YT','#ff0033'],
  ['rutube','RuTube','RT','#2563eb'],
  ['dzen','Dzen','DZ','#111827'],
  ['vk','VK','VK','#2787f5'],
  ['vkvideo','VK Video','VK','#2787f5'],
  ['facebook','Facebook','FB','#1877f2'],
  ['instagram','Instagram','IG','#e1306c'],
  ['tiktok','TikTok','TT','#000000'],
  ['vimeo','Vimeo','VI','#1ab7ea'],
  ['twitch','Twitch','TW','#9146ff'],
  ['dailymotion','DailyMotion','DM','#0066dc'],
  ['pinterest','Pinterest','PIN','#e60023'],
  ['reddit','Reddit','RD','#ff4500'],
  ['twitter','X / Twitter','X','#111827'],
  ['linkedin','LinkedIn','IN','#0077b5'],
  ['bilibili','Bilibili','BI','#00a1d6'],
  ['weibo','Weibo','WB','#e6162d'],
  ['douyin','DouYin','DY','#111827'],
  ['kuaishou','Kuaishou','KS','#ff7a00'],
  ['xiaohongshu','XiaoHongShu','XH','#ff2442'],
  ['pixabay','Pixabay','PB','#2ec4b6'],
  ['pexels','Pexels','PX','#05a081'],
  ['soundcloud','SoundCloud','SC','#ff5500'],
  ['yandexmusic','Yandex Music','YM','#ffcc00'],
  ['bandcamp','Bandcamp','BC','#629aa9'],
  ['mixcloud','Mixcloud','MC','#5000ff'],
  ['applemusic','Apple Music','AM','#fa243c'],
  ['spotify','Spotify','SP','#1db954']
];

const DETECTORS = {
  // --- ДОБАВЛЕНА ЛОГИКА ОПРЕДЕЛЕНИЯ ПРЯМОЙ ССЫЛКИ ---
  direct: u => {
      const lu = String(u).toLowerCase();
      return lu.includes('/download/') || /\.(mp4|mp3|m4a|webm|wav|ogg|avi|mov|mkv)(?:\?|$)/.test(lu);
  },
  youtube: u => u.includes('youtube.com') || u.includes('youtu.be'),
  rutube:u => u.includes('rutube.ru'),
  dzen:u => u.includes('dzen.ru') || u.includes('zen.yandex'),
  vkvideo:u => u.includes('vkvideo.ru'),
  vk:u => u.includes('vk.com') && !u.includes('vkvideo.ru'),
  facebook:u => u.includes('facebook.com') || u.includes('fb.watch') || u.includes('fb.com'),
  instagram:u => u.includes('instagram.com'),
  tiktok:u => u.includes('tiktok.com') || u.includes('vm.tiktok.com'),
  vimeo:u => u.includes('vimeo.com'),
  twitch:u => u.includes('twitch.tv'),
  dailymotion:u => u.includes('dailymotion.com'),
  pinterest:u => u.includes('pinterest.com') || u.includes('pin.it'),
  reddit:u => u.includes('reddit.com') || u.includes('redd.it'),
  twitter:u => u.includes('twitter.com') || u.includes('x.com') || u.includes('t.co'),
  linkedin:u => u.includes('linkedin.com'),
  bilibili:u => u.includes('bilibili.com') || u.includes('b23.tv'),
  weibo:u => u.includes('weibo.com'),
  douyin:u => u.includes('douyin.com'),
  kuaishou:u => u.includes('kuaishou.com') || u.includes('gifshow.com'),
  xiaohongshu:u => u.includes('xiaohongshu.com') || u.includes('xhslink.com'),
  pixabay:u => u.includes('pixabay.com/videos') || u.includes('pixabay.com/ru/videos'),
  pexels:u => u.includes('pexels.com/video') || u.includes('pexels.com/ru-ru/video'),
  soundcloud:u => u.includes('soundcloud.com'),
  yandexmusic:u => u.includes('music.yandex'),
  bandcamp:u => u.includes('bandcamp.com'),
  mixcloud:u => u.includes('mixcloud.com'),
  applemusic:u => u.includes('music.apple.com'),
  spotify:u => u.includes('spotify.com')
};

function detectPlatform(url){
  const u = String(url || '').toLowerCase();

  for(const [id] of PLATFORMS){
    if(DETECTORS[id] && DETECTORS[id](u)){
      return id;
    }
  }

  return null;
}

function isSupportedLink(url){
  return !!detectPlatform(url);
}

function isYouTubeLink(url){
  return DETECTORS.youtube(String(url || '').toLowerCase());
}

function normalizeLink(url){
  return String(url || '')
    .trim()
    .replace(/[.,;]+$/g,'')
    .replace(/\/+$/,'')
    .toLowerCase();
}

function analyzeLinks(){
  const input = document.getElementById('inputLinks');
  const rawLines = input.value.split('\n');

  const links = [];
  const firstSeen = new Map();
  const seenCount = new Map();
  const duplicates = [];

  rawLines.forEach((raw, idx) => {
    const url = raw.trim();

    if(!url){
      return;
    }

    const norm = normalizeLink(url);
    const platform = detectPlatform(url);

    const prevCount = seenCount.get(norm) || 0;
    const copyIndex = prevCount + 1;

    const item = {
      url,
      norm,
      line:idx + 1,
      platform,
      supported:!!platform,
      duplicate:false,
      firstLine:null,
      copyIndex:copyIndex
    };

    if(firstSeen.has(norm)){
      item.duplicate = true;
      item.firstLine = firstSeen.get(norm).line;
      duplicates.push(item);
    }else{
      firstSeen.set(norm, item);
    }

    seenCount.set(norm, copyIndex);
    links.push(item);
  });

  const uniqueSupported = links.filter(x => x.supported);
  const unsupported = links.filter(x => !x.supported);

  return {
    links,
    uniqueSupported,
    unsupported,
    duplicates
  };
}

function convertYouTubeLink(link){
  const t = String(link || '').trim();
  const parts = t.split('?');

  if(parts.length < 2){
    return t;
  }

  const p = new URLSearchParams(parts[1]);
  const vid = p.get('v') || '';
  const ts = p.get('t') || p.get('start') || '';

  let q = '';

  if(vid){
    q += `v=${vid}`;
  }

  if(ts){
    q += (q ? '&' : '') + `t=${ts}`;
  }

  return q ? `${parts[0]}?${q}` : parts[0];
}

function extractTimeParam(url){
  const m = String(url || '').match(/[?&](?:t|start)=(\d+)/);
  return m ? +m[1] : null;
}

function extractVideoId(url){
  const m = String(url || '').match(/(?:v=|be\/|shorts\/|live\/)([a-zA-Z0-9_-]+)/);
  return m ? m[1] : null;
}

function isLiveVideo(url){
  return String(url || '').includes('/live/');
}

function escapeHtml(s){
  return String(s)
    .replaceAll('&','&amp;')
    .replaceAll('<','&lt;')
    .replaceAll('>','&gt;')
    .replaceAll('"','&quot;')
    .replaceAll("'","&#039;");
}

function buildPlatformCard(id,total){
  const meta = PLATFORMS.find(x => x[0] === id);

  if(!meta){
    return '';
  }

  const [,name,abbr,color] = meta;
  const done = platformDone[id] || 0;
  const failed = platformFailed[id] || 0;
  const processed = done + failed;
  const pct = total > 0 ? Math.min(100, Math.round((processed / total) * 100)) : 0;
  const isDone = total > 0 && done === total;

  return `
    <div class="platform-card active ${isDone ? 'done' : ''}" id="plat-${id}">
      <span class="platform-count" id="cnt-${id}">${total}</span>
      <div class="platform-top">
        <div class="platform-icon" style="--color:${color}">${abbr}</div>
        <div class="platform-info">
          <div class="platform-name">${name}</div>
          <div class="platform-sub" id="psub-${id}">${processed > 0 || isRunning ? `${done}/${total} готово` : `${total} ссыл.`}</div>
        </div>
      </div>
      <div class="platform-progress">
        <div class="platform-progress-fill" id="pfill-${id}" style="width:${pct}%"></div>
      </div>
    </div>
  `;
}

function renderPlatforms(counts){
  const box = document.getElementById('platforms');
  if(!box) return;

  const active = PLATFORMS
    .map(([id]) => id)
    .filter(id => (counts[id] || 0) > 0);

  if(!active.length){
    box.innerHTML = '';
    return;
  }

  box.innerHTML = active
    .map(id => buildPlatformCard(id, counts[id] || 0))
    .join('');
}

function updatePlatformProgress(platform, ok){
  if(!platform){
    return;
  }

  if(ok){
    platformDone[platform] = (platformDone[platform] || 0) + 1;
  }else{
    platformFailed[platform] = (platformFailed[platform] || 0) + 1;
  }

  renderPlatforms(platformTotals);
}

function resetPlatformProgress(){
  platformTotals = {};
  platformDone = {};
  platformFailed = {};
  renderPlatforms(platformTotals);
}

function updateLinksInfo(analysis){
  const info = document.getElementById('linksInfo');
  const input = document.getElementById('inputLinks');
  const dupStat = document.getElementById('dupStatBox');

  if(!info || !input){
    return;
  }

  const uniqueCount = analysis.uniqueSupported.length;
  const dupCount = analysis.duplicates.length;
  const badCount = analysis.unsupported.length;

  document.getElementById('totalCount').textContent = uniqueCount;
  document.getElementById('duplicateCount').textContent = dupCount;
  document.getElementById('retainCount').textContent = badCount;

  input.classList.toggle('has-duplicates', dupCount > 0);

  if(dupStat){
    dupStat.classList.toggle('danger', dupCount > 0);
  }

  if(!analysis.links.length){
    info.classList.remove('show');
    info.innerHTML = '';
    return;
  }

  let html = `
    <div class="ok">Уникальных поддерживаемых ссылок: ${uniqueCount}</div>
    <div class="${badCount ? 'warn' : 'ok'}">Неподдерживаемых строк: ${badCount}</div>
  `;

  if(dupCount > 0){
    html += `<div class="dup-title">Найдены дубли: ${dupCount}</div>`;

    analysis.duplicates.forEach(d => {
      html += `<div class="dup-line">Строка ${d.line} повторяет строку ${d.firstLine}: ${escapeHtml(d.url)}</div>`;
    });
  }else{
    html += `<div class="ok">Дублей не найдено.</div>`;
  }

  info.innerHTML = html;
  info.classList.add('show');
}

function updateCounts(){
  const analysis = analyzeLinks();
  const counts = {};

  for(const item of analysis.uniqueSupported){
    counts[item.platform] = (counts[item.platform] || 0) + 1;
  }

  updateLinksInfo(analysis);

  if(!isRunning){
    platformTotals = counts;
    platformDone = {};
    platformFailed = {};
    renderPlatforms(counts);
  }
}

function buildJobsFromInput(){
  const analysis = analyzeLinks();

  return analysis.uniqueSupported.map(item => {
    const url = item.url;
    const platform = item.platform;
    const copyIndex = item.copyIndex || 1;

    if(platform === 'youtube'){
      const cleanUrl = convertYouTubeLink(url);

      return {
        type:'youtube',
        platform:'youtube',
        url:cleanUrl,
        startTime:extractTimeParam(cleanUrl),
        isLive:isLiveVideo(cleanUrl),
        videoId:extractVideoId(cleanUrl),
        copyIndex:copyIndex,
        duplicate:!!item.duplicate
      };
    }

    if(platform === 'pixabay'){
      return {
        type:'pixabay',
        platform:'pixabay',
        url,
        copyIndex:copyIndex,
        duplicate:!!item.duplicate
      };
    }

    if(platform === 'pexels'){
      return {
        type:'pexels',
        platform:'pexels',
        url,
        copyIndex:copyIndex,
        duplicate:!!item.duplicate
      };
    }

    return {
      type:platform === 'pinterest' ? 'pinterest' : `generic_${platform}`,
      platform,
      url,
      copyIndex:copyIndex,
      duplicate:!!item.duplicate
    };
  });
}

function termLine(text, cls='line-info'){
  const body = document.getElementById('termBody');
  const cur = document.getElementById('cursor');

  if(!body || !cur){
    return;
  }

  const span = document.createElement('span');
  span.className = cls;
  span.textContent = text;

  const br = document.createElement('br');

  body.insertBefore(span, cur);
  body.insertBefore(br, cur);
  body.scrollTop = body.scrollHeight;
}

function termClear(){
  const body = document.getElementById('termBody');

  if(body){
    body.innerHTML = '<span id="cursor" class="cursor"></span>';
  }
}

function setCursor(v){
  const c = document.getElementById('cursor');

  if(c){
    c.classList.toggle('hidden', !v);
  }
}

function setTermStatus(s){
  const el = document.getElementById('termStatus');

  if(!el){
    return;
  }

  el.className = `term-status ${s}`;

  const map = {
    idle:'● ожидание',
    running:'▶ скачивание',
    done:'✓ готово',
    error:'✗ ошибка'
  };

  el.textContent = map[s] || s;
}

function setProgress(pct, loading=false){
  const bar = document.getElementById('progressBar');
  const lbl = document.getElementById('progressLabel');
  const pctEl = document.getElementById('progressPct');
  const ratio = document.getElementById('progressRatio');

  if(!bar || !lbl || !pctEl || !ratio){
    return;
  }

  if(loading){
    bar.classList.add('loading');
    bar.style.width = '';
    lbl.textContent = 'Скачивание...';
    pctEl.textContent = '';
  }else{
    bar.classList.remove('loading');
    bar.style.width = `${pct}%`;
    pctEl.textContent = `${pct}%`;
    lbl.textContent = pct >= 100 ? 'Готово' : (isRunning ? 'В процессе...' : 'Ожидание...');
  }

  ratio.textContent = `${completedJobs} / ${totalJobs}`;
}


function updateRealProgress(data){
  const bar = document.getElementById('progressBar');
  const lbl = document.getElementById('progressLabel');
  const pctEl = document.getElementById('progressPct');
  const ratio = document.getElementById('progressRatio');

  if(!bar || !lbl || !pctEl || !ratio){
    return;
  }

  let percent = Number(data.percent || 0);
  const total = Number(data.total || 0);

  if(percent < 0){
    percent = 0;
  }

  if(percent > 100){
    percent = 100;
  }

  if(total > 0){
    bar.classList.remove('loading');
    bar.style.width = `${percent}%`;
    pctEl.textContent = `${percent.toFixed(1)}%`;
  }else{
    bar.classList.add('loading');
    bar.style.width = '';
    pctEl.textContent = 'размер неизвестен';
  }

  lbl.textContent = data.text || 'Скачивание...';
  ratio.textContent = `${completedJobs} / ${totalJobs}`;
}

async function checkServer(){
  const pill = document.getElementById('serverPill');
  const txt = document.getElementById('serverPillText');

  if(!pill || !txt){
    return false;
  }

  try{
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 1800);

    const r = await fetch(`${SERVER}/status`, {
      method:'GET',
      signal:controller.signal,
      cache:'no-store'
    });

    clearTimeout(timer);

    if(r.ok){
      const d = await r.json();

      pill.className = 'server connected';
      txt.textContent = 'Система готова'; 

      const ytdlpVerEl = document.getElementById('aboutYtdlpVersion');
      if (ytdlpVerEl) {
        ytdlpVerEl.textContent = d.ytdlp_version || 'неизвестно';
      }

      return true;
    }
  }catch(e){}

  pill.className = 'server disconnected';
  txt.textContent = 'Сервер не подключен';

  return false;
}

/* ===== PATCH 5.5.7 JS: Playlist Detector with Bandcamp ===== */
function isPlaylist(url){
  const u = String(url || '').toLowerCase();
  
  const isYT = (u.includes('youtube.com') || u.includes('youtu.be')) && (u.includes('list=') || u.includes('/playlist'));
  const isSoundCloud = u.includes('soundcloud.com') && (u.includes('/sets/') || u.includes('/albums'));
  const isBandcamp = u.includes('bandcamp.com') && u.includes('/album/');
  
  return isYT || isSoundCloud || isBandcamp;
}

let currentPlaylistData = null;
let currentPlaylistUrl = '';
let currentPlaylistIndex = -1;

async function handlePlaylistLink(url, index){
  showToast('⏳ Анализирую структуру альбома/плейлиста...', true); 
  termLine(`⏳ Обнаружен альбом/плейлист: ${url}`, 'line-warn');
  termLine(`  Загружаю названия треков без скачивания файлов...`, 'line-info');

  document.getElementById('btnStart').disabled = true;

  try {
    const res = await fetch(`${SERVER}/parse-playlist`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });

    if(!res.ok){
      const err = await res.json();
      throw new Error(err.error || 'Ошибка загрузки метаданных');
    }

    const data = await res.json();

    if(!data.ok || !data.entries || !data.entries.length){
      throw new Error('В плейлисте не найдено треков');
    }

    currentPlaylistData = data;
    currentPlaylistUrl = url;
    currentPlaylistIndex = index;

    renderPlaylistModal(data);
  } catch (e) {
    termLine(`✗ Не удалось получить структуру плейлиста: ${e.message}`, 'line-error');
    showToast(`⚠ Ошибка плейлиста: ${e.message}`);
    document.getElementById('btnStart').disabled = false;
  }
}

function renderPlaylistModal(data){
  const title = document.getElementById('playlistModalTitle');
  title.textContent = `Плейлист: ${data.title || 'Альбом'} (${data.entries.length} элементов)`;

  const container = document.getElementById('playlistContainer');
  container.innerHTML = '';

  // 1. Вытаскиваем ID и ВРЕМЯ (таймкод) конкретного видео из оригинальной ссылки
  const targetVideoId = extractVideoId(currentPlaylistUrl);
  const targetTime = extractTimeParam(currentPlaylistUrl); // <-- ДОБАВИЛИ ИЗВЛЕЧЕНИЕ ВРЕМЕНИ
  let foundSpecificTarget = false;

  data.entries.forEach((item, idx) => {
    const div = document.createElement('div');
    div.className = 'playlist-item';
    div.onclick = (e) => {
      if(e.target.tagName !== 'INPUT'){
        const cb = div.querySelector('input');
        cb.checked = !cb.checked;
      }
    };

    // 2. Логика расстановки галочек
    let isChecked = true; 
    
    if (targetVideoId) {
        const currentItemId = extractVideoId(item.url);
        if (currentItemId === targetVideoId) {
            isChecked = true; 
            foundSpecificTarget = true;
            div.id = 'target-playlist-item'; 
            
            // 3. ВОССТАНАВЛИВАЕМ ПРИВЯЗКУ КО ВРЕМЕНИ
            if (targetTime !== null) {
                // Если в ссылке уже есть знак вопроса (например, ?v=...), добавляем через &
                if (item.url.includes('?')) {
                    item.url += `&t=${targetTime}`;
                } else {
                    item.url += `?t=${targetTime}`;
                }
            }
        } else {
            isChecked = false; 
        }
    }

    const checkedAttr = isChecked ? 'checked' : '';

    div.innerHTML = `
      <input type="checkbox" value="${idx}" ${checkedAttr}>
      <span class="playlist-item-title" title="${escapeHtml(item.title)}">${idx + 1}. ${escapeHtml(item.title)}</span>
    `;
    container.appendChild(div);
  });

  // Защита: если целевое видео не найдено, выбираем все
  if (targetVideoId && !foundSpecificTarget) {
      toggleAllPlaylist(true);
  }

  document.getElementById('playlistModal').classList.add('show');
  document.getElementById('btnStart').disabled = false;

  setTimeout(() => {
    hideToast();
    
    // Прокрутка к видео
    const targetEl = document.getElementById('target-playlist-item');
    if (targetEl && container) {
        container.scrollTop = targetEl.offsetTop - container.offsetTop - (container.clientHeight / 2) + (targetEl.clientHeight / 2);
    }
  }, 400);
}

function closePlaylistModal(){
  document.getElementById('playlistModal').classList.remove('show');
  currentPlaylistData = null;
  currentPlaylistUrl = '';
  currentPlaylistIndex = -1;
}

function toggleAllPlaylist(val){
  const checkboxes = document.querySelectorAll('#playlistContainer input[type="checkbox"]');
  checkboxes.forEach(cb => cb.checked = val);
}

function confirmPlaylistDownload(){
  const checkboxes = document.querySelectorAll('#playlistContainer input[type="checkbox"]');
  const selectedIndices = [];

  checkboxes.forEach(cb => {
    if(cb.checked){
      selectedIndices.push(parseInt(cb.value));
    }
  });

  if(!selectedIndices.length){
    showToast('⚠ Выберите хотя бы один элемент!');
    return;
  }

  const selectedUrls = selectedIndices.map(idx => currentPlaylistData.entries[idx].url);

  const textarea = document.getElementById('inputLinks');
  const lines = textarea.value.split('\n');

  lines.splice(currentPlaylistIndex, 1, ...selectedUrls);
  textarea.value = lines.join('\n');

  closePlaylistModal();
  updateCounts();

  showToast(`✓ Развернуто треков: ${selectedUrls.length}`);
  termLine(`✓ Альбом разбит на ${selectedUrls.length} выбранных элементов. Запускаю скачивание...`, 'line-ok');

  startDownload();
}

async function startDownload(){

 // === ДОБАВЬТЕ ЭТОТ БЛОК (Очистка журнала от старых сообщений) ===
  const logContainer = document.getElementById('log') || document.getElementById('logContent') || document.getElementById('logContainer');
  if (logContainer) {
      logContainer.innerHTML = '';
  }
  // =================================================================

  const urlsText = document.getElementById('inputLinks').value;
  const urls = urlsText.split('\n').map(u => u.trim()).filter(u => u);

  if(isRunning){
    return;
  }
 if(window.switchToPlatforms) window.switchToPlatforms(); // <--- ДОБАВЛЕНО (Принудительно показать платформы при старте)
  updateCounts();

  const ok = await checkServer();

  if(!ok){
    showToast('⚠ Сервер недоступен');
    termLine('✗ Сервер недоступен', 'line-error');
    return;
  }

  const textarea = document.getElementById('inputLinks');
  const lines = textarea.value.split('\n').map(x => x.trim()).filter(Boolean);
  let playlistUrl = null;
  let playlistIndex = -1;

  for(let i = 0; i < lines.length; i++){
    if(isPlaylist(lines[i])){
      playlistUrl = lines[i];
      playlistIndex = i;
      break;
    }
  }

  if(playlistUrl){
    handlePlaylistLink(playlistUrl, playlistIndex);
    return;
  }

  const jobs = buildJobsFromInput();

  if(!jobs.length){
    showToast('⚠ Нет поддерживаемых уникальных ссылок');
    return;
  }
  
    // === ПРОВЕРКА ВИДЕО С ТАЙМКОДОМ (?t=) ===
  const jobsWithTime = jobs.filter(j => j.type === 'youtube' && j.startTime !== null && j.startTime !== undefined && !j.isLive);

  if(jobsWithTime.length > 0){
    const decision = await showTimeChoiceModal(jobsWithTime, jobsWithTime.length);

    if(decision.choice === 'full'){
      if(decision.applyAll){
        // Все видео с таймкодом — качаем целиком
        jobsWithTime.forEach(j => { j.startTime = null; });
        termLine(`🎬 Видео с таймкодом (${jobsWithTime.length}) будут скачаны целиком`, 'line-info');
      } else {
        // Только первое — целиком, остальные оставляем как сегменты
        jobsWithTime[0].startTime = null;
        termLine(`🎬 Первое видео с таймкодом будет скачано целиком`, 'line-info');
      }
    } else {
      // Сегмент
      if(decision.applyAll){
        termLine(`✂ Все видео с таймкодом (${jobsWithTime.length}) — только сегменты`, 'line-info');
      } else {
        // Остальные — целиком, только первое сегментом
        jobsWithTime.slice(1).forEach(j => { j.startTime = null; });
        termLine(`✂ Первое видео — сегмент, остальные целиком`, 'line-info');
      }
    }
  }
  // ========================================
  
      // === ГЕНЕРИРУЕМ ВИЗУАЛЬНЫЙ СПИСОК С УМНЫМ ВОЗОБНОВЛЕНИЕМ ===
  // Собираем список ссылок, которые реально были успешно скачаны в прошлый раз
  const alreadyDoneUrls = new Set();
  document.querySelectorAll('#detailedLinksList .job-item.success').forEach(item => {
      const urlSpan = item.querySelector('.job-url');
      if (urlSpan) {
          alreadyDoneUrls.add(urlSpan.textContent.trim());
      }
  });

      const listHtml = jobs.map((job, idx) => {
      let statusIcon = '⏳';
      let itemClass = '';

      if (alreadyDoneUrls.has(String(job.url).trim())) {
          statusIcon = '✅';
          itemClass = 'success';
          job.skip = true;
      }

            // Сохраняем путь к файлу, если он уже известен
      const savedPath = window.downloadedFilesMap && window.downloadedFilesMap[idx] ? window.downloadedFilesMap[idx] : '';
      
      // ВАЖНО: удваиваем слэши для Windows, чтобы они не исчезли в HTML
      const safeSavedPath = savedPath.replace(/\\/g, '\\\\').replace(/'/g, "\\'");

      return `
          <div class="job-item ${itemClass}" id="job-item-${idx}">
              <span class="job-status" id="job-icon-${idx}">${statusIcon}</span>
              <span class="job-url" id="job-url-${idx}">${escapeHtml(job.url)}</span>
              
              <!-- Кнопки-иконки в стиле приложения с подсказками -->
              <div style="display:flex; gap:6px; margin-left:auto; align-items:center;">
                  <button class="btn btn-slim btn-icon-only" title="Открыть ссылку в браузере" onclick="openLinkInBrowser('${escapeHtml(job.url)}')">🌐</button>
                  <button class="btn btn-slim btn-icon-only" title="Копировать ссылку" onclick="copyLinkText('${escapeHtml(job.url)}')">📋</button>
                  <button class="btn btn-slim btn-icon-only" title="Открыть папку и выделить файл" onclick="openFileFolder(${idx}, '${safeSavedPath}')">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--cyan);">
                      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                    </svg>
                  </button>
              </div>
          </div>
      `;
  }).join('');
  document.getElementById('detailedLinksList').innerHTML = listHtml;
  // ===========================================================

  const analysis = analyzeLinks();

  if(analysis.duplicates.length){
    showToast(`⚠ Найдены похожие/повторные ссылки: ${analysis.duplicates.length}. Они будут скачаны как копии (2), (3)...`);
  }

  const settings = {
    segmentDuration:+document.getElementById('segment-duration').value || 12,
    format:document.getElementById('format').value,
    directory:document.getElementById('directory').value || '%USERPROFILE%\\Downloads',
    maxDuration:+document.getElementById('max-duration').value || 0
  };

  await saveCurrentSettings(false);

  resetPlatformProgress();

  for(const job of jobs){
    const p = job.platform || 'generic';
    platformTotals[p] = (platformTotals[p] || 0) + 1;
  }

  renderPlatforms(platformTotals);

    isRunning = true;
  completedJobs = 0;
  totalJobs = jobs.length;

  // Прячем кнопку "Скачать", показываем "Стоп"
  document.getElementById('btnStart').style.display = 'none';
  document.getElementById('btnStop').style.display = 'inline-flex';
  document.getElementById('btnStop').disabled = false;
  document.getElementById('btnStop').textContent = '🛑 Стоп';

  document.getElementById('doneCount').textContent = '0';

  termClear();
  setCursor(true);
  setTermStatus('running');
  setProgress(0, true);

  termLine(`▶ Отправляю задач: ${jobs.length}`, 'line-info');

  if(analysis.duplicates.length){
    termLine(`⚠ Найдены похожие/повторные ссылки: ${analysis.duplicates.length}. Не пропускаю — сохраню как (2), (3)...`, 'line-warn');
  }

  try{
    const res = await fetch(`${SERVER}/download`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({jobs, settings})
    });

    if(!res.ok){
      let errText = 'Ошибка запуска';

      try{
        const e = await res.json();
        errText = e.error || errText;
      }catch(e){}

      termLine(`✗ ${errText}`, 'line-error');
      setTermStatus('error');
      finishUI();
      return;
    }

    listenSSE();
  }catch(e){
    termLine(`✗ ${e.message}`, 'line-error');
    setTermStatus('error');
    finishUI();
  }
}

function listenSSE(){
  if(sse){
    sse.close();
  }

  sse = new EventSource(`${SERVER}/stream`);

  sse.onmessage = e => {
    try{
      const data = JSON.parse(e.data);
      const type = data.type;
      const text = data.text;

      const cls = {
        info:'line-info',
        ok:'line-ok',
        error:'line-error',
        warn:'line-warn',
        cmd:'line-cmd',
        url:'line-url',
        sep:'line-sep',
        done:'line-done'
      }[type] || 'line-info';

            if(type === 'progress'){
        updateRealProgress(data);
        return;
      }

      // === ВОПРОС О КОНВЕРТАЦИИ В H264 ===
      if(type === 'ask_convert'){
        showConvertDialog(data);
        return;
      }
      if(type === 'convert_done'){
        showToast('✅ Перекодировка в H264 завершена!');
        setTermStatus('done');
        return;
      }

           if(type === 'job_done'){
        completedJobs++;
        document.getElementById('doneCount').textContent = completedJobs;

        updatePlatformProgress(data.platform, !!data.ok);
        setProgress(Math.round((completedJobs / totalJobs) * 100), false);
        
        let jIdx = data.job_index;
        let el = document.getElementById(`job-item-${jIdx}`);
        let iconEl = document.getElementById(`job-icon-${jIdx}`);
        
        if(el && iconEl) {
            if(data.ok) {
                iconEl.textContent = '✅';
                el.classList.add('success');
                
                // === ЗАМЕНЯЕМ ССЫЛКУ НА ИМЯ И ОБНОВЛЯЕМ ПУТЬ ДЛЯ КНОПКИ ===
                if (data.file_name && data.file_path) {
                    // Заменяем текст со ссылкой на красивое имя файла
                    let urlSpan = el.querySelector('.job-url');
                    if (urlSpan) {
                        urlSpan.textContent = data.file_name;
                        urlSpan.title = data.file_path; // Показываем путь при наведении мыши
                    }
                    
                    // Сохраняем в глобальный список (для открытия папки)
                    window.downloadedFilesMap[jIdx] = data.file_path;
                    
                    // Обновляем кнопку "Открыть папку" точным путем
                    let folderBtn = el.querySelector('button[title="Открыть папку и выделить файл"]');
                    if (folderBtn) {
                        // Экранируем слеши для JS
                        let safePath = data.file_path.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
                        folderBtn.setAttribute('onclick', `openFileFolder(${jIdx}, '${safePath}')`);
                    }
                }
                // =========================================================

            } else {
                iconEl.textContent = '❌';
                el.classList.add('error');
            }
        }
        return;
      }

      if(type === 'done'){
        sse.close();

        if(text === 'finished'){
          setTermStatus('done');
          setProgress(100, false);
          showToast('✅ Все загрузки завершены');
          playDoneSound();
        }else{
          setTermStatus('error');
          setProgress(0, false);
        }

        finishUI();
        return;
      }

      termLine(text, cls);
    }catch(err){}
  };

  sse.onerror = () => {
    if(isRunning){
      termLine('✗ Соединение с журналом прервано', 'line-error');
      setTermStatus('error');
      finishUI();
    }

    if(sse){
      sse.close();
    }
  };
}

function finishUI(){
  isRunning = false;
  setCursor(false);

  const btn = document.getElementById('btnStart');
  const btnStop = document.getElementById('btnStop');

  if(btn){
    btn.style.display = 'inline-flex';
    btn.disabled = false;
  }
  if(btnStop){
    btnStop.style.display = 'none';
  }

  const bar = document.getElementById('progressBar');
  if(bar) bar.classList.remove('loading');
}

function clearLinks(){
if(window.switchToText) window.switchToText();

  // Очищаем список скачанных, чтобы галочки не мешали новым загрузкам
  const detailedList = document.getElementById('detailedLinksList');
  if(detailedList){
    detailedList.innerHTML = '';
  }

  const input = document.getElementById('inputLinks');

  if(input){
    input.value = '';
    input.classList.remove('has-duplicates');
  }

  completedJobs = 0;
  totalJobs = 0;

  document.getElementById('doneCount').textContent = '0';
  document.getElementById('duplicateCount').textContent = '0';

  const info = document.getElementById('linksInfo');

  if(info){
    info.classList.remove('show');
    info.innerHTML = '';
  }

  resetPlatformProgress();
  setProgress(0, false);
  updateCounts();
  showToast('Очищено');
}


async function readClipboardTextSafe(){
  try{
    const r = await fetch(`${SERVER}/clipboard-read`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({})
    });

    if(r.ok){
      const data = await r.json();

      if(data.ok){
        return String(data.text || '');
      }
    }
  }catch(e){}

  return '';
}

function extractLinksFromText(text){
  const re = /https?:\/\/[^\s"'<>]+/gi;
  const links = [];
  let m;

  while((m = re.exec(String(text || ''))) !== null){
    links.push(m[0]);
  }

  return links;
}

function insertTextAtCursor(el, text){
  if(!el){
    return;
  }

  const start = el.selectionStart || 0;
  const end = el.selectionEnd || 0;
  const before = el.value.slice(0, start);
  const after = el.value.slice(end);

  el.value = before + text + after;
  el.selectionStart = el.selectionEnd = start + text.length;
  el.focus();
  updateCounts();
}

async function pasteFromClipboard(){
  const text = await readClipboardTextSafe();

  if(!text){
    showToast('⚠ Буфер обмена пуст или недоступен');
    return;
  }

  const links = extractLinksFromText(text);

  if(links.length){
    document.getElementById('inputLinks').value = links.join('\n');
    updateCounts();
    showToast(`✓ Найдено ссылок: ${links.length}`);
    setTimeout(window.switchToPlatforms, 100); // <--- ДОБАВЛЕНО
    return;
  }

  const input = document.getElementById('inputLinks');
  insertTextAtCursor(input, text);
  showToast('✓ Текст вставлен');
  setTimeout(window.switchToPlatforms, 100); // <--- ДОБАВЛЕНО
}


async function browseFolder(){
  const currentDir = document.getElementById('directory').value || '%USERPROFILE%\\Downloads';

  try{
    const r = await fetch(`${SERVER}/browse-folder`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({directory:currentDir})
    });

    if(!r.ok){
      showToast('⚠ Не удалось открыть обзор папок');
      return;
    }

    const data = await r.json();

    if(data.ok && data.directory){
      document.getElementById('directory').value = data.directory;
      await saveCurrentSettings(false);
      showToast('Папка выбрана');
    }else{
      showToast('Выбор папки отменён');
    }
  }catch(e){
    showToast('⚠ Сервер недоступен');
  }
}


async function openFolder(){
  const dir = document.getElementById('directory').value || '%USERPROFILE%\\Downloads';

  await saveCurrentSettings(false);

  try{
    await fetch(`${SERVER}/open-folder`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({directory:dir})
    });
  }catch(e){
    showToast('⚠ Сервер недоступен');
  }
}

function hideToast(){
  const t = document.getElementById('toast');
  if(t){
    t.classList.remove('show');
  }
}

let toastTimeout = null;

function showToast(msg, keepOpen = false){
  const t = document.getElementById('toast');
  if(!t) return;

  clearTimeout(toastTimeout);
  
  t.textContent = msg;
  t.classList.add('show');

  if (!keepOpen) {
    toastTimeout = setTimeout(() => {
      t.classList.remove('show');
    }, 3200);
  }
}


async function openDonate(){
  try{
    await fetch(`${SERVER}/open-url`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        url:'https://paypal.me/studioyouar'
      })
    });
  }catch(e){
    window.open('https://paypal.me/studioyouar', '_blank');
  }
}

async function openBoosty(){
  try{
    await fetch(`${SERVER}/open-url`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        url:'https://boosty.to/time_vegas_pro/donate'
      })
    });
  }catch(e){
    window.open('https://boosty.to/time_vegas_pro/donate', '_blank');
  }
}

function playDoneSound(){
  try{
    const ctx = new (window.AudioContext || window.webkitAudioContext)();

    [523,659,784,1047].forEach((freq,i) => {
      const o = ctx.createOscillator();
      const g = ctx.createGain();

      o.connect(g);
      g.connect(ctx.destination);

      o.frequency.value = freq;
      o.type = 'sine';

      const t = ctx.currentTime + i * .12;

      g.gain.setValueAtTime(0, t);
      g.gain.linearRampToValueAtTime(.16, t + .02);
      g.gain.exponentialRampToValueAtTime(.001, t + .25);

      o.start(t);
      o.stop(t + .26);
    });
  }catch(e){}
}


function createRightClickMenu(){
  let menu = document.getElementById('rightClickMenu');

  if(menu){
    return menu;
  }

  menu = document.createElement('div');
  menu.id = 'rightClickMenu';

  menu.innerHTML = `
    <button class="rc-btn" id="rcPasteLinks"><span class="rc-icon">📋</span> Вставить ссылки</button>
    <button class="rc-btn" id="rcPasteText"><span class="rc-icon">📝</span> Вставить текст</button>
    <div class="rc-sep"></div>
    <button class="rc-btn" id="rcCopy"><span class="rc-icon">📄</span> Копировать</button>
    <button class="rc-btn" id="rcCut"><span class="rc-icon">✂</span> Вырезать</button>
    <div class="rc-sep"></div>
    <button class="rc-btn" id="rcSelectAll"><span class="rc-icon">🔲</span> Выделить всё</button>
    <button class="rc-btn danger" id="rcClear"><span class="rc-icon">🧹</span> Очистить поле</button>
  `;

  document.body.appendChild(menu);
  return menu;
}

function hideRightClickMenu(){
  const menu = document.getElementById('rightClickMenu');

  if(menu){
    menu.style.display = 'none';
  }
}

function bindTextareaContextMenu(){
  const input = document.getElementById('inputLinks');

  if(!input){
    return;
  }

  const menu = createRightClickMenu();

  input.addEventListener('contextmenu', e => {
    e.preventDefault();

    menu.style.left = `${Math.min(e.clientX, window.innerWidth - 230)}px`;
    menu.style.top = `${Math.min(e.clientY, window.innerHeight - 250)}px`;
    menu.style.display = 'block';
  });

  document.addEventListener('click', e => {
    if(!menu.contains(e.target)){
      hideRightClickMenu();
    }
  });

  document.addEventListener('keydown', e => {
    if(e.key === 'Escape'){
      hideRightClickMenu();
    }
  });

  document.getElementById('rcPasteLinks').onclick = async () => {
    hideRightClickMenu();

    const text = await readClipboardTextSafe();
    const links = extractLinksFromText(text);

    if(!links.length){
      showToast('⚠ В буфере не найдено ссылок');
      return;
    }

    input.value = links.join('\n');
    updateCounts();
    showToast(`✓ Вставлено ссылок: ${links.length}`);
  };

  document.getElementById('rcPasteText').onclick = async () => {
    hideRightClickMenu();

    const text = await readClipboardTextSafe();

    if(!text){
      showToast('⚠ Буфер обмена пуст');
      return;
    }

    insertTextAtCursor(input, text);
    showToast('✓ Текст вставлен');
  };

  document.getElementById('rcCopy').onclick = async () => {
    hideRightClickMenu();

    const selected = input.value.substring(input.selectionStart, input.selectionEnd) || input.value;

    try{
      await navigator.clipboard.writeText(selected);
      showToast('✓ Скопировано');
    }catch(e){
      showToast('⚠ Не удалось скопировать');
    }
  };

  document.getElementById('rcCut').onclick = async () => {
    hideRightClickMenu();

    const start = input.selectionStart || 0;
    const end = input.selectionEnd || 0;
    const selected = input.value.substring(start, end);

    if(!selected){
      showToast('⚠ Ничего не выделено');
      return;
    }

    try{
      await navigator.clipboard.writeText(selected);
    }catch(e){}

    input.value = input.value.slice(0, start) + input.value.slice(end);
    input.selectionStart = input.selectionEnd = start;
    updateCounts();
    showToast('✓ Вырезано');
  };

  // --- НОВЫЕ КНОПКИ ЗДЕСЬ (ВНУТРИ ФУНКЦИИ) ---

  // Выделить всё
  document.getElementById('rcSelectAll').onclick = () => {
    hideRightClickMenu();
    input.select();
  };

  // Очистить поле
  document.getElementById('rcClear').onclick = () => {
    hideRightClickMenu();
    clearLinks();
  };
}

// === МЕНЮ ДЛЯ СПИСКА ССЫЛОК ПРИ СКАЧИВАНИИ ===
let rightClickedUrl = '';

function createListContextMenu() {
  let menu = document.getElementById('listRightClickMenu');
  if (menu) return menu;

  menu = document.createElement('div');
  menu.id = 'listRightClickMenu';
  menu.innerHTML = `
    <button class="rc-btn" id="rcListCopy"><span class="rc-icon">📄</span> Копировать</button>
    <button class="rc-btn" id="rcListOpen"><span class="rc-icon">🌐</span> Открыть в браузере</button>
  `;
  document.body.appendChild(menu);
  return menu;
}

function bindListContextMenu() {
  const list = document.getElementById('detailedLinksList');
  if (!list) return;

  const menu = createListContextMenu();

  list.addEventListener('contextmenu', e => {
    // Ищем, кликнули ли мы по строке с ссылкой
    const item = e.target.closest('.job-item');
    if (!item) return;

    e.preventDefault();

    // Запоминаем ссылку из этой строки
    const urlSpan = item.querySelector('.job-url');
    if (urlSpan) {
      rightClickedUrl = urlSpan.textContent;
    }

    menu.style.left = `${Math.min(e.clientX, window.innerWidth - 230)}px`;
    menu.style.top = `${Math.min(e.clientY, window.innerHeight - 100)}px`;
    menu.style.display = 'block';
  });

  document.addEventListener('click', e => {
    if (!menu.contains(e.target)) {
      menu.style.display = 'none';
    }
  });
  
  document.addEventListener('keydown', e => {
    if(e.key === 'Escape') menu.style.display = 'none';
  });

  // Кнопка Копировать
  document.getElementById('rcListCopy').onclick = async () => {
    menu.style.display = 'none';
    
    // Если пользователь выделил кусок текста (как у вас на скрине) - берем его. Если нет - берем всю ссылку.
    const selectedText = window.getSelection().toString().trim();
    const textToCopy = selectedText ? selectedText : rightClickedUrl;

    if (textToCopy) {
      try {
        await navigator.clipboard.writeText(textToCopy);
        showToast('✓ Скопировано');
      } catch(err) {
        showToast('⚠ Ошибка копирования');
      }
    }
  };

  // Кнопка Открыть в браузере
  document.getElementById('rcListOpen').onclick = async () => {
    menu.style.display = 'none';
    if (rightClickedUrl) {
      try {
        await fetch(`${SERVER}/open-url`, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ url: rightClickedUrl })
        });
      } catch(err) {
        window.open(rightClickedUrl, '_blank');
      }
    }
  };
}


async function autoCheckUpdateOnStart(){
  try{
    const r = await fetch(`${SERVER}/check-update`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({})
    });

    const d = await r.json();

    if(!r.ok || !d.ok){
      return;
    }

    if(d.has_update){
      showToast(`⬇ Доступна новая версия ${d.update_version}`);

      const about = document.getElementById('aboutMenu');

      if(about){
        openAboutMenu();
      }

      setUpdateStatus(
        `Доступна новая версия: ${d.current_version} → ${d.update_version}\n` +
        `Файл: ${d.asset_name || 'Baikal Downloader.exe'}\n` +
        `Размер: ${d.size_text || 'неизвестно'}`,
        'warn'
      );

      setTimeout(() => {
        const ok = true;

        if(ok){
          const about2 = document.getElementById('aboutMenu');

          if(about2){
            openAboutMenu();
          }
        }
      }, 600);
    }else{
      setUpdateStatus(`Установлена актуальная версия: ${d.current_version}`, 'ok');
    }
  }catch(e){}
}


document.addEventListener('DOMContentLoaded', async () => {
  await loadAppInfo();

  setTimeout(() => {
    autoCheckUpdateOnStart();
  }, 1200);

  await loadSavedSettings();
  bindSettingsAutosave();
  bindTextareaContextMenu();
  bindListContextMenu();
  bindSmoothPopupDetails();

  resetPlatformProgress();
  updateCounts();

  checkServer();
  setInterval(checkServer, 5000);

    // === УМНОЕ ПЕРЕКЛЮЧЕНИЕ: ТЕКСТ <-> ПЛАТФОРМЫ ===
  const input = document.getElementById('inputLinks');
  const platformsBox = document.getElementById('platformsBox');
  const workspaceNote = document.getElementById('workspaceNote');

    window.switchToPlatforms = function() {
      const linksText = input.value.trim();
      if (linksText && !isRunning) {
          input.style.display = 'none';
          platformsBox.style.display = 'flex';
          document.getElementById('detailedLinksList').style.display = 'flex'; // Показываем список
          platformsBox.style.borderColor = 'rgba(125,211,252,.1)';
          workspaceNote.innerHTML = 'Кликни по карточкам, чтобы изменить ссылки';
      }
  };

  window.switchToText = function() {
      if (!isRunning) {
          platformsBox.style.display = 'none';
          document.getElementById('detailedLinksList').style.display = 'none'; // Прячем список
          input.style.display = 'block';
          input.focus();
          workspaceNote.innerHTML = 'Вставь ссылки, и они превратятся в карточки';
      }
  };

  if(input){
    input.addEventListener('input', updateCounts);
    
    // Когда убираем мышку из текстового поля - превращаем в платформы
    input.addEventListener('blur', () => {
        setTimeout(window.switchToPlatforms, 150);
    });
  }

  if (platformsBox) {
      // Когда кликаем по платформам - возвращаем текст
      platformsBox.addEventListener('click', window.switchToText);
      platformsBox.addEventListener('mouseenter', () => { if(!isRunning) platformsBox.style.borderColor = 'rgba(34,211,238,.4)'; });
      platformsBox.addEventListener('mouseleave', () => { platformsBox.style.borderColor = 'rgba(125,211,252,.1)'; });
  }
  // ===============================================

  document.body.addEventListener('dragover', e => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  });

  document.body.addEventListener('drop', async e => {
    e.preventDefault();

    const file = [...e.dataTransfer.files].find(f => f.name.toLowerCase().endsWith('.docx'));

    if(!file){
      return;
    }

    if(!window.JSZip){
      showToast('⚠ Модуль чтения DOCX ещё не загрузился');
      return;
    }

    try{
      const zip = await JSZip.loadAsync(await file.arrayBuffer());
      const links = [];

      const relsFile = zip.file('word/_rels/document.xml.rels');
      const docFile = zip.file('word/document.xml');

      const relsText = relsFile ? await relsFile.async('text') : '';
      const docText = docFile ? await docFile.async('text') : '';

      if(relsText){
        const relsDoc = new DOMParser().parseFromString(relsText, 'application/xml');
        const id2url = new Map();

        relsDoc.querySelectorAll('Relationship').forEach(n => {
          const tgt = n.getAttribute('Target');

          if(tgt && /^https?:\/\//i.test(tgt)){
            id2url.set(n.getAttribute('Id'), tgt);
          }
        });

        if(docText){
          const doc = new DOMParser().parseFromString(docText, 'application/xml');

          doc.querySelectorAll('hyperlink').forEach(h => {
            const rid = h.getAttribute('r:id');

            if(rid && id2url.has(rid)){
              links.push(id2url.get(rid));
            }
          });
        }
      }

      if(docText){
        const rawLinks = docText.match(/https?:\/\/[^<>\s"]+/gi) || [];
        links.push(...rawLinks);
      }

      document.getElementById('inputLinks').value = links.join('\n');

      updateCounts();
      showToast(`✓ Загружено ссылок из DOCX: ${links.length}`);
    }catch(err){
      showToast('⚠ Не удалось прочитать DOCX');
    }
  });
});

async function cancelDownload() {
    if (!isRunning) return;
    
    let btnStop = document.getElementById('btnStop');
    btnStop.disabled = true;
    btnStop.textContent = "⏳ Отмена...";
    
    try {
        await fetch(`${SERVER}/cancel`, { method: 'POST' });
        showToast("🛑 Подана команда на отмену", "error");
    } catch (e) {
        showToast("⚠ Ошибка связи с сервером", "error");
    }
}

// === ЛОГИКА ВЫБОРА: СЕГМЕНТ ИЛИ ВСЁ ВИДЕО (ТАЙМКОД) ===
let timeChoiceResolver = null;

function showTimeChoiceModal(jobsWithTime, totalTimeJobs){
  return new Promise((resolve) => {
    timeChoiceResolver = resolve;

    const seg = +document.getElementById('segment-duration').value || 12;
    const info = document.getElementById('timeModalInfo');
    const list = document.getElementById('timeModalList');
    const applyAllWrap = document.getElementById('timeApplyAllWrap');
    const applyAllCb = document.getElementById('timeApplyAll');

    // Обновляем текст кнопки "Только сегмент" актуальным значением секунд
    const segBtn = document.querySelector('#timeModal .btn-blue');
    if(segBtn){
      segBtn.textContent = `✂ Только сегмент (${seg} сек)`;
    }

    if(info){
      info.innerHTML = `Обнаружено видео с привязкой ко времени (таймкод <b>?t=</b>): <b>${totalTimeJobs}</b>.<br>` +
                       `Что сделать?<br>` +
                       `<span style="color:var(--muted); font-size:11px;">• «Только сегмент» — скачает ${seg} секунд начиная с таймкода.<br>` +
                       `• «Скачать целиком» — скачает всё видео полностью.</span>`;
    }

    // Показываем первое видео (или несколько) для наглядности
    if(list){
      list.innerHTML = jobsWithTime.slice(0, 5).map(j => {
        const mm = Math.floor(j.startTime / 60);
        const ss = j.startTime % 60;
        const timeStr = `${String(mm).padStart(2,'0')}:${String(ss).padStart(2,'0')}`;
        return `<div style="font-family:var(--mono); font-size:11px; color:var(--muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">⏱ ${timeStr} — ${escapeHtml(j.url)}</div>`;
      }).join('') + (jobsWithTime.length > 5 ? `<div style="font-size:11px; color:var(--muted);">...и ещё ${jobsWithTime.length - 5}</div>` : '');
    }

    // Показываем "Применить ко всем" только если таких видео больше одного
    if(applyAllWrap){
      applyAllWrap.style.display = totalTimeJobs > 1 ? 'flex' : 'none';
      if(applyAllCb) applyAllCb.checked = totalTimeJobs > 1; // по умолчанию отмечено
    }

    document.getElementById('timeModal').classList.add('show');
  });
}

function resolveTimeChoice(choice){
  const applyAllCb = document.getElementById('timeApplyAll');
  const applyAll = applyAllCb ? applyAllCb.checked : true;

  document.getElementById('timeModal').classList.remove('show');

  if(timeChoiceResolver){
    timeChoiceResolver({ choice, applyAll });
    timeChoiceResolver = null;
  }
}



function showConvertDialog(data){
  const count = data.count || 0;
  const filesList = (data.files || [])
    .map(f => `• ${f.name} (кодек: ${f.codec.toUpperCase()})`)
    .join('\n');

  const modal = document.getElementById('convertModal');
  const info = document.getElementById('convertInfo');
  if(info){
    info.innerHTML = `Обнаружено файлов с кодеком, отличным от H.264: <b>${count}</b>.<br>` +
                     `Монтажные программы лучше работают с H.264 (AVC).<br><br>` +
                     `<div style="font-family:var(--mono); font-size:11px; color:var(--muted); white-space:pre-wrap; max-height:150px; overflow:auto;">${escapeHtml(filesList)}</div><br>` +
                     `Хотите перекодировать их в H.264 прямо сейчас?`;
  }
  if(modal){
    modal.classList.add('show');
  }
}

async function confirmConvertH264(){
  document.getElementById('convertModal').classList.remove('show');
  showToast('🔄 Запускаю перекодировку в H264...', true);
  setTermStatus('running');
  try{
    await fetch(`${SERVER}/convert-h264`, { method: 'POST' });
  }catch(e){
    showToast('⚠ Ошибка запуска конвертации');
  }
}

function cancelConvertH264(){
  document.getElementById('convertModal').classList.remove('show');
  showToast('Конвертация отменена. Файлы оставлены как есть.');
}

async function openYoutubeAuth() {
        let btn = document.getElementById("btn-auth");
        let hint = document.getElementById("auth-hint");
        let originalText = btn.innerHTML;
        btn.innerHTML = "⏳ Ожидание авторизации... (Войдите в аккаунт и закройте окно)";
        btn.disabled = true;

        try {
            let response = await fetch(`${SERVER}/api/open_auth`, { method: 'POST' });
            let data = await response.json();

            if (response.ok) {
                if (data.saved) {
                    btn.innerHTML = "✅ Авторизация сохранена (Изменить аккаунт)";
                    btn.style.background = "linear-gradient(135deg, #3b82f6, #2563eb)";
                    if (hint) hint.innerHTML = "<span style='color:#34d399; font-weight:bold;'>Профиль найден!</span> Программа готова к скачиванию 18+ видео.";
                    showToast("✅ Авторизация успешно сохранена!");
                } else {
                    btn.innerHTML = originalText;
                    showToast("⚠ Вход не выполнен (окно закрыто слишком быстро)", "error");
                }
            } else {
                btn.innerHTML = originalText;
                showToast("⚠ Ошибка запуска окна авторизации", "error");
            }
        } catch (error) {
            btn.innerHTML = originalText;
            showToast("⚠ Ошибка сети", "error");
        }

        btn.disabled = false;
    }
    
   // Глобальный реестр путей скачанных файлов
window.downloadedFilesMap = window.downloadedFilesMap || {};

// Открыть папку и выделить файл (Единая правильная функция)
async function openFileFolder(idx, filePath) {
    const defaultDir = document.getElementById('directory').value || '';
    
    // Берем путь из аргумента, либо из памяти, либо просто папку загрузок
    let targetPath = filePath;
    if (!targetPath || targetPath === 'undefined') {
        targetPath = window.downloadedFilesMap[idx] || defaultDir;
    }

    try {
        const res = await fetch(`${SERVER}/open-file-in-folder`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ path: targetPath, directory: defaultDir })
        });
        const data = await res.json();
        if(!data.ok) {
            showToast('⚠ Папка или файл не найдены');
        }
    } catch(e) {
        showToast('⚠ Ошибка связи с сервером');
    }
} 

// Открыть ссылку в браузере
async function openLinkInBrowser(url) {
    try {
        await fetch(`${SERVER}/open-url`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ url })
        });
    } catch(e) {
        window.open(url, '_blank');
    }
}

// Скопировать ссылку в буфер
async function copyLinkText(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('✓ Ссылка скопирована в буфер');
    } catch(e) {
        showToast('⚠ Не удалось скопировать');
    }
}

// Обработка выбранной папки
function onFolderPicked(event) {
    const files = event.target.files;
    if (files && files.length > 0) {
        // Получаем полный путь к выбранной папке
        const fullPath = files[0].path ? files[0].path.substring(0, files[0].path.lastIndexOf('\\')) : '';
        if (fullPath) {
            document.getElementById('directory').value = fullPath;
            saveCurrentSettings(false);
            showToast('Выбрана папка: ' + fullPath);
        }
    }
}
</script>

<script>
(function () {
    if (!window.showBottomMessage) {
        window.showBottomMessage = function (message, type) {
            try {
                type = type || "info";

                var text = "";

                if (message === undefined || message === null) {
                    text = "";
                } else if (typeof message === "string") {
                    text = message;
                } else {
                    try {
                        text = JSON.stringify(message);
                    } catch (e) {
                        text = String(message);
                    }
                }

                if (!text) {
                    return;
                }

                var existingToastFns = [
                    "showToast",
                    "toast",
                    "notify",
                    "showNotification",
                    "showAppToast",
                    "addToast"
                ];

                for (var i = 0; i < existingToastFns.length; i++) {
                    var fnName = existingToastFns[i];

                    if (typeof window[fnName] === "function") {
                        try {
                            window[fnName](text, type);
                            return;
                        } catch (e) {
                            try {
                                window[fnName](text);
                                return;
                            } catch (e2) {}
                        }
                    }
                }

                var container = document.getElementById("baikalBottomToastContainer");

                if (!container) {
                    container = document.createElement("div");
                    container.id = "baikalBottomToastContainer";
                    container.style.position = "fixed";
                    container.style.left = "50%";
                    container.style.bottom = "24px";
                    container.style.transform = "translateX(-50%)";
                    container.style.zIndex = "999999";
                    container.style.display = "flex";
                    container.style.flexDirection = "column";
                    container.style.alignItems = "center";
                    container.style.gap = "10px";
                    container.style.pointerEvents = "none";
                    document.body.appendChild(container);
                }

                var item = document.createElement("div");
                item.textContent = text;
                item.style.maxWidth = "min(520px, calc(100vw - 32px))";
                item.style.padding = "12px 16px";
                item.style.borderRadius = "12px";
                item.style.color = "#ffffff";
                item.style.fontSize = "14px";
                item.style.lineHeight = "1.35";
                item.style.boxShadow = "0 12px 35px rgba(0,0,0,0.35)";
                item.style.pointerEvents = "auto";
                item.style.opacity = "0";
                item.style.transition = "opacity .2s ease, transform .2s ease";
                item.style.transform = "translateY(10px)";
                item.style.whiteSpace = "pre-wrap";
                item.style.wordBreak = "break-word";

                if (type === "error") {
                    item.style.background = "#b42318";
                } else if (type === "success") {
                    item.style.background = "#1a7f37";
                } else if (type === "warning") {
                    item.style.background = "#9a6700";
                } else {
                    item.style.background = "#24292f";
                }

                container.appendChild(item);

                requestAnimationFrame(function () {
                    item.style.opacity = "1";
                    item.style.transform = "translateY(0)";
                });

                setTimeout(function () {
                    item.style.opacity = "0";
                    item.style.transform = "translateY(10px)";

                    setTimeout(function () {
                        if (item && item.parentNode) {
                            item.parentNode.removeChild(item);
                        }
                    }, 250);
                }, 4500);
            } catch (e) {
                console.log("showBottomMessage error:", e);
            }
        };
    }

    if (!window.showBottomUpdateNotice) {
        window.showBottomUpdateNotice = function (info) {
            try {
                var currentVersion = info.current_version || info.currentVersion || "";
                var updateVersion = info.update_version || info.updateVersion || "";
                var assetName = info.asset_name || info.assetName || "Baikal_Downloader_Setup.exe";
                var sizeText = info.size_text || info.sizeText || "неизвестно";

                var message = "Доступна новая версия";

                if (currentVersion || updateVersion) {
                    message += ": " + currentVersion + " → " + updateVersion;
                }

                message += "\nФайл: " + assetName;
                message += "\nРазмер: " + sizeText;

                window.showBottomMessage(message, "info");

                if (typeof window.openUpdateWindow === "function") {
                    setTimeout(function () {
                        try {
                            window.openUpdateWindow(info);
                        } catch (e) {
                            console.log("openUpdateWindow error:", e);
                        }
                    }, 500);
                }
            } catch (e) {
                console.log("showBottomUpdateNotice error:", e);
            }
        };
    }

    window.alert = function (message) {
        window.showBottomMessage(message, "info");
    };

    window.confirm = function (message) {
        window.showBottomMessage(message, "info");
        return true;
    };

    window.prompt = function (message, defaultValue) {
        window.showBottomMessage(message, "info");
        return defaultValue || "";
    };
})();
</script>

<script>
window.addEventListener('pywebviewready', function() {
  const winControls = document.getElementById('winControls');
  if (winControls) {
    winControls.style.display = 'flex';
  }
});
</script>

<script>
function formatSizeFromBytes(size) {
    try {
        size = Number(size);

        if (!size || size <= 0) {
            return "";
        }

        var units = ["Б", "КБ", "МБ", "ГБ", "ТБ"];
        var value = size;

        for (var i = 0; i < units.length; i++) {
            if (value < 1024 || i === units.length - 1) {
                if (units[i] === "Б") {
                    return Math.round(value) + " " + units[i];
                }

                return value.toFixed(1).replace(".", ",") + " " + units[i];
            }

            value = value / 1024;
        }

        return "";
    } catch (e) {
        return "";
    }
}
</script>

</body>
</html>
"""

  # --- УМНАЯ КНОПКА АВТОРИЗАЦИИ (ПРОВЕРКА ПРОФИЛЯ) ---
profile_dir = os.path.join(DATA_DIR, "youtube_profile")
if os.path.exists(profile_dir):
    # Если мы уже входили (папка есть) -> Синяя кнопка
    HTML_PAGE = HTML_PAGE.replace("__AUTH_BTN_TEXT__", "✅ Авторизация сохранена (Изменить аккаунт)")
    HTML_PAGE = HTML_PAGE.replace("__AUTH_COLOR__", "linear-gradient(135deg, #3b82f6, #2563eb)")
    HTML_PAGE = HTML_PAGE.replace("__AUTH_HINT__", "<span style='color:#34d399; font-weight:bold;'>Профиль найден!</span> Программа готова к скачиванию 18+ видео.")
else:
    # Если входим в первый раз -> Зеленая кнопка
    HTML_PAGE = HTML_PAGE.replace("__AUTH_BTN_TEXT__", "🔑 Войти в аккаунт YouTube")
    HTML_PAGE = HTML_PAGE.replace("__AUTH_COLOR__", "linear-gradient(135deg, #10b981, #059669)")
    HTML_PAGE = HTML_PAGE.replace("__AUTH_HINT__", "Программа откроет окно вашего браузера. Войдите в аккаунт и закройте окно — мы сами сохраним доступ!")
# ----------------------------------------------------

# ЭТОТ КОД ДОЛЖЕН БЫТЬ ТАМ, ГДЕ ВЫЗЫВАЕТСЯ НАЖАТИЕ КНОПКИ АВТОРИЗАЦИИ:
def run_youtube_auth():
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    
    # Засекаем время
    start_time = time.time()
    
    try:
        if getattr(sys, 'frozen', False):
            # Если программа скомпилирована в EXE, запускаем САМИ СЕБЯ с секретной командой
            subprocess.run([sys.executable, "RUN_AUTH", data_dir], check=True)
        else:
            # Если запускаем через обычный Python (для разработки)
            import youtube_auth
            youtube_auth.main(data_dir)
            
        # Проверяем, сколько времени окно было открыто
        elapsed_time = time.time() - start_time
        
        # Если окно закрыли быстрее, чем за 15 секунд — считаем, что входа не было
        if elapsed_time < 15:
            return {"status": "error", "message": "Окно закрыто слишком быстро. Вы не авторизовались!"}
            
        return {"status": "success", "message": "Профиль браузера сохранен."}
        
    except Exception as e:
        return {"status": "error", "message": f"Ошибка запуска: {str(e)}"}
 
def log(msg, level="info"):
    message_queue.put(
        json.dumps(
            {
                "type": level,
                "text": str(msg),
            },
            ensure_ascii=False
        )
    )


def job_done(platform, ok=True, job_index=0, file_path=""):
    file_name = os.path.basename(file_path) if file_path and file_path not in ["Видео", "Video"] else ""
    message_queue.put(
        json.dumps(
            {
                "type": "job_done",
                "platform": platform or "generic",
                "ok": bool(ok),
                "job_index": job_index,
                "file_path": file_path,   # <-- Полный путь для выделения в папке
                "file_name": file_name    # <-- Имя файла для замены ссылки в UI
            },
            ensure_ascii=False
        )
    )


def _find_ffmpeg():
    strict_path = os.path.join(BASE_DIR, "tools", "ffmpeg", "bin", f"ffmpeg{EXE_EXT}")
    if os.path.exists(strict_path):
        return strict_path

    candidates = [
        FFMPEG_PATH,
        os.path.join(FFMPEG_DIR, f"ffmpeg{EXE_EXT}"),
        os.path.join(BASE_DIR, "ffmpeg", "bin", f"ffmpeg{EXE_EXT}"),
        os.path.join(BASE_DIR, "ffmpeg", f"ffmpeg{EXE_EXT}"),
        os.path.join(BASE_DIR, f"ffmpeg{EXE_EXT}"),
        shutil.which("ffmpeg"),
    ]

    for p in candidates:
        if p and os.path.exists(p):
            return p

    return None


_resolved_ffmpeg = _find_ffmpeg()

if _resolved_ffmpeg:
    FFMPEG_PATH = _resolved_ffmpeg


def _find_js_runtime():
    """
    Ищет JS-рантайм для yt-dlp.
    Сначала проверяет Deno (так как yt-dlp сейчас отдает ему наивысший приоритет),
    затем Node.js. Сначала в локальной папке tools, потом в системе.
    """
    local_deno = os.path.join(TOOLS_DIR, f"deno{EXE_EXT}")
    if os.path.exists(local_deno):
        return "deno", local_deno
    
    local_node = os.path.join(TOOLS_DIR, f"node{EXE_EXT}")
    if os.path.exists(local_node):
        return "node", local_node
    
    sys_deno = shutil.which("deno")
    if sys_deno:
        return "deno", sys_deno
    
    sys_node = shutil.which("node")
    if sys_node:
        return "node", sys_node
    
    return None, None


def get_youtube_extra_args():
    args = []
    
    rt_type, rt_path = _find_js_runtime()
    if rt_type and rt_path:
        args.extend(["--js-runtimes", f"{rt_type}:{rt_path}"])
    else:
        log("Предупреждение: JS-рантайм (Deno/Node.js) не обнаружен.", "warn")
        
    settings = load_app_settings()
    browser = settings.get("browserCookies", "none").strip().lower()
    
    if browser == "auth_profile":
        profile_dir = os.path.join(DATA_DIR, "youtube_profile")
        browser_info_file = os.path.join(DATA_DIR, "browser_type.txt")
        
        if os.path.exists(profile_dir):
            b_type = "chrome"
            if os.path.exists(browser_info_file):
                with open(browser_info_file, "r", encoding="utf-8") as f:
                    b_type = f.read().strip()
            
            # Передаем ядру полный путь до папки профиля
            abs_profile = os.path.abspath(profile_dir)
            args.extend(["--cookies-from-browser", f"{b_type}:{abs_profile}"])
            log("🔑 Используется безопасный встроенный профиль авторизации", "ok")
        else:
            log("⚠ Профиль авторизации не найден! Нажмите 'Войти в аккаунт YouTube' в настройках.", "error")
            
    elif browser == "cookies.txt":
        cookies_path = os.path.join(DATA_DIR, "cookies.txt")
        if os.path.exists(cookies_path):
            args.extend(["--cookies", cookies_path])
            log("🔑 Используется файл cookies.txt", "ok")
        else:
            log(f"⚠ Файл cookies.txt не найден! Положите его в папку: {DATA_DIR}", "error")
            
    return args
def get_safe_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", str(name)).strip()


def get_unique_filepath(download_dir, base_name, ext=".mp4"):
    base_name = get_safe_filename(base_name) or f"video_{int(time.time())}"
    file_path = os.path.join(download_dir, f"{base_name}{ext}")

    counter = 2
    while os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        file_path = os.path.join(download_dir, f"{base_name} ({counter}){ext}")
        counter += 1

    return file_path


def get_copy_suffix(copy_index):
    try:
        copy_index = int(copy_index or 1)
    except Exception:
        copy_index = 1

    if copy_index > 1:
        return f" ({copy_index})"

    return ""


YTDLP_NAME_REGISTRY = {}


def _filename_stem_exists(download_dir, wanted_stem):
    wanted_stem = str(wanted_stem or "").strip().lower()

    if not wanted_stem:
        return False

    try:
        if not os.path.isdir(download_dir):
            return False

        for name in os.listdir(download_dir):
            stem, _ext = os.path.splitext(name)

            if stem.strip().lower() == wanted_stem:
                path = os.path.join(download_dir, name)

                try:
                    if os.path.isfile(path) and os.path.getsize(path) > 0:
                        return True
                except Exception:
                    return True
    except Exception:
        pass

    return False


def _reserve_name_index(download_dir, base_name, requested_index=1):
    base_name = get_safe_filename(base_name) or f"video_{int(time.time())}"

    try:
        requested_index = int(requested_index or 1)
    except Exception:
        requested_index = 1

    if requested_index < 1:
        requested_index = 1

    key = os.path.abspath(download_dir).lower() + "|" + base_name.lower()

    reserved_until = YTDLP_NAME_REGISTRY.get(key, 0)
    index = max(requested_index, reserved_until + 1)

    while True:
        if index <= 1:
            wanted_stem = base_name
        else:
            wanted_stem = f"{base_name} ({index})"

        if not _filename_stem_exists(download_dir, wanted_stem):
            break

        index += 1

    YTDLP_NAME_REGISTRY[key] = index
    return index
# --- ВОЗВРАЩАЕМ СТАРУЮ ЛОГИКУ НОМЕРОВ ---
def get_numeric_out_tmpl(download_dir, start_time=None):
    base_name = "597" if start_time is None else str(start_time)
    counter = 1
    while True:
        name_to_check = base_name if counter == 1 else f"{base_name} ({counter})"
        if not _filename_stem_exists(download_dir, name_to_check):
            return os.path.join(download_dir, f"{name_to_check}.%(ext)s")
        counter += 1
# ----------------------------------------

def safe_decode(bytes_data):
    """
    Умный декодер: автоматически определяет правильную кодировку русского языка (UTF-8, CP1251 или CP866).
    """
    if not bytes_data:
        return ""
    for encoding in ("utf-8", "cp1251", "cp866"):
        try:
            return bytes_data.decode(encoding)
        except UnicodeDecodeError:
            continue
    # Если ничего не подошло, декодируем с заменой поврежденных символов
    return bytes_data.decode("utf-8", errors="replace")

def get_ytdlp_title_for_url(url):
    try:
        if not os.path.exists(YTDLP_PATH):
            return ""

        cmd = [
            YTDLP_PATH,
            "--skip-download",
            "--no-playlist",
            "--no-warnings",
            "--print",
            "%(title)s",
        ]
        
        if "youtube" in url.lower() or "youtu.be" in url.lower():
            cmd += get_youtube_extra_args()
            
        cmd.append(url)

        # Читаем вывод в бинарном режиме
        proc = subprocess.run(
            cmd,
            cwd=BASE_DIR,
            capture_output=True,
            timeout=90,
        )

        # Безопасно расшифровываем название на русском языке
        stdout_text = safe_decode(proc.stdout)
        title = ""

        for line in stdout_text.splitlines():
            line = line.strip()
            if line:
                title = line
                break

        return title

    except Exception as e:
        log(f"  Не удалось заранее проверить имя файла: {e}", "warn")
        return ""


def get_ytdlp_collision_suffix(download_dir, url, requested_index=1, title_tail=""):
    title = get_ytdlp_title_for_url(url)

    if not title:
        return get_copy_suffix(requested_index)

    base_name = get_safe_filename(f"{title}{title_tail}") or f"video_{int(time.time())}"
    final_index = _reserve_name_index(download_dir, base_name, requested_index)

    if final_index > 1:
        log(f"  Такое имя уже есть или запланировано: сохраняю как копию ({final_index})", "warn")

    return get_copy_suffix(final_index)


def get_installed_version():
    if os.path.exists(YTDLP_VERSION_FILE):
        try:
            with open(YTDLP_VERSION_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass

    return None


def save_installed_version(version):
    try:
        with open(YTDLP_VERSION_FILE, "w", encoding="utf-8") as f:
            f.write(version or "unknown")
    except Exception:
        pass


def get_ffmpeg_installed_version():
    if os.path.exists(FFMPEG_VERSION_FILE):
        try:
            with open(FFMPEG_VERSION_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass

    return None


def save_ffmpeg_installed_version(version):
    try:
        with open(FFMPEG_VERSION_FILE, "w", encoding="utf-8") as f:
            f.write(version or "unknown")
    except Exception:
        pass


def github_json(url, timeout=15):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "BaikalDownloader/5.5",
            "Accept": "application/vnd.github+json",
        },
    )

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def get_latest_ytdlp_release():
    try:
        data = github_json(GITHUB_YTDLP_API, 12)
        tag = data.get("tag_name", "")
        target_asset = "yt-dlp.exe" if IS_WIN else "yt-dlp_macos"

        for asset in data.get("assets", []):
            if asset.get("name") == target_asset:
                return tag, asset.get("browser_download_url")

        if not IS_WIN:
            for asset in data.get("assets", []):
                if asset.get("name") == "yt-dlp":
                    return tag, asset.get("browser_download_url")

        return tag, None
    except Exception as e:
        log(f"GitHub недоступен для yt-dlp: {e}", "warn")
        return None, None


def get_latest_ffmpeg_release():
    try:
        data = github_json(GITHUB_FFMPEG_API, 18)
        tag = data.get("tag_name", "")
        assets = data.get("assets", [])

        preferred = None
        fallback = None

        for asset in assets:
            name = asset.get("name", "").lower()
            url = asset.get("browser_download_url")

            if not url or not name.endswith(".zip"):
                continue

            if IS_WIN:
                if "win64" in name:
                    if "gpl" in name and "shared" not in name:
                        preferred = url
                        break
                    fallback = fallback or url
            else:
                if "macos" in name or "osx" in name:
                    preferred = url
                    break

        return tag, preferred or fallback
    except Exception as e:
        log(f"GitHub недоступен для ffmpeg: {e}", "warn")
        return None, None


def download_ytdlp():
    log("Проверяю yt-dlp...", "info")

    if os.path.exists(YTDLP_PATH):
        installed = get_installed_version()
        latest_tag, _ = get_latest_ytdlp_release()

        if installed and latest_tag and installed == latest_tag:
            log(f"yt-dlp актуален ({installed})", "ok")
            return True

        if not latest_tag:
            log("Не удалось проверить обновления, использую текущий yt-dlp", "warn")
            return True

    latest_tag, download_url = get_latest_ytdlp_release()

    if not download_url:
        if os.path.exists(YTDLP_PATH):
            log("Ссылка загрузки недоступна, использую существующий yt-dlp", "warn")
            return True

        log("Не удалось получить ссылку на yt-dlp", "error")
        return False

    log("Скачиваю yt-dlp...", "info")
    tmp_path = YTDLP_PATH + ".tmp"

    try:
        urllib.request.urlretrieve(download_url, tmp_path)

        if os.path.exists(YTDLP_PATH):
            os.remove(YTDLP_PATH)

        os.rename(tmp_path, YTDLP_PATH)
        if not IS_WIN:
            try:
                os.chmod(YTDLP_PATH, 0o755)
                # --- ФИКС ДЛЯ MACOS: Снимаем блокировку Gatekeeper с yt-dlp ---
                if sys.platform == "darwin":
                    subprocess.run(["xattr", "-d", "com.apple.quarantine", YTDLP_PATH], stderr=subprocess.DEVNULL)
            except Exception as e:
                log(f"Не удалось выдать права на запуск yt-dlp: {e}", "warn")
        save_installed_version(latest_tag)

        log(f"yt-dlp установлен: {latest_tag}", "ok")
        return True
    except Exception as e:
        log(f"Ошибка загрузки yt-dlp: {e}", "error")

        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass

        return os.path.exists(YTDLP_PATH)


def download_deno():
    """
    Проверяет наличие автономного Deno в tools. Если его нет,
    скачивает официальный ZIP-архив с GitHub и распаковывает его напрямую в tools.
    Решена проблема с ошибкой [WinError 2] при перезаписи файлов.
    """
    global DENO_PATH
    log("Проверяю автономный Deno...", "info")

    local_deno = os.path.join(TOOLS_DIR, f"deno{EXE_EXT}")
    if os.path.exists(local_deno):
        log("Автономный Deno уже установлен в tools", "ok")
        DENO_PATH = local_deno
        return True

    log("Автономный Deno не найден в tools. Начинаю автоматическую установку...", "info")
    os.makedirs(TOOLS_DIR, exist_ok=True)

    if IS_WIN:
        download_url = "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip"
    elif IS_MAC:
        import platform
        if platform.machine().lower() == "arm64":
            download_url = "https://github.com/denoland/deno/releases/latest/download/deno-aarch64-apple-darwin.zip"
        else:
            download_url = "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-apple-darwin.zip"
    else:
        download_url = "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-unknown-linux-gnu.zip"

    tmp_zip = os.path.join(TOOLS_DIR, "deno_tmp.zip")
    try:
        # Скачиваем с User-Agent
        req = urllib.request.Request(
            download_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )
        with urllib.request.urlopen(req, timeout=120) as response, open(tmp_zip, "wb") as out_file:
            shutil.copyfileobj(response, out_file)
        
        # Читаем ZIP и сразу записываем в нужный файл без промежуточной распаковки/переименований
        extracted = False
        with zipfile.ZipFile(tmp_zip, "r") as z:
            for file_info in z.infolist():
                if file_info.filename.lower() in ["deno", "deno.exe"]:
                    if os.path.exists(local_deno):
                        try:
                            os.remove(local_deno)
                        except Exception:
                            pass
                    
                    # Прямая потоковая запись в local_deno
                    with z.open(file_info) as source, open(local_deno, "wb") as target:
                        shutil.copyfileobj(source, target)
                    
                    extracted = True
                    break
        
        if not extracted:
            raise FileNotFoundError("Исполняемый файл deno не найден в архиве")

        if not IS_WIN:
            os.chmod(local_deno, 0o755)

        log("Автономный Deno успешно установлен в tools", "ok")
        DENO_PATH = local_deno
        return True
    except Exception as e:
        log(f"Не удалось установить автономный Deno: {e}", "warn")
        return False
    finally:
        if os.path.exists(tmp_zip):
            try:
                os.remove(tmp_zip)
            except Exception:
                pass


def download_node():
    """
    [РЕЗЕРВНЫЙ МЕТОД] Проверяет Node.js и скачивает в tools, если Deno не смог установиться.
    """
    global NODE_PATH
    log("Проверяю автономный Node.js...", "info")

    local_node = os.path.join(TOOLS_DIR, f"node{EXE_EXT}")
    if os.path.exists(local_node):
        log("Автономный Node.js уже установлен в tools", "ok")
        NODE_PATH = local_node
        return True

    log("Автономный Node.js не найден в tools. Запускаю установку резервного рантайма...", "info")
    os.makedirs(TOOLS_DIR, exist_ok=True)

    if IS_WIN:
        download_url = "https://nodejs.org/dist/v20.11.1/win-x64/node.exe"
        tmp_path = NODE_PATH + ".tmp"
        try:
            req = urllib.request.Request(
                download_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
            )
            with urllib.request.urlopen(req, timeout=120) as response, open(tmp_path, "wb") as out_file:
                shutil.copyfileobj(response, out_file)
            
            if os.path.exists(NODE_PATH):
                os.remove(NODE_PATH)
            os.rename(tmp_path, NODE_PATH)
            log("Резервный Node.js успешно установлен в tools", "ok")
            return True
        except Exception as e:
            log(f"Не удалось скачать автономный Node.js: {e}", "warn")
            if os.path.exists(tmp_path):
                try: os.remove(tmp_path)
                except: pass
            
            sys_node = shutil.which("node")
            if sys_node:
                log("Использую резервный системный Node.js", "ok")
                return True
            return False
    else:
        if IS_MAC:
            download_url = "https://nodejs.org/dist/v20.11.1/node-v20.11.1-darwin-x64.tar.gz"
        else:
            download_url = "https://nodejs.org/dist/v20.11.1/node-v20.11.1-linux-x64.tar.gz"

        tmp_tar = os.path.join(TOOLS_DIR, "node_tmp.tar.gz")
        try:
            req = urllib.request.Request(
                download_url,
                headers={
                    "User-Agent": "Mozilla/5.0"
                }
            )
            with urllib.request.urlopen(req, timeout=180) as response, open(tmp_tar, "wb") as out_file:
                shutil.copyfileobj(response, out_file)
            
            import tarfile
            with tarfile.open(tmp_tar, "r:gz") as tar:
                for member in tar.getmembers():
                    if member.name.endswith("/bin/node") or member.name == "node":
                        extracted_f = tar.extractfile(member)
                        if extracted_f:
                            if os.path.exists(NODE_PATH):
                                os.remove(NODE_PATH)
                            with open(NODE_PATH, "wb") as dest:
                                dest.write(extracted_f.read())
                            break
            os.chmod(NODE_PATH, 0o755)
            log("Резервный Node.js успешно установлен в tools", "ok")
            return True
        except Exception as e:
            log(f"Не удалось установить автономный Node.js: {e}", "warn")
            sys_node = shutil.which("node")
            if sys_node:
                log("Использую системный Node.js", "ok")
                return True
            return False
        finally:
            if os.path.exists(tmp_tar):
                try: os.remove(tmp_tar)
                except: pass


def download_ffmpeg():
    global FFMPEG_PATH

    log("Проверяю ffmpeg...", "info")

    ff = _find_ffmpeg()

    if ff:
        FFMPEG_PATH = ff
        ver = get_ffmpeg_installed_version()

        if ver:
            log(f"ffmpeg найден ({ver})", "ok")
        else:
            log(f"ffmpeg найден: {ff}", "ok")

        return True

    latest_tag, download_url = get_latest_ffmpeg_release()

    if not download_url:
        if not IS_WIN:
            log("Использую резервную ссылку FFmpeg для macOS...", "info")
            download_url = "https://github.com/eugeneware/ffmpeg-static/releases/download/b5.0.1/darwin-x64"
        else:
            log("Не удалось получить архив ffmpeg", "warn")
            return False

    log("Скачиваю ffmpeg...", "info")

    tmp_zip = os.path.join(BASE_DIR, "ffmpeg.zip")
    tmp_extract = os.path.join(BASE_DIR, "_ffmpeg_tmp")

    try:
        urllib.request.urlretrieve(download_url, tmp_zip)

        if not IS_WIN and not download_url.endswith('.zip'):
            os.makedirs(FFMPEG_BIN_DIR, exist_ok=True)
            target_bin = os.path.join(FFMPEG_BIN_DIR, "ffmpeg")
            shutil.copy2(tmp_zip, target_bin)
            os.chmod(target_bin, 0o755)
            FFMPEG_PATH = target_bin
            save_ffmpeg_installed_version("mac-static-b5.0.1")
            log("ffmpeg установлен (прямой бинарник)", "ok")
            return True

        if os.path.isdir(tmp_extract):
            shutil.rmtree(tmp_extract, ignore_errors=True)

        os.makedirs(tmp_extract, exist_ok=True)

        with zipfile.ZipFile(tmp_zip, "r") as z:
            z.extractall(tmp_extract)

        found = None
        target_file = f"ffmpeg{EXE_EXT}"

        for root, _, files in os.walk(tmp_extract):
            if target_file in files and os.path.basename(root).lower() == "bin":
                found = os.path.join(root, target_file)
                break

        if not found:
            for root, _, files in os.walk(tmp_extract):
                if target_file in files:
                    found = os.path.join(root, target_file)
                    break

        if not found:
            log(f"В архиве не найден {target_file}", "warn")
            return False

        if os.path.isdir(FFMPEG_DIR):
            shutil.rmtree(FFMPEG_DIR, ignore_errors=True)

        bin_dir = os.path.dirname(found)

        if os.path.basename(bin_dir).lower() == "bin":
            shutil.copytree(bin_dir, FFMPEG_BIN_DIR)
        else:
            os.makedirs(FFMPEG_BIN_DIR, exist_ok=True)
            shutil.copy2(found, os.path.join(FFMPEG_BIN_DIR, target_file))

        FFMPEG_PATH = os.path.join(FFMPEG_BIN_DIR, target_file)
        
        if not IS_WIN:
            try:
                os.chmod(FFMPEG_PATH, 0o755)
                # --- ФИКС ДЛЯ MACOS: Снимаем блокировку Gatekeeper с FFmpeg ---
                if sys.platform == "darwin":
                    subprocess.run(["xattr", "-d", "com.apple.quarantine", FFMPEG_PATH], stderr=subprocess.DEVNULL)
                # --------------------------------------------------------------
            except Exception as e:
                log(f"Не удалось выдать права на запуск ffmpeg: {e}", "warn")

        save_ffmpeg_installed_version(latest_tag or "unknown")

        log(f"ffmpeg установлен: {latest_tag or 'unknown'}", "ok")
        return True
    except Exception as e:
        log(f"Ошибка установки ffmpeg: {e}", "warn")
        return False
    finally:
        try:
            if os.path.exists(tmp_zip):
                os.remove(tmp_zip)

            if os.path.isdir(tmp_extract):
                shutil.rmtree(tmp_extract, ignore_errors=True)
        except Exception:
            pass


def format_time(seconds):
    if not isinstance(seconds, (int, float)) or seconds < 0:
        return "—"

    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60

    if h:
        return f"{h}ч {m}м {s}с"

    if m:
        return f"{m}м {s}с"

    return f"{s}с"


def play_backend_done_sound():
    """
    Системный звуковой сигнал (бипер) по завершению всех скачиваний.
    Точно повторяет JS-арпеджио [До, Ми, Соль, До]
    """
    try:
        if IS_WIN:
            import winsound
            winsound.Beep(523, 120)  # До (C5)
            winsound.Beep(659, 120)  # Ми (E5)
            winsound.Beep(784, 120)  # Соль (G5)
            winsound.Beep(1047, 250) # До (C6) - финальный акцент
        else:
            sys.stdout.write('\a')
            sys.stdout.flush()
    except Exception:
        pass


def _bd_to_number(value):
    if value is None:
        return 0.0

    value = str(value).strip()

    if value in ("", "NA", "None", "none", "null", "N/A"):
        return 0.0

    try:
        return float(value)
    except Exception:
        return 0.0


def _bd_format_bytes(num):
    num = float(num or 0)

    units = ["Б", "КБ", "МБ", "ГБ", "ТБ"]

    for unit in units:
        if num < 1024:
            return f"{num:.1f} {unit}"
        num /= 1024

    return f"{num:.1f} ПБ"


def _bd_format_time_short(seconds):
    seconds = int(seconds or 0)

    if seconds < 0:
        seconds = 0

    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60

    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"

    return f"{m:02d}:{s:02d}"


def _bd_emit_progress(percent, downloaded, total, speed, eta, elapsed, status="downloading"):
    if total and total > 0:
        size_text = f"{_bd_format_bytes(downloaded)} / {_bd_format_bytes(total)}"
    else:
        size_text = f"{_bd_format_bytes(downloaded)} / размер неизвестен"

    text = (
        f"{percent:.1f}% · "
        f"{size_text} · "
        f"скорость {_bd_format_bytes(speed)}/с · "
        f"прошло {_bd_format_time_short(elapsed)} · "
        f"осталось {_bd_format_time_short(eta)}"
    )

    message_queue.put(
        json.dumps(
            {
                "type": "progress",
                "status": status,
                "percent": round(float(percent or 0), 1),
                "downloaded": float(downloaded or 0),
                "total": float(total or 0),
                "speed": float(speed or 0),
                "eta": int(eta or 0),
                "elapsed": int(elapsed or 0),
                "text": text,
            },
            ensure_ascii=False,
        )
    )


def _bd_parse_ytdlp_progress_line(line, started_at):
    line = str(line or "").strip()

    if not line.startswith("BD_PROGRESS|"):
        return False

    parts = line.split("|")

    if len(parts) < 8:
        return True

    status = parts[1]
    downloaded = _bd_to_number(parts[2])
    total = _bd_to_number(parts[3])
    estimate = _bd_to_number(parts[4])
    speed = _bd_to_number(parts[5])
    eta = _bd_to_number(parts[6])

    elapsed = time.monotonic() - started_at

    if total <= 0 and estimate > 0:
        total = estimate

    percent = 0.0

    if total > 0:
        percent = downloaded / total * 100.0
        percent = max(0.0, min(100.0, percent))

    _bd_emit_progress(
        percent=percent,
        downloaded=downloaded,
        total=total,
        speed=speed,
        eta=eta,
        elapsed=elapsed,
        status=status,
    )

    return True


def _bd_add_ytdlp_progress_args(cmd):
    if not cmd:
        return cmd

    cmd = list(cmd)

    exe = os.path.basename(str(cmd[0])).lower()

    if "yt-dlp" not in exe:
        return cmd

    if "--progress-template" in cmd:
        return cmd

    progress_args = [
        "--newline",
        "--no-color",
        "--progress-template",
        "download:BD_PROGRESS|%(progress.status)s|%(progress.downloaded_bytes)s|%(progress.total_bytes)s|%(progress.total_bytes_estimate)s|%(progress.speed)s|%(progress.eta)s|%(progress.elapsed)s",
    ]

    return [cmd[0]] + progress_args + cmd[1:]


def run_process(cmd, cwd=BASE_DIR, prefix=" "):
    global current_process, cancel_requested
    actual_file = "Видео"
    started_at = time.monotonic()

    try:
        cmd = _bd_add_ytdlp_progress_args(cmd)

        # Запускаем процесс в бинарном режиме
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            cwd=cwd,
        )
        
        current_process = proc

        # Читаем сырые байты построчно
        for line_bytes in proc.stdout:
            if cancel_requested:
                proc.kill()
                break
                
            # Безопасно декодируем русский язык
            line = safe_decode(line_bytes).rstrip()

            if not line:
                continue

            if _bd_parse_ytdlp_progress_line(line, started_at):
                continue

            log(f"{prefix}{line}", "cmd")

            if "[download] Destination:" in line:
                actual_file = line.split("Destination:", 1)[1].strip()
            elif "[Merger] Merging formats into" in line:
                m = re.search(r'"([^"]+)"', line)
                if m:
                    actual_file = m.group(1)
            elif "has already been downloaded" in line and "[download]" in line:
                try:
                    actual_file = line.split("[download]", 1)[1].split("has already", 1)[0].strip()
                except Exception:
                    pass

        proc.wait()

        elapsed = time.monotonic() - started_at

        if proc.returncode == 0:
            _bd_emit_progress(
                percent=100,
                downloaded=0,
                total=0,
                speed=0,
                eta=0,
                elapsed=elapsed,
                status="finished",
            )

        current_process = None

        # Регистрируем успешно скачанный файл для последующей проверки кодека
        if proc.returncode == 0 and actual_file not in ("Видео", "Video"):
            try:
                full = actual_file
                if not os.path.isabs(full):
                    full = os.path.join(cwd, actual_file)
                if os.path.exists(full):
                    downloaded_files_session.append(os.path.abspath(full))
            except Exception:
                pass

        return proc.returncode, actual_file

    except Exception as e:
        log(f"✗ Ошибка запуска процесса: {e}", "error")
        return 999, actual_file


# ===== PATCH 5.5.3: MP3 Conversion Helpers =====
def convert_to_mp3(input_path):
    """
    Принудительно конвертирует скачанный аудио/видеофайл в MP3 с максимальным качеством.
    """
    if not FFMPEG_PATH or not os.path.exists(input_path):
        return input_path

    base, ext = os.path.splitext(input_path)
    if ext.lower() == ".mp3":
        return input_path

    dir_name = os.path.dirname(input_path)
    base_name = os.path.basename(base)
    output_path = get_unique_filepath(dir_name, base_name, ".mp3")

    cmd = [
        FFMPEG_PATH,
        "-y",
        "-i", input_path,
        "-vn",
        "-acodec", "libmp3lame",
        "-q:a", "0",
        output_path
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL
        )
        proc.wait()
        if proc.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            try:
                os.remove(input_path)
            except Exception:
                pass
            return output_path
    except Exception as e:
        log(f"  Ошибка конвертации в MP3: {e}", "warn")

    return input_path
    
    # ===== ПРОВЕРКА КОДЕКА И КОНВЕРТАЦИЯ В H264 =====

# Глобальный список файлов, скачанных в текущей сессии
downloaded_files_session = []
files_to_convert_pending = []  # Файлы, ожидающие подтверждения конвертации


def _find_ffprobe():
    """Ищет ffprobe рядом с ffmpeg."""
    if FFMPEG_PATH and os.path.exists(FFMPEG_PATH):
        probe = os.path.join(os.path.dirname(FFMPEG_PATH), f"ffprobe{EXE_EXT}")
        if os.path.exists(probe):
            return probe
    return shutil.which("ffprobe")


def get_video_codec(file_path):
    """Возвращает название видеокодека файла (h264, vp9, av1 и т.д.) или ''."""
    ffprobe = _find_ffprobe()
    if not ffprobe or not os.path.exists(file_path):
        return ""

    cmd = [
        ffprobe,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=codec_name",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=30)
        codec = safe_decode(proc.stdout).strip().lower()
        return codec
    except Exception:
        return ""


def is_h264_codec(codec):
    """Проверяет, является ли кодек H264/AVC."""
    codec = str(codec or "").lower()
    return codec in ("h264", "avc", "avc1")


def find_non_h264_files():
    """Проверяет все скачанные видеофайлы и возвращает список тех, что не H264."""
    non_h264 = []
    video_exts = (".mp4", ".webm", ".mkv", ".avi", ".mov", ".flv", ".ts")

    for fpath in downloaded_files_session:
        if not fpath or not os.path.exists(fpath):
            continue
        ext = os.path.splitext(fpath)[1].lower()
        if ext not in video_exts:
            continue
        codec = get_video_codec(fpath)
        if codec and not is_h264_codec(codec):
            non_h264.append({"path": fpath, "codec": codec})
    return non_h264


def convert_to_h264(input_path):
    """Перекодирует видеофайл в H.264 (AVC) + AAC в контейнер MP4."""
    if not FFMPEG_PATH or not os.path.exists(input_path):
        return False

    dir_name = os.path.dirname(input_path)
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    # Временный выходной файл
    output_path = os.path.join(dir_name, f"{base_name}_h264_tmp.mp4")

    cmd = [
        FFMPEG_PATH,
        "-y",
        "-i", input_path,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        output_path,
    ]

    try:
        log(f"  Конвертирую в H264: {os.path.basename(input_path)}...", "info")
        code, _ = run_process(cmd, BASE_DIR, "  ")

        if code == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 100_000:
            # Определяем финальное имя (заменяем оригинал на .mp4)
            final_path = os.path.join(dir_name, f"{base_name}.mp4")

            try:
                os.remove(input_path)  # Удаляем оригинал (VP9/AV1)
            except Exception:
                pass

            # Если после удаления имя свободно — переименовываем; иначе делаем уникальное
            if os.path.exists(final_path):
                final_path = get_unique_filepath(dir_name, base_name, ".mp4")

            os.rename(output_path, final_path)
            log(f"✓ Перекодировано в H264: {os.path.basename(final_path)}", "ok")
            return True
        else:
            log(f"✗ Ошибка конвертации: {os.path.basename(input_path)}", "error")
            if os.path.exists(output_path):
                try: os.remove(output_path)
                except: pass
            return False
    except Exception as e:
        log(f"  Ошибка конвертации в H264: {e}", "warn")
        if os.path.exists(output_path):
            try: os.remove(output_path)
            except: pass
        return False


def run_h264_conversion():
    """Конвертирует все файлы из списка ожидания."""
    global files_to_convert_pending
    if not files_to_convert_pending:
        return

    total = len(files_to_convert_pending)
    log(f"🔄 Начинаю перекодировку {total} файлов в H264...", "info")

    for i, item in enumerate(files_to_convert_pending):
        log(f"[{i+1}/{total}] Кодек {item['codec']} → H264", "info")
        convert_to_h264(item["path"])

    files_to_convert_pending = []
    log("✅ Перекодировка завершена!", "done")
    message_queue.put(json.dumps({"type": "convert_done", "text": "finished"}, ensure_ascii=False))
    play_backend_done_sound()

# ================================================


# --- УЛУЧШЕННЫЕ ФУНКЦИИ ДЛЯ СКАЧИВАНИЯ МУЗЫКИ ---

def get_music_metadata_via_ytdlp(url):
    """
    Запрашивает у самого yt-dlp точные теги исполнителя и трека.
    """
    try:
        if not os.path.exists(YTDLP_PATH):
            return None
            
        cmd = [
            YTDLP_PATH,
            "--skip-download",
            "--no-playlist",
            "--no-warnings",
            "--print", "%(artist)s - %(title)s",
            url
        ]
        
        proc = subprocess.run(
            cmd,
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15
        )
        
        output = str(proc.stdout or "").strip()
        if output and "NA" not in output and len(output) > 3:
            return output
    except Exception:
        pass
    return None


def get_music_metadata(url):
    """
    Резервный HTML-парсер, если yt-dlp API не сработал.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8"
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            html_raw = response.read()
            
        try:
            html_text = gzip.decompress(html_raw).decode("utf-8", errors="replace")
        except Exception:
            html_text = html_raw.decode("utf-8", errors="replace")
            
        html_text = html.unescape(html_text)

        # Для Spotify
        if "spotify.com" in url:
            title_match = re.search(r'<meta property="og:title" content="([^"]+)"', html_text)
            artist_match = re.search(r'<meta property="twitter:attr:author" content="([^"]+)"', html_text)
            if not artist_match:
                artist_match = re.search(r'<meta property="og:description" content="([^·]+)·', html_text)
            
            if title_match:
                title = title_match.group(1)
                artist = artist_match.group(1).strip() if artist_match else ""
                return f"{artist} - {title}".strip(" -")

        # Для Apple Music
        elif "music.apple.com" in url:
            title_match = re.search(r'<meta property="og:title" content="([^"]+)"', html_text)
            if title_match:
                title = title_match.group(1).split(" by ")[0].split(" - ")[0]
                return title

        # Для Яндекс Музыки
        elif "music.yandex" in url:
            title_match = re.search(r'<meta property="og:title" content="([^"]+)"', html_text)
            if title_match:
                raw_title = title_match.group(1)
                raw_title = raw_title.replace("Слушать на Яндекс Музыке", "")
                raw_title = raw_title.replace("Слушать онлайн на Яндекс Музыке", "")
                raw_title = raw_title.replace("на Яндекс Музыке", "")
                raw_title = raw_title.replace("«", "").replace("»", "").replace('"', '').strip()
                return raw_title

    except Exception as e:
        log(f"  Ошибка получения HTML-метаданных музыки: {e}", "warn")
    return None


def download_youtube(job, download_dir, fmt, segment_duration, max_duration):
    url = job["url"]
    start_time_job = job.get("startTime")
    is_live = job.get("isLive", False)
    copy_index = job.get("copyIndex", 1)

    is_mp3 = (fmt == "bestaudio-mp3")
    use_fmt = "bestaudio/best" if is_mp3 else fmt
    

    is_search = url.startswith("ytsearch:") or url.startswith("ytsearch1:")
    
    settings = load_app_settings()
    use_real_names = str(settings.get("useRealNames", "true")).lower() == "true"

    if use_real_names:
        if is_search:
            search_query = url.replace("ytsearch1:", "").replace("ytsearch:", "")
            log(f"  Ищу трек на YouTube: {search_query}", "info")
            out_tmpl = os.path.join(download_dir, f"{get_safe_filename(search_query)}{get_copy_suffix(copy_index)}.%(ext)s")
        else:
            if start_time_job is not None:
                title_tail = f"_{start_time_job}s"
            else:
                title_tail = ""
            copy_suffix = get_ytdlp_collision_suffix(download_dir, url, copy_index, title_tail)
            out_tmpl = os.path.join(download_dir, f"%(title)s{copy_suffix}.%(ext)s")
    else:
        log("  Использую классическое числовое имя (597)...", "info")
        out_tmpl = get_numeric_out_tmpl(download_dir, start_time_job)

    cmd = [
        YTDLP_PATH,
        "--format", use_fmt,
        "--output", out_tmpl,
        "--no-playlist",
        "--newline",
        "--no-warnings",                 # <--- ОБЯЗАТЕЛЬНО ЗАПЯТАЯ ЗДЕСЬ
        "--concurrent-fragments", "10"   # <--- НАШ ТУРБО РЕЖИМ
    ]

        
    # Внедряем JS Runtime (Deno или Node.js)
    cmd += get_youtube_extra_args()

    if is_mp3:
        cmd += [
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "0"
        ]

    if FFMPEG_PATH:
        cmd += ["--ffmpeg-location", os.path.dirname(FFMPEG_PATH)]

    if max_duration > 0 and not is_search:
        cmd += ["--download-sections", f"*0-{max_duration}"]

    if start_time_job is not None and not is_search:
        end_time = start_time_job + segment_duration
        if is_live:
            cmd += [
                "--downloader", "ffmpeg",
                "--downloader-args", f"ffmpeg_i:-ss {start_time_job} -t {segment_duration}",
            ]
        else:
            cmd += [
                "--download-sections", f"*{start_time_job}-{end_time}",
                "--force-keyframes-at-cuts",
            ]

    cmd.append(url)

    code, actual_file = run_process(cmd, BASE_DIR, " ")

    if code == 0:
        if actual_file != "Видео" and actual_file != "Video":
            if is_mp3:
                actual_file = os.path.splitext(actual_file)[0] + ".mp3"
            
            log(f"✓ Готово: {os.path.basename(actual_file)}", "ok")
        else:
            log("✓ Готово: Загрузка завершена", "ok")
        return True, actual_file

    log(f"✗ Ошибка YouTube/Поиска, код {code}", "error")
    
    # --- СОЗДАНИЕ ПУСТОГО ФАЙЛА-МАРКЕРА ПРИ ОШИБКЕ ---
    if not use_real_names:
        marker_ext = ".mp3" if is_mp3 else ".mp4"
        marker_path = out_tmpl.replace(".%(ext)s", marker_ext)
        try:
            open(marker_path, "w").close()
            log(f"  Создан пустой файл-маркер: {os.path.basename(marker_path)}", "warn")
        except Exception:
            pass
    # -------------------------------------------------

    return False, ""


def download_generic(platform, url, download_dir, fmt, max_duration=0, copy_index=1):
    # ==== ПЕРЕХВАТ И АВТОМАТИЧЕСКАЯ УСТАНОВКА MP3 ДЛЯ МУЗЫКАЛЬНЫХ САЙТОВ ====
    music_domains = ["spotify.com", "music.apple.com", "music.yandex", "soundcloud.com", "bandcamp.com", "mixcloud.com"]
    is_music_platform = any(x in url.lower() for x in music_domains) or platform in ["soundcloud", "yandexmusic", "bandcamp", "mixcloud", "applemusic", "spotify"]

    if is_music_platform:
        fmt = "bestaudio-mp3"  # Принудительно выставляем MP3

    # ПЕРЕХВАТ ЗАЩИЩЕННОЙ МУЗЫКИ (Spotify, Apple Music, Yandex Music)
    if any(x in url for x in ["spotify.com", "music.apple.com", "music.yandex"]):
        log(f"  Обнаружен защищенный сервис ({platform}). Активирую обход защиты...", "warn")
        
        meta = get_music_metadata_via_ytdlp(url)
        if not meta:
            meta = get_music_metadata(url)
            
        if meta:
            log(f"  Найдено точное название: {meta}", "ok")
            search_job = {
                "url": f"ytsearch1:{meta}",
                "copyIndex": copy_index
            }
            return download_youtube(search_job, download_dir, "bestaudio-mp3", 12, 0)
        else:
            log("  Не удалось извлечь точное название. Пробую стандартное скачивание...", "warn")

    platform_clean = str(platform or "").replace("generic_", "")

    settings = load_app_settings()
    use_real_names = str(settings.get("useRealNames", "true")).lower() == "true"

    if use_real_names:
        copy_suffix = get_ytdlp_collision_suffix(
            download_dir=download_dir,
            url=url,
            requested_index=copy_index,
            title_tail="",
        )
        out_tmpl = os.path.join(download_dir, f"%(title)s{copy_suffix}.%(ext)s")

        if copy_suffix:
            log(f"  Повторная/похожая ссылка {platform_clean}: сохраняю с суффиксом{copy_suffix}", "warn")
    else:
        out_tmpl = get_numeric_out_tmpl(download_dir)

    is_mp3 = (fmt == "bestaudio-mp3")
    use_fmt = "best[ext=mp4]/best" if platform_clean in ["instagram", "tiktok", "douyin"] else ("bestaudio/best" if is_mp3 else fmt)

    cmd = [
        YTDLP_PATH,
        "--format", use_fmt,
        "--output", out_tmpl,
        "--no-warnings",                 # <--- ОБЯЗАТЕЛЬНО ЗАПЯТАЯ ЗДЕСЬ
        "--concurrent-fragments", "10"   # <--- НАШ ТУРБО РЕЖИМ
        ]

   
        
    if is_mp3:
        cmd += ["--extract-audio", "--audio-format", "mp3", "--audio-quality", "0"]

    if FFMPEG_PATH:
        cmd += ["--ffmpeg-location", os.path.dirname(FFMPEG_PATH)]

    if max_duration > 0:
        cmd += ["--download-sections", f"*0-{max_duration}"]

    cmd.append(url)

    code, actual_file = run_process(cmd, BASE_DIR, " ")

    if code == 0:
        if actual_file not in ["Видео", "Video"]:
            if is_mp3:
                actual_file = os.path.splitext(actual_file)[0] + ".mp3"
            log(f"✓ Готово: {os.path.basename(actual_file)}", "ok")
                    
            log(f"✓ Готово: {os.path.basename(actual_file)}", "ok")
        else:
            log("✓ Готово: Загрузка завершена", "ok")
        return True, actual_file

    log(f"✗ Ошибка платформы {platform_clean}, код {code}", "error")
    return False, ""  # <--- Добавили пустую строку


# === ВСТРОЕННЫЙ ЗАГРУЗЧИК ДЛЯ ПРЯМЫХ ССЫЛОК (БЕЗ ОШИБОК yt-dlp) ===
def download_direct_link(url, download_dir, copy_index, is_mp3):
    # --- ХИТРОСТЬ ДЛЯ PIXABAY ---
    if "pixabay.com/videos/download/" in url:
        m = re.search(r'-(\d+)', url)
        if m:
            video_id = m.group(1)
            log(f"  Pixabay обнаружен. Активируем внутренний API yt-dlp для ID {video_id}...", "info")
            
            ext = ".mp3" if is_mp3 else ".mp4"
            settings = load_app_settings()
            use_real_names = str(settings.get("useRealNames", "true")).lower() == "true"
            
            if use_real_names:
                base_name = f"pixabay_{video_id}"
            else:
                base_name = f"{video_id}-pxb"
                
            file_path = get_unique_filepath(download_dir, base_name + get_copy_suffix(copy_index), ext)
            yt_exe = globals().get('YT_DLP_PATH', 'yt-dlp')
            
            # Тот самый трюк: генерируем ссылку, которая 100% включит официальный плагин Pixabay в yt-dlp
            fake_page_url = f"https://pixabay.com/videos/a-{video_id}/"
            
            cmd = [
                yt_exe,
                "--extractor-args", "generic:impersonate",
                "--no-warnings",
                "-f", "bestaudio" if is_mp3 else "b",
                "-o", file_path,
                fake_page_url
            ]
            
            code, _ = run_process(cmd, BASE_DIR, " ")
            
            # Проверяем итог (файл должен быть больше 100 КБ)
            if code == 0 and os.path.exists(file_path) and os.path.getsize(file_path) > 100_000:
                if is_mp3 and not file_path.endswith(".mp3"):
                    log("  Конвертирую в MP3...", "info")
                    file_path = convert_to_mp3(file_path)
                size_mb = os.path.getsize(file_path) / (1024 * 1024)
                log(f"✓ Готово (Pixabay API): {os.path.basename(file_path)} ({size_mb:.1f}MB)", "ok")
                return True
            else:
                log("✗ Ошибка скачивания. Пробуем скачать прямую ссылку...", "warn")
                if os.path.exists(file_path):
                    try: os.remove(file_path)
                    except: pass
                
                # Запасной вариант - качаем саму прямую ссылку
                cmd_direct = [
                    yt_exe,
                    "--extractor-args", "generic:impersonate",
                    "--add-header", "Referer: https://pixabay.com/",
                    "--no-warnings",
                    "-o", file_path,
                    url
                ]
                code_direct, _ = run_process(cmd_direct, BASE_DIR, " ")
                
                if code_direct == 0 and os.path.exists(file_path) and os.path.getsize(file_path) > 100_000:
                    size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    log(f"✓ Готово (Прямая ссылка): {os.path.basename(file_path)} ({size_mb:.1f}MB)", "ok")
                    return True
                else:
                    log("✗ Не удалось пробить защиту Pixabay.", "error")
                    if os.path.exists(file_path):
                        try: os.remove(file_path)
                        except: pass
                    return False
    
    # -----------------------------------------------------------

    log("  Запускаю прямое скачивание файла...", "info")
    
    parsed_orig = urllib.parse.urlparse(url)
    # Убираем слеш на конце, чтобы правильно прочитать ID, если ссылка кончается на .../6130312/
    clean_path = parsed_orig.path.rstrip('/')
    filename = os.path.basename(clean_path)
    
    ext = ".mp4"
    
    # Ищем, не прямая ли это ссылка Pexels
    m_pexels = re.search(r'pexels\.com/.*/video/(\d+)', url)
    m_ext = re.search(r'\.(mp4|mp3|m4a|webm|wav|ogg|avi|mov|mkv)', filename, re.IGNORECASE)
    
    settings = load_app_settings()
    use_real_names = str(settings.get("useRealNames", "true")).lower() == "true"

    if m_pexels:
        video_id = m_pexels.group(1)
        base_name = f"pexels_{video_id}" if use_real_names else f"{video_id}-pxl"
    elif m_ext:
        ext = m_ext.group(0).lower()
        base_name = urllib.parse.unquote(filename[:m_ext.start()])
    elif filename.isdigit():
        # Если в конце неизвестной ссылки просто ID (например 12345)
        base_name = filename
    else:
        base_name = f"dl_{int(time.time())}"
        
    base_name = get_safe_filename(base_name) or f"dl_{int(time.time())}"
    copy_suffix = get_copy_suffix(copy_index)
    file_path = get_unique_filepath(download_dir, base_name + copy_suffix, ext)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "*/*"
    }

    success = False

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            total_size = int(resp.headers.get('content-length', 0))
            
            with open(file_path, "wb") as f:
                downloaded = 0
                start_t = time.monotonic()
                last_update = start_t
                
                while True:
                    if cancel_requested:
                        break
                    chunk = resp.read(1024 * 128)
                    if not chunk: break
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    now = time.monotonic()
                    if now - last_update > 0.5:
                        elapsed = now - start_t
                        speed = downloaded / elapsed if elapsed > 0 else 0
                        percent = (downloaded / total_size * 100) if total_size > 0 else 0
                        eta = (total_size - downloaded) / speed if speed > 0 and total_size > 0 else 0
                        _bd_emit_progress(percent, downloaded, total_size, speed, eta, elapsed, "downloading")
                        last_update = now
                        
        if cancel_requested:
            try: os.remove(file_path)
            except: pass
            return False

        _bd_emit_progress(100, downloaded, total_size, 0, 0, time.monotonic() - start_t, "finished")
        success = True
        
    except Exception as e:
        log(f"  Стандартный метод заблокирован ({e}). Пробую жёсткое скачивание (curl)...", "warn")
        
        try:
            cmd_curl = [
                "curl", "-L",
                "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "-o", file_path,
                url
            ]
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            proc = subprocess.Popen(cmd_curl, startupinfo=startupinfo, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            proc.communicate()
            
            if proc.returncode == 0 and os.path.exists(file_path) and os.path.getsize(file_path) > 100_000:
                success = True
            else:
                log("  curl скачал заглушку защиты. Пробую FFmpeg...", "warn")
                ffmpeg_exe = globals().get('FFMPEG_PATH', 'ffmpeg')
                if ffmpeg_exe:
                    cmd_ffmpeg = [
                        ffmpeg_exe, "-y",
                        "-user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                        "-i", url, "-c", "copy", file_path
                    ]
                    code, _ = run_process(cmd_ffmpeg, BASE_DIR, " ")
                    if code == 0 and os.path.exists(file_path) and os.path.getsize(file_path) > 100_000:
                        success = True
        except Exception as backup_err:
            log(f"  Ошибка резервных методов: {backup_err}", "error")

    if success:
        if is_mp3 and not file_path.endswith(".mp3"):
            log("  Конвертирую в MP3...", "info")
            file_path = convert_to_mp3(file_path)
            
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        log(f"✓ Готово: {os.path.basename(file_path)} ({size_mb:.1f}MB)", "ok")
        return True, file_path
    else:
        log("✗ Не удалось скачать файл (Сервер полностью заблокировал доступ)", "error")
        
        # --- СОЗДАНИЕ ПУСТОГО ФАЙЛА-МАРКЕРА ПРИ ОШИБКЕ ---
        if not use_real_names:
            try:
                open(file_path, "w").close()
                log(f"  Создан пустой файл-маркер: {os.path.basename(file_path)}", "warn")
            except Exception:
                pass
        else:
            if os.path.exists(file_path):
                try: os.remove(file_path)
                except: pass
        # -------------------------------------------------
        return False, ""

def download_pinterest(url, download_dir, copy_index=1, is_mp3=False):
    log("  Pinterest: извлекаю ссылку на видео...", "info")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "DNT": "1",
        "Connection": "keep-alive",
    }

    original_url = url

    if "pin.it" in url:
        try:
            req0 = urllib.request.Request(url, headers=headers)
            req0.get_method = lambda: "HEAD"

            with urllib.request.urlopen(req0, timeout=10) as r:
                url = r.url

            log(f"  Redirect -> {url}", "info")
        except Exception:
            pass

    video_url = None
    base_name = f"pin_{int(time.time())}"

    try:
        req = urllib.request.Request(url, headers=headers)

        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()

        try:
            html_text = gzip.decompress(raw).decode("utf-8", errors="replace")
        except Exception:
            html_text = raw.decode("utf-8", errors="replace")

        title_match = re.search(r"<title>(.*?)</title>", html_text, re.IGNORECASE)

        if title_match:
            raw_title = title_match.group(1).split("|")[0].strip()
            clean_title = get_safe_filename(raw_title)

            if clean_title:
                base_name = clean_title

        mp4_patterns = [
            r'"(https://v(?:1|2)?\.pinimg\.com/[^"\']+?\.mp4(?:\?[^"\']*)?)"',
            r'(https://v\.pinimg\.com/videos/[^"\'<>\s]+\.mp4(?:\?[^"\'<>\s]*)?)',
        ]

        for pat in mp4_patterns:
            matches = re.findall(pat, html_text)

            if matches:
                def _res(u):
                    m = re.search(r"(\d{3,4})p", u)
                    return int(m.group(1)) if m else 0

                matches.sort(key=_res, reverse=True)
                video_url = matches[0].replace("\\/", "/")
                log(f"  Найден mp4: {video_url[:80]}...", "info")
                break

        if not video_url:
            m3u8_patterns = [
                r'"(https://v(?:1|2)?\.pinimg\.com/[^"\']+?\.m3u8(?:\?[^"\']*)?)"',
            ]

            for pat in m3u8_patterns:
                matches = re.findall(pat, html_text)

                if matches:
                    video_url = matches[0].replace("\\/", "/")
                    log(f"  Найден m3u8: {video_url[:80]}...", "info")
                    break

        if not video_url:
            json_blocks = re.findall(
                r'<script[^>]*id="__(?:PWS_DATA|NEXT_DATA|PWS_INITIAL_STATE)__"[^>]*>'
                r"([^<]{100,})</script>",
                html_text,
                re.DOTALL,
            )

            for block in json_blocks:
                block = re.sub(r"^[^{]*", "", block).strip()

                try:
                    obj = json.loads(block)
                    text_block = json.dumps(obj)
                except Exception:
                    text_block = block

                for pat in [
                    r'"(https://v[^"]+?\.mp4[^"]*)"',
                    r'"(https://v[^"]+?\.m3u8[^"]*)"',
                ]:
                    found = re.findall(pat, text_block)

                    if found:
                        video_url = found[0].replace("\\/", "/")
                        log(f"  Найдено в JSON: {video_url[:80]}...", "info")
                        break

                if video_url:
                    break

    except Exception as e:
        log(f"  Ошибка при скрапинге страницы: {e}", "warn")

    if video_url:
        copy_suffix = get_copy_suffix(copy_index)

        if copy_suffix:
            log(f"  Повторная/похожая ссылка Pinterest: сохраняю с суффиксом{copy_suffix}", "warn")
            base_name = f"{base_name}{copy_suffix}"

        file_path = get_unique_filepath(download_dir, base_name, ".mp4")

        if ".m3u8" in video_url:
            if FFMPEG_PATH:
                log("  Скачиваю через ffmpeg (m3u8)...", "info")

                cmd = [
                    FFMPEG_PATH,
                    "-y",
                    "-i",
                    video_url,
                    "-c",
                    "copy",
                    "-bsf:a",
                    "aac_adtstoasc",
                    file_path,
                ]

                try:
                    proc = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                    )

                    for line in proc.stdout:
                        line = line.rstrip()

                        if line and ("frame=" in line or "error" in line.lower()):
                            log(f"  {line}", "cmd")

                    proc.wait()

                    if proc.returncode == 0 and os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                        if is_mp3:
                            log("  Извлекаю MP3 из Pinterest m3u8...", "info")
                            file_path = convert_to_mp3(file_path)
                        size_mb = os.path.getsize(file_path) / (1024 * 1024)
                        log(f"✓ Готово: {os.path.basename(file_path)} ({size_mb:.1f}MB)", "ok")
                        return True, file_path

                    log("  ffmpeg завершился с ошибкой, пробую yt-dlp...", "warn")
                except Exception as e:
                    log(f"  ffmpeg исключение: {e}, пробую yt-dlp...", "warn")
            else:
                log("  ffmpeg не найден для скачивания m3u8, пробую yt-dlp...", "warn")
        else:
            log("  Скачиваю mp4 напрямую...", "info")

            try:
                req2 = urllib.request.Request(video_url, headers=headers)

                with urllib.request.urlopen(req2, timeout=60) as resp2:
                    with open(file_path, "wb") as f:
                        while True:
                            chunk = resp2.read(65536)

                            if not chunk:
                                break

                            f.write(chunk)

                if is_mp3:
                    log("  Извлекаю MP3 из Pinterest mp4...", "info")
                    file_path = convert_to_mp3(file_path)

                size_mb = os.path.getsize(file_path) / (1024 * 1024)
                log(f"✓ Готово: {os.path.basename(file_path)} ({size_mb:.1f}MB)", "ok")
                return True, file_path
            except Exception as e:
                log(f"  Ошибка прямого скачивания: {e}, пробую yt-dlp...", "warn")

    log("  Пробую yt-dlp (формат: best)...", "info")

    copy_suffix = get_ytdlp_collision_suffix(
        download_dir=download_dir,
        url=url or original_url,
        requested_index=copy_index,
        title_tail="",
    )

    out_tmpl = os.path.join(download_dir, f"%(title)s{copy_suffix}.%(ext)s")

    if copy_suffix:
        log(f"  Повторная/похожая ссылка Pinterest: сохраняю с суффиксом{copy_suffix}", "warn")

    cmd = [
        YTDLP_PATH,
        "--format",
        "bestaudio/best" if is_mp3 else "best",
        "--output",
        out_tmpl,
        "--no-playlist",
    ]

    if is_mp3:
        cmd += [
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "0"
        ]

    if FFMPEG_PATH:
        cmd += ["--ffmpeg-location", os.path.dirname(FFMPEG_PATH)]

    cmd.append(url or original_url)

    code, actual_file = run_process(cmd, BASE_DIR, "  ")

    if code == 0:
        if actual_file != "Video" and actual_file != "Видео":
            if is_mp3:
                actual_file = os.path.splitext(actual_file)[0] + ".mp3"
            log(f"✓ Готово: {os.path.basename(actual_file)}", "ok")
        else:
            log("✓ Готово: Загрузка завершена", "ok")
        return True, actual_file  # <--- Исправлено

    log(f"✗ yt-dlp Pinterest, код {code}", "error")
    log("  Pinterest: video не удалось скачать автоматически.", "warn")
    return False, ""  # <--- Исправлено


def download_pixabay(url, download_dir, copy_index=1, is_mp3=False):
    try:
        m = re.search(r"-(\d+)/?$", url)

        if not m:
            m = re.search(r"videos/(?:[^/]+-)?(\d+)", url)

        if not m:
            log("Не удалось извлечь ID Pixabay", "error")
            return False, ""

        video_id = m.group(1)

        api_url = f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&id={video_id}"
        req = urllib.request.Request(api_url, headers={"User-Agent": "VideoDownloader/1.0"})

        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))

        if not data.get("hits"):
            log("Pixabay: video не найдено", "error")
            return False, ""

        video_info = data["hits"][0]
        videos = video_info.get("videos", {})

        video_url = None

        for q in ["large", "medium", "small", "tiny"]:
            if videos.get(q, {}).get("url"):
                video_url = videos[q]["url"]
                break

        if not video_url:
            log("Pixabay: нет файлов", "error")
            return False, ""

        settings = load_app_settings()
        use_real_names = str(settings.get("useRealNames", "true")).lower() == "true"

        if use_real_names:
            tags = video_info.get("tags", "")
            if tags:
                clean_name = get_safe_filename(tags.replace(", ", "_").replace(" ", "_"))
                base_name = f"pixabay_{clean_name}"
            else:
                base_name = f"pixabay_{video_info.get('id', video_id)}"
        else:
            base_name = f"{video_info.get('id', video_id)}-pxb"

        file_path = get_unique_filepath(download_dir, base_name, ".mp4")

        req2 = urllib.request.Request(video_url, headers={"User-Agent": "VideoDownloader/1.0"})

        with urllib.request.urlopen(req2, timeout=60) as resp2:
            with open(file_path, "wb") as f:
                while True:
                    chunk = resp2.read(65536)

                    if not chunk:
                        break

                    f.write(chunk)

        if is_mp3:
            log("  Извлекаю MP3 из Pixabay...", "info")
            file_path = convert_to_mp3(file_path)

        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        log(f"✓ Готово: {os.path.basename(file_path)} ({size_mb:.1f}MB)", "ok")
        return True, file_path  # <--- Исправлено

    except Exception as e:
        log(f"✗ Ошибка API: {e}", "error")
        
        try:
            settings = load_app_settings()
            use_real_names = str(settings.get("useRealNames", "true")).lower() == "true"
            if not use_real_names and 'file_path' in locals():
                open(file_path, "w").close()
                log(f"  Создан пустой файл-маркер: {os.path.basename(file_path)}", "warn")
        except Exception:
            pass
        
        return False, ""  # <--- Исправлено


def download_pexels(url, download_dir, copy_index=1, is_mp3=False):
    try:
        m = re.search(r"video/[^/]+-(\d+)/?$", url)

        if not m:
            m = re.search(r"/(\d+)/?$", url)

        if not m:
            log("Не удалось извлечь ID Pexels", "error")
            return False, ""

        video_id = m.group(1)

        api_url = f"https://api.pexels.com/videos/videos/{video_id}"
        req = urllib.request.Request(
            api_url,
            headers={
                "Authorization": PEXELS_API_KEY,
                "User-Agent": "VideoDownloader/1.0",
            },
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            info = json.loads(resp.read().decode("utf-8", errors="replace"))

        video_files = info.get("video_files", [])

        if not video_files:
            log("Pexels: нет файлов", "error")
            return False, ""

        best = sorted(video_files, key=lambda x: x.get("width", 0), reverse=True)[0]
        video_url = best["link"]

        settings = load_app_settings()
        use_real_names = str(settings.get("useRealNames", "true")).lower() == "true"

        if use_real_names:
            url_path = info.get("url", "")
            m_slug = re.search(r"/video/([^/]+)-\d+/?", url_path)
            if m_slug:
                clean_name = get_safe_filename(m_slug.group(1).replace("-", "_"))
                base_name = f"pexels_{clean_name}"
            else:
                base_name = f"pexels_{info.get('id', video_id)}"
        else:
            base_name = f"{info.get('id', video_id)}-pxl"

        file_path = get_unique_filepath(download_dir, base_name, ".mp4")

        req2 = urllib.request.Request(
            video_url,
            headers={
                "Authorization": PEXELS_API_KEY,
                "User-Agent": "VideoDownloader/1.0",
            },
        )

        with urllib.request.urlopen(req2, timeout=60) as resp2:
            with open(file_path, "wb") as f:
                while True:
                    chunk = resp2.read(65536)

                    if not chunk:
                        break

                    f.write(chunk)

        if is_mp3:
            log("  Извлекаю MP3 из Pexels...", "info")
            file_path = convert_to_mp3(file_path)

        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        log(f"✓ Готово: {os.path.basename(file_path)} ({size_mb:.1f}MB)", "ok")
        return True, file_path  # <--- Исправлено

    except Exception as e:
        log(f"✗ Pexels: {e}", "error")
        return False, ""  # <--- Исправлено


def run_downloads(jobs, settings):
    global is_running, start_time, FFMPEG_PATH, cancel_requested
    
    is_running = True
    cancel_requested = False # Сбрасываем перед новым запуском
    start_time = time.time()

    try:
        segment_duration = int(settings.get("segmentDuration", 12) or 12)
        max_duration = int(settings.get("maxDuration", 0) or 0)

        fmt = settings.get(
            "format",
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        )

        is_mp3 = (fmt == "bestaudio-mp3")

        directory = settings.get("directory", DEFAULT_APP_SETTINGS["directory"]) or DEFAULT_APP_SETTINGS["directory"]

        save_app_settings(
            {
                "directory": directory,
                "format": fmt,
                "segmentDuration": str(segment_duration),
                "maxDuration": str(max_duration) if max_duration > 0 else "",
            }
        )

        download_dir = get_download_dir_from_setting(directory)

        # 1. Готовим yt-dlp
        if not download_ytdlp():
            log("Не удалось подготовить yt-dlp", "error")
            message_queue.put(json.dumps({"type": "done", "text": "error"}, ensure_ascii=False))
            return

        # 2. Готовим автономный Deno в папке tools
        if not download_deno():
            log("Портативный Deno установить не удалось. Пробую резервный Node.js...", "warn")
            if not download_node():
                log("Резервные JS-рантаймы отсутствуют. YouTube-загрузки без рантайма могут дать сбой.", "warn")

        # 3. Готовим FFmpeg
        ff = _find_ffmpeg()
        if not ff:
            if not download_ffmpeg():
                log("ffmpeg не найден, продолжаю без него (склейка и MP3 могут не работать)", "warn")
            else:
                ff = _find_ffmpeg()

        FFMPEG_PATH = ff if ff else None

        os.makedirs(download_dir, exist_ok=True)

        log(f"Папка: {download_dir}", "info")

        if FFMPEG_PATH:
            log(f"ffmpeg: {FFMPEG_PATH}", "ok")
        else:
            log("ffmpeg: не найден", "warn")

        if max_duration > 0:
            log(f"Макс. длительность: {format_time(max_duration)}", "info")

        total = len(jobs)

        YTDLP_NAME_REGISTRY.clear()
        downloaded_files_session.clear()  # <-- Очищаем список файлов сессии

        log(f"Загрузка {total} медиа", "info")
        log("─" * 50, "sep")

        for i, job in enumerate(jobs):
            if cancel_requested:
                log("🛑 Загрузка прервана пользователем!", "error")
                break # Выходим из цикла очереди
                
            # === НОВЫЙ БЛОК: ПРОПУСК УЖЕ СКАЧАННОГО ===
            if job.get("skip"):
                log(f"\n[{i + 1}/{total}] ПРОПУСК (Уже скачано ранее)", "ok")
                job_done(job.get("platform", "generic"), True, i)
                continue
            # ==========================================
            
            job_type = job.get("type", "youtube")
            platform = job.get("platform") or job_type.replace("generic_", "")
            url = job.get("url", "")
            copy_index = job.get("copyIndex", 1)

            elapsed = time.time() - start_time

            if i > 0:
                remaining_est = elapsed * (total - i) / i
            else:
                remaining_est = 0

            log(
                f"\n[{i + 1}/{total}] {job_type.upper()} | Прошло: {format_time(elapsed)} | Осталось: {format_time(remaining_est)}",
                "info",
            )
            log(url, "url")

            ok = False

          
            if job_type == "pixabay":
                ok, downloaded_file = download_pixabay(url, download_dir, copy_index, is_mp3)
            elif job_type == "pexels":
                ok, downloaded_file = download_pexels(url, download_dir, copy_index, is_mp3)
            elif job_type == "pinterest" or "pinterest.com" in url or "pin.it" in url:
                ok, downloaded_file = download_pinterest(url, download_dir, copy_index, is_mp3)
            elif job_type == "youtube":
                ok, downloaded_file = download_youtube(job, download_dir, fmt, segment_duration, max_duration)
            elif platform == "direct":
                ok, downloaded_file = download_direct_link(url, download_dir, copy_index, is_mp3)
            else:
                ok, downloaded_file = download_generic(platform, url, download_dir, fmt, max_duration, copy_index)

            # Если путь не абсолютный, делаем его абсолютным
            if downloaded_file and not os.path.isabs(downloaded_file):
                downloaded_file = os.path.join(download_dir, downloaded_file)

            job_done(platform, ok, i, downloaded_file)

        elapsed_total = time.time() - start_time

        log("\n" + "=" * 50, "sep")
        log(f"✓ Завершено: {total} элементов", "done")
        log(f"⏱ Потрачено: {format_time(elapsed_total)}", "info")
        log(f"📁 {download_dir}", "info")

        

        # Воспроизводим системный звук
        play_backend_done_sound()

        message_queue.put(json.dumps({"type": "done", "text": "finished"}, ensure_ascii=False))

    except Exception as e:
        log(f"Критическая ошибка: {e}", "error")
        message_queue.put(json.dumps({"type": "done", "text": "error"}, ensure_ascii=False))
    finally:
        is_running = False


def browse_for_folder(initial_dir=None):
    initial_dir = get_download_dir_from_setting(initial_dir or DEFAULT_APP_SETTINGS["directory"])

    try:
        os.makedirs(initial_dir, exist_ok=True)
    except Exception:
        initial_dir = os.path.expanduser(os.path.expandvars(DEFAULT_APP_SETTINGS["directory"]))

    if sys.platform == "win32":
        # ПОПЫТКА 1: Открываем мгновенный современный диалог через встроенный tkinter
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw() # Прячем главное окно
            root.attributes('-topmost', True) # Выводим поверх интерфейса программы
            selected = filedialog.askdirectory(initialdir=initial_dir, title="Выберите папку для загрузок")
            root.destroy()
            if selected:
                return os.path.normpath(selected)
            return None
        except Exception:
            pass # Если tkinter вырезан из exe, переходим к запасному варианту (PowerShell)

        # ПОПЫТКА 2: Резервный PowerShell-скрипт (Использует хак с OpenFileDialog для современного вида)
        try:
            ps_initial = initial_dir.replace("'", "''")
            ps_script = f"""
            Add-Type -AssemblyName System.Windows.Forms
            $dialog = New-Object System.Windows.Forms.OpenFileDialog
            $dialog.Title = "Выберите папку для загрузок"
            $dialog.InitialDirectory = '{ps_initial}'
            $dialog.ValidateNames = $false
            $dialog.CheckFileExists = $false
            $dialog.CheckPathExists = $true
            $dialog.FileName = "Выбор_папки"
            $result = $dialog.ShowDialog()
            if ($result -eq [System.Windows.Forms.DialogResult]::OK) {{
                Write-Output ([System.IO.Path]::GetDirectoryName($dialog.FileName))
            }}
            """

            proc = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-STA",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    ps_script,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
            )

            selected = proc.stdout.strip()
            if selected:
                return selected

        except Exception as e:
            log(f"Не удалось открыть системный обзор папок: {e}", "warn")

    # === Код для macOS ===
    if sys.platform == "darwin":
        try:
            script = 'POSIX path of (choose folder with prompt "Выберите папку для загрузок")'

            proc = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
            )

            selected = proc.stdout.strip()

            if selected:
                return selected

        except Exception as e:
            log(f"Не удалось открыть обзор папок macOS: {e}", "warn")

    # === Код для Linux ===
    try:
        proc = subprocess.run(
            [
                "zenity",
                "--file-selection",
                "--directory",
                "--title=Выберите папку для загрузок",
                f"--filename={initial_dir}",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )

        selected = proc.stdout.strip()

        if selected:
            return selected

    except Exception:
        pass

    return None


def read_system_clipboard():
    try:
        if sys.platform == "win32":
            proc = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    "Get-Clipboard -Raw",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=8,
            )

            return proc.stdout or ""

        if sys.platform == "darwin":
            proc = subprocess.run(
                ["pbpaste"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=8,
            )

            return proc.stdout or ""

        for cmd in (["wl-paste"], ["xclip", "-selection", "clipboard", "-o"], ["xsel", "-b", "-o"]):
            try:
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=8,
                )

                if proc.stdout:
                    return proc.stdout
            except Exception:
                pass

    except Exception as e:
        log(f"Не удалось прочитать буфер обмена: {e}", "warn")

    return ""


def normalize_update_url(url):
    url = str(url or "").strip()
    url = url.replace("/tree/main/releases/download/", "/releases/download/")
    url = url.replace("/blob/main/releases/download/", "/releases/download/")
    url = url.replace(" ", "%20")
    return url


def version_tuple(v):
    nums = re.findall(r"\d+", str(v or ""))

    if not nums:
        nums = ["0"]

    nums = [int(x) for x in nums]

    while len(nums) < 3:
        nums.append(0)

    return tuple(nums[:4])


def is_update_available():
    return version_tuple(UPDATE_VERSION) > version_tuple(APP_VERSION)


def format_size_short(num):
    try:
        num = float(num or 0)
    except Exception:
        num = 0

    units = ["Б", "КБ", "МБ", "ГБ"]

    for unit in units:
        if num < 1024:
            return f"{num:.1f} {unit}"
        num /= 1024

    return f"{num:.1f} ТБ"


def fetch_latest_release_info():
    last_error = ""

    api_urls = [
        GITHUB_RELEASES_API,
        GITHUB_RELEASES_TAG_API,
    ]

    for api_url in api_urls:
        try:
            req = urllib.request.Request(
                api_url,
                headers={
                    "User-Agent": "BaikalDownloaderUpdater",
                    "Accept": "application/vnd.github+json",
                },
            )

            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))

            tag_name = str(data.get("tag_name") or "").strip()
            release_name = str(data.get("name") or "").strip()
            html_url = str(data.get("html_url") or "").strip()
            os_assets = data.get("assets") or []

            latest_version = tag_name.lstrip("vV").strip()

            selected_asset = None

            for asset in os_assets:
                name = str(asset.get("name") or "")
                lower_name = name.lower()

                if not lower_name.endswith(".exe"):
                    continue

                if "setup" in lower_name:
                    selected_asset = asset
                    break

            if selected_asset is None:
                needle = str(UPDATE_ASSET_NAME_CONTAINS or "").lower()

                for asset in os_assets:
                    name = str(asset.get("name") or "")
                    lower_name = name.lower()

                    if not lower_name.endswith(".exe"):
                        continue

                    if needle and needle in lower_name:
                        selected_asset = asset
                        break

            if selected_asset is None:
                for asset in os_assets:
                    name = str(asset.get("name") or "")

                    if name.lower().endswith(".exe"):
                        selected_asset = asset
                        break

            if selected_asset is None:
                return {
                    "ok": False,
                    "error": "В GitHub Release не найден .exe файл в Assets. Нужен Setup-инсталлятор.",
                    "tag_name": tag_name,
                    "release_name": release_name,
                    "html_url": html_url,
                }

            asset_name = str(selected_asset.get("name") or "").strip()
            download_url = str(selected_asset.get("browser_download_url") or "").strip()
            size = int(selected_asset.get("size") or 0)

            if not latest_version:
                latest_version = UPDATE_VERSION

            return {
                "ok": True,
                "tag_name": tag_name,
                "release_name": release_name,
                "latest_version": latest_version,
                "asset_name": asset_name,
                "download_url": download_url,
                "size": size,
                "size_text": format_size_short(size) if size else "неизвестно",
                "html_url": html_url,
                "api_url": api_url,
            }

        except Exception as e:
            last_error = f"{api_url}: {e}"

    return {
        "ok": False,
        "error": f"Не удалось получить данные GitHub Release: {last_error}",
    }


def find_github_release_exe_asset(release_info):
    assets = release_info.get("assets") or []

    if not isinstance(assets, list):
        return None

    exe_assets = []

    for asset in assets:
        if not isinstance(asset, dict):
            continue

        name = str(asset.get("name") or "").strip()
        url = str(asset.get("browser_download_url") or "").strip()

        if not name or not url:
            continue

        if name.lower().endswith(".exe"):
            exe_assets.append({
                "name": name,
                "url": url,
            })

    if not exe_assets:
        return None

    preferred_words = [
        "setup",
        "installer",
        "install",
        "baikal",
        "downloader",
    ]

    for item in exe_assets:
        normalized = item["name"].lower()
        normalized = normalized.replace("_", " ")
        normalized = normalized.replace(".", " ")
        normalized = normalized.replace("-", " ")

        if "setup" in normalized:
            return item

    for item in exe_assets:
        normalized = item["name"].lower()
        normalized = normalized.replace("_", " ")
        normalized = normalized.replace(".", " ")
        normalized = normalized.replace("-", " ")

        if any(word in normalized for word in preferred_words):
            return item

    return exe_assets[0]


def parse_version_to_tuple(version):
    version = str(version or "").strip()
    version = version.lower().lstrip("v")

    parts = []
    current = ""

    for ch in version:
        if ch.isdigit():
            current += ch
        else:
            if current:
                parts.append(int(current))
                current = ""

    if current:
        parts.append(int(current))

    return tuple(parts)


def is_version_newer(new_version, current_version):
    new_tuple = parse_version_to_tuple(new_version)
    current_tuple = parse_version_to_tuple(current_version)

    max_len = max(len(new_tuple), len(current_tuple))

    new_tuple = new_tuple + (0,) * (max_len - len(new_tuple))
    current_tuple = current_tuple + (0,) * (max_len - len(current_tuple))

    return new_tuple > current_tuple


def format_file_size(size):
    try:
        size = int(size)
    except Exception:
        return "неизвестно"

    if size <= 0:
        return "неизвестно"

    units = ["Б", "КБ", "МБ", "ГБ", "ТБ"]
    value = float(size)

    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "Б":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}".replace(".", ",")
        value /= 1024

    return f"{size} Б"


def check_update_info():
    current_version = str(APP_VERSION).strip()

    result_no_update = {
        "ok": True,
        "has_update": False,
        "current_version": current_version,
        "update_version": current_version,
        "url": "",
        "asset_name": "",
        "size": 0,
        "size_text": "неизвестно",
        "source": "github_none",
        "message": "Обновлений нет",
    }

    try:
        req = urllib.request.Request(
            GITHUB_RELEASES_API,
            headers={
                "User-Agent": "BaikalDownloader-Updater",
                "Accept": "application/vnd.github+json",
            },
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))

    except Exception as e:
        result_no_update["source"] = "github_unavailable"
        result_no_update["github_error"] = str(e)
        result_no_update["message"] = "GitHub Release не найден или недоступен"
        return result_no_update

    tag_name = str(data.get("tag_name") or "").strip()
    latest_version = tag_name.lstrip("vV").strip()

    if not latest_version:
        result_no_update["source"] = "github_no_version"
        result_no_update["message"] = "В GitHub Release не указана версия"
        return result_no_update

    asset = None
    assets = data.get("assets") or []

    target_ext = ".dmg" if IS_MAC else ".exe"

    if isinstance(assets, list):
        for item in assets:
            if not isinstance(item, dict):
                continue

            name = str(item.get("name") or "").strip()
            url = str(item.get("browser_download_url") or "").strip()

            if not name or not url:
                continue

            lower_name = name.lower()

            if lower_name.endswith(target_ext):
                if IS_MAC or ("setup" in lower_name):
                    asset = item
                    break

        if asset is None:
            for item in assets:
                if not isinstance(item, dict):
                    continue

                name = str(item.get("name") or "").strip()
                url = str(item.get("browser_download_url") or "").strip()

                if not name or not url:
                    continue

                if name.lower().endswith(target_ext):
                    asset = item
                    break

    if asset is None:
        return {
            "ok": True,
            "has_update": False,
            "current_version": current_version,
            "update_version": latest_version,
            "url": "",
            "asset_name": "",
            "size": 0,
            "size_text": "неизвестно",
            "source": "github_release_without_target",
            "message": f"GitHub Release есть, но файл {target_ext} не найден в Assets",
        }

    asset_name = str(asset.get("name") or "").strip()
    download_url = str(asset.get("browser_download_url") or "").strip()
    size = int(asset.get("size") or 0)

    has_update = is_version_newer(latest_version, current_version)

    return {
        "ok": True,
        "has_update": has_update,
        "current_version": current_version,
        "update_version": latest_version,
        "url": download_url if has_update else "",
        "asset_name": asset_name if has_update else "",
        "size": size if has_update else 0,
        "size_text": format_file_size(size) if has_update and size else "неизвестно",
        "source": "github_latest_release",
        "tag_name": tag_name,
        "html_url": str(data.get("html_url") or ""),
        "message": "Доступно обновление" if has_update else "Установлена актуальная версия",
    }


def download_file_with_progress(url, output_path):
    url = str(url or "").strip()
    output_path = os.path.abspath(output_path)

    if not url:
        raise RuntimeError("Пустая ссылка для скачивания обновления")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    temp_path = output_path + ".download"

    try:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    except Exception:
        pass

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 BaikalDownloader-Updater",
            "Accept": "application/octet-stream,*/*",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            with open(temp_path, "wb") as f:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)

        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception:
                pass

        os.replace(temp_path, output_path)

    except Exception:
        raise
    finally:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass


def get_update_download_dir():
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        path = os.path.join(base, "Baikal Downloader", "download")
    else:
        path = os.path.join(os.path.expanduser("~"), ".baikal_downloader", "download")

    os.makedirs(path, exist_ok=True)
    return path


def launch_installer_gui(installer_path):
    installer_path = os.path.abspath(installer_path)

    if not os.path.exists(installer_path):
        raise FileNotFoundError(installer_path)

    if sys.platform == "win32":
        import ctypes
        result = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            installer_path,
            None,
            os.path.dirname(installer_path),
            1,
        )
        if result <= 32:
            raise RuntimeError(f"Не удалось запустить установщик. ShellExecuteW code: {result}")
        return True

    subprocess.Popen(
        [installer_path],
        cwd=os.path.dirname(installer_path),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    return True


# ==== [MACOS SPECIFIC UPDATE HELPERS] ====

def watch_and_apply_xattr_mac():
    """
    Фоновый поток для macOS. Ждет появления приложения в /Applications 
    и автоматически сбрасывает карантин Gatekeeper.
    """
    target_app = "/Applications/Baikal Downloader.app"
    log("Запущен фоновый мониторинг папки /Applications для авто-снятия карантина...", "info")
    for _ in range(300):
        if os.path.exists(target_app):
            time.sleep(2)
            try:
                subprocess.run(["xattr", "-cr", target_app], check=True)
                log("✓ Обнаружено скопированное вручную приложение! Карантин Gatekeeper снят.", "ok")
                break
            except Exception as e:
                log(f"Не удалось снять Gatekeeper с {target_app}: {e}", "warn")
        time.sleep(2)


def install_mac_dmg(dmg_path):
    """
    Автоматическое монтирование DMG, копирование .app в /Applications,
    выполнение xattr -cr и перезапуск обновленной версии.
    """
    log("Начало обновления macOS из DMG...", "info")
    mount_path = None
    try:
        log("Монтирую диск обновления...", "info")
        proc = subprocess.run(
            ["hdiutil", "mount", dmg_path],
            capture_output=True, text=True, timeout=30, errors="replace"
        )
        
        mount_points = re.findall(r'(/Volumes/[^\n\t]+)', proc.stdout)
        if not mount_points:
            mount_points = [os.path.join("/Volumes", d) for d in os.listdir("/Volumes") if "baikal" in d.lower() or "downloader" in d.lower()]

        if not mount_points:
            raise RuntimeError("Не удалось автоматически определить точку монтирования диска DMG.")

        mount_path = mount_points[0].strip()
        log(f"Диск успешно смонтирован: {mount_path}", "info")

        app_inside = None
        for item in os.listdir(mount_path):
            if item.endswith(".app"):
                app_inside = os.path.join(mount_path, item)
                break

        if not app_inside:
            raise FileNotFoundError("Приложение .app не найдено внутри смонтированного диска DMG.")

        target_app = "/Applications/Baikal Downloader.app"
        log(f"Найдено приложение: {app_inside}. Начинаю копирование в /Applications...", "info")

        if os.path.exists(target_app):
            try:
                shutil.rmtree(target_app)
            except Exception:
                old_path = target_app + ".old"
                if os.path.exists(old_path):
                    shutil.rmtree(old_path, ignore_errors=True)
                os.rename(target_app, old_path)

        subprocess.run(["ditto", app_inside, target_app], check=True)
        log("Копирование успешно завершено!", "ok")

        log("Выполняю снятие карантина Gatekeeper (xattr -cr)...", "info")
        subprocess.run(["xattr", "-cr", target_app], check=True)
        log("✓ Карантин Gatekeeper успешно сброшен!", "ok")

        log("Размонтирую диск DMG...", "info")
        subprocess.run(["hdiutil", "detach", mount_path], capture_output=True)

        log("Запускаю обновленную версию...", "ok")
        subprocess.Popen(["open", target_app])

        threading.Thread(target=lambda: (time.sleep(1), os._exit(0)), daemon=True).start()

        return {
            "ok": True,
            "message": "Обновление успешно завершено! Программа перезапускается...",
            "will_restart": True
        }

    except Exception as e:
        log(f"Авто-установка не удалась: {e}. Перехожу на ручной режим...", "warn")
        
        subprocess.Popen(["open", dmg_path])
        
        threading.Thread(target=watch_and_apply_xattr_mac, daemon=True).start()

        return {
            "ok": True,
            "message": "Открыт диск обновления. Пожалуйста, перетащите иконку Baikal Downloader в папку Программы (Applications). Снятие Gatekeeper произойдет автоматически!",
            "will_restart": False
        }


def install_program_update():
    info = check_update_info()

    if not info.get("ok"):
        return {
            "ok": False,
            "error": info.get("error") or "Не удалось проверить обновление",
            "source": info.get("source"),
        }

    if not info.get("has_update"):
        return {
            "ok": False,
            "error": "Обновление недоступно или не найдено на GitHub",
            "current_version": info.get("current_version"),
            "update_version": info.get("update_version"),
            "source": info.get("source"),
            "message": info.get("message"),
        }

    update_url = str(info.get("url") or "").strip()

    if not update_url:
        if IS_MAC:
            update_url = normalize_update_url(UPDATE_EXE_URL).replace(".exe", ".dmg")
        else:
            update_url = normalize_update_url(UPDATE_EXE_URL)

    lower_url = update_url.lower()

    if "api.github.com/repos/" in lower_url:
        return { "ok": False, "error": "Получена GitHub API ссылка вместо прямой ссылки на инсталлятор" }

    if "/releases/tag/" in lower_url:
        return { "ok": False, "error": "Получена страница релиза вместо прямой ссылки на инсталлятор" }

    asset_name = str(info.get("asset_name") or "").strip()

    if not asset_name:
        version_for_name = str(info.get("update_version") or UPDATE_VERSION).strip()
        ext = ".dmg" if IS_MAC else ".exe"
        asset_name = f"Baikal_Downloader_Setup_{version_for_name}{ext}"

    asset_name = get_safe_filename(asset_name)

    download_dir = get_update_download_dir()
    downloaded_path = os.path.join(download_dir, asset_name)

    download_file_with_progress(update_url, downloaded_path)

    if not os.path.exists(downloaded_path) or os.path.getsize(downloaded_path) <= 0:
        return { "ok": False, "error": "Файл установщика скачан некорректно", "url": update_url }

    if IS_MAC:
        return install_mac_dmg(downloaded_path)

    launch_installer_gui(downloaded_path)

    def delayed_exit():
        try:
            time.sleep(1.0)
            try:
                shutdown_http_server()
            except Exception:
                pass
            time.sleep(0.3)
        finally:
            os._exit(0)

    threading.Thread(target=delayed_exit, daemon=True).start()

    return {
        "ok": True,
        "message": "Обновление скачано. Сейчас откроется установщик.",
        "will_restart": True,
        "path": downloaded_path,
        "url": update_url,
        "asset_name": asset_name,
        "source": info.get("source"),
    }


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        try:
            self._do_GET()
        except Exception as e:
            try:
                self.send_response(500)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self._cors()
                self.end_headers()
                self.wfile.write(str(e).encode("utf-8", errors="replace"))
            except Exception:
                pass

    def _do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self._cors()
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        
        elif parsed.path.startswith("/fonts/"):
            font_name = os.path.basename(parsed.path)
            font_path = os.path.join(FONTS_DIR, font_name)
            
            if os.path.exists(font_path):
                self.send_response(200)
                self.send_header("Content-Type", "font/woff2")
                self.send_header("Cache-Control", "public, max-age=31536000")
                self._cors()
                self.end_headers()
                with open(font_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                # Если шрифт еще не скачался, отдаем 404, интерфейс временно использует системный
                self.send_response(404)
                self.end_headers()
                
        elif parsed.path == "/bkL.png":
            logo_path = os.path.join(BASE_DIR, "bkL.png")
            if not os.path.exists(logo_path):
                logo_path = os.path.join(BUNDLE_DIR, "bkL.png")
            
            if os.path.exists(logo_path):
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self._cors()
                self.end_headers()
                with open(logo_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()

        elif parsed.path == "/app-info":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self._cors()
            self.end_headers()

            self.wfile.write(
                json.dumps(
                    {
                        "title": APP_TITLE,
                        "version": APP_VERSION,
                        "author": APP_AUTHOR,
                        "paypal": APP_PAYPAL,
                        "paypal_url": APP_PAYPAL_URL,
                        "boosty": APP_BOOSTY,
                        "boosty_url": APP_BOOSTY_URL,
                        "update_version": APP_VERSION,
                        "update_url": normalize_update_url(UPDATE_EXE_URL),
                        "frozen": bool(getattr(sys, "frozen", False)),
                    },
                    ensure_ascii=False,
                ).encode("utf-8")
            )

        elif parsed.path == "/settings":
            settings = load_app_settings()
            # ▼▼▼ ДОБАВИТЬ: отдаём в интерфейс уже раскрытый абсолютный путь ▼▼▼
            try:
                settings["directory"] = os.path.expanduser(os.path.expandvars(settings.get("directory", "")))
            except Exception:
                pass
            # ▲▲▲ КОНЕЦ ДОБАВЛЕНИЯ ▲▲▲
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self._cors()
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    settings,
                    ensure_ascii=False
                ).encode("utf-8")
            )
           
        elif parsed.path == "/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self._cors()
            self.end_headers()

            self.wfile.write(
                json.dumps(
                    {
                        "running": is_running,
                        "ytdlp_version": get_installed_version() or "неизвестно",
                    },
                    ensure_ascii=False,
                ).encode("utf-8")
            )

        elif parsed.path == "/stream":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("X-Accel-Buffering", "no")
            self._cors()
            self.end_headers()

            while True:
                try:
                    msg = message_queue.get(timeout=25)
                    self.wfile.write(f"data: {msg}\n\n".encode("utf-8"))
                    self.wfile.flush()

                    data = json.loads(msg)

                    if data.get("type") == "done":
                        break
                except queue.Empty:
                    try:
                        self.wfile.write(b": heartbeat\n\n")
                        self.wfile.flush()
                    except Exception:
                        break
                except Exception:
                    break

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        try:
            self._do_POST()
        except Exception as e:
            try:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self._cors()
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}, ensure_ascii=False).encode("utf-8"))
            except Exception:
                pass

    def read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)

        if not raw:
            return {}

        return json.loads(raw.decode("utf-8", errors="replace"))

    def _do_POST(self):
        global is_running

        # === ЗАПУСК КОНВЕРТАЦИИ В H264 ===
        if self.path == "/convert-h264":
            t = threading.Thread(target=run_h264_conversion, daemon=True)
            t.start()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._cors()
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}, ensure_ascii=False).encode("utf-8"))
            return
        # =================================

        # === ОТМЕНА ЗАГРУЗКИ ===
        if self.path == "/cancel":
            global cancel_requested, current_process
            cancel_requested = True
            
            if current_process:
                try:
                    current_process.kill()
                except:
                    pass
                    
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._cors()
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}, ensure_ascii=False).encode("utf-8"))
            return
             # === ОБРАБОТКА АВТОРИЗАЦИИ ===
        if self.path == "/api/open_auth":
            try:
                log("⏳ Ищу поддерживаемый браузер...", "info")
                browser_exe = find_auth_browser()
                if not browser_exe:
                    raise Exception("Браузер не найден (нужен Chrome, Edge, Яндекс, Opera или Brave)")

                profile_dir = os.path.join(DATA_DIR, "youtube_profile")
                os.makedirs(profile_dir, exist_ok=True)

                cmd = [
                    browser_exe,
                    "--app=https://accounts.google.com/ServiceLogin?service=youtube",
                    f"--user-data-dir={profile_dir}",
                    "--disable-features=TranslateUI"
                ]

                log("⏳ Открываю окно. Войдите в аккаунт и ЗАКРОЙТЕ окно.", "info")
                start_time = time.time()
                
                # Запускаем БРАУЗЕР напрямую (никаких вторых копий программы)
                proc = _ORIGINAL_SUBPROCESS_POPEN(cmd)
                proc.wait() # Ждем, пока человек закроет окно
                
                elapsed_time = time.time() - start_time
                is_saved = os.path.exists(profile_dir)
                
                # Если окно было открыто меньше 15 секунд — человек точно не успел ввести логин и пароль
                if elapsed_time < 15:
                    is_saved = False

                if is_saved:
                    log("✅ Профиль авторизации успешно сохранен!", "ok")
                else:
                    log("⚠ Окно было закрыто без авторизации.", "warn")

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self._cors()
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "saved": is_saved}, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                log(f"❌ Ошибка запуска окна: {str(e)}", "error")
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self._cors()
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}, ensure_ascii=False).encode("utf-8"))
            return
        # =========================================
        
        if self.path == "/parse-playlist":
            data = self.read_json()
            url = str(data.get("url") or "").strip()

            if not url:
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self._cors()
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Пустая ссылка"}, ensure_ascii=False).encode("utf-8"))
                return

            if not os.path.exists(YTDLP_PATH):
                if not download_ytdlp():
                    self.send_response(500)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self._cors()
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "yt-dlp отсутствует"}, ensure_ascii=False).encode("utf-8"))
                    return

            try:
                cmd = [
                    YTDLP_PATH,
                    "--flat-playlist",
                    "--dump-single-json",
                    "--no-warnings",
                    url
                ]

                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=60
                )

                if proc.returncode != 0:
                    err_msg = proc.stderr.strip() or "Не удалось получить структуру."
                    self.send_response(500)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self._cors()
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": err_msg}, ensure_ascii=False).encode("utf-8"))
                    return

                playlist_json = json.loads(proc.stdout)
                title = playlist_json.get("title") or "Альбом/Плейлист"
                entries = playlist_json.get("entries", [])

                clean_entries = []
                for entry in entries:
                    if not entry:
                        continue
                    
                    v_title = entry.get("title")
                    v_url = entry.get("url") or ""
                    v_id = entry.get("id") or v_url or "track"

                    if "soundcloud" in url:
                        if v_url and v_url.startswith("/"):
                            v_url = "https://soundcloud.com" + v_url
                        elif v_url and not v_url.startswith("http"):
                            v_url = "https://soundcloud.com/" + v_url
                        elif not v_url:
                            v_url = f"https://soundcloud.com/{v_id}"

                    if "bandcamp.com" in url:
                        if v_url and not v_url.startswith("http"):
                            if v_url.startswith("/track/"):
                                parsed_orig = urllib.parse.urlparse(url)
                                v_url = f"{parsed_orig.scheme}://{parsed_orig.netloc}{v_url}"
                        elif not v_url:
                            v_url = url

                    if not v_title or str(v_title).strip() in ["", "None", "Без названия", "None - None"]:
                        if "soundcloud.com" in v_url:
                            parsed_url = urllib.parse.urlparse(v_url)
                            path_parts = [p for p in parsed_url.path.split("/") if p]
                            if len(path_parts) >= 2:
                                artist = path_parts[-2].replace("-", " ").replace("_", " ").strip().title()
                                track = path_parts[-1].replace("-", " ").replace("_", " ").strip().title()
                                v_title = f"{artist} — {track}"
                        
                        if not v_title or str(v_title).strip() in ["", "None", "Без названия"]:
                            v_title = f"Трек {v_id}"

                    duration_sec = entry.get("duration")
                    duration_str = ""
                    if duration_sec is not None:
                        try:
                            ds = int(float(duration_sec))
                            m = ds // 60
                            s = ds % 60
                            duration_str = f" [{m:02d}:{s:02d}]"
                        except Exception:
                            pass

                    display_title = f"{v_title}{duration_str}" if duration_str else v_title

                    if "youtube" in url or "youtu.be" in url:
                        if v_url and not v_url.startswith("http"):
                            v_url = f"https://www.youtube.com/watch?v={v_id}"
                        elif not v_url:
                            v_url = f"https://www.youtube.com/watch?v={v_id}"

                    clean_entries.append({
                        "title": display_title,
                        "url": v_url
                    })

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self._cors()
                self.end_headers()
                self.wfile.write(
                    json.dumps({
                        "ok": True,
                        "title": title,
                        "entries": clean_entries
                    }, ensure_ascii=False).encode("utf-8")
                )

            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self._cors()
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Ошибка парсинга: {str(e)}"}, ensure_ascii=False).encode("utf-8"))
            return

        if self.path == "/open-url":
            data = self.read_json()
            url = str(data.get("url") or "").strip()

            allowed = [
                "https://paypal.me/",
                "https://www.paypal.me/",
                "https://boosty.to/",
                "https://www.boosty.to/"
            ]

            # Разрешаем любые безопасные ссылки (http и https)
            if not url.startswith("http://") and not url.startswith("https://"):
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self._cors()
                self.end_headers()
                self.wfile.write(
                    json.dumps(
                        {
                            "ok": False,
                            "error": "Разрешены только http и https ссылки",
                        },
                        ensure_ascii=False
                    ).encode("utf-8")
                )
                return


            try:
                webbrowser.open(url)
                ok = True
                err = ""
            except Exception as e:
                ok = False
                err = str(e)

            self.send_response(200 if ok else 500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._cors()
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {
                        "ok": ok,
                        "error": err,
                    },
                    ensure_ascii=False
                ).encode("utf-8")
            )
            return

        if self.path == "/check-update":
            info = check_update_info()

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._cors()
            self.end_headers()
            self.wfile.write(json.dumps(info, ensure_ascii=False).encode("utf-8"))
            return

        if self.path == "/install-update":
            result = install_program_update()

            self.send_response(200 if result.get("ok") else 500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._cors()
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
            return

        if self.path == "/clipboard-read":
            text = read_system_clipboard()

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._cors()
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {
                        "ok": True,
                        "text": text,
                    },
                    ensure_ascii=False
                ).encode("utf-8")
            )
            return

        if self.path == "/save-settings":
            data = self.read_json()

            ok = save_app_settings(data)

            self.send_response(200 if ok else 500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._cors()
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {
                        "ok": ok,
                        "settings": load_app_settings(),
                    },
                    ensure_ascii=False
                ).encode("utf-8")
            )
            return

        elif self.path == "/download":
            data = self.read_json()

            if is_running:
                self.send_response(409)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self._cors()
                self.end_headers()
                self.wfile.write(
                    json.dumps(
                        {"error": "Загрузка уже выполняется"},
                        ensure_ascii=False
                    ).encode("utf-8")
                )
                return

            while not message_queue.empty():
                try:
                    message_queue.get_nowait()
                except Exception:
                    break

            jobs = data.get("jobs", [])
            settings = data.get("settings", {})

            t = threading.Thread(
                target=run_downloads,
                args=(jobs, settings),
                daemon=True
            )
            t.start()

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._cors()
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {"ok": True, "count": len(jobs)},
                    ensure_ascii=False
                ).encode("utf-8")
            )

        elif self.path == "/browse-folder":
            data = self.read_json()
            directory = data.get("directory", DEFAULT_APP_SETTINGS["directory"]) or DEFAULT_APP_SETTINGS["directory"]

            selected = browse_for_folder(directory)

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._cors()
            self.end_headers()

            if selected:
                save_app_settings(
                    {
                        "directory": selected,
                    }
                )

                self.wfile.write(
                    json.dumps(
                        {
                            "ok": True,
                            "directory": selected,
                        },
                        ensure_ascii=False,
                    ).encode("utf-8")
                )
            else:
                self.wfile.write(
                    json.dumps(
                        {
                            "ok": False,
                            "directory": directory,
                        },
                        ensure_ascii=False,
                    ).encode("utf-8")
                )

            return

# 1. Добавить новый эндпоинт для открытия папки с выделением файла
        elif self.path == "/open-file-in-folder":
            data = self.read_json()
            file_path = str(data.get("path") or "").strip()
            download_dir = str(data.get("directory") or "").strip()
            
            try:
                target = None
                
                # 1. Сначала ищем точное совпадение
                if file_path:
                    if os.path.exists(file_path):
                        target = file_path
                    else:
                        # 2. Умный поиск (Fuzzy Search) для файлов с Facebook/YouTube
                        # Если спецсимволы или пробелы исказились, ищем файл по сходству
                        dir_name = os.path.dirname(file_path) or download_dir
                        base_name = os.path.basename(file_path)
                        
                        if os.path.exists(dir_name) and base_name:
                            clean_base = base_name.replace(" ", "").replace("·", "").lower()
                            name_part = base_name[:15] # Берем первые 15 символов
                            
                            for f in os.listdir(dir_name):
                                clean_f = f.replace(" ", "").replace("·", "").lower()
                                # Ищем либо по началу строки, либо по имени без пробелов
                                if f.startswith(name_part) or clean_f == clean_base:
                                    target = os.path.join(dir_name, f)
                                    break
                
                # 3. Если файл так и не найден, просто откроем папку
                if not target and download_dir and os.path.exists(download_dir):
                    target = download_dir
                
                if target:
                    target = os.path.abspath(os.path.normpath(target)).replace('"', '')
                    
                    if os.path.isfile(target):
                        # ФАЙЛ НАЙДЕН — открываем папку и выделяем его
                        if sys.platform == "win32":
                            import ctypes
                            try:
                                ctypes.windll.ole32.CoInitialize(None)
                                
                                folder_path = os.path.dirname(target)
                                
                                ILCreateFromPathW = ctypes.windll.shell32.ILCreateFromPathW
                                ILCreateFromPathW.restype = ctypes.c_void_p
                                ILCreateFromPathW.argtypes = [ctypes.c_wchar_p]
                                
                                ILFindLastID = ctypes.windll.shell32.ILFindLastID
                                ILFindLastID.restype = ctypes.c_void_p
                                ILFindLastID.argtypes = [ctypes.c_void_p]
                                
                                ILFree = ctypes.windll.shell32.ILFree
                                ILFree.argtypes = [ctypes.c_void_p]
                                
                                SHOpenFolderAndSelectItems = ctypes.windll.shell32.SHOpenFolderAndSelectItems
                                SHOpenFolderAndSelectItems.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_ulong]
                                
                                folder_pidl = ILCreateFromPathW(folder_path)
                                item_pidl = ILCreateFromPathW(target)
                                
                                if folder_pidl and item_pidl:
                                    child_pidl = ILFindLastID(item_pidl)
                                    pidl_array = (ctypes.c_void_p * 1)(child_pidl)
                                    SHOpenFolderAndSelectItems(folder_pidl, 1, pidl_array, 0)
                                    
                                if folder_pidl: ILFree(folder_pidl)
                                if item_pidl: ILFree(item_pidl)
                                
                                ctypes.windll.ole32.CoUninitialize()
                            except Exception as win_e:
                                os.startfile(os.path.dirname(target))
                        elif sys.platform == "darwin":
                            subprocess.Popen(['open', '-R', target])
                        else:
                            subprocess.Popen(['xdg-open', os.path.dirname(target)])
                    else:
                        # ЭТО ПАПКА (файл не найден). Используем хак для предотвращения новых окон!
                        if sys.platform == "win32":
                            import ctypes
                            from ctypes import wintypes
                            try:
                                ctypes.windll.ole32.CoInitialize(None)
                                ILCreateFromPathW = ctypes.windll.shell32.ILCreateFromPathW
                                ILCreateFromPathW.restype = ctypes.c_void_p
                                ILCreateFromPathW.argtypes = [ctypes.c_wchar_p]
                                ILFree = ctypes.windll.shell32.ILFree
                                ILFree.argtypes = [ctypes.c_void_p]
                                
                                folder_pidl = ILCreateFromPathW(target)
                                if folder_pidl:
                                    class SHELLEXECUTEINFOW(ctypes.Structure):
                                        _fields_ = [
                                            ("cbSize", wintypes.DWORD),
                                            ("fMask", ctypes.c_ulong),
                                            ("hwnd", wintypes.HWND),
                                            ("lpVerb", wintypes.LPCWSTR),
                                            ("lpFile", wintypes.LPCWSTR),
                                            ("lpParameters", wintypes.LPCWSTR),
                                            ("lpDirectory", wintypes.LPCWSTR),
                                            ("nShow", ctypes.c_int),
                                            ("hInstApp", wintypes.HINSTANCE),
                                            ("lpIDList", ctypes.c_void_p),
                                            ("lpClass", wintypes.LPCWSTR),
                                            ("hkeyClass", wintypes.HKEY),
                                            ("dwHotKey", wintypes.DWORD),
                                            ("hIconOrMonitor", wintypes.HANDLE),
                                            ("hProcess", wintypes.HANDLE),
                                        ]
                                    ShellExecuteExW = ctypes.windll.shell32.ShellExecuteExW
                                    ShellExecuteExW.argtypes = [ctypes.POINTER(SHELLEXECUTEINFOW)]
                                    ShellExecuteExW.restype = wintypes.BOOL
                                    
                                    sei = SHELLEXECUTEINFOW()
                                    sei.cbSize = ctypes.sizeof(SHELLEXECUTEINFOW)
                                    sei.fMask = 0x00000004
                                    sei.nShow = 1
                                    sei.lpIDList = folder_pidl
                                    ShellExecuteExW(ctypes.byref(sei))
                                    ILFree(folder_pidl)
                                ctypes.windll.ole32.CoUninitialize()
                            except Exception:
                                os.startfile(target)
                        elif sys.platform == "darwin":
                            subprocess.Popen(['open', target])
                        else:
                            subprocess.Popen(['xdg-open', target])
            except Exception as e:
                pass

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._cors()
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}, ensure_ascii=False).encode("utf-8"))
            return

        elif self.path == "/open-folder":
            data = self.read_json()
            directory = data.get("directory", DEFAULT_APP_SETTINGS["directory"]) or DEFAULT_APP_SETTINGS["directory"]

            save_app_settings({"directory": directory})

            folder_path = get_download_dir_from_setting(directory)
            os.makedirs(folder_path, exist_ok=True)

            try:
                folder_path = os.path.abspath(os.path.normpath(folder_path)).replace('"', '')
                
                if sys.platform == "win32":
                    import ctypes
                    from ctypes import wintypes
                    try:
                        ctypes.windll.ole32.CoInitialize(None)
                        
                        ILCreateFromPathW = ctypes.windll.shell32.ILCreateFromPathW
                        ILCreateFromPathW.restype = ctypes.c_void_p
                        ILCreateFromPathW.argtypes = [ctypes.c_wchar_p]
                        
                        ILFree = ctypes.windll.shell32.ILFree
                        ILFree.argtypes = [ctypes.c_void_p]
                        
                        folder_pidl = ILCreateFromPathW(folder_path)
                        
                        if folder_pidl:
                            class SHELLEXECUTEINFOW(ctypes.Structure):
                                _fields_ = [
                                    ("cbSize", wintypes.DWORD),
                                    ("fMask", ctypes.c_ulong),
                                    ("hwnd", wintypes.HWND),
                                    ("lpVerb", wintypes.LPCWSTR),
                                    ("lpFile", wintypes.LPCWSTR),
                                    ("lpParameters", wintypes.LPCWSTR),
                                    ("lpDirectory", wintypes.LPCWSTR),
                                    ("nShow", ctypes.c_int),
                                    ("hInstApp", wintypes.HINSTANCE),
                                    ("lpIDList", ctypes.c_void_p),
                                    ("lpClass", wintypes.LPCWSTR),
                                    ("hkeyClass", wintypes.HKEY),
                                    ("dwHotKey", wintypes.DWORD),
                                    ("hIconOrMonitor", wintypes.HANDLE),
                                    ("hProcess", wintypes.HANDLE),
                                ]
                            
                            ShellExecuteExW = ctypes.windll.shell32.ShellExecuteExW
                            ShellExecuteExW.argtypes = [ctypes.POINTER(SHELLEXECUTEINFOW)]
                            ShellExecuteExW.restype = wintypes.BOOL
                            
                            sei = SHELLEXECUTEINFOW()
                            sei.cbSize = ctypes.sizeof(SHELLEXECUTEINFOW)
                            sei.fMask = 0x00000004
                            sei.nShow = 1
                            sei.lpIDList = folder_pidl
                            
                            ShellExecuteExW(ctypes.byref(sei))
                            ILFree(folder_pidl)
                            
                        ctypes.windll.ole32.CoUninitialize()
                    except Exception as win_e:
                        os.startfile(folder_path)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", folder_path])
                else:
                    subprocess.Popen(["xdg-open", folder_path])
            except Exception:
                pass

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._cors()
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}, ensure_ascii=False).encode("utf-8"))
            return

        else:
            self.send_response(404)
            self.end_headers()


class ReusableTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


httpd_instance = None
server_ready = threading.Event()
server_error = None


def run_http_server():
    global httpd_instance, server_error

    try:
        with ReusableTCPServer(("127.0.0.1", PORT), Handler) as httpd:
            httpd_instance = httpd
            server_ready.set()
            httpd.serve_forever()
    except Exception as e:
        server_error = e
        server_ready.set()


def shutdown_http_server():
    global httpd_instance

    try:
        if httpd_instance:
            httpd_instance.shutdown()
            httpd_instance.server_close()
    except Exception:
        pass


def find_app_browser_exe():
    candidates = []

    if sys.platform == "win32":
        pf = os.environ.get("PROGRAMFILES", "")
        pfx86 = os.environ.get("PROGRAMFILES(X86)", "")
        local = os.environ.get("LOCALAPPDATA", "")

        candidates += [
            os.path.join(pf, "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(pfx86, "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(local, "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(pf, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(pfx86, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(local, "Google", "Chrome", "Application", "chrome.exe"),
        ]

        for name in ["msedge", "chrome"]:
            found = shutil.which(name)

            if found:
                candidates.append(found)

    elif sys.platform == "darwin":
        candidates += [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ]
    else:
        for name in ["microsoft-edge", "microsoft-edge-stable", "google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]:
            found = shutil.which(name)

            if found:
                candidates.append(found)

    for p in candidates:
        if p and os.path.exists(p):
            return p

    return None


class WindowAPI:
    def __init__(self):
        self._window = None

    def set_window(self, window):
        self._window = window

    def minimize(self):
        if self._window:
            self._window.minimize()

    def maximize(self):
        if self._window:
            self._window.toggle_fullscreen()

    def close(self):
        if self._window:
            self._window.destroy()


def style_native_window(window):
    """
    Красит стандартную рамку и заголовок Windows в цвет интерфейса #06101d.
    Применяется до показа окна на экране, чтобы избежать белой вспышки.
    """
    if sys.platform == "win32":
        try:
            import ctypes
            hwnd = window.native.Handle.ToInt64()
            dwmapi = ctypes.windll.dwmapi
            user32 = ctypes.windll.user32

            # 1. Включаем темную тему для заголовка (Windows 10/11)
            dark_mode = ctypes.c_int(1)
            dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark_mode), ctypes.sizeof(dark_mode))
            dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(dark_mode), ctypes.sizeof(dark_mode))

            # 2. Красим шапку в цвет интерфейса #06101d (формат цвета BGR: 0x001D1006)
            caption_color = ctypes.c_int(0x001D1006)
            dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(caption_color), ctypes.sizeof(caption_color))

            # 3. Красим текст заголовка в светлый оттенок #eef7ff (формат BGR: 0x00FFF7EE)
            text_color = ctypes.c_int(0x00FFF7EE)
            dwmapi.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(text_color), ctypes.sizeof(text_color))

            # 4. Принудительное обновление стилей окна в Windows
            # SWP_FRAMECHANGED (0x0020) | SWP_NOMOVE (0x0002) | SWP_NOSIZE (0x0001) | SWP_NOZORDER (0x0004)
            user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0020 | 0x0002 | 0x0001 | 0x0004)
        except Exception as e:
            print("Не удалось применить тему к рамке Windows:", e)


def open_desktop_window(url):
    if webview is not None:
        try:
            splash_text("Загружаю интерфейс...")

            api = WindowAPI()

            # Создаем стандартное окно, но изначально СКРЫТЫМ (hidden=True)
            window = webview.create_window(
                APP_TITLE,
                url,
                width=APP_WIDTH,
                height=APP_HEIGHT,
                min_size=(940, 650),
                text_select=True,
                frameless=False,            # <--- Стандартное окно (без рамок вокруг интерфейса, только шапка)
                background_color="#06101d", # <--- Задний фон в тон приложения
                hidden=True,                # <--- Прячем при создании, чтобы не было белого мерцания
                js_api=api,
            )
            api.set_window(window)

            # Как только окно создано в памяти (loaded), мы его красим и отображаем уже готовым
            def initialize_and_show():
                style_native_window(window) # Красим шапку в синий
                window.show()               # Показываем уже красивое окно!
                
                # Плавно закрываем сплэш-скрин
                try:
                    splash_text("Готово")
                    time.sleep(0.4)
                    close_splash()
                except Exception:
                    pass

            window.events.loaded += initialize_and_show

            webview.start()
            return

        except Exception as e:
            print("Не удалось запустить pywebview.")
            print(e)
            print("Пробую режим приложения через Edge/Chrome...")

    browser_exe = find_app_browser_exe()

    if browser_exe:
        try:
            splash_text("Открываю окно браузера...")

            user_data_dir = os.path.join(BASE_DIR, "_webview_profile_55")
            os.makedirs(user_data_dir, exist_ok=True)

            cmd = [
                browser_exe,
                f"--app={url}",
                "--new-window",
                f"--user-data-dir={user_data_dir}",
                "--disable-features=TranslateUI",
            ]

            proc = subprocess.Popen(cmd)

            time.sleep(2.2)
            close_splash()

            try:
                proc.wait()
            except KeyboardInterrupt:
                pass

            return

        except Exception as e:
            print("Не удалось открыть Edge/Chrome в режиме приложения.")
            print(e)

    print("pywebview и Edge/Chrome app mode недоступны.")
    print("Открываю обычный браузер как запасной вариант.")

    splash_text("Открываю браузер...")
    webbrowser.open(url)

    time.sleep(2)
    close_splash()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
# ================= ФОНОВАЯ ЗАГРУЗКА ШРИФТОВ =================
def download_fonts_in_background():
    import ssl
    import urllib.request
    from concurrent.futures import ThreadPoolExecutor

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    # Базовый URL надежного CDN
    base_url = "https://cdn.jsdelivr.net/npm/@fontsource/{font}/files/{filename}"

    # Точно ваш список с картинки
    font_specs = {
        "jetbrains-mono": [
            "cyrillic-400-normal", "cyrillic-500-normal", "cyrillic-700-normal",
            "latin-400-normal", "latin-500-normal", "latin-700-normal"
        ],
        "manrope": [
            "cyrillic-400-normal", "cyrillic-500-normal", "cyrillic-600-normal", "cyrillic-700-normal", "cyrillic-800-normal",
            "latin-400-normal", "latin-500-normal", "latin-600-normal", "latin-700-normal", "latin-800-normal"
        ],
        "unbounded": [
            "cyrillic-400-normal", "cyrillic-600-normal", "cyrillic-800-normal", "cyrillic-900-normal",
            "latin-400-normal", "latin-600-normal", "latin-800-normal", "latin-900-normal"
        ]
    }

    download_list = []
    for font, specs in font_specs.items():
        for spec in specs:
            filename = f"{font}-{spec}.woff2"
            url = base_url.format(font=font, filename=filename)
            path = os.path.join(FONTS_DIR, filename)
            if not os.path.exists(path):
                download_list.append((url, path))

    # Функция для скачивания одного файла
    def fetch(item):
        url, path = item
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                with open(path, "wb") as f:
                    f.write(resp.read())
        except Exception as e:
            print(f"[Шрифты] Ошибка {path}: {e}")

    # Запускаем скачивание в 10 потоков (ОЧЕНЬ БЫСТРО)
    if download_list:
        with ThreadPoolExecutor(max_workers=10) as executor:
            executor.map(fetch, download_list)
        print("[Шрифты] Все файлы с картинки успешно скачаны!")
# ============================================================

if __name__ == "__main__":
    url = f"http://127.0.0.1:{PORT}"
    
    threading.Thread(target=download_fonts_in_background, daemon=True).start()
    
    splash_text("Запуск сервера...")

    print("=" * 60)
    print(f" {APP_TITLE}")
    print(" Режим: Web UI отдельным окном")
    print(f" {url}")
    print("=" * 60)

    server_thread = threading.Thread(
        target=run_http_server,
        daemon=True,
    )
    server_thread.start()

    server_ready.wait(timeout=5)

    if server_error:
        print("\nОшибка запуска сервера.")
        print(f"Порт {PORT} может быть занят.")
        print("Закрой старую копию программы или поменяй PORT в начале файла.")
        print(server_error)
        input("\nНажми Enter для выхода...")
        sys.exit(1)

    try:
        splash_text("Открываю окно...")
        open_desktop_window(url)
    finally:
        shutdown_http_server()
