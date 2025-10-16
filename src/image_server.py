import subprocess
import sys
import socket
import threading
import time
import re
import os
import platform
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
            # Flask's path converter includes query parameters in the filename
            # We need to strip them for file serving
            # Query parameters are already handled by Flask separately
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
        # Check for bundled cloudflared first (when running from packaged app)
        cloudflared_cmd = self._find_cloudflared()
        
        # Check for system-installed tools
        has_system_cloudflared = shutil.which('cloudflared')
        has_ngrok = shutil.which('ngrok')
        
        if not cloudflared_cmd and not has_system_cloudflared and not has_ngrok:
            print("[yellow]WARNING: No tunnel tool found (cloudflared or ngrok).[/yellow]")
            print("[yellow]Images will be served from localhost and won't be accessible to Notion.[/yellow]")
            print("[yellow]To fix: Install cloudflared with 'brew install cloudflared'[/yellow]")
        
        # Prefer bundled or system cloudflared
        if cloudflared_cmd:
            self.proc = subprocess.Popen([
                cloudflared_cmd, 'tunnel', '--url', self.local_url, '--loglevel', 'info'
            ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            # Parse stdout for trycloudflare URL
            self.public_url = self._wait_cloudflared_url(timeout=10)
            if self.public_url:
                # Wait for DNS to propagate and tunnel to be accessible
                self._wait_for_tunnel_ready(self.public_url)
            return self.public_url or self.local_url
        # Fallback ngrok
        if has_ngrok:
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
    
    def _wait_for_tunnel_ready(self, url: str, timeout: int = 15) -> bool:
        """Wait for tunnel URL to be accessible"""
        import socket
        end = time.time() + timeout
        hostname = url.replace('https://', '').replace('http://', '').split('/')[0]
        
        # First wait for DNS to resolve
        while time.time() < end:
            try:
                socket.gethostbyname(hostname)
                break
            except socket.gaierror:
                time.sleep(1)
        
        # Then wait for HTTP to be accessible
        while time.time() < end:
            try:
                r = requests.get(url, timeout=3)
                if r.status_code == 200:
                    return True
            except Exception:
                pass
            time.sleep(1)
        return False

    def _find_cloudflared(self) -> Optional[str]:
        """Find bundled cloudflared binary, checking both PyInstaller and Electron contexts"""
        # Determine OS and architecture
        is_linux = sys.platform.startswith('linux')
        is_darwin = sys.platform == 'darwin'
        arch = 'arm64' if platform.machine() in ('arm64', 'aarch64') else 'amd64'
        
        # Build binary name based on platform
        if is_linux:
            binary_name = f'cloudflared-linux-{arch}'
        elif is_darwin:
            binary_name = f'cloudflared-{arch}'
        else:
            binary_name = None
        
        # Check if running from PyInstaller bundle
        if binary_name and getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # Running from PyInstaller bundle
            bundled = os.path.join(sys._MEIPASS, 'bundled_tools', binary_name)
            if os.path.exists(bundled) and os.access(bundled, os.X_OK):
                return bundled
        
        # Check if running from Electron app (via environment variable)
        if binary_name and os.environ.get('ELECTRON_RUN_AS_NODE'):
            # Try to find in app resources
            app_path = os.environ.get('APP_RESOURCE_PATH')
            if app_path:
                bundled = os.path.join(app_path, 'bundled_tools', binary_name)
                if os.path.exists(bundled) and os.access(bundled, os.X_OK):
                    return bundled
        
        # Check for project-bundled tools in dev (project root)
        project_root = Path(__file__).resolve().parents[1]
        candidates = []
        if binary_name:
            # e.g. bundled_tools/cloudflared-arm64 on mac
            candidates.append(project_root / 'bundled_tools' / binary_name)
            # also support old naming if any
            if is_darwin:
                for name in (f'cloudflared-{arch}',):
                    candidates.append(project_root / 'bundled_tools' / name)
            if is_linux:
                for name in (f'cloudflared-linux-{arch}',):
                    candidates.append(project_root / 'bundled_tools' / name)
        for c in candidates:
            if c.exists() and os.access(str(c), os.X_OK):
                return str(c)

        # Check for system-installed cloudflared
        system_cf = shutil.which('cloudflared')
        if system_cf:
            return system_cf
        
        return None
    
    def stop(self):
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except Exception:
                pass

