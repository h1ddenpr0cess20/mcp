import hashlib
import os
import shlex
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

DOCKERFILE_HASH_LABEL = "shell-mcp.dockerfile-sha256"

# Probe order when DOCKER_COMMAND is unset. A plain `docker` comes first so any
# correctly configured daemon (docker group membership, rootless Docker, Docker
# Desktop, a remote DOCKER_HOST) is used as-is; sudo is only a fallback for
# hosts where the socket really is root-only. `-n` keeps sudo from ever trying
# to read a password.
DOCKER_COMMAND_CANDIDATES = (["docker"], ["sudo", "-n", "docker"])

# Probes and lifecycle commands are quick; a cap keeps an unreachable daemon
# from wedging setup instead of reporting a usable error.
DOCKER_PROBE_TIMEOUT = 30

# Setup retries after a failure, backing off so a permanently broken daemon
# does not get re-probed on every single tool call.
RETRY_BASE_DELAY = 5
RETRY_MAX_DELAY = 60

DOCKER_SETUP_HELP = """
Fix any one of the following, then retry:
  * Start the daemon:            sudo systemctl start docker
  * Use Docker without sudo:     sudo usermod -aG docker "$USER"
                                 (log out and back in for it to take effect)
  * Or install rootless Docker:  dockerd-rootless-setuptool.sh install
  * Or point the server at a working command in .env, e.g.
        DOCKER_COMMAND=podman
        DOCKER_COMMAND=sudo -n docker
    (a sudo command must include -n so it fails fast instead of waiting on a
    password prompt this server cannot answer)
""".rstrip()


class ContainerManager:
    """Manage the Docker container used as the shell sandbox."""

    def __init__(self):
        configured = os.getenv("DOCKER_COMMAND", "").strip()
        self.docker_command = shlex.split(configured) if configured else list(DOCKER_COMMAND_CANDIDATES[0])
        if configured and not self.docker_command:
            raise ValueError("DOCKER_COMMAND must not be empty")
        # An explicit setting is used verbatim; otherwise the working command is
        # discovered on first use so no sudo is required when none is needed.
        self.autodetect_docker_command = not configured
        self._docker_command_resolved = False
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
        self.ephemeral = os.getenv("DOCKER_EPHEMERAL", "true").lower() in (
            "1", "true", "yes",
        )
        self.command_timeout = int(os.getenv("COMMAND_TIMEOUT", "1200"))
        self.dockerfile_dir = Path(__file__).resolve().parent / "sandbox"
        # Serializes container lifecycle changes so concurrent tool calls cannot
        # race into two `docker run` invocations for the same container name.
        self._lock = threading.RLock()
        self._setup_lock = threading.Lock()
        self._setup_thread: threading.Thread | None = None
        self._setup_error: str | None = None
        self._setup_failures = 0
        self._next_retry_at = 0.0
        self._reset_done = False
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
                # Never inherit stdin. Without this a helper that reads from the
                # terminal (notably a sudo password prompt) blocks forever with
                # its prompt swallowed by capture_output, and in stdio mode it
                # would eat the MCP protocol stream. Closed stdin makes such a
                # read fail immediately with a diagnosable error instead.
                stdin=subprocess.DEVNULL if input_text is None else None,
                input=input_text,
                timeout=timeout,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(f"Container command was not found: {args[0]}") from exc
        if check and result.returncode != 0:
            raise RuntimeError(
                f"Docker command failed ({result.returncode}): "
                f"{result.stderr.strip() or result.stdout.strip()}"
            )
        return result

    def _docker(self, *args: str, **kwargs) -> subprocess.CompletedProcess:
        return self._run(*self.docker_command, *args, **kwargs)

    @staticmethod
    def _describe_failure(result: subprocess.CompletedProcess) -> str:
        output = (result.stderr or "").strip() or (result.stdout or "").strip()
        return output.splitlines()[0] if output else f"exit status {result.returncode}"

    def _probe_docker_command(self, command: list[str]) -> str | None:
        """Return None when `command` can reach a daemon, else why it cannot."""
        if shutil.which(command[0]) is None:
            return f"{command[0]!r} is not installed or not on PATH"
        try:
            result = self._run(
                *command, "version", "--format", "{{.Server.Version}}",
                check=False, timeout=DOCKER_PROBE_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return f"timed out after {DOCKER_PROBE_TIMEOUT}s"
        except RuntimeError as exc:
            return str(exc)
        return None if result.returncode == 0 else self._describe_failure(result)

    def resolve_docker_command(self):
        """Find a Docker invocation that reaches the daemon, preferring no sudo.

        Runs once per process. With DOCKER_COMMAND set the configured command is
        only verified; otherwise plain `docker` is tried first and sudo is used
        only when the socket genuinely needs it.
        """
        with self._lock:
            if self._docker_command_resolved:
                return
            candidates = (
                [list(candidate) for candidate in DOCKER_COMMAND_CANDIDATES]
                if self.autodetect_docker_command
                else [list(self.docker_command)]
            )
            failures = []
            for candidate in candidates:
                if candidate[0] == "sudo" and "-n" not in candidate:
                    self._log(
                        "Warning: DOCKER_COMMAND runs sudo without -n; add -n so a "
                        "missing sudo permission fails fast instead of waiting on a "
                        "password prompt this server cannot answer"
                    )
                problem = self._probe_docker_command(candidate)
                if problem is None:
                    self.docker_command = candidate
                    self._docker_command_resolved = True
                    self._log(f"Using Docker command: {shlex.join(candidate)}")
                    return
                failures.append(f"  - `{shlex.join(candidate)}` failed: {problem}")
            raise RuntimeError(
                "Could not reach the Docker daemon.\n"
                + "\n".join(failures)
                + "\n"
                + DOCKER_SETUP_HELP
            )

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
            stdin=subprocess.DEVNULL,
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

    def container_image_changed(self) -> bool:
        """True when the container was created from a different image than the current one.

        Without this a persistent sandbox keeps running the image it was created
        from even after another session rebuilt `self.image` underneath it.
        """
        container = self._docker(
            "inspect", "--format", "{{.Image}}", self.container_name, check=False
        )
        image = self._docker(
            "image", "inspect", "--format", "{{.Id}}", self.image, check=False
        )
        if container.returncode != 0 or image.returncode != 0:
            return False
        return container.stdout.strip() != image.stdout.strip()

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
        state = self.container_state()
        if state != "running":
            logs = self._docker("logs", "--tail", "20", self.container_name, check=False)
            detail = (logs.stdout or "").strip() or (logs.stderr or "").strip()
            raise RuntimeError(
                f"Container {self.container_name} is {state} immediately after creation"
                + (f": {detail}" if detail else "")
            )

    def remove_container(self):
        """Remove the container, tolerating one that is already gone."""
        result = self._docker("rm", "--force", self.container_name, check=False)
        if result.returncode != 0 and "no such container" not in result.stderr.lower():
            raise RuntimeError(
                f"Could not remove container {self.container_name}: {self._describe_failure(result)}"
            )

    def reset_for_new_session(self):
        """Discard any container and workspace volume left over from a previous session.

        Mirrors the clean-snapshot restore the VM-backed shell sandboxes do on
        every start, so each new server process gets a fresh sandbox instead of
        resuming whatever the last session left behind. Runs at most once per
        process: a setup retry, or a mid-session repair after the container was
        removed underneath us, must not wipe the workspace a session is using.
        """
        with self._lock:
            if self._reset_done:
                return
            self._log(
                f"Ephemeral mode: discarding container {self.container_name} "
                f"and volume {self.volume} from any previous session"
            )
            self.remove_container()
            # `docker volume rm` reports a missing volume even with --force on
            # some versions, so a failure is only worth surfacing when the
            # volume exists and is held by something else.
            result = self._docker("volume", "rm", "--force", self.volume, check=False)
            if result.returncode != 0 and "no such volume" not in result.stderr.lower():
                self._log(
                    f"Warning: could not remove volume {self.volume} "
                    f"({self._describe_failure(result)}); the workspace may carry over"
                )
            self._reset_done = True

    def ensure_container(self, recreate: bool = False):
        """Bring the container to a running state, recreating it when unusable."""
        with self._lock:
            state = self.container_state()
            if state != "not_found" and (recreate or self.container_image_changed()):
                self._log(f"Recreating container {self.container_name} on the current image")
                self.remove_container()
                state = "not_found"
            if state == "running":
                return
            if state == "not_found":
                self.create_container()
                return
            if state == "paused":
                self._log(f"Unpausing container {self.container_name}")
                self._docker("unpause", self.container_name)
                return
            if state in ("created", "exited"):
                self._log(f"Starting existing container {self.container_name}")
                self._docker("start", self.container_name)
                return
            # dead, restarting, removing: not startable, so replace it outright.
            self._log(f"Container {self.container_name} is {state}; recreating it")
            self.remove_container()
            self.create_container()

    def ensure_running(self):
        """Full preparation: resolve the Docker command, refresh the image, start the container."""
        with self._lock:
            self.resolve_docker_command()
            rebuilt = self.ensure_image()
            self.ensure_container(recreate=rebuilt)

    def start_background_setup(self):
        """Prepare the sandbox (build image, start container) without blocking.

        Safe to call repeatedly; only one setup runs at a time, and a failed
        setup is retried on a later call once its backoff has elapsed.
        """
        with self._setup_lock:
            if self._ready.is_set():
                return
            if self._setup_thread is not None and self._setup_thread.is_alive():
                return
            if time.monotonic() < self._next_retry_at:
                return
            self._setup_thread = threading.Thread(
                target=self._setup, name="sandbox-setup", daemon=True
            )
            self._setup_thread.start()

    def _setup(self):
        try:
            # Resolve first: the ephemeral reset already issues Docker commands,
            # so it must not run with an unverified command and report a
            # permission error where the daemon diagnosis belongs.
            self.resolve_docker_command()
            if self.ephemeral:
                self.reset_for_new_session()
            self.ensure_running()
        except Exception as exc:
            self._setup_failures += 1
            delay = min(RETRY_MAX_DELAY, RETRY_BASE_DELAY * 2 ** (self._setup_failures - 1))
            self._next_retry_at = time.monotonic() + delay
            self._setup_error = str(exc)
            self._log(f"Sandbox setup failed: {exc}")
            self._log(f"Retrying on the next tool call made more than {delay}s from now")
        else:
            self._setup_error = None
            self._setup_failures = 0
            self._next_retry_at = 0.0
            self._ready.set()
            self._log("Sandbox is ready")

    def _require_ready(self):
        """Fast-path readiness gate so tool calls never block on an image build."""
        if self._ready.is_set():
            self._repair_if_stopped()
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

    def _repair_if_stopped(self):
        """Cheap per-call check that the container is still usable.

        Only the container state is inspected on the hot path. Image freshness
        is deliberately not re-checked here: a rebuild belongs in background
        setup, not inside a tool call it would block for minutes while
        destroying the container the session is working in.
        """
        if self.container_state() == "running":
            return
        with self._lock:
            if self.container_state() == "running":
                return
            if not self.image_exists():
                # The image was removed underneath us and has to be rebuilt,
                # which is far too slow to do inline.
                self._ready.clear()
                self.start_background_setup()
                raise RuntimeError(
                    f"The sandbox image {self.image} is missing and is being rebuilt "
                    "in the background. Retry this tool call in a minute or two."
                )
            self._log(f"Container {self.container_name} is not running; repairing it")
            self.ensure_container()

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
        # --user keeps exec on the same account the container was created with;
        # without it a non-root DOCKER_USER silently gets root for tool calls.
        args.extend(["--user", self.user, "--workdir", self.workdir, self.container_name, *command])
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
        """Stop or remove the container on server exit.

        A no-op when the sandbox never came up, so shutdown does not raise from
        an atexit handler on a host where Docker was unreachable all along.
        """
        if not self._docker_command_resolved:
            return
        try:
            state = self.container_state()
            if state == "not_found":
                return
            if self.remove_on_exit:
                self._log(f"Removing container {self.container_name}")
                self._docker("rm", "--force", self.container_name, check=False)
                return
            if state != "running":
                return
            self._log(f"Stopping container {self.container_name}")
            self._docker("stop", "--time", "10", self.container_name, check=False)
        except Exception as exc:
            self._log(f"Could not stop container {self.container_name}: {exc}")
