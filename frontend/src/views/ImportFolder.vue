<template>
  <div class="cs-page import-page">
    <div class="header">
      <el-page-header @back="back" title="返回">
        <template #content><span class="cs-title">按文件夹导入</span></template>
      </el-page-header>
    </div>

    <div class="body cs-scroll">
      <!-- step 1: pick / drop -->
      <div v-if="!importPlan" class="pick-wrap">
        <input
          ref="folderInput"
          type="file"
          webkitdirectory
          directory
          multiple
          style="display: none"
          @change="onFolderPick"
        />
        <div
          class="dropzone"
          :class="{ over: dragOver }"
          @dragover.prevent="dragOver = true"
          @dragleave.prevent="dragOver = false"
          @drop.prevent="onDrop2"
          @click="folderInput?.click()"
        >
          <el-icon class="dz-icon"><FolderOpened /></el-icon>
          <div class="dz-title">拖入文件夹，或点击选择文件夹</div>
          <div class="dz-desc">
            将按子文件夹自动创建分类；仅导入 JPG/JPEG，其他文件自动忽略。<br />
            建议用电脑操作大批量导入。
          </div>
        </div>
        <div v-if="scanning" class="picked">正在扫描文件夹…</div>
      </div>

      <!-- step 2: preview / edit -->
      <template v-else>
        <div class="summary-bar">
          <div class="summary-text">
            将创建 <b>{{ liveCategoryCount }}</b> 个分类，导入 <b>{{ liveJpgCount }}</b> 张 JPG
            <span v-if="importPlan.skipped" class="dim">（忽略 {{ importPlan.skipped }} 个非 JPG）</span>
          </div>
          <el-button size="small" :disabled="importing" @click="resetImport">重新选择</el-button>
        </div>

        <div class="import-tree">
          <div v-for="(node, i) in importPlan.roots" :key="node.name + i">
            <ImportPreviewNode
              :node="node"
              :depth="0"
              @remove="removeRoot(i)"
              @view="viewFile"
              @changed="bumpImport"
            />
          </div>
          <div v-if="importPlan.roots.length === 0 && importPlan.looseFiles.length === 0" class="picked">
            已全部移除，没有可导入的内容。
          </div>
          <div v-if="importPlan.looseFiles.length" class="import-loose">
            另有 {{ importPlan.looseFiles.length }} 张散图（位于「{{ importPlan.looseFolderName || '所选文件夹' }}」下）→
            {{ importParentId ? '归入所选分类' : `新建分类「${importPlan.looseFolderName || '未分类'}」` }}
          </div>
        </div>
      </template>
    </div>

    <!-- sticky footer action bar (only in preview) -->
    <div v-if="importPlan" class="footer-bar">
      <el-select v-model="importParentId" size="default" class="dest-select">
        <el-option :value="0" label="作为新分类（顶层）" />
        <el-option
          v-for="opt in flatCategoryOptions"
          :key="opt.id"
          :value="opt.id"
          :label="`导入到：${opt.label}`"
        />
      </el-select>
      <el-button
        type="primary"
        :loading="importing"
        :disabled="liveJpgCount === 0"
        @click="runImport"
      >
        开始导入
      </el-button>
    </div>

    <!-- upload progress overlay -->
    <div v-if="importing" class="progress-overlay">
      <div class="progress-box">
        <div class="picked">{{ importStatus }}</div>
        <el-progress :percentage="importProgress" :stroke-width="12" />
      </div>
    </div>

    <!-- single image viewer -->
    <el-dialog
      v-model="viewerVisible"
      :title="viewerTitle"
      width="92%"
      top="5vh"
      @closed="onViewerClosed"
    >
      <div v-if="viewFileUrl" class="viewer-body">
        <div class="viewer-stage">
          <el-button class="nav-btn left" circle :disabled="viewIndex <= 0" @click="viewPrev">
            <el-icon><ArrowLeft /></el-icon>
          </el-button>
          <img :src="viewFileUrl" class="viewer-img" />
          <el-button
            class="nav-btn right"
            circle
            :disabled="viewIndex >= viewList.length - 1"
            @click="viewNext"
          >
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>
        <div v-if="viewFileMeta" class="viewer-meta">
          <div><span class="k">文件名</span>{{ viewFileMeta.name }}</div>
          <div><span class="k">尺寸</span>{{ viewFileMeta.w }} × {{ viewFileMeta.h }} 像素（{{ viewFileMeta.mp }} MP）</div>
          <div><span class="k">大小</span>{{ viewFileMeta.size }}</div>
          <div><span class="k">类型</span>{{ viewFileMeta.type || '未知' }}</div>
          <div><span class="k">修改时间</span>{{ viewFileMeta.mtime }}</div>
        </div>
      </div>
      <template #footer>
        <div class="viewer-footer">
          <span class="dim small">← → 键可切换 · {{ viewIndex + 1 }}/{{ viewList.length }}</span>
          <span class="cs-spacer" />
          <el-button type="danger" @click="deleteCurrentView">
            <el-icon style="margin-right: 4px"><Delete /></el-icon>删除这张
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { CategoryNode } from '@/api/types'
import { createCategory, listCategories, uploadPhotos } from '@/api'
import { compressImage } from '@/utils/image'
import ImportPreviewNode from '@/components/ImportPreviewNode.vue'
import { buildImportPlan, countFiles, isJpeg, type ImportNode } from '@/utils/folderImport'

const props = defineProps<{ spaceId: string }>()
const spaceId = props.spaceId
const router = useRouter()

const treeData = ref<CategoryNode[]>([])
const folderInput = ref<HTMLInputElement | null>(null)
const dragOver = ref(false)
const scanning = ref(false)
const importPlan = ref<ReturnType<typeof buildImportPlan> | null>(null)
const importParentId = ref<number>(0)
const importing = ref(false)
const importProgress = ref(0)
const importStatus = ref('')

function back() {
  router.push({ name: 'manage', params: { spaceId } })
}

// bumped when the plan is edited so computed counts re-evaluate.
const importRev = ref(0)
function bumpImport() {
  importRev.value += 1
}

const liveCategoryCount = computed(() => {
  void importRev.value
  if (!importPlan.value) return 0
  return importPlan.value.roots.reduce((s, r) => s + countCategories(r), 0)
})
const liveJpgCount = computed(() => {
  void importRev.value
  if (!importPlan.value) return 0
  const rootSum = importPlan.value.roots.reduce((s, r) => s + countFiles(r), 0)
  return rootSum + importPlan.value.looseFiles.length
})

function countCategories(node: ImportNode): number {
  return 1 + node.children.reduce((s, c) => s + countCategories(c), 0)
}

function removeRoot(index: number) {
  if (!importPlan.value) return
  importPlan.value.roots.splice(index, 1)
  bumpImport()
}

const flatCategoryOptions = computed(() => {
  const opts: { id: number; label: string }[] = []
  const walk = (nodes: CategoryNode[], prefix: string) => {
    for (const n of nodes) {
      opts.push({ id: n.id, label: prefix + n.name })
      walk(n.children, prefix + n.name + ' / ')
    }
  }
  walk(treeData.value, '')
  return opts
})

function resetImport() {
  importPlan.value = null
  importProgress.value = 0
}

function onFolderPick(e: Event) {
  const input = e.target as HTMLInputElement
  const files = input.files ? Array.from(input.files) : []
  const withPaths = files.map((f) => ({
    file: f,
    path: (f as any).webkitRelativePath || f.name,
  }))
  buildPlan(withPaths)
  input.value = ''
}

async function onDrop2(e: DragEvent) {
  dragOver.value = false
  const items = e.dataTransfer?.items
  if (!items) return
  scanning.value = true
  try {
    const entries: any[] = []
    for (let i = 0; i < items.length; i++) {
      const entry = (items[i] as any).webkitGetAsEntry?.()
      if (entry) entries.push(entry)
    }
    const collected: { file: File; path: string }[] = []
    await Promise.all(entries.map((en) => readEntry(en, '', collected)))
    buildPlan(collected)
  } finally {
    scanning.value = false
  }
}

function readEntry(entry: any, prefix: string, out: { file: File; path: string }[]): Promise<void> {
  return new Promise((resolve) => {
    if (entry.isFile) {
      entry.file((file: File) => {
        out.push({ file, path: prefix + entry.name })
        resolve()
      }, () => resolve())
    } else if (entry.isDirectory) {
      const reader = entry.createReader()
      const all: any[] = []
      const readBatch = () => {
        reader.readEntries(async (batch: any[]) => {
          if (batch.length === 0) {
            await Promise.all(all.map((c) => readEntry(c, prefix + entry.name + '/', out)))
            resolve()
          } else {
            all.push(...batch)
            readBatch()
          }
        }, () => resolve())
      }
      readBatch()
    } else {
      resolve()
    }
  })
}

function buildPlan(files: { file: File; path: string }[]) {
  const plan = buildImportPlan(files)
  if (plan.jpgCount === 0) {
    ElMessage.warning('没有找到可导入的 JPG 图片')
    importPlan.value = null
    return
  }
  importPlan.value = plan
}

async function runImport() {
  if (!importPlan.value) return
  importing.value = true
  importProgress.value = 0
  try {
    const rootParent = importParentId.value || null
    let totalFiles = importPlan.value.roots.reduce((s, r) => s + countFiles(r), 0)
    totalFiles += importPlan.value.looseFiles.length
    let done = 0

    const createAndUpload = async (node: ImportNode, parentId: number | null) => {
      importStatus.value = `创建分类「${node.name}」…`
      const existing = findChildByName(parentId, node.name)
      const catId = existing ?? (await createCategory(spaceId, node.name, parentId)).id
      if (node.files.length) {
        const compressed: File[] = []
        for (const f of node.files) {
          if (isJpeg(f)) compressed.push(await compressImage(f))
        }
        importStatus.value = `上传「${node.name}」(${compressed.length} 张)…`
        await uploadPhotos(spaceId, catId, compressed)
        done += node.files.length
        importProgress.value = Math.round((done / totalFiles) * 100)
      }
      await loadTree()
      for (const child of node.children) {
        await createAndUpload(child, catId)
      }
    }

    for (const root of importPlan.value.roots) {
      await createAndUpload(root, rootParent)
    }

    if (importPlan.value.looseFiles.length) {
      const compressed: File[] = []
      for (const f of importPlan.value.looseFiles) {
        if (isJpeg(f)) compressed.push(await compressImage(f))
      }
      let looseTarget = rootParent
      if (!looseTarget) {
        const name = importPlan.value.looseFolderName || '未分类'
        const existing = findChildByName(null, name)
        looseTarget = existing ?? (await createCategory(spaceId, name, null)).id
      }
      importStatus.value = `上传散图(${compressed.length} 张)…`
      await uploadPhotos(spaceId, looseTarget, compressed)
      done += importPlan.value.looseFiles.length
      importProgress.value = Math.round((done / totalFiles) * 100)
    }

    importProgress.value = 100
    ElMessage.success('文件夹导入完成，缩略图后台生成中')
    back()
  } catch (e: any) {
    ElMessage.error(e?.message || '导入过程中出错')
  } finally {
    importing.value = false
    importStatus.value = ''
  }
}

function findChildByName(parentId: number | null, name: string): number | null {
  const search = (nodes: CategoryNode[]): number | null => {
    for (const n of nodes) {
      const matchParent = parentId == null ? n.parent_id == null : n.parent_id === parentId
      if (matchParent && n.name === name) return n.id
      const r = search(n.children)
      if (r != null) return r
    }
    return null
  }
  return search(treeData.value)
}

async function loadTree() {
  treeData.value = await listCategories(spaceId)
}

// ----- single image viewer (prev/next + delete) -----
const viewerVisible = ref(false)
const viewFileUrl = ref('')
const viewList = ref<File[]>([])
const viewIndex = ref(0)
const viewFileMeta = ref<{
  name: string
  w: number
  h: number
  mp: string
  size: string
  type: string
  mtime: string
} | null>(null)
const viewerTitle = computed(() => viewFileMeta.value?.name || '预览')

function fmtSize(bytes: number): string {
  if (bytes >= 1024 * 1024) return (bytes / 1024 / 1024).toFixed(2) + ' MB'
  return (bytes / 1024).toFixed(0) + ' KB'
}

function loadViewAt(index: number) {
  const file = viewList.value[index]
  if (!file) return
  viewIndex.value = index
  if (viewFileUrl.value) URL.revokeObjectURL(viewFileUrl.value)
  viewFileUrl.value = URL.createObjectURL(file)
  viewFileMeta.value = {
    name: file.name,
    w: 0,
    h: 0,
    mp: '—',
    size: fmtSize(file.size),
    type: file.type,
    mtime: file.lastModified ? new Date(file.lastModified).toLocaleString('zh-CN') : '—',
  }
  const img = new Image()
  img.onload = () => {
    if (viewFileMeta.value) {
      viewFileMeta.value.w = img.naturalWidth
      viewFileMeta.value.h = img.naturalHeight
      viewFileMeta.value.mp = ((img.naturalWidth * img.naturalHeight) / 1e6).toFixed(1)
    }
  }
  img.src = viewFileUrl.value
}

function viewFile(req: { files: File[]; index: number }) {
  viewList.value = req.files
  viewerVisible.value = true
  loadViewAt(req.index)
  window.addEventListener('keydown', onViewerKey)
}

function viewPrev() {
  if (viewIndex.value > 0) loadViewAt(viewIndex.value - 1)
}
function viewNext() {
  if (viewIndex.value < viewList.value.length - 1) loadViewAt(viewIndex.value + 1)
}

function onViewerKey(e: KeyboardEvent) {
  if (!viewerVisible.value) return
  if (e.key === 'ArrowLeft') {
    e.preventDefault()
    viewPrev()
  } else if (e.key === 'ArrowRight') {
    e.preventDefault()
    viewNext()
  }
}

async function deleteCurrentView() {
  try {
    await ElMessageBox.confirm(
      `确认删除「${viewFileMeta.value?.name}」？此操作仅从本次导入中移除，不影响原文件。`,
      '删除图片',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }
  const idx = viewIndex.value
  viewList.value.splice(idx, 1)
  bumpImport()
  if (viewList.value.length === 0) {
    viewerVisible.value = false
    return
  }
  loadViewAt(Math.min(idx, viewList.value.length - 1))
}

function onViewerClosed() {
  window.removeEventListener('keydown', onViewerKey)
  if (viewFileUrl.value) {
    URL.revokeObjectURL(viewFileUrl.value)
    viewFileUrl.value = ''
  }
}

onMounted(loadTree)
onUnmounted(() => {
  window.removeEventListener('keydown', onViewerKey)
  if (viewFileUrl.value) URL.revokeObjectURL(viewFileUrl.value)
})
</script>

<style scoped>
.import-page {
  height: 100vh;
  height: 100dvh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.header {
  padding: 12px 14px;
  padding-top: calc(env(safe-area-inset-top) + 8px);
  background: var(--cs-bg-elev);
  border-bottom: 1px solid var(--cs-border);
}
.body {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
  max-width: 900px;
  width: 100%;
  margin: 0 auto;
}
.pick-wrap {
  padding-top: 8vh;
}
.dropzone {
  border: 2px dashed var(--cs-border);
  border-radius: 14px;
  padding: 48px 20px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}
.dropzone.over {
  border-color: var(--cs-accent);
  background: color-mix(in srgb, var(--cs-accent) 8%, transparent);
}
.dz-icon {
  font-size: 52px;
  color: var(--cs-accent);
  margin-bottom: 10px;
}
.dz-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 8px;
}
.dz-desc {
  font-size: 13px;
  color: var(--cs-text-dim);
  line-height: 1.7;
}
.summary-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.summary-text {
  flex: 1;
  font-size: 14px;
}
.summary-text .dim {
  font-size: 12px;
}
.dim {
  color: var(--cs-text-dim);
}
.small {
  font-size: 12px;
}
.import-tree {
  border: 1px solid var(--cs-border);
  border-radius: 10px;
  padding: 8px 12px;
}
.import-loose {
  font-size: 12px;
  color: var(--cs-text-dim);
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--cs-border);
}
.picked {
  color: var(--cs-text-dim);
  font-size: 13px;
  margin-top: 10px;
  text-align: center;
}
.footer-bar {
  display: flex;
  gap: 10px;
  padding: 12px 14px;
  padding-bottom: calc(env(safe-area-inset-bottom) + 12px);
  background: var(--cs-bg-elev);
  border-top: 1px solid var(--cs-border);
}
.dest-select {
  flex: 1;
}
.progress-overlay {
  position: fixed;
  inset: 0;
  z-index: 3000;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
}
.progress-box {
  width: 86%;
  max-width: 420px;
  background: var(--cs-bg-elev);
  border: 1px solid var(--cs-border);
  border-radius: 12px;
  padding: 20px;
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
  max-height: 62vh;
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
.viewer-footer {
  display: flex;
  align-items: center;
}
</style>
