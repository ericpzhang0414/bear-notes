#!/usr/bin/env python3
"""Recall feedback memories for Claude Code SessionStart hook.

Only injects #ai/memory/feedback/entry — behavioral corrections
that the agent MUST know to avoid repeating past mistakes.

Uses bearcli to read live Bear notes. Output is injected into the
conversation context at session start. Keep it compact.
"""

import json
import re
import subprocess
import sys


def bearcli(*args):
    """Run bearcli and return stdout."""
    result = subprocess.run(
        ["bearcli"] + list(args), capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def bearcli_json(*args):
    """Run bearcli --format json and parse."""
    raw = bearcli(*(list(args) + ["--format", "json"]))
    return json.loads(raw) if raw else []


def get_note_content(note_id):
    """Read raw markdown content of a note."""
    return bearcli("cat", note_id)


def parse_section_summary(content):
    """Extract ## section titles + first sentence of body text."""
    summaries = []
    # Split by ## sections, skip preamble (H1 title, tag, note-level comment)
    parts = re.split(r'\n(?=## )', content)
    for part in parts:
        lines = part.strip().split('\n')
        if not lines or not lines[0].startswith('## '):
            continue
        title = lines[0].strip().lstrip('#').strip()
        if not title:
            continue
        # Find first real body line (skip HTML comments and blank lines)
        body = ""
        for line in lines[1:]:
            if line.startswith('<!--') or line.strip() == '':
                continue
            body = line.strip()
            break
        if body:
            if len(body) > 150:
                body = body[:150] + "..."
            summaries.append(f"**{title}**: {body}")
        else:
            summaries.append(f"**{title}**")
    return summaries


def main():
    # Use tag in query string — more reliable than --tag parameter
    notes = bearcli_json("search", "「MEM」 #ai/memory/feedback/entry")

    if not notes:
        return  # Silent — no feedback memories yet

    all_summaries = []
    for note in notes:
        nid = note.get("id", "")
        content = get_note_content(nid)
        if not content:
            continue
        sections = parse_section_summary(content)
        all_summaries.extend(sections)

    if not all_summaries:
        return

    print("## Bear Memory (auto-loaded)\n")
    print("**Behavioral feedback:**")
    for s in all_summaries:
        print(f"- {s}")
    print()


if __name__ == "__main__":
    main()
