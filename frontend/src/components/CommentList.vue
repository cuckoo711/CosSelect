<template>
  <div class="comment-list">
    <div class="scroll-area">
      <div v-if="comments.length === 0" class="empty">还没有批注，来发表第一条吧</div>
      <div
        v-for="c in comments"
        :key="c.id"
        class="comment"
        :class="{ pinned: c.is_pinned }"
      >
        <div class="head">
          <span class="author" :class="{ leader: c.is_leader }">
            <span v-if="c.is_leader" class="tag">团长</span>
            {{ c.author }}
          </span>
          <span v-if="c.is_pinned" class="pin">📌置顶</span>
          <span class="cs-spacer" />
          <span class="time">{{ fmt(c.created_at) }}</span>
        </div>

        <div v-if="editingId === c.id" class="edit">
          <el-input v-model="editText" type="textarea" :rows="2" maxlength="2000" />
          <div class="edit-actions">
            <el-button size="small" @click="cancelEdit">取消</el-button>
            <el-button size="small" type="primary" @click="saveEdit(c)">保存</el-button>
          </div>
        </div>
        <div v-else class="content">{{ c.content }}</div>

        <div class="foot">
          <button
            class="like"
            :class="{ on: c.liked_by_me }"
            v-if="!isLeader"
            @click="onLike(c)"
          >
            👍 赞同 {{ c.likes_count }}
          </button>
          <span v-else class="like static">👍 {{ c.likes_count }}</span>
          <span class="cs-spacer" />
          <template v-if="c.can_edit && editingId !== c.id">
            <button class="txt" @click="startEdit(c)">编辑</button>
            <button class="txt danger" @click="onDelete(c)">删除</button>
          </template>
        </div>
      </div>
    </div>

    <div class="input-bar">
      <el-input
        v-model="newText"
        placeholder="写下你的批注…"
        maxlength="2000"
        @keyup.enter="submit"
      />
      <el-button type="primary" :loading="sending" @click="submit">发送</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Comment } from '@/api/types'
import { createComment, deleteComment, toggleLike, updateComment } from '@/api'

const props = defineProps<{
  spaceId: number
  photoId: number
  comments: Comment[]
  isLeader: boolean
}>()
const emit = defineEmits<{ (e: 'changed'): void }>()

const newText = ref('')
const sending = ref(false)
const editingId = ref<number | null>(null)
const editText = ref('')

function fmt(s: string) {
  const d = new Date(s.endsWith('Z') ? s : s + 'Z')
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

async function submit() {
  const t = newText.value.trim()
  if (!t) return
  sending.value = true
  try {
    await createComment(props.spaceId, props.photoId, t)
    newText.value = ''
    emit('changed')
  } finally {
    sending.value = false
  }
}

function startEdit(c: Comment) {
  editingId.value = c.id
  editText.value = c.content
}
function cancelEdit() {
  editingId.value = null
  editText.value = ''
}
async function saveEdit(c: Comment) {
  const t = editText.value.trim()
  if (!t) return
  await updateComment(props.spaceId, c.id, t)
  cancelEdit()
  emit('changed')
}

async function onDelete(c: Comment) {
  try {
    await ElMessageBox.confirm('确认删除这条批注？', '删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  await deleteComment(props.spaceId, c.id)
  ElMessage.success('已删除')
  emit('changed')
}

async function onLike(c: Comment) {
  await toggleLike(props.spaceId, c.id)
  emit('changed')
}
</script>

<style scoped>
.comment-list {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.scroll-area {
  flex: 1;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  padding-bottom: 8px;
}
.empty {
  color: var(--cs-text-dim);
  text-align: center;
  padding: 40px 0;
}
.comment {
  border-bottom: 1px solid var(--cs-border);
  padding: 12px 2px;
}
.comment.pinned {
  background: color-mix(in srgb, var(--cs-danger) 8%, transparent);
  border-radius: 8px;
  padding: 12px 10px;
}
.head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  margin-bottom: 4px;
}
.author {
  font-weight: 600;
}
.author .tag {
  background: var(--cs-danger);
  color: #fff;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  margin-right: 4px;
}
.pin {
  font-size: 11px;
  color: var(--cs-danger);
}
.time {
  color: var(--cs-text-dim);
  font-size: 12px;
}
.content {
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}
.foot {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 8px;
}
.like {
  background: var(--cs-bg-elev2);
  border: none;
  color: var(--cs-text-dim);
  border-radius: 14px;
  padding: 3px 12px;
  font-size: 12px;
}
.like.on {
  color: var(--cs-accent);
  background: color-mix(in srgb, var(--cs-accent) 20%, transparent);
}
.like.static {
  background: transparent;
}
.txt {
  background: none;
  border: none;
  color: var(--cs-text-dim);
  font-size: 12px;
}
.txt.danger {
  color: var(--cs-danger);
}
.edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 6px;
}
.input-bar {
  display: flex;
  gap: 8px;
  padding: 10px 0 0;
  border-top: 1px solid var(--cs-border);
}
</style>
