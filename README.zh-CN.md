# bear-notes

Bear 笔记的 AI 代理技能 — 涵盖笔记书写规范、MCP 增删改查操作，以及主动式持久化记忆系统。支持 Claude Code、CodeBuddy、WorkBuddy、Gemini CLI、Copilot CLI、Codex CLI。

## 功能

**笔记书写规范** — 结构模板（标题 + 第 2 行标签 + 正文）、标题规则（仅用 `##` / `###`）、Wiki 链接（`[[笔记标题]]`）、文本格式、带状态的任务清单、日期前缀标题（`YYYYMMDD | 标题`）、引用块、脚注、TagCon 图标。

**标签体系** — 7 个顶级标签（`#tme`、`#tech`、`#diary`、`#archive`、`#log`、`#read`、`#family`），按内容匹配到最深层叶子标签的分级分配协议。

**MCP 操作** — 通过 Bear 内置 `bearcli mcp-server` 提供 25 个 MCP 工具，覆盖完整增删改查、Bear 原生搜索语法、标签 / 置顶 / 附件管理、笔记生命周期（废纸篓 / 归档 / 恢复）。安全规则：`overwrite_note` 强制要求 `baseHash`、`edit_note` 原子性编辑、每次写入后验证。

**标签操作协议** — 通过 `edit_note` 精确文本匹配安全编辑标签。绝不使用 `add_tags` / `remove_tags` / `rename_tag` / `delete_tag`（会修改笔记正文）。已文档化三种场景：迁移标签、为无标签笔记添加标签、移除标签。

**主动式记忆系统** — 代理在每次会话开始时自动召回用户偏好、反馈和项目上下文。在学习到新偏好、收到纠正或捕获决策时主动写入记忆——无需用户说「记住这个」。主题分组笔记（`「MEM」Type · Topic`）配合 `##` sections，语义搜索 + 混合排序，确定性聚类。四种 CoALA 记忆类型（user、feedback、project、reference）。通过 `#ai/memory` 下的 Bear 笔记跨代理共享记忆。

## 安装

```bash
git clone <repo-url> bear-notes
cd bear-notes
./install.sh
```

自动执行 7 个阶段：
1. 检测已安装的代理（Claude Code / CodeBuddy / WorkBuddy / Gemini / Copilot / Codex）
2. 检查旧版本（如有则备份）
3. 通过软链接安装技能
4. 为各代理配置 Bear MCP
5. 安装记忆系统（Python 依赖 + 嵌入索引重建）
6. 在各代理全局指令中配置主动记忆召回
7. 验证安装并输出报告

### 选项

```
./install.sh              # 自动检测、安装、配置 MCP、部署记忆系统、配置召回、验证
./install.sh --check      # 仅验证，不作修改
./install.sh --force      # 覆盖旧版本时跳过确认
./install.sh --no-memory  # 跳过记忆系统部署（pip 安装 + 索引重建）
./install.sh --no-recall  # 跳过全局指令自动配置
./install.sh --uninstall  # 移除所有软链接（MCP 配置保留）
```

### 常用命令

```bash
# 记忆索引与搜索
python3 memory/embed.py --rebuild          # 重建嵌入索引
python3 memory/embed.py --stats            # 显示笔记数、section 数、类型分布
python3 memory/search.py "<查询>"          # 语义搜索（含 section 信息）
python3 memory/search.py --find-group "文本" --type user  # 查找最佳 topic 笔记

# 迁移（旧 1:1 格式 → topic 分组）
python3 memory/embed.py --migrate-plan     # 阶段 1：预览分组方案（只读 JSON）
# → Agent 通过 MCP 执行                    # 阶段 2：创建 topic 笔记，归档旧笔记
python3 memory/embed.py --rebuild          # 阶段 3：重建索引

# 测试
python3 test_memory.py                     # 运行完整测试套件（37 个测试）
```

## 记忆系统

`memory/` 子目录提供主动式持久化记忆层，AI 代理无需用户显式指令即可在会话间保持记忆。

**格式：** 主题分组笔记 — 每个主题一张笔记（如 `「MEM」User · 编码偏好`），每个 `##` section 是一条记忆条目。最新条目排在最前（追加用 `position="beginning"`）。通过 max-section 余弦相似度自动分组（阈值 0.48，基于 `paraphrase-multilingual-MiniLM-L12-v2` 校准）。

**主动协议：** 代理在会话开始时静默召回记忆，无需被要求即可写入新记忆。详见 `memory/SKILL.md` → Proactive Memory Protocol。

| 组件 | 用途 |
|------|------|
| `memory/SKILL.md` | 记忆子技能 — 格式规范、分类规则、主动协议、CRUD 操作 |
| `memory/embed.py` | 嵌入构建器 — 每个 section 独立索引，`--migrate-plan` 聚类迁移，`--stats` |
| `memory/search.py` | 语义搜索 + 混合排序，`--find-group` topic 匹配 |
| `memory/requirements.txt` | Python 依赖：`sentence-transformers>=5.0`、`numpy>=2.0` |
| `test_memory.py` | 完整测试套件 — 37 个测试覆盖所有组件 |

**记忆类型：** `user`（用户身份与偏好）、`feedback`（纠正与行为指引）、`project`（截止时间、约束、决策）、`reference`（外部资源指针）。

**模型：** `paraphrase-multilingual-MiniLM-L12-v2` — 针对多语言（中文 + 英文）语义相似度优化。

**排序公式：** `0.6×相似度 + 0.3×新近度 + 0.1×置信度`。搜索使用 per-section 向量，分组使用 max section 相似度（find-group）或质心比较（migrate-plan）。

**索引：** `~/.bear-memory-index/` 为设备本地，不同步。首次使用、备份恢复后或迁移后需运行 `embed.py --rebuild`。

## 项目结构

```
bear-notes/
├── SKILL.md              # 主技能文件（书写规范 + MCP 操作）
├── README.md / README.zh-CN.md
├── install.sh            # 多代理安装器（7 阶段）
├── test_memory.py        # 测试套件（37 个测试）
├── memory/
│   ├── SKILL.md          # 记忆子技能（主动协议 + 格式 + 操作）
│   ├── embed.py          # 嵌入构建器 + 索引 + migrate-plan
│   ├── search.py         # 语义搜索 + find-group
│   └── requirements.txt
└── docs/                 # 设计文档
```

## 主动记忆召回

`install.sh` 自动向各代理的全局指令文件注入记忆召回块：

| 代理 | 全局指令文件 | 自动配置 |
|------|------------|---------|
| Claude Code | `~/.claude/CLAUDE.md` | ✅ |
| CodeBuddy | `~/.codebuddy/CODEBUDDY.md` | ✅ |
| WorkBuddy | `~/.workbuddy/WORKBUDDY.md` | ✅ |
| Gemini CLI | `~/.gemini/GEMINI.md` | ✅ |
| Copilot CLI | `~/.copilot/instructions.md` | ✅ |
| Codex CLI | `~/.codex/CODEX.md` | ✅ |

注入的指令块要求代理：
- 会话开始时召回 `#ai/memory/user/entry` 和 `#ai/memory/feedback/entry`
- 学习到用户偏好、纠正或决策时主动创建记忆
- 绝不等待用户说「记住这个」

跳过此步骤：`./install.sh --no-recall`

## 更新

技能通过**软链接**安装到本仓库的 `SKILL.md`。在任意设备上更新：

```bash
git pull                 # 技能通过软链接立即生效
./install.sh --check     # 验证一切正常
```

### 迁移（旧 1:1 格式 → Topic 分组）

```bash
python3 memory/embed.py --migrate-plan   # 阶段 1：预览分组方案（只读）
# → Agent 通过 MCP 执行                   # 阶段 2：创建 topic 笔记，归档旧笔记
python3 memory/embed.py --rebuild        # 阶段 3：重建索引
```

## 支持的代理

| 代理 | 技能路径 | MCP 配置 | 全局指令 |
|------|---------|---------|---------|
| Claude Code | `~/.claude/skills/bear-notes/SKILL.md` | `~/.claude.json` | `~/.claude/CLAUDE.md` |
| CodeBuddy | `~/.codebuddy/skills-marketplace/skills/bear-notes/SKILL.md` | `~/.codebuddy/mcp.json` | `~/.codebuddy/CODEBUDDY.md` |
| WorkBuddy | `~/.workbuddy/skills/bear-notes/SKILL.md` | `~/.workbuddy/.mcp.json` | `~/.workbuddy/WORKBUDDY.md` |
| Gemini CLI | `~/.gemini/skills/bear-notes/SKILL.md` | `~/.gemini/settings.json` | `~/.gemini/GEMINI.md` |
| Copilot CLI | `~/.copilot/skills/bear-notes/SKILL.md` | `~/.copilot/config.json` | `~/.copilot/instructions.md` |
| Codex CLI | `~/.codex/skills/bear-notes/SKILL.md` | `~/.codex/mcp.json` | `~/.codex/CODEX.md` |

## 环境要求

- Bear.app 2.8+（内置 `bearcli`）
- `bearcli` 软链接到 `~/bin/bearcli`（或在 PATH 中）
- 代理需支持 MCP stdio 服务
- Python 3.10+，记忆系统需要 `sentence-transformers` 和 `numpy`（`pip3 install -r memory/requirements.txt`）
