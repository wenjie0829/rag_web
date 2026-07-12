<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const acceptedFormats = '.txt,.md,.pdf,.docx'
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
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

async function loadIndexedDocuments() {
  try {
    const { data } = await axios.get(`${API_BASE}/documents`)
    uploads.value = (data.documents || []).map((document, index) => ({
      uid: `indexed-${document.source}-${index}`,
      raw: null,
      name: document.source,
      percentage: 100,
      status: 'success',
      detail: `已索引 ${document.chunks} 个段落`,
    }))
  } catch {
    // The chat remains usable if the document-list request is temporarily unavailable.
  }
}

watch(
  messages,
  () => persistChat(),
  { deep: true },
)

function persistChat() {
  const persistentMessages = messages.value
    .filter((message) => !message.loading)
    .map(({ role, content, sources = [], error = false }) => ({ role, content, sources, error }))
  localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(persistentMessages))
}

restoreChat()
onMounted(async () => {
  await loadIndexedDocuments()
  await scrollToLatest()
})

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
    // Upload in sequence so the local embedding model indexes documents predictably.
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
        item.status = 'success'
        item.percentage = 100
        item.detail = `已索引 ${data.chunks} 个段落`
      } catch (error) {
        item.status = 'error'
        item.detail = error.response?.data?.detail || '上传或索引失败'
      }
    }
    const failed = pendingFiles.filter((file) => file.status === 'error').length
    ElMessage[failed ? 'warning' : 'success'](failed ? `${failed} 个文件处理失败` : '文件已上传并完成索引')
  } finally {
    uploading.value = false
  }
}

async function scrollToLatest() {
  await nextTick()
  if (messageList.value) messageList.value.scrollTop = messageList.value.scrollHeight
}

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

async function ask() {
  const text = question.value.trim()
  if (!text || sending.value) return

  messages.value.push({ role: 'user', content: text })
  question.value = ''
  sending.value = true
  await scrollToLatest()

  messages.value.push({ role: 'assistant', content: '', sources: [], loading: true })
  // Read the just-inserted item back from the reactive array before updating it.
  // This guarantees the completed response triggers the persistence watcher.
  const assistantMessage = messages.value[messages.value.length - 1]
  try {
    const { data } = await axios.post(`${API_BASE}/ask`, { question: text })
    assistantMessage.content = data.answer
    assistantMessage.sources = data.sources || []
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
</script>

<template>
  <main class="workspace">
    <header>
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

      <el-upload drag multiple :auto-upload="false" :show-file-list="false" :accept="acceptedFormats" @change="selectFiles">
        <div class="upload-hint">
          <strong>拖拽文件到此处，或点击选择</strong>
          <span>支持 TXT、Markdown、PDF、DOCX；可一次选择多个文件</span>
        </div>
      </el-upload>

      <div v-if="uploads.length" class="upload-list">
        <div v-for="file in uploads" :key="file.uid" class="upload-item">
          <div class="file-row">
            <span class="file-name">{{ file.name }}</span>
            <el-button v-if="file.status !== 'success'" text type="danger" :disabled="uploading" @click="removeFile(file.uid)">移除</el-button>
            <el-tag v-else type="success" size="small">已索引</el-tag>
          </div>
          <el-progress :percentage="file.percentage" :status="file.status === 'error' ? 'exception' : file.status === 'success' ? 'success' : undefined" />
          <small v-if="file.detail" :class="{ 'error-text': file.status === 'error' }">{{ file.detail }}</small>
        </div>
      </div>
    </el-card>

    <el-card class="chat-card" shadow="never">
      <template #header><span>知识库问答</span></template>
      <div ref="messageList" class="message-list">
        <el-empty v-if="!messages.length" description="上传文档后，开始提问吧" />
        <article v-for="(message, index) in messages" :key="index" class="message" :class="message.role">
          <div class="message-label">{{ message.role === 'user' ? '你' : 'RAG 助手' }}</div>
          <div class="bubble" :class="{ error: message.error }">
            <template v-if="message.loading">正在检索并生成回答…</template>
            <template v-else>{{ message.content }}</template>
          </div>
          <div v-if="message.sources?.length" class="sources">
            <span>引用来源：</span>
            <el-tag v-for="source in message.sources" :key="`${source.source}-${source.chunk_index}`" class="source-link" size="small" effect="plain" @click="openSource(source)">
              {{ source.source }} · 段落 {{ source.chunk_index + 1 }}
            </el-tag>
          </div>
        </article>
      </div>
      <div class="ask-box">
        <el-input v-model="question" type="textarea" :rows="3" resize="none" placeholder="输入关于已上传文档的问题…" @keydown.enter.exact.prevent="ask" />
        <div class="ask-actions">
          <span>Enter 发送，Shift + Enter 换行</span>
          <el-button type="primary" :loading="sending" :disabled="!question.trim()" @click="ask">发送</el-button>
        </div>
      </div>
    </el-card>

    <el-dialog v-model="sourceDialogVisible" :title="selectedSource?.source || '引用片段'" width="720px" class="source-dialog">
      <el-skeleton v-if="sourceLoading" :rows="5" animated />
      <el-alert v-else-if="sourceError" :title="sourceError" type="error" :closable="false" show-icon />
      <template v-else-if="selectedSource">
        <p class="source-meta">{{ selectedSource.source }} · 段落 {{ selectedSource.chunk_index + 1 }}</p>
        <article class="source-content">{{ selectedSource.content }}</article>
      </template>
    </el-dialog>
  </main>
</template>

<style>
* { box-sizing: border-box; }
body { margin: 0; background: #f5f7fa; color: #1f2937; font-family: Inter, "Microsoft YaHei", sans-serif; }
.workspace { width: min(960px, calc(100% - 32px)); margin: 40px auto; }
header { margin-bottom: 24px; }
h1 { margin: 0 0 8px; font-size: 30px; }
header p { margin: 0; color: #64748b; }
.upload-card, .chat-card { margin-bottom: 20px; border-radius: 12px; }
.card-header, .file-row, .ask-actions { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.card-header { font-weight: 600; }
.upload-hint { display: grid; gap: 8px; padding: 12px; color: #64748b; }
.upload-hint strong { color: #334155; }
.upload-list { display: grid; gap: 12px; margin-top: 18px; }
.upload-item { padding: 10px 12px; border: 1px solid #e5e7eb; border-radius: 8px; }
.file-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.upload-item small { display: block; margin-top: 6px; color: #64748b; }
.error-text { color: #dc2626 !important; }
.message-list { min-height: 280px; max-height: 480px; overflow-y: auto; padding: 4px 2px 16px; }
.message { display: flex; flex-direction: column; margin: 14px 0; }
.message.user { align-items: flex-end; }
.message-label { margin-bottom: 5px; color: #64748b; font-size: 12px; }
.bubble { max-width: 82%; padding: 11px 14px; border-radius: 10px; background: #f1f5f9; white-space: pre-wrap; line-height: 1.6; }
.user .bubble { background: #409eff; color: white; }
.bubble.error { background: #fef2f2; color: #b91c1c; }
.sources { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-top: 8px; color: #64748b; font-size: 12px; }
.source-link { cursor: pointer; }
.source-link:hover { background: #ecf5ff; }
.ask-box { border-top: 1px solid #e5e7eb; padding-top: 16px; }
.ask-actions { margin-top: 10px; color: #94a3b8; font-size: 12px; }
.source-meta { margin: 0 0 12px; color: #64748b; font-size: 13px; }
.source-content { max-height: 55vh; overflow-y: auto; padding: 16px; border-radius: 8px; background: #f8fafc; white-space: pre-wrap; line-height: 1.75; }
@media (max-width: 600px) { .workspace { width: min(100% - 20px, 960px); margin-top: 20px; } .bubble { max-width: 94%; } }
</style>
