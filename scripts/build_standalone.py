#!/usr/bin/env python3
"""Build a standalone PianoPlayer executable with PyInstaller."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    dist_dir = root / "dist"
    build_dir = root / "build"

    # Build from a clean state to avoid stale frozen artifacts.
    shutil.rmtree(dist_dir, ignore_errors=True)
    shutil.rmtree(build_dir, ignore_errors=True)

    data_sep = ";" if platform.system() == "Windows" else ":"
    scores_src = root / "scores"
    add_data = f"{scores_src}{data_sep}scores"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name",
        "pianoplayer",
        "--onefile",
        "--exclude-module",
        "vedo",
        "--exclude-module",
        "vtk",
        "--exclude-module",
        "PyQt5",
        "--exclude-module",
        "PyQt6",
        "--exclude-module",
        "PySide2",
        "--exclude-module",
        "PySide6",
        "--exclude-module",
        "pygame",
        "--exclude-module",
        "matplotlib",
        "--exclude-module",
        "mpl_toolkits",
        "--collect-submodules",
        "pianoplayer",
        "--add-data",
        add_data,
        str(root / "pianoplayer" / "cli.py"),
    ]

    env = os.environ.copy()
    env["PYTHONPATH"] = str(root)

    subprocess.run(cmd, check=True, cwd=root, env=env)

    executable_name = "pianoplayer.exe" if platform.system() == "Windows" else "pianoplayer"
    exe_path = dist_dir / executable_name
    print(f"Built executable: {exe_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
