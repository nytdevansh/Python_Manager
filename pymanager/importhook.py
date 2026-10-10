"""
Transparent Auto-Compatibility Import Hook for Python Environments.

Allows developers to write standard Python code without learning any new CLI or configuration.
When an incompatible library is imported, this hook:
1. Dynamically detects that the package requires an older/different Python version.
2. Auto-provisions that Python version and environment under the hood.
3. Transparently proxies imports and calls across Python versions.
"""

import sys
import os
import types
from importlib.abc import MetaPathFinder, Loader
from importlib.machinery import ModuleSpec
from typing import Any, Optional, Dict

from .discovery import AutoVersionResolver
from .provisioner import EnvironmentProvisioner
from .bridge import SubprocessBridge
from .utils import logger, get_current_python_version


class AutoProxyModule(types.ModuleType):
    """
    Transparent proxy module that forwards attributes and function calls
    to a sub-environment running the required Python version.
    """

    def __init__(self, fullname: str, sub_env_path: str):
        super().__init__(fullname)
        self.__name__ = fullname
        self._sub_env_path = sub_env_path
        self._bridge = SubprocessBridge(sub_env_path)
        self.__file__ = f"<pymanager-compat-bridge:{sub_env_path}>"
        self.__path__ = [sub_env_path]

    def __getattr__(self, name: str) -> Any:
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(f"Module '{self.__name__}' has no attribute '{name}'")

        full_attr_name = f"{self.__name__}.{name}"

        class ProxyCallableOrAttr:
            def __init__(self, parent_bridge: SubprocessBridge, mod_name: str, attr: str):
                self._bridge = parent_bridge
                self._mod_name = mod_name
                self._attr = attr
                self._full_name = f"{mod_name}.{attr}"

            def __call__(self, *args, **kwargs):
                return self._bridge.call_function(self._mod_name, self._attr, *args, **kwargs)

            def __getattr__(self, sub_name):
                # Chain to nested attribute or submodule
                return ProxyCallableOrAttr(self._bridge, self._full_name, sub_name)

            def __repr__(self):
                return f"<CompatProxy '{self._full_name}'>"

        return ProxyCallableOrAttr(self._bridge, self.__name__, name)


class CompatLoader(Loader):
    """Loader that creates AutoProxyModule instances."""

    def __init__(self, fullname: str, sub_env_path: str):
        self.fullname = fullname
        self.sub_env_path = sub_env_path

    def create_module(self, spec: ModuleSpec) -> types.ModuleType:
        module = AutoProxyModule(self.fullname, self.sub_env_path)
        sys.modules[self.fullname] = module
        return module

    def exec_module(self, module: types.ModuleType) -> None:
        pass


class CompatMetaPathFinder(MetaPathFinder):
    """
    sys.meta_path hook that intercepts imports of incompatible libraries
    and provisions their environment under the hood.
    """

    def __init__(self, venv_root: Optional[str] = None):
        if not venv_root:
            venv_root = os.environ.get("VIRTUAL_ENV", os.getcwd())
        self.venv_root = venv_root
        self.resolver = AutoVersionResolver()
        self.provisioner = EnvironmentProvisioner(venv_root)
        self.current_python = get_current_python_version()
        self._resolved_sub_envs: Dict[str, str] = {}

    def _get_pinned_version(self, package_name: str) -> Optional[str]:
        """Check requirements.txt in project/script directories for pinned version."""
        candidates = [
            os.path.join(os.getcwd(), "requirements.txt"),
            os.path.join(os.getcwd(), "examples", "requirements.txt"),
            os.path.join(self.venv_root, "requirements.txt"),
            os.path.join(os.path.dirname(self.venv_root), "requirements.txt"),
        ]
        if sys.argv and sys.argv[0]:
            script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            candidates.insert(0, os.path.join(script_dir, "requirements.txt"))

        for req_path in candidates:
            if os.path.exists(req_path):
                try:
                    with open(req_path, "r") as f:
                        for line in f:
                            clean_line = line.strip().split("#")[0].strip()
                            if "==" in clean_line:
                                name, ver = clean_line.split("==", 1)
                                if name.strip().lower() == package_name.lower():
                                    return ver.strip()
                except Exception:
                    pass
        return None

    def find_spec(
        self, fullname: str, path: Optional[Any] = None, target: Optional[Any] = None
    ) -> Optional[ModuleSpec]:
        top_level = fullname.split(".")[0]

        # Ignore standard library or internal modules
        if top_level in sys.builtin_module_names or top_level.startswith("_"):
            return None

        # If already resolved in our sub-environments:
        if top_level in self._resolved_sub_envs:
            sub_env_path = self._resolved_sub_envs[top_level]
            spec = ModuleSpec(
                fullname,
                CompatLoader(fullname, sub_env_path),
                is_package=True
            )
            spec.submodule_search_locations = [sub_env_path]
            return spec

        # Check if the package is already importable natively in current environment
        try:
            normal_spec = None
            for finder in sys.meta_path:
                if finder is not self and hasattr(finder, "find_spec"):
                    normal_spec = finder.find_spec(top_level, path, target)
                    if normal_spec is not None:
                        break
            if normal_spec is not None:
                return None  # Package is already installed natively
        except Exception:
            pass

        # Package is not natively available in current environment.
        # Check if project requested a specific pinned version:
        pinned_version = self._get_pinned_version(top_level)
        pkg_spec = f"{top_level}=={pinned_version}" if pinned_version else top_level

        try:
            res = self.resolver.resolve(top_level, self.current_python, package_version=pinned_version)
            if not res["compatible"] and res["download_url"]:
                logger.info(
                    f"[pymanager] Package '{pkg_spec}' requires Python {res['target_version']}. "
                    f"Auto-provisioning under the hood..."
                )
                sub_env_path = self.provisioner.ensure_sub_env(
                    res["target_version"],
                    res["download_url"],
                    pkg_spec
                )
                self._resolved_sub_envs[top_level] = sub_env_path
                spec = ModuleSpec(
                    fullname,
                    CompatLoader(fullname, sub_env_path),
                    is_package=True
                )
                spec.submodule_search_locations = [sub_env_path]
                return spec
        except Exception as e:
            logger.error(f"[pymanager] Resolution error for {top_level}: {e}")
            return None

        return None


def install_hook(venv_root: Optional[str] = None):
    """Installs the transparent auto-compatibility hook into the running Python process."""
    finder = CompatMetaPathFinder(venv_root)
    # Insert at the end of sys.meta_path so standard imports always take precedence
    if not any(isinstance(f, CompatMetaPathFinder) for f in sys.meta_path):
        sys.meta_path.append(finder)
        logger.info("[pymanager] Auto-compatibility hook active in Python environment.")
