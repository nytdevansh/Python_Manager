from setuptools import setup, find_packages

setup(
    name="pymanager",
    version="0.1.0",
    description="A smart Python environment manager with multi-version support.",
    author="Jadu",
    packages=find_packages(),
    install_requires=[
        "pyyaml",
        "packaging",
        "requests"
    ],
    entry_points={
        "console_scripts": [
            "pymanager=pymanager.cli:main",
        ],
    },
    python_requires=">=3.7",
)
