from importlib.metadata import version, PackageNotFoundError

"""Omen strategic reasoning engine package."""

__all__ = ["__version__"]

try:
  __version__ = version("omenai")
except (ImportError, PackageNotFoundError):
  __version__ = "dev"
