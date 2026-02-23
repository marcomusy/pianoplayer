import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pianoplayer import __version__


def test_version_present() -> None:
    assert isinstance(__version__, str)
    assert __version__
