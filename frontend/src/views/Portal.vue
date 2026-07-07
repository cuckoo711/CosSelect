<template>
  <div class="cs-page portal">
    <div class="cs-container">
      <div class="brand">
        <div class="logo">📸</div>
        <h1 class="cs-title">团片选片</h1>
        <p class="cs-subtitle">私密 · 轻量 · 移动优先的协作选片工具</p>
      </div>

      <div class="cs-card entry" @click="goLeader">
        <div class="entry-icon">👑</div>
        <div class="entry-body">
          <div class="entry-name">我是团长</div>
          <div class="entry-desc">创建或管理选片空间，上传图片、生成口令</div>
        </div>
        <el-icon><ArrowRight /></el-icon>
      </div>

      <div class="cs-card entry" @click="goParticipant">
        <div class="entry-icon">🙋</div>
        <div class="entry-body">
          <div class="entry-name">我是参与者</div>
          <div class="entry-desc">输入口令加入空间，评分、批注、点赞</div>
        </div>
        <el-icon><ArrowRight /></el-icon>
      </div>

      <div v-if="session.authed" class="resume">
        <el-button text type="primary" @click="resume">
          继续上次空间（{{ session.displayName }}）
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'

const router = useRouter()
const session = useSessionStore()

function goLeader() {
  router.push({ name: 'leader-create' })
}
function goParticipant() {
  router.push({ name: 'join' })
}
function resume() {
  if (!session.spaceId) return
  router.push({ name: 'space', params: { spaceId: session.spaceId } })
}
</script>

<style scoped>
.portal {
  justify-content: center;
}
.brand {
  text-align: center;
  margin: 40px 0 28px;
}
.logo {
  font-size: 48px;
}
.entry {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 14px;
  cursor: pointer;
  transition: border-color 0.2s, transform 0.1s;
}
.entry:active {
  transform: scale(0.99);
  border-color: var(--cs-accent);
}
.entry-icon {
  font-size: 30px;
}
.entry-body {
  flex: 1;
}
.entry-name {
  font-size: 17px;
  font-weight: 600;
}
.entry-desc {
  font-size: 12px;
  color: var(--cs-text-dim);
  margin-top: 2px;
}
.resume {
  text-align: center;
  margin-top: 20px;
}
</style>
