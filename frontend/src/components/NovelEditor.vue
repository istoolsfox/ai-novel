<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useRoute } from "vue-router";
import {
  NCard, NSelect, NSpace, NButton, NInput, NTag, NText, NPopconfirm,
  NSplit, NEmpty, NSpin, useMessage,
} from "naive-ui";
import { useChapterStore } from "../stores/chapter";
import { exportApi } from "../api";

const route = useRoute();
const message = useMessage();
const chapterStore = useChapterStore();

const projectId = computed(() => route.params.projectId as string);
const selectedChapterId = ref<string | null>(null);
const editingDraft = ref("");
const saving = ref(false);
const splitSize = ref(0.4);

onMounted(async () => {
  await chapterStore.fetchChapters(projectId.value);
  if (chapterStore.chapters.length > 0) {
    selectChapter(chapterStore.chapters[0].id);
  }
});

function selectChapter(id: string) {
  selectedChapterId.value = id;
  const ch = chapterStore.chapters.find((c) => c.id === id);
  editingDraft.value = ch?.draft || "";
}

const currentChapter = computed(() =>
  chapterStore.chapters.find((c) => c.id === selectedChapterId.value),
);

const chapterOptions = computed(() =>
  chapterStore.chapters.map((ch) => ({
    label: `第 ${ch.chapter_number} 章 · ${ch.title || "未命名"}`,
    value: ch.id,
  })),
);

async function handleSave() {
  if (!selectedChapterId.value || !currentChapter.value) return;
  saving.value = true;
  try {
    await chapterStore.updateChapter(projectId.value, selectedChapterId.value, {
      chapter_number: currentChapter.value.chapter_number,
      title: currentChapter.value.title,
      draft: editingDraft.value,
    });
    message.success("已保存");
  } catch (e: any) {
    message.error(e.message);
  } finally {
    saving.value = false;
  }
}

async function handleFinalize() {
  if (!selectedChapterId.value) return;
  try {
    await chapterStore.finalizeChapter(projectId.value, selectedChapterId.value);
    message.success("已定稿");
  } catch (e: any) {
    message.error(e.message);
  }
}

async function handleExport(format: "markdown" | "txt" | "docx" | "pdf" | "epub") {
  try {
    await exportApi[format](projectId.value);
    message.success(`已导出 ${format.toUpperCase()}`);
  } catch (e: any) {
    message.error(e.message);
  }
}

const wordCount = computed(() => editingDraft.value.length);
</script>

<template>
  <div class="novel-editor-page">
    <div class="toolbar">
      <NSpace align="center">
        <NSelect
          v-model:value="selectedChapterId"
          :options="chapterOptions"
          style="width: 300px"
          placeholder="选择章节"
          @update:value="selectChapter"
        />
        <NTag v-if="currentChapter" size="small" :type="currentChapter.status === 'finalized' ? 'success' : 'default'">
          {{ currentChapter.status }}
        </NTag>
        <NText depth="3" style="font-size: 12px">{{ wordCount }} 字</NText>
      </NSpace>
      <NSpace>
        <NButton size="small" :loading="saving" @click="handleSave">保存</NButton>
        <NPopconfirm @positive-click="handleFinalize">
          <template #trigger>
            <NButton size="small" type="success" ghost>定稿</NButton>
          </template>
          确认定稿此章节？
        </NPopconfirm>
        <NButton size="small" @click="handleExport('markdown')">MD</NButton>
        <NButton size="small" @click="handleExport('docx')">DOCX</NButton>
        <NButton size="small" @click="handleExport('pdf')">PDF</NButton>
      </NSpace>
    </div>

    <NEmpty
      v-if="chapterStore.chapters.length === 0"
      description="还没有章节，去启动托管生成吧"
      style="margin-top: 80px"
    />

    <NCard v-else-if="currentChapter" style="margin-top: 12px">
      <div class="editor-header">
        <NInput
          :value="currentChapter.title"
          placeholder="章节标题"
          style="width: 300px"
          @update:value="(v: string) => {
            if (currentChapter) currentChapter.title = v;
          }"
        />
      </div>
      <NInput
        v-model:value="editingDraft"
        type="textarea"
        :autosize="{ minRows: 20 }"
        placeholder="章节正文..."
        style="margin-top: 12px; font-size: 15px; line-height: 2;"
      />
    </NCard>
  </div>
</template>

<style scoped>
.novel-editor-page { max-width: 900px; }
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.editor-header {
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>
