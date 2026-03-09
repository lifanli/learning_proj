# 📦 安装说明

## 快速安装

```bash
cd projects/learning-system

# 方法 1: 使用 pip
pip install -r requirements.txt

# 方法 2: 使用 pip3
pip3 install -r requirements.txt

# 方法 3: 使用 python -m pip
python -m pip install -r requirements.txt
```

## 手动安装核心依赖

```bash
# 核心依赖
pip install flask requests

# 测试依赖
pip install pytest

# 可选：向量数据库
# pip install weaviate-client chromadb
```

## 验证安装

```bash
# 运行测试
python run_tests.py

# 运行主程序
python main.py

# 运行 API 服务
python -m src.api

# 运行 Web 界面
python -m src.web
```

## 预期输出

### 主程序
```
学习智能体系统 v0.1.0
========================================
✓ 核心组件初始化完成
  - Memory Manager: ...
  - Vector DB: ...
  - Skill Manager: ...
  ...
系统就绪!
```

### 测试
```
🧪 学习智能体系统 - 测试开始
==================================================
=== 主程序测试 ===
主程序运行：成功
...
========================================
测试报告
========================================
总测试数：4
通过：4
失败：0
通过率：100.0%
========================================
```

---

**安装完成后即可使用！** 🚀
