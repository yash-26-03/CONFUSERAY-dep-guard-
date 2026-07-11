import json
import urllib.parse

try:
    import requests
except ImportError:  # pragma: no cover - requests is in requirements.txt
    requests = None

NPM_URL = "https://registry.npmjs.org"
PYPI_URL = "https://pypi.org/pypi"
MAVEN_URL = "https://search.maven.org/solrsearch/select"
TIMEOUT = 8  

class RegistryError(Exception):
    pass

def normalize(exists, latest, versions, source):
    return {
        "exists": exists,
        "latest_version": latest,
        "versions": versions or [],
        "registry": source,
    }

class RegistryClient:
    def __init__(self, offline=False, cache_path=None, timeout=TIMEOUT):
        self.offline = offline
        self.cache_path = cache_path
        self.timeout = timeout
        self._cache = None
        if cache_path:
            try:
                with open(cache_path, "r", encoding="utf-8") as fh:
                    self._cache = json.load(fh)
            except (OSError, json.JSONDecodeError):
                self._cache = {}

        if not offline and requests is None:
            raise RegistryError(
                "live mode needs the 'requests' package (pip install requests)"
            )

    # -- public api --
    def lookup(self, ecosystem, name):
        if ecosystem == "npm":
            return self._npm(name)
        if ecosystem == "pypi":
            return self._pypi(name)
        if ecosystem == "maven":
            return self._maven(name)
        return None

    # -- npm --
    def _npm(self, name):
        if self.offline:
            return self._cache_lookup("npm", name)
        
        url = f"{NPM_URL}/{urllib.parse.quote(name, safe='@')}"
        resp = self._get(url)
        if resp is None:
            return normalize(False, None, [], "npm")
        latest = resp.get("dist-tags", {}).get("latest")
        versions = list(resp.get("versions", {}).keys())
        return normalize(True, latest, versions, "npm")

    # -- pypi --
    def _pypi(self, name):
        if self.offline:
            return self._cache_lookup("pypi", name.lower())
        url = f"{PYPI_URL}/{name}/json"
        resp = self._get(url)
        if resp is None:
            return normalize(False, None, [], "pypi")
        info = resp.get("info", {})
        latest = info.get("version")
        versions = list(resp.get("releases", {}).keys())
        return normalize(True, latest, versions, "pypi")

    # -- maven central --
    def _maven(self, coord):
        if self.offline:
            return self._cache_lookup("maven", coord)
        try:
            gid, aid = coord.split(":", 1)
        except ValueError:
            return normalize(False, None, [], "maven")
        params = {
            "q": f'g:"{gid}" AND a:"{aid}"',
            "core": "gav",
            "rows": "20",
            "wt": "json",
        }
        resp = self._get(MAVEN_URL, params=params)
        if resp is None:
            return normalize(False, None, [], "maven")
        docs = resp.get("response", {}).get("docs", [])
        if not docs:
            return normalize(False, None, [], "maven")
        versions = [d.get("v") for d in docs if d.get("v")]
        latest = versions[0] if versions else None
        return normalize(True, latest, versions, "maven")

    # -- helpers --
    def _get(self, url, params=None):
        try:
            r = requests.get(url, params=params, timeout=self.timeout,
                             headers={"Accept": "application/json"})
        except requests.RequestException as exc:
            # network blip -> bubble up, caller records a medium finding
            raise RegistryError(f"registry request failed: {exc}")
        if r.status_code == 404:
            return None
        if r.status_code != 200:
            raise RegistryError(f"{url} returned HTTP {r.status_code}")
        try:
            return r.json()
        except ValueError:
            raise RegistryError(f"{url} returned non-json body")

    def _cache_lookup(self, ecosystem, name):
        bucket = self._cache.get(ecosystem, {}) if self._cache else {}
        entry = bucket.get(name)
        if not entry:
            return normalize(False, None, [], ecosystem)
        return normalize(
            entry.get("exists", False),
            entry.get("latest_version"),
            entry.get("versions", []),
            ecosystem,
        )
