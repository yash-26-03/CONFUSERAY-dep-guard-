#!/usr/bin/env bash
# pre-commit hook for dep-guard
# Install: cp scripts/pre-commit-hook.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit

set -e

echo "[dep-guard] scanning dependencies..."

if ! command -v depguard &> /dev/null; then
    echo "[dep-guard] not installed, skipping (pip install -e .)"
    exit 0
fi

depguard scan . --config depguard.config.json --fail-on high --quiet
STATUS=$?

if [ $STATUS -ne 0 ]; then
    echo "[dep-guard] dependency confusion risk detected! Fix before committing."
    exit 1
fi

echo "[dep-guard] clean."
