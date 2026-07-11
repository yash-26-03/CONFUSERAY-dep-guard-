import pytest
from CONFUSERAY.scorer import compute_risk_score, score_to_severity
from CONFUSERAY.config import Config


def test_score_to_severity_critical():
    assert score_to_severity(14) == "critical"


def test_score_to_severity_high():
    assert score_to_severity(9) == "high"


def test_score_to_severity_medium():
    assert score_to_severity(5) == "medium"


def test_score_to_severity_low():
    assert score_to_severity(2) == "low"


def test_score_to_severity_zero():
    assert score_to_severity(0) == "low"


def test_risk_score_internal_and_public_higher_version():
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
    # internal(3) + public_exists(4) + higher_version(5) + no_config(2) = 14
    assert result["score"] == 14
    assert result["severity"] == "critical"


def test_risk_score_internal_and_public_same_version():
    cfg = Config({"internal_packages": ["acme-auth"]})
    registry_result = {
        "exists": True,
        "latest_version": "1.0.0",
        "versions": ["1.0.0"],
    }
    result = compute_risk_score(
        name="acme-auth",
        ecosystem="npm",
        config=cfg,
        registry_result=registry_result,
        requested_version="1.0.0",
    )
    # internal(3) + public_exists(4) + no_config(2) = 9
    assert result["score"] == 9
    assert result["severity"] == "high"


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
    # not internal, so no internal points — only public exists points
    assert result["score"] < 9


def test_risk_score_with_registry_config():
    cfg = Config({"internal_packages": ["acme-auth"]})
    registry_result = {
        "exists": True,
        "latest_version": "1.0.0",
        "versions": ["1.0.0"],
    }
    result = compute_risk_score(
        name="acme-auth",
        ecosystem="npm",
        config=cfg,
        registry_result=registry_result,
        requested_version="1.0.0",
        has_registry_config=True,
    )
    # has_registry_config removes the +2
    assert result["score"] == 9 - 2


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
