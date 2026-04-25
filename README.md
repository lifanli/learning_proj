# Learning Code Project - Development Branch

`study-proj-current` 是当前项目的开发分支，用来保存代码演进记录。

公开说明、项目介绍和面向展示的内容以 `main` 分支为准。本分支只保留最小 README，不跟踪过程文档、个人笔记、运行数据、日志、知识库输出和前端构建产物。

## 开发约定

- 日常代码修改在本分支完成。
- 稳定后再合并到 `main`。
- API Key 只放在本地 `.env`，不要写进配置文件或提交记录。
- 本地过程文档默认被 `.gitignore` 忽略。

## 常用命令

```powershell
.\start.bat
```

```powershell
conda run -n study-proj python -m pytest -q
```

```powershell
cd frontend
npm run build
```
