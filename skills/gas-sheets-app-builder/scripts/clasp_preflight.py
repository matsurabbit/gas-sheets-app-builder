#!/usr/bin/env python3
"""Inspect a clasp runner and print a sanitized, version-aware command map."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def run(runner: list[str], args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        runner + args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def command_map(is_v3: bool) -> dict[str, list[str]]:
    if is_v3:
        return {
            "auth": ["show-authorized-user"],
            "create": ["create-script"],
            "status": ["show-file-status"],
            "openScript": ["open-script"],
            "openContainer": ["open-container"],
            "list": ["list-scripts"],
            "push": ["push"],
        }
    return {
        "auth": ["login", "--status"],
        "create": ["create"],
        "status": ["status"],
        "openScript": ["open"],
        "openContainer": ["open", "--addon"],
        "list": ["list"],
        "push": ["push"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-auth", action="store_true", help="Do not run the auth status command")
    parser.add_argument("runner", nargs=argparse.REMAINDER, help="Runner after --, e.g. node_modules/.bin/clasp")
    args = parser.parse_args()

    runner = args.runner
    if runner and runner[0] == "--":
        runner = runner[1:]
    if not runner:
        parser.error("clasp runner is required after --")

    executable = Path(runner[0])
    if ("/" in runner[0] or "\\" in runner[0]) and not executable.exists():
        parser.error(f"runner not found: {runner[0]}")

    try:
        version_result = run(runner, ["--version"])
        help_result = run(runner, ["--help"])
    except OSError as exc:
        parser.error(f"runner could not be executed: {exc}")

    if version_result.returncode != 0 or help_result.returncode != 0:
        message = (version_result.stderr or help_result.stderr or "clasp inspection failed").strip().splitlines()[0]
        parser.error(message)

    version_text = version_result.stdout.strip().splitlines()[0]
    match = re.search(r"(?:^|\D)(\d+)\.(\d+)(?:\.\d+)?", version_text)
    help_text = help_result.stdout + help_result.stderr
    is_v3 = "open-script" in help_text or (match is not None and int(match.group(1)) >= 3)
    commands = command_map(is_v3)

    authenticated: bool | None = None
    auth_message = "skipped"
    if not args.skip_auth:
        auth_result = run(runner, commands["auth"])
        authenticated = auth_result.returncode == 0
        auth_message = "authenticated" if authenticated else "authentication required"

    output = {
        "runner": runner,
        "version": version_text,
        "family": "v3" if is_v3 else "v2",
        "authenticated": authenticated,
        "authMessage": auth_message,
        "commands": commands,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if authenticated is not False else 2


if __name__ == "__main__":
    raise SystemExit(main())
