<script setup>
import { onMounted, ref } from 'vue'
import { apiGet, apiSend } from '../api'

const content = ref('')
const notice = ref('')
const error = ref('')

async function load() {
  try {
    const data = await apiGet('/api/settings')
    content.value = data.content || ''
    error.value = ''
  } catch (err) {
    error.value = String(err)
  }
}

async function save() {
  try {
    await apiSend('/api/settings', 'PUT', { content: content.value })
    notice.value = '设置已保存。'
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
        <h2>设置</h2>
        <p class="muted">直接编辑原始配置文件，保存后由接口写回。</p>
      </div>
      <div class="actions">
        <button class="secondary" @click="load">重新加载</button>
        <button @click="save">保存</button>
      </div>
    </div>

    <p v-if="notice" class="success">{{ notice }}</p>
    <p v-if="error" class="error">{{ error }}</p>

    <section class="card">
      <textarea v-model="content" class="editor"></textarea>
    </section>
  </div>
</template>