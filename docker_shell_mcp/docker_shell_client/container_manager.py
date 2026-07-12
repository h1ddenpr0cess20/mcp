import os
import shlex
import subprocess
import sys
from pathlib import Path


class ContainerManager:
    """Manage the Docker container used as the shell sandbox."""

    def __init__(self):
        self.docker_command = shlex.split(os.getenv("DOCKER_COMMAND", "sudo -n docker"))
        if not self.docker_command:
            raise ValueError("DOCKER_COMMAND must not be empty")
        self.container_name = os.getenv("DOCKER_CONTAINER", "shell-mcp-sandbox")
        self.image = os.getenv("DOCKER_IMAGE", "shell-mcp-sandbox:latest")
        self.hostname = os.getenv("DOCKER_HOSTNAME", "shell-sandbox")
        self.workdir = os.getenv("DOCKER_WORKDIR", "/workspace")
        self.user = os.getenv("DOCKER_USER", "root")
        self.network = os.getenv("DOCKER_NETWORK", "bridge")
        self.memory = os.getenv("DOCKER_MEMORY", "2g")
        self.cpus = os.getenv("DOCKER_CPUS", "2")
        self.pids_limit = os.getenv("DOCKER_PIDS_LIMIT", "512")
        self.volume = os.getenv("DOCKER_VOLUME", "shell-mcp-data")
        self.remove_on_exit = os.getenv("DOCKER_REMOVE_ON_EXIT", "false").lower() in (
            "1", "true", "yes",
        )
        self.command_timeout = int(os.getenv("COMMAND_TIMEOUT", "1200"))
        self.dockerfile_dir = Path(__file__).resolve().parent / "sandbox"

    def _log(self, message: str):
        sys.stderr.write(f"[container-manager] {message}\n")
        sys.stderr.flush()

    def _run(
        self,
        *args: str,
        check: bool = True,
        input_text: str | None = None,
        timeout: int | None = None,
    ) -> subprocess.CompletedProcess:
        try:
            result = subprocess.run(
                args,
                check=False,
                capture_output=True,
                text=True,
                input=input_text,
                timeout=timeout,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"Container command was not found: {self.docker_command[0]}"
            ) from exc
        if check and result.returncode != 0:
            raise RuntimeError(
                f"Docker command failed ({result.returncode}): "
                f"{result.stderr.strip() or result.stdout.strip()}"
            )
        return result

    def _docker(self, *args: str, **kwargs) -> subprocess.CompletedProcess:
        return self._run(*self.docker_command, *args, **kwargs)

    def image_exists(self) -> bool:
        return self._docker("image", "inspect", self.image, check=False).returncode == 0

    def ensure_image(self):
        if self.image_exists():
            return
        self._log(f"Building sandbox image {self.image}")
        self._docker("build", "--tag", self.image, str(self.dockerfile_dir))

    def container_state(self) -> str:
        result = self._docker(
            "inspect", "--format", "{{.State.Status}}", self.container_name, check=False
        )
        if result.returncode != 0:
            return "not_found"
        return result.stdout.strip()

    def create_container(self):
        args = [
            "run", "--detach",
            "--name", self.container_name,
            "--hostname", self.hostname,
            "--workdir", self.workdir,
            "--user", self.user,
            "--network", self.network,
            "--memory", self.memory,
            "--cpus", self.cpus,
            "--pids-limit", self.pids_limit,
            "--security-opt", "no-new-privileges=true",
            "--volume", f"{self.volume}:{self.workdir}",
        ]
        if self.remove_on_exit:
            args.append("--rm")
        args.extend([self.image, "sleep", "infinity"])
        self._log(f"Creating container {self.container_name}")
        self._docker(*args)

    def ensure_running(self):
        """Build the default image if needed and start or create the container."""
        self._docker("version", check=True)
        state = self.container_state()
        if state == "running":
            return
        if state == "not_found":
            self.ensure_image()
            self.create_container()
            return
        self._log(f"Starting existing container {self.container_name}")
        self._docker("start", self.container_name)

    def exec(
        self,
        command: list[str],
        *,
        input_text: str | None = None,
        check: bool = False,
    ) -> subprocess.CompletedProcess:
        """Execute an argv-style command inside the running container."""
        self.ensure_running()
        args = ["exec"]
        if input_text is not None:
            args.append("--interactive")
        args.extend(["--workdir", self.workdir, self.container_name, *command])
        return self._docker(
            *args,
            check=check,
            input_text=input_text,
            timeout=self.command_timeout + 5,
        )

    def copy_to(self, local_path: str, container_path: str):
        self.ensure_running()
        self._docker("cp", local_path, f"{self.container_name}:{container_path}")

    def copy_from(self, container_path: str, local_path: str):
        self.ensure_running()
        self._docker("cp", f"{self.container_name}:{container_path}", local_path)

    def stop_container(self):
        if self.container_state() != "running":
            return
        action = "Removing" if self.remove_on_exit else "Stopping"
        self._log(f"{action} container {self.container_name}")
        if self.remove_on_exit:
            self._docker("rm", "--force", self.container_name, check=False)
        else:
            self._docker("stop", "--time", "10", self.container_name, check=False)
