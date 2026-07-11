"""Tiny HTTP server for the scan-history dashboard.

No deps beyond stdlib (pymongo only needed when --mongo-uri is used).
Run via: depguard dashboard --reports-dir ./reports
"""
import http.server
import json
import os
import glob
import webbrowser


def scan_reports_dir(reports_dir):
    """Build a quick index of every JSON report in the directory."""
    out = []
    for path in sorted(glob.glob(os.path.join(reports_dir, "*.json"))):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            out.append({
                "file": os.path.basename(path),
                "generated_at": data.get("generated_at", ""),
                "total_findings": data.get("total_findings", 0),
                "summary": data.get("summary", {}),
                "meta": data.get("meta", {}),
            })
        except (json.JSONDecodeError, OSError):
            pass
    return out


class _Handler(http.server.BaseHTTPRequestHandler):
    """
    /              -> dashboard html
    /api/reports   -> index of all reports
    /api/report/X  -> single report json
    """

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._serve_dashboard()
        elif self.path == "/api/reports":
            self._serve_index()
        elif self.path.startswith("/api/report/"):
            self._serve_report()
        else:
            self.send_error(404)

    def _serve_dashboard(self):
        html = os.path.join(self.server.dashboard_dir, "dashboard.html")
        self._send_file(html, "text/html; charset=utf-8")

    def _serve_index(self):
        if self.server.db is not None:
            from .db import get_reports_index
            idx = get_reports_index(self.server.db)
        else:
            idx = scan_reports_dir(self.server.reports_dir)
        self._send_json(idx)

    def _serve_report(self):
        report_id = os.path.basename(self.path)

        if self.server.db is not None:
            from .db import get_report
            doc = get_report(self.server.db, report_id)
            if not doc:
                self.send_error(404)
                return
            self._send_json(doc)
            return

        # filesystem mode — report_id is a filename
        if not report_id.endswith(".json"):
            self.send_error(400)
            return
        fpath = os.path.join(self.server.reports_dir, report_id)
        if not os.path.realpath(fpath).startswith(
            os.path.realpath(self.server.reports_dir)
        ):
            self.send_error(403)
            return
        self._send_file(fpath, "application/json")

    def _send_json(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path, content_type):
        try:
            with open(path, "rb") as f:
                body = f.read()
        except FileNotFoundError:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # suppress request logs


def serve(reports_dir=None, port=8085, open_browser=True, mongo_uri=None):
    """Fire up the dashboard. Blocks until Ctrl+C."""
    db = None
    if mongo_uri:
        from .db import get_db
        db = get_db(mongo_uri)
        try:
            db.client.admin.command("ping")
        except Exception as exc:
            print(f"error: can't reach MongoDB: {exc}")
            return 1
        print("  connected to MongoDB")

    if not mongo_uri:
        reports_dir = os.path.abspath(reports_dir or "./reports")
        if not os.path.isdir(reports_dir):
            print(f"error: not a directory: {reports_dir}")
            return 1

    srv = http.server.HTTPServer(("127.0.0.1", port), _Handler)
    srv.reports_dir = reports_dir
    srv.dashboard_dir = os.path.dirname(os.path.abspath(__file__))
    srv.db = db

    url = f"http://127.0.0.1:{port}"
    print(f"  dep-guard dashboard  ->  {url}")
    if reports_dir and not mongo_uri:
        print(f"  reports: {reports_dir}")
    print("  ctrl+c to stop\n")

    if open_browser:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nbye.")
    return 0
