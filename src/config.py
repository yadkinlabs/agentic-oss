"""
Loads agentic-oss.yml from the consuming repo.
Falls back to sensible defaults for every field.
"""

import os
import yaml

DEFAULTS = {
    "project": {
        "name": "",
        "description": "",
        "docs_url": "",
    },
    "labels": {
        "bug":       "bug",
        "feature":   "enhancement",
        "question":  "question",
        "duplicate": "duplicate",
        "spam":      "spam",
        "stale":     "stale",
        "handled":   "agentic-handled",
    },
    "stale": {
        "days_before_stale": 30,
        "days_before_close": 15,
        "exempt_labels":     ["pinned", "security"],
    },
    "faq":             [],
    "sensitive_paths": [],
    "digest": {
        "mention": "",   # e.g. "@yadkinlabs"
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(base.get(key), dict):
            result[key] = _deep_merge(base[key], val)
        else:
            result[key] = val
    return result


def load() -> dict:
    path = os.environ.get("CONFIG_PATH", ".github/agentic-oss.yml")
    try:
        with open(path) as f:
            user_config = yaml.safe_load(f) or {}
        return _deep_merge(DEFAULTS, user_config)
    except FileNotFoundError:
        return dict(DEFAULTS)
