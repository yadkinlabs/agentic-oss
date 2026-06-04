# agentic-oss

AI-powered triage for open source GitHub repositories. Automates the noise — questions, duplicates, spam, stale issues — and surfaces what needs a human: bugs and feature requests.

## What it does

**Handles automatically:**
- Questions → Claude answers using your FAQ and docs, closes the issue
- Duplicates → links to the original, closes
- Spam → closes without engagement
- Stale issues → warns after N days, closes after M more

**Queues for you:**
- Bugs → labeled, acknowledged, waiting for your triage
- Feature requests → labeled, queued for your review

**Daily digest:**
- One issue per day summarizing everything the bot handled
- You get one email, not dozens

**PR review:**
- Welcomes first-time contributors
- Posts a summary of what the PR does
- Flags if it touches sensitive paths (auth, config, etc.)
- You decide merge or reject

## Setup

### 1. Add your Anthropic API key as a secret

In your repo: **Settings → Secrets and variables → Actions → New repository secret**

Name: `ANTHROPIC_API_KEY`

### 2. Copy the workflow files

Copy the three files from [`examples/workflows/`](examples/workflows/) into your repo's `.github/workflows/` directory.

### 3. Add your config

Copy [`examples/agentic-oss.yml`](examples/agentic-oss.yml) to `.github/agentic-oss.yml` in your repo and fill in your project details, FAQ entries, and sensitive paths.

### 4. That's it

Push the files. The next issue or PR opened in your repo will be triaged automatically.

## Configuration

```yaml
# .github/agentic-oss.yml

project:
  name: my-project
  description: What your project does in one sentence.
  docs_url: https://github.com/you/my-project#readme

stale:
  days_before_stale: 30
  days_before_close: 15

faq:
  - question: How do I install this?
    answer: See the Quick Start section in the README.

sensitive_paths:
  - src/auth
  - src/config

digest:
  mention: "@your-github-username"
```

See [`examples/agentic-oss.yml`](examples/agentic-oss.yml) for the full reference.

## Requirements

- Public GitHub repo (free Actions minutes)
- Anthropic API key (~$0.01 per triage event using Claude Haiku)

## Contributing

Issues and PRs welcome. This repo uses agentic-oss to triage itself.

## Support

Built by [Yadkin Labs](mailto:opensource@yadkinlabs.com). Need help deploying this or building agentic systems for your organization? Reach out.

## License

MIT — see [LICENSE](LICENSE).
