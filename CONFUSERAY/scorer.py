import re

SEVERITY_LEVELS = [
    (12, "critical"),
    (8, "high"),
    (4, "medium"),
    (0, "low"),
]


def score_to_severity(score):  
    for threshold, label in SEVERITY_LEVELS:
        if score >= threshold:
            return label
    return "low"


def _vtuple(version):
    if not version:
        return tuple()
    return tuple(int(p) for p in re.findall(r"\d+", version))

def _version_higher(public_ver, requested_ver):
    
    if not public_ver:
        return False
    pub = _vtuple(public_ver)
    req = _vtuple(requested_ver)
    if not req:
        return True
    return pub > req


def compute_risk_score(name, ecosystem, config, registry_result,
                       requested_version, has_registry_config=False,
                       is_typosquat=False):
    
    score = 0
    factors = []

    if config.is_internal(name):
        score += 3
        factors.append("+3: package in internal scope")

    if registry_result.get("exists"):
        score += 4
        factors.append("+4: public package exists on registry")

        latest = registry_result.get("latest_version")
        if latest and requested_version:
            if _version_higher(latest, requested_version):
                score += 5
                factors.append("+5: public version higher than declared")

    if not has_registry_config:
        score += 2
        factors.append("+2: no registry config protection")

    if is_typosquat:
        score += 4
        factors.append("+4: typosquatting detected")

    return {
        "score": score,
        "severity": score_to_severity(score),
        "factors": factors,
    }

