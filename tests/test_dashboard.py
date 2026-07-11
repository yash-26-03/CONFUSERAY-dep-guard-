"""Tests for the dashboard module -- server logic only, no HTTP."""
import json
import os
import tempfile

import pytest

from CONFUSERAY.dashboard.server import scan_reports_dir


# -- fixtures ---------------------------------------------------------------

@pytest.fixture
def reports_dir(tmp_path):
    """Create a temp dir with a couple of fake report files."""
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
    # a non-json file that should be ignored
    (tmp_path / "notes.txt").write_text("not a report")
    return tmp_path


@pytest.fixture
def empty_dir(tmp_path):
    return tmp_path / "empty"


# -- tests ------------------------------------------------------------------

class TestScanReportsDir:
    def test_finds_all_json(self, reports_dir):
        idx = scan_reports_dir(str(reports_dir))
        assert len(idx) == 2

    def test_index_has_expected_fields(self, reports_dir):
        idx = scan_reports_dir(str(reports_dir))
        for entry in idx:
            assert "file" in entry
            assert "generated_at" in entry
            assert "total_findings" in entry
            assert "summary" in entry
            assert "meta" in entry

    def test_sorted_by_filename(self, reports_dir):
        idx = scan_reports_dir(str(reports_dir))
        files = [e["file"] for e in idx]
        assert files == sorted(files)

    def test_skips_non_json(self, reports_dir):
        # notes.txt should not appear
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
        # first report should have passed=False
        first = next(e for e in idx if e["file"] == "scan_a.json")
        assert first["meta"]["passed"] is False
        assert first["meta"]["scanned_files"] == 2

        second = next(e for e in idx if e["file"] == "scan_b.json")
        assert second["meta"]["passed"] is True


class TestCLIDashboardSubcommand:
    """Just verify the subcommand is wired up in argparse."""

    def test_dashboard_subcommand_exists(self):
        from CONFUSERAY.cli import build_parser
        parser = build_parser()
        # should parse without error
        args = parser.parse_args(["dashboard", "--reports-dir", "/tmp/reports",
                                  "--port", "9999", "--no-open"])
        assert args.command == "dashboard"
        assert args.reports_dir == "/tmp/reports"
        assert args.port == 9999
        assert args.no_open is True

    def test_dashboard_defaults(self):
        from CONFUSERAY.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["dashboard"])
        assert args.reports_dir == "./reports"
        assert args.port == 8085
        assert args.no_open is False


class TestEnrichedMeta:
    """Verify the JSON report gets the extra meta fields."""

    def test_json_report_has_enriched_meta(self, reports_dir):
        """Check that sample reports have the enriched fields the dashboard needs."""
        idx = scan_reports_dir(str(reports_dir))
        for entry in idx:
            meta = entry["meta"]
            assert "passed" in meta
            assert "fail_on" in meta
            assert "scanned_files" in meta
            assert "total_deps" in meta
