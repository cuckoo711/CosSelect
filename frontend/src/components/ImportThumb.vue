<template>
  <div ref="root" class="thumb" @click="$emit('view')">
    <img v-if="url" :src="url" :alt="file.name" />
    <div v-else class="ph"><el-icon><Picture /></el-icon></div>
    <div class="del" @click.stop="$emit('remove')">
      <el-icon><Close /></el-icon>
    </div>
    <div class="fname">{{ file.name }}</div>
  </div>
</template>

<script setup lang="ts">
import { onUnmounted, ref } from 'vue'
import { createThumbUrl } from '@/utils/thumbnail'

const props = defineProps<{ file: File }>()
defineEmits<{ (e: 'view'): void; (e: 'remove'): void }>()

const root = ref<HTMLElement | null>(null)
const url = ref('')
let observer: IntersectionObserver | null = null
let generated = false

function generate() {
  if (generated) return
  generated = true
  createThumbUrl(props.file, 160)
    .then((u) => {
      url.value = u
    })
    .catch(() => {
      generated = false // allow retry on next intersection
    })
}

// Lazily build the thumbnail only when the cell enters the viewport, so a
// folder with hundreds of photos doesn't decode them all at once.
function mount() {
  if (!root.value) return
  if (!('IntersectionObserver' in window)) {
    generate()
    return
  }
  // Thumbs are tiny (~160px JPEGs), so preload several screens ahead to avoid
  // waiting while scrolling. Vertical margin is large; the worker pool + the
  // generation queue keep memory/CPU bounded.
  observer = new IntersectionObserver(
    (entries) => {
      if (entries.some((e) => e.isIntersecting)) generate()
    },
    { rootMargin: '2000px 0px' },
  )
  observer.observe(root.value)
}

// use a microtask so the ref is attached
requestAnimationFrame(mount)

onUnmounted(() => {
  observer?.disconnect()
  if (url.value) URL.revokeObjectURL(url.value)
})
</script>

<style scoped>
.thumb {
  position: relative;
  aspect-ratio: 1 / 1;
  border-radius: 8px;
  overflow: hidden;
  background: var(--cs-bg-elev2);
  cursor: pointer;
}
.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.ph {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--cs-text-dim);
  font-size: 16px;
}
.del {
  position: absolute;
  top: 1px;
  right: 1px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.55);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
}
.del:active {
  background: var(--cs-danger);
}
/* filename hidden on the tiny grid thumbs; shown in the big viewer instead */
.fname {
  display: none;
}
</style>
