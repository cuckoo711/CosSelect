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
      <el-dropdown trigger="click" @command="onMenu">
        <el-icon class="menu-btn"><MoreFilled /></el-icon>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item v-if="session.isLeader" command="manage">分类与上传</el-dropdown-item>
            <el-dropdown-item v-if="session.isLeader" command="stats">统计看板</el-dropdown-item>
            <el-dropdown-item command="exit" divided>退出空间</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <!-- content -->
    <div class="content cs-scroll" ref="scrollRef">
      <div v-if="loading" class="loading"><el-icon class="spin"><Loading /></el-icon> 加载中…</div>
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
import { deletePhoto, listCategories, listPhotos } from '@/api'
import { useSessionStore } from '@/stores/session'
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
  else if (cmd === 'exit') {
    session.logout()
    router.push('/')
  }
}

function goManage() {
  router.push({ name: 'manage', params: { spaceId } })
}

onMounted(loadCategories)
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
.loading {
  text-align: center;
  color: var(--cs-text-dim);
  padding: 60px 0;
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
