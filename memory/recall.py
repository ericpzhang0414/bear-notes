#!/usr/bin/env python3
"""Recall feedback memories for Claude Code SessionStart hook.

Only injects #ai/memory/feedback/entry — behavioral corrections
that the agent MUST know to avoid repeating past mistakes.

Uses bearcli to read live Bear notes. Output is injected into the
conversation context at session start. Output is a compact command-style
list: section titles only, no body text. Agent must search memory for
full rule details when needed.
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


def parse_section_titles(content):
    """Extract only ## section titles — no body text.

    Returns compact key-phrases for command-style output. Hook output
    only needs to remind the agent which rules exist; body text can be
    loaded on demand via search_notes when context is needed.
    """
    titles = []
    parts = re.split(r'\n(?=## )', content)
    for part in parts:
        lines = part.strip().split('\n')
        if not lines or not lines[0].startswith('## '):
            continue
        title = lines[0].strip().lstrip('#').strip()
        if not title:
            continue
        # Keep only the key phrase (< 20 chars when possible)
        titles.append(title)
    return titles


def main():
    notes = bearcli_json("search", "「MEM」 #ai/memory/feedback/entry")

    if not notes:
        return  # Silent — no feedback memories yet

    all_titles = []
    for note in notes:
        nid = note.get("id", "")
        content = get_note_content(nid)
        if not content:
            continue
        titles = parse_section_titles(content)
        all_titles.extend(titles)

    if not all_titles:
        return

    # Command-style single-line output: ⛔ RULE | RULE | RULE
    rules = " | ".join(all_titles)
    max_line = 5
    if len(all_titles) > max_line:
        # Split into multiple lines, max_line rules per line
        lines = []
        for i in range(0, len(all_titles), max_line):
            chunk = all_titles[i:i+max_line]
            lines.append(" | ".join(chunk))
        rules = "\n   ".join(lines)

    print(f"⛔ {rules}")


if __name__ == "__main__":
    main()
