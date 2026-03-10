"""DNSCrypt-Sorter — measure and rank DNS resolvers by latency."""

__version__ = "0.5.0"

from .cli import main

__all__ = ["__version__", "main"]
