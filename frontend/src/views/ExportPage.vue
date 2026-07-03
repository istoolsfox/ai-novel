<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import {
  NCard, NSpace, NButton, NTag, NText, NEmpty, NStatistic, NGrid, NGridItem, useMessage,
} from "naive-ui";
import { chapterApi, exportApi } from "../api";
import type { Chapter } from "../api/types";

const route = useRoute();
const message = useMessage();
const projectId = computed(() => route.params.projectId as string);
const chapters = ref<Chapter[]>([]);
const exporting = ref(false);

onMounted(async () => {
  chapters.value = await chapterApi.list(projectId.value);
});

const totalWords = computed(() =>
  chapters.value.reduce((sum, c) => sum + (c.word_count || 0), 0),
);

const formats = [
  { key: "markdown" as const, label: "Markdown", icon: "📝", desc: ".md 文件，通用纯文本" },
  { key: "txt" as const, label: "TXT", icon: "📄", desc: "纯文本，无格式" },
  { key: "docx" as const, label: "Word", icon: "📘", desc: ".docx 文档" },
  { key: "pdf" as const, label: "PDF", icon: "📕", desc: "PDF 文档" },
  { key: "epub" as const, label: "EPUB", icon: "📗", desc: "电子书格式" },
];

async function handleExport(format: typeof formats[0]) {
  exporting.value = true;
  try {
    await exportApi[format.key](projectId.value);
    message.success(`${format.label} 导出成功`);
  } catch (e: any) {
    message.error(e.message);
  } finally {
    exporting.value = false;
  }
}
</script>

<template>
  <div class="export-page">
    <h2 style="margin-bottom: 20px">📥 导出</h2>

    <NGrid :cols="3" :x-gap="16" :y-gap="16" style="margin-bottom: 20px">
      <NGridItem>
        <NCard>
          <NStatistic label="章节数" :value="chapters.length" />
        </NCard>
      </NGridItem>
      <NGridItem>
        <NCard>
          <NStatistic label="总字数" :value="totalWords" />
        </NCard>
      </NGridItem>
      <NGridItem>
        <NCard>
          <NStatistic
            label="已定稿"
            :value="chapters.filter(c => c.status === 'final' || c.status === 'finalized').length"
          />
        </NCard>
      </NGridItem>
    </NGrid>

    <NCard title="选择导出格式">
      <NEmpty v-if="chapters.length === 0" description="还没有章节，无法导出" />
      <div v-else class="format-grid">
        <NCard
          v-for="fmt in formats"
          :key="fmt.key"
          class="format-card"
          hoverable
          @click="handleExport(fmt)"
        >
          <div class="format-icon">{{ fmt.icon }}</div>
          <div class="format-info">
            <NText strong>{{ fmt.label }}</NText>
            <NText depth="3" style="font-size: 12px">{{ fmt.desc }}</NText>
          </div>
          <NButton
            size="small"
            type="primary"
            :loading="exporting"
            @click.stop="handleExport(fmt)"
          >
            导出
          </NButton>
        </NCard>
      </div>
    </NCard>

    <NCard title="章节预览" style="margin-top: 16px" v-if="chapters.length > 0">
      <NSpace vertical :size="8">
        <div v-for="ch in chapters" :key="ch.id" class="chapter-row">
          <NText>第 {{ ch.chapter_number }} 章 · {{ ch.title || "未命名" }}</NText>
          <NTag
            size="tiny"
            :type="ch.status === 'final' || ch.status === 'finalized' ? 'success' : 'default'"
          >
            {{ ch.status }}
          </NTag>
          <NText depth="3" style="font-size: 12px">{{ ch.word_count || 0 }} 字</NText>
        </div>
      </NSpace>
    </NCard>
  </div>
</template>

<style scoped>
.export-page { max-width: 800px; }
.format-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 12px;
}
.format-card {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  transition: transform 0.2s;
}
.format-card:hover { transform: translateY(-2px); }
.format-icon { font-size: 32px; }
.format-info { flex: 1; display: flex; flex-direction: column; }
.chapter-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 0;
}
</style>
