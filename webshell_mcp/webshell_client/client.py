import os
import stat

import paramiko


class ShellClient:
    """SSH/SFTP client for shell operations."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        known_hosts: str | None = None,
    ):
        self.host = host or os.getenv("SSH_HOST")
        self.port = port or int(os.getenv("SSH_PORT", "22"))
        self.user = os.getenv("SSH_USER")
        self.key_path = os.getenv("SSH_KEY_PATH")
        self.password = os.getenv("SSH_PASSWORD")
        self.known_hosts = os.path.expanduser(
            known_hosts or os.getenv("SSH_KNOWN_HOSTS", "~/.webshell_mcp/known_hosts")
        )
        self.timeout = int(os.getenv("SSH_TIMEOUT", "10"))
        self.command_timeout = int(os.getenv("COMMAND_TIMEOUT", "1200"))
        self._client: paramiko.SSHClient | None = None

    def connect(self):
        """Establish SSH connection to the remote host."""
        self._client = paramiko.SSHClient()
        self._client.load_system_host_keys()
        if os.path.isfile(self.known_hosts):
            self._client.load_host_keys(self.known_hosts)
        # An unknown host key is always a failure. The managed VM's key is
        # pinned by VMManager.record_host_key while the VM is being built, so
        # there is no first-contact gap to cover; any other target has to be
        # in the system known_hosts or in SSH_KNOWN_HOSTS already.
        self._client.set_missing_host_key_policy(paramiko.RejectPolicy())
        kwargs = dict(
            hostname=self.host,
            port=self.port,
            username=self.user,
            timeout=self.timeout,
        )
        if self.key_path:
            kwargs["key_filename"] = os.path.expanduser(self.key_path)
        else:
            kwargs["password"] = self.password
        self._client.connect(**kwargs)

    def _ensure_connected(self):
        """Reconnect if the connection was lost."""
        if self._client is None or self._client.get_transport() is None or not self._client.get_transport().is_active():
            self.connect()

    def execute(self, command: str, timeout: int | None = None) -> dict:
        """Execute a shell command and return stdout, stderr, and exit code."""
        self._ensure_connected()
        stdin, stdout, stderr = self._client.exec_command(
            command, timeout=timeout or self.command_timeout
        )
        return {
            "stdout": stdout.read().decode(),
            "stderr": stderr.read().decode(),
            "exit_code": stdout.channel.recv_exit_status(),
        }

    def _sftp(self) -> paramiko.SFTPClient:
        """Get an SFTP client, connecting if needed."""
        self._ensure_connected()
        return self._client.open_sftp()

    def upload(self, local_path: str, remote_path: str) -> dict:
        """Upload a local file to the remote host via SFTP."""
        sftp = self._sftp()
        try:
            sftp.put(local_path, remote_path)
            file_stat = sftp.stat(remote_path)
            return {
                "remote_path": remote_path,
                "size": file_stat.st_size,
            }
        finally:
            sftp.close()

    def download(self, remote_path: str, local_path: str) -> dict:
        """Download a remote file to the local host via SFTP."""
        sftp = self._sftp()
        try:
            sftp.get(remote_path, local_path)
            local_size = os.path.getsize(local_path)
            return {
                "local_path": local_path,
                "size": local_size,
            }
        finally:
            sftp.close()

    def _resolve_path(self, sftp: paramiko.SFTPClient, path: str) -> str:
        """Resolve ~ to the remote home directory."""
        if path == "~" or path.startswith("~/"):
            home = sftp.normalize(".")
            return home + path[1:]
        return path

    def list_remote(self, path: str = "~") -> list[dict]:
        """List files in a remote directory via SFTP."""
        sftp = self._sftp()
        try:
            path = self._resolve_path(sftp, path)
            entries = []
            for attr in sftp.listdir_attr(path):
                entries.append({
                    "name": attr.filename,
                    "size": attr.st_size,
                    "is_dir": stat.S_ISDIR(attr.st_mode) if attr.st_mode else False,
                    "permissions": oct(attr.st_mode & 0o777) if attr.st_mode else None,
                    "modified": attr.st_mtime,
                })
            return entries
        finally:
            sftp.close()

    def read_remote(self, path: str) -> str:
        """Read a remote file's contents via SFTP."""
        sftp = self._sftp()
        try:
            path = self._resolve_path(sftp, path)
            with sftp.open(path, "r") as f:
                return f.read().decode()
        finally:
            sftp.close()

    def write_remote(self, path: str, content: str) -> dict:
        """Write content to a remote file via SFTP."""
        sftp = self._sftp()
        try:
            path = self._resolve_path(sftp, path)
            with sftp.open(path, "w") as f:
                f.write(content)
            file_stat = sftp.stat(path)
            return {
                "path": path,
                "size": file_stat.st_size,
            }
        finally:
            sftp.close()

    def system_info(self) -> dict:
        """Get hostname, uptime, memory, and disk usage from the remote host."""
        result = self.execute(
            "echo HOSTNAME=$(hostname);"
            "echo UPTIME=$(uptime -p);"
            "echo KERNEL=$(uname -r);"
            "free -h | awk '/^Mem:/ {print \"MEM_TOTAL=\" $2 \" MEM_USED=\" $3 \" MEM_AVAILABLE=\" $7}';"
            "df -h / | awk 'NR==2 {print \"DISK_TOTAL=\" $2 \" DISK_USED=\" $3 \" DISK_AVAILABLE=\" $4 \" DISK_USE_PCT=\" $5}'"
        )
        if result["exit_code"] != 0:
            return result

        info = {}
        for line in result["stdout"].strip().split("\n"):
            for pair in line.split():
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    info[key.lower()] = value
        return info

    def disconnect(self):
        """Close the SSH connection."""
        if self._client:
            self._client.close()
            self._client = None
