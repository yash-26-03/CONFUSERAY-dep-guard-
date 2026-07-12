import json
import os
import tempfile
import pytest

from CONFUSERAY.dashboard.server import scan_reports_dir


@pytest.fixture
def reports_dir(tmp_path):
    """Created a temp dir with fake report files."""
    r1 = {
        "generated_at": "2026-06-15T09:00:00Z",
        "summary": {"critical": 1, "high": 1},
        "total_findings": 2,
        "meta": {"project": "/tmp/proj", "passed": False, "fail_on": "high",
                 "scanned_files": 2, "total_deps": 30},
        "findings": [
            {"package": "foo", "ecosystem": "npm", "severity": "critical",
             "title": "bad", "detail": "very bad", "recommendation": "fix it",
             "version": "1.0", "source": "package.json", "risk_score": 14},
            {"package": "bar", "ecosystem": "pypi", "severity": "high",
             "title": "meh", "detail": "not great", "recommendation": "pin it",
             "version": "any", "source": "requirements.txt", "risk_score": 9},
        ],
    }
    r2 = {
        "generated_at": "2026-07-01T10:00:00Z",
        "summary": {"medium": 1},
        "total_findings": 1,
        "meta": {"project": "/tmp/proj", "passed": True, "fail_on": "high",
                 "scanned_files": 2, "total_deps": 28},
        "findings": [
            {"package": "baz", "ecosystem": "npm", "severity": "medium",
             "title": "ok", "detail": "just a warning", "recommendation": "check it",
             "version": "^1.0", "source": "package.json", "risk_score": None},
        ],
    }
    (tmp_path / "scan_a.json").write_text(json.dumps(r1))
    (tmp_path / "scan_b.json").write_text(json.dumps(r2))
    (tmp_path / "notes.txt").write_text("not a report")     
    return tmp_path


@pytest.fixture
def empty_dir(tmp_path):
    return tmp_path / "empty"


class TestScanReportsDir:
    def test_finds_all_json(self, reports_dir):
        idx = scan_reports_dir(str(reports_dir))
        assert len(idx) == 2

    @pytest.mark.parametrize("field", ["file", "generated_at", "total_findings", "summary", "meta"])
    def test_index_has_expected_fields(self, reports_dir, field):
        idx = scan_reports_dir(str(reports_dir))
        assert all(field in entry for entry in idx)

    def test_sorted_by_filename(self, reports_dir):
        idx = scan_reports_dir(str(reports_dir))
        files = [e["file"] for e in idx]
        assert files == sorted(files)

    def test_skips_non_json(self, reports_dir):
        idx = scan_reports_dir(str(reports_dir))
        files = [e["file"] for e in idx]
        assert "notes.txt" not in files

    def test_skips_bad_json(self, reports_dir):
        (reports_dir / "broken.json").write_text("{invalid json!!")
        idx = scan_reports_dir(str(reports_dir))
        files = [e["file"] for e in idx]
        assert "broken.json" not in files
        assert len(idx) == 2  # still finds the two good ones

    def test_empty_dir(self, tmp_path):
        idx = scan_reports_dir(str(tmp_path))
        assert idx == []

    def test_meta_fields_preserved(self, reports_dir):
        idx = scan_reports_dir(str(reports_dir))
        
        first = next(e for e in idx if e["file"] == "scan_a.json")
        assert first["meta"]["passed"] is False
        assert first["meta"]["scanned_files"] == 2

        second = next(e for e in idx if e["file"] == "scan_b.json")
        assert second["meta"]["passed"] is True


class TestCLIDashboardSubcommand:

    @pytest.mark.parametrize("cmd_args,expected", [
        (["dashboard", "--reports-dir", "/tmp/reports", "--port", "9999", "--no-open"],
         {"reports_dir": "/tmp/reports", "port": 9999, "no_open": True}),
        (["dashboard"],
         {"reports_dir": "./reports", "port": 8085, "no_open": False}),
    ])
    def test_dashboard_command(self, cmd_args, expected):
        from CONFUSERAY.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(cmd_args)
        assert args.command == "dashboard"
        for key, value in expected.items():
            assert getattr(args, key) == value


class TestEnrichedMeta:

    @pytest.mark.parametrize("field", ["passed", "fail_on", "scanned_files", "total_deps"])
    def test_json_report_has_enriched_meta(self, reports_dir, field):
        
        idx = scan_reports_dir(str(reports_dir))
        assert all(field in entry["meta"] for entry in idx)
