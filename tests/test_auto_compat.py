import os
import pytest
from unittest.mock import patch, MagicMock
from pymanager.discovery import AutoVersionResolver, discover_available_python_versions
from pymanager.provisioner import EnvironmentProvisioner
from pymanager.importhook import CompatMetaPathFinder, install_hook


def test_auto_version_resolver_compatible():
    resolver = AutoVersionResolver()
    with patch('pymanager.discovery.query_package_info') as mock_info:
        mock_info.return_value = MagicMock(requires_python=">=3.8")
        res = resolver.resolve("requests", "3.12.0")
        assert res["compatible"] is True
        assert res["target_version"] == "3.12.0"
        assert res["download_url"] is None


def test_auto_version_resolver_incompatible_selects_highest():
    resolver = AutoVersionResolver()
    with patch('pymanager.discovery.query_package_info') as mock_info, \
         patch('pymanager.discovery.discover_available_python_versions') as mock_discover:
        mock_info.return_value = MagicMock(requires_python="<3.12,>=3.8")
        mock_discover.return_value = {
            "3.10.12": "https://example.com/py310.tar.gz",
            "3.11.17": "https://example.com/py311.tar.gz",
            "3.12.1": "https://example.com/py312.tar.gz",
        }
        res = resolver.resolve("scipy", "3.12.0")
        assert res["compatible"] is False
        assert res["target_version"] == "3.11.17"
        assert res["download_url"] == "https://example.com/py311.tar.gz"


def test_provisioner_directory_structure(tmp_path):
    prov = EnvironmentProvisioner(str(tmp_path))
    assert os.path.exists(prov.compat_dir)
    assert os.path.exists(prov.pythons_dir)
    assert os.path.exists(prov.envs_dir)
    assert os.path.exists(prov.cache_dir)


@patch('pymanager.provisioner.run_command')
def test_provisioner_ensure_sub_env(mock_run, tmp_path):
    prov = EnvironmentProvisioner(str(tmp_path))
    prov.ensure_python = MagicMock(return_value="/mock/python3")
    mock_run.return_value = MagicMock(returncode=0)

    env_dir = prov.ensure_sub_env("3.11.0", "http://example.com", "scipy==1.10.1")
    assert env_dir == os.path.join(prov.envs_dir, "env_3.11.0")


def test_importhook_installation():
    import sys
    initial_finders = list(sys.meta_path)
    install_hook()
    assert any(isinstance(f, CompatMetaPathFinder) for f in sys.meta_path)
