"""Package metadata for pianoplayer."""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

__author__ = "Marco Musy"
__email__ = "marco.musy@gmail.com"
__status__ = "dev"
__website__ = "https://github.com/marcomusy/pianoplayer"
__license__ = "MIT"

try:
    __version__ = version("pianoplayer")
except PackageNotFoundError:
    __version__ = "0+unknown"
