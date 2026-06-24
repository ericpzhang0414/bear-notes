# Memory Operations: Update & Forget

## Update Memory

Note: Tag changes must follow the **Tag Operation Protocol** in bear-notes skill.

**For multi-entry notes (has `##` sections):**
```
1. get_note(id, includeContent:true) → content + hash
2. Identify which section to update (by section title or index)
3. Build replacement section content (preserving ## header and metadata)
4. edit_note to replace the section:
   find:    "## <section title>\n<!-- metadata -->\n\n<body>\n\n> source"
   replace: "## <section title>\n<!-- metadata -->\n\n<new body>\n\n> source"
5. embed.py --update <id>  (re-indexes all sections)
```

**For single-section notes:**
```
1. get_note(id, includeContent:true) → content + hash
2. Build updated full note content preserving the format
3. edit_note or overwrite_note per Tag Operation Protocol (bear-notes skill)
4. embed.py --update <id>
```

## Forget Memory

```
1. get_note(id, includeContent:true) → content
2. Count ## sections in the note

3. If note has > 1 section:
   a. Use edit_note to find and remove the target section
      find:    "## <section title>\n<!-- ... -->\n\n<body>\n\n> source"
      replace: "" (empty, being careful with surrounding whitespace)
   b. Optionally update note-level <!-- updated: <date> -->
   c. embed.py --update <id>  (removes that section's embedding)
   d. Index note wiki link stays (the topic still exists)

4. If note has exactly 1 section (or is the last remaining):
   a. trash_note(id) or archive_note(id)
   b. Find the type's index note → edit_note to remove the wiki link line
   c. embed.py --remove <id>
```
