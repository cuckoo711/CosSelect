<template>
  <div class="cs-page">
    <div class="header">
      <el-page-header @back="back" title="返回">
        <template #content><span class="cs-title">分类与上传</span></template>
      </el-page-header>
    </div>

    <div class="cs-container">
      <!-- invite code card -->
      <div class="cs-card" style="margin-bottom: 16px">
        <div class="cs-row">
          <div>
            <div class="dim small">当前口令（24h 有效）</div>
            <div class="code mono">{{ inviteCode || '—' }}</div>
            <div class="dim small" v-if="expireText">到期：{{ expireText }}</div>
            <div class="dim small" style="margin-top: 4px">空间 ID：{{ spaceId }}</div>
          </div>
          <span class="cs-spacer" />
          <el-button @click="onRegen" :loading="regenerating">重置口令</el-button>
        </div>
        <div class="cs-row" style="margin-top: 12px; gap: 8px; flex-wrap: wrap">
          <el-button size="small" type="primary" @click="copyText(participantLink)">
            复制参与者链接
          </el-button>
          <el-button size="small" @click="copyText(leaderLink)">复制团长链接</el-button>
          <el-button size="small" @click="copyText(inviteCode)">复制口令</el-button>
          <el-button size="small" @click="downloadInfo">
            <el-icon style="margin-right: 4px"><Download /></el-icon>下载 TXT
          </el-button>
        </div>
      </div>

      <!-- approval management -->
      <div class="cs-card" style="margin-bottom: 16px">
        <div class="cs-row" style="margin-bottom: 10px">
          <b>成员审批</b>
          <el-badge :value="pending.length" :hidden="pending.length === 0" style="margin-left: 8px" />
          <span class="cs-spacer" />
          <span class="dim small" style="margin-right: 8px">加入需审批</span>
          <el-switch v-model="requireApproval" @change="onToggleApproval" />
        </div>

        <div v-if="!requireApproval" class="dim small">已关闭审批，参与者输入口令设置 CN 后可直接进入。</div>

        <template v-else>
          <div v-if="pending.length === 0" class="dim small">暂无待审批的加入申请。</div>
          <div v-for="p in pending" :key="p.participant_id" class="approve-row">
            <span class="cn">{{ p.nickname }}</span>
            <span class="dim small">{{ fmtTime(p.join_time) }}</span>
            <span class="cs-spacer" />
            <el-button size="small" type="success" @click="onApprove(p.participant_id)">通过</el-button>
            <el-button size="small" type="danger" plain @click="onReject(p.participant_id)">拒绝</el-button>
          </div>
        </template>
      </div>

      <!-- add category -->
      <div class="cs-card" style="margin-bottom: 16px">
        <div class="cs-row" style="margin-bottom: 10px; flex-wrap: wrap; gap: 8px">
          <b>分类管理</b>
          <span class="cs-spacer" />
          <el-button size="small" @click="goImport">
            <el-icon style="margin-right: 4px"><FolderOpened /></el-icon>导入文件夹
          </el-button>
          <el-button size="small" type="primary" @click="openAdd(null)">新建根分类</el-button>
        </div>
        <el-tree
          :data="treeData"
          node-key="id"
          :props="{ label: 'name', children: 'children' }"
          draggable
          :allow-drop="allowDrop"
          @node-drop="onDrop"
          default-expand-all
        >
          <template #default="{ data }">
            <span class="tree-row">
              <span class="tree-name">{{ data.name }}</span>
              <span class="tree-count">{{ data.photo_count }}张</span>
              <span class="tree-ops">
                <el-icon @click.stop="openAdd(data.id)"><Plus /></el-icon>
                <el-icon @click.stop="openRename(data)"><Edit /></el-icon>
                <el-icon @click.stop="openUpload(data)"><Upload /></el-icon>
                <el-icon
                  :class="{ disabled: data.photo_count > 0 || data.children.length > 0 }"
                  @click.stop="onDelete(data)"
                  ><Delete
                /></el-icon>
              </span>
            </span>
          </template>
        </el-tree>
      </div>
    </div>

    <!-- add / rename dialog -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="86%">
      <el-input v-model="dialogName" placeholder="分类名称" maxlength="100" />
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmDialog">确定</el-button>
      </template>
    </el-dialog>

    <!-- upload dialog -->
    <el-dialog v-model="uploadVisible" :title="`上传到「${uploadTarget?.name}」`" width="90%">
      <input
        ref="fileInput"
        type="file"
        accept="image/*"
        multiple
        style="display: none"
        @change="onFilePick"
      />
      <el-button type="primary" plain style="width: 100%" @click="fileInput?.click()">
        选择图片（可多选）
      </el-button>
      <div v-if="picked.length" class="picked">已选 {{ picked.length }} 张，共 {{ pickedMB }} MB</div>
      <div class="picked dim">上传前会自动压缩到最大 500 万像素，以节省流量与存储。</div>
      <div v-if="compressing" class="picked">正在压缩图片…</div>
      <el-progress v-if="uploading && !compressing" :percentage="progress" :stroke-width="10" style="margin-top: 12px" />
      <template #footer>
        <el-button @click="uploadVisible = false" :disabled="uploading">取消</el-button>
        <el-button type="primary" :loading="uploading" :disabled="!picked.length" @click="doUpload">
          {{ compressing ? '压缩中…' : '开始上传' }}
        </el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { CategoryNode } from '@/api/types'
import {
  approveParticipant,
  createCategory,
  deleteCategory,
  getSpaceInfo,
  listCategories,
  listPendingParticipants,
  regenerateCode,
  rejectParticipant,
  reorderCategories,
  setApprovalSetting,
  updateCategory,
  uploadPhotos,
} from '@/api'
import { copyText, downloadText } from '@/utils/clipboard'
import { compressImage } from '@/utils/image'
import { useSessionStore } from '@/stores/session'
import { SpaceSocket, type WsMessage } from '@/utils/ws'

const props = defineProps<{ spaceId: string }>()
const spaceId = props.spaceId
const router = useRouter()
const session = useSessionStore()

const treeData = ref<CategoryNode[]>([])
const inviteCode = ref('')
const expireText = ref('')
const regenerating = ref(false)

const requireApproval = ref(true)
const pending = ref<{ participant_id: number; nickname: string; status: string; join_time: string }[]>([])
let socket: SpaceSocket | null = null
let pollTimer: number | null = null

const accessUrl = typeof window !== 'undefined' ? window.location.origin : ''
const participantLink = computed(() => `${accessUrl}/?code=${inviteCode.value}`)
const leaderLink = computed(() => `${accessUrl}/?sid=${spaceId}&key=${session.manageKey || ''}`)

function fmtTime(s: string) {
  const d = new Date(s.endsWith('Z') ? s : s + 'Z')
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

async function loadPending() {
  try {
    pending.value = await listPendingParticipants(spaceId, 'pending')
  } catch {
    /* ignore */
  }
}

async function onToggleApproval(val: boolean) {
  try {
    await setApprovalSetting(spaceId, val)
    ElMessage.success(val ? '已开启加入审批' : '已关闭加入审批')
    if (val) loadPending()
  } catch {
    requireApproval.value = !val
  }
}

async function onApprove(id: number) {
  await approveParticipant(spaceId, id)
  pending.value = pending.value.filter((p) => p.participant_id !== id)
  ElMessage.success('已通过')
}

async function onReject(id: number) {
  await rejectParticipant(spaceId, id)
  pending.value = pending.value.filter((p) => p.participant_id !== id)
  ElMessage.info('已拒绝')
}

function handleWs(msg: WsMessage) {
  if (msg.type === 'join_request') {
    loadPending()
  }
}

function downloadInfo() {
  const text = [
    '【团片选片 - 空间信息】',
    '',
    '参与者一键进入链接（发给团员，打开后设置 CN 即可）：',
    participantLink.value,
    '',
    `空间 ID：${spaceId}`,
    `进入口令：${inviteCode.value}（24 小时有效，可随时重置）`,
    expireText.value ? `口令到期：${expireText.value}` : '',
    `参与者访问地址：${accessUrl}`,
    '',
    '团长一键管理链接（仅自己保存，勿外发）：',
    leaderLink.value,
  ]
    .filter((l) => l !== '')
    .join('\n')
  downloadText(`团片选片_空间${spaceId}.txt`, text)
  ElMessage.success('信息已下载')
}

const dialogVisible = ref(false)
const dialogMode = ref<'add' | 'rename'>('add')
const dialogName = ref('')
const dialogParentId = ref<number | null>(null)
const dialogTargetId = ref<number | null>(null)
const dialogTitle = computed(() => (dialogMode.value === 'add' ? '新建分类' : '重命名分类'))

const uploadVisible = ref(false)
const uploadTarget = ref<CategoryNode | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const picked = ref<File[]>([])
const uploading = ref(false)
const compressing = ref(false)
const progress = ref(0)
const pickedMB = computed(() =>
  (picked.value.reduce((s, f) => s + f.size, 0) / 1024 / 1024).toFixed(1),
)

function back() {
  router.push({ name: 'space', params: { spaceId } })
}

function goImport() {
  router.push({ name: 'import', params: { spaceId } })
}

async function loadTree() {
  treeData.value = await listCategories(spaceId)
}

async function loadInfo() {
  try {
    const info = await getSpaceInfo(spaceId)
    inviteCode.value = info.invite_code
    expireText.value = new Date(info.expire_time + 'Z').toLocaleString('zh-CN')
    requireApproval.value = info.require_approval
  } catch {
    /* ignore */
  }
}

async function onRegen() {
  regenerating.value = true
  try {
    const res = await regenerateCode(spaceId)
    inviteCode.value = res.invite_code
    expireText.value = new Date(res.expire_time + 'Z').toLocaleString('zh-CN')
    ElMessage.success('口令已重置，旧口令失效')
  } finally {
    regenerating.value = false
  }
}

function openAdd(parentId: number | null) {
  dialogMode.value = 'add'
  dialogName.value = ''
  dialogParentId.value = parentId
  dialogVisible.value = true
}
function openRename(node: CategoryNode) {
  dialogMode.value = 'rename'
  dialogName.value = node.name
  dialogTargetId.value = node.id
  dialogVisible.value = true
}
async function confirmDialog() {
  const name = dialogName.value.trim()
  if (!name) {
    ElMessage.warning('请输入名称')
    return
  }
  if (dialogMode.value === 'add') {
    await createCategory(spaceId, name, dialogParentId.value)
  } else if (dialogTargetId.value) {
    await updateCategory(spaceId, dialogTargetId.value, { name })
  }
  dialogVisible.value = false
  await loadTree()
}

async function onDelete(node: CategoryNode) {
  if (node.photo_count > 0) {
    ElMessage.warning('非空分类不可删除')
    return
  }
  if (node.children.length > 0) {
    ElMessage.warning('请先删除子分类')
    return
  }
  await deleteCategory(spaceId, node.id)
  ElMessage.success('已删除')
  await loadTree()
}

function openUpload(node: CategoryNode) {
  uploadTarget.value = node
  picked.value = []
  progress.value = 0
  uploadVisible.value = true
}
function onFilePick(e: Event) {
  const files = (e.target as HTMLInputElement).files
  picked.value = files ? Array.from(files) : []
}
async function doUpload() {
  if (!uploadTarget.value || !picked.value.length) return
  uploading.value = true
  progress.value = 0
  compressing.value = true
  try {
    // compress in the browser first (<=5MP) to save bandwidth
    const count = picked.value.length
    const compressed: File[] = []
    for (const f of picked.value) {
      compressed.push(await compressImage(f))
    }
    compressing.value = false
    await uploadPhotos(spaceId, uploadTarget.value.id, compressed, (p) => (progress.value = p))
    ElMessage.success(`已上传 ${count} 张，缩略图后台生成中`)
    uploadVisible.value = false
    await loadTree()
  } finally {
    uploading.value = false
    compressing.value = false
  }
}

// drag to reorder among siblings
function allowDrop(_draggingNode: any, dropNode: any, type: string) {
  return type !== 'inner' && dropNode.level === _draggingNode.level
}
async function onDrop(_dragging: any, _drop: any, _pos: string) {
  // recompute sibling order from tree
  const items: { id: number; sort_order: number }[] = []
  const walk = (arr: CategoryNode[]) => {
    arr.forEach((n, i) => {
      items.push({ id: n.id, sort_order: i })
      walk(n.children)
    })
  }
  walk(treeData.value)
  await reorderCategories(spaceId, items)
  ElMessage.success('排序已保存')
}

onMounted(() => {
  loadTree()
  loadInfo()
  loadPending()
  socket = new SpaceSocket(spaceId, handleWs)
  socket.connect()
  // polling fallback for pending list
  pollTimer = window.setInterval(() => {
    if (requireApproval.value) loadPending()
  }, 10000)
})

onUnmounted(() => {
  socket?.close()
  if (pollTimer) window.clearInterval(pollTimer)
})
</script>

<style scoped>
.header {
  padding: 12px 14px;
  padding-top: calc(env(safe-area-inset-top) + 8px);
  background: var(--cs-bg-elev);
  border-bottom: 1px solid var(--cs-border);
}
.dim {
  color: var(--cs-text-dim);
}
.small {
  font-size: 12px;
}
.approve-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  border-top: 1px solid var(--cs-border);
}
.approve-row .cn {
  font-weight: 600;
}
.code {
  font-size: 26px;
  font-weight: 700;
  color: var(--cs-accent);
}
.tree-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding-right: 8px;
}
.tree-name {
  flex: 1;
}
.tree-count {
  font-size: 12px;
  color: var(--cs-text-dim);
}
.tree-ops {
  display: flex;
  gap: 12px;
}
.tree-ops .el-icon {
  font-size: 16px;
  color: var(--cs-text-dim);
}
.tree-ops .el-icon.disabled {
  opacity: 0.3;
}
.picked {
  margin-top: 10px;
  color: var(--cs-text-dim);
  font-size: 13px;
}
.dropzone {
  border: 2px dashed var(--cs-border);
  border-radius: 12px;
  padding: 32px 16px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}
.dropzone.over {
  border-color: var(--cs-accent);
  background: color-mix(in srgb, var(--cs-accent) 8%, transparent);
}
.dz-icon {
  font-size: 40px;
  color: var(--cs-accent);
  margin-bottom: 8px;
}
.dz-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 6px;
}
.dz-desc {
  font-size: 12px;
  color: var(--cs-text-dim);
  line-height: 1.6;
}
.import-summary {
  font-size: 14px;
  margin-bottom: 10px;
}
.import-summary .dim {
  font-size: 12px;
}
.import-tree {
  max-height: 320px;
  border: 1px solid var(--cs-border);
  border-radius: 10px;
  padding: 8px 10px;
}
.import-loose {
  font-size: 12px;
  color: var(--cs-text-dim);
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--cs-border);
}
.viewer-body {
  text-align: center;
}
.viewer-stage {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}
.viewer-img {
  max-width: 100%;
  max-height: 60vh;
  object-fit: contain;
  border-radius: 8px;
  background: var(--cs-bg-elev2);
}
.nav-btn {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  z-index: 2;
}
.nav-btn.left {
  left: 4px;
}
.nav-btn.right {
  right: 4px;
}
.viewer-footer {
  display: flex;
  align-items: center;
}
.viewer-meta {
  margin-top: 12px;
  text-align: left;
  font-size: 13px;
  line-height: 1.9;
}
.viewer-meta .k {
  display: inline-block;
  width: 72px;
  color: var(--cs-text-dim);
}
</style>
