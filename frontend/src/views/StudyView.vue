<script setup>
import { onMounted, ref } from 'vue'
import { apiGet, apiSend } from '../api'
import { formatCurriculumStatus, formatDepth, formatManualMode } from '../labels'
import TaskPanel from '../components/TaskPanel.vue'

const curriculum = ref(null)
const form = ref({ goal: '大模型全栈工程师', depth: 'expert' })
const manual = ref({ mode: 'study-topic', value: '', max_pages: 50 })
const notice = ref('')
const error = ref('')

async function loadCurriculum() {
  try {
    const data = await apiGet('/api/curriculum')
    curriculum.value = data.curriculum
    error.value = ''
  } catch (err) {
    error.value = String(err)
  }
}

async function generateCurriculum() {
  try {
    const data = await apiSend('/api/curriculum/generate', 'POST', form.value)
    notice.value = `课程表生成任务已加入队列：${data.task.id}`
    error.value = ''
  } catch (err) {
    error.value = String(err)
  }
}

async function approveCurriculum() {
  try {
    await apiSend('/api/curriculum/approve', 'POST')
    notice.value = '课程表已批准。'
    await loadCurriculum()
  } catch (err) {
    error.value = String(err)
  }
}

async function autoStudy() {
  try {
    const data = await apiSend('/api/curriculum/auto-study', 'POST')
    notice.value = `自动学习任务已加入队列：${data.task.id}`
    error.value = ''
  } catch (err) {
    error.value = String(err)
  }
}

async function manualStudy() {
  try {
    const data = await apiSend('/api/study/manual', 'POST', manual.value)
    notice.value = `手动学习任务已加入队列：${data.task.id}`
    error.value = ''
  } catch (err) {
    error.value = String(err)
  }
}

onMounted(loadCurriculum)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2>学习流程</h2>
        <p class="muted">课程表生成、审批和长期学习任务都会通过后台任务执行。</p>
      </div>
      <button @click="loadCurriculum">刷新课程表</button>
    </div>

    <p v-if="notice" class="success">{{ notice }}</p>
    <p v-if="error" class="error">{{ error }}</p>

    <section class="card">
      <h3>生成课程表</h3>
      <div class="form-grid">
        <label>目标<input v-model="form.goal" /></label>
        <label>深度
          <select v-model="form.depth">
            <option value="quick">{{ formatDepth('quick') }}</option>
            <option value="comprehensive">{{ formatDepth('comprehensive') }}</option>
            <option value="expert">{{ formatDepth('expert') }}</option>
          </select>
        </label>
      </div>
      <button @click="generateCurriculum">生成</button>
    </section>

    <section class="card" v-if="curriculum">
      <div class="section-header">
        <h3>当前课程表</h3>
        <div class="actions">
          <button class="secondary" @click="approveCurriculum">批准</button>
          <button @click="autoStudy">开始 / 继续自动学习</button>
        </div>
      </div>
      <div class="grid two-col">
        <div class="kv-row"><span>目标</span><strong>{{ curriculum.goal }}</strong></div>
        <div class="kv-row"><span>状态</span><strong>{{ formatCurriculumStatus(curriculum.status) }}</strong></div>
        <div class="kv-row"><span>深度</span><strong>{{ formatDepth(curriculum.depth) }}</strong></div>
        <div class="kv-row"><span>领域数</span><strong>{{ curriculum.domains?.length || 0 }}</strong></div>
      </div>
      <div class="stack">
        <details v-for="domain in curriculum.domains || []" :key="domain.name" class="details-card">
          <summary>{{ domain.priority }} · {{ domain.name }}（{{ domain.topics?.length || 0 }} 个主题）</summary>
          <p class="muted">{{ domain.description }}</p>
          <ul class="plain-list">
            <li v-for="topic in domain.topics || []" :key="topic.name">
              <strong>{{ topic.name }}</strong>：{{ formatCurriculumStatus(topic.status) }}
            </li>
          </ul>
        </details>
      </div>
    </section>

    <section class="card">
      <h3>手动学习</h3>
      <div class="form-grid">
        <label>模式
          <select v-model="manual.mode">
            <option value="study-topic">{{ formatManualMode('study-topic') }}</option>
            <option value="study-course">{{ formatManualMode('study-course') }}</option>
            <option value="study-github">{{ formatManualMode('study-github') }}</option>
            <option value="study-arxiv">{{ formatManualMode('study-arxiv') }}</option>
            <option value="study-wechat">{{ formatManualMode('study-wechat') }}</option>
          </select>
        </label>
        <label>内容<input v-model="manual.value" placeholder="主题或链接" /></label>
        <label>最大页数<input type="number" min="1" v-model.number="manual.max_pages" /></label>
      </div>
      <button @click="manualStudy">提交手动学习任务</button>
    </section>

    <TaskPanel />
  </div>
</template>