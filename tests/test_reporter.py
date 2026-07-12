import os
import json
import pytest
import shutil
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


@pytest.fixture
def tmp_file():
    tmpdir = tempfile.mkdtemp()
    def _make(name):
        return os.path.join(tmpdir, name)
    yield _make
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.mark.parametrize("field", ["package", "ecosystem", "severity", "title", "detail",
                                     "recommendation", "version", "source", "risk_score"])
def test_finding_to_dict_has_fields(field):
    f = _make_finding()
    d = finding_to_dict(f)
    assert field in d

def test_finding_to_dict_risk_score():
    f = _make_finding(risk_score=14)
    d = finding_to_dict(f)
    assert d["risk_score"] == 14


@pytest.mark.parametrize("findings_count,total", [
    (2, 2),  # normal report
    (0, 0),  # empty report
])
def test_write_json_report(tmp_file, findings_count, total):
    findings = [_make_finding()] if findings_count > 0 else []
    if findings_count > 1:
        findings.append(_make_finding(package="bad-lib", severity="medium"))
    
    path = tmp_file("report.json")
    write_json_report(findings, path)

    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    assert "generated_at" in data
    assert data["total_findings"] == total
    assert len(data["findings"]) == total


def test_write_markdown_report(tmp_file):
    findings = [_make_finding()]
    path = tmp_file("report.md")
    write_markdown_report(findings, path)

    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    
    assert "# dep-guard report" in text
    assert "evil-pkg" in text
    assert "high" in text.lower()
