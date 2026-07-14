<template>
  <!-- 遮罩层 -->
  <div v-if="props.open" class="sidebar-overlay" @click="emit('close')"></div>

  <!-- 侧边栏 -->
  <div class="sidebar" :class="{ open: props.open }">
    <!-- 头部 -->
    <div class="sidebar-header">
      <h3>📁 我的文件</h3>
      <span class="file-count">{{ files.length }}</span>
    </div>

    <!-- 搜索框 -->
    <div class="sidebar-search" ref="searchContainer">
      <input
        ref="searchInput"
        type="text"
        v-model="searchKeyword"
        placeholder="搜索问答..."
        @input="onInputChange"
        @focus="showHistory = true"
        @keyup.enter="performSearch"
        @keyup.esc="clearSearch"
      />
      <span v-if="searchKeyword" class="search-clear" @click="clearSearch">✕</span>

      <div v-if="showHistory && searchHistory.length > 0 && !searchKeyword.trim()" class="search-history">
        <div class="history-title">搜索历史</div>
        <div
          v-for="item in searchHistory"
          :key="item"
          class="history-item"
          @mousedown.prevent="applyHistorySearch(item)"
        >
           {{ item }}
        </div>
        <div class="history-clear" @mousedown.prevent="clearHistory">清空历史</div>
      </div>
    </div>

    <!-- 文件列表 -->
    <div class="session-list">
      <template v-if="searchKeyword.trim()">
        <div v-if="searchResults.length === 0" class="no-result">
          <span>未找到匹配的问答...</span>
        </div>
        <div
          v-for="result in searchResults"
          :key="result.fileId + (result.msg ? result.msg.id : 'file')"
          class="qa-item search-item"
          @click="goToSearchResult(result)"
        >
          <div v-if="result.isFileHeader">
            <div class="search-file-result">
              <span class="q">📄 {{ result.fileName }}</span>
              <button class="preview-btn" @click.stop="previewFile(result.fileName)">预览</button>
            </div>
            <div class="a">包含 {{ getFileMessageCount(result.fileId) }} 条问答</div>
          </div>
          <div v-else>
            <div class="q">Q：{{ truncate(result.msg.question, 40) }}</div>
            <div class="a">A：{{ truncate(result.msg.answer, 60) }}</div>
            <div class="qa-meta">{{ result.fileName }} · {{ formatTime(result.msg.timestamp) }}</div>
          </div>
        </div>
      </template>

      <template v-else>
        <div v-if="files.length === 0" class="empty-state">
          <p>还没有上传文件</p>
          <p class="hint">上传后，问答记录会出现在这里</p>
        </div>
        <div v-for="file in files" :key="file.id" class="file-item" :data-file-id="file.id">
          <div class="file-header" @click="toggleFile(file.id)">
            <div class="file-info">
              <span class="file-icon">📄</span>
              <span class="file-name">{{ file.name }}</span>
              <button class="preview-btn" @click.stop="previewFile(file.name)">预览</button>
            </div>
            <div class="file-actions">
              <span class="badge">{{ file.messages.length }}</span>
              <button class="delete-btn" @click.stop="handleDeleteFile(file.id)">✕</button>
            </div>
          </div>

          <div v-if="expandedFiles.includes(file.id)" class="file-messages">
            <div v-if="file.messages.length === 0" class="empty-msg">暂无问答记录</div>
            <div
              v-for="msg in file.messages"
              :key="msg.id"
              class="qa-item"
              @click="openQaDialog(file.name, msg)"
            >
              <div class="qa-header">
                <div class="q">Q：{{ truncate(msg.question, 40) }}</div>
                <button class="qa-delete-btn" @click.stop="handleDeleteMessage(file.id, msg.id)">✕</button>
              </div>
              <div class="a">A：{{ truncate(msg.answer, 60) }}</div>
              <div class="qa-time">{{ formatTime(msg.timestamp) }}</div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- 底部 -->
    <div class="sidebar-footer">
      <button class="trash-btn" @click="openTrashDialog">
        🗑️ 回收站 <span v-if="trashCount" class="trash-badge">{{ trashCount }}</span>
      </button>
      <button class="clear-btn" @click="handleClearAll">清空所有</button>
    </div>
  </div>

  <!-- 预览弹窗 -->
  <el-dialog v-model="previewVisible" :title="previewFileName" width="80%" top="5vh" destroy-on-close>
    <div v-if="previewLoading" class="preview-loading">加载中...</div>
    <pre v-else class="preview-content">{{ previewContent }}</pre>
  </el-dialog>

  <!-- 问答弹窗 -->
  <el-dialog v-model="qaDialogVisible" :title="qaDialogTitle" width="70%" top="5vh" destroy-on-close>
    <div class="qa-dialog-content">
      <div class="qa-dialog-question">
        <span class="label">Q：</span>
        <span>{{ qaDialogQuestion }}</span>
      </div>
      <div class="qa-dialog-answer">
        <span class="label">A：</span>
        <div class="qa-dialog-answer-text">{{ qaDialogAnswer }}</div>
      </div>
    </div>
  </el-dialog>

  <!-- 回收站弹窗 -->
  <el-dialog v-model="trashDialogVisible" title="🗑️ 回收站" width="85%" top="5vh" destroy-on-close>
    <div class="trash-search">
      <input
        type="text"
        v-model="trashKeyword"
        placeholder="搜索回收站..."
        @input="applyTrashFilter"
      />
    </div>
    <div class="trash-tabs">
      <span
        :class="{ active: trashTab === 'files' }"
        @click="trashTab = 'files'; applyTrashFilter()"
      >
        文件 ({{ filteredTrashFiles.length }})
      </span>
      <span
        :class="{ active: trashTab === 'messages' }"
        @click="trashTab = 'messages'; applyTrashFilter()"
      >
        问答 ({{ filteredTrashMessages.length }})
      </span>
    </div>
    <div class="trash-list">
      <div v-show="trashTab === 'files'">
        <div v-if="filteredTrashFiles.length === 0" class="trash-empty">暂无文件</div>
        <div v-for="item in filteredTrashFiles" :key="item.fileId" class="trash-item">
          <div class="trash-item-info">
            <span class="trash-item-name">📄 {{ item.name }}</span>
            <span class="trash-item-time">删除于 {{ formatTime(item.deletedAt) }}</span>
          </div>
          <div class="trash-item-actions">
            <button class="preview-btn" @click="previewFile(item.name)">预览</button>
            <button class="restore-btn" @click="handleRestoreFile(item.fileId)">↩️ 恢复</button>
            <button class="delete-btn" @click="handlePermanentDeleteFile(item.fileId)">永久删除</button>
          </div>
        </div>
      </div>
      <div v-show="trashTab === 'messages'">
        <div v-if="filteredTrashMessages.length === 0" class="trash-empty">暂无问答</div>
        <div
          v-for="item in filteredTrashMessages"
          :key="item.messageId"
          class="trash-item"
          @click="openQaDialog(item.fileName, { question: item.question, answer: item.answer })"
        >
          <div class="trash-item-info">
            <span class="trash-item-name">Q：{{ truncate(item.question, 30) }}</span>
            <span class="trash-item-source">{{ item.fileName }}</span>
            <span class="trash-item-time">删除于 {{ formatTime(item.deletedAt) }}</span>
          </div>
          <div class="trash-item-actions" @click.stop>
            <button class="restore-btn" @click="handleRestoreMessage(item.messageId)">↩️ 恢复</button>
            <button class="delete-btn" @click="handlePermanentDeleteMessage(item.messageId)">永久删除</button>
          </div>
        </div>
      </div>
    </div>
    <div class="trash-footer">
      <button class="clear-trash-btn" @click="handleEmptyTrash">🗑️ 清空回收站</button>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRagStore } from '../stores/ragStore'
import axios from 'axios'
import { ElMessage } from 'element-plus'

// ===== 接收父组件控制 =====
const props = defineProps({
  open: {
    type: Boolean,
    default: false
  }
})
const emit = defineEmits(['close'])

// ===== Store =====
const store = useRagStore()
const files = computed(() => store.files)

// ===== 展开状态 =====
const expandedFiles = ref([])

// ===== 搜索 =====
const searchKeyword = ref('')
const searchResults = ref([])
const showHistory = ref(false)
const searchHistory = ref([])
const MAX_HISTORY = 6
const searchContainer = ref(null)
const searchInput = ref(null)

const loadSearchHistory = () => {
  try {
    const saved = localStorage.getItem('rag_search_history')
    if (saved) searchHistory.value = JSON.parse(saved).slice(0, MAX_HISTORY)
  } catch { searchHistory.value = [] }
}

const saveSearchHistory = (keyword) => {
  if (!keyword.trim()) return
  let history = searchHistory.value.filter(item => item !== keyword.trim())
  history.unshift(keyword.trim())
  if (history.length > MAX_HISTORY) history = history.slice(0, MAX_HISTORY)
  searchHistory.value = history
  localStorage.setItem('rag_search_history', JSON.stringify(history))
}

const clearHistory = () => {
  if (confirm('确定要清空所有搜索历史吗？')) {
    searchHistory.value = []
    localStorage.removeItem('rag_search_history')
    showHistory.value = false
  }
}

const executeSearch = () => {
  const keyword = searchKeyword.value.trim()
  if (!keyword) {
    searchResults.value = []
    showHistory.value = false
    return
  }
  saveSearchHistory(keyword)
  const lowerKeyword = keyword.toLowerCase()
  const results = []
  files.value.forEach(file => {
    const fileMatches = file.name.toLowerCase().includes(lowerKeyword)
    const matchedMessages = file.messages.filter(msg =>
      msg.question.toLowerCase().includes(lowerKeyword) ||
      msg.answer.toLowerCase().includes(lowerKeyword)
    )
    if (fileMatches) {
      results.push({ fileId: file.id, fileName: file.name, msg: null, isFileHeader: true })
      file.messages.forEach(msg => {
        results.push({ fileId: file.id, fileName: file.name, msg: msg, isFileHeader: false })
      })
    } else if (matchedMessages.length > 0) {
      matchedMessages.forEach(msg => {
        results.push({ fileId: file.id, fileName: file.name, msg: msg, isFileHeader: false })
      })
    }
  })
  searchResults.value = results
  showHistory.value = false
}

const onInputChange = () => executeSearch()
const performSearch = () => executeSearch()

const applyHistorySearch = (keyword) => {
  searchKeyword.value = keyword
  executeSearch()
}

const clearSearch = () => {
  searchKeyword.value = ''
  searchResults.value = []
  showHistory.value = false
}

const handleClickOutside = (e) => {
  if (searchContainer.value && !searchContainer.value.contains(e.target)) {
    showHistory.value = false
  }
}

const goToSearchResult = (result) => {
  if (result.isFileHeader) {
    const file = files.value.find(f => f.id === result.fileId)
    if (!file) return
    if (!expandedFiles.value.includes(result.fileId)) {
      expandedFiles.value.push(result.fileId)
    }
    store.setCurrentFile(result.fileId)
    ElMessage.success(`已选择文件：${file.name}`)
    nextTick(() => {
      const el = document.querySelector(`[data-file-id="${result.fileId}"]`)
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    })
    return
  }
  if (result.msg) {
    openQaDialog(result.fileName, result.msg)
  }
}

const getFileMessageCount = (fileId) => {
  const file = files.value.find(f => f.id === fileId)
  return file ? file.messages.length : 0
}

// ===== 预览 =====
const previewVisible = ref(false)
const previewFileName = ref('')
const previewContent = ref('')
const previewLoading = ref(false)

const previewFile = async (fileName) => {
  previewVisible.value = true
  previewFileName.value = fileName
  previewLoading.value = true
  previewContent.value = ''
  try {
    const API_BASE = 'http://localhost:8000'
    const { data } = await axios.get(`${API_BASE}/documents/content`, {
      params: { source: fileName }
    })
    previewContent.value = data
  } catch (error) {
    previewContent.value = '无法加载文件内容'
  } finally {
    previewLoading.value = false
  }
}

// ===== 问答弹窗 =====
const qaDialogVisible = ref(false)
const qaDialogTitle = ref('')
const qaDialogQuestion = ref('')
const qaDialogAnswer = ref('')

const openQaDialog = (fileName, msg) => {
  qaDialogTitle.value = fileName
  qaDialogQuestion.value = msg.question
  qaDialogAnswer.value = msg.answer
  qaDialogVisible.value = true
}

// ===== 文件操作 =====
const toggleFile = (id) => {
  const file = files.value.find(f => f.id === id)
  if (!file) return
  store.setCurrentFile(id)
  ElMessage.success(`已选择文件：${file.name}`)
  const idx = expandedFiles.value.indexOf(id)
  if (idx > -1) expandedFiles.value.splice(idx, 1)
  else expandedFiles.value.push(id)
}

const handleDeleteFile = (id) => {
  if (confirm('确定要删除这个文件及其所有问答记录吗？')) {
    store.deleteFile(id)
    const idx = expandedFiles.value.indexOf(id)
    if (idx > -1) expandedFiles.value.splice(idx, 1)
  }
}

const handleDeleteMessage = (fileId, messageId) => {
  if (confirm('确定要删除这条问答记录吗？')) {
    store.deleteMessage(fileId, messageId)
  }
}

const handleClearAll = () => {
  store.clearAll()
  expandedFiles.value = []
}

// ===== 回收站 =====
const trashDialogVisible = ref(false)
const trashTab = ref('files')
const trashKeyword = ref('')
const filteredTrashFiles = ref([])
const filteredTrashMessages = ref([])

const trashCount = computed(() => {
  return store.trash.files.length + store.trash.messages.length
})

const openTrashDialog = () => {
  trashDialogVisible.value = true
  applyTrashFilter()
}

const applyTrashFilter = () => {
  const keyword = trashKeyword.value.trim().toLowerCase()
  filteredTrashFiles.value = store.trash.files.filter(item => {
    if (!keyword) return true
    return item.name.toLowerCase().includes(keyword)
  })
  filteredTrashMessages.value = store.trash.messages.filter(item => {
    if (!keyword) return true
    return item.question.toLowerCase().includes(keyword) ||
           item.answer.toLowerCase().includes(keyword)
  })
}

const handleRestoreFile = (fileId) => {
  store.restoreFile(fileId)
  applyTrashFilter()
}

const handleRestoreMessage = (messageId) => {
  store.restoreMessage(messageId)
  applyTrashFilter()
}

const handlePermanentDeleteFile = (fileId) => {
  if (confirm('确定要永久删除此文件吗？不可恢复！')) {
    store.permanentDeleteFile(fileId)
    applyTrashFilter()
  }
}

const handlePermanentDeleteMessage = (messageId) => {
  if (confirm('确定要永久删除此问答吗？不可恢复！')) {
    store.permanentDeleteMessage(messageId)
    applyTrashFilter()
  }
}

const handleEmptyTrash = () => {
  store.emptyTrash()
  applyTrashFilter()
}

// ===== 工具函数 =====
const truncate = (text, maxLen) => {
  if (!text) return ''
  return text.length > maxLen ? text.slice(0, maxLen) + '...' : text
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', { hour12: false })
}

// ===== 初始化 =====
onMounted(() => {
  store._load()
  loadSearchHistory()
  document.addEventListener('click', handleClickOutside)
})
</script>

<style scoped>
/* ===== 遮罩层（手机端） ===== */
.sidebar-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.4);
  z-index: 999;
}

/* ===== 侧边栏容器 ===== */
.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: 80%;
  max-width: 320px;
  background: #f8f9fa;
  border-right: 1px solid #e8ecf1;
  z-index: 1000;
  transform: translateX(-100%);
  transition: transform 0.3s ease;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar.open {
  transform: translateX(0);
}

/* ===== 桌面端 ===== */
@media (min-width: 769px) {
  .sidebar {
    position: relative;
    transform: none !important;
    width: 300px;
    min-width: 300px;
    max-width: 300px;
    z-index: 1;
  }
  .sidebar-overlay {
    display: none !important;
  }
}

/* ===== 以下是你原有的样式（保持不变） ===== */
.sidebar-header {
  padding: 16px 20px;
  border-bottom: 1px solid #e8ecf1;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  flex-shrink: 0;
}

.sidebar-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1a2332;
}

.file-count {
  background: #e8ecf1;
  color: #1a2332;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
}

.sidebar-search {
  padding: 10px 16px;
  border-bottom: 1px solid #e8ecf1;
  background: white;
  flex-shrink: 0;
  position: relative;
  overflow: visible;
}

.sidebar-search input {
  width: 100%;
  padding: 6px 28px 6px 14px;
  border: 1px solid #d0d7e2;
  border-radius: 20px;
  font-size: 13px;
  outline: none;
  background: #f8f9fa;
  box-sizing: border-box;
  transition: border-color 0.2s;
}

.sidebar-search input:focus {
  border-color: #409eff;
  background: white;
}

.sidebar-search .search-clear {
  position: absolute;
  right: 22px;
  top: 50%;
  transform: translateY(-50%);
  color: #b0b8c4;
  cursor: pointer;
  font-size: 14px;
  padding: 2px 4px;
  border-radius: 50%;
  transition: all 0.2s;
  line-height: 1;
}

.sidebar-search .search-clear:hover {
  color: #1a2332;
  background: #f0f2f5;
}

.search-history {
  position: absolute;
  top: 100%;
  left: 0;
  width: 100%;
  background: white;
  border: 1px solid #d0d7e2;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  margin-top: 4px;
  z-index: 10;
  padding: 4px 0;
  box-sizing: border-box;
}

.history-title {
  padding: 6px 14px;
  font-size: 12px;
  color: #8a9aa8;
  border-bottom: 1px solid #f0f2f5;
}

.history-item {
  padding: 8px 14px;
  cursor: pointer;
  font-size: 13px;
  color: #1a2332;
  transition: background 0.15s;
}

.history-item:hover {
  background: #f0f4fa;
}

.history-clear {
  padding: 8px 14px;
  cursor: pointer;
  font-size: 12px;
  color: #e74c3c;
  border-top: 1px solid #f0f2f5;
  text-align: center;
}

.history-clear:hover {
  background: #fef0f0;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 12px;
  min-height: 0;
}

.empty-state {
  padding: 40px 20px;
  text-align: center;
  color: #8a9aa8;
  font-size: 14px;
}

.empty-state .hint {
  font-size: 12px;
  color: #b0b8c4;
  margin-top: 4px;
}

.file-item {
  margin-bottom: 6px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  overflow: hidden;
}

.file-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  cursor: pointer;
  transition: background 0.15s;
}

.file-header:hover {
  background: #f0f2f5;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  flex: 1;
  flex-wrap: nowrap;
}

.file-icon {
  font-size: 14px;
  flex-shrink: 0;
}

.file-name {
  font-size: 13px;
  font-weight: 500;
  color: #1a2332;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 120px;
  flex: 0 1 auto;
}

.file-name:hover {
  color: #409eff;
}

.preview-btn {
  flex-shrink: 0;
  white-space: nowrap;
  background: none;
  border: none;
  color: #409eff;
  cursor: pointer;
  font-size: 12px;
  padding: 0 4px;
}

.preview-btn:hover {
  color: #1a3c6e;
  text-decoration: underline;
}

.file-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.badge {
  background: #e8ecf1;
  color: #1a2332;
  padding: 0 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
}

.delete-btn {
  background: none;
  border: none;
  color: #b0b8c4;
  cursor: pointer;
  font-size: 14px;
  padding: 0 4px;
  transition: color 0.15s;
}

.delete-btn:hover {
  color: #e74c3c;
}

.file-messages {
  padding: 6px 14px 12px 14px;
  border-top: 1px solid #f0f2f5;
  background: #fafbfc;
}

.qa-item {
  padding: 6px 0;
  border-bottom: 1px solid #f0f2f5;
  cursor: pointer;
  transition: background 0.15s;
}

.qa-item:hover {
  background: #f0f4fa;
  margin: 0 -8px;
  padding-left: 8px;
  padding-right: 8px;
  border-radius: 4px;
}

.qa-item:last-child {
  border-bottom: none;
}

.qa-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.qa-delete-btn {
  background: none;
  border: none;
  color: #b0b8c4;
  cursor: pointer;
  font-size: 12px;
  padding: 0 4px;
}

.qa-delete-btn:hover {
  color: #e74c3c;
}

.q {
  font-size: 13px;
  font-weight: 500;
  color: #1a2332;
  flex: 1;
}

.a {
  font-size: 13px;
  color: #4a5a6a;
  margin-top: 2px;
}

.qa-time {
  font-size: 11px;
  color: #b0b8c4;
  margin-top: 2px;
}

.qa-meta {
  font-size: 11px;
  color: #b0b8c4;
  margin-top: 2px;
}

.empty-msg {
  font-size: 13px;
  color: #b0b8c4;
  padding: 8px 0;
}

.search-item {
  padding: 8px 0;
  border-bottom: 1px solid #f0f2f5;
}

.search-file-result {
  display: flex;
  align-items: center;
  gap: 8px;
}

.search-file-result .q {
  cursor: pointer;
  flex: 1;
}

.search-file-result .q:hover {
  color: #409eff;
}

.no-result {
  text-align: center;
  color: #b0b8c4;
  padding: 40px 0;
  font-size: 14px;
}

.sidebar-footer {
  padding: 12px 20px;
  border-top: 1px solid #e8ecf1;
  background: white;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.trash-btn {
  width: 100%;
  padding: 8px;
  background: none;
  border: 1px solid #e8ecf1;
  border-radius: 6px;
  color: #8a9aa8;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.trash-btn:hover {
  background: #f0f2f5;
  border-color: #b0b8c4;
}

.trash-badge {
  background: #409eff;
  color: white;
  border-radius: 50%;
  padding: 0 6px;
  font-size: 11px;
  min-width: 6px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.clear-btn {
  width: 100%;
  padding: 8px;
  background: none;
  border: 1px solid #e8ecf1;
  border-radius: 6px;
  color: #8a9aa8;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
}

.clear-btn:hover {
  background: #fef0f0;
  border-color: #f5c6cb;
  color: #e74c3c;
}

.preview-content {
  max-height: 70vh;
  overflow-y: auto;
  padding: 16px;
  background: #f8fafc;
  border-radius: 8px;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-size: 14px;
  line-height: 1.8;
}

.preview-loading {
  text-align: center;
  padding: 40px;
  color: #8a9aa8;
}

.qa-dialog-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.qa-dialog-question {
  font-size: 15px;
  font-weight: 500;
  color: #1a2332;
  padding-bottom: 8px;
  border-bottom: 1px solid #e8ecf1;
}

.qa-dialog-answer {
  font-size: 15px;
  color: #333;
  line-height: 1.8;
  max-height: 55vh;
  overflow-y: auto;
}

.qa-dialog-answer .label {
  font-weight: 500;
  color: #409eff;
}

.qa-dialog-question .label {
  font-weight: 500;
  color: #e6a23c;
}

.trash-search {
  padding: 8px 0 12px 0;
  width: 100%;
  box-sizing: border-box;
}

.trash-search input {
  width: 100%;
  padding: 6px 14px;
  border: 1px solid #d0d7e2;
  border-radius: 20px;
  font-size: 13px;
  outline: none;
  background: #f8f9fa;
  box-sizing: border-box;
}

.trash-search input:focus {
  border-color: #409eff;
  background: white;
}

.trash-tabs {
  display: flex;
  gap: 12px;
  border-bottom: 1px solid #e8ecf1;
  padding-bottom: 8px;
  margin-bottom: 12px;
}

.trash-tabs span {
  cursor: pointer;
  font-size: 14px;
  color: #8a9aa8;
  padding: 4px 0;
}

.trash-tabs span.active {
  color: #1a2332;
  font-weight: 500;
  border-bottom: 2px solid #409eff;
}

.trash-list {
  max-height: 50vh;
  overflow-y: auto;
}

.trash-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-bottom: 1px solid #f0f2f5;
}

.trash-item-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.trash-item-name {
  font-size: 13px;
  font-weight: 500;
  color: #1a2332;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.trash-item-source {
  font-size: 12px;
  color: #8a9aa8;
}

.trash-item-time {
  font-size: 11px;
  color: #b0b8c4;
}

.trash-item-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.trash-item-actions button {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 4px;
}

.restore-btn {
  color: #409eff;
}

.restore-btn:hover {
  background: #ecf5ff;
}

.trash-item-actions .delete-btn {
  color: #e74c3c;
}

.trash-item-actions .delete-btn:hover {
  background: #fef0f0;
}

.trash-empty {
  text-align: center;
  color: #b0b8c4;
  padding: 30px 0;
  font-size: 14px;
}

.trash-footer {
  margin-top: 12px;
  text-align: right;
}

.clear-trash-btn {
  padding: 6px 16px;
  background: #fef0f0;
  border: 1px solid #f5c6cb;
  border-radius: 6px;
  color: #e74c3c;
  cursor: pointer;
  font-size: 13px;
}

.clear-trash-btn:hover {
  background: #fce4e4;
}

.sidebar ::-webkit-scrollbar {
  width: 4px;
}

.sidebar ::-webkit-scrollbar-track {
  background: transparent;
}

.sidebar ::-webkit-scrollbar-thumb {
  background: #d0d7e2;
  border-radius: 4px;
}

.sidebar ::-webkit-scrollbar-thumb:hover {
  background: #b0b8c4;
}
</style>