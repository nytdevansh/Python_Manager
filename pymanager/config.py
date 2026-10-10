import os
import yaml
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

@dataclass
class PackageConfig:
    name: str
    version: str
    python_version: Optional[str] = None

@dataclass
class SubEnvironmentConfig:
    python_version: str
    packages: List[str] = field(default_factory=list)

@dataclass
class PythonInstallationConfig:
    version: str
    path: str

@dataclass
class EnvironmentConfig:
    name: str
    main_python: str
    dependencies: List[PackageConfig] = field(default_factory=list)
    sub_environments: List[SubEnvironmentConfig] = field(default_factory=list)
    python_installations: List[PythonInstallationConfig] = field(default_factory=list)

    @classmethod
    def load(cls, path: str) -> 'EnvironmentConfig':
        """Load environment config from a YAML file."""
        if not os.path.exists(path):
            return cls(name="default", main_python="3.10")
            
        with open(path, 'r') as f:
            data = yaml.safe_load(f) or {}
            
        deps = [PackageConfig(**d) for d in data.get('dependencies', [])]
        sub_envs = [SubEnvironmentConfig(**s) for s in data.get('sub_environments', [])]
        py_installs = [PythonInstallationConfig(**p) for p in data.get('python_installations', [])]
        
        return cls(
            name=data.get('name', 'default'),
            main_python=data.get('main_python', '3.10'),
            dependencies=deps,
            sub_environments=sub_envs,
            python_installations=py_installs
        )

    def save(self, path: str):
        """Save environment config to a YAML file."""
        data = {
            'name': self.name,
            'main_python': self.main_python,
            'dependencies': [d.__dict__ for d in self.dependencies],
            'sub_environments': [s.__dict__ for s in self.sub_environments],
            'python_installations': [p.__dict__ for p in self.python_installations]
        }
        with open(path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
