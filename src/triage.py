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

    result = claude_client.triage_issue(issue, config)
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
