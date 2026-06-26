#!/usr/bin/env python3
"""Build and maintain the memory embedding index for bear-notes.

Usage:
  embed.py --rebuild            Full rebuild of all memory embeddings
  embed.py --update <note_id>   Update a single note's embeddings (all sections)
  embed.py --remove <note_id>   Remove a note from the index
  embed.py --stats              Show index statistics
  embed.py --migrate-plan       Generate migration plan (old → multi-entry format)

The index lives at ~/.bear-memory-index/embeddings.jsonl
Each line: {"note_id": "...", "section_index": int, "section_title": "...",
             "hash": "...", "type": "...", "agent": "...", "confidence": "...",
             "updated": "...", "vector": [...]}

Multi-entry notes (new format) use ## sections, each gets its own index entry.
Single-entry notes (old format) get section_index=-1 and are treated as one section.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

INDEX_DIR = Path.home() / ".bear-memory-index"
INDEX_FILE = INDEX_DIR / "embeddings.jsonl"
MEMORY_TAG = "#ai/memory"
MIGRATE_THRESHOLD = 0.48

# Lazy-load the model (loaded on first use)
_model = None

def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _model


# ── bearcli helpers ────────────────────────────────────────────────

_BEARCLI = os.environ.get("BEARCLI_CMD", "bearcli")

def bearcli(*args):
    """Run bearcli and return stdout."""
    result = subprocess.run(
        [_BEARCLI] + list(args),
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"bearcli failed: {result.stderr.strip()}")
    return result.stdout.strip()


def bearcli_json(*args):
    """Run bearcli with --format json and parse output."""
    return json.loads(bearcli(*(list(args) + ["--format", "json"])))


# ── Metadata parsing ───────────────────────────────────────────────

def parse_metadata_comment(comment_text):
    """Extract fields from a single HTML comment string.

    Returns dict with type, agent, confidence, updated, or None if invalid.
    Handles both new-format (full 4-field) and old-format (4-field) comments.
    """
    m = re.search(
        r'<!--\s*type:\s*(\S+)\s+agent:\s*(\S+)\s+confidence:\s*(\S+)\s+updated:\s*(\S+)\s*-->',
        comment_text
    )
    if not m:
        return None
    return {
        "type": m.group(1),
        "agent": m.group(2),
        "confidence": m.group(3),
        "updated": m.group(4),
    }


def parse_note_level_comment(content):
    """Extract only 'updated' from the note-level comment (new-format preamble).

    New-format note-level comments only have 'updated' field.
    Returns the updated date string, or None.
    """
    m = re.search(
        r'<!--\s*updated:\s*(\S+)\s*-->',
        content[:500]
    )
    if not m:
        return None
    return m.group(1)


def parse_sections(content):
    """Parse note content into section dicts.

    New format (has ## sections):
      Returns list of dicts with section_index, section_title, text (for embedding),
      type, agent, confidence, updated. Note-level preamble is skipped.

    Old format (no ## sections):
      Returns a single section with section_index=-1, using the original
      note-level metadata comment.

    Returns empty list if no valid metadata found anywhere.
    """
    # Detect format: look for ## headers after the preamble
    section_matches = list(re.finditer(r'^## (.+)$', content, re.MULTILINE))

    if not section_matches:
        # ── Old format: single entry ──
        meta = parse_metadata_comment(content)
        if not meta:
            return []
        clean = re.sub(r'<!--.*?-->', '', content).strip()
        return [{
            "section_index": -1,
            "section_title": "",
            "text": clean,
            "type": meta["type"],
            "agent": meta["agent"],
            "confidence": meta["confidence"],
            "updated": meta["updated"],
        }]

    # ── New format: multiple ## sections ──
    sections = []
    for i, m in enumerate(section_matches):
        section_title = m.group(1).strip()
        start = m.start()
        # Find the next ## section or end of content
        if i + 1 < len(section_matches):
            end = section_matches[i + 1].start()
        else:
            end = len(content)

        section_text = content[start:end].strip()

        # Extract metadata from the first HTML comment within this section
        meta = parse_metadata_comment(section_text)
        if not meta:
            print(f"  WARN: section {i} ('{section_title}') has no valid metadata — skipped")
            continue

        # Build embedding text: ## title + body + source line (no HTML comment)
        clean_text = re.sub(r'<!--.*?-->', '', section_text).strip()

        sections.append({
            "section_index": i,
            "section_title": section_title,
            "text": clean_text,
            "type": meta["type"],
            "agent": meta["agent"],
            "confidence": meta["confidence"],
            "updated": meta["updated"],
        })

    return sections


# ── Bear note helpers ──────────────────────────────────────────────

def is_memory_note(note):
    """Check if a note is a memory entry (has #ai/memory/*/entry tag)."""
    tags = note.get("tags", [])
    for t in tags:
        t_clean = t.lstrip("#")
        if t_clean.startswith("ai/memory/") and t_clean.endswith("/entry"):
            return True
    return False


def get_memory_notes():
    """Fetch all memory entry notes from Bear."""
    notes = []
    try:
        results = bearcli_json("search", f"{MEMORY_TAG}", "--format", "json")
        if isinstance(results, list):
            for r in results:
                if isinstance(r, dict) and "id" in r and is_memory_note(r):
                    notes.append(r)
    except Exception as e:
        print(f"  Search error: {e}")
    return notes


def get_note_content(note_id):
    """Fetch raw content of a note."""
    result = bearcli("cat", note_id)
    try:
        data = json.loads(result)
        return data.get("content", "")
    except json.JSONDecodeError:
        return result


def embed_text(text):
    """Generate embedding vector for text."""
    model = get_model()
    return model.encode(text, normalize_embeddings=True).tolist()


# ── Index operations ───────────────────────────────────────────────

def load_index():
    """Load all entries from the index file."""
    if not INDEX_FILE.exists():
        return []
    entries = []
    with open(INDEX_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def save_index(entries):
    """Write entries to the index file."""
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    with open(INDEX_FILE, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


def rebuild():
    """Full rebuild of the embedding index."""
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    notes = get_memory_notes()
    if not notes:
        print("No memory notes found. Create a note with #ai/memory/<type>/entry tag first.")
        return

    entries = []
    skipped_notes = 0
    total_sections = 0

    for note in notes:
        try:
            content = get_note_content(note["id"])
        except Exception as e:
            print(f"  SKIP {note['id']}: read failed ({e})")
            skipped_notes += 1
            continue

        sections = parse_sections(content)
        if not sections:
            print(f"  SKIP {note['id']} '{note.get('title','')}': no valid metadata")
            skipped_notes += 1
            continue

        note_hash = note.get("contentHash", note.get("hash", ""))
        for sec in sections:
            vector = embed_text(sec["text"])
            entries.append({
                "note_id": note["id"],
                "section_index": sec["section_index"],
                "section_title": sec["section_title"],
                "hash": note_hash,
                "type": sec["type"],
                "agent": sec["agent"],
                "confidence": sec["confidence"],
                "updated": sec["updated"],
                "vector": vector,
            })
            total_sections += 1

        fmt = "new" if sections[0]["section_index"] >= 0 else "old"
        print(f"  OK {note['id']} [{fmt}] {len(sections)} section(s) — {note.get('title','')}")

    save_index(entries)

    note_count = len(set(e["note_id"] for e in entries))
    print(f"\nIndexed {total_sections} sections across {note_count} notes ({skipped_notes} notes skipped)")


def update(note_id):
    """Update a single note's embeddings — removes old entries, re-indexes all sections."""
    try:
        content = get_note_content(note_id)
    except Exception as e:
        print(f"Error reading note: {e}")
        sys.exit(1)

    sections = parse_sections(content)
    if not sections:
        print("Error: no valid metadata found in note")
        sys.exit(1)

    # Remove all old entries for this note_id
    entries = [e for e in load_index() if e["note_id"] != note_id]

    # Add new entries for each section
    for sec in sections:
        vector = embed_text(sec["text"])
        entries.append({
            "note_id": note_id,
            "section_index": sec["section_index"],
            "section_title": sec["section_title"],
            "hash": "",
            "type": sec["type"],
            "agent": sec["agent"],
            "confidence": sec["confidence"],
            "updated": sec["updated"],
            "vector": vector,
        })

    save_index(entries)
    print(f"Updated {len(sections)} section(s) for {note_id}")


def remove(note_id):
    """Remove all entries for a note from the index."""
    entries = [e for e in load_index() if e["note_id"] != note_id]
    save_index(entries)
    print(f"Removed {note_id} from index")


def stats():
    """Show index statistics."""
    entries = load_index()
    if not entries:
        print("Index is empty. Run 'embed.py --rebuild' first.")
        return

    note_ids = set(e["note_id"] for e in entries)
    types = {}
    agents = {}
    old_count = 0
    new_count = 0

    for e in entries:
        types[e["type"]] = types.get(e["type"], 0) + 1
        agents[e["agent"]] = agents.get(e["agent"], 0) + 1
        if e.get("section_index", -1) >= 0:
            new_count += 1
        else:
            old_count += 1

    print(f"Notes:    {len(note_ids)}")
    print(f"Sections: {len(entries)}  (new-format: {new_count}, old-format: {old_count})")
    print(f"Types:    {types}")
    print(f"Agents:   {agents}")
    if entries:
        dims = len(entries[0]["vector"])
        print(f"Vector:   {dims} dims")


# ── Migration plan ─────────────────────────────────────────────────

def cosine_sim(a, b):
    """Vectors are normalized; dot product = cosine similarity."""
    return float(np.dot(a, b))


def centroid(vectors):
    """Compute the mean (centroid) of a list of vectors, re-normalized."""
    if not vectors:
        return None
    c = np.mean(vectors, axis=0)
    norm = np.linalg.norm(c)
    if norm > 0:
        c = c / norm
    return c.tolist()


def generate_topic_title(sections):
    """Generate a topic title from a group of section dicts.

    Derives the broad topic from section titles by extracting common
    keywords. Falls back to the first section's title if no commonality.
    """
    # Simple heuristic: use the type name + a representative keyword
    titles = [s["section_title"] for s in sections]
    if not titles:
        return "Memory Group"

    # For now, return a generic placeholder. The agent/user will refine
    # the topic title during migration execution.
    mem_type = sections[0].get("type", sections[0].get("metadata", {}).get("type", "project"))
    type_label = {"user": "User", "feedback": "Feedback", "project": "Project", "reference": "Reference"}
    label = type_label.get(mem_type, mem_type.capitalize())

    # Use the most representative title as the topic base
    # (the one closest to the centroid of all section texts)
    if len(sections) == 1:
        return f"「MEM」{label} · {sections[0]['section_title']}"

    # For multiple sections: use a simple topic derived from common words
    words_count = {}
    for s in sections:
        for word in s["section_title"].split():
            words_count[word] = words_count.get(word, 0) + 1

    # Pick the top words that appear in multiple titles as the topic hint
    common_words = [w for w, c in sorted(words_count.items(), key=lambda x: -x[1]) if c >= 2]
    if common_words:
        topic = " ".join(common_words[:3])
    else:
        topic = sections[0]["section_title"]

    return f"「MEM」{label} · {topic}"


def migrate_plan():
    """Generate migration plan for old-format single-entry notes.

    Outputs JSON plan to stdout:
      - Groups of semantically similar old notes → one topic note each
      - Ungrouped notes → individual topic notes
      - Stats for user review
    """
    old_notes = []

    # Collect all old-format notes
    for note in get_memory_notes():
        try:
            content = get_note_content(note["id"])
        except Exception:
            continue

        # Check if old format (no ## sections)
        if re.search(r'^## ', content, re.MULTILINE):
            continue  # Already new format, skip

        meta = parse_metadata_comment(content)
        if not meta:
            continue

        clean = re.sub(r'<!--.*?-->', '', content).strip()
        vector = embed_text(clean)
        old_notes.append({
            "note_id": note["id"],
            "title": note.get("title", ""),
            "content_hash": note.get("contentHash", ""),
            "type": meta["type"],
            "agent": meta["agent"],
            "confidence": meta["confidence"],
            "updated": meta["updated"],
            "body": clean,
            "vector": vector,
            "created": note.get("createdAt", note.get("created", "")),
        })

    if not old_notes:
        print(json.dumps({"groups": [], "ungrouped": [], "stats": {
            "total_old_notes": 0, "grouped": 0, "ungrouped": 0, "topic_notes_to_create": 0
        }}, indent=2, ensure_ascii=False))
        return

    # Group by type, then cluster within each type
    type_groups = {}
    for note in old_notes:
        type_groups.setdefault(note["type"], []).append(note)

    all_groups = []
    all_ungrouped = []

    for mem_type, notes in type_groups.items():
        # Deterministic sort: created ASC, note_id ASC (tiebreaker)
        notes.sort(key=lambda n: (n.get("created", ""), n["note_id"]))

        clusters = []  # Each cluster is a list of note dicts

        for note in notes:
            best_cluster = None
            best_sim = -1

            for cluster in clusters:
                # Compute centroid of this cluster
                vectors = [m["vector"] for m in cluster]
                c = np.mean(vectors, axis=0)
                norm = np.linalg.norm(c)
                if norm > 0:
                    c = c / norm
                sim = float(np.dot(note["vector"], c))
                if sim > best_sim:
                    best_sim = sim
                    best_cluster = cluster

            if best_sim >= MIGRATE_THRESHOLD and best_cluster is not None:
                best_cluster.append(note)
            else:
                clusters.append([note])

        # Format output for each cluster
        for cluster in clusters:
            # Sort sections by updated DESC (newest first in the topic note)
            cluster_sorted = sorted(cluster, key=lambda n: n.get("updated", ""), reverse=True)

            sections = []
            for n in cluster_sorted:
                # Extract section title from old note title (strip 「MEM」 prefix)
                sec_title = n["title"]
                if sec_title.startswith("「MEM」"):
                    sec_title = sec_title[len("「MEM」"):].strip()
                sections.append({
                    "note_id": n["note_id"],
                    "title": sec_title,
                    "metadata": {
                        "type": n["type"],
                        "agent": n["agent"],
                        "confidence": n["confidence"],
                        "updated": n["updated"],
                    },
                    "body": n["body"],
                    "updated": n["updated"],
                })

            topic_title = generate_topic_title(
                [{"section_title": s["title"], "type": mem_type} for s in sections]
            )

            # Compute average similarity within cluster
            if len(cluster) >= 2:
                sims = []
                for i in range(len(cluster)):
                    for j in range(i + 1, len(cluster)):
                        sims.append(float(np.dot(cluster[i]["vector"], cluster[j]["vector"])))
                avg_sim = round(sum(sims) / len(sims), 4)
            else:
                avg_sim = None  # Single-note cluster: no pairwise similarity

            entry = {
                "type": mem_type,
                "topic_title": topic_title,
                "source_note_ids": [s["note_id"] for s in sections],
                "sections": sections,
                "avg_similarity": avg_sim,
            }

            if len(cluster) == 1:
                all_ungrouped.append(entry)
            else:
                all_groups.append(entry)

    total = len(old_notes)
    grouped_count = sum(len(g["sections"]) for g in all_groups)
    ungrouped_count = total - grouped_count
    topic_count = len(all_groups) + len(all_ungrouped)

    plan = {
        "threshold": MIGRATE_THRESHOLD,
        "groups": all_groups,
        "ungrouped": all_ungrouped,
        "stats": {
            "total_old_notes": total,
            "grouped": grouped_count,
            "ungrouped": ungrouped_count,
            "topic_notes_to_create": topic_count,
        },
    }

    print(json.dumps(plan, indent=2, ensure_ascii=False))


# ── CLI ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "--rebuild":
        rebuild()
    elif cmd == "--update" and len(sys.argv) == 3:
        update(sys.argv[2])
    elif cmd == "--remove" and len(sys.argv) == 3:
        remove(sys.argv[2])
    elif cmd == "--stats":
        stats()
    elif cmd == "--migrate-plan":
        migrate_plan()
    else:
        print(__doc__)
        sys.exit(1)
