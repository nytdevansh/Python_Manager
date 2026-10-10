import sys
import subprocess
import platform
import logging
from dataclasses import dataclass
from typing import Optional, List

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("pymanager")

@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_color(message: str, color: str):
    """Print a message with the specified color."""
    print(f"{color}{message}{Colors.ENDC}")

def get_current_python_version() -> str:
    """Get the current Python version as a string (e.g., '3.10.12')."""
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

def run_command(cmd: List[str], cwd: Optional[str] = None, capture_output: bool = True) -> CommandResult:
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            text=True,
            capture_output=capture_output,
            check=False
        )
        return CommandResult(
            returncode=result.returncode,
            stdout=result.stdout if capture_output else "",
            stderr=result.stderr if capture_output else ""
        )
    except FileNotFoundError as e:
        return CommandResult(returncode=127, stdout="", stderr=str(e))

def find_system_python(version: str) -> Optional[str]:
    """Find a system Python executable by version string."""
    res = run_command(["which", f"python{version}"])
    if res.returncode == 0 and res.stdout.strip():
        return res.stdout.strip()
    return None
