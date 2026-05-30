#!/usr/bin/env python3
"""Comprehensive tests for bear-notes memory module (embed.py + search.py).

Covers: parse_sections, rebuild, update, stats, migrate-plan, search, find-group.
Uses mock Bear data — no real Bear database needed.
"""

import json
import os
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np

# Add memory/ to path
sys.path.insert(0, str(Path(__file__).parent / "memory"))

# ── Mock setup (before importing modules under test) ──
# We patch at the module level so embed.py and search.py don't try to
# import sentence_transformers or call bearcli during tests.

# Pre-compute simple deterministic vectors (8-dim for speed)
def _mock_encode(text, normalize_embeddings=True):
    """Deterministic mock embedding: hash-based 8-dim vector."""
    import hashlib
    h = hashlib.sha256(text.encode()).digest()
    vec = np.array([b / 255.0 for b in h[:8]], dtype=np.float32)
    if normalize_embeddings:
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
    return vec


# ── Test data ──────────────────────────────────────────────────────

OLD_FORMAT_NOTE = """# 「MEM」偏好暗色主题
#ai/memory/user/entry

<!-- type: user agent: claude-code confidence: confirmed updated: 2026-05-20 -->

用户在所有 IDE 和应用中偏好暗色主题。

> claude-code · 2026-05-20 — 用户在设置中明确选择暗色主题"""

OLD_FORMAT_NOTE_2 = """# 「MEM」资深iOS开发者
#ai/memory/user/entry

<!-- type: user agent: claude-code confidence: confirmed updated: 2026-05-25 -->

用户是资深 iOS 开发者，主要使用 Swift 和 Objective-C。

> claude-code · 2026-05-25 — 用户自我介绍"""

OLD_FORMAT_NOTE_FEEDBACK = """# 「MEM」不要重构无关代码
#ai/memory/feedback/entry

<!-- type: feedback agent: claude-code confidence: confirmed updated: 2026-05-30 -->

修改代码时只动与任务直接相关的部分，不要顺手优化相邻代码。

> claude-code · 2026-05-30 — 用户多次强调后记录"""

NEW_FORMAT_NOTE_2_SECTIONS = """# 「MEM」User · 编码偏好
#ai/memory/user/entry

<!-- updated: 2026-05-30 -->

## 偏好暗色主题
<!-- type: user agent: claude-code confidence: confirmed updated: 2026-05-30 -->

用户在所有 IDE 和应用中使用暗色主题。

> claude-code · 2026-05-30 — 用户在 VS Code 设置中明确选择

## 偏好2空格缩进
<!-- type: user agent: claude-code confidence: inferred updated: 2026-05-28 -->

用户在 JS/TS 项目中使用 2 空格缩进，不使用 tabs。

> claude-code · 2026-05-28 — 从项目 .eslintrc 推断"""

NEW_FORMAT_NOTE_1_SECTION = """# 「MEM」User · iOS开发
#ai/memory/user/entry

<!-- updated: 2026-05-25 -->

## 资深iOS开发者
<!-- type: user agent: claude-code confidence: confirmed updated: 2026-05-25 -->

用户是资深 iOS 开发者，主要使用 Swift 和 Objective-C。

> claude-code · 2026-05-25 — 用户自我介绍"""

# Note without valid metadata (should be skipped)
NOTE_NO_METADATA = """# Some Note
#ai/memory/user/entry

No metadata here."""

# Note with ## but no per-section metadata
NOTE_MALFORMED_SECTION = """# 「MEM」User · Broken
#ai/memory/user/entry

<!-- updated: 2026-05-30 -->

## Missing metadata section
No comment here.

> claude-code · 2026-05-30 — test"""


# ── Tests ──────────────────────────────────────────────────────────

class TestParseSections(unittest.TestCase):
    """Test the parse_sections function from embed.py."""

    @classmethod
    def setUpClass(cls):
        # Mock sentence_transformers before importing embed
        cls._st_patcher = patch.dict(sys.modules, {
            'sentence_transformers': MagicMock(),
        })
        cls._st_patcher.start()
        import embed
        cls.embed = embed

    @classmethod
    def tearDownClass(cls):
        cls._st_patcher.stop()

    def test_old_format_single_section(self):
        """Old format (no ##) should return one section with section_index=-1."""
        sections = self.embed.parse_sections(OLD_FORMAT_NOTE)
        self.assertEqual(len(sections), 1)
        sec = sections[0]
        self.assertEqual(sec["section_index"], -1)
        self.assertEqual(sec["section_title"], "")
        self.assertEqual(sec["type"], "user")
        self.assertEqual(sec["agent"], "claude-code")
        self.assertEqual(sec["confidence"], "confirmed")
        self.assertEqual(sec["updated"], "2026-05-20")
        # Text should NOT contain HTML comment
        self.assertNotIn("<!--", sec["text"])
        self.assertIn("偏好暗色主题", sec["text"])

    def test_new_format_two_sections(self):
        """New format should return sections with correct indices."""
        sections = self.embed.parse_sections(NEW_FORMAT_NOTE_2_SECTIONS)
        self.assertEqual(len(sections), 2)

        sec0 = sections[0]
        self.assertEqual(sec0["section_index"], 0)
        self.assertEqual(sec0["section_title"], "偏好暗色主题")
        self.assertEqual(sec0["type"], "user")
        self.assertEqual(sec0["confidence"], "confirmed")
        self.assertNotIn("<!--", sec0["text"])

        sec1 = sections[1]
        self.assertEqual(sec1["section_index"], 1)
        self.assertEqual(sec1["section_title"], "偏好2空格缩进")
        self.assertEqual(sec1["confidence"], "inferred")

    def test_new_format_one_section(self):
        """New format with single section still works."""
        sections = self.embed.parse_sections(NEW_FORMAT_NOTE_1_SECTION)
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0]["section_index"], 0)
        self.assertEqual(sections[0]["section_title"], "资深iOS开发者")

    def test_no_metadata_returns_empty(self):
        """Notes without valid metadata should return empty list."""
        sections = self.embed.parse_sections(NOTE_NO_METADATA)
        self.assertEqual(sections, [])

    def test_malformed_section_skipped(self):
        """Section without metadata should be skipped."""
        sections = self.embed.parse_sections(NOTE_MALFORMED_SECTION)
        self.assertEqual(sections, [])

    def test_section_text_is_clean(self):
        """Section embedding text should not contain HTML comments."""
        sections = self.embed.parse_sections(OLD_FORMAT_NOTE)
        self.assertNotIn("type:", sections[0]["text"])
        self.assertNotIn("<!--", sections[0]["text"])

        sections = self.embed.parse_sections(NEW_FORMAT_NOTE_2_SECTIONS)
        for sec in sections:
            self.assertNotIn("<!--", sec["text"])


class TestEmbedIndexOperations(unittest.TestCase):
    """Test index CRUD operations (rebuild, update, remove, stats)."""

    @classmethod
    def setUpClass(cls):
        cls._st_patcher = patch.dict(sys.modules, {
            'sentence_transformers': MagicMock(),
        })
        cls._st_patcher.start()

        # Patch embed_text to use deterministic mock
        cls._embed_patcher = patch(
            'embed.embed_text',
            side_effect=lambda text: _mock_encode(text).tolist()
        )
        cls._mock_embed = cls._embed_patcher.start()

        import embed
        cls.embed = embed

        # Use temp index file
        cls.tmpdir = tempfile.mkdtemp()
        cls._index_patcher = patch('embed.INDEX_FILE', Path(cls.tmpdir) / "embeddings.jsonl")
        cls._index_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls._st_patcher.stop()
        cls._embed_patcher.stop()
        cls._index_patcher.stop()

    def setUp(self):
        """Clean index before each test."""
        idx_file = self.embed.INDEX_FILE
        if idx_file.exists():
            idx_file.unlink()

    def _mock_memory_notes(self, notes_data):
        """Create mock note dicts for get_memory_notes."""
        return [
            {
                "id": n["id"],
                "title": n.get("title", ""),
                "contentHash": n.get("hash", "abc123"),
                "tags": n.get("tags", []),
            }
            for n in notes_data
        ]

    def test_rebuild_empty(self):
        """Rebuild with no notes should print info, not crash."""
        with patch('embed.get_memory_notes', return_value=[]):
            self.embed.rebuild()
        # Index file should not be created (early return)
        self.assertFalse(self.embed.INDEX_FILE.exists())

    def test_rebuild_old_format(self):
        """Rebuild with old-format notes creates one entry per note."""
        mock_notes = [
            {"id": "NOTE001", "title": "「MEM」偏好暗色主题",
             "hash": "h1", "tags": ["ai/memory/user/entry"]},
            {"id": "NOTE002", "title": "「MEM」iOS开发者",
             "hash": "h2", "tags": ["ai/memory/user/entry"]},
        ]

        def mock_get_content(note_id):
            return {"NOTE001": OLD_FORMAT_NOTE, "NOTE002": OLD_FORMAT_NOTE_2}[note_id]

        with patch('embed.get_memory_notes', return_value=mock_notes), \
             patch('embed.get_note_content', side_effect=mock_get_content):
            self.embed.rebuild()

        entries = self.embed.load_index()
        self.assertEqual(len(entries), 2)
        for e in entries:
            self.assertEqual(e["section_index"], -1)
            self.assertEqual(e["section_title"], "")
            self.assertEqual(e["type"], "user")
        note_ids = {e["note_id"] for e in entries}
        self.assertEqual(note_ids, {"NOTE001", "NOTE002"})

    def test_rebuild_new_format(self):
        """Rebuild with new-format notes creates one entry per section."""
        mock_notes = [
            {"id": "NOTE003", "title": "「MEM」User · 编码偏好",
             "hash": "h3", "tags": ["ai/memory/user/entry"]},
        ]

        with patch('embed.get_memory_notes', return_value=mock_notes), \
             patch('embed.get_note_content', return_value=NEW_FORMAT_NOTE_2_SECTIONS):
            self.embed.rebuild()

        entries = self.embed.load_index()
        self.assertEqual(len(entries), 2)  # 2 sections
        indices = {e["section_index"] for e in entries}
        self.assertEqual(indices, {0, 1})
        titles = {e["section_title"] for e in entries}
        self.assertEqual(titles, {"偏好暗色主题", "偏好2空格缩进"})

    def test_rebuild_mixed_format(self):
        """Rebuild with both old and new format notes."""
        mock_notes = [
            {"id": "OLD1", "title": "「MEM」偏好暗色主题",
             "hash": "h1", "tags": ["ai/memory/user/entry"]},
            {"id": "NEW1", "title": "「MEM」Feedback · 代码原则",
             "hash": "h2", "tags": ["ai/memory/feedback/entry"]},
        ]

        def mock_get_content(note_id):
            if note_id == "OLD1":
                return OLD_FORMAT_NOTE
            return OLD_FORMAT_NOTE_FEEDBACK  # single old-format

        with patch('embed.get_memory_notes', return_value=mock_notes), \
             patch('embed.get_note_content', side_effect=mock_get_content):
            self.embed.rebuild()

        entries = self.embed.load_index()
        self.assertEqual(len(entries), 2)  # 1 old + 1 feedback
        types = {e["type"] for e in entries}
        self.assertEqual(types, {"user", "feedback"})

    def test_update_note(self):
        """Update re-indexes all sections of a note."""
        # First rebuild with old format
        mock_notes = [
            {"id": "NOTE001", "title": "「MEM」偏好暗色主题",
             "hash": "h1", "tags": ["ai/memory/user/entry"]},
        ]

        with patch('embed.get_memory_notes', return_value=mock_notes), \
             patch('embed.get_note_content', return_value=OLD_FORMAT_NOTE):
            self.embed.rebuild()

        self.assertEqual(len(self.embed.load_index()), 1)

        # Now update with new format (2 sections)
        with patch('embed.get_note_content', return_value=NEW_FORMAT_NOTE_2_SECTIONS):
            self.embed.update("NOTE001")

        entries = self.embed.load_index()
        self.assertEqual(len(entries), 2)  # old entry removed, 2 new sections

    def test_remove_note(self):
        """Remove deletes all entries for a note_id."""
        mock_notes = [
            {"id": "NOTE001", "title": "test", "hash": "h1",
             "tags": ["ai/memory/user/entry"]},
        ]
        with patch('embed.get_memory_notes', return_value=mock_notes), \
             patch('embed.get_note_content', return_value=NEW_FORMAT_NOTE_2_SECTIONS):
            self.embed.rebuild()
        self.assertEqual(len(self.embed.load_index()), 2)

        self.embed.remove("NOTE001")
        self.assertEqual(len(self.embed.load_index()), 0)

    def test_stats(self):
        """Stats shows note count, section count, and format distribution."""
        mock_notes = [
            {"id": "N1", "title": "old note", "hash": "h1",
             "tags": ["ai/memory/user/entry"]},
            {"id": "N2", "title": "new note", "hash": "h2",
             "tags": ["ai/memory/user/entry"]},
        ]
        def mock_content(note_id):
            return OLD_FORMAT_NOTE if note_id == "N1" else NEW_FORMAT_NOTE_2_SECTIONS

        with patch('embed.get_memory_notes', return_value=mock_notes), \
             patch('embed.get_note_content', side_effect=mock_content):
            self.embed.rebuild()

        entries = self.embed.load_index()
        self.assertEqual(len(entries), 3)  # 1 old + 2 new

        # Check that stats doesn't crash
        captured = StringIO()
        with patch('sys.stdout', captured):
            self.embed.stats()
        output = captured.getvalue()
        self.assertIn("Notes:", output)
        self.assertIn("Sections:", output)
        self.assertIn("new-format", output)
        self.assertIn("old-format", output)


class TestMigratePlan(unittest.TestCase):
    """Test the --migrate-plan clustering algorithm."""

    @classmethod
    def setUpClass(cls):
        cls._st_patcher = patch.dict(sys.modules, {
            'sentence_transformers': MagicMock(),
        })
        cls._st_patcher.start()

        cls._embed_patcher = patch(
            'embed.embed_text',
            side_effect=lambda text: _mock_encode(text).tolist()
        )
        cls._embed_patcher.start()

        import embed
        cls.embed = embed

    @classmethod
    def tearDownClass(cls):
        cls._st_patcher.stop()
        cls._embed_patcher.stop()

    def _make_old_note(self, nid, content, title="", note_type="user"):
        """Helper to create old-format note data."""
        import re
        meta = self.embed.parse_metadata_comment(content)
        return {
            "id": nid,
            "title": title,
            "contentHash": f"hash_{nid}",
            "tags": [f"ai/memory/{note_type}/entry"],
            "content": content,
            "type": note_type,
            "agent": meta["agent"] if meta else "claude-code",
            "confidence": meta["confidence"] if meta else "confirmed",
            "updated": meta["updated"] if meta else "2026-05-30",
            "vector": _mock_encode(content),
            "created": f"2026-05-{20+int(nid[-1]):02d}",
        }

    def test_empty_migrate_plan(self):
        """Empty database produces empty plan."""
        with patch('embed.get_memory_notes', return_value=[]):
            captured = StringIO()
            with patch('sys.stdout', captured):
                self.embed.migrate_plan()
            plan = json.loads(captured.getvalue())
            self.assertEqual(plan["stats"]["total_old_notes"], 0)

    def test_migrate_only_new_format_skipped(self):
        """Notes with ## sections are skipped (already migrated)."""
        mock_notes = [
            {"id": "N1", "title": "「MEM」User · 编码偏好",
             "contentHash": "h1", "tags": ["ai/memory/user/entry"]},
        ]
        with patch('embed.get_memory_notes', return_value=mock_notes), \
             patch('embed.get_note_content', return_value=NEW_FORMAT_NOTE_2_SECTIONS):
            captured = StringIO()
            with patch('sys.stdout', captured):
                self.embed.migrate_plan()
        plan = json.loads(captured.getvalue())
        self.assertEqual(plan["stats"]["total_old_notes"], 0)

    def test_migrate_ungrouped_single_note(self):
        """Single note goes to ungrouped."""
        mock_notes = [
            {"id": "N1", "title": "「MEM」偏好暗色主题",
             "contentHash": "h1", "tags": ["ai/memory/user/entry"]},
        ]
        with patch('embed.get_memory_notes', return_value=mock_notes), \
             patch('embed.get_note_content', return_value=OLD_FORMAT_NOTE):
            captured = StringIO()
            with patch('sys.stdout', captured):
                self.embed.migrate_plan()
        plan = json.loads(captured.getvalue())
        self.assertEqual(plan["stats"]["total_old_notes"], 1)
        self.assertEqual(plan["stats"]["ungrouped"], 1)
        self.assertEqual(plan["stats"]["topic_notes_to_create"], 1)

    def test_migrate_grouping(self):
        """Similar notes get grouped together."""
        # Two user notes about coding style (similar text)
        content_1 = """# 「MEM」偏好暗色主题
#ai/memory/user/entry

<!-- type: user agent: claude-code confidence: confirmed updated: 2026-05-20 -->

用户在所有 IDE 和应用中偏好暗色主题，认为亮色主题伤眼。

> claude-code · 2026-05-20 — test"""

        content_2 = """# 「MEM」偏好深色模式
#ai/memory/user/entry

<!-- type: user agent: claude-code confidence: confirmed updated: 2026-05-25 -->

用户在所有编辑器中开启深色模式，不喜欢白色背景。

> claude-code · 2026-05-25 — test"""

        mock_notes = [
            {"id": "N1", "title": "「MEM」偏好暗色主题",
             "contentHash": "h1", "tags": ["ai/memory/user/entry"]},
            {"id": "N2", "title": "「MEM」偏好深色模式",
             "contentHash": "h2", "tags": ["ai/memory/user/entry"]},
        ]

        def mock_content(note_id):
            return content_1 if note_id == "N1" else content_2

        # Override embed_text to use real vectors for clustering test
        with patch('embed.get_memory_notes', return_value=mock_notes), \
             patch('embed.get_note_content', side_effect=mock_content):
            captured = StringIO()
            with patch('sys.stdout', captured):
                self.embed.migrate_plan()
        plan = json.loads(captured.getvalue())
        self.assertEqual(plan["stats"]["total_old_notes"], 2)
        # Two nearly-identical notes about dark theme should be grouped
        self.assertEqual(plan["stats"]["grouped"], 2)

    def test_migrate_different_types_not_grouped(self):
        """Notes of different types are never grouped together."""
        mock_notes = [
            {"id": "N1", "title": "「MEM」偏好暗色主题",
             "contentHash": "h1", "tags": ["ai/memory/user/entry"]},
            {"id": "N2", "title": "「MEM」不要重构",
             "contentHash": "h2", "tags": ["ai/memory/feedback/entry"]},
        ]

        def mock_content(note_id):
            return OLD_FORMAT_NOTE if note_id == "N1" else OLD_FORMAT_NOTE_FEEDBACK

        with patch('embed.get_memory_notes', return_value=mock_notes), \
             patch('embed.get_note_content', side_effect=mock_content):
            captured = StringIO()
            with patch('sys.stdout', captured):
                self.embed.migrate_plan()
        plan = json.loads(captured.getvalue())
        self.assertEqual(plan["stats"]["total_old_notes"], 2)
        # Different types should never be in same group
        self.assertEqual(plan["stats"]["grouped"], 0)
        self.assertEqual(plan["stats"]["ungrouped"], 2)

    def test_deterministic_output(self):
        """Same input should produce identical plan (sort stability)."""
        mock_notes = [
            {"id": "N1", "title": "「MEM」A", "contentHash": "h1",
             "tags": ["ai/memory/user/entry"]},
            {"id": "N2", "title": "「MEM」B", "contentHash": "h2",
             "tags": ["ai/memory/user/entry"]},
        ]

        with patch('embed.get_memory_notes', return_value=mock_notes), \
             patch('embed.get_note_content', return_value=OLD_FORMAT_NOTE):
            captured1 = StringIO()
            with patch('sys.stdout', captured1):
                self.embed.migrate_plan()
            plan1 = json.loads(captured1.getvalue())

            captured2 = StringIO()
            with patch('sys.stdout', captured2):
                self.embed.migrate_plan()
            plan2 = json.loads(captured2.getvalue())

        self.assertEqual(plan1, plan2)


class TestSearchFunctions(unittest.TestCase):
    """Test search.py ranking and find-group."""

    @classmethod
    def setUpClass(cls):
        cls._st_patcher = patch.dict(sys.modules, {
            'sentence_transformers': MagicMock(),
        })
        cls._st_patcher.start()

        import search
        cls.search = search

        # Use temp index
        cls.tmpdir = tempfile.mkdtemp()
        cls._index_patcher = patch('search.INDEX_FILE', Path(cls.tmpdir) / "embeddings.jsonl")
        cls._index_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls._st_patcher.stop()
        cls._index_patcher.stop()

    def setUp(self):
        idx_file = self.search.INDEX_FILE
        if idx_file.exists():
            idx_file.unlink()

    def _write_index(self, entries):
        """Write test entries to the mock index file."""
        self.search.INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(self.search.INDEX_FILE, "w") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")

    def _make_entry(self, note_id, type_, section_index=-1, section_title="",
                    updated="2026-05-30", confidence="confirmed", agent="claude-code"):
        """Create a mock index entry with deterministic vector."""
        text = f"{note_id} {section_title} {type_}"
        return {
            "note_id": note_id,
            "section_index": section_index,
            "section_title": section_title,
            "hash": f"hash_{note_id}",
            "type": type_,
            "agent": agent,
            "confidence": confidence,
            "updated": updated,
            "vector": _mock_encode(text).tolist(),
        }

    def test_search_returns_results(self):
        """Basic search should return ranked results."""
        entries = [
            self._make_entry("N1", "user", -1, "", updated="2026-05-30"),
            self._make_entry("N2", "feedback", -1, "", updated="2026-05-28"),
        ]
        self._write_index(entries)

        with patch('search.get_model', return_value=MagicMock()), \
             patch('search.cosine_sim', return_value=0.8):
            results = self.search.search("test query", top=5)
            self.assertEqual(len(results), 2)
            # Results should be sorted by score descending
            self.assertGreaterEqual(results[0]["score"], results[1]["score"])

    def test_search_type_filter(self):
        """Search should filter by type."""
        entries = [
            self._make_entry("N1", "user"),
            self._make_entry("N2", "feedback"),
        ]
        self._write_index(entries)

        with patch('search.get_model', return_value=MagicMock()), \
             patch('search.cosine_sim', return_value=0.8):
            results = self.search.search("test", mem_type="user")
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["type"], "user")

    def test_search_agent_filter(self):
        """Search should filter by agent."""
        entries = [
            self._make_entry("N1", "user", agent="claude-code"),
            self._make_entry("N2", "user", agent="codebuddy"),
        ]
        self._write_index(entries)

        with patch('search.get_model', return_value=MagicMock()), \
             patch('search.cosine_sim', return_value=0.8):
            results = self.search.search("test", agent="codebuddy")
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].get("note_id"), "N2")

    def test_search_results_include_section_info(self):
        """Results for new-format notes include section info."""
        entries = [
            self._make_entry("N1", "user", section_index=0, section_title="偏好暗色"),
            self._make_entry("N1", "user", section_index=1, section_title="偏好缩进"),
        ]
        self._write_index(entries)

        with patch('search.get_model', return_value=MagicMock()), \
             patch('search.cosine_sim', return_value=0.8):
            results = self.search.search("test")
            self.assertEqual(len(results), 2)
            for r in results:
                self.assertIn("section_index", r)
                self.assertIn("section_title", r)

    def test_find_group_match(self):
        """find_group should return the best matching note_id."""
        entries = [
            self._make_entry("N1", "user", 0, "偏好暗色", updated="2026-05-30"),
            self._make_entry("N1", "user", 1, "偏好缩进", updated="2026-05-28"),
            self._make_entry("N2", "user", 0, "iOS开发", updated="2026-05-25"),
        ]
        self._write_index(entries)

        # Mock model.encode to return vector that's more similar to N1 entries
        mock_model = MagicMock()
        n1_vec = np.array(entries[0]["vector"])  # N1 section 0 vector
        mock_model.encode.return_value = n1_vec  # Query matches N1 section 0 exactly

        with patch('search.get_model', return_value=mock_model):
            result = self.search.find_group("暗色主题", mem_type="user", threshold=0.70)

        self.assertIn("note_id", result)
        self.assertEqual(result["note_id"], "N1")
        self.assertGreater(result["similarity"], 0.9)

    def test_find_group_no_match(self):
        """find_group should return empty when below threshold."""
        entries = [
            self._make_entry("N1", "user", 0, "iOS开发"),
        ]
        self._write_index(entries)

        mock_model = MagicMock()
        # Return an orthogonal vector (cosine ≈ 0)
        orthogonal = np.zeros(8, dtype=np.float32)
        orthogonal[0] = 1.0
        mock_model.encode.return_value = orthogonal

        # N1's vector is hash-based, likely not orthogonal but different enough
        # Use a very high threshold to force no match
        with patch('search.get_model', return_value=mock_model):
            result = self.search.find_group("completely unrelated text",
                                            mem_type="user", threshold=0.99)
        self.assertEqual(result, {})

    def test_find_group_empty_index(self):
        """Empty index returns empty result."""
        self._write_index([])
        result = self.search.find_group("test", mem_type="user")
        self.assertEqual(result, {})

    def test_find_group_respects_type_filter(self):
        """find_group only matches within the specified type."""
        entries = [
            self._make_entry("N1", "user", 0, "偏好暗色"),
            self._make_entry("N2", "feedback", 0, "反馈"),
        ]
        self._write_index(entries)

        # Query vector matches N1 exactly
        n1_vec = np.array(entries[0]["vector"])
        mock_model = MagicMock()
        mock_model.encode.return_value = n1_vec

        # With type=feedback, N1 (user) should be excluded
        with patch('search.get_model', return_value=mock_model):
            result = self.search.find_group("test", mem_type="feedback", threshold=0.70)
        # N2 is feedback and the only candidate; similarity depends on hash
        self.assertIn("note_id", result)
        self.assertEqual(result["note_id"], "N2")

    def test_recency_score(self):
        """Recency should be 1.0 for today, decay for past dates."""
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        self.assertAlmostEqual(self.search.recency_score(today), 1.0, places=1)
        # 30 days ago should be ~0.5
        self.assertLess(self.search.recency_score("2026-04-30"), 0.6)

    def test_confidence_boost(self):
        """Confirmed should boost more than inferred."""
        self.assertGreater(
            self.search.confidence_boost("confirmed"),
            self.search.confidence_boost("inferred")
        )

    def test_scoring_formula(self):
        """Hybrid scoring combines all three factors."""
        entries = [
            self._make_entry("N1", "user", updated="2026-05-30", confidence="confirmed"),
        ]
        self._write_index(entries)

        mock_model = MagicMock()
        mock_model.encode.return_value = np.array(entries[0]["vector"])

        with patch('search.get_model', return_value=mock_model):
            results = self.search.search("test")
            self.assertEqual(len(results), 1)
            r = results[0]
            # score = 0.6*sim + 0.3*recency + 0.1*confidence
            expected = 0.6 * r["similarity"] + 0.3 * r["recency"] + 0.1 * r["confidence_bonus"]
            self.assertAlmostEqual(r["score"], expected, places=2)


class TestCosineCentroid(unittest.TestCase):
    """Test cosine similarity and centroid helpers."""

    @classmethod
    def setUpClass(cls):
        cls._st_patcher = patch.dict(sys.modules, {
            'sentence_transformers': MagicMock(),
        })
        cls._st_patcher.start()
        import embed
        cls.embed = embed

    @classmethod
    def tearDownClass(cls):
        cls._st_patcher.stop()

    def test_cosine_same_vector(self):
        """Identical vectors should have cosine similarity of 1.0."""
        v = _mock_encode("test").tolist()
        sim = self.embed.cosine_sim(v, v)
        self.assertAlmostEqual(sim, 1.0, places=5)

    def test_cosine_different_vectors(self):
        """Different vectors should have similarity less than 1."""
        v1 = _mock_encode("dark theme preference").tolist()
        v2 = _mock_encode("iOS developer Swift").tolist()
        sim = self.embed.cosine_sim(v1, v2)
        self.assertLess(sim, 1.0)

    def test_centroid_matches_single_vector(self):
        """Centroid of one vector should equal that vector (normalized)."""
        v = _mock_encode("test")
        v_list = v.tolist()
        c = self.embed.centroid([v_list])
        self.assertAlmostEqual(float(np.dot(c, v_list)), 1.0, places=5)

    def test_centroid_of_similar_vectors(self):
        """Centroid of similar vectors should be close to each."""
        v1 = _mock_encode("dark theme preference for IDE").tolist()
        v2 = _mock_encode("dark mode in all editors").tolist()
        c = self.embed.centroid([v1, v2])
        # Centroid should have positive cosine with both
        self.assertGreater(float(np.dot(c, v1)), 0)
        self.assertGreater(float(np.dot(c, v2)), 0)


class TestCLIParsing(unittest.TestCase):
    """Test command-line argument handling."""

    def test_embed_help(self):
        """embed.py with no args should print help."""
        import subprocess
        result = subprocess.run(
            [sys.executable, "memory/embed.py"],
            capture_output=True, text=True
        )
        self.assertIn("Usage:", result.stdout)
        self.assertIn("--rebuild", result.stdout)
        self.assertIn("--migrate-plan", result.stdout)

    def test_embed_stats_runs(self):
        """embed.py --stats should succeed (even with empty index)."""
        import subprocess
        result = subprocess.run(
            [sys.executable, "memory/embed.py", "--stats"],
            capture_output=True, text=True
        )
        # Should either succeed or print "empty" message
        self.assertIn(result.returncode, [0])

    def test_search_help(self):
        """search.py with no args should print help."""
        import subprocess
        result = subprocess.run(
            [sys.executable, "memory/search.py"],
            capture_output=True, text=True
        )
        self.assertIn("Usage:", result.stdout)
        self.assertIn("--find-group", result.stdout)
        self.assertIn("--threshold", result.stdout)


if __name__ == "__main__":
    # Run tests, exit with non-zero on failure
    unittest.main(verbosity=2)
