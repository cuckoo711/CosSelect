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
            <el-input v-model="spaceIdInput" placeholder="如 k7m2x9qp3a" />
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
          <div class="result-row column highlight">
            <span class="label">🔗 参与者一键进入链接（发给团员）</span>
            <el-input :model-value="participantLink" readonly type="textarea" :autosize="{ minRows: 2 }" />
            <el-button size="small" type="primary" @click="copyText(participantLink)">
              复制参与者链接
            </el-button>
          </div>
          <div class="result-row column highlight">
            <span class="label">👑 团长一键管理链接（仅自己保存）</span>
            <el-input :model-value="leaderLink" readonly type="textarea" :autosize="{ minRows: 2 }" />
            <el-button size="small" @click="copyText(leaderLink)">复制团长链接</el-button>
          </div>
          <el-divider style="margin: 8px 0">或手动分享以下信息</el-divider>
          <div class="result-row column">
            <span class="label">参与者访问地址</span>
            <el-input :model-value="accessUrl" readonly>
              <template #append>
                <el-button @click="copyText(accessUrl)">复制</el-button>
              </template>
            </el-input>
          </div>
          <div class="result-row column">
            <span class="label">空间 ID</span>
            <el-input :model-value="created?.space_id" readonly>
              <template #append>
                <el-button @click="copyText(created?.space_id || '')">复制</el-button>
              </template>
            </el-input>
          </div>
          <div class="result-row column">
            <span class="label">进入口令</span>
            <el-input :model-value="created?.invite_code" readonly class="big-input">
              <template #append>
                <el-button @click="copyText(created?.invite_code || '')">复制</el-button>
              </template>
            </el-input>
          </div>
          <div class="result-row column">
            <span class="label">团长管理密钥（务必保存）</span>
            <el-input :model-value="created?.manage_key" readonly type="textarea" :autosize="{ minRows: 2 }" />
            <el-button size="small" text type="primary" @click="copyText(created?.manage_key || '')">
              复制密钥
            </el-button>
          </div>
          <el-alert type="warning" :closable="false" show-icon style="margin-top: 8px">
            密钥用于后续管理该空间，丢失将无法再管理。口令 24 小时有效，可随时重置。
          </el-alert>
        </div>
        <template #footer>
          <div class="dialog-footer">
            <el-button @click="copyAll">复制全部</el-button>
            <el-button @click="downloadInfo">
              <el-icon style="margin-right: 4px"><Download /></el-icon>下载 TXT
            </el-button>
            <el-button type="primary" @click="enterCreated">进入空间</el-button>
          </div>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { createSpace, getSpaceInfo } from '@/api'
import { useSessionStore } from '@/stores/session'
import { copyText, downloadText } from '@/utils/clipboard'

const router = useRouter()
const session = useSessionStore()

const creating = ref(false)
const entering = ref(false)
const showResult = ref(false)
const created = ref<{ space_id: string; invite_code: string; manage_key: string } | null>(null)

const spaceIdInput = ref('')
const keyInput = ref('')

const accessUrl = computed(() => (typeof window !== 'undefined' ? window.location.origin : ''))
const participantLink = computed(() =>
  created.value ? `${accessUrl.value}/?code=${created.value.invite_code}` : '',
)
const leaderLink = computed(() =>
  created.value
    ? `${accessUrl.value}/?sid=${created.value.space_id}&key=${created.value.manage_key}`
    : '',
)

function buildInfoText(): string {
  const c = created.value
  if (!c) return ''
  return [
    '【团片选片 - 空间信息】',
    '',
    '参与者一键进入链接（发给团员，打开后设置 CN 即可）：',
    participantLink.value,
    '',
    `空间 ID：${c.space_id}`,
    `进入口令：${c.invite_code}（24 小时有效，可随时重置）`,
    `参与者访问地址：${accessUrl.value}`,
    '',
    '团长一键管理链接（仅自己保存，勿外发）：',
    leaderLink.value,
    '团长管理密钥（务必妥善保存，丢失将无法再管理该空间）：',
    c.manage_key,
  ].join('\n')
}

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

function copyAll() {
  copyText(buildInfoText())
}

function downloadInfo() {
  if (!created.value) return
  downloadText(`团片选片_空间${created.value.space_id}.txt`, buildInfoText())
  ElMessage.success('信息已下载')
}

async function onEnter() {
  const sid = spaceIdInput.value.trim()
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
.result-row.column .label {
  color: var(--cs-text-dim);
  font-size: 13px;
}
.result-row.highlight {
  background: color-mix(in srgb, var(--cs-accent) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--cs-accent) 30%, transparent);
  border-radius: 10px;
  padding: 10px;
  margin-bottom: 10px;
}
.result-row.highlight .label {
  color: var(--cs-text);
  font-weight: 600;
}
.big-input :deep(.el-input__inner) {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 2px;
  color: var(--cs-accent);
}
.dialog-footer {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}
</style>
