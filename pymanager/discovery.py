"""
Dynamic Python Version Discovery and Resolver.

Discovers available Python versions dynamically from official feeds (without hardcoding)
and resolves the optimal Python version for any library's requirements.
"""

import json
import platform
import urllib.request
from typing import List, Optional, Dict
from packaging.specifiers import SpecifierSet
from packaging.version import Version, InvalidVersion
from .utils import logger
from .pypi import query_package_info, PackageInfo

# Cache discovered versions in-memory
_DISCOVERED_VERSIONS_CACHE: Optional[List[str]] = None
_STANDALONE_ASSETS_CACHE: Optional[Dict[str, str]] = None


def get_current_platform_key() -> str:
    """Return the platform architecture string for standalone Python binaries."""
    machine = platform.machine().lower()
    system = platform.system().lower()

    if system == "darwin":
        arch = "aarch64" if machine in ("arm64", "aarch64") else "x86_64"
        return f"{arch}-apple-darwin"
    elif system == "linux":
        arch = "aarch64" if machine in ("arm64", "aarch64") else "x86_64"
        return f"{arch}-unknown-linux-gnu"
    elif system == "windows":
        arch = "x86_64" if machine in ("amd64", "x86_64") else "i686"
        return f"{arch}-pc-windows-msvc"
    return f"{machine}-{system}"


def discover_available_python_versions() -> Dict[str, str]:
    """
    Dynamically discover all available Python versions and their download URLs
    from the python-build-standalone release index without hardcoding.
    Returns: Dict mapping version string (e.g. '3.11.17') to download URL.
    """
    global _STANDALONE_ASSETS_CACHE
    if _STANDALONE_ASSETS_CACHE is not None:
        return _STANDALONE_ASSETS_CACHE

    plat_key = get_current_platform_key()
    url = "https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest"
    req = urllib.request.Request(url, headers={"User-Agent": "python-auto-env"})

    version_url_map = {}
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for asset in data.get("assets", []):
                name = asset.get("name", "")
                download_url = asset.get("browser_download_url", "")
                # We want standard install_only archives for our platform
                if (
                    plat_key in name
                    and "install_only" in name
                    and "stripped" not in name
                    and name.startswith("cpython-")
                ):
                    # Format: cpython-3.11.17+20261009-aarch64-apple-darwin-install_only.tar.gz
                    raw_ver = name.split("+")[0].replace("cpython-", "")
                    version_url_map[raw_ver] = download_url
    except Exception as e:
        logger.warning(f"Could not query standalone releases API: {e}. Trying fallback...")

    # If the API was rate-limited or unavailable, fall back to querying python.org
    if not version_url_map:
        version_url_map = _fallback_python_org_versions()

    _STANDALONE_ASSETS_CACHE = version_url_map
    return version_url_map


def _fallback_python_org_versions() -> Dict[str, str]:
    """Fallback: query python.org official release list dynamically."""
    url = "https://www.python.org/api/v2/downloads/release/?format=json"
    req = urllib.request.Request(url, headers={"User-Agent": "python-auto-env"})
    versions = {}
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for item in data:
                name = item.get("name", "")
                if name.startswith("Python 3."):
                    ver = name.replace("Python ", "").strip()
                    # Only stable releases
                    if "a" not in ver and "b" not in ver and "rc" not in ver:
                        versions[ver] = f"https://www.python.org/ftp/python/{ver}/Python-{ver}.tgz"
    except Exception as e:
        logger.error(f"Fallback python.org query failed: {e}")
    return versions


class AutoVersionResolver:
    """
    Dynamically resolves the best Python version for an incompatible package
    without any hardcoded version tables.
    """

    def resolve(
        self, package_name: str, current_python: str, package_version: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Determine if the package is compatible with current_python.
        If not, automatically finds the highest compatible Python version dynamically.
        """
        info = query_package_info(package_name, package_version)
        requires_python = info.requires_python

        if not requires_python:
            return {
                "compatible": True,
                "target_version": current_python,
                "download_url": None,
                "reason": "Package specifies no Python version constraint.",
            }

        try:
            spec = SpecifierSet(requires_python)
        except Exception as e:
            return {
                "compatible": True,
                "target_version": current_python,
                "download_url": None,
                "reason": f"Invalid specifier on PyPI: {e}",
            }

        # Check if current Python satisfies the requirement
        if spec.contains(current_python):
            return {
                "compatible": True,
                "target_version": current_python,
                "download_url": None,
                "reason": f"Compatible with current Python {current_python}",
            }

        # Package is incompatible with current Python!
        # Dynamically discover all available Python versions:
        available_versions = discover_available_python_versions()

        # Sort available versions in descending order to pick the highest compatible version
        valid_candidates = []
        for ver_str, download_url in available_versions.items():
            try:
                v = Version(ver_str)
                if spec.contains(ver_str):
                    valid_candidates.append((v, ver_str, download_url))
            except InvalidVersion:
                continue

        valid_candidates.sort(key=lambda item: item[0], reverse=True)

        if valid_candidates:
            best_version, ver_str, download_url = valid_candidates[0]
            return {
                "compatible": False,
                "target_version": ver_str,
                "download_url": download_url,
                "reason": (
                    f"Package {package_name} requires {requires_python}, "
                    f"incompatible with {current_python}. "
                    f"Auto-selected highest compatible Python {ver_str}."
                ),
            }

        return {
            "compatible": False,
            "target_version": None,
            "download_url": None,
            "reason": f"No available Python version satisfies {requires_python}",
        }
