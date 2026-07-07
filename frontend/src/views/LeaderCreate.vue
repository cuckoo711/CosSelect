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
            <el-button type="primary" @click="openConfirm">进入空间</el-button>
          </div>
        </template>
      </el-dialog>

      <!-- important-notice confirmation before entering -->
      <el-dialog
        v-model="confirmVisible"
        title="进入前请务必确认"
        width="90%"
        :close-on-click-modal="false"
        :show-close="false"
      >
        <div class="notice">
          <el-alert type="error" :closable="false" show-icon style="margin-bottom: 12px">
            以下信息一旦丢失将无法找回，请立即保存！
          </el-alert>
          <ul class="notice-list">
            <li>
              <b>团长管理密钥</b>是你管理本空间的<b>唯一凭证</b>。系统不保存明文、无法找回，
              丢失后将<b>永久无法管理</b>该空间（无法上传、审批、导出等）。
            </li>
            <li>
              <b>团长一键管理链接</b>包含该密钥，换设备登录时用它可直接进入，请妥善保管、切勿外发。
            </li>
            <li>
              <b>进入口令</b>与<b>参与者链接</b>用于团员加入，24 小时有效，可随时重置。
            </li>
            <li>建议将上述信息复制到备忘录，或保存我们为你生成的 TXT 文件。</li>
          </ul>
          <el-alert
            v-if="!downloaded"
            type="warning"
            :closable="false"
            show-icon
            style="margin-top: 8px"
          >
            你还未下载信息文件，点击确认时将自动为你下载一份。
          </el-alert>
        </div>
        <template #footer>
          <div class="dialog-footer">
            <el-button @click="confirmVisible = false">再看看</el-button>
            <el-button type="primary" :disabled="countdown > 0" @click="confirmEnter">
              {{ countdown > 0 ? `请阅读（${countdown}s）` : '我已知晓，进入空间' }}
            </el-button>
          </div>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue'
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
const downloaded = ref(false)

const confirmVisible = ref(false)
const countdown = ref(0)
let countdownTimer: number | null = null

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

function doDownload() {
  if (!created.value) return
  downloadText(`团片选片_空间${created.value.space_id}.txt`, buildInfoText())
  downloaded.value = true
}

function downloadInfo() {
  doDownload()
  ElMessage.success('信息已下载')
}

function openConfirm() {
  confirmVisible.value = true
  countdown.value = 3
  if (countdownTimer) window.clearInterval(countdownTimer)
  countdownTimer = window.setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0 && countdownTimer) {
      window.clearInterval(countdownTimer)
      countdownTimer = null
    }
  }, 1000)
}

function confirmEnter() {
  if (countdown.value > 0) return
  // force a download on first entry if the leader hasn't saved the info yet
  if (!downloaded.value) {
    doDownload()
    ElMessage.success('已为你下载空间信息，请妥善保存')
  }
  confirmVisible.value = false
  enterCreated()
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

onUnmounted(() => {
  if (countdownTimer) window.clearInterval(countdownTimer)
})
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
.notice-list {
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--cs-text);
}
.notice-list li {
  margin-bottom: 8px;
}
.notice-list b {
  color: var(--cs-accent);
}
</style>
