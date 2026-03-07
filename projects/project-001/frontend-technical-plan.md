# 前端技术方案：智能学习助手 Web 应用

**项目 ID**: project-001  
**文档类型**: 前端技术方案  
**负责人**: 陈雨桐（前端工程师）  
**创建时间**: 2026-03-06 20:45 UTC  
**版本**: v1.0  
**状态**: 设计稿（待审查）

---

## 一、项目概述

### 1.1 项目背景
智能学习助手是一个基于 Web 的学习平台，帮助用户梳理知识体系并解答学习问题。

### 1.2 核心功能
| 功能模块 | 说明 |
|----------|------|
| **知识梳理** | 帮助用户整理、结构化所学知识，形成知识图谱 |
| **问题解答** | 基于 LangChain 智能体，提供智能化的问题解答 |
| **学习进度** | 跟踪学习进度，展示知识点掌握情况 |
| **交互对话** | 与智能体进行自然语言对话，获取学习指导 |

### 1.3 目标用户
所有想学习相关知识的用户（无特定限制，需支持广泛的用户群体）

---

## 二、技术栈选型

### 2.1 核心技术栈

| 层级 | 技术选型 | 版本 | 选型理由 |
|------|----------|------|----------|
| **框架** | Vue 3 | 3.4+ | 组合式 API、性能优秀、生态完善 |
| **语言** | TypeScript | 5.3+ | 类型安全、开发体验好、与 Vue 3 完美配合 |
| **构建工具** | Vite | 5.0+ | 极速冷启动、热更新快、打包优化好 |
| **状态管理** | Pinia | 2.1+ | Vue 3 官方推荐、轻量、TypeScript 友好 |
| **路由** | Vue Router | 4.2+ | Vue 3 官方路由、支持组合式 API |
| **UI 框架** | Element Plus | 2.4+ | 丰富的组件库、中文文档完善、社区活跃 |
| **样式方案** | Tailwind CSS | 3.4+ | 原子化 CSS、开发效率高、易于维护 |
| **HTTP 客户端** | Axios | 1.6+ | 成熟稳定、拦截器支持好、TypeScript 类型完善 |
| **图表库** | ECharts | 5.4+ | 功能强大、中文支持好、适合学习数据可视化 |

### 2.2 辅助工具库

| 用途 | 库名 | 说明 |
|------|------|------|
| **代码规范** | ESLint + Prettier | 统一代码风格 |
| **Git Hook** | Husky + lint-staged | 提交前自动检查 |
| **测试框架** | Vitest + Vue Test Utils | 单元测试 |
| **E2E 测试** | Playwright | 端到端测试 |
| **API 模拟** | MSW (Mock Service Worker) | 开发时 Mock API |
| **工具函数** | Lodash-es | 常用工具函数 |
| **日期处理** | Day.js | 轻量级日期库 |
| **图标库** | @element-plus/icons-vue | Element Plus 官方图标 |

### 2.3 技术选型对比

#### 为什么选择 Vue 3 而不是 React？

| 维度 | Vue 3 | React | 决策理由 |
|------|-------|-------|----------|
| **学习曲线** | 较低 | 中等 | 团队成员可能更熟悉 Vue |
| **开发效率** | 高（模板语法） | 高（JSX） | Vue 模板更直观 |
| **性能** | 优秀 | 优秀 | 两者性能相当 |
| **生态成熟度** | 成熟 | 非常成熟 | React 生态更丰富，但 Vue 也足够 |
| **TypeScript 支持** | 优秀 | 优秀 | 两者都很好 |
| **决策** | ✅ 选定 | - | 项目要求 Vue3 |

#### 为什么选择 Element Plus？

| 维度 | Element Plus | Ant Design Vue | Naive UI |
|------|--------------|----------------|----------|
| **组件丰富度** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **中文文档** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **社区活跃度** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **TypeScript 支持** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **主题定制** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **决策** | ✅ 选定 | - | - | 中文生态最好，文档完善 |

---

## 三、项目架构设计

### 3.1 目录结构

```
smart-learning-assistant/
├── public/                      # 静态资源
│   ├── favicon.ico
│   └── logo.svg
├── src/
│   ├── assets/                  # 项目资源
│   │   ├── styles/              # 全局样式
│   │   │   ├── index.scss       # 样式入口
│   │   │   ├── variables.scss   # SCSS 变量
│   │   │   └── tailwind.css     # Tailwind 配置
│   │   └── images/              # 图片资源
│   ├── components/              # 公共组件
│   │   ├── common/              # 通用组件
│   │   │   ├── AppHeader.vue    # 顶部导航
│   │   │   ├── AppSidebar.vue   # 侧边栏
│   │   │   ├── AppFooter.vue    # 页脚
│   │   │   └── LoadingSpinner.vue
│   │   ├── knowledge/           # 知识模块组件
│   │   │   ├── KnowledgeGraph.vue    # 知识图谱
│   │   │   ├── KnowledgeCard.vue     # 知识卡片
│   │   │   ├── KnowledgeTree.vue     # 知识树
│   │   │   └── KnowledgeEditor.vue   # 知识编辑器
│   │   ├── chat/                # 对话模块组件
│   │   │   ├── ChatWindow.vue        # 对话窗口
│   │   │   ├── ChatMessage.vue       # 消息气泡
│   │   │   ├── ChatInput.vue         # 输入框
│   │   │   └── ChatSidebar.vue       # 对话侧边栏
│   │   └── dashboard/           # 仪表盘组件
│   │       ├── ProgressChart.vue     # 进度图表
│   │       ├── StatsCard.vue         # 统计卡片
│   │       └── LearningPath.vue      # 学习路径
│   ├── composables/             # 组合式函数
│   │   ├── useChat.ts           # 对话逻辑
│   │   ├── useKnowledge.ts      # 知识管理逻辑
│   │   ├── useLearningProgress.ts # 学习进度逻辑
│   │   └── useApi.ts            # API 请求封装
│   ├── views/                   # 页面视图
│   │   ├── HomeView.vue         # 首页
│   │   ├── KnowledgeView.vue    # 知识梳理页
│   │   ├── ChatView.vue         # 对话页
│   │   ├── DashboardView.vue    # 学习仪表盘
│   │   └── ProfileView.vue      # 个人中心
│   ├── stores/                  # Pinia 状态管理
│   │   ├── user.ts              # 用户状态
│   │   ├── knowledge.ts         # 知识状态
│   │   ├── chat.ts              # 对话状态
│   │   └── learningProgress.ts  # 学习进度状态
│   ├── router/                  # 路由配置
│   │   └── index.ts
│   ├── api/                     # API 接口
│   │   ├── client.ts            # Axios 实例
│   │   ├── knowledge.ts         # 知识相关 API
│   │   ├── chat.ts              # 对话相关 API
│   │   └── user.ts              # 用户相关 API
│   ├── types/                   # TypeScript 类型定义
│   │   ├── knowledge.ts
│   │   ├── chat.ts
│   │   └── user.ts
│   ├── utils/                   # 工具函数
│   │   ├── format.ts            # 格式化函数
│   │   ├── storage.ts           # 本地存储封装
│   │   └── validators.ts        # 验证函数
│   ├── constants/               # 常量定义
│   │   └── index.ts
│   ├── App.vue                  # 根组件
│   └── main.ts                  # 入口文件
├── tests/                       # 测试文件
│   ├── unit/                    # 单元测试
│   └── e2e/                     # E2E 测试
├── .env                         # 环境变量
├── .eslintrc.cjs                # ESLint 配置
├── .prettierrc                  # Prettier 配置
├── index.html                   # HTML 模板
├── package.json                 # 依赖配置
├── tsconfig.json                # TypeScript 配置
├── vite.config.ts               # Vite 配置
└── README.md                    # 项目说明
```

### 3.2 模块划分

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           智能学习助手前端架构                           │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                            展示层 (Views)                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │   首页      │  │ 知识梳理页  │  │  对话页     │  │  仪表盘     │   │
│  │  HomeView   │  │KnowledgeView│  │  ChatView   │  │DashboardView│   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                          组件层 (Components)                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │  通用组件   │  │  知识组件   │  │  对话组件   │  │  图表组件   │   │
│  │  (common)   │  │ (knowledge) │  │   (chat)    │  │ (dashboard) │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                         逻辑层 (Composables + Stores)                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │ useChat.ts  │  │useKnowledge │  │  useApi.ts  │  │  Pinia 状态  │   │
│  │ 对话逻辑    │  │ 知识逻辑    │  │ API 封装    │  │  管理       │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                            数据层 (API + Types)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │  Axios 实例 │  │  知识 API   │  │  对话 API   │  │  类型定义   │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 四、核心组件设计

### 4.1 知识梳理模块

#### KnowledgeGraph.vue - 知识图谱组件

```vue
<template>
  <div class="knowledge-graph-container">
    <div ref="graphContainer" class="graph-canvas"></div>
    <div class="graph-controls">
      <el-button @click="zoomIn">放大</el-button>
      <el-button @click="zoomOut">缩小</el-button>
      <el-button @click="resetView">重置视图</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import * as d3 from 'd3'
import type { KnowledgeNode, KnowledgeEdge } from '@/types/knowledge'

const props = defineProps<{
  nodes: KnowledgeNode[]
  edges: KnowledgeEdge[]
}>()

const graphContainer = ref<HTMLElement | null>(null)
let svg: d3.Selection<SVGSVGElement, unknown, null, undefined> | null = null

onMounted(() => {
  initGraph()
})

watch(() => [props.nodes, props.edges], () => {
  updateGraph()
}, { deep: true })

function initGraph() {
  if (!graphContainer.value) return
  
  const width = graphContainer.value.clientWidth
  const height = graphContainer.value.clientHeight
  
  svg = d3.select(graphContainer.value)
    .append('svg')
    .attr('width', width)
    .attr('height', height)
    .call(
      d3.zoom<SVGSVGElement, unknown>().on('zoom', (event) => {
        svg?.select('g').attr('transform', event.transform)
      })
    )
    .append('g')
  
  renderGraph()
}

function renderGraph() {
  // 使用 D3 力导向图渲染知识图谱
  // ... 实现细节
}

function updateGraph() {
  // 更新图谱数据
  // ... 实现细节
}

function zoomIn() { /* ... */ }
function zoomOut() { /* ... */ }
function resetView() { /* ... */ }
</script>

<style scoped lang="scss">
.knowledge-graph-container {
  position: relative;
  width: 100%;
  height: 600px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  
  .graph-canvas {
    width: 100%;
    height: 100%;
  }
  
  .graph-controls {
    position: absolute;
    top: 16px;
    right: 16px;
    display: flex;
    gap: 8px;
  }
}
</style>
```

#### KnowledgeCard.vue - 知识卡片组件

```vue
<template>
  <el-card class="knowledge-card" :class="{ 'is-mastered': isMastered }">
    <template #header>
      <div class="card-header">
        <span class="title">{{ knowledge.title }}</span>
        <el-tag :type="difficultyTagType">{{ knowledge.difficulty }}</el-tag>
      </div>
    </template>
    
    <div class="card-content">
      <p class="description">{{ knowledge.description }}</p>
      
      <div class="progress-section">
        <div class="progress-label">掌握程度</div>
        <el-progress 
          :percentage="knowledge.masteryLevel" 
          :status="progressStatus"
        />
      </div>
      
      <div class="meta-info">
        <span class="study-time">
          <el-icon><Clock /></el-icon>
          学习时长：{{ formatTime(knowledge.studyTime) }}
        </span>
        <span class="last-review">
          <el-icon><Refresh /></el-icon>
          最后复习：{{ formatDate(knowledge.lastReviewDate) }}
        </span>
      </div>
    </div>
    
    <template #actions>
      <el-button type="primary" size="small" @click="handleReview">
        复习
      </el-button>
      <el-button size="small" @click="handleEdit">
        编辑
      </el-button>
      <el-button size="small" @click="handleDelete">
        删除
      </el-button>
    </template>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Clock, Refresh } from '@element-plus/icons-vue'
import type { KnowledgeItem } from '@/types/knowledge'
import { formatTime, formatDate } from '@/utils/format'

const props = defineProps<{
  knowledge: KnowledgeItem
}>()

const emit = defineEmits<{
  review: [id: string]
  edit: [id: string]
  delete: [id: string]
}>()

const isMastered = computed(() => props.knowledge.masteryLevel >= 90)

const difficultyTagType = computed(() => {
  const map: Record<string, 'success' | 'warning' | 'danger'> = {
    '入门': 'success',
    '初级': 'success',
    '中级': 'warning',
    '高级': 'danger',
    '专家': 'danger'
  }
  return map[props.knowledge.difficulty] || 'info'
})

const progressStatus = computed(() => {
  if (props.knowledge.masteryLevel >= 90) return 'success'
  if (props.knowledge.masteryLevel >= 60) return 'warning'
  return undefined
})

function handleReview() {
  emit('review', props.knowledge.id)
}

function handleEdit() {
  emit('edit', props.knowledge.id)
}

function handleDelete() {
  emit('delete', props.knowledge.id)
}
</script>

<style scoped lang="scss">
.knowledge-card {
  transition: all 0.3s;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }
  
  &.is-mastered {
    border-color: #67c23a;
  }
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .title {
      font-size: 16px;
      font-weight: 600;
      color: #303133;
    }
  }
  
  .card-content {
    .description {
      color: #606266;
      margin-bottom: 16px;
      line-height: 1.6;
    }
    
    .progress-section {
      margin-bottom: 12px;
      
      .progress-label {
        font-size: 12px;
        color: #909399;
        margin-bottom: 4px;
      }
    }
    
    .meta-info {
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      color: #909399;
      
      span {
        display: flex;
        align-items: center;
        gap: 4px;
      }
    }
  }
}
</style>
```

### 4.2 对话模块

#### ChatWindow.vue - 对话窗口组件

```vue
<template>
  <div class="chat-window">
    <div class="chat-messages" ref="messagesContainer">
      <ChatMessage
        v-for="message in messages"
        :key="message.id"
        :message="message"
        :is-streaming="message.isStreaming"
      />
      
      <div v-if="isLoading" class="loading-indicator">
        <el-skeleton :rows="3" animated />
      </div>
    </div>
    
    <div class="chat-input-area">
      <ChatInput
        v-model="inputValue"
        :disabled="isLoading"
        @submit="handleSend"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { useChatStore } from '@/stores/chat'
import ChatMessage from './ChatMessage.vue'
import ChatInput from './ChatInput.vue'

const chatStore = useChatStore()

const messagesContainer = ref<HTMLElement | null>(null)
const inputValue = ref('')

const messages = computed(() => chatStore.messages)
const isLoading = computed(() => chatStore.isLoading)

watch(() => messages.value.length, async () => {
  await nextTick()
  scrollToBottom()
})

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

async function handleSend(content: string) {
  if (!content.trim() || isLoading.value) return
  
  await chatStore.sendMessage(content)
  inputValue.value = ''
}
</script>

<style scoped lang="scss">
.chat-window {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f5f7fa;
  
  .chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    
    .loading-indicator {
      padding: 16px;
    }
  }
  
  .chat-input-area {
    padding: 16px 20px;
    background: #fff;
    border-top: 1px solid #e0e0e0;
  }
}
</style>
```

### 4.3 仪表盘模块

#### ProgressChart.vue - 学习进度图表

```vue
<template>
  <div ref="chartContainer" class="progress-chart"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'

const props = defineProps<{
  data: {
    date: string
    studyTime: number
    masteryLevel: number
  }[]
}>()

const chartContainer = ref<HTMLElement | null>(null)
let chart: echarts.ECharts | null = null

onMounted(() => {
  initChart()
})

watch(() => props.data, () => {
  updateChart()
}, { deep: true })

onBeforeUnmount(() => {
  chart?.dispose()
})

function initChart() {
  if (!chartContainer.value) return
  
  chart = echarts.init(chartContainer.value)
  updateChart()
}

function updateChart() {
  if (!chart) return
  
  const option: EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' }
    },
    legend: {
      data: ['学习时长', '掌握程度']
    },
    xAxis: {
      type: 'category',
      data: props.data.map(d => d.date)
    },
    yAxis: [
      {
        type: 'value',
        name: '学习时长 (分钟)',
        position: 'left'
      },
      {
        type: 'value',
        name: '掌握程度 (%)',
        position: 'right',
        max: 100
      }
    ],
    series: [
      {
        name: '学习时长',
        type: 'bar',
        data: props.data.map(d => d.studyTime),
        itemStyle: { color: '#409eff' }
      },
      {
        name: '掌握程度',
        type: 'line',
        yAxisIndex: 1,
        data: props.data.map(d => d.masteryLevel),
        itemStyle: { color: '#67c23a' },
        lineStyle: { width: 3 }
      }
    ]
  }
  
  chart.setOption(option)
}
</script>

<style scoped lang="scss">
.progress-chart {
  width: 100%;
  height: 300px;
}
</style>
```

---

## 五、状态管理设计

### 5.1 Pinia Store 结构

#### chat.ts - 对话状态管理

```typescript
// src/stores/chat.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ChatMessage, ChatSession } from '@/types/chat'
import { chatApi } from '@/api/chat'

export const useChatStore = defineStore('chat', () => {
  // State
  const sessions = ref<ChatSession[]>([])
  const currentSessionId = ref<string | null>(null)
  const messages = ref<ChatMessage[]>([])
  const isLoading = ref(false)
  const isStreaming = ref(false)
  
  // Getters
  const currentSession = computed(() => 
    sessions.value.find(s => s.id === currentSessionId.value)
  )
  
  const hasUnreadMessages = computed(() => 
    messages.value.some(m => !m.read && m.role === 'assistant')
  )
  
  // Actions
  async function createSession(title: string) {
    const session = await chatApi.createSession({ title })
    sessions.value.unshift(session)
    currentSessionId.value = session.id
    messages.value = []
    return session
  }
  
  async function loadSession(sessionId: string) {
    currentSessionId.value = sessionId
    isLoading.value = true
    try {
      messages.value = await chatApi.getMessages(sessionId)
    } finally {
      isLoading.value = false
    }
  }
  
  async function sendMessage(content: string) {
    if (!currentSessionId.value) return
    
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date().toISOString()
    }
    
    messages.value.push(userMessage)
    isStreaming.value = true
    
    try {
      const response = await chatApi.sendMessage(currentSessionId.value, content)
      
      // 处理流式响应
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
        isStreaming: true
      }
      messages.value.push(assistantMessage)
      
      // 流式更新内容
      for await (const chunk of response) {
        assistantMessage.content += chunk
        // 触发 UI 更新
        messages.value = [...messages.value]
      }
      
      assistantMessage.isStreaming = false
      messages.value = [...messages.value]
    } catch (error) {
      console.error('Send message failed:', error)
      throw error
    } finally {
      isStreaming.value = false
    }
  }
  
  function clearMessages() {
    messages.value = []
  }
  
  return {
    // State
    sessions,
    currentSessionId,
    messages,
    isLoading,
    isStreaming,
    // Getters
    currentSession,
    hasUnreadMessages,
    // Actions
    createSession,
    loadSession,
    sendMessage,
    clearMessages
  }
})
```

#### knowledge.ts - 知识状态管理

```typescript
// src/stores/knowledge.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { KnowledgeItem, KnowledgeNode, KnowledgeEdge } from '@/types/knowledge'
import { knowledgeApi } from '@/api/knowledge'

export const useKnowledgeStore = defineStore('knowledge', () => {
  // State
  const items = ref<KnowledgeItem[]>([])
  const nodes = ref<KnowledgeNode[]>([])
  const edges = ref<KnowledgeEdge[]>([])
  const isLoading = ref(false)
  
  // Getters
  const masteryAverage = computed(() => {
    if (items.value.length === 0) return 0
    const sum = items.value.reduce((acc, item) => acc + item.masteryLevel, 0)
    return Math.round(sum / items.value.length)
  })
  
  const masteredCount = computed(() => 
    items.value.filter(item => item.masteryLevel >= 90).length
  )
  
  const needsReview = computed(() => 
    items.value.filter(item => {
      const daysSinceReview = daysSince(item.lastReviewDate)
      return daysSinceReview >= item.reviewInterval
    })
  )
  
  // Actions
  async function loadKnowledge() {
    isLoading.value = true
    try {
      items.value = await knowledgeApi.getItems()
      const graph = await knowledgeApi.getGraph()
      nodes.value = graph.nodes
      edges.value = graph.edges
    } finally {
      isLoading.value = false
    }
  }
  
  async function addItem(item: Omit<KnowledgeItem, 'id'>) {
    const newItem = await knowledgeApi.createItem(item)
    items.value.push(newItem)
    return newItem
  }
  
  async function updateItem(id: string, updates: Partial<KnowledgeItem>) {
    const updated = await knowledgeApi.updateItem(id, updates)
    const index = items.value.findIndex(i => i.id === id)
    if (index !== -1) {
      items.value[index] = updated
    }
    return updated
  }
  
  async function deleteItem(id: string) {
    await knowledgeApi.deleteItem(id)
    items.value = items.value.filter(i => i.id !== id)
  }
  
  async function updateMastery(id: string, level: number) {
    await updateItem(id, { 
      masteryLevel: Math.min(100, Math.max(0, level)),
      lastReviewDate: new Date().toISOString()
    })
  }
  
  return {
    // State
    items,
    nodes,
    edges,
    isLoading,
    // Getters
    masteryAverage,
    masteredCount,
    needsReview,
    // Actions
    loadKnowledge,
    addItem,
    updateItem,
    deleteItem,
    updateMastery
  }
})

function daysSince(dateString: string): number {
  const date = new Date(dateString)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  return Math.floor(diff / (1000 * 60 * 60 * 24))
}
```

---

## 六、API 接口设计

### 6.1 Axios 实例配置

```typescript
// src/api/client.ts
import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig } from 'axios'
import { useUserStore } from '@/stores/user'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function createApiClient(): AxiosInstance {
  const client = axios.create({
    baseURL: BASE_URL,
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json'
    }
  })
  
  // 请求拦截器
  client.interceptors.request.use(
    (config) => {
      const userStore = useUserStore()
      if (userStore.token) {
        config.headers.Authorization = `Bearer ${userStore.token}`
      }
      return config
    },
    (error) => Promise.reject(error)
  )
  
  // 响应拦截器
  client.interceptors.response.use(
    (response) => response.data,
    (error) => {
      if (error.response?.status === 401) {
        // Token 过期，跳转登录
        const userStore = useUserStore()
        userStore.logout()
        window.location.href = '/login'
      }
      return Promise.reject(error)
    }
  )
  
  return client
}

export const apiClient = createApiClient()
```

### 6.2 API 接口定义

```typescript
// src/api/chat.ts
import { apiClient } from './client'
import type { ChatMessage, ChatSession } from '@/types/chat'

export const chatApi = {
  // 创建对话会话
  createSession(data: { title: string }): Promise<ChatSession> {
    return apiClient.post('/api/chat/sessions', data)
  },
  
  // 获取会话列表
  getSessions(): Promise<ChatSession[]> {
    return apiClient.get('/api/chat/sessions')
  },
  
  // 获取会话消息
  getMessages(sessionId: string): Promise<ChatMessage[]> {
    return apiClient.get(`/api/chat/sessions/${sessionId}/messages`)
  },
  
  // 发送消息（支持流式响应）
  async *sendMessage(sessionId: string, content: string): AsyncGenerator<string> {
    const response = await fetch(`${apiClient.defaults.baseURL}/api/chat/sessions/${sessionId}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({ content })
    })
    
    const reader = response.body?.getReader()
    const decoder = new TextDecoder()
    
    while (true) {
      const { done, value } = await reader!.read()
      if (done) break
      
      const chunk = decoder.decode(value)
      // 解析 SSE 格式
      const lines = chunk.split('\n')
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          yield line.slice(6)
        }
      }
    }
  },
  
  // 删除会话
  deleteSession(sessionId: string): Promise<void> {
    return apiClient.delete(`/api/chat/sessions/${sessionId}`)
  }
}
```

---

## 七、性能优化方案

### 7.1 代码分割

```typescript
// src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/HomeView.vue')
  },
  {
    path: '/knowledge',
    name: 'Knowledge',
    component: () => import('@/views/KnowledgeView.vue')
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('@/views/ChatView.vue')
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/DashboardView.vue')
  }
]

export const router = createRouter({
  history: createWebHistory(),
  routes
})
```

### 7.2 组件懒加载

```vue
<!-- 大型组件使用 defineAsyncComponent -->
<script setup lang="ts">
import { defineAsyncComponent } from 'vue'

const KnowledgeGraph = defineAsyncComponent(() => 
  import('@/components/knowledge/KnowledgeGraph.vue')
)
</script>
```

### 7.3 虚拟滚动

对于长列表（如消息列表、知识列表），使用虚拟滚动优化性能：

```vue
<template>
  <RecycleScroller
    :items="messages"
    :item-size="80"
    key-field="id"
  >
    <template #default="{ item }">
      <ChatMessage :message="item" />
    </template>
  </RecycleScroller>
</template>

<script setup lang="ts">
import { RecycleScroller } from 'vue-virtual-scroller'
import 'vue-virtual-scroller/dist/vue-virtual-scroller.css'
</script>
```

### 7.4 图片优化

```typescript
// 使用 WebP 格式 + 懒加载
// vite.config.ts
export default defineConfig({
  plugins: [
    vue(),
    viteImagemin({
      webp: { quality: 80 }
    })
  ]
})
```

---

## 八、开发规范

### 8.1 代码规范

```json
// .eslintrc.cjs
module.exports = {
  root: true,
  env: {
    browser: true,
    es2021: true,
    node: true
  },
  extends: [
    'eslint:recommended',
    'plugin:vue/vue3-recommended',
    'plugin:@typescript-eslint/recommended',
    'prettier'
  ],
  parser: 'vue-eslint-parser',
  parserOptions: {
    parser: '@typescript-eslint/parser',
    ecmaVersion: 'latest',
    sourceType: 'module'
  },
  plugins: ['@typescript-eslint'],
  rules: {
    'vue/multi-word-component-names': 'off',
    '@typescript-eslint/no-explicit-any': 'warn',
    'vue/require-default-prop': 'off'
  }
}
```

### 8.2 提交规范

采用 Conventional Commits 规范：

```
feat: 添加知识图谱组件
fix: 修复对话窗口滚动问题
docs: 更新 README 文档
style: 代码格式化
refactor: 重构状态管理逻辑
test: 添加单元测试
chore: 更新依赖
```

---

## 九、开发计划

### 9.1 阶段划分

| 阶段 | 时间 | 任务 | 交付物 |
|------|------|------|--------|
| **Phase 1** | 第 1 周 | 项目初始化、基础配置 | 可运行的项目框架 |
| **Phase 2** | 第 2 周 | 通用组件开发、UI 框架集成 | 基础组件库 |
| **Phase 3** | 第 3 周 | 知识梳理模块开发 | 知识图谱、知识卡片 |
| **Phase 4** | 第 4 周 | 对话模块开发 | 对话窗口、流式响应 |
| **Phase 5** | 第 5 周 | 仪表盘模块开发 | 进度图表、数据统计 |
| **Phase 6** | 第 6 周 | 联调测试、性能优化 | 可部署版本 |

### 9.2 里程碑

| 里程碑 | 时间 | 验收标准 |
|--------|------|----------|
| M1: 框架搭建完成 | 第 1 周末 | 项目可运行，路由、状态管理配置完成 |
| M2: 核心组件完成 | 第 3 周末 | 知识梳理模块可独立演示 |
| M3: 对话功能完成 | 第 4 周末 | 可与后端智能体正常对话 |
| M4: 完整功能完成 | 第 6 周末 | 所有核心功能可用，可部署 |

---

## 十、风险与应对

| 风险 | 可能性 | 影响 | 应对措施 |
|------|--------|------|----------|
| **流式响应实现复杂** | 中 | 中 | 提前调研 SSE/WebSocket 方案，预留缓冲时间 |
| **知识图谱渲染性能** | 中 | 中 | 使用 Canvas 替代 SVG，限制节点数量，分批次渲染 |
| **跨浏览器兼容性** | 低 | 中 | 使用 Babel 转译，Polyfill 填充，测试主流浏览器 |
| **后端 API 变更** | 中 | 高 | 定义清晰的 API 契约，使用 TypeScript 类型约束 |
| **时间紧张** | 高 | 高 | 优先实现核心功能，非核心功能延后 |

---

## 十一、待确认事项

需要与架构师和后端工程师确认：

1. **API 接口规范**: RESTful 还是 GraphQL？
2. **认证方式**: JWT Token 还是 Session？
3. **流式响应协议**: SSE 还是 WebSocket？
4. **错误码规范**: 统一错误码格式
5. **数据格式**: 日期格式、分页格式等

---

## 十二、总结

本技术方案基于 **Vue 3 + TypeScript + Element Plus** 构建智能学习助手前端应用，采用模块化设计，包含知识梳理、智能对话、学习仪表盘三大核心模块。

**核心优势**:
- ✅ Vue 3 组合式 API，代码组织清晰
- ✅ TypeScript 类型安全，减少运行时错误
- ✅ Element Plus 组件丰富，开发效率高
- ✅ Pinia 状态管理，轻量且 TypeScript 友好
- ✅ Vite 构建，开发体验优秀

**下一步**:
1. 等待架构师和后端工程师确认 API 规范
2. 等待 Challenger 审查本方案
3. 根据反馈完善方案
4. 开始 Phase 1 实施

---

**文档状态**: 设计稿（v1.0）  
**最后更新**: 2026-03-06 20:45 UTC  
**下一步**: 提交 Challenger 审查