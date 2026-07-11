import json
import os

DEFAULT_IGNORE_DIRS = {
    "node_modules", ".git", "venv", ".venv", "__pycache__", "dist",
    "build", ".idea", ".vscode", "target",
}

class ConfigError(Exception):
    pass

class Config:
    def __init__(self, data):
        self.internal_scopes = [s.lower() for s in data.get("internal_scopes", [])]
        self.internal_packages = [p.lower() for p in data.get("internal_packages", [])]
        self.ignore_dirs = set(data.get("ignore_dirs", DEFAULT_IGNORE_DIRS))
        self.enabled = set(data.get("ecosystems", ["npm", "pypi", "maven"]))
        self.fail_on = data.get("fail_on", "high").lower()
        self.warn_unpinned = bool(data.get("warn_unpinned", False))

    def is_internal(self, name):
        
        n = name.lower()
        if n in self.internal_packages:
            return True
        # scoped npm packages: @acme/something
        if "/" in n:
            scope = n.split("/", 1)[0]
            if scope in self.internal_scopes:
                return True
        
        for scope in self.internal_scopes:
            if scope.startswith("@"):
                continue  
            if n.startswith(scope + "-") or n == scope:
                return True
        return False


def load_config(path):
    if not path or not os.path.exists(path):
        raise ConfigError(f"config file not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"config is not valid json: {exc}")
    if not isinstance(data, dict):
        raise ConfigError("config root must be a json object")
    return Config(data)
