import json
import tempfile
import pytest
from CONFUSERAY.config import Config, load_config, ConfigError


@pytest.fixture
def temp_json_file():
    """Create a temporary JSON file and clean up after."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    yield tmp
    tmp.close()
    import os
    os.unlink(tmp.name)


@pytest.mark.parametrize("config,pkg,expected", [
    ({"internal_packages": ["acme-auth"]}, "acme-auth", True),
    ({"internal_scopes": ["@acme"]}, "@acme/payments", True),
    ({"internal_scopes": ["acme"]}, "acme-utils", True),
    ({"internal_packages": ["acme-auth"]}, "react", False),
    ({"internal_packages": ["Acme-Auth"]}, "acme-auth", True),
])
def test_is_internal(config, pkg, expected):
    cfg = Config(config)
    assert cfg.is_internal(pkg) is expected


def test_load_config_valid(temp_json_file):
    data = {
        "internal_scopes": ["@acme"],
        "internal_packages": ["billing-core"],
        "fail_on": "medium",
    }
    json.dump(data, temp_json_file)
    temp_json_file.close()
    cfg = load_config(temp_json_file.name)
    assert "@acme" in cfg.internal_scopes
    assert "billing-core" in cfg.internal_packages
    assert cfg.fail_on == "medium"

def test_load_config_missing_file():
    with pytest.raises(ConfigError):
        load_config("/no/such/file.json")

def test_load_config_invalid_json(temp_json_file):
    temp_json_file.write("{not valid json!!!")
    temp_json_file.close()
    with pytest.raises(ConfigError):
        load_config(temp_json_file.name)
def test_config_defaults():
    cfg = Config({})
    assert cfg.fail_on == "high"
    assert cfg.warn_unpinned is False
    assert cfg.internal_packages == []
    assert cfg.internal_scopes == []
    assert "npm" in cfg.enabled
    assert "pypi" in cfg.enabled
