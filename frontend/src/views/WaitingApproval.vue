<template>
  <div class="cs-page waiting">
    <div class="cs-container center">
      <div class="cs-card box">
        <template v-if="state === 'pending'">
          <div class="icon spin">⏳</div>
          <div class="cs-title" style="font-size: 20px">等待团长审批</div>
          <p class="cs-subtitle">
            你的 CN「{{ session.nickname }}」已提交，团长通过后即可进入空间。
          </p>
          <el-icon class="loading"><Loading /></el-icon>
        </template>

        <template v-else-if="state === 'rejected'">
          <div class="icon">🚫</div>
          <div class="cs-title" style="font-size: 20px">申请被拒绝</div>
          <p class="cs-subtitle">团长拒绝了你的加入申请。你可以换个 CN 重新申请。</p>
          <el-button type="primary" @click="reapply">重新申请</el-button>
        </template>

        <template v-else>
          <div class="icon">✅</div>
          <div class="cs-title" style="font-size: 20px">审批通过</div>
          <p class="cs-subtitle">正在进入空间…</p>
        </template>

        <el-button text style="margin-top: 16px" @click="leave">退出</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getMyStatus } from '@/api'
import { useSessionStore } from '@/stores/session'
import { SpaceSocket, type WsMessage } from '@/utils/ws'

const props = defineProps<{ spaceId: string }>()
const spaceId = props.spaceId
const router = useRouter()
const session = useSessionStore()

const state = ref<'pending' | 'approved' | 'rejected'>(
  (session.status as any) || 'pending',
)

let socket: SpaceSocket | null = null
let pollTimer: number | null = null

function onApproved() {
  state.value = 'approved'
  session.setStatus('approved')
  ElMessage.success('审批通过，欢迎加入')
  setTimeout(() => router.replace({ name: 'space', params: { spaceId } }), 600)
}

function onRejected() {
  state.value = 'rejected'
  session.setStatus('rejected')
}

function handleWs(msg: WsMessage) {
  const m = msg as { type?: string; nickname?: string; status?: string }
  if (m.type === 'approval_result' && session.nickname && m.nickname === session.nickname) {
    if (m.status === 'approved') onApproved()
    else if (m.status === 'rejected') onRejected()
  }
}

async function poll() {
  if (!session.nickname) return
  try {
    const res = await getMyStatus(spaceId, session.nickname)
    if (res.status === 'approved') onApproved()
    else if (res.status === 'rejected') onRejected()
  } catch {
    /* ignore */
  }
}

function reapply() {
  session.logout()
  router.replace({ name: 'join', query: { code: session.inviteCode || undefined } })
}

function leave() {
  session.logout()
  router.replace('/')
}

onMounted(() => {
  if (state.value === 'approved') {
    onApproved()
    return
  }
  socket = new SpaceSocket(spaceId, handleWs)
  socket.connect()
  // polling fallback every 5s
  pollTimer = window.setInterval(poll, 5000)
  poll()
})

onUnmounted(() => {
  socket?.close()
  if (pollTimer) window.clearInterval(pollTimer)
})
</script>

<style scoped>
.waiting {
  justify-content: center;
}
.center {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100dvh;
}
.box {
  text-align: center;
  max-width: 360px;
}
.icon {
  font-size: 48px;
  margin-bottom: 8px;
}
.icon.spin {
  animation: pulse 1.5s ease-in-out infinite;
}
@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.4;
  }
}
.loading {
  font-size: 24px;
  color: var(--cs-accent);
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
