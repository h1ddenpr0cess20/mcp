import subprocess
import time
from unittest.mock import patch

import pytest

from docker_shell_client import ContainerManager
from docker_shell_client.container_manager import DOCKER_COMMAND_CANDIDATES


def completed(code=0, stdout="", stderr=""):
    return subprocess.CompletedProcess([], code, stdout, stderr)


@pytest.fixture
def manager(monkeypatch):
    """A manager with the Docker command already resolved, as after setup."""
    monkeypatch.delenv("DOCKER_COMMAND", raising=False)
    manager = ContainerManager()
    manager._docker_command_resolved = True
    return manager


def test_ensure_running_reuses_running_container(monkeypatch, manager):
    with patch.object(manager, "ensure_image", return_value=False), \
            patch.object(manager, "container_image_changed", return_value=False), \
            patch.object(manager, "_docker", side_effect=[completed(stdout="running\n")]) as docker:
        manager.ensure_running()
    assert docker.call_count == 1


def test_ephemeral_defaults_to_enabled(monkeypatch):
    monkeypatch.delenv("DOCKER_EPHEMERAL", raising=False)
    assert ContainerManager().ephemeral is True


def test_ephemeral_can_be_disabled(monkeypatch):
    monkeypatch.setenv("DOCKER_EPHEMERAL", "false")
    assert ContainerManager().ephemeral is False


def test_reset_for_new_session_discards_container_and_volume(manager):
    with patch.object(manager, "_docker", return_value=completed()) as docker:
        manager.reset_for_new_session()
    commands = [call.args for call in docker.call_args_list]
    assert ("rm", "--force", manager.container_name) in commands
    assert ("volume", "rm", "--force", manager.volume) in commands


def test_reset_runs_only_once_per_process(manager):
    """A retry or a mid-session repair must not wipe the workspace in use."""
    with patch.object(manager, "_docker", return_value=completed()) as docker:
        manager.reset_for_new_session()
        first_call_count = docker.call_count
        manager.reset_for_new_session()
    assert docker.call_count == first_call_count


def test_reset_tolerates_missing_container_and_volume(manager):
    """First launch has nothing to discard; that must not abort setup."""
    no_container = completed(code=1, stderr="Error: No such container: shell-mcp-sandbox")
    no_volume = completed(code=1, stderr="Error: No such volume: shell-mcp-data")
    with patch.object(manager, "_docker", side_effect=[no_container, no_volume]):
        manager.reset_for_new_session()
    assert manager._reset_done


def test_reset_warns_but_continues_when_volume_is_in_use(manager):
    in_use = completed(code=1, stderr="Error response from daemon: volume is in use")
    logs = []
    with patch.object(manager, "_docker", return_value=completed()) as docker, \
            patch.object(manager, "_log", side_effect=logs.append):
        docker.side_effect = [completed(), in_use]
        manager.reset_for_new_session()
    assert any("could not remove volume" in message.lower() for message in logs)


def test_setup_resolves_then_resets_then_starts_when_ephemeral(monkeypatch):
    """The reset issues Docker commands, so the command must be resolved first."""
    monkeypatch.setenv("DOCKER_EPHEMERAL", "true")
    manager = ContainerManager()
    calls = []
    with patch.object(manager, "resolve_docker_command", side_effect=lambda: calls.append("resolve")), \
            patch.object(manager, "reset_for_new_session", side_effect=lambda: calls.append("reset")), \
            patch.object(manager, "ensure_running", side_effect=lambda: calls.append("ensure")):
        manager._setup()
    assert calls == ["resolve", "reset", "ensure"]
    assert manager._ready.is_set()


def test_setup_skips_reset_when_not_ephemeral(monkeypatch):
    monkeypatch.setenv("DOCKER_EPHEMERAL", "false")
    manager = ContainerManager()
    with patch.object(manager, "resolve_docker_command"), \
            patch.object(manager, "reset_for_new_session") as reset, \
            patch.object(manager, "ensure_running"):
        manager._setup()
    reset.assert_not_called()
    assert manager._ready.is_set()


def test_setup_failure_schedules_a_backed_off_retry(manager):
    with patch.object(manager, "resolve_docker_command"), \
            patch.object(manager, "reset_for_new_session"), \
            patch.object(manager, "ensure_running", side_effect=RuntimeError("boom")):
        manager._setup()
    assert manager._setup_error == "boom"
    assert manager._next_retry_at > time.monotonic()
    assert not manager._ready.is_set()


def test_setup_success_clears_a_previous_failure(manager):
    manager._setup_error = "boom"
    manager._setup_failures = 3
    manager._next_retry_at = time.monotonic() + 60
    with patch.object(manager, "resolve_docker_command"), \
            patch.object(manager, "reset_for_new_session"), patch.object(manager, "ensure_running"):
        manager._setup()
    assert manager._setup_error is None
    assert manager._next_retry_at == 0.0
    assert manager._ready.is_set()


def test_background_setup_respects_retry_backoff(manager):
    manager._next_retry_at = time.monotonic() + 60
    with patch.object(manager, "_setup") as setup:
        manager.start_background_setup()
    setup.assert_not_called()


def test_background_setup_runs_once_backoff_elapsed(manager):
    manager._next_retry_at = time.monotonic() - 1
    with patch.object(manager, "_setup") as setup:
        manager.start_background_setup()
        if manager._setup_thread is not None:
            manager._setup_thread.join(timeout=5)
    setup.assert_called_once()


def test_docker_command_defaults_to_plain_docker(monkeypatch):
    monkeypatch.delenv("DOCKER_COMMAND", raising=False)
    manager = ContainerManager()
    assert manager.docker_command == ["docker"]
    assert manager.autodetect_docker_command is True


def test_docker_command_can_be_overridden(monkeypatch):
    monkeypatch.setenv("DOCKER_COMMAND", "podman")
    manager = ContainerManager()
    assert manager.docker_command == ["podman"]
    assert manager.autodetect_docker_command is False


def test_blank_docker_command_falls_back_to_autodetection(monkeypatch):
    monkeypatch.setenv("DOCKER_COMMAND", "   ")
    manager = ContainerManager()
    assert manager.docker_command == ["docker"]
    assert manager.autodetect_docker_command is True


def test_resolve_prefers_docker_without_sudo(monkeypatch):
    monkeypatch.delenv("DOCKER_COMMAND", raising=False)
    manager = ContainerManager()
    with patch.object(manager, "_probe_docker_command", return_value=None) as probe:
        manager.resolve_docker_command()
    assert manager.docker_command == ["docker"]
    probe.assert_called_once_with(["docker"])


def test_resolve_falls_back_to_sudo_when_socket_needs_root(monkeypatch):
    monkeypatch.delenv("DOCKER_COMMAND", raising=False)
    manager = ContainerManager()
    with patch.object(manager, "_probe_docker_command", side_effect=["permission denied", None]):
        manager.resolve_docker_command()
    assert manager.docker_command == ["sudo", "-n", "docker"]
    assert manager._docker_command_resolved


def test_resolve_reports_every_candidate_and_how_to_fix_it(monkeypatch):
    monkeypatch.delenv("DOCKER_COMMAND", raising=False)
    manager = ContainerManager()
    with patch.object(manager, "_probe_docker_command", side_effect=["permission denied", "a password is required"]):
        with pytest.raises(RuntimeError) as excinfo:
            manager.resolve_docker_command()
    message = str(excinfo.value)
    assert "permission denied" in message
    assert "a password is required" in message
    assert "usermod -aG docker" in message
    assert not manager._docker_command_resolved


def test_resolve_does_not_probe_alternatives_for_an_explicit_command(monkeypatch):
    monkeypatch.setenv("DOCKER_COMMAND", "podman")
    manager = ContainerManager()
    with patch.object(manager, "_probe_docker_command", return_value=None) as probe:
        manager.resolve_docker_command()
    probe.assert_called_once_with(["podman"])


def test_resolve_runs_only_once(monkeypatch):
    monkeypatch.delenv("DOCKER_COMMAND", raising=False)
    manager = ContainerManager()
    with patch.object(manager, "_probe_docker_command", return_value=None) as probe:
        manager.resolve_docker_command()
        manager.resolve_docker_command()
    probe.assert_called_once()


def test_probe_reports_docker_missing_from_path(manager):
    with patch("docker_shell_client.container_manager.shutil.which", return_value=None):
        assert "not installed" in manager._probe_docker_command(["docker"])


def test_probe_reports_daemon_error(manager):
    with patch("docker_shell_client.container_manager.shutil.which", return_value="/usr/bin/docker"), \
            patch.object(manager, "_run", return_value=completed(code=1, stderr="permission denied\nmore")):
        assert manager._probe_docker_command(["docker"]) == "permission denied"


def test_probe_reports_a_hung_daemon_instead_of_blocking(manager):
    with patch("docker_shell_client.container_manager.shutil.which", return_value="/usr/bin/docker"), \
            patch.object(manager, "_run", side_effect=subprocess.TimeoutExpired(["docker"], 30)):
        assert "timed out" in manager._probe_docker_command(["docker"])


def test_run_never_inherits_stdin(manager):
    """A sudo password prompt must fail fast, not block on a stdin it cannot read."""
    with patch("docker_shell_client.container_manager.subprocess.run", return_value=completed()) as run:
        manager._run("docker", "version")
    assert run.call_args.kwargs["stdin"] is subprocess.DEVNULL


def test_run_uses_a_pipe_when_sending_input(manager):
    with patch("docker_shell_client.container_manager.subprocess.run", return_value=completed()) as run:
        manager._run("docker", "exec", input_text="hello")
    assert run.call_args.kwargs["stdin"] is None
    assert run.call_args.kwargs["input"] == "hello"


def test_run_names_the_missing_binary(manager):
    with patch("docker_shell_client.container_manager.subprocess.run", side_effect=FileNotFoundError()):
        with pytest.raises(RuntimeError, match="sudo"):
            manager._run("sudo", "-n", "docker", "version")


def test_ensure_container_starts_stopped_container(manager):
    with patch.object(manager, "container_image_changed", return_value=False), \
            patch.object(manager, "_docker", side_effect=[completed(stdout="exited\n"), completed()]) as docker:
        manager.ensure_container()
    assert docker.call_args_list[-1].args == ("start", manager.container_name)


def test_ensure_container_unpauses_paused_container(manager):
    with patch.object(manager, "container_image_changed", return_value=False), \
            patch.object(manager, "_docker", side_effect=[completed(stdout="paused\n"), completed()]) as docker:
        manager.ensure_container()
    assert docker.call_args_list[-1].args == ("unpause", manager.container_name)


def test_ensure_container_recreates_a_dead_container(manager):
    with patch.object(manager, "container_image_changed", return_value=False), \
            patch.object(manager, "container_state", return_value="dead"), \
            patch.object(manager, "remove_container") as remove, \
            patch.object(manager, "create_container") as create:
        manager.ensure_container()
    remove.assert_called_once()
    create.assert_called_once()


def test_ensure_running_builds_and_creates_missing_container(manager):
    with patch.object(manager, "image_exists", return_value=False), \
            patch.object(manager, "build_image") as build, \
            patch.object(manager, "container_state", side_effect=["not_found", "running"]), \
            patch.object(manager, "_docker", return_value=completed()) as docker:
        manager.ensure_running()
    build.assert_called_once()
    commands = [call.args for call in docker.call_args_list]
    assert any(command[:2] == ("run", "--detach") for command in commands)


def test_ensure_running_recreates_container_after_rebuild(manager):
    with patch.object(manager, "image_exists", return_value=True), \
            patch.object(manager, "image_is_stale", return_value=True), \
            patch.object(manager, "build_image"), \
            patch.object(manager, "container_state", side_effect=["running", "running"]), \
            patch.object(manager, "_docker", return_value=completed()) as docker:
        manager.ensure_running()
    commands = [call.args for call in docker.call_args_list]
    assert ("rm", "--force", manager.container_name) in commands
    assert any(command[:2] == ("run", "--detach") for command in commands)


def test_ensure_container_recreates_when_image_was_rebuilt_elsewhere(manager):
    """A persistent container must not keep running a superseded image."""
    with patch.object(manager, "container_image_changed", return_value=True), \
            patch.object(manager, "container_state", side_effect=["running", "running"]), \
            patch.object(manager, "_docker", return_value=completed()) as docker:
        manager.ensure_container()
    commands = [call.args for call in docker.call_args_list]
    assert ("rm", "--force", manager.container_name) in commands
    assert any(command[:2] == ("run", "--detach") for command in commands)


def test_container_image_changed_compares_image_ids(manager):
    with patch.object(manager, "_docker", side_effect=[completed(stdout="sha256:aaa\n"), completed(stdout="sha256:bbb\n")]):
        assert manager.container_image_changed()
    with patch.object(manager, "_docker", side_effect=[completed(stdout="sha256:aaa\n"), completed(stdout="sha256:aaa\n")]):
        assert not manager.container_image_changed()


def test_container_image_changed_is_false_when_inspect_fails(manager):
    with patch.object(manager, "_docker", side_effect=[completed(code=1), completed(code=1)]):
        assert not manager.container_image_changed()


def test_create_container_reports_a_container_that_died_immediately(manager):
    with patch.object(manager, "container_state", return_value="exited"), \
            patch.object(manager, "_docker", return_value=completed(stdout="exec format error")):
        with pytest.raises(RuntimeError, match="exited immediately after creation"):
            manager.create_container()


def test_remove_container_tolerates_a_missing_container(manager):
    missing = completed(code=1, stderr="Error: No such container: shell-mcp-sandbox")
    with patch.object(manager, "_docker", return_value=missing):
        manager.remove_container()


def test_remove_container_raises_on_a_real_failure(manager):
    failure = completed(code=1, stderr="Error response from daemon: cannot remove container")
    with patch.object(manager, "_docker", return_value=failure):
        with pytest.raises(RuntimeError, match="Could not remove container"):
            manager.remove_container()


def test_image_is_stale_compares_dockerfile_hash(manager):
    with patch.object(manager, "_docker", return_value=completed(stdout="deadbeef\n")):
        assert manager.image_is_stale()
    with patch.object(manager, "_docker", return_value=completed(stdout=f"{manager.dockerfile_hash()}\n")):
        assert not manager.image_is_stale()


def test_exec_uses_argv_and_interactive_stdin(manager):
    with patch.object(manager, "_require_ready"), patch.object(manager, "_docker", return_value=completed()) as docker:
        manager.exec(["tee", "--", "/tmp/a file"], input_text="hello", check=True)
    assert docker.call_args.args[:6] == ("exec", "--interactive", "--user", manager.user, "--workdir", manager.workdir)
    assert docker.call_args.kwargs["input_text"] == "hello"


def test_exec_runs_as_the_configured_user(monkeypatch):
    monkeypatch.setenv("DOCKER_USER", "agent")
    manager = ContainerManager()
    with patch.object(manager, "_require_ready"), patch.object(manager, "_docker", return_value=completed()) as docker:
        manager.exec(["id"])
    assert docker.call_args.args[:3] == ("exec", "--user", "agent")


def test_exec_fails_fast_while_sandbox_is_building(manager):
    with patch.object(manager, "start_background_setup") as setup:
        with pytest.raises(RuntimeError, match="still being prepared"):
            manager.exec(["true"])
    setup.assert_called_once()


def test_exec_reports_setup_error_and_retries(manager):
    manager._setup_error = "build exploded"
    with patch.object(manager, "start_background_setup") as setup:
        with pytest.raises(RuntimeError, match="build exploded"):
            manager.exec(["true"])
    setup.assert_called_once()


def test_exec_runs_normally_once_ready(manager):
    manager._ready.set()
    with patch.object(manager, "_repair_if_stopped"), patch.object(manager, "_docker", return_value=completed()) as docker:
        result = manager.exec(["true"])
    assert result.returncode == 0
    assert docker.call_args.args[0] == "exec"


def test_ready_tool_call_only_checks_container_state(manager):
    """The hot path must not re-inspect or rebuild the image on every call."""
    manager._ready.set()
    with patch.object(manager, "_docker", side_effect=[completed(stdout="running\n"), completed()]) as docker, \
            patch.object(manager, "ensure_image") as ensure_image:
        manager.exec(["true"])
    ensure_image.assert_not_called()
    assert docker.call_args_list[0].args[0] == "inspect"


def test_ready_tool_call_repairs_a_stopped_container(manager):
    manager._ready.set()
    with patch.object(manager, "container_state", side_effect=["exited", "exited"]), \
            patch.object(manager, "image_exists", return_value=True), \
            patch.object(manager, "ensure_container") as ensure_container, \
            patch.object(manager, "_docker", return_value=completed()):
        manager.exec(["true"])
    ensure_container.assert_called_once()


def test_ready_tool_call_defers_a_missing_image_to_background_setup(manager):
    """Rebuilding takes minutes, so it must never happen inline in a tool call."""
    manager._ready.set()
    with patch.object(manager, "container_state", return_value="not_found"), \
            patch.object(manager, "image_exists", return_value=False), \
            patch.object(manager, "start_background_setup") as setup, \
            patch.object(manager, "ensure_container") as ensure_container:
        with pytest.raises(RuntimeError, match="being rebuilt"):
            manager.exec(["true"])
    ensure_container.assert_not_called()
    setup.assert_called_once()
    assert not manager._ready.is_set()


def test_stop_container_removes_a_stopped_container_when_configured(monkeypatch):
    monkeypatch.setenv("DOCKER_REMOVE_ON_EXIT", "true")
    manager = ContainerManager()
    manager._docker_command_resolved = True
    with patch.object(manager, "container_state", return_value="exited"), \
            patch.object(manager, "_docker", return_value=completed()) as docker:
        manager.stop_container()
    assert docker.call_args.args == ("rm", "--force", manager.container_name)


def test_stop_container_is_a_noop_when_docker_never_came_up(monkeypatch):
    manager = ContainerManager()
    with patch.object(manager, "_docker") as docker:
        manager.stop_container()
    docker.assert_not_called()


def test_stop_container_swallows_shutdown_errors(manager):
    with patch.object(manager, "container_state", side_effect=RuntimeError("daemon gone")):
        manager.stop_container()


def test_candidate_sudo_command_is_non_interactive():
    assert DOCKER_COMMAND_CANDIDATES[1] == ["sudo", "-n", "docker"]
