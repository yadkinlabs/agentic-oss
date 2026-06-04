"""
Thin wrapper around the GitHub REST API.
Uses GITHUB_TOKEN from the environment — no extra credentials needed.
"""

import json
import os

import requests

_BASE = "https://api.github.com"
_REPO = os.environ.get("GITHUB_REPOSITORY", "")  # "owner/repo"
_TOKEN = os.environ.get("GITHUB_TOKEN", "")

_HEADERS = {
    "Authorization": f"Bearer {_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def _get(path: str, params: dict | None = None) -> dict | list:
    resp = requests.get(f"{_BASE}{path}", headers=_HEADERS, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _post(path: str, data: dict) -> dict:
    resp = requests.post(f"{_BASE}{path}", headers=_HEADERS, json=data, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _patch(path: str, data: dict) -> dict:
    resp = requests.patch(f"{_BASE}{path}", headers=_HEADERS, json=data, timeout=15)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Issues
# ---------------------------------------------------------------------------

def get_issue(number: int) -> dict:
    return _get(f"/repos/{_REPO}/issues/{number}")


def list_open_issues(since: str | None = None) -> list[dict]:
    params = {"state": "open", "per_page": 100}
    if since:
        params["since"] = since
    return _get(f"/repos/{_REPO}/issues", params=params)


def post_comment(number: int, body: str) -> dict:
    return _post(f"/repos/{_REPO}/issues/{number}/comments", {"body": body})


def add_labels(number: int, labels: list[str]) -> None:
    _post(f"/repos/{_REPO}/issues/{number}/labels", {"labels": labels})


def close_issue(number: int, reason: str = "completed") -> None:
    _patch(f"/repos/{_REPO}/issues/{number}", {"state": "closed", "state_reason": reason})


def create_issue(title: str, body: str, labels: list[str] | None = None) -> dict:
    data: dict = {"title": title, "body": body}
    if labels:
        data["labels"] = labels
    return _post(f"/repos/{_REPO}/issues", data)


def ensure_label_exists(name: str, color: str = "ededed", description: str = "") -> None:
    try:
        _get(f"/repos/{_REPO}/labels/{requests.utils.quote(name)}")
    except requests.HTTPError:
        try:
            _post(f"/repos/{_REPO}/labels", {"name": name, "color": color, "description": description})
        except requests.HTTPError:
            pass


# ---------------------------------------------------------------------------
# Pull requests
# ---------------------------------------------------------------------------

def get_pr(number: int) -> dict:
    return _get(f"/repos/{_REPO}/pulls/{number}")


def get_pr_files(number: int) -> list[dict]:
    return _get(f"/repos/{_REPO}/pulls/{number}/files")


def is_first_time_contributor(username: str) -> bool:
    """Returns True if this user has never had a merged PR in this repo."""
    try:
        prs = _get(f"/repos/{_REPO}/pulls", params={
            "state": "closed", "per_page": 10,
        })
        merged = [p for p in prs if p.get("merged_at") and p["user"]["login"] == username]
        return len(merged) == 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Activity log (for digest)
# ---------------------------------------------------------------------------

def list_issues_with_label(label: str, state: str = "closed") -> list[dict]:
    return _get(f"/repos/{_REPO}/issues", params={
        "labels": label,
        "state": state,
        "per_page": 100,
    })
