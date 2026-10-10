import os
import tempfile
import yaml
from pymanager.config import (
    EnvironmentConfig, 
    PackageConfig, 
    SubEnvironmentConfig, 
    PythonInstallationConfig
)

def test_default_config_load():
    config = EnvironmentConfig.load("nonexistent.yaml")
    assert config.name == "default"
    assert config.main_python == "3.10"
    assert len(config.dependencies) == 0
    assert len(config.sub_environments) == 0

def test_config_save_and_load():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "config.yaml")
        
        config = EnvironmentConfig(
            name="test_env",
            main_python="3.11",
            dependencies=[
                PackageConfig(name="requests", version="2.31.0"),
                PackageConfig(name="numpy", version="1.24.0", python_version="3.9")
            ],
            sub_environments=[
                SubEnvironmentConfig(python_version="3.9", packages=["numpy==1.24.0"])
            ],
            python_installations=[
                PythonInstallationConfig(version="3.9", path="/tmp/py39")
            ]
        )
        
        config.save(config_path)
        assert os.path.exists(config_path)
        
        loaded_config = EnvironmentConfig.load(config_path)
        assert loaded_config.name == "test_env"
        assert loaded_config.main_python == "3.11"
        assert len(loaded_config.dependencies) == 2
        assert loaded_config.dependencies[0].name == "requests"
        assert loaded_config.dependencies[1].python_version == "3.9"
        assert len(loaded_config.sub_environments) == 1
        assert loaded_config.sub_environments[0].python_version == "3.9"
        assert len(loaded_config.python_installations) == 1
        assert loaded_config.python_installations[0].path == "/tmp/py39"

def test_config_load_empty_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "empty.yaml")
        with open(config_path, "w") as f:
            f.write("")
            
        config = EnvironmentConfig.load(config_path)
        assert config.name == "default"
        assert config.main_python == "3.10"

def test_config_save_creates_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "new_config.yaml")
        config = EnvironmentConfig(name="test", main_python="3.8")
        config.save(config_path)
        
        with open(config_path, "r") as f:
            content = yaml.safe_load(f)
            
        assert content["name"] == "test"
        assert content["main_python"] == "3.8"
        assert "dependencies" in content

def test_config_package_config_defaults():
    pkg = PackageConfig(name="pandas", version="2.0.0")
    assert pkg.python_version is None

def test_config_sub_environment_defaults():
    sub_env = SubEnvironmentConfig(python_version="3.12")
    assert sub_env.packages == []
