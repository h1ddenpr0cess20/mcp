import hashlib
import os
import shlex
import subprocess
import sys
import threading
from pathlib import Path

DOCKERFILE_HASH_LABEL = "shell-mcp.dockerfile-sha256"


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
        self._setup_lock = threading.Lock()
        self._setup_thread: threading.Thread | None = None
        self._setup_error: str | None = None
        self._ready = threading.Event()

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

    def dockerfile_hash(self) -> str:
        dockerfile = self.dockerfile_dir / "Dockerfile"
        return hashlib.sha256(dockerfile.read_bytes()).hexdigest()

    def image_is_stale(self) -> bool:
        """True when the image was built from a different Dockerfile than the current one."""
        result = self._docker(
            "image", "inspect", "--format",
            f'{{{{index .Config.Labels "{DOCKERFILE_HASH_LABEL}"}}}}',
            self.image, check=False,
        )
        if result.returncode != 0:
            return False
        return result.stdout.strip() != self.dockerfile_hash()

    def ensure_image(self) -> bool:
        """Build the image if missing or stale. Returns True when a build ran."""
        if not self.image_exists():
            self._log(f"Building sandbox image {self.image} (first run; this can take a few minutes)")
            self.build_image()
            return True
        if self.image_is_stale():
            self._log(f"Dockerfile changed; rebuilding sandbox image {self.image}")
            self.build_image()
            return True
        return False

    def build_image(self):
        """Build the sandbox image, streaming progress to stderr."""
        process = subprocess.Popen(
            [
                *self.docker_command, "build",
                "--tag", self.image,
                "--label", f"{DOCKERFILE_HASH_LABEL}={self.dockerfile_hash()}",
                str(self.dockerfile_dir),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        assert process.stdout is not None
        for line in process.stdout:
            self._log(f"build: {line.rstrip()}")
        process.wait()
        if process.returncode != 0:
            raise RuntimeError(
                f"Docker image build failed ({process.returncode}); see logs above"
            )
        self._log(f"Image {self.image} built")

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
        """Build or refresh the image if needed and start or create the container."""
        self._docker("version", check=True)
        rebuilt = self.ensure_image()
        state = self.container_state()
        if rebuilt and state != "not_found":
            self._log(f"Recreating container {self.container_name} on the new image")
            self._docker("rm", "--force", self.container_name)
            state = "not_found"
        if state == "running":
            return
        if state == "not_found":
            self.create_container()
            return
        self._log(f"Starting existing container {self.container_name}")
        self._docker("start", self.container_name)

    def start_background_setup(self):
        """Prepare the sandbox (build image, start container) without blocking.

        Safe to call repeatedly; only one setup runs at a time, and a failed
        setup is retried on the next call.
        """
        with self._setup_lock:
            if self._ready.is_set():
                return
            if self._setup_thread is not None and self._setup_thread.is_alive():
                return
            self._setup_error = None
            self._setup_thread = threading.Thread(
                target=self._setup, name="sandbox-setup", daemon=True
            )
            self._setup_thread.start()

    def _setup(self):
        try:
            self.ensure_running()
        except Exception as exc:
            self._setup_error = str(exc)
            self._log(f"Sandbox setup failed: {exc}")
        else:
            self._ready.set()
            self._log("Sandbox is ready")

    def _require_ready(self):
        """Fast-path readiness gate so tool calls never block on an image build."""
        if self._ready.is_set():
            self.ensure_running()
            return
        error = self._setup_error
        self.start_background_setup()
        if error:
            raise RuntimeError(
                f"Sandbox setup failed and is being retried: {error}"
            )
        raise RuntimeError(
            "The sandbox is still being prepared (building the Docker image "
            "on first run). Retry this tool call in a minute or two."
        )

    def exec(
        self,
        command: list[str],
        *,
        input_text: str | None = None,
        check: bool = False,
    ) -> subprocess.CompletedProcess:
        """Execute an argv-style command inside the running container."""
        self._require_ready()
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
        self._require_ready()
        self._docker("cp", local_path, f"{self.container_name}:{container_path}")

    def copy_from(self, container_path: str, local_path: str):
        self._require_ready()
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
