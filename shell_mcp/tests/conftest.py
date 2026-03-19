import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_ssh_client(mocker):
    """Mock paramiko.SSHClient for unit tests."""
    mock_client = mocker.MagicMock()
    mock_transport = mocker.MagicMock()
    mock_transport.is_active.return_value = True
    mock_client.get_transport.return_value = mock_transport

    mock_stdin = MagicMock()
    mock_stdout = MagicMock()
    mock_stderr = MagicMock()
    mock_stdout.read.return_value = b""
    mock_stderr.read.return_value = b""
    mock_stdout.channel.recv_exit_status.return_value = 0
    mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

    mocker.patch("paramiko.SSHClient", return_value=mock_client)
    return mock_client
