import os
import pytest
from unittest.mock import patch, MagicMock
from pymanager.environment import EnvironmentManager, InstallResult
from pymanager.resolver import Resolution


@pytest.fixture
def env_mgr(tmpdir):
    return EnvironmentManager(str(tmpdir))


def test_init_environment_new(env_mgr):
    env_mgr.init_environment("3.10.0")
    assert os.path.exists(env_mgr.cache_dir)
    assert os.path.exists(env_mgr.pythons_dir)
    assert os.path.exists(env_mgr.envs_dir)
    assert os.path.exists(env_mgr.config_path)
    assert env_mgr.config.main_python == "3.10.0"


def test_init_environment_existing(env_mgr):
    env_mgr.init_environment("3.10.0")
    env_mgr.config.main_python = "3.11.0"
    env_mgr.config.save(env_mgr.config_path)

    # Should not overwrite existing config
    env_mgr.init_environment("3.9.0")
    # The config file already exists, so init_environment won't change it.
    # However, env_mgr.config was loaded in __init__, so reload to check file:
    from pymanager.config import EnvironmentConfig
    reloaded = EnvironmentConfig.load(env_mgr.config_path)
    assert reloaded.main_python == "3.11.0"


def test_ensure_python_version_existing(env_mgr):
    """If the python binary already exists, no build should happen."""
    version = "3.10.0"
    install_dir = os.path.join(env_mgr.pythons_dir, version)
    bin_dir = os.path.join(install_dir, "bin")
    os.makedirs(bin_dir)
    python_bin = os.path.join(bin_dir, "python3")
    with open(python_bin, 'w') as f:
        f.write("")

    res_bin = env_mgr._ensure_python_version(version)
    assert res_bin == python_bin


def test_ensure_python_version_build(env_mgr):
    """When no local binary exists, the builder should download and build."""
    mock_builder = MagicMock()
    mock_builder.download_source.return_value = "/tmp/source"
    # Replace the already-instantiated builder on the manager
    env_mgr.builder = mock_builder

    env_mgr._ensure_python_version("3.9.0")

    mock_builder.download_source.assert_called_once()
    mock_builder.build_python.assert_called_once()
    assert len(env_mgr.config.python_installations) == 1
    assert env_mgr.config.python_installations[0].version == "3.9.0"


@patch('pymanager.environment.run_command')
def test_create_sub_environment(mock_run, env_mgr):
    env_mgr._ensure_python_version = MagicMock(return_value="/mock/python")
    env_path = env_mgr.create_sub_environment("3.9.0", ["requests==2.31.0"])

    assert env_path == os.path.join(env_mgr.envs_dir, "env_3.9.0")
    assert mock_run.call_count == 2  # venv creation + pip install
    assert mock_run.call_args_list[0][0][0] == ["/mock/python", "-m", "venv", env_path]

    assert len(env_mgr.config.sub_environments) == 1
    assert env_mgr.config.sub_environments[0].python_version == "3.9.0"
    assert "requests==2.31.0" in env_mgr.config.sub_environments[0].packages


@patch('pymanager.environment.run_command')
def test_install_package_compatible(mock_run, env_mgr):
    env_mgr.init_environment("3.10.0")
    env_mgr.resolver.resolve = MagicMock(return_value=Resolution(True, "3.10.0", "OK"))

    res = env_mgr.install_package("requests", "2.31.0")

    assert res.success is True
    assert res.python_version == "3.10.0"
    assert res.sub_env_path is None
    assert mock_run.call_count == 1
    assert len(env_mgr.config.dependencies) == 1


def test_install_package_incompatible_no_fallback(env_mgr):
    env_mgr.init_environment("3.10.0")
    env_mgr.resolver.resolve = MagicMock(return_value=Resolution(False, None, "Fail"))

    res = env_mgr.install_package("requests", "2.31.0")

    assert res.success is False
    assert res.message == "Fail"


@patch('pymanager.environment.run_command')
def test_install_package_incompatible_with_fallback(mock_run, env_mgr):
    env_mgr.init_environment("3.10.0")
    env_mgr.resolver.resolve = MagicMock(return_value=Resolution(False, "3.9.0", "Fallback"))
    env_mgr.create_sub_environment = MagicMock(return_value="/mock/env_3.9.0")

    res = env_mgr.install_package("requests", "2.31.0")

    assert res.success is True
    assert res.python_version == "3.9.0"
    assert res.sub_env_path == "/mock/env_3.9.0"
    env_mgr.create_sub_environment.assert_called_once_with("3.9.0", ["requests==2.31.0"])
    assert len(env_mgr.config.dependencies) == 1
    assert env_mgr.config.dependencies[0].python_version == "3.9.0"
