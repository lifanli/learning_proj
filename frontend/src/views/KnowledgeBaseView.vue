<script setup>
import { computed, onMounted, ref } from 'vue'
import { apiGet } from '../api'

const tree = ref([])
const selected = ref(null)
const query = ref('')
const loading = ref(false)
const error = ref('')

async function loadTree() {
  loading.value = true
  try {
    const data = await apiGet('/api/knowledge-base')
    tree.value = data.items || []
    error.value = ''
  } catch (err) {
    error.value = String(err)
  } finally {
    loading.value = false
  }
}

async function openFile(node) {
  if (node.type !== 'file') return
  try {
    const params = new URLSearchParams({ path: node.path })
    selected.value = await apiGet(`/api/knowledge-base/file?${params.toString()}`)
    error.value = ''
  } catch (err) {
    error.value = String(err)
  }
}

function flattenNodes(nodes, depth = 0, output = []) {
  for (const node of nodes || []) {
    output.push({ ...node, depth })
    if (node.children?.length) flattenNodes(node.children, depth + 1, output)
  }
  return output
}

const visibleNodes = computed(() => {
  const nodes = flattenNodes(tree.value)
  const term = query.value.trim().toLowerCase()
  if (!term) return nodes
  return nodes.filter((node) => {
    return node.name.toLowerCase().includes(term) || node.path.toLowerCase().includes(term)
  })
})

const selectedTitle = computed(() => selected.value?.path || '请选择一个文档文件')

onMounted(loadTree)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2>知识库</h2>
        <p class="muted">浏览已生成的书籍、章节和文档文件。</p>
      </div>
      <button @click="loadTree">重新加载目录</button>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <div class="split kb-layout">
      <section class="card">
        <div class="section-header">
          <h3>知识库目录</h3>
          <span class="muted">{{ visibleNodes.length }} 项</span>
        </div>
        <input v-model="query" placeholder="按标题或路径筛选" />

        <p v-if="loading" class="muted">正在加载知识库...</p>
        <p v-else-if="!visibleNodes.length" class="muted">没有找到文档文件。</p>

        <div v-else class="tree-list">
          <button
            v-for="node in visibleNodes"
            :key="node.path"
            class="tree-row"
            :class="{ file: node.type === 'file', active: selected?.path === node.path }"
            :style="{ paddingLeft: `${0.8 + node.depth * 1.2}rem` }"
            @click="openFile(node)"
          >
            <span>{{ node.type === 'directory' ? '目录' : '文件' }}</span>
            <strong>{{ node.name }}</strong>
          </button>
        </div>
      </section>

      <section class="card">
        <div class="section-header">
          <div>
            <h3>{{ selectedTitle }}</h3>
            <p class="muted">只读预览。如需修改，请在工作区编辑对应文件。</p>
          </div>
        </div>
        <pre v-if="selected" class="log-box kb-preview">{{ selected.content }}</pre>
        <p v-else class="muted">从左侧目录选择文件后预览内容。</p>
      </section>
    </div>
  </div>
</template>