<template>
  <div class="cs-page">
    <div class="header">
      <el-page-header @back="back" title="返回">
        <template #content><span class="cs-title">统计看板</span></template>
      </el-page-header>
    </div>

    <div class="cs-container">
      <div class="cs-row" style="margin-bottom: 12px">
        <span class="dim small">共 {{ rows.length }} 张图片</span>
        <span class="cs-spacer" />
        <el-button type="primary" @click="doExport">导出 CSV</el-button>
      </div>

      <div v-if="loading" class="loading">加载中…</div>
      <div v-else-if="rows.length === 0" class="loading">暂无数据</div>
      <div v-else class="list">
        <div v-for="(r, i) in rows" :key="r.photo_id" class="stat-card">
          <div class="rank">{{ i + 1 }}</div>
          <img :src="r.thumbnail_url || r.original_url" class="thumb" />
          <div class="info">
            <div class="name">{{ r.original_name }}</div>
            <div class="path">{{ r.category_path }}</div>
            <div class="metrics">
              <span class="score">⭐ {{ r.avg_score.toFixed(1) }}</span>
              <span class="dim">{{ r.rating_count }}人评</span>
              <span class="dim">💬{{ r.comment_count }}</span>
              <span class="dim">👍{{ r.total_likes }}</span>
              <span class="dim">❤️{{ r.total_favorites }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { StatsRow } from '@/api/types'
import { exportCsvUrl, getStats } from '@/api'
import { useSessionStore } from '@/stores/session'

const props = defineProps<{ spaceId: string }>()
const spaceId = Number(props.spaceId)
const router = useRouter()
const session = useSessionStore()

const rows = ref<StatsRow[]>([])
const loading = ref(true)

function back() {
  router.push({ name: 'space', params: { spaceId } })
}

async function load() {
  loading.value = true
  try {
    rows.value = await getStats(spaceId)
  } finally {
    loading.value = false
  }
}

async function doExport() {
  // fetch with manage key header, then trigger download of the blob
  try {
    const resp = await fetch(exportCsvUrl(spaceId), {
      headers: { 'X-Manage-Key': session.manageKey || '' },
    })
    if (!resp.ok) throw new Error('导出失败')
    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `cosselect_space_${spaceId}.csv`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch (e: any) {
    ElMessage.error(e.message || '导出失败')
  }
}

onMounted(load)
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
.loading {
  text-align: center;
  color: var(--cs-text-dim);
  padding: 60px 0;
}
.stat-card {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--cs-bg-elev);
  border: 1px solid var(--cs-border);
  border-radius: 10px;
  padding: 8px;
  margin-bottom: 8px;
}
.rank {
  width: 24px;
  text-align: center;
  font-weight: 700;
  color: var(--cs-accent);
}
.thumb {
  width: 56px;
  height: 56px;
  border-radius: 8px;
  object-fit: cover;
  flex-shrink: 0;
}
.info {
  flex: 1;
  min-width: 0;
}
.name {
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.path {
  font-size: 12px;
  color: var(--cs-text-dim);
  margin: 2px 0;
}
.metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 12px;
}
.score {
  font-weight: 600;
}
</style>
