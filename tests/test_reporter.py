import os
import json
import tempfile
from CONFUSERAY.scanner import Finding
from CONFUSERAY.reporter import finding_to_dict, write_json_report, write_markdown_report


def _make_finding(**overrides):
    defaults = dict(
        package="evil-pkg",
        ecosystem="npm",
        severity="high",
        title="Dependency confusion",
        detail="evil-pkg exists on public registry",
        recommendation="Pin to internal version",
        version="1.0.0",
        source="package.json",
        risk_score=14,
    )
    defaults.update(overrides)
    return Finding(**defaults)


# -- finding_to_dict --------------------------------------------------------

def test_finding_to_dict_fields():
    f = _make_finding()
    d = finding_to_dict(f)
    for key in ("package", "ecosystem", "severity", "title", "detail",
                "recommendation", "version", "source", "risk_score"):
        assert key in d


def test_finding_to_dict_risk_score():
    f = _make_finding(risk_score=14)
    d = finding_to_dict(f)
    assert d["risk_score"] == 14


# -- write_json_report ------------------------------------------------------

def test_write_json_report():
    findings = [_make_finding(), _make_finding(package="bad-lib", severity="medium")]
    tmpdir = tempfile.mkdtemp()
    path = os.path.join(tmpdir, "report.json")
    write_json_report(findings, path)

    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    assert "generated_at" in data
    assert data["total_findings"] == 2
    assert len(data["findings"]) == 2


def test_json_report_empty():
    tmpdir = tempfile.mkdtemp()
    path = os.path.join(tmpdir, "empty.json")
    write_json_report([], path)

    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    assert data["total_findings"] == 0
    assert data["findings"] == []


# -- write_markdown_report --------------------------------------------------

def test_write_markdown_report():
    findings = [_make_finding()]
    tmpdir = tempfile.mkdtemp()
    path = os.path.join(tmpdir, "report.md")
    write_markdown_report(findings, path)

    text = open(path, encoding="utf-8").read()
    assert "# dep-guard report" in text
    assert "evil-pkg" in text
    assert "high" in text.lower()
