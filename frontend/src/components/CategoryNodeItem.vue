<template>
  <div class="node-wrap">
    <div
      class="node"
      :class="{ active: node.id === activeId }"
      :style="{ paddingLeft: 12 + depth * 16 + 'px' }"
      @click="onClick"
    >
      <el-icon v-if="hasChildren" class="caret" :class="{ open: expanded }">
        <CaretRight />
      </el-icon>
      <span v-else class="caret-placeholder" />
      <span class="name">{{ node.name }}</span>
      <span class="count">{{ node.photo_count }}</span>
    </div>
    <div v-if="hasChildren && expanded" class="children">
      <CategoryNodeItem
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :depth="depth + 1"
        :active-id="activeId"
        @select="$emit('select', $event)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { CategoryNode } from '@/api/types'

const props = defineProps<{ node: CategoryNode; depth: number; activeId: number | null }>()
const emit = defineEmits<{ (e: 'select', node: CategoryNode): void }>()

const expanded = ref(true)
const hasChildren = computed(() => props.node.children && props.node.children.length > 0)

function onClick() {
  if (hasChildren.value) {
    expanded.value = !expanded.value
  }
  emit('select', props.node)
}
</script>

<style scoped>
.node {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}
.node:active {
  background: var(--cs-bg-elev2);
}
.node.active {
  background: color-mix(in srgb, var(--cs-accent) 22%, transparent);
  color: var(--cs-accent);
}
.caret {
  transition: transform 0.15s;
  font-size: 12px;
  color: var(--cs-text-dim);
}
.caret.open {
  transform: rotate(90deg);
}
.caret-placeholder {
  width: 12px;
  display: inline-block;
}
.name {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.count {
  font-size: 12px;
  color: var(--cs-text-dim);
  background: var(--cs-bg-elev2);
  border-radius: 10px;
  padding: 1px 8px;
}
</style>
