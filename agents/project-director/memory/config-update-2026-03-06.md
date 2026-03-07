# 团队配置更新 - 2026-03-06 13:40

## 管理员要求
- 把所有 Agent 的中文名字更新到 openclaw.json 配置中
- 让 Manager 能清楚显示谁在发消息
- 解决"不知道谁在发消息"的问题

## 已完成的配置更新

| Agent ID | 原 name | 新 name | 配置文件 |
|----------|---------|---------|----------|
| frontend-engineer | Frontend Engineer | 陈明轩 \| 前端工程师 | openclaw.json |
| review-worker | 反问 Worker | 陆思琪 \| 质量审查专员 | openclaw.json |
| search-worker | 搜索 Worker | 苏婉儿 \| 信息搜集专员 | openclaw.json |
| project-director | 项目总监 | 林小雅 \| 项目总监 | openclaw.json |

## 配置格式
```json
{
  "agentId": "xxx",
  "name": "中文名 | 岗位名称",
  ...
}
```

## 效果
- Matrix 消息会显示：`陈明轩 | 前端工程师 💕`
- 管理员一眼就能看出是谁发的消息
- 不再混淆

## 下一步
- 等待 Manager 重新加载配置
- 后续创建的新角色也要遵循这个命名规范
