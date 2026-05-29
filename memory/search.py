#!/usr/bin/env python3
"""Semantic search over bear-notes memory entries with hybrid ranking.

Usage:
  search.py "<query>"                    Top 5 results, all types
  search.py "<query>" --top 10           Top 10 results
  search.py "<query>" --type user        Filter by memory type
  search.py "<query>" --agent claude-code  Filter by source agent
  search.py "<query>" --raw              Show raw scores (no filtering)

Scoring:
  score = 0.6 * cosine_similarity + 0.3 * recency + 0.1 * confidence_boost
"""

import json
import math
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

INDEX_DIR = Path.home() / ".bear-memory-index"
INDEX_FILE = INDEX_DIR / "embeddings.jsonl"

_model = None

def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
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
    return np.dot(a, b)

def recency_score(updated_str):
    """Exponential decay based on days since last update.
    Returns 1.0 for today, ~0.37 after 30 days, ~0.05 after 90 days.
    """
    try:
        updated = datetime.strptime(updated_str, "%Y-%m-%d")
        days = (datetime.now() - updated).days
        # Half-life of 30 days
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

def format_output(results, raw=False):
    for i, r in enumerate(results):
        print(f"#{i+1}  [{r['type']}]  score={r['score']}")
        print(f"    note_id={r['note_id']}")
        if raw:
            print(f"    sim={r['similarity']}  recency={r['recency']}  conf={r['confidence_bonus']}")
        print(f"    {r['updated']} · {r['confidence']}")
        print()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

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
