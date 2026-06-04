"""
Digest handler — runs on a daily cron schedule.
Creates a summary issue of everything agentic-oss handled in the last 24 hours.
"""

import logging
from datetime import datetime, timedelta, timezone

import claude_client
import config as cfg
import github_client as gh

log = logging.getLogger(__name__)


def run(config: dict) -> None:
    handled_label = config["labels"]["handled"]
    mention = config["digest"].get("mention", "")

    # Fetch all issues with the handled label closed in the last 48h
    # (using a wider window to account for cron timing drift)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)

    all_handled = gh.list_issues_with_label(handled_label, state="closed")
    recent = [
        i for i in all_handled
        if datetime.fromisoformat(i["closed_at"].replace("Z", "+00:00")) > cutoff
    ]

    # Also check open issues handled today
    open_handled = gh.list_issues_with_label(handled_label, state="open")
    recent_open = [
        i for i in open_handled
        if datetime.fromisoformat(i["updated_at"].replace("Z", "+00:00")) > cutoff
    ]

    all_recent = recent + recent_open

    if not all_recent:
        log.info("No handled activity in the last 48h — skipping digest")
        return

    log.info("Creating digest for %d handled items", len(all_recent))

    summary = claude_client.summarize_activity(all_recent, config)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    body_lines = [
        f"## Agentic OSS Daily Digest — {date_str}",
        "",
        summary,
        "",
        "### Handled items",
        "",
    ]

    for item in all_recent:
        state_icon = "🔴" if item["state"] == "closed" else "🟡"
        labels = ", ".join(lbl["name"] for lbl in item.get("labels", []) if lbl["name"] != handled_label)
        body_lines.append(f"{state_icon} #{item['number']} — {item['title']}" + (f" `{labels}`" if labels else ""))

    if mention:
        body_lines += ["", f"cc {mention}"]

    body = "\n".join(body_lines)

    issue = gh.create_issue(
        title=f"Agentic OSS Digest — {date_str}",
        body=body,
        labels=["agentic-digest"],
    )

    log.info("Digest created: #%d", issue["number"])
