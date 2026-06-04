"""
Entry point — reads GitHub Actions environment, dispatches to the right handler.
"""

import json
import logging
import os
import sys

import config as cfg
import digest
import stale
import triage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("agentic-oss")


def main() -> None:
    mode = os.environ.get("ACTION_MODE", "triage")
    config = cfg.load()

    log.info("agentic-oss starting — mode=%s", mode)

    if mode == "stale":
        stale.run(config)
        return

    if mode == "digest":
        digest.run(config)
        return

    # Triage mode — read GitHub event
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")

    if not event_path or not os.path.exists(event_path):
        log.error("GITHUB_EVENT_PATH not set or file not found: %s", event_path)
        sys.exit(1)

    with open(event_path) as f:
        event = json.load(f)

    log.info("Event: %s", event_name)
    triage.run(event_name, event, config)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log.error("agentic-oss failed: %s", e, exc_info=True)
        # Exit 0 so we don't block PRs/issues on a triage failure
        sys.exit(0)
