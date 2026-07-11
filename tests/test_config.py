import os
import json
import tempfile
import pytest
from CONFUSERAY.config import Config, load_config, ConfigError


# -- is_internal ------------------------------------------------------------

def test_is_internal_exact_match():
    cfg = Config({"internal_packages": ["acme-auth"]})
    assert cfg.is_internal("acme-auth") is True


def test_is_internal_scoped_npm():
    cfg = Config({"internal_scopes": ["@acme"]})
    assert cfg.is_internal("@acme/payments") is True


def test_is_internal_prefix_match():
    # bare scope prefix: "acme" matches "acme-utils" via startswith("acme-")
    cfg = Config({"internal_scopes": ["acme"]})
    assert cfg.is_internal("acme-utils") is True


def test_is_internal_not_internal():
    cfg = Config({"internal_packages": ["acme-auth"]})
    assert cfg.is_internal("react") is False


def test_is_internal_case_insensitive():
    cfg = Config({"internal_packages": ["Acme-Auth"]})
    assert cfg.is_internal("acme-auth") is True


# -- load_config ------------------------------------------------------------

def test_load_config_valid():
    data = {
        "internal_scopes": ["@acme"],
        "internal_packages": ["billing-core"],
        "fail_on": "medium",
    }
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    try:
        json.dump(data, tmp)
        tmp.close()
        cfg = load_config(tmp.name)
        assert "@acme" in cfg.internal_scopes
        assert "billing-core" in cfg.internal_packages
        assert cfg.fail_on == "medium"
    finally:
        os.unlink(tmp.name)


def test_load_config_missing_file():
    with pytest.raises(ConfigError):
        load_config("/no/such/file.json")


def test_load_config_invalid_json():
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    try:
        tmp.write("{not valid json!!!")
        tmp.close()
        with pytest.raises(ConfigError):
            load_config(tmp.name)
    finally:
        os.unlink(tmp.name)


# -- defaults ---------------------------------------------------------------

def test_config_defaults():
    cfg = Config({})
    assert cfg.fail_on == "high"
    assert cfg.warn_unpinned is False
    assert cfg.internal_packages == []
    assert cfg.internal_scopes == []
    assert "npm" in cfg.enabled
    assert "pypi" in cfg.enabled
