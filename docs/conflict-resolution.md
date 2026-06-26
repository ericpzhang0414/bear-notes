# Bear Conflict Resolution

## Detection — 如何发现冲突

| 检测方法 | Bear 搜索语法 | 检测什么 |
|---------|-------------|---------|
| 无标签笔记 | `@untagged` | 同步/导入丢失标签 |
| 同日大量创建 | `@cdate(YYYY-MM-DD)` | 批量导入/同步事件 |
| 重复标题 | 搜同名标题，结果数 > 1 | 同步产生重复副本 |
| 空笔记 | `@empty` | 同步异常空壳 |

## Classification — 冲突类型与处理

| 类型 | 症状 | 处理 |
|------|------|------|
| Type A: 同步重复 | 同名双份：有标签（旧）+ 无标签（新） | `trash_note` 删除无标签副本 |
| Type B: 标签丢失 | 单份笔记，无标签，无同名副本 | `edit_note` Case B 打标签 |
| Type C: 冲突标记残留 | 内容正常但 Bear 侧边栏有冲突 badge | `archive_note` → `restore_note` |

决策树：

```
异常笔记
├─ 存在同名有标签笔记 → Type A → trash_note 删除无标签副本
├─ 不存在同名笔记，内容正常 → Type B → edit_note Case B 打标签
└─ 笔记本身无问题，但 Bear 显示冲突 badge → Type C → archive → restore
```

## Resolution Details

### Type A: 同步重复冲突

这是最常见的情况：iCloud 同步产生同名重复笔记，冲突副本丢失标签、创建时间集中在某一时刻。

**识别特征：**
- 原始版本：有标签，创建时间较早（原始日期）
- 冲突副本：无标签（tags 为空数组），创建时间为同步事件时间（如 `2026-06-26T09:07:26Z`），格式受损（行2为空）

**处理步骤：**
1. 对冲突副本标题执行精确搜索，确认存在同名有标签笔记
2. `trash_note(conflict_id)` 删除无标签副本
3. 验证原始版本标签和内容完好（`get_note(original_id)`）

**示例：**
```
search_notes(query: ""关于 MVC 的一个常见误用"") → 2 results
  原始: 2019-05-20, tags: [reference/tech/ios/architecture] ✓
  冲突: 2026-06-26, tags: [] ✗

trash_note(conflict_id) → location: "trash" ✓
```

### Type B: 标签丢失

笔记内容正常但缺少标签，且不存在同名有标签版本。常见于从其他平台导入或同步异常。

**处理步骤：**
1. `read_note_content(id)` 了解内容，匹配最佳标签
2. 使用 Tag Operation Protocol Case B 加标签
3. Format Validation 确认行1=标题，行2=标签，行3=空行

### Type C: 冲突标记残留

笔记内容已正确（无重复、有标签），但 Bear 侧边栏仍显示冲突 badge。这是 Bear 的 UI 状态缓存问题。

**处理步骤：**
1. `archive_note(id)` → 笔记进入归档
2. `restore_note(id)` → 笔记回到活跃列表
3. 检查 Bear 侧边栏冲突 badge 消失

> 原理：archive/restore 会触发 Bear 重新计算笔记的同步状态，清除残留的冲突标记。

## Post-Resolution Verification

所有类型处理完成后，执行以下验证：

| 检查项 | 方法 | 预期 |
|-------|------|------|
| 冲突副本已清理 | `search_notes(query: "@cdate(YYYY-MM-DD)", location: "notes")` | 仅剩正常笔记 |
| 冲突副本在垃圾箱 | `search_notes(query: "@cdate(YYYY-MM-DD)", location: "trash")` | 数量匹配 |
| 无标签笔记减少 | `search_notes(query: "@untagged")` | 数量减少 |
| 原始笔记完好 | `get_note(original_id)` | 标签和内容 intact |
| Type C badge 清除 | 用户确认 Bear 侧边栏 | 冲突 badge 消失 |
