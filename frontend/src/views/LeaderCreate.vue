<template>
  <div class="cs-page">
    <div class="cs-container">
      <el-page-header @back="$router.push('/')" title="返回">
        <template #content><span class="cs-title">团长入口</span></template>
      </el-page-header>

      <div class="cs-card" style="margin-top: 16px">
        <div class="cs-title" style="font-size: 18px">创建新空间</div>
        <p class="cs-subtitle">创建后会生成 8 位口令与团长管理密钥，请妥善保存密钥</p>
        <el-button type="primary" size="large" :loading="creating" @click="onCreate" style="width: 100%">
          创建选片空间
        </el-button>
      </div>

      <el-divider>或</el-divider>

      <div class="cs-card">
        <div class="cs-title" style="font-size: 18px">管理已有空间</div>
        <p class="cs-subtitle">输入空间 ID 与团长管理密钥</p>
        <el-form label-position="top">
          <el-form-item label="空间 ID">
            <el-input v-model="spaceIdInput" placeholder="如 1" inputmode="numeric" />
          </el-form-item>
          <el-form-item label="管理密钥">
            <el-input v-model="keyInput" placeholder="创建时获得的密钥" show-password />
          </el-form-item>
        </el-form>
        <el-button size="large" :loading="entering" @click="onEnter" style="width: 100%">
          进入管理
        </el-button>
      </div>

      <el-dialog v-model="showResult" title="空间创建成功" width="90%" :close-on-click-modal="false">
        <div class="result">
          <div class="result-row">
            <span class="label">空间 ID</span>
            <span class="value mono">{{ created?.space_id }}</span>
          </div>
          <div class="result-row">
            <span class="label">进入口令</span>
            <span class="value mono big">{{ created?.invite_code }}</span>
          </div>
          <div class="result-row column">
            <span class="label">团长管理密钥（务必保存）</span>
            <el-input :model-value="created?.manage_key" readonly>
              <template #append>
                <el-button @click="copyKey">复制</el-button>
              </template>
            </el-input>
          </div>
          <el-alert type="warning" :closable="false" show-icon style="margin-top: 12px">
            密钥用于后续管理该空间，丢失将无法再管理。口令 24 小时有效，可随时重置。
          </el-alert>
        </div>
        <template #footer>
          <el-button type="primary" @click="enterCreated">进入空间</el-button>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { createSpace, getSpaceInfo } from '@/api'
import { useSessionStore } from '@/stores/session'

const router = useRouter()
const session = useSessionStore()

const creating = ref(false)
const entering = ref(false)
const showResult = ref(false)
const created = ref<{ space_id: number; invite_code: string; manage_key: string } | null>(null)

const spaceIdInput = ref('')
const keyInput = ref('')

async function onCreate() {
  creating.value = true
  try {
    const data = await createSpace()
    created.value = data
    showResult.value = true
  } finally {
    creating.value = false
  }
}

function enterCreated() {
  if (!created.value) return
  session.setLeader(created.value.space_id, created.value.manage_key, created.value.invite_code)
  router.push({ name: 'space', params: { spaceId: created.value.space_id } })
}

async function copyKey() {
  if (!created.value) return
  try {
    await navigator.clipboard.writeText(created.value.manage_key)
    ElMessage.success('已复制密钥')
  } catch {
    ElMessage.info('请手动长按复制')
  }
}

async function onEnter() {
  const sid = Number(spaceIdInput.value)
  if (!sid || !keyInput.value) {
    ElMessage.warning('请填写空间 ID 和管理密钥')
    return
  }
  entering.value = true
  // temporarily set key so interceptor sends it
  session.setLeader(sid, keyInput.value.trim())
  try {
    const info = await getSpaceInfo(sid)
    session.setInviteCode(info.invite_code)
    router.push({ name: 'space', params: { spaceId: sid } })
  } catch {
    session.logout()
  } finally {
    entering.value = false
  }
}
</script>

<style scoped>
.result-row {
  display: flex;
  align-items: center;
  margin-bottom: 14px;
}
.result-row.column {
  flex-direction: column;
  align-items: stretch;
  gap: 6px;
}
.result-row .label {
  color: var(--cs-text-dim);
  width: 110px;
  flex-shrink: 0;
}
.result-row .value.big {
  font-size: 24px;
  font-weight: 700;
  color: var(--cs-accent);
}
</style>
