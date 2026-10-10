import os
import json
import pytest
import tempfile
from unittest.mock import patch, MagicMock
from pymanager.bridge import SubprocessBridge, ModuleProxy

@pytest.fixture
def bridge(tmpdir):
    env_dir = tmpdir.mkdir("env")
    bin_dir = env_dir.mkdir("bin")
    python_bin = bin_dir.join("python")
    python_bin.write("") # touch the file
    return SubprocessBridge(str(env_dir))

def test_bridge_init_missing_python(tmpdir):
    with pytest.raises(FileNotFoundError):
        SubprocessBridge(str(tmpdir))

@patch('subprocess.Popen')
def test_bridge_call_function_success(mock_popen, bridge):
    mock_process = MagicMock()
    mock_process.communicate.return_value = (json.dumps({"status": "success", "result": "hello"}), "")
    mock_process.returncode = 0
    mock_popen.return_value = mock_process
    
    res = bridge.call_function("math", "sqrt", 16)
    
    assert res == "hello"
    mock_popen.assert_called_once()

@patch('subprocess.Popen')
def test_bridge_call_function_error_response(mock_popen, bridge):
    mock_process = MagicMock()
    mock_process.communicate.return_value = (json.dumps({"status": "error", "message": "ModuleNotFoundError"}), "")
    mock_process.returncode = 0
    mock_popen.return_value = mock_process
    
    with pytest.raises(RuntimeError, match="Error in remote execution: ModuleNotFoundError"):
        bridge.call_function("missing_module", "func")

@patch('subprocess.Popen')
def test_bridge_call_function_process_failure(mock_popen, bridge):
    mock_process = MagicMock()
    mock_process.communicate.return_value = ("", "Segmentation fault")
    mock_process.returncode = 139
    mock_popen.return_value = mock_process
    
    with pytest.raises(RuntimeError, match="Subprocess failed: Segmentation fault"):
        bridge.call_function("math", "sqrt", -1)

@patch('subprocess.Popen')
def test_bridge_call_function_invalid_json(mock_popen, bridge):
    mock_process = MagicMock()
    mock_process.communicate.return_value = ("Not a JSON", "")
    mock_process.returncode = 0
    mock_popen.return_value = mock_process
    
    with pytest.raises(RuntimeError, match="Failed to decode JSON"):
        bridge.call_function("math", "sqrt", 16)

def test_module_proxy():
    mock_bridge = MagicMock()
    mock_bridge.call_function.return_value = 4.0
    
    proxy = ModuleProxy(mock_bridge, "math")
    res = proxy.sqrt(16)
    
    assert res == 4.0
    mock_bridge.call_function.assert_called_once_with("math", "sqrt", 16)

@patch('subprocess.Popen')
def test_bridge_serialization_edge_case(mock_popen, bridge):
    # Non-json-serializable types should ideally fail or be handled
    # But since we're directly calling call_function with inputs, we just check how it passes
    
    # We want to simulate what happens if we pass something that json.dumps inside call_function fails on
    # However, json.dumps is not explicitly called with a try/except in call_function for the input payload
    # It will just raise TypeError.
    with pytest.raises(TypeError):
        bridge.call_function("module", "func", set([1, 2, 3]))
