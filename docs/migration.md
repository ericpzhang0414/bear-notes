# Memory Format Migration

将旧格式（单条记忆一个笔记）迁移到新格式（多条记忆按 topic 聚合）。

## 格式差异

| 特性 | 旧格式 | 新格式 |
|------|--------|--------|
| 笔记结构 | 一个笔记 = 一条记忆 | 一个笔记 = N 条记忆（## sections） |
| Metadata | note-level comment | per-section comment |
| 数量 | N 条记忆 = N 个笔记 | N 条记忆 = ~N/3 个笔记 |
| 索引 | section_index = -1 | section_index ≥ 0 |

## 三阶段迁移

### Phase 1: 生成迁移计划

```
python3 memory/embed.py --migrate-plan
```

输出 JSON plan：
- `groups`: 语义相近的旧笔记聚类（将合并为一个 topic note）
- `ungrouped`: 无法聚类的单条笔记（各自独立为一个 topic note）
- `stats`: 总数统计

**检查 plan:**
- 查看每个 group 内的 sections，确认聚合合理
- 如果不合理，调整 `MIGRATE_THRESHOLD`（默认 0.48）重新生成
- 注意 topic_title 是自动生成的，可能需要手动调整

### Phase 2: 执行迁移

根据 plan 逐个创建新格式 topic note：

```
对每个 group（cluster）:
  1. 创建新 topic note:
     - 标题: plan 中的 topic_title
     - 标签: #ai/memory/<type>/entry
     - 内容: group 中每个 section 转换为 ## section 格式
     - sections 按 updated DESC 排列（最新在最前）
  2. embed.py --update <new_note_id>
  3. trash_note 每个旧 source note
  4. 更新对应 Index note（移除旧链接，添加新链接）

对每个 ungrouped:
  1. 为单条记忆创建新格式 note（单个 ## section）
  2. 其余同上
```

### Phase 3: 清理验证

```
1. search_notes(query: "「MEM」", tag: #ai/memory) → 确认没有旧格式笔记
2. python3 memory/embed.py --stats → 确认 section_index 全部 ≥ 0
3. python3 memory/search.py "test query" → 确认搜索正常
```

## 注意事项

- 迁移过程中旧笔记仍然可搜索，不会丢失数据
- 使用 trash_note 而非永久删除，出问题可恢复
- 建议按 type 分批迁移（先 user → feedback → project → reference）
- 每批迁移后运行 `embed.py --stats` 验证
