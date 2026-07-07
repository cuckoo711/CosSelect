<template>
  <div class="cs-page space-home">
    <!-- header -->
    <div class="header">
      <el-icon class="menu-btn" @click="drawer = true"><Menu /></el-icon>
      <div class="title-box">
        <div class="cat-name">{{ activeCategory?.name || '选择分类' }}</div>
        <div class="role">{{ session.displayName }}</div>
      </div>
      <el-dropdown trigger="click" @command="onSort">
        <span class="sort-btn">
          {{ sortLabel }} <el-icon><ArrowDown /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="score">按平均分</el-dropdown-item>
            <el-dropdown-item command="time">按上传时间</el-dropdown-item>
            <el-dropdown-item command="count">按评分人数</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
      <el-button
        v-if="session.isLeader"
        type="primary"
        size="small"
        class="upload-btn"
        @click="goManage"
      >
        <el-icon style="margin-right: 4px"><UploadFilled /></el-icon>上传
      </el-button>
      <el-dropdown trigger="click" @command="onMenu">
        <el-icon class="menu-btn"><MoreFilled /></el-icon>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item v-if="session.isLeader" command="manage">分类与上传</el-dropdown-item>
            <el-dropdown-item v-if="session.isLeader" command="stats">统计看板</el-dropdown-item>
            <el-dropdown-item v-if="session.isLeader" command="invite">邀请团员</el-dropdown-item>
            <el-dropdown-item command="exit" divided>退出空间</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <!-- content -->
    <div class="content cs-scroll" ref="scrollRef">
      <div v-if="loading" class="loading"><el-icon class="spin"><Loading /></el-icon> 加载中…</div>

      <!-- empty guide -->
      <div v-else-if="showGuide" class="guide">
        <!-- Leader, no categories at all -->
        <template v-if="session.isLeader && categories.length === 0">
          <div class="guide-icon">📂</div>
          <div class="guide-title">欢迎来到选片空间</div>
          <p class="guide-desc">
            这里是团队一起给团片打分、批注、选片的地方。<br />
            开始前，先创建分类并上传照片吧。
          </p>
          <div class="guide-steps">
            <div class="step"><span class="n">1</span> 创建分类（如「第一天」「场景A」）</div>
            <div class="step"><span class="n">2</span> 批量上传照片（自动压缩，省流量）</div>
            <div class="step"><span class="n">3</span> 把口令 / 链接发给团员一起选片</div>
          </div>
          <el-button type="primary" size="large" class="guide-btn" @click="goManage">
            <el-icon style="margin-right: 6px"><FolderAdd /></el-icon>去创建分类 / 上传照片
          </el-button>
          <el-button text class="guide-sub" @click="onMenu('invite')">复制邀请信息给团员</el-button>
        </template>

        <!-- Leader, has categories but current one is empty -->
        <template v-else-if="session.isLeader">
          <div class="guide-icon">🖼️</div>
          <div class="guide-title">「{{ activeCategory?.name }}」还没有照片</div>
          <p class="guide-desc">上传照片到这个分类，团员就能开始评分了。</p>
          <el-button type="primary" size="large" class="guide-btn" @click="goManage">
            <el-icon style="margin-right: 6px"><UploadFilled /></el-icon>上传照片
          </el-button>
          <el-button text class="guide-sub" @click="drawer = true">切换其他分类</el-button>
        </template>

        <!-- Participant, nothing to see yet -->
        <template v-else>
          <div class="guide-icon">⏳</div>
          <div class="guide-title">团长还没上传照片</div>
          <p class="guide-desc">照片上传后就能在这里评分、批注啦，稍后再来看看吧。</p>
          <el-button v-if="categories.length > 0" text class="guide-sub" @click="drawer = true">
            查看其他分类
          </el-button>
        </template>
      </div>

      <PhotoGrid
        v-else
        :photos="photos"
        :show-manage="session.isLeader"
        @open="openViewer"
        @delete="onDeletePhoto"
      />
    </div>

    <!-- category drawer -->
    <el-drawer v-model="drawer" title="分类" direction="ltr" size="78%">
      <CategoryTree :nodes="categories" :active-id="activeCategoryId" @select="onSelectCategory" />
      <div v-if="session.isLeader" style="margin-top: 16px">
        <el-button type="primary" plain style="width: 100%" @click="goManage">管理分类 / 上传</el-button>
      </div>
    </el-drawer>

    <!-- viewer -->
    <PhotoViewer
      :visible="viewerVisible"
      :space-id="spaceId"
      :photos="photos"
      :start-index="viewerIndex"
      :is-leader="session.isLeader"
      @close="viewerVisible = false"
      @update-photo="onPhotoUpdated"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { CategoryNode, Photo, SortKey } from '@/api/types'
import { deletePhoto, getSpaceInfo, listCategories, listPhotos } from '@/api'
import { useSessionStore } from '@/stores/session'
import { copyText } from '@/utils/clipboard'
import CategoryTree from '@/components/CategoryTree.vue'
import PhotoGrid from '@/components/PhotoGrid.vue'
import PhotoViewer from '@/components/PhotoViewer.vue'

const props = defineProps<{ spaceId: string }>()
const spaceId = props.spaceId
const router = useRouter()
const session = useSessionStore()

const drawer = ref(false)
const categories = ref<CategoryNode[]>([])
const activeCategoryId = ref<number | null>(null)
const photos = ref<Photo[]>([])
const loading = ref(false)
const sort = ref<SortKey>('score')

const viewerVisible = ref(false)
const viewerIndex = ref(0)

const sortLabel = computed(
  () => ({ score: '平均分', time: '上传时间', count: '评分人数' })[sort.value],
)

const activeCategory = computed(() => findCat(categories.value, activeCategoryId.value))

// show the empty-state guide when there are no photos to display
const showGuide = computed(() => !loading.value && photos.value.length === 0)

const accessUrl = typeof window !== 'undefined' ? window.location.origin : ''

function findCat(nodes: CategoryNode[], id: number | null): CategoryNode | null {
  if (id == null) return null
  for (const n of nodes) {
    if (n.id === id) return n
    const c = findCat(n.children, id)
    if (c) return c
  }
  return null
}

function firstLeafOrAny(nodes: CategoryNode[]): CategoryNode | null {
  // prefer first category with photos, else first category
  let firstWithPhotos: CategoryNode | null = null
  let first: CategoryNode | null = null
  const walk = (arr: CategoryNode[]) => {
    for (const n of arr) {
      if (!first) first = n
      if (!firstWithPhotos && n.photo_count > 0) firstWithPhotos = n
      walk(n.children)
    }
  }
  walk(nodes)
  return firstWithPhotos || first
}

async function loadCategories() {
  categories.value = await listCategories(spaceId)
  if (!activeCategoryId.value) {
    const c = firstLeafOrAny(categories.value)
    if (c) {
      activeCategoryId.value = c.id
      await loadPhotos()
    }
  }
}

async function loadPhotos() {
  if (activeCategoryId.value == null) {
    photos.value = []
    return
  }
  loading.value = true
  try {
    photos.value = await listPhotos(spaceId, activeCategoryId.value, sort.value)
  } finally {
    loading.value = false
  }
}

function onSelectCategory(node: CategoryNode) {
  activeCategoryId.value = node.id
  drawer.value = false
  loadPhotos()
}

function onSort(cmd: SortKey) {
  sort.value = cmd
  loadPhotos()
}

function openViewer(index: number) {
  viewerIndex.value = index
  viewerVisible.value = true
}

function onPhotoUpdated(p: Photo) {
  const idx = photos.value.findIndex((x) => x.id === p.id)
  if (idx >= 0) photos.value[idx] = { ...p }
}

async function onDeletePhoto(p: Photo) {
  try {
    await ElMessageBox.confirm(`删除图片「${p.original_name}」？`, '删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  await deletePhoto(spaceId, p.id)
  ElMessage.success('已删除')
  await loadCategories()
  await loadPhotos()
}

function onMenu(cmd: string) {
  if (cmd === 'manage') goManage()
  else if (cmd === 'stats') router.push({ name: 'stats', params: { spaceId } })
  else if (cmd === 'invite') inviteMembers()
  else if (cmd === 'exit') {
    session.logout()
    router.push('/')
  }
}

function inviteMembers() {
  const code = session.inviteCode || ''
  const link = code ? `${accessUrl}/?code=${code}` : accessUrl
  const text = [
    '【团片选片 · 邀请你参与】',
    `参与者链接（打开设置 CN 即可）：${link}`,
    code ? `口令：${code}` : '',
    `或访问 ${accessUrl} 选择「我是参与者」`,
  ]
    .filter(Boolean)
    .join('\n')
  copyText(text)
}

function goManage() {
  router.push({ name: 'manage', params: { spaceId } })
}

async function showLeaderInactivityNotice() {
  if (!session.isLeader) return
  let noticeDays = 30
  let lastAccess: string | null = null
  try {
    const info = await getSpaceInfo(spaceId)
    noticeDays = info.inactive_notice_days ?? 30
    lastAccess = info.last_access_at
  } catch {
    /* use defaults */
  }
  const lastText = lastAccess
    ? new Date(lastAccess.endsWith('Z') ? lastAccess : lastAccess + 'Z').toLocaleString('zh-CN')
    : '刚刚'
  ElMessageBox.alert(
    `<div style="line-height:1.7">
      为节省服务器资源，超过 <b style="color:var(--el-color-danger)">${noticeDays} 天</b> 未访问的空间将被自动销毁，届时所有图片、评分与批注都将被清空且无法恢复。<br/><br/>
      请定期进入本空间以保持活跃。<br/>
      <span style="color:var(--el-text-color-secondary);font-size:12px">上次活跃：${lastText}</span>
    </div>`,
    '空间保留提示',
    {
      dangerouslyUseHTMLString: true,
      confirmButtonText: '我知道了',
      customClass: 'cs-notice-box',
    },
  ).catch(() => {})
}

onMounted(() => {
  loadCategories()
  showLeaderInactivityNotice()
})
</script>

<style scoped>
.space-home {
  height: 100vh;
  height: 100dvh;
  overflow: hidden;
}
.header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  padding-top: calc(env(safe-area-inset-top) + 8px);
  background: var(--cs-bg-elev);
  border-bottom: 1px solid var(--cs-border);
}
.menu-btn {
  font-size: 22px;
  cursor: pointer;
}
.title-box {
  flex: 1;
  min-width: 0;
}
.cat-name {
  font-size: 16px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.role {
  font-size: 11px;
  color: var(--cs-text-dim);
}
.sort-btn {
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: 13px;
  color: var(--cs-accent);
  cursor: pointer;
}
.content {
  height: 100%;
  padding: 12px;
  padding-bottom: 40px;
}
.upload-btn {
  flex-shrink: 0;
}
.loading {
  text-align: center;
  color: var(--cs-text-dim);
  padding: 60px 0;
}
.guide {
  max-width: 420px;
  margin: 0 auto;
  padding: 48px 20px;
  text-align: center;
}
.guide-icon {
  font-size: 52px;
  margin-bottom: 12px;
}
.guide-title {
  font-size: 19px;
  font-weight: 600;
  margin-bottom: 8px;
}
.guide-desc {
  color: var(--cs-text-dim);
  font-size: 13px;
  line-height: 1.7;
  margin-bottom: 20px;
}
.guide-steps {
  text-align: left;
  background: var(--cs-bg-elev);
  border: 1px solid var(--cs-border);
  border-radius: 12px;
  padding: 14px 16px;
  margin-bottom: 20px;
}
.guide-steps .step {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  padding: 7px 0;
}
.guide-steps .n {
  flex-shrink: 0;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--cs-accent);
  color: #fff;
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.guide-btn {
  width: 100%;
}
.guide-sub {
  margin-top: 10px;
}
.spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
