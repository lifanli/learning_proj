<script setup>
import { onMounted, ref, watch } from 'vue'
import { apiGet } from '../api'

const files = ref([])
const selected = ref('')
const log = ref(null)
const error = ref('')

async function loadFiles() {
  try {
    const data = await apiGet('/api/logs')
    files.value = data.files || []
    if (!selected.value && files.value.length) selected.value = files.value[0]
  } catch (err) {
    error.value = String(err)
  }
}

async function loadLog() {
  if (!selected.value) return
  try {
    log.value = await apiGet(`/api/logs/${selected.value}?limit=400`)
    error.value = ''
  } catch (err) {
    error.value = String(err)
  }
}

watch(selected, loadLog)
onMounted(async () => {
  await loadFiles()
  await loadLog()
})
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2>日志</h2>
        <p class="muted">直接查看日志文件，不再依赖隐藏的旧控制台。</p>
      </div>
      <div class="actions">
        <button class="secondary" @click="loadFiles">重新加载文件</button>
        <button @click="loadLog">刷新日志</button>
      </div>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <section class="card">
      <label>日志文件
        <select v-model="selected">
          <option v-for="file in files" :key="file" :value="file">{{ file }}</option>
        </select>
      </label>
      <pre v-if="log" class="log-box tall">{{ log.lines.join('\n') }}</pre>
    </section>
  </div>
</template>