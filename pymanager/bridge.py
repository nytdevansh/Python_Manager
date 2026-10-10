import json
import os
import tempfile
import subprocess
from typing import Any

class ModuleProxy:
    def __init__(self, bridge: 'SubprocessBridge', module: str):
        self._bridge = bridge
        self._module = module

    def __getattr__(self, name: str):
        def wrapper(*args, **kwargs):
            return self._bridge.call_function(self._module, name, *args, **kwargs)
        return wrapper

class SubprocessBridge:
    def __init__(self, sub_env_path: str):
        self.sub_env_path = sub_env_path
        python_candidate = os.path.join(self.sub_env_path, "bin", "python")
        if not os.path.exists(python_candidate):
            python_candidate = os.path.join(self.sub_env_path, "bin", "python3")
        if not os.path.exists(python_candidate):
            raise FileNotFoundError(f"Python executable not found in sub-environment: {self.sub_env_path}")
        self.python_bin = python_candidate

    def call_function(self, module: str, function: str, *args, **kwargs) -> Any:
        """Execute a function in a sub-environment's Python and return the result."""
        payload = {
            "module": module,
            "function": function,
            "args": args,
            "kwargs": kwargs
        }
        
        script_content = f"""
import sys
import json
import importlib

def main():
    try:
        input_data = sys.stdin.read()
        request = json.loads(input_data)
        
        mod = importlib.import_module(request['module'])
        attr = getattr(mod, request['function'])
        if callable(attr):
            result = attr(*request['args'], **request['kwargs'])
        else:
            result = attr
        
        print(json.dumps({{"status": "success", "result": result}}))
    except Exception as e:
        print(json.dumps({{"status": "error", "message": str(e)}}))

if __name__ == '__main__':
    main()
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script_content)
            script_path = f.name
            
        try:
            process = subprocess.Popen(
                [self.python_bin, script_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(input=json.dumps(payload))
            
            if process.returncode != 0:
                raise RuntimeError(f"Subprocess failed: {stderr}")
                
            try:
                response = json.loads(stdout)
            except json.JSONDecodeError:
                raise RuntimeError(f"Failed to decode JSON from subprocess. Output: {stdout}")
                
            if response.get("status") == "error":
                raise RuntimeError(f"Error in remote execution: {response.get('message')}")
                
            return response.get("result")
        finally:
            if os.path.exists(script_path):
                os.remove(script_path)

    def create_proxy(self, module: str) -> ModuleProxy:
        """Create a proxy object that forwards attribute access to the sub-environment."""
        return ModuleProxy(self, module)
