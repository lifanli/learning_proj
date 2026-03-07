<template>
  <div class="chat">
    <el-header>
      <h1>智能体助手</h1>
    </el-header>
    <el-main>
      <div class="messages">
        <div v-for="msg in messages" :key="msg.id" :class="['message', msg.role]">
          <div class="bubble">{{ msg.content }}</div>
        </div>
      </div>
      <div class="input-area">
        <el-input v-model="inputMessage" placeholder="输入问题..." @keyup.enter="sendMessage" />
        <el-button type="primary" @click="sendMessage">发送</el-button>
      </div>
    </el-main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const messages = ref([
  { id: 1, role: 'assistant', content: '你好！我是你的学习助手，有什么问题吗？' }
])
const inputMessage = ref('')

const sendMessage = async () => {
  if (!inputMessage.value.trim()) return
  
  messages.value.push({
    id: Date.now(),
    role: 'user',
    content: inputMessage.value
  })
  
  // TODO: 调用后端 API
  // const response = await api.chat(inputMessage.value)
  
  inputMessage.value = ''
}
</script>

<style scoped>
.chat {
  height: 100vh;
  display: flex;
  flex-direction: column;
}
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}
.message {
  margin-bottom: 20px;
}
.message.user {
  text-align: right;
}
.bubble {
  display: inline-block;
  padding: 10px 15px;
  border-radius: 10px;
  max-width: 70%;
}
.message.user .bubble {
  background: #409EFF;
  color: white;
}
.message.assistant .bubble {
  background: #f0f0f0;
}
.input-area {
  display: flex;
  gap: 10px;
  padding: 20px;
  border-top: 1px solid #e6e6e6;
}
</style>
