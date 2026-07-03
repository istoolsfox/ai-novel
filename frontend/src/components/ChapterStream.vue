<script setup lang="ts">
import { computed } from "vue";
import { NScrollbar, NEmpty, NTag, NText } from "naive-ui";
import type { Chapter } from "../api/types";

const props = defineProps<{
  projectId: string;
  chapters: Chapter[];
  currentChapter?: number;
}>();

const sortedChapters = computed(() =>
  [...props.chapters].sort((a, b) => a.chapter_number - b.chapter_number),
);
</script>

<template>
  <div class="chapter-stream">
    <NEmpty v-if="sortedChapters.length === 0" description="还没有章节生成" />
    <NScrollbar style="max-height: 500px">
      <div class="stream-list">
        <div
          v-for="ch in sortedChapters"
          :key="ch.id"
          class="stream-item"
          :class="{ active: ch.chapter_number === currentChapter }"
        >
          <div class="item-header">
            <NText strong>第 {{ ch.chapter_number }} 章</NText>
            <span class="item-title">{{ ch.title || "未命名" }}</span>
            <NTag
              size="tiny"
              :type="ch.status === 'finalized' ? 'success' : ch.status === 'draft' ? 'default' : 'warning'"
            >
              {{ ch.status }}
            </NTag>
          </div>
          <div v-if="ch.draft" class="item-preview">
            {{ ch.draft.slice(0, 200) }}...
          </div>
          <div class="item-footer">
            <NText depth="3" style="font-size: 12px">{{ ch.word_count || 0 }} 字</NText>
          </div>
        </div>
      </div>
    </NScrollbar>
  </div>
</template>

<style scoped>
.chapter-stream { max-height: 500px; }
.stream-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.stream-item {
  padding: 12px 16px;
  border-radius: 10px;
  border: 1px solid rgba(128, 128, 128, 0.1);
  transition: all 0.2s;
}
.stream-item.active {
  border-color: #2080f0;
  box-shadow: 0 0 0 2px rgba(32, 128, 240, 0.1);
}
.item-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.item-title {
  flex: 1;
  color: #555;
  font-size: 14px;
}
.item-preview {
  font-size: 13px;
  color: #888;
  line-height: 1.6;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}
.item-footer {
  margin-top: 6px;
}
</style>
