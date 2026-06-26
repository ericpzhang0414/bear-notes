# 多级抓取策略

网页内容获取按以下优先级自动降级：

```
WebFetch → Firecrawl MCP → curl → 人工介入
```

## Tier 1: WebFetch

Claude Code 内置工具。直接调用，无需配置。

**已知限制**：WebFetch 在发起请求前会调用 `claude.ai` 上的安全验证服务。如果当前网络阻断了到 `*.claude.ai` 或 `*.anthropic.com` 的连接（常见于企业网络/VPN），验证步骤失败会导致**所有域名**的 WebFetch 请求都被拒绝。错误信息：
```
Unable to verify if domain X is safe to fetch.
This may be due to network restrictions or enterprise security policies blocking claude.ai.
```

**诊断**：如果多个不相关域名（包括 `example.com`）全部返回同样错误，说明是 WebFetch 安全验证层不可达，而非目标网站问题。此时应跳过 WebFetch，直接进入下一级。

## Tier 2: Firecrawl MCP

专业的网页抓取 MCP 服务，走 Firecrawl 云端通道，不依赖 `claude.ai`。

**前置条件**：
1. `npx -y firecrawl-mcp` 可用
2. MCP 配置在 `~/.claude.json` 的 `mcpServers` 中：
```json
"firecrawl": {
  "command": "npx",
  "args": ["-y", "firecrawl-mcp"],
  "env": {
    "FIRECRAWL_API_KEY": "fc-xxxxx"
  }
}
```
3. 会话重启后 MCP 连接生效（运行 `/mcp` 确认）

**API Key**：`firecrawl_scrape` 和 `firecrawl_search` 在无 API Key 时也可免费使用（按 IP 限频）。有 Key 则解锁全部功能（`firecrawl_crawl`、`firecrawl_map` 等）。免费 Key 可在 https://firecrawl.dev 获取。

**使用**：`mcp__firecrawl__firecrawl_scrape(url: "<URL>")`

**优势**：能处理 JS 渲染页面，比 curl 提取质量更高。

## Tier 3: curl + HTML 文本提取

无需任何外部服务，直接 HTTP 请求 + Python HTML→text 转换。

**脚本**：

```bash
curl -sL "<URL>" 2>&1 | python3 -c "
import sys, re, html as html_mod

content = sys.stdin.read()

# 去除 script/style 标签
content = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', content, flags=re.DOTALL)

# 尝试提取 main/article 内容区
main = re.search(r'<main[^>]*>(.*?)</main>', content, re.DOTALL)
if main:
    content = main.group(1)
else:
    article = re.search(r'<article[^>]*>(.*?)</article>', content, re.DOTALL)
    if article:
        content = article.group(1)

# 去除所有 HTML 标签
text = re.sub(r'<[^>]+>', '', content)

# HTML 实体解码
text = html_mod.unescape(text)

# 清洗多余空行
text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
text = text.strip()

print(text[:15000])
"
```

**适用**：大多数静态/SSR 页面。不适合纯 JS 渲染的 SPA 页面。

**参数**：`text[:15000]` 可根据需要调整截断长度。

## 故障排查

| 症状 | 可能原因 | 排查 |
|------|---------|------|
| WebFetch 所有域名失败 | `claude.ai` 被网络阻断 | 用 curl 测试 `claude.ai` 可达性 |
| Firecrawl MCP 不在 `/mcp` 列表 | 配置位置错误或未重启 | 确认配在 `~/.claude.json`，重启会话 |
| Firecrawl 返回 403 | API Key 无效或额度用尽 | 检查 Key 或切换 keyless 模式 |
| curl 返回空内容 | 纯 JS 渲染页面 | 改用 Firecrawl 或人工粘贴 |
