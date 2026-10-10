import pytest
from unittest.mock import patch, MagicMock
from pymanager.pypi import query_package_info, get_supported_python_versions, PackageInfo
import requests

@patch('requests.get')
def test_query_package_info_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "info": {
            "name": "requests",
            "version": "2.31.0",
            "requires_python": ">=3.7",
            "classifiers": ["Programming Language :: Python :: 3.8"]
        }
    }
    mock_get.return_value = mock_resp
    
    info = query_package_info("requests")
    assert info.name == "requests"
    assert info.version == "2.31.0"
    assert info.requires_python == ">=3.7"
    assert "Programming Language :: Python :: 3.8" in info.classifiers
    mock_get.assert_called_with("https://pypi.org/pypi/requests/json")

@patch('requests.get')
def test_query_package_info_with_version(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "info": {
            "name": "requests",
            "version": "2.20.0",
        }
    }
    mock_get.return_value = mock_resp
    
    info = query_package_info("requests", "2.20.0")
    assert info.name == "requests"
    assert info.version == "2.20.0"
    assert info.requires_python is None
    mock_get.assert_called_with("https://pypi.org/pypi/requests/2.20.0/json")

@patch('requests.get')
def test_query_package_info_network_error(mock_get):
    mock_get.side_effect = requests.RequestException("Network failure")
    with pytest.raises(requests.RequestException):
        query_package_info("requests")

@patch('pymanager.pypi.query_package_info')
def test_get_supported_python_versions_from_classifiers(mock_query):
    mock_query.return_value = PackageInfo(
        name="testpkg",
        version="1.0",
        requires_python=None,
        classifiers=[
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3"
        ]
    )
    versions = get_supported_python_versions("testpkg")
    assert "3.7" in versions
    assert "3.8" in versions
    assert "3" not in versions # should ignore generic "3"

@patch('pymanager.pypi.query_package_info')
def test_get_supported_python_versions_from_requires_python(mock_query):
    mock_query.return_value = PackageInfo(
        name="testpkg",
        version="1.0",
        requires_python=">=3.9,<3.12",
        classifiers=[]
    )
    versions = get_supported_python_versions("testpkg")
    assert "3.9" in versions
    assert "3.10" in versions
    assert "3.11" in versions
    assert "3.8" not in versions
    assert "3.12" not in versions

@patch('pymanager.pypi.query_package_info')
def test_get_supported_python_versions_malformed_requires(mock_query):
    mock_query.return_value = PackageInfo(
        name="testpkg",
        version="1.0",
        requires_python="invalid-specifier",
        classifiers=[]
    )
    from packaging.specifiers import InvalidSpecifier
    with pytest.raises(InvalidSpecifier):
        get_supported_python_versions("testpkg")
