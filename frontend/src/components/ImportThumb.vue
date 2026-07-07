<template>
  <div class="thumb" @click="$emit('view')">
    <img :src="url" :alt="file.name" loading="lazy" />
    <div class="del" @click.stop="$emit('remove')">
      <el-icon><Close /></el-icon>
    </div>
    <div class="fname">{{ file.name }}</div>
  </div>
</template>

<script setup lang="ts">
import { onUnmounted, ref } from 'vue'

const props = defineProps<{ file: File }>()
defineEmits<{ (e: 'view'): void; (e: 'remove'): void }>()

// object URL is created once and released when this thumb unmounts
// (i.e. when its folder is collapsed or removed), preventing memory leaks.
const url = ref(URL.createObjectURL(props.file))

onUnmounted(() => {
  URL.revokeObjectURL(url.value)
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
.del {
  position: absolute;
  top: 3px;
  right: 3px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}
.del:active {
  background: var(--cs-danger);
}
.fname {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 2px 4px;
  font-size: 10px;
  color: #fff;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.7));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
