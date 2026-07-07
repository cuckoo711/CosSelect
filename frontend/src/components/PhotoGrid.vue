<template>
  <div class="photo-grid">
    <div v-if="photos.length === 0" class="empty">该分类下暂无图片</div>
    <div v-else class="grid">
      <div
        v-for="(photo, idx) in photos"
        :key="photo.id"
        class="cell"
        @click="$emit('open', idx)"
      >
        <div class="thumb-wrap">
          <img
            :src="photo.thumbnail_url || photo.image_url"
            loading="lazy"
            decoding="async"
            class="thumb"
            :alt="photo.original_name"
          />
          <div v-if="photo.my_favorite" class="fav-badge">❤️</div>
          <div v-if="showManage" class="del-badge" @click.stop="$emit('delete', photo)">
            <el-icon><Delete /></el-icon>
          </div>
        </div>
        <div class="meta">
          <span class="score">
            <el-icon color="#ffcd3c"><StarFilled /></el-icon>
            {{ photo.avg_score.toFixed(1) }}
          </span>
          <span class="dim">{{ photo.rating_count }}人</span>
          <span v-if="photo.comment_count" class="dim">💬{{ photo.comment_count }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Photo } from '@/api/types'

defineProps<{ photos: Photo[]; showManage?: boolean }>()
defineEmits<{
  (e: 'open', index: number): void
  (e: 'delete', photo: Photo): void
}>()
</script>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}
@media (min-width: 520px) {
  .grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
.cell {
  background: var(--cs-bg-elev);
  border-radius: 10px;
  overflow: hidden;
  cursor: pointer;
}
.cell:active {
  opacity: 0.9;
}
.thumb-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 1 / 1;
  background: var(--cs-bg-elev2);
}
.thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.fav-badge {
  position: absolute;
  top: 6px;
  right: 6px;
  font-size: 14px;
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.6));
}
.del-badge {
  position: absolute;
  top: 6px;
  left: 6px;
  background: rgba(0, 0, 0, 0.55);
  color: #fff;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.meta {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  font-size: 12px;
}
.score {
  display: flex;
  align-items: center;
  gap: 3px;
  font-weight: 600;
}
.dim {
  color: var(--cs-text-dim);
}
.empty {
  color: var(--cs-text-dim);
  text-align: center;
  padding: 60px 20px;
}
</style>
