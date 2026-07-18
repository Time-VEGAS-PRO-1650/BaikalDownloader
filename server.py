# -*- coding: utf-8 -*-
"""
Байкал Downloader 5.5.16 (плейлисты, авто-Deno, авто-Node.js, MP3, обход блокировок, звуковое оповещение)
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
APP_TITLE = "Байкал Downloader 5.5.16"
APP_VERSION = "5.5.16"
APP_AUTHOR = "Iurii Cojocari (Time VEGAS PRO)"

# Константы Донатов
APP_PAYPAL = "paypal.me/studioyouar"
APP_PAYPAL_URL = "https://paypal.me/studioyouar"
APP_BOOSTY = "boosty.to/time_vegas_pro"
APP_BOOSTY_URL = "https://boosty.to/time_vegas_pro/donate"

# Ссылка на обновление.
UPDATE_VERSION = "5.5.16"
UPDATE_EXE_URL = "https://github.com/Time-VEGAS-PRO-1650/BaikalDownloader/releases/download/v5.6.0/Baikal_Downloader_Setup_5.6.exe"


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

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TOOLS_DIR, exist_ok=True)

SETTINGS_FILE = os.path.join(DATA_DIR, "baikal_settings.txt")

DEFAULT_APP_SETTINGS = {
    "directory": r"%USERPROFILE%\Downloads",
    "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
    "segmentDuration": "12",
    "maxDuration": "",
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
<title>Байкал Downloader 5.5.16</title>
<script async src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>

<style>
:root{
  --bg:#06101d;
  --panel:#101a2d;
  --line:rgba(125,211,252,.18);
  --line2:rgba(125,211,252,.38);
  --text:#eef7ff;
  --muted:#8190aa;
  --cyan:#22d3ee;
  --blue:#60a5fa;
  --violet:#a78bfa;
  --green:#34d399;
  --orange:#f59e0b;
  --red:#fb4966;
  --font:Segoe UI,system-ui,-apple-system,BlinkMacSystemFont,sans-serif;
  --mono:Consolas,"JetBrains Mono",monospace;
}

*{
  box-sizing:border-box;
  margin:0;
  padding:0;
}

body{
  height: 100vh;
  width: 100vw;
  margin: 0;
  padding: 0;
  overflow: hidden;
  font-family:var(--font);
  color:var(--text);
  background:
    radial-gradient(circle at top left,rgba(34,211,238,.16),transparent 30%),
    radial-gradient(circle at top right,rgba(167,139,250,.14),transparent 33%),
    var(--bg);
}

button,
input,
select,
textarea{
  font:inherit;
}

button{
  border:0;
}

/* Убираем белую рамку фокуса при запуске и клике */
button:focus, 
summary:focus, 
.btn:focus {
  outline: none;
}

/* ГИБКИЙ ИНТЕРФЕЙС НА ВСЕ ОКНО БЕЗ ОГРАНИЧИВАЮЩИХ РАМОК */
.app{
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: rgba(9, 15, 28, 0.95);
  overflow: hidden;
}

/* ШАПКА ТЕПЕРЬ СТАНДАРТНАЯ, БЕЗ ЛИШНИХ КУРСОРОВ */
.topbar{
  min-height: 58px;
  padding: 0 15px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.025);
}

.brand{
  display: flex;
  align-items: center;
  gap: 11px;
  min-width: 0;
  -webkit-app-region: drag; /* Позволяет тащить окно за логотип и название */
}

.logo{
  width: 38px;
  height: 38px;
  border-radius: 10px;
  object-fit: cover;
  flex: 0 0 auto;
}

.brand h1{
  font-size: 16px;
  line-height: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.brand p{
  margin-top: 4px;
  color: var(--muted);
  font-family: var(--mono);
  font-size: 10px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.top-right{
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
  -webkit-app-region: no-drag; /* Отключаем drag для кнопок, чтобы они нажимались */
}

/* КНОПКИ УПРАВЛЕНИЯ ОКНОМ СТРОГО В РЯД С ОСТАЛЬНЫМИ */
.win-controls {
  display: none !important; /* Полностью скрываем HTML-кнопки, оставляем только системные */
  align-items: center;
  gap: 8px;
}

.win-btn {
  width: 36px;
  height: 36px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font);
  font-size: 13px;
  font-weight: 750;
  background: rgba(255, 255, 255, 0.065);
  color: var(--text);
  cursor: pointer;
  transition: .15s;
  border: 1px solid var(--line);
  -webkit-app-region: no-drag;
}

.win-btn:hover {
  transform: translateY(-1px);
  border-color: var(--line2);
  background: rgba(255, 255, 255, 0.095);
}

.win-btn.win-close:hover {
  background: rgba(251, 73, 102, 0.2);
  border-color: rgba(251, 73, 102, 0.5);
  color: #ff9aad;
}

.server{
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: 390px;
  padding: 7px 11px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
  color: var(--muted);
  font-family: var(--mono);
  font-size: 10.5px;
  white-space: nowrap;
  -webkit-app-region: no-drag;
}

.about-menu{
  position: relative;
  -webkit-app-region: no-drag;
}

.about-menu summary{
  list-style: none;
}

.about-menu summary::-webkit-details-marker{
  display: none;
}

.about-btn{
  width: 36px;
  height: 36px;
  padding: 0;
  border-radius: 999px;
  font-size: 15px;
  font-weight: 950;
}

.about-window{
  position: absolute;
  right: 0;
  top: 43px;
  width: 360px;
  z-index: 45;
  padding: 13px;
  border: 1px solid var(--line2);
  border-radius: 16px;
  background: rgba(13, 22, 39, 0.985);
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.58);
}

.about-head{
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.about-logo{
  width: 52px;
  height: 52px;
  border-radius: 12px;
  object-fit: cover;
}

.about-title{
  min-width: 0;
}

.about-title b{
  display: block;
  font-size: 14px;
}

.about-title span{
  display: block;
  margin-top: 3px;
  color: var(--muted);
  font-family: var(--mono);
  font-size: 10px;
}

.about-text{
  display: grid;
  gap: 6px;
  margin-top: 10px;
  padding: 10px;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 13px;
  background: rgba(255, 255, 255, 0.035);
  color: #dcecff;
  font-family: var(--mono);
  font-size: 10.5px;
  line-height: 1.45;
}

.about-text a{
  color: #7dd3fc;
  text-decoration: none;
}

.about-actions{
  display: grid;
  grid-template-columns: 1fr;
  gap: 7px;
  margin-top: 10px;
}

.update-status{
  min-height: 18px;
  margin-top: 9px;
  color: var(--muted);
  font-family: var(--mono);
  font-size: 10px;
  line-height: 1.45;
  white-space: pre-wrap;
}

.update-status.ok{
  color: var(--green);
}

.update-status.warn{
  color: var(--orange);
}

.update-status.error{
  color: var(--red);
}

.server-dot{
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--red);
  flex: 0 0 auto;
  box-shadow: 0 0 0 4px rgba(251, 73, 102, .12);
}

.server.connected{
  color: #baf7dc;
  border-color: rgba(52, 211, 153, .28);
}

.server.connected .server-dot{
  background: var(--green);
  box-shadow: 0 0 0 4px rgba(52, 211, 153, .13), 0 0 16px rgba(52, 211, 153, .7);
}

.controls{
  padding: 12px 14px;
  display: grid;
  gap: 10px;
  border-bottom: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.018);
}

.progress-meta{
  display: flex;
  justify-content: space-between;
  gap: 10px;
  color: var(--muted);
  font-family: var(--mono);
  font-size: 10.5px;
  margin-bottom: 6px;
}

.progress-track{
  height: 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, .07);
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, .06);
}

.progress-fill{
  height: 100%;
  width: 0%;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--cyan), var(--blue), var(--violet));
  transition: .28s;
  box-shadow: 0 0 18px rgba(34, 211, 238, .45);
}

.progress-fill.loading{
  width: 34%;
  animation: load 1.1s ease-in-out infinite;
}

@keyframes load{
  0%{margin-left: -35%}
  100%{margin-left: 105%}
}

.action-row{
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 9px;
  align-items: center;
}

.btns{
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  align-items: center;
}

.btn{
  height: 37px;
  padding: 0 13px;
  border-radius: 11px;
  cursor: pointer;
  color: var(--text);
  background: rgba(255, 255, 255, .065);
  border: 1px solid var(--line);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  font-size: 12px;
  font-weight: 750;
  transition: .15s;
  white-space: nowrap;
}

.btn:hover:not(:disabled){
  transform: translateY(-1px);
  border-color: var(--line2);
  background: rgba(255, 255, 255, .095);
}

.btn:disabled{
  opacity: .45;
  cursor: not-allowed;
}

.btn-main{
  min-width: 140px;
  height: 40px;
  background: linear-gradient(135deg, #0891b2, #2563eb);
  color: white;
  border-color: rgba(255, 255, 255, .18);
  box-shadow: 0 10px 28px rgba(34, 211, 238, .16);
}

.btn-red{
  color: #ff9aad;
  border-color: rgba(251, 73, 102, .25);
  background: rgba(251, 73, 102, .09);
}

.btn-green{
  color: #a7f3d0;
  border-color: rgba(52, 211, 153, .25);
  background: rgba(52, 211, 153, .09);
}

.btn-blue{
  color: #93c5fd;
  border-color: rgba(96, 165, 250, .25);
  background: rgba(96, 165, 250, .09);
}

.stats{
  display: grid;
  grid-template-columns: repeat(4, 78px);
  gap: 7px;
}

.stat{
  padding: 7px 8px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: rgba(255, 255, 255, .04);
}

.stat.danger{
  border-color: rgba(251, 73, 102, .35);
  background: rgba(251, 73, 102, .09);
}

.stat b{
  display: block;
  font-size: 19px;
  line-height: 1;
}

.stat span{
  display: block;
  margin-top: 4px;
  color: var(--muted);
  font-family: var(--mono);
  font-size: 8.5px;
  text-transform: uppercase;
}

.settings{
  position: relative;
}

.settings summary{
  list-style: none;
}

.settings summary::-webkit-details-marker{
  display: none;
}

.settings-window{
  position: absolute;
  right: 0;
  top: 43px;
  width: 400px;
  z-index: 30;
  padding: 11px;
  border: 1px solid var(--line2);
  border-radius: 16px;
  background: rgba(13, 22, 39, .98);
  box-shadow: 0 24px 80px rgba(0, 0, 0, .55);
}

.settings-title{
  display: flex;
  justify-content: space-between;
  margin-bottom: 9px;
  font-size: 12.5px;
  font-weight: 850;
}

.settings-title small{
  color: var(--muted);
  font-family: var(--mono);
  font-size: 9px;
}

.settings-grid{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 9px;
}

.field{
  display: grid;
  gap: 5px;
}

.field.full{
  grid-column: 1/-1;
}

.field label{
  color: var(--muted);
  font-family: var(--mono);
  font-size: 9.5px;
}

.input-row{
  display: flex;
  gap: 7px;
}

input,
select{
  width: 100%;
  height: 35px;
  padding: 0 10px;
  color: var(--text);
  background: rgba(3, 8, 18, .72);
  border: 1px solid var(--line);
  outline: none;
  border-radius: 11px;
  font-family: var(--mono);
  font-size: 10.5px;
}

textarea:focus,
input:focus,
select:focus{
  border-color: rgba(34, 211, 238, .55);
  box-shadow: 0 0 0 3px rgba(34, 211, 238, .08);
}

/* ОСНОВНОЙ БЛОК ЗАПОЛНЯЕТ ВСЕ СВОБОДНОЕ ПРОСТРАНСТВО */
.main{
  flex: 1;
  overflow-y: auto;
  padding: 12px 14px 14px;
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  align-items: start;
}

.panel{
  border: 1px solid var(--line);
  border-radius: 16px;
  background: rgba(16, 26, 45, .80);
  overflow: hidden;
}

.panel-head{
  min-height: 38px;
  padding: 8px 13px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, .065);
}

.panel-title{
  color: #dff8ff;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: .8px;
  font-weight: 850;
}

.panel-note{
  color: var(--muted);
  font-family: var(--mono);
  font-size: 9.5px;
}

.panel-body{
  padding: 11px;
}

textarea{
  width: 100%;
  height: 270px;
  min-height: 170px;
  max-height: 560px;
  resize: both;
  padding: 12px;
  color: var(--text);
  background: rgba(3, 8, 18, .72);
  border: 1px solid var(--line);
  outline: none;
  border-radius: 12px;
  line-height: 1.5;
  font-family: var(--mono);
  font-size: 12px;
  overflow: auto;
}

textarea.has-duplicates{
  border-color: rgba(251, 73, 102, .75);
  box-shadow: 0 0 0 3px rgba(251, 73, 102, .12);
}

textarea::placeholder{
  color: #61708a;
}

.info-box{
  margin-top: 10px;
  display: none;
  padding: 10px 11px;
  border-radius: 13px;
  border: 1px solid rgba(125, 211, 252, .18);
  background: rgba(255, 255, 255, .035);
  font-family: var(--mono);
  font-size: 10.5px;
  line-height: 1.55;
}

.info-box.show{
  display: block;
}

.info-box .ok{
  color: var(--green);
}

.info-box .warn{
  color: var(--orange);
}

.info-box .dup-title{
  color: #ffb4c0;
  font-weight: 900;
}

.info-box .dup-line{
  color: var(--red);
  margin-top: 3px;
  word-break: break-all;
}

.platforms-panel{
  display: none;
}

.platforms-grid{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(112px, 1fr));
  gap: 8px;
  width: 100%;
}

.platform-card{
  min-height: 86px;
  padding: 8px;
  border: 1px solid rgba(255, 255, 255, .08);
  border-radius: 13px;
  background: rgba(255, 255, 255, .045);
  position: relative;
  overflow: hidden;
  transition: .15s;
}

.platform-card.active{
  border-color: rgba(34, 211, 238, .45);
  background: rgba(34, 211, 238, .08);
}

.platform-card.done{
  border-color: rgba(52, 211, 153, .48);
  background: rgba(52, 211, 153, .12);
}

.platform-top{
  display: grid;
  grid-template-columns: 34px 1fr;
  gap: 8px;
  align-items: center;
}

.platform-icon{
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  background: var(--color, #334155);
  color: white;
  font-weight: 950;
  font-size: 12px;
}

.platform-info{
  min-width: 0;
}

.platform-name{
  font-size: 11px;
  font-weight: 850;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.platform-sub{
  margin-top: 3px;
  color: var(--muted);
  font-family: var(--mono);
  font-size: 9px;
}

.platform-count{
  position: absolute;
  top: 6px;
  right: 6px;
  min-width: 19px;
  height: 19px;
  padding: 0 6px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: var(--cyan);
  color: #041018;
  font-family: var(--mono);
  font-size: 9px;
  font-weight: 950;
}

.platform-progress{
  margin-top: 9px;
  height: 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, .08);
  overflow: hidden;
}

.platform-progress-fill{
  height: 100%;
  width: 0%;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--cyan), var(--blue), var(--violet));
  transition: .25s;
}

.platform-card.done .platform-progress-fill{
  background: linear-gradient(90deg, #22c55e, #34d399);
}

.bottom{
  padding: 0 14px 14px;
}

.log-details{
  border: 1px solid var(--line);
  border-radius: 15px;
  background: rgba(16, 26, 45, .72);
  overflow: hidden;
}

.log-details summary{
  height: 36px;
  padding: 0 12px;
  cursor: pointer;
  list-style: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  font-weight: 800;
}

.log-details summary::-webkit-details-marker{
  display: none;
}

.log-details summary::after{
  content: "⌄";
  color: var(--muted);
}

.log-details[open] summary::after{
  transform: rotate(180deg);
}

.termbar{
  height: 31px;
  padding: 0 12px;
  display: flex;
  align-items: center;
  gap: 7px;
  border-top: 1px solid rgba(255, 255, 255, .06);
  border-bottom: 1px solid rgba(255, 255, 255, .06);
  background: rgba(0, 0, 0, .18);
}

.dot{
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.r{background: #ff5f57}
.y{background: #febc2e}
.g{background: #28c840}

.term-name{
  flex: 1;
  color: var(--muted);
  font-family: var(--mono);
  font-size: 10px;
}

.term-status{
  color: var(--muted);
  font-family: var(--mono);
  font-size: 10px;
}

.term-status.running{color: var(--cyan)}
.term-status.done{color: var(--green)}
.term-status.error{color: var(--red)}

.term-body{
  max-height: 230px;
  overflow: auto;
  padding: 11px;
  font-family: var(--mono);
  font-size: 11px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}

.line-info{color: #b7c1d8}
.line-ok{color: var(--green)}
.line-error{color: var(--red)}
.line-warn{color: var(--orange)}
.line-cmd{color: #74839c}
.line-url{color: #7dd3fc}
.line-sep{color: #465269}
.line-done{color: var(--green); font-weight: 900}

.cursor{
  display: inline-block;
  width: 7px;
  height: 12px;
  background: var(--green);
  vertical-align: -2px;
  animation: blink 1s steps(1) infinite;
}

.cursor.hidden{
  display: none;
}

@keyframes blink{
  50%{opacity: 0}
}

.toast{
  position: fixed;
  right: 18px;
  bottom: 18px;
  z-index: 60;
  max-width: min(390px, calc(100% - 36px));
  padding: 11px 13px;
  border-radius: 13px;
  background: rgba(13, 22, 39, .96);
  color: var(--text);
  border: 1px solid var(--line2);
  box-shadow: 0 18px 60px rgba(0, 0, 0, .45);
  transform: translateY(24px);
  opacity: 0;
  pointer-events: none;
  transition: .22s;
  font-family: var(--mono);
  font-size: 11px;
}

.toast.show{
  transform: translateY(0);
  opacity: 1;
}

details.about-menu,
details.settings{
  position: relative;
}

details:not([open]) > .about-window,
details:not([open]) > .settings-window{
  display: block;
}

.about-window,
.settings-window{
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transform: translateY(-10px) scale(.96);
  transform-origin: top right;
  transition:
    opacity .18s ease,
    transform .22s cubic-bezier(.2, .8, .2, 1),
    visibility 0s linear .22s;
}

.about-menu[open] .about-window,
.settings[open] .settings-window{
  opacity: 1;
  visibility: visible;
  pointer-events: auto;
  transform: translateY(0) scale(1);
  transition:
    opacity .18s ease,
    transform .22s cubic-bezier(.2, .8, .2, 1),
    visibility 0s linear 0s;
}

.about-menu.is-closing .about-window,
.settings.is-closing .settings-window{
  opacity: 0;
  visibility: visible;
  pointer-events: none;
  transform: translateY(-8px) scale(.96);
}

.about-menu[open] > summary,
.settings[open] > summary{
  border-color: rgba(34, 211, 238, .55);
  background: rgba(34, 211, 238, .13);
  box-shadow: 0 0 0 3px rgba(34, 211, 238, .08);
}

body.popup-open::before{
  content: "";
  position: fixed;
  inset: 0;
  z-index: 20;
  background: rgba(0, 0, 0, .18);
  backdrop-filter: blur(2px);
  pointer-events: none;
  opacity: 1;
  transition: opacity .18s ease;
}

.about-window{
  z-index: 45;
}

.settings-window{
  z-index: 46;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(5px);
  z-index: 9999;
  display: none;
  align-items: center;
  justify-content: center;
  padding: 12px;
}

.modal-backdrop.show {
  display: flex;
}

.playlist-modal {
  width: min(680px, 100%);
  max-height: 85vh;
  background: rgba(13, 22, 39, 0.985);
  border: 1px solid var(--line2);
  border-radius: 18px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.6);
  overflow: hidden;
  animation: mSlide 0.22s cubic-bezier(0.2, 0.8, 0.2, 1);
}

@keyframes mSlide {
  from { transform: translateY(15px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

.playlist-header {
  padding: 14px 16px;
  border-bottom: 1px solid var(--line);
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.02);
}

.playlist-header h3 {
  font-size: 15px;
  font-weight: 900;
  color: var(--cyan);
}

.playlist-body {
  padding: 14px;
  overflow-y: auto;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.playlist-controls {
  display: flex;
  gap: 8px;
}

.playlist-list {
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: rgba(3, 8, 18, 0.72);
  padding: 6px;
}

.playlist-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.12s;
  margin-bottom: 3px;
}

.playlist-item:hover {
  background: rgba(255, 255, 255, 0.04);
}

.playlist-item input[type="checkbox"] {
  width: 17px;
  height: 17px;
  margin: 0;
  cursor: pointer;
  accent-color: var(--cyan);
}

.playlist-item-title {
  font-size: 12.5px;
  font-family: var(--font);
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  user-select: none;
}

.playlist-footer {
  padding: 12px 14px;
  border-top: 1px solid var(--line);
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  background: rgba(255, 255, 255, 0.01);
}

@media(max-width:980px){
  .action-row{
    grid-template-columns: 1fr;
  }

  .stats{
    grid-template-columns: repeat(4, 1fr);
  }
}

@media(max-width:720px){
  .topbar{
    height: auto;
    min-height: 58px;
    flex-direction: column;
    align-items: flex-start;
    padding: 10px;
  }

  .top-right{
    width: 100%;
    align-items: flex-start;
  }

  .server{
    max-width: none;
    width: 100%;
  }

  .about-window{
    position: fixed;
    left: 10px;
    right: 10px;
    top: 82px;
    width: auto;
  }

  .btns{
    display: grid;
    grid-template-columns: 1fr 1fr;
  }

  .btn-main{
    width: 100%;
  }

  .settings-window{
    position: fixed;
    left: 10px;
    right: 10px;
    top: 120px;
    width: auto;
  }

  .stats{
    grid-template-columns: repeat(2, 1fr);
  }
}

@media(max-width:460px){
  .settings-grid{
    grid-template-columns: 1fr;
  }

  .field.full{
    grid-column: auto;
  }

  .platforms-grid{
    grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
  }
}
</style>
</head>

<body>
<div class="app">

  <header class="topbar">
    <div class="brand">
      <img class="logo" src="/bkL.png" alt="Logo">
      <div>
        <h1>Байкал Downloader 5.5.16</h1>
        <p>Умные загрузки. Без границ.</p>
      </div>
    </div>

    <div class="top-right">
      <div id="serverPill" class="server disconnected">
        <span class="server-dot"></span>
        <span id="serverPillText">Проверяю сервер...</span>
      </div>

      <details class="about-menu" id="aboutMenu">
        <summary class="btn about-btn" onmouseenter="this.title='О программе'" onmouseleave="this.title=''">ℹ</summary>

        <div class="about-window">
          <div class="about-head">
            <img class="about-logo" src="/bkL.png" alt="Logo">
            <div class="about-title">
              <b>Байкал Downloader 5.5.16</b>
              <span id="aboutVersion">версия: 5.5.16</span>
            </div>
          </div>

          <div class="about-text">
            <div>Автор: <b id="aboutAuthor">Iurii Cojocari (Time VEGAS PRO)</b></div>
            <div>Донат PayPal: <a id="aboutPaypal" href="#" onclick="openDonate(); return false;">paypal.me/studioyouar</a></div>
            <div>Донат Boosty: <a id="aboutBoosty" href="#" onclick="openBoosty(); return false;">boosty.to/time_vegas_pro</a></div>
            <div>Обновления: <span id="aboutUpdateVersion">v5.5.16</span></div>
            <div style="opacity: 0.6; font-size: 9px; margin-top: 4px; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 4px;">
              Версия ядра yt-dlp: <span id="aboutYtdlpVersion">определяется...</span>
            </div>
          </div>

          <div class="about-actions">
            <button class="btn btn-blue" onclick="openWhatsNewModal()">💡 Что нового в v5.5.16</button>
            <button class="btn" onclick="checkProgramUpdate()">🔄 Проверить обновление</button>
            <button class="btn btn-green" onclick="installProgramUpdate()">⬇ Обновить программу</button>
          </div>

          <div id="updateStatus" class="update-status">Готово к проверке обновлений.</div>
        </div>
      </details>

      
    </div>
  </header>

  <section class="controls">
    <div>
      <div class="progress-meta">
        <span id="progressLabel">Ожидание...</span>
        <span><span id="progressRatio">0 / 0</span> · <span id="progressPct">0%</span></span>
      </div>
      <div class="progress-track">
        <div id="progressBar" class="progress-fill"></div>
      </div>
    </div>

    <div class="action-row">
      <button class="btn btn-main" id="btnStart" onclick="startDownload()">▶ Скачать</button>

      <div class="btns">
        <button class="btn" onclick="pasteFromClipboard()">📋 Вставить</button>
        <button class="btn btn-red" onclick="clearLinks()">🧹 Очистить</button>
        <button class="btn btn-green" onclick="openFolder()">📁 Папка</button>

        <details class="settings">
          <summary class="btn">⚙ Настройки</summary>
          <div class="settings-window">
            <div class="settings-title">
              <span>Настройки загрузки</span>
            </div>

            <div class="settings-grid">
              <div class="field full">
                <label>Папка загрузки</label>
                <div class="input-row">
                  <input id="directory" type="text" value="%USERPROFILE%\Downloads" placeholder="%USERPROFILE%\Downloads или D:\VideoDownloads">
                  <button class="btn" onclick="browseFolder()">🔎 Обзор</button>
                  <button class="btn" onclick="openFolder()">📂</button>
                </div>
              </div>

              <div class="field full">
                <label>Качество / формат</label>
                <select id="format">
                  <option value="bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best">Лучшее MP4</option>
                  <option value="best">Лучшее любое</option>
                  <option value="bestvideo[height<=1080]+bestaudio/best[height<=1080]">1080p</option>
                  <option value="bestvideo[height<=720]+bestaudio/best[height<=720]">720p</option>
                  <option value="bestvideo[height<=480]+bestaudio/best[height<=480]">480p</option>
                  <option value="bestaudio-mp3">Только аудио (MP3)</option>
                </select>
              </div>

              <div class="field">
                <label>Сегмент YouTube, сек</label>
                <input id="segment-duration" type="number" value="12" min="1">
              </div>

              <div class="field">
                <label>Макс. длительность, сек</label>
                <input id="max-duration" type="number" value="" min="0" placeholder="без ограничения">
              </div>

              <div class="field full">
                <label>Сохранение настроек</label>
                <button class="btn btn-green" onclick="saveCurrentSettings(true, true)">💾 Сохранить настройки</button>
              </div>
            </div>
          </div>
        </details>
      </div>

      <div class="stats">
        <div class="stat">
          <b id="totalCount">0</b>
          <span>Уник.</span>
        </div>
        <div class="stat">
          <b id="doneCount">0</b>
          <span>Скачано</span>
        </div>
        <div class="stat danger" id="dupStatBox">
          <b id="duplicateCount">0</b>
          <span>Дубли</span>
        </div>
        <div class="stat">
          <b id="retainCount">0</b>
          <span>Не подд.</span>
        </div>
      </div>
    </div>
  </section>

  <main class="main" id="mainArea">

    <section class="panel platforms-panel" id="platformsPanel">
      <div class="panel-head">
        <div class="panel-title">Платформы</div>
        <div class="panel-note">сетка сама подстраивается под ширину окна</div>
      </div>
      <div class="panel-body">
        <div id="platforms" class="platforms-grid"></div>
      </div>
    </section>

    <section class="panel links-panel">
      <div class="panel-head">
        <div class="panel-title">Ссылки</div>
        <div class="panel-note">дубли будут показаны ниже и скачаны как копии</div>
      </div>

      <div class="panel-body">
        <textarea id="inputLinks" placeholder="Вставь ссылки сюда, каждая с новой строки.

Поддерживаются ВИДЕО:
YouTube (и плейлисты), RuTube, Dzen, VK, VK Video, Facebook, Instagram, TikTok, Vimeo, Twitch и др.

Поддерживается МУЗЫКА:
SoundCloud (и плейлисты), Yandex Music, Apple Music, Spotify, Bandcamp (и плейлисты/альбомы), Mixcloud.
(скачиваются в MP3 автоматически)

Платформы появятся сверху над этим окном."></textarea>

        <div id="linksInfo" class="info-box"></div>
      </div>
    </section>
  </main>

  <footer class="bottom">
    <details class="log-details" id="logDetails">
      <summary>📟 Журнал скачивания</summary>

      <div class="termbar">
        <span class="dot r"></span>
        <span class="dot y"></span>
        <span class="dot g"></span>
        <span class="term-name">журнал_скачивания.log</span>
        <span id="termStatus" class="term-status idle">● ожидание</span>
      </div>

      <div id="termBody" class="term-body">
        <span class="line-info">Ожидание...</span><br>
        <span class="line-ok">Система готова.</span><br>
        <span id="cursor" class="cursor hidden"></span>
      </div>
    </details>
  </footer>

</div>

<!-- MODAL: YouTube/SoundCloud/Bandcamp Playlist Parser -->
<div id="playlistModal" class="modal-backdrop">
  <div class="playlist-modal">
    <div class="playlist-header">
      <h3 id="playlistModalTitle">Обнаружен плейлист</h3>
      <button class="btn" style="width:30px;height:30px;padding:0;border-radius:50%;" onclick="closePlaylistModal()">✕</button>
    </div>
    <div class="playlist-body">
      <div class="playlist-controls">
        <button class="btn btn-green" onclick="toggleAllPlaylist(true)">✓ Выбрать все</button>
        <button class="btn btn-red" onclick="toggleAllPlaylist(false)">𗙚 Снять все</button>
      </div>
      <div id="playlistContainer" class="playlist-list">
        <!-- JS dynamically renders elements -->
      </div>
    </div>
    <div class="playlist-footer">
      <button class="btn" onclick="closePlaylistModal()">Отмена</button>
      <button class="btn btn-main" id="btnConfirmPlaylist" onclick="confirmPlaylistDownload()">Загрузить выбранное</button>
    </div>
  </div>
</div>

<!-- MODAL: What's New in Version -->
<div id="whatsNewModal" class="modal-backdrop">
  <div class="playlist-modal" style="width: min(540px, 100%);">
    <div class="playlist-header">
      <h3 style="color: var(--cyan); display: flex; align-items: center; gap: 8px;">
        <span>🚀 Что нового в версии 5.5.16</span>
      </h3>
      <button class="btn" style="width:30px;height:30px;padding:0;border-radius:50%;" onclick="closeWhatsNewModal()">✕</button>
    </div>
    <div class="playlist-body" style="font-family: var(--font); font-size: 13px; line-height: 1.6; color: var(--text); padding: 16px 20px; display: flex; flex-direction: column; gap: 14px;">
      
      <div style="background: rgba(34, 211, 238, 0.05); border: 1px solid rgba(34, 211, 238, 0.15); padding: 12px; border-radius: 12px;">
        <b style="color: var(--cyan); display: block; margin-bottom: 6px;">✨ Главные нововведения v5.5.16:</b>
        <ul style="padding-left: 20px; display: grid; gap: 6px; list-style-type: disc;">
          <li><b>Авто-Deno и Node.js для YouTube:</b> Полное решение ошибки <i>«This video is not available»</i>. Программа сама находит или скачивает портативный Deno/Node в папку <code>tools</code> для моментальной расшифровки алгоритмов YouTube без ручной настройки.</li>
          <li><b>Звуковые сигналы (Бипер):</b> Добавлены приятные системные звуковые сигналы на бэкенде и фронтенде по завершению скачивания!</li>
          <li><b>Авто-MP3 для музыки:</b> Spotify, Яндекс.Музыка, Apple Music, SoundCloud, Bandcamp и Mixcloud скачиваются в MP3 автоматически — без ручного переключения формата. Видео по-прежнему идёт в MP4.</li>
          <li><b>Обновления для macOS (.dmg):</b> На Mac программа сама ищет `.dmg` на GitHub, скачивает, монтирует и ставит обновление.</li>
          <li><b>Авто-снятие Gatekeeper:</b> После установки/копирования в `/Applications` автоматически выполняется `xattr -cr` — запуск без ручного ввода команды в Терминале.</li>
          <li><b>Альбомы/плейлисты Bandcamp:</b> Распознавание альбомов и интерактивный выбор треков с длительностью.</li>
          <li><b>Парсинг имён SoundCloud:</b> Красивые названия вида [Артист — Песня] вместо «Без названия».</li>
        </ul>
      </div>

    </div>
    <div class="playlist-footer">
      <button class="btn btn-main" onclick="closeWhatsNewModal()">Отлично!</button>
    </div>
  </div>
</div>

<div id="toast" class="toast"></div>

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
    }

    if(s.maxDuration !== undefined){
      document.getElementById('max-duration').value = s.maxDuration || '';
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
    maxDuration:document.getElementById('max-duration').value || ''
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
    'max-duration'
  ];

  ids.forEach(id => {
    const el = document.getElementById(id);

    if(!el){
      return;
    }

    el.addEventListener('change', () => saveCurrentSettings(true));

    if(id === 'directory' || id === 'segment-duration' || id === 'max-duration'){
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

const PLATFORMS = [
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
  youtube:u => u.includes('youtube.com') || u.includes('youtu.be'),
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
  const panel = document.getElementById('platformsPanel');

  if(!box || !panel){
    return;
  }

  const active = PLATFORMS
    .map(([id]) => id)
    .filter(id => (counts[id] || 0) > 0);

  if(!active.length){
    box.innerHTML = '';
    panel.style.display = 'none';
    return;
  }

  panel.style.display = 'block';

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

  data.entries.forEach((item, idx) => {
    const div = document.createElement('div');
    div.className = 'playlist-item';
    div.onclick = (e) => {
      if(e.target.tagName !== 'INPUT'){
        const cb = div.querySelector('input');
        cb.checked = !cb.checked;
      }
    };

    div.innerHTML = `
      <input type="checkbox" value="${idx}" checked>
      <span class="playlist-item-title" title="${escapeHtml(item.title)}">${idx + 1}. ${escapeHtml(item.title)}</span>
    `;
    container.appendChild(div);
  });

  document.getElementById('playlistModal').classList.add('show');
  document.getElementById('btnStart').disabled = false;

  setTimeout(() => {
    hideToast();
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
  if(isRunning){
    return;
  }

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

  document.getElementById('btnStart').disabled = true;
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

      if(type === 'job_done'){
        completedJobs++;
        document.getElementById('doneCount').textContent = completedJobs;

        updatePlatformProgress(data.platform, !!data.ok);
        setProgress(Math.round((completedJobs / totalJobs) * 100), false);
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

  if(btn){
    btn.disabled = false;
  }

  const bar = document.getElementById('progressBar');

  if(bar){
    bar.classList.remove('loading');
  }
}

function clearLinks(){
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
    return;
  }

  const input = document.getElementById('inputLinks');
  insertTextAtCursor(input, text);
  showToast('✓ Текст вставлен');
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
      showToast('📁 Папка выбрана');
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
  menu.style.position = 'fixed';
  menu.style.zIndex = '9999';
  menu.style.display = 'none';
  menu.style.minWidth = '190px';
  menu.style.padding = '6px';
  menu.style.borderRadius = '12px';
  menu.style.border = '1px solid rgba(125,211,252,.38)';
  menu.style.background = 'rgba(13,22,39,.98)';
  menu.style.boxShadow = '0 18px 60px rgba(0,0,0,.45)';
  menu.style.fontFamily = 'Consolas, monospace';
  menu.style.fontSize = '12px';

  menu.innerHTML = `
    <button id="rcPasteLinks" style="width:100%;height:34px;border:0;border-radius:999px;margin-bottom:5px;cursor:pointer;background:rgba(34,211,238,.16);color:#eef7ff;text-align:left;padding:0 10px;">📋 Вставить ссылки</button>
    <button id="rcPasteText" style="width:100%;height:34px;border:0;border-radius:999px;margin-bottom:5px;cursor:pointer;background:rgba(255,255,255,.07);color:#eef7ff;text-align:left;padding:0 10px;">📝 Вставить текст</button>
    <button id="rcCopy" style="width:100%;height:34px;border:0;border-radius:999px;margin-bottom:5px;cursor:pointer;background:rgba(255,255,255,.07);color:#eef7ff;text-align:left;padding:0 10px;">📄 Копировать</button>
    <button id="rcCut" style="width:100%;height:34px;border:0;border-radius:999px;cursor:pointer;background:rgba(251,73,102,.12);color:#ffb4c0;text-align:left;padding:0 10px;">✂ Вырезать</button>
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

    menu.style.left = `${Math.min(e.clientX, window.innerWidth - 210)}px`;
    menu.style.top = `${Math.min(e.clientY, window.innerHeight - 170)}px`;
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
  bindSmoothPopupDetails();

  resetPlatformProgress();
  updateCounts();

  checkServer();
  setInterval(checkServer, 5000);

  const input = document.getElementById('inputLinks');

  if(input){
    input.addEventListener('input', updateCounts);
  }

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


def job_done(platform, ok=True):
    message_queue.put(
        json.dumps(
            {
                "type": "job_done",
                "platform": platform or "generic",
                "ok": bool(ok),
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
        log("Предупреждение: JS-рантайм (Deno/Node.js) не обнаружен. Расшифровка алгоритмов YouTube может дать сбой.", "warn")
        
    if USE_BROWSER_COOKIES:
        args.extend(["--cookies-from-browser", BROWSER_COOKIES])
        
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
    actual_file = "Видео"
    started_at = time.monotonic()

    try:
        cmd = _bd_add_ytdlp_progress_args(cmd)

        # Запускаем процесс в бинарном режиме (БЕЗ text=True и БЕЗ жесткой кодировки)
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            cwd=cwd,
        )

        # Читаем сырые байты построчно
        for line_bytes in proc.stdout:
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

    cmd = [
        YTDLP_PATH,
        "--format", use_fmt,
        "--output", out_tmpl,
        "--no-playlist",
        "--newline",
        "--no-warnings"
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
        return True

    log(f"✗ Ошибка YouTube/Поиска, код {code}", "error")
    return False


def download_generic(platform, url, download_dir, fmt, max_duration=0, copy_index=1):
    # ==== ПЕРЕХВАТ И АВТОМАТИЧЕСКАЯ УСТАНОВКА MP3 ДЛЯ МУЗЫКАЛЬНЫХ САЙТОВ ====
    music_domains = ["spotify.com", "music.apple.com", "music.yandex", "soundcloud.com", "bandcamp.com", "mixcloud.com"]
    is_music_platform = any(x in url.lower() for x in music_domains) or platform in ["soundcloud", "yandexmusic", "bandcamp", "mixcloud", "applemusic", "spotify"]

    if is_music_platform:
        fmt = "bestaudio-mp3"  # Принудительно выставляем MP3
    # =========================================================================

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

    copy_suffix = get_ytdlp_collision_suffix(
        download_dir=download_dir,
        url=url,
        requested_index=copy_index,
        title_tail="",
    )

    out_tmpl = os.path.join(download_dir, f"%(title)s{copy_suffix}.%(ext)s")

    if copy_suffix:
        log(f"  Повторная/похожая ссылка {platform_clean}: сохраняю с суффиксом{copy_suffix}", "warn")

    is_mp3 = (fmt == "bestaudio-mp3")

    if platform_clean in ["instagram", "tiktok", "douyin"]:
        use_fmt = "best[ext=mp4]/best"
    else:
        use_fmt = "bestaudio/best" if is_mp3 else fmt

    cmd = [
        YTDLP_PATH,
        "--format", use_fmt,
        "--output", out_tmpl,
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

    if max_duration > 0:
        cmd += ["--download-sections", f"*0-{max_duration}"]

    cmd.append(url)

    code, actual_file = run_process(cmd, BASE_DIR, " ")

    if code == 0:
        if actual_file != "Видео" and actual_file != "Video":
            if is_mp3:
                actual_file = os.path.splitext(actual_file)[0] + ".mp3"
            log(f"✓ Готово: {os.path.basename(actual_file)}", "ok")
        else:
            log("✓ Готово: Загрузка завершена", "ok")
        return True

    log(f"✗ Ошибка платформы {platform_clean}, код {code}", "error")
    return False


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
                        return True

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
                return True
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
        return True

    log(f"✗ yt-dlp Pinterest, код {code}", "error")
    log("  Pinterest: video не удалось скачать автоматически.", "warn")
    return False


def download_pixabay(url, download_dir, copy_index=1, is_mp3=False):
    try:
        m = re.search(r"-(\d+)/?$", url)

        if not m:
            m = re.search(r"videos/(?:[^/]+-)?(\d+)", url)

        if not m:
            log("Не удалось извлечь ID Pixabay", "error")
            return False

        video_id = m.group(1)

        api_url = f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&id={video_id}"
        req = urllib.request.Request(api_url, headers={"User-Agent": "VideoDownloader/1.0"})

        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))

        if not data.get("hits"):
            log("Pixabay: video не найдено", "error")
            return False

        video_info = data["hits"][0]
        videos = video_info.get("videos", {})

        video_url = None

        for q in ["large", "medium", "small", "tiny"]:
            if videos.get(q, {}).get("url"):
                video_url = videos[q]["url"]
                break

        if not video_url:
            log("Pixabay: нет файлов", "error")
            return False

        tags = video_info.get("tags", "")

        if tags:
            clean_name = get_safe_filename(tags.replace(", ", "_").replace(" ", "_"))
            base_name = f"pixabay_{clean_name}"
        else:
            base_name = f"pixabay_{video_info.get('id', video_id)}"

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
        return True

    except Exception as e:
        log(f"✗ Pixabay: {e}", "error")
        return False


def download_pexels(url, download_dir, copy_index=1, is_mp3=False):
    try:
        m = re.search(r"video/[^/]+-(\d+)/?$", url)

        if not m:
            m = re.search(r"/(\d+)/?$", url)

        if not m:
            log("Не удалось извлечь ID Pexels", "error")
            return False

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
            return False

        best = sorted(video_files, key=lambda x: x.get("width", 0), reverse=True)[0]
        video_url = best["link"]

        url_path = info.get("url", "")
        m_slug = re.search(r"/video/([^/]+)-\d+/?", url_path)

        if m_slug:
            clean_name = get_safe_filename(m_slug.group(1).replace("-", "_"))
            base_name = f"pexels_{clean_name}"
        else:
            base_name = f"pexels_{info.get('id', video_id)}"

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
        return True

    except Exception as e:
        log(f"✗ Pexels: {e}", "error")
        return False


def run_downloads(jobs, settings):
    global is_running, start_time, FFMPEG_PATH

    is_running = True
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

        log(f"Загрузка {total} медиа", "info")
        log("─" * 50, "sep")

        for i, job in enumerate(jobs):
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
                ok = download_pixabay(url, download_dir, copy_index, is_mp3)
            elif job_type == "pexels":
                ok = download_pexels(url, download_dir, copy_index, is_mp3)
            elif job_type == "pinterest" or "pinterest.com" in url or "pin.it" in url:
                ok = download_pinterest(url, download_dir, copy_index, is_mp3)
            elif job_type == "youtube":
                ok = download_youtube(job, download_dir, fmt, segment_duration, max_duration)
            else:
                ok = download_generic(platform, url, download_dir, fmt, max_duration, copy_index)

            job_done(platform, ok)

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
        try:
            ps_initial = initial_dir.replace("'", "''")

            ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms
$dialog = New-Object System.Windows.Forms.FolderBrowserDialog
$dialog.Description = "Выберите папку для загрузок"
$dialog.SelectedPath = '{ps_initial}'
$dialog.ShowNewFolderButton = $true
$result = $dialog.ShowDialog()
if ($result -eq [System.Windows.Forms.DialogResult]::OK) {{
    Write-Output $dialog.SelectedPath
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

            if not any(url.startswith(x) for x in allowed):
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self._cors()
                self.end_headers()
                self.wfile.write(
                    json.dumps(
                        {
                            "ok": False,
                            "error": "Недопустимая ссылка",
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

        elif self.path == "/open-folder":
            data = self.read_json()
            directory = data.get("directory", DEFAULT_APP_SETTINGS["directory"]) or DEFAULT_APP_SETTINGS["directory"]

            save_app_settings(
                {
                    "directory": directory,
                }
            )

            folder_path = get_download_dir_from_setting(directory)

            os.makedirs(folder_path, exist_ok=True)

            try:
                if sys.platform == "win32":
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


if __name__ == "__main__":
    url = f"http://127.0.0.1:{PORT}"

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
