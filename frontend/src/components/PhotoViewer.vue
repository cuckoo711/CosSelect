<template>
  <div class="viewer" v-if="visible">
    <!-- top bar -->
    <div class="top-bar">
      <el-icon class="close" @click="close"><Close /></el-icon>
      <span class="index">{{ currentIndex + 1 }} / {{ photos.length }}</span>
      <span class="cs-spacer" />
      <span class="name">{{ current?.original_name }}</span>
    </div>

    <!-- image stage -->
    <div
      class="stage"
      ref="stageRef"
      @touchstart="onTouchStart"
      @touchmove.prevent="onTouchMove"
      @touchend="onTouchEnd"
    >
      <img
        v-if="current"
        :src="displaySrc"
        class="stage-img"
        :style="imgStyle"
        draggable="false"
        @load="onImgLoad"
      />

      <!-- view original floating button -->
      <div v-if="!showingOriginal && current" class="view-original" @click.stop="confirmOriginal">
        查看原图 ({{ sizeMB }} MB)
      </div>
      <div v-if="loadingOriginal" class="loading-original">原图加载中…</div>

      <!-- side arrows (desktop) -->
      <div class="arrow left" v-if="currentIndex > 0" @click.stop="prev">
        <el-icon><ArrowLeftBold /></el-icon>
      </div>
      <div class="arrow right" v-if="currentIndex < photos.length - 1" @click.stop="next">
        <el-icon><ArrowRightBold /></el-icon>
      </div>
    </div>

    <!-- filmstrip: prev/next small thumbs -->
    <div class="filmstrip">
      <div class="film prev">
        <img v-if="prevPhoto" :src="prevPhoto.thumbnail_url || prevPhoto.original_url" @click="prev" />
      </div>
      <div class="film current">
        <img v-if="current" :src="current.thumbnail_url || current.original_url" />
      </div>
      <div class="film next">
        <img v-if="nextPhoto" :src="nextPhoto.thumbnail_url || nextPhoto.original_url" @click="next" />
      </div>
    </div>

    <!-- bottom toolbar -->
    <div class="toolbar">
      <div class="rating-block">
        <div class="avg">
          <el-icon color="#ffcd3c"><StarFilled /></el-icon>
          <b>{{ (detail?.avg_score ?? current?.avg_score ?? 0).toFixed(1) }}</b>
          <span class="dim">({{ detail?.rating_count ?? current?.rating_count ?? 0 }}人)</span>
        </div>
        <div class="my-rate" v-if="!isLeader">
          <span class="dim small">我的评分</span>
          <el-rate
            v-model="myScore"
            allow-half
            :max="5"
            @change="onRate"
            size="large"
          />
        </div>
        <div class="my-rate" v-else>
          <span class="dim small">团长不参与评分</span>
        </div>
      </div>

      <div class="actions">
        <button class="act" :class="{ on: isFavorite }" v-if="!isLeader" @click="onFavorite">
          <span class="ic">{{ isFavorite ? '❤️' : '🤍' }}</span>
          <span class="lbl">喜欢</span>
        </button>
        <button class="act" @click="download">
          <el-icon size="20"><Download /></el-icon>
          <span class="lbl">下载</span>
        </button>
        <button class="act" @click="commentDrawer = true">
          <el-icon size="20"><ChatDotRound /></el-icon>
          <span class="lbl">批注{{ comments.length ? ` ${comments.length}` : '' }}</span>
        </button>
      </div>
    </div>

    <!-- comments drawer -->
    <el-drawer
      v-model="commentDrawer"
      title="批注"
      direction="btt"
      size="72%"
      :z-index="4000"
    >
      <CommentList
        :space-id="spaceId"
        :photo-id="current?.id ?? 0"
        :comments="comments"
        :is-leader="isLeader"
        @changed="reloadComments"
      />
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import type { Comment, Photo, PhotoDetail } from '@/api/types'
import {
  getPhotoDetail,
  listComments,
  submitRating,
  toggleFavorite,
} from '@/api'
import CommentList from './CommentList.vue'

const props = defineProps<{
  visible: boolean
  spaceId: number
  photos: Photo[]
  startIndex: number
  isLeader: boolean
}>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'update-photo', photo: Photo): void
}>()

const currentIndex = ref(props.startIndex)
const detail = ref<PhotoDetail | null>(null)
const comments = ref<Comment[]>([])
const commentDrawer = ref(false)

const showingOriginal = ref(false)
const loadingOriginal = ref(false)

const myScore = ref(0)
const isFavorite = ref(false)

const stageRef = ref<HTMLElement | null>(null)

const current = computed(() => props.photos[currentIndex.value] || null)
const prevPhoto = computed(() => props.photos[currentIndex.value - 1] || null)
const nextPhoto = computed(() => props.photos[currentIndex.value + 1] || null)
const sizeMB = computed(() =>
  current.value ? (current.value.file_size / 1024 / 1024).toFixed(1) : '0',
)

const displaySrc = computed(() => {
  if (!current.value) return ''
  return showingOriginal.value
    ? current.value.original_url
    : current.value.thumbnail_url || current.value.original_url
})

// ----- zoom / pan state -----
const scale = ref(1)
const tx = ref(0)
const ty = ref(0)
const imgStyle = computed(() => ({
  transform: `translate(${tx.value}px, ${ty.value}px) scale(${scale.value})`,
  transition: gestureActive.value ? 'none' : 'transform 0.2s',
}))

function resetTransform() {
  scale.value = 1
  tx.value = 0
  ty.value = 0
}

watch(
  () => props.startIndex,
  (v) => {
    currentIndex.value = v
  },
)

watch(
  () => props.visible,
  (v) => {
    if (v) {
      currentIndex.value = props.startIndex
      loadCurrent()
    }
  },
)

watch(currentIndex, () => loadCurrent())

async function loadCurrent() {
  if (!current.value) return
  showingOriginal.value = false
  resetTransform()
  myScore.value = current.value.my_score ?? 0
  isFavorite.value = current.value.my_favorite
  try {
    const d = await getPhotoDetail(props.spaceId, current.value.id)
    detail.value = d
    comments.value = d.comments
    myScore.value = d.my_score ?? 0
    isFavorite.value = d.my_favorite
  } catch {
    /* ignore */
  }
}

async function reloadComments() {
  if (!current.value) return
  comments.value = await listComments(props.spaceId, current.value.id)
}

function close() {
  emit('close')
}

function prev() {
  if (currentIndex.value > 0) currentIndex.value--
}
function next() {
  if (currentIndex.value < props.photos.length - 1) currentIndex.value++
}

function confirmOriginal() {
  ElMessageBox.confirm(
    `原图约 ${sizeMB.value} MB，确认加载高清原图？`,
    '查看原图',
    { confirmButtonText: '加载', cancelButtonText: '取消', type: 'info' },
  )
    .then(() => {
      loadingOriginal.value = true
      showingOriginal.value = true
    })
    .catch(() => {})
}

function onImgLoad() {
  loadingOriginal.value = false
}

async function onRate(val: number) {
  if (!current.value || props.isLeader) return
  try {
    const res = await submitRating(props.spaceId, current.value.id, val)
    if (detail.value) {
      detail.value.avg_score = res.avg_score
      detail.value.rating_count = res.rating_count
    }
    current.value.my_score = val
    current.value.avg_score = res.avg_score
    current.value.rating_count = res.rating_count
    emit('update-photo', current.value)
    ElMessage.success('评分已保存')
  } catch {
    myScore.value = current.value.my_score ?? 0
  }
}

async function onFavorite() {
  if (!current.value || props.isLeader) return
  const res = await toggleFavorite(props.spaceId, current.value.id)
  isFavorite.value = res.favorite
  current.value.my_favorite = res.favorite
  emit('update-photo', current.value)
}

function download() {
  if (!current.value) return
  const url = current.value.original_url + '?download=true'
  const a = document.createElement('a')
  a.href = url
  a.download = current.value.original_name
  document.body.appendChild(a)
  a.click()
  a.remove()
}

// ----- touch gestures -----
const gestureActive = ref(false)
let startX = 0
let startY = 0
let startDist = 0
let startScale = 1
let panStartX = 0
let panStartY = 0
let mode: 'none' | 'swipe' | 'pan' | 'pinch' = 'none'

function dist(touches: TouchList) {
  const dx = touches[0].clientX - touches[1].clientX
  const dy = touches[0].clientY - touches[1].clientY
  return Math.hypot(dx, dy)
}

function onTouchStart(e: TouchEvent) {
  gestureActive.value = true
  if (e.touches.length === 2) {
    mode = 'pinch'
    startDist = dist(e.touches)
    startScale = scale.value
  } else if (e.touches.length === 1) {
    startX = e.touches[0].clientX
    startY = e.touches[0].clientY
    panStartX = tx.value
    panStartY = ty.value
    mode = scale.value > 1 ? 'pan' : 'swipe'
  }
}

function onTouchMove(e: TouchEvent) {
  if (mode === 'pinch' && e.touches.length === 2) {
    const d = dist(e.touches)
    scale.value = Math.min(5, Math.max(1, (startScale * d) / startDist))
  } else if (mode === 'pan' && e.touches.length === 1) {
    tx.value = panStartX + (e.touches[0].clientX - startX)
    ty.value = panStartY + (e.touches[0].clientY - startY)
  } else if (mode === 'swipe' && e.touches.length === 1) {
    tx.value = e.touches[0].clientX - startX
  }
}

function onTouchEnd(e: TouchEvent) {
  gestureActive.value = false
  if (mode === 'swipe') {
    const dx = tx.value
    const dy = Math.abs(e.changedTouches[0].clientY - startY)
    if (Math.abs(dx) > 60 && Math.abs(dx) > dy) {
      if (dx < 0) next()
      else prev()
    }
    tx.value = 0
  } else if (mode === 'pinch') {
    if (scale.value <= 1.05) resetTransform()
  }
  if (e.touches.length === 0) mode = 'none'
}
</script>

<style scoped>
.viewer {
  position: fixed;
  inset: 0;
  z-index: 3000;
  background: #000;
  display: flex;
  flex-direction: column;
  touch-action: none;
}
.top-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  padding-top: calc(env(safe-area-inset-top) + 10px);
  color: #eee;
  font-size: 13px;
  background: rgba(0, 0, 0, 0.6);
}
.top-bar .close {
  font-size: 22px;
  cursor: pointer;
}
.top-bar .name {
  max-width: 50%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--cs-text-dim);
}
.stage {
  flex: 1;
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}
.stage-img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  will-change: transform;
  user-select: none;
}
.view-original {
  position: absolute;
  right: 14px;
  bottom: 14px;
  background: rgba(0, 0, 0, 0.65);
  border: 1px solid rgba(255, 255, 255, 0.25);
  color: #fff;
  padding: 8px 14px;
  border-radius: 20px;
  font-size: 13px;
  backdrop-filter: blur(4px);
}
.loading-original {
  position: absolute;
  top: 12px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
}
.arrow {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.4);
  color: #fff;
  display: none;
  align-items: center;
  justify-content: center;
}
.arrow.left {
  left: 8px;
}
.arrow.right {
  right: 8px;
}
@media (min-width: 640px) {
  .arrow {
    display: flex;
  }
}
.filmstrip {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 6px 0;
  background: rgba(0, 0, 0, 0.6);
}
.film {
  border-radius: 6px;
  overflow: hidden;
  opacity: 0.5;
}
.film img {
  display: block;
  object-fit: cover;
}
.film.prev img,
.film.next img {
  width: 40px;
  height: 40px;
}
.film.current {
  opacity: 1;
  border: 2px solid var(--cs-accent);
}
.film.current img {
  width: 52px;
  height: 52px;
}
.toolbar {
  background: var(--cs-bg-elev);
  border-top: 1px solid var(--cs-border);
  padding: 10px 14px;
  padding-bottom: calc(env(safe-area-inset-bottom) + 10px);
}
.rating-block {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 6px;
}
.avg {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 16px;
}
.avg .dim,
.dim {
  color: var(--cs-text-dim);
}
.dim.small {
  font-size: 11px;
}
.my-rate {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}
.actions {
  display: flex;
  gap: 6px;
}
.act {
  flex: 1;
  background: var(--cs-bg-elev2);
  border: none;
  color: var(--cs-text);
  border-radius: 8px;
  padding: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  font-size: 11px;
}
.act.on {
  color: var(--cs-danger);
}
.act .ic {
  font-size: 18px;
}
.act:active {
  background: #2e2e2e;
}
</style>
