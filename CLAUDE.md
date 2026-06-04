# agentic-oss

GitHub Action for AI-powered OSS triage. No server, no database — pure Python
scripts triggered by GitHub Actions. Claude Haiku handles classification; all
GitHub API calls use the built-in GITHUB_TOKEN.

## How it works

Three modes, three workflows:

| Mode   | Trigger                    | Does                                    |
|--------|----------------------------|-----------------------------------------|
| triage | issue.opened / pr.opened   | Classifies, labels, comments, closes    |
| stale  | cron (daily)               | Warns stale issues, closes after N more |
| digest | cron (daily)               | Opens a summary issue of yesterday's work |

Entry point: `action.yml` → `src/main.py` → reads `ACTION_MODE` env var → dispatches.

## File layout

```
action.yml              # Composite action definition
src/
  main.py               # Entry point, reads GitHub event, dispatches
  config.py             # Loads .github/agentic-oss.yml from consuming repo
  triage.py             # handle_issue(), handle_pr(), _validate_triage_result()
  stale.py              # stale.run()
  digest.py             # digest.run()
  claude_client.py      # Claude API — triage_issue(), review_pr(), summarize_activity()
  github_client.py      # GitHub REST API thin wrapper
examples/
  agentic-oss.yml       # Config template for consuming repos
  workflows/            # Workflow templates to copy into consuming repos
```

## Security model

Two layers protect against prompt injection from malicious issue/PR content:

1. **Input hardening** (`claude_client.py`): issue/PR titles and bodies are wrapped
   in `=== BEGIN/END UNTRUSTED USER CONTENT ===` delimiters. `_INJECTION_GUARD`
   rules are appended to both system prompts instructing Claude to treat the
   content as data, never as instructions.

2. **Output validation** (`triage.py:_validate_triage_result`): every Claude response
   is checked against strict allowlists before any GitHub API call:
   - `classification` must be in `_VALID_CLASSIFICATIONS`
   - `action` must be in `_VALID_ACTIONS`
   - `labels` are filtered to only names configured in the repo's `config.labels`
   - `comment` is truncated to 1000 chars
   - Anything that fails validation defaults to `close_spam` — safe fallback

Never add issue/PR content outside the delimiters. Never skip `_validate_triage_result`.

## Adding a new event handler

1. Add a handler function in `triage.py` or a new module
2. Dispatch it from `triage.run()` or `main.main()`
3. Add a corresponding workflow in `examples/workflows/`
4. Validate all Claude output against an allowlist before acting on it

## Local testing

```bash
pip install -r requirements.txt

export ANTHROPIC_API_KEY=...
export GITHUB_TOKEN=...
export GITHUB_REPOSITORY=owner/repo
export GITHUB_EVENT_NAME=issues
export GITHUB_EVENT_PATH=/tmp/event.json

# Write a fake event payload to /tmp/event.json, then:
python src/main.py
```

Failures exit 0 intentionally — triage errors must never block issue or PR creation.
