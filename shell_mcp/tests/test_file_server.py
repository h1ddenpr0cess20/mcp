import json
import urllib.request

import pytest

from shell_client.file_server import FileServer


@pytest.fixture
def file_server(tmp_path):
    """Start a FileServer on a random-ish port with a temp files dir."""
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


class TestRegister:
    def test_returns_metadata(self, tmp_path):
        server = FileServer(files_dir=str(tmp_path), host="127.0.0.1", port=9999)
        result = server.register("/tmp/report.pdf", "report.pdf", 2048)

        assert result["filename"] == "report.pdf"
        assert result["size"] == 2048
        assert result["mime_type"] == "application/pdf"
        assert "file_" in result["file_id"]
        assert "9999" in result["url"]

    def test_unknown_extension_defaults_to_octet_stream(self, tmp_path):
        server = FileServer(files_dir=str(tmp_path), host="127.0.0.1", port=9999)
        result = server.register("/tmp/data.xyz123", "data.xyz123", 100)
        assert result["mime_type"] == "application/octet-stream"


class TestHTTPServing:
    def test_file_content_endpoint(self, file_server, tmp_path):
        test_file = tmp_path / "hello.txt"
        test_file.write_text("hello world")
        meta = file_server.register(str(test_file), "hello.txt", 11)

        url = f"http://127.0.0.1:{file_server.port}/files/{meta['file_id']}/content"
        with urllib.request.urlopen(url) as resp:
            assert resp.read() == b"hello world"
            assert resp.headers["Content-Type"] == "text/plain"

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

    def test_404_for_missing_legacy_path(self, file_server):
        url = f"http://127.0.0.1:{file_server.port}/no_such_file.txt"
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(url)
        assert exc_info.value.code == 404
