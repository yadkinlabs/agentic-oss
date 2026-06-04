"""
Claude integration — classifies issues and PRs, generates responses.
"""

import json
import os

import anthropic

_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

_TRIAGE_SYSTEM = """You are an assistant that triages GitHub issues for an open source project.

Given an issue, classify it and decide what action to take. Return ONLY a JSON object.

Classifications:
- "bug"        — a reproducible defect in the software
- "feature"    — a request for new functionality
- "question"   — a how-to or usage question
- "duplicate"  — clearly the same as an existing issue
- "spam"       — irrelevant, abusive, or automated noise
- "unclear"    — not enough information to classify

Actions:
- "label_and_acknowledge" — for bugs and features: add label, post a brief acknowledgment
- "reply_and_close"       — for questions: answer if possible, close the issue
- "close_duplicate"       — for duplicates: note the original, close
- "close_spam"            — for spam: close without engagement
- "ask_clarification"     — for unclear issues: ask for more detail

Return format:
{
  "classification": "bug|feature|question|duplicate|spam|unclear",
  "action": "label_and_acknowledge|reply_and_close|close_duplicate|close_spam|ask_clarification",
  "comment": "the exact comment to post (friendly, concise, helpful)",
  "labels": ["label1"],
  "reasoning": "one sentence explanation"
}

Tone: friendly, professional, welcoming. This is open source — contributors are volunteers."""

_PR_SYSTEM = """You are an assistant that reviews incoming pull requests for an open source project.

Given a PR, produce a brief summary and flag anything that needs the maintainer's attention.
Return ONLY a JSON object:
{
  "summary": "1-3 sentence description of what this PR does",
  "flags": ["list of concerns, if any — e.g. touches auth, no tests, breaking change"],
  "welcome_first_timer": true | false,
  "comment": "the exact comment to post on the PR"
}

Tone: encouraging and constructive. First-time contributors especially deserve a warm welcome."""


def triage_issue(issue: dict, config: dict) -> dict:
    project = config.get("project", {})
    faq = config.get("faq", [])

    faq_text = ""
    if faq:
        faq_text = "\n\nKnown FAQs:\n" + "\n".join(
            f"Q: {f['question']}\nA: {f['answer']}" for f in faq
        )

    context = (
        f"Project: {project.get('name', '')} — {project.get('description', '')}\n"
        f"Docs: {project.get('docs_url', '')}"
        f"{faq_text}\n\n"
        f"Issue #{issue['number']}: {issue['title']}\n\n"
        f"{issue.get('body') or '(no description)'}"
    )

    response = _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=_TRIAGE_SYSTEM,
        messages=[{"role": "user", "content": context}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1].lstrip("json").strip()
        raw = raw.rsplit("```", 1)[0].strip()
    return json.loads(raw)


def review_pr(pr: dict, files: list[dict], is_first_timer: bool, config: dict) -> dict:
    project = config.get("project", {})
    sensitive = config.get("sensitive_paths", [])

    touched = [f["filename"] for f in files]
    sensitive_touched = [p for p in sensitive if any(t.startswith(p) for t in touched)]

    context = (
        f"Project: {project.get('name', '')} — {project.get('description', '')}\n\n"
        f"PR #{pr['number']}: {pr['title']}\n"
        f"Author: {pr['user']['login']} (first-time contributor: {is_first_timer})\n\n"
        f"Description:\n{pr.get('body') or '(no description)'}\n\n"
        f"Files changed ({len(touched)}):\n" + "\n".join(f"  - {f}" for f in touched[:30]) +
        (f"\n\nSensitive paths touched: {sensitive_touched}" if sensitive_touched else "")
    )

    response = _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=_PR_SYSTEM,
        messages=[{"role": "user", "content": context}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1].lstrip("json").strip()
        raw = raw.rsplit("```", 1)[0].strip()
    return json.loads(raw)


def summarize_activity(handled_issues: list[dict], config: dict) -> str:
    """Generate a plain-English daily digest summary."""
    if not handled_issues:
        return "No activity to report."

    lines = [f"- #{i['number']}: {i['title']} ({i['state']})" for i in handled_issues[:50]]
    context = f"Summarize this list of GitHub issues handled by an AI triage bot today:\n" + "\n".join(lines)

    response = _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        messages=[{"role": "user", "content": context}],
    )
    return response.content[0].text.strip()
