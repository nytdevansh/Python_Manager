import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock
from pymanager.builder import PythonBuilder, PythonInstallation

@pytest.fixture
def builder(tmpdir):
    return PythonBuilder(str(tmpdir.mkdir("cache")))

@patch('urllib.request.urlretrieve')
@patch('tarfile.open')
def test_download_source(mock_tarfile, mock_urlretrieve, builder, tmpdir):
    mock_tar = MagicMock()
    mock_tarfile.return_value.__enter__.return_value = mock_tar
    
    target_dir = str(tmpdir.mkdir("target"))
    res = builder.download_source("3.10.0", target_dir)
    
    assert res == os.path.join(target_dir, "Python-3.10.0")
    mock_urlretrieve.assert_called_once()
    assert mock_urlretrieve.call_args[0][0] == "https://www.python.org/ftp/python/3.10.0/Python-3.10.0.tgz"
    mock_tar.extractall.assert_called_once_with(path=target_dir)

@patch('pymanager.builder.run_command')
@patch('platform.system')
def test_build_python_linux(mock_system, mock_run_cmd, builder, tmpdir):
    mock_system.return_value = "Linux"
    mock_run_cmd.return_value = MagicMock(returncode=0, stdout="")
    
    source_dir = str(tmpdir.mkdir("source"))
    install_dir = str(tmpdir.mkdir("install"))
    
    bin_path = builder.build_python(source_dir, install_dir)
    
    assert bin_path == os.path.join(install_dir, "bin", "python3")
    assert mock_run_cmd.call_count == 3
    # Configure
    assert mock_run_cmd.call_args_list[0][0][0][0] == "./configure"
    assert mock_run_cmd.call_args_list[0][0][0][1] == f"--prefix={install_dir}"
    # Make
    assert mock_run_cmd.call_args_list[1][0][0][0] == "make"
    # Make install
    assert mock_run_cmd.call_args_list[2][0][0] == ["make", "install"]

@patch('pymanager.builder.run_command')
def test_build_python_failure(mock_run_cmd, builder, tmpdir):
    mock_run_cmd.return_value = MagicMock(returncode=1)
    
    source_dir = str(tmpdir.mkdir("source"))
    install_dir = str(tmpdir.mkdir("install"))
    
    with pytest.raises(RuntimeError, match="Configure failed"):
        builder.build_python(source_dir, install_dir)

@patch('os.path.getctime')
@patch('os.path.exists')
@patch('os.path.isdir')
@patch('os.listdir')
def test_get_installed_pythons(mock_listdir, mock_isdir, mock_exists, mock_getctime, builder):
    mock_listdir.return_value = ["3.10.0", "not_a_python"]
    mock_isdir.side_effect = lambda p: True
    mock_exists.side_effect = lambda p: "not_a_python" not in p
    mock_getctime.return_value = 1600000000.0
    
    installs = builder.get_installed_pythons("/fake/dir")
    
    assert len(installs) == 1
    assert installs[0].version == "3.10.0"
    assert installs[0].path == "/fake/dir/3.10.0"

def test_get_installed_pythons_empty_dir(builder):
    installs = builder.get_installed_pythons("/nonexistent_fake_dir")
    assert len(installs) == 0
