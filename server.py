# -*- coding: utf-8 -*-
"""
Байкал Downloader 5.6.12 (плейлисты, авто-Deno, авто-Node.js, MP3, обход блокировок, прямые ссылки)
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
