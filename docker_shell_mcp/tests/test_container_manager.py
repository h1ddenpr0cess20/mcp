import subprocess
from unittest.mock import patch

import pytest

from docker_shell_client import ContainerManager


def completed(code=0, stdout="", stderr=""):
    return subprocess.CompletedProcess([], code, stdout, stderr)


def test_ensure_running_reuses_running_container(monkeypatch):
    monkeypatch.setenv("DOCKER_CONTAINER", "test-sandbox")
    manager = ContainerManager()
    with patch.object(manager, "ensure_image", return_value=False), \
            patch.object(manager, "_docker", side_effect=[completed(), completed(stdout="running\n")]) as docker:
        manager.ensure_running()
    assert docker.call_count == 2


def test_docker_command_defaults_to_sudo_docker(monkeypatch):
    monkeypatch.delenv("DOCKER_COMMAND", raising=False)
    assert ContainerManager().docker_command == ["sudo", "-n", "docker"]


def test_docker_command_can_be_overridden(monkeypatch):
    monkeypatch.setenv("DOCKER_COMMAND", "docker")
    assert ContainerManager().docker_command == ["docker"]


def test_ensure_running_starts_stopped_container():
    manager = ContainerManager()
    with patch.object(manager, "ensure_image", return_value=False), \
            patch.object(manager, "_docker", side_effect=[completed(), completed(stdout="exited\n"), completed()]) as docker:
        manager.ensure_running()
    assert docker.call_args_list[-1].args == ("start", manager.container_name)


def test_ensure_running_builds_and_creates_missing_container():
    manager = ContainerManager()
    with patch.object(manager, "_docker", side_effect=[
        completed(), completed(code=1), completed(code=1), completed()
    ]) as docker, patch.object(manager, "build_image") as build:
        manager.ensure_running()
    build.assert_called_once()
    commands = [call.args for call in docker.call_args_list]
    assert any(command[:2] == ("run", "--detach") for command in commands)


def test_ensure_running_recreates_container_after_rebuild():
    manager = ContainerManager()
    with patch.object(manager, "image_exists", return_value=True), \
            patch.object(manager, "image_is_stale", return_value=True), \
            patch.object(manager, "build_image"), \
            patch.object(manager, "_docker", side_effect=[
                completed(), completed(stdout="running\n"), completed(), completed()
            ]) as docker:
        manager.ensure_running()
    commands = [call.args for call in docker.call_args_list]
    assert ("rm", "--force", manager.container_name) in commands
    assert any(command[:2] == ("run", "--detach") for command in commands)


def test_image_is_stale_compares_dockerfile_hash():
    manager = ContainerManager()
    with patch.object(manager, "_docker", return_value=completed(stdout="deadbeef\n")):
        assert manager.image_is_stale()
    with patch.object(manager, "_docker", return_value=completed(stdout=f"{manager.dockerfile_hash()}\n")):
        assert not manager.image_is_stale()


def test_exec_uses_argv_and_interactive_stdin():
    manager = ContainerManager()
    with patch.object(manager, "_require_ready"), patch.object(manager, "_docker", return_value=completed()) as docker:
        manager.exec(["tee", "--", "/tmp/a file"], input_text="hello", check=True)
    assert docker.call_args.args[:4] == ("exec", "--interactive", "--workdir", manager.workdir)
    assert docker.call_args.kwargs["input_text"] == "hello"


def test_exec_fails_fast_while_sandbox_is_building():
    manager = ContainerManager()
    with patch.object(manager, "start_background_setup") as setup:
        with pytest.raises(RuntimeError, match="still being prepared"):
            manager.exec(["true"])
    setup.assert_called_once()


def test_exec_reports_setup_error_and_retries():
    manager = ContainerManager()
    manager._setup_error = "build exploded"
    with patch.object(manager, "start_background_setup") as setup:
        with pytest.raises(RuntimeError, match="build exploded"):
            manager.exec(["true"])
    setup.assert_called_once()


def test_exec_runs_normally_once_ready():
    manager = ContainerManager()
    manager._ready.set()
    with patch.object(manager, "ensure_running"), patch.object(manager, "_docker", return_value=completed()) as docker:
        result = manager.exec(["true"])
    assert result.returncode == 0
    assert docker.call_args.args[0] == "exec"
