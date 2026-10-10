import os
import shutil
import venv
from dataclasses import dataclass
from typing import Optional, List
from .config import EnvironmentConfig, PackageConfig, SubEnvironmentConfig, PythonInstallationConfig
from .resolver import VersionResolver
from .builder import PythonBuilder
from .utils import get_current_python_version, run_command, logger

@dataclass
class InstallResult:
    success: bool
    package: str
    version: Optional[str]
    python_version: str
    sub_env_path: Optional[str]
    message: str

class EnvironmentManager:
    def __init__(self, base_path: str):
        self.base_path = base_path
        self.pymanager_dir = os.path.join(base_path, ".pymanager")
        self.cache_dir = os.path.join(self.pymanager_dir, "cache")
        self.pythons_dir = os.path.join(self.pymanager_dir, "pythons")
        self.envs_dir = os.path.join(self.pymanager_dir, "envs")
        self.config_path = os.path.join(base_path, "environment.yml")
        self.config = EnvironmentConfig.load(self.config_path)
        self.resolver = VersionResolver()
        self.builder = PythonBuilder(self.cache_dir)

    def init_environment(self, python_version: Optional[str] = None):
        """Create the .pymanager directory structure."""
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.pythons_dir, exist_ok=True)
        os.makedirs(self.envs_dir, exist_ok=True)
        
        if not os.path.exists(self.config_path):
            self.config.name = os.path.basename(os.path.abspath(self.base_path))
            self.config.main_python = python_version or get_current_python_version()
            self.config.save(self.config_path)
            logger.info(f"Initialized new environment at {self.base_path}")
        else:
            logger.info("Environment already initialized.")

    def _ensure_python_version(self, version: str) -> str:
        """Ensure a specific Python version is available, build if necessary."""
        install_dir = os.path.join(self.pythons_dir, version)
        python_bin = os.path.join(install_dir, "bin", "python3")
        
        if os.path.exists(python_bin):
            return python_bin
            
        logger.info(f"Python {version} not found locally. Building from source...")
        build_dir = os.path.join(self.cache_dir, f"build_{version}")
        os.makedirs(build_dir, exist_ok=True)
        
        source_dir = self.builder.download_source(version, build_dir)
        self.builder.build_python(source_dir, install_dir)
        
        # Update config
        self.config.python_installations.append(PythonInstallationConfig(version=version, path=install_dir))
        self.config.save(self.config_path)
        
        return python_bin

    def create_sub_environment(self, python_version: str, packages: List[str]) -> str:
        """Create a venv with a specific Python version."""
        python_bin = self._ensure_python_version(python_version)
        env_name = f"env_{python_version}"
        env_path = os.path.join(self.envs_dir, env_name)
        
        if not os.path.exists(env_path):
            logger.info(f"Creating sub-environment for Python {python_version} at {env_path}")
            run_command([python_bin, "-m", "venv", env_path])
            
            # Record in config
            self.config.sub_environments.append(SubEnvironmentConfig(python_version=python_version, packages=[]))
            self.config.save(self.config_path)
            
        # Install packages
        pip_bin = os.path.join(env_path, "bin", "pip")
        for pkg in packages:
            logger.info(f"Installing {pkg} in sub-environment...")
            run_command([pip_bin, "install", pkg])
            
            # Update config packages list
            for sub_env in self.config.sub_environments:
                if sub_env.python_version == python_version and pkg not in sub_env.packages:
                    sub_env.packages.append(pkg)
            self.config.save(self.config_path)
            
        return env_path

    def install_package(self, package_name: str, version: Optional[str] = None) -> InstallResult:
        """Main install flow for a package."""
        logger.info(f"Resolving {package_name}...")
        main_python = self.config.main_python
        
        # 1-2. Query PyPI & Resolve
        resolution = self.resolver.resolve(package_name, main_python, version)
        pkg_spec = f"{package_name}=={version}" if version else package_name
        
        if resolution.compatible:
            # 3. Compatible with main Python
            logger.info(f"{package_name} is compatible with main Python {main_python}. Installing globally...")
            # For this MVP, we assume main python pip is available in path or we install via current sys.executable
            import sys
            run_command([sys.executable, "-m", "pip", "install", pkg_spec])
            self.config.dependencies.append(PackageConfig(name=package_name, version=version or "latest"))
            self.config.save(self.config_path)
            return InstallResult(True, package_name, version, main_python, None, "Installed in main environment")
            
        if not resolution.recommended_python:
            return InstallResult(False, package_name, version, main_python, None, resolution.reason)
            
        # 4-7. Incompatible. Use/Build alternate Python and sub-environment
        logger.info(f"{package_name} needs Python {resolution.recommended_python}. Preparing sub-environment...")
        target_python = resolution.recommended_python
        
        env_path = self.create_sub_environment(target_python, [pkg_spec])
        
        # 8. Update environment.yml
        self.config.dependencies.append(PackageConfig(
            name=package_name, 
            version=version or "latest", 
            python_version=target_python
        ))
        self.config.save(self.config_path)
        
        return InstallResult(True, package_name, version, target_python, env_path, "Installed in sub-environment")
