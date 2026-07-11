import argparse
import sys
import os

from . import __version__, EXIT_CLEAN, EXIT_FINDINGS, EXIT_ERROR
from .config import load_config, ConfigError
from .registries import RegistryClient, RegistryError
from .scanner import scan_project, should_fail
from .reporter import (print_console, write_json_report, write_markdown_report,
                       build_report_payload)
from .sarif import write_sarif_report

def build_parser():
    p = argparse.ArgumentParser(
        prog="depguard",
        description=("Static scanner for dependency-confusion attacks. Reads "
                     "package.json / requirements.txt / pom.xml and flags "
                     "internal packages that also exist on a public registry."),
    )
    p.add_argument("--version", action="version", version=f"dep-guard {__version__}")

    sub = p.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="scan a project directory")
    scan.add_argument("path", help="project root to scan")
    scan.add_argument("-c", "--config", required=True,
                      help="internal-package config (json)")
    scan.add_argument("--offline", action="store_true",
                      help="use local registry cache instead of real HTTP")
    scan.add_argument("--cache", default=None,
                      help="path to registry cache json (implies --offline if set)")
    scan.add_argument("--report-json", default=None,
                      help="write findings to this json file")
    scan.add_argument("--report-md", default=None,
                      help="write findings to this markdown file")
    scan.add_argument("--report-sarif", default=None,
                      help="write findings in SARIF 2.1 format (GitHub Code Scanning)")
    scan.add_argument("--fail-on", default=None,
                      help="override fail severity (critical|high|medium|low)")
    scan.add_argument("--warn-unpinned", action="store_true",
                      help="also report unpinned dependency versions")
    scan.add_argument("--mongo-uri", default="mongodb://localhost:27017/",
                      help="save report to MongoDB (default: mongodb://localhost:27017/)")
    scan.add_argument("-q", "--quiet", action="store_true",
                      help="less progress output")

    sub.add_parser("init", help="print a starter config to stdout")

    dash = sub.add_parser("dashboard", help="open scan-history dashboard")
    dash.add_argument("--reports-dir", default="./reports",
                      help="directory of JSON report files (default: ./reports)")
    dash.add_argument("--port", type=int, default=8085,
                      help="port to serve on (default: 8085)")
    dash.add_argument("--no-open", action="store_true",
                      help="don't auto-open browser")
    dash.add_argument("--mongo-uri", default="mongodb://localhost:27017/",
                      help="read reports from MongoDB (default: mongodb://localhost:27017/)")
    return p

STARTER_CONFIG = """{
  "internal_scopes": ["@yourcompany"],
  "internal_packages": [
    "yourcompany-utils",
    "yourcompany-auth"
  ],
  "ecosystems": ["npm", "pypi", "maven"],
  "fail_on": "high",
  "warn_unpinned": false
}
"""

def _progress(msg):
    print(f"  ... {msg}", file=sys.stderr)

def cmd_scan(args):
    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    if args.fail_on:
        config.fail_on = args.fail_on.lower()
    if args.warn_unpinned:
        config.warn_unpinned = True

    offline = args.offline or (args.cache is not None)
    try:
        client = RegistryClient(offline=offline, cache_path=args.cache)
    except RegistryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    progress = None if args.quiet else _progress

    try:
        stats = {}
        findings = scan_project(args.path, config, client, progress=progress,
                                stats=stats)
    except (FileNotFoundError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    passed = not should_fail(findings, config.fail_on)
    meta = {
        "project": os.path.abspath(args.path),
        "config": args.config,
        "scanned_files": stats.get("files", 0),
        "total_deps": stats.get("deps", 0),
        "passed": passed,
        "fail_on": config.fail_on,
    }
    if args.report_json:
        write_json_report(findings, args.report_json, meta=meta)
        _progress(f"wrote {args.report_json}")
    if args.report_md:
        write_markdown_report(findings, args.report_md, meta=meta)
        _progress(f"wrote {args.report_md}")
    if args.report_sarif:
        write_sarif_report(findings, args.report_sarif, meta=meta)
        _progress(f"wrote {args.report_sarif}")
    if args.mongo_uri:
        try:
            from .dashboard.db import get_db, save_report
            payload = build_report_payload(findings, meta=meta)
            db = get_db(args.mongo_uri)
            save_report(db, payload)
            _progress("saved to MongoDB")
        except Exception as exc:
            print(f"warning: failed to save to MongoDB ({args.mongo_uri}): {exc}", file=sys.stderr)

    print_console(findings, scanned_files=stats.get("files", 0),
                  total_deps=stats.get("deps", 0))

    if not passed:
        return EXIT_FINDINGS
    return EXIT_CLEAN

def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        print(STARTER_CONFIG)
        return EXIT_CLEAN
    if args.command == "scan":
        return cmd_scan(args)
    if args.command == "dashboard":
        from .dashboard.server import serve
        return serve(reports_dir=args.reports_dir, port=args.port,
                     open_browser=not args.no_open,
                     mongo_uri=args.mongo_uri)

    parser.print_help()
    return EXIT_ERROR

if __name__ == "__main__":
    sys.exit(main())
