"""Tests for image validation and storage."""

import pytest

from blog_app.media import MAX_IMAGE_BYTES, detect_image_type, media_path, save_image
from blog_app.store import BlogError
from tests.conftest import GIF, JPEG, PNG, WEBP


class TestDetectImageType:
    @pytest.mark.unit
    @pytest.mark.parametrize("data,kind", [(PNG, "png"), (JPEG, "jpg"), (GIF, "gif"), (WEBP, "webp"), (b"GIF87a" + b"0" * 9, "gif")])
    def test_recognizes_real_formats_by_content(self, data, kind):
        assert detect_image_type(data) == kind

    @pytest.mark.unit
    @pytest.mark.parametrize("data", [
        b"", b"hello", b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>",
        b"<html><script>alert(1)</script></html>", b"RIFF\x00\x00\x00\x00WAVEfmt ", b"%PDF-1.7", b"MZ\x90\x00", b"\x89PNG",
    ])
    def test_rejects_everything_else(self, data):
        assert detect_image_type(data) is None


class TestSaveImage:
    @pytest.mark.unit
    def test_stores_under_a_random_name_with_the_detected_extension(self, tmp_path):
        name = save_image(tmp_path / "media", PNG)
        assert name.endswith(".png") and len(name) == 36
        assert (tmp_path / "media" / name).read_bytes() == PNG

    @pytest.mark.unit
    def test_names_are_unique(self, tmp_path):
        assert len({save_image(tmp_path, PNG) for _ in range(20)}) == 20

    @pytest.mark.unit
    def test_extension_comes_from_the_content_not_the_caller(self, tmp_path):
        assert save_image(tmp_path, JPEG).endswith(".jpg")

    @pytest.mark.unit
    def test_rejects_non_images_and_leaves_nothing_behind(self, tmp_path):
        with pytest.raises(BlogError, match="PNG, JPEG, GIF, and WebP"):
            save_image(tmp_path, b"<svg onload=alert(1)>")
        assert list(tmp_path.iterdir()) == []

    @pytest.mark.unit
    def test_rejects_empty(self, tmp_path):
        with pytest.raises(BlogError, match="empty"):
            save_image(tmp_path, b"")

    @pytest.mark.unit
    def test_rejects_oversized(self, tmp_path):
        with pytest.raises(BlogError, match="at most"):
            save_image(tmp_path, PNG + b"0" * MAX_IMAGE_BYTES)

    @pytest.mark.unit
    def test_accepts_exactly_the_limit(self, tmp_path):
        assert save_image(tmp_path, PNG + b"0" * (MAX_IMAGE_BYTES - len(PNG)))


class TestMediaPath:
    @pytest.mark.unit
    def test_finds_a_stored_file(self, tmp_path):
        name = save_image(tmp_path, GIF)
        assert media_path(tmp_path, name) == tmp_path / name

    @pytest.mark.unit
    @pytest.mark.parametrize("name", [
        "../etc/passwd", "..%2f..%2fetc%2fpasswd", "/etc/passwd", "a" * 32 + ".png", "a" * 32 + ".svg", "a" * 32 + ".png/../x",
        "A" * 32 + ".png", ("a" * 32 + ".png\n"), "", ".", "..", "blog.db", "secret_key", "g" * 32 + ".png",
    ])
    def test_refuses_any_name_we_would_not_have_generated(self, tmp_path, name):
        (tmp_path / "secret_key").write_text("x")
        assert media_path(tmp_path, name) is None

    @pytest.mark.unit
    def test_a_trailing_newline_is_not_forgiven_even_if_such_a_file_exists(self, tmp_path):
        name = "a" * 32 + ".png\n"
        (tmp_path / name).write_bytes(PNG)
        assert media_path(tmp_path, name) is None

    @pytest.mark.unit
    def test_missing_file(self, tmp_path):
        assert media_path(tmp_path, "0" * 32 + ".png") is None
