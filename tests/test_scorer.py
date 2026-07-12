import pytest
from CONFUSERAY.scorer import compute_risk_score, score_to_severity
from CONFUSERAY.config import Config


@pytest.mark.parametrize("score,severity", [
    (14, "critical"),
    (9, "high"),
    (5, "medium"),
    (2, "low"),
    (0, "low"),
])
def test_score_to_severity(score, severity):
    assert score_to_severity(score) == severity


@pytest.mark.parametrize("name,internal_pkg,latest_ver,requested_ver,has_config,is_typo,expected_score", [
    # internal + public + higher version = critical (3+4+5+2=14)
    ("acme-auth", "acme-auth", "999.0.0", "1.0.0", False, False, 14),
    # internal + public + same version = high (3+4+2=9)
    ("acme-auth", "acme-auth", "1.0.0", "1.0.0", False, False, 9),
    # with registry config = less risk (9-2=7)
    ("acme-auth", "acme-auth", "1.0.0", "1.0.0", True, False, 7),
])
def test_compute_risk_score(name, internal_pkg, latest_ver, requested_ver, has_config, is_typo, expected_score):
    cfg = Config({"internal_packages": [internal_pkg] if internal_pkg else []})
    registry_result = {
        "exists": True,
        "latest_version": latest_ver,
        "versions": [latest_ver],
    }
    result = compute_risk_score(
        name=name,
        ecosystem="npm",
        config=cfg,
        registry_result=registry_result,
        requested_version=requested_ver,
        has_registry_config=has_config,
        is_typosquat=is_typo,
    )
    assert result["score"] == expected_score
    assert result["severity"] == score_to_severity(expected_score)


def test_risk_score_not_internal():
    cfg = Config({"internal_packages": ["other-pkg"]})
    registry_result = {
        "exists": True,
        "latest_version": "18.0.0",
        "versions": ["18.0.0"],
    }
    result = compute_risk_score(
        name="react",
        ecosystem="npm",
        config=cfg,
        registry_result=registry_result,
        requested_version="18.0.0",
    )
    assert result["score"] < 9

def test_risk_score_typosquat():
    cfg = Config({"internal_packages": []})
    registry_result = {"exists": False, "latest_version": None, "versions": []}
    result = compute_risk_score(
        name="reqeusts",
        ecosystem="pypi",
        config=cfg,
        registry_result=registry_result,
        requested_version="1.0.0",
        is_typosquat=True,
    )
    # typosquat adds +4
    assert result["score"] >= 4


def test_factors_are_descriptive():
    cfg = Config({"internal_packages": ["acme-auth"]})
    registry_result = {
        "exists": True,
        "latest_version": "999.0.0",
        "versions": ["999.0.0"],
    }
    result = compute_risk_score(
        name="acme-auth",
        ecosystem="npm",
        config=cfg,
        registry_result=registry_result,
        requested_version="1.0.0",
    )
    assert isinstance(result["factors"], list)
    assert len(result["factors"]) > 0
    for factor in result["factors"]:
        assert isinstance(factor, str)
        assert len(factor) > 5  # human-readable, not just a code
