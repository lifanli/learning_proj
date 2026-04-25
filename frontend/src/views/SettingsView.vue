<script setup>
import { onMounted, ref } from 'vue'
import { apiGet, apiSend } from '../api'

const content = ref('')
const apiKey = ref('')
const apiKeyEnv = ref('')
const llmStatus = ref(null)
const llmCheck = ref(null)
const notice = ref('')
const error = ref('')
const keyNotice = ref('')
const keyError = ref('')
const checking = ref(false)

async function load() {
  try {
    const data = await apiGet('/api/settings')
    content.value = data.content || ''
    await loadLlmStatus()
    error.value = ''
  } catch (err) {
    error.value = String(err)
  }
}

async function loadLlmStatus() {
  llmStatus.value = await apiGet('/api/settings/llm')
  apiKeyEnv.value = llmStatus.value.api_key_env || 'DASHSCOPE_API_KEY'
}

async function save() {
  try {
    await apiSend('/api/settings', 'PUT', { content: content.value })
    await loadLlmStatus()
    notice.value = '设置已保存。'
    error.value = ''
  } catch (err) {
    error.value = String(err)
  }
}

async function saveApiKey() {
  try {
    const data = await apiSend('/api/settings/llm/api-key', 'PUT', {
      api_key: apiKey.value,
      api_key_env: apiKeyEnv.value,
    })
    llmStatus.value = data.status
    apiKey.value = ''
    keyNotice.value = 'API Key 已保存到本地 .env，并已刷新当前后端进程。'
    keyError.value = ''
    llmCheck.value = null
  } catch (err) {
    keyError.value = String(err)
  }
}

async function testLlm() {
  checking.value = true
  keyNotice.value = ''
  keyError.value = ''
  try {
    llmCheck.value = await apiSend('/api/settings/llm/check', 'POST')
    llmStatus.value = llmCheck.value.status || llmStatus.value
  } catch (err) {
    keyError.value = String(err)
  } finally {
    checking.value = false
  }
}

function keyStateText(state) {
  if (!state?.present) return '未设置'
  const suffix = state.suffix ? `，尾号 ${state.suffix}` : ''
  return `已设置，长度 ${state.length}${suffix}`
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
      <div class="section-header">
        <div>
          <h3>LLM 密钥</h3>
          <p class="muted">密钥只保存到本地 .env，不会写入 settings.yaml。</p>
        </div>
        <button class="secondary" @click="loadLlmStatus">刷新状态</button>
      </div>

      <div v-if="llmStatus" class="stack compact">
        <p class="muted">环境变量：{{ llmStatus.api_key_env }}</p>
        <p class="muted">.env：{{ keyStateText(llmStatus.env_file_key) }}</p>
        <p class="muted">当前后端进程：{{ keyStateText(llmStatus.process_key) }}</p>
        <p class="muted">模型：{{ llmStatus.deep_model || llmStatus.model }} · {{ llmStatus.base_url }}</p>
      </div>

      <div class="form-grid">
        <label>环境变量名<input v-model="apiKeyEnv" placeholder="DASHSCOPE_API_KEY" /></label>
        <label>API Key<input v-model="apiKey" type="password" placeholder="粘贴新的 API Key" /></label>
      </div>
      <div class="actions">
        <button @click="saveApiKey" :disabled="!apiKey">保存 API Key</button>
        <button class="secondary" @click="testLlm" :disabled="checking">
          {{ checking ? '测试中...' : '测试 LLM 连接' }}
        </button>
      </div>

      <p v-if="keyNotice" class="success">{{ keyNotice }}</p>
      <p v-if="keyError" class="error">{{ keyError }}</p>
      <p v-if="llmCheck?.ok" class="success">LLM 连接成功：{{ llmCheck.reply || 'OK' }}</p>
      <p v-else-if="llmCheck && !llmCheck.ok" class="error">LLM 连接失败：{{ llmCheck.error }}</p>
    </section>

    <section class="card">
      <h3>原始配置</h3>
      <p class="muted">这里不会显示明文密钥。如果要更新密钥，请使用上方的专用输入框。</p>
      <textarea v-model="content" class="editor"></textarea>
    </section>
  </div>
</template>
