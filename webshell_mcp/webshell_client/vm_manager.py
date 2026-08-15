import glob
import os
import re
import shlex
import shutil
import subprocess
import sys
import threading
import time
import urllib.request


ISO_DIR_URL = "https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/"
ISO_NAME_RE = re.compile(r"debian-(\d+\.\d+\.\d+)-amd64-netinst\.iso")
# Only used when the mirror listing can't be read; `current` moves off it eventually.
ISO_FALLBACK_NAME = "debian-13.6.0-amd64-netinst.iso"
ISO_MIN_SIZE = 500 * 1024 * 1024  # 500MB — netinst is ~754MB
TOOLCHAIN_VERSION = "2"
TOOLCHAIN_MARKER = f"/var/lib/webshell-mcp/toolchain-{TOOLCHAIN_VERSION}"
TOOLCHAIN_SNAPSHOT = f"clean-base-toolchain-{TOOLCHAIN_VERSION}"

# Keep this baseline aligned with shell_mcp. Web-only dependencies are added by
# the webshell setup below.
REQUIRED_APT_PACKAGES = (
    "ca-certificates curl wget openssh-client git git-lfs "
    "python3 python3-pip python3-venv python3-dev "
    "build-essential nodejs npm "
    "pandoc poppler-utils libreoffice-nogui ghostscript qpdf tesseract-ocr "
    "fonts-dejavu-core fonts-liberation2 fonts-noto-core"
)
AGENT_APT_PACKAGES = (
    "vim nano tmux jq yq tree file less rsync patch diffutils moreutils gawk "
    "unzip zip p7zip-full xz-utils tar fzf bat ripgrep fd-find "
    "dnsutils iputils-ping netcat-openbsd socat whois "
    "htop lsof strace procps xxd binutils "
    "cmake pkg-config autoconf automake clang shellcheck shfmt "
    "sqlite3 ffmpeg imagemagick graphviz xvfb man-db gnupg openssl cron ufw"
)
OPTIONAL_APT_PACKAGES = "wkhtmltopdf unoconv miller"


def _resolve_iso_name() -> str:
    """Filename of the netinst ISO Debian is currently serving.

    Debian's `current` directory only ever holds the newest point release, so a
    pinned filename starts 404ing (wget exit 8) the moment a new one ships.
    """
    try:
        with urllib.request.urlopen(ISO_DIR_URL + "SHA256SUMS", timeout=30) as resp:
            body = resp.read().decode("utf-8", "replace")
        versions = set(ISO_NAME_RE.findall(body))
        if versions:
            latest = max(versions, key=lambda v: tuple(int(p) for p in v.split(".")))
            return f"debian-{latest}-amd64-netinst.iso"
        raise ValueError("no netinst ISO listed")
    except Exception as exc:
        sys.stderr.write(
            f"[vm-manager] Could not resolve current Debian ISO ({exc}); "
            f"falling back to {ISO_FALLBACK_NAME}\n"
        )
        sys.stderr.flush()
        return ISO_FALLBACK_NAME


def _apt_toolchain_lines() -> list[str]:
    """Shell lines for reliable, release-tolerant package provisioning."""
    return [
        "export DEBIAN_FRONTEND=noninteractive",
        "apt_retry() {",
        "  attempts=0",
        "  until apt-get -o Acquire::Retries=3 \"$@\"; do",
        "    attempts=$((attempts + 1))",
        "    [ \"$attempts\" -ge 3 ] && return 1",
        "    sleep 5",
        "  done",
        "}",
        "install_available() {",
        "  apt_retry install -y --no-install-recommends \"$@\" && return 0",
        "  echo 'Package group failed; retrying packages individually' >&2",
        "  for package in \"$@\"; do",
        "    apt_retry install -y --no-install-recommends \"$package\" || " +
        "echo \"WARNING: package $package is unavailable\" >&2",
        "  done",
        "}",
        "dpkg --configure -a || true",
        "apt_retry update",
        f"apt_retry install -y --no-install-recommends {REQUIRED_APT_PACKAGES}",
        f"install_available {AGENT_APT_PACKAGES}",
        f"install_available {OPTIONAL_APT_PACKAGES}",
    ]

SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


class _Spinner:
    """Terminal spinner for long-running operations."""

    def __init__(self, message: str):
        self.message = message
        self._stop = threading.Event()
        self._thread = None

    def _spin(self):
        i = 0
        while not self._stop.is_set():
            frame = SPINNER_FRAMES[i % len(SPINNER_FRAMES)]
            sys.stderr.write(f"\r{frame} {self.message}")
            sys.stderr.flush()
            i += 1
            self._stop.wait(0.1)
        sys.stderr.write(f"\r  {self.message} — done\n")
        sys.stderr.flush()

    def __enter__(self):
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_exc):
        self._stop.set()
        self._thread.join()

    def update(self, message: str):
        self.message = message


class VMManager:
    """Manages VirtualBox VM lifecycle: create, start, wait for SSH."""

    def __init__(self):
        self.vm_name = os.getenv("VM_NAME", "ai-webshell")
        self.vm_ram = int(os.getenv("VM_RAM", "2048"))
        self.vm_cpus = int(os.getenv("VM_CPUS", "2"))
        self.vm_disk = int(os.getenv("VM_DISK", "30720"))
        self.vm_user = os.getenv("SSH_USER", "ai-agent")
        self.vm_pass = os.getenv("VM_PASS", "changeme123")
        self.iso_url = os.getenv("ISO_URL")
        self.iso_path_pinned = os.getenv("ISO_PATH")
        # Resolving the current release needs the network, so defer it to
        # ensure_iso() and start from whatever is already on disk.
        self.iso_path = (
            os.path.expanduser(self.iso_path_pinned)
            if self.iso_path_pinned
            else self._local_iso() or os.path.expanduser(f"~/{ISO_FALLBACK_NAME}")
        )
        self.ssh_pubkey_path = os.path.expanduser(
            os.getenv("SSH_PUBKEY_PATH", "~/.ssh/ai_vm_key.pub")
        )
        self.ssh_key_path = os.path.expanduser(
            os.getenv("SSH_KEY_PATH", "~/.ssh/ai_vm_key")
        )
        self.network_mode = os.getenv("NETWORK_MODE", "hostonly")
        self.host_only_if = os.getenv("HOST_ONLY_IF", "vboxnet0")
        self.shared_folder = os.path.expanduser(
            os.getenv("SHARED_FOLDER", "~/vm-share")
        )
        self.ssh_host = os.getenv("SSH_HOST")
        self.ssh_port = int(os.getenv("SSH_PORT", "22"))
        self.searxng_port = int(os.getenv("SEARXNG_PORT", "8889"))
        self.vm_sudo = os.getenv("VM_SUDO", "false").lower() in ("1", "true", "yes")
        self.known_hosts_path = os.path.expanduser(
            os.getenv("SSH_KNOWN_HOSTS", "~/.webshell_mcp/known_hosts")
        )

    def _run(self, *args, check=True, capture=True) -> subprocess.CompletedProcess:
        result = subprocess.run(
            args,
            check=False,
            capture_output=capture,
            text=True,
        )
        if check and result.returncode != 0:
            stderr = result.stderr.strip() if result.stderr else ""
            stdout = result.stdout.strip() if result.stdout else ""
            if stderr:
                sys.stderr.write(f"[vm-manager] STDERR: {stderr}\n")
                sys.stderr.flush()
            if stdout:
                sys.stderr.write(f"[vm-manager] STDOUT: {stdout}\n")
                sys.stderr.flush()
            raise subprocess.CalledProcessError(
                result.returncode, args, stdout or None, stderr or None,
            )
        return result

    def _vbox(self, *args, **kwargs) -> subprocess.CompletedProcess:
        return self._run("vboxmanage", *args, **kwargs)

    def _log(self, msg: str):
        sys.stderr.write(f"[vm-manager] {msg}\n")
        sys.stderr.flush()

    def vm_exists(self) -> bool:
        result = self._vbox("list", "vms", check=False)
        return f'"{self.vm_name}"' in (result.stdout or "")

    def vm_state(self) -> str:
        """Return VM state: 'running', 'poweroff', 'saved', etc."""
        result = self._vbox("showvminfo", self.vm_name, "--machinereadable", check=False)
        if result.returncode != 0:
            return "not_found"
        for line in result.stdout.splitlines():
            if line.startswith("VMState="):
                return line.split("=", 1)[1].strip('"')
        return "unknown"

    def vm_ip(self) -> str | None:
        """Get VM IP from guest properties."""
        result = self._vbox(
            "guestproperty", "get", self.vm_name,
            "/VirtualBox/GuestInfo/Net/0/V4/IP",
            check=False,
        )
        if result.returncode == 0 and "Value:" in result.stdout:
            return result.stdout.split("Value:")[1].strip()
        return None

    def _iso_looks_valid(self) -> bool:
        """Check that the ISO exists and passes minimum size check."""
        if not os.path.isfile(self.iso_path):
            return False
        size = os.path.getsize(self.iso_path)
        if size < ISO_MIN_SIZE:
            self._log(f"ISO too small ({size / (1024**2):.0f}MB) — likely incomplete")
            return False
        return True

    def _local_iso(self) -> str | None:
        """Newest complete netinst ISO already sitting in the home directory."""
        candidates = []
        for path in glob.glob(os.path.expanduser("~/debian-*-amd64-netinst.iso")):
            match = ISO_NAME_RE.fullmatch(os.path.basename(path))
            if match and os.path.getsize(path) >= ISO_MIN_SIZE:
                candidates.append(
                    (tuple(int(p) for p in match.group(1).split(".")), path)
                )
        return max(candidates)[1] if candidates else None

    def ensure_iso(self):
        if self._iso_looks_valid() and not os.path.isfile(self.iso_path + ".part"):
            self._log(f"ISO found: {self.iso_path}")
            return

        iso_url = self.iso_url or ISO_DIR_URL + _resolve_iso_name()
        if not self.iso_path_pinned:
            # Download whatever release `current` is serving today
            self.iso_path = os.path.expanduser(f"~/{os.path.basename(iso_url)}")
        part_path = self.iso_path + ".part"

        if os.path.isfile(self.iso_path) and not os.path.isfile(part_path):
            os.rename(self.iso_path, part_path)

        if os.path.isfile(part_path):
            size_mb = os.path.getsize(part_path) / (1024 * 1024)
            self._log(f"Resuming download ({size_mb:.0f}MB already downloaded)...")

        with _Spinner(f"Downloading {os.path.basename(iso_url)} (~754MB)"):
            self._run(
                "wget", "-c", "-q", "-O", part_path, iso_url,
            )
            os.rename(part_path, self.iso_path)

    def ensure_ssh_key(self):
        if os.path.isfile(self.ssh_pubkey_path):
            self._log(f"SSH key found: {self.ssh_pubkey_path}")
            return
        self._log("Generating SSH key pair...")
        self._run(
            "ssh-keygen", "-t", "ed25519",
            "-f", self.ssh_key_path, "-N", "",
        )
        self._log(f"SSH key generated: {self.ssh_key_path}")

    def create_vm(self):
        self._log(f"Creating VM: {self.vm_name}")
        self._vbox("createvm", "--name", self.vm_name, "--ostype", "Debian_64", "--register")

        self._log(f"Configuring: {self.vm_ram}MB RAM, {self.vm_cpus} CPUs")
        self._vbox(
            "modifyvm", self.vm_name,
            "--memory", str(self.vm_ram),
            "--cpus", str(self.vm_cpus),
            "--vram", "16",
            "--graphicscontroller", "vmsvga",
            "--audio", "none",
            "--usb", "off",
            "--usbehci", "off",
        )

        disk_path = os.path.expanduser(
            f"~/VirtualBox VMs/{self.vm_name}/{self.vm_name}.vdi"
        )
        self._log(f"Creating {self.vm_disk}MB disk")
        self._vbox(
            "createmedium", "disk",
            "--filename", disk_path,
            "--size", str(self.vm_disk),
            "--format", "VDI",
            "--variant", "Standard",
        )

        self._log("Attaching storage")
        self._vbox("storagectl", self.vm_name, "--name", "SATA", "--add", "sata", "--controller", "IntelAhci")
        self._vbox(
            "storageattach", self.vm_name,
            "--storagectl", "SATA", "--port", "0", "--device", "0",
            "--type", "hdd", "--medium", disk_path,
        )
        self._vbox("storagectl", self.vm_name, "--name", "IDE", "--add", "ide")

        self._configure_network()
        self._configure_shared_folder()

        self._configure_unattended_install()

        self._log("Taking pre-install snapshot")
        self._vbox("snapshot", self.vm_name, "take", "pre-install", "--description", "Before unattended install")

    def _configure_network(self):
        self._log(f"Configuring network: {self.network_mode}")
        if self.network_mode == "hostonly":
            self._vbox("modifyvm", self.vm_name, "--nic1", "nat")
            self._vbox("modifyvm", self.vm_name, "--natpf1", "ssh,tcp,127.0.0.1,2223,,22")
            self._vbox("modifyvm", self.vm_name, "--natpf1",
                        f"searxng,tcp,127.0.0.1,{self.searxng_port},,{self.searxng_port}")
            self._vbox("hostonlyif", "create", check=False)
            self._vbox(
                "modifyvm", self.vm_name,
                "--nic2", "hostonly", "--hostonlyadapter2", self.host_only_if,
            )
        elif self.network_mode == "nat":
            self._vbox("modifyvm", self.vm_name, "--nic1", "nat")
            self._vbox(
                "modifyvm", self.vm_name,
                "--natpf1", "ssh,tcp,127.0.0.1,2223,,22",
            )
            self._vbox("modifyvm", self.vm_name, "--natpf1",
                        f"searxng,tcp,127.0.0.1,{self.searxng_port},,{self.searxng_port}")
        elif self.network_mode == "bridged":
            result = self._run("ip", "route", "get", "1")
            host_if = result.stdout.split()[4]
            self._vbox(
                "modifyvm", self.vm_name,
                "--nic1", "bridged", "--bridgeadapter1", host_if,
            )

    def _configure_shared_folder(self):
        self._log(f"Setting up shared folder: {self.shared_folder}")
        os.makedirs(self.shared_folder, exist_ok=True)
        self._vbox(
            "sharedfolder", "add", self.vm_name,
            "--name", "vm-share",
            "--hostpath", self.shared_folder,
            "--automount", "--auto-mount-point", "/mnt/share",
        )

    def _write_setup_script(self) -> str:
        """Write post-install setup steps to a script file in the VM dir."""
        with open(self.ssh_pubkey_path) as f:
            ssh_pubkey = f.read().strip()

        vm_dir = os.path.expanduser(f"~/VirtualBox VMs/{self.vm_name}")
        script_path = os.path.join(vm_dir, "vbox-setup.sh")

        lines = [
            "#!/bin/sh",
            f"mkdir -p /home/{self.vm_user}/.ssh",
            f"printf '%s\\n' {shlex.quote(ssh_pubkey)} > /home/{self.vm_user}/.ssh/authorized_keys",
            f"chown -R {self.vm_user}:{self.vm_user} /home/{self.vm_user}/.ssh",
            f"chmod 700 /home/{self.vm_user}/.ssh",
            f"chmod 600 /home/{self.vm_user}/.ssh/authorized_keys",
            *_apt_toolchain_lines(),
            "ufw default deny incoming || true",
            "ufw default allow outgoing || true",
            "ufw allow ssh || true",
            f"ufw allow {self.searxng_port}/tcp || true",
            "ufw --force enable || true",
            "sed -i 's/^#\\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config || true",
            "sed -i 's/^#\\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config || true",
            f"grep -q 'AllowUsers {self.vm_user}' /etc/ssh/sshd_config || echo 'AllowUsers {self.vm_user}' >> /etc/ssh/sshd_config",
            "systemctl restart ssh || true",
            f"usermod -aG vboxsf {self.vm_user} || true",
            "mkdir -p /etc/pip.conf.d",
            "printf '[global]\\nbreak-system-packages = true\\n' > /etc/pip.conf",
            # Ensure pip3 is available — apt install may have silently failed
            "command -v pip3 || apt-get install -y python3-pip || " +
            "(curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py && python3 /tmp/get-pip.py) || true",
            # --- Web fetch dependencies ---
            "pip3 install -q curl_cffi trafilatura markdownify playwright || true",
            "python3 -m playwright install --with-deps chromium || true",
            # --- Document / office Python libraries ---
            "pip3 install -q python-docx pdfplumber pypdf reportlab weasyprint " +
            "openpyxl pandas xlrd csvkit python-pptx beautifulsoup4 lxml " +
            "pillow cairosvg ebooklib pytesseract pdf2image || true",
            # --- HTTP / network ---
            "pip3 install -q requests httpx aiohttp paramiko fabric || true",
            # --- CLI / output ---
            "pip3 install -q click rich typer tqdm loguru || true",
            # --- Data / config ---
            "pip3 install -q pydantic pyyaml toml python-dotenv jinja2 " +
            "arrow pendulum humanize tabulate orjson msgpack " +
            "chardet python-magic dateparser rapidfuzz || true",
            # --- Scheduling / task queues ---
            "pip3 install -q tenacity schedule celery || true",
            # --- Databases ---
            "pip3 install -q redis psycopg2-binary pymysql pymongo sqlalchemy alembic || true",
            # --- Data science ---
            "pip3 install -q numpy scipy matplotlib seaborn plotly scikit-learn || true",
            # --- NLP / AI ---
            "pip3 install -q nltk tiktoken anthropic openai || true",
            # --- Web / API serving ---
            "pip3 install -q fastapi uvicorn || true",
            # --- Security ---
            "pip3 install -q cryptography || true",
            # --- Dev tools ---
            "pip3 install -q psutil gitpython pygments uv black ruff mypy " +
            "pytest hypothesis watchdog || true",
            # --- Cloud / infra SDKs ---
            "pip3 install -q docker kubernetes boto3 " +
            "google-cloud-storage azure-storage-blob || true",
            # --- SearXNG installation ---
            "git clone --depth 1 https://github.com/searxng/searxng.git /opt/searxng || true",
            "pip3 install -q setuptools wheel || true",
            "pip3 install -q -r /opt/searxng/requirements.txt || true",
            "pip3 install -q --no-build-isolation --no-deps /opt/searxng || true",
            # SearXNG settings
            "mkdir -p /etc/searxng",
            "cat > /etc/searxng/settings.yml << 'SEARXNG_EOF'\n" +
            "use_default_settings: true\n" +
            "general:\n" +
            "  instance_name: \"webshell-mcp searxng\"\n" +
            "  debug: false\n" +
            "server:\n" +
            f"  port: {self.searxng_port}\n" +
            "  bind_address: \"0.0.0.0\"\n" +
            "  secret_key: \"webshell-mcp-searxng\"\n" +
            "  limiter: false\n" +
            "  image_proxy: true\n" +
            "  method: POST\n" +
            "search:\n" +
            "  safe_search: 0\n" +
            "  default_lang: \"en\"\n" +
            "  formats:\n" +
            "    - html\n" +
            "    - json\n" +
            "SEARXNG_EOF",
            # SearXNG systemd service
            "cat > /etc/systemd/system/searxng.service << 'SYSTEMD_EOF'\n" +
            "[Unit]\n" +
            "Description=SearXNG\n" +
            "After=network.target\n" +
            "[Service]\n" +
            "Type=simple\n" +
            "Environment=SEARXNG_SETTINGS_PATH=/etc/searxng/settings.yml\n" +
            "ExecStart=/usr/bin/python3 -m searx.webapp\n" +
            "Restart=always\n" +
            "RestartSec=5\n" +
            "[Install]\n" +
            "WantedBy=multi-user.target\n" +
            "SYSTEMD_EOF",
            "systemctl daemon-reload || true",
            "systemctl enable searxng || true",
            "systemctl start searxng || true",
            "npm install --global typescript tsx eslint prettier || true",
            "missing=''",
            "for command in git node npm python3 pip3 gcc make pandoc libreoffice; do",
            "  command -v \"$command\" >/dev/null 2>&1 || missing=\"$missing $command\"",
            "done",
            "[ -z \"$missing\" ] || { echo \"Missing required tools:$missing\" >&2; exit 1; }",
            "python3 -c 'import docx, openpyxl, pptx, pypdf, reportlab, playwright' || " +
            "{ echo 'Missing required document or browser Python libraries' >&2; exit 1; }",
            f"mkdir -p {os.path.dirname(TOOLCHAIN_MARKER)}",
            f"touch {TOOLCHAIN_MARKER}",
        ]

        if self.vm_sudo:
            lines += [
                f"usermod -aG sudo {self.vm_user} || true",
                f"echo '{self.vm_user} ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/{self.vm_user}",
                f"chmod 440 /etc/sudoers.d/{self.vm_user}",
            ]

        with open(script_path, "w") as f:
            f.write("\n".join(lines) + "\n")

        return script_path

    def _guest_toolchain_is_current(self, host: str, port: int) -> bool:
        result = subprocess.run(
            [
                "ssh", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes",
                "-p", str(port), "-i", self.ssh_key_path,
                f"{self.vm_user}@{host}", f"test -f {TOOLCHAIN_MARKER}",
            ],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0

    def _ensure_guest_toolchain(self, host: str, port: int):
        """Provision or repair the toolchain in an already-created VM."""
        if self._guest_toolchain_is_current(host, port):
            return

        self._log(f"Installing managed VM toolchain version {TOOLCHAIN_VERSION}")
        with open(self._write_setup_script()) as f:
            script = f.read()

        ssh = [
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes",
            "-p", str(port), "-i", self.ssh_key_path, f"{self.vm_user}@{host}",
        ]
        passwordless = subprocess.run(
            [*ssh, "sudo -n true"], capture_output=True, text=True,
        ).returncode == 0
        if passwordless:
            result = subprocess.run(
                [*ssh, "sudo -n /bin/sh -s"], input=script,
                capture_output=True, text=True,
            )
        else:
            result = subprocess.run(
                [*ssh, "sudo -S -p '' /bin/sh -s"],
                input=f"{self.vm_pass}\n{script}", capture_output=True, text=True,
            )
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
            raise RuntimeError(f"Managed VM toolchain provisioning failed: {detail}")

    def _configure_unattended_install(self):
        self._log("Configuring unattended install")

        self._write_setup_script()

        self._vbox(
            "unattended", "install", self.vm_name,
            f"--iso={self.iso_path}",
            f"--user={self.vm_user}",
            f"--password={self.vm_pass}",
            "--full-user-name=AI Agent",
            "--time-zone=UTC",
            "--hostname=ai-webshell.local",
            "--post-install-command=chroot /target /bin/sh /cdrom/vbox-setup.sh",
        )

        self._patch_viso_disable_speech()
        self._patch_viso_add_setup_script()
        self._patch_preseed()

    def _patch_preseed(self):
        """Fix VirtualBox placeholder values in the generated preseed."""
        vm_dir = os.path.expanduser(f"~/VirtualBox VMs/{self.vm_name}")
        viso_files = sorted(
            [f for f in os.listdir(vm_dir) if f.endswith("-aux-iso.viso")],
            key=lambda f: os.path.getmtime(os.path.join(vm_dir, f)),
        )
        if not viso_files:
            self._log("WARNING: No VISO file found for preseed patch")
            return

        viso_path = os.path.join(vm_dir, viso_files[-1])
        preseed_path = None
        with open(viso_path) as f:
            viso_content = f.read()
        try:
            tokens = shlex.split(viso_content)
        except ValueError:
            tokens = viso_content.split()
        for token in tokens:
            if "preseed.cfg=" in token and ":must-remove:" not in token:
                preseed_path = token.split("preseed.cfg=", 1)[1]
                break

        if not preseed_path or not os.path.isfile(preseed_path):
            self._log("WARNING: preseed file not found")
            return

        with open(preseed_path) as f:
            content = f.read()

        content = content.replace(
            "--preseed-late-command",
            "--preseed-late-command || true",
        )

        if "pkgsel/include" not in content:
            content += (
                "\nd-i pkgsel/include string "
                "openssh-server sudo git curl wget ca-certificates\n"
            )

        content = content.replace(
            "d-i passwd/user-default-groups string admin",
            "d-i passwd/user-default-groups string sudo",
        )

        content = content.replace(
            "d-i mirror/country string CT",
            "d-i mirror/country string manual\n"
            "d-i mirror/http/hostname string deb.debian.org\n"
            "d-i mirror/http/directory string /debian",
        )

        content = content.replace(
            "d-i netcfg/choose_interface select auto",
            "d-i netcfg/choose_interface select enp0s3",
        )

        with open(preseed_path, "w") as f:
            f.write(content)

        self._log("Patched preseed: mirror=deb.debian.org, interface=enp0s3")

    def _patch_viso_add_setup_script(self):
        """Add vbox-setup.sh to the VISO."""
        vm_dir = os.path.expanduser(f"~/VirtualBox VMs/{self.vm_name}")
        script_path = os.path.join(vm_dir, "vbox-setup.sh")
        viso_files = sorted(
            [f for f in os.listdir(vm_dir) if f.endswith("-aux-iso.viso")],
            key=lambda f: os.path.getmtime(os.path.join(vm_dir, f)),
        )
        if not viso_files:
            self._log("WARNING: No VISO file found for setup script")
            return

        viso_path = os.path.join(vm_dir, viso_files[-1])
        quoted_path = f"'{script_path}'" if " " in script_path else script_path
        entry = f"/vbox-setup.sh={quoted_path}"

        with open(viso_path) as f:
            content = f.read()
        lines = [
            line for line in content.splitlines(keepends=True)
            if not line.strip().startswith("/vbox-setup.sh=")
        ]
        with open(viso_path, "w") as f:
            f.write("".join(lines) + f"\n{entry}\n")

        self._log(f"Added vbox-setup.sh to VISO: {script_path}")

    def _patch_viso_disable_speech(self):
        """Replace menu.cfg in the VISO with a minimal version."""
        vm_dir = os.path.expanduser(f"~/VirtualBox VMs/{self.vm_name}")
        viso_files = sorted(
            [f for f in os.listdir(vm_dir) if f.endswith("-aux-iso.viso")],
            key=lambda f: os.path.getmtime(os.path.join(vm_dir, f)),
        )
        if not viso_files:
            self._log("WARNING: No VISO file found to patch")
            return

        viso_path = os.path.join(vm_dir, viso_files[-1])

        default_label = "install"
        with open(viso_path) as f:
            viso_content = f.read()
        try:
            tokens = shlex.split(viso_content)
        except ValueError:
            tokens = viso_content.split()
        for token in tokens:
            if "isolinux/txt.cfg=" in token and ":must-remove:" not in token:
                local_txt_cfg = token.split("txt.cfg=", 1)[1]
                if os.path.isfile(local_txt_cfg):
                    with open(local_txt_cfg) as tf:
                        for tline in tf:
                            tline = tline.strip()
                            if tline.startswith("default "):
                                default_label = tline.split()[1]
                                break
                break

        menu_path = os.path.join(vm_dir, "patched-menu.cfg")
        with open(menu_path, "w") as f:
            f.write(f"default {default_label}\n")
            f.write("timeout 10\n")
            f.write("prompt 0\n")
            f.write("include txt.cfg\n")

        quoted_path = f"'{menu_path}'" if " " in menu_path else menu_path
        remove_entry = "isolinux/menu.cfg=:must-remove:"
        add_entry = f"isolinux/menu.cfg={quoted_path}"
        new_block = f"\n{remove_entry}\n{add_entry}\n"

        with open(viso_path) as f:
            content = f.read()
        lines = [
            line for line in content.splitlines(keepends=True)
            if not line.strip().startswith("isolinux/menu.cfg=")
        ]
        content = "".join(lines) + new_block
        with open(viso_path, "w") as f:
            f.write(content)

        self._log(f"Patched VISO: menu.cfg → default={default_label}, timeout=1s (speech installer disabled)")

    def _snapshot_exists(self, name: str) -> bool:
        """Return True if a snapshot with the given name exists."""
        result = self._vbox("snapshot", self.vm_name, "list", "--machinereadable", check=False)
        return f'SnapshotName="{name}"' in (result.stdout or "")

    def restore_clean(self, snapshot_name: str = TOOLCHAIN_SNAPSHOT):
        """Power off the VM (if running) and restore a clean snapshot."""
        state = self.vm_state()
        if state == "running":
            self._log("Powering off VM for snapshot restore")
            self._vbox("controlvm", self.vm_name, "poweroff")
            time.sleep(3)
        with _Spinner(f"Restoring {snapshot_name} snapshot"):
            self._vbox("snapshot", self.vm_name, "restore", snapshot_name)

    def start_vm(self):
        state = self.vm_state()
        if state == "running":
            self._log("VM is already running — skipping startvm")
            return
        if state == "saved":
            self._log("VM is saved — restoring")
        else:
            self._log(f"Starting VM (headless) — current state: {state}")
        self._vbox("startvm", self.vm_name, "--type", "headless")

    def _hostonly_vm_ip(self) -> str | None:
        """Find VM's IP on the hostonly interface."""
        import concurrent.futures
        import ipaddress
        import socket

        result = self._run("ip", "-o", "-4", "addr", "show", self.host_only_if, check=False)
        if result.returncode != 0 or not result.stdout:
            return None
        parts = result.stdout.split()
        cidr = next((p for p in parts if "/" in p), None)
        if not cidr:
            return None
        host_ip = cidr.split("/")[0]
        network = ipaddress.IPv4Interface(cidr).network

        def _try_ssh(addr: str) -> str | None:
            try:
                with socket.create_connection((addr, 22), timeout=1):
                    return addr
            except OSError:
                return None

        neigh = self._run("ip", "neigh", "show", "dev", self.host_only_if, check=False)
        for line in (neigh.stdout or "").splitlines():
            addr = line.split()[0]
            try:
                if ipaddress.IPv4Address(addr) in network and addr != host_ip:
                    if _try_ssh(addr):
                        return addr
            except ValueError:
                continue

        candidates = [str(h) for h in network.hosts() if str(h) != host_ip]
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as ex:
            futures = {ex.submit(_try_ssh, addr): addr for addr in candidates}
            for future in concurrent.futures.as_completed(futures):
                addr = future.result()
                if addr:
                    return addr
        return None

    def wait_for_ssh(self, timeout: int = 600, interval: int = 10) -> str:
        """Wait for SSH to become reachable. Returns the SSH host to use."""
        if self.network_mode == "hostonly":
            host = None
            port = 22
        elif self.network_mode == "nat":
            host = "127.0.0.1"
            port = 2223
        else:
            host = self.ssh_host
            port = self.ssh_port

        deadline = time.time() + timeout

        with _Spinner(f"Waiting for SSH {host or '(detecting IP)'}:{port}") as spinner:
            while time.time() < deadline:
                elapsed = int(time.time() + timeout - deadline)

                if host is None:
                    ip = self._hostonly_vm_ip()
                    if ip:
                        host = ip
                        spinner.update(f"Waiting for SSH {host}:{port} ({elapsed}s)")
                    else:
                        spinner.update(f"Waiting for VM IP on {self.host_only_if} ({elapsed}s)")
                        time.sleep(interval)
                        continue

                spinner.update(f"Waiting for SSH {host}:{port} ({elapsed}s)")

                result = subprocess.run(
                    [
                        "ssh",
                        "-o", "StrictHostKeyChecking=no",
                        "-o", "ConnectTimeout=5",
                        "-o", "BatchMode=yes",
                        "-p", str(port),
                        "-i", self.ssh_key_path,
                        f"{self.vm_user}@{host}",
                        "echo ok",
                    ],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0 and "ok" in result.stdout:
                    return host
                time.sleep(interval)

        raise TimeoutError(f"SSH not reachable after {timeout}s")

    def record_host_key(self, host: str, port: int) -> str | None:
        """Pin the VM's SSH host key so clients never have to trust on first use.

        Called once the VM answers SSH. The key is captured here, while we are
        talking to a VM we just built on this machine, so ``ShellClient`` can
        reject an unknown key instead of accepting whatever it is offered.

        Args:
            host: Address the VM answered SSH on.
            port: SSH port the VM answered on.

        Returns:
            Path to the known_hosts file, or None if the key could not be read.
        """
        if not shutil.which("ssh-keyscan"):
            self._log("ssh-keyscan not found -- cannot pin the VM host key")
            return None

        try:
            result = self._run("ssh-keyscan", "-p", str(port), host, check=False)
        except OSError as exc:
            # Pinning is part of start-up; never let it take the VM down with it.
            self._log(f"ssh-keyscan failed ({exc}) -- host key not pinned")
            return None
        scanned = [
            line for line in (result.stdout or "").splitlines()
            if line.strip() and not line.startswith("#")
        ]
        if not scanned:
            self._log(f"No host key offered by {host}:{port} -- not pinned")
            return None

        path = self.known_hosts_path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # The VM is issued a new host key on every rebuild, so a stale entry
        # for this address has to go before the current one is written.
        stale = {host, f"[{host}]:{port}"}
        kept: list[str] = []
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as handle:
                kept = [
                    line.rstrip("\n") for line in handle
                    if line.split(" ", 1)[0] not in stale
                ]
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("\n".join([*kept, *scanned]) + "\n")
        os.chmod(path, 0o600)
        self._log(f"Pinned VM host key in {path}")
        return path

    def stop_vm(self):
        """Power off the VM if it is running."""
        if not shutil.which("vboxmanage"):
            return
        state = self.vm_state()
        if state == "running":
            self._log("Powering off VM")
            self._vbox("controlvm", self.vm_name, "poweroff", check=False)

    def ensure_running(self) -> dict:
        """Ensure VM exists, is running, and SSH is reachable.

        Returns dict with ssh_host, ssh_port, and searxng_url.
        """
        if not shutil.which("vboxmanage"):
            self._log("VirtualBox not found — assuming external SSH target")
            searxng_host = self.ssh_host
            # Not our VM, so its key is not ours to pin; it has to already
            # be in the caller's known_hosts.
            return {
                "ssh_host": self.ssh_host,
                "ssh_port": self.ssh_port,
                "known_hosts": None,
                "searxng_url": f"http://{searxng_host}:{self.searxng_port}",
            }

        state = self.vm_state() if self.vm_exists() else "not_found"

        snapshot_is_current = False
        if state == "not_found":
            self._log("VM does not exist — creating from scratch")
            self.ensure_iso()
            self.ensure_ssh_key()
            with _Spinner("Creating and configuring VM"):
                self.create_vm()
            self.start_vm()
            host = self.wait_for_ssh(timeout=1200)
            port = 2223 if self.network_mode == "nat" else self.ssh_port
            self._ensure_guest_toolchain(host, port)
            with _Spinner("Taking post-install snapshot"):
                self._vbox("snapshot", self.vm_name, "take", TOOLCHAIN_SNAPSHOT,
                            "--description", "Validated web, development, and document toolchain")
        else:
            snapshot_is_current = self._snapshot_exists(TOOLCHAIN_SNAPSHOT)
            if snapshot_is_current:
                self.restore_clean(TOOLCHAIN_SNAPSHOT)
            elif self._snapshot_exists("clean-base"):
                self.restore_clean("clean-base")
            else:
                self._log("clean-base snapshot not found — starting as-is")
            self.start_vm()
            host = self.wait_for_ssh(timeout=120)

        port = 2223 if self.network_mode == "nat" else self.ssh_port
        if state != "not_found":
            self._ensure_guest_toolchain(host, port)
            if not snapshot_is_current:
                with _Spinner("Saving upgraded toolchain snapshot"):
                    self._vbox("snapshot", self.vm_name, "take", TOOLCHAIN_SNAPSHOT,
                               "--description", "Validated web, development, and document toolchain")
        # For NAT mode, SearXNG is port-forwarded to localhost;
        # for hostonly/bridged, connect to the VM IP directly.
        if self.network_mode == "nat":
            searxng_host = "127.0.0.1"
        else:
            searxng_host = host
        return {
            "ssh_host": host,
            "ssh_port": port,
            "known_hosts": self.record_host_key(host, port),
            "searxng_url": f"http://{searxng_host}:{self.searxng_port}",
        }
