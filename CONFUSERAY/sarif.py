import json
import os

SARIF_SCHEMA = ("https://raw.githubusercontent.com/oasis-tcs/sarif-spec/"
                "main/sarif-2.1/schema/sarif-schema-2.1.0.json")

LEVEL_MAP = {
    "critical": "error",
    "high": "error",
    "medium": "warning",
    "low": "note",
    "info": "note",
}

def _rule_id(finding):
    
    title = finding.title.lower()
    if "typosquat" in title:
        return "TYP001"
    if finding.severity == "critical":
        return "DEP001"
    if finding.severity == "high":
        return "DEP002"
    if finding.severity == "medium":
        return "DEP003"
    return "DEP004"

def _build_result(finding):
    
    result = {
        "ruleId": _rule_id(finding),
        "level": LEVEL_MAP.get(finding.severity, "note"),
        "message": {"text": f"{finding.title}: {finding.detail}"},
    }
    if finding.source:
        result["locations"] = [{
            "physicalLocation": {
                "artifactLocation": {"uri": finding.source},
            },
        }]
    return result

def _collect_rules(findings):
    
    seen = {}
    for f in findings:
        rid = _rule_id(f)
        if rid not in seen:
            seen[rid] = {
                "id": rid,
                "shortDescription": {"text": f.title},
                "defaultConfiguration": {
                    "level": LEVEL_MAP.get(f.severity, "note"),
                },
            }
    return list(seen.values())

def write_sarif_report(findings, path, meta=None):
    
    sarif = {
        "$schema": SARIF_SCHEMA,
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "dep-guard",
                    "version": "0.5.0",
                    "informationUri": "https://github.com/dep-guard/dep-guard",
                    "rules": _collect_rules(findings),
                },
            },
            "results": [_build_result(f) for f in findings],
        }],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(sarif, fh, indent=2)
    return path
