<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import {
  NSelect, NSpace, NButton, NInput, NTag, NText, NPopconfirm,
  NEmpty, useMessage,
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
    <div class="editor-toolbar">
      <NSpace align="center" class="toolbar-left">
        <NSelect
          v-model:value="selectedChapterId"
          :options="chapterOptions"
          class="chapter-select"
          placeholder="选择章节"
          @update:value="selectChapter"
        />
        <NTag v-if="currentChapter" size="small" :type="currentChapter.status === 'finalized' ? 'success' : 'default'">
          {{ currentChapter.status }}
        </NTag>
        <NText depth="3" style="font-size: 12px">{{ wordCount }} 字</NText>
      </NSpace>
      <NSpace class="toolbar-actions">
        <NButton size="small" type="primary" :loading="saving" @click="handleSave">保存</NButton>
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

    <div v-else-if="currentChapter" class="editor-grid">
      <main class="manuscript-panel">
        <div class="editor-header">
          <NText depth="3">正文编辑</NText>
          <NInput
            :value="currentChapter.title"
            placeholder="章节标题"
            class="title-input"
            @update:value="(v: string) => {
              if (currentChapter) currentChapter.title = v;
            }"
          />
        </div>
        <NInput
          v-model:value="editingDraft"
          type="textarea"
          :autosize="{ minRows: 30 }"
          placeholder="章节正文..."
          class="draft-editor"
        />
      </main>

      <aside class="chapter-sidebar">
        <div class="meta-block">
          <NText depth="3">当前章节</NText>
          <strong>第 {{ currentChapter.chapter_number }} 章</strong>
          <NText>{{ currentChapter.title || "未命名" }}</NText>
        </div>
        <div class="meta-grid">
          <div>
            <NText depth="3">字数</NText>
            <strong>{{ wordCount }}</strong>
          </div>
          <div>
            <NText depth="3">质量分</NText>
            <strong>{{ currentChapter.quality_score || 0 }}</strong>
          </div>
          <div>
            <NText depth="3">状态</NText>
            <NTag size="small" :type="currentChapter.status === 'finalized' ? 'success' : 'default'">
              {{ currentChapter.status }}
            </NTag>
          </div>
        </div>
        <div class="side-actions">
          <NButton block type="primary" :loading="saving" @click="handleSave">保存正文</NButton>
          <NPopconfirm @positive-click="handleFinalize">
            <template #trigger>
              <NButton block type="success" ghost>标记定稿</NButton>
            </template>
            确认定稿此章节？
          </NPopconfirm>
        </div>
        <div class="export-actions">
          <NText depth="3">全书导出</NText>
          <NSpace vertical size="small">
            <NButton block size="small" @click="handleExport('markdown')">Markdown</NButton>
            <NButton block size="small" @click="handleExport('docx')">DOCX</NButton>
            <NButton block size="small" @click="handleExport('pdf')">PDF</NButton>
          </NSpace>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.novel-editor-page {
  width: 100%;
  min-height: calc(100vh - 92px);
}
.editor-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 14px;
}
.toolbar-left,
.toolbar-actions {
  min-width: 0;
}
.chapter-select {
  width: min(420px, 48vw);
  min-width: 260px;
}
.editor-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 280px;
  gap: 16px;
  align-items: start;
}
.manuscript-panel,
.chapter-sidebar {
  border: 1px solid rgba(128, 128, 128, 0.16);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);
}
.manuscript-panel {
  min-width: 0;
  padding: 18px;
}
.editor-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 14px;
}
.title-input {
  max-width: 520px;
}
.draft-editor :deep(textarea) {
  min-height: calc(100vh - 240px) !important;
  padding: 26px 32px !important;
  font-size: 16px;
  line-height: 2;
  letter-spacing: 0;
  resize: vertical;
}
.chapter-sidebar {
  position: sticky;
  top: 0;
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 16px;
}
.meta-block,
.meta-grid,
.side-actions,
.export-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.meta-grid > div {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
@media (max-width: 960px) {
  .editor-grid {
    grid-template-columns: 1fr;
  }
  .chapter-sidebar {
    position: static;
    order: -1;
  }
  .chapter-select {
    width: 100%;
  }
  .toolbar-left,
  .toolbar-actions {
    width: 100%;
  }
}
</style>
