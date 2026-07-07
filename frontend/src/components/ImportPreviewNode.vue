<template>
  <div class="ip-node">
    <div class="ip-row" :style="{ paddingLeft: depth * 14 + 'px' }">
      <el-icon class="ip-caret" :class="{ open: expanded }" @click="expanded = !expanded">
        <CaretRight />
      </el-icon>
      <el-icon class="ip-folder"><Folder /></el-icon>
      <span class="ip-name" @click="expanded = !expanded">{{ node.name }}</span>
      <span class="ip-count">{{ total }} 张</span>
      <el-icon class="ip-remove" title="移除该文件夹" @click.stop="$emit('remove')">
        <Delete />
      </el-icon>
    </div>

    <div v-show="expanded" class="ip-body">
      <!-- direct images of this folder -->
      <div v-if="node.files.length" class="ip-grid" :style="{ marginLeft: (depth + 1) * 14 + 'px' }">
        <ImportThumb
          v-for="(f, i) in node.files"
          :key="fileKey(f, i)"
          :file="f"
          @view="$emit('view', { files: node.files, index: i })"
          @remove="removeFile(i)"
        />
      </div>

      <!-- child folders -->
      <ImportPreviewNode
        v-for="(child, i) in node.children"
        :key="child.name + i"
        :node="child"
        :depth="depth + 1"
        @remove="removeChild(i)"
        @view="$emit('view', $event)"
        @changed="$emit('changed')"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ImportNode, ViewRequest } from '@/utils/folderImport'
import { countFiles } from '@/utils/folderImport'
import ImportThumb from './ImportThumb.vue'

const props = defineProps<{ node: ImportNode; depth: number }>()
const emit = defineEmits<{
  (e: 'remove'): void
  (e: 'view', req: ViewRequest): void
  (e: 'changed'): void
}>()

const expanded = ref(props.depth === 0)

const total = computed(() => countFiles(props.node))

function fileKey(f: File, i: number) {
  return `${f.name}-${f.size}-${i}`
}

function removeFile(index: number) {
  props.node.files.splice(index, 1)
  emit('changed')
}

function removeChild(index: number) {
  props.node.children.splice(index, 1)
  emit('changed')
}
</script>

<style scoped>
.ip-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 0;
  font-size: 13px;
}
.ip-caret {
  font-size: 12px;
  color: var(--cs-text-dim);
  transition: transform 0.15s;
  cursor: pointer;
}
.ip-caret.open {
  transform: rotate(90deg);
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
  cursor: pointer;
}
.ip-count {
  color: var(--cs-text-dim);
  font-size: 12px;
}
.ip-remove {
  color: var(--cs-text-dim);
  font-size: 14px;
  cursor: pointer;
}
.ip-remove:active {
  color: var(--cs-danger);
}
.ip-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(44px, 1fr));
  gap: 4px;
  padding: 4px 0 8px;
}
</style>
