
from firetv_client.client import ADBClient
from firetv_client.media import MediaController, FIRETV_KEYS


def _make_media(monkeypatch, mock_subprocess_run):
    monkeypatch.delenv("FIRETV_HOST", raising=False)
    monkeypatch.delenv("ADB_HOST", raising=False)
    monkeypatch.delenv("ADB_SERIAL", raising=False)
    monkeypatch.setenv("ADB_TIMEOUT", "10")
    client = ADBClient()
    return MediaController(client)


class TestNavigate:
    """Unit tests for MediaController.navigate."""

    def test_navigate_up(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.returncode = 0

        media = _make_media(monkeypatch, mock_subprocess_run)
        media.navigate("up")

        args = mock_run.call_args[0][0]
        assert "KEYCODE_DPAD_UP" in args[2]

    def test_navigate_select(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.returncode = 0

        media = _make_media(monkeypatch, mock_subprocess_run)
        media.navigate("select")

        args = mock_run.call_args[0][0]
        assert "KEYCODE_DPAD_CENTER" in args[2]

    def test_navigate_back(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.returncode = 0

        media = _make_media(monkeypatch, mock_subprocess_run)
        media.navigate("back")

        args = mock_run.call_args[0][0]
        assert "KEYCODE_BACK" in args[2]

    def test_navigate_unknown_key_adds_prefix(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.returncode = 0

        media = _make_media(monkeypatch, mock_subprocess_run)
        media.navigate("F1")

        args = mock_run.call_args[0][0]
        assert "KEYCODE_F1" in args[2]


class TestNavigateRepeat:
    """Unit tests for MediaController.navigate_repeat."""

    def test_navigate_repeat_calls_multiple_times(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.returncode = 0

        media = _make_media(monkeypatch, mock_subprocess_run)
        result = media.navigate_repeat("down", count=3, delay_ms=0)

        assert mock_run.call_count == 3
        assert result["count"] == 3

    def test_navigate_repeat_returns_last_result(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.returncode = 0

        media = _make_media(monkeypatch, mock_subprocess_run)
        result = media.navigate_repeat("right", count=2, delay_ms=0)

        assert "count" in result
        assert result["count"] == 2


class TestInputText:
    """Unit tests for MediaController.input_text."""

    def test_input_text_escapes_spaces(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.returncode = 0

        media = _make_media(monkeypatch, mock_subprocess_run)
        media.input_text("hello world")

        args = mock_run.call_args[0][0]
        assert "%s" in args[2]

    def test_clear_input_sends_del_keys(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.returncode = 0

        media = _make_media(monkeypatch, mock_subprocess_run)
        media.clear_input(5)

        args = mock_run.call_args[0][0]
        assert args[2].count("KEYCODE_DEL") == 5


class TestMediaControl:
    """Unit tests for media playback controls."""

    def test_play(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.returncode = 0

        media = _make_media(monkeypatch, mock_subprocess_run)
        media.media_control("play")

        args = mock_run.call_args[0][0]
        assert "KEYCODE_MEDIA_PLAY" in args[2]

    def test_pause(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.returncode = 0

        media = _make_media(monkeypatch, mock_subprocess_run)
        media.media_control("pause")

        args = mock_run.call_args[0][0]
        assert "KEYCODE_MEDIA_PAUSE" in args[2]


class TestVolume:
    """Unit tests for MediaController volume methods."""

    def test_volume_up(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.returncode = 0

        media = _make_media(monkeypatch, mock_subprocess_run)
        media.volume("volume_up")

        args = mock_run.call_args[0][0]
        assert "KEYCODE_VOLUME_UP" in args[2]

    def test_mute(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.returncode = 0

        media = _make_media(monkeypatch, mock_subprocess_run)
        media.volume("mute")

        args = mock_run.call_args[0][0]
        assert "KEYCODE_VOLUME_MUTE" in args[2]


class TestNowPlaying:
    """Unit tests for MediaController.now_playing."""

    SAMPLE_DUMPSYS = """
SessionRecord{abc com.netflix.ninja/..., ...}
  package=com.netflix.ninja
  description=null
  metadata=Media2Description{title=Stranger Things, artist=Netflix, album=Season 4}
  state=PlaybackState {state=3, position=120000, bufferedPosition=0, speed=1.0, ...}
  duration=3600000
"""

    def test_now_playing_parses_app(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = self.SAMPLE_DUMPSYS
        mock_result.returncode = 0

        media = _make_media(monkeypatch, mock_subprocess_run)
        result = media.now_playing()

        assert result["app"] == "com.netflix.ninja"

    def test_now_playing_parses_state_playing(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = self.SAMPLE_DUMPSYS
        mock_result.returncode = 0

        media = _make_media(monkeypatch, mock_subprocess_run)
        result = media.now_playing()

        assert result["state"] == "playing"

    def test_now_playing_state_paused(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = "state=PlaybackState {state=2"
        mock_result.returncode = 0

        media = _make_media(monkeypatch, mock_subprocess_run)
        result = media.now_playing()

        assert result["state"] == "paused"

    def test_now_playing_parses_position(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = self.SAMPLE_DUMPSYS
        mock_result.returncode = 0

        media = _make_media(monkeypatch, mock_subprocess_run)
        result = media.now_playing()

        assert result["position_ms"] == 120000
        assert result["duration_ms"] == 3600000

    def test_now_playing_returns_error_on_failure(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.stderr = "error"
        mock_result.returncode = 1

        media = _make_media(monkeypatch, mock_subprocess_run)
        result = media.now_playing()

        assert result["exit_code"] == 1


class TestWakeSleep:
    """Unit tests for MediaController.wake and sleep."""

    def test_wake(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.returncode = 0

        media = _make_media(monkeypatch, mock_subprocess_run)
        media.wake()

        args = mock_run.call_args[0][0]
        assert "KEYCODE_WAKEUP" in args[2]

    def test_sleep(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.returncode = 0

        media = _make_media(monkeypatch, mock_subprocess_run)
        media.sleep()

        args = mock_run.call_args[0][0]
        assert "KEYCODE_SLEEP" in args[2]


class TestFireTVKeys:
    """Sanity checks on the FIRETV_KEYS constant."""

    def test_all_navigation_keys_present(self):
        for key in ["up", "down", "left", "right", "select", "back", "home", "menu"]:
            assert key in FIRETV_KEYS

    def test_all_media_keys_present(self):
        for key in ["play", "pause", "play_pause", "stop", "next", "previous",
                    "rewind", "fast_forward"]:
            assert key in FIRETV_KEYS

    def test_all_volume_keys_present(self):
        for key in ["volume_up", "volume_down", "mute"]:
            assert key in FIRETV_KEYS
