# Qwen 接入与学习项目优化建议

## 本次已经落地的改动

### 1. 给项目加了可复用的 LLM 模板层
新增文件：`src/core/llm_presets.py`

现在项目可以识别并应用三类模板：
- `custom_openai`：通用 OpenAI 兼容接口
- `dashscope_qwen`：阿里云百炼 / DashScope，面向 Qwen 3.6
- `anthropic_claude`：Claude

这样做的意义是：
- 避免手工改 `provider` / `base_url` / `api_mode` / `api_key_env` 时互相打架
- 后续你要继续接更多模型时，不需要到处写 if/else
- 系统设置页终于能表达“这是一个模型接入方案”，而不是只有零散字段

### 2. 默认配置已经切到 DashScope / Qwen 文本优先方案
更新文件：`config/settings.yaml`

当前默认配置：
- `llm.provider = openai`
- `llm.base_url = https://dashscope.aliyuncs.com/compatible-mode/v1`
- `llm.api_key_env = DASHSCOPE_API_KEY`
- `llm.api_mode = chat_completions`
- `llm.model = qwen3.6-max-preview`
- `llm.enable_thinking = true`
- `models.fast = qwen3.6-plus`
- `models.deep = qwen3.6-max-preview`
- `models.vision = qwen3.6-plus`

也就是：
- 主文本链路先用 `qwen3.6-max-preview`
- 快速/通用任务和未来视觉入口预留 `qwen3.6-plus`

### 3. Streamlit 设置页可以直接选 DashScope/Qwen 模板
更新文件：`app.py`

现在系统设置页新增了：
- `LLM 方案模板` 选择框
- DashScope/Qwen 的说明文案
- `DASHSCOPE_API_KEY` 的明确提示
- DashScope 推荐的 `base_url` / `api_mode` 帮助信息
- API 连通性区域也会检查 `DASHSCOPE_API_KEY`

你可以直接：
1. 打开“系统设置”
2. 选择 `阿里云百炼 / DashScope（Qwen 文本优先）`
3. 填写：
   - 环境变量名：`DASHSCOPE_API_KEY`
   - 或直接在本地临时填写 API Key
4. 保存配置

### 4. Worker 默认模型也和新配置对齐了
更新文件：
- `src/core/worker.py`
- `src/researchers/wechat_reader.py`
- `src/storage/rag_manager.py`

这一步的意义是：
- 不只是设置文件改了
- 连代码里“兜底默认值”和注释语义也同步到了 Qwen 3.6
- 减少未来有人忘记配 models 时出现老模型名回退的问题

### 5. 增加了模板测试
新增文件：`tests/test_llm_presets.py`

已验证：
- DashScope/Qwen 模板能正确填充文本优先配置
- 切回 Anthropic 时能清掉 OpenAI 专属字段
- 当前配置结构能正确识别为 DashScope/Qwen 模板

## 我建议你怎么使用

### 最简单的使用方式
推荐环境变量方式：

```bash
export DASHSCOPE_API_KEY=  # 在本机填写，不要提交真实 Key
```

然后启动项目。

如果你暂时只想在本机快速试：
- 也可以在系统设置页里直接填 API Key
- 但这更适合临时调试，不适合长期保存

### 你现在这套模型分工，我认为是合理的
当前建议分工：
- `llm.model = qwen3.6-max-preview`：主文本规划、深度总结、课程结构生成
- `models.fast = qwen3.6-plus`：轻量标签、分类、一般提取类任务
- `models.deep = qwen3.6-max-preview`：课程规划、章节规划、复杂归纳
- `models.vision = qwen3.6-plus`：先占位，后续再开图片理解测试

这是一个比较好的“先把文本链路做稳，再逐步开多模态”的路线。

---

## 我对你的学习项目的理解

我现在对这个项目的判断更明确了：

它不是一个普通的“资料抓取器”，而是在往“个人学习操作系统”走。

它的核心闭环其实是：
1. 从课程 / GitHub / 论文 / 网页抓素材
2. 把素材清洗、打标签、结构化
3. 形成课程表 / 学习路径
4. 再把这些材料组织成面向人的知识输出

也就是说，这个项目真正的价值不是“调一个模型回答问题”，而是：

“把外部知识源变成可持续学习、可追踪、可出版的个人知识生产流水线。”

这是很对的方向。

## 我认为这次接入 Qwen 的意义，不只是多一个模型

### 1. 它让项目更像“自己的学习基础设施”
以前项目的 LLM 层虽然能用，但更像“谁能跑就先接谁”。

这次把 DashScope/Qwen 作为一个明确方案接进去以后，项目开始具备：
- 可切换模型供应商
- 可保存稳定模板
- 可从 UI 配置
- 可在代码里统一回落

这说明你的项目开始从“实验脚本集合”走向“长期维护系统”。

### 2. 文本优先是对的，不要急着先上多模态
你现在先强调：
- 文本回答质量
- 学习路径组织
- 引用与出处
- 长文本整合

这个判断我认为非常对。

因为你的项目当前真正的瓶颈，其实不是“能不能看图”，而是：
- 是否能把材料组织成稳定、可信、连续的学习内容
- 是否能把来源、代码、论文引用说清楚
- 是否能把多来源内容融合成对学习者有帮助的结构

这些问题，本质上都先是文本问题。

### 3. Qwen 3.6-max-preview 很适合放在“深度整理层”
从你给的调用例子看，你关心的是：
- thinking 模式
- 流式输出 reasoning + final answer
- 兼容 OpenAI SDK

这和你的项目非常匹配，因为你的几个核心环节其实都不是简单问答，而是：
- 课程规划
- 主题分解
- 素材归并
- 章节生成
- 质量审查

这些都更像“带中间推理的文本加工任务”。

所以我建议你把 `qwen3.6-max-preview` 主要放在：
- `CurriculumAgent`
- `TopicExplorer`
- `BookPlanner`
- `SectionWriter`
- `QualityReviewer`

而不是把它浪费在所有轻量提取任务上。

---

## 我觉得这个学习项目接下来最值得做的 4 件事

### A. 把“模型接入配置”和“任务用模型策略”拆开
现在项目已经有：
- `llm.model`
- `models.fast/deep/vision`

下一步建议再更明确一点：
- 配置层：这个供应商是谁，API 怎么接
- 策略层：哪个任务用 fast，哪个任务用 deep

这样以后你换模型时，不会影响任务编排。

### B. 给关键学习任务建立“文本质量约束”
比起多模态，我更建议先把这些规则做强：
- 引用代码必须标来源链接
- 引用论文必须标题目/作者/年份/链接
- 长文总结必须保留章节层次
- 输出学习笔记时要区分“事实”“解释”“建议”

这会直接提升你项目最终内容的可信度。

### C. 把 reasoning 当成“调试信号”，不是最终展示物
Qwen thinking 很有价值，但我建议：
- 开发阶段：记录 reasoning，用来诊断为什么规划跑偏
- 生产阶段：默认只展示整理后的正式输出
- 只有 debug 模式才暴露 reasoning

因为学习产品真正要交给用户的是清晰答案，不是中间思维噪音。

### D. 逐步引入“来源治理”
如果你的目标是高质量学习系统，那么后面最关键的一层不是模型，而是来源治理：
- 哪些内容来自官方文档
- 哪些来自博客
- 哪些来自仓库源码
- 哪些来自论文
- 哪些只是模型总结推断

只要这层做起来，你的项目就会从“会生成内容”升级成“可信的学习助手”。

---

## 一句话总结

我对这个项目现在的看法是：

它最值得做成的，不是一个单纯的 AI 问答工具，而是一个“可配置模型、可追踪来源、可持续积累素材、可生成学习成果”的学习生产系统。

而这次把 DashScope / Qwen 3.6 文本链路接进去，是把这个系统从“能跑”推进到“可以长期打磨”的一步。
