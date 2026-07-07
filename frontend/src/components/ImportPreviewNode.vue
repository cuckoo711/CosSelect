<template>
  <div class="ip-node">
    <div class="ip-row" :style="{ paddingLeft: depth * 16 + 'px' }">
      <el-icon class="ip-folder"><Folder /></el-icon>
      <span class="ip-name">{{ node.name }}</span>
      <span class="ip-count">{{ node.files.length }} 张</span>
    </div>
    <ImportPreviewNode
      v-for="(child, i) in node.children"
      :key="i"
      :node="child"
      :depth="depth + 1"
    />
  </div>
</template>

<script setup lang="ts">
import type { ImportNode } from '@/utils/folderImport'

defineProps<{ node: ImportNode; depth: number }>()
</script>

<style scoped>
.ip-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 0;
  font-size: 13px;
}
.ip-folder {
  color: var(--cs-accent);
  font-size: 14px;
}
.ip-name {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ip-count {
  color: var(--cs-text-dim);
  font-size: 12px;
}
</style>
