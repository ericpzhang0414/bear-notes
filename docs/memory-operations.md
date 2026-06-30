# Memory Operations — Update & Forget

完整流程参考，bear-memory skill 的补充文档。

## Update Memory

更新已有记忆的某个 section 内容。

```
1. search_notes(query: "「MEM」", tag: #ai/memory/<type>/entry) → 定位目标 topic note
2. get_note(id, includeContent:true) → 获取完整内容 + hash
3. 定位要修改的 ## section（通过 section title 匹配）
4. edit_note(id, edits: [{
     find:    "exact ## section block including metadata comment and body",
     replace: "updated ## section block"
   }])
5. embed.py --update <note_id>  → 重建该 note 的索引
6. get_note(id) 验证
```

**注意**: 
- find 字符串必须包含完整的 section 内容（从 `## title` 到下一个 `## ` 或文末）
- 更新 metadata comment 中的 `updated` 日期
- 如果改变了语义，需要重新运行 embed rebuild 才能让语义搜索生效

## Forget Memory

删除某个记忆 section 或整条 topic note。

### 删除单个 section

```
1. get_note(id, includeContent:true)
2. edit_note(id, edits: [{
     find:    "## section title\n<!-- ... -->\n\nbody text\n\n> source\n\n",
     replace: ""
   }])
3. embed.py --update <note_id>
```

### 删除整个 topic note

```
1. 从 Index note 中移除对应的 [[wikilink]]
2. trash_note(id) 或 archive_note(id)
3. embed.py --remove <note_id>
```

**选择 trash vs archive:**
- `trash_note`: 不确定是否永久删除时使用（可恢复）
- `archive_note`: 历史记忆，保留但不再活跃使用

## Index Note 维护

每次创建/删除 topic note 后都需要更新对应的 Index note：

```
# 新增 → 追加一行
edit_note(index_id, edits: [{
  find: "## 条目\n\n- [[existing last entry]]",
  replace: "## 条目\n\n- [[existing last entry]]\n- [[new topic note]]"
}])

# 删除 → 移除对应行
edit_note(index_id, edits: [{
  find: "- [[deleted note]]\n",
  replace: ""
}])
```
