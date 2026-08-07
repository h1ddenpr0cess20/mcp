import json
import urllib.request

import pytest

from webshell_client.file_server import FileServer


@pytest.fixture
def file_server(tmp_path):
    """Start a FileServer on an ephemeral port with a temp files dir."""
    server = FileServer(files_dir=str(tmp_path), host="127.0.0.1", port=0)
    server.start()
    # HTTPServer picks an ephemeral port when given port=0
    server.port = server._server.server_address[1]
    yield server
    server._server.shutdown()


class TestMakeFileId:
    def test_deterministic(self):
        a = FileServer.make_file_id("/some/path.pdf")
        b = FileServer.make_file_id("/some/path.pdf")
        assert a == b

    def test_has_prefix(self):
        fid = FileServer.make_file_id("/any/path")
        assert fid.startswith("file_")

    def test_different_paths_different_ids(self):
        a = FileServer.make_file_id("/a.txt")
        b = FileServer.make_file_id("/b.txt")
        assert a != b

    def test_id_length_is_consistent(self):
        fid = FileServer.make_file_id("/some/path.pdf")
        # "file_" + 16 hex chars
        assert len(fid) == 5 + 16


class TestRegister:
    def test_returns_metadata(self, tmp_path):
        server = FileServer(files_dir=str(tmp_path), host="127.0.0.1", port=9999)
        result = server.register("/tmp/report.pdf", "report.pdf", 2048)

        assert result["filename"] == "report.pdf"
        assert result["size"] == 2048
        assert result["mime_type"] == "application/pdf"
        assert "file_" in result["file_id"]
        assert result["url"] == f"http://127.0.0.1:9999/files/{result['file_id']}/content"

    def test_unknown_extension_defaults_to_octet_stream(self, tmp_path):
        server = FileServer(files_dir=str(tmp_path), host="127.0.0.1", port=9999)
        result = server.register("/tmp/data.xyz123", "data.xyz123", 100)
        assert result["mime_type"] == "application/octet-stream"

    def test_registers_to_internal_file_map(self, tmp_path):
        server = FileServer(files_dir=str(tmp_path), host="127.0.0.1", port=9999)
        result = server.register("/tmp/doc.txt", "doc.txt", 500)
        file_id = result["file_id"]

        assert file_id in server._file_map
        assert server._file_map[file_id]["path"] == "/tmp/doc.txt"
        assert server._file_map[file_id]["filename"] == "doc.txt"
        assert server._file_map[file_id]["size"] == 500

    def test_overwrite_same_path_keeps_same_id(self, tmp_path):
        server = FileServer(files_dir=str(tmp_path), host="127.0.0.1", port=9999)
        r1 = server.register("/tmp/report.pdf", "report.pdf", 1000)
        r2 = server.register("/tmp/report.pdf", "report.pdf", 2000)
        assert r1["file_id"] == r2["file_id"]
        # Latest registration should update the size in the map
        assert server._file_map[r2["file_id"]]["size"] == 2000

    def test_common_mime_types(self, tmp_path):
        server = FileServer(files_dir=str(tmp_path), host="127.0.0.1", port=9999)
        cases = {
            "image.png": "image/png",
            "data.json": "application/json",
            "page.html": "text/html",
            "archive.zip": "application/zip",
        }
        for filename, expected_mime in cases.items():
            result = server.register(f"/tmp/{filename}", filename, 100)
            assert result["mime_type"] == expected_mime, f"Wrong mime for {filename}"


class TestHTTPServing:
    def test_file_content_endpoint(self, file_server, tmp_path):
        test_file = tmp_path / "hello.txt"
        test_file.write_text("hello world")
        meta = file_server.register(str(test_file), "hello.txt", 11)

        url = f"http://127.0.0.1:{file_server.port}/files/{meta['file_id']}/content"
        with urllib.request.urlopen(url) as resp:
            assert resp.read() == b"hello world"
            assert resp.headers["Content-Type"] == "text/plain"
            assert resp.headers["Content-Disposition"] == 'attachment; filename="hello.txt"'

    def test_file_metadata_endpoint(self, file_server, tmp_path):
        test_file = tmp_path / "data.json"
        test_file.write_text('{"key": "value"}')
        meta = file_server.register(str(test_file), "data.json", 16)

        url = f"http://127.0.0.1:{file_server.port}/files/{meta['file_id']}"
        with urllib.request.urlopen(url) as resp:
            body = json.loads(resp.read())
            assert body["id"] == meta["file_id"]
            assert body["filename"] == "data.json"
            assert body["mime_type"] == "application/json"
            assert body["bytes"] == 16

    def test_legacy_direct_path(self, file_server, tmp_path):
        test_file = tmp_path / "legacy.txt"
        test_file.write_text("legacy content")

        url = f"http://127.0.0.1:{file_server.port}/legacy.txt"
        with urllib.request.urlopen(url) as resp:
            assert resp.read() == b"legacy content"

    def test_404_for_missing_file_id(self, file_server):
        url = f"http://127.0.0.1:{file_server.port}/files/nonexistent/content"
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(url)
        assert exc_info.value.code == 404

    def test_404_for_missing_metadata(self, file_server):
        url = f"http://127.0.0.1:{file_server.port}/files/nonexistent"
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(url)
        assert exc_info.value.code == 404

    def test_404_for_missing_legacy_path(self, file_server):
        url = f"http://127.0.0.1:{file_server.port}/no_such_file.txt"
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(url)
        assert exc_info.value.code == 404

    def test_404_when_registered_file_deleted_from_disk(self, file_server, tmp_path):
        test_file = tmp_path / "ephemeral.txt"
        test_file.write_text("temporary")
        meta = file_server.register(str(test_file), "ephemeral.txt", 9)
        test_file.unlink()  # file removed after registration

        url = f"http://127.0.0.1:{file_server.port}/files/{meta['file_id']}/content"
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(url)
        assert exc_info.value.code == 404


class TestFileServerInit:
    def test_creates_files_dir(self, tmp_path):
        files_dir = tmp_path / "subdir" / "files"
        FileServer(files_dir=str(files_dir), host="127.0.0.1", port=0)
        assert files_dir.exists()

    def test_defaults_from_env(self, monkeypatch, tmp_path):
        monkeypatch.setenv("FILES_DIR", str(tmp_path / "env-files"))
        monkeypatch.setenv("FILE_SERVER_HOST", "0.0.0.0")
        monkeypatch.setenv("FILE_SERVER_PORT", "7777")

        server = FileServer()
        assert server.host == "0.0.0.0"
        assert server.port == 7777

    def test_explicit_args_override_env(self, monkeypatch, tmp_path):
        monkeypatch.setenv("FILE_SERVER_HOST", "0.0.0.0")
        monkeypatch.setenv("FILE_SERVER_PORT", "7777")

        server = FileServer(files_dir=str(tmp_path), host="192.168.1.1", port=8888)
        assert server.host == "192.168.1.1"
        assert server.port == 8888
