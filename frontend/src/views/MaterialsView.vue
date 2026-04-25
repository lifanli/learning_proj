<script setup>
import { onMounted, ref } from 'vue'
import { apiGet } from '../api'
import { formatSourceType } from '../labels'

const items = ref([])
const selected = ref(null)
const keyword = ref('')
const sourceType = ref('')
const error = ref('')

async function load() {
  try {
    const params = new URLSearchParams()
    if (keyword.value) params.set('keyword', keyword.value)
    if (sourceType.value) params.set('source_type', sourceType.value)
    params.set('limit', '100')
    const data = await apiGet(`/api/materials?${params.toString()}`)
    items.value = data.items || []
    error.value = ''
  } catch (err) {
    error.value = String(err)
  }
}

async function openItem(id) {
  try {
    selected.value = await apiGet(`/api/materials/${id}`)
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
        <h2>学习资料</h2>
        <p class="muted">浏览已保存的资料，并按需查看完整内容。</p>
      </div>
      <button @click="load">搜索</button>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <section class="card">
      <div class="form-grid">
        <label>关键词<input v-model="keyword" /></label>
        <label>来源类型
          <select v-model="sourceType">
            <option value="">全部来源</option>
            <option value="arxiv">论文</option>
            <option value="github">代码仓库</option>
            <option value="web">网页</option>
            <option value="wechat">公众号</option>
            <option value="course">课程</option>
            <option value="topic">主题</option>
          </select>
        </label>
      </div>
    </section>

    <div class="split">
      <section class="card">
        <h3>搜索结果</h3>
        <ul class="plain-list selectable-list">
          <li v-for="item in items" :key="item.id" @click="openItem(item.id)">
            <strong>{{ item.title || '（未命名）' }}</strong>
            <div class="muted">{{ formatSourceType(item.source_type) }} · {{ item.id }}</div>
          </li>
        </ul>
      </section>

      <section class="card">
        <h3>详情</h3>
        <template v-if="selected">
          <div class="stack">
            <div class="kv-row"><span>标题</span><strong>{{ selected.title }}</strong></div>
            <div class="kv-row"><span>来源链接</span><strong>{{ selected.source_url }}</strong></div>
            <div class="kv-row"><span>类型</span><strong>{{ formatSourceType(selected.source_type) }}</strong></div>
            <pre class="log-box">{{ selected.content }}</pre>
          </div>
        </template>
        <p v-else class="muted">选择一条资料查看完整内容。</p>
      </section>
    </div>
  </div>
</template>