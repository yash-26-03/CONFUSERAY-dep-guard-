import json
import pytest

try:
    from pymongo import MongoClient
    HAS_PYMONGO = True
except ImportError:
    HAS_PYMONGO = False

from CONFUSERAY.dashboard.db import get_db, save_report, get_reports_index, get_report

pytestmark = pytest.mark.skipif(not HAS_PYMONGO, reason="pymongo not installed")

TEST_DB_NAME = "depguard_test"


@pytest.fixture
def db():
    client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
    try:
        client.admin.command("ping")
    except Exception:
        pytest.skip("MongoDB not running at localhost:27017")
    test_db = client[TEST_DB_NAME]
    yield test_db
    client.drop_database(TEST_DB_NAME)
    client.close()


SAMPLE_REPORT = {
    "generated_at": "2026-07-08T10:00:00Z",
    "summary": {"critical": 1, "high": 1},
    "total_findings": 2,
    "meta": {
        "project": "/tmp/testproj",
        "config": "test.json",
        "scanned_files": 1,
        "total_deps": 10,
        "passed": False,
        "fail_on": "high",
    },
    "findings": [
        {
            "package": "evil-pkg",
            "ecosystem": "npm",
            "severity": "critical",
            "title": "Dependency confusion",
            "detail": "found on public registry",
            "recommendation": "pin it",
            "version": "^1.0",
            "source": "package.json",
            "risk_score": 14,
        },
        {
            "package": "sus-lib",
            "ecosystem": "pypi",
            "severity": "high",
            "title": "Typosquat",
            "detail": "looks like internal-lib",
            "recommendation": "verify name",
            "version": "any",
            "source": "requirements.txt",
            "risk_score": 9,
        },
    ],
}


class TestSaveAndRetrieve:
    def test_save_returns_id(self, db):
        rid = save_report(db, SAMPLE_REPORT)
        assert rid  
        assert len(rid) == 24  # ObjectId hex length

    def test_index_after_save(self, db):
        save_report(db, SAMPLE_REPORT)
        idx = get_reports_index(db)
        assert len(idx) == 1
        entry = idx[0]
        assert entry["generated_at"] == "2026-07-08T10:00:00Z"
        assert entry["total_findings"] == 2
        assert entry["summary"]["critical"] == 1
        assert entry["meta"]["passed"] is False

    def test_get_report_by_id(self, db):
        rid = save_report(db, SAMPLE_REPORT)
        doc = get_report(db, rid)
        assert doc is not None
        assert doc["total_findings"] == 2
        assert len(doc["findings"]) == 2
        assert doc["findings"][0]["package"] == "evil-pkg"

    @pytest.mark.parametrize("report_id", ["not_a_valid_id", "000000000000000000000000"])
    def test_get_report_not_found(self, db, report_id):
        doc = get_report(db, report_id)
        assert doc is None

    def test_multiple_reports(self, db):
        r2 = dict(SAMPLE_REPORT)
        r2["generated_at"] = "2026-07-09T10:00:00Z"
        r2["total_findings"] = 0
        r2["summary"] = {}
        save_report(db, SAMPLE_REPORT)
        save_report(db, r2)
        idx = get_reports_index(db)
        assert len(idx) == 2
        # sorted oldest first
        assert idx[0]["generated_at"] == "2026-07-08T10:00:00Z"
        assert idx[1]["generated_at"] == "2026-07-09T10:00:00Z"

    def test_index_file_field_is_objectid_string(self, db):
        save_report(db, SAMPLE_REPORT)
        idx = get_reports_index(db)
        assert len(idx[0]["file"]) == 24


class TestCLIMongoArgs:
    @pytest.mark.parametrize("cmd", [
        ["scan", ".", "-c", "test.json", "--mongo-uri", "mongodb://localhost:27017/"],
        ["dashboard", "--mongo-uri", "mongodb://localhost:27017/"],
    ])
    def test_mongo_uri_arg(self, cmd):
        from CONFUSERAY.cli import build_parser
        p = build_parser()
        args = p.parse_args(cmd)
        assert args.mongo_uri == "mongodb://localhost:27017/"

    def test_mongo_uri_defaults_local(self):
        from CONFUSERAY.cli import build_parser
        p = build_parser()
        args = p.parse_args(["scan", ".", "-c", "test.json"])
        assert args.mongo_uri == "mongodb://localhost:27017/"
