# bear-notes: AI Agent 持久记忆体系

## Context

bear-notes skill 已完成 CLI→MCP 迁移和多 agent 分发。在此基础上增加 AI agent 持久记忆能力，使 Bear 笔记可作为 agent 的长期记忆后端。遵循业界 CoALA 框架和 80/20 模式（结构化索引覆盖 80% 查询，语义搜索覆盖 20%）。

## 架构

```
bear-notes-skill/
├── SKILL.md                      # 基础层：笔记约定 + MCP 操作 + Tag Protocol（不变）
├── memory/
│   ├── SKILL.md                  # 记忆层：格式定义 + 操作协议 + 分类规则
│   ├── embed.py                  # 嵌入生成/更新
│   ├── search.py                 # 语义搜索 + 混合排序
│   └── requirements.txt          # sentence-transformers
├── install.sh
└── README.md
```

基础层（SKILL.md）提供笔记 CRUD 原语，不感知记忆业务。记忆层（memory/SKILL.md）调用基础层原语，独立演进。

## 记忆标签体系

所有记忆笔记归入顶层 `#ai` 标签下：

| 标签 | 用途 | 笔记角色 |
|------|------|---------|
| `#ai/memory/user` | 用户偏好/身份/习惯 | 索引笔记 |
| `#ai/memory/user/entry` | 具体用户记忆 | 条目笔记 |
| `#ai/memory/feedback` | 用户纠正/反馈 | 索引笔记 |
| `#ai/memory/feedback/entry` | 具体反馈记忆 | 条目笔记 |
| `#ai/memory/project` | 项目上下文/约束 | 索引笔记 |
| `#ai/memory/project/entry` | 具体项目记忆 | 条目笔记 |
| `#ai/memory/reference` | 外部资源索引 | 索引笔记 |
| `#ai/memory/reference/entry` | 具体引用记忆 | 条目笔记 |

## 记忆类型

沿用 Claude Code 内置系统的四种类型：

| 类型 | 含义 | 例子 |
|------|------|------|
| `user` | 用户身份、偏好、习惯、知识背景 | 编码风格、语言偏好 |
| `feedback` | 用户对 agent 行为的纠正/认可 | 不要 mock 数据库 |
| `project` | 项目上下文、决策、约束 | 6 月冻结合入 |
| `reference` | 外部资源索引 | Linear 项目 INGEST |

## 双层存储模型

索引笔记 + 条目笔记，兼顾快速概览和并发安全：

```
#ai/memory/user           ← 索引笔记（1 次调用概览全部 user 记忆）
  ├── 条目 1               ← 独立笔记，baseHash 保护并发
  ├── 条目 2
  └── 条目 N
```

**读取**：概览 → 读索引（1 次调用），详情 → `get_note(entry_id)`

**搜索**：`search_notes(query, tag: #ai/memory/*/entry)` → 排序 → 取 top N

**写入**：`create_note` 新建条目 → `edit_note` 更新索引

**删除**：`trash_note` 条目 → `edit_note` 更新索引

## 条目笔记格式

```markdown
# 「MEM」用户偏好：编码风格使用 tabs
#ai/memory/user/entry

<!-- type: user agent: claude-code confidence: confirmed updated: 2026-05-29 -->

用户偏好使用 tabs 而非 spaces 进行缩进。

> claude-code · 2026-05-29 — 用户指出「用 tab，别用 space」
```

| 行 | 内容 | 说明 |
|----|------|------|
| 1 | `# 「MEM」<描述>` | 标题。「MEM」前缀 + 语义描述，Bear 侧边栏可区分 |
| 2 | `#ai/memory/<type>/entry` | 标签 |
| 3 | 空行 | |
| 4 | `<!-- type: ... agent: ... -->` | HTML 注释。脚本可解析，Bear 预览不渲染 |
| 5 | 空行 | |
| 6+ | 正文 | 自然语言，1-3 段 |
| 最后 | `> agent · date — source` | 溯源行 |

**元数据字段：**

| 字段 | 必填 | 取值 |
|------|------|------|
| `type` | ✅ | `user` / `feedback` / `project` / `reference` |
| `agent` | ✅ | `claude-code` / `codebuddy` / `workbuddy` / ... |
| `confidence` | ✅ | `confirmed` / `inferred` |
| `updated` | ✅ | `YYYY-MM-DD` |

## 索引笔记格式

```markdown
# 「MEM」User Memory Index
#ai/memory/user

<!-- type: user agent: all updated: 2026-05-29 -->

## 条目

- [[「MEM」用户偏好：编码风格使用 tabs]] — 使用 tabs 缩进
- [[「MEM」用户偏好：简洁错误处理]] — 不要过度防御
- [[「MEM」用户角色：iOS 高级工程师]] — 主要技术栈
```

Wiki link 列表，Bear 原生可跳转。新增记忆时在末尾追加一行。

## 分类规则（memory/SKILL.md 指令）

Agent 按决策树分类：
```
- 关于「你是谁、你喜欢什么、怎么工作」→ user
- 关于「你做错了、应该这样做」→ feedback
- 关于「这个项目正在发生什么、约束条件」→ project
- 关于「信息在哪里能找到」→ reference
- 不确定 → 默认 project
```

Agent 创建记忆后输出分类理由，用户在 Bear 中可直接修改标签纠正。

## 检索排序

```
score = 0.6 × cosine_similarity(query_embed, memory_embed)
      + 0.3 × recency_score(days_since_updated)
      + 0.1 × confidence_boost(1.5 for confirmed, 0.8 for inferred)
```

`embed.py` 维护向量索引（`~/.bear-memory-index/`），`search.py` 混合排序返回 top N。

## 跨设备索引同步

`~/.bear-memory-index/` 不在 iCloud 范围内，每台设备独立维护。首次安装时 `embed.py --rebuild` 扫描所有 `#ai/memory/*/entry` 笔记重建索引。后续增量更新（agent 每次记忆操作后调用 `embed.py --update <note_id>`）。

## 文件变更

| 操作 | 路径 | 说明 |
|------|------|------|
| ✅ 新增 | `memory/embed.py` | 嵌入生成/更新（已完成） |
| ✅ 新增 | `memory/search.py` | 语义搜索 + 排序（已完成） |
| ✅ 新增 | `memory/requirements.txt` | sentence-transformers >= 5.0, numpy >= 2.0 |
| 待完成 | `memory/SKILL.md` | 记忆系统 skill |
| 不变 | `SKILL.md` | 基础层，无需修改 |

## 存储产物

| 产物 | 位置 | 同步方式 |
|------|------|---------|
| 记忆笔记（正文） | Bear 数据库，标签 `#ai/memory/*/entry` | iCloud 自动同步 |
| 向量索引 | `~/.bear-memory-index/embeddings.jsonl` | 每台设备独立，`embed.py --rebuild` 重建 |

向量索引不入 git 仓库。iCloud 保证笔记住内容跨设备一致；每台设备在首次使用时运行 `embed.py --rebuild` 扫描本地 Bear 数据库重建索引。

## 可行性验证（2026-05-30）

测试环境：Python 3.9, sentence-transformers 5.1.2, all-MiniLM-L6-v2 (384-dim), Bear 2.8+

### 测试流程

```
1. 创建测试记忆笔记（符合格式规范）
2. embed.py --rebuild   扫描 Bear → 生成嵌入 → 写入 JSONL
3. search.py 多组 query 测试语义搜索 + 混合排序
4. embed.py --stats     验证索引状态
```

### 测试结果

| 测试项 | 结果 | 详情 |
|--------|------|------|
| embed.py --rebuild | ✅ | 扫描 2 条记忆，生成 384 维向量，写入 embeddings.jsonl |
| 中文语义搜索 | ✅ | `"代码格式化规范"` → 匹配 "编码风格使用 tabs"，score=0.69 |
| 英文语义搜索 | ✅ | `"tabs vs spaces"` → sim=0.47, recency=0.98, conf=1.5, score=0.72 |
| 类型筛选 | ✅ | `--type user` 正确过滤 |
| --raw 分数分解 | ✅ | similarity / recency / confidence 三项分别可见 |
| 混合排序 | ✅ | 相关 query 0.72 vs 随机 query 0.49，Δ = 0.23，区分度可用 |
| embed.py --stats | ✅ | Types: {user: 2}, Agents: {claude-code: 2}, Dims: 384 |
| 模型加载时间 | ~3s | 首次加载 all-MiniLM-L6-v2，后续调用 < 10ms |
| 跨设备索引重建 | ✅ | `embed.py --rebuild` 从 Bear 笔记重新生成索引 |

### 已知限制

- **embed.py 首次运行需联网**下载模型（~80MB），之后完全离线
- **基线分数偏高**（随机 query score=0.49）：只有 2 条同类记忆时区分度有限，记忆数量增加后相对排序改善
- **不支持中文同义词扩展**：例如 "tab" vs "缩进" 的关系依赖模型训练数据而非显式注入
- **`read_note_content` offset/limit bug**（Bear MCP Known Issue）：全量读取备用，不影响当前功能
