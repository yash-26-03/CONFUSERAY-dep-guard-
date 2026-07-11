import sys
sys.dont_write_bytecode = True

"""
dep-guard: a small static scanner for dependency confusion vulnerabilities.

It reads dependency files (package.json, requirements.txt, pom.xml), checks the
declared packages against public registries (npm / PyPI / Maven Central) and
flags any "internal" package name that also happens to exist publicly -- which
is exactly the setup a dependency-confusion attack relies on.

Run with:  python -m depguard scan ./my-project --config depguard.config.json
"""

__version__ = "0.6.0"
__author__ = "HCIC / dep-guard"

EXIT_CLEAN = 0
EXIT_FINDINGS = 1
EXIT_ERROR = 2
