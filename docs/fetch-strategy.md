# Multi-Level Content Fetch Strategy

当用户提供了 URL 要求收录时，按以下三级自动降级策略获取内容。

## 策略概览

```
Level 1: WebFetch     ← 最快最方便，但受限较多
Level 2: Firecrawl    ← 功能最强，需要 MCP 已配置
Level 3: curl         ← 最后兜底，无依赖
全部失败 → 人工介入（粘贴/占位/放弃）
```

## Level 1: WebFetch

```
WebFetch(url, prompt: "提取文章正文内容，包含标题、作者、发布时间和全文")
```

**适用**: 大多数公开网页、博客文章
**限制**: 认证页面、部分动态渲染页面可能失败
**失败处理**: → 降级到 Level 2

## Level 2: Firecrawl MCP

```
mcp__firecrawl__firecrawl_scrape(url, formats: ["markdown"])
```

**适用**: JavaScript 渲染页面、WebFetch 失败的页面
**前提**: Firecrawl MCP 已配置在 agent 中
**失败处理**: → 降级到 Level 3

## Level 3: curl

```bash
curl -sL --max-time 15 \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
  "<URL>" | python3 -c "
import sys, re
html = sys.stdin.read()
# Remove scripts and styles
html = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL)
# Remove all HTML tags
text = re.sub(r'<[^>]+>', ' ', html)
# Collapse whitespace
text = re.sub(r'\s+', ' ', text).strip()
# Extract title
title_m = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
if title_m:
    print(f'# {title_m.group(1).strip()}\n')
print(text[:10000])
"
```

**适用**: 所有级别的兜底
**限制**: 
- 只能提取可见文本，丢失格式
- 10KB 截断
- JavaScript 渲染内容不可见
**失败处理**: → 人工介入

## 人工介入

三级全部失败时，向用户展示：

```
内容获取失败：
  WebFetch:  <具体错误>
  Firecrawl: <具体错误 / 未配置>
  curl:      <具体错误>

请选择：
  a) 手动粘贴内容
  b) 创建空笔记占位（稍后手动补充）
  c) 放弃收录
```

## 特殊情况

### PDF 文件

```
Read(file_path: "<本地路径>") → 提取文本
```

注意：Bear MCP 不支持附件上传，原始 PDF 文件需手动拖入 Bear。

### 用户直接粘贴

用户直接提供文本内容 → 跳过所有级别，直接使用。

### 用户口述

用户口头描述内容 → 跳过所有级别，直接整理。来源标注「个人想法」。

## 故障排查

| 现象 | 可能原因 | 解决 |
|------|---------|------|
| WebFetch 返回空 | 页面需要 JavaScript | 降到 Level 2 |
| Firecrawl 不可用 | MCP 未配置或 API key 未设置 | 降到 Level 3 |
| curl 返回 403 | 网站有反爬保护 | 尝试添加更多 headers 或人工介入 |
| 所有级别返回空 | 页面是纯 SPA 或需要登录 | 人工介入 |
