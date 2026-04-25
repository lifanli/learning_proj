<script setup>
import { onMounted, ref } from 'vue'
import { apiGet } from '../api'
import { formatCurriculumStatus, formatSourceType } from '../labels'
import TaskPanel from '../components/TaskPanel.vue'

const summary = ref(null)
const error = ref('')

async function load() {
  try {
    summary.value = await apiGet('/api/dashboard')
    error.value = ''
  } catch (err) {
    error.value = String(err)
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2>总览</h2>
        <p class="muted">轻量控制台，用来查看系统状态和后台任务。</p>
      </div>
      <button @click="load">刷新</button>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <template v-if="summary">
      <div class="grid stats">
        <div class="card stat">
          <span class="muted">学习资料</span>
          <strong>{{ summary.materials_total }}</strong>
        </div>
        <div class="card stat">
          <span class="muted">课程表状态</span>
          <strong>{{ formatCurriculumStatus(summary.curriculum.status || 'none') }}</strong>
        </div>
        <div class="card stat">
          <span class="muted">已完成主题</span>
          <strong>{{ summary.curriculum.progress.done }}</strong>
        </div>
        <div class="card stat">
          <span class="muted">待学习主题</span>
          <strong>{{ summary.curriculum.progress.pending }}</strong>
        </div>
      </div>

      <section class="card">
        <h3>资料类型</h3>
        <div class="grid two-col">
          <div v-for="(count, name) in summary.materials_by_type" :key="name" class="kv-row">
            <span>{{ formatSourceType(name) }}</span>
            <strong>{{ count }}</strong>
          </div>
        </div>
      </section>

      <section class="card">
        <h3>最近日志文件</h3>
        <ul class="plain-list">
          <li v-for="file in summary.log_files" :key="file">{{ file }}</li>
        </ul>
      </section>
    </template>

    <TaskPanel />
  </div>
</template>