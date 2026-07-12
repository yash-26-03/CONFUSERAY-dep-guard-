import os
import tempfile
import shutil
import pytest

from CONFUSERAY.config import Config
from CONFUSERAY.registries import RegistryClient
from CONFUSERAY.scanner import scan_project, has_registry_protection

HERE = os.path.dirname(__file__)
CACHE = os.path.join(HERE, "data", "registry_cache.json")
EXAMPLES = os.path.join(os.path.dirname(HERE), "Examples")


@pytest.fixture
def client():
    return RegistryClient(offline=True, cache_path=CACHE)

@pytest.fixture
def tmp_project():
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


def _config():
    return Config({
        "internal_scopes": ["@acme", "@acme-corp"],
        "internal_packages": ["acme-payments-lib", "billing-core", "acme-auth"],
        "ecosystems": ["npm", "pypi", "maven"],
        "fail_on": "high",
    })

def test_scan_flags_confused_packages(client):
    findings = scan_project(EXAMPLES, _config(), client)
    flagged = {f.package for f in findings if f.severity in ("critical", "high")}
    # @acme/payments exists publicly with version 999 -> critical
    assert "@acme/payments" in flagged
    # acme-payments-lib exists on pypi with 8.0.0 -> critical
    assert "acme-payments-lib" in flagged


def test_scan_clean_when_internal_absent(tmp_project, client):
    """cache says an internal pkg is NOT public, no critical finding."""
    with open(os.path.join(tmp_project, "requirements.txt"), "w") as fh:
        fh.write("acme-auth==1.5.0\n")

    findings = scan_project(tmp_project, _config(), client)
    assert not [f for f in findings if f.severity in ("critical", "high")]


def test_scan_includes_risk_score(client):
    findings = scan_project(EXAMPLES, _config(), client)
    confused = [f for f in findings if "Dependency confusion" in f.title]
    assert all(f.risk_score and f.risk_score > 0 for f in confused)


@pytest.mark.parametrize("file_content,ecosystem,expected", [
    (None, "npm", False),  # no file
    (None, "pypi", False),  # no file
    ("@acme:registry=https://npm.internal\n", "npm", True),  # .npmrc present
])
def test_has_registry_protection(tmp_project, file_content, ecosystem, expected):
    if file_content:
        fname = ".npmrc" if ecosystem == "npm" else f".{ecosystem}rc"
        with open(os.path.join(tmp_project, fname), "w") as fh:
            fh.write(file_content)
    assert has_registry_protection(tmp_project, ecosystem) is expected

def test_scan_registry_config_warning(tmp_project, client):
    with open(os.path.join(tmp_project, "requirements.txt"), "w") as fh:
        fh.write("acme-payments-lib==2.0.0\n")

    findings = scan_project(tmp_project, _config(), client)
    config_warnings = [f for f in findings if "registry scope" in f.title.lower()]
    assert len(config_warnings) > 0


def test_scan_warn_unpinned(tmp_project, client):
    with open(os.path.join(tmp_project, "requirements.txt"), "w") as fh:
        fh.write("flask>=2.0\n")

    cfg = Config({
        "internal_packages": [],
        "ecosystems": ["pypi"],
        "warn_unpinned": True,
    })
    findings = scan_project(tmp_project, cfg, client)

    unpinned = [f for f in findings if "Unpinned" in f.title]
    assert len(unpinned) == 1
    assert unpinned[0].package == "flask"

