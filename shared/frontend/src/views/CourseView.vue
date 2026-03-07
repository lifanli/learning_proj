<template>
  <div class="course">
    <h1>{{ course.title }}</h1>
    <p>{{ course.description }}</p>
    <el-divider />
    <h3>课程内容</h3>
    <el-timeline>
      <el-timeline-item timestamp="第 1 课" placement="top">
        <el-card>
          <h4>课程介绍</h4>
          <p>了解课程大纲和学习目标</p>
        </el-card>
      </el-timeline-item>
      <el-timeline-item timestamp="第 2 课" placement="top">
        <el-card>
          <h4>基础知识</h4>
          <p>学习核心概念</p>
        </el-card>
      </el-timeline-item>
    </el-timeline>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const course = ref({
  id: route.params.id,
  title: 'Python 入门',
  description: '学习 Python 编程基础'
})
</script>
