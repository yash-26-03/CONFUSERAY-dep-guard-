import sys
import json
from collections import Counter
from datetime import datetime

from .scanner import Finding, SEVERITY_ORDER

_COLOURS = {
    "critical": "\033[91m",  # red
    "high": "\033[31m",      # bright-ish red
    "medium": "\033[33m",    # yellow
    "low": "\033[36m",       # cyan
    "info": "\033[90m",      # grey
}
_RESET = "\033[0m"
_BOLD = "\033[1m"

def _use_colour():
    return sys.stdout.isatty() and sys.platform != "win32"  # win console is iffy

def _c(text, code):
    if not _use_colour():
        return text
    return f"{code}{text}{_RESET}"

def _sort(findings):
    return sorted(findings,
                  key=lambda f: (-SEVERITY_ORDER.get(f.severity, 0), f.package))

def print_console(findings, scanned_files=0, total_deps=0):
    """Human-readable summary to stdout."""
    findings = _sort(findings)
    counts = Counter(f.severity for f in findings)

    print()
    print(_c(" dep-guard scan report ", _BOLD + "\033[44m"))
    print(_c("-" * 52, _COLOURS["info"]))
    print(f" files scanned : {scanned_files}")
    print(f" deps parsed   : {total_deps}")
    print(f" findings      : {len(findings)}"
          + (f"  (critical={counts.get('critical',0)}, "
             f"high={counts.get('high',0)}, medium={counts.get('medium',0)})"
             if findings else ""))
    print(_c("-" * 52, _COLOURS["info"]))

    if not findings:
        print(_c(" OK - no dependency-confusion exposure detected.", "\033[32m"))
        print()
        return

    for f in findings:
        sev = f.severity.upper()
        print(_c(f"[{sev:<8}] {f.package}  ({f.ecosystem})", _COLOURS.get(f.severity, "")))
        print(f"    {f.title}")
        print(f"    {f.detail}")
        if f.risk_score is not None:
            print(f"    risk   : {f.risk_score} pts")
        if f.source:
            print(f"    source : {f.source}"
                  + (f"   declared {f.version}" if f.version else ""))
        print(f"    fix    : {f.recommendation}")
        print()

    print(_c("-" * 52, _COLOURS["info"]))
    critical = counts.get("critical", 0)
    high = counts.get("high", 0)
    if critical or high:
        print(_c(f" {critical + high} high/critical finding(s) -- "
                 f"this build should fail.", _COLOURS["critical"]))
    print()


# -- file reports --
def finding_to_dict(f):
    return {
        "package": f.package,
        "ecosystem": f.ecosystem,
        "severity": f.severity,
        "title": f.title,
        "detail": f.detail,
        "recommendation": f.recommendation,
        "version": f.version,
        "source": f.source,
        "risk_score": f.risk_score,
    }

def build_report_payload(findings, meta=None):
    """Build the report dict -- reused by file writer and mongo saver."""
    return {
        "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": dict(Counter(f.severity for f in findings)),
        "total_findings": len(findings),
        "meta": meta or {},
        "findings": [finding_to_dict(f) for f in _sort(findings)],
    }

def write_json_report(findings, path, meta=None):
    payload = build_report_payload(findings, meta)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    return path

def write_markdown_report(findings, path, meta=None):
    findings = _sort(findings)
    lines = ["# dep-guard report", ""]
    lines.append(f"_Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}_")
    lines.append("")
    counts = Counter(f.severity for f in findings)
    if counts:
        lines.append("## Summary")
        for sev in ("critical", "high", "medium", "low", "info"):
            if sev in counts:
                lines.append(f"- **{sev}**: {counts[sev]}")
    else:
        lines.append("_No findings._")
    lines.append("")

    if findings:
        lines.append("## Findings")
        lines.append("")
        for f in findings:
            lines.append(f"### `{f.package}` ({f.ecosystem}) — {f.severity.upper()}")
            lines.append(f"- **{f.title}**")
            lines.append(f"- {f.detail}")
            if f.source:
                lines.append(f"- source: `{f.source}`"
                             + (f"  (declared `{f.version}`)" if f.version else ""))
            if f.risk_score is not None:
                lines.append(f"- risk score: **{f.risk_score}**")
            lines.append(f"- **fix**: {f.recommendation}")
            lines.append("")

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return path
