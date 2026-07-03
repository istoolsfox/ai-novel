<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import {
  NCard, NSpace, NInput, NButton, NTag, NEmpty, NText, NGrid, NGridItem,
  NScrollbar, useMessage,
} from "naive-ui";
import { wikiApi } from "../api";

const route = useRoute();
const message = useMessage();
const projectId = computed(() => route.params.projectId as string);

const searchQuery = ref("");
const wikiPages = ref<Array<{ path: string; content: string }>>([]);
const pageCount = ref(0);
const selectedPage = ref<{ path: string; content: string } | null>(null);
const newPagePath = ref("");
const newPageContent = ref("");
const loading = ref(false);

async function fetchAll() {
  loading.value = true;
  try {
    wikiPages.value = await wikiApi.search(projectId.value, "");
    pageCount.value = wikiPages.value.length;
  } finally {
    loading.value = false;
  }
}

async function handleSearch() {
  loading.value = true;
  try {
    wikiPages.value = await wikiApi.search(projectId.value, searchQuery.value);
  } finally {
    loading.value = false;
  }
}

async function handleWrite() {
  if (!newPagePath.value.trim()) {
    message.warning("请输入 Wiki 路径");
    return;
  }
  try {
    await wikiApi; // wikiWrite 需要通过 api 调用
    // 直接用 fetch
    const { api } = await import("../api/client");
    await api.post(`/api/projects/${projectId.value}/wiki`, {
      path: newPagePath.value,
      content: newPageContent.value || "# 新页面",
    });
    message.success("已写入");
    newPagePath.value = "";
    newPageContent.value = "";
    await fetchAll();
  } catch (e: any) {
    message.error(e.message);
  }
}

function selectPage(page: { path: string; content: string }) {
  selectedPage.value = page;
}

onMounted(() => fetchAll());
</script>

<template>
  <div class="wiki-page">
    <div class="page-header">
      <h2>🧠 llmwiki 记忆</h2>
      <NText depth="3">长篇记忆、章节摘要与 Wiki 语义页面 · 共 {{ pageCount }} 页</NText>
    </div>

    <NGrid :cols="3" :x-gap="16" :y-gap="16" responsive="screen">
      <!-- 左侧：搜索 + 列表 -->
      <NGridItem :span="1">
        <NCard size="small">
          <NSpace vertical>
            <NInput
              v-model:value="searchQuery"
              placeholder="搜索 Wiki..."
              @keyup.enter="handleSearch"
            />
            <NButton size="small" @click="handleSearch">搜索</NButton>
          </NSpace>
          <NDivider style="margin: 12px 0" />
          <NScrollbar style="max-height: 400px">
            <NEmpty v-if="wikiPages.length === 0" description="暂无页面" />
            <div v-else class="wiki-list">
              <div
                v-for="page in wikiPages"
                :key="page.path"
                class="wiki-item"
                :class="{ active: selectedPage?.path === page.path }"
                @click="selectPage(page)"
              >
                <NText strong class="wiki-path">{{ page.path }}</NText>
                <NText depth="3" class="wiki-preview">
                  {{ page.content.slice(0, 80) }}...
                </NText>
              </div>
            </div>
          </NScrollbar>
        </NCard>
      </NGridItem>

      <!-- 中间：页面内容 -->
      <NGridItem :span="1">
        <NCard title="页面内容" size="small">
          <NEmpty v-if="!selectedPage" description="选择左侧页面查看内容" />
          <div v-else class="wiki-content">
            <NTag size="small" style="margin-bottom: 8px">{{ selectedPage.path }}</NTag>
            <pre class="wiki-text">{{ selectedPage.content }}</pre>
          </div>
        </NCard>
      </NGridItem>

      <!-- 右侧：写入新页面 -->
      <NGridItem :span="1">
        <NCard title="写入新页面" size="small">
          <NSpace vertical>
            <NInput v-model:value="newPagePath" placeholder="路径，如 notes/idea.md" />
            <NInput
              v-model:value="newPageContent"
              type="textarea"
              :autosize="{ minRows: 6, maxRows: 15 }"
              placeholder="页面内容..."
            />
            <NButton type="primary" @click="handleWrite">写入</NButton>
          </NSpace>
        </NCard>
      </NGridItem>
    </NGrid>
  </div>
</template>

<script lang="ts">
import { NDivider } from "naive-ui";
</script>

<style scoped>
.wiki-page { max-width: 1200px; }
.page-header { margin-bottom: 16px; }
.page-header h2 { font-size: 20px; font-weight: 700; margin-bottom: 4px; }
.wiki-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.wiki-item {
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s;
}
.wiki-item:hover { background: rgba(128, 128, 128, 0.05); }
.wiki-item.active {
  border-color: #2080f0;
  background: rgba(32, 128, 240, 0.05);
}
.wiki-path { display: block; font-size: 13px; }
.wiki-preview {
  display: block;
  font-size: 11px;
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.wiki-content { padding: 4px; }
.wiki-text {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  line-height: 1.7;
  max-height: 400px;
  overflow-y: auto;
  padding: 8px;
  border-radius: 6px;
  background: rgba(128, 128, 128, 0.04);
  font-family: inherit;
}
</style>
