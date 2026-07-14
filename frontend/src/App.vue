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
                  <el-button size="small" text @click="reaskMessage(idx)"><svg width="24" height="24" viewBox="0 0 24 24" fill="none"
     xmlns="http://www.w3.org/2000/svg">
  <path d="M20 11C19.5 7.1 16.2 4 12 4C7.6 4 4 7.6 4 12C4 16.4 7.6 20 12 20C15.2 20 18 18.1 19.3 15.3"
                            stroke="#8A8D94"
                            stroke-width="2"
                            stroke-linecap="round"/>
                      <path d="M20 5V11H14"
                            stroke="#8A8D94"
                            stroke-width="2"
                            stroke-linecap="round"
                            stroke-linejoin="round"/>
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
// ===== 加载已索引文档（从后端同步） =====
async function loadIndexedDocuments() {
  try {
    const { data } = await axios.get(`${API_BASE}/documents`)
    const docs = data.documents || []
    
    // 更新 uploads（用于中间区域显示）
    uploads.value = docs.map(doc => ({
      uid: `indexed-${doc.source}`,
      raw: null,
      name: doc.source,
      percentage: 100,
      status: 'success',
      detail: `已索引 ${doc.chunks} 个段落`,
    }))

    // 同步到侧边栏 store（去重）
    docs.forEach(doc => {
      const exists = store.files.find(f => f.name === doc.source)
      if (!exists) {
        store.addFile(doc.source)
      }
    })

    console.log(`✅ 从后端加载了 ${docs.length} 个文件`)
  } catch (error) {
    console.warn('加载索引文档失败:', error)
  }
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
        const response = await axios.post(`${API_BASE}/upload`, formData, {
          onUploadProgress: (event) => {
            if (event.total) item.percentage = Math.round((event.loaded / event.total) * 100)
          },
        })
        
        console.log('上传响应:', response.data)
        
        // 检查响应是否包含 chunks 字段
        if (response.data && response.data.chunks !== undefined) {
          item.status = 'success'
          item.percentage = 100
          item.detail = `已索引 ${response.data.chunks} 个段落`
        } else {
          throw new Error('响应格式异常')
        }

        // 同步到侧边栏 store
        const existingFile = store.files.find(f => f.name === item.name)
        if (!existingFile) {
          store.addFile(item.name)
        }

        setTimeout(() => {
          const idx = uploads.value.findIndex(f => f.uid === item.uid)
          if (idx > -1) {
            uploads.value.splice(idx, 1)
          }
        }, 100)
      } catch (error) {
        console.error('上传错误:', error)
        item.status = 'error'
        item.detail = error.response?.data?.detail || error.message || '上传或索引失败'
      }
    }
    const failed = pendingFiles.filter((file) => file.status === 'error').length
    if (failed) {
      ElMessage.warning(`${failed} 个文件处理失败`)
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

// ===== 重新回答 =====
const reaskMessage = async (index) => {
  const msg = messages.value[index]
  if (!msg || msg.role !== 'assistant') return

  const userMsg = messages.value[index - 1]
  if (!userMsg || userMsg.role !== 'user') {
    ElMessage.warning('未找到对应的用户问题')
    return
  }

  // 保存原回答（如果失败可以恢复）
  const originalContent = msg.content
  const originalSources = msg.sources

  msg.loading = true
  msg.content = '正在重新生成回答…'
  msg.sources = []

  try {
    const { data } = await axios.post(`${API_BASE}/ask`, { question: userMsg.content })
    
    let cleanAnswer = data.answer || ''
    cleanAnswer = cleanAnswer.replace(/【来源:.*?】/g, '').trim()
    cleanAnswer = cleanAnswer.replace(/^[\*\-\_]{3,}\s*$/gm, '')
    cleanAnswer = cleanAnswer.replace(/\*\*\*/g, '')
    cleanAnswer = cleanAnswer.replace(/\*+/g, '')
    
    msg.content = cleanAnswer || data.answer || '未获取到回答'
    msg.sources = data.sources || []
  } catch (error) {
    // 失败时恢复原回答
    msg.content = originalContent || '重新回答失败，请重试'
    msg.sources = originalSources || []
    ElMessage.error('重新回答失败，已恢复原回答')
  } finally {
    msg.loading = false
    persistChat()
    await scrollToLatest()
  }
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
oonMounted(async () => {
  // 从后端加载已索引的文件列表
  await loadIndexedDocuments()
  
  // 如果加载后 store.files 为空，尝试从 localStorage 恢复（兼容旧数据）
  if (store.files.length === 0) {
    store._load()
  }
  
  await scrollToLatest()
  
  // 进入页面时立即检查一次回收站
  store.cleanTrash()

  // 每 5 分钟检查一次回收站
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