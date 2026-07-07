<template>
  <div class="cs-page">
    <div class="cs-container">
      <el-page-header @back="$router.push('/')" title="返回">
        <template #content><span class="cs-title">参与者入口</span></template>
      </el-page-header>

      <div class="cs-card" style="margin-top: 16px">
        <el-steps :active="step" align-center finish-status="success" style="margin-bottom: 24px">
          <el-step title="输入口令" />
          <el-step title="设置昵称" />
        </el-steps>

        <template v-if="step === 0">
          <el-form label-position="top">
            <el-form-item label="进入口令（8 位）">
              <el-input
                v-model="code"
                placeholder="如 A3B9C7K2"
                maxlength="8"
                class="mono"
                @input="code = code.toUpperCase()"
              />
            </el-form-item>
          </el-form>
          <el-button type="primary" size="large" :loading="verifying" @click="onVerify" style="width: 100%">
            验证口令
          </el-button>
        </template>

        <template v-else>
          <el-form label-position="top">
            <el-form-item label="你的昵称（本空间唯一）">
              <el-input v-model="nickname" placeholder="如 摄影师小王" maxlength="50" />
            </el-form-item>
          </el-form>
          <el-alert type="info" :closable="false" show-icon style="margin-bottom: 12px">
            相同昵称再次进入会自动恢复你的评分、批注与喜欢记录。
          </el-alert>
          <el-button type="primary" size="large" :loading="joining" @click="onJoin" style="width: 100%">
            进入空间
          </el-button>
          <el-button text @click="step = 0" style="width: 100%; margin-top: 8px">重新输入口令</el-button>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { joinSpace, verifyCodeGlobal } from '@/api'
import { useSessionStore } from '@/stores/session'

const router = useRouter()
const session = useSessionStore()

const step = ref(0)
const code = ref('')
const nickname = ref('')
const verifying = ref(false)
const joining = ref(false)
const verifiedSpaceId = ref<string | null>(null)

async function onVerify() {
  if (code.value.length !== 8) {
    ElMessage.warning('请输入 8 位口令')
    return
  }
  verifying.value = true
  try {
    const res = await verifyCodeGlobal(code.value.trim())
    if (!res.valid || !res.space_id) {
      ElMessage.error('口令无效或已过期')
      return
    }
    verifiedSpaceId.value = res.space_id
    step.value = 1
  } finally {
    verifying.value = false
  }
}

async function onJoin() {
  const name = nickname.value.trim()
  if (!name) {
    ElMessage.warning('请输入昵称')
    return
  }
  if (!verifiedSpaceId.value) {
    step.value = 0
    return
  }
  joining.value = true
  try {
    const data = await joinSpace(verifiedSpaceId.value, name)
    session.setParticipant(verifiedSpaceId.value, data.token, data.nickname)
    session.setInviteCode(code.value.trim())
    ElMessage.success(data.is_new ? '欢迎加入' : '已恢复你的历史记录')
    router.push({ name: 'space', params: { spaceId: verifiedSpaceId.value } })
  } finally {
    joining.value = false
  }
}
</script>
