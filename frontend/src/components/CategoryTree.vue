<template>
  <div class="cat-tree">
    <div v-if="nodes.length === 0" class="empty">暂无分类</div>
    <CategoryNodeItem
      v-for="node in nodes"
      :key="node.id"
      :node="node"
      :depth="0"
      :active-id="activeId"
      @select="$emit('select', $event)"
    />
  </div>
</template>

<script setup lang="ts">
import type { CategoryNode } from '@/api/types'
import CategoryNodeItem from './CategoryNodeItem.vue'

defineProps<{ nodes: CategoryNode[]; activeId: number | null }>()
defineEmits<{ (e: 'select', node: CategoryNode): void }>()
</script>

<style scoped>
.empty {
  color: var(--cs-text-dim);
  text-align: center;
  padding: 20px;
  font-size: 13px;
}
</style>
