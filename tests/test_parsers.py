import os
import pytest

from CONFUSERAY import parsers
from CONFUSERAY.scanner import is_pinned, version_is_higher, should_fail, Finding

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, "data")


def test_requirements_basic_and_unpinned():
    deps = parsers.parse_requirements(os.path.join(DATA, "requirements.txt"))
    names = {d[0] for d in deps}
    assert "requests" in names
    assert "flask" in names
    assert "acme-payments-lib" in names
    
    assert "-r" not in names
    assert "" not in names


def test_requirements_extras_stripped():
    path = os.path.join(DATA, "req_with_extras.txt")
    deps = parsers.parse_requirements(path)
    got = {d[0]: d[1] for d in deps}
    assert "celery" in got            # extras [redis] removed from name
    assert got["celery"].startswith("==5")


def test_package_json_scopes_all_sections():
    deps = parsers.parse_package_json(os.path.join(DATA, "package.json"))
    names = {d[0] for d in deps}
    assert "@acme/payments" in names
    assert "@acme/shared-utils" in names   # comes from devDependencies
    assert "react" in names


def test_pom_resolves_property_version():
    deps = parsers.parse_pom_xml(os.path.join(DATA, "pom.xml"))
    coords = {d[0]: d[1] for d in deps}
    assert "com.acme:payments-sdk" in coords
    assert coords["com.acme:payments-sdk"] == "3.0.0"  # ${payments.version}



@pytest.mark.parametrize("spec,pinned", [
    ("1.2.3", True),
    ("==2.0.0", True),
    ("4.17.21", True),
    ("*", False),
    ("latest", False),
    (">=1.0", False),
    ("^1.2.3", False),
    ("", False),
])
def test_is_pinned(spec, pinned):
    assert is_pinned(spec) is pinned


@pytest.mark.parametrize("version,spec,expected", [
    ("999.0.0", "^2.0.0", True),
    ("1.0.0", "==2.0.0", False),
    ("8.0.0", "any", True),
    (None, "1.0.0", False),
])
def test_version_is_higher(version, spec, expected):
    assert version_is_higher(version, spec) is expected


@pytest.mark.parametrize("findings,threshold,expected", [
    ([Finding("x", "npm", "critical", "t", "d", "r")], "high", True),
    ([Finding("y", "npm", "medium", "t", "d", "r")], "high", False),
    ([Finding("y", "npm", "medium", "t", "d", "r")], "medium", True),
    ([], "low", False),
])
def test_should_fail_thresholds(findings, threshold, expected):
    assert should_fail(findings, threshold) is expected
