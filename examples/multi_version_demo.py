"""
Multi-Version Library Compatibility Demo.

This script demonstrates transparent multi-version Python execution in a single process:
- Modern libraries (requests, click) run natively on the host Python version.
- Older libraries (scipy 1.10.1, requires Python <3.12) are auto-provisioned
  and executed in an isolated sub-environment under the hood.

No custom configuration or code modifications are required.
"""

import sys
import requests
import click
import scipy.constants
import scipy.special


def main():
    print("=" * 65)
    print("  🚀 Multi-Version Python Environment Compatibility Demo")
    print("=" * 65)
    print(f"\n  Main Host Python Version: {sys.version.split()[0]}")
    print()

    # 1. Native library: requests
    print("─" * 65)
    print("  [1] Native Library: requests (Python >= 3.10)")
    print("─" * 65)
    resp = requests.get("https://httpbin.org/get", timeout=5)
    print(f"      • HTTP Status: {resp.status_code}")
    print(f"      • Requests Version: {requests.__version__}")
    print("      • Executed natively on main Python interpreter ✅")

    # 2. Native library: click
    print()
    print("─" * 65)
    print("  [2] Native Library: click (Python >= 3.10)")
    print("─" * 65)
    styled_message = click.style("Click formatted message successfully!", fg="bright_cyan", bold=True)
    print(f"      • Output: {styled_message}")
    print("      • Executed natively on main Python interpreter ✅")

    # 3. Incompatible library: scipy==1.10.1 (requires Python < 3.12)
    print()
    print("─" * 65)
    print("  [3] Incompatible Library: scipy 1.10.1 (Requires Python < 3.12)")
    print("─" * 65)
    print("      • Importing scipy, scipy.constants, scipy.special...")
    c = scipy.constants.value("speed of light in vacuum")
    print(f"      • scipy.constants speed of light: {c:,.0f} m/s")
    
    fact_10 = scipy.special.factorial(10, exact=True)
    print(f"      • scipy.special factorial(10): {fact_10}")
    print("      • Auto-provisioned & executed via sub-environment under the hood ✅")

    print()
    print("=" * 65)
    print("  🎉 SUCCESS: All libraries executed seamlessly across Python versions!")
    print("=" * 65)


if __name__ == "__main__":
    main()
