import json
import re
import os
import xml.etree.ElementTree as ET

class ParseError(Exception):
    pass

# ---------------------------------------------------------------------------
# npm / package.json
# ---------------------------------------------------------------------------
NPM_DEP_KEYS = (
    "dependencies",
    "devDependencies",
    "peerDependencies",
    "optionalDependencies",
)

def parse_package_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ParseError(f"{path}: invalid package.json -> {exc}")

    out = []
    if not isinstance(data, dict):
        raise ParseError(f"{path}: package.json root is not an object")

    for key in NPM_DEP_KEYS:
        deps = data.get(key) or {}
        if not isinstance(deps, dict):
            continue
        for name, spec in deps.items():
            if not isinstance(name, str):
                continue
            # things like "file:./local" or "git+https://..." are not registry deps
            spec_str = str(spec) if spec else ""
            if spec_str.startswith(("file:", "git+", "link:", "workspace:")):
                continue
            out.append((name, spec_str or "*", key))
    return out

# ---------------------------------------------------------------------------
# python / requirements.txt
# ---------------------------------------------------------------------------
_REQ_RE = re.compile(
    r"^\s*"
    r"(?P<name>[A-Za-z0-9_.\-]+\s*\[[^\]]*\]"   # name[extras] or name
    r"|[A-Za-z0-9_.\-]+)"
    r"\s*(?P<spec>[^;#]*)"                       # version specifiers
    r"\s*(;.*)?$"                                # env marker, ignored
)

def parse_requirements(path):
    out = []
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            # strip inline comment
            if " #" in line:
                line = line.split(" #", 1)[0].strip()
            # options / non-package lines -> skip quietly
            if line.startswith(("-", "git+", "http://", "https://")):
                continue
            m = _REQ_RE.match(line)
            if not m:
                continue
            name = m.group("name").strip()
            spec = m.group("spec").strip()
            # drop extras: foo[bar]==1.0  -> foo==1.0
            name = re.sub(r"\[[^\]]*\]", "", name).strip()
            out.append((name, spec or "any", str(lineno)))
    return out

# ---------------------------------------------------------------------------
# maven / pom.xml
# ---------------------------------------------------------------------------
def _strip_ns(tag):
    
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag

def parse_pom_xml(path):
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        raise ParseError(f"{path}: could not parse xml -> {exc}")

    root = tree.getroot()
    props = {}
    props_node = root.find(".//{*}properties")
    if props_node is not None:
        for child in props_node:
            props[_strip_ns(child.tag)] = (child.text or "").strip()

    out = []
    # both direct deps and managed deps
    for dep in root.findall(".//{*}dependency"):
        fields = {}
        for child in dep:
            fields[_strip_ns(child.tag)] = (child.text or "").strip()

        gid = fields.get("groupId", "")
        aid = fields.get("artifactId", "")
        ver = fields.get("version", "").strip()

        if not gid or not aid:
            continue
        if "scope" in fields and fields["scope"] == "test":
            pass  

        if ver.startswith("${") and ver.endswith("}"):
            key = ver[2:-1]
            ver = props.get(key, ver)

        # maven coord stored as "groupId:artifactId", version separate
        coord = f"{gid}:{aid}"
        out.append((coord, ver or "unspecified", gid))

    return out

# ---------------------------------------------------------------------------
# dispatcher
# ---------------------------------------------------------------------------
FILENAME_MAP = {
    "package.json": ("npm", parse_package_json),
    "requirements.txt": ("pypi", parse_requirements),
    "pom.xml": ("maven", parse_pom_xml),
}

def detect_ecosystem(filename):
    base = os.path.basename(filename)
    # requirements style: requirements-dev.txt, requirements/base.txt etc.
    if base.startswith("requirements") and base.endswith(".txt"):
        return "pypi"
    info = FILENAME_MAP.get(base)
    return info[0] if info else None

def parse_file(path):
    eco = detect_ecosystem(path)
    if eco is None:
        return None, []
    _, fn = FILENAME_MAP.get(os.path.basename(path)) or (None, None)

    # requirements-*.txt isn't in FILENAME_MAP directly
    if fn is None and eco == "pypi":
        fn = parse_requirements
    if fn is None:
        return eco, []

    return eco, fn(path)

