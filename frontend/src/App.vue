<script setup>
import { RouterLink, RouterView, useRoute } from 'vue-router'

const route = useRoute()
const navItems = [
  { to: '/', label: '总览' },
  { to: '/study', label: '学习流程' },
  { to: '/knowledge-base', label: '知识库' },
  { to: '/materials', label: '学习资料' },
  { to: '/publish', label: '出版' },
  { to: '/logs', label: '日志' },
  { to: '/settings', label: '设置' },
]
</script>

<template>
  <div class="layout">
    <aside class="sidebar">
      <h1>学习项目控制台</h1>
      <p class="subtitle">统一管理课程表、学习资料、出版任务和运行日志。</p>
      <nav>
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="nav-link"
          :class="{ active: route.path === item.to }"
        >
          {{ item.label }}
        </RouterLink>
      </nav>
    </aside>
    <main class="content">
      <RouterView />
    </main>
  </div>
</template>