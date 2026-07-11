"""End-to-end-ish test: scan a tiny project with the offline registry cache.
Keeps the suite green without hitting the real internet."""
import os
import tempfile

from CONFUSERAY.config import Config
from CONFUSERAY.registries import RegistryClient
from CONFUSERAY.scanner import scan_project, has_registry_protection

HERE = os.path.dirname(__file__)
CACHE = os.path.join(HERE, "data", "registry_cache.json")
# reuse the example files as a scan target
EXAMPLES = os.path.join(os.path.dirname(HERE), "Examples")


def _config():
    return Config({
        "internal_scopes": ["@acme", "@acme-corp"],
        "internal_packages": ["acme-payments-lib", "billing-core", "acme-auth"],
        "ecosystems": ["npm", "pypi", "maven"],
        "fail_on": "high",
    })


def test_scan_flags_confused_packages():
    client = RegistryClient(offline=True, cache_path=CACHE)
    findings = scan_project(EXAMPLES, _config(), client)

    flagged = {f.package for f in findings if f.severity in ("critical", "high")}
    # @acme/payments exists publicly with version 999 -> critical
    assert "@acme/payments" in flagged
    # acme-payments-lib exists on pypi with 8.0.0 -> critical
    assert "acme-payments-lib" in flagged


def test_scan_clean_when_internal_absent():
    """If the cache says an internal pkg is NOT public, no critical finding."""
    tmp = tempfile.mkdtemp()
    with open(os.path.join(tmp, "requirements.txt"), "w") as fh:
        fh.write("acme-auth==1.5.0\n")

    client = RegistryClient(offline=True, cache_path=CACHE)
    findings = scan_project(tmp, _config(), client)
    assert not [f for f in findings if f.severity in ("critical", "high")]


def test_scan_includes_risk_score():
    """Findings from confused packages should have a risk_score."""
    client = RegistryClient(offline=True, cache_path=CACHE)
    findings = scan_project(EXAMPLES, _config(), client)

    confused = [f for f in findings if "Dependency confusion" in f.title]
    for f in confused:
        assert f.risk_score is not None
        assert f.risk_score > 0


def test_has_registry_protection_missing():
    """A directory with no config files should report no protection."""
    tmp = tempfile.mkdtemp()
    assert has_registry_protection(tmp, "npm") is False
    assert has_registry_protection(tmp, "pypi") is False


def test_has_registry_protection_present():
    """A .npmrc file counts as protection for npm."""
    tmp = tempfile.mkdtemp()
    with open(os.path.join(tmp, ".npmrc"), "w") as fh:
        fh.write("@acme:registry=https://npm.internal\n")
    assert has_registry_protection(tmp, "npm") is True


def test_scan_registry_config_warning():
    """Projects without registry config should get a medium warning."""
    tmp = tempfile.mkdtemp()
    with open(os.path.join(tmp, "requirements.txt"), "w") as fh:
        fh.write("acme-payments-lib==2.0.0\n")

    client = RegistryClient(offline=True, cache_path=CACHE)
    findings = scan_project(tmp, _config(), client)

    config_warnings = [f for f in findings if "registry scope" in f.title.lower()]
    assert len(config_warnings) > 0


def test_scan_warn_unpinned():
    """When warn_unpinned is set, loose specs should be flagged."""
    tmp = tempfile.mkdtemp()
    with open(os.path.join(tmp, "requirements.txt"), "w") as fh:
        fh.write("flask>=2.0\n")

    cfg = Config({
        "internal_packages": [],
        "ecosystems": ["pypi"],
        "warn_unpinned": True,
    })
    client = RegistryClient(offline=True, cache_path=CACHE)
    findings = scan_project(tmp, cfg, client)

    unpinned = [f for f in findings if "Unpinned" in f.title]
    assert len(unpinned) == 1
    assert unpinned[0].package == "flask"

