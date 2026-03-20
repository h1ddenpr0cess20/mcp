import hashlib
import json
import mimetypes
import os
import ssl
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


class FileServer:
    """Local HTTPS file server for serving screenshots and other files."""

    def __init__(
        self,
        files_dir: str | None = None,
        host: str | None = None,
        port: int | None = None,
    ):
        self.files_dir = Path(
            files_dir or os.path.expanduser(os.getenv("FILES_DIR", "~/mcp-files"))
        )
        self.host = host if host is not None else os.getenv("FILE_SERVER_HOST", "127.0.0.1")
        self.port = port if port is not None else int(os.getenv("FILE_SERVER_PORT", "9410"))
        self.files_dir.mkdir(parents=True, exist_ok=True)
        self._file_map: dict[str, dict] = {}
        self._server: HTTPServer | None = None
        self._cert_dir = Path(
            os.getenv("CERT_DIR", os.path.expanduser("~/.android_mcp_certs"))
        )

    def _ensure_certs(self) -> tuple[str, str]:
        """Generate self-signed certs if they don't exist."""
        self._cert_dir.mkdir(parents=True, exist_ok=True)
        cert_path = self._cert_dir / "cert.pem"
        key_path = self._cert_dir / "key.pem"

        if cert_path.exists() and key_path.exists():
            return str(cert_path), str(key_path)

        subprocess.run(
            [
                "openssl", "req", "-x509", "-newkey", "rsa:2048",
                "-keyout", str(key_path),
                "-out", str(cert_path),
                "-days", "365", "-nodes",
                "-subj", "/CN=localhost",
                "-addext", f"subjectAltName=DNS:localhost,IP:127.0.0.1,IP:{self.host}",
            ],
            capture_output=True,
            check=True,
        )
        return str(cert_path), str(key_path)

    @staticmethod
    def make_file_id(local_path: str) -> str:
        digest = hashlib.md5(local_path.encode()).hexdigest()[:16]
        return f"file_{digest}"

    def register(self, local_path: str, filename: str, size: int) -> dict:
        """Register a downloaded file and return metadata with a URL."""
        mime_type, _ = mimetypes.guess_type(filename)
        mime_type = mime_type or "application/octet-stream"
        file_id = self.make_file_id(local_path)

        self._file_map[file_id] = {
            "path": local_path,
            "filename": filename,
            "mime_type": mime_type,
            "size": size,
        }

        return {
            "file_id": file_id,
            "filename": filename,
            "size": size,
            "mime_type": mime_type,
            "url": f"https://{self.host}:{self.port}/files/{file_id}/content",
        }

    def start(self):
        """Start the HTTPS file server in a daemon thread."""
        cert_path, key_path = self._ensure_certs()
        file_map = self._file_map
        files_dir = self.files_dir

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                path = self.path.lstrip("/")

                # /files/<file_id>/content
                if path.startswith("files/") and path.endswith("/content"):
                    file_id = path[len("files/"):-len("/content")]
                    entry = file_map.get(file_id)
                    if not entry or not os.path.exists(entry["path"]):
                        self.send_error(404)
                        return
                    with open(entry["path"], "rb") as f:
                        data = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", entry["mime_type"])
                    self.send_header("Content-Disposition",
                                     f'inline; filename="{entry["filename"]}"')
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(data)

                # /files/<file_id>  (metadata)
                elif path.startswith("files/"):
                    file_id = path[len("files/"):]
                    entry = file_map.get(file_id)
                    if not entry:
                        self.send_error(404)
                        return
                    body = json.dumps({
                        "id": file_id,
                        "filename": entry["filename"],
                        "mime_type": entry["mime_type"],
                        "bytes": entry["size"],
                    }).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(body)

                # /<filename>  (legacy direct path)
                else:
                    filename = os.path.basename(path)
                    local_path = str(files_dir / filename)
                    if not os.path.exists(local_path):
                        self.send_error(404)
                        return
                    mime_type, _ = mimetypes.guess_type(filename)
                    with open(local_path, "rb") as f:
                        data = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", mime_type or "application/octet-stream")
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(data)

            def log_message(self, *args, **kwargs):
                pass

        self._server = HTTPServer((self.host, self.port), _Handler)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(cert_path, key_path)
        self._server.socket = ctx.wrap_socket(self._server.socket, server_side=True)
        thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        thread.start()
