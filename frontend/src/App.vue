<template>
  <div class="app-layout">
    <!-- 左侧侧边栏 -->
<!-- frontend/src/App.vue -->
<Sidebar :open="sidebarOpen" @close="closeSidebar" />

    <!-- 右侧主内容区 -->
    <main class="workspace">
      <header>
          <button class="menu-btn" @click="toggleSidebar" aria-label="Toggle sidebar">
        ☰
      </button>
        <h1>RAG Web</h1>
        <p>上传文档后，向你的本地知识库提问。</p>
      </header>

      <el-card class="upload-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>文档上传与索引</span>
            <el-button type="primary" :loading="uploading" :disabled="!hasPendingFiles" @click="uploadFiles">
              上传并索引
            </el-button>
          </div>
        </template>

        <el-upload
          drag
          multiple
          :auto-upload="false"
          :show-file-list="false"
          :accept="acceptedFormats"
          @change="selectFiles"
        >
          <div class="upload-hint">
            <strong>拖拽文件到此处，或点击选择</strong>
            <span>支持 TXT、Markdown、PDF、DOCX；可一次选择多个文件</span>
          </div>
        </el-upload>

        <div v-if="uploads.length" class="upload-list">
          <div v-for="file in uploads" :key="file.uid" class="upload-item">
            <div class="file-row">
              <span class="file-name">{{ file.name }}</span>
              <el-button v-if="file.status !== 'success'" text type="danger" :disabled="uploading" @click="removeFile(file.uid)">
                移除
              </el-button>
              <el-tag v-else type="success" size="small">已索引</el-tag>
            </div>
            <el-progress
              :percentage="file.percentage"
              :status="file.status === 'error' ? 'exception' : file.status === 'success' ? 'success' : undefined"
            />
            <small v-if="file.detail" :class="{ 'error-text': file.status === 'error' }">{{ file.detail }}</small>
          </div>
        </div>
      </el-card>

      <!-- 聊天卡片 -->
      <el-card class="chat-card" shadow="never">
        <template #header>
          <div class="chat-card-header">
            <span>知识库问答</span>
            <el-button size="small" text @click="shareAll" v-if="messages.length">分享全部</el-button>
          </div>
        </template>

        <div ref="messageList" class="message-list">
          <el-empty v-if="!messages.length" description="上传文档后，开始提问吧" />
          <div v-for="(msg, idx) in messages" :key="idx" class="message" :class="msg.role">
            <div class="message-label">{{ msg.role === 'user' ? '你' : 'RAG 助手' }}</div>
            <div class="bubble" :class="{ error: msg.error }">
              <template v-if="msg.loading">正在检索并生成回答…</template>
              <template v-else>{{ msg.content }}</template>
              </div>
                <!-- 🆕 用户消息的操作按钮 -->
                <!-- 🆕 用户消息的操作按钮（在气泡下方） -->
            <div v-if="!msg.loading && msg.role === 'user' && msg.content" class="message-actions">
              <el-button size="small" text @click="copyMessage(msg.content)"><svg width="24" height="24" viewBox="0 0 24 24" fill="none"
                                      xmlns="http://www.w3.org/2000/svg">
                                    <rect x="7" y="7" width="12" height="12" rx="3"
                                          stroke="#8A8D94" stroke-width="2"/>
                                    <path d="M7 17H6C4.343 17 3 15.657 3 14V6C3 4.343 4.343 3 6 3H14C15.657 3 17 4.343 17 6V7"
                                          stroke="#8A8D94" stroke-width="2"
                                          stroke-linecap="round"/>
                                  </svg></el-button>
              <el-button size="small" text @click="editMessage(idx)"><svg width="24" height="24" viewBox="0 0 24 24" fill="none"
                      xmlns="http://www.w3.org/2000/svg">
                    <path d="M4 20L4.8 16.2L15.8 5.2C16.6 4.4 17.9 4.4 18.7 5.2L19 5.5C19.8 6.3 19.8 7.6 19 8.4L8 19.4L4 20Z"
                          stroke="#8A8D94"
                          stroke-width="2"
                          stroke-linejoin="round"/>
                    <path d="M14.5 6.5L17.5 9.5"
                          stroke="#8A8D94"
                          stroke-width="2"
                          stroke-linecap="round"/>
                    <path d="M15 20H21"
                          stroke="#8A8D94"
                          stroke-width="2"
                          stroke-linecap="round"/>
                  </svg></el-button>
                              </div>
                      <!-- 复制按钮 -->
            <div v-if="!msg.loading && msg.role === 'assistant' && msg.content" class="message-actions">
              <el-button size="small" text @click="copyMessage(msg.content)"><svg width="24" height="24" viewBox="0 0 24 24" fill="none"
                      xmlns="http://www.w3.org/2000/svg">
                    <rect x="7" y="7" width="12" height="12" rx="3"
                          stroke="#8A8D94" stroke-width="2"/>
                    <path d="M7 17H6C4.343 17 3 15.657 3 14V6C3 4.343 4.343 3 6 3H14C15.657 3 17 4.343 17 6V7"
                          stroke="#8A8D94" stroke-width="2"
                          stroke-linecap="round"/>
                  </svg></el-button>
            </div>
            <div v-if="msg.sources?.length" class="sources">
              <span>引用来源：</span>
              <el-tag
                v-for="source in msg.sources"
                :key="`${source.source}-${source.chunk_index}`"
                class="source-link"
                size="small"
                effect="plain"
                @click="openSource(source)"
              >
                {{ source.source }} · 段落 {{ source.chunk_index + 1 }}
              </el-tag>
            </div>
          </div>
        </div>

        <div class="ask-box">
          <el-input
            v-model="question"
            type="textarea"
            :rows="2"
            resize="none"
            placeholder="输入关于已上传文档的问题…"
            @keydown.enter.exact.prevent="ask"
          />
          <div class="ask-actions">
            <span>Enter 发送，Shift+Enter 换行</span>
            <el-button type="primary" :loading="sending" :disabled="!question.trim()" @click="ask">
              发送
            </el-button>
          </div>
        </div>
      </el-card>
    </main>
  </div>

  <!-- 引用片段弹窗 -->
  <el-dialog v-model="sourceDialogVisible" :title="selectedSource?.source || '引用片段'" width="720px" class="source-dialog">
    <el-skeleton v-if="sourceLoading" :rows="5" animated />
    <el-alert v-else-if="sourceError" :title="sourceError" type="error" :closable="false" show-icon />
    <template v-else-if="selectedSource">
      <p class="source-meta">{{ selectedSource.source }} · 段落 {{ selectedSource.chunk_index + 1 }}</p>
      <article class="source-content">{{ selectedSource.content }}</article>
    </template>
  </el-dialog>
</template>

<script setup>
import Sidebar from './components/Sidebar.vue'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useRagStore } from './stores/ragStore'


// ===== 状态 =====
const sidebarOpen = ref(false)
const toggleSidebar = () => {
sidebarOpen.value = !sidebarOpen.value
}
const closeSidebar = () => {
sidebarOpen.value = false
}
const store = useRagStore()
const acceptedFormats = '.txt,.md,.pdf,.docx'
const API_BASE = 'https://rag-production-18b0.up.railway.app'
const CHAT_STORAGE_KEY = 'rag-web-chat-history-v1'

const uploads = ref([])
const uploading = ref(false)
const question = ref('')
const sending = ref(false)
const messages = ref([])
const messageList = ref(null)
const sourceDialogVisible = ref(false)
const sourceLoading = ref(false)
const sourceError = ref('')
const selectedSource = ref(null)

const hasPendingFiles = computed(() => uploads.value.some((file) => file.status !== 'success'))

// ===== 聊天记录持久化 =====
function restoreChat() {
  try {
    const savedMessages = JSON.parse(localStorage.getItem(CHAT_STORAGE_KEY) || '[]')
    if (Array.isArray(savedMessages)) {
      messages.value = savedMessages.filter((message) => message?.content && !message.loading)
    }
  } catch {
    localStorage.removeItem(CHAT_STORAGE_KEY)
  }
}

function persistChat() {
  const persistentMessages = messages.value
    .filter((message) => !message.loading)
    .map(({ role, content, sources = [], error = false }) => ({ role, content, sources, error }))
  localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(persistentMessages))
}

watch(messages, () => persistChat(), { deep: true })

// ===== 加载已索引文档 =====
async function loadIndexedDocuments() {
  // 什么都不做 —— 中间区域不再显示历史文件
  // 文件列表只在侧边栏展示
}
// ===== 文件上传 =====
function selectFiles(uploadFile) {
  if (uploads.value.some((file) => file.uid === uploadFile.uid)) return
  uploads.value.push({
    uid: uploadFile.uid,
    raw: uploadFile.raw,
    name: uploadFile.name,
    percentage: 0,
    status: 'ready',
    detail: '',
  })
}

function removeFile(uid) {
  if (uploading.value) return
  uploads.value = uploads.value.filter((file) => file.uid !== uid)
}

async function uploadFiles() {
  const pendingFiles = uploads.value.filter((file) => file.status !== 'success')
  if (!pendingFiles.length) return

  uploading.value = true
  try {
    for (const item of pendingFiles) {
      item.status = 'uploading'
      item.percentage = 0
      const formData = new FormData()
      formData.append('file', item.raw)
      try {
        const { data } = await axios.post(`${API_BASE}/upload`, formData, {
          onUploadProgress: (event) => {
            if (event.total) item.percentage = Math.round((event.loaded / event.total) * 100)
          },
        })
        // 上传成功
        item.status = 'success'
        item.percentage = 100
        item.detail = `已索引 ${data.chunks} 个段落`

        // 1. 同步到侧边栏 store
        const existingFile = store.files.find(f => f.name === item.name)
        if (!existingFile) {
          store.addFile(item.name)
        }

        // 2. 从 uploads 中移除该文件（不再显示在中间区域）
        //    用 setTimeout 确保界面更新后再删除，避免闪烁
        setTimeout(() => {
          const idx = uploads.value.findIndex(f => f.uid === item.uid)
          if (idx > -1) {
            uploads.value.splice(idx, 1)
          }
        }, 100)
      } catch (error) {
        item.status = 'error'
        item.detail = error.response?.data?.detail || '上传或索引失败'
        // 如果后端返回智谱 embedding 错误，显示更具体信息
        if (error.response?.data?.detail?.includes('input数组')) {
          item.detail = '文件过大，请分段上传或联系管理员'
        }
      }
    }
    const failed = pendingFiles.filter((file) => file.status === 'error').length
    if (failed) {
      ElMessage.warning(`${failed} 个文件处理失败，请重试`)
    } else {
      ElMessage.success('文件已上传并完成索引')
    }
  } finally {
    uploading.value = false
  }
}

// 修改用户消息：把内容回填到输入框
const editMessage = (index) => {
  const msg = messages.value[index]
  if (msg && msg.role === 'user') {
    question.value = msg.content
    // 可选：删除这条消息，让用户重新发送
    // messages.value.splice(index, 1)
    // 或者保留原消息，在发送新消息时替换
    // 这里采用简单方式：把内容填入输入框，用户手动修改后发送
    // 也可以自动删除原消息
    if (confirm('删除原消息并重新编辑发送吗？')) {
      messages.value.splice(index, 1)
      // 同时删除对应的助手回复（如果有）
      if (index < messages.value.length && messages.value[index]?.role === 'assistant') {
        messages.value.splice(index, 1)
      }
      // 聚焦输入框
      nextTick(() => {
        const input = document.querySelector('.ask-box textarea')
        if (input) input.focus()
      })
    }
  }
}

// ===== 滚动 =====
async function scrollToLatest() {
  await nextTick()
  if (messageList.value) messageList.value.scrollTop = messageList.value.scrollHeight
}

// ===== 引用片段弹窗 =====
async function openSource(source) {
  sourceDialogVisible.value = true
  sourceLoading.value = true
  sourceError.value = ''
  selectedSource.value = null
  try {
    const { data } = await axios.get(`${API_BASE}/documents/chunk`, {
      params: { source: source.source, chunk_index: source.chunk_index },
    })
    selectedSource.value = data
  } catch (error) {
    sourceError.value = error.response?.data?.detail || '无法加载引用片段，请稍后重试。'
  } finally {
    sourceLoading.value = false
  }
}

// ===== 问答 =====
async function ask() {
  const text = question.value.trim()
  if (!text || !text.length) return

  messages.value.push({ role: 'user', content: text })
  question.value = ''
  sending.value = true
  await scrollToLatest()

  messages.value.push({ role: 'assistant', content: '', sources: [], loading: true })
  const assistantMessage = messages.value[messages.value.length - 1]

  try {
    const { data } = await axios.post(`${API_BASE}/ask`, { question: text })
    
  // 清理回答内容
  let cleanAnswer = data.answer || ''
  // 1. 清理【来源：...】标记
  cleanAnswer = cleanAnswer.replace(/【来源:.*?】/g, '').trim()
  // 2. 清理单独成行的 *** 或 ---
  cleanAnswer = cleanAnswer.replace(/^[\*\-\_]{3,}\s*$/gm, '')
  // 3. 清理行内的 ***
  cleanAnswer = cleanAnswer.replace(/\*\*\*/g, '')
  // 4. 清理单独的 * 字符（保留中文标点，不破坏正常文字）
  //    注意：只清理英文语境下的 *，不清理中文中的 *
  cleanAnswer = cleanAnswer.replace(/\*+/g, '')
    
    assistantMessage.content = cleanAnswer || data.answer || '未获取到回答'
    assistantMessage.sources = data.sources || []

    // 同步到侧边栏 store
 // 使用当前选中的文件 ID，如果没有则取第一个文件
    const targetFileId = store.currentFileID || (store.files.length > 0 ? store.files[0].id : null)
  console.log('提问时 currentFileID =', store.currentFileID, 'targetFileId =', targetFileId)
    if (targetFileId) {
      store.addMessage(targetFileId, text, cleanAnswer || data.answer || '')
    }
  } catch (error) {
    assistantMessage.content = error.response?.data?.detail || '服务暂时不可用，请稍后再试。'
    assistantMessage.error = true
  } finally {
    assistantMessage.loading = false
    sending.value = false
    persistChat()
    await scrollToLatest()
  }
}

// ===== 复制 / 分享 =====
const copyMessage = (content) => {
  navigator.clipboard.writeText(content).then(() => {
    ElMessage.success('已复制到剪贴板')
  }).catch(() => ElMessage.error('复制失败'))
}

const shareAll = () => {
  const text = messages.value
    .filter(m => !m.loading && m.content)
    .map(m => `${m.role === 'user' ? '👤' : '🤖'} ${m.content}`)
    .join('\n\n')
  if (!text) {
    ElMessage.warning('暂无对话内容可分享')
    return
  }
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('全部对话已复制')
  }).catch(() => ElMessage.error('分享失败'))
}

// ===== 初始化 =====
restoreChat()
onMounted(async () => {  
  window.store = store  // 把 store 挂到全局，方便调试
  await scrollToLatest()
  
  // 进入页面时立即检查一次
  store.cleanTrash()

  // 然后每 5 分钟检查一次
  setInterval(() => {
    store.cleanTrash()
  }, 5 * 60 * 1000)
})
</script>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

.workspace {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding: 12px 24px 20px 24px; /* 上下左右都缩小 */
  overflow-y: auto;
  background: #f5f7fa;
}

* {
  box-sizing: border-box;
}

html,
body {
  margin: 0;
  padding: 0;
  height: 100%;
  background: #f5f7fa;
}

body {
  margin: 0;
  background: #f5f7fa;
  color: #1f2937;
  font-family: Inter, "Microsoft YaHei", sans-serif;
}

header {
  margin-bottom: 12px;
}

h1 {
  margin: 0 0 4px;
  font-size: 22px;
}

header p {
  margin: 0;
  font-size: 13px;
  color: #64748b;
}
.upload-card,
.chat-card {
  margin-bottom: 20px;
  border-radius: 12px;
}

.card-header,
.file-row,
.ask-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.card-header {
  font-weight: 600;
}

.chat-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.upload-card .el-upload {
  min-height: 180px !important; /* 拉高上传区域 */
}
.upload-hint {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  min-height: 160px;
  padding: 20px;
  color: #64748b;
}

.upload-hint strong {
  color: #334155;
}

.upload-list {
  display: grid;
  gap: 12px;
  margin-top: 18px;
  overflow: visible;
}

.upload-item {
  padding: 10px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: visible;
}

.upload-item .el-progress {
  margin-top: 8px;
  display: block !important;
}

.file-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.upload-item small {
  display: block;
  margin-top: 6px;
  color: #64748b;
}

.error-text {
  color: #dc2626 !important;
}

.message-list {
  min-height: 280px;
  max-height: 480px;
  overflow-y: auto;
  padding: 4px 2px 16px;
}

.message {
  display: flex;
  flex-direction: column;
  margin: 14px 0;
}

.message.user {
  align-items: flex-end;
}

.message-label {
  margin-bottom: 5px;
  color: #64748b;
  font-size: 12px;
}

.bubble {
  max-width: 82%;
  padding: 11px 14px;
  border-radius: 10px;
  background: #f1f5f9;
  white-space: pre-wrap;
  line-height: 1.6;
}

.user .bubble {
  background: #409eff;
  color: white;
}

.bubble.error {
  background: #fef2f2;
  color: #b91c1c;
}

.message-actions {
  display: flex;
  gap: 2px;
  margin-top: 6px;
}

.message-actions .el-button {
  padding: 2px 6px;
  font-size: 12px;
}

.sources {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  color: #64748b;
  font-size: 12px;
}

.source-link {
  cursor: pointer;
}

.source-link:hover {
  background: #ecf5ff;
}

.ask-box {
  border-top: 1px solid #e5e7eb;
  padding-top: 16px;
}

.ask-actions {
  margin-top: 10px;
  color: #94a3b8;
  font-size: 12px;
}

.source-meta {
  margin: 0 0 12px;
  color: #64748b;
  font-size: 13px;
}

.source-content {
  max-height: 55vh;
  overflow-y: auto;
  padding: 16px;
  border-radius: 8px;
  background: #f8fafc;
  white-space: pre-wrap;
  line-height: 1.75;
}

@media (max-width: 600px) {
  .workspace {
    padding: 12px 16px;
  }

  .bubble {
    max-width: 94%;
  }
}

/* frontend/src/App.vue */
/* 在 style 中添加 */

.menu-btn {
  display: none;
  font-size: 24px;
  background: none;
  border: none;
  cursor: pointer;
  color: inherit;
  padding: 8px;
  margin-right: 8px;
}

@media (max-width: 768px) {
  .menu-btn {
    display: inline-block;
  }
}

</style>