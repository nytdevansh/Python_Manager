import pytest
from unittest.mock import patch, MagicMock
from pymanager.resolver import VersionResolver, Resolution
from pymanager.pypi import PackageInfo

@pytest.fixture
def resolver():
    return VersionResolver()

@patch('pymanager.resolver.query_package_info')
def test_resolve_compatible(mock_query, resolver):
    mock_query.return_value = PackageInfo(
        name="testpkg",
        version="1.0",
        requires_python=">=3.8",
        classifiers=[]
    )
    res = resolver.resolve("testpkg", "3.10")
    assert res.compatible is True
    assert res.recommended_python == "3.10"
    assert "Compatible" in res.reason

@patch('pymanager.resolver.query_package_info')
def test_resolve_no_requires_python(mock_query, resolver):
    mock_query.return_value = PackageInfo(
        name="testpkg",
        version="1.0",
        requires_python=None,
        classifiers=[]
    )
    res = resolver.resolve("testpkg", "3.10")
    assert res.compatible is True
    assert res.recommended_python == "3.10"
    assert "No Requires-Python" in res.reason

@patch('pymanager.resolver.query_package_info')
def test_resolve_incompatible_finds_alternative(mock_query, resolver):
    mock_query.return_value = PackageInfo(
        name="testpkg",
        version="1.0",
        requires_python="<3.10,>=3.7",
        classifiers=[]
    )
    # current is 3.11, should find highest <3.10 (so 3.9.0)
    res = resolver.resolve("testpkg", "3.11")
    assert res.compatible is False
    assert res.recommended_python.startswith("3.9")
    assert "Incompatible" in res.reason

@patch('pymanager.resolver.query_package_info')
def test_resolve_incompatible_no_alternative(mock_query, resolver):
    mock_query.return_value = PackageInfo(
        name="testpkg",
        version="1.0",
        requires_python="<3.0", # Impossible given known pythons 3.7+
        classifiers=[]
    )
    res = resolver.resolve("testpkg", "3.10")
    assert res.compatible is False
    assert res.recommended_python is None
    assert "Could not find any compatible Python" in res.reason

@patch('pymanager.resolver.query_package_info')
def test_resolve_invalid_package(mock_query, resolver):
    mock_query.side_effect = Exception("Not found")
    res = resolver.resolve("nonexistent_pkg", "3.10")
    assert res.compatible is False
    assert res.recommended_python is None
    assert "Failed to query PyPI" in res.reason

@patch('pymanager.resolver.query_package_info')
def test_resolve_invalid_specifier(mock_query, resolver):
    mock_query.return_value = PackageInfo(
        name="testpkg",
        version="1.0",
        requires_python="invalid-spec",
        classifiers=[]
    )
    res = resolver.resolve("testpkg", "3.10")
    assert res.compatible is True
    assert res.recommended_python == "3.10"
    assert "Invalid specifier" in res.reason
