"""Local photo-to-component schematic workbench."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("pv-structure-workbench")
except PackageNotFoundError:  # Running from a source checkout without installation.
    __version__ = "3.0.0"

__all__ = ["__version__"]
