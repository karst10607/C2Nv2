import subprocess
import sys
import socket
import threading
import time
import re
from pathlib import Path
from typing import Optional
from flask import Flask, send_from_directory
import shutil
import requests

class StaticServer:
    def __init__(self, root: Path, host: str = "127.0.0.1", port: Optional[int] = None):
        self.root = Path(root)
        self.host = host
        self.port = port or self._find_free_port()
        self.app = Flask(__name__, static_folder=None)
        self._setup_routes()
        self._thread: Optional[threading.Thread] = None

    def _setup_routes(self):
        @self.app.route('/<path:filename>')
        def serve_file(filename):
            return send_from_directory(self.root, filename)

        @self.app.route('/')
        def index():
            return 'OK'

    @staticmethod
    def _find_free_port() -> int:
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()
        return port

    def start(self):
        def run():
            self.app.run(host=self.host, port=self.port, debug=False, use_reloader=False)
        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

class Tunnel:
    def __init__(self, local_url: str):
        self.local_url = local_url
        self.proc: Optional[subprocess.Popen] = None
        self.public_url: Optional[str] = None

    def start(self) -> str:
        # Prefer cloudflared
        if shutil.which('cloudflared'):
            self.proc = subprocess.Popen([
                'cloudflared', 'tunnel', '--url', self.local_url, '--loglevel', 'info'
            ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            # Parse stdout for trycloudflare URL
            self.public_url = self._wait_cloudflared_url(timeout=10)
            return self.public_url or self.local_url
        # Fallback ngrok
        if shutil.which('ngrok'):
            self.proc = subprocess.Popen(['ngrok', 'http', self.local_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # Try local API to get tunnel public URL
            self.public_url = self._wait_ngrok_url(timeout=10)
            return self.public_url or self.local_url
        # No tunnel available
        return self.local_url

    def _wait_cloudflared_url(self, timeout: int = 10) -> Optional[str]:
        if not self.proc or not self.proc.stdout:
            return None
        url_re = re.compile(r"https?://[\w.-]+\.trycloudflare\.com")
        end = time.time() + timeout
        lines = []
        while time.time() < end:
            try:
                line = self.proc.stdout.readline()
            except Exception:
                break
            if not line:
                time.sleep(0.2)
                continue
            lines.append(line)
            m = url_re.search(line)
            if m:
                return m.group(0)
        return None

    def _wait_ngrok_url(self, timeout: int = 10) -> Optional[str]:
        end = time.time() + timeout
        while time.time() < end:
            try:
                r = requests.get('http://127.0.0.1:4040/api/tunnels', timeout=1)
                if r.ok:
                    data = r.json()
                    tunnels = data.get('tunnels') or []
                    for t in tunnels:
                        pub = t.get('public_url')
                        if pub and pub.startswith(('http://','https://')):
                            return pub
            except Exception:
                pass
            time.sleep(0.5)
        return None

    def stop(self):
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except Exception:
                pass

