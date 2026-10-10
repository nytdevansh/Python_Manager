from dataclasses import dataclass
from packaging.specifiers import SpecifierSet
from packaging.version import Version, InvalidVersion
from typing import Optional
from .pypi import query_package_info

@dataclass
class Resolution:
    compatible: bool
    recommended_python: Optional[str]
    reason: str

class VersionResolver:
    def __init__(self):
        # Stable patch releases for downloading and compiling from python.org
        self.known_pythons = [
            "3.15.0",
            "3.14.0",
            "3.13.2",
            "3.12.9",
            "3.11.9",
            "3.10.16",
            "3.9.21",
            "3.8.20",
        ]

    def _normalize_version(self, version: str) -> str:
        """Normalize version string to major.minor.micro format."""
        parts = version.split(".")
        if len(parts) == 2:
            return f"{version}.0"
        return version

    def resolve(self, package_name: str, current_python: str, package_version: Optional[str] = None) -> Resolution:
        """
        Determine if the package is compatible with current_python.
        If not, find the highest compatible Python version.
        """
        try:
            info = query_package_info(package_name, package_version)
        except Exception as e:
            return Resolution(False, None, f"Failed to query PyPI: {e}")

        requires_python = info.requires_python
        
        # If no python restriction, assume compatible
        if not requires_python:
            return Resolution(True, current_python, "No Requires-Python specifier found.")

        try:
            spec = SpecifierSet(requires_python)
        except Exception as e:
            return Resolution(True, current_python, f"Invalid specifier on PyPI: {e}")

        # Check if current is compatible (try both "3.14" and "3.14.0")
        normalized = self._normalize_version(current_python)
        if spec.contains(current_python) or spec.contains(normalized):
            return Resolution(True, current_python, "Compatible with current Python version.")

        # Find best alternative (highest compatible version)
        for pv in self.known_pythons:
            if spec.contains(pv):
                return Resolution(
                    False, pv,
                    f"Incompatible with Python {current_python}. "
                    f"Recommended: Python {pv} (based on requires_python: {requires_python})"
                )

        return Resolution(False, None, f"Could not find any compatible Python version for {requires_python}")
