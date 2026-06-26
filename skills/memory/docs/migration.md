# Migration: Old Format → New Format

Old 1:1 format notes must be migrated to the topic-grouped format. Migration is **explicit** — triggered by user, not automatic.

## Trigger & Prerequisites

```
Phase 1: Generate migration plan (read-only, safe)
──────────────────────────────────────────────────
$ python3 skills/memory/embed.py --migrate-plan
→ Outputs JSON plan to stdout with groups, ungrouped, and stats

User reviews: grouping correctness, topic titles, avg_similarity scores
User can adjust: groupings, topic titles, skip certain notes

Phase 2: Agent executes the plan (user confirms → MCP writes)
───────────────────────────────────────────────────────────────
Agent reads the plan JSON → for each group:
  1. create_note → new topic note (multi-section format)
  2. archive_note → archive each old note (safe, not deleted)

Phase 3: Rebuild index + update index notes
───────────────────────────────────────────
$ python3 skills/memory/embed.py --rebuild
Agent updates 4 index notes with new topic wiki links

Old notes are archived, not trashed — recoverable if migration has issues.
```

## Grouping Algorithm

Uses **deterministic greedy clustering + centroid comparison**:

```
1. Collect old-format notes (no ## sections), sorted by created ASC, note_id ASC
2. Group by type (cluster only within same type)
3. For each type, greedy centroid clustering (threshold 0.48):
   - First note seeds cluster 1
   - Each subsequent note: compare to each cluster's centroid
   - If cos_sim ≥ 0.48 → add to best cluster, recompute centroid
   - Else → create new cluster
4. Multi-note clusters → topic notes; single-note clusters → also converted
```

Stability guaranteed by: fixed sort order, fixed threshold, centroid recompute on join.
