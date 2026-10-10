import os
import sys
from unittest.mock import patch, MagicMock
from pymanager.utils import get_current_python_version, run_command, find_system_python, print_color, Colors

def test_get_current_python_version():
    version = get_current_python_version()
    assert isinstance(version, str)
    assert len(version.split('.')) == 3

@patch('subprocess.run')
def test_run_command_success(mock_run):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "output"
    mock_result.stderr = ""
    mock_run.return_value = mock_result
    
    res = run_command(["echo", "hello"])
    assert res.returncode == 0
    assert res.stdout == "output"
    assert res.stderr == ""
    mock_run.assert_called_once()

@patch('subprocess.run')
def test_run_command_failure(mock_run):
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "error"
    mock_run.return_value = mock_result
    
    res = run_command(["false"])
    assert res.returncode == 1
    assert res.stdout == ""
    assert res.stderr == "error"

@patch('subprocess.run')
def test_run_command_file_not_found(mock_run):
    mock_run.side_effect = FileNotFoundError("No such file")
    res = run_command(["nonexistent_command"])
    assert res.returncode == 127
    assert "No such file" in res.stderr

@patch('pymanager.utils.run_command')
def test_find_system_python_found(mock_run_cmd):
    mock_run_cmd.return_value = MagicMock(returncode=0, stdout="/usr/bin/python3.10\n", stderr="")
    path = find_system_python("3.10")
    assert path == "/usr/bin/python3.10"
    mock_run_cmd.assert_called_once_with(["which", "python3.10"])

@patch('pymanager.utils.run_command')
def test_find_system_python_not_found(mock_run_cmd):
    mock_run_cmd.return_value = MagicMock(returncode=1, stdout="", stderr="")
    path = find_system_python("3.9")
    assert path is None

def test_print_color(capsys):
    print_color("hello", Colors.OKGREEN)
    captured = capsys.readouterr()
    assert Colors.OKGREEN in captured.out
    assert "hello" in captured.out
    assert Colors.ENDC in captured.out
