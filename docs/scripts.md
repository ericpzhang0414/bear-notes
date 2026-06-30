# Memory Scripts Reference

## embed.py — 嵌入索引管理

索引位置: `~/.bear-memory-index/embeddings.jsonl`

### 命令

```
python3 memory/embed.py --rebuild
```
全量重建所有记忆嵌入。扫描 `#ai/memory/*/entry` 标签下所有笔记，解析 sections，生成向量。首次使用或索引损坏时执行。

```
python3 memory/embed.py --update <note_id>
```
增量更新单个笔记。删除该 note_id 的旧索引条目，重新解析所有 sections 并生成新向量。用于创建/编辑记忆后。

```
python3 memory/embed.py --remove <note_id>
```
从索引中移除笔记。用于 trash/archive 记忆后。

```
python3 memory/embed.py --stats
```
显示索引统计：笔记数、section 数（新旧格式分别统计）、类型分布、agent 分布、向量维度。

```
python3 memory/embed.py --migrate-plan
```
生成旧格式 → 新格式迁移计划。详见 `docs/migration.md`。

### 模型

`paraphrase-multilingual-MiniLM-L12-v2` (SentenceTransformers)，384 维归一化向量。支持中英文混合语义匹配。

### 索引格式

每行一个 JSON:
```json
{
  "note_id": "Bear note UUID",
  "section_index": 0,
  "section_title": "## section title",
  "hash": "content hash (仅 --rebuild 时写入)",
  "type": "user|feedback|project|reference",
  "agent": "claude-code|codebuddy|...",
  "confidence": "confirmed|inferred",
  "updated": "YYYY-MM-DD",
  "vector": [0.01, -0.02, ...]
}
```

## search.py — 语义搜索

### 命令

```
python3 memory/search.py "<query>" [options]
```

**Options:**

| 参数 | 说明 | 默认 |
|------|------|------|
| `--top N` | 返回结果数 | 5 |
| `--type <type>` | 过滤记忆类型 | 全部 |
| `--agent <name>` | 过滤来源 agent | 全部 |
| `--raw` | 显示原始分数分解 | off |

### 评分公式

```
score = 0.6 × cosine_similarity + 0.3 × recency + 0.1 × confidence_bonus
```

- **cosine_similarity**: 查询向量与记忆向量的余弦相似度
- **recency**: 指数衰减 `e^(-days/43)`，今天=1.0，30天≈0.37
- **confidence_bonus**: confirmed=1.5, inferred=0.8

### --find-group 模式

```
python3 memory/search.py --find-group "<body text>" --type <type> [--threshold 0.48]
```

用于新建记忆前查找最匹配的已有 topic note。返回最佳匹配的 note_id 和相似度，或空对象表示无匹配（需要创建新笔记）。

阈值 0.48 针对 `paraphrase-multilingual-MiniLM-L12-v2` 调优。临时降低阈值用 `--threshold 0.45`。

### 输出格式

标准搜索:
```
#1  [user]  score=0.8723  section 0: "编码偏好"
    note_id=1234...
    2026-06-15 · confirmed
```

--find-group:
```json
{"note_id": "1234...", "similarity": 0.62, "threshold": 0.48}
```

## recall.py — SessionStart Hook

Claude Code SessionStart hook 调用。加载两项内容注入会话上下文：

1. **Feedback Memory**: `#ai/memory/feedback/entry` 下所有 ## section titles，格式化为 `⛔ RULE | RULE | RULE`
2. **Reference Index**: `📚 Reference Index` 笔记的 ## 分类概览，格式化为紧凑话题地图

输出通常 < 1KB。Agent 按需搜索获取完整内容。

**配置方式**: install.sh Phase Z2 自动添加到 `~/.claude/settings.json` 的 SessionStart hooks。

## 索引维护

- **重建**: `embed.py --rebuild`（首次安装 / 索引损坏时）
- **增量更新**: `embed.py --update <id>`（每次创建/编辑记忆后，由 bear-memory skill 自动调用）
- **无需手动定期重建**: 增量更新保持索引最新
- **索引文件**: `~/.bear-memory-index/embeddings.jsonl`（纯文本，可手动检查）
