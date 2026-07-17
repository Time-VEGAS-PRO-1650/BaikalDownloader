# -*- coding: utf-8 -*-
"""
Байкал Downloader 5.5.9 (плейлисты, авто-Node.js, MP3, обход блокировок, звуковое оповещение)
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

    finally:
        shutdown_http_server()
