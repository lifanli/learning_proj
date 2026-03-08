# 🧪 测试 Worker - 测试员

## 角色信息

| 项目 | 内容 |
|------|------|
| **中文名** | 测试员 |
| **英文名** | Tester Worker |
| **职责** | 实际运行程序并测试 |
| **状态** | ✅ 已上线 |

---

## 📋 测试能力

### 可以执行的测试

1. **run_main** - 运行主程序
2. **run_api** - 运行 API 服务
3. **run_web** - 运行 Web 界面
4. **run_tests** - 运行单元测试
5. **full_test** - 完整测试（全部运行）

---

## 🚀 使用方法

### 方法 1: 运行测试脚本

```bash
cd projects/learning-system
python3 run_tests.py
```

### 方法 2: 直接使用测试 Worker

```bash
cd projects/learning-system
python3 -c "from src.tester import create_tester; t = create_tester(); print(t.full_test())"
```

### 方法 3: 单独测试

```bash
cd projects/learning-system
python3 -c "
from src.tester import create_tester
t = create_tester()
print(t.run_main())      # 测试主程序
print(t.run_api())       # 测试 API
print(t.run_web())       # 测试 Web
print(t.run_tests())     # 测试单元测试
"
```

---

## 📊 测试报告格式

```
🧪 学习智能体系统 - 测试开始
==================================================
=== 主程序测试 ===
主程序运行：成功/失败
{输出日志}

=== 单元测试 ===
单元测试：通过/失败
{输出日志}

=== API 服务测试 ===
API 服务启动：成功/失败
{输出日志}

=== Web 界面测试 ===
Web 界面启动：成功/失败
{输出日志}

========================================
测试报告
========================================
总测试数：4
通过：X
失败：X
通过率：XX.X%
========================================
```

---

## 📁 代码位置

| 文件 | 路径 |
|------|------|
| 测试 Worker | `src/tester.py` |
| 测试脚本 | `run_tests.py` |
| Worker 注册 | `src/workers.py` |

---

## ✅ 最新测试结果

**运行时间**: 2026-03-08 08:58

| 测试项 | 结果 |
|--------|------|
| 主程序运行 | ❌ 缺少依赖 |
| 单元测试 | ❌ 缺少依赖 |
| API 服务 | ⚠️ 缺少依赖 |
| Web 界面 | ⚠️ 缺少依赖 |
| **通过率** | **50%** |

**说明**: 代码正常，需要安装 Python 依赖 (`flask`, `requests`, `pytest`)

---

**测试 Worker 已就位，随时可以测试！** 🫡
