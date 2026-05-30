#!/usr/bin/env python3
"""Semantic search over bear-notes memory entries with hybrid ranking.

Usage:
  search.py "<query>"                    Top 5 results, all types
  search.py "<query>" --top 10           Top 10 results
  search.py "<query>" --type user        Filter by memory type
  search.py "<query>" --agent claude-code  Filter by source agent
  search.py "<query>" --raw              Show raw scores (no filtering)
  search.py --find-group "<text>"        Find best topic note to group with
           --type <type> [--threshold 0.70]

Scoring:
  score = 0.6 * cosine_similarity + 0.3 * recency + 0.1 * confidence_boost
"""

import json
import math
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

INDEX_DIR = Path.home() / ".bear-memory-index"
INDEX_FILE = INDEX_DIR / "embeddings.jsonl"
FIND_GROUP_THRESHOLD = 0.48

_model = None

def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _model


def load_index():
    if not INDEX_FILE.exists():
        print("Index not found. Run 'embed.py --rebuild' first.", file=sys.stderr)
        sys.exit(1)
    entries = []
    with open(INDEX_FILE) as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))
    return entries


def cosine_sim(a, b):
    """Vectors are already normalized from embed.py. Dot product = cosine similarity."""
    return float(np.dot(a, b))


def recency_score(updated_str):
    """Exponential decay based on days since last update.
    Returns 1.0 for today, ~0.37 after 30 days, ~0.05 after 90 days.
    """
    try:
        updated = datetime.strptime(updated_str, "%Y-%m-%d")
        days = (datetime.now() - updated).days
        return math.exp(-days / 43.0)  # 30/ln(2) ≈ 43
    except Exception:
        return 0.5


def confidence_boost(confidence):
    if confidence == "confirmed":
        return 1.5
    return 0.8


def search(query, top=5, mem_type=None, agent=None):
    model = get_model()
    entries = load_index()

    if mem_type:
        entries = [e for e in entries if e["type"] == mem_type]
    if agent:
        entries = [e for e in entries if e["agent"] == agent]

    if not entries:
        print("No matching memories found.")
        return []

    query_vec = model.encode(query, normalize_embeddings=True)

    results = []
    for e in entries:
        sim = cosine_sim(query_vec, e["vector"])
        rec = recency_score(e["updated"])
        conf = confidence_boost(e["confidence"])
        score = 0.6 * sim + 0.3 * rec + 0.1 * conf

        results.append({
            "note_id": e["note_id"],
            "section_index": e.get("section_index", -1),
            "section_title": e.get("section_title", ""),
            "type": e["type"],
            "confidence": e["confidence"],
            "updated": e["updated"],
            "similarity": round(sim, 4),
            "recency": round(rec, 4),
            "confidence_bonus": round(conf, 4),
            "score": round(score, 4),
        })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top]


def find_group(query_text, mem_type=None, threshold=FIND_GROUP_THRESHOLD):
    """Find the best existing topic note to group a new memory with.

    Uses max section similarity — compares the query against each section
    individually and picks the best match. This is more permissive than
    centroid comparison and appropriate for daily use (if a new memory is
    similar to any existing section, it probably belongs in that topic).

    Returns {"note_id": "...", "similarity": 0.xx} or empty dict {}.
    """
    model = get_model()
    entries = load_index()

    if mem_type:
        entries = [e for e in entries if e["type"] == mem_type]

    if not entries:
        return {}

    query_vec = model.encode(query_text, normalize_embeddings=True)

    # Find best matching section → its note wins
    best_note_id = None
    best_sim = -1

    for e in entries:
        sim = cosine_sim(query_vec, e["vector"])
        if sim > best_sim:
            best_sim = sim
            best_note_id = e["note_id"]

    if best_sim >= threshold:
        return {"note_id": best_note_id, "similarity": round(best_sim, 4), "threshold": threshold}
    return {}


def format_output(results, raw=False):
    for i, r in enumerate(results):
        sec_idx = r.get("section_index", -1)

        # Build section context line
        if sec_idx >= 0:
            sec_context = f"section {sec_idx}: \"{r['section_title']}\""
        else:
            sec_context = "(old format, single entry)"

        print(f"#{i+1}  [{r['type']}]  score={r['score']}  {sec_context}")
        print(f"    note_id={r['note_id']}")
        if raw:
            print(f"    sim={r['similarity']}  recency={r['recency']}  conf={r['confidence_bonus']}")
        print(f"    {r['updated']} · {r['confidence']}")
        print()


def format_find_group(result):
    """Format the output of --find-group."""
    if not result:
        print("{}")
        print("\nNo matching topic note found — create a new note.")
        return

    print(json.dumps(result, ensure_ascii=False))
    print(f"\nMatch found: note_id={result['note_id']}")
    print(f"  similarity: {result['similarity']}  (threshold: {result['threshold']})")
    print(f"  → append to this note with position=\"beginning\"")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    # ── --find-group mode ──
    if sys.argv[1] == "--find-group":
        if len(sys.argv) < 3:
            print("Usage: search.py --find-group \"<text>\" [--type <type>] [--threshold <float>]")
            sys.exit(1)

        query = sys.argv[2]
        mem_type = None
        threshold = FIND_GROUP_THRESHOLD

        args = sys.argv[3:]
        i = 0
        while i < len(args):
            if args[i] == "--type" and i + 1 < len(args):
                mem_type = args[i + 1]; i += 2
            elif args[i] == "--threshold" and i + 1 < len(args):
                threshold = float(args[i + 1]); i += 2
            else:
                i += 1

        result = find_group(query, mem_type=mem_type, threshold=threshold)
        format_find_group(result)
        sys.exit(0)

    # ── Normal search mode ──
    query = sys.argv[1]
    top = 5
    mem_type = None
    agent = None
    raw = False

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--top" and i + 1 < len(args):
            top = int(args[i + 1]); i += 2
        elif args[i] == "--type" and i + 1 < len(args):
            mem_type = args[i + 1]; i += 2
        elif args[i] == "--agent" and i + 1 < len(args):
            agent = args[i + 1]; i += 2
        elif args[i] == "--raw":
            raw = True; i += 1
        else:
            i += 1

    results = search(query, top=top, mem_type=mem_type, agent=agent)
    format_output(results, raw=raw)
