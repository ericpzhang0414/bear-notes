# Script Integration & Index Maintenance

## embed.py

Maintains `~/.bear-memory-index/embeddings.jsonl`:

```
embed.py --rebuild              Full rebuild from Bear notes (per-section indexing)
embed.py --update <note_id>     Re-index all sections of a note
embed.py --remove <note_id>     Remove all entries for a note from index
embed.py --stats                Show note count + section count + type distribution
embed.py --migrate-plan         Generate migration plan (old → new format) as JSON
```

## search.py

Semantic search with hybrid ranking + topic grouping:

```
search.py "<query>"                    Top 5 results, all types
search.py "<query>" --top 10           Top 10 results
search.py "<query>" --type user        Filter by memory type
search.py "<query>" --agent claude-code  Filter by source agent
search.py "<query>" --raw              Show score breakdown (with section info)
search.py --find-group "<text>"        Find best topic note for new memory
           --type <type> [--threshold 0.48]
```

Ranking formula: `score = 0.6 × similarity + 0.3 × recency + 0.1 × confidence_boost`

Results include `section_index` and `section_title` when available (new format).

Scripts call `bearcli` CLI internally to read note content. They do NOT modify Bear notes — all writes go through MCP tools.

## Index Maintenance

- `~/.bear-memory-index/` is per-device, not synced
- Run `embed.py --rebuild` on first use, after restoring from backup, or after migration
- Run `embed.py --update <id>` after every memory create/update/forget
- Each `##` section gets its own index entry with `section_index`, `section_title`
- Index entries reference notes by `id` + `contentHash` — if a note is edited outside the memory workflow, re-index with `--update <id>`
