import os
import pytest
from CONFUSERAY.registries import RegistryClient, RegistryError, normalize

CACHE_PATH = os.path.join(os.path.dirname(__file__), "data", "registry_cache.json")


# -- normalize --------------------------------------------------------------

def test_normalize_builds_dict():
    result = normalize(True, "1.0.0", ["1.0.0"], "npm")
    assert result["exists"] is True
    assert result["latest_version"] == "1.0.0"
    assert result["versions"] == ["1.0.0"]
    assert result["registry"] == "npm"


def test_normalize_empty():
    result = normalize(False, None, [], "pypi")
    assert result["exists"] is False
    assert result["latest_version"] is None
    assert result["versions"] == []
    assert result["registry"] == "pypi"


# -- offline lookups using the real cache file ------------------------------

@pytest.fixture
def client():
    return RegistryClient(offline=True, cache_path=CACHE_PATH)


def test_offline_npm_lookup(client):
    result = client.lookup("npm", "@acme/payments")
    assert result["exists"] is True
    assert result["latest_version"] == "999.0.0"
    assert "999.0.0" in result["versions"]


def test_offline_pypi_lookup(client):
    result = client.lookup("pypi", "acme-payments-lib")
    assert result["exists"] is True
    assert result["latest_version"] == "8.0.0"


def test_offline_not_found(client):
    result = client.lookup("npm", "@acme/auth")
    assert result["exists"] is False


def test_offline_maven_lookup(client):
    result = client.lookup("maven", "com.acme:payments-sdk")
    assert result["exists"] is True
    assert result["latest_version"] == "7.0.0"


# -- edge cases -------------------------------------------------------------

def test_client_no_cache_returns_not_found():
    bare = RegistryClient(offline=True)
    result = bare.lookup("npm", "anything")
    assert result["exists"] is False
