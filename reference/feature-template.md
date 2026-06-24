# Feature Note Template

The user has a distinctive pattern for feature/task notes with status tracking:

```markdown
# YYYYMMDD | Feature Name
#tag

## 状态
- [x] 评估
- [x] 开发
- [ ] 体验
- [ ] 测试
- [ ] 合入
- [ ] 发布

## 信息
**需求单：** [link]
**视觉稿：** [link]
**工作量：** Xd
```

## Usage

- Title uses `YYYYMMDD | Feature Name` date-prefixed format
- `## 状态` checklist tracks the feature lifecycle: 评估 → 开发 → 体验 → 测试 → 合入 → 发布
- `## 信息` section captures requirement links, design specs, and work estimates
- Tag should nest under `#tme/feature/YYYY/MM` for proper categorization
