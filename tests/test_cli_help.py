import subprocess
import sys
from pathlib import Path


def test_cli_help_runs() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "pianoplayer.cli", "-h"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "usage:" in result.stdout
