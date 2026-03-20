import subprocess
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_subprocess_run(mocker):
    """Mock subprocess.run for ADB command unit tests."""
    mock_result = MagicMock(spec=subprocess.CompletedProcess)
    mock_result.stdout = ""
    mock_result.stderr = ""
    mock_result.returncode = 0
    mock_run = mocker.patch("subprocess.run", return_value=mock_result)
    return mock_run, mock_result


@pytest.fixture
def adb_client(monkeypatch, mock_subprocess_run):
    """Create an ADBClient with mocked subprocess."""
    monkeypatch.delenv("ADB_HOST", raising=False)
    monkeypatch.delenv("ADB_SERIAL", raising=False)
    monkeypatch.setenv("ADB_TIMEOUT", "10")

    from android_client.client import ADBClient

    return ADBClient()


@pytest.fixture
def adb_client_serial(monkeypatch, mock_subprocess_run):
    """Create an ADBClient with a serial number configured."""
    monkeypatch.delenv("ADB_HOST", raising=False)
    monkeypatch.setenv("ADB_SERIAL", "emulator-5554")
    monkeypatch.setenv("ADB_TIMEOUT", "10")

    from android_client.client import ADBClient

    return ADBClient()
