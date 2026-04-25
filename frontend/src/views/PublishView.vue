<script setup>
import { ref } from 'vue'
import { apiSend } from '../api'
import TaskPanel from '../components/TaskPanel.vue'

const form = ref({ topic: '', parent_id: '', tags: '' })
const notice = ref('')
const error = ref('')

async function submit() {
  try {
    const payload = {
      topic: form.value.topic,
      parent_id: form.value.parent_id || null,
      tags: form.value.tags.split(',').map((item) => item.trim()).filter(Boolean),
    }
    const data = await apiSend('/api/publish', 'POST', payload)
    notice.value = `出版任务已加入队列：${data.task.id}`
    error.value = ''
  } catch (err) {
    error.value = String(err)
  }
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2>出版</h2>
        <p class="muted">启动耗时较长的出版任务，同时保持界面可继续操作。</p>
      </div>
    </div>

    <p v-if="notice" class="success">{{ notice }}</p>
    <p v-if="error" class="error">{{ error }}</p>

    <section class="card">
      <div class="form-grid">
        <label>主题<input v-model="form.topic" /></label>
        <label>父级资料编号<input v-model="form.parent_id" /></label>
        <label>标签<input v-model="form.tags" placeholder="大模型, 注意力机制" /></label>
      </div>
      <button @click="submit" :disabled="!form.topic">提交出版任务</button>
    </section>

    <TaskPanel />
  </div>
</template>