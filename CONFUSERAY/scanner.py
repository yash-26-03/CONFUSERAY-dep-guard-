import os
import re

from .config import Config
from .registries import RegistryClient, RegistryError
from . import parsers
from .typosquat import find_typosquats
from .scorer import compute_risk_score


SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}

class Finding:
    def __init__(self, package, ecosystem, severity, title, detail,
                 recommendation, version=None, source=None, risk_score=None):
        self.package = package
        self.ecosystem = ecosystem
        self.severity = severity
        self.title = title
        self.detail = detail
        self.recommendation = recommendation
        self.version = version
        self.source = source  # which file this came from
        self.risk_score = risk_score

    def __repr__(self):
        return f"<Finding [{self.severity}] {self.package}>"


# -- version helpers --
# lightweight semver-ish comparator. good enough for a >= b on dotted numbers.
def _vtuple(version):
    if not version:
        return tuple()
    parts = re.findall(r"\d+", version)
    return tuple(int(p) for p in parts)


def version_is_higher(public_ver, requested_ver):
    
    if not public_ver:
        return False
    pub = _vtuple(public_ver)
    req = _vtuple(requested_ver)
    if not req:
        return True  # project asked for "any" -> public wins by default
    return pub > req


def is_pinned(spec):
    """A spec counts as 'pinned' only if it nails an exact version."""
    if not spec or spec in ("*", "any", "latest", "unspecified", "x"):
        return False
    # exact pins
    if spec.startswith("==") or re.match(r"^\d", spec) and " " not in spec.strip():
        # npm "1.2.3" exact, or "1.2.3" with no range operator
        return True
    # maven plain "1.2.3"
    if re.match(r"^\d+\.\d+", spec):
        return True
    return False


# -- registry config check --
def has_registry_protection(project_path, ecosystem):
    
    checks = {
        "npm": [".npmrc"],
        "pypi": ["pip.conf", ".pypirc", "pyproject.toml"],
        "maven": ["settings.xml"],
    }
    for fname in checks.get(ecosystem, []):
        if os.path.isfile(os.path.join(project_path, fname)):
            return True
    return False


# -- the scan --
def discover_files(root, ignore_dirs):
    """Yield dependency file paths under root, skipping noise dirs."""
    for dirpath, dirnames, filenames in os.walk(root):
        # mutate dirnames in place -> os.walk skips them
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]
        for fname in filenames:
            if parsers.detect_ecosystem(fname) is not None:
                yield os.path.join(dirpath, fname)


def _mitigation(ecosystem, package):
    if ecosystem == "npm":
        return (
            f"Pin {package} to the exact internal version in package.json and "
            f"force the scope to your private registry via .npmrc "
            f"('@scope:registry=https://npm.internal/...')."
        )
    if ecosystem == "pypi":
        return (
            f"Pin {package} to the internal build and restrict it to the private "
            f"index using --index-url/--extra-index-url ordering, or a pip.conf "
            f"that points private packages at an internal index only."
        )
    return (
        f"Pin {package} to the internal version and scope repository lookups to "
        f"the private Maven repo in settings.xml."
    )


def scan_project(project_path, config, client, progress=None, stats=None):
    
    findings = []

    if not os.path.isdir(project_path):
        raise FileNotFoundError(f"project path is not a directory: {project_path}")

    file_count = 0
    dep_count = 0

    for dep_file in discover_files(project_path, config.ignore_dirs):
        ecosystem = parsers.detect_ecosystem(dep_file)
        if ecosystem not in config.enabled:
            continue

        try:
            _, deps = parsers.parse_file(dep_file)
        except parsers.ParseError as exc:
            findings.append(Finding(
                package="-", ecosystem=ecosystem, severity="medium",
                title="Could not parse dependency file",
                detail=str(exc),
                recommendation="Fix the file so it can be scanned, or exclude it.",
                source=dep_file,
            ))
            continue

        file_count += 1
        dep_count += len(deps)
        if progress:
            progress(f"{ecosystem}: {os.path.relpath(dep_file, project_path)} "
                     f"({len(deps)} pkgs)")

        has_config = has_registry_protection(project_path, ecosystem)

        
        typosquats = find_typosquats(deps, config.internal_packages)

        for name, spec, _meta in deps:
            
            if config.warn_unpinned and not is_pinned(spec):
                findings.append(Finding(
                    package=name, ecosystem=ecosystem, severity="medium",
                    title="Unpinned dependency version",
                    detail=f"{name} is declared as '{spec}', which lets the "
                           f"resolver pick any matching public version.",
                    recommendation=f"Pin {name} to an exact version.",
                    version=spec, source=dep_file,
                ))

            # typosquatting check
            if name in typosquats:
                similar_to = typosquats[name]
                findings.append(Finding(
                    package=name, ecosystem=ecosystem, severity="high",
                    title="Possible typosquatting of internal package",
                    detail=f"{name} looks suspiciously similar to internal "
                           f"package '{similar_to}'.",
                    recommendation=f"Verify that '{name}' is the correct "
                                   f"package and not a typosquat of '{similar_to}'.",
                    version=spec, source=dep_file,
                ))

            
            if not config.is_internal(name):
                continue

            try:
                result = client.lookup(ecosystem, name)
            except RegistryError as exc:
                findings.append(Finding(
                    package=name, ecosystem=ecosystem, severity="medium",
                    title="Registry lookup failed",
                    detail=str(exc),
                    recommendation="Retry, or switch to --offline with a cache.",
                    version=spec, source=dep_file,
                ))
                continue

            if result and result["exists"]:
                is_typo = name in typosquats
                score_info = compute_risk_score(
                    name, ecosystem, config, result, spec,
                    has_registry_config=has_config, is_typosquat=is_typo,
                )
                severity = score_info["severity"]
                active = version_is_higher(result["latest_version"], spec)
                title = ("Dependency confusion: internal package found on PUBLIC "
                         "registry" + (" (higher version present)" if active else ""))
                detail = (
                    f"{name} is listed as internal, but a public {result['registry']} "
                    f"package exists (latest={result['latest_version']}, "
                    f"{len(result['versions'])} versions). "
                    f"Risk score: {score_info['score']}"
                )
                findings.append(Finding(
                    package=name, ecosystem=ecosystem, severity=severity,
                    title=title, detail=detail,
                    recommendation=_mitigation(ecosystem, name),
                    version=spec, source=dep_file,
                    risk_score=score_info["score"],
                ))

            
            if not has_config and config.is_internal(name):
                findings.append(Finding(
                    package=name, ecosystem=ecosystem, severity="medium",
                    title="No registry scope configuration found",
                    detail=f"No {ecosystem} registry config (e.g. .npmrc, pip.conf) "
                           f"detected in project root to protect internal packages.",
                    recommendation=f"Add a registry config file to scope '{name}' "
                                   f"to your private registry.",
                    version=spec, source=dep_file,
                ))

    if stats is not None:
        stats["files"] = file_count
        stats["deps"] = dep_count

    return findings


def should_fail(findings, fail_on):
    threshold = SEVERITY_ORDER.get(fail_on, SEVERITY_ORDER["high"])
    for f in findings:
        if SEVERITY_ORDER.get(f.severity, 0) >= threshold:
            return True
    return False
