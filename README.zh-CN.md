# bear-notes

Bear 笔记的 AI 代理技能 — 涵盖笔记书写规范、MCP 增删改查操作，以及持久化记忆系统。支持 Claude Code、CodeBuddy、WorkBuddy、Gemini CLI、Copilot CLI、Codex CLI。

## 功能

**笔记书写规范** — 结构模板（标题 + 第 2 行标签 + 正文）、标题规则（仅用 `##` / `###`）、Wiki 链接（`[[笔记标题]]`）、文本格式、带状态的任务清单、日期前缀标题（`YYYYMMDD | 标题`）、引用块、脚注、TagCon 图标。

**标签体系** — 7 个顶级标签（`#tme`、`#tech`、`#diary`、`#archive`、`#log`、`#read`、`#family`），按内容匹配到最深层叶子标签的分级分配协议。

**MCP 操作** — 通过 Bear 内置 `bearcli mcp-server` 提供 25 个 MCP 工具，覆盖完整增删改查、Bear 原生搜索语法、标签 / 置顶 / 附件管理、笔记生命周期（废纸篓 / 归档 / 恢复）。安全规则：`overwrite_note` 强制要求 `baseHash`、`edit_note` 原子性编辑、每次写入后验证。

**标签操作协议** — 通过 `edit_note` 精确文本匹配安全编辑标签。绝不使用 `add_tags` / `remove_tags` / `rename_tag` / `delete_tag`（会修改笔记正文）。已文档化三种场景：迁移标签、为无标签笔记添加标签、移除标签。

**持久化记忆系统** — AI 代理记忆采用双层存储（索引笔记 + 条目笔记）。四种 CoALA 记忆类型（user、feedback、project、reference）。语义搜索配合混合排序（60% 相似度 + 30% 新近度 + 10% 置信度）。通过 `#ai/memory` 下的 Bear 笔记跨代理共享记忆。

## 安装

```bash
git clone <repo-url> bear-notes
cd bear-notes
./install.sh
```

自动执行 6 个阶段：
1. 检测已安装的代理（Claude Code / CodeBuddy / WorkBuddy / Gemini / Copilot / Codex）
2. 检查旧版本（如有则备份）
3. 通过软链接安装技能
4. 为各代理配置 Bear MCP
5. 安装记忆系统（Python 依赖 + 嵌入索引重建）
6. 验证安装并输出报告

### 选项

```
./install.sh              # 自动检测、安装、配置 MCP、部署记忆系统、验证
./install.sh --check      # 仅验证，不作修改
./install.sh --force      # 覆盖旧版本时跳过确认
./install.sh --no-memory  # 跳过记忆系统部署（pip 安装 + 索引重建）
./install.sh --uninstall  # 移除所有软链接（MCP 配置保留）
```

## 记忆系统

`memory/` 子目录提供持久化记忆层，使 AI 代理能够在会话之间保持记忆。

| 组件 | 用途 |
|------|------|
| `memory/SKILL.md` | 记忆子技能（格式规范、分类规则、增删改查操作） |
| `memory/embed.py` | 嵌入构建器 — 维护 `~/.bear-memory-index/embeddings.jsonl` |
| `memory/search.py` | 语义搜索，混合排序（`0.6×相似度 + 0.3×新近度 + 0.1×置信度`） |
| `memory/requirements.txt` | Python 依赖：`sentence-transformers>=5.0`、`numpy>=2.0` |

**记忆类型：** `user`（用户身份与偏好）、`feedback`（纠正与行为指引）、`project`（截止时间、约束、决策）、`reference`（外部资源指针）。

**索引：** `~/.bear-memory-index/` 为设备本地，不同步。首次使用或从备份恢复后需运行 `embed.py --rebuild`。

## 项目结构

```
bear-notes/
├── SKILL.md              # 主技能文件（书写规范 + MCP 操作）
├── README.md
├── README.zh-CN.md       # 中文说明
├── install.sh            # 多代理安装器
├── memory/
│   ├── SKILL.md          # 记忆子技能
│   ├── embed.py          # 嵌入构建器 + 索引维护
│   ├── search.py         # 语义搜索
│   └── requirements.txt
└── docs/                 # 设计文档
```

## 更新

技能通过**软链接**安装到本仓库的 `SKILL.md`。在任意设备上更新：

```bash
git pull                 # 技能通过软链接立即生效
./install.sh --check     # 验证一切正常
```

## 支持的代理

| 代理 | 技能路径 | MCP 配置 |
|------|---------|---------|
| Claude Code | `~/.claude/skills/bear-notes/SKILL.md` | `~/.claude.json` |
| CodeBuddy | `~/.codebuddy/skills-marketplace/skills/bear-notes/SKILL.md` | `~/.codebuddy/mcp.json` |
| WorkBuddy | `~/.workbuddy/skills/bear-notes/SKILL.md` | `~/.workbuddy/.mcp.json` |
| Gemini CLI | `~/.gemini/skills/bear-notes/SKILL.md` | `~/.gemini/settings.json` |
| Copilot CLI | `~/.copilot/skills/bear-notes/SKILL.md` | `~/.copilot/config.json` |
| Codex CLI | `~/.codex/skills/bear-notes/SKILL.md` | `~/.codex/mcp.json` |

## 环境要求

- Bear.app 2.8+（内置 `bearcli`）
- `bearcli` 软链接到 `~/bin/bearcli`（或在 PATH 中）
- 代理需支持 MCP stdio 服务
- Python 3.10+，记忆系统需要 `sentence-transformers` 和 `numpy`（`pip3 install -r memory/requirements.txt`）
