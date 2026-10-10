import os
import sys
import argparse
from .environment import EnvironmentManager
from .utils import print_color, Colors, run_command
from .config import EnvironmentConfig
from .pypi import query_package_info, get_supported_python_versions


def get_env_manager() -> EnvironmentManager:
    return EnvironmentManager(os.getcwd())


def init_cmd(args):
    manager = get_env_manager()
    manager.init_environment(args.python)
    print_color(f"Environment initialized in {os.getcwd()}", Colors.OKGREEN)


def install_cmd(args):
    manager = get_env_manager()
    pkg = args.package
    version = None
    if "==" in pkg:
        pkg, version = pkg.split("==", 1)

    result = manager.install_package(pkg, version)
    if result.success:
        print_color(f"Success: {result.message} using Python {result.python_version}", Colors.OKGREEN)
    else:
        print_color(f"Failed to install: {result.message}", Colors.FAIL)


def run_cmd(args):
    print_color(f"Running script {args.script}...", Colors.OKCYAN)
    res = run_command([sys.executable, args.script] + args.script_args, capture_output=False)
    sys.exit(res.returncode)


def list_cmd(args):
    config = EnvironmentConfig.load("environment.yml")
    print_color(f"Environment: {config.name}", Colors.HEADER)
    print_color(f"Main Python: {config.main_python}", Colors.OKCYAN)

    print("\nDependencies:")
    for dep in config.dependencies:
        py_ver = dep.python_version or "main"
        print(f"  - {dep.name} ({dep.version}) [Python: {py_ver}]")

    print("\nSub-Environments:")
    for sub in config.sub_environments:
        print(f"  - Python {sub.python_version}: {', '.join(sub.packages)}")


def info_cmd(args):
    try:
        versions = get_supported_python_versions(args.package)
        print_color(f"Package: {args.package}", Colors.HEADER)
        if versions:
            print(f"Supported Python versions: {', '.join(versions)}")
        else:
            print("Could not determine specific supported Python versions.")
    except Exception as e:
        print_color(f"Error querying info: {e}", Colors.FAIL)


def clean_cmd(args):
    print_color("Cleaning unused Python versions... (Not fully implemented in MVP)", Colors.WARNING)


def config_cmd(args):
    if os.path.exists("environment.yml"):
        with open("environment.yml", "r") as f:
            print(f.read())
    else:
        print_color("No environment.yml found.", Colors.FAIL)


def enable_cmd(args):
    """Enable auto-compatibility hook inside a virtual environment."""
    venv_dir = args.venv or os.environ.get("VIRTUAL_ENV") or sys.prefix

    site_packages = None
    lib_dir = os.path.join(venv_dir, "lib")
    if os.path.exists(lib_dir):
        for entry in os.listdir(lib_dir):
            sp = os.path.join(lib_dir, entry, "site-packages")
            if os.path.isdir(sp):
                site_packages = sp
                break

    if not site_packages:
        for p in sys.path:
            if "site-packages" in p and (venv_dir in p or not args.venv):
                site_packages = p
                break

    if not site_packages or not os.path.exists(site_packages):
        print_color(f"Could not locate site-packages in virtual environment: {venv_dir}", Colors.FAIL)
        sys.exit(1)

    sitecustomize_path = os.path.join(site_packages, "sitecustomize.py")
    content = """import os, sys
try:
    from pymanager.importhook import install_hook
    install_hook()
except Exception:
    pass
"""
    with open(sitecustomize_path, "w") as f:
        f.write(content)

    print_color(f"Auto-compatibility enabled in virtual environment: {venv_dir}", Colors.OKGREEN)
    print("Incompatible libraries will now be auto-provisioned and proxied under the hood.")


def disable_cmd(args):
    """Disable auto-compatibility hook inside a virtual environment."""
    venv_dir = args.venv or os.environ.get("VIRTUAL_ENV") or sys.prefix
    lib_dir = os.path.join(venv_dir, "lib")
    if os.path.exists(lib_dir):
        for entry in os.listdir(lib_dir):
            sitecustomize_path = os.path.join(lib_dir, entry, "site-packages", "sitecustomize.py")
            if os.path.exists(sitecustomize_path):
                os.remove(sitecustomize_path)
                print_color(f"Auto-compatibility disabled in: {venv_dir}", Colors.OKGREEN)
                return
    print_color("Hook was not installed or already removed.", Colors.WARNING)


def main():
    parser = argparse.ArgumentParser(description="pymanager - Smart Python environment manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_enable = subparsers.add_parser("enable", help="Enable auto-compatibility in a virtual environment")
    p_enable.add_argument("--venv", help="Path to virtual environment root (defaults to active venv)")

    p_disable = subparsers.add_parser("disable", help="Disable auto-compatibility in a virtual environment")
    p_disable.add_argument("--venv", help="Path to virtual environment root (defaults to active venv)")

    p_init = subparsers.add_parser("init", help="Initialize a new managed environment")
    p_init.add_argument("--python", help="Main Python version to use")

    p_install = subparsers.add_parser("install", help="Install a package")
    p_install.add_argument("package", help="Package to install (e.g. requests==2.31.0)")

    p_run = subparsers.add_parser("run", help="Run a script")
    p_run.add_argument("script", help="Script to run")
    p_run.add_argument("script_args", nargs=argparse.REMAINDER, help="Arguments for the script")

    p_list = subparsers.add_parser("list", help="List environments and packages")

    p_info = subparsers.add_parser("info", help="Show compatibility info for a package")
    p_info.add_argument("package", help="Package name")

    p_clean = subparsers.add_parser("clean", help="Remove unused Python versions")
    p_config = subparsers.add_parser("config", help="Show environment.yml")

    args = parser.parse_args()

    commands = {
        "enable": enable_cmd,
        "disable": disable_cmd,
        "init": init_cmd,
        "install": install_cmd,
        "run": run_cmd,
        "list": list_cmd,
        "info": info_cmd,
        "clean": clean_cmd,
        "config": config_cmd,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
