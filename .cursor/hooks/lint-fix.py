"""Cursor afterFileEdit hook: auto-fix lint issues on saved Python files."""

import json
import subprocess
import sys


def main() -> None:
    payload = json.load(sys.stdin)
    file_path = payload.get("path", "")

    if not file_path.endswith(".py"):
        print(json.dumps({}))
        return

    subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--fix", "--quiet", file_path],
        capture_output=True,
        timeout=10,
    )
    subprocess.run(
        [sys.executable, "-m", "ruff", "format", "--quiet", file_path],
        capture_output=True,
        timeout=10,
    )

    print(json.dumps({"additional_context": f"Auto-formatted {file_path} with ruff."}))


if __name__ == "__main__":
    main()
