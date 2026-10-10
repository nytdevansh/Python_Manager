# 🚀 pymanager

[![Python Versions](https://img.shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14%20%7C%203.15-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-50%2F50%20passing-brightgreen.svg)](tests/)

**Transparent multi-version Python execution for virtual environments — zero code changes, zero configuration files to learn.**

---

## 💡 The Problem

You want to upgrade to the latest Python version (e.g. Python 3.15) to take advantage of speedups and new language features. But your project depends on a critical library (or one of its dependencies) that only supports an older Python version (e.g. `< 3.12`):

```text
ERROR: Could not find a version that satisfies the requirement scipy==1.10.1
(from versions: none)
ERROR: Package 'scipy' requires a different Python: 3.15.0 not in '<3.12,>=3.8'
```

Until now, you had two bad choices:
1. **Stay stuck** on an older Python version across your entire project.
2. **Rewrite or replace** the incompatible library.

---

## ⚡ The Solution

`pymanager` enables **multi-version execution inside standard Python virtual environments under the hood**:

1. Write standard, idiomatic Python code:
   ```python
   import requests       # Runs natively on modern Python (e.g. 3.14)
   import click          # Runs natively on modern Python (e.g. 3.14)
   import scipy.constants # Incompatible with 3.14? Runs on Python 3.11 under the hood!
   ```
2. **Zero new syntax or configuration files to learn**: You do not write manual bridge calls or edit proprietary config files.
3. **Dynamic discovery**: `pymanager` queries PyPI metadata and official release feeds dynamically to find the highest compatible Python version — **no hardcoded version lists**.
4. **Self-contained**: Downloads portable, standalone Python distributions directly into your `.venv` — **no host C compilers, Homebrew, or Xcode tools needed**.

---

## 🏃 Quickstart: Reproduce in 60 Seconds

Clone the repository and run the turnkey reproduction demo:

```bash
git clone https://github.com/your-username/pymanager.git
cd pymanager

# Run the 1-click reproduction script (macOS / Linux):
./run_demo.sh
```

### Or Step-by-Step in Any Virtual Environment:

```bash
# 1. Create and activate a standard virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install pymanager into the virtual environment
pip install -e .

# 3. Enable auto-compatibility in the environment (runs under the hood via sitecustomize)
pymanager enable

# 4. Run your regular Python script!
python examples/multi_version_demo.py
```

---

## 🖥️ Live Output

```text
=================================================================
  🚀 Multi-Version Python Environment Compatibility Demo
=================================================================

  Main Host Python Version: 3.12.10

─────────────────────────────────────────────────────────────────
  [1] Native Library: requests (Python >= 3.10)
─────────────────────────────────────────────────────────────────
      • HTTP Status: 200
      • Requests Version: 2.34.2
      • Executed natively on main Python interpreter ✅

─────────────────────────────────────────────────────────────────
  [2] Native Library: click (Python >= 3.10)
─────────────────────────────────────────────────────────────────
      • Output: Click formatted message successfully!
      • Executed natively on main Python interpreter ✅

─────────────────────────────────────────────────────────────────
  [3] Incompatible Library: scipy 1.10.1 (Requires Python < 3.12)
─────────────────────────────────────────────────────────────────
      • Importing scipy, scipy.constants, scipy.special...
      • scipy.constants speed of light: 299,792,458 m/s
      • scipy.special factorial(10): 3,628,800
      • Auto-provisioned & executed via sub-environment under the hood ✅

=================================================================
  🎉 SUCCESS: All libraries executed seamlessly across Python versions!
=================================================================
```

*Subsequent runs execute in **milliseconds** because the provisioned environment is cached inside the virtual environment.*

---

## 🛠️ How It Works Under The Hood

```
┌───────────────────────────────────────────────────────────────────────┐
│                          Your Python Process                          │
│                                                                       │
│  import requests    ──▶ Standard Site-Packages (Python 3.14) ✅       │
│  import click       ──▶ Standard Site-Packages (Python 3.14) ✅       │
│                                                                       │
│  import scipy       ──▶ sys.meta_path Hook (CompatMetaPathFinder)    │
│                            │                                          │
│                            ▼                                          │
│                   Dynamic PyPI Inspection                             │
│                   scipy 1.10.1 requires '<3.12, >=3.8'                │
│                            │                                          │
│                            ▼                                          │
│                   Auto-Provisioning (.venv/.compat/)                  │
│                   • Fetches portable Python 3.11.17 distribution      │
│                   • Unpacks without host C compilers                  │
│                   • Creates sub-venv & installs scipy==1.10.1         │
│                            │                                          │
│                            ▼                                          │
│                   Transparent ModuleProxy                             │
│                   • Returns proxy module to user script               │
│                   • Subprocess IPC bridge forwards calls seamlessly   │
└───────────────────────────────────────────────────────────────────────┘
```

1. **MetaPath Import Hook**: An import hook (`CompatMetaPathFinder`) is registered via `sitecustomize.py`. It only intervenes when an import cannot be satisfied by the current Python interpreter.
2. **Dynamic Resolver**: Queries PyPI JSON metadata to inspect `Requires-Python` constraints and matches against available releases to pick the optimal Python version.
3. **Portable Distribution Provisioner**: Downloads standalone, self-contained Python distributions (`python-build-standalone`) directly into the `.venv` directory.
4. **IPC Bridge**: Forwards attributes, submodules, and function calls across process boundaries using standard JSON-RPC over stdin/stdout.

---

## 🧪 Running the Test Suite

The project includes a 50-test unit and integration test suite with mocking for network and filesystem operations:

```bash
# Run tests with pytest
python -m pytest tests/ -v
```

```text
============================== 50 passed in 0.18s ==============================
```

---

## 📁 Project Structure

```
pymanager/
├── pymanager/
│   ├── __init__.py          # Package metadata
│   ├── cli.py               # CLI: enable, disable, info, list
│   ├── importhook.py        # sys.meta_path transparent import hook
│   ├── discovery.py         # Dynamic PyPI & Python release resolver
│   ├── provisioner.py       # Portable Python download & sub-venv isolation
│   ├── bridge.py            # Subprocess IPC bridge & ModuleProxy
│   ├── pypi.py              # PyPI JSON API client
│   ├── resolver.py          # Version range specifier parser
│   └── utils.py             # Color output, logging, runner
├── examples/
│   ├── multi_version_demo.py # Turnkey demonstration script
│   └── requirements.txt     # Example dependencies (mixed versions)
├── tests/                   # 50 unit tests
├── run_demo.sh              # 1-click reproduction script
├── pyproject.toml           # Modern PEP 517/621 packaging
├── setup.py                 # Setuptools fallback
├── LICENSE                  # MIT License
└── README.md                # Documentation
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
