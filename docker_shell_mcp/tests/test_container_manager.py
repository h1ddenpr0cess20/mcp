import subprocess
from unittest.mock import patch

from docker_shell_client import ContainerManager


def completed(code=0, stdout="", stderr=""):
    return subprocess.CompletedProcess([], code, stdout, stderr)


def test_ensure_running_reuses_running_container(monkeypatch):
    monkeypatch.setenv("DOCKER_CONTAINER", "test-sandbox")
    manager = ContainerManager()
    with patch.object(manager, "_docker", side_effect=[completed(), completed(stdout="running\n")]) as docker:
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
    with patch.object(manager, "_docker", side_effect=[completed(), completed(stdout="exited\n"), completed()]) as docker:
        manager.ensure_running()
    assert docker.call_args_list[-1].args == ("start", manager.container_name)


def test_ensure_running_builds_and_creates_missing_container():
    manager = ContainerManager()
    with patch.object(manager, "_docker", side_effect=[
        completed(), completed(code=1), completed(code=1), completed(), completed()
    ]) as docker:
        manager.ensure_running()
    commands = [call.args for call in docker.call_args_list]
    assert ("build", "--tag", manager.image, str(manager.dockerfile_dir)) in commands
    assert any(command[:2] == ("run", "--detach") for command in commands)


def test_exec_uses_argv_and_interactive_stdin():
    manager = ContainerManager()
    with patch.object(manager, "ensure_running"), patch.object(manager, "_docker", return_value=completed()) as docker:
        manager.exec(["tee", "--", "/tmp/a file"], input_text="hello", check=True)
    assert docker.call_args.args[:4] == ("exec", "--interactive", "--workdir", manager.workdir)
    assert docker.call_args.kwargs["input_text"] == "hello"
