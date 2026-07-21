import subprocess

import pytest
from unittest.mock import MagicMock, patch

from webshell_client.vm_manager import VMManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _completed(returncode=0, stdout="", stderr=""):
    result = MagicMock(spec=subprocess.CompletedProcess)
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


def _vm(monkeypatch=None, **env_overrides):
    """Construct a VMManager with default test env vars."""
    defaults = {
        "VM_NAME": "test-webshell",
        "VM_RAM": "1024",
        "VM_CPUS": "1",
        "VM_DISK": "10240",
        "SSH_USER": "tester",
        "VM_PASS": "pass",
        "NETWORK_MODE": "nat",
        "SSH_HOST": "127.0.0.1",
        "SSH_PORT": "22",
        "VM_SUDO": "false",
        "SEARXNG_PORT": "8889",
    }
    defaults.update(env_overrides)
    if monkeypatch:
        for k, v in defaults.items():
            monkeypatch.setenv(k, v)
    return VMManager()


# ---------------------------------------------------------------------------
# __init__ / env var reading
# ---------------------------------------------------------------------------

class TestVMManagerInit:
    def test_defaults_from_env(self, monkeypatch):
        vm = _vm(monkeypatch)
        assert vm.vm_name == "test-webshell"
        assert vm.vm_ram == 1024
        assert vm.vm_cpus == 1
        assert vm.network_mode == "nat"
        assert vm.searxng_port == 8889

    def test_vm_sudo_false(self, monkeypatch):
        vm = _vm(monkeypatch, VM_SUDO="false")
        assert vm.vm_sudo is False

    def test_vm_sudo_true_variants(self, monkeypatch):
        for val in ("true", "1", "yes"):
            monkeypatch.setenv("VM_SUDO", val)
            vm = VMManager()
            assert vm.vm_sudo is True, f"Expected True for VM_SUDO={val}"

    def test_default_vm_name_is_ai_webshell(self, monkeypatch):
        # Clear VM_NAME to test the default
        monkeypatch.delenv("VM_NAME", raising=False)
        vm = VMManager()
        assert vm.vm_name == "ai-webshell"

    def test_default_searxng_port(self, monkeypatch):
        monkeypatch.delenv("SEARXNG_PORT", raising=False)
        vm = VMManager()
        assert vm.searxng_port == 8889


# ---------------------------------------------------------------------------
# _run / _vbox
# ---------------------------------------------------------------------------

class TestRun:
    def test_run_returns_completed_process(self, monkeypatch):
        vm = _vm(monkeypatch)
        with patch("subprocess.run", return_value=_completed(0, "ok")) as mock_run:
            result = vm._run("echo", "ok")
        assert result.returncode == 0
        mock_run.assert_called_once()

    def test_run_raises_on_nonzero_when_check_true(self, monkeypatch):
        vm = _vm(monkeypatch)
        with patch("subprocess.run", return_value=_completed(1, stderr="err")):
            with pytest.raises(subprocess.CalledProcessError):
                vm._run("false", check=True)

    def test_run_does_not_raise_when_check_false(self, monkeypatch):
        vm = _vm(monkeypatch)
        with patch("subprocess.run", return_value=_completed(1, stderr="err")):
            result = vm._run("false", check=False)
        assert result.returncode == 1

    def test_vbox_prepends_vboxmanage(self, monkeypatch):
        vm = _vm(monkeypatch)
        with patch("subprocess.run", return_value=_completed(0, "")) as mock_run:
            vm._vbox("list", "vms")
        args_used = mock_run.call_args[0][0]
        assert args_used[0] == "vboxmanage"
        assert "list" in args_used
        assert "vms" in args_used


# ---------------------------------------------------------------------------
# vm_exists
# ---------------------------------------------------------------------------

class TestVmExists:
    def test_returns_true_when_vm_listed(self, monkeypatch):
        vm = _vm(monkeypatch)
        with patch("subprocess.run", return_value=_completed(0, '"test-webshell" {abc}')):
            assert vm.vm_exists() is True

    def test_returns_false_when_vm_absent(self, monkeypatch):
        vm = _vm(monkeypatch)
        with patch("subprocess.run", return_value=_completed(0, '"other-vm" {xyz}')):
            assert vm.vm_exists() is False

    def test_returns_false_on_vbox_error(self, monkeypatch):
        vm = _vm(monkeypatch)
        with patch("subprocess.run", return_value=_completed(1, "")):
            assert vm.vm_exists() is False


# ---------------------------------------------------------------------------
# vm_state
# ---------------------------------------------------------------------------

class TestVmState:
    def test_parses_running_state(self, monkeypatch):
        vm = _vm(monkeypatch)
        output = 'VMState="running"\nVMStateChangeTime="2024-01-01"\n'
        with patch("subprocess.run", return_value=_completed(0, output)):
            assert vm.vm_state() == "running"

    def test_parses_poweroff_state(self, monkeypatch):
        vm = _vm(monkeypatch)
        output = 'VMState="poweroff"\n'
        with patch("subprocess.run", return_value=_completed(0, output)):
            assert vm.vm_state() == "poweroff"

    def test_returns_not_found_on_error(self, monkeypatch):
        vm = _vm(monkeypatch)
        with patch("subprocess.run", return_value=_completed(1, "")):
            assert vm.vm_state() == "not_found"

    def test_returns_unknown_when_no_vmstate_line(self, monkeypatch):
        vm = _vm(monkeypatch)
        with patch("subprocess.run", return_value=_completed(0, "name=test-vm\n")):
            assert vm.vm_state() == "unknown"


# ---------------------------------------------------------------------------
# vm_ip
# ---------------------------------------------------------------------------

class TestVmIp:
    def test_returns_ip_when_present(self, monkeypatch):
        vm = _vm(monkeypatch)
        output = "Value: 192.168.56.101\n"
        with patch("subprocess.run", return_value=_completed(0, output)):
            assert vm.vm_ip() == "192.168.56.101"

    def test_returns_none_on_error(self, monkeypatch):
        vm = _vm(monkeypatch)
        with patch("subprocess.run", return_value=_completed(1, "")):
            assert vm.vm_ip() is None

    def test_returns_none_when_value_absent(self, monkeypatch):
        vm = _vm(monkeypatch)
        with patch("subprocess.run", return_value=_completed(0, "No value set!")):
            assert vm.vm_ip() is None


# ---------------------------------------------------------------------------
# _iso_looks_valid
# ---------------------------------------------------------------------------

class TestIsoLooksValid:
    def test_returns_false_when_file_missing(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ISO_PATH", str(tmp_path / "missing.iso"))
        vm = _vm(monkeypatch)
        assert vm._iso_looks_valid() is False

    def test_returns_false_when_file_too_small(self, monkeypatch, tmp_path):
        iso = tmp_path / "small.iso"
        iso.write_bytes(b"x" * 100)
        monkeypatch.setenv("ISO_PATH", str(iso))
        vm = _vm(monkeypatch)
        assert vm._iso_looks_valid() is False

    def test_returns_true_when_file_large_enough(self, monkeypatch, tmp_path):
        iso = tmp_path / "valid.iso"
        with open(iso, "wb") as f:
            f.seek(600 * 1024 * 1024)
            f.write(b"\x00")
        monkeypatch.setenv("ISO_PATH", str(iso))
        vm = _vm(monkeypatch)
        assert vm._iso_looks_valid() is True


# ---------------------------------------------------------------------------
# ensure_ssh_key
# ---------------------------------------------------------------------------

class TestEnsureSshKey:
    def test_skips_keygen_when_pubkey_exists(self, monkeypatch, tmp_path):
        pubkey = tmp_path / "key.pub"
        pubkey.write_text("ssh-ed25519 AAAA test")
        monkeypatch.setenv("SSH_PUBKEY_PATH", str(pubkey))
        monkeypatch.setenv("SSH_KEY_PATH", str(tmp_path / "key"))
        vm = _vm(monkeypatch)

        with patch("subprocess.run") as mock_run:
            vm.ensure_ssh_key()
        mock_run.assert_not_called()

    def test_runs_keygen_when_pubkey_missing(self, monkeypatch, tmp_path):
        pubkey = tmp_path / "key.pub"
        key = tmp_path / "key"
        monkeypatch.setenv("SSH_PUBKEY_PATH", str(pubkey))
        monkeypatch.setenv("SSH_KEY_PATH", str(key))
        vm = _vm(monkeypatch)

        with patch("subprocess.run", return_value=_completed(0)) as mock_run:
            vm.ensure_ssh_key()
        called_args = mock_run.call_args[0][0]
        assert "ssh-keygen" in called_args


# ---------------------------------------------------------------------------
# start_vm
# ---------------------------------------------------------------------------

class TestStartVm:
    def test_skips_start_when_already_running(self, monkeypatch):
        vm = _vm(monkeypatch)
        running_output = 'VMState="running"\n'

        with patch("subprocess.run", return_value=_completed(0, running_output)) as mock_run:
            vm.start_vm()

        calls_args = [c[0][0] for c in mock_run.call_args_list]
        assert not any("startvm" in args for args in calls_args)

    def test_calls_startvm_when_not_running(self, monkeypatch):
        vm = _vm(monkeypatch)
        poweroff_output = 'VMState="poweroff"\n'

        side_effects = [
            _completed(0, poweroff_output),  # showvminfo -> state
            _completed(0),                    # startvm
        ]
        with patch("subprocess.run", side_effect=side_effects) as mock_run:
            vm.start_vm()

        calls_args = [c[0][0] for c in mock_run.call_args_list]
        assert any("startvm" in args for args in calls_args)


# ---------------------------------------------------------------------------
# ensure_running — no vboxmanage path
# ---------------------------------------------------------------------------

class TestEnsureRunningNoVbox:
    def test_returns_ssh_host_port_and_searxng_url(self, monkeypatch):
        vm = _vm(monkeypatch, SSH_HOST="10.0.0.5", SSH_PORT="22", SEARXNG_PORT="8889")

        with patch("shutil.which", return_value=None):
            result = vm.ensure_running()

        assert result["ssh_host"] == "10.0.0.5"
        assert result["ssh_port"] == 22
        assert result["searxng_url"] == "http://10.0.0.5:8889"


# ---------------------------------------------------------------------------
# ensure_running — vboxmanage present, VM already running
# ---------------------------------------------------------------------------

class TestEnsureRunningVmRunning:
    def test_reuses_vm_when_ssh_already_reachable(self, monkeypatch):
        """A running VM with SSH already up skips restore/reboot entirely."""
        vm = _vm(monkeypatch, NETWORK_MODE="nat")

        with patch("shutil.which", return_value="/usr/bin/vboxmanage"), \
                patch.object(vm, "vm_exists", return_value=True), \
                patch.object(vm, "vm_state", return_value="running"), \
                patch.object(vm, "_quick_ssh_probe", return_value="127.0.0.1") as mock_probe, \
                patch.object(vm, "restore_clean") as mock_restore, \
                patch.object(vm, "start_vm") as mock_start, \
                patch.object(vm, "wait_for_ssh") as mock_wait:
            result = vm.ensure_running()

        mock_probe.assert_called_once()
        mock_restore.assert_not_called()
        mock_start.assert_not_called()
        mock_wait.assert_not_called()
        assert result["ssh_host"] == "127.0.0.1"
        assert result["ssh_port"] == 2223
        assert result["searxng_url"] == "http://127.0.0.1:8889"

    def test_falls_back_to_restore_when_quick_probe_fails(self, monkeypatch):
        """A running VM whose SSH doesn't answer falls back to the full
        restore/reboot/wait cycle, same as before this fast path existed."""
        vm = _vm(monkeypatch, NETWORK_MODE="nat")

        with patch("shutil.which", return_value="/usr/bin/vboxmanage"), \
                patch.object(vm, "vm_exists", return_value=True), \
                patch.object(vm, "vm_state", return_value="running"), \
                patch.object(vm, "_quick_ssh_probe", return_value=None) as mock_probe, \
                patch.object(vm, "_snapshot_exists", return_value=True), \
                patch.object(vm, "restore_clean") as mock_restore, \
                patch.object(vm, "start_vm") as mock_start, \
                patch.object(vm, "wait_for_ssh", return_value="127.0.0.1") as mock_wait:
            result = vm.ensure_running()

        mock_probe.assert_called_once()
        mock_restore.assert_called_once()
        mock_start.assert_called_once()
        mock_wait.assert_called_once_with(timeout=120)
        assert result["ssh_host"] == "127.0.0.1"
        assert result["ssh_port"] == 2223
        assert result["searxng_url"] == "http://127.0.0.1:8889"


# ---------------------------------------------------------------------------
# _quick_ssh_probe
# ---------------------------------------------------------------------------

class TestQuickSshProbe:
    def test_returns_host_when_ssh_succeeds(self, monkeypatch):
        vm = _vm(monkeypatch, NETWORK_MODE="nat")
        with patch("subprocess.run", return_value=_completed(0, "ok")) as mock_run:
            assert vm._quick_ssh_probe() == "127.0.0.1"
        called_args = mock_run.call_args[0][0]
        assert called_args[0] == "ssh"

    def test_returns_none_when_ssh_fails(self, monkeypatch):
        vm = _vm(monkeypatch, NETWORK_MODE="nat")
        with patch("subprocess.run", return_value=_completed(255, "")):
            assert vm._quick_ssh_probe() is None

    def test_returns_none_when_hostonly_ip_undetected(self, monkeypatch):
        vm = _vm(monkeypatch, NETWORK_MODE="hostonly")
        with patch.object(vm, "_hostonly_vm_ip", return_value=None):
            assert vm._quick_ssh_probe() is None
