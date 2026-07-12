import os
import pytest
from CONFUSERAY.registries import RegistryClient, RegistryError, normalize

CACHE_PATH = os.path.join(os.path.dirname(__file__), "data", "registry_cache.json")


@pytest.mark.parametrize("exists,latest,versions,registry,expected_exists,expected_latest", [
    (True, "1.0.0", ["1.0.0"], "npm", True, "1.0.0"),
    (False, None, [], "pypi", False, None),
])
def test_normalize(exists, latest, versions, registry, expected_exists, expected_latest):
    result = normalize(exists, latest, versions, registry)
    assert result["exists"] is expected_exists
    assert result["latest_version"] is expected_latest
    assert result["versions"] == versions
    assert result["registry"] == registry



@pytest.fixture
def client():
    return RegistryClient(offline=True, cache_path=CACHE_PATH)

@pytest.mark.parametrize("ecosystem,package,exists,latest", [
    ("npm", "@acme/payments", True, "999.0.0"),
    ("pypi", "acme-payments-lib", True, "8.0.0"),
    ("maven", "com.acme:payments-sdk", True, "7.0.0"),
    ("npm", "@acme/auth", False, None),
])
def test_offline_lookup(client, ecosystem, package, exists, latest):
    result = client.lookup(ecosystem, package)
    assert result["exists"] is exists
    if exists:
        assert result["latest_version"] == latest


# edge cases
def test_client_no_cache_returns_not_found():
    bare = RegistryClient(offline=True)
    result = bare.lookup("npm", "anything")
    assert result["exists"] is False
