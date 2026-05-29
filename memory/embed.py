#!/usr/bin/env python3
"""Build and maintain the memory embedding index for bear-notes.

Usage:
  embed.py --rebuild          Full rebuild of all memory embeddings
  embed.py --update <note_id> Update a single note's embedding
  embed.py --remove <note_id> Remove a note from the index
  embed.py --stats            Show index statistics

The index lives at ~/.bear-memory-index/embeddings.jsonl
Each line: {"note_id": "...", "hash": "...", "vector": [...], "updated": "..."}
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

INDEX_DIR = Path.home() / ".bear-memory-index"
INDEX_FILE = INDEX_DIR / "embeddings.jsonl"
MEMORY_TAG = "#ai/memory"

# Lazy-load the model (loaded on first use)
_model = None

def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def bearcli(*args):
    """Run bearcli and return stdout."""
    result = subprocess.run(
        ["bearcli"] + list(args),
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"bearcli failed: {result.stderr.strip()}")
    return result.stdout.strip()

def bearcli_json(*args):
    """Run bearcli with --format json and parse output."""
    return json.loads(bearcli(*(list(args) + ["--format", "json"])))

def parse_metadata(content):
    """Extract type, agent, confidence, updated from HTML comment in note body."""
    m = re.search(r'<!--\s*type:\s*(\S+)\s+agent:\s*(\S+)\s+confidence:\s*(\S+)\s+updated:\s*(\S+)\s*-->', content)
    if not m:
        return None
    return {
        "type": m.group(1),
        "agent": m.group(2),
        "confidence": m.group(3),
        "updated": m.group(4),
    }

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
    # Search for all notes under #ai/memory tag tree
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
    # bearcli cat returns JSON: {"content": "..."}
    try:
        data = json.loads(result)
        return data.get("content", "")
    except json.JSONDecodeError:
        return result

def embed_text(text):
    """Generate embedding vector for text."""
    model = get_model()
    return model.encode(text, normalize_embeddings=True).tolist()

def rebuild():
    """Full rebuild of the embedding index."""
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    notes = get_memory_notes()
    if not notes:
        print("No memory notes found. Create a note with #ai/memory/<type>/entry tag first.")
        return

    entries = []
    skipped = 0
    for note in notes:
        try:
            content = get_note_content(note["id"])
        except Exception as e:
            print(f"  SKIP {note['id']}: read failed ({e})")
            skipped += 1
            continue

        meta = parse_metadata(content)
        if not meta:
            print(f"  SKIP {note['id']}: no metadata comment found")
            skipped += 1
            continue

        # Use content for embedding (strip the metadata comment + source line)
        clean = re.sub(r'<!--.*?-->', '', content).strip()
        vector = embed_text(clean)

        entries.append({
            "note_id": note["id"],
            "hash": note.get("contentHash", note.get("hash", "")),
            "type": meta["type"],
            "agent": meta["agent"],
            "confidence": meta["confidence"],
            "updated": meta["updated"],
            "vector": vector,
        })
        print(f"  OK {note['id']} {note['title']}")

    with open(INDEX_FILE, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")

    print(f"\nIndexed {len(entries)} memories ({skipped} skipped)")

def update(note_id):
    """Update a single note's embedding."""
    try:
        content = get_note_content(note_id)
    except Exception as e:
        print(f"Error reading note: {e}")
        sys.exit(1)

    meta = parse_metadata(content)
    if not meta:
        print("Error: no metadata comment found in note")
        sys.exit(1)

    clean = re.sub(r'<!--.*?-->', '', content).strip()
    vector = embed_text(clean)

    entry = {
        "note_id": note_id,
        "hash": "",
        "type": meta["type"],
        "agent": meta["agent"],
        "confidence": meta["confidence"],
        "updated": meta["updated"],
        "vector": vector,
    }

    # Read existing, replace or append
    entries = load_index()
    found = False
    for i, e in enumerate(entries):
        if e["note_id"] == note_id:
            entries[i] = entry
            found = True
            break
    if not found:
        entries.append(entry)

    with open(INDEX_FILE, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")

    print(f"Updated embedding for {note_id}")

def remove(note_id):
    """Remove a note from the index."""
    entries = [e for e in load_index() if e["note_id"] != note_id]
    with open(INDEX_FILE, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
    print(f"Removed {note_id} from index")

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

def stats():
    """Show index statistics."""
    entries = load_index()
    if not entries:
        print("Index is empty. Run 'embed.py --rebuild' first.")
        return

    types = {}
    agents = {}
    for e in entries:
        types[e["type"]] = types.get(e["type"], 0) + 1
        agents[e["agent"]] = agents.get(e["agent"], 0) + 1

    print(f"Total memories: {len(entries)}")
    print(f"Types: {types}")
    print(f"Agents: {agents}")
    dims = len(entries[0]["vector"]) if entries else 0
    print(f"Vector dims:  {dims}")

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
    else:
        print(__doc__)
        sys.exit(1)
