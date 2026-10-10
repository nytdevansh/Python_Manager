import os
import tarfile
import urllib.request
import platform
import shutil
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from .utils import run_command, logger

@dataclass
class PythonInstallation:
    version: str
    path: str
    created_at: str

class PythonBuilder:
    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def download_source(self, version: str, target_dir: str) -> str:
        """Download Python source tarball from python.org."""
        tarball_name = f"Python-{version}.tgz"
        url = f"https://www.python.org/ftp/python/{version}/{tarball_name}"
        tarball_path = os.path.join(self.cache_dir, tarball_name)
        
        if not os.path.exists(tarball_path):
            logger.info(f"Downloading Python {version} from {url}...")
            urllib.request.urlretrieve(url, tarball_path)
            
        logger.info(f"Extracting {tarball_path} to {target_dir}...")
        with tarfile.open(tarball_path, "r:gz") as tar:
            tar.extractall(path=target_dir)
            
        return os.path.join(target_dir, f"Python-{version}")

    def build_python(self, source_dir: str, install_dir: str) -> str:
        """Configure, make, and make install Python from source."""
        logger.info(f"Building Python at {source_dir}, installing to {install_dir}...")
        os.makedirs(install_dir, exist_ok=True)
        
        configure_cmd = ["./configure", f"--prefix={install_dir}"]
        
        # macOS specific: use Homebrew openssl if available
        if platform.system() == "Darwin":
            brew_prefix = run_command(["brew", "--prefix"]).stdout.strip()
            if brew_prefix:
                openssl_dir = os.path.join(brew_prefix, "opt", "openssl@3")
                if not os.path.exists(openssl_dir):
                    openssl_dir = os.path.join(brew_prefix, "opt", "openssl@1.1")
                if os.path.exists(openssl_dir):
                    configure_cmd.append(f"--with-openssl={openssl_dir}")
                    
        logger.info("Running configure...")
        res = run_command(configure_cmd, cwd=source_dir, capture_output=False)
        if res.returncode != 0:
            raise RuntimeError("Configure failed")
            
        nproc = os.cpu_count() or 4
        logger.info(f"Running make -j{nproc}...")
        res = run_command(["make", f"-j{nproc}"], cwd=source_dir, capture_output=False)
        if res.returncode != 0:
            raise RuntimeError("Make failed")
            
        logger.info("Running make install...")
        res = run_command(["make", "install"], cwd=source_dir, capture_output=False)
        if res.returncode != 0:
            raise RuntimeError("Make install failed")
            
        return os.path.join(install_dir, "bin", "python3")

    def get_installed_pythons(self, base_dir: str) -> List[PythonInstallation]:
        """List locally built Pythons."""
        installs = []
        if not os.path.exists(base_dir):
            return installs
            
        for d in os.listdir(base_dir):
            path = os.path.join(base_dir, d)
            bin_path = os.path.join(path, "bin", "python3")
            if os.path.isdir(path) and os.path.exists(bin_path):
                ctime = os.path.getctime(path)
                created_at = datetime.fromtimestamp(ctime).isoformat()
                installs.append(PythonInstallation(version=d, path=path, created_at=created_at))
                
        return installs
