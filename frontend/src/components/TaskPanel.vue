<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { apiGet, apiSend } from '../api'
import { formatTaskKind, formatTaskStatus, translateTaskText } from '../labels'

const tasks = ref([])
const selectedTask = ref(null)
const selectedTaskId = ref('')
const loading = ref(false)
const error = ref('')
const detailError = ref('')
const actionMessage = ref('')
const actionError = ref('')
const showFullDetail = ref(false)
let timer = null

async function loadTasks() {
  loading.value = true
  try {
    const data = await apiGet('/api/tasks')
    tasks.value = data.items || []
    if (selectedTaskId.value && !showFullDetail.value) {
      const latest = tasks.value.find((task) => task.id === selectedTaskId.value)
      if (latest) {
        const previousStatus = selectedTask.value?.status
        selectedTask.value = { ...selectedTask.value, ...latest }
        if (latest.status !== previousStatus || (latest.has_result && selectedTask.value?.result == null)) {
          await loadTaskDetail(latest.id)
        }
      }
    }
    error.value = ''
  } catch (err) {
    error.value = String(err)
  } finally {
    loading.value = false
  }
}

async function selectTask(task) {
  selectedTaskId.value = task.id
  selectedTask.value = task
  showFullDetail.value = false
  detailError.value = ''
  actionMessage.value = ''
  actionError.value = ''
  await loadTaskDetail(task.id)
}

async function loadTaskDetail(taskId) {
  try {
    selectedTask.value = await apiGet(`/api/tasks/${taskId}`)
    detailError.value = ''
  } catch (err) {
    detailError.value = String(err)
  }
}

async function cancelTask(task) {
  if (!task?.id) return
  actionMessage.value = ''
  actionError.value = ''
  try {
    const data = await apiSend(`/api/tasks/${task.id}/cancel`, 'POST')
    selectedTask.value = data.task
    actionMessage.value = `已发送取消请求：${formatTaskKind(task.kind)}（${task.id}）。`
    await loadTasks()
  } catch (err) {
    actionError.value = String(err)
  }
}

async function retryTask(task) {
  if (!task?.id) return
  actionMessage.value = ''
  actionError.value = ''
  try {
    const data = await apiSend(`/api/tasks/${task.id}/retry`, 'POST')
    selectedTask.value = data.task
    selectedTaskId.value = data.task.id
    showFullDetail.value = false
    actionMessage.value = `已重新加入队列：${data.task.id}。`
    await loadTasks()
  } catch (err) {
    actionError.value = String(err)
  }
}

function taskSummary(task) {
  if (task.error) return compactText(firstLine(task.error), 180)
  if (task.result_summary) return translateTaskText(task.result_summary)
  return translateTaskText(task.message || 'No details yet.')
}

function taskDetailText(task) {
  if (!task) return ''
  if (task.error) return task.error
  if (task.result !== undefined && task.result !== null) return JSON.stringify(task.result, null, 2)
  return translateTaskText(task.message || '')
}

function compactText(value, limit = 4000) {
  const text = String(value || '')
  if (text.length <= limit) return text
  return `${text.slice(0, limit)}\n\n... 已隐藏 ${text.length - limit} 个字符。`
}

function firstLine(value) {
  return String(value || '').split(/\r?\n/)[0]
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  return new Date(timestamp * 1000).toLocaleString('zh-CN')
}

function progressValue(task) {
  return Math.max(0, Math.min(100, Number(task?.progress || 0)))
}

const detailText = computed(() => {
  if (!selectedTask.value) return ''
  const text = taskDetailText(selectedTask.value)
  return showFullDetail.value ? text : compactText(text)
})

onMounted(() => {
  loadTasks()
  timer = setInterval(loadTasks, 4000)
})

onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <section class="card">
    <div class="section-header">
      <h3>后台任务</h3>
      <button class="secondary" @click="loadTasks">刷新</button>
    </div>

    <p v-if="loading">正在加载任务...</p>
    <p v-else-if="error" class="error">{{ error }}</p>

    <div v-else-if="tasks.length" class="task-grid">
      <div class="stack">
        <button
          v-for="task in tasks"
          :key="task.id"
          class="task-item task-button"
          :class="{ active: selectedTaskId === task.id }"
          @click="selectTask(task)"
        >
          <div class="section-header">
            <div class="task-title">{{ formatTaskKind(task.kind) }}</div>
            <span class="task-pill" :class="`status-${task.status}`">{{ formatTaskStatus(task.status) }}</span>
          </div>
          <div class="muted">{{ task.id }} · {{ formatTime(task.updated_at) }}</div>
          <div class="progress-track" :title="`${progressValue(task)}%`">
            <div class="progress-fill" :style="{ width: `${progressValue(task)}%` }"></div>
          </div>
          <div class="task-summary">{{ taskSummary(task) }}</div>
        </button>
      </div>

      <aside class="task-detail">
        <template v-if="selectedTask">
          <div class="section-header">
            <div>
              <h4>{{ formatTaskKind(selectedTask.kind) }}</h4>
              <p class="muted">{{ selectedTask.id }} · {{ formatTime(selectedTask.updated_at) }}</p>
            </div>
            <div class="actions">
              <button v-if="selectedTask.can_cancel" class="secondary" @click="cancelTask(selectedTask)">
                取消
              </button>
              <button v-if="selectedTask.can_retry" @click="retryTask(selectedTask)">
                重试
              </button>
              <button class="secondary" @click="showFullDetail = !showFullDetail">
                {{ showFullDetail ? '精简显示' : '完整显示' }}
              </button>
            </div>
          </div>
          <div class="progress-track detail-progress" :title="`${progressValue(selectedTask)}%`">
            <div class="progress-fill" :style="{ width: `${progressValue(selectedTask)}%` }"></div>
          </div>
          <p v-if="actionMessage" class="success">{{ actionMessage }}</p>
          <p v-if="actionError" class="error">{{ actionError }}</p>
          <p v-if="detailError" class="error">{{ detailError }}</p>
          <pre class="log-box">{{ detailText }}</pre>
        </template>
        <p v-else class="muted">选择一个任务查看详情。</p>
      </aside>
    </div>

    <p v-else class="muted">暂无任务。</p>
  </section>
</template>