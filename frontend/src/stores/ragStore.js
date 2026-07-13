// src/stores/ragStore.js
import { defineStore } from 'pinia'

export const useRagStore = defineStore('rag', {
  state: () => ({
    files: [],
    favorites: [],
    currentFileID: null,  // 统一用 currentFileID
    trash: {
      files: [],
      messages: []
    }
  }),

  actions: {
    // ========== 文件管理 ==========
    addFile(name) {
      const id = Date.now().toString()
      this.files.push({
        id,
        name,
        createdAt: new Date().toISOString(),
        messages: []
      })
      this.currentFileID = id
      this._save()
      return id
    },

    // 删除文件 → 移入回收站（同时把该文件下的问答也移入回收站）
// 删除文件 → 移入回收站（文件进文件列表，问答进问答列表）
    deleteFile(fileId) {
      const index = this.files.findIndex(f => f.id === fileId)
      if (index === -1) return
      const file = this.files[index]

      // 1. 把文件存入回收站的文件列表
      this.trash.files.push({
        fileId: file.id,
        name: file.name,
        deletedAt: new Date().toISOString(),
        data: JSON.parse(JSON.stringify(file))
      })

      // 2. 把该文件下的所有问答存入回收站的问答列表
      file.messages.forEach(msg => {
        this.trash.messages.push({
          messageId: msg.id,
          fileId: file.id,
          fileName: file.name,
          question: msg.question,
          answer: msg.answer,
          deletedAt: new Date().toISOString()
        })
      })

      // 3. 从文件列表中删除
      this.files.splice(index, 1)
      if (this.currentFileID === fileId) {
        this.currentFileID = this.files.length > 0 ? this.files[0].id : null
      }
      this._save()
    },
    // 删除问答 → 移入回收站
    deleteMessage(fileId, messageId) {
      const file = this.files.find(f => f.id === fileId)
      if (!file) return
      const msgIndex = file.messages.findIndex(m => m.id === messageId)
      if (msgIndex === -1) return
      const msg = file.messages[msgIndex]
      this.trash.messages.push({
        messageId: msg.id,
        fileId: file.id,
        fileName: file.name,
        question: msg.question,
        answer: msg.answer,
        deletedAt: new Date().toISOString()
      })
      file.messages.splice(msgIndex, 1)
      this._save()
    },

    setCurrentFile(fileId) {
      this.currentFileID = fileId
      this._save()
    },

    // ========== 回收站 - 恢复 ==========
    restoreFile(trashFileId) {
      const index = this.trash.files.findIndex(t => t.fileId === trashFileId)
      if (index === -1) return
      const item = this.trash.files[index]
      const existing = this.files.find(f => f.name === item.name)
      if (existing) {
        alert('已存在同名文件，请先处理或重命名后再恢复')
        return
      }
      // 1. 恢复文件（只恢复文件本身，不恢复问答）
      // 注意：item.data 里包含 messages，但我们需要把 messages 清空再恢复
      const fileData = JSON.parse(JSON.stringify(item.data))
      fileData.messages = []  // 只恢复文件，不恢复问答
      this.files.push(fileData)
      this.trash.files.splice(index, 1)

      // 2. 不删除 trash.messages，让用户单独恢复问答
      this._save()
    },
    restoreMessage(trashMsgId) {
      const index = this.trash.messages.findIndex(t => t.messageId === trashMsgId)
      if (index === -1) return
      const item = this.trash.messages[index]
      const file = this.files.find(f => f.id === item.fileId)
      if (!file) {
        alert('原文件已不存在，无法恢复该问答')
        this.trash.messages.splice(index, 1)
        this._save()
        return
      }
      file.messages.push({
        id: item.messageId,
        question: item.question,
        answer: item.answer,
        timestamp: new Date().toISOString()
      })
      this.trash.messages.splice(index, 1)
      this._save()
    },

    // ========== 回收站 - 永久删除 ==========
    permanentDeleteFile(trashFileId) {
      const index = this.trash.files.findIndex(t => t.fileId === trashFileId)
      if (index === -1) return
      this.trash.files.splice(index, 1)
      this._save()
    },

    permanentDeleteMessage(trashMsgId) {
      const index = this.trash.messages.findIndex(t => t.messageId === trashMsgId)
      if (index === -1) return
      this.trash.messages.splice(index, 1)
      this._save()
    },

    // ========== 回收站 - 清空全部 ==========
    emptyTrash() {
      if (confirm('确定要清空回收站吗？此操作不可恢复！')) {
        this.trash.files = []
        this.trash.messages = []
        this._save()
      }
    },

    // ========== 回收站 - 自动清理过期（7天） ==========
    cleanTrash() {
      const now = Date.now()
      const sevenDays = 7 * 24 * 60 * 60 * 1000
      let changed = false

      const beforeFiles = this.trash.files.length
      this.trash.files = this.trash.files.filter(item => {
        return (now - new Date(item.deletedAt).getTime()) < sevenDays
      })
      if (this.trash.files.length !== beforeFiles) changed = true

      const beforeMessages = this.trash.messages.length
      this.trash.messages = this.trash.messages.filter(item => {
        return (now - new Date(item.deletedAt).getTime()) < sevenDays
      })
      if (this.trash.messages.length !== beforeMessages) changed = true

      if (changed) this._save()
    },

    // ========== 消息管理 ==========
    addMessage(fileId, question, answer) {
      const file = this.files.find(f => f.id === fileId)
      if (!file) return
      file.messages.push({
        id: Date.now().toString(),
        question,
        answer,
        timestamp: new Date().toISOString()
      })
      this._save()
    },

    // ========== 收藏管理 ==========
    toggleFavorite(message) {
      const idx = this.favorites.findIndex(f => f.id === message.id)
      if (idx > -1) {
        this.favorites.splice(idx, 1)
      } else {
        this.favorites.push({ ...message })
      }
      this._save()
    },

    isFavorite(messageId) {
      return this.favorites.some(f => f.id === messageId)
    },

    // ========== 获取当前文件的上下文 ==========
    getContextMessages(fileId, limit = 5) {
      const file = this.files.find(f => f.id === fileId)
      if (!file) return []
      return file.messages.slice(-limit).flatMap(m => [
        { role: 'user', content: m.question },
        { role: 'assistant', content: m.answer }
      ])
    },

    // ========== 清空所有数据 ==========
    clearAll() {
      if (confirm('确定要清空所有数据吗？此操作不可恢复！')) {
        this.files = []
        this.favorites = []
        this.currentFileID = null
        this.trash.files = []
        this.trash.messages = []
        localStorage.removeItem('rag_data')
      }
    },

    // ========== 持久化 ==========
    _save() {
      try {
        localStorage.setItem('rag_data', JSON.stringify({
          files: this.files,
          favorites: this.favorites,
          currentFileID: this.currentFileID,
          trash: this.trash
        }))
      } catch (e) {
        console.warn('保存数据失败:', e)
      }
    },

    _load() {
      try {
        const raw = localStorage.getItem('rag_data')
        if (raw) {
          const data = JSON.parse(raw)
          this.files = data.files || []
          this.favorites = data.favorites || []
          this.currentFileID = data.currentFileID || null
          this.trash = data.trash || { files: [], messages: [] }
          this.cleanTrash()
        }
      } catch (e) {
        console.warn('加载数据失败:', e)
      }
    }
  }
})