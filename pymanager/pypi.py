import requests
from dataclasses import dataclass
from typing import List, Optional
from packaging.specifiers import SpecifierSet
from packaging.version import Version

@dataclass
class PackageInfo:
    name: str
    version: str
    requires_python: Optional[str]
    classifiers: List[str]

def query_package_info(package_name: str, package_version: Optional[str] = None) -> PackageInfo:
    """Query PyPI JSON API for package information."""
    url = f"https://pypi.org/pypi/{package_name}/json"
    if package_version:
        url = f"https://pypi.org/pypi/{package_name}/{package_version}/json"
        
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    
    info = data["info"]
    return PackageInfo(
        name=info["name"],
        version=info["version"],
        requires_python=info.get("requires_python"),
        classifiers=info.get("classifiers", [])
    )

def get_supported_python_versions(package_name: str, package_version: Optional[str] = None) -> List[str]:
    """Parse Requires-Python and classifiers to determine supported versions."""
    info = query_package_info(package_name, package_version)
    supported_versions = set()
    
    # Check classifiers first
    for classifier in info.classifiers:
        if classifier.startswith("Programming Language :: Python :: "):
            parts = classifier.split("::")
            version_str = parts[-1].strip()
            # Ignore generic "3" or "2"
            if len(version_str.split('.')) > 1:
                supported_versions.add(version_str)
                
    # If requires_python is present, validate or generate range
    if info.requires_python:
        spec = SpecifierSet(info.requires_python)
        # Standard versions to check against (3.7 through 3.17)
        test_versions = [f"3.{x}" for x in range(7, 18)]
        for tv in test_versions:
            if spec.contains(tv):
                supported_versions.add(tv)
                
    return sorted(list(supported_versions))
