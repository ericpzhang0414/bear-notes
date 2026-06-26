#!/usr/bin/env python3
"""Recall memories and reference index for Claude Code SessionStart hook.

Injects two things into session context:
1. #ai/memory/feedback/entry — behavioral corrections
2. 📚 Reference Index — topic map of external knowledge base

Uses bearcli to read live Bear notes. Output is compact (typically < 1KB).
Agent must search memory/reference for full details when needed.
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


# ── Feedback Memory ──────────────────────────────────────────────

def parse_section_titles(content):
    """Extract only ## section titles — no body text."""
    titles = []
    parts = re.split(r'\n(?=## )', content)
    for part in parts:
        lines = part.strip().split('\n')
        if not lines or not lines[0].startswith('## '):
            continue
        title = lines[0].strip().lstrip('#').strip()
        if not title:
            continue
        titles.append(title)
    return titles


def recall_feedback():
    """Load feedback memory rules."""
    notes = bearcli_json("search", "「MEM」 #ai/memory/feedback/entry")

    if not notes:
        return None

    all_titles = []
    for note in notes:
        nid = note.get("id", "")
        content = get_note_content(nid)
        if not content:
            continue
        titles = parse_section_titles(content)
        all_titles.extend(titles)

    if not all_titles:
        return None

    # Command-style single-line output: ⛔ RULE | RULE | RULE
    rules = " | ".join(all_titles)
    max_line = 5
    if len(all_titles) > max_line:
        lines = []
        for i in range(0, len(all_titles), max_line):
            chunk = all_titles[i:i+max_line]
            lines.append(" | ".join(chunk))
        rules = "\n   ".join(lines)

    return f"⛔ {rules}"


# ── Reference Index ──────────────────────────────────────────────

def parse_reference_sections(content):
    """Extract ## section headings with counts from Reference Index.

    Input: '## 文章 (9)\n→ [[note]]...'
    Output: [('文章', 9, ['架构设计原则', 'Swift Concurrency']), ...]
    """
    sections = []
    parts = re.split(r'\n(?=## )', content)
    for part in parts:
        lines = part.strip().split('\n')
        if not lines or not lines[0].startswith('## '):
            continue
        heading = lines[0].strip().lstrip('#').strip()

        # Extract name and count: "文章 (9)" or "视频 (0)"
        m = re.match(r'(.+?)\s*\((\d+)\)', heading)
        if not m:
            continue
        name = m.group(1).strip()
        count = int(m.group(2))

        # Extract note titles (from → [[Title]] or → [[target | Title]] lines)
        titles = []
        for line in lines[1:]:
            # Match [[display]] or [[target|display]]
            for m in re.finditer(r'\[\[(?:[^\]|]+\|)?([^\]|]+)\]\]', line):
                titles.append(m.group(1).strip())

        sections.append((name, count, titles))

    return sections


def recall_reference_index():
    """Load 📚 Reference Index and format as compact topic map."""
    notes = bearcli_json("search", "📚 Reference Index #reference")

    if not notes:
        return None

    content = get_note_content(notes[0].get("id", ""))
    if not content:
        return None

    sections = parse_reference_sections(content)
    if not sections:
        return None

    # Build compact topic map
    total = sum(c for _, c, _ in sections)
    lines = [f"📚 #reference ({total}):"]

    for name, count, titles in sections:
        if count == 0:
            continue  # skip empty categories
        if count <= 5 or len(titles) <= 5:
            # Few enough to list all
            topic_str = ", ".join(titles[:5])
        else:
            # Many: show count + sample
            sample = ", ".join(titles[:3])
            topic_str = f"{sample}, …(+{count - 3})"
        lines.append(f"  {name}({count}): {topic_str}")

    return "\n".join(lines)


# ── Main ─────────────────────────────────────────────────────────

def main():
    outputs = []

    fb = recall_feedback()
    if fb:
        outputs.append(fb)

    ref = recall_reference_index()
    if ref:
        outputs.append(ref)

    if outputs:
        print("\n".join(outputs))


if __name__ == "__main__":
    main()
