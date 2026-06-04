"""
Triage handler — runs on issue.opened and pull_request.opened events.
"""

import json
import logging
import os

import claude_client
import config as cfg
import github_client as gh

log = logging.getLogger(__name__)

_VALID_CLASSIFICATIONS = {"bug", "feature", "question", "duplicate", "spam", "unclear"}
_VALID_ACTIONS = {
    "label_and_acknowledge", "reply_and_close",
    "close_duplicate", "close_spam", "ask_clarification",
}
_VALID_LABELS_KEYS = {"bug", "feature", "question", "duplicate", "spam", "stale", "handled"}


def _validate_triage_result(result: dict, config: dict) -> dict:
    """
    Reject or sanitize any triage result that doesn't match the allowed schema.
    If validation fails, fall back to closing as spam — safe default.
    """
    allowed_label_names = set(config["labels"].values())

    if result.get("classification") not in _VALID_CLASSIFICATIONS:
        log.warning("Invalid classification '%s' — falling back to spam", result.get("classification"))
        return {"classification": "spam", "action": "close_spam", "comment": "", "labels": [], "reasoning": "validation failure"}

    if result.get("action") not in _VALID_ACTIONS:
        log.warning("Invalid action '%s' — falling back to spam", result.get("action"))
        return {"classification": "spam", "action": "close_spam", "comment": "", "labels": [], "reasoning": "validation failure"}

    # Strip any labels Claude invented that aren't in our allowed set
    raw_labels = result.get("labels") or []
    if not isinstance(raw_labels, list):
        raw_labels = []
    result["labels"] = [l for l in raw_labels if l in allowed_label_names]

    # Truncate comment to prevent runaway output
    comment = result.get("comment") or ""
    result["comment"] = comment[:1000]

    return result


def _ensure_labels(config: dict) -> None:
    labels = config["labels"]
    colors = {
        "bug":       "d73a4a",
        "feature":   "a2eeef",
        "question":  "d876e3",
        "duplicate": "cfd3d7",
        "spam":      "e4e669",
        "stale":     "fef2c0",
        "handled":   "0075ca",
    }
    descriptions = {
        "handled": "Handled automatically by agentic-oss",
        "stale":   "No recent activity",
    }
    for key, name in labels.items():
        gh.ensure_label_exists(name, colors.get(key, "ededed"), descriptions.get(key, ""))


def handle_issue(event: dict, config: dict) -> None:
    issue = event["issue"]
    number = issue["number"]
    labels_cfg = config["labels"]

    log.info("Triaging issue #%d: %s", number, issue["title"])

    result = _validate_triage_result(claude_client.triage_issue(issue, config), config)
    log.info("Classification: %s — action: %s", result["classification"], result["action"])

    action = result["action"]
    labels_to_add = [labels_cfg["handled"]]

    if action == "label_and_acknowledge":
        cls = result["classification"]
        if cls in labels_cfg:
            labels_to_add.append(labels_cfg[cls])
        gh.add_labels(number, labels_to_add)
        gh.post_comment(number, result["comment"])

    elif action == "reply_and_close":
        labels_to_add.append(labels_cfg.get("question", "question"))
        gh.add_labels(number, labels_to_add)
        gh.post_comment(number, result["comment"])
        gh.close_issue(number, reason="completed")

    elif action == "close_duplicate":
        labels_to_add.append(labels_cfg.get("duplicate", "duplicate"))
        gh.add_labels(number, labels_to_add)
        gh.post_comment(number, result["comment"])
        gh.close_issue(number, reason="duplicate")

    elif action == "close_spam":
        labels_to_add.append(labels_cfg.get("spam", "spam"))
        gh.add_labels(number, labels_to_add)
        gh.close_issue(number, reason="not_planned")

    elif action == "ask_clarification":
        gh.add_labels(number, labels_to_add)
        gh.post_comment(number, result["comment"])

    log.info("Done — issue #%d handled", number)


def handle_pr(event: dict, config: dict) -> None:
    pr = event["pull_request"]
    number = pr["number"]
    username = pr["user"]["login"]

    log.info("Reviewing PR #%d: %s", number, pr["title"])

    files = gh.get_pr_files(number)
    is_first_timer = gh.is_first_time_contributor(username)

    result = claude_client.review_pr(pr, files, is_first_timer, config)
    log.info("PR summary generated, flags: %s", result.get("flags"))

    gh.add_labels(number, [config["labels"]["handled"]])
    gh.post_comment(number, result["comment"])

    log.info("Done — PR #%d reviewed", number)


def run(event_name: str, event: dict, config: dict) -> None:
    _ensure_labels(config)

    if event_name == "issues":
        action = event.get("action")
        if action in ("opened", "reopened"):
            handle_issue(event, config)

    elif event_name == "pull_request":
        action = event.get("action")
        if action in ("opened", "reopened", "ready_for_review"):
            handle_pr(event, config)

    else:
        log.info("Unhandled event: %s", event_name)
