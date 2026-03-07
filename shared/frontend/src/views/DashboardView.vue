<template>
  <div class="dashboard">
    <el-header>
      <h1>学习仪表盘</h1>
      <el-button @click="logout">退出</el-button>
    </el-header>
    <el-main>
      <el-row :gutter="20">
        <el-col :span="8">
          <el-card>
            <h3>学习进度</h3>
            <el-progress :percentage="75" />
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card>
            <h3>已完成课程</h3>
            <p>3 / 10</p>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card>
            <h3>学习时长</h3>
            <p>25 小时</p>
          </el-card>
        </el-col>
      </el-row>
      <el-divider />
      <h3>推荐课程</h3>
      <el-row :gutter="20">
        <el-col :span="12" v-for="course in courses" :key="course.id">
          <el-card>
            <h4>{{ course.title }}</h4>
            <p>{{ course.description }}</p>
            <el-button type="primary" @click="startCourse(course.id)">开始学习</el-button>
          </el-card>
        </el-col>
      </el-row>
    </el-main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const courses = ref([
  { id: 1, title: 'Python 入门', description: '学习 Python 编程基础' },
  { id: 2, title: 'Vue3 开发', description: '学习 Vue3 框架' },
])

const startCourse = (id: number) => {
  router.push(`/course/${id}`)
}

const logout = () => {
  localStorage.removeItem('token')
  router.push('/login')
}
</script>

<style scoped>
.dashboard {
  height: 100vh;
}
.el-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  border-bottom: 1px solid #e6e6e6;
}
</style>
