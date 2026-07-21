import hashlib
import json
import mimetypes
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


class FileServer:
    """Local HTTP server for files copied out of the Colab runtime."""

    def __init__(self, files_dir=None, host=None, port=None):
        self.files_dir = Path(files_dir or os.path.expanduser(os.getenv("FILES_DIR", "~/mcp-files")))
        self.host = host if host is not None else os.getenv("FILE_SERVER_HOST", "127.0.0.1")
        self.port = port if port is not None else int(os.getenv("FILE_SERVER_PORT", "9631"))
        self.files_dir.mkdir(parents=True, exist_ok=True)
        self._file_map = {}
        self._server = None

    @staticmethod
    def make_file_id(local_path):
        return f"file_{hashlib.md5(local_path.encode()).hexdigest()[:16]}"

    def register(self, local_path, filename, size):
        mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        file_id = self.make_file_id(local_path)
        self._file_map[file_id] = {"path": local_path, "filename": filename, "mime_type": mime_type, "size": size}
        return {"file_id": file_id, "filename": filename, "size": size, "mime_type": mime_type,
                "url": f"http://{self.host}:{self.port}/files/{file_id}/content"}

    def start(self):
        file_map = self._file_map

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                path = self.path.lstrip("/")
                if path.startswith("files/") and path.endswith("/content"):
                    file_id = path[len("files/"):-len("/content")]
                    entry = file_map.get(file_id)
                    if not entry or not os.path.exists(entry["path"]):
                        self.send_error(404)
                        return
                    with open(entry["path"], "rb") as handle:
                        body = handle.read()
                    self.send_response(200)
                    self.send_header("Content-Type", entry["mime_type"])
                    safe_name = entry["filename"].replace("\\", "_").replace('"', "_")
                    self.send_header("Content-Disposition", f'attachment; filename="{safe_name}"')
                elif path.startswith("files/"):
                    file_id = path[len("files/"):]
                    entry = file_map.get(file_id)
                    if not entry:
                        self.send_error(404)
                        return
                    body = json.dumps({"id": file_id, "filename": entry["filename"],
                                       "mime_type": entry["mime_type"], "bytes": entry["size"]}).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                else:
                    self.send_error(404)
                    return
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args, **_kwargs):
                pass

        self._server = HTTPServer((self.host, self.port), Handler)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
