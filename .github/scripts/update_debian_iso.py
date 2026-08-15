#!/usr/bin/env python3
"""Bump the pinned Debian netinst ISO fallback to the current point release.

The VM managers resolve the ISO filename from the mirror at download time, so
this only refreshes the offline fallback and the illustrative values in the
`.env.example` files. Nothing here touches test fixtures — several tests pin
specific versions on purpose to exercise version comparison.
"""

import os
import pathlib
import re
import sys
import urllib.request


ISO_DIR_URL = "https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/"
ISO_NAME_RE = re.compile(r"debian-(\d+\.\d+\.\d+)-amd64-netinst\.iso")
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

# (path, regex) pairs. Each regex must capture the version in group 1 so the
# match can be rewritten in place without disturbing the rest of the line.
TARGETS = [
    (
        "shell_mcp/shell_client/vm_manager.py",
        re.compile(r'^(ISO_FALLBACK_NAME = "debian-)(\d+\.\d+\.\d+)(-amd64-netinst\.iso")$', re.M),
    ),
    (
        "webshell_mcp/webshell_client/vm_manager.py",
        re.compile(r'^(ISO_FALLBACK_NAME = "debian-)(\d+\.\d+\.\d+)(-amd64-netinst\.iso")$', re.M),
    ),
    (
        "shell_mcp/.env.example",
        re.compile(r'^(# ISO_(?:PATH|URL)=\S*debian-)(\d+\.\d+\.\d+)(-amd64-netinst\.iso)', re.M),
    ),
    (
        "webshell_mcp/.env.example",
        re.compile(r'^(# ISO_(?:PATH|URL)=\S*debian-)(\d+\.\d+\.\d+)(-amd64-netinst\.iso)', re.M),
    ),
]


def latest_version() -> str:
    """Highest netinst version listed in the mirror's `current` directory."""
    with urllib.request.urlopen(ISO_DIR_URL + "SHA256SUMS", timeout=60) as resp:
        body = resp.read().decode("utf-8", "replace")
    versions = set(ISO_NAME_RE.findall(body))
    if not versions:
        sys.exit(f"No netinst ISO listed at {ISO_DIR_URL}SHA256SUMS")
    return max(versions, key=lambda v: tuple(int(p) for p in v.split(".")))


def verify_downloadable(version: str) -> None:
    """Confirm the mirror really serves the ISO before proposing a bump."""
    url = f"{ISO_DIR_URL}debian-{version}-amd64-netinst.iso"
    request = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(request, timeout=60) as resp:
        if resp.status != 200:
            sys.exit(f"{url} returned HTTP {resp.status}")


def apply(version: str) -> tuple[list[str], str | None]:
    """Rewrite every target to `version`. Returns (changed files, old version)."""
    changed = []
    previous = None
    for relative_path, pattern in TARGETS:
        path = REPO_ROOT / relative_path
        text = path.read_text()
        matches = pattern.findall(text)
        if not matches:
            sys.exit(f"Pattern for {relative_path} matched nothing — update this script")
        previous = previous or matches[0][1]
        updated = pattern.sub(rf"\g<1>{version}\g<3>", text)
        if updated != text:
            path.write_text(updated)
            changed.append(relative_path)
    return changed, previous


def main() -> None:
    version = latest_version()
    verify_downloadable(version)
    changed, previous = apply(version)

    for line in (
        f"version={version}",
        f"previous={previous}",
        f"changed={'true' if changed else 'false'}",
    ):
        print(line)
        if output := os.getenv("GITHUB_OUTPUT"):
            with open(output, "a") as handle:
                handle.write(line + "\n")

    if changed:
        print(f"Updated {len(changed)} file(s): {', '.join(changed)}", file=sys.stderr)
    else:
        print(f"Already pinned to {version}", file=sys.stderr)


if __name__ == "__main__":
    main()
