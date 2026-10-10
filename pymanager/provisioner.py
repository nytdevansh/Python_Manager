"""
Self-contained Python Provisioner for Virtual Environments.

Manages sub-Python installations and sub-environments completely inside
the virtual environment directory, without requiring any system compilers.
"""

import os
import tarfile
import urllib.request
import subprocess
from typing import Optional
from .utils import logger, run_command


class EnvironmentProvisioner:
    """
    Provisions specific Python versions and isolated sub-environments
    completely within a virtual environment directory.
    """

    def __init__(self, venv_root: str):
        self.venv_root = venv_root
        # Store all compat pythons and envs inside the virtual environment
        self.compat_dir = os.path.join(venv_root, ".compat")
        self.pythons_dir = os.path.join(self.compat_dir, "pythons")
        self.envs_dir = os.path.join(self.compat_dir, "envs")
        self.cache_dir = os.path.join(self.compat_dir, "cache")

        os.makedirs(self.pythons_dir, exist_ok=True)
        os.makedirs(self.envs_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)

    def ensure_python(self, version: str, download_url: str) -> str:
        """
        Download and unpack the portable Python version into the venv.
        Returns the path to the python3 binary.
        """
        python_install_dir = os.path.join(self.pythons_dir, version)
        python_bin = os.path.join(python_install_dir, "bin", "python3")
        if os.path.exists(python_bin):
            return python_bin

        # Also check if it's extracted under an inner 'python' directory
        inner_bin = os.path.join(python_install_dir, "python", "bin", "python3")
        if os.path.exists(inner_bin):
            return inner_bin

        logger.info(f"Downloading portable Python {version}...")
        tar_name = f"python-{version}.tar.gz"
        tar_path = os.path.join(self.cache_dir, tar_name)

        if not os.path.exists(tar_path):
            req = urllib.request.Request(download_url, headers={"User-Agent": "python-auto-env"})
            with urllib.request.urlopen(req) as resp, open(tar_path, "wb") as f:
                while chunk := resp.read(65536):
                    f.write(chunk)

        logger.info(f"Extracting portable Python {version}...")
        os.makedirs(python_install_dir, exist_ok=True)
        with tarfile.open(tar_path, "r:*") as tar:
            tar.extractall(path=python_install_dir)

        if os.path.exists(python_bin):
            return python_bin
        if os.path.exists(inner_bin):
            return inner_bin

        # Search for python3 executable in the install directory
        for root, _, files in os.walk(python_install_dir):
            if "python3" in files:
                candidate = os.path.join(root, "python3")
                if os.access(candidate, os.X_OK):
                    return candidate

        raise FileNotFoundError(f"Could not locate python3 binary in {python_install_dir}")

    def ensure_sub_env(self, version: str, download_url: str, package_spec: str) -> str:
        """
        Ensures an isolated sub-venv for this Python version exists
        with the requested package installed.
        Returns the path to the sub-environment directory.
        """
        env_dir = os.path.join(self.envs_dir, f"env_{version}")
        pip_bin = os.path.join(env_dir, "bin", "pip")

        if not os.path.exists(env_dir):
            python_bin = self.ensure_python(version, download_url)
            logger.info(f"Creating isolated sub-environment for Python {version} at {env_dir}...")
            res = run_command([python_bin, "-m", "venv", env_dir])
            if res.returncode != 0:
                raise RuntimeError(f"Failed to create venv: {res.stderr}")

        # Check if the package is installed
        check_res = run_command([pip_bin, "show", package_spec.split("==")[0]])
        if check_res.returncode != 0:
            logger.info(f"Installing {package_spec} into Python {version} environment...")
            install_res = run_command([pip_bin, "install", package_spec])
            if install_res.returncode != 0:
                raise RuntimeError(f"Failed to install {package_spec}: {install_res.stderr}")

        return env_dir
