---
name: reference
description: Collect and organize external knowledge in Bear. USE WHEN the user mentions: 收录/收集/剪藏/收藏/capture/clip/save/保存这篇文章/保存这个网页/存一下/收起来/take a note/看到一篇好文章/发现一篇有意思/interesting article/思维模型/mental model/框架/framework/论文/paper/行业动态/业内趋势/news/trend/教程/tutorial/guide/最佳实践/best practice/工具推荐/tool推荐/归类/分类reference/重新分类/reclassify/找一篇文章/之前收录过/搜一下reference/查收录. Also triggers on references to the #reference tag or knowledge curation. Does NOT trigger on: GTD tasks (use bear-gtd), AI memory (use bear-memory), generic note creation (use bear-notes).
---

# Bear Reference — 外部知识收录

**Prerequisites:** bear-notes skill loaded (MCP operations + Tag Protocol + Note Format Validation).

## 标签体系

```
#reference                          ← 外部知识统一入口
├── #reference/article              ← 文章/博客/长文/深度报告
│   └── #reference/article/mrpeak   ← mrpeak 博客（从 #read/blog 迁移）
├── #reference/book                 ← 书籍/课程（从 #read 迁移，保留书目子标签）
├── #reference/tech                 ← 技术知识（从 #tech 迁移，保留原有子标签）
├── #reference/idea                 ← 概念/思维模型/原则/框架
├── #reference/guide                ← 教程/指南/最佳实践
├── #reference/news                 ← 行业动态/新闻/趋势
├── #reference/tool                 ← 工具/产品推荐与评测
└── #reference/video                ← 视频/播客/演讲笔记
```

### 子标签管理规则

**何时创建：** 某父标签下同主题笔记积累 ≥5 篇时，创建子标签。低于 5 篇不急着分。

**命名：** 小写英文单词，多词用连字符（`claude-code`，非 `claude_code` 或 `ClaudeCode`）。

**层级：** 仅一层子标签（`reference/guide/claude-code` ✓，`reference/guide/claude-code/v2` ✗）。

**子标签哲学：** 不同类别按自身特点选择分组维度，不强求统一。

| 类别 | 分组维度 | 已有子标签 |
|------|---------|----------|
| `article` | 按作者 | `article/mrpeak` |
| `book` | 按书名 | `book/格局`、`book/自私的基因` 等 |
| `tech` | 按技术领域 | `tech/ios`、`tech/ai`、`tech/flutter` 等 |
| `guide` | 按工具/产品 | `guide/bear`、`guide/claude-code` |
| `tool` | 按工具类型 | （待整理） |
| `idea` | 通常不需要 | — |

**何时不建子标签：** 单篇笔记、主题边界模糊、父标签下总量 <10 篇且主题分散。

**新建子标签后：** 更新 📚 Reference Index 对应分组（按子标签拆分为子列表）。

## 笔记格式

### 标准模板

```
# 内容标题
#reference/子标签

> **来源：** [URL 或 文件名]
> **收录：** YYYY-MM-DD

## 关键内容

（用自己的话总结核心观点。不收录全文——这是整理而非搬运。
必要时引用原文摘要，用 `>` 标记）

> 原文关键段落

## 我的思考

（仅在用户有评论性发言时写入。用 `> 💭` 前缀区分用户原话与润色。）

## 关联笔记

- [[相关笔记标题]]：关联说明
```

### 简洁版（快速收录）

```
# 内容标题
#reference/子标签

> **来源：** [URL]
> **收录：** YYYY-MM-DD

## 关键内容

核心要点总结。

## 关联笔记

- [[相关笔记]]
```

### 区段规则

- **标题**：内容标题，不需要日期前缀（收录时间在元数据中）
- **来源**：URL、文件名、或「手动粘贴」「个人想法」
- **「## 关键内容」**：必需。用自己话总结，必要时 `>` 引用原文
- **「## 我的思考」**：条件性。用户有评论→提取；纯指令→省略；不追问
- **「## 关联笔记」**：条件性。至少 1 条关联→保留；无关联→完全省略

## 内容来源与限制

| 来源 | 处理方式 | 约束 |
|------|---------|------|
| 网页 URL | `WebFetch` → `Firecrawl MCP` → `curl` 三级自动降级 | 全失败→人工介入（粘贴/占位/放弃） |
| PDF | `Read` → 提取文本 | Bear MCP 不支持附件上传，原始文件需手动拖入 |
| 用户粘贴 | 直接使用 | 来源标注「手动粘贴」 |
| 用户口述 | 直接整理 | 来源标注「个人想法」 |

> 多级抓取策略详见 `docs/fetch-strategy.md`。

## 分类优先级

**内容的核心价值决定类型，而非形式：**

```
1. 概念/原则/框架？                        → #reference/idea
2. 操作步骤/上手指南？                      → #reference/guide
3. 工具本身（推荐/评测/使用）？              → #reference/tool
4. 技术实现细节/代码/原理？                  → #reference/tech/...
5. 书籍系统化知识？                         → #reference/book
6. 视频/音频内容本身（非文本等价物）？       → #reference/video
7. 时效性信息（行业动态/事件）？              → #reference/news
8. 以上都不匹配                            → #reference/article（兜底）
```

不确定时默认 `#reference/article`，后续用「归类」调整。

---

## 工作流

### Phase 1 — 收录

触发词：收录/收藏/保存这篇文章/存一下/take a note/看到一篇好文章...

```
1. 获取内容（URL 三级自动降级）
   - WebFetch
     → 成功：继续
     → 失败（WebFetch 不可用或目标页面受限）：
       - Firecrawl MCP (`firecrawl_scrape`)
         → 可用且成功：继续
         → 不可用或失败：
           - `curl -sL <URL>` + 提取文本（脚本见 `docs/fetch-strategy.md`）
             → 成功：继续
             → 失败：展示各层原因 + 降级选项（粘贴内容 / 空笔记占位 / 放弃）
   - PDF → Read 读取文本
   - 用户粘贴 → 直接使用
   - 用户口述 → 直接整理

2. 去重检测（URL 来源时）
   - 提取标题 + 域名
   - search_notes(tag: reference, query: "标题关键词")
   - 命中 → 提示「可能已收录过：[[已有笔记]]」
     → a) 跳过 b) 仍创建 c) 打开查看
   - 无命中 → 继续

3. 判断类型 → 匹配子标签（遵循分类优先级）

4. 搜索已有笔记 → 建议关联
   - search_notes(tag: reference, query: "内容关键词")
   - 命中前 5 条 → 询问是否关联
   - 无命中 → 跳过

5. 提取「我的思考」
   - 用户有评论性发言 → 提取
   - 纯指令 → 省略

6. 创建笔记
   - create_note(title, content: 模板, tags: ["reference/子标签"])
   - ⚠️ 立即执行 Note Format Validation（检查行1标题、行2标签、行3空行）

7. 有关联 → 在关联笔记追加双向链接

8. 更新 📚 Reference Index

9. 确认：「已收录到 #reference/子标签：标题」
```

### Phase 2 — 归类

触发词：归类/分类reference/重新分类

> 用于修正已有笔记的分类（所有笔记在收录时已直接分类，没有 inbox）。

```
1. 用户指定目标笔记（标题或搜索定位）
   - 「把 xxx 归类到 idea」→ 精确匹配
   - 「归类 #reference/article 下关于设计模式的」→ 先搜索再逐条确认

2. 确认新子标签（遵循分类优先级）

3. edit_note 修改行2标签（Tag Operation Protocol）

4. 更新 📚 Reference Index 分组

5. 输出：已从 #reference/A → #reference/B
```

### Phase 3 — 检索

触发词：找一篇文章/之前收录过/搜一下reference/查收录

```
1. search_notes(tag: reference, query: "关键词")
2. 展示结果（标题 + 来源 + 收录日期，同名标题附带来源 URL 前缀以区分）
3. 用户选择 → open_note 或读取展示
```

### Phase 4 — 维护索引

📚 Reference Index 笔记（`#reference`）按子标签分组列出全部 Wiki Link。

```
每次操作后自动更新：
- 新收录 → 追加 [[链接]] + 更新数量
- 标签变更 → 从旧分组移除 → 新分组追加

手动触发「重建 reference 索引」→ 全量扫描重建

索引增长控制：
- 某类型 ≤ 30 条 → 全量列出
- 某类型 > 30 条 → 最近 5 条 + 关键词
- 某类型 > 50 条 → 仅类型名 + 数量 + 关键词

容错：
- MOC 更新失败 → 提示用户可稍后手动重建
- 索引允许短暂不一致，不是数据库约束
```

---

## Agent 引用 Reference

### 分层加载

```
Layer 1: 会话启动 → 📚 Reference Index（话题地图，< 1KB）
Layer 2: 任务触发 → 搜索 #reference + 关键词，加载 ## 关键内容
Layer 3: 用户显式 → "参考一下reference" / "之前收录过关于X的"
```

### RULE 4 触发条件（写入 CLAUDE.md）

仅在以下场景搜索 `#reference`：
- 用户明确要求参考 reference
- Agent 知识不足以给出确定答案，需要外部权威来源
- 涉及概念理解/工具选型/最佳实践对比

**不触发**：基础命令用法、常规编码任务、Agent 可直接回答的问题。

---

## 三个 Reference 标签

| 标签 | 内容 | 读者 | 创建方式 |
|------|------|------|---------|
| `#reference` | 外部知识笔记 | 人（agent 按需检索） | reference skill |
| `#ai/memory/reference` | AI 记忆指针 | Agent | Agent 主动写入 |
| `#tme/reference` | 工作参考资料 | 人（工作场景） | 手动创建 |

```
判断：工作内容 → #tme/reference
      外部知识 → 人读 → #reference
      外部知识 → Agent读 → #ai/memory/reference
```

---

## 参考文件

按需通过 Read 加载：

| 文件 | 内容 | 触发条件 |
|------|------|---------|
| `docs/template.md` | 标准模板 + 简洁模板 + 字段说明 | 创建收录笔记时 |
| `docs/fetch-strategy.md` | 多级抓取策略 + curl 提取脚本 + 故障排查 | WebFetch 失败时 |
