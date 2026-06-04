"""
Stale handler — runs on a daily cron schedule.
Warns issues that have been inactive, closes ones that have been warned and ignored.
"""

import logging
from datetime import datetime, timedelta, timezone

import config as cfg
import github_client as gh

log = logging.getLogger(__name__)

_STALE_COMMENT = (
    "This issue has been automatically marked as stale because it has had no activity "
    "for {days} days. It will be closed in {close_days} days if no further activity occurs. "
    "If this is still relevant, please leave a comment or update the issue. Thank you!"
)

_CLOSE_COMMENT = (
    "This issue has been automatically closed due to inactivity. "
    "If this is still relevant, please open a new issue with updated information."
)


def run(config: dict) -> None:
    stale_cfg = config["stale"]
    days_before_stale = int(stale_cfg.get("days_before_stale", 30))
    days_before_close = int(stale_cfg.get("days_before_close", 15))
    exempt_labels = set(stale_cfg.get("exempt_labels", []))
    stale_label = config["labels"]["stale"]
    handled_label = config["labels"]["handled"]

    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(days=days_before_stale)
    close_cutoff = now - timedelta(days=days_before_stale + days_before_close)

    issues = gh.list_open_issues()
    log.info("Checking %d open issues for staleness", len(issues))

    for issue in issues:
        # Skip PRs (GitHub returns them in issues list)
        if "pull_request" in issue:
            continue

        issue_labels = {lbl["name"] for lbl in issue.get("labels", [])}

        # Skip exempt issues
        if issue_labels & exempt_labels:
            continue

        updated_at = datetime.fromisoformat(issue["updated_at"].replace("Z", "+00:00"))
        number = issue["number"]

        if stale_label in issue_labels:
            # Already stale — check if it's time to close
            if updated_at < close_cutoff:
                log.info("Closing stale issue #%d", number)
                gh.add_labels(number, [handled_label])
                gh.post_comment(number, _CLOSE_COMMENT)
                gh.close_issue(number, reason="not_planned")
        else:
            # Not yet stale — check if it should be warned
            if updated_at < stale_cutoff:
                log.info("Marking issue #%d as stale", number)
                gh.add_labels(number, [stale_label])
                gh.post_comment(number, _STALE_COMMENT.format(
                    days=days_before_stale,
                    close_days=days_before_close,
                ))
