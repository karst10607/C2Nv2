import socket
import threading
from pathlib import Path
from typing import Optional
from flask import Flask, send_from_directory

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
